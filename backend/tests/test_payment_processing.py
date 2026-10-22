"""Tests for payment invoice processing with a credential-free fake provider."""

from __future__ import annotations

import json
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from syncally.application.payment_processing import (
    PAYPAL_REQUEST_ID_RETRY_WINDOW,
    PaymentInvoiceLineItem,
    PaymentInvoiceReconciliation,
    PaymentInvoiceRequest,
    PaymentNeedsAction,
    PaymentOutcomeUnknown,
    PaymentRetryableError,
    PaymentWorkItem,
    payment_invoice_number,
    process_payment_intent,
    reconcile_payment_intent,
)
from syncally.domain.payments.intent import (
    PaymentIntentStatus,
    VerifiedProviderPaymentState,
    VerifiedProviderPaymentStatus,
)
from syncally.domain.shared.money import Money
from syncally.infrastructure.paypal import PayPalSandboxInvoiceProvider, _provider_request_id


def _request() -> PaymentInvoiceRequest:
    intent_id = uuid4()
    return PaymentInvoiceRequest(
        payment_intent_id=intent_id,
        deal_id=uuid4(),
        invoice_number=payment_invoice_number(intent_id),
        reference=str(intent_id),
        amount=Money(Decimal("10.00"), "USD"),
        seller_business_name="Seller Co",
        buyer_business_name="Buyer Co",
        buyer_contact_name="Buyer Admin",
        buyer_contact_email="buyer@example.com",
        line_items=(
            PaymentInvoiceLineItem(
                name="Steel bolts",
                description="SKU-1",
                quantity=Decimal("2"),
                unit="box",
                unit_price=Money(Decimal("5.00"), "USD"),
            ),
        ),
    )


def _work_item(
    request: PaymentInvoiceRequest,
    *,
    status: PaymentIntentStatus = PaymentIntentStatus.AUTHORIZED,
    provider_invoice_id: str | None = None,
    request_payload_hash: str | None = None,
    invoice_request: PaymentInvoiceRequest | None = None,
    request_error_code: str | None = None,
    request_error_detail: str | None = None,
    provider_create_started_at: datetime | None = None,
) -> PaymentWorkItem:
    return PaymentWorkItem(
        payment_intent_id=request.payment_intent_id,
        status=status,
        amount=request.amount,
        invoice_number=request.invoice_number,
        reference=request.reference,
        provider_invoice_id=provider_invoice_id,
        request_payload_hash=request_payload_hash,
        invoice_request=request if invoice_request is None else invoice_request,
        request_error_code=request_error_code,
        request_error_detail=request_error_detail,
        provider_create_started_at=provider_create_started_at,
    )


class FakeProcessingRepository:
    def __init__(self, work: PaymentWorkItem) -> None:
        self.work = work
        self.calls: list[str] = []
        self.begin_create_conflict = False
        self.reconciliation_failures = []

    def load(self, payment_intent_id):
        self.calls.append("load")
        return self.work

    def begin_create(self, payment_intent_id, request_payload_hash):
        self.calls.append("begin_create")
        if self.begin_create_conflict:
            self.work = replace(
                self.work,
                status=PaymentIntentStatus.PROVIDER_CREATED,
                provider_invoice_id="paypal-invoice-1",
            )
            raise PaymentNeedsAction("PAYMENT_STATE_CHANGED", "concurrent worker advanced state")
        self.work = replace(
            self.work,
            status=PaymentIntentStatus.CREATE_PENDING,
            request_payload_hash=request_payload_hash,
            provider_create_started_at=self.work.provider_create_started_at or datetime.now(UTC),
        )

    def mark_create_unknown(self, payment_intent_id):
        self.calls.append("mark_create_unknown")
        self.work = replace(self.work, status=PaymentIntentStatus.CREATE_UNKNOWN)

    def reconcile_create_not_found(self, payment_intent_id):
        self.calls.append("reconcile_create_not_found")
        self.work = replace(self.work, status=PaymentIntentStatus.AUTHORIZED)

    def record_provider_created(self, payment_intent_id, provider_invoice_id):
        self.calls.append("record_provider_created")
        self.work = replace(
            self.work,
            status=PaymentIntentStatus.PROVIDER_CREATED,
            provider_invoice_id=provider_invoice_id,
        )

    def mark_sent(self, payment_intent_id):
        self.calls.append("mark_sent")
        self.work = replace(self.work, status=PaymentIntentStatus.SENT)

    def mark_failure(self, payment_intent_id, code, detail):
        self.calls.append("mark_failure")
        self.work = replace(
            self.work,
            status=(
                PaymentIntentStatus.PROVIDER_CREATED
                if self.work.status is PaymentIntentStatus.PROVIDER_CREATED
                else PaymentIntentStatus.FAILED
            ),
            failure_code=code,
            failure_detail=detail,
        )

    def mark_manual_action(self, payment_intent_id, code, detail):
        self.calls.append("mark_manual_action")
        status = self.work.status
        if status is PaymentIntentStatus.AUTHORIZED:
            status = PaymentIntentStatus.FAILED
        elif status is PaymentIntentStatus.CREATE_PENDING:
            status = PaymentIntentStatus.CREATE_UNKNOWN
        self.work = replace(
            self.work,
            status=status,
            failure_code=code,
            failure_detail=detail,
        )

    def record_reconciliation_failure(
        self,
        payment_intent_id,
        *,
        outbox_event_id,
        webhook_event_id,
        lease_until,
        error_code,
        error_detail,
    ):
        self.calls.append("record_reconciliation_failure")
        self.reconciliation_failures.append((error_code, error_detail))


