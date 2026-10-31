"""Persist human negotiation commands without reinterpreting legacy snapshots."""

import sqlalchemy as sa

from alembic import op

revision = "0016_persisted_negotiation_rounds"
down_revision = "0015_counterparty_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("negotiation_sessions") as batch:
        batch.create_unique_constraint("uq_negotiation_session_scope", ["id", "deal_id"])
        batch.create_check_constraint("ck_negotiation_round_count", "round_count >= 0 AND round_count <= max_rounds")
    with op.batch_alter_table("proposals") as batch:
        batch.add_column(sa.Column("lifecycle_origin", sa.String(16), nullable=False, server_default="LEGACY"))
        batch.add_column(sa.Column("created_by", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("evidence_refs", sa.JSON(), nullable=True))
        batch.create_foreign_key("fk_proposal_creator", "users", ["created_by"], ["id"])
        batch.create_unique_constraint("uq_proposal_scope", ["id", "deal_id"])
        batch.create_foreign_key("fk_proposal_session_scope", "negotiation_sessions", ["negotiation_session_id", "deal_id"], ["id", "deal_id"])
        batch.create_foreign_key("fk_proposal_predecessor_scope", "proposals", ["based_on_proposal_id", "deal_id"], ["id", "deal_id"])
        batch.create_check_constraint("ck_proposal_number_positive", "proposal_number > 0")
        batch.create_check_constraint("ck_proposal_origin", "lifecycle_origin IN ('LEGACY', 'HUMAN_ROUNDS')")
        batch.create_check_constraint("ck_human_proposal_state", "lifecycle_origin = 'LEGACY' OR (created_by IS NOT NULL AND status IN ('SUBMITTED', 'ACCEPTED_AS_CANDIDATE', 'REJECTED', 'SUPERSEDED', 'EXPIRED'))")
        batch.create_check_constraint("ck_human_proposal_expiry", "lifecycle_origin = 'LEGACY' OR expires_at IS NULL OR expires_at > created_at")
    with op.batch_alter_table("agreement_versions") as batch:
        batch.create_unique_constraint("uq_agreement_scope", ["id", "deal_id"])
        batch.create_foreign_key("fk_agreement_proposal_scope", "proposals", ["proposal_id", "deal_id"], ["id", "deal_id"])
        batch.create_check_constraint("ck_agreement_version_positive", "version_number > 0")
    op.create_index("uq_agreement_pending_deal", "agreement_versions", ["deal_id"], unique=True,
                    sqlite_where=sa.text("status = 'PENDING_APPROVAL'"), postgresql_where=sa.text("status = 'PENDING_APPROVAL'"))
    op.create_table(
        "negotiation_actions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("deal_id", sa.Uuid(), sa.ForeignKey("deals.id"), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("command_id", sa.Uuid(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("actor_organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("expected_deal_revision", sa.Integer(), nullable=False),
        sa.Column("proposal_id", sa.Uuid()),
        sa.Column("predecessor_id", sa.Uuid()),
        sa.Column("candidate_id", sa.Uuid()),
        sa.Column("invalidated_candidate_id", sa.Uuid()),
        sa.Column("from_status", sa.String(32)),
        sa.Column("to_status", sa.String(32)),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("deal_id", "command_id", name="uq_negotiation_command"),
        sa.ForeignKeyConstraint(["session_id", "deal_id"], ["negotiation_sessions.id", "negotiation_sessions.deal_id"], name="fk_action_session_scope"),
        sa.ForeignKeyConstraint(["proposal_id", "deal_id"], ["proposals.id", "proposals.deal_id"], name="fk_action_proposal_scope"),
        sa.ForeignKeyConstraint(["predecessor_id", "deal_id"], ["proposals.id", "proposals.deal_id"], name="fk_action_predecessor_scope"),
        sa.ForeignKeyConstraint(["candidate_id", "deal_id"], ["agreement_versions.id", "agreement_versions.deal_id"], name="fk_action_candidate_scope"),
        sa.ForeignKeyConstraint(["invalidated_candidate_id", "deal_id"], ["agreement_versions.id", "agreement_versions.deal_id"], name="fk_action_invalidated_scope"),
        sa.CheckConstraint("action IN ('submit', 'counter', 'accept', 'reject', 'supersede', 'expire', 'escalate')", name="ck_negotiation_action"),
        sa.CheckConstraint("expected_deal_revision >= 0", name="ck_negotiation_action_revision"),
    )
    terminal = sa.text("action IN ('accept', 'reject', 'supersede', 'expire')")
    op.create_index("uq_negotiation_terminal_action", "negotiation_actions", ["proposal_id"], unique=True, sqlite_where=terminal, postgresql_where=terminal)


def downgrade() -> None:
    actions = sa.table("negotiation_actions", sa.column("id"))
    proposals = sa.table("proposals", sa.column("lifecycle_origin"))
    if (op.get_bind().scalar(sa.select(sa.func.count()).select_from(actions))
            or op.get_bind().scalar(sa.select(sa.func.count()).select_from(proposals).where(proposals.c.lifecycle_origin == "HUMAN_ROUNDS"))):
        raise RuntimeError("Cannot downgrade 0016 with human negotiation history; retain schema and roll back application code only")
    op.drop_table("negotiation_actions")
    op.drop_index("uq_agreement_pending_deal", table_name="agreement_versions")
    with op.batch_alter_table("agreement_versions") as batch:
        batch.drop_constraint("fk_agreement_proposal_scope", type_="foreignkey")
        batch.drop_constraint("ck_agreement_version_positive", type_="check")
        batch.drop_constraint("uq_agreement_scope", type_="unique")
    with op.batch_alter_table("proposals") as batch:
        for name in ("ck_proposal_number_positive", "ck_proposal_origin", "ck_human_proposal_state", "ck_human_proposal_expiry"):
            batch.drop_constraint(name, type_="check")
        for name in ("fk_proposal_creator", "fk_proposal_session_scope", "fk_proposal_predecessor_scope"):
            batch.drop_constraint(name, type_="foreignkey")
        batch.drop_constraint("uq_proposal_scope", type_="unique")
        batch.drop_column("evidence_refs")
        batch.drop_column("created_by")
        batch.drop_column("lifecycle_origin")
    with op.batch_alter_table("negotiation_sessions") as batch:
        batch.drop_constraint("ck_negotiation_round_count", type_="check")
        batch.drop_constraint("uq_negotiation_session_scope", type_="unique")