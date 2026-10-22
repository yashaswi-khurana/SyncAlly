"""Persistence for the PayPal payment worker.

Each repository method commits before returning. The application can therefore
call PayPal only after the database transaction that prepared the operation has
closed.
"""

from __future__ import annotations

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
    PaymentWorkItem,
    payment_invoice_number,
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
    Deal,
    Organization,
    OrganizationMember,
    PaymentIntent,
    PaymentMilestone,
    User,
)

SessionFactory = Callable[[], Session]


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
                PaymentIntentStatus.PROVIDER_CREATED,
            }:
                intent.mark_failed()
            return {"failure_code": code, "failure_detail": detail}

        self._transition(payment_intent_id, transition)

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
            db.commit()


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
