"""Add password hashes for API authentication.

Revision ID: 0003_user_password_hash
Revises: 0002_refresh_tokens
"""

import sqlalchemy as sa

from alembic import op

revision = "0003_user_password_hash"
down_revision = "0002_refresh_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(256), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_hash")
