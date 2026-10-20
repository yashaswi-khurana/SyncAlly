"""Add payment intent last-checked time and the one-active-per-milestone index.

Revision ID: 0008_payment_intent_last_checked
Revises: 0007_outbox_poll_index
"""

import sqlalchemy as sa

from alembic import op

revision = "0008_payment_intent_last_checked"
down_revision = "0007_outbox_poll_index"
branch_labels = None
depends_on = None

_INDEX_NAME = "ix_payment_intents_one_active_per_milestone"
_TABLE = "payment_intents"
_WHERE = "status NOT IN ('PAID', 'FAILED', 'CANCELLED')"


def upgrade() -> None:
    op.add_column("payment_intents", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))

    context = op.get_context()
    if context.dialect.name == "postgresql":
        with context.autocommit_block():
            op.create_index(
                _INDEX_NAME, _TABLE, ["payment_milestone_id"],
                unique=True, postgresql_where=sa.text(_WHERE), postgresql_concurrently=True,
            )
    else:
        op.create_index(
            _INDEX_NAME, _TABLE, ["payment_milestone_id"], unique=True, sqlite_where=sa.text(_WHERE)
        )


def downgrade() -> None:
    context = op.get_context()
    if context.dialect.name == "postgresql":
        with context.autocommit_block():
            op.drop_index(_INDEX_NAME, table_name=_TABLE, postgresql_concurrently=True)
    else:
        op.drop_index(_INDEX_NAME, table_name=_TABLE)

    op.drop_column("payment_intents", "last_checked_at")
