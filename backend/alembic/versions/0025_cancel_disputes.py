"""Add deal cases and evidence tables for cancellation and disputes.

Revision ID: 0025_cancel_disputes
Revises: 0024_amendments
Create Date: 2026-11-07 10:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0025_cancel_disputes"
down_revision = "0025_system_admin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deal_cases",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("deal_id", sa.Uuid(), sa.ForeignKey("deals.id"), nullable=False),
        sa.Column("agreement_version_id", sa.Uuid(), sa.ForeignKey("agreement_versions.id"), nullable=False),
        sa.Column("agreement_terms_hash", sa.String(length=64), nullable=False),
        sa.Column("case_type", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("obligation_references", sa.JSON(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("requested_by_organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN"),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolved_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence_visibility", sa.String(length=32), nullable=False, server_default="MUTUAL_VISIBLE"),
        sa.Column("bilateral_consent_counterparty_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("bilateral_consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("operational_impact_blockers", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_deal_cases_deal_id", "deal_cases", ["deal_id"])
    op.create_index("ix_deal_cases_status", "deal_cases", ["status"])

    op.create_table(
        "deal_case_evidence",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("case_id", sa.Uuid(), sa.ForeignKey("deal_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("submitted_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("submitted_by_organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("visibility", sa.String(length=32), nullable=False, server_default="MUTUAL_VISIBLE"),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("metadata_payload", sa.JSON(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_deal_case_evidence_case_id", "deal_case_evidence", ["case_id"])


def downgrade() -> None:
    bind = op.get_bind()
    count = bind.execute(
        sa.text("SELECT COUNT(*) FROM deal_cases")
    ).scalar_one()
    if count:
        raise RuntimeError("Cannot downgrade while deal case history exists")
    op.drop_index("ix_deal_case_evidence_case_id", table_name="deal_case_evidence")
    op.drop_table("deal_case_evidence")
    op.drop_index("ix_deal_cases_status", table_name="deal_cases")
    op.drop_index("ix_deal_cases_deal_id", table_name="deal_cases")
    op.drop_table("deal_cases")
