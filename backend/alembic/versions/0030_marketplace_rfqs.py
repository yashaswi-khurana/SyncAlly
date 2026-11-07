"""Add buyer marketplace requests for quote."""

import sqlalchemy as sa

from alembic import op
from syncally.infrastructure.models.base import UUID_TYPE

revision = "0030_marketplace_rfqs"
down_revision = "0029_marketplace_listings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "marketplace_rfqs",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column("organization_id", UUID_TYPE, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("destination_country_code", sa.String(length=2), nullable=False),
        sa.Column("target_delivery_date", sa.Date(), nullable=True),
        sa.Column("target_unit_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_marketplace_rfq_quantity_positive"),
        sa.CheckConstraint("target_unit_price IS NULL OR target_unit_price >= 0", name="ck_marketplace_rfq_price_nonnegative"),
        sa.CheckConstraint(
            "(target_unit_price IS NULL AND currency IS NULL) OR "
            "(target_unit_price IS NOT NULL AND currency IS NOT NULL)",
            name="ck_marketplace_rfq_budget_currency_pair",
        ),
        sa.CheckConstraint("status IN ('ACTIVE', 'CLOSED')", name="ck_marketplace_rfq_status"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketplace_rfqs_organization_id", "marketplace_rfqs", ["organization_id"])
    op.create_index("ix_marketplace_rfqs_status", "marketplace_rfqs", ["status"])
    op.create_index("ix_marketplace_rfqs_status_category", "marketplace_rfqs", ["status", "category"])
    op.create_index(
        "ix_marketplace_rfqs_status_destination",
        "marketplace_rfqs",
        ["status", "destination_country_code"],
    )


def downgrade() -> None:
    has_rfqs = op.get_bind().execute(sa.text("SELECT 1 FROM marketplace_rfqs LIMIT 1")).first()
    if has_rfqs:
        raise RuntimeError("Cannot downgrade marketplace RFQs migration with published requests")
    op.drop_index("ix_marketplace_rfqs_status_destination", table_name="marketplace_rfqs")
    op.drop_index("ix_marketplace_rfqs_status_category", table_name="marketplace_rfqs")
    op.drop_index("ix_marketplace_rfqs_status", table_name="marketplace_rfqs")
    op.drop_index("ix_marketplace_rfqs_organization_id", table_name="marketplace_rfqs")
    op.drop_table("marketplace_rfqs")
