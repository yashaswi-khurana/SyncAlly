"""Deal create and retrieval use cases.

This module owns deal orchestration: it uses the verified ``ActorContext`` for
authorization and a ``DealRepository`` port for persistence. It must stay free of
HTTP parsing, request/response schemas, and SQLAlchemy so the rules can be tested
without FastAPI or a database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from syncally.application.identity import ActorContext
from syncally.application.seller_suggestions import (
    SellerSuggestionItem,
    SellerSuggestionService,
)
from syncally.domain.deals.deal import Deal
from syncally.domain.shared.errors import DomainError
from syncally.domain.shared.identifiers import DealId, OrganizationId

__all__ = [
    "CreateDealCommand",
    "DealAccessDenied",
    "DealNotFound",
    "DealRepository",
    "SellerSuggestionItem",
    "SellerSuggestionService",
    "create_deal",
    "get_deal",
    "list_deals",
]


class DealRepository(Protocol):
    """Persistence port for the deal aggregate."""

    def active_organization_exists(self, organization_id: UUID) -> bool:
        """Return whether an active organization exists for the identifier."""

    def add(self, deal: Deal) -> Deal:
        """Persist a newly created deal and return the stored representation."""

    def get_for_participant(self, deal_id: UUID, user_id: UUID) -> Deal | None:
        """Load a deal only when the user has an active membership in either party."""

    def list_for_participant(self, user_id: UUID) -> list[Deal]:
        """List every deal where the user has an active membership in either party."""


class DealNotFound(DomainError):
    """The deal or an organization it references does not exist for this actor.

    The same error covers a missing deal and a deal the actor may not see so callers
    cannot tell the two cases apart.
    """


class DealAccessDenied(DomainError):
    """The actor may not act on behalf of the requested organization."""


@dataclass(frozen=True)
class CreateDealCommand:
    """Input for creating a draft deal between two organizations."""

    buyer_organization_id: UUID
    seller_organization_id: UUID
    initiator_party: str = "BUYER"
    display_name: str | None = None
    opening_request: str | None = None


def create_deal(
    actor: ActorContext,
    command: CreateDealCommand,
    repository: DealRepository,
    now: datetime | None = None,
) -> Deal:
    """Create a draft deal for an actor acting on behalf of its selected party."""
    if command.initiator_party not in {"BUYER", "SELLER"}:
        raise DealAccessDenied("Invalid initiating party")
    initiator = command.buyer_organization_id if command.initiator_party == "BUYER" else command.seller_organization_id
    if initiator not in actor.organization_ids or not actor.has_permission(initiator, "deal.create"):
        raise DealAccessDenied("Actor cannot create a deal for this organization")
    if not _both_organizations_active(repository, command):
        raise DealNotFound("Buyer or seller organization is not available")

    deal = Deal(
        id=DealId(uuid4()),
        buyer_organization_id=OrganizationId(command.buyer_organization_id),
        seller_organization_id=OrganizationId(command.seller_organization_id),
        created_at=now or datetime.now(UTC),
        display_name=command.display_name,
    )
    return repository.add(deal)


def get_deal(actor: ActorContext, deal_id: UUID, repository: DealRepository) -> Deal:
    """Load a deal the actor participates in, hiding missing and forbidden deals alike."""
    deal = repository.get_for_participant(deal_id, actor.user_id)
    if deal is None or not actor.can_read_deal(deal):
        raise DealNotFound("Deal not found")
    return deal


def list_deals(
    actor: ActorContext,
    repository: DealRepository,
    organization_id: UUID | None = None,
) -> list[Deal]:
    """List deals visible through one party, or all party scopes when omitted."""
    deals = repository.list_for_participant(actor.user_id)
    if organization_id is not None:
        if organization_id not in actor.organization_ids:
            return []
        return [
            deal for deal in deals
            if organization_id in {deal.buyer_organization_id, deal.seller_organization_id}
            and actor.has_deal_authority(deal, organization_id, "deal.read_assigned")
        ]
    return [deal for deal in deals if actor.can_read_deal(deal)]


def _both_organizations_active(repository: DealRepository, command: CreateDealCommand) -> bool:
    buyer_exists = repository.active_organization_exists(command.buyer_organization_id)
    seller_exists = repository.active_organization_exists(command.seller_organization_id)
    return buyer_exists and seller_exists
