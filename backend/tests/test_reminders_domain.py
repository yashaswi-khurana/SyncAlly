"""Pure domain tests for obligation reminders, UTC timing, and suppression."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

from syncally.domain.reminders.reminder import (
    DealReminder,
    ReminderScope,
    ReminderStatus,
    SuppressionReason,
    build_deduplication_key,
    ensure_utc,
)
from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import DealId, OrganizationId, UserId


class ReminderDomainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.deal_id = DealId(uuid4())
        self.org_id = OrganizationId(uuid4())
        self.user_id = UserId(uuid4())
        self.ref_id = uuid4()
        self.now = datetime(2026, 11, 7, 12, 0, 0, tzinfo=UTC)

    def test_ensure_utc_rejects_naive_datetime(self) -> None:
        naive = datetime(2026, 11, 7, 12, 0, 0)
        with self.assertRaises(InvariantViolation):
            ensure_utc(naive, "due_at")

    def test_ensure_utc_converts_other_timezones(self) -> None:
        est = timezone(timedelta(hours=-5))
        dt_est = datetime(2026, 11, 7, 7, 0, 0, tzinfo=est)
        converted = ensure_utc(dt_est, "due_at")
        self.assertEqual(converted.tzinfo, UTC)
        self.assertEqual(converted.hour, 12)

    def test_build_deduplication_key_deterministic(self) -> None:
        key1 = build_deduplication_key(self.deal_id, ReminderScope.FULFILLMENT, self.ref_id, 0)
        key2 = build_deduplication_key(self.deal_id, ReminderScope.FULFILLMENT, self.ref_id, 0)
        self.assertEqual(key1, key2)
        self.assertEqual(key1, f"{self.deal_id}:FULFILLMENT:{self.ref_id}:0")

        key_org = build_deduplication_key(
            self.deal_id,
            ReminderScope.FULFILLMENT,
            self.ref_id,
            0,
            recipient_organization_id=self.org_id,
        )
        self.assertEqual(key_org, f"{self.deal_id}:FULFILLMENT:{self.ref_id}:{self.org_id}:0")

        key_user = build_deduplication_key(
            self.deal_id,
            ReminderScope.ROUTING,
            self.ref_id,
            1,
            recipient_organization_id=self.org_id,
            recipient_user_id=self.user_id,
        )
        self.assertEqual(
            key_user, f"{self.deal_id}:ROUTING:{self.ref_id}:{self.org_id}:{self.user_id}:1"
        )

    def test_recurrence_cap_bounds(self) -> None:
        with self.assertRaises(InvariantViolation):
            DealReminder(
                id=uuid4(),
                deal_id=self.deal_id,
                scope=ReminderScope.MILESTONE,
                reference_id=self.ref_id,
                recipient_organization_id=self.org_id,
                recipient_user_id=None,
                status=ReminderStatus.SCHEDULED,
                scheduled_for=self.now,
                due_at=self.now + timedelta(days=1),
                recurrence_cap=0,
            )
        with self.assertRaises(InvariantViolation):
            DealReminder(
                id=uuid4(),
                deal_id=self.deal_id,
                scope=ReminderScope.MILESTONE,
                reference_id=self.ref_id,
                recipient_organization_id=self.org_id,
                recipient_user_id=None,
                status=ReminderStatus.SCHEDULED,
                scheduled_for=self.now,
                due_at=self.now + timedelta(days=1),
                recurrence_cap=11,
            )

    def test_is_due_evaluation(self) -> None:
        reminder = DealReminder(
            id=uuid4(),
            deal_id=self.deal_id,
            scope=ReminderScope.CASE,
            reference_id=self.ref_id,
            recipient_organization_id=self.org_id,
            recipient_user_id=None,
            status=ReminderStatus.SCHEDULED,
            scheduled_for=self.now,
            due_at=self.now + timedelta(hours=2),
        )
        self.assertFalse(reminder.is_due(self.now + timedelta(hours=1)))
        self.assertTrue(reminder.is_due(self.now + timedelta(hours=2)))
        self.assertTrue(reminder.is_due(self.now + timedelta(hours=3)))

    def test_mark_delivered(self) -> None:
        reminder = DealReminder(
            id=uuid4(),
            deal_id=self.deal_id,
            scope=ReminderScope.ROUTING,
            reference_id=self.ref_id,
            recipient_organization_id=self.org_id,
            recipient_user_id=self.user_id,
            status=ReminderStatus.SCHEDULED,
            scheduled_for=self.now,
            due_at=self.now,
        )
        delivered_time = self.now + timedelta(minutes=5)
        reminder.mark_delivered(delivered_time)

        self.assertEqual(reminder.status, ReminderStatus.DELIVERED)
        self.assertEqual(reminder.delivered_at, delivered_time)
        self.assertEqual(reminder.recurrence_count, 1)
        self.assertIsNone(reminder.next_attempt_at)
        self.assertEqual(reminder.version, 2)

    def test_mark_suppressed(self) -> None:
        reminder = DealReminder(
            id=uuid4(),
            deal_id=self.deal_id,
            scope=ReminderScope.FULFILLMENT,
            reference_id=self.ref_id,
            recipient_organization_id=self.org_id,
            recipient_user_id=None,
            status=ReminderStatus.SCHEDULED,
            scheduled_for=self.now,
            due_at=self.now + timedelta(days=1),
        )
        suppressed_time = self.now + timedelta(hours=1)
        reminder.mark_suppressed(SuppressionReason.RESOLVED, suppressed_time)

        self.assertEqual(reminder.status, ReminderStatus.SUPPRESSED)
        self.assertEqual(reminder.suppressed_at, suppressed_time)
        self.assertEqual(reminder.suppression_reason, SuppressionReason.RESOLVED)
        self.assertEqual(reminder.version, 2)

    def test_record_retry_exponential_backoff_and_limit(self) -> None:
        reminder = DealReminder(
            id=uuid4(),
            deal_id=self.deal_id,
            scope=ReminderScope.MILESTONE,
            reference_id=self.ref_id,
            recipient_organization_id=self.org_id,
            recipient_user_id=None,
            status=ReminderStatus.PENDING,
            scheduled_for=self.now,
            due_at=self.now,
        )
        # Attempt 1 -> 30s
        reminder.record_retry("network timeout", self.now)
        self.assertEqual(reminder.status, ReminderStatus.PENDING)
        self.assertEqual(reminder.retry_count, 1)
        self.assertEqual(reminder.next_attempt_at, self.now + timedelta(seconds=30))

        # Attempt 2 -> 60s
        reminder.record_retry("network timeout", self.now + timedelta(seconds=30))
        self.assertEqual(reminder.retry_count, 2)
        self.assertEqual(reminder.next_attempt_at, self.now + timedelta(seconds=30 + 60))

        # Attempts 3, 4, 5
        reminder.record_retry("network timeout", self.now)
        reminder.record_retry("network timeout", self.now)
        reminder.record_retry("network timeout", self.now)
        self.assertEqual(reminder.retry_count, 5)
        self.assertEqual(reminder.status, ReminderStatus.FAILED)
        self.assertIsNone(reminder.next_attempt_at)


if __name__ == "__main__":
    unittest.main()
