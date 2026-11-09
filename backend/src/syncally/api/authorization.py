"""Shared API-level authorization decisions for party-scoped deal routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from syncally.application.identity import ActorContext


def require_deal_action(
    actor: ActorContext,
    deal: object,
    organization_id: UUID,
    permission: str,
) -> None:
    """Enforce party membership, independent deal scope, then action permission."""
    party_ids = {
        getattr(deal, "buyer_organization_id"),
        getattr(deal, "seller_organization_id"),
    }
    if organization_id not in party_ids or organization_id not in actor.organization_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    if not actor.has_deal_authority(deal, organization_id, "deal.read_assigned"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    if not actor.has_deal_authority(deal, organization_id, permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Organization permission '{permission}' required")


def resolve_actor_party(actor: ActorContext, deal: object, requested: UUID | None = None) -> UUID:
    party_ids = {
        getattr(deal, "buyer_organization_id"),
        getattr(deal, "seller_organization_id"),
    }
    candidates = party_ids & actor.organization_ids
    if requested is not None:
        if requested not in candidates:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
        return requested
    if not candidates:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    if len(candidates) != 1:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Select the organization you are acting for")
    return next(iter(candidates))
