"""Tests for Gmail API email delivery over HTTPS."""

from __future__ import annotations

import base64
import json
import unittest
from decimal import Decimal
from email import policy
from email.parser import BytesParser
from types import SimpleNamespace
from urllib.parse import parse_qs

import httpx
from pydantic import SecretStr

from syncally.application.payment_processing import (
    PaymentInvoiceNotice,
    PaymentNeedsAction,
    PaymentRetryableError,
)
from syncally.domain.shared.money import Money
from syncally.infrastructure.gmail import (
    GmailApiEmailNotifier,
    GmailSMTPInvoiceNotifier,
    configured_invitation_notifier,
    configured_invoice_notifier,
)


class GmailApiEmailNotifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.notice = PaymentInvoiceNotice(
            invoice_number="SA-test",
            amount=Money(Decimal("10.00"), "USD"),
            recipient_email="buyer@example.com",
            recipient_view_url="https://sandbox.paypal.com/invoice/p/test",
        )

    def _notifier(self, transport: httpx.BaseTransport) -> GmailApiEmailNotifier:
        return GmailApiEmailNotifier(
            "client-id",
            "client-secret",
            "refresh-token",
            "syncally.sender@gmail.com",
            transport=transport,
        )

    def test_invoice_uses_oauth_refresh_and_gmail_send_https_apis(self) -> None:
        requests: list[httpx.Request] = []

        def respond(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.url.host == "oauth2.googleapis.com":
                return httpx.Response(200, json={"access_token": "access-token"})
            return httpx.Response(200, json={"id": "gmail-message-id"})

        self._notifier(httpx.MockTransport(respond)).send_invoice_notice(self.notice)

        token_request, send_request = requests
        self.assertEqual(token_request.url.host, "oauth2.googleapis.com")
        token_form = parse_qs(token_request.content.decode())
        self.assertEqual(token_form["grant_type"], ["refresh_token"])
        self.assertEqual(token_form["refresh_token"], ["refresh-token"])
        self.assertEqual(send_request.url.host, "gmail.googleapis.com")
        self.assertEqual(send_request.headers["Authorization"], "Bearer access-token")
        raw = json.loads(send_request.content)["raw"]
        decoded = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
        email = BytesParser(policy=policy.default).parsebytes(decoded)
        self.assertEqual(email["From"], "syncally.sender@gmail.com")
        self.assertEqual(email["To"], "buyer@example.com")
        self.assertIn(self.notice.recipient_view_url, email.get_body(preferencelist=["plain"]).get_content())

    def test_invitation_has_escaped_html_alternative(self) -> None:
        requests: list[httpx.Request] = []

        def respond(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.url.host == "oauth2.googleapis.com":
                return httpx.Response(200, json={"access_token": "access-token"})
            return httpx.Response(200, json={"id": "gmail-message-id"})

        self._notifier(httpx.MockTransport(respond)).send_team_invitation(
            "buyer@example.com",
            "Buyer <Team>",
            "https://syncally.example/#/invite?token=secret",
            "2026-12-15T00:00:00+00:00",
        )

        raw = json.loads(requests[1].content)["raw"]
        decoded = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
        email = BytesParser(policy=policy.default).parsebytes(decoded)
        self.assertIn("Buyer <Team>", email.get_body(preferencelist=["plain"]).get_content())
        self.assertIn("Buyer &lt;Team&gt;", email.get_body(preferencelist=["html"]).get_content())

    def test_quota_response_is_retryable(self) -> None:
        def respond(request: httpx.Request) -> httpx.Response:
            if request.url.host == "oauth2.googleapis.com":
                return httpx.Response(200, json={"access_token": "access-token"})
            return httpx.Response(
                403,
                json={"error": {"errors": [{"reason": "userRateLimitExceeded"}]}},
            )

        with self.assertRaises(PaymentRetryableError) as raised:
            self._notifier(httpx.MockTransport(respond)).send_invoice_notice(self.notice)

        self.assertEqual(raised.exception.code, "GMAIL_API_TEMPORARILY_UNAVAILABLE")

    def test_revoked_refresh_token_requires_reauthorization(self) -> None:
        notifier = self._notifier(
            httpx.MockTransport(lambda _: httpx.Response(400, json={"error": "invalid_grant"}))
        )

        with self.assertRaises(PaymentNeedsAction) as raised:
            notifier.send_invoice_notice(self.notice)

        self.assertEqual(raised.exception.code, "GMAIL_API_AUTH_FAILED")

    def test_gmail_api_is_preferred_over_legacy_smtp(self) -> None:
        config = SimpleNamespace(
            gmail_api_client_id="client-id",
            gmail_api_client_secret=SecretStr("client-secret"),
            gmail_api_refresh_token=SecretStr("refresh-token"),
            gmail_api_sender_email="sender@gmail.com",
            gmail_smtp_username="sender@gmail.com",
            gmail_app_password=SecretStr("app-password"),
            gmail_from_email="sender@gmail.com",
        )

        self.assertIsInstance(configured_invoice_notifier(config), GmailApiEmailNotifier)
        self.assertIsInstance(configured_invitation_notifier(config), GmailApiEmailNotifier)

    def test_smtp_remains_fallback_when_api_provider_is_not_configured(self) -> None:
        config = SimpleNamespace(
            gmail_api_client_id="",
            gmail_api_client_secret=SecretStr(""),
            gmail_api_refresh_token=SecretStr(""),
            gmail_api_sender_email="",
            gmail_smtp_username="sender@gmail.com",
            gmail_app_password=SecretStr("app-password"),
            gmail_from_email="",
        )

        self.assertIsInstance(configured_invoice_notifier(config), GmailSMTPInvoiceNotifier)


if __name__ == "__main__":
    unittest.main()