class FakeInvoiceProvider:
    def __init__(
        self,
        *,
        find_results=None,
        create_results=None,
        send_results=None,
        invoice_status_results=None,
    ) -> None:
        self.find_results = list(find_results or [])
        self.create_results = list(create_results or [])
        self.send_results = list(send_results or [])
        self.invoice_status_results = list(invoice_status_results or [])
        self.calls: list[str] = []

    @staticmethod
    def _next(results, default):
        result = results.pop(0) if results else default
        if isinstance(result, Exception):
            raise result
        return result

    def find_invoice(self, lookup):
        self.calls.append("find")
        return self._next(self.find_results, None)

    def get_invoice_status(self, provider_invoice_id):
        self.calls.append("get_status")
        return self._next(self.invoice_status_results, "DRAFT")

    def create_invoice(self, request):
        self.calls.append("create")
        return self._next(self.create_results, "paypal-invoice-1")

    def send_invoice(self, provider_invoice_id, payment_intent_id):
        self.calls.append("send")
        return self._next(self.send_results, None)


class PaymentProcessingTests(unittest.TestCase):
    def test_reconciliation_rejects_mismatched_authorized_amount(self) -> None:
        request = _request()
        repository = FakeProcessingRepository(
            _work_item(
                request,
                status=PaymentIntentStatus.SENT,
                provider_invoice_id="paypal-invoice-1",
            )
        )

        class MismatchedProvider(FakeInvoiceProvider):
            def get_invoice_reconciliation(self, provider_invoice_id):
                return PaymentInvoiceReconciliation(
                    provider_invoice_id=provider_invoice_id,
                    invoice_number=request.invoice_number,
                    reference=request.reference,
                    amount=Money(Decimal("11.00"), "USD"),
                    payment_state=VerifiedProviderPaymentState(
                        status=VerifiedProviderPaymentStatus.PAID,
                        paid_amount=Money(Decimal("11.00"), "USD"),
                        provider_reference=provider_invoice_id,
                    ),
                )

        with self.assertRaises(PaymentNeedsAction) as raised:
            reconcile_payment_intent(
                request.payment_intent_id,
                outbox_event_id=uuid4(),
                webhook_event_id=uuid4(),
                lease_until=datetime.now(UTC),
                repository=repository,
                provider=MismatchedProvider(),
            )

        self.assertEqual(raised.exception.code, "PAYPAL_RECONCILIATION_MISMATCH")
        self.assertEqual(repository.work.status, PaymentIntentStatus.SENT)
        self.assertEqual(repository.calls, ["load", "record_reconciliation_failure"])
        self.assertEqual(
            repository.reconciliation_failures[0][0], "PAYPAL_RECONCILIATION_MISMATCH"
        )

    def test_authorized_intent_creates_and_sends_invoice(self) -> None:
        request = _request()
        repository = FakeProcessingRepository(_work_item(request))
        provider = FakeInvoiceProvider()

        process_payment_intent(request.payment_intent_id, repository, provider)

        self.assertEqual(provider.calls, ["create", "send"])
        self.assertEqual(repository.work.status, PaymentIntentStatus.SENT)
        self.assertEqual(repository.work.provider_invoice_id, "paypal-invoice-1")
        self.assertEqual(
            repository.calls,
            ["load", "begin_create", "record_provider_created", "load", "mark_sent"],
        )

    def test_create_timeout_is_reconciled_before_any_retry(self) -> None:
        request = _request()
        repository = FakeProcessingRepository(_work_item(request))
        provider = FakeInvoiceProvider(
            create_results=[
                PaymentOutcomeUnknown("PAYPAL_OUTCOME_UNKNOWN", "safe retry detail")
            ],
            find_results=["paypal-invoice-1"],
        )

        with self.assertRaises(PaymentOutcomeUnknown):
            process_payment_intent(request.payment_intent_id, repository, provider)
        self.assertEqual(repository.work.status, PaymentIntentStatus.CREATE_UNKNOWN)

        process_payment_intent(request.payment_intent_id, repository, provider)

        self.assertEqual(provider.calls, ["create", "find", "get_status", "send"])
        self.assertEqual(repository.work.status, PaymentIntentStatus.SENT)

    def test_verified_not_found_allows_retry_after_search(self) -> None:
        request = _request()
        repository = FakeProcessingRepository(
            _work_item(
                request,
                status=PaymentIntentStatus.CREATE_UNKNOWN,
                request_payload_hash=request.payload_hash,
                provider_create_started_at=datetime.now(UTC),
            )
        )
        provider = FakeInvoiceProvider(find_results=[None], create_results=["paypal-invoice-2"])

        process_payment_intent(request.payment_intent_id, repository, provider)

        self.assertEqual(provider.calls, ["find", "create", "send"])
        self.assertEqual(repository.work.status, PaymentIntentStatus.SENT)

    def test_unknown_create_past_safe_retry_window_needs_manual_reconciliation(self) -> None:
        request = _request()
        now = datetime(2026, 10, 22, tzinfo=UTC)
        repository = FakeProcessingRepository(
            _work_item(
                request,
                status=PaymentIntentStatus.CREATE_UNKNOWN,
                request_payload_hash=request.payload_hash,
                provider_create_started_at=now - PAYPAL_REQUEST_ID_RETRY_WINDOW,
            )
        )
        provider = FakeInvoiceProvider(find_results=[None])

        with self.assertRaises(PaymentNeedsAction) as raised:
            process_payment_intent(request.payment_intent_id, repository, provider, now=now)

        self.assertEqual(raised.exception.code, "PAYMENT_CREATE_RETRY_WINDOW_EXPIRED")
        self.assertEqual(provider.calls, ["find"])
        self.assertEqual(repository.work.status, PaymentIntentStatus.CREATE_UNKNOWN)

    def test_unknown_create_without_timestamp_needs_manual_reconciliation(self) -> None:
        request = _request()
        repository = FakeProcessingRepository(
            _work_item(
                request,
                status=PaymentIntentStatus.CREATE_UNKNOWN,
                request_payload_hash=request.payload_hash,
            )
        )
        provider = FakeInvoiceProvider(find_results=[None])

        with self.assertRaises(PaymentNeedsAction) as raised:
            process_payment_intent(request.payment_intent_id, repository, provider)

        self.assertEqual(raised.exception.code, "PAYMENT_CREATE_TIME_UNKNOWN")
        self.assertEqual(provider.calls, ["find"])

    def test_changed_request_after_unknown_result_needs_manual_action(self) -> None:
        original = _request()
        changed = replace(original, buyer_contact_email="new-buyer@example.com")
        repository = FakeProcessingRepository(
            _work_item(
                original,
                status=PaymentIntentStatus.CREATE_UNKNOWN,
                request_payload_hash=original.payload_hash,
                invoice_request=changed,
            )
        )
        provider = FakeInvoiceProvider(find_results=[None])

        with self.assertRaises(PaymentNeedsAction):
            process_payment_intent(original.payment_intent_id, repository, provider)

        self.assertEqual(provider.calls, [])
        self.assertEqual(repository.work.status, PaymentIntentStatus.CREATE_UNKNOWN)
        self.assertEqual(repository.work.failure_code, "PAYMENT_INVOICE_REQUEST_CHANGED")

    def test_unknown_create_with_found_paid_invoice_is_marked_sent_without_resending(self) -> None:
        request = _request()
        repository = FakeProcessingRepository(
            _work_item(
                request,
                status=PaymentIntentStatus.CREATE_UNKNOWN,
                request_payload_hash=request.payload_hash,
                provider_create_started_at=datetime.now(UTC),
            )
        )
        provider = FakeInvoiceProvider(
            find_results=["paypal-invoice-1"],
            invoice_status_results=["PAID"],
        )

        process_payment_intent(request.payment_intent_id, repository, provider)

        self.assertEqual(provider.calls, ["find", "get_status"])
        self.assertEqual(repository.work.status, PaymentIntentStatus.SENT)
        self.assertEqual(repository.work.provider_invoice_id, "paypal-invoice-1")

    def test_create_conflict_does_not_fail_invoice_created_by_another_worker(self) -> None:
        request = _request()
        repository = FakeProcessingRepository(_work_item(request))
        repository.begin_create_conflict = True
        provider = FakeInvoiceProvider()

        process_payment_intent(request.payment_intent_id, repository, provider)

        self.assertEqual(provider.calls, ["send"])
        self.assertEqual(repository.work.status, PaymentIntentStatus.SENT)

    def test_permanent_create_failure_is_saved_for_manual_action(self) -> None:
        request = _request()
        repository = FakeProcessingRepository(_work_item(request))
        provider = FakeInvoiceProvider(
            create_results=[
                PaymentNeedsAction("PAYPAL_INVALID_REQUEST", "PayPal rejected invoice data.")
            ]
        )

        with self.assertRaises(PaymentNeedsAction):
            process_payment_intent(request.payment_intent_id, repository, provider)

        self.assertEqual(repository.work.status, PaymentIntentStatus.FAILED)
        self.assertEqual(repository.work.failure_code, "PAYPAL_INVALID_REQUEST")

    def test_missing_buyer_contact_does_not_call_provider(self) -> None:
        request = _request()
        repository = FakeProcessingRepository(
            _work_item(
                request,
                invoice_request=None,
                request_error_code="PAYMENT_BUYER_CONTACT_AMBIGUOUS",
                request_error_detail="The buyer organization needs exactly one active admin.",
            )
        )
        repository.work = replace(repository.work, invoice_request=None)
        provider = FakeInvoiceProvider()

        with self.assertRaises(PaymentNeedsAction):
            process_payment_intent(request.payment_intent_id, repository, provider)

        self.assertEqual(provider.calls, [])
        self.assertEqual(repository.work.status, PaymentIntentStatus.FAILED)

    def test_send_timeout_retries_send_without_creating_another_invoice(self) -> None:
        request = _request()
        repository = FakeProcessingRepository(
            _work_item(
                request,
                status=PaymentIntentStatus.PROVIDER_CREATED,
                provider_invoice_id="paypal-invoice-1",
            )
        )
        provider = FakeInvoiceProvider(
            send_results=[
                PaymentRetryableError("PAYPAL_TEMPORARY", "retry later"),
                None,
            ]
        )

        with self.assertRaises(PaymentRetryableError):
            process_payment_intent(request.payment_intent_id, repository, provider)
        self.assertEqual(repository.work.status, PaymentIntentStatus.PROVIDER_CREATED)
        process_payment_intent(request.payment_intent_id, repository, provider)

        self.assertEqual(provider.calls, ["send", "send"])
        self.assertEqual(repository.work.status, PaymentIntentStatus.SENT)

    def test_invoice_number_and_provider_operation_ids_are_stable(self) -> None:
        intent_id = uuid4()

        self.assertEqual(payment_invoice_number(intent_id), payment_invoice_number(intent_id))
        self.assertEqual(len(payment_invoice_number(intent_id)), 25)
        self.assertEqual(
            _provider_request_id(intent_id, "create"),
            _provider_request_id(intent_id, "create"),
        )
        self.assertNotEqual(
            _provider_request_id(intent_id, "create"),
            _provider_request_id(intent_id, "send"),
        )


