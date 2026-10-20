"""Tests for the standalone workflow worker entry point."""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from temporalio.service import RPCError, RPCStatusCode
from temporalio.testing import WorkflowEnvironment

from syncally.application.workflow_notifications import (
    DealWorkflowNotification,
    NotificationKind,
)
from syncally.domain.deals.deal import DealStatus
from syncally.infrastructure.models import Base, Organization
from syncally.infrastructure.models import Deal as DealRow
from syncally.workflows.deal import (
    REFRESH_DEAL_STATE_ACTIVITY,
    DealWorkflow,
    DealWorkflowInput,
    DealWorkflowStatus,
)
from syncally.workflows.worker import (
    CONNECT_RETRY_INTERVAL_SECONDS,
    GRACEFUL_SHUTDOWN_TIMEOUT,
    SHUTDOWN_SIGNALS,
    _connect_with_retry,
    _register_shutdown_handlers,
    _request_shutdown,
    create_worker,
    run_worker,
    workflow_activities,
)

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_TEMPORAL_TEST_SERVER_ERROR: str | None = None


class WorkflowWorkerTests(unittest.TestCase):
    def test_registers_the_refresh_activity_on_the_worker(self) -> None:
        activities = workflow_activities(lambda: None)

        self.assertEqual(len(activities), 1)
        self.assertEqual(
            getattr(activities[0], "__temporal_activity_definition").name,
            REFRESH_DEAL_STATE_ACTIVITY,
        )

    def test_create_worker_registers_the_deal_workflow(self) -> None:
        with (
            ThreadPoolExecutor(max_workers=1) as activity_executor,
            patch("syncally.workflows.worker.Worker") as worker_class,
        ):
            create_worker(
                object(),
                task_queue="deals",
                activity_executor=activity_executor,
                session_factory=lambda: None,
            )

        worker_class.assert_called_once()
        _, kwargs = worker_class.call_args
        self.assertEqual(kwargs["task_queue"], "deals")
        self.assertEqual(kwargs["workflows"], [DealWorkflow])
        self.assertIs(kwargs["activity_executor"], activity_executor)
        self.assertEqual(
            kwargs["graceful_shutdown_timeout"], GRACEFUL_SHUTDOWN_TIMEOUT
        )
        self.assertEqual(
            getattr(kwargs["activities"][0], "__temporal_activity_definition").name,
            REFRESH_DEAL_STATE_ACTIVITY,
        )

    def test_worker_does_not_start_api_routes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys; import syncally.workflows.worker; "
                    "assert 'syncally.api.main' not in sys.modules; "
                    "assert 'fastapi' not in sys.modules"
                ),
            ],
            cwd=_BACKEND_DIR,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_api_does_not_start_the_worker(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys; import syncally.api.main; "
                    "assert 'syncally.workflows.worker' not in sys.modules"
                ),
            ],
            cwd=_BACKEND_DIR,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)


class ConnectWithRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_retries_transient_rpc_failure_then_returns_client(self) -> None:
        client = object()
        error = RPCError("unavailable", RPCStatusCode.UNAVAILABLE, b"")
        connect = AsyncMock(side_effect=[error, client])

        with (
            patch("syncally.workflows.worker.temporalio.client.Client.connect", connect),
            patch("syncally.workflows.worker.asyncio.sleep", new=AsyncMock()) as sleep,
            patch("syncally.workflows.worker.logger") as logger,
        ):
            result = await _connect_with_retry(
                address="localhost:7233", namespace="default"
            )

        self.assertIs(result, client)
        self.assertEqual(connect.await_count, 2)
        sleep.assert_awaited_once_with(CONNECT_RETRY_INTERVAL_SECONDS)
        logger.exception.assert_called_once()

    async def test_retries_transient_exceptions_then_returns_client(self) -> None:
        client = object()
        error = OSError("connection refused")
        connect = AsyncMock(side_effect=[error, client])

        with (
            patch("syncally.workflows.worker.temporalio.client.Client.connect", connect),
            patch("syncally.workflows.worker.asyncio.sleep", new=AsyncMock()) as sleep,
            patch("syncally.workflows.worker.logger"),
        ):
            result = await _connect_with_retry(
                address="localhost:7233", namespace="default"
            )

        self.assertIs(result, client)
        self.assertEqual(connect.await_count, 2)
        sleep.assert_awaited_once_with(CONNECT_RETRY_INTERVAL_SECONDS)

    async def test_permanent_rpc_error_raises_without_retrying(self) -> None:
        error = RPCError("permission denied", RPCStatusCode.PERMISSION_DENIED, b"")
        connect = AsyncMock(side_effect=error)

        with (
            patch("syncally.workflows.worker.temporalio.client.Client.connect", connect),
            patch("syncally.workflows.worker.asyncio.sleep", new=AsyncMock()) as sleep,
            patch("syncally.workflows.worker.logger") as logger,
        ):
            with self.assertRaises(RPCError) as raised:
                await _connect_with_retry(
                    address="localhost:7233", namespace="default"
                )

        self.assertIs(raised.exception, error)
        self.assertEqual(connect.await_count, 1)
        sleep.assert_not_awaited()
        logger.error.assert_called_once()

    async def test_cancellation_propagates_without_retrying(self) -> None:
        connect = AsyncMock(side_effect=asyncio.CancelledError())

        with (
            patch("syncally.workflows.worker.temporalio.client.Client.connect", connect),
            patch("syncally.workflows.worker.asyncio.sleep", new=AsyncMock()) as sleep,
        ):
            with self.assertRaises(asyncio.CancelledError):
                await _connect_with_retry(
                    address="localhost:7233", namespace="default"
                )

        self.assertEqual(connect.await_count, 1)
        sleep.assert_not_awaited()


class WorkerShutdownSignalTests(unittest.IsolatedAsyncioTestCase):
    async def test_signal_callback_requests_graceful_shutdown(self) -> None:
        worker = MagicMock()
        worker.shutdown = AsyncMock()

        _request_shutdown(worker, "SIGTERM")
        await asyncio.sleep(0)

        worker.shutdown.assert_awaited_once_with()

    def test_registers_all_supported_shutdown_signals(self) -> None:
        loop = MagicMock()
        worker = MagicMock()

        installed = _register_shutdown_handlers(loop, worker)

        self.assertEqual(installed, list(SHUTDOWN_SIGNALS))
        self.assertEqual(loop.add_signal_handler.call_count, len(SHUTDOWN_SIGNALS))
        for call, signal_number in zip(
            loop.add_signal_handler.call_args_list, SHUTDOWN_SIGNALS, strict=True
        ):
            self.assertEqual(
                call.args,
                (signal_number, _request_shutdown, worker, signal_number.name),
            )

    def test_unsupported_signal_handler_does_not_break_startup(self) -> None:
        loop = MagicMock()
        loop.add_signal_handler.side_effect = [NotImplementedError, None]
        worker = MagicMock()

        installed = _register_shutdown_handlers(loop, worker)

        self.assertEqual(installed, [signal.SIGINT])


class RunWorkerExecutorTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_worker_shuts_down_executor_after_worker_exits(self) -> None:
        executor = MagicMock()
        worker = MagicMock()
        worker.run = AsyncMock()

        with (
            patch(
                "syncally.workflows.worker.concurrent.futures.ThreadPoolExecutor",
                return_value=executor,
            ),
            patch("syncally.workflows.worker.create_worker", return_value=worker),
            patch(
                "syncally.workflows.worker.temporalio.client.Client.connect",
                new=AsyncMock(return_value=object()),
            ),
        ):
            await run_worker(address="localhost:7233", namespace="default", task_queue="deals")

        executor.shutdown.assert_called_once_with(wait=True)

    async def test_run_worker_shuts_down_executor_when_worker_raises(self) -> None:
        executor = MagicMock()
        worker = MagicMock()
        worker.run = AsyncMock(side_effect=RuntimeError("worker failed"))

        with (
            patch(
                "syncally.workflows.worker.concurrent.futures.ThreadPoolExecutor",
                return_value=executor,
            ),
            patch("syncally.workflows.worker.create_worker", return_value=worker),
            patch(
                "syncally.workflows.worker.temporalio.client.Client.connect",
                new=AsyncMock(return_value=object()),
            ),
        ):
            with self.assertRaises(RuntimeError):
                await run_worker(
                    address="localhost:7233", namespace="default", task_queue="deals"
                )

        executor.shutdown.assert_called_once_with(wait=True)


class WorkflowWorkerIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        global _TEMPORAL_TEST_SERVER_ERROR
        if _TEMPORAL_TEST_SERVER_ERROR is not None:
            self.skipTest(f"Temporal test server unavailable: {_TEMPORAL_TEST_SERVER_ERROR}")
        try:
            self.environment = await WorkflowEnvironment.start_time_skipping(
                test_server_existing_path=os.environ.get("SYNCALLY_TEMPORAL_TEST_SERVER")
            )
        except RuntimeError as error:
            message = str(error)
            if "failed to download ephemeral server executable" not in message.lower():
                raise
            _TEMPORAL_TEST_SERVER_ERROR = message
            self.skipTest(f"Temporal test server unavailable: {message}")

        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        buyer_id = uuid4()
        seller_id = uuid4()
        self.deal_id = uuid4()
        with Session(self.engine) as db:
            db.add_all(
                [
                    Organization(id=buyer_id, legal_name="Buyer Co", country_code="US"),
                    Organization(id=seller_id, legal_name="Seller Co", country_code="CA"),
                    DealRow(
                        id=self.deal_id,
                        buyer_organization_id=buyer_id,
                        seller_organization_id=seller_id,
                        status=DealStatus.DRAFT.value,
                        version=0,
                    ),
                ]
            )
            db.commit()
        self.task_queue = f"deal-worker-integration-tests-{uuid4()}"

    async def asyncTearDown(self) -> None:
        if hasattr(self, "engine"):
            Base.metadata.drop_all(self.engine)
            self.engine.dispose()
        if hasattr(self, "environment"):
            await self.environment.shutdown()

    async def test_real_worker_reloads_persisted_deal_state(self) -> None:
        executor = ThreadPoolExecutor(max_workers=2)
        try:
            worker = create_worker(
                self.environment.client,
                task_queue=self.task_queue,
                activity_executor=executor,
                session_factory=lambda: Session(self.engine),
            )
            await worker.__aenter__()
            try:
                workflow_input = DealWorkflowInput(
                    deal_id=str(self.deal_id),
                    agreement_version_id=None,
                )
                handle = await self.environment.client.start_workflow(
                    DealWorkflow.run,
                    workflow_input,
                    id=f"deal/{self.deal_id}/lifecycle",
                    task_queue=self.task_queue,
                )

                await handle.signal(DealWorkflow.notify, self._notification())
                await self._wait_for_processed_notifications(handle, 1)

                self.assertEqual((await handle.describe()).status.name, "RUNNING")
                self.assertEqual(self._deal_status(), DealStatus.DRAFT.value)

                with Session(self.engine) as db:
                    db.execute(
                        update(DealRow)
                        .where(DealRow.id == self.deal_id)
                        .values(status=DealStatus.COMPLETED.value)
                    )
                    db.commit()
                await handle.signal(DealWorkflow.notify, self._notification())

                async with asyncio.timeout(10):
                    result = await handle.result()
            finally:
                await worker.__aexit__(None, None, None)
        finally:
            executor.shutdown(wait=True)

        self.assertEqual(result.status, DealWorkflowStatus.DOMAIN_TERMINAL)
        self.assertEqual(result.processed_notifications, 2)

    def _deal_status(self) -> str:
        with Session(self.engine) as db:
            deal = db.get(DealRow, self.deal_id)
            self.assertIsNotNone(deal)
            return deal.status

    def _notification(self) -> DealWorkflowNotification:
        return DealWorkflowNotification(
            notification_id=str(uuid4()),
            record_id=str(uuid4()),
            kind=NotificationKind.AGREEMENT_APPROVAL_RECORDED,
        )

    async def _wait_for_processed_notifications(self, handle, count: int) -> None:
        async with asyncio.timeout(5):
            while await handle.query(DealWorkflow.processed_notification_count) < count:
                await asyncio.sleep(0.01)


if __name__ == "__main__":
    unittest.main()
