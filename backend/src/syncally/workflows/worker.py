"""Standalone Temporal worker for deal lifecycle workflows.

Run with ``python -m syncally.workflows.worker``. This process imports no
FastAPI application or API routes: the HTTP API and the workflow worker are
started independently over the same database and application services.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging

import temporalio.client
import temporalio.service
from temporalio.worker import Worker

from syncally.config import settings
from syncally.infrastructure.temporal import is_permanent_rpc_error
from syncally.workflows.activities import RefreshDealStateActivity, SessionFactory
from syncally.workflows.deal import DealWorkflow

logger = logging.getLogger(__name__)

ACTIVITY_EXECUTOR_MAX_WORKERS = 10
CONNECT_RETRY_INTERVAL_SECONDS = 2.0


async def _connect_with_retry(
    *,
    address: str,
    namespace: str,
    tls: bool = False,
) -> temporalio.client.Client:
    """Connect to Temporal, retrying transient startup failures indefinitely."""
    while True:
        try:
            return await temporalio.client.Client.connect(
                address,
                namespace=namespace,
                tls=tls,
            )
        except temporalio.service.RPCError as error:
            if is_permanent_rpc_error(error):
                logger.error(
                    "Permanent Temporal connection failure, not retrying: %s", error
                )
                raise
            logger.exception("Failed to connect to Temporal, retrying")
            await asyncio.sleep(CONNECT_RETRY_INTERVAL_SECONDS)
        except Exception:
            logger.exception("Failed to connect to Temporal, retrying")
            await asyncio.sleep(CONNECT_RETRY_INTERVAL_SECONDS)



def workflow_activities(session_factory: SessionFactory | None = None) -> list:
    """Build the activity callables registered on the worker task queue."""
    activity_instance = RefreshDealStateActivity(session_factory)
    return [activity_instance.refresh_deal_state]


def create_worker(
    client: temporalio.client.Client,
    *,
    task_queue: str,
    activity_executor: concurrent.futures.Executor,
    session_factory: SessionFactory | None = None,
) -> Worker:
    """Create the deal workflow worker without connecting to Temporal."""
    return Worker(
        client,
        task_queue=task_queue,
        workflows=[DealWorkflow],
        activities=workflow_activities(session_factory),
        activity_executor=activity_executor,
    )


async def run_worker(
    *,
    address: str,
    namespace: str,
    task_queue: str,
    tls: bool = False,
    session_factory: SessionFactory | None = None,
) -> None:
    client = await _connect_with_retry(
        address=address,
        namespace=namespace,
        tls=tls,
    )
    activity_executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=ACTIVITY_EXECUTOR_MAX_WORKERS
    )
    try:
        worker = create_worker(
            client,
            task_queue=task_queue,
            activity_executor=activity_executor,
            session_factory=session_factory,
        )
        logger.info("Starting deal workflow worker on task queue %s", task_queue)
        await worker.run()
    finally:
        activity_executor.shutdown(wait=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(
        run_worker(
            address=settings.temporal_address,
            namespace=settings.temporal_namespace,
            task_queue=settings.temporal_task_queue,
            tls=settings.temporal_tls,
        )
    )


if __name__ == "__main__":
    main()
