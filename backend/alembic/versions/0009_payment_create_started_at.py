"""Track the first PayPal invoice-create request time.

Revision ID: 0009_payment_create_started_at
Revises: 0008_payment_intent_last_checked
"""

import sqlalchemy as sa

from alembic import op

revision = "0009_payment_create_started_at"
down_revision = "0008_payment_intent_last_checked"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("payment_intents")}
    if "provider_create_started_at" not in columns:
        op.add_column(
            "payment_intents",
            sa.Column("provider_create_started_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("payment_intents")}
    if "provider_create_started_at" in columns:
        op.drop_column("payment_intents", "provider_create_started_at")
