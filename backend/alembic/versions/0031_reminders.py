"""Add durable obligation reminders table and indexes."""

import sqlalchemy as sa
from alembic import op
from syncally.infrastructure.models.base import UUID_TYPE

revision = "0031_reminders"
down_revision = "0030_marketplace_rfqs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deal_reminders",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column("deal_id", UUID_TYPE, nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("reference_id", UUID_TYPE, nullable=False),
        sa.Column("recipient_organization_id", UUID_TYPE, nullable=False),
        sa.Column("recipient_user_id", UUID_TYPE, nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="SCHEDULED"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recurrence_cap", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("recurrence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deduplication_key", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False, server_default="IN_APP"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suppressed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suppression_reason", sa.String(length=64), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "scope IN ('FULFILLMENT', 'MILESTONE', 'CASE', 'ROUTING')",
            name="ck_deal_reminders_scope",
        ),
        sa.CheckConstraint(
            "status IN ('SCHEDULED', 'PENDING', 'DELIVERED', 'SUPPRESSED', 'FAILED')",
            name="ck_deal_reminders_status",
        ),
        sa.CheckConstraint("channel IN ('IN_APP')", name="ck_deal_reminders_channel"),
        sa.CheckConstraint("recurrence_cap >= 1", name="ck_deal_reminders_recurrence_cap_positive"),
        sa.CheckConstraint("recurrence_count >= 0", name="ck_deal_reminders_recurrence_count_nonneg"),
        sa.CheckConstraint("retry_count >= 0", name="ck_deal_reminders_retry_count_nonneg"),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deduplication_key", name="uq_deal_reminders_deduplication_key"),
    )
    op.create_index("ix_deal_reminders_deal_status", "deal_reminders", ["deal_id", "status"])
    op.create_index(
        "ix_deal_reminders_pending_due",
        "deal_reminders",
        ["status", "due_at", "next_attempt_at"],
    )
    op.create_index("ix_deal_reminders_dedup", "deal_reminders", ["deduplication_key"], unique=True)
    op.create_index(
        "ix_deal_reminders_recipient",
        "deal_reminders",
        ["recipient_organization_id", "status"],
    )


def downgrade() -> None:
    from alembic import context

    if not context.is_offline_mode():
        has_records = op.get_bind().execute(sa.text("SELECT 1 FROM deal_reminders LIMIT 1")).first()
        if has_records:
            raise RuntimeError("Cannot downgrade deal reminders migration with existing records")
    op.drop_index("ix_deal_reminders_recipient", table_name="deal_reminders")
    op.drop_index("ix_deal_reminders_dedup", table_name="deal_reminders")
    op.drop_index("ix_deal_reminders_pending_due", table_name="deal_reminders")
    op.drop_index("ix_deal_reminders_deal_status", table_name="deal_reminders")
    op.drop_table("deal_reminders")
