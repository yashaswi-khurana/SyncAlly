import unittest
from decimal import Decimal

import httpx
from pydantic import SecretStr

from syncally.application.invoicing import InvoiceFailure
from syncally.infrastructure.paypal.adapter import SandboxPayPalAdapter


class SandboxAdapterTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.response = httpx.Response(201, json={"id": "INV2-TEST-1234"})
        self.adapter = SandboxPayPalAdapter(
            SecretStr("fake-client-id"),
            SecretStr("fake-secret-never-log"),
            transport=httpx.MockTransport(self.handle),
        )

    def tearDown(self):
        self.adapter.close()

    def handle(self, request):
        self.requests.append(request)
        self.assertEqual(request.url.host, "api-m.sandbox.paypal.com")
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "fake-token-never-log"})
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

    def test_create_uses_stable_header_and_send_is_a_separate_endpoint(self):
        self.assertEqual(self.adapter.create({"detail": {}}, "stable-create"), "INV2-TEST-1234")
        self.assertEqual(self.requests[-1].headers["PayPal-Request-Id"], "stable-create")
        self.assertEqual(self.requests[-1].headers["Prefer"], "return=representation")
        self.response = httpx.Response(202)
        self.adapter.send("INV2-TEST-1234", "stable-send")
        self.assertEqual(self.requests[-1].url.path, "/v2/invoicing/invoices/INV2-TEST-1234/send")
        self.assertNotIn("PayPal-Request-Id", self.requests[-1].headers)

    def test_timeout_is_ambiguous_for_mutation_only(self):
        self.response = httpx.ReadTimeout("fake-secret-never-log")
        for call, ambiguous in (
            (lambda: self.adapter.create({}, "id"), True),
            (lambda: self.adapter.send("INV2-TEST-1234", "id"), True),
            (lambda: self.adapter.get("INV2-TEST-1234"), False),
        ):
            with self.subTest(ambiguous=ambiguous), self.assertRaises(InvoiceFailure) as result:
                call()
            self.assertEqual(result.exception.ambiguous, ambiguous)
            self.assertNotIn("fake-secret", str(result.exception))

    def test_http_failure_classification_and_redaction(self):
        for code, permanent, ambiguous in (
            (400, True, False),
            (401, True, False),
            (403, True, False),
            (422, True, False),
            (429, False, False),
            (500, False, True),
            (503, False, True),
            (408, False, True),
            (302, True, False),
        ):
            with self.subTest(code=code):
                self.response = httpx.Response(code, text="fake-secret-never-log")
                with self.assertRaises(InvoiceFailure) as result:
                    self.adapter.create({}, "stable")
                self.assertEqual(result.exception.permanent, permanent)
                self.assertEqual(result.exception.ambiguous, ambiguous)
                self.assertNotIn("fake-secret", str(result.exception))

    def test_create_malformed_response_preserves_ambiguity(self):
        for data in ({}, {"id": "bad/../../url"}, []):
            with self.subTest(data=data):
                self.response = httpx.Response(201, json=data)
                with self.assertRaises(InvoiceFailure) as result:
                    self.adapter.create({}, "stable")
                self.assertTrue(result.exception.ambiguous)

    def test_minimal_create_link_is_parsed_without_following_url(self):
        self.response = httpx.Response(
            201, json={"href": "https://untrusted.example/INV2-TEST-1234"}
        )
        self.assertEqual(self.adapter.create({}, "stable"), "INV2-TEST-1234")
        self.assertEqual(len(self.requests), 2)

    def test_invalid_reference_cannot_change_origin_or_path(self):
        with self.assertRaises(InvoiceFailure):
            self.adapter.get("https://live.paypal.com/secret")
        self.assertEqual(self.requests, [])

    def test_normalizes_authoritative_invoice(self):
        self.response = httpx.Response(
            200,
            json={
                "id": "INV2-TEST-1234",
                "detail": {"invoice_number": "SA-test", "reference": "intent"},
                "status": "DRAFT",
                "amount": {"value": "10.00", "currency_code": "USD"},
                "invoicer": {"email_address": "seller@example.com"},
                "primary_recipients": [{"billing_info": {"email_address": "buyer@example.com"}}],
            },
        )
        result = self.adapter.get("INV2-TEST-1234")
        self.assertEqual(result.amount, Decimal("10"))
        self.assertEqual(result.currency, "USD")

    def test_invalid_evidence_is_permanent_and_redacted(self):
        self.response = httpx.Response(200, json={"error": "fake-secret-never-log"})
        with self.assertRaises(InvoiceFailure) as result:
            self.adapter.get("INV2-TEST-1234")
        self.assertTrue(result.exception.permanent)
        self.assertNotIn("fake-secret", str(result.exception))

    def test_empty_search_does_not_claim_definitive_absence(self):
        self.response = httpx.Response(200, json={"total_items": 0})
        self.assertEqual(self.adapter.find("SA-test"), [])
        self.assertEqual(self.requests[-1].url.path, "/v2/invoicing/search-invoices")

    def test_duplicate_search_hits_require_action(self):
        self.response = httpx.Response(
            200,
            json={
                "items": [
                    {"id": "INV2-A", "detail": {"invoice_number": "same"}},
                    {"id": "INV2-B", "detail": {"invoice_number": "same"}},
                ]
            },
        )
        with self.assertRaises(InvoiceFailure) as result:
            self.adapter.find("same")
        self.assertTrue(result.exception.permanent)

    def test_token_failure_is_not_an_ambiguous_invoice_create(self):
        def denied(request):
            return httpx.Response(401, text="fake-secret-never-log")

        adapter = SandboxPayPalAdapter(
            SecretStr("fake"), SecretStr("fake"), transport=httpx.MockTransport(denied)
        )
        try:
            with self.assertRaises(InvoiceFailure) as result:
                adapter.create({}, "stable")
            self.assertFalse(result.exception.ambiguous)
            self.assertTrue(result.exception.permanent)
        finally:
            adapter.close()
