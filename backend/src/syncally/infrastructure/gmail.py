"""Optional Gmail SMTP delivery for PayPal invoice notifications."""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from syncally.application.payment_processing import (
    PaymentInvoiceNotice,
    PaymentNeedsAction,
    PaymentRetryableError,
)
from syncally.domain.shared.money import canonical_decimal

_GMAIL_SMTP_HOST = "smtp.gmail.com"
_GMAIL_SMTP_PORT = 587
_GMAIL_SMTP_TIMEOUT_SECONDS = 20.0


class GmailSMTPInvoiceNotifier:
    """Send a plain-text copy of a Sandbox invoice using Gmail SMTP."""

    def __init__(
        self,
        username: str,
        app_password: str,
        from_email: str | None = None,
    ) -> None:
        if not username.strip() or not app_password.strip():
            raise ValueError("GMAIL_SMTP_USERNAME and GMAIL_APP_PASSWORD are required.")
        configured_username = username.strip()
        configured_from_email = (from_email or username).strip()
        if any(
            address.count("@") != 1
            or any(character.isspace() for character in address)
            for address in (configured_username, configured_from_email)
        ):
            raise ValueError("Gmail sender addresses must be valid email addresses.")
        self._username = configured_username
        self._app_password = "".join(app_password.split())
        self._from_email = configured_from_email

    def send_invoice_notice(self, notice: PaymentInvoiceNotice) -> None:
        message = EmailMessage()
        message["From"] = self._from_email
        message["To"] = notice.recipient_email
        message["Subject"] = f"Your SyncAlly PayPal Sandbox invoice {notice.invoice_number}"
        message["X-SyncAlly-Invoice-Number"] = notice.invoice_number
        message.set_content(
            "A PayPal Sandbox invoice has been created for your SyncAlly transaction.\n\n"
            f"Invoice: {notice.invoice_number}\n"
            f"Amount: {notice.amount.currency} {canonical_decimal(notice.amount.amount)}\n\n"
            f"View invoice: {notice.recipient_view_url}\n\n"
            "This is a Sandbox invoice for testing. PayPal Sandbox notifications are not sent "
            "to real Gmail inboxes; SyncAlly sent this separate email so you can open the "
            "invoice link."
        )

        try:
            with smtplib.SMTP(
                _GMAIL_SMTP_HOST,
                _GMAIL_SMTP_PORT,
                timeout=_GMAIL_SMTP_TIMEOUT_SECONDS,
            ) as smtp:
                smtp.ehlo()
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
                smtp.login(self._username, self._app_password)
                smtp.send_message(message)
        except smtplib.SMTPAuthenticationError as error:
            raise PaymentNeedsAction(
                "GMAIL_SMTP_AUTH_FAILED",
                "Gmail rejected SMTP authentication; verify the sender address and App Password.",
            ) from error
        except smtplib.SMTPResponseException as error:
            if 400 <= error.smtp_code < 500:
                raise PaymentRetryableError(
                    "GMAIL_TEMPORARILY_UNAVAILABLE",
                    "Gmail temporarily rejected the invoice email; it will be retried.",
                ) from error
            raise PaymentNeedsAction(
                "GMAIL_SMTP_REJECTED",
                "Gmail rejected the invoice email; check the sender configuration and recipient.",
            ) from error
        except smtplib.SMTPRecipientsRefused as error:
            codes = [code for code, _ in error.recipients.values()]
            if codes and all(400 <= code < 500 for code in codes):
                raise PaymentRetryableError(
                    "GMAIL_TEMPORARILY_UNAVAILABLE",
                    "Gmail temporarily rejected the invoice email; it will be retried.",
                ) from error
            raise PaymentNeedsAction(
                "GMAIL_SMTP_RECIPIENT_REJECTED",
                "Gmail rejected the invoice recipient; verify the buyer contact email.",
            ) from error
        except (smtplib.SMTPException, OSError, TimeoutError) as error:
            raise PaymentRetryableError(
                "GMAIL_TEMPORARILY_UNAVAILABLE",
                "Gmail is temporarily unavailable; the invoice email will be retried.",
            ) from error
