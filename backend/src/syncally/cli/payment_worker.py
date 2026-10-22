"""Standalone worker for payment authorization outbox events.

Run with python -m syncally.cli.payment_worker. PayPal credentials are read
only by this process from its environment.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from sqlalchemy.orm import Session

from syncally.config import GmailSettings, PayPalSettings, settings
from syncally.infrastructure.database import SessionLocal
from syncally.infrastructure.gmail import GmailSMTPInvoiceNotifier
from syncally.infrastructure.payment_outbox import (
    dispatch_pending_payment_events,
)
from syncally.infrastructure.paypal import PayPalSandboxInvoiceProvider
from syncally.infrastructure.repositories.payment_processing import (
    SqlAlchemyPaymentProcessingRepository,
)
from syncally.operations import Operation, configure_logging, log_operation

logger = logging.getLogger(__name__)


def run_forever(
    *,
    poll_interval: float,
    batch_size: int,
    session_factory: Callable[[], Session] = SessionLocal,
    provider: PayPalSandboxInvoiceProvider | None = None,
    notifier: GmailSMTPInvoiceNotifier | None = None,
) -> None:
    if provider is None:
        paypal_settings = PayPalSettings()
        provider = PayPalSandboxInvoiceProvider(
            paypal_settings.paypal_client_id,
            paypal_settings.paypal_client_secret.get_secret_value(),
        )
    if notifier is None:
        gmail_settings = GmailSettings()
        gmail_username = gmail_settings.gmail_smtp_username.strip()
        gmail_password = gmail_settings.gmail_app_password.get_secret_value()
        gmail_from_email = gmail_settings.gmail_from_email.strip()
        gmail_has_configuration = bool(gmail_username or gmail_password or gmail_from_email)
        if gmail_has_configuration:
            if not gmail_username or not gmail_password:
                raise ValueError(
                    "GMAIL_SMTP_USERNAME and GMAIL_APP_PASSWORD must both be configured."
                )
            notifier = GmailSMTPInvoiceNotifier(
                gmail_username,
                gmail_password,
                gmail_from_email or None,
            )
    repository = SqlAlchemyPaymentProcessingRepository(session_factory)
    log_operation(logger, Operation.WORKER_STARTED, worker="payment")
    while True:
        try:
            dispatch_pending_payment_events(
                session_factory,
                repository,
                provider,
                batch_size=batch_size,
                notifier=notifier,
            )
        except Exception:
            log_operation(logger, Operation.WORKER_FAILED, level=logging.ERROR, worker="payment")
        time.sleep(poll_interval)


def main() -> None:
    configure_logging()
    try:
        run_forever(
            poll_interval=settings.outbox_poll_interval_seconds,
            batch_size=settings.outbox_batch_size,
        )
    except Exception:
        log_operation(logger, Operation.WORKER_FAILED, level=logging.CRITICAL, worker="payment")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
