import importlib.util
import unittest
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text


class InvitingPartyMigrationTests(unittest.TestCase):
    def test_preserves_legacy_rows_and_refuses_lossy_downgrade(self):
        path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0021_inviting_party.py"
        spec = importlib.util.spec_from_file_location("migration_0021", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE counterparty_onboardings (invitation_jti TEXT PRIMARY KEY, buyer_organization_id TEXT NOT NULL, shell_organization_id TEXT NOT NULL, CONSTRAINT ck_onboarding_distinct_parties CHECK (buyer_organization_id <> shell_organization_id))"))
            connection.execute(text("INSERT INTO counterparty_onboardings VALUES ('old', 'buyer', 'shell')"))
            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()
            row = connection.execute(text("SELECT inviting_organization_id, inviter_party FROM counterparty_onboardings")).one()
            self.assertEqual(tuple(row), ("buyer", "BUYER"))
            connection.execute(text("INSERT INTO counterparty_onboardings VALUES ('new', 'seller', 'shell2', 'SELLER')"))
            with self.assertRaises(RuntimeError):
                migration.downgrade()
            self.assertEqual(connection.execute(text("SELECT COUNT(*) FROM counterparty_onboardings")).scalar_one(), 2)
            connection.execute(text("DELETE FROM counterparty_onboardings WHERE invitation_jti='new'"))
            migration.downgrade()
            self.assertEqual(connection.execute(text("SELECT buyer_organization_id FROM counterparty_onboardings")).scalar_one(), "buyer")
        engine.dispose()
