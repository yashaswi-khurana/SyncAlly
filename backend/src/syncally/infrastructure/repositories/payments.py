"""SQLAlchemy persistence for authorized payment intents.

Mirrors the crash-safety shape of ``repositories.agreements``: the intent row
and its outbox row are written in one caller-owned transaction, and the
one-active-intent-per-milestone invariant is enforced by a database
constraint (``ix_payment_intents_one_active_per_milestone``) rather than a
check-then-insert race. No PayPal call happens anywhere in this module.

``add`` flushes directly rather than inside ``begin_nested()``: every error
path here rolls back the whole caller-owned transaction (see
``authorize_payment_intent_in_transaction``) rather than continuing it, so no
savepoint is needed to isolate the failed insert.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import case, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syncally.application.payments import (
    AuthorizePaymentIntentCommand,
    DuplicateActivePaymentIntent,
    IdempotencyKeyReused,
    PaymentIntentAuthorizationOutcome,
    PaymentIntentCommandMismatch,
    PaymentMilestoneNotFound,
    PaymentModeChanged,
    PaymentStatusRecord,
    authorize_payment_intent,
)
from syncally.domain.agreements.agreement import AgreementStatus
from syncally.domain.payments.intent import PaymentExecutionMode
from syncally.domain.payments.intent import PaymentIntent as DomainPaymentIntent
from syncally.domain.payments.intent import PaymentMilestone as DomainPaymentMilestone
from syncally.domain.shared.identifiers import (
    AgreementVersionId,
    DealId,
    OrganizationId,
    PaymentIntentId,
    PaymentMilestoneId,
    UserId,
)
from syncally.domain.shared.money import Money
from syncally.infrastructure.models import (
    AgreementVersion,
    Deal,
    Organization,
    OrganizationMember,
    OutboxEvent,
    PaymentIntent,
    User,
)
from syncally.infrastructure.models import PaymentMilestone as PaymentMilestoneRow
from syncally.infrastructure.repositories.agreements import SqlAlchemyOutboxRepository

_PAYMENT_INTENT_AUTHORIZED_STATUS = "AUTHORIZED"
_ONE_ACTIVE_PER_MILESTONE_INDEX = "ix_payment_intents_one_active_per_milestone"


@dataclass(frozen=True, slots=True)
class ExtendedPaymentStatusRecord(PaymentStatusRecord):
    """Extended payment status record with buyer contact, retry diagnostics, and invoice link."""

    invoice_url: str | None = None
    recipient_email: str | None = None
    recipient_name: str | None = None
    retry_count: int = 0
    next_retry_at: datetime | None = None
    outbox_status: str | None = None
    retry_scheduled_at: datetime | None = None
    lease_expires_at: datetime | None = None
    failure_reason: str | None = None


def _utc_timestamp(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _build_invoice_url(
    provider: str, provider_invoice_id: str | None, status: str | None = None
) -> str | None:
    if not provider_invoice_id:
        return None
    raw_id = provider_invoice_id.strip()
    if raw_id.startswith("private-"):
        return None
    if status in ("PAID", "CANCELLED"):
        return None
    if raw_id.startswith("http://") or raw_id.startswith("https://"):
        return raw_id
    if provider.upper() == "PAYPAL":
        clean_id = raw_id.lstrip("#")
        return f"https://www.sandbox.paypal.com/invoice/p/#{clean_id}"
    return None


def _violated_constraint_name(error: IntegrityError) -> str | None:
    """Postgres names the violated constraint; SQLite (used in tests) doesn't."""
    diag = getattr(error.orig, "diag", None)
    return getattr(diag, "constraint_name", None)


def _is_one_active_per_milestone_violation(error: IntegrityError) -> bool:
    """Only the one-active-per-milestone index means ``DuplicateActivePaymentIntent``."""
    constraint_name = _violated_constraint_name(error)
    if constraint_name is not None:
        return constraint_name == _ONE_ACTIVE_PER_MILESTONE_INDEX
    # SQLite reports the column, not the index - distinct enough from the
    # idempotency_key and FK/check violations this must not be confused with.
    return "payment_milestone_id" in str(error.orig)


def _is_idempotency_key_violation(error: IntegrityError) -> bool:
    constraint_name = _violated_constraint_name(error)
    if constraint_name is not None:
        return "idempotency_key" in constraint_name
    return "idempotency_key" in str(error.orig)


class SqlAlchemyPaymentIntentRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(
        self, command: AuthorizePaymentIntentCommand, *, now: datetime
    ) -> PaymentIntentAuthorizationOutcome:
        milestone, deal, agreement_version = self._load_milestone_and_deal(
            command.payment_milestone_id
        )
        self._require_command_matches_milestone(
            command, milestone, deal, agreement_version
        )

        # Constructing the domain aggregate re-checks the seller/payer/idempotency-key
        # invariants that matter even if every field above already lined up
        # (e.g. a blank idempotency key) - see domain.payments.intent.
        DomainPaymentIntent(
            id=PaymentIntentId(command.id),
            milestone=DomainPaymentMilestone(
                id=PaymentMilestoneId(milestone.id),
                deal_id=DealId(milestone.deal_id),
                agreement_version_id=AgreementVersionId(milestone.agreement_version_id),
                sequence_number=milestone.sequence_number,
                payer_organization_id=OrganizationId(milestone.payer_organization_id),
                amount=Money(milestone.amount, milestone.currency),
                trigger=milestone.trigger_type,
                due_condition=milestone.due_condition,
            ),
            seller_organization_id=OrganizationId(command.seller_organization_id),
            payer_organization_id=OrganizationId(command.payer_organization_id),
            authorized_by=UserId(command.authorized_by),
            idempotency_key=command.idempotency_key,
            created_at=now,
        )

        # Checked up front, not just on the index violation below: a retry
        # for the *same* milestone also trips the one-active-per-milestone
        # index, and which of the two a database reports first on a single
        # conflicting INSERT isn't something to rely on.
        existing = self._db.scalar(
            select(PaymentIntent).where(PaymentIntent.idempotency_key == command.idempotency_key)
        )
        if existing is not None:
            return self._matching_outcome_or_raise(existing, command)

        mode = PaymentExecutionMode(command.execution_mode)
        if command.expected_mode is not None and command.expected_mode != mode:
            raise PaymentModeChanged("Payment mode changed; preview the new authorization again")

        try:
            self._db.add(
                PaymentIntent(
                    id=command.id,
                    deal_id=command.deal_id,
                    agreement_version_id=command.agreement_version_id,
                    payment_milestone_id=command.payment_milestone_id,
                    seller_organization_id=command.seller_organization_id,
                    payer_organization_id=command.payer_organization_id,
                    authorized_by=command.authorized_by,
                    amount=command.amount.amount,
                    currency=command.amount.currency,
                    status=_PAYMENT_INTENT_AUTHORIZED_STATUS,
                    provider=mode.provider,
                    execution_mode=mode.value,
                    reconciliation_source="NONE",
                    idempotency_key=command.idempotency_key,
                    version=0,
                    created_at=now,
                )
            )
            self._db.flush()
        except IntegrityError as error:
            if _is_idempotency_key_violation(error):
                # Lost the race: a concurrent insert claimed this key between
                # the check above and this flush.
                self._db.rollback()
                existing = self._db.scalar(
                    select(PaymentIntent).where(PaymentIntent.idempotency_key == command.idempotency_key)
                )
                return self._matching_outcome_or_raise(existing, command)
            if not _is_one_active_per_milestone_violation(error):
                raise
            raise DuplicateActivePaymentIntent(
                "An active payment intent already exists for this milestone"
            ) from error
        return PaymentIntentAuthorizationOutcome(
            intent_id=command.id, already_existed=False, provider=mode.provider, execution_mode=mode.value
        )

    def list_for_agreement(self, agreement_version_id: UUID) -> list[PaymentStatusRecord]:
        """Read each milestone's latest status with buyer contact and retry diagnostics."""
        rows = self._db.execute(
            select(PaymentIntent, PaymentMilestoneRow)
            .join(
                PaymentMilestoneRow,
                PaymentMilestoneRow.id == PaymentIntent.payment_milestone_id,
            )
            .where(PaymentIntent.agreement_version_id == agreement_version_id)
            .order_by(
                PaymentMilestoneRow.sequence_number,
                PaymentIntent.created_at.desc(),
                PaymentIntent.id.desc(),
            )
        ).all()
        if not rows:
            return []

        latest_by_milestone: dict[UUID, tuple[PaymentIntent, PaymentMilestoneRow]] = {}
        for intent, milestone in rows:
            latest_by_milestone.setdefault(milestone.id, (intent, milestone))

        intents = [intent for intent, _ in latest_by_milestone.values()]
        intent_ids = [intent.id for intent in intents]
        payer_org_ids = {intent.payer_organization_id for intent in intents}

        outbox_by_intent: dict[UUID, OutboxEvent] = {}
        if intent_ids:
            outbox_rows = self._db.execute(
                select(OutboxEvent)
                .where(
                    OutboxEvent.aggregate_type == "payment_intent",
                    OutboxEvent.aggregate_id.in_(intent_ids),
                )
                .order_by(
                    case((OutboxEvent.status.in_(("RETRYING", "PROCESSING", "PENDING")), 0), else_=1),
                    OutboxEvent.created_at.desc(),
                    OutboxEvent.id.desc(),
                )
            ).scalars().all()
            for outbox in outbox_rows:
                outbox_by_intent.setdefault(outbox.aggregate_id, outbox)

        contact_by_org: dict[UUID, tuple[str | None, str | None]] = {}
        if payer_org_ids:
            org_rows = self._db.execute(
                select(Organization.id, Organization.legal_name)
                .where(Organization.id.in_(payer_org_ids))
            ).all()
            for org_id, legal_name in org_rows:
                contact_by_org[org_id] = (None, legal_name)

            member_rows = self._db.execute(
                select(
                    OrganizationMember.organization_id,
                    User.display_name,
                    User.email,
                )
                .join(User, User.id == OrganizationMember.user_id)
                .where(
                    OrganizationMember.organization_id.in_(payer_org_ids),
                    OrganizationMember.status == "ACTIVE",
                    User.status == "ACTIVE",
                )
                .order_by(
                    case((OrganizationMember.role == "ADMIN", 0), else_=1),
                    User.id,
                )
            ).all()
            for org_id, display_name, email in member_rows:
                current_email, _ = contact_by_org.get(org_id, (None, None))
                if current_email is None:
                    contact_by_org[org_id] = (email, display_name)

        records: list[PaymentStatusRecord] = []
        for intent, milestone in latest_by_milestone.values():
            outbox = outbox_by_intent.get(intent.id)
            recipient_email, recipient_name = contact_by_org.get(
                intent.payer_organization_id, (None, None)
            )

            failure_reason = intent.failure_code
            if failure_reason is None and intent.status == "FAILED":
                failure_reason = intent.failure_detail or (outbox.error_detail if outbox else None)
            elif failure_reason is None and outbox and outbox.status in ("FAILED", "DEAD_LETTER"):
                failure_reason = outbox.error_detail

            next_retry_at = outbox.next_attempt_at if outbox is not None else None
            if next_retry_at is not None and next_retry_at.tzinfo is None:
                next_retry_at = next_retry_at.replace(tzinfo=UTC)

            records.append(
                ExtendedPaymentStatusRecord(
                    intent_id=intent.id,
                    milestone_sequence=milestone.sequence_number,
                    amount=Money(intent.amount, intent.currency),
                    status=intent.status,
                    reconciled_amount=(
                        Money(intent.reconciled_amount, intent.currency)
                        if intent.reconciled_amount is not None
                        else None
                    ),
                    last_checked_at=_utc_timestamp(intent.last_checked_at),
                    last_reconciled_at=_utc_timestamp(intent.last_reconciled_at),
                    provider=intent.provider,
                    execution_mode=intent.execution_mode,
                    reconciliation_source=intent.reconciliation_source,
                    invoice_reference=intent.provider_invoice_id if intent.execution_mode == "OFFLINE_DEMO" else None,
                    version=intent.version,
                    invoice_url=_build_invoice_url(
                        intent.provider, intent.provider_invoice_id, intent.status
                    ) if intent.execution_mode == "PAYPAL_SANDBOX" else None,
                    recipient_email=recipient_email,
                    recipient_name=recipient_name,
                    retry_count=outbox.retry_count if outbox is not None else 0,
                    next_retry_at=next_retry_at,
                    outbox_status=outbox.status if outbox is not None else None,
                    retry_scheduled_at=(
                        next_retry_at
                        if outbox is not None and (
                            outbox.status == "RETRYING"
                            or (outbox.status == "PENDING" and outbox.retry_count > 0)
                        )
                        else None
                    ),
                    lease_expires_at=(
                        next_retry_at
                        if outbox is not None and outbox.status == "PROCESSING"
                        else None
                    ),
                    failure_reason=failure_reason,
                )
            )
        return records

    def _matching_outcome_or_raise(
        self, existing: PaymentIntent | None, command: AuthorizePaymentIntentCommand
    ) -> PaymentIntentAuthorizationOutcome:
        """Recognize a lost-acknowledgement retry: same idempotency key, same authorization.

        Only a genuine replay returns successfully - a key reused for a
        materially different authorization is a client bug, not a retry.
        """
        if existing is not None and (
            existing.deal_id == command.deal_id
            and existing.agreement_version_id == command.agreement_version_id
            and existing.payment_milestone_id == command.payment_milestone_id
            and existing.seller_organization_id == command.seller_organization_id
            and existing.payer_organization_id == command.payer_organization_id
            and existing.authorized_by == command.authorized_by
            and existing.amount == command.amount.amount
            and existing.currency == command.amount.currency
        ):
            return PaymentIntentAuthorizationOutcome(
                intent_id=existing.id, already_existed=True,
                provider=existing.provider, execution_mode=existing.execution_mode,
            )
        raise IdempotencyKeyReused(
            f"Idempotency key {command.idempotency_key!r} is already used by a different payment authorization"
        )

    def is_active_seller_member(self, organization_id: UUID, user_id: UUID) -> bool:
        """Application authorization port, backed by current database membership."""
        return self._db.scalar(
            select(OrganizationMember.id)
            .join(Organization, Organization.id == OrganizationMember.organization_id)
            .join(User, User.id == OrganizationMember.user_id)
            .where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == "ACTIVE",
                Organization.status == "ACTIVE",
                User.status == "ACTIVE",
            )
        ) is not None

    def _load_milestone_and_deal(
        self, payment_milestone_id: UUID
    ) -> tuple[PaymentMilestoneRow, Deal, AgreementVersion]:
        row = self._db.execute(
            select(PaymentMilestoneRow, Deal, AgreementVersion)
            .join(Deal, Deal.id == PaymentMilestoneRow.deal_id)
            .join(AgreementVersion, AgreementVersion.id == PaymentMilestoneRow.agreement_version_id)
            .where(PaymentMilestoneRow.id == payment_milestone_id)
        ).first()
        if row is None:
            raise PaymentMilestoneNotFound(f"No payment milestone {payment_milestone_id}")
        milestone, deal, agreement_version = row
        return milestone, deal, agreement_version

    def _require_command_matches_milestone(
        self,
        command: AuthorizePaymentIntentCommand,
        milestone: PaymentMilestoneRow,
        deal: Deal,
        agreement_version: AgreementVersion,
    ) -> None:
        mismatches = {
            "deal_id": milestone.deal_id != command.deal_id,
            "agreement_version_id": milestone.agreement_version_id != command.agreement_version_id,
            "agreement_version_deal_id": agreement_version.deal_id != command.deal_id,
            "agreement_version_status": agreement_version.status != AgreementStatus.COMMITTED.value,
            "seller_organization_id": deal.seller_organization_id != command.seller_organization_id,
            "payer_organization_id": milestone.payer_organization_id != command.payer_organization_id,
            "amount": milestone.amount != command.amount.amount,
            "currency": milestone.currency != command.amount.currency,
        }
        bad_fields = [field for field, mismatched in mismatches.items() if mismatched]
        if bad_fields:
            raise PaymentIntentCommandMismatch(
                f"Command disagrees with its payment milestone on: {', '.join(bad_fields)}"
            )


def authorize_payment_intent_in_transaction(
    db: Session,
    command: AuthorizePaymentIntentCommand,
    *,
    now: datetime | None = None,
) -> PaymentIntentAuthorizationOutcome:
    """Run AuthorizePaymentIntent as one transaction: commits on success, rolls back on failure.

    The intent row and its ``PAYMENT_INTENT_AUTHORIZED`` outbox row are saved
    together or not at all, so a crash between them cannot happen.
    """
    now = now or datetime.now(UTC)
    try:
        repository = SqlAlchemyPaymentIntentRepository(db)
        outcome = authorize_payment_intent(
            command,
            repository,
            repository,
            SqlAlchemyOutboxRepository(db),
            now=now,
        )
        db.commit()
        return outcome
    except Exception:
        db.rollback()
        raise
