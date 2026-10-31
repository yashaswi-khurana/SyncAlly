import importlib.util
import io
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import sqlalchemy as sa
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import IntegrityError

from alembic import command


class PaymentModeMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0017_explicit_payment_modes.py"
        spec = importlib.util.spec_from_file_location("payment_mode_migration", path)
        self.migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.migration)
        self.engine = sa.create_engine("sqlite:///:memory:")
        self.connection = self.engine.connect()
        self.connection.exec_driver_sql("CREATE TABLE payment_intents (id TEXT PRIMARY KEY, provider TEXT NOT NULL, provider_invoice_id TEXT, payment_milestone_id TEXT, status TEXT, amount NUMERIC, idempotency_key TEXT UNIQUE, version INTEGER, request_payload_hash TEXT, last_reconciled_at TEXT)")
        self.connection.exec_driver_sql("CREATE UNIQUE INDEX ix_payment_intents_provider_invoice_unique ON payment_intents (provider, provider_invoice_id) WHERE provider_invoice_id IS NOT NULL")
        self.connection.exec_driver_sql("CREATE UNIQUE INDEX ix_payment_intents_one_active_per_milestone ON payment_intents (payment_milestone_id) WHERE status NOT IN ('PAID', 'FAILED', 'CANCELLED')")
        self.connection.exec_driver_sql("CREATE TABLE webhook_events (provider TEXT)")
        self.migration.op = Operations(MigrationContext.configure(self.connection))

    def tearDown(self) -> None:
        self.connection.close()
        self.engine.dispose()

    def test_populated_upgrade_preserves_history_indexes_and_legacy_evidence(self) -> None:
        for index, provider in enumerate(("PAYPAL", "UNKNOWN", "OFFLINE_DEMO")):
            self.connection.execute(sa.text("INSERT INTO payment_intents VALUES (:id,:provider,'INV2-SIM-old',:id,'PAID',10,:id,7,'hash','2026-10-31')"), {"id": str(index), "provider": provider})
        original = list(self.connection.exec_driver_sql("SELECT * FROM payment_intents ORDER BY id"))
        indexes = self._indexes()
        self.migration.upgrade()
        saved = list(self.connection.exec_driver_sql("SELECT * FROM payment_intents ORDER BY id"))
        self.assertEqual([tuple(row[:10]) for row in saved], [tuple(row) for row in original])
        self.assertEqual([row[-2:] for row in saved], [("PAYPAL_SANDBOX", "LEGACY_UNVERIFIED"), ("LEGACY_UNRESOLVED", "LEGACY_UNVERIFIED"), ("LEGACY_UNRESOLVED", "LEGACY_UNVERIFIED")])
        self.assertEqual(self._indexes(), indexes)
        with self.assertRaises(IntegrityError):
            self.connection.exec_driver_sql("UPDATE payment_intents SET provider='OFFLINE_DEMO', execution_mode='OFFLINE_DEMO' WHERE id='0'")
        self.migration.downgrade()
        self.assertEqual(list(self.connection.exec_driver_sql("SELECT * FROM payment_intents ORDER BY id")), original)

    def test_new_provenance_prevents_downgrade_and_invalid_pairs(self) -> None:
        self.migration.upgrade()
        with self.assertRaises(IntegrityError):
            self.connection.exec_driver_sql("INSERT INTO payment_intents (id,provider,execution_mode) VALUES ('bad','PAYPAL','OFFLINE_DEMO')")
        self.connection.exec_driver_sql("INSERT INTO payment_intents (id,provider,execution_mode,reconciliation_source) VALUES ('new','OFFLINE_DEMO','OFFLINE_DEMO','NONE')")
        with self.assertRaisesRegex(RuntimeError, "payment provenance"):
            self.migration.downgrade()
        self.assertIn("execution_mode", {column["name"] for column in sa.inspect(self.connection).get_columns("payment_intents")})

    def _indexes(self) -> list:
        return [(index["name"], index["column_names"], index["unique"],
                 str(index["dialect_options"].get("sqlite_where", "")))
                for index in sa.inspect(self.connection).get_indexes("payment_intents")]

    def test_postgres_additive_upgrade_sql_without_connections(self) -> None:
        root = Path(__file__).resolve().parents[1]
        output = io.StringIO()
        config = Config(str(root / "alembic.ini"), output_buffer=output)
        config.set_main_option("script_location", str(root / "alembic"))
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql+psycopg://offline.example/syncally", "APP_ENV": "test"}), patch("logging.config.fileConfig"):
            command.upgrade(config, "0016_persisted_negotiation_rounds:head", sql=True)
        for value in ("execution_mode", "LEGACY_UNVERIFIED", "payment_identity_immutable", "0017_explicit_payment_modes"):
            self.assertIn(value, output.getvalue())