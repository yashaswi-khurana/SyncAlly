"""Read the latest persisted payment state for a deal."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
from syncally.api.deals import get_deal_repository
from syncally.application.deals import DealNotFound, DealRepository
from syncally.application.identity import ActorContext
from syncally.application.payments import (
    PaymentStatusRepository,
    list_current_payment_statuses,
)
from syncally.domain.shared.money import canonical_decimal
from syncally.infrastructure.database import get_db
from syncally.infrastructure.repositories.agreements import SqlAlchemyAgreementRepository
from syncally.infrastructure.repositories.payments import SqlAlchemyPaymentIntentRepository

router = APIRouter(prefix="/deals/{deal_id}/payments", tags=["payments"])


class PaymentStatusResponse(BaseModel):
    """Safe payment summary; provider invoice IDs and links are intentionally omitted."""

    id: UUID
    milestone_sequence: int
    amount: str
    currency: str
    status: str
    reconciled_amount: str | None
    last_checked_at: datetime | None
    last_reconciled_at: datetime | None


def get_payment_status_repository(db: Session = Depends(get_db)) -> PaymentStatusRepository:
    """Provide the persisted payment status read port for this request."""
    return SqlAlchemyPaymentIntentRepository(db)


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
        )
        for payment in payments
    ]
