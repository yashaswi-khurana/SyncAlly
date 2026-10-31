"""Add explicit curated demo ownership without adopting any legacy data."""

import sqlalchemy as sa

from alembic import op

revision = "0013_curated_demo_fixture"
down_revision = "0012_message_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "demo_fixtures",
        sa.Column("fixture_key", sa.String(64), primary_key=True),
        sa.Column("fixture_version", sa.Integer(), nullable=False),
        sa.Column(
            "buyer_organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False
        ),
        sa.Column(
            "seller_organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False
        ),
        sa.Column("deal_id", sa.Uuid(), sa.ForeignKey("deals.id"), nullable=False),
        sa.UniqueConstraint("deal_id"),
        sa.CheckConstraint("fixture_version > 0", name="ck_demo_fixture_version_positive"),
        sa.CheckConstraint(
            "buyer_organization_id <> seller_organization_id",
            name="ck_demo_fixture_distinct_parties",
        ),
    )


def downgrade() -> None:
    op.drop_table("demo_fixtures")
