"""The additive ownership marker must never claim or remove legacy deals."""

import importlib.util
import unittest
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from syncally.infrastructure.database import create_database_engine
from syncally.infrastructure.models import Base, Deal, DemoFixture, Organization


class DemoFixtureMigrationTests(unittest.TestCase):
    def test_upgrade_downgrade_preserve_legacy_and_enforce_unique_ownership(self) -> None:
        path = (
            Path(__file__).resolve().parents[1]
            / "alembic"
            / "versions"
            / "0013_curated_demo_fixture.py"
        )
        spec = importlib.util.spec_from_file_location("demo_fixture_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        self.assertEqual(migration.down_revision, "0012_message_idempotency")
        engine = create_database_engine("sqlite://")
        try:
            with engine.begin() as connection:
                Base.metadata.create_all(
                    connection,
                    tables=[
                        table
                        for table in Base.metadata.sorted_tables
                        if table.name != "demo_fixtures"
                    ],
                )
                from uuid import uuid4

                buyer, seller, deal = uuid4(), uuid4(), uuid4()
                connection.execute(
                    Organization.__table__.insert(),
                    [
                        {
                            "id": buyer,
                            "legal_name": "Demo Buyer Co",
                            "country_code": "US",
                            "status": "ACTIVE",
                        },
                        {
                            "id": seller,
                            "legal_name": "Demo Seller Co",
                            "country_code": "US",
                            "status": "ACTIVE",
                        },
                    ],
                )
                connection.execute(
                    Deal.__table__.insert().values(
                        id=deal, buyer_organization_id=buyer, seller_organization_id=seller
                    )
                )
                original = connection.execute(select(Deal.__table__)).all()
                migration.op = Operations(MigrationContext.configure(connection))
                migration.upgrade()
                self.assertEqual(connection.execute(select(DemoFixture.__table__)).all(), [])
                self.assertEqual(connection.execute(select(Deal.__table__)).all(), original)
                connection.execute(
                    DemoFixture.__table__.insert().values(
                        fixture_key="first",
                        fixture_version=1,
                        buyer_organization_id=buyer,
                        seller_organization_id=seller,
                        deal_id=deal,
                    )
                )
                for key, version, buyer_id, deal_id in (
                    ("second", 1, buyer, deal),
                    ("invalid-version", 0, buyer, deal),
                    ("invalid-parties", 1, seller, deal),
                    ("missing-deal", 1, buyer, uuid4()),
                ):
                    with self.subTest(key=key), connection.begin_nested():
                        with self.assertRaises(IntegrityError):
                            connection.execute(
                                DemoFixture.__table__.insert().values(
                                    fixture_key=key,
                                    fixture_version=version,
                                    buyer_organization_id=buyer_id,
                                    seller_organization_id=seller,
                                    deal_id=deal_id,
                                )
                            )
                    if key == "second":
                        connection.execute(DemoFixture.__table__.delete())
                migration.downgrade()
                self.assertNotIn("demo_fixtures", inspect(connection).get_table_names())
                self.assertEqual(connection.execute(select(Deal.__table__)).all(), original)
                self.assertEqual(len(connection.execute(select(Organization.__table__)).all()), 2)
        finally:
            engine.dispose()
