"""Standalone process that relays pending outbox rows to Temporal.

Run with ``python -m syncally.cli.outbox_worker``. A fully separate process
from the FastAPI app: starting the API never starts this worker, and vice
versa.
"""

from __future__ import annotations

import logging
import time

import temporalio.service

from syncally.config import settings
from syncally.infrastructure.database import SessionLocal
from syncally.infrastructure.outbox import dispatch_pending_outbox_events
from syncally.infrastructure.temporal import TemporalDealWorkflowStarter, is_permanent_rpc_error

logger = logging.getLogger(__name__)


def _connect_with_retry(*, poll_interval: float) -> TemporalDealWorkflowStarter:
    while True:
        try:
            return TemporalDealWorkflowStarter.connect(
                address=settings.temporal_address,
                namespace=settings.temporal_namespace,
                task_queue=settings.temporal_task_queue,
                tls=settings.temporal_tls,
            )
        except temporalio.service.RPCError as error:
            if is_permanent_rpc_error(error):
                logger.error("Permanent Temporal connection failure, not retrying: %s", error)
                raise
            logger.exception("Failed to connect to Temporal, retrying")
            time.sleep(poll_interval)
        except Exception:
            logger.exception("Failed to connect to Temporal, retrying")
            time.sleep(poll_interval)


def run_forever(*, poll_interval: float, batch_size: int) -> None:
    starter = _connect_with_retry(poll_interval=poll_interval)
    while True:
        try:
            dispatch_pending_outbox_events(SessionLocal, starter, batch_size=batch_size)
        except Exception:
            logger.exception("Outbox dispatch iteration failed")
        time.sleep(poll_interval)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    run_forever(
        poll_interval=settings.outbox_poll_interval_seconds,
        batch_size=settings.outbox_batch_size,
    )


if __name__ == "__main__":
    main()
