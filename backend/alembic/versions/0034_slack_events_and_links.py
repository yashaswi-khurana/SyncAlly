"""Persist Slack event delivery and explicit user linking."""

import sqlalchemy as sa

from alembic import op
from syncally.infrastructure.models.base import UUID_TYPE

revision = "0034_slack_events_and_links"
down_revision = "0033_slack_integrations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "slack_events",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column("event_id", sa.String(128), nullable=False),
        sa.Column("installation_id", UUID_TYPE, nullable=False),
        sa.Column("workspace_id", sa.String(64), nullable=False),
        sa.Column("slack_user_id", sa.String(64), nullable=False),
        sa.Column("channel_id", sa.String(64), nullable=False),
        sa.Column("message_ts", sa.String(32), nullable=False),
        sa.Column("thread_ts", sa.String(32), nullable=False),
        sa.Column("command", sa.String(32), nullable=False),
        sa.Column("deal_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('PENDING', 'PROCESSING', 'DELIVERED', 'FAILED')", name="ck_slack_event_status"),
        sa.ForeignKeyConstraint(["installation_id"], ["slack_installations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_slack_events_pending", "slack_events", ["status", "available_at"])
    op.create_index("ix_slack_events_retention", "slack_events", ["status", "created_at"])
    op.create_table(
        "slack_user_links",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column("installation_id", UUID_TYPE, nullable=False),
        sa.Column("organization_id", UUID_TYPE, nullable=False),
        sa.Column("workspace_id", sa.String(64), nullable=False),
        sa.Column("slack_user_id", sa.String(64), nullable=False),
        sa.Column("user_id", UUID_TYPE, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["installation_id"], ["slack_installations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("installation_id", "slack_user_id", name="uq_slack_user_link_slack_identity"),
        sa.UniqueConstraint("installation_id", "user_id", name="uq_slack_user_link_syncally_identity"),
    )
    op.create_table(
        "slack_link_challenges",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column("event_id", sa.String(128), nullable=False),
        sa.Column("installation_id", UUID_TYPE, nullable=False),
        sa.Column("organization_id", UUID_TYPE, nullable=False),
        sa.Column("workspace_id", sa.String(64), nullable=False),
        sa.Column("slack_user_id", sa.String(64), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("encrypted_code", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["installation_id"], ["slack_installations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_hash"),
        sa.UniqueConstraint("event_id", name="uq_slack_link_challenge_event"),
    )
    op.create_index("ix_slack_link_challenges_expires_at", "slack_link_challenges", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_slack_link_challenges_expires_at", table_name="slack_link_challenges")
    op.drop_table("slack_link_challenges")
    op.drop_table("slack_user_links")
    op.drop_index("ix_slack_events_retention", table_name="slack_events")
    op.drop_index("ix_slack_events_pending", table_name="slack_events")
    op.drop_table("slack_events")
