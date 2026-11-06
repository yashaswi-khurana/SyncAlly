"""Collection trade terms schema versioning with history-loss downgrade guard."""

import sqlalchemy as sa

from alembic import op

revision = "0021_collection_schema"
down_revision = "0020_fulfillment_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    sqlite = bind.dialect.name == "sqlite"

    op.add_column(
        "agreement_versions",
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "proposals",
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
    )

    if sqlite:
        op.execute(
            "CREATE TRIGGER ck_agreement_version_schema_version_insert "
            "BEFORE INSERT ON agreement_versions WHEN NEW.schema_version NOT IN (1, 2) "
            "BEGIN SELECT RAISE(ABORT, 'schema_version must be 1 or 2'); END"
        )
        op.execute(
            "CREATE TRIGGER ck_agreement_version_schema_version_update "
            "BEFORE UPDATE OF schema_version ON agreement_versions "
            "WHEN NEW.schema_version NOT IN (1, 2) "
            "BEGIN SELECT RAISE(ABORT, 'schema_version must be 1 or 2'); END"
        )
        op.execute(
            "CREATE TRIGGER ck_proposal_schema_version_insert "
            "BEFORE INSERT ON proposals WHEN NEW.schema_version NOT IN (1, 2) "
            "BEGIN SELECT RAISE(ABORT, 'schema_version must be 1 or 2'); END"
        )
        op.execute(
            "CREATE TRIGGER ck_proposal_schema_version_update "
            "BEFORE UPDATE OF schema_version ON proposals "
            "WHEN NEW.schema_version NOT IN (1, 2) "
            "BEGIN SELECT RAISE(ABORT, 'schema_version must be 1 or 2'); END"
        )
    else:
        op.create_check_constraint(
            "ck_agreement_version_schema_version",
            "agreement_versions",
            "schema_version IN (1, 2)",
        )
        op.create_check_constraint(
            "ck_proposal_schema_version",
            "proposals",
            "schema_version IN (1, 2)",
        )


def downgrade() -> None:
    bind = op.get_bind()
    v2_agreements = bind.scalar(
        sa.text("SELECT COUNT(*) FROM agreement_versions WHERE schema_version > 1")
    )
    v2_proposals = bind.scalar(
        sa.text("SELECT COUNT(*) FROM proposals WHERE schema_version > 1")
    )
    if v2_agreements or v2_proposals:
        raise RuntimeError(
            "Cannot downgrade 0021_collection_schema with schema_version > 1 records; data loss prevented"
        )

    sqlite = bind.dialect.name == "sqlite"
    if sqlite:
        version = tuple(
            int(part)
            for part in bind.exec_driver_sql("SELECT sqlite_version()").scalar().split(".")
        )
        if version < (3, 35, 0):
            raise RuntimeError("Cannot safely drop schema_version on SQLite older than 3.35")
        op.execute("DROP TRIGGER IF EXISTS ck_agreement_version_schema_version_insert")
        op.execute("DROP TRIGGER IF EXISTS ck_agreement_version_schema_version_update")
        op.execute("DROP TRIGGER IF EXISTS ck_proposal_schema_version_insert")
        op.execute("DROP TRIGGER IF EXISTS ck_proposal_schema_version_update")
    else:
        op.drop_constraint(
            "ck_agreement_version_schema_version", "agreement_versions", type_="check"
        )
        op.drop_constraint("ck_proposal_schema_version", "proposals", type_="check")

    op.drop_column("agreement_versions", "schema_version")
    op.drop_column("proposals", "schema_version")
