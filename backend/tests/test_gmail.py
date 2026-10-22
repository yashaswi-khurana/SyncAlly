"""Tests for Gmail's retryable and permanent SMTP response handling."""

from __future__ import annotations

import smtplib
import unittest
from decimal import Decimal
from unittest.mock import patch

from syncally.application.payment_processing import (
    PaymentInvoiceNotice,
    PaymentNeedsAction,
    PaymentRetryableError,
)
from syncally.domain.shared.money import Money
from syncally.infrastructure.gmail import GmailSMTPInvoiceNotifier


class _FakeSMTP:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def ehlo(self):
        pass

    def starttls(self, *, context):
        pass

    def login(self, username, password):
        pass

    def send_message(self, message):
        raise self.error


class GmailSMTPInvoiceNotifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.notifier = GmailSMTPInvoiceNotifier("sender@example.com", "app-password")
        self.notice = PaymentInvoiceNotice(
            invoice_number="SA-test",
            amount=Money(Decimal("10.00"), "USD"),
            recipient_email="buyer@example.com",
            recipient_view_url="https://paypal.com/invoice/p/test",
        )

    def test_permanent_recipient_refusal_needs_manual_action(self) -> None:
        smtp = _FakeSMTP(
            smtplib.SMTPRecipientsRefused(
                {"buyer@example.com": (550, b"mailbox unavailable")}
            )
        )

        with patch("syncally.infrastructure.gmail.smtplib.SMTP", return_value=smtp):
            with self.assertRaises(PaymentNeedsAction) as raised:
                self.notifier.send_invoice_notice(self.notice)

        self.assertEqual(raised.exception.code, "GMAIL_SMTP_RECIPIENT_REJECTED")

    def test_temporary_recipient_refusal_is_retryable(self) -> None:
        smtp = _FakeSMTP(
            smtplib.SMTPRecipientsRefused(
                {"buyer@example.com": (450, b"mailbox temporarily unavailable")}
            )
        )

        with patch("syncally.infrastructure.gmail.smtplib.SMTP", return_value=smtp):
            with self.assertRaises(PaymentRetryableError) as raised:
                self.notifier.send_invoice_notice(self.notice)

        self.assertEqual(raised.exception.code, "GMAIL_TEMPORARILY_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
