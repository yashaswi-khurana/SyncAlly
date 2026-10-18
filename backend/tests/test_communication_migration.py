"""SQLite execution coverage for the communication upgrade and downgrade."""

import importlib.util
import unittest
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine, inspect


class CommunicationMigrationTests(unittest.TestCase):
    def test_upgrade_adds_source_reference_and_scope_indexes_downgrade_removes_them(self) -> None:
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "alembic"
            / "versions"
            / "0004_communication_sources_and_scope_indexes.py"
        )
        spec = importlib.util.spec_from_file_location(
            "communication_migration", migration_path
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = create_engine("sqlite+pysqlite:///:memory:")
        metadata = MetaData()
        Table(
            "conversations",
            metadata,
            Column("deal_id", Integer),
            Column("participant_organization_id", Integer),
            Column("created_at", DateTime),
        )
        Table(
            "messages",
            metadata,
            Column("conversation_id", Integer),
            Column("visibility", String),
            Column("created_at", DateTime),
        )
        Table(
            "constraints",
            metadata,
            Column("deal_id", Integer),
            Column("owner_organization_id", Integer),
            Column("kind", String),
            Column("status", String),
            Column("visibility", String),
            Column("created_at", DateTime),
        )

        try:
            with engine.begin() as connection:
                metadata.create_all(connection)
                migration.op = Operations(MigrationContext.configure(connection))
                migration.upgrade()

                upgraded = inspect(connection)
                self.assertIn(
                    "source_reference",
                    {column["name"] for column in upgraded.get_columns("messages")},
                )
                self.assertEqual(
                    {
                        "ix_conversations_deal_participant_created",
                        "ix_messages_conversation_visibility_created",
                        "ix_constraints_deal_owner_visibility_created",
                    },
                    {
                        index["name"]
                        for table in ("conversations", "messages", "constraints")
                        for index in upgraded.get_indexes(table)
                    },
                )
                self.assertEqual(
                    {
                        "ck_message_visibility",
                        "ck_constraint_kind",
                        "ck_constraint_status",
                        "ck_constraint_visibility",
                    },
                    {
                        check["name"]
                        for table in ("messages", "constraints")
                        for check in upgraded.get_check_constraints(table)
                    },
                )

                migration.downgrade()
                downgraded = inspect(connection)
                self.assertNotIn(
                    "source_reference",
                    {column["name"] for column in downgraded.get_columns("messages")},
                )
                self.assertEqual(
                    [],
                    [
                        index["name"]
                        for table in ("conversations", "messages", "constraints")
                        for index in downgraded.get_indexes(table)
                    ],
                )
                self.assertEqual(
                    [],
                    [
                        check["name"]
                        for table in ("messages", "constraints")
                        for check in downgraded.get_check_constraints(table)
                    ],
                )
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
