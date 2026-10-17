"""Authenticated actor and organization authorization rules."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from syncally.infrastructure.models import Deal, Organization, OrganizationMember, User


@dataclass(frozen=True)
class ActorContext:
    """The verified user and active organization memberships for one request."""

    user_id: UUID
    organization_ids: frozenset[UUID]

    def can_access_deal(self, deal: Deal) -> bool:
        """Return whether the actor belongs to either party of the deal."""
        return bool(
            {deal.buyer_organization_id, deal.seller_organization_id}
            & self.organization_ids
        )


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
