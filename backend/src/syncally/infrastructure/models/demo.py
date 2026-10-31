"""Explicit ownership of the local curated fixture, never inferred from parties."""

from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from syncally.infrastructure.models.base import UUID_TYPE, Base


class DemoFixture(Base):
    __tablename__ = "demo_fixtures"
    __table_args__ = (
        CheckConstraint("fixture_version > 0", name="ck_demo_fixture_version_positive"),
        CheckConstraint(
            "buyer_organization_id <> seller_organization_id",
            name="ck_demo_fixture_distinct_parties",
        ),
    )

    fixture_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    fixture_version: Mapped[int] = mapped_column(Integer, nullable=False)
    buyer_organization_id: Mapped[UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id"), nullable=False
    )
    seller_organization_id: Mapped[UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id"), nullable=False
    )
    deal_id: Mapped[UUID] = mapped_column(
        UUID_TYPE, ForeignKey("deals.id"), nullable=False, unique=True
    )
