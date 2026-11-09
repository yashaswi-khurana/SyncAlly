"""Persistence-backed resolution of verified actor context."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from syncally.application.identity import ActorContext
from syncally.domain.organizations.authorization import expand_grants
from syncally.domain.organizations.organization import (
    OrganizationCapability,
    OrganizationMemberRole,
    resolve_effective_capabilities,
)
from syncally.infrastructure.models import DealAssignment, Organization, OrganizationMember, User


def resolve_actor(db: Session, user_id: UUID) -> ActorContext | None:
    """Resolve an active user and their active memberships from persistence."""
    user = db.scalar(select(User).where(User.id == user_id, User.status == "ACTIVE"))
    if user is None:
        return None

    memberships = db.execute(
        select(
            OrganizationMember.organization_id,
            OrganizationMember.role,
            OrganizationMember.capabilities,
            OrganizationMember.role_bundles,
            OrganizationMember.permissions,
            OrganizationMember.is_owner,
        )
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.status == "ACTIVE",
            Organization.status == "ACTIVE",
        )
    ).all()

    roles_by_organization: dict[UUID, OrganizationMemberRole] = {}
    capabilities_by_organization: dict[UUID, frozenset[OrganizationCapability]] = {}
    permissions_by_organization: dict[UUID, frozenset[str]] = {}
    all_deal_organization_ids: set[UUID] = set()
    owned_organization_ids: set[UUID] = set()

    for org_id, role_str, caps_raw, bundles_raw, permissions_raw, is_owner in memberships:
        try:
            role = OrganizationMemberRole(role_str)
            roles_by_organization[org_id] = role
        except ValueError:
            pass

        capabilities_by_organization[org_id] = resolve_effective_capabilities(
            role_str, caps_raw
        )
        permissions = expand_grants(bundles_raw, permissions_raw, owner=bool(is_owner))
        permissions_by_organization[org_id] = permissions
        if bool(is_owner):
            owned_organization_ids.add(org_id)
        if "deal.read_all" in permissions:
            all_deal_organization_ids.add(org_id)

    active_assignments = db.execute(
        select(DealAssignment.organization_id, DealAssignment.deal_id)
        .join(OrganizationMember, (OrganizationMember.organization_id == DealAssignment.organization_id) & (OrganizationMember.user_id == DealAssignment.user_id))
        .where(
            DealAssignment.user_id == user_id,
            DealAssignment.status == "ACTIVE",
            OrganizationMember.status == "ACTIVE",
        )
    ).all()

    return ActorContext(
        user_id=user_id,
        organization_ids=frozenset(roles_by_organization.keys()),
        system_role=user.system_role,
        roles_by_organization=roles_by_organization,
        capabilities_by_organization=capabilities_by_organization,
        permissions_by_organization=permissions_by_organization,
        all_deal_organization_ids=frozenset(all_deal_organization_ids),
        assigned_deals=frozenset((org_id, deal_id) for org_id, deal_id in active_assignments),
        owned_organization_ids=frozenset(owned_organization_ids),
    )


def verify_member_capability(
    db: Session,
    organization_id: UUID,
    user_id: UUID,
    required_capability: OrganizationCapability,
    for_update: bool = True,
) -> OrganizationMember:
    """Perform a fresh, transactional capability check with row locking against persistence."""
    stmt = (
        select(OrganizationMember)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .join(User, User.id == OrganizationMember.user_id)
        .where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.status == "ACTIVE",
            Organization.status == "ACTIVE",
            User.status == "ACTIVE",
        )
    )
    if for_update:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)

    member = db.scalar(stmt)
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active organization membership required",
        )

    permission_by_legacy = {
        OrganizationCapability.ADMINISTRATION: "org.members.manage",
        OrganizationCapability.DRAFTING: "deal.edit_assigned",
        OrganizationCapability.AGREEMENT_APPROVAL: "agreement.approve",
        OrganizationCapability.FINANCE: "payments.authorize",
        OrganizationCapability.FULFILLMENT: "fulfillment.record",
    }
    permission = permission_by_legacy[required_capability]
    grants = set(expand_grants(member.role_bundles, member.permissions, owner=member.is_owner))
    # Compatibility for explicitly persisted old capabilities only. Role names no longer imply grants.
    for legacy in member.capabilities or []:
        try:
            grants.add(permission_by_legacy[OrganizationCapability(legacy)])
        except (ValueError, KeyError):
            continue
    if permission not in grants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Organization permission '{permission}' required",
        )

    return member


def repair_organization_finance_membership(
    db: Session,
    organization_id: UUID,
    user_id: UUID,
) -> bool:
    """Repair finance authority for an active administrator when an organization has no finance members.

    Preserves the self-modification restriction on general member editing and avoids blanket admin
    grants by only provisioning FINANCE if the organization currently has zero members with FINANCE capability.
    """
    from datetime import UTC, datetime
    from uuid import uuid4

    from syncally.infrastructure.models import AuditEvent

    members = db.scalars(
        select(OrganizationMember)
        .where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.status == "ACTIVE",
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    ).all()

    # Check if ANY active member already has FINANCE capability
    has_any_finance = any(
        OrganizationCapability.FINANCE in resolve_effective_capabilities(m.role, m.capabilities)
        for m in members
    )
    if has_any_finance:
        return False

    # Find the target administrator
    admin_member = next(
        (m for m in members if m.user_id == user_id and m.role == OrganizationMemberRole.ADMIN.value),
        None,
    )
    if admin_member is None:
        return False

    current_caps = list(admin_member.capabilities or [])
    if OrganizationCapability.FINANCE.value not in current_caps:
        current_caps.append(OrganizationCapability.FINANCE.value)
    admin_member.capabilities = current_caps
    admin_member.version = admin_member.version + 1

    db.add(
        AuditEvent(
            id=uuid4(),
            aggregate_type="organization_member",
            aggregate_id=admin_member.id,
            event_type="member.finance_repaired",
            actor_type="USER",
            actor_id=str(user_id),
            occurred_at=datetime.now(UTC),
            payload={
                "organization_id": str(organization_id),
                "reason": "initial_finance_authority_repair",
            },
        )
    )
    db.flush()
    return True
