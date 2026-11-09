"""Closed organization permission catalog and composable role bundles."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum


class Permission(StrEnum):
    ORG_PROFILE_MANAGE = "org.profile.manage"
    ORG_MEMBERS_MANAGE = "org.members.manage"
    DEAL_CREATE = "deal.create"
    DEAL_READ_ASSIGNED = "deal.read_assigned"
    DEAL_READ_ALL = "deal.read_all"
    DEAL_EDIT_ASSIGNED = "deal.edit_assigned"
    DEAL_ASSIGN = "deal.assign"
    AGREEMENT_APPROVE = "agreement.approve"
    PAYMENTS_READ = "payments.read"
    PAYMENTS_AUTHORIZE = "payments.authorize"
    FULFILLMENT_READ = "fulfillment.read"
    FULFILLMENT_RECORD = "fulfillment.record"
    MARKETPLACE_MANAGE = "marketplace.manage"
    APPROVAL_ROUTING_MANAGE = "approval_routing.manage"


ALL_PERMISSIONS = frozenset(item.value for item in Permission)
HIGH_IMPACT_PERMISSIONS = frozenset({
    Permission.ORG_MEMBERS_MANAGE.value,
    Permission.DEAL_READ_ALL.value,
})

BUNDLES: dict[str, frozenset[str]] = {
    "ORG_ADMIN": frozenset({
        Permission.ORG_PROFILE_MANAGE.value,
        Permission.ORG_MEMBERS_MANAGE.value,
        Permission.DEAL_ASSIGN.value,
    }),
    "DEAL_MANAGER": frozenset({
        Permission.DEAL_CREATE.value,
        Permission.DEAL_ASSIGN.value,
        Permission.DEAL_READ_ASSIGNED.value,
        Permission.DEAL_EDIT_ASSIGNED.value,
    }),
    "DEAL_MEMBER": frozenset({
        Permission.DEAL_READ_ASSIGNED.value,
        Permission.DEAL_EDIT_ASSIGNED.value,
    }),
    "APPROVER": frozenset({
        Permission.DEAL_READ_ASSIGNED.value,
        Permission.AGREEMENT_APPROVE.value,
    }),
    "FINANCE": frozenset({
        Permission.DEAL_READ_ASSIGNED.value,
        Permission.PAYMENTS_READ.value,
        Permission.PAYMENTS_AUTHORIZE.value,
    }),
    "FULFILLMENT": frozenset({
        Permission.DEAL_READ_ASSIGNED.value,
        Permission.FULFILLMENT_READ.value,
        Permission.FULFILLMENT_RECORD.value,
    }),
}

OWNER_BUNDLE = "ORG_OWNER"
OWNER_ONLY_BUNDLES = frozenset({"ORG_ADMIN"})
OWNER_ONLY_PERMISSIONS = frozenset({
    Permission.ORG_MEMBERS_MANAGE.value,
    Permission.DEAL_READ_ALL.value,
})


def expand_grants(bundles: Iterable[str] | None, permissions: Iterable[str] | None, *, owner: bool = False) -> frozenset[str]:
    """Return known permission keys from persisted bundle and custom grants."""
    if owner:
        return ALL_PERMISSIONS
    effective: set[str] = set()
    for bundle in bundles or ():
        if bundle == OWNER_BUNDLE:
            return ALL_PERMISSIONS
        effective.update(BUNDLES.get(bundle, ()))
    effective.update(item for item in permissions or () if item in ALL_PERMISSIONS)
    return frozenset(effective)


def validate_grants(bundles: Iterable[str], permissions: Iterable[str]) -> tuple[set[str], set[str]]:
    """Normalize a requested grant set, rejecting unknown or protected entries."""
    normalized_bundles = set(bundles)
    normalized_permissions = set(permissions)
    unknown_bundles = normalized_bundles - set(BUNDLES)
    unknown_permissions = normalized_permissions - ALL_PERMISSIONS
    if (
        OWNER_BUNDLE in normalized_bundles
        or Permission.ORG_MEMBERS_MANAGE.value in normalized_permissions
        or unknown_bundles
        or unknown_permissions
    ):
        raise ValueError("Unknown or protected role/permission grant")
    return normalized_bundles, normalized_permissions
