"""Migration execution and stamping coverage, with opt-in isolated PostgreSQL schemas."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

BACKEND = Path(__file__).resolve().parents[1]
PREVIOUS = "0010_unique_provider_invoice_id"
HEAD = "0011_organization_active_legal_name_index"
INDEX = "ix_organizations_active_legal_name_lower"


class OrganizationIndexMigrationTests(unittest.TestCase):
    def test_sqlite_index_still_upgrades_and_downgrades(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "organization_index_migration", BACKEND / "alembic" / "versions" / f"{HEAD}.py"
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = create_engine("sqlite+pysqlite:///:memory:")
        self.addCleanup(engine.dispose)
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE organizations (legal_name TEXT, status TEXT)"))
            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()
            migration.upgrade()
            definition = connection.execute(text(
                "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = :name"
            ), {"name": INDEX}).scalar_one()
            self.assertIn("lower(legal_name)", definition)
            self.assertIn("status = 'ACTIVE'", definition)
            migration.downgrade()
            self.assertEqual(connection.execute(text(
                "SELECT count(*) FROM sqlite_master WHERE type = 'index' AND name = :name"
            ), {"name": INDEX}).scalar_one(), 0)

    def test_offline_sql_widens_before_index_and_long_revision_stamp(self) -> None:
        environment = dict(os.environ, DATABASE_URL="postgresql+psycopg://localhost/unused")
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", f"{PREVIOUS}:head", "--sql"],
            cwd=BACKEND, env=environment, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        sql = result.stdout
        widening = sql.index("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE TEXT")
        self.assertLess(widening, sql.index("DROP INDEX CONCURRENTLY"))
        self.assertLess(widening, sql.index(f"UPDATE alembic_version SET version_num='{HEAD}'"))


@unittest.skipUnless(os.environ.get("TEST_POSTGRES_URL"), "Set TEST_POSTGRES_URL for PostgreSQL migration tests")
class OrganizationIndexPostgresMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        url = make_url(os.environ["TEST_POSTGRES_URL"])
        self.assertEqual(url.get_backend_name(), "postgresql")
        self.engine = create_engine(url)
        self.addCleanup(self.engine.dispose)
        self.schema = f"syncally_migration_{uuid4().hex}"
        with self.engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.addCleanup(self._drop_schema)
        # Every Alembic subprocess and assertion uses only this unique test schema.
        self.url = url.update_query_dict({"options": f"-csearch_path={self.schema}"})
        self.scoped_engine = create_engine(self.url)
        self.addCleanup(self.scoped_engine.dispose)

    def _drop_schema(self) -> None:
        with self.engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))

    def migrate(self, action: str, revision: str) -> None:
        environment = dict(os.environ, DATABASE_URL=self.url.render_as_string(hide_password=False))
        result = subprocess.run(
            [sys.executable, "-m", "alembic", action, revision],
            cwd=BACKEND, env=environment, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def version_column(self) -> tuple[str, int | None]:
        with self.scoped_engine.connect() as connection:
            return tuple(connection.execute(text(
                "SELECT data_type, character_maximum_length FROM information_schema.columns "
                "WHERE table_schema = :schema AND table_name = 'alembic_version' "
                "AND column_name = 'version_num'"
            ), {"schema": self.schema}).one())

    def assert_head(self) -> None:
        with self.scoped_engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one(), HEAD)
            definition = connection.execute(text(
                "SELECT indexdef FROM pg_indexes WHERE schemaname = :schema AND indexname = :name"
            ), {"schema": self.schema, "name": INDEX}).scalar_one()
            self.assertIn("lower(legal_name)", definition)
            self.assertIn("ACTIVE", definition)
        self.assertEqual(self.version_column(), ("text", None))

    def test_existing_0010_preserves_records_and_stamps_unchanged_head(self) -> None:
        self.migrate("upgrade", PREVIOUS)
        self.assertEqual(self.version_column(), ("character varying", 32))
        organization_id = uuid4()
        with self.scoped_engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO organizations (id, legal_name, country_code) VALUES (:id, 'Migration proof', 'US')"
            ), {"id": organization_id})
        self.migrate("upgrade", "head")
        self.assert_head()
        with self.scoped_engine.connect() as connection:
            self.assertEqual(connection.execute(text(
                "SELECT legal_name FROM organizations WHERE id = :id"
            ), {"id": organization_id}).scalar_one(), "Migration proof")

    def test_fresh_upgrade_downgrade_and_reupgrade(self) -> None:
        self.migrate("upgrade", "head")
        self.assert_head()
        self.migrate("downgrade", PREVIOUS)
        self.assertEqual(self.version_column(), ("text", None))
        with self.scoped_engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one(), PREVIOUS)
            self.assertIsNone(connection.execute(text("SELECT to_regclass(:name)"), {"name": INDEX}).scalar_one())
        self.migrate("upgrade", "head")
        self.assert_head()
        self.migrate("downgrade", "base")
        self.migrate("upgrade", "head")
        self.assert_head()

    def test_recovers_index_left_by_interrupted_stamp(self) -> None:
        self.migrate("upgrade", PREVIOUS)
        with self.scoped_engine.begin() as connection:
            connection.execute(text(
                f"CREATE INDEX {INDEX} ON organizations (lower(legal_name)) WHERE status = 'ACTIVE'"
            ))
        self.assertEqual(self.version_column(), ("character varying", 32))
        self.migrate("upgrade", "head")
        self.assert_head()

    def test_existing_wider_version_column_remains_compatible(self) -> None:
        self.migrate("upgrade", PREVIOUS)
        with self.scoped_engine.begin() as connection:
            connection.execute(text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)"))
        self.migrate("upgrade", "head")
        self.assert_head()
        self.migrate("downgrade", PREVIOUS)
        self.assertEqual(self.version_column(), ("text", None))


if __name__ == "__main__":
    unittest.main()
