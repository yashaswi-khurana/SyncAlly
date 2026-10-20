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

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syncally.application.payments import (
    AuthorizePaymentIntentCommand,
    DuplicateActivePaymentIntent,
    IdempotencyKeyReused,
    PaymentIntentAuthorizationOutcome,
    PaymentIntentCommandMismatch,
    PaymentMilestoneNotFound,
    UnauthorizedPaymentAuthorization,
    authorize_payment_intent,
)
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
    Deal,
    Organization,
    OrganizationMember,
    PaymentIntent,
    User,
)
from syncally.infrastructure.models import PaymentMilestone as PaymentMilestoneRow
from syncally.infrastructure.repositories.agreements import SqlAlchemyOutboxRepository

_PAYMENT_INTENT_AUTHORIZED_STATUS = "AUTHORIZED"
_ONE_ACTIVE_PER_MILESTONE_INDEX = "ix_payment_intents_one_active_per_milestone"


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
        milestone, deal = self._load_milestone_and_deal(command.payment_milestone_id)
        self._require_command_matches_milestone(command, milestone, deal)
        self._require_active_member(command.payer_organization_id, command.authorized_by)

        # Constructing the domain aggregate re-checks the payer/idempotency-key
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
        return PaymentIntentAuthorizationOutcome(intent_id=command.id, already_existed=False)

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
            return PaymentIntentAuthorizationOutcome(intent_id=existing.id, already_existed=True)
        raise IdempotencyKeyReused(
            f"Idempotency key {command.idempotency_key!r} is already used by a different payment authorization"
        )

    def _load_milestone_and_deal(self, payment_milestone_id: UUID) -> tuple[PaymentMilestoneRow, Deal]:
        row = self._db.execute(
            select(PaymentMilestoneRow, Deal)
            .join(Deal, Deal.id == PaymentMilestoneRow.deal_id)
            .where(PaymentMilestoneRow.id == payment_milestone_id)
        ).first()
        if row is None:
            raise PaymentMilestoneNotFound(f"No payment milestone {payment_milestone_id}")
        milestone, deal = row
        return milestone, deal

    def _require_command_matches_milestone(
        self, command: AuthorizePaymentIntentCommand, milestone: PaymentMilestoneRow, deal: Deal
    ) -> None:
        mismatches = {
            "deal_id": milestone.deal_id != command.deal_id,
            "agreement_version_id": milestone.agreement_version_id != command.agreement_version_id,
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

    def _require_active_member(self, organization_id: UUID, user_id: UUID) -> None:
        is_active_member = self._db.scalar(
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
        )
        if is_active_member is None:
            raise UnauthorizedPaymentAuthorization(
                "authorized_by must be an active member of the payer organization"
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
        outcome = authorize_payment_intent(
            command,
            SqlAlchemyPaymentIntentRepository(db),
            SqlAlchemyOutboxRepository(db),
            now=now,
        )
        db.commit()
        return outcome
    except Exception:
        db.rollback()
        raise
