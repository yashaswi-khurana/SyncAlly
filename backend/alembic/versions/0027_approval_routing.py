"""Add organization approval routing policies and per-approver routing decisions."""

import sqlalchemy as sa
from alembic import op

revision = "0027_approval_routing"
down_revision = "0026_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_approval_routing_policies",
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("approver_user_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("mode IN ('SEQUENTIAL', 'PARALLEL')", name="ck_approval_routing_mode"),
        sa.CheckConstraint("version > 0", name="ck_approval_routing_version_positive"),
    )

    op.create_table(
        "agreement_routing_decisions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("agreement_version_id", sa.Uuid(), sa.ForeignKey("agreement_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("terms_hash", sa.String(length=64), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("agreement_version_id", "organization_id", "user_id"),
        sa.CheckConstraint("policy_version > 0", name="ck_routing_decision_policy_version_positive"),
    )
    op.create_index(
        "ix_agreement_routing_decisions_version_org",
        "agreement_routing_decisions",
        ["agreement_version_id", "organization_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    policy_count = bind.execute(sa.text("SELECT COUNT(*) FROM organization_approval_routing_policies")).scalar_one()
    decision_count = bind.execute(sa.text("SELECT COUNT(*) FROM agreement_routing_decisions")).scalar_one()
    if policy_count or decision_count:
        raise RuntimeError("Cannot downgrade while approval routing policies or decisions exist")
    op.drop_index("ix_agreement_routing_decisions_version_org", table_name="agreement_routing_decisions")
    op.drop_table("agreement_routing_decisions")
    op.drop_table("organization_approval_routing_policies")
