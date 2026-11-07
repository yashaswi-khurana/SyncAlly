"""Seller-published marketplace listings."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from syncally.infrastructure.models.base import UUID_TYPE, Base
from syncally.infrastructure.models.mixins import TimestampMixin


class MarketplaceListing(TimestampMixin, Base):
    __tablename__ = "marketplace_listings"
    __table_args__ = (
        CheckConstraint("available_quantity > 0", name="ck_marketplace_listing_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_marketplace_listing_price_nonnegative"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_marketplace_listing_status"),
        Index("ix_marketplace_listings_status_category", "status", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    available_quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE", index=True)
