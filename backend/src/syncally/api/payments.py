"""Read the latest persisted payment state for a deal."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
from syncally.api.authorization import require_deal_action, resolve_actor_party
from syncally.api.deals import get_deal_repository
from syncally.application.agreements import AgreementNotFound, get_current_agreement
from syncally.application.deals import DealNotFound, DealRepository, get_deal
from syncally.application.identity import ActorContext
from syncally.application.payments import (
    AuthorizePaymentIntentCommand,
    DuplicateActivePaymentIntent,
    IdempotencyKeyReused,
    PaymentModeChanged,
    PaymentStatusRepository,
    UnauthorizedPaymentAuthorization,
    list_current_payment_statuses,
)
from syncally.config import settings
from syncally.domain.agreements.agreement import AgreementStatus
from syncally.domain.agreements.fulfillment import FulfillmentStage
from syncally.domain.agreements.trade_terms import TradeTerms
from syncally.domain.payments.intent import (
    DELIVERY_TRIGGERS,
    PaymentExecutionMode,
    PaymentIntentStatus,
    check_milestone_trigger_eligibility,
)
from syncally.domain.shared.money import (
    Money,
    bounded_decimal,
    canonical_decimal,
    has_excess_currency_precision,
)
from syncally.infrastructure.database import get_db
from syncally.infrastructure.deal_completion import _event_total, _scaled
from syncally.infrastructure.models import (
    FulfillmentEvent,
    Obligation,
    PaymentIntent,
    PaymentMilestone,
)
from syncally.infrastructure.paypal import PAYPAL_INVOICE_SUPPORTED_CURRENCIES
from syncally.infrastructure.repositories.agreements import SqlAlchemyAgreementRepository
from syncally.infrastructure.repositories.payments import (
    SqlAlchemyPaymentIntentRepository,
    _build_invoice_url,
    _derive_lifecycle_state,
    authorize_payment_intent_in_transaction,
)

router = APIRouter(prefix="/deals/{deal_id}/payments", tags=["payments"])


class PaymentOutboxStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    RETRYING = "RETRYING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


class PaymentStatusResponse(BaseModel):
    """Safe payment summary including invoice link and retry diagnostics."""

    id: UUID
    milestone_sequence: int
    amount: str
    currency: str
    status: PaymentIntentStatus
    requires_polling: bool
    reconciled_amount: str | None
    last_checked_at: datetime | None
    last_reconciled_at: datetime | None
    invoice_url: str | None = None
    recipient_email: str | None = None
    recipient_name: str | None = None
    retry_count: int = 0
    next_retry_at: datetime | None = None
    outbox_status: PaymentOutboxStatus | None = None
    retry_scheduled_at: datetime | None = None
    lease_expires_at: datetime | None = None
    failure_reason: str | None = None
    provider: str = "UNKNOWN"
    execution_mode: str = "LEGACY_UNRESOLVED"
    reconciliation_source: str = "LEGACY_UNVERIFIED"
    invoice_reference: str | None = None
    version: int = 0
    payment_milestone_id: UUID | None = None
    milestone_id: str | None = None
    source_terms_reference: str | None = None
    lifecycle_state: str | None = None
    is_eligible: bool | None = None


class AuthorizePaymentRequest(BaseModel):
    """Authorize one invoice for the current committed agreement."""

    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(min_length=1, max_length=256)
    expected_mode: PaymentExecutionMode | None = None
    payment_milestone_id: UUID | None = None
    milestone_id: str | None = None


class AuthorizePaymentResponse(BaseModel):
    id: UUID
    status: str
    already_existed: bool
    provider: str
    execution_mode: str
    payment_milestone_id: UUID | None = None
    milestone_id: str | None = None


class PaymentPreviewResponse(BaseModel):
    execution_mode: PaymentExecutionMode
    provider: str


class MilestoneAllocationResponse(BaseModel):
    obligation_id: str
    amount: str
    currency: str


class MilestonePaymentSummaryResponse(BaseModel):
    id: UUID
    sequence_number: int
    milestone_id: str | None = None
    source_terms_reference: str | None = None
    amount: str
    currency: str
    trigger_type: str
    due_condition: str
    lifecycle_state: str
    is_eligible: bool
    ineligibility_reason: str | None = None
    allocations: list[MilestoneAllocationResponse] = Field(default_factory=list)
    active_intent_id: UUID | None = None
    intent_status: PaymentIntentStatus | None = None
    reconciled_amount: str | None = None
    last_checked_at: datetime | None = None
    last_reconciled_at: datetime | None = None
    invoice_url: str | None = None
    invoice_reference: str | None = None
    failure_reason: str | None = None


def _check_milestone_delivery_confirmed(
    db: Session,
    deal_id: UUID,
    agreement_version_id: UUID,
    milestone: PaymentMilestone,
    term: object | None,
    terms: TradeTerms,
) -> bool:
    allocations = getattr(term, "allocations", ())
    if allocations:
        for alloc in allocations:
            obligation = db.scalar(
                select(Obligation).where(
                    Obligation.deal_id == deal_id,
                    Obligation.agreement_version_id == agreement_version_id,
                    Obligation.obligation_type == "DELIVERY",
                    Obligation.source_terms_reference == alloc.obligation_id,
                )
            )
            if obligation is None:
                return False
            matching_obligation_ids = select(Obligation.id).where(
                Obligation.deal_id == deal_id,
                Obligation.source_terms_reference == alloc.obligation_id,
            )
            events = list(
                db.scalars(
                    select(FulfillmentEvent).where(
                        FulfillmentEvent.deal_id == deal_id,
                        FulfillmentEvent.obligation_id.in_(matching_obligation_ids),
                    )
                )
            )
            shipment = next((s for s in terms.shipments if s.id == alloc.obligation_id), None)
            if shipment is None:
                return False
            if shipment.quantity is not None:
                expected = _scaled(shipment.quantity)
            elif shipment.allocations:
                expected = sum(_scaled(a.quantity) for a in shipment.allocations)
            else:
                return False
            confirmed = _event_total(events, FulfillmentStage.CONFIRMED)
            if confirmed < expected:
                return False
        return True

    if milestone.obligation_id:
        ob = db.get(Obligation, milestone.obligation_id)
        ref = ob.source_terms_reference if ob else None
        matching_obligation_ids = (
            select(Obligation.id).where(
                Obligation.deal_id == deal_id,
                Obligation.source_terms_reference == ref,
            )
            if ref
            else [milestone.obligation_id]
        )
        events = list(
            db.scalars(
                select(FulfillmentEvent).where(
                    FulfillmentEvent.deal_id == deal_id,
                    FulfillmentEvent.obligation_id.in_(matching_obligation_ids),
                )
            )
        )
        confirmed = _event_total(events, FulfillmentStage.CONFIRMED)
        if terms.shipments:
            s0 = terms.shipments[0]
            if s0.quantity is not None:
                expected = _scaled(s0.quantity)
            elif s0.allocations:
                expected = sum(_scaled(a.quantity) for a in s0.allocations)
            else:
                expected = 0
            return confirmed >= expected if expected > 0 else False
        return confirmed > 0

    delivery_obs = list(
        db.scalars(
            select(Obligation).where(
                Obligation.deal_id == deal_id,
                Obligation.agreement_version_id == agreement_version_id,
                Obligation.obligation_type == "DELIVERY",
            )
        )
    )
    if not delivery_obs:
        return False
    for index, ob in enumerate(delivery_obs):
        matching_obligation_ids = select(Obligation.id).where(
            Obligation.deal_id == deal_id,
            Obligation.source_terms_reference == ob.source_terms_reference,
        )
        events = list(
            db.scalars(
                select(FulfillmentEvent).where(
                    FulfillmentEvent.deal_id == deal_id,
                    FulfillmentEvent.obligation_id.in_(matching_obligation_ids),
                )
            )
        )
        matching_shipment = next(
            (
                s
                for s in terms.shipments
                if (s.id and s.id == ob.source_terms_reference)
                or ob.source_terms_reference == f"shipments[{terms.shipments.index(s)}]"
            ),
            terms.shipments[index] if index < len(terms.shipments) else None,
        )
        if matching_shipment is None:
            return False
        if matching_shipment.quantity is not None:
            expected = _scaled(matching_shipment.quantity)
        elif matching_shipment.allocations:
            expected = sum(_scaled(a.quantity) for a in matching_shipment.allocations)
        else:
            return False
        if _event_total(events, FulfillmentStage.CONFIRMED) < expected:
            return False
    return True


@router.get("/preview", response_model=PaymentPreviewResponse)
def preview_payment_route(deal_id: UUID, organization_id: UUID | None = None, actor: ActorContext = Depends(get_current_actor),
                          deal_repository: DealRepository = Depends(get_deal_repository), db: Session = Depends(get_db)) -> PaymentPreviewResponse:
    try:
        deal = get_deal(actor, deal_id, deal_repository)
        selected_org = resolve_actor_party(actor, deal, organization_id)
        require_deal_action(actor, deal, selected_org, "payments.read")
        agreement = get_current_agreement(actor, deal_id, deal_repository, SqlAlchemyAgreementRepository(db))
        if agreement.status is not AgreementStatus.COMMITTED:
            raise HTTPException(status_code=409, detail="The agreement must be committed before payment preview")
        mode = PaymentExecutionMode(settings.payment_mode)
        return PaymentPreviewResponse(execution_mode=mode, provider=mode.provider)
    except (AgreementNotFound, DealNotFound) as error:
        raise HTTPException(status_code=404, detail="Deal not found") from error


def get_payment_status_repository(db: Session = Depends(get_db)) -> PaymentStatusRepository:
    """Provide the persisted payment status read port for this request."""
    return SqlAlchemyPaymentIntentRepository(db)


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=AuthorizePaymentResponse)
def authorize_payment_route(
    deal_id: UUID,
    payload: AuthorizePaymentRequest,
    organization_id: UUID | None = None,
    actor: ActorContext = Depends(get_current_actor),
    deal_repository: DealRepository = Depends(get_deal_repository),
    db: Session = Depends(get_db),
) -> AuthorizePaymentResponse:
    """Let an authenticated seller queue one payment request after agreement commit."""
    try:
        deal = get_deal(actor, deal_id, deal_repository)
        selected_org = resolve_actor_party(actor, deal, organization_id)
        if selected_org != deal.seller_organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Payment authorization must be performed for the seller organization",
            )
        require_deal_action(actor, deal, selected_org, "payments.authorize")
        agreement = get_current_agreement(
            actor,
            deal_id,
            deal_repository,
            SqlAlchemyAgreementRepository(db),
        )
        if agreement.status is not AgreementStatus.COMMITTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The agreement must be committed before payment can be requested",
            )

        try:
            if hasattr(agreement, "terms") and isinstance(agreement.terms, TradeTerms):
                terms = agreement.terms
            elif hasattr(agreement, "canonical_terms_json"):
                terms = TradeTerms.from_canonical_json(agreement.canonical_terms_json)
            else:
                raise ValueError("Agreement has no terms")
        except Exception as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Committed agreement terms could not be parsed",
            ) from error

        # Validate milestone sums, finite Decimal bounds, and zero-residual policy
        for p in terms.payment_terms:
            try:
                bounded_decimal(
                    p.amount.amount,
                    allow_negative=False,
                    allow_zero=False,
                    field_name="Payment milestone amount",
                )
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Invalid payment milestone amount: {exc}",
                ) from exc
            if has_excess_currency_precision(p.amount.amount, p.amount.currency):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Payment milestone amount {p.amount.amount} exceeds currency '{p.amount.currency}' precision",
                )
            if p.amount.currency != terms.total.currency:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Currency mismatch in payment terms: {p.amount.currency} != {terms.total.currency}",
                )
            if p.allocations:
                alloc_sum = sum((a.amount.amount for a in p.allocations), Decimal("0"))
                if alloc_sum != p.amount.amount:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Allocations for payment term do not sum to milestone amount ({alloc_sum} != {p.amount.amount})",
                    )
                for a in p.allocations:
                    if a.amount.currency != p.amount.currency:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Allocation currency does not match milestone currency",
                        )
                    try:
                        bounded_decimal(
                            a.amount.amount,
                            allow_negative=False,
                            allow_zero=False,
                            field_name="Allocation amount",
                        )
                    except Exception as exc:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"Invalid allocation amount: {exc}",
                        ) from exc
                    if has_excess_currency_precision(a.amount.amount, a.amount.currency):
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"Allocation amount {a.amount.amount} exceeds currency '{a.amount.currency}' precision",
                        )

        milestone_sum = sum((p.amount.amount for p in terms.payment_terms), Decimal("0"))
        if milestone_sum != terms.total.amount:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Payment milestone amounts ({milestone_sum}) do not equal terms total ({terms.total.amount})",
            )

        all_milestones = list(
            db.scalars(
                select(PaymentMilestone)
                .where(PaymentMilestone.agreement_version_id == agreement.version_id)
                .order_by(PaymentMilestone.sequence_number)
            )
        )
        if not all_milestones:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The committed agreement has no payment milestone",
            )

        milestone = None
        if payload.payment_milestone_id:
            milestone = next((m for m in all_milestones if m.id == payload.payment_milestone_id), None)
            if milestone is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Payment milestone not found",
                )
        elif payload.milestone_id:
            milestone = next((m for m in all_milestones if m.source_terms_reference == payload.milestone_id), None)
            if milestone is None:
                match_idx = next((i for i, t in enumerate(terms.payment_terms) if t.id == payload.milestone_id), None)
                if match_idx is not None and match_idx < len(all_milestones):
                    milestone = all_milestones[match_idx]
            if milestone is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Payment milestone '{payload.milestone_id}' not found",
                )
        else:
            if len(all_milestones) == 1:
                milestone = all_milestones[0]
            else:
                active_milestone_ids = set(
                    db.scalars(
                        select(PaymentIntent.payment_milestone_id).where(
                            PaymentIntent.deal_id == deal_id,
                            PaymentIntent.status.notin_(("FAILED", "CANCELLED")),
                        )
                    )
                )
                available = [
                    m for m in all_milestones
                    if m.status != "PAID" and m.id not in active_milestone_ids
                ]
                milestone = available[0] if available else all_milestones[0]

        matching_term = next(
            (t for t in terms.payment_terms if (milestone.source_terms_reference and t.id == milestone.source_terms_reference)),
            None,
        )
        if matching_term is None and 0 <= milestone.sequence_number - 1 < len(terms.payment_terms):
            matching_term = terms.payment_terms[milestone.sequence_number - 1]

        matching_milestone_ids = (
            select(PaymentMilestone.id).where(
                PaymentMilestone.deal_id == deal_id,
                PaymentMilestone.source_terms_reference == milestone.source_terms_reference,
            )
            if milestone.source_terms_reference
            else [milestone.id]
        )
        existing_paid = db.scalar(
            select(PaymentIntent).where(
                PaymentIntent.deal_id == deal_id,
                PaymentIntent.payment_milestone_id.in_(matching_milestone_ids),
                PaymentIntent.status == "PAID",
            ).limit(1)
        )
        if (
            milestone.status == "PAID"
            or (existing_paid is not None and existing_paid.idempotency_key != payload.idempotency_key)
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Payment milestone {milestone.sequence_number} has already been paid",
            )

        # Trigger condition & eligibility evaluation
        delivery_confirmed = False
        trigger_norm = milestone.trigger_type.strip().casefold()
        if trigger_norm in DELIVERY_TRIGGERS:
            delivery_confirmed = _check_milestone_delivery_confirmed(
                db, deal_id, agreement.version_id, milestone, matching_term, terms
            )

        eligible, reason = check_milestone_trigger_eligibility(
            milestone.trigger_type,
            agreement_committed=True,
            delivery_confirmed=delivery_confirmed,
        )
        if not eligible:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Payment milestone {milestone.sequence_number} is not eligible: {reason}",
            )

        if (
            settings.payment_mode == PaymentExecutionMode.PAYPAL_SANDBOX.value
            and milestone.currency not in PAYPAL_INVOICE_SUPPORTED_CURRENCIES
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"PayPal Invoicing does not support {milestone.currency}. "
                    "The agreed trade currency remains unchanged; both parties must "
                    "approve a PayPal-supported currency before requesting an invoice."
                ),
            )

        outcome = authorize_payment_intent_in_transaction(
            db,
            AuthorizePaymentIntentCommand(
                id=uuid4(),
                deal_id=deal_id,
                agreement_version_id=agreement.version_id,
                payment_milestone_id=milestone.id,
                seller_organization_id=deal.seller_organization_id,
                payer_organization_id=milestone.payer_organization_id,
                authorized_by=actor.user_id,
                amount=Money(milestone.amount, milestone.currency),
                idempotency_key=payload.idempotency_key,
                execution_mode=PaymentExecutionMode(settings.payment_mode),
                expected_mode=payload.expected_mode,
                source_terms_reference=milestone.source_terms_reference,
            ),
        )
        intent = db.get(PaymentIntent, outcome.intent_id)
        if intent is None:
            raise RuntimeError("Authorized payment intent was not persisted")
        return AuthorizePaymentResponse(
            id=intent.id,
            status=intent.status,
            already_existed=outcome.already_existed,
            provider=intent.provider,
            execution_mode=intent.execution_mode,
            payment_milestone_id=milestone.id,
            milestone_id=milestone.source_terms_reference,
        )
    except HTTPException:
        db.rollback()
        raise
    except (AgreementNotFound, DealNotFound) as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found") from error
    except UnauthorizedPaymentAuthorization as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except (DuplicateActivePaymentIntent, IdempotencyKeyReused, PaymentModeChanged) as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except Exception:
        db.rollback()
        raise


@router.get("", response_model=list[PaymentStatusResponse])
def list_payment_statuses_route(
    deal_id: UUID,
    organization_id: UUID | None = None,
    actor: ActorContext = Depends(get_current_actor),
    deal_repository: DealRepository = Depends(get_deal_repository),
    payment_repository: PaymentStatusRepository = Depends(get_payment_status_repository),
    db: Session = Depends(get_db),
) -> list[PaymentStatusResponse]:
    """Return current-agreement payment state to either active deal participant."""
    try:
        deal = get_deal(actor, deal_id, deal_repository)
        selected_org = resolve_actor_party(actor, deal, organization_id)
        require_deal_action(actor, deal, selected_org, "payments.read")
        payments = list_current_payment_statuses(
            actor,
            deal_id,
            deal_repository,
            SqlAlchemyAgreementRepository(db),
            payment_repository,
        )
    except DealNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found") from error
    return [
        PaymentStatusResponse(
            id=payment.intent_id,
            milestone_sequence=payment.milestone_sequence,
            amount=canonical_decimal(payment.amount.amount),
            currency=payment.amount.currency,
            status=payment.status,
            requires_polling=not PaymentIntentStatus(payment.status).is_terminal,
            reconciled_amount=(
                canonical_decimal(payment.reconciled_amount.amount)
                if payment.reconciled_amount is not None
                else None
            ),
            last_checked_at=payment.last_checked_at,
            last_reconciled_at=payment.last_reconciled_at,
            provider=payment.provider,
            execution_mode=payment.execution_mode,
            reconciliation_source=payment.reconciliation_source,
            invoice_reference=payment.invoice_reference,
            version=payment.version,
            invoice_url=getattr(payment, "invoice_url", None),
            recipient_email=getattr(payment, "recipient_email", None),
            recipient_name=getattr(payment, "recipient_name", None),
            retry_count=getattr(payment, "retry_count", 0),
            next_retry_at=getattr(payment, "next_retry_at", None),
            outbox_status=getattr(payment, "outbox_status", None),
            retry_scheduled_at=getattr(payment, "retry_scheduled_at", None),
            lease_expires_at=getattr(payment, "lease_expires_at", None),
            failure_reason=getattr(payment, "failure_reason", None),
            payment_milestone_id=getattr(payment, "payment_milestone_id", None),
            milestone_id=getattr(payment, "source_terms_reference", None),
            source_terms_reference=getattr(payment, "source_terms_reference", None),
            lifecycle_state=getattr(payment, "lifecycle_state", None),
            is_eligible=getattr(payment, "is_eligible", None),
        )
        for payment in payments
    ]


@router.get("/milestones", response_model=list[MilestonePaymentSummaryResponse])
def list_payment_milestones_route(
    deal_id: UUID,
    organization_id: UUID | None = None,
    actor: ActorContext = Depends(get_current_actor),
    deal_repository: DealRepository = Depends(get_deal_repository),
    db: Session = Depends(get_db),
) -> list[MilestonePaymentSummaryResponse]:
    """Return all payment milestones and their current lifecycle states for the committed agreement."""
    try:
        deal = get_deal(actor, deal_id, deal_repository)
        selected_org = resolve_actor_party(actor, deal, organization_id)
        require_deal_action(actor, deal, selected_org, "payments.read")
        agreement = get_current_agreement(
            actor,
            deal_id,
            deal_repository,
            SqlAlchemyAgreementRepository(db),
        )
    except DealNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found") from error
    except AgreementNotFound:
        return []

    if agreement.status is not AgreementStatus.COMMITTED:
        return []

    try:
        if hasattr(agreement, "terms") and isinstance(agreement.terms, TradeTerms):
            terms = agreement.terms
        elif hasattr(agreement, "canonical_terms_json"):
            terms = TradeTerms.from_canonical_json(agreement.canonical_terms_json)
        else:
            return []
    except Exception:
        return []

    milestone_rows = list(
        db.scalars(
            select(PaymentMilestone)
            .where(PaymentMilestone.agreement_version_id == agreement.version_id)
            .order_by(PaymentMilestone.sequence_number)
        )
    )
    if not milestone_rows:
        return []

    intent_rows = list(
        db.scalars(
            select(PaymentIntent)
            .where(PaymentIntent.deal_id == deal_id)
            .order_by(PaymentIntent.created_at.desc(), PaymentIntent.id.desc())
        )
    )

    intents_by_milestone: dict[UUID, PaymentIntent] = {}
    intents_by_reference: dict[str, PaymentIntent] = {}
    for intent in intent_rows:
        if intent.payment_milestone_id not in intents_by_milestone:
            intents_by_milestone[intent.payment_milestone_id] = intent
        m_row = db.get(PaymentMilestone, intent.payment_milestone_id)
        if m_row and m_row.source_terms_reference and m_row.source_terms_reference not in intents_by_reference:
            intents_by_reference[m_row.source_terms_reference] = intent

    results: list[MilestonePaymentSummaryResponse] = []
    for milestone in milestone_rows:
        matching_term = next(
            (
                t
                for t in terms.payment_terms
                if (milestone.source_terms_reference and t.id == milestone.source_terms_reference)
            ),
            None,
        )
        if matching_term is None and 0 <= milestone.sequence_number - 1 < len(terms.payment_terms):
            matching_term = terms.payment_terms[milestone.sequence_number - 1]

        intent = intents_by_milestone.get(milestone.id)
        if intent is None and milestone.source_terms_reference:
            intent = intents_by_reference.get(milestone.source_terms_reference)

        delivery_confirmed = False
        trigger_norm = milestone.trigger_type.strip().casefold()
        if trigger_norm in DELIVERY_TRIGGERS:
            delivery_confirmed = _check_milestone_delivery_confirmed(
                db, deal_id, agreement.version_id, milestone, matching_term, terms
            )

        is_eligible, ineligibility_reason = check_milestone_trigger_eligibility(
            milestone.trigger_type,
            agreement_committed=True,
            delivery_confirmed=delivery_confirmed,
        )

        if milestone.status == "PAID" or (intent is not None and intent.status == "PAID"):
            is_eligible = False
            ineligibility_reason = "Payment already reconciled"

        lifecycle_state = (
            _derive_lifecycle_state(intent.status)
            if intent is not None
            else ("reconciled" if milestone.status == "PAID" else ("eligible" if is_eligible else "ineligible"))
        )

        alloc_responses = [
            MilestoneAllocationResponse(
                obligation_id=a.obligation_id,
                amount=canonical_decimal(a.amount.amount),
                currency=a.amount.currency,
            )
            for a in getattr(matching_term, "allocations", ())
        ]

        invoice_url = None
        if intent is not None and intent.execution_mode == "PAYPAL_SANDBOX":
            invoice_url = _build_invoice_url(
                intent.provider, intent.provider_invoice_id, intent.status
            )

        results.append(
            MilestonePaymentSummaryResponse(
                id=milestone.id,
                sequence_number=milestone.sequence_number,
                milestone_id=milestone.source_terms_reference,
                source_terms_reference=milestone.source_terms_reference,
                amount=canonical_decimal(milestone.amount),
                currency=milestone.currency,
                trigger_type=milestone.trigger_type,
                due_condition=milestone.due_condition,
                lifecycle_state=lifecycle_state,
                is_eligible=is_eligible,
                ineligibility_reason=ineligibility_reason if not is_eligible else None,
                allocations=alloc_responses,
                active_intent_id=intent.id if intent else None,
                intent_status=PaymentIntentStatus(intent.status) if intent else None,
                reconciled_amount=(
                    canonical_decimal(intent.reconciled_amount)
                    if intent and intent.reconciled_amount is not None
                    else (canonical_decimal(milestone.amount) if milestone.status == "PAID" else None)
                ),
                last_checked_at=intent.last_checked_at if intent else None,
                last_reconciled_at=intent.last_reconciled_at if intent else None,
                invoice_url=invoice_url,
                invoice_reference=intent.provider_invoice_id if intent else None,
                failure_reason=intent.failure_reason if intent else None,
            )
        )
    return results
