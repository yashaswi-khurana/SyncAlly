"""Explicit private counterparty binding; never infer ownership from legacy rows."""

import sqlalchemy as sa

from alembic import op

revision = "0015_counterparty_onboarding"
down_revision = "0014_outbox_dispatch_started_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "counterparty_onboardings",
        sa.Column("invitation_jti", sa.Uuid(), primary_key=True),
        sa.Column("deal_id", sa.Uuid(), sa.ForeignKey("deals.id"), nullable=False),
        sa.Column("buyer_organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("shell_organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("inviter_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("recipient_email", sa.String(320), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("recipient_organization_id", sa.Uuid(), sa.ForeignKey("organizations.id")),
        sa.UniqueConstraint("deal_id", name="uq_counterparty_onboarding_deal"),
        sa.UniqueConstraint("shell_organization_id", name="uq_counterparty_onboarding_shell"),
        sa.CheckConstraint("buyer_organization_id <> shell_organization_id", name="ck_onboarding_distinct_parties"),
    )


def downgrade() -> None:
    table = sa.table("counterparty_onboardings", sa.column("invitation_jti"))
    if op.get_bind().scalar(sa.select(sa.func.count()).select_from(table)):
        raise RuntimeError("Cannot downgrade 0015 with onboarding history; retain the schema and roll back application code only")
    op.drop_table("counterparty_onboardings")