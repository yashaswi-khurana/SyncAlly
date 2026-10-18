"""Verified request identity passed into application use cases."""

from __future__ import annotations

from dataclasses import dataclass

from syncally.domain.shared.identifiers import OrganizationId, UserId


@dataclass(frozen=True)
class ActorContext:
    """The verified user and active organization memberships for one request."""

    user_id: UserId
    organization_ids: frozenset[OrganizationId]

    def can_access_organizations(
        self,
        buyer_organization_id: OrganizationId,
        seller_organization_id: OrganizationId,
    ) -> bool:
        """Return whether the actor belongs to either party of a deal."""
        return bool(
            {buyer_organization_id, seller_organization_id} & self.organization_ids
        )
