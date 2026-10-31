"""Tests for PostgreSQL coordination shared by demo mutations and reset."""

from __future__ import annotations

import unittest
from unittest.mock import Mock
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from syncally.infrastructure.demo_lifecycle import (
    lock_demo_deal_creation,
    lock_demo_payment_processing,
    lock_demo_reset,
    lock_outbox_dispatch,
)


def _postgres_session() -> Mock:
    db = Mock()
    db.bind.dialect.name = "postgresql"
    db.get_bind.return_value.dialect.name = "postgresql"
    return db


class DemoLifecycleLockTests(unittest.TestCase):
    def test_sqlite_lock_starts_write_transaction_without_committing(self) -> None:
        engine = create_engine("sqlite://")
        with Session(engine) as db:
            lock_demo_reset(db)
            self.assertTrue(db.connection().connection.driver_connection.in_transaction)
            db.execute(text("CREATE TABLE lock_probe (value INTEGER)"))
            db.rollback()
            self.assertEqual(
                db.scalar(text("SELECT count(*) FROM sqlite_master WHERE name = 'lock_probe'")), 0
            )
        engine.dispose()

    def test_sqlite_lock_refuses_existing_write_without_committing(self) -> None:
        engine = create_engine("sqlite://")
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE lock_probe (value INTEGER)"))
        with Session(engine) as db:
            db.execute(text("INSERT INTO lock_probe VALUES (1)"))
            with self.assertRaisesRegex(RuntimeError, "own the SQLite transaction"):
                lock_demo_reset(db)
            db.rollback()
            self.assertEqual(db.scalar(text("SELECT count(*) FROM lock_probe")), 0)
        engine.dispose()

    def test_reset_acquires_transaction_scoped_advisory_lock(self) -> None:
        db = _postgres_session()

        lock_demo_reset(db)

        statement = str(db.execute.call_args.args[0])
        self.assertIn("pg_advisory_xact_lock", statement)

    def test_outbox_claim_uses_the_same_transaction_scoped_reset_lock(self) -> None:
        reset_db, dispatch_db = _postgres_session(), _postgres_session()
        lock_demo_reset(reset_db)
        lock_outbox_dispatch(dispatch_db)
        self.assertEqual(str(reset_db.execute.call_args.args[0]), str(dispatch_db.execute.call_args.args[0]))
        self.assertEqual(reset_db.execute.call_args.args[1], dispatch_db.execute.call_args.args[1])
        dispatch_db.commit.assert_not_called()

    def test_demo_deal_creation_uses_the_reset_lock(self) -> None:
        db = _postgres_session()
        buyer_id, seller_id = uuid4(), uuid4()
        db.scalars.return_value = [buyer_id, seller_id]

        lock_demo_deal_creation(db, buyer_id, seller_id)

        self.assertIn("pg_advisory_xact_lock", str(db.execute.call_args.args[0]))

    def test_non_demo_deal_creation_does_not_take_the_reset_lock(self) -> None:
        db = _postgres_session()
        buyer_id, seller_id = uuid4(), uuid4()
        db.scalars.return_value = [buyer_id]

        lock_demo_deal_creation(db, buyer_id, seller_id)

        db.execute.assert_not_called()

    def test_payment_for_a_demo_deal_uses_the_reset_lock(self) -> None:
        db = _postgres_session()
        buyer_id, seller_id = uuid4(), uuid4()
        db.scalar.return_value = Mock(
            buyer_organization_id=buyer_id,
            seller_organization_id=seller_id,
        )
        db.scalars.return_value = [buyer_id, seller_id]

        lock_demo_payment_processing(db, uuid4())

        self.assertIn("pg_advisory_xact_lock", str(db.execute.call_args.args[0]))


if __name__ == "__main__":
    unittest.main()
