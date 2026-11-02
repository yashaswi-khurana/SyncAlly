"""Add capabilities and version to organization_members for granular capability-based access control."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0019_organization_permissions"
down_revision = "0018_organization_profiles"
branch_labels = None
depends_on = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column(
        "organization_members",
        sa.Column("capabilities", JSON_TYPE, nullable=False, server_default="[]"),
    )
    op.add_column(
        "organization_members",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        query = sa.text(
            "SELECT COUNT(*) FROM organization_members "
            "WHERE (capabilities IS NOT NULL AND capabilities::text != '[]') OR version > 1"
        )
    else:
        query = sa.text(
            "SELECT COUNT(*) FROM organization_members "
            "WHERE (capabilities IS NOT NULL AND capabilities != '[]') OR version > 1"
        )
    count = bind.scalar(query)
    if count:
        raise RuntimeError(
            "Cannot downgrade 0019 with existing member capabilities or version > 1; data loss prevented"
        )
    op.drop_column("organization_members", "version")
    op.drop_column("organization_members", "capabilities")
