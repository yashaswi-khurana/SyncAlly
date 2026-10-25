"""Read the latest persisted payment state for a deal."""

from datetime import datetime
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
    PaymentStatusRepository,
    UnauthorizedPaymentAuthorization,
    list_current_payment_statuses,
)
from syncally.domain.agreements.agreement import AgreementStatus
from syncally.domain.shared.money import Money, canonical_decimal
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import PaymentIntent, PaymentMilestone
from syncally.infrastructure.repositories.agreements import SqlAlchemyAgreementRepository
from syncally.infrastructure.repositories.payments import (
    SqlAlchemyPaymentIntentRepository,
    authorize_payment_intent_in_transaction,
)

router = APIRouter(prefix="/deals/{deal_id}/payments", tags=["payments"])


class PaymentStatusResponse(BaseModel):
    """Safe payment summary including invoice link and retry diagnostics."""

    id: UUID
    milestone_sequence: int
    amount: str
    currency: str
    status: str
    reconciled_amount: str | None
    last_checked_at: datetime | None
    last_reconciled_at: datetime | None
    invoice_url: str | None = None
    recipient_email: str | None = None
    recipient_name: str | None = None
    retry_count: int = 0
    next_retry_at: datetime | None = None
    failure_reason: str | None = None


class AuthorizePaymentRequest(BaseModel):
    """Authorize one invoice for the current committed agreement."""

    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(min_length=1, max_length=256)


class AuthorizePaymentResponse(BaseModel):
    id: UUID
    status: str
    already_existed: bool


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
            ),
        )
        intent = db.get(PaymentIntent, outcome.intent_id)
        if intent is None:
            raise RuntimeError("Authorized payment intent was not persisted")
        return AuthorizePaymentResponse(
            id=intent.id,
            status=intent.status,
            already_existed=outcome.already_existed,
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
    except (DuplicateActivePaymentIntent, IdempotencyKeyReused) as error:
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
            reconciled_amount=(
                canonical_decimal(payment.reconciled_amount.amount)
                if payment.reconciled_amount is not None
                else None
            ),
            last_checked_at=payment.last_checked_at,
            last_reconciled_at=payment.last_reconciled_at,
            invoice_url=getattr(payment, "invoice_url", None),
            recipient_email=getattr(payment, "recipient_email", None),
            recipient_name=getattr(payment, "recipient_name", None),
            retry_count=getattr(payment, "retry_count", 0),
            next_retry_at=getattr(payment, "next_retry_at", None),
            failure_reason=getattr(payment, "failure_reason", None),
        )
        for payment in payments
    ]
