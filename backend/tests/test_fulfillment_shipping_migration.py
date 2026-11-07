"""Shipping detail migration preserves older fulfillment records."""

import importlib.util
import unittest
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


class FulfillmentShippingMigrationTests(unittest.TestCase):
    def test_upgrade_keeps_history_and_new_fields_are_nullable(self) -> None:
        path = (
            Path(__file__).resolve().parents[1]
            / "alembic"
            / "versions"
            / "0028_fulfillment_shipping_details.py"
        )
        spec = importlib.util.spec_from_file_location("fulfillment_shipping_migration", path)
        assert spec is not None and spec.loader is not None
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)

        engine = sa.create_engine("sqlite:///:memory:")
        with engine.begin() as connection:
            metadata = sa.MetaData()
            events = sa.Table(
                "fulfillment_events",
                metadata,
                sa.Column("id", sa.Uuid(), primary_key=True),
                sa.Column("event_type", sa.String(16), nullable=False),
                sa.Column("quantity", sa.Text(), nullable=False),
            )
            metadata.create_all(connection)
            event_id = uuid4()
            connection.execute(
                events.insert().values(id=event_id, event_type="SHIPPED", quantity="2")
            )
            migration.op = Operations(MigrationContext.configure(connection))

            migration.upgrade()

            row = connection.execute(
                sa.text(
                    "SELECT event_type, quantity, carrier, tracking_number, dispatch_date, expected_delivery_date "
                    "FROM fulfillment_events WHERE id = :id"
                ),
                {"id": event_id.hex},
            ).one()
            self.assertEqual(tuple(row), ("SHIPPED", "2", None, None, None, None))

            migration.downgrade()
            columns = {
                column["name"]
                for column in sa.inspect(connection).get_columns("fulfillment_events")
            }
            self.assertEqual(columns, {"id", "event_type", "quantity"})
        engine.dispose()
