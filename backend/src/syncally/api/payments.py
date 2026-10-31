"""Read the latest persisted payment state for a deal."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
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
from syncally.domain.payments.intent import PaymentExecutionMode, PaymentIntentStatus
from syncally.domain.shared.money import Money, canonical_decimal
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import PaymentIntent, PaymentMilestone
from syncally.infrastructure.repositories.agreements import SqlAlchemyAgreementRepository
from syncally.infrastructure.repositories.payments import (
    SqlAlchemyPaymentIntentRepository,
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


class AuthorizePaymentRequest(BaseModel):
    """Authorize one invoice for the current committed agreement."""

    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(min_length=1, max_length=256)
    expected_mode: PaymentExecutionMode | None = None


class AuthorizePaymentResponse(BaseModel):
    id: UUID
    status: str
    already_existed: bool
    provider: str
    execution_mode: str


class PaymentPreviewResponse(BaseModel):
    execution_mode: PaymentExecutionMode
    provider: str


@router.get("/preview", response_model=PaymentPreviewResponse)
def preview_payment_route(deal_id: UUID, actor: ActorContext = Depends(get_current_actor),
                          deal_repository: DealRepository = Depends(get_deal_repository), db: Session = Depends(get_db)) -> PaymentPreviewResponse:
    try:
        deal = get_deal(actor, deal_id, deal_repository)
        if not SqlAlchemyPaymentIntentRepository(db).is_active_seller_member(deal.seller_organization_id, actor.user_id):
            raise HTTPException(status_code=403, detail="Only an active seller member can preview payment authorization")
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
    actor: ActorContext = Depends(get_current_actor),
    deal_repository: DealRepository = Depends(get_deal_repository),
    db: Session = Depends(get_db),
) -> AuthorizePaymentResponse:
    """Let an authenticated seller queue one payment request after agreement commit."""
    try:
        deal = get_deal(actor, deal_id, deal_repository)
        if deal.seller_organization_id not in actor.organization_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only an active seller member can authorize a payment request",
            )
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
        milestone = db.scalar(
            select(PaymentMilestone)
            .where(PaymentMilestone.agreement_version_id == agreement.version_id)
            .order_by(PaymentMilestone.sequence_number)
            .limit(1)
        )
        if milestone is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The committed agreement has no payment milestone",
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
    actor: ActorContext = Depends(get_current_actor),
    deal_repository: DealRepository = Depends(get_deal_repository),
    payment_repository: PaymentStatusRepository = Depends(get_payment_status_repository),
    db: Session = Depends(get_db),
) -> list[PaymentStatusResponse]:
    """Return current-agreement payment state to either active deal participant."""
    try:
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
        )
        for payment in payments
    ]
