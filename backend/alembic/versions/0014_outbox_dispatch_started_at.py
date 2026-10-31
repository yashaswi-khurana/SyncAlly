"""Retain durable evidence of generic outbox dispatch attempts."""

import sqlalchemy as sa

from alembic import op

revision = "0014_outbox_dispatch_started_at"
down_revision = "0013_curated_demo_fixture"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "outbox_events",
        sa.Column("dispatch_started_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("outbox_events", "dispatch_started_at")