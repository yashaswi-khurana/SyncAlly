"""Persistence-backed resolution of verified actor context."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from syncally.application.identity import ActorContext
from syncally.infrastructure.models import Organization, OrganizationMember, User


def resolve_actor(db: Session, user_id: UUID) -> ActorContext | None:
    """Resolve an active user and their active memberships from persistence."""
    user = db.scalar(select(User).where(User.id == user_id, User.status == "ACTIVE"))
    if user is None:
        return None

    organization_ids = db.scalars(
        select(OrganizationMember.organization_id)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.status == "ACTIVE",
            Organization.status == "ACTIVE",
        )
    )
    return ActorContext(user_id=user_id, organization_ids=frozenset(organization_ids))
