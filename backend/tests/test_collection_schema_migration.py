import importlib.util
import unittest
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import IntegrityError


class CollectionSchemaMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "alembic"
            / "versions"
            / "0021_collection_schema.py"
        )
        spec = importlib.util.spec_from_file_location("collection_schema_migration", migration_path)
        assert spec is not None and spec.loader is not None
        self.migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.migration)
        self.engine = sa.create_engine("sqlite:///:memory:")
        self.connection = self.engine.connect()
        self.connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        self._create_prior_schema()
        self.migration.op = Operations(MigrationContext.configure(self.connection))

    def tearDown(self) -> None:
        self.connection.close()
        self.engine.dispose()

    def _create_prior_schema(self) -> None:
        metadata = sa.MetaData()
        sa.Table("deals", metadata, sa.Column("id", sa.Uuid(), primary_key=True))
        sa.Table("organizations", metadata, sa.Column("id", sa.Uuid(), primary_key=True))
        sa.Table("users", metadata, sa.Column("id", sa.Uuid(), primary_key=True))
        sa.Table(
            "negotiation_sessions",
            metadata,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("deal_id", sa.Uuid(), sa.ForeignKey("deals.id"), nullable=False),
        )
        sa.Table(
            "proposals",
            metadata,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("deal_id", sa.Uuid(), sa.ForeignKey("deals.id"), nullable=False),
            sa.Column("negotiation_session_id", sa.Uuid(), sa.ForeignKey("negotiation_sessions.id"), nullable=False),
            sa.Column("proposal_number", sa.Integer(), nullable=False),
            sa.Column("author_organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("terms_json", sa.JSON(), nullable=False),
            sa.Column("terms_hash", sa.String(64), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
        )
        sa.Table(
            "agreement_versions",
            metadata,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("deal_id", sa.Uuid(), sa.ForeignKey("deals.id"), nullable=False),
            sa.Column("proposal_id", sa.Uuid(), sa.ForeignKey("proposals.id"), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("canonical_terms_json", sa.JSON(), nullable=False),
            sa.Column("terms_hash", sa.String(64), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        )
        metadata.create_all(self.engine)

    def _insert_fixture(self) -> tuple[uuid4, uuid4, uuid4]:
        deal_id, org_id, user_id = uuid4(), uuid4(), uuid4()
        session_id, proposal_id, agreement_id = uuid4(), uuid4(), uuid4()
        self.connection.execute(sa.text("INSERT INTO deals (id) VALUES (:id)"), {"id": deal_id.hex})
        self.connection.execute(sa.text("INSERT INTO organizations (id) VALUES (:id)"), {"id": org_id.hex})
        self.connection.execute(sa.text("INSERT INTO users (id) VALUES (:id)"), {"id": user_id.hex})
        self.connection.execute(
            sa.text("INSERT INTO negotiation_sessions (id, deal_id) VALUES (:id, :deal)"),
            {"id": session_id.hex, "deal": deal_id.hex},
        )
        self.connection.execute(
            sa.text(
                "INSERT INTO proposals (id, deal_id, negotiation_session_id, proposal_number, "
                "author_organization_id, terms_json, terms_hash, status) "
                "VALUES (:id, :deal, :session, 1, :org, '{}', 'h1', 'DRAFT')"
            ),
            {"id": proposal_id.hex, "deal": deal_id.hex, "session": session_id.hex, "org": org_id.hex},
        )
        self.connection.execute(
            sa.text(
                "INSERT INTO agreement_versions (id, deal_id, proposal_id, version_number, "
                "canonical_terms_json, terms_hash, status, created_by) "
                "VALUES (:id, :deal, :prop, 1, '{}', 'h1', 'PENDING_APPROVAL', :user)"
            ),
            {"id": agreement_id.hex, "deal": deal_id.hex, "prop": proposal_id.hex, "user": user_id.hex},
        )
        return deal_id, proposal_id, agreement_id

    def test_upgrade_adds_schema_version_and_backfills_default(self) -> None:
        deal_id, proposal_id, agreement_id = self._insert_fixture()

        self.migration.upgrade()

        # Existing rows have schema_version = 1
        prop_ver = self.connection.scalar(
            sa.text("SELECT schema_version FROM proposals WHERE id = :id"),
            {"id": proposal_id.hex},
        )
        self.assertEqual(prop_ver, 1)

        agr_ver = self.connection.scalar(
            sa.text("SELECT schema_version FROM agreement_versions WHERE id = :id"),
            {"id": agreement_id.hex},
        )
        self.assertEqual(agr_ver, 1)

        # Trigger check constraint rejects schema_version = 3
        with self.assertRaises(IntegrityError):
            self.connection.execute(
                sa.text(
                    "UPDATE proposals SET schema_version = 3 WHERE id = :id"
                ),
                {"id": proposal_id.hex},
            )

        # Update to schema_version = 2 succeeds
        self.connection.execute(
            sa.text("UPDATE proposals SET schema_version = 2 WHERE id = :id"),
            {"id": proposal_id.hex},
        )
        self.assertEqual(
            self.connection.scalar(
                sa.text("SELECT schema_version FROM proposals WHERE id = :id"),
                {"id": proposal_id.hex},
            ),
            2,
        )

    def test_downgrade_refuses_when_v2_records_exist(self) -> None:
        deal_id, proposal_id, agreement_id = self._insert_fixture()
        self.migration.upgrade()

        # Case 1: agreement_versions has schema_version = 2
        self.connection.execute(
            sa.text("UPDATE agreement_versions SET schema_version = 2 WHERE id = :id"),
            {"id": agreement_id.hex},
        )
        with self.assertRaises(RuntimeError) as ctx:
            self.migration.downgrade()
        self.assertIn("data loss prevented", str(ctx.exception))

        # Reset agreement_version and set proposal to schema_version = 2
        self.connection.execute(
            sa.text("UPDATE agreement_versions SET schema_version = 1 WHERE id = :id"),
            {"id": agreement_id.hex},
        )
        self.connection.execute(
            sa.text("UPDATE proposals SET schema_version = 2 WHERE id = :id"),
            {"id": proposal_id.hex},
        )
        with self.assertRaises(RuntimeError) as ctx:
            self.migration.downgrade()
        self.assertIn("data loss prevented", str(ctx.exception))

    def test_downgrade_succeeds_when_only_v1_records_exist(self) -> None:
        deal_id, proposal_id, agreement_id = self._insert_fixture()
        self.migration.upgrade()

        # Both remain schema_version = 1
        self.migration.downgrade()

        # Columns should be dropped
        cols_props = [
            row[1]
            for row in self.connection.exec_driver_sql("PRAGMA table_info(proposals)").fetchall()
        ]
        self.assertNotIn("schema_version", cols_props)

        cols_agrs = [
            row[1]
            for row in self.connection.exec_driver_sql("PRAGMA table_info(agreement_versions)").fetchall()
        ]
        self.assertNotIn("schema_version", cols_agrs)
