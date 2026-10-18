"""Application use cases for creating and retrieving deals."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from syncally.application.identity import ActorContext
from syncally.domain.deals.deal import Deal
from syncally.domain.shared.identifiers import DealId, OrganizationId


class DealRepository(Protocol):
    """Persistence operations required by the deal use cases."""

    def add(self, deal: Deal) -> Deal:
        """Persist a new deal and return its stored domain representation."""

    def get_by_id(self, deal_id: DealId) -> Deal | None:
        """Return a deal by ID, or ``None`` when it does not exist."""


class DealNotFoundError(LookupError):
    """Raised when a deal is missing or unavailable to the current actor."""


class DealParticipationRequired(PermissionError):
    """Raised when the actor belongs to neither organization in a new deal."""


def create_deal(
    actor: ActorContext,
    buyer_organization_id: OrganizationId,
    seller_organization_id: OrganizationId,
    repository: DealRepository,
) -> Deal:
    """Create a draft deal when the actor belongs to one of its organizations."""
    deal = Deal(
        id=DealId(uuid4()),
        buyer_organization_id=buyer_organization_id,
        seller_organization_id=seller_organization_id,
        created_at=datetime.now(UTC),
    )
    if not actor.can_access_organizations(
        deal.buyer_organization_id, deal.seller_organization_id
    ):
        raise DealParticipationRequired(
            "Actor must belong to the buyer or seller organization"
        )
    return repository.add(deal)


def get_deal(
    actor: ActorContext,
    deal_id: DealId,
    repository: DealRepository,
) -> Deal:
    """Return a deal only when the actor belongs to one of its organizations."""
    deal = repository.get_by_id(deal_id)
    if deal is None or not actor.can_access_organizations(
        deal.buyer_organization_id, deal.seller_organization_id
    ):
        raise DealNotFoundError("Deal not found")
    return deal
