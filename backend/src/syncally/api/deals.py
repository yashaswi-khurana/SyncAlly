"""Deal HTTP endpoints.

Routes validate request schemas, derive the actor from authentication, call the
application use cases, and translate their outcomes into a stable error contract.
No deal policy or persistence happens here.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
from syncally.application.deals import (
    CreateDealCommand,
    DealAccessDenied,
    DealNotFound,
    DealRepository,
    create_deal,
    get_deal,
)
from syncally.application.identity import ActorContext
from syncally.domain.deals.deal import Deal
from syncally.domain.shared.errors import InvariantViolation
from syncally.infrastructure.database import get_db
from syncally.infrastructure.repositories import SqlAlchemyDealRepository

router = APIRouter(prefix="/deals", tags=["deals"])


class CreateDealRequest(BaseModel):
    """Fields required to start a draft deal between a buyer and a seller."""

    buyer_organization_id: UUID
    seller_organization_id: UUID


class DealResponse(BaseModel):
    """Public representation of a deal; never a serialized ORM entity."""

    id: UUID
    buyer_organization_id: UUID
    seller_organization_id: UUID
    status: str
    version: int


def get_deal_repository(db: Session = Depends(get_db)) -> DealRepository:
    """Provide the deal persistence port for the current request."""
    return SqlAlchemyDealRepository(db)


def _to_response(deal: Deal) -> DealResponse:
    return DealResponse(
        id=deal.id,
        buyer_organization_id=deal.buyer_organization_id,
        seller_organization_id=deal.seller_organization_id,
        status=deal.status.value,
        version=deal.version,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DealResponse)
def create_deal_route(
    payload: CreateDealRequest,
    actor: ActorContext = Depends(get_current_actor),
    repository: DealRepository = Depends(get_deal_repository),
) -> DealResponse:
    """Create a draft deal for the buyer organization the actor belongs to."""
    try:
        deal = create_deal(
            actor,
            CreateDealCommand(
                buyer_organization_id=payload.buyer_organization_id,
                seller_organization_id=payload.seller_organization_id,
            ),
            repository,
        )
    except DealAccessDenied as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DealNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvariantViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_response(deal)


@router.get("/{deal_id}", response_model=DealResponse)
def read_deal_route(
    deal_id: UUID,
    actor: ActorContext = Depends(get_current_actor),
    repository: DealRepository = Depends(get_deal_repository),
) -> DealResponse:
    """Return a deal to an active member of either party."""
    try:
        deal = get_deal(actor, deal_id, repository)
    except DealNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_response(deal)
