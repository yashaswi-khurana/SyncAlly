"""Payment milestone and intent explicit collection references with history-loss downgrade guard."""

import sqlalchemy as sa
from alembic import op

revision = "0022_milestone_payments"
down_revision = "0021_collection_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payment_milestones",
        sa.Column("source_terms_reference", sa.String(64), nullable=True),
    )
    op.add_column(
        "payment_intents",
        sa.Column("source_terms_reference", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    referenced_milestones = bind.scalar(
        sa.text("SELECT COUNT(*) FROM payment_milestones WHERE source_terms_reference IS NOT NULL")
    )
    referenced_intents = bind.scalar(
        sa.text("SELECT COUNT(*) FROM payment_intents WHERE source_terms_reference IS NOT NULL")
    )
    if referenced_milestones or referenced_intents:
        raise RuntimeError(
            "Cannot downgrade 0022_milestone_payments with milestone references; data loss prevented"
        )

    sqlite = bind.dialect.name == "sqlite"
    if sqlite:
        version = tuple(
            int(part)
            for part in bind.exec_driver_sql("SELECT sqlite_version()").scalar().split(".")
        )
        if version < (3, 35, 0):
            raise RuntimeError("Cannot safely drop columns on SQLite older than 3.35")

    op.drop_column("payment_intents", "source_terms_reference")
    op.drop_column("payment_milestones", "source_terms_reference")
