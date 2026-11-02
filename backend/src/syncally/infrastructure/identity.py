"""Persistence-backed resolution of verified actor context."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from syncally.application.identity import ActorContext
from syncally.domain.organizations.organization import (
    OrganizationCapability,
    OrganizationMemberRole,
    resolve_effective_capabilities,
)
from syncally.infrastructure.models import Organization, OrganizationMember, User


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

    for org_id, role_str, caps_raw in memberships:
        try:
            role = OrganizationMemberRole(role_str)
            roles_by_organization[org_id] = role
        except ValueError:
            pass

        capabilities_by_organization[org_id] = resolve_effective_capabilities(
            role_str, caps_raw
        )

    return ActorContext(
        user_id=user_id,
        organization_ids=frozenset(roles_by_organization.keys()),
        roles_by_organization=roles_by_organization,
        capabilities_by_organization=capabilities_by_organization,
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

    effective_capabilities = resolve_effective_capabilities(member.role, member.capabilities)
    if required_capability not in effective_capabilities:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Organization capability '{required_capability.value}' required",
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
