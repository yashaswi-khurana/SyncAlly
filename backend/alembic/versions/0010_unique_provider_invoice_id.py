"""Enforce one local payment intent per provider invoice."""

import sqlalchemy as sa

from alembic import op

revision = "0010_unique_provider_invoice_id"
down_revision = "0009_payment_create_started_at"
branch_labels = None
depends_on = None

_INDEX_NAME = "ix_payment_intents_provider_invoice_unique"
_TABLE = "payment_intents"
_WHERE = "provider_invoice_id IS NOT NULL"


def upgrade() -> None:
    duplicate = op.get_bind().execute(
        sa.text(
            """SELECT provider, provider_invoice_id
            FROM payment_intents
            WHERE provider_invoice_id IS NOT NULL
            GROUP BY provider, provider_invoice_id
            HAVING COUNT(*) > 1
            LIMIT 1"""
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot enforce provider invoice uniqueness while duplicate payment intents exist."
        )

    context = op.get_context()
    if context.dialect.name == "postgresql":
        with context.autocommit_block():
            op.drop_index(
                _INDEX_NAME,
                table_name=_TABLE,
                if_exists=True,
                postgresql_concurrently=True,
            )
            op.create_index(
                _INDEX_NAME,
                _TABLE,
                ["provider", "provider_invoice_id"],
                unique=True,
                postgresql_where=sa.text(_WHERE),
                postgresql_concurrently=True,
            )
    else:
        op.create_index(
            _INDEX_NAME,
            _TABLE,
            ["provider", "provider_invoice_id"],
            unique=True,
            sqlite_where=sa.text(_WHERE),
            if_not_exists=True,
        )


def downgrade() -> None:
    context = op.get_context()
    if context.dialect.name == "postgresql":
        with context.autocommit_block():
            op.drop_index(
                _INDEX_NAME,
                table_name=_TABLE,
                postgresql_concurrently=True,
            )
    else:
        op.drop_index(_INDEX_NAME, table_name=_TABLE)
