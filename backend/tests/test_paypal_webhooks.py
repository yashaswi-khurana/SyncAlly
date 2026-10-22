"""Tests for verified PayPal webhook intake and durable deduplication."""

from __future__ import annotations

import asyncio
import json
import unittest
from decimal import Decimal
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.main import app
from syncally.api.paypal_webhooks import get_paypal_webhook_configuration
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import Base, OutboxEvent, PaymentIntent, WebhookEvent


class FakeWebhookVerifier:
    def __init__(self, verified: bool) -> None:
        self.verified = verified
        self.calls = []

    def verify_webhook_signature(self, headers, event, webhook_id):
        self.calls.append((headers, event, webhook_id))
        return self.verified


class PayPalWebhookRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = lambda: Session(self.engine, expire_on_commit=False)
        self.verifier = FakeWebhookVerifier(True)
        app.dependency_overrides[get_db] = self._get_db
        app.dependency_overrides[get_paypal_webhook_configuration] = lambda: (
            self.verifier,
            "sandbox-webhook-id",
        )

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _get_db(self):
        with self.session_factory() as db:
            yield db

    def _post(self, payload: dict) -> httpx.Response:
        async def send() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                return await client.post(
                    "/webhooks/paypal/invoicing",
                    content=json.dumps(payload),
                    headers={
                        "content-type": "application/json",
                        "paypal-auth-algo": "SHA256withRSA",
                        "paypal-cert-url": "https://api-m.sandbox.paypal.com/cert",
                        "paypal-transmission-id": "transmission-1",
                        "paypal-transmission-sig": "signature",
                        "paypal-transmission-time": "2026-10-22T10:00:00Z",
                    },
                )

        return asyncio.run(send())

    def _create_intent(self, provider_invoice_id: str = "invoice-1") -> PaymentIntent:
        intent = PaymentIntent(
            id=uuid4(),
            deal_id=uuid4(),
            agreement_version_id=uuid4(),
            payment_milestone_id=uuid4(),
            seller_organization_id=uuid4(),
            payer_organization_id=uuid4(),
            authorized_by=uuid4(),
            amount=Decimal("10.00"),
            currency="USD",
            status="SENT",
            provider="PAYPAL",
            provider_invoice_id=provider_invoice_id,
            idempotency_key=str(uuid4()),
            version=1,
        )
        with self.session_factory() as db:
            db.add(intent)
            db.commit()
        return intent

    @staticmethod
    def _event(event_id: str, invoice_id: str) -> dict:
        return {
            "id": event_id,
            "event_type": "INVOICING.INVOICE.PAID",
            "resource": {"id": invoice_id, "status": "PAID"},
        }

    def test_invalid_signature_is_rejected_without_persisting_event(self) -> None:
        self.verifier.verified = False

        response = self._post(self._event("event-1", "invoice-1"))

        self.assertEqual(response.status_code, 400)
        with self.session_factory() as db:
            self.assertEqual(db.scalar(select(WebhookEvent.id)), None)
            self.assertEqual(db.scalar(select(OutboxEvent.id)), None)

    def test_verified_event_and_reconciliation_outbox_are_saved_once(self) -> None:
        intent = self._create_intent()
        event = self._event("event-1", "invoice-1")

        first = self._post(event)
        second = self._post(event)

        self.assertEqual(first.status_code, 202)
        self.assertEqual(first.json(), {"status": "accepted"})
        self.assertEqual(second.status_code, 202)
        self.assertEqual(second.json(), {"status": "duplicate"})
        self.assertEqual(len(self.verifier.calls), 2)
        self.assertEqual(self.verifier.calls[0][2], "sandbox-webhook-id")
        with self.session_factory() as db:
            webhook = db.scalar(select(WebhookEvent))
            queued = db.scalar(select(OutboxEvent))
            self.assertEqual(webhook.provider_event_id, "event-1")
            self.assertEqual(webhook.payment_intent_id, intent.id)
            self.assertEqual(queued.payload["payment_intent_id"], str(intent.id))
            self.assertEqual(queued.payload["webhook_event_id"], str(webhook.id))
            self.assertEqual(len(db.scalars(select(WebhookEvent)).all()), 1)
            self.assertEqual(len(db.scalars(select(OutboxEvent)).all()), 1)

    def test_verified_unmatched_invoice_is_recorded_without_payment_work(self) -> None:
        response = self._post(self._event("event-2", "other-invoice"))

        self.assertEqual(response.status_code, 202)
        with self.session_factory() as db:
            webhook = db.scalar(select(WebhookEvent))
            self.assertIsNone(webhook.payment_intent_id)
            self.assertTrue(webhook.processed)
            self.assertEqual(db.scalar(select(OutboxEvent.id)), None)


if __name__ == "__main__":
    unittest.main()
