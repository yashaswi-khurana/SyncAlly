"""SQLite coverage for provider invoice identity uniqueness."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, MetaData, String, Table, create_engine, inspect
from sqlalchemy.exc import IntegrityError


class ProviderInvoiceUniqueMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "alembic"
            / "versions"
            / "0010_unique_provider_invoice_id.py"
        )
        spec = importlib.util.spec_from_file_location("provider_invoice_migration", migration_path)
        self.migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.migration)
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        self.connection = self.engine.connect()
        metadata = MetaData()
        self.payment_intents = Table(
            "payment_intents",
            metadata,
            Column("provider", String(32), nullable=False),
            Column("provider_invoice_id", String, nullable=True),
        )
        metadata.create_all(self.connection)
        self.migration.op = Operations(MigrationContext.configure(self.connection))

    def tearDown(self) -> None:
        self.connection.close()
        self.engine.dispose()

    def test_upgrade_enforces_provider_scoped_invoice_uniqueness_and_downgrades(self) -> None:
        self.migration.upgrade()
        self.migration.upgrade()

        indexes = {index["name"]: index for index in inspect(self.connection).get_indexes("payment_intents")}
        self.assertTrue(indexes["ix_payment_intents_provider_invoice_unique"]["unique"])

        self.connection.execute(
            self.payment_intents.insert(),
            [
                {"provider": "PAYPAL", "provider_invoice_id": "invoice-1"},
                {"provider": "OTHER", "provider_invoice_id": "invoice-1"},
                {"provider": "PAYPAL", "provider_invoice_id": None},
                {"provider": "PAYPAL", "provider_invoice_id": None},
            ],
        )
        with self.assertRaises(IntegrityError):
            self.connection.execute(
                self.payment_intents.insert().values(
                    provider="PAYPAL", provider_invoice_id="invoice-1"
                )
            )
        self.connection.rollback()

        self.migration.downgrade()
        self.connection.execute(
            self.payment_intents.insert().values(
                provider="PAYPAL", provider_invoice_id="invoice-1"
            )
        )

    def test_upgrade_rejects_existing_duplicate_provider_invoice_ids(self) -> None:
        self.connection.execute(
            self.payment_intents.insert(),
            [
                {"provider": "PAYPAL", "provider_invoice_id": "invoice-1"},
                {"provider": "PAYPAL", "provider_invoice_id": "invoice-1"},
            ],
        )

        with self.assertRaisesRegex(RuntimeError, "duplicate payment intents"):
            self.migration.upgrade()

        indexes = {index["name"] for index in inspect(self.connection).get_indexes("payment_intents")}
        self.assertNotIn("ix_payment_intents_provider_invoice_unique", indexes)


if __name__ == "__main__":
    unittest.main()
