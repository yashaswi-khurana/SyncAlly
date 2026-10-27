"""Credential-free API-to-payment-worker proof for the first demo lifecycle."""

from __future__ import annotations

import asyncio
import json
import unittest
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID

import httpx
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.auth import get_current_actor
from syncally.api.conversations import get_ai_suggestion_provider
from syncally.api.main import app
from syncally.api.paypal_webhooks import get_paypal_webhook_configuration
from syncally.application.identity import ActorContext
from syncally.application.payment_processing import (
    PaymentInvoiceReconciliation,
    PaymentOutcomeUnknown,
)
from syncally.application.payments import (
    PAYMENT_INTENT_AUTHORIZED_EVENT_TYPE,
    PAYPAL_WEBHOOK_RECONCILIATION_EVENT_TYPE,
)
from syncally.domain.ai.contracts import ProposedTerms
from syncally.domain.payments.intent import (
    VerifiedProviderPaymentState,
    VerifiedProviderPaymentStatus,
)
from syncally.infrastructure.ai.fake import DeterministicFakeAIProvider
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import (
    AgreementVersion,
    AuditEvent,
    Base,
    Obligation,
    Organization,
    OrganizationMember,
    OutboxEvent,
    PaymentIntent,
    Proposal,
    User,
    WebhookEvent,
)
from syncally.infrastructure.payment_outbox import dispatch_one_payment_event
from syncally.infrastructure.repositories.payment_processing import (
    SqlAlchemyPaymentProcessingRepository,
)


class FakeWebhookVerifier:
    def verify_webhook_signature(self, headers, event, webhook_id):
        return webhook_id == "fake-webhook"


class FakePayPalInvoiceProvider:
    """Retain a created invoice across a simulated worker restart."""

    def __init__(self) -> None:
        self.invoice_id = "sandbox-invoice-1"
        self.request = None
        self.create_calls = 0
        self.send_calls = 0
        self.find_calls = 0
        self.send_completed = False

    def find_invoice(self, lookup):
        self.find_calls += 1
        if self.request is not None and lookup.invoice_number == self.request.invoice_number:
            return self.invoice_id
        return None

    def get_invoice_status(self, provider_invoice_id):
        self.assert_invoice(provider_invoice_id)
        return "SENT" if self.send_completed else "DRAFT"

    def create_invoice(self, request):
        self.create_calls += 1
        self.request = request
        # The provider has created the invoice, but the worker loses the response.
        raise PaymentOutcomeUnknown("PAYPAL_TIMEOUT", "Fake timeout after create")

    def send_invoice(self, provider_invoice_id, payment_intent_id):
        self.assert_invoice(provider_invoice_id)
        self.send_calls += 1
        self.send_completed = True

    def get_invoice_reconciliation(self, provider_invoice_id):
        self.assert_invoice(provider_invoice_id)
        assert self.request is not None
        return PaymentInvoiceReconciliation(
            provider_invoice_id=self.invoice_id,
            invoice_number=self.request.invoice_number,
            reference=self.request.reference,
            amount=self.request.amount,
            payment_state=VerifiedProviderPaymentState(
                status=VerifiedProviderPaymentStatus.PAID,
                paid_amount=self.request.amount,
                provider_reference=self.invoice_id,
            ),
        )

    def assert_invoice(self, provider_invoice_id: str) -> None:
        if provider_invoice_id != self.invoice_id:
            raise AssertionError("Unexpected fake invoice ID")


class DemoLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine, expire_on_commit=False)
        self.session_factory = lambda: Session(self.engine, expire_on_commit=False)
        self.buyer_user = User(email="buyer@example.test", display_name="Buyer")
        self.seller_user = User(email="seller@example.test", display_name="Seller")
        self.outsider_user = User(email="outsider@example.test", display_name="Outsider")
        self.buyer = Organization(legal_name="Buyer Co", country_code="US")
        self.seller = Organization(legal_name="Seller Co", country_code="CA")
        self.outsider = Organization(legal_name="Other Co", country_code="GB")
        self.session.add_all(
            [
                self.buyer_user,
                self.seller_user,
                self.outsider_user,
                self.buyer,
                self.seller,
                self.outsider,
            ]
        )
        self.session.flush()
        self.session.add_all(
            [
                OrganizationMember(
                    user_id=self.buyer_user.id,
                    organization_id=self.buyer.id,
                    role="ADMIN",
                    status="ACTIVE",
                ),
                OrganizationMember(
                    user_id=self.seller_user.id,
                    organization_id=self.seller.id,
                    role="ADMIN",
                    status="ACTIVE",
                ),
                OrganizationMember(
                    user_id=self.outsider_user.id,
                    organization_id=self.outsider.id,
                    role="ADMIN",
                    status="ACTIVE",
                ),
            ]
        )
        self.session.commit()

        self.actor = [ActorContext(self.buyer_user.id, frozenset({self.buyer.id}))]
        self.ai = DeterministicFakeAIProvider(
            proposal=ProposedTerms(
                schema_version=1,
                description="Steel bolts",
                quantity=Decimal("10"),
                unit="box",
                unit_price=Decimal("25.00"),
                currency="USD",
                delivery_destination="Toronto",
                delivery_date=date(2026, 12, 1),
            )
        )
        self.paypal = FakePayPalInvoiceProvider()
        app.dependency_overrides[get_db] = lambda: self.session
        app.dependency_overrides[get_current_actor] = lambda: self.actor[0]
        app.dependency_overrides[get_ai_suggestion_provider] = lambda: self.ai
        app.dependency_overrides[get_paypal_webhook_configuration] = lambda: (
            FakeWebhookVerifier(),
            "fake-webhook",
        )
        self.session_local_patch = patch(
            "syncally.api.paypal_webhooks.SessionLocal", self.session_factory
        )
        self.session_local_patch.start()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.session_local_patch.stop()
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_api_to_payment_worker_lifecycle_is_private_and_idempotent(self) -> None:
        deal_response = self._request(
            "POST",
            "/deals",
            json={
                "buyer_organization_id": str(self.buyer.id),
                "seller_organization_id": str(self.seller.id),
            },
        )
        self.assertEqual(deal_response.status_code, 201, deal_response.text)
        deal_id = deal_response.json()["id"]

        buyer_message = self._request(
            "POST",
            f"/deals/{deal_id}/messages",
            json={
                "body": "Steel bolts, 10 boxes, deliver to Toronto. Buyer private reserve is 900 USD.",
                "visibility": "PRIVATE",
            },
        )
        self.assertEqual(buyer_message.status_code, 201, buyer_message.text)
        buyer_message_id = buyer_message.json()["id"]

        self.actor[0] = ActorContext(self.seller_user.id, frozenset({self.seller.id}))
        seller_message = self._request(
            "POST",
            f"/deals/{deal_id}/messages",
            json={"body": "Seller private floor is 20 USD per box.", "visibility": "PRIVATE"},
        )
        self.assertEqual(seller_message.status_code, 201, seller_message.text)
        self.assertNotIn("900 USD", self._request("GET", f"/deals/{deal_id}/messages").text)

        self.actor[0] = ActorContext(self.buyer_user.id, frozenset({self.buyer.id}))
        proposal_response = self._request(
            "POST",
            f"/deals/{deal_id}/ai/proposal",
            json={"organization_id": str(self.buyer.id)},
        )
        self.assertEqual(proposal_response.status_code, 200, proposal_response.text)
        ai_context = self.ai.last_request.context
        ai_message_bodies = {message.body for message in ai_context.messages}
        self.assertTrue(any("900 USD" in body for body in ai_message_bodies))
        self.assertFalse(any("20 USD" in body for body in ai_message_bodies))

        invalid_terms = {
            key: value
            for key, value in proposal_response.json().items()
            if key != "status"
        }
        invalid_terms["quantity"] = "-1"
        invalid_terms["payment_trigger"] = "seller_invoice"
        invalid_terms["organization_id"] = str(self.buyer.id)
        invalid_response = self._request(
            "POST",
            f"/deals/{deal_id}/agreements/from-reviewed-terms",
            json=invalid_terms,
        )
        self.assertEqual(invalid_response.status_code, 422, invalid_response.text)
        self.assertIn("quantity must be positive", invalid_response.json()["detail"])

        agreement_response = self._request(
            "POST",
            f"/deals/{deal_id}/agreements/from-reviewed-terms",
            json={
                **{
                    key: value
                    for key, value in proposal_response.json().items()
                    if key != "status"
                },
                "payment_trigger": "seller_invoice",
                "organization_id": str(self.buyer.id),
            },
        )
        self.assertEqual(agreement_response.status_code, 201, agreement_response.text)
        agreement = agreement_response.json()
        self.assertEqual(agreement["status"], "PENDING_APPROVAL")
        self.assertEqual(agreement["terms"]["payment_terms"][0]["amount"]["amount"], "250")

        with self.session_factory() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Proposal)), 1)
            self.assertEqual(db.scalar(select(func.count()).select_from(AgreementVersion)), 1)

        self.actor[0] = ActorContext(self.outsider_user.id, frozenset({self.outsider.id}))
        self.assertEqual(self._request("GET", f"/deals/{deal_id}").status_code, 404)
        self.assertEqual(self._request("GET", f"/deals/{deal_id}/agreements/current").status_code, 404)
        self.assertEqual(self._request("GET", f"/deals/{deal_id}/payments").status_code, 404)

        self.actor[0] = ActorContext(self.buyer_user.id, frozenset({self.buyer.id}))
        buyer_messages = self._request("GET", f"/deals/{deal_id}/messages")
        self.assertEqual(buyer_messages.status_code, 200, buyer_messages.text)
        self.assertTrue(any(message["id"] == buyer_message_id for message in buyer_messages.json()))
        self.assertNotIn("Seller private floor", buyer_messages.text)
        self.assertEqual(
            self._request(
                "POST",
                f"/deals/{deal_id}/payments",
                json={"idempotency_key": "seller-invoice-once"},
            ).status_code,
            403,
        )
        self._approve(deal_id, agreement, self.buyer_user, self.buyer)

        self.actor[0] = ActorContext(self.seller_user.id, frozenset({self.seller.id}))
        seller_messages = self._request("GET", f"/deals/{deal_id}/messages")
        self.assertEqual(seller_messages.status_code, 200, seller_messages.text)
        self.assertTrue(any(message["id"] == seller_message.json()["id"] for message in seller_messages.json()))
        self.assertNotIn("900 USD", seller_messages.text)
        self._approve(deal_id, agreement, self.seller_user, self.seller)
        committed = self._request(
            "POST",
            f"/deals/{deal_id}/agreements/{agreement['version_number']}/commit",
            json={"terms_hash": agreement["terms_hash"]},
        )
        self.assertEqual(committed.status_code, 200, committed.text)
        replay = self._request(
            "POST",
            f"/deals/{deal_id}/agreements/{agreement['version_number']}/commit",
            json={"terms_hash": agreement["terms_hash"]},
        )
        self.assertEqual(replay.status_code, 200, replay.text)

        payment_response = self._request(
            "POST",
            f"/deals/{deal_id}/payments",
            json={"idempotency_key": "seller-invoice-once"},
        )
        self.assertEqual(payment_response.status_code, 202, payment_response.text)
        intent_id = UUID(payment_response.json()["id"])
        payment_replay = self._request(
            "POST",
            f"/deals/{deal_id}/payments",
            json={"idempotency_key": "seller-invoice-once"},
        )
        self.assertEqual(payment_replay.status_code, 202, payment_replay.text)
        self.assertEqual(payment_replay.json()["id"], str(intent_id))
        self.assertTrue(payment_replay.json()["already_existed"])

        with self.session_factory() as db:
            self.assertEqual(
                db.scalar(
                    select(func.count())
                    .select_from(OutboxEvent)
                    .where(OutboxEvent.event_type == PAYMENT_INTENT_AUTHORIZED_EVENT_TYPE)
                ),
                1,
            )
            self.assertEqual(
                db.scalar(
                    select(func.count())
                    .select_from(Obligation)
                ),
                2,
            )
            intent = db.get(PaymentIntent, intent_id)
            self.assertEqual(intent.status, "AUTHORIZED")

        # First worker stops after PayPal creates the invoice but before it saves the response.
        self.assertTrue(
            dispatch_one_payment_event(
                self.session_factory,
                SqlAlchemyPaymentProcessingRepository(self.session_factory),
                self.paypal,
            )
        )
        with self.session_factory() as db:
            intent = db.get(PaymentIntent, intent_id)
            self.assertEqual(intent.status, "CREATE_UNKNOWN")
            event = db.scalar(
                select(OutboxEvent).where(
                    OutboxEvent.event_type == PAYMENT_INTENT_AUTHORIZED_EVENT_TYPE
                )
            )
            event.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
            db.add(
                OutboxEvent(
                    aggregate_type="payment_intent",
                    aggregate_id=intent_id,
                    event_type=PAYMENT_INTENT_AUTHORIZED_EVENT_TYPE,
                    payload={"payment_intent_id": str(intent_id)},
                    status="PENDING",
                    retry_count=0,
                )
            )
            db.commit()

        # A new worker searches PayPal first, reuses the invoice, and sends once.
        self.assertTrue(
            dispatch_one_payment_event(
                self.session_factory,
                SqlAlchemyPaymentProcessingRepository(self.session_factory),
                self.paypal,
            )
        )
        self.assertEqual(self.paypal.create_calls, 1)
        self.assertEqual(self.paypal.find_calls, 1)
        self.assertEqual(self.paypal.send_calls, 1)
        with self.session_factory() as db:
            self.assertEqual(db.get(PaymentIntent, intent_id).status, "SENT")
        self.assertTrue(
            dispatch_one_payment_event(
                self.session_factory,
                SqlAlchemyPaymentProcessingRepository(self.session_factory),
                self.paypal,
            )
        )
        self.assertEqual(self.paypal.create_calls, 1)
        self.assertEqual(self.paypal.send_calls, 1)

        event = {
            "id": "webhook-paid-1",
            "event_type": "INVOICING.INVOICE.PAID",
            "resource": {"id": self.paypal.invoice_id, "payer_email": "private@example.test"},
        }
        first_webhook = self._post_webhook(event)
        duplicate_webhook = self._post_webhook(event)
        self.assertEqual(first_webhook.json(), {"status": "accepted"})
        self.assertEqual(duplicate_webhook.json(), {"status": "duplicate"})
        self.assertTrue(
            dispatch_one_payment_event(
                self.session_factory,
                SqlAlchemyPaymentProcessingRepository(self.session_factory),
                self.paypal,
            )
        )

        self.actor[0] = ActorContext(self.buyer_user.id, frozenset({self.buyer.id}))
        statuses = self._request("GET", f"/deals/{deal_id}/payments")
        self.assertEqual(statuses.status_code, 200, statuses.text)
        self.assertEqual(statuses.json()[0]["status"], "PAID")
        self.assertEqual(statuses.json()[0]["reconciled_amount"], "250")
        self.assertNotIn(self.paypal.invoice_id, statuses.text)
        self.assertNotIn("private@example.test", statuses.text)
        self.assertEqual(self.paypal.create_calls, 1)
        self.assertEqual(self.paypal.send_calls, 1)

        with self.session_factory() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(WebhookEvent)), 1)
            webhook = db.scalar(select(WebhookEvent))
            self.assertNotIn("payer_email", webhook.raw_payload["resource"])
            self.assertEqual(
                db.scalar(
                    select(func.count())
                    .select_from(OutboxEvent)
                    .where(OutboxEvent.event_type == PAYPAL_WEBHOOK_RECONCILIATION_EVENT_TYPE)
                ),
                1,
            )
            self.assertEqual(
                db.scalar(
                    select(func.count())
                    .select_from(AuditEvent)
                    .where(AuditEvent.event_type == "AGREEMENT_COMMITTED")
                ),
                1,
            )

    def _approve(self, deal_id, agreement, user, organization) -> None:
        self.actor[0] = ActorContext(user.id, frozenset({organization.id}))
        response = self._request(
            "POST",
            f"/deals/{deal_id}/agreements/{agreement['version_number']}/approve",
            json={"terms_hash": agreement["terms_hash"]},
        )
        self.assertEqual(response.status_code, 200, response.text)

    def _post_webhook(self, payload: dict) -> httpx.Response:
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

    def _request(self, method: str, path: str, *, json: dict | None = None) -> httpx.Response:
        async def send() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                return await client.request(method, path, json=json)

        return asyncio.run(send())


if __name__ == "__main__":
    unittest.main()