class PayPalSandboxAdapterTests(unittest.TestCase):
    def test_webhook_signature_uses_the_registered_webhook_and_paypal_headers(self) -> None:
        responses = [
            (200, b'{"access_token":"test-token","expires_in":3600}'),
            (200, b'{"verification_status":"SUCCESS"}'),
        ]
        sent_requests = []
        provider = PayPalSandboxInvoiceProvider(
            "sandbox-client",
            "sandbox-secret",
            send_request=lambda http_request: (
                sent_requests.append(http_request) or responses.pop(0)
            ),
        )
        headers = {
            "paypal-auth-algo": "SHA256withRSA",
            "paypal-cert-url": "https://api-m.sandbox.paypal.com/cert",
            "paypal-transmission-id": "transmission-1",
            "paypal-transmission-sig": "signature",
            "paypal-transmission-time": "2026-10-22T10:00:00Z",
        }
        event = {"id": "event-1", "event_type": "INVOICING.INVOICE.PAID"}

        self.assertTrue(provider.verify_webhook_signature(headers, event, "webhook-1"))

        self.assertEqual(
            sent_requests[1].full_url,
            "https://api-m.sandbox.paypal.com/v1/notifications/verify-webhook-signature",
        )
        payload = json.loads(sent_requests[1].data)
        self.assertEqual(payload["webhook_id"], "webhook-1")
        self.assertEqual(payload["webhook_event"], event)
        self.assertEqual(payload["transmission_sig"], "signature")

    def test_reconciliation_uses_current_invoice_amount_and_does_not_trust_paid_event(self) -> None:
        responses = [
            (200, b'{"access_token":"test-token","expires_in":3600}'),
            (
                200,
                b'{"id":"paypal-invoice-1","status":"PAID",'
                b'"detail":{"invoice_number":"SA-test","reference":"intent-1"},'
                b'"amount":{"currency_code":"USD","value":"10.00"},'
                b'"payments":{"paid_amount":{"currency_code":"USD","value":"4.00"}}}',
            ),
        ]
        provider = PayPalSandboxInvoiceProvider(
            "sandbox-client",
            "sandbox-secret",
            send_request=lambda http_request: responses.pop(0),
        )

        state = provider.get_invoice_reconciliation("paypal-invoice-1")

        self.assertEqual(state.payment_state.status, VerifiedProviderPaymentStatus.PARTIALLY_PAID)
        self.assertEqual(state.payment_state.paid_amount.amount, Decimal("4.00"))
        self.assertEqual(state.amount.amount, Decimal("10.00"))
        self.assertEqual(state.reference, "intent-1")

    def test_create_and_send_use_sandbox_and_separate_idempotent_requests(self) -> None:
        request = _request()
        responses = [
            (200, b'{"access_token":"test-token","expires_in":3600}'),
            (201, b'{"id":"paypal-invoice-1"}'),
            (202, b""),
        ]
        sent_requests = []

        def sender(http_request):
            sent_requests.append(http_request)
            return responses.pop(0)

        provider = PayPalSandboxInvoiceProvider(
            "sandbox-client",
            "sandbox-secret",
            send_request=sender,
        )

        invoice_id = provider.create_invoice(request)
        provider.send_invoice(invoice_id, request.payment_intent_id)

        self.assertEqual(invoice_id, "paypal-invoice-1")
        self.assertEqual(
            sent_requests[0].full_url,
            "https://api-m.sandbox.paypal.com/v1/oauth2/token",
        )
        self.assertEqual(
            sent_requests[1].full_url,
            "https://api-m.sandbox.paypal.com/v2/invoicing/invoices",
        )
        create_headers = {key.lower(): value for key, value in sent_requests[1].header_items()}
        send_headers = {key.lower(): value for key, value in sent_requests[2].header_items()}
        self.assertEqual(
            create_headers["paypal-request-id"],
            _provider_request_id(request.payment_intent_id, "create"),
        )
        self.assertEqual(
            send_headers["paypal-request-id"],
            _provider_request_id(request.payment_intent_id, "send"),
        )
        create_payload = json.loads(sent_requests[1].data)
        send_payload = json.loads(sent_requests[2].data)
        self.assertEqual(create_payload["detail"]["invoice_number"], request.invoice_number)
        self.assertEqual(create_payload["detail"]["currency_code"], "USD")
        self.assertEqual(
            create_payload["primary_recipients"][0]["billing_info"]["email_address"],
            "buyer@example.com",
        )
        self.assertEqual(create_payload["items"][0]["unit_amount"]["value"], "5")
        self.assertEqual(send_payload, {"send_to_invoicer": False, "send_to_recipient": True})

    def test_create_timeout_is_marked_as_unknown(self) -> None:
        responses = [(200, b'{"access_token":"test-token","expires_in":3600}')]

        def sender(http_request):
            if "oauth2/token" in http_request.full_url:
                return responses.pop(0)
            raise TimeoutError()

        provider = PayPalSandboxInvoiceProvider(
            "sandbox-client",
            "sandbox-secret",
            send_request=sender,
        )

        with self.assertRaises(PaymentOutcomeUnknown):
            provider.create_invoice(_request())

    def test_permanent_paypal_error_does_not_persist_provider_body(self) -> None:
        responses = [
            (200, b'{"access_token":"test-token","expires_in":3600}'),
            (422, b'{"name":"INVALID_REQUEST","message":"sensitive invoice detail"}'),
        ]

        provider = PayPalSandboxInvoiceProvider(
            "sandbox-client",
            "sandbox-secret",
            send_request=lambda http_request: responses.pop(0),
        )

        with self.assertRaises(PaymentNeedsAction) as raised:
            provider.create_invoice(_request())

        self.assertEqual(raised.exception.code, "PAYPAL_INVALID_REQUEST")
        self.assertNotIn("sensitive invoice detail", raised.exception.detail)

    def test_invoice_search_requires_one_matching_result(self) -> None:
        request = _request()
        responses = [
            (200, b'{"access_token":"test-token","expires_in":3600}'),
            (
                200,
                json.dumps(
                    {
                        "items": [
                            {
                                "id": "paypal-invoice-1",
                                "detail": {
                                    "invoice_number": request.invoice_number,
                                    "reference": request.reference,
                                },
                                "amount": {"currency_code": "USD", "value": "10.00"},
                                "primary_recipients": [
                                    {
                                        "billing_info": {
                                            "email_address": request.buyer_contact_email
                                        }
                                    }
                                ],
                            }
                        ]
                    }
                ).encode(),
            ),
        ]
        sent_requests = []
        provider = PayPalSandboxInvoiceProvider(
            "sandbox-client",
            "sandbox-secret",
            send_request=lambda http_request: (
                sent_requests.append(http_request) or responses.pop(0)
            ),
        )

        result = provider.find_invoice(request.lookup)

        self.assertEqual(result, "paypal-invoice-1")
        self.assertEqual(
            sent_requests[1].full_url,
            "https://api-m.sandbox.paypal.com/v2/invoicing/search-invoices?page=1&page_size=2&total_required=true",
        )

    def test_get_invoice_status_uses_the_sandbox_invoice_endpoint(self) -> None:
        responses = [
            (200, b'{"access_token":"test-token","expires_in":3600}'),
            (200, b'{"id":"paypal-invoice-1","status":"PAID"}'),
        ]
        sent_requests = []
        provider = PayPalSandboxInvoiceProvider(
            "sandbox-client",
            "sandbox-secret",
            send_request=lambda http_request: (
                sent_requests.append(http_request) or responses.pop(0)
            ),
        )

        self.assertEqual(provider.get_invoice_status("paypal-invoice-1"), "PAID")
        self.assertEqual(
            sent_requests[1].full_url,
            "https://api-m.sandbox.paypal.com/v2/invoicing/invoices/paypal-invoice-1",
        )

    def test_non_object_create_response_is_an_unknown_outcome(self) -> None:
        responses = [
            (200, b'{"access_token":"test-token","expires_in":3600}'),
            (201, b'[]'),
        ]
        provider = PayPalSandboxInvoiceProvider(
            "sandbox-client",
            "sandbox-secret",
            send_request=lambda http_request: responses.pop(0),
        )

        with self.assertRaises(PaymentOutcomeUnknown):
            provider.create_invoice(_request())

    def test_oauth_401_is_retryable_and_does_not_expose_credentials(self) -> None:
        provider = PayPalSandboxInvoiceProvider(
            "sandbox-client",
            "sandbox-secret",
            send_request=lambda http_request: (401, b'{"error":"invalid_client"}'),
        )

        with self.assertRaises(PaymentRetryableError) as raised:
            provider.create_invoice(_request())

        self.assertEqual(raised.exception.code, "PAYPAL_AUTH_FAILED")
        self.assertNotIn("sandbox-secret", raised.exception.detail)

    def test_unit_price_precision_is_checked_before_serializing(self) -> None:
        request = _request()
        item = replace(request.line_items[0], unit_price=Money(Decimal("5.001"), "USD"))
        request = replace(request, line_items=(item,))
        provider = PayPalSandboxInvoiceProvider("sandbox-client", "sandbox-secret")

        with self.assertRaises(PaymentNeedsAction) as raised:
            provider._invoice_payload(request)

        self.assertEqual(raised.exception.code, "PAYPAL_INVOICE_ITEM_INVALID")

    def test_invoice_search_accepts_empty_results_with_zero_total(self) -> None:
        request = _request()
        responses = [
            (200, b'{"access_token":"test-token","expires_in":3600}'),
            (200, b'{"total_items":0,"total_pages":0}'),
        ]
        provider = PayPalSandboxInvoiceProvider(
            "sandbox-client",
            "sandbox-secret",
            send_request=lambda http_request: responses.pop(0),
        )

        self.assertIsNone(provider.find_invoice(request.lookup))


if __name__ == "__main__":
    unittest.main()
