"""Participant reads and capability-checked fulfillment fact commands."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
from syncally.api.deals import get_deal_repository
from syncally.application.deals import DealNotFound, get_deal
from syncally.application.fulfillment import (
    FulfillmentAccessDenied,
    FulfillmentConflict,
    FulfillmentEventRecord,
    FulfillmentRepository,
    FulfillmentSnapshot,
    FulfillmentUnavailable,
    RecordFulfillmentCommand,
    get_fulfillment_snapshot,
    record_fulfillment_event,
)
from syncally.application.identity import ActorContext
from syncally.domain.agreements.fulfillment import FulfillmentStage, bounded_quantity
from syncally.domain.deals.deal import Deal
from syncally.domain.organizations.organization import OrganizationCapability
from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.money import canonical_decimal
from syncally.infrastructure.database import get_db
from syncally.infrastructure.identity import verify_member_capability
from syncally.infrastructure.repositories.fulfillment import SqlAlchemyFulfillmentRepository

router = APIRouter(prefix="/deals/{deal_id}/fulfillment", tags=["fulfillment"])


class RecordFulfillmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agreement_version_id: UUID
    terms_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    obligation_id: UUID
    organization_id: UUID
    event_type: FulfillmentStage
    quantity: Decimal
    carrier: str | None = Field(default=None, max_length=120)
    tracking_number: str | None = Field(default=None, max_length=128)
    dispatch_date: date | None = None
    expected_delivery_date: date | None = None
    expected_version: int = Field(ge=0, strict=True)
    idempotency_key: str = Field(min_length=1, max_length=128, pattern=r"\S")

    @field_validator("quantity", mode="before")
    @classmethod
    def parse_exact_decimal(cls, value: object) -> Decimal:
        if not isinstance(value, str):
            raise ValueError("Quantity must be sent as an exact decimal string")
        try:
            quantity = Decimal(value)
        except InvalidOperation as error:
            raise ValueError("Quantity must be a valid decimal") from error
        try:
            return bounded_quantity(quantity)
        except InvariantViolation as error:
            raise ValueError(str(error)) from error

    @field_validator("carrier", "tracking_number", mode="before")
    @classmethod
    def normalize_shipping_text(cls, value: object) -> object:
        return value.strip() or None if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_shipping_details(self) -> RecordFulfillmentRequest:
        has_shipping_details = any((self.carrier, self.tracking_number, self.dispatch_date, self.expected_delivery_date))
        if self.event_type is FulfillmentStage.SHIPPED:
            if not self.carrier:
                raise ValueError("A carrier is required when reporting a shipment")
            if self.dispatch_date is None:
                raise ValueError("A dispatch date is required when reporting a shipment")
            if self.expected_delivery_date and self.expected_delivery_date < self.dispatch_date:
                raise ValueError("Expected delivery date cannot be before dispatch date")
        elif has_shipping_details:
            raise ValueError("Shipping details can only be added to a shipped event")
        return self


class FulfillmentEventResponse(BaseModel):
    id: UUID
    deal_id: UUID
    agreement_version_id: UUID
    terms_hash: str
    obligation_id: UUID
    organization_id: UUID
    user_id: UUID
    event_type: FulfillmentStage
    quantity: str
    unit: str
    carrier: str | None
    tracking_number: str | None
    dispatch_date: date | None
    expected_delivery_date: date | None
    source_type: str
    recorded_at: str
    version: int


class FulfillmentSnapshotResponse(BaseModel):
    deal_id: UUID
    state: str
    agreement_version_id: UUID | None
    agreement_version_number: int | None
    terms_hash: str | None
    obligation_id: UUID | None
    planned_quantity: str | None
    unit: str | None
    destination: str | None
    target_date: str | None
    shipped_quantity: str
    observed_quantity: str
    confirmed_quantity: str
    fulfillment_version: int
    payment_complete: bool
    deal_completed: bool
    events: list[FulfillmentEventResponse]


def get_fulfillment_repository(db: Session = Depends(get_db)) -> FulfillmentRepository:
    return SqlAlchemyFulfillmentRepository(db)


def _event_response(event: FulfillmentEventRecord) -> FulfillmentEventResponse:
    return FulfillmentEventResponse(
        id=event.id,
        deal_id=event.deal_id,
        agreement_version_id=event.agreement_version_id,
        terms_hash=event.terms_hash,
        obligation_id=event.obligation_id,
        organization_id=event.organization_id,
        user_id=event.user_id,
        event_type=event.stage,
        quantity=canonical_decimal(event.quantity),
        unit=event.unit,
        carrier=event.carrier,
        tracking_number=event.tracking_number,
        dispatch_date=event.dispatch_date,
        expected_delivery_date=event.expected_delivery_date,
        source_type=event.source_type,
        recorded_at=event.recorded_at.isoformat(),
        version=event.version,
    )


def _snapshot_response(snapshot: FulfillmentSnapshot) -> FulfillmentSnapshotResponse:
    return FulfillmentSnapshotResponse(
        deal_id=snapshot.deal_id,
        state=snapshot.state,
        agreement_version_id=snapshot.agreement_version_id,
        agreement_version_number=snapshot.agreement_version_number,
        terms_hash=snapshot.terms_hash,
        obligation_id=snapshot.obligation_id,
        planned_quantity=(canonical_decimal(snapshot.planned_quantity) if snapshot.planned_quantity is not None else None),
        unit=snapshot.unit,
        destination=snapshot.destination,
        target_date=snapshot.target_date,
        shipped_quantity=canonical_decimal(snapshot.shipped_quantity),
        observed_quantity=canonical_decimal(snapshot.observed_quantity),
        confirmed_quantity=canonical_decimal(snapshot.confirmed_quantity),
        fulfillment_version=snapshot.fulfillment_version,
        payment_complete=snapshot.payment_complete,
        deal_completed=snapshot.deal_completed,
        events=[_event_response(event) for event in snapshot.events],
    )


def _raise_fulfillment_error(error: Exception) -> NoReturn:
    if isinstance(error, DealNotFound):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found") from error
    if isinstance(error, FulfillmentAccessDenied):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    if isinstance(error, (FulfillmentConflict, FulfillmentUnavailable)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if isinstance(error, InvariantViolation):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    raise error


@router.get("", response_model=FulfillmentSnapshotResponse)
def read_fulfillment_route(
    deal_id: UUID,
    actor: ActorContext = Depends(get_current_actor),
    deal_repository=Depends(get_deal_repository),
    fulfillment_repository: FulfillmentRepository = Depends(get_fulfillment_repository),
) -> FulfillmentSnapshotResponse:
    try:
        return _snapshot_response(
            get_fulfillment_snapshot(actor, deal_id, deal_repository, fulfillment_repository)
        )
    except Exception as error:
        _raise_fulfillment_error(error)


@router.post("/events", status_code=status.HTTP_201_CREATED, response_model=FulfillmentEventResponse)
def record_fulfillment_route(
    deal_id: UUID,
    payload: RecordFulfillmentRequest,
    actor: ActorContext = Depends(get_current_actor),
    deal_repository=Depends(get_deal_repository),
    fulfillment_repository: FulfillmentRepository = Depends(get_fulfillment_repository),
    db: Session = Depends(get_db),
) -> FulfillmentEventResponse:
    try:
        deal: Deal = get_deal(actor, deal_id, deal_repository)
        if payload.organization_id not in actor.organization_ids or payload.organization_id not in (
            deal.buyer_organization_id,
            deal.seller_organization_id,
        ):
            raise FulfillmentAccessDenied("Select an active organization that belongs to this deal")
        verify_member_capability(
            db,
            payload.organization_id,
            actor.user_id,
            OrganizationCapability.FULFILLMENT,
            for_update=True,
        )
        event = record_fulfillment_event(
            actor,
            deal,
            RecordFulfillmentCommand(
                agreement_version_id=payload.agreement_version_id,
                terms_hash=payload.terms_hash,
                obligation_id=payload.obligation_id,
                organization_id=payload.organization_id,
                stage=payload.event_type,
                quantity=payload.quantity,
                carrier=payload.carrier,
                tracking_number=payload.tracking_number,
                dispatch_date=payload.dispatch_date,
                expected_delivery_date=payload.expected_delivery_date,
                expected_version=payload.expected_version,
                idempotency_key=payload.idempotency_key,
            ),
            fulfillment_repository,
        )
        return _event_response(event)
    except Exception as error:
        _raise_fulfillment_error(error)
