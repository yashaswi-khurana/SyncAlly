"""Persist explicit Slack share-command bodies for worker processing."""

import sqlalchemy as sa

from alembic import op

revision = "0037_slack_message_relay"
down_revision = "0036_slack_deal_name_references"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("slack_events", sa.Column("message_body", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("slack_events", "message_body")