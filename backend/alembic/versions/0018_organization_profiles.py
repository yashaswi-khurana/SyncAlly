"""Create organization_profiles table for bounded profile collections."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0018_organization_profiles"
down_revision = "0017_explicit_payment_modes"
branch_labels = None
depends_on = None

UUID = sa.Uuid(as_uuid=True).with_variant(postgresql.UUID(as_uuid=True), "postgresql")
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "organization_profiles",
        sa.Column(
            "organization_id",
            UUID,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("capabilities", JSON_TYPE, nullable=False, server_default="[]"),
        sa.Column("products", JSON_TYPE, nullable=False, server_default="[]"),
        sa.Column("regions", JSON_TYPE, nullable=False, server_default="[]"),
        sa.Column("contacts", JSON_TYPE, nullable=False, server_default="[]"),
        sa.Column("verification_status", sa.String(32), nullable=False, server_default="UNVERIFIED"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "updated_by_user_id",
            UUID,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("verification_status = 'UNVERIFIED'", name="ck_org_profile_unverified"),
        sa.CheckConstraint("version > 0", name="ck_org_profile_version_positive"),
    )


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM organization_profiles")):
        raise RuntimeError("Cannot downgrade 0018 with existing organization profiles; data loss prevented")
    op.drop_table("organization_profiles")
