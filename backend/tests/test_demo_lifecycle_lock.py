"""Tests for PostgreSQL coordination shared by demo mutations and reset."""

from __future__ import annotations

import unittest
from unittest.mock import Mock
from uuid import uuid4

from syncally.infrastructure.demo_lifecycle import (
    lock_demo_deal_creation,
    lock_demo_payment_processing,
    lock_demo_reset,
)


def _postgres_session() -> Mock:
    db = Mock()
    db.bind.dialect.name = "postgresql"
    return db


class DemoLifecycleLockTests(unittest.TestCase):
    def test_reset_acquires_transaction_scoped_advisory_lock(self) -> None:
        db = _postgres_session()

        lock_demo_reset(db)

        statement = str(db.execute.call_args.args[0])
        self.assertIn("pg_advisory_xact_lock", statement)

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
