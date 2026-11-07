"""Search public seller listings and manage listings for an organization."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
from syncally.api.organizations import _active_admin_membership
from syncally.application.identity import ActorContext
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import MarketplaceListing, Organization

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


class MarketplaceListingRequest(BaseModel):
    organization_id: UUID
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=2000)
    category: str = Field(min_length=2, max_length=100)
    available_quantity: Decimal = Field(gt=0, max_digits=20, decimal_places=6)
    unit: str = Field(min_length=1, max_length=32)
    unit_price: Decimal = Field(ge=0, max_digits=20, decimal_places=6)
    currency: str = Field(pattern=r"^[A-Z]{3}$")

    @field_validator("title", "category", "unit", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class MarketplaceListingResponse(BaseModel):
    id: UUID
    organization_id: UUID
    organization_name: str
    country_code: str
    title: str
    description: str
    category: str
    available_quantity: str
    unit: str
    unit_price: str
    currency: str


def _response(
    listing: MarketplaceListing, organization: Organization
) -> dict[str, Any]:
    return {
        "id": listing.id,
        "organization_id": organization.id,
        "organization_name": organization.legal_name,
        "country_code": organization.country_code,
        "title": listing.title,
        "description": listing.description,
        "category": listing.category,
        "available_quantity": format(listing.available_quantity, "f"),
        "unit": listing.unit,
        "unit_price": format(listing.unit_price, "f"),
        "currency": listing.currency,
    }


@router.get("/listings", response_model=list[MarketplaceListingResponse])
def search_marketplace_listings(
    q: str | None = Query(default=None, max_length=100),
    country_code: str | None = Query(default=None, min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$"),
    category: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10000),
    _actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    statement = (
        select(MarketplaceListing, Organization)
        .join(Organization, Organization.id == MarketplaceListing.organization_id)
        .where(
            MarketplaceListing.status == "ACTIVE",
            Organization.status == "ACTIVE",
        )
        .order_by(MarketplaceListing.created_at.desc(), MarketplaceListing.id)
        .limit(limit)
        .offset(offset)
    )
    if country_code:
        statement = statement.where(Organization.country_code == country_code.upper())
    if category and category.strip():
        statement = statement.where(MarketplaceListing.category.ilike(f"%{category.strip()}%"))
    if q and q.strip():
        term = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{term}%"
        statement = statement.where(
            MarketplaceListing.title.ilike(pattern, escape="\\")
            | MarketplaceListing.description.ilike(pattern, escape="\\")
            | MarketplaceListing.category.ilike(pattern, escape="\\")
        )
    return [_response(listing, organization) for listing, organization in db.execute(statement)]


@router.post("/listings", status_code=201, response_model=MarketplaceListingResponse)
def create_marketplace_listing(
    payload: MarketplaceListingRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    organization, _ = _active_admin_membership(db, payload.organization_id, actor.user_id)
    listing = MarketplaceListing(
        organization_id=organization.id,
        title=payload.title,
        description=payload.description.strip(),
        category=payload.category,
        available_quantity=payload.available_quantity,
        unit=payload.unit,
        unit_price=payload.unit_price,
        currency=payload.currency,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return _response(listing, organization)


@router.delete("/listings/{listing_id}")
def deactivate_marketplace_listing(
    listing_id: UUID,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    listing = db.get(MarketplaceListing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    _active_admin_membership(db, listing.organization_id, actor.user_id)
    listing.status = "INACTIVE"
    db.commit()
    return {"status": "INACTIVE"}
