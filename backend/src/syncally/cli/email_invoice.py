"""Send a Gmail copy of an existing PayPal Sandbox invoice."""

from __future__ import annotations

import argparse

from syncally.config import GmailSettings, PayPalSettings
from syncally.infrastructure.gmail import GmailSMTPInvoiceNotifier
from syncally.infrastructure.paypal import PayPalSandboxInvoiceProvider


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("invoice_id", help="PayPal Sandbox invoice ID, such as INV2-...")
    args = parser.parse_args()

    paypal_settings = PayPalSettings()
    gmail_settings = GmailSettings()
    gmail_username = gmail_settings.gmail_smtp_username.strip()
    gmail_password = gmail_settings.gmail_app_password.get_secret_value()
    if not gmail_username or not gmail_password:
        parser.error("set GMAIL_SMTP_USERNAME and GMAIL_APP_PASSWORD in backend/.env first")

    provider = PayPalSandboxInvoiceProvider(
        paypal_settings.paypal_client_id,
        paypal_settings.paypal_client_secret.get_secret_value(),
    )
    notice = provider.get_invoice_notice(args.invoice_id)
    notifier = GmailSMTPInvoiceNotifier(
        gmail_username,
        gmail_password,
        gmail_settings.gmail_from_email.strip() or None,
    )
    notifier.send_invoice_notice(notice)
    print(f"Sent invoice {notice.invoice_number} to {notice.recipient_email}.")


if __name__ == "__main__":
    main()
