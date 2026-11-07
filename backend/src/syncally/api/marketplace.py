"""Search public seller listings and manage listings for an organization."""

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
from syncally.api.organizations import _active_admin_membership
from syncally.application.identity import ActorContext
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import MarketplaceListing, MarketplaceRFQ, Organization

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


@router.get("/listings/{listing_id}", response_model=MarketplaceListingResponse)
def get_marketplace_listing(
    listing_id: UUID,
    _actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    result = db.execute(
        select(MarketplaceListing, Organization)
        .join(Organization, Organization.id == MarketplaceListing.organization_id)
        .where(
            MarketplaceListing.id == listing_id,
            MarketplaceListing.status == "ACTIVE",
            Organization.status == "ACTIVE",
        )
    ).one_or_none()
    if result is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing, organization = result
    return _response(listing, organization)


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


class MarketplaceRFQRequest(BaseModel):
    organization_id: UUID
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=2000)
    category: str = Field(min_length=2, max_length=100)
    quantity: Decimal = Field(gt=0, max_digits=20, decimal_places=6)
    unit: str = Field(min_length=1, max_length=32)
    destination_country_code: str = Field(pattern=r"^[A-Z]{2}$")
    target_delivery_date: date | None = None
    target_unit_price: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=6)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")

    @field_validator("title", "category", "unit", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_budget_currency_pair(self) -> "MarketplaceRFQRequest":
        if (self.target_unit_price is None) != (self.currency is None):
            raise ValueError("target_unit_price and currency must be provided together")
        return self


class MarketplaceRFQResponse(BaseModel):
    id: UUID
    organization_id: UUID
    organization_name: str
    organization_country_code: str
    title: str
    description: str
    category: str
    quantity: str
    unit: str
    destination_country_code: str
    target_delivery_date: date | None
    target_unit_price: str | None
    currency: str | None


def _rfq_response(rfq: MarketplaceRFQ, organization: Organization) -> dict[str, Any]:
    return {
        "id": rfq.id,
        "organization_id": organization.id,
        "organization_name": organization.legal_name,
        "organization_country_code": organization.country_code,
        "title": rfq.title,
        "description": rfq.description,
        "category": rfq.category,
        "quantity": format(rfq.quantity, "f"),
        "unit": rfq.unit,
        "destination_country_code": rfq.destination_country_code,
        "target_delivery_date": rfq.target_delivery_date,
        "target_unit_price": format(rfq.target_unit_price, "f") if rfq.target_unit_price is not None else None,
        "currency": rfq.currency,
    }


@router.get("/rfqs", response_model=list[MarketplaceRFQResponse])
def search_marketplace_rfqs(
    q: str | None = Query(default=None, max_length=100),
    destination_country_code: str | None = Query(
        default=None, min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$"
    ),
    category: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10000),
    _actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    statement = (
        select(MarketplaceRFQ, Organization)
        .join(Organization, Organization.id == MarketplaceRFQ.organization_id)
        .where(MarketplaceRFQ.status == "ACTIVE", Organization.status == "ACTIVE")
        .order_by(MarketplaceRFQ.created_at.desc(), MarketplaceRFQ.id)
        .limit(limit)
        .offset(offset)
    )
    if destination_country_code:
        statement = statement.where(
            MarketplaceRFQ.destination_country_code == destination_country_code.upper()
        )
    if category and category.strip():
        statement = statement.where(MarketplaceRFQ.category.ilike(f"%{category.strip()}%"))
    if q and q.strip():
        term = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{term}%"
        statement = statement.where(
            MarketplaceRFQ.title.ilike(pattern, escape="\\")
            | MarketplaceRFQ.description.ilike(pattern, escape="\\")
            | MarketplaceRFQ.category.ilike(pattern, escape="\\")
        )
    return [_rfq_response(rfq, organization) for rfq, organization in db.execute(statement)]


@router.post("/rfqs", status_code=201, response_model=MarketplaceRFQResponse)
def create_marketplace_rfq(
    payload: MarketplaceRFQRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    organization, _ = _active_admin_membership(db, payload.organization_id, actor.user_id)
    rfq = MarketplaceRFQ(
        organization_id=organization.id,
        title=payload.title,
        description=payload.description.strip(),
        category=payload.category,
        quantity=payload.quantity,
        unit=payload.unit,
        destination_country_code=payload.destination_country_code,
        target_delivery_date=payload.target_delivery_date,
        target_unit_price=payload.target_unit_price,
        currency=payload.currency,
    )
    db.add(rfq)
    db.commit()
    db.refresh(rfq)
    return _rfq_response(rfq, organization)


@router.get("/rfqs/{rfq_id}", response_model=MarketplaceRFQResponse)
def get_marketplace_rfq(
    rfq_id: UUID,
    _actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    rfq = db.get(MarketplaceRFQ, rfq_id)
    organization = db.get(Organization, rfq.organization_id) if rfq else None
    if rfq is None or rfq.status != "ACTIVE" or organization is None or organization.status != "ACTIVE":
        raise HTTPException(status_code=404, detail="Request for quote not found")
    return _rfq_response(rfq, organization)


@router.delete("/rfqs/{rfq_id}")
def close_marketplace_rfq(
    rfq_id: UUID,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    rfq = db.get(MarketplaceRFQ, rfq_id)
    if rfq is None:
        raise HTTPException(status_code=404, detail="Request for quote not found")
    _active_admin_membership(db, rfq.organization_id, actor.user_id)
    rfq.status = "CLOSED"
    db.commit()
    return {"status": "CLOSED"}
