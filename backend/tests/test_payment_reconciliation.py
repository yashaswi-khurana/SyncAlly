"""Tests for atomic PayPal payment reconciliation and stale-result protection."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.application.payment_processing import PaymentNeedsAction
from syncally.domain.payments.intent import (
    PaymentIntentStatus,
    VerifiedProviderPaymentState,
    VerifiedProviderPaymentStatus,
)
from syncally.domain.shared.money import Money
from syncally.infrastructure.models import (
    AuditEvent,
    Base,
    OutboxEvent,
    PaymentIntent,
    PaymentMilestone,
    WebhookEvent,
)
from syncally.infrastructure.repositories.payment_processing import (
    SqlAlchemyPaymentProcessingRepository,
)


class PaymentReconciliationRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = lambda: Session(self.engine, expire_on_commit=False)
        self.repository = SqlAlchemyPaymentProcessingRepository(self.session_factory)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _seed(
        self,
        *,
        status: PaymentIntentStatus = PaymentIntentStatus.SENT,
        reconciled_amount: Decimal | None = None,
    ) -> tuple[PaymentIntent, OutboxEvent, WebhookEvent, datetime]:
        intent_id = uuid4()
        milestone_id = uuid4()
        webhook_id = uuid4()
        event_id = uuid4()
        lease_until = datetime.now(UTC) + timedelta(minutes=5)
        milestone = PaymentMilestone(
            id=milestone_id,
            deal_id=uuid4(),
            agreement_version_id=uuid4(),
            sequence_number=1,
            payer_organization_id=uuid4(),
            amount=Decimal("10.00"),
            currency="USD",
            trigger_type="ON_APPROVAL",
            due_condition="Due on receipt",
        )
        intent = PaymentIntent(
            id=intent_id,
            deal_id=milestone.deal_id,
            agreement_version_id=milestone.agreement_version_id,
            payment_milestone_id=milestone.id,
            seller_organization_id=uuid4(),
            payer_organization_id=milestone.payer_organization_id,
            authorized_by=uuid4(),
            amount=Decimal("10.00"),
            currency="USD",
            status=status.value,
            provider="PAYPAL",
            provider_invoice_id="paypal-invoice-1",
            idempotency_key=str(uuid4()),
            reconciled_amount=reconciled_amount,
            version=3,
        )
        webhook = WebhookEvent(
            id=webhook_id,
            provider="PAYPAL",
            provider_event_id="WH-event-1",
            event_type="INVOICING.INVOICE.PAID",
            raw_payload={"id": "WH-event-1"},
            payment_intent_id=intent_id,
            processed=False,
        )
        outbox = OutboxEvent(
            id=event_id,
            aggregate_type="payment_intent",
            aggregate_id=intent_id,
            event_type="PAYPAL_WEBHOOK_RECONCILIATION_REQUESTED",
            payload={"payment_intent_id": str(intent_id), "webhook_event_id": str(webhook_id)},
            status="PROCESSING",
            retry_count=0,
            next_attempt_at=lease_until,
        )
        with self.session_factory() as db:
            db.add_all([milestone, intent, webhook, outbox])
            db.commit()
        return intent, outbox, webhook, lease_until

    def _record(
        self,
        intent: PaymentIntent,
        outbox: OutboxEvent,
        webhook: WebhookEvent,
        lease_until: datetime,
        status: VerifiedProviderPaymentStatus,
        amount: str,
    ) -> None:
        self.repository.record_reconciliation(
            intent.id,
            VerifiedProviderPaymentState(
                status=status,
                paid_amount=Money(Decimal(amount), "USD"),
                provider_reference="paypal-invoice-1",
            ),
            outbox_event_id=outbox.id,
            webhook_event_id=webhook.id,
            lease_until=lease_until,
        )

    def test_payment_audit_webhook_and_outbox_complete_atomically(self) -> None:
        intent, outbox, webhook, lease_until = self._seed()

        self._record(
            intent,
            outbox,
            webhook,
            lease_until,
            VerifiedProviderPaymentStatus.PAID,
            "10.00",
        )

        with self.session_factory() as db:
            saved_intent = db.get(PaymentIntent, intent.id)
            saved_outbox = db.get(OutboxEvent, outbox.id)
            saved_webhook = db.get(WebhookEvent, webhook.id)
            audit = db.scalar(select(AuditEvent))
            self.assertEqual(saved_intent.status, PaymentIntentStatus.PAID.value)
            self.assertEqual(saved_intent.reconciled_amount, Decimal("10.00"))
            self.assertIsNotNone(saved_intent.last_checked_at)
            self.assertIsNotNone(saved_intent.last_reconciled_at)
            self.assertEqual(saved_outbox.status, "DELIVERED")
            self.assertIsNotNone(saved_outbox.delivered_at)
            self.assertTrue(saved_webhook.processed)
            self.assertEqual(audit.event_type, "PAYMENT_STATE_RECONCILED")
            self.assertEqual(audit.payload["previous_status"], "SENT")
            self.assertEqual(audit.payload["current_status"], "PAID")

    def test_partial_payment_is_saved_as_partial_not_paid(self) -> None:
        intent, outbox, webhook, lease_until = self._seed()

        self._record(
            intent,
            outbox,
            webhook,
            lease_until,
            VerifiedProviderPaymentStatus.PARTIALLY_PAID,
            "4.00",
        )

        with self.session_factory() as db:
            saved = db.get(PaymentIntent, intent.id)
            self.assertEqual(saved.status, PaymentIntentStatus.PARTIALLY_PAID.value)
            self.assertEqual(saved.reconciled_amount, Decimal("4.00"))

    def test_pending_provider_state_does_not_mark_payment_paid(self) -> None:
        intent, outbox, webhook, lease_until = self._seed()

        self._record(
            intent,
            outbox,
            webhook,
            lease_until,
            VerifiedProviderPaymentStatus.PENDING,
            "0.00",
        )

        with self.session_factory() as db:
            saved = db.get(PaymentIntent, intent.id)
            self.assertEqual(saved.status, PaymentIntentStatus.PENDING.value)
            self.assertNotEqual(saved.status, PaymentIntentStatus.PAID.value)

    def test_unknown_provider_state_does_not_mark_payment_paid(self) -> None:
        intent, outbox, webhook, lease_until = self._seed()

        self._record(
            intent,
            outbox,
            webhook,
            lease_until,
            VerifiedProviderPaymentStatus.UNKNOWN,
            "0.00",
        )

        with self.session_factory() as db:
            saved = db.get(PaymentIntent, intent.id)
            self.assertEqual(saved.status, PaymentIntentStatus.SENT.value)

    def test_older_lower_payment_result_cannot_overwrite_progress(self) -> None:
        intent, outbox, webhook, lease_until = self._seed(
            status=PaymentIntentStatus.PARTIALLY_PAID,
            reconciled_amount=Decimal("4.00"),
        )

        with self.assertRaises(PaymentNeedsAction):
            self._record(
                intent,
                outbox,
                webhook,
                lease_until,
                VerifiedProviderPaymentStatus.PENDING,
                "0.00",
            )

        with self.session_factory() as db:
            saved = db.get(PaymentIntent, intent.id)
            self.assertEqual(saved.status, PaymentIntentStatus.PARTIALLY_PAID.value)
            self.assertEqual(saved.reconciled_amount, Decimal("4.00"))
            self.assertEqual(db.scalar(select(AuditEvent.id)), None)
            self.assertEqual(db.get(OutboxEvent, outbox.id).status, "PROCESSING")

    def test_stale_provider_observation_cannot_downgrade_paid_intent(self) -> None:
        intent, outbox, webhook, lease_until = self._seed(
            status=PaymentIntentStatus.PAID,
            reconciled_amount=Decimal("10.00"),
        )

        self._record(
            intent,
            outbox,
            webhook,
            lease_until,
            VerifiedProviderPaymentStatus.PAID,
            "10.00",
        )

        with self.session_factory() as db:
            saved = db.get(PaymentIntent, intent.id)
            self.assertEqual(saved.status, PaymentIntentStatus.PAID.value)
            self.assertEqual(saved.reconciled_amount, Decimal("10.00"))
            self.assertEqual(db.get(OutboxEvent, outbox.id).status, "DELIVERED")
            audit = db.scalar(select(AuditEvent))
            self.assertEqual(audit.payload["current_status"], "PAID")

    def test_conflicting_provider_state_cannot_replace_a_paid_intent(self) -> None:
        intent, outbox, webhook, lease_until = self._seed(
            status=PaymentIntentStatus.PAID,
            reconciled_amount=Decimal("10.00"),
        )

        with self.assertRaises(PaymentNeedsAction):
            self._record(
                intent,
                outbox,
                webhook,
                lease_until,
                VerifiedProviderPaymentStatus.PENDING,
                "0.00",
            )

        with self.session_factory() as db:
            saved = db.get(PaymentIntent, intent.id)
            self.assertEqual(saved.status, PaymentIntentStatus.PAID.value)
            self.assertEqual(saved.reconciled_amount, Decimal("10.00"))
            self.assertEqual(db.scalar(select(AuditEvent.id)), None)
            self.assertEqual(db.get(OutboxEvent, outbox.id).status, "PROCESSING")


if __name__ == "__main__":
    unittest.main()
