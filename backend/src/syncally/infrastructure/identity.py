"""Persistence-backed resolution of verified actor context."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from syncally.application.identity import ActorContext
from syncally.domain.organizations.organization import (
    OrganizationCapability,
    OrganizationMemberRole,
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
        except ValueError:
            role = OrganizationMemberRole.MEMBER
        roles_by_organization[org_id] = role

        assigned_caps: set[OrganizationCapability] = set()
        for item in (caps_raw or []):
            try:
                assigned_caps.add(OrganizationCapability(item))
            except ValueError:
                pass

        defaults: frozenset[OrganizationCapability]
        if role == OrganizationMemberRole.ADMIN:
            defaults = frozenset({
                OrganizationCapability.ADMINISTRATION,
                OrganizationCapability.DRAFTING,
                OrganizationCapability.AGREEMENT_APPROVAL,
            })
        else:
            defaults = frozenset({OrganizationCapability.DRAFTING})

        capabilities_by_organization[org_id] = defaults | frozenset(assigned_caps)

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

    try:
        role = OrganizationMemberRole(member.role)
    except ValueError:
        role = OrganizationMemberRole.MEMBER

    assigned_caps: set[OrganizationCapability] = set()
    for item in (member.capabilities or []):
        try:
            assigned_caps.add(OrganizationCapability(item))
        except ValueError:
            pass

    defaults: frozenset[OrganizationCapability]
    if role == OrganizationMemberRole.ADMIN:
        defaults = frozenset({
            OrganizationCapability.ADMINISTRATION,
            OrganizationCapability.DRAFTING,
            OrganizationCapability.AGREEMENT_APPROVAL,
        })
    else:
        defaults = frozenset({OrganizationCapability.DRAFTING})

    effective_capabilities = defaults | frozenset(assigned_caps)
    if required_capability not in effective_capabilities:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Organization capability '{required_capability.value}' required",
        )

    return member
