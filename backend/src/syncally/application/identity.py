"""Authenticated actor and organization authorization rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


class DealParticipation(Protocol):
    """The deal fields required to decide whether an actor takes part."""

    buyer_organization_id: UUID
    seller_organization_id: UUID


@dataclass(frozen=True)
class ActorContext:
    """The verified user and active organization memberships for one request."""

    user_id: UUID
    organization_ids: frozenset[UUID]

    def can_access_deal(self, deal: DealParticipation) -> bool:
        """Return whether the actor belongs to either party of the deal."""
        return bool(
            {deal.buyer_organization_id, deal.seller_organization_id}
            & self.organization_ids
        )
