"""Deal HTTP endpoints."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
from syncally.application.identity import ActorContext
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import Deal, Organization, OrganizationMember


def get_authorized_deal(
    deal_id: UUID,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> Deal:
    """Load a deal only when the actor belongs to one of its organizations."""
    active_membership = exists(
        select(OrganizationMember.id)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .where(
            OrganizationMember.user_id == actor.user_id,
            OrganizationMember.status == "ACTIVE",
            Organization.status == "ACTIVE",
            or_(
                OrganizationMember.organization_id == Deal.buyer_organization_id,
                OrganizationMember.organization_id == Deal.seller_organization_id,
            ),
        )
    )
    deal = db.scalar(select(Deal).where(Deal.id == deal_id, active_membership))
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    if not actor.can_access_organizations(
        deal.buyer_organization_id, deal.seller_organization_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    return deal


def read_deal(deal: Deal = Depends(get_authorized_deal)) -> dict[str, str]:
    """Return the public deal state after authorization."""
    return {"id": str(deal.id), "status": deal.status}
