"""Authenticated actor and organization authorization rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from syncally.domain.organizations.authorization import Permission
from syncally.domain.organizations.organization import (
    OrganizationCapability,
    OrganizationMemberRole,
)


class DealParticipation(Protocol):
    """The deal fields required to decide whether an actor takes part."""

    id: UUID
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
    system_role: str = "USER"
    permissions_by_organization: dict[UUID, frozenset[str]] = field(default_factory=dict)
    all_deal_organization_ids: frozenset[UUID] = frozenset()
    assigned_deals: frozenset[tuple[UUID, UUID]] = frozenset()
    owned_organization_ids: frozenset[UUID] = frozenset()

    def can_access_deal(self, deal: DealParticipation) -> bool:
        """Return whether the actor belongs to either party of the deal."""
        for organization_id in {deal.buyer_organization_id, deal.seller_organization_id} & self.organization_ids:
            if (
                organization_id in self.owned_organization_ids
                or organization_id in self.all_deal_organization_ids
                or (organization_id, deal.id) in self.assigned_deals
            ):
                return True
        return False

    def can_read_deal(self, deal: DealParticipation) -> bool:
        for organization_id in {deal.buyer_organization_id, deal.seller_organization_id} & self.organization_ids:
            if self.has_deal_authority(deal, organization_id, "deal.read_assigned"):
                return True
        return False

    def has_deal_scope(self, deal: DealParticipation, organization_id: UUID) -> bool:
        if organization_id not in self.organization_ids or organization_id not in {
            deal.buyer_organization_id, deal.seller_organization_id
        }:
            return False
        permissions = self.permissions_by_organization.get(organization_id, frozenset())
        return (
            organization_id in self.owned_organization_ids
            or "deal.read_all" in permissions
            or (organization_id, deal.id) in self.assigned_deals
        )

    def has_deal_authority(self, deal: DealParticipation, organization_id: UUID, permission: Permission | str) -> bool:
        if not self.has_deal_scope(deal, organization_id):
            return False
        permissions = self.permissions_by_organization.get(organization_id, frozenset())
        key = permission.value if isinstance(permission, Permission) else permission
        return (
            organization_id in self.owned_organization_ids
            or key in permissions
            or (key == "deal.read_assigned" and "deal.read_all" in permissions)
        )

    @property
    def is_system_admin(self) -> bool:
        """System administration never implies organization data membership."""
        return self.system_role == "SYSTEM_ADMIN"

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

    def has_permission(self, organization_id: UUID, permission: Permission | str) -> bool:
        if organization_id not in self.organization_ids:
            return False
        if organization_id in self.owned_organization_ids:
            return True
        key = permission.value if isinstance(permission, Permission) else permission
        return key in self.permissions_by_organization.get(organization_id, frozenset())
