"""Create the initial SyncAlly commercial ledger schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB()


def uuid_column() -> sa.Column:
    return sa.Column(UUID, nullable=False)


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("legal_name", sa.Text(), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "organization_members",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="MEMBER"),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "user_id"),
    )
    op.create_index("ix_organization_members_user_id", "organization_members", ["user_id"])
    op.create_table(
        "deals",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("buyer_organization_id", UUID, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("seller_organization_id", UUID, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("current_proposal_id", UUID, nullable=True),
        sa.Column("current_agreement_version_id", UUID, nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("buyer_organization_id <> seller_organization_id", name="ck_deal_distinct_parties"),
    )
    op.create_table(
        "conversations",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("deal_id", UUID, sa.ForeignKey("deals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("participant_organization_id", UUID, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "messages",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("conversation_id", UUID, sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_user_id", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("author_agent_id", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("visibility", sa.String(32), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(author_user_id IS NOT NULL AND author_agent_id IS NULL) "
            "OR (author_user_id IS NULL AND author_agent_id IS NOT NULL)",
            name="ck_message_has_author",
        ),
    )
    op.create_table(
        "negotiation_sessions",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("deal_id", UUID, sa.ForeignKey("deals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("max_rounds", sa.Integer(), nullable=False),
        sa.Column("round_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_proposal_id", UUID, nullable=True),
        sa.Column("escalated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("deal_id"),
        sa.CheckConstraint("max_rounds > 0", name="ck_negotiation_max_rounds_positive"),
    )
    op.create_table(
        "proposals",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("deal_id", UUID, sa.ForeignKey("deals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("negotiation_session_id", UUID, sa.ForeignKey("negotiation_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("proposal_number", sa.Integer(), nullable=False),
        sa.Column("author_organization_id", UUID, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("based_on_proposal_id", UUID, sa.ForeignKey("proposals.id"), nullable=True),
        sa.Column("terms_json", JSONB, nullable=False),
        sa.Column("terms_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("deal_id", "proposal_number"),
    )
    op.create_table(
        "constraints",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("deal_id", UUID, sa.ForeignKey("deals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_organization_id", UUID, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("field", sa.Text(), nullable=False),
        sa.Column("typed_value", sa.Text(), nullable=False),
        sa.Column("currency_or_unit", sa.Text(), nullable=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="EXTRACTED"),
        sa.Column("visibility", sa.String(32), nullable=False),
        sa.Column("source_message_id", UUID, sa.ForeignKey("messages.id"), nullable=True),
        sa.Column("source_span", sa.Text(), nullable=True),
        sa.Column("confirmed_by", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "agreement_versions",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("deal_id", UUID, sa.ForeignKey("deals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("proposal_id", UUID, sa.ForeignKey("proposals.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("canonical_terms_json", JSONB, nullable=False),
        sa.Column("terms_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING_APPROVAL"),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("deal_id", "version_number"),
    )
    op.create_table(
        "approvals",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("deal_id", UUID, sa.ForeignKey("deals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agreement_version_id", UUID, sa.ForeignKey("agreement_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("terms_hash", sa.String(64), nullable=False),
        sa.Column("auth_context", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("agreement_version_id", "organization_id"),
    )
    op.create_table(
        "obligations",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("deal_id", UUID, sa.ForeignKey("deals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agreement_version_id", UUID, sa.ForeignKey("agreement_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("obligation_type", sa.String(32), nullable=False),
        sa.Column("owner_organization_id", UUID, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("counterparty_organization_id", UUID, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("due_condition", sa.Text(), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_terms_reference", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("owner_organization_id <> counterparty_organization_id", name="ck_obligation_distinct_parties"),
    )
    op.create_table(
        "payment_milestones",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("deal_id", UUID, sa.ForeignKey("deals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agreement_version_id", UUID, sa.ForeignKey("agreement_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("obligation_id", UUID, sa.ForeignKey("obligations.id"), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("payer_organization_id", UUID, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("amount", sa.Numeric(20, 6), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("trigger_type", sa.String(64), nullable=False),
        sa.Column("due_condition", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("agreement_version_id", "sequence_number"),
        sa.CheckConstraint("sequence_number > 0", name="ck_payment_milestone_sequence_positive"),
        sa.CheckConstraint("amount > 0", name="ck_payment_milestone_amount_positive"),
    )
    op.create_table(
        "payment_intents",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("deal_id", UUID, sa.ForeignKey("deals.id"), nullable=False),
        sa.Column("agreement_version_id", UUID, sa.ForeignKey("agreement_versions.id"), nullable=False),
        sa.Column("payment_milestone_id", UUID, sa.ForeignKey("payment_milestones.id"), nullable=False),
        sa.Column("seller_organization_id", UUID, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("payer_organization_id", UUID, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("authorized_by", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Numeric(20, 6), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="AUTHORIZED"),
        sa.Column("provider", sa.String(32), nullable=False, server_default="PAYPAL"),
        sa.Column("provider_invoice_id", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("request_payload_hash", sa.String(64), nullable=True),
        sa.Column("reconciled_amount", sa.Numeric(20, 6), nullable=True),
        sa.Column("last_reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(64), nullable=True),
        sa.Column("failure_detail", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("idempotency_key"),
        sa.CheckConstraint("amount > 0", name="ck_payment_intent_amount_positive"),
    )
    op.create_table(
        "webhook_events",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_event_id", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("raw_payload", JSONB, nullable=False),
        sa.Column("payment_intent_id", UUID, sa.ForeignKey("payment_intents.id"), nullable=True),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "provider_event_id"),
    )
    op.create_table(
        "outbox_events",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("aggregate_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", UUID, nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("aggregate_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", UUID, nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("actor_type", sa.String(32), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("correlation_id", sa.Text(), nullable=True),
        sa.Column("payload", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )


def downgrade() -> None:
    for table in (
        "audit_events",
        "outbox_events",
        "webhook_events",
        "payment_intents",
        "payment_milestones",
        "obligations",
        "approvals",
        "agreement_versions",
        "constraints",
        "proposals",
        "negotiation_sessions",
        "messages",
        "conversations",
        "deals",
        "organization_members",
        "users",
        "organizations",
    ):
        op.drop_table(table)
