"""Send an email copy of an existing PayPal Sandbox invoice."""

from __future__ import annotations

import argparse

from syncally.config import EmailSettings, PayPalSettings
from syncally.infrastructure.gmail import configured_invoice_notifier
from syncally.infrastructure.paypal import PayPalSandboxInvoiceProvider


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("invoice_id", help="PayPal Sandbox invoice ID, such as INV2-...")
    args = parser.parse_args()

    paypal_settings = PayPalSettings()
    email_settings = EmailSettings()
    try:
        notifier = configured_invoice_notifier(email_settings)
    except ValueError as error:
        parser.error(f"invalid email configuration: {error}")
    if notifier is None:
        parser.error(
            "set Gmail API OAuth settings or Gmail SMTP credentials in backend/.env first"
        )

    provider = PayPalSandboxInvoiceProvider(
        paypal_settings.paypal_client_id,
        paypal_settings.paypal_client_secret.get_secret_value(),
    )
    notice = provider.get_invoice_notice(args.invoice_id)
    notifier.send_invoice_notice(notice)
    print("Invoice email copy sent.")


if __name__ == "__main__":
    main()
