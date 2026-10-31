"""Add partial functional index for active organization legal name search."""

import sqlalchemy as sa

from alembic import op

revision = "0011_organization_active_legal_name_index"
down_revision = "0010_unique_provider_invoice_id"
branch_labels = None
depends_on = None

_INDEX_NAME = "ix_organizations_active_legal_name_lower"
_TABLE = "organizations"
_WHERE = "status = 'ACTIVE'"


def upgrade() -> None:
    context = op.get_context()
    if context.dialect.name == "postgresql":
        # This published revision exceeds Alembic's default VARCHAR(32). Widen
        # before concurrent DDL commits, so Alembic can stamp this unchanged ID.
        op.alter_column("alembic_version", "version_num", type_=sa.Text())
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
                [sa.func.lower(sa.column("legal_name"))],
                postgresql_ops={None: "text_pattern_ops"},
                postgresql_where=sa.text(_WHERE),
                postgresql_concurrently=True,
            )
    else:
        op.create_index(
            _INDEX_NAME,
            _TABLE,
            [sa.func.lower(sa.column("legal_name"))],
            sqlite_where=sa.text(_WHERE),
            if_not_exists=True,
        )


def downgrade() -> None:
    # Retain TEXT: Alembic replaces the current long revision only after this
    # function returns, and a wider bookkeeping column is backward compatible.
    context = op.get_context()
    if context.dialect.name == "postgresql":
        with context.autocommit_block():
            op.drop_index(
                _INDEX_NAME,
                table_name=_TABLE,
                if_exists=True,
                postgresql_concurrently=True,
            )
    else:
        op.drop_index(_INDEX_NAME, table_name=_TABLE)
