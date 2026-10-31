"""Standalone worker for payment authorization outbox events.

Run with python -m syncally.cli.payment_worker. PayPal credentials are read
only by this process from its environment.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from sqlalchemy.orm import Session

from syncally.config import settings
from syncally.infrastructure.database import SessionLocal
from syncally.infrastructure.gmail import GmailSMTPInvoiceNotifier
from syncally.infrastructure.offline_payments import PaymentProviderResolver
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
    repository = SqlAlchemyPaymentProcessingRepository(session_factory)
    log_operation(logger, Operation.WORKER_STARTED, worker="payment")
    while True:
        try:
            dispatch_pending_payment_events(
                session_factory,
                repository,
                provider or PaymentProviderResolver(),
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
