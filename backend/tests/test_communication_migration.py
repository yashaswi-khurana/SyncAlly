"""SQLite execution coverage for the communication upgrade and downgrade."""

import importlib.util
import unittest
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.exc import IntegrityError


class MessageIdempotencyMigrationTests(unittest.TestCase):
    def test_upgrade_preserves_legacy_duplicates_and_downgrade_only_removes_additions(self) -> None:
        path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0012_message_idempotency.py"
        spec = importlib.util.spec_from_file_location("message_idempotency_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        self.assertEqual(migration.revision, "0012_message_idempotency")
        self.assertEqual(migration.down_revision, "0011_organization_active_legal_name_index")
        engine = create_engine("sqlite+pysqlite:///:memory:")
        try:
            with engine.begin() as connection:
                connection.execute(text("CREATE TABLE messages (id INTEGER PRIMARY KEY, conversation_id INTEGER, author_user_id INTEGER, body TEXT)"))
                connection.execute(text("INSERT INTO messages VALUES (1, 10, 20, 'same'), (2, 10, 20, 'same')"))
                migration.op = Operations(MigrationContext.configure(connection))
                migration.upgrade()
                columns = {column["name"]: column for column in inspect(connection).get_columns("messages")}
                self.assertTrue(columns["idempotency_key"]["nullable"])
                self.assertTrue(columns["idempotency_fingerprint"]["nullable"])
                self.assertEqual(connection.execute(text("SELECT id, body, idempotency_key, idempotency_fingerprint FROM messages ORDER BY id")).fetchall(), [(1, "same", None, None), (2, "same", None, None)])
                self.assertEqual(inspect(connection).get_unique_constraints("messages")[0]["name"], "uq_messages_conversation_author_idempotency_key")
                connection.execute(text("INSERT INTO messages VALUES (3, 10, 20, 'new', 'key', 'v1:hash')"))
                with self.assertRaises(IntegrityError):
                    connection.execute(text("INSERT INTO messages VALUES (4, 10, 20, 'new', 'key', 'v1:hash')"))
                connection.execute(text("INSERT INTO messages VALUES (5, 11, 20, 'new', 'key', 'v1:hash'), (6, 10, 21, 'new', 'key', 'v1:hash')"))
                migration.downgrade()
                self.assertEqual({column["name"] for column in inspect(connection).get_columns("messages")}, {"id", "conversation_id", "author_user_id", "body"})
                self.assertEqual(connection.execute(text("SELECT count(*) FROM messages")).scalar_one(), 5)
        finally:
            engine.dispose()


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
            Column("author_user_id", Integer),
            Column("author_agent_id", String),
            Column("body", String),
            Column("visibility", String),
            Column("source_type", String),
            Column("created_at", DateTime),
        )
        Table(
            "constraints",
            metadata,
            Column("deal_id", Integer),
            Column("owner_organization_id", Integer),
            Column("field", String),
            Column("typed_value", String),
            Column("kind", String),
            Column("status", String),
            Column("visibility", String),
            Column("source_message_id", Integer),
            Column("source_span", String),
            Column("confirmed_by", Integer),
            Column("confirmed_at", DateTime),
            Column("version", Integer),
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
                        "ck_message_source_type",
                        "ck_message_source_matches_author",
                        "ck_message_body_nonempty",
                        "ck_constraint_kind",
                        "ck_constraint_status",
                        "ck_constraint_visibility",
                        "ck_constraint_fact_nonempty",
                        "ck_constraint_source_present",
                        "ck_constraint_source_span_nonempty",
                        "ck_constraint_version_nonnegative",
                        "ck_constraint_confirmation_metadata_pair",
                        "ck_constraint_confirmation_status",
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


class ConversationPartyUniquenessMigrationTests(unittest.TestCase):
    def _load_migration(self):
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "alembic"
            / "versions"
            / "0005_conversation_party_unique.py"
        )
        spec = importlib.util.spec_from_file_location(
            "conversation_party_uniqueness_migration", migration_path
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        return migration

    def _metadata(self) -> MetaData:
        metadata = MetaData()
        Table(
            "conversations",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("deal_id", Integer),
            Column("participant_organization_id", Integer),
            Column("created_at", DateTime),
        )
        Table(
            "messages",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("conversation_id", Integer),
        )
        return metadata

    def test_upgrade_deduplicates_and_enforces_one_conversation_per_party(self) -> None:
        migration = self._load_migration()
        engine = create_engine("sqlite+pysqlite:///:memory:")
        try:
            with engine.begin() as connection:
                self._metadata().create_all(connection)
                connection.execute(
                    text(
                        "INSERT INTO conversations "
                        "(id, deal_id, participant_organization_id, created_at) VALUES "
                        "(1, 10, 100, '2026-01-01 00:00:00'), "
                        "(2, 10, 100, '2026-01-02 00:00:00'), "
                        "(3, 10, 200, '2026-01-03 00:00:00')"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO messages (id, conversation_id) VALUES "
                        "(1, 1), (2, 2), (3, 3)"
                    )
                )

                migration.op = Operations(MigrationContext.configure(connection))
                migration.upgrade()

                self.assertEqual(
                    connection.execute(
                        text(
                            "SELECT id, deal_id, participant_organization_id "
                            "FROM conversations ORDER BY id"
                        )
                    ).fetchall(),
                    [(1, 10, 100), (3, 10, 200)],
                )
                self.assertEqual(
                    connection.execute(
                        text("SELECT id, conversation_id FROM messages ORDER BY id")
                    ).fetchall(),
                    [(1, 1), (2, 1), (3, 3)],
                )
                self.assertIn(
                    "uq_conversations_deal_participant",
                    {
                        constraint["name"]
                        for constraint in inspect(connection).get_unique_constraints(
                            "conversations"
                        )
                    },
                )
                with self.assertRaises(IntegrityError):
                    connection.execute(
                        text(
                            "INSERT INTO conversations "
                            "(id, deal_id, participant_organization_id, created_at) "
                            "VALUES (4, 10, 100, '2026-01-04 00:00:00')"
                        )
                    )
        finally:
            engine.dispose()

    def test_downgrade_removes_the_unique_constraint(self) -> None:
        migration = self._load_migration()
        engine = create_engine("sqlite+pysqlite:///:memory:")
        try:
            with engine.begin() as connection:
                self._metadata().create_all(connection)
                migration.op = Operations(MigrationContext.configure(connection))
                migration.upgrade()
                migration.downgrade()

                self.assertEqual(
                    [],
                    inspect(connection).get_unique_constraints("conversations"),
                )
                connection.execute(
                    text(
                        "INSERT INTO conversations "
                        "(id, deal_id, participant_organization_id, created_at) VALUES "
                        "(1, 10, 100, '2026-01-01 00:00:00'), "
                        "(2, 10, 100, '2026-01-02 00:00:00')"
                    )
                )
                self.assertEqual(
                    connection.execute(
                        text("SELECT count(*) FROM conversations")
                    ).scalar_one(),
                    2,
                )
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
