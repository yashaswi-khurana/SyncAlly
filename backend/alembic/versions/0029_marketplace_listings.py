"""Add seller marketplace listings."""

import sqlalchemy as sa

from alembic import op
from syncally.infrastructure.models.base import UUID_TYPE

revision = "0029_marketplace_listings"
down_revision = "0028_fulfillment_shipping_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "marketplace_listings",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column("organization_id", UUID_TYPE, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("available_quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("unit_price", sa.Numeric(20, 6), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("available_quantity > 0", name="ck_marketplace_listing_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_marketplace_listing_price_nonnegative"),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_marketplace_listing_status"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketplace_listings_organization_id", "marketplace_listings", ["organization_id"])
    op.create_index("ix_marketplace_listings_status", "marketplace_listings", ["status"])
    op.create_index("ix_marketplace_listings_status_category", "marketplace_listings", ["status", "category"])


def downgrade() -> None:
    has_listings = op.get_bind().execute(
        sa.text("SELECT 1 FROM marketplace_listings LIMIT 1")
    ).first()
    if has_listings:
        raise RuntimeError("Cannot downgrade marketplace listings migration with published listings")
    op.drop_index("ix_marketplace_listings_status_category", table_name="marketplace_listings")
    op.drop_index("ix_marketplace_listings_status", table_name="marketplace_listings")
    op.drop_index("ix_marketplace_listings_organization_id", table_name="marketplace_listings")
    op.drop_table("marketplace_listings")
