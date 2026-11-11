"""Add explicit Slack deal subscriptions and outbound delivery queue."""

import sqlalchemy as sa

from alembic import op
from syncally.infrastructure.models.base import UUID_TYPE

revision = "0035_slack_deal_subscriptions"
down_revision = "0034_slack_events_and_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_outbox_events_type_created", "outbox_events", ["event_type", "created_at"]
    )
    op.create_table(
        "slack_deal_subscriptions",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column("installation_id", UUID_TYPE, nullable=False),
        sa.Column("organization_id", UUID_TYPE, nullable=False),
        sa.Column("workspace_id", sa.String(64), nullable=False),
        sa.Column("slack_user_id", sa.String(64), nullable=False),
        sa.Column("user_id", UUID_TYPE, nullable=False),
        sa.Column("deal_id", UUID_TYPE, nullable=False),
        sa.Column("channel_id", sa.String(64), nullable=False),
        sa.Column("thread_ts", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["installation_id"], ["slack_installations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "installation_id", "user_id", "deal_id", "channel_id", "thread_ts",
            name="uq_slack_deal_subscription_thread",
        ),
    )
    op.create_index(
        "ix_slack_deal_subscriptions_deal",
        "slack_deal_subscriptions",
        ["deal_id", "created_at"],
    )
    op.create_table(
        "slack_notification_deliveries",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column("source_event_id", UUID_TYPE, nullable=False),
        sa.Column("subscription_id", UUID_TYPE, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'DELIVERED', 'FAILED')",
            name="ck_slack_notification_delivery_status",
        ),
        sa.ForeignKeyConstraint(["source_event_id"], ["outbox_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_id"], ["slack_deal_subscriptions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_event_id", "subscription_id",
            name="uq_slack_notification_source_subscription",
        ),
    )
    op.create_index(
        "ix_slack_notification_deliveries_pending",
        "slack_notification_deliveries",
        ["status", "available_at"],
    )
    op.create_index(
        "ix_slack_notification_deliveries_retention",
        "slack_notification_deliveries",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_slack_notification_deliveries_retention", table_name="slack_notification_deliveries")
    op.drop_index("ix_slack_notification_deliveries_pending", table_name="slack_notification_deliveries")
    op.drop_table("slack_notification_deliveries")
    op.drop_index("ix_slack_deal_subscriptions_deal", table_name="slack_deal_subscriptions")
    op.drop_table("slack_deal_subscriptions")
    op.drop_index("ix_outbox_events_type_created", table_name="outbox_events")
