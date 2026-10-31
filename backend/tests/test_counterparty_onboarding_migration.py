import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url

from alembic import command
from syncally.infrastructure.database import create_database_engine
from syncally.infrastructure.models import Base, CounterpartyOnboarding, Deal, Organization, User


class CounterpartyOnboardingMigrationTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("TEST_POSTGRES_URL"), "Set TEST_POSTGRES_URL for isolated F4 migration execution")
    def test_postgres_fresh_upgrade_and_empty_downgrade(self) -> None:
        root = Path(__file__).resolve().parents[1]
        engine = create_engine(os.environ["TEST_POSTGRES_URL"], hide_parameters=True)
        schema = f"onboarding_migration_{uuid4().hex}"
        try:
            with engine.begin() as connection:
                connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            url = make_url(os.environ["TEST_POSTGRES_URL"]).update_query_dict({"options": f"-csearch_path={schema}"}).render_as_string(hide_password=False)
            with (
                patch.dict(os.environ, {"DATABASE_URL": url, "APP_ENV": "test"}),
                patch("logging.config.fileConfig"),
            ):
                config = Config(str(root / "alembic.ini"))
                config.set_main_option("script_location", str(root / "alembic"))
                command.upgrade(config, "head")
                with engine.connect() as connection:
                    self.assertIn("counterparty_onboardings", inspect(connection).get_table_names(schema=schema))
                command.downgrade(config, "0014_outbox_dispatch_started_at")
                with engine.connect() as connection:
                    self.assertNotIn("counterparty_onboardings", inspect(connection).get_table_names(schema=schema))
        finally:
            with engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            engine.dispose()

    def test_populated_upgrade_preserves_legacy_and_refuses_history_loss(self) -> None:
        path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0015_counterparty_onboarding.py"
        spec = importlib.util.spec_from_file_location("counterparty_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        self.assertEqual(migration.down_revision, "0014_outbox_dispatch_started_at")
        engine = create_database_engine("sqlite://")
        try:
            with engine.begin() as connection:
                Base.metadata.create_all(connection, tables=[table for table in Base.metadata.sorted_tables if table.name != "counterparty_onboardings"])
                buyer, seller, deal, user = uuid4(), uuid4(), uuid4(), uuid4()
                connection.execute(Organization.__table__.insert(), [{"id": buyer, "legal_name": "Legacy buyer", "country_code": "US"}, {"id": seller, "legal_name": "Legacy seller", "country_code": "JP"}])
                connection.execute(User.__table__.insert().values(id=user, email="buyer@example.com", display_name="Buyer", status="ACTIVE"))
                connection.execute(Deal.__table__.insert().values(id=deal, buyer_organization_id=buyer, seller_organization_id=seller))
                original = connection.execute(select(Deal.__table__)).all()
                migration.op = Operations(MigrationContext.configure(connection))
                migration.upgrade()
                self.assertEqual(connection.execute(select(CounterpartyOnboarding.__table__)).all(), [])
                self.assertEqual(connection.execute(select(Deal.__table__)).all(), original)
                migration.downgrade()
                self.assertNotIn("counterparty_onboardings", inspect(connection).get_table_names())
                migration.upgrade()
                from datetime import UTC, datetime
                connection.execute(CounterpartyOnboarding.__table__.insert().values(invitation_jti=uuid4(), deal_id=deal, buyer_organization_id=buyer, shell_organization_id=seller, inviter_user_id=user, recipient_email="seller@example.com", expires_at=datetime.now(UTC)))
                with self.assertRaisesRegex(RuntimeError, "onboarding history"):
                    migration.downgrade()
                self.assertEqual(connection.execute(select(Deal.__table__)).all(), original)
                self.assertEqual(len(connection.execute(select(CounterpartyOnboarding.__table__)).all()), 1)
        finally:
            engine.dispose()

    def test_postgres_upgrade_sql_0014_to_0015(self) -> None:
        import io
        import os
        from unittest.mock import patch
        root = Path(__file__).resolve().parents[1]
        output = io.StringIO()
        with (
            patch.dict(os.environ, {"DATABASE_URL": "postgresql+psycopg://offline.example/syncally", "APP_ENV": "test"}),
            patch("logging.config.fileConfig"),
        ):
            config = Config(str(root / "alembic.ini"), output_buffer=output)
            config.set_main_option("script_location", str(root / "alembic"))
            command.upgrade(config, "0014_outbox_dispatch_started_at:head", sql=True)
        self.assertIn("CREATE TABLE counterparty_onboardings", output.getvalue())
        self.assertIn("0015_counterparty_onboarding", output.getvalue())