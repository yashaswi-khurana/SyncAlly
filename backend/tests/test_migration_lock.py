"""Tests for PostgreSQL migration serialization and advisory lock coordination."""

from __future__ import annotations

import os
import threading
import time
import unittest
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from syncally.infrastructure.migration_config import (
    MIGRATION_ADVISORY_LOCK_ID,
    serialize_migrations,
)


def _make_postgres_connection() -> MagicMock:
    conn = MagicMock()
    conn.dialect.name = "postgresql"
    conn.closed = False
    conn.in_transaction.return_value = False
    return conn


def _make_sqlite_connection() -> MagicMock:
    conn = MagicMock()
    conn.dialect.name = "sqlite"
    conn.closed = False
    conn.in_transaction.return_value = False
    return conn


class MigrationLockTests(unittest.TestCase):
    def test_postgresql_acquires_and_releases_session_advisory_lock(self) -> None:
        conn = _make_postgres_connection()

        with serialize_migrations(conn):
            # Inside the block, the lock statement has executed
            self.assertEqual(conn.execute.call_count, 1)
            acquire_stmt = str(conn.execute.call_args_list[0][0][0])
            acquire_params = conn.execute.call_args_list[0][0][1]
            self.assertIn("pg_advisory_lock", acquire_stmt)
            self.assertEqual(acquire_params, {"lock_id": MIGRATION_ADVISORY_LOCK_ID})

        # Exiting the block triggers unlock
        self.assertEqual(conn.execute.call_count, 2)
        unlock_stmt = str(conn.execute.call_args_list[1][0][0])
        unlock_params = conn.execute.call_args_list[1][0][1]
        self.assertIn("pg_advisory_unlock", unlock_stmt)
        self.assertEqual(unlock_params, {"lock_id": MIGRATION_ADVISORY_LOCK_ID})

    def test_non_postgresql_dialect_bypasses_advisory_locking(self) -> None:
        conn = _make_sqlite_connection()

        with serialize_migrations(conn):
            pass

        conn.execute.assert_not_called()

    def test_autobegin_transaction_is_committed_to_prevent_external_transaction_leak(self) -> None:
        conn = _make_postgres_connection()
        conn.in_transaction.return_value = True

        with serialize_migrations(conn):
            # lock query autobegan a transaction; commit must be called before yielding to Alembic
            self.assertEqual(conn.commit.call_count, 1)

        # unlock query autobegan a transaction; commit must be called again on exit
        self.assertEqual(conn.commit.call_count, 2)

    def test_migration_error_rolls_back_active_transaction_and_releases_lock(self) -> None:
        conn = _make_postgres_connection()
        # When entering context, transaction is not active; when error occurs, transaction is active
        conn.in_transaction.side_effect = [False, True, False]

        with self.assertRaises(RuntimeError) as ctx:
            with serialize_migrations(conn):
                raise RuntimeError("migration DDL failed")

        self.assertEqual(str(ctx.exception), "migration DDL failed")
        conn.rollback.assert_called_once()
        self.assertEqual(conn.execute.call_count, 2)
        unlock_stmt = str(conn.execute.call_args_list[1][0][0])
        self.assertIn("pg_advisory_unlock", unlock_stmt)

    def test_unlock_failure_does_not_mask_primary_migration_exception(self) -> None:
        conn = _make_postgres_connection()
        # First call (lock) succeeds, second call (unlock) fails with an exception
        conn.execute.side_effect = [None, RuntimeError("unlock connection severed")]

        with self.assertRaises(ValueError) as ctx:
            with serialize_migrations(conn):
                raise ValueError("root migration error")

        # The root migration error must be raised, not masked by the unlock failure
        self.assertEqual(str(ctx.exception), "root migration error")

    def test_closed_connection_skips_rollback_and_unlock(self) -> None:
        conn = _make_postgres_connection()

        with serialize_migrations(conn):
            conn.closed = True

        # Only the acquire call should have occurred
        self.assertEqual(conn.execute.call_count, 1)
        conn.rollback.assert_not_called()

    def test_lock_id_is_valid_signed_64bit_integer(self) -> None:
        # PostgreSQL bigint range: -2^63 to 2^63 - 1
        min_bigint = -(2**63)
        max_bigint = 2**63 - 1
        self.assertGreaterEqual(MIGRATION_ADVISORY_LOCK_ID, min_bigint)
        self.assertLessEqual(MIGRATION_ADVISORY_LOCK_ID, max_bigint)
        # Expected 'SYNCALEM' in ASCII hex
        self.assertEqual(MIGRATION_ADVISORY_LOCK_ID, 0x53594E43414C454D)

    def test_concurrent_threads_are_serialized_by_lock(self) -> None:
        """Adversarial concurrency test: simulated database lock forces sequential execution."""
        db_mutex = threading.Lock()
        active_migrations = 0
        max_concurrent = 0
        execution_order: list[str] = []

        def simulated_migration(thread_name: str) -> None:
            nonlocal active_migrations, max_concurrent
            conn = _make_postgres_connection()

            def execute_mock(stmt, params=None):  # noqa: ANN001
                nonlocal active_migrations, max_concurrent
                sql = str(stmt)
                if "pg_advisory_lock" in sql:
                    db_mutex.acquire()
                    active_migrations += 1
                    if active_migrations > max_concurrent:
                        max_concurrent = active_migrations
                elif "pg_advisory_unlock" in sql:
                    active_migrations -= 1
                    db_mutex.release()

            conn.execute.side_effect = execute_mock

            with serialize_migrations(conn):
                execution_order.append(f"{thread_name}-start")
                time.sleep(0.01)
                execution_order.append(f"{thread_name}-end")

        t1 = threading.Thread(target=simulated_migration, args=("T1",))
        t2 = threading.Thread(target=simulated_migration, args=("T2",))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Mutual exclusion: at no point were 2 threads actively executing within the lock
        self.assertEqual(max_concurrent, 1)
        # One thread must completely finish before the other starts
        self.assertTrue(
            (execution_order == ["T1-start", "T1-end", "T2-start", "T2-end"])
            or (execution_order == ["T2-start", "T2-end", "T1-start", "T1-end"])
        )


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Set TEST_POSTGRES_URL for PostgreSQL migration tests"
)
class PostgresRealAdvisoryLockTests(unittest.TestCase):
    def setUp(self) -> None:
        url = make_url(os.environ["TEST_POSTGRES_URL"])
        self.assertEqual(url.get_backend_name(), "postgresql")
        self.engine = create_engine(url)
        self.addCleanup(self.engine.dispose)

    def test_real_postgres_session_advisory_lock_mutual_exclusion(self) -> None:
        active = 0
        max_active = 0
        barrier = threading.Barrier(2)

        def worker() -> None:
            nonlocal active, max_active
            with self.engine.connect() as conn:
                barrier.wait()
                with serialize_migrations(conn):
                    active += 1
                    if active > max_active:
                        max_active = active
                    time.sleep(0.05)
                    active -= 1

        w1 = threading.Thread(target=worker)
        w2 = threading.Thread(target=worker)
        w1.start()
        w2.start()
        w1.join()
        w2.join()

        self.assertEqual(max_active, 1)


if __name__ == "__main__":
    unittest.main()
