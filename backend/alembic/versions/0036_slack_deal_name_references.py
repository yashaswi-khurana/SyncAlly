"""Store encrypted Slack deal-name references for command resolution."""

import sqlalchemy as sa

from alembic import op

revision = "0036_slack_deal_name_references"
down_revision = "0035_slack_deal_subscriptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("slack_events", sa.Column("deal_reference", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("slack_events", "deal_reference")
