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
    # Adding the column and (on postgres) building the index concurrently are
    # two separate transactions - autocommit_block() commits the column add
    # before the index build runs. If the index build then fails, rerunning
    # this migration must not try to re-add a column that already landed.
    existing_columns = {col["name"] for col in sa.inspect(op.get_bind()).get_columns(_TABLE)}
    if "last_checked_at" not in existing_columns:
        op.add_column("payment_intents", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))

    context = op.get_context()
    if context.dialect.name == "postgresql":
        with context.autocommit_block():
            # A prior failed CONCURRENTLY build can leave an invalid index
            # behind; IF NOT EXISTS alone would then skip rebuilding it.
            op.drop_index(
                _INDEX_NAME, table_name=_TABLE,
                if_exists=True, postgresql_concurrently=True,
            )
            op.create_index(
                _INDEX_NAME, _TABLE, ["payment_milestone_id"],
                unique=True, postgresql_where=sa.text(_WHERE), postgresql_concurrently=True,
            )
    else:
        op.create_index(
            _INDEX_NAME, _TABLE, ["payment_milestone_id"],
            unique=True, sqlite_where=sa.text(_WHERE), if_not_exists=True,
        )


def downgrade() -> None:
    context = op.get_context()
    if context.dialect.name == "postgresql":
        with context.autocommit_block():
            op.drop_index(_INDEX_NAME, table_name=_TABLE, postgresql_concurrently=True)
    else:
        op.drop_index(_INDEX_NAME, table_name=_TABLE)

    op.drop_column("payment_intents", "last_checked_at")
