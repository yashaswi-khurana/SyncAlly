"""Add the platform-level system administrator role.

Revision ID: 0025_system_admin
Revises: 0024_amendments
Create Date: 2026-11-07
"""

import sqlalchemy as sa

from alembic import op

revision = "0025_system_admin"
down_revision = "0024_amendments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("system_role", sa.String(length=32), nullable=False, server_default="USER"),
    )


def downgrade() -> None:
    op.drop_column("users", "system_role")
