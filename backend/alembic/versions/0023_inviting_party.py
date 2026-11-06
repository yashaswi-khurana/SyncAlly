"""Preserve the initiating party for counterparty invitations."""

import sqlalchemy as sa

from alembic import op

revision = "0021_inviting_party"
down_revision = "0020_fulfillment_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("counterparty_onboardings") as batch:
        batch.drop_constraint("ck_onboarding_distinct_parties", type_="check")
        batch.alter_column("buyer_organization_id", new_column_name="inviting_organization_id")
        batch.add_column(sa.Column("inviter_party", sa.String(6), nullable=False, server_default="BUYER"))
        batch.create_check_constraint("ck_onboarding_distinct_parties", "inviting_organization_id <> shell_organization_id")
        batch.create_check_constraint("ck_onboarding_inviter_party", "inviter_party IN ('BUYER', 'SELLER')")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT COUNT(*) FROM counterparty_onboardings WHERE inviter_party <> 'BUYER'")).scalar_one():
        raise RuntimeError("Cannot downgrade while seller-initiated invitation history exists")
    with op.batch_alter_table("counterparty_onboardings") as batch:
        batch.drop_constraint("ck_onboarding_inviter_party", type_="check")
        batch.drop_constraint("ck_onboarding_distinct_parties", type_="check")
        batch.drop_column("inviter_party")
        batch.alter_column("inviting_organization_id", new_column_name="buyer_organization_id")
        batch.create_check_constraint("ck_onboarding_distinct_parties", "buyer_organization_id <> shell_organization_id")
