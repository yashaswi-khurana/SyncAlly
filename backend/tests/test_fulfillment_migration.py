import importlib.util
import io
import unittest
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import IntegrityError


class FulfillmentMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "alembic"
            / "versions"
            / "0020_fulfillment_events.py"
        )
        spec = importlib.util.spec_from_file_location("fulfillment_migration", migration_path)
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
            "agreement_versions",
            metadata,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("deal_id", sa.Uuid(), nullable=False),
            sa.Column("terms_hash", sa.String(64), nullable=False),
            sa.UniqueConstraint("id", "deal_id", name="uq_agreement_scope"),
            sa.ForeignKeyConstraint(["deal_id"], ["deals.id"]),
        )
        sa.Table(
            "obligations",
            metadata,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("deal_id", sa.Uuid(), nullable=False),
            sa.Column("agreement_version_id", sa.Uuid(), nullable=False),
            sa.Column("obligation_type", sa.String(32), nullable=False),
            sa.Column("owner_organization_id", sa.Uuid(), nullable=False),
            sa.Column("counterparty_organization_id", sa.Uuid(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("due_condition", sa.Text()),
            sa.Column("due_date", sa.DateTime(timezone=True)),
            sa.Column("source_terms_reference", sa.Text()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "owner_organization_id <> counterparty_organization_id",
                name="ck_obligation_distinct_parties",
            ),
            sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["agreement_version_id"], ["agreement_versions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["owner_organization_id"], ["organizations.id"]),
            sa.ForeignKeyConstraint(["counterparty_organization_id"], ["organizations.id"]),
        )
        sa.Table(
            "payment_milestones",
            metadata,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("obligation_id", sa.Uuid(), sa.ForeignKey("obligations.id")),
        )
        metadata.create_all(self.engine)

    def test_upgrade_preserves_existing_obligations_and_downgrade_blocks_recorded_history(self) -> None:
        deal_id, buyer_id, seller_id, user_id = (uuid4() for _ in range(4))
        agreement_id, obligation_id = uuid4(), uuid4()
        milestone_id = uuid4()
        self.connection.execute(sa.text("INSERT INTO deals (id) VALUES (:id)"), {"id": deal_id.hex})
        self.connection.execute(
            sa.text("INSERT INTO organizations (id) VALUES (:buyer), (:seller)"),
            {"buyer": buyer_id.hex, "seller": seller_id.hex},
        )
        self.connection.execute(sa.text("INSERT INTO users (id) VALUES (:id)"), {"id": user_id.hex})
        self.connection.execute(
            sa.text("INSERT INTO agreement_versions (id, deal_id, terms_hash) VALUES (:id, :deal, :hash)"),
            {"id": agreement_id.hex, "deal": deal_id.hex, "hash": "a" * 64},
        )
        self.connection.execute(
            sa.text(
                "INSERT INTO obligations (id, deal_id, agreement_version_id, obligation_type, "
                "owner_organization_id, counterparty_organization_id, status, source_terms_reference, "
                "created_at, updated_at) VALUES (:id, :deal, :agreement, 'DELIVERY', :seller, :buyer, "
                "'PENDING', 'shipments[0]', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "id": obligation_id.hex,
                "deal": deal_id.hex,
                "agreement": agreement_id.hex,
                "seller": seller_id.hex,
                "buyer": buyer_id.hex,
            },
        )
        self.connection.execute(
            sa.text("INSERT INTO payment_milestones (id, obligation_id) VALUES (:id, :obligation)"),
            {"id": milestone_id.hex, "obligation": obligation_id.hex},
        )
        before = self.connection.execute(
            sa.text("SELECT id, deal_id, agreement_version_id, status, source_terms_reference FROM obligations")
        ).one()

        self.migration.upgrade()

        after_rows = self.connection.execute(
            sa.text("SELECT id, deal_id, agreement_version_id, status, source_terms_reference FROM obligations")
        ).all()
        self.assertEqual(len(after_rows), 1, f"migration lost obligation history: {after_rows!r}")
        after = after_rows[0]
        self.assertEqual(tuple(after), tuple(before))
        self.assertEqual(
            self.connection.scalar(
                sa.text("SELECT obligation_id FROM payment_milestones WHERE id=:id"),
                {"id": milestone_id.hex},
            ),
            obligation_id.hex,
        )
        self.assertEqual(
            self.connection.scalar(
                sa.text("SELECT fulfillment_version FROM obligations WHERE id=:id"),
                {"id": obligation_id.hex},
            ),
            0,
        )
        event_id = uuid4()
        self.connection.execute(
            sa.text(
                "INSERT INTO fulfillment_events (id, deal_id, agreement_version_id, terms_hash, obligation_id, "
                "actor_organization_id, actor_user_id, event_type, quantity, unit, source_type, "
                "idempotency_key, request_hash, version) VALUES (:id, :deal, :agreement, :hash, :obligation, "
                ":seller, :user, 'SHIPPED', '1', 'each', 'USER_ATTESTATION', 'key', :request_hash, 1)"
            ),
            {
                "id": event_id.hex,
                "deal": deal_id.hex,
                "agreement": agreement_id.hex,
                "hash": "a" * 64,
                "obligation": obligation_id.hex,
                "seller": seller_id.hex,
                "user": user_id.hex,
                "request_hash": "b" * 64,
            },
        )
        with self.assertRaisesRegex(RuntimeError, "Cannot downgrade fulfillment state"):
            self.migration.downgrade()
        self.assertEqual(
            self.connection.scalar(sa.text("SELECT COUNT(*) FROM fulfillment_events")), 1
        )
        with self.assertRaises(IntegrityError):
            self.connection.execute(
                sa.text(
                    "INSERT INTO fulfillment_events (id, deal_id, agreement_version_id, terms_hash, obligation_id, "
                    "actor_organization_id, actor_user_id, event_type, quantity, unit, source_type, "
                    "idempotency_key, request_hash, version) VALUES (:id, :deal, :agreement, :hash, :obligation, "
                    ":seller, :user, 'CONFIRMED', '1', 'each', 'USER_ATTESTATION', 'bad', :request_hash, 2)"
                ),
                {
                    "id": uuid4().hex,
                    "deal": deal_id.hex,
                    "agreement": agreement_id.hex,
                    "hash": "c" * 64,
                    "obligation": obligation_id.hex,
                    "seller": seller_id.hex,
                    "user": user_id.hex,
                    "request_hash": "d" * 64,
                },
            )
        self.connection.execute(
            sa.text("DELETE FROM fulfillment_events WHERE id=:id"), {"id": event_id.hex}
        )
        self.connection.execute(
            sa.text("UPDATE obligations SET fulfillment_version=1 WHERE id=:id"),
            {"id": obligation_id.hex},
        )
        with self.assertRaisesRegex(RuntimeError, "Cannot downgrade fulfillment state"):
            self.migration.downgrade()
        self.connection.execute(
            sa.text("UPDATE obligations SET fulfillment_version=0 WHERE id=:id"),
            {"id": obligation_id.hex},
        )
        self.migration.downgrade()
        self.assertNotIn(
            "fulfillment_version",
            {column["name"] for column in sa.inspect(self.connection).get_columns("obligations")},
        )

    def test_postgres_upgrade_emits_additive_constraints(self) -> None:
        output = io.StringIO()
        context = MigrationContext.configure(
            dialect_name="postgresql",
            opts={"as_sql": True, "output_buffer": output},
        )
        self.migration.op = Operations(context)

        self.migration.upgrade()

        sql = output.getvalue()
        self.assertIn("ALTER TABLE obligations ADD COLUMN fulfillment_version INTEGER", sql)
        self.assertIn("ADD CONSTRAINT ck_obligation_fulfillment_version_nonnegative", sql)
        self.assertIn("ADD CONSTRAINT uq_obligation_fulfillment_scope", sql)
        self.assertIn("ADD CONSTRAINT uq_agreement_scope_hash", sql)
        self.assertIn("CREATE TABLE fulfillment_events", sql)


if __name__ == "__main__":
    unittest.main()
