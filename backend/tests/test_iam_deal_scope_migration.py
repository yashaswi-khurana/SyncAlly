"""Runtime coverage for the IAM deal-scope migration backfill."""

import importlib.util
import unittest
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from syncally.infrastructure.models.base import JSON_TYPE, UUID_TYPE


class IamDealScopeMigrationTests(unittest.TestCase):
    def test_upgrade_backfills_owner_and_known_legacy_permissions_without_assignments(self) -> None:
        engine = sa.create_engine("sqlite://")
        metadata = sa.MetaData()
        organizations = sa.Table(
            "organizations", metadata,
            sa.Column("id", UUID_TYPE, primary_key=True),
        )
        users = sa.Table("users", metadata, sa.Column("id", UUID_TYPE, primary_key=True))
        sa.Table("deals", metadata, sa.Column("id", UUID_TYPE, primary_key=True))
        members = sa.Table(
            "organization_members", metadata,
            sa.Column("id", UUID_TYPE, primary_key=True),
            sa.Column("organization_id", UUID_TYPE, nullable=False),
            sa.Column("user_id", UUID_TYPE, nullable=False),
            sa.Column("role", sa.String(32), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("capabilities", JSON_TYPE, nullable=False),
        )
        audit_events = sa.Table(
            "audit_events", metadata,
            sa.Column("id", UUID_TYPE, primary_key=True),
            sa.Column("aggregate_type", sa.String(64), nullable=False),
            sa.Column("event_type", sa.String(96), nullable=False),
            sa.Column("aggregate_id", UUID_TYPE, nullable=False),
            sa.Column("actor_id", UUID_TYPE, nullable=False),
            sa.Column("payload", JSON_TYPE),
            sa.Column("occurred_at", sa.DateTime(), nullable=False),
        )
        metadata.create_all(engine)

        organization_id, owner_id, admin_id, member_id = (uuid4() for _ in range(4))
        with engine.begin() as connection:
            connection.execute(organizations.insert(), {"id": organization_id})
            connection.execute(users.insert(), [{"id": user_id} for user_id in (owner_id, admin_id, member_id)])
            connection.execute(members.insert(), [
                {"id": uuid4(), "organization_id": organization_id, "user_id": owner_id,
                 "role": "ADMIN", "status": "ACTIVE", "capabilities": []},
                {"id": uuid4(), "organization_id": organization_id, "user_id": admin_id,
                 "role": "ADMIN", "status": "ACTIVE", "capabilities": ["FINANCE"]},
                {"id": uuid4(), "organization_id": organization_id, "user_id": member_id,
                 "role": "MEMBER", "status": "ACTIVE", "capabilities": ["UNKNOWN_LEGACY_CAPABILITY"]},
            ])
            connection.execute(audit_events.insert(), {
                "id": uuid4(), "aggregate_type": "organization",
                "event_type": "organization.owner_registered", "aggregate_id": organization_id,
                "actor_id": owner_id, "payload": {"user_id": str(owner_id)},
                "occurred_at": datetime.now(UTC),
            })

            spec = importlib.util.spec_from_file_location(
                "migration_0032_iam_deal_scope",
                Path(__file__).parents[1] / "alembic" / "versions" / "0032_iam_deal_scope.py",
            )
            assert spec is not None and spec.loader is not None
            migration = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration)
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()

            rows = connection.execute(sa.text(
                "SELECT user_id, role_bundles, permissions, is_owner "
                "FROM organization_members ORDER BY user_id"
            )).mappings().all()
            migrated = {UUID(str(row["user_id"])): row for row in rows}
            self.assertTrue(migrated[owner_id]["is_owner"])
            self.assertEqual(migrated[owner_id]["role_bundles"], "[]")
            self.assertEqual(migrated[admin_id]["role_bundles"], '["ORG_ADMIN"]')
            self.assertEqual(
                migrated[admin_id]["permissions"],
                '["deal.read_assigned", "payments.authorize", "payments.read"]',
            )
            self.assertEqual(migrated[member_id]["permissions"], "[]")
            self.assertEqual(connection.scalar(sa.text("SELECT COUNT(*) FROM deal_assignments")), 0)

        engine.dispose()


if __name__ == "__main__":
    unittest.main()
