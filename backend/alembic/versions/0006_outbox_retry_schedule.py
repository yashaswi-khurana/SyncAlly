"""Persist the outbox retry schedule.

Revision ID: 0006_outbox_retry_schedule
Revises: 0005_conversation_party_unique
"""

import sqlalchemy as sa

from alembic import op

revision = "0006_outbox_retry_schedule"
down_revision = "0005_conversation_party_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("outbox_events", sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("outbox_events", "next_attempt_at")
