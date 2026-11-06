"""Add amendment lineage and rationale columns to agreement versions.

Revision ID: 0024_amendments
Revises: 0023_inviting_party
Create Date: 2026-11-06 18:15:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0024_amendments"
down_revision = "0023_inviting_party"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("agreement_versions") as batch_op:
        batch_op.add_column(sa.Column("prior_agreement_version_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("prior_terms_hash", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("amendment_rationale", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            "fk_agreement_version_prior_version",
            "agreement_versions",
            ["prior_agreement_version_id"],
            ["id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    count = bind.execute(
        sa.text("SELECT COUNT(*) FROM agreement_versions WHERE version_number > 1")
    ).scalar_one()
    if count:
        raise RuntimeError("Cannot downgrade while amendment history exists")
    with op.batch_alter_table("agreement_versions") as batch_op:
        batch_op.drop_constraint("fk_agreement_version_prior_version", type_="foreignkey")
        batch_op.drop_column("amendment_rationale")
        batch_op.drop_column("prior_terms_hash")
        batch_op.drop_column("prior_agreement_version_id")
