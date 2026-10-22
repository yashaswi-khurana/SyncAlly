"""SQLite coverage for the PayPal create timestamp migration."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, inspect


class PaymentCreateStartedMigrationTests(unittest.TestCase):
    def test_upgrade_adds_timestamp_and_downgrade_removes_it(self) -> None:
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "alembic"
            / "versions"
            / "0009_payment_create_started_at.py"
        )
        spec = importlib.util.spec_from_file_location("payment_create_migration", migration_path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = create_engine("sqlite+pysqlite:///:memory:")
        metadata = MetaData()
        Table(
            "payment_intents",
            metadata,
            Column("id", Integer, primary_key=True),
        )

        try:
            with engine.begin() as connection:
                metadata.create_all(connection)
                migration.op = Operations(MigrationContext.configure(connection))
                migration.upgrade()
                migration.upgrade()

                self.assertIn(
                    "provider_create_started_at",
                    {column["name"] for column in inspect(connection).get_columns("payment_intents")},
                )

                migration.downgrade()
                self.assertNotIn(
                    "provider_create_started_at",
                    {column["name"] for column in inspect(connection).get_columns("payment_intents")},
                )
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
