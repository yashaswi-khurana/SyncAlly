"""Persist organization-scoped Slack OAuth installations and one-use state."""

import sqlalchemy as sa

from alembic import op
from syncally.infrastructure.models.base import JSON_TYPE, UUID_TYPE

revision = "0033_slack_integrations"
down_revision = "0032_iam_deal_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "slack_installations",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column("organization_id", UUID_TYPE, nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_name", sa.String(length=256), nullable=False),
        sa.Column("bot_user_id", sa.String(length=64), nullable=False),
        sa.Column("encrypted_bot_token", sa.Text(), nullable=True),
        sa.Column("granted_scopes", JSON_TYPE, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("connected_by_user_id", UUID_TYPE, nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('CONNECTED', 'DISCONNECTED')",
            name="ck_slack_installation_status",
        ),
        sa.CheckConstraint(
            "(status = 'CONNECTED' AND encrypted_bot_token IS NOT NULL AND disconnected_at IS NULL) "
            "OR (status = 'DISCONNECTED' AND encrypted_bot_token IS NULL AND disconnected_at IS NOT NULL)",
            name="ck_slack_installation_credential_lifecycle",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["connected_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_slack_installation_org_connected",
        "slack_installations",
        ["organization_id"],
        unique=True,
        postgresql_where=sa.text("status = 'CONNECTED'"),
        sqlite_where=sa.text("status = 'CONNECTED'"),
    )
    op.create_index(
        "uq_slack_installation_workspace_connected",
        "slack_installations",
        ["workspace_id"],
        unique=True,
        postgresql_where=sa.text("status = 'CONNECTED'"),
        sqlite_where=sa.text("status = 'CONNECTED'"),
    )

    op.create_table(
        "slack_oauth_states",
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("organization_id", UUID_TYPE, nullable=False),
        sa.Column("user_id", UUID_TYPE, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("state_hash"),
    )
    op.create_index(
        "ix_slack_oauth_states_expires_at",
        "slack_oauth_states",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_slack_oauth_states_expires_at", table_name="slack_oauth_states")
    op.drop_table("slack_oauth_states")
    op.drop_index(
        "uq_slack_installation_workspace_connected", table_name="slack_installations"
    )
    op.drop_index("uq_slack_installation_org_connected", table_name="slack_installations")
    op.drop_table("slack_installations")
