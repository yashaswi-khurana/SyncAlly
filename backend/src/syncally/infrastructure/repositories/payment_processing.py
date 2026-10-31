"""Persistence for the PayPal payment worker.

Each repository method commits before returning. The application can therefore
call PayPal only after the database transaction that prepared the operation has
closed.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from syncally.application.payment_processing import (
    PaymentInvoiceLineItem,
    PaymentInvoiceRequest,
    PaymentNeedsAction,
    PaymentProcessingRepository,
    PaymentRetryableError,
    PaymentWorkItem,
    payment_invoice_number,
)
from syncally.application.payments import (
    OFFLINE_RECONCILIATION_EVENT_TYPE,
    PAYPAL_WEBHOOK_RECONCILIATION_EVENT_TYPE,
)
from syncally.domain.agreements.agreement import AgreementStatus
from syncally.domain.agreements.trade_terms import TradeTerms
from syncally.domain.organizations.organization import OrganizationMemberRole
from syncally.domain.payments.intent import (
    PaymentIntent as DomainPaymentIntent,
)
from syncally.domain.payments.intent import (
    PaymentIntentStatus,
    VerifiedProviderPaymentState,
    VerifiedProviderPaymentStatus,
)
from syncally.domain.payments.intent import (
    PaymentMilestone as DomainPaymentMilestone,
)
from syncally.domain.shared.errors import DomainError
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
    AuditEvent,
    Deal,
    Organization,
    OrganizationMember,
    OutboxEvent,
    PaymentIntent,
    PaymentMilestone,
    User,
    WebhookEvent,
)
from syncally.operations import Operation, log_operation

SessionFactory = Callable[[], Session]

logger = logging.getLogger(__name__)


class SqlAlchemyPaymentProcessingRepository(PaymentProcessingRepository):
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def load(self, payment_intent_id: UUID) -> PaymentWorkItem | None:
        with self._session_factory() as db:
            row = db.get(PaymentIntent, payment_intent_id)
            if row is None:
                return None
            status = PaymentIntentStatus(row.status)
            amount = Money(row.amount, row.currency)
            invoice_number = payment_invoice_number(row.id)
            reference = str(row.id)
            request = None
            request_error_code = None
            request_error_detail = None
            if status in {
                PaymentIntentStatus.AUTHORIZED,
                PaymentIntentStatus.CREATE_PENDING,
                PaymentIntentStatus.CREATE_UNKNOWN,
            }:
                try:
                    request = self._invoice_request(db, row, amount, invoice_number, reference)
                except PaymentNeedsAction as error:
                    request_error_code = error.code
                    request_error_detail = error.detail
            return PaymentWorkItem(
                payment_intent_id=row.id,
                status=status,
                amount=amount,
                invoice_number=invoice_number,
                reference=reference,
                provider_invoice_id=row.provider_invoice_id,
                request_payload_hash=row.request_payload_hash,
                provider_create_started_at=row.provider_create_started_at,
                invoice_request=request,
                request_error_code=request_error_code,
                request_error_detail=request_error_detail,
                failure_code=row.failure_code,
                failure_detail=row.failure_detail,
                provider=row.provider,
                execution_mode=row.execution_mode,
                version=row.version,
            )

    def begin_create(self, payment_intent_id: UUID, request_payload_hash: str) -> None:
        def transition(intent: DomainPaymentIntent, row: PaymentIntent) -> dict:
            if row.request_payload_hash and row.request_payload_hash != request_payload_hash:
                raise PaymentNeedsAction(
                    "PAYMENT_INVOICE_REQUEST_CHANGED",
                    "Invoice details changed before the provider request; inspect the intent manually.",
                )
            intent.begin_create()
            return {
                "request_payload_hash": request_payload_hash,
                "provider_create_started_at": row.provider_create_started_at or datetime.now(UTC),
                "failure_code": None,
                "failure_detail": None,
            }

        self._transition(payment_intent_id, transition)

    def mark_create_unknown(self, payment_intent_id: UUID) -> None:
        def transition(intent: DomainPaymentIntent, row: PaymentIntent) -> dict:
            if intent.status is PaymentIntentStatus.CREATE_UNKNOWN:
                return {}
            intent.record_create_unknown()
            return {}

        self._transition(payment_intent_id, transition)

    def reconcile_create_not_found(self, payment_intent_id: UUID) -> None:
        def transition(intent: DomainPaymentIntent, row: PaymentIntent) -> dict:
            intent.reconcile_provider_state(
                VerifiedProviderPaymentState(
                    status=VerifiedProviderPaymentStatus.NOT_FOUND,
                    paid_amount=Money(Decimal("0"), row.currency),
                )
            )
            return {"failure_code": None, "failure_detail": None}

        self._transition(payment_intent_id, transition)

    def record_provider_created(
        self, payment_intent_id: UUID, provider_invoice_id: str
    ) -> None:
        def transition(intent: DomainPaymentIntent, row: PaymentIntent) -> dict:
            if intent.status is PaymentIntentStatus.PROVIDER_CREATED:
                if intent.provider_reference != provider_invoice_id:
                    raise PaymentNeedsAction(
                        "PAYMENT_PROVIDER_REFERENCE_CONFLICT",
                        "A different provider invoice is already saved; inspect the intent manually.",
                    )
                return {}
            intent.record_provider_created(provider_invoice_id)
            return {"failure_code": None, "failure_detail": None}

        self._transition(payment_intent_id, transition)

    def mark_sent(self, payment_intent_id: UUID) -> None:
        def transition(intent: DomainPaymentIntent, row: PaymentIntent) -> dict:
            if intent.status in {
                PaymentIntentStatus.SENT,
                PaymentIntentStatus.PENDING,
                PaymentIntentStatus.PARTIALLY_PAID,
                PaymentIntentStatus.PAID,
            }:
                return {}
            intent.mark_sent()
            return {"failure_code": None, "failure_detail": None}

        self._transition(payment_intent_id, transition)

    def mark_failure(self, payment_intent_id: UUID, code: str, detail: str) -> None:
        def transition(intent: DomainPaymentIntent, row: PaymentIntent) -> dict:
            if intent.status is PaymentIntentStatus.FAILED:
                return {"failure_code": code, "failure_detail": detail}
            if intent.status is not PaymentIntentStatus.PROVIDER_CREATED:
                intent.mark_failed()
            return {"failure_code": code, "failure_detail": detail}

        self._transition(payment_intent_id, transition)

    def mark_manual_action(self, payment_intent_id: UUID, code: str, detail: str) -> None:
        def transition(intent: DomainPaymentIntent, row: PaymentIntent) -> dict:
            if intent.status is PaymentIntentStatus.CREATE_PENDING:
                # The worker cannot prove whether the external create ran.
                intent.record_create_unknown()
            elif intent.status in {
                PaymentIntentStatus.AUTHORIZED,
            }:
                intent.mark_failed()
            return {"failure_code": code, "failure_detail": detail}

        self._transition(payment_intent_id, transition)

    def record_reconciliation(
        self,
        payment_intent_id: UUID,
        payment_state: VerifiedProviderPaymentState,
        *,
        outbox_event_id: UUID,
        webhook_event_id: UUID,
        lease_until: datetime,
    ) -> None:
        """Apply provider truth and finish its webhook work in one transaction."""
        now = datetime.now(UTC)
        with self._session_factory() as db:
            outbox_statement = select(OutboxEvent).where(
                OutboxEvent.id == outbox_event_id,
                OutboxEvent.status == "PROCESSING",
                OutboxEvent.next_attempt_at == lease_until,
                OutboxEvent.next_attempt_at > now,
            )
            intent_statement = select(PaymentIntent).where(
                PaymentIntent.id == payment_intent_id
            )
            webhook_statement = select(WebhookEvent).where(
                WebhookEvent.id == webhook_event_id,
                WebhookEvent.payment_intent_id == payment_intent_id,
            )
            if db.bind is not None and db.bind.dialect.name == "postgresql":
                outbox_statement = outbox_statement.with_for_update()
                intent_statement = intent_statement.with_for_update()
                webhook_statement = webhook_statement.with_for_update()
            outbox = db.scalar(outbox_statement)
            if outbox is None:
                log_operation(
                    logger,
                    Operation.PAYMENT_LEASE_LOST,
                    outbox_event_id=outbox_event_id,
                    payment_intent_id=payment_intent_id,
                )
                return
            row = db.scalar(intent_statement)
            webhook = db.scalar(webhook_statement)
            if row is None or webhook is None:
                raise PaymentNeedsAction(
                    "PAYMENT_RECONCILIATION_RECORD_MISSING",
                    "The payment or webhook record is missing; inspect the reconciliation event.",
                )

            simulation = payment_state.source == "OFFLINE_DEMO"
            expected_provider = "OFFLINE_DEMO" if simulation else "PAYPAL"
            expected_mode = "OFFLINE_DEMO" if simulation else "PAYPAL_SANDBOX"
            expected_event = OFFLINE_RECONCILIATION_EVENT_TYPE if simulation else PAYPAL_WEBHOOK_RECONCILIATION_EVENT_TYPE
            if ((row.provider, row.execution_mode) != (expected_provider, expected_mode)
                    or webhook.provider != expected_provider or webhook.processed
                    or outbox.aggregate_type != "payment_intent" or outbox.aggregate_id != row.id
                    or outbox.event_type != expected_event
                    or outbox.payload != {"payment_intent_id": str(row.id), "webhook_event_id": str(webhook.id)}
                    or payment_state.provider_reference != row.provider_invoice_id):
                raise PaymentNeedsAction("PAYMENT_PROVENANCE_UNRESOLVED", "Reconciliation evidence does not match the intent and event identity.")
            if simulation:
                from syncally.infrastructure.repositories.offline_payments import (
                    require_simulation_scope,
                    simulation_state,
                )

                try:
                    require_simulation_scope(db, row, UUID(webhook.raw_payload["actor_user_id"]))
                    if (webhook.event_type != expected_event or row.version != webhook.raw_payload["expected_version"]
                            or simulation_state(row, webhook.raw_payload) != payment_state):
                        raise PaymentNeedsAction("PAYMENT_STATE_CHANGED", "Simulation evidence or payment version changed.")
                except (KeyError, ValueError, TypeError) as error:
                    raise PaymentNeedsAction("PAYMENT_RECONCILIATION_REJECTED", "Simulation evidence is invalid.") from error

            previous_status = row.status
            try:
                intent = _restore_domain_intent(db, row)
                if intent.status is PaymentIntentStatus.PAID:
                    if (
                        payment_state.status is not VerifiedProviderPaymentStatus.PAID
                        or payment_state.paid_amount.amount != row.amount
                        or payment_state.paid_amount.currency != row.currency
                    ):
                        raise PaymentNeedsAction(
                            "PAYMENT_TERMINAL_STATE_CONFLICT",
                            "PayPal's current payment state conflicts with the saved paid state; inspect it manually.",
                        )
                elif intent.status in {
                    PaymentIntentStatus.FAILED,
                    PaymentIntentStatus.CANCELLED,
                }:
                    raise PaymentNeedsAction(
                        "PAYMENT_TERMINAL_STATE_CONFLICT",
                        "The saved payment is terminal and cannot be reconciled automatically.",
                    )
                else:
                    intent.reconcile_provider_state(payment_state)
            except (DomainError, ValueError, TypeError) as error:
                raise PaymentNeedsAction(
                    "PAYMENT_RECONCILIATION_REJECTED",
                    "PayPal's current payment state conflicts with the saved payment; inspect it manually.",
                ) from error

            status_changed = intent.status is not PaymentIntentStatus(row.status)
            amount_changed = intent.reconciled_amount != (
                Money(row.reconciled_amount, row.currency)
                if row.reconciled_amount is not None
                else None
            )
            result = db.execute(
                update(PaymentIntent)
                .where(
                    PaymentIntent.id == payment_intent_id,
                    PaymentIntent.version == row.version,
                    PaymentIntent.status == row.status,
                )
                .values(
                    status=intent.status.value,
                    provider_invoice_id=intent.provider_reference,
                    reconciled_amount=(
                        intent.reconciled_amount.amount if intent.reconciled_amount else None
                    ),
                    last_checked_at=now,
                    reconciliation_source=payment_state.source if payment_state.status is not VerifiedProviderPaymentStatus.UNKNOWN else row.reconciliation_source,
                    last_reconciled_at=(
                        now
                        if payment_state.status is not VerifiedProviderPaymentStatus.UNKNOWN
                        else row.last_reconciled_at
                    ),
                    version=row.version + 1,
                )
            )
            if result.rowcount != 1:
                raise PaymentRetryableError(
                    "PAYMENT_STATE_CHANGED",
                    "The payment state changed concurrently; fetch PayPal's current state and retry.",
                )

            db.add(
                AuditEvent(
                    aggregate_type="payment_intent",
                    aggregate_id=payment_intent_id,
                    event_type=(
                        "PAYMENT_STATE_RECONCILED"
                        if status_changed or amount_changed
                        else "PAYMENT_RECONCILIATION_CHECKED"
                    ),
                    actor_type="SIMULATION" if simulation else "PROVIDER",
                    actor_id="OFFLINE_DEMO" if simulation else "PAYPAL",
                    occurred_at=now,
                    correlation_id=webhook.provider_event_id,
                    payload={
                        "previous_status": previous_status,
                        "current_status": intent.status.value,
                        "provider_status": payment_state.status.value,
                        "paid_amount": str(payment_state.paid_amount.amount),
                        "currency": payment_state.paid_amount.currency,
                        "reconciliation_source": payment_state.source,
                    },
                )
            )
            webhook.processed = True
            outbox.status = "DELIVERED"
            outbox.delivered_at = now
            outbox.next_attempt_at = None
            outbox.error_detail = None
            fields = dict(
                outbox_event_id=outbox.id,
                payment_intent_id=payment_intent_id,
                deal_id=row.deal_id,
                event_type=outbox.event_type,
                status=outbox.status,
                retry_count=outbox.retry_count,
                payment_status=intent.status.value,
            )
            db.commit()
            log_operation(logger, Operation.PAYMENT_OUTBOX_COMPLETED, **fields)

    def record_reconciliation_failure(
        self,
        payment_intent_id: UUID,
        *,
        outbox_event_id: UUID,
        webhook_event_id: UUID,
        lease_until: datetime,
        error_code: str,
        error_detail: str,
    ) -> None:
        """Atomically retain a failed check without changing the last trusted state."""
        now = datetime.now(UTC)
        with self._session_factory() as db:
            outbox_statement = select(OutboxEvent).where(
                OutboxEvent.id == outbox_event_id,
                OutboxEvent.status == "PROCESSING",
                OutboxEvent.next_attempt_at == lease_until,
                OutboxEvent.next_attempt_at > now,
            )
            intent_statement = select(PaymentIntent).where(
                PaymentIntent.id == payment_intent_id
            )
            webhook_statement = select(WebhookEvent).where(
                WebhookEvent.id == webhook_event_id,
                WebhookEvent.payment_intent_id == payment_intent_id,
            )
            if db.bind is not None and db.bind.dialect.name == "postgresql":
                outbox_statement = outbox_statement.with_for_update()
                intent_statement = intent_statement.with_for_update()
                webhook_statement = webhook_statement.with_for_update()
            outbox = db.scalar(outbox_statement)
            if outbox is None:
                log_operation(
                    logger,
                    Operation.PAYMENT_LEASE_LOST,
                    outbox_event_id=outbox_event_id,
                    payment_intent_id=payment_intent_id,
                )
                return

            intent = db.scalar(intent_statement)
            webhook = db.scalar(webhook_statement)
            db.add(
                AuditEvent(
                    aggregate_type="payment_intent",
                    aggregate_id=payment_intent_id,
                    event_type="PAYMENT_RECONCILIATION_NEEDS_ACTION",
                    actor_type="SYSTEM",
                    actor_id="payment-worker",
                    occurred_at=now,
                    correlation_id=(
                        webhook.provider_event_id if webhook is not None else str(webhook_event_id)
                    ),
                    payload={
                        "payment_status": intent.status if intent is not None else None,
                        "error_code": error_code,
                    },
                )
            )
            if webhook is not None and outbox.aggregate_id == payment_intent_id and outbox.payload == {"payment_intent_id": str(payment_intent_id), "webhook_event_id": str(webhook.id)}:
                webhook.processed = True
            outbox.status = "FAILED"
            outbox.next_attempt_at = None
            outbox.error_detail = error_detail
            fields = dict(
                outbox_event_id=outbox.id,
                payment_intent_id=payment_intent_id,
                deal_id=intent.deal_id if intent is not None else None,
                event_type=outbox.event_type,
                status=outbox.status,
                retry_count=outbox.retry_count,
                payment_status=intent.status if intent is not None else None,
                error_code=error_code,
                failure_kind="PERMANENT",
            )
            db.commit()
            log_operation(logger, Operation.PAYMENT_OUTBOX_COMPLETED, level=logging.ERROR, **fields)

    def _invoice_request(
        self,
        db: Session,
        intent: PaymentIntent,
        amount: Money,
        invoice_number: str,
        reference: str,
    ) -> PaymentInvoiceRequest:
        row = db.execute(
            select(PaymentMilestone, Deal, AgreementVersion)
            .join(Deal, Deal.id == PaymentMilestone.deal_id)
            .join(AgreementVersion, AgreementVersion.id == PaymentMilestone.agreement_version_id)
            .where(
                PaymentMilestone.id == intent.payment_milestone_id,
                PaymentMilestone.deal_id == intent.deal_id,
                PaymentMilestone.agreement_version_id == intent.agreement_version_id,
            )
        ).first()
        if row is None:
            raise PaymentNeedsAction(
                "PAYMENT_AGREEMENT_NOT_FOUND",
                "The committed payment milestone or agreement is unavailable; inspect the intent.",
            )
        milestone, deal, agreement = row
        try:
            terms = TradeTerms.from_canonical_json(agreement.canonical_terms_json)
            terms.validate_for_commit()
        except (ArithmeticError, DomainError, KeyError, TypeError, ValueError) as error:
            raise PaymentNeedsAction(
                "PAYMENT_AGREEMENT_INVALID",
                "The committed agreement terms cannot be used to create an invoice.",
            ) from error
        if (
            agreement.status != AgreementStatus.COMMITTED.value
            or terms.terms_hash != agreement.terms_hash
            or terms.buyer_id != deal.buyer_organization_id
            or terms.seller_id != deal.seller_organization_id
            or deal.seller_organization_id != intent.seller_organization_id
            or deal.buyer_organization_id != intent.payer_organization_id
            or milestone.payer_organization_id != intent.payer_organization_id
            or milestone.amount != intent.amount
            or milestone.currency != intent.currency
            or terms.total != amount
        ):
            raise PaymentNeedsAction(
                "PAYMENT_AGREEMENT_MISMATCH",
                "The saved payment intent does not match its committed agreement.",
            )

        buyer = db.get(Organization, deal.buyer_organization_id)
        seller = db.get(Organization, deal.seller_organization_id)
        if buyer is None or seller is None or buyer.status != "ACTIVE" or seller.status != "ACTIVE":
            raise PaymentNeedsAction(
                "PAYMENT_ORGANIZATION_INACTIVE",
                "Both deal organizations must be active to create a payment invoice.",
            )

        admin_users = list(
            db.scalars(
                select(User)
                .join(OrganizationMember, OrganizationMember.user_id == User.id)
                .where(
                    OrganizationMember.organization_id == buyer.id,
                    OrganizationMember.role == OrganizationMemberRole.ADMIN.value,
                    OrganizationMember.status == "ACTIVE",
                    User.status == "ACTIVE",
                )
                .order_by(User.id)
            )
        )
        if len(admin_users) != 1:
            code = (
                "PAYMENT_BUYER_CONTACT_MISSING"
                if not admin_users
                else "PAYMENT_BUYER_CONTACT_AMBIGUOUS"
            )
            detail = (
                "The buyer organization needs exactly one active admin as its invoice contact."
            )
            raise PaymentNeedsAction(code, detail)
        contact = admin_users[0]
        line_items = tuple(
            PaymentInvoiceLineItem(
                name=item.description,
                description=item.sku,
                quantity=item.quantity,
                unit=item.unit,
                unit_price=item.unit_price,
            )
            for item in terms.line_items
        )
        return PaymentInvoiceRequest(
            payment_intent_id=intent.id,
            deal_id=deal.id,
            invoice_number=invoice_number,
            reference=reference,
            amount=amount,
            seller_business_name=seller.legal_name,
            buyer_business_name=buyer.legal_name,
            buyer_contact_name=contact.display_name,
            buyer_contact_email=contact.email,
            line_items=line_items,
        )

    def _transition(
        self,
        payment_intent_id: UUID,
        transition: Callable[[DomainPaymentIntent, PaymentIntent], dict],
    ) -> None:
        with self._session_factory() as db:
            statement = select(PaymentIntent).where(PaymentIntent.id == payment_intent_id)
            if db.bind is not None and db.bind.dialect.name == "postgresql":
                statement = statement.with_for_update()
            row = db.scalar(statement)
            if row is None:
                raise PaymentNeedsAction(
                    "PAYMENT_INTENT_NOT_FOUND",
                    "The payment intent no longer exists; inspect the outbox event.",
                )
            try:
                intent = _restore_domain_intent(db, row)
                additional_values = transition(intent, row)
            except PaymentNeedsAction:
                raise
            except (DomainError, ValueError, TypeError) as error:
                raise PaymentNeedsAction(
                    "PAYMENT_STATE_INVALID",
                    "The saved payment state cannot be transitioned safely.",
                ) from error
            values = {
                "status": intent.status.value,
                "provider_invoice_id": intent.provider_reference,
                "reconciled_amount": (
                    intent.reconciled_amount.amount if intent.reconciled_amount else None
                ),
                "version": row.version + 1,
                **additional_values,
            }
            result = db.execute(
                update(PaymentIntent)
                .where(
                    PaymentIntent.id == payment_intent_id,
                    PaymentIntent.version == row.version,
                    PaymentIntent.status == row.status,
                )
                .values(**values)
            )
            if result.rowcount != 1:
                raise PaymentNeedsAction(
                    "PAYMENT_STATE_CHANGED",
                    "The payment state changed concurrently; reconcile the intent before retrying.",
                )
            fields = dict(
                payment_intent_id=payment_intent_id,
                deal_id=row.deal_id,
                payment_status=intent.status.value,
            )
            db.commit()
            log_operation(logger, Operation.PAYMENT_STATE_CHANGED, **fields)


def _restore_domain_intent(db: Session, row: PaymentIntent) -> DomainPaymentIntent:
    milestone_row = db.get(PaymentMilestone, row.payment_milestone_id)
    if milestone_row is None:
        raise PaymentNeedsAction(
            "PAYMENT_MILESTONE_NOT_FOUND",
            "The payment milestone is missing; inspect the payment intent.",
        )
    return DomainPaymentIntent.restore(
        status=PaymentIntentStatus(row.status),
        id=PaymentIntentId(row.id),
        milestone=DomainPaymentMilestone(
            id=PaymentMilestoneId(milestone_row.id),
            deal_id=DealId(milestone_row.deal_id),
            agreement_version_id=AgreementVersionId(milestone_row.agreement_version_id),
            sequence_number=milestone_row.sequence_number,
            payer_organization_id=OrganizationId(milestone_row.payer_organization_id),
            amount=Money(milestone_row.amount, milestone_row.currency),
            trigger=milestone_row.trigger_type,
            due_condition=milestone_row.due_condition,
        ),
        seller_organization_id=OrganizationId(row.seller_organization_id),
        payer_organization_id=OrganizationId(row.payer_organization_id),
        authorized_by=UserId(row.authorized_by),
        idempotency_key=row.idempotency_key,
        created_at=row.created_at,
        provider_reference=row.provider_invoice_id,
        reconciled_amount=(
            Money(row.reconciled_amount, row.currency)
            if row.reconciled_amount is not None
            else None
        ),
    )
