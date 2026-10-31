"""Tests for payment outbox claiming, retry, and manual-action behavior."""

from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.application.payment_processing import (
    PaymentInvoiceReconciliation,
    PaymentRetryableError,
    PaymentWorkItem,
)
from syncally.domain.payments.intent import (
    PaymentIntentStatus,
    VerifiedProviderPaymentState,
    VerifiedProviderPaymentStatus,
)
from syncally.domain.shared.money import Money
from syncally.infrastructure.models import Base, OutboxEvent
from syncally.infrastructure.payment_outbox import (
    claim_next_payment_event,
    dispatch_one_payment_event,
)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class FakeRepository:
    def __init__(self, work=None, error=None) -> None:
        self.work = work
        self.error = error
        self.reconciliations = []

    def load(self, payment_intent_id):
        if self.error is not None:
            raise self.error
        return self.work

    def begin_create(self, payment_intent_id, request_payload_hash):
        raise AssertionError("A terminal fixture should not create an invoice")

    def mark_create_unknown(self, payment_intent_id):
        raise AssertionError("A terminal fixture should not mark an unknown create")

    def reconcile_create_not_found(self, payment_intent_id):
        raise AssertionError("A terminal fixture should not reconcile")

    def record_provider_created(self, payment_intent_id, provider_invoice_id):
        raise AssertionError("A terminal fixture should not save a provider invoice")

    def mark_sent(self, payment_intent_id):
        raise AssertionError("A terminal fixture should not send")

    def mark_failure(self, payment_intent_id, code, detail):
        raise AssertionError("A terminal fixture should not fail")

    def mark_manual_action(self, payment_intent_id, code, detail):
        raise AssertionError("A terminal fixture should not require manual action")

    def record_reconciliation(
        self,
        payment_intent_id,
        payment_state,
        *,
        outbox_event_id,
        webhook_event_id,
        lease_until,
    ):
        self.reconciliations.append(
            (payment_intent_id, payment_state, outbox_event_id, webhook_event_id, lease_until)
        )


class NoCallProvider:
    def find_invoice(self, lookup):
        raise AssertionError("No provider call is expected")

    def create_invoice(self, request):
        raise AssertionError("No provider call is expected")

    def send_invoice(self, provider_invoice_id, payment_intent_id):
        raise AssertionError("No provider call is expected")


class PaymentOutboxWorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = lambda: Session(self.engine)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _event(
        self,
        *,
        event_type="PAYMENT_INTENT_AUTHORIZED",
        status="PENDING",
        next_attempt_at=None,
        payload=None,
    ):
        event_id = uuid4()
        event = OutboxEvent(
            id=event_id,
            aggregate_type="payment_intent",
            aggregate_id=uuid4(),
            event_type=event_type,
            payload=payload or {"payment_intent_id": str(uuid4())},
            status=status,
            next_attempt_at=next_attempt_at,
        )
        with self.session_factory() as db:
            db.add(event)
            db.commit()
        return event_id

    def test_webhook_event_fetches_current_provider_state_and_completes(self) -> None:
        work = self._sent_work()
        webhook_id = uuid4()
        event_id = self._event(
            event_type="PAYPAL_WEBHOOK_RECONCILIATION_REQUESTED",
            payload={
                "payment_intent_id": str(work.payment_intent_id),
                "webhook_event_id": str(webhook_id),
            },
        )
        repository = FakeRepository(work=work)
        calls = []

        class ReconciliationProvider(NoCallProvider):
            def get_invoice_reconciliation(self, provider_invoice_id):
                calls.append(provider_invoice_id)
                return PaymentInvoiceReconciliation(
                    provider_invoice_id=provider_invoice_id,
                    invoice_number=work.invoice_number,
                    reference=work.reference,
                    amount=work.amount,
                    payment_state=VerifiedProviderPaymentState(
                        status=VerifiedProviderPaymentStatus.PENDING,
                        paid_amount=Money(Decimal("0.00"), "USD"),
                        provider_reference=provider_invoice_id,
                    ),
                )

        self.assertTrue(
            dispatch_one_payment_event(
                self.session_factory,
                repository,
                ReconciliationProvider(),
            )
        )

        self.assertEqual(calls, ["paypal-invoice-1"])
        self.assertEqual(len(repository.reconciliations), 1)
        self.assertEqual(repository.reconciliations[0][0], work.payment_intent_id)
        self.assertEqual(repository.reconciliations[0][2], event_id)
        self.assertEqual(repository.reconciliations[0][3], webhook_id)
        with self.session_factory() as db:
            self.assertEqual(db.get(OutboxEvent, event_id).status, "DELIVERED")

    def _sent_work(self) -> PaymentWorkItem:
        intent_id = uuid4()
        return PaymentWorkItem(
            payment_intent_id=intent_id,
            status=PaymentIntentStatus.SENT,
            amount=Money(Decimal("10.00"), "USD"),
            invoice_number="SA-test",
            reference=str(intent_id),
            provider_invoice_id="paypal-invoice-1",
            request_payload_hash=None,
            invoice_request=None,
        )

    def test_mixed_batch_resolves_each_persisted_mode_not_global_configuration(self) -> None:
        from syncally.config import settings
        from syncally.infrastructure.offline_payments import (
            OfflineDemoInvoiceProvider,
            PaymentProviderResolver,
        )
        from syncally.infrastructure.payment_outbox import dispatch_pending_payment_events

        sandbox = self._sent_work()
        offline = replace(self._sent_work(), provider="OFFLINE_DEMO", execution_mode="OFFLINE_DEMO")
        offline = replace(offline, provider_invoice_id=f"OFFLINE-{offline.payment_intent_id}")
        unresolved = replace(self._sent_work(), provider="UNKNOWN", execution_mode="LEGACY_UNRESOLVED")
        works = {work.payment_intent_id: work for work in (sandbox, offline, unresolved)}
        events = [self._event(payload={"payment_intent_id": str(work.payment_intent_id)}) for work in works.values()]
        resolutions = []

        class Repository(FakeRepository):
            def load(self, payment_intent_id):
                return works[payment_intent_id]

        class Resolver(PaymentProviderResolver):
            def resolve(self, work):
                resolutions.append(work.execution_mode)
                if work.execution_mode == "PAYPAL_SANDBOX":
                    return NoCallProvider()
                if work.execution_mode == "OFFLINE_DEMO":
                    return OfflineDemoInvoiceProvider(work)
                return super().resolve(work)

            def notifier(self, work):
                return None

        with patch.object(settings, "payment_mode", "OFFLINE_DEMO"), patch("syncally.config.PayPalSettings", side_effect=AssertionError("No remote construction")):
            self.assertEqual(dispatch_pending_payment_events(self.session_factory, Repository(), Resolver(), batch_size=3), 3)
        self.assertCountEqual(resolutions, ["PAYPAL_SANDBOX", "OFFLINE_DEMO", "LEGACY_UNRESOLVED"])
        with self.session_factory() as db:
            self.assertEqual([db.get(OutboxEvent, event).status for event in events], ["DELIVERED", "DELIVERED", "FAILED"])

    def test_completed_intent_marks_payment_outbox_delivered(self) -> None:
        event_id = self._event()
        repository = FakeRepository(work=self._sent_work())

        self.assertTrue(
            dispatch_one_payment_event(
                self.session_factory,
                repository,
                NoCallProvider(),
            )
        )

        with self.session_factory() as db:
            event = db.get(OutboxEvent, event_id)
            self.assertEqual(event.status, "DELIVERED")
            self.assertIsNotNone(event.delivered_at)
            self.assertIsNone(event.next_attempt_at)

    def test_transient_failure_schedules_durable_retry(self) -> None:
        event_id = self._event()
        now = datetime.now(UTC)
        repository = FakeRepository(
            error=PaymentRetryableError(
                "PAYPAL_TEMPORARY",
                "PayPal is temporarily unavailable; the payment will be retried.",
            )
        )

        dispatch_one_payment_event(
            self.session_factory,
            repository,
            NoCallProvider(),
            now=now,
        )

        with self.session_factory() as db:
            event = db.get(OutboxEvent, event_id)
            self.assertEqual(event.status, "PENDING")
            self.assertEqual(event.retry_count, 1)
            self.assertGreater(_utc(event.next_attempt_at), now)
            self.assertIn("temporarily unavailable", event.error_detail)

    def test_missing_intent_becomes_permanent_manual_action(self) -> None:
        event_id = self._event()
        repository = FakeRepository()

        dispatch_one_payment_event(
            self.session_factory,
            repository,
            NoCallProvider(),
        )

        with self.session_factory() as db:
            event = db.get(OutboxEvent, event_id)
            self.assertEqual(event.status, "FAILED")
            self.assertIn("no longer exists", event.error_detail)
            self.assertIsNone(event.next_attempt_at)

    def test_payment_worker_does_not_claim_temporal_events(self) -> None:
        self._event(event_type="AGREEMENT_COMMITTED")

        with self.session_factory() as db:
            self.assertIsNone(claim_next_payment_event(db))

    def test_expired_payment_worker_lease_can_be_recovered(self) -> None:
        event_id = self._event(
            status="PROCESSING",
            next_attempt_at=datetime.now(UTC) - timedelta(seconds=1),
        )

        with self.session_factory() as db:
            claimed = claim_next_payment_event(db, now=datetime.now(UTC))

        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.id, event_id)
        with self.session_factory() as db:
            event = db.get(OutboxEvent, event_id)
            self.assertEqual(event.status, "PROCESSING")
            self.assertGreater(_utc(event.next_attempt_at), datetime.now(UTC))


if __name__ == "__main__":
    unittest.main()
