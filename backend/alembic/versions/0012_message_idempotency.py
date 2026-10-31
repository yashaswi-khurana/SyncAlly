"""Atomically install nullable message retry metadata and scoped uniqueness."""

import sqlalchemy as sa

from alembic import op

revision = "0012_message_idempotency"
down_revision = "0011_organization_active_legal_name_index"
branch_labels = None
depends_on = None

_CONSTRAINT = "uq_messages_conversation_author_idempotency_key"


def upgrade() -> None:
    with op.batch_alter_table("messages") as batch:
        batch.add_column(sa.Column("idempotency_key", sa.String(128), nullable=True))
        batch.add_column(sa.Column("idempotency_fingerprint", sa.String(67), nullable=True))
        batch.create_unique_constraint(
            _CONSTRAINT, ["conversation_id", "author_user_id", "idempotency_key"]
        )


def downgrade() -> None:
    with op.batch_alter_table("messages") as batch:
        batch.drop_constraint(_CONSTRAINT, type_="unique")
        batch.drop_column("idempotency_fingerprint")
        batch.drop_column("idempotency_key")