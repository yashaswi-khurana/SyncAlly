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
from syncally.domain.deals.deal import Deal
from syncally.domain.shared.errors import DomainError
from syncally.domain.shared.identifiers import DealId, OrganizationId


class DealRepository(Protocol):
    """Persistence port for the deal aggregate."""

    def active_organization_exists(self, organization_id: UUID) -> bool:
        """Return whether an active organization exists for the identifier."""

    def add(self, deal: Deal) -> Deal:
        """Persist a newly created deal and return the stored representation."""

    def get_for_participant(self, deal_id: UUID, user_id: UUID) -> Deal | None:
        """Load a deal only when the user has an active membership in either party."""


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


def create_deal(
    actor: ActorContext,
    command: CreateDealCommand,
    repository: DealRepository,
    now: datetime | None = None,
) -> Deal:
    """Create a draft deal for an actor acting on behalf of the buyer organization."""
    if command.buyer_organization_id not in actor.organization_ids:
        raise DealAccessDenied("Actor cannot create a deal for this buyer organization")
    if not _both_organizations_active(repository, command):
        raise DealNotFound("Buyer or seller organization is not available")

    deal = Deal(
        id=DealId(uuid4()),
        buyer_organization_id=OrganizationId(command.buyer_organization_id),
        seller_organization_id=OrganizationId(command.seller_organization_id),
        created_at=now or datetime.now(UTC),
    )
    return repository.add(deal)


def get_deal(actor: ActorContext, deal_id: UUID, repository: DealRepository) -> Deal:
    """Load a deal the actor participates in, hiding missing and forbidden deals alike."""
    deal = repository.get_for_participant(deal_id, actor.user_id)
    if deal is None or not actor.can_access_deal(deal):
        raise DealNotFound("Deal not found")
    return deal


def _both_organizations_active(repository: DealRepository, command: CreateDealCommand) -> bool:
    buyer_exists = repository.active_organization_exists(command.buyer_organization_id)
    seller_exists = repository.active_organization_exists(command.seller_organization_id)
    return buyer_exists and seller_exists
