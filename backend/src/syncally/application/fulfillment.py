"""Typed commands and read models for version-bound delivery facts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from syncally.application.deals import DealNotFound, DealRepository, get_deal
from syncally.application.identity import ActorContext
from syncally.domain.agreements.fulfillment import FulfillmentStage, bounded_quantity
from syncally.domain.deals.deal import Deal
from syncally.domain.shared.errors import DomainError, InvariantViolation


class FulfillmentConflict(DomainError):
    """The version, idempotency key, or delivery stage changed concurrently."""


class FulfillmentAccessDenied(DomainError):
    """The actor cannot record this kind of delivery fact for the selected party."""


class FulfillmentUnavailable(DomainError):
    """The requested delivery obligation is missing, stale, or no longer current."""


@dataclass(frozen=True, slots=True)
class RecordFulfillmentCommand:
    agreement_version_id: UUID
    terms_hash: str
    obligation_id: UUID
    organization_id: UUID
    stage: FulfillmentStage
    quantity: Decimal
    expected_version: int
    idempotency_key: str

    def __post_init__(self) -> None:
        if not isinstance(self.stage, FulfillmentStage):
            raise InvariantViolation("Unsupported fulfillment stage")
        bounded_quantity(self.quantity)
        if type(self.expected_version) is not int or self.expected_version < 0:
            raise InvariantViolation("Expected fulfillment version must be nonnegative")
        if not self.idempotency_key.strip() or len(self.idempotency_key) > 128:
            raise InvariantViolation("A bounded fulfillment idempotency key is required")
        if len(self.terms_hash) != 64 or any(c not in "0123456789abcdef" for c in self.terms_hash):
            raise InvariantViolation("A canonical agreement terms hash is required")


@dataclass(frozen=True, slots=True)
class FulfillmentEventRecord:
    id: UUID
    deal_id: UUID
    agreement_version_id: UUID
    terms_hash: str
    obligation_id: UUID
    organization_id: UUID
    user_id: UUID
    stage: FulfillmentStage
    quantity: Decimal
    unit: str
    source_type: str
    recorded_at: datetime
    version: int


@dataclass(frozen=True, slots=True)
class FulfillmentSnapshot:
    deal_id: UUID
    state: str
    agreement_version_id: UUID | None
    agreement_version_number: int | None
    terms_hash: str | None
    obligation_id: UUID | None
    planned_quantity: Decimal | None
    unit: str | None
    destination: str | None
    target_date: str | None
    shipped_quantity: Decimal
    observed_quantity: Decimal
    confirmed_quantity: Decimal
    fulfillment_version: int
    payment_complete: bool
    deal_completed: bool
    events: tuple[FulfillmentEventRecord, ...]


class FulfillmentRepository(Protocol):
    def get_snapshot(self, deal_id: UUID) -> FulfillmentSnapshot:
        """Return current fulfillment state for a deal participant."""

    def append_event(
        self,
        *,
        deal: Deal,
        actor: ActorContext,
        command: RecordFulfillmentCommand,
    ) -> FulfillmentEventRecord:
        """Append one fact and its audit/outbox records atomically."""


def get_fulfillment_snapshot(
    actor: ActorContext,
    deal_id: UUID,
    deal_repository: DealRepository,
    fulfillment_repository: FulfillmentRepository,
) -> FulfillmentSnapshot:
    deal = get_deal(actor, deal_id, deal_repository)
    return fulfillment_repository.get_snapshot(deal.id)


def record_fulfillment_event(
    actor: ActorContext,
    deal: Deal,
    command: RecordFulfillmentCommand,
    fulfillment_repository: FulfillmentRepository,
) -> FulfillmentEventRecord:
    if not actor.can_access_deal(deal):
        raise DealNotFound("Deal not found")
    if command.organization_id not in actor.organization_ids:
        raise FulfillmentAccessDenied("Select an active organization membership")
    if command.organization_id not in (deal.buyer_organization_id, deal.seller_organization_id):
        raise FulfillmentAccessDenied("Selected organization is not a party to this deal")
    if command.stage is FulfillmentStage.SHIPPED:
        allowed_organization = deal.seller_organization_id
    else:
        allowed_organization = deal.buyer_organization_id
    if command.organization_id != allowed_organization:
        raise FulfillmentAccessDenied("This fulfillment fact must be recorded by the responsible deal party")
    return fulfillment_repository.append_event(
        deal=deal,
        actor=actor,
        command=command,
    )
