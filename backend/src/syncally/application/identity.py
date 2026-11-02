"""Authenticated actor and organization authorization rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from syncally.domain.organizations.organization import (
    OrganizationCapability,
    OrganizationMemberRole,
)


class DealParticipation(Protocol):
    """The deal fields required to decide whether an actor takes part."""

    buyer_organization_id: UUID
    seller_organization_id: UUID


@dataclass(frozen=True)
class ActorContext:
    """The verified user and active organization memberships for one request."""

    user_id: UUID
    organization_ids: frozenset[UUID]
    roles_by_organization: dict[UUID, OrganizationMemberRole] = field(default_factory=dict)
    capabilities_by_organization: dict[UUID, frozenset[OrganizationCapability]] = field(
        default_factory=dict
    )

    def can_access_deal(self, deal: DealParticipation) -> bool:
        """Return whether the actor belongs to either party of the deal."""
        return bool(
            {deal.buyer_organization_id, deal.seller_organization_id}
            & self.organization_ids
        )

    def has_capability(
        self, organization_id: UUID, capability: OrganizationCapability | str
    ) -> bool:
        """Return whether the actor has the specified effective capability in the organization."""
        if organization_id not in self.organization_ids:
            return False
        if isinstance(capability, str):
            try:
                cap = OrganizationCapability(capability)
            except ValueError:
                return False
        else:
            cap = capability
        effective = self.capabilities_by_organization.get(organization_id, frozenset())
        return cap in effective
