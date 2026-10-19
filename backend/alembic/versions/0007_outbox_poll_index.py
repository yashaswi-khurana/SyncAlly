"""Index the outbox poll query's status, retry-time, and ordering columns.

Revision ID: 0007_outbox_poll_index
Revises: 0006_outbox_retry_schedule
"""

from alembic import op

revision = "0007_outbox_poll_index"
down_revision = "0006_outbox_retry_schedule"
branch_labels = None
depends_on = None

_INDEX_NAME = "ix_outbox_events_status_next_attempt_created"
_TABLE = "outbox_events"
_COLUMNS = ["status", "next_attempt_at", "created_at"]


def upgrade() -> None:
    context = op.get_context()
    if context.dialect.name == "postgresql":
        with context.autocommit_block():
            op.create_index(_INDEX_NAME, _TABLE, _COLUMNS, postgresql_concurrently=True)
    else:
        op.create_index(_INDEX_NAME, _TABLE, _COLUMNS)


def downgrade() -> None:
    context = op.get_context()
    if context.dialect.name == "postgresql":
        with context.autocommit_block():
            op.drop_index(_INDEX_NAME, table_name=_TABLE, postgresql_concurrently=True)
    else:
        op.drop_index(_INDEX_NAME, table_name=_TABLE)
