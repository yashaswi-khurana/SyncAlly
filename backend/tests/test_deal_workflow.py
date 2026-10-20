"""Temporal tests for durable deal notifications and bounded waiting."""

from __future__ import annotations

import asyncio
import os
import unittest
from dataclasses import dataclass
from uuid import uuid4

from temporalio import activity
from temporalio.client import WorkflowFailureError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from syncally.workflows.deal import (
    REFRESH_DEAL_STATE_ACTIVITY,
    DealWorkflow,
    DealWorkflowInput,
    DealWorkflowNotification,
    DealWorkflowResult,
    DealWorkflowStatus,
    NotificationKind,
)

_TEMPORAL_TEST_SERVER_ERROR: str | None = None


@dataclass(frozen=True)
class RefreshCall:
    workflow_input: DealWorkflowInput
    notification: DealWorkflowNotification


class RefreshActivity:
    def __init__(self) -> None:
        self.calls: list[RefreshCall] = []
        self.terminal_record_ids: set[str] = set()
        self.failures_remaining = 0

    @activity.defn(name=REFRESH_DEAL_STATE_ACTIVITY)
    async def refresh(
        self,
        workflow_input: DealWorkflowInput,
        notification: DealWorkflowNotification,
    ) -> bool:
        if self.failures_remaining:
            self.failures_remaining -= 1
            raise RuntimeError("temporary activity failure")
        self.calls.append(RefreshCall(workflow_input, notification))
        return notification.record_id in self.terminal_record_ids


def new_workflow_input() -> DealWorkflowInput:
    return DealWorkflowInput(
        deal_id=str(uuid4()),
        agreement_version_id=str(uuid4()),
    )


def new_notification(
    *, notification_id: str | None = None, record_id: str | None = None
) -> DealWorkflowNotification:
    return DealWorkflowNotification(
        notification_id=notification_id or str(uuid4()),
        record_id=record_id or str(uuid4()),
        kind=NotificationKind.AGREEMENT_APPROVAL_RECORDED,
    )


class DealWorkflowUnitTests(unittest.TestCase):
    def test_duplicate_signal_ids_are_queued_once(self) -> None:
        workflow = DealWorkflow()
        notification = new_notification()

        workflow.notify(notification)
        workflow.notify(notification)

        self.assertEqual(workflow._pending, [notification])
        self.assertEqual(workflow._seen_notification_ids, {notification.notification_id})

    def test_workflow_input_rejects_unsupported_schema_and_invalid_ids(self) -> None:
        with self.assertRaises(ValueError):
            DealWorkflowInput(str(uuid4()), str(uuid4()), schema_version=2)
        with self.assertRaises(ValueError):
            DealWorkflowInput("not-a-uuid", str(uuid4()))


class DealWorkflowTests(unittest.IsolatedAsyncioTestCase):
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
        self.task_queue = f"deal-workflow-tests-{uuid4()}"
        self.input = new_workflow_input()
        self.activity = RefreshActivity()

    async def asyncTearDown(self) -> None:
        if hasattr(self, "environment"):
            await self.environment.shutdown()

    async def start_worker(self) -> Worker:
        worker = Worker(
            self.environment.client,
            task_queue=self.task_queue,
            workflows=[DealWorkflow],
            activities=[self.activity.refresh],
            max_cached_workflows=0,
        )
        await worker.__aenter__()
        return worker

    async def test_duplicate_and_out_of_order_signals_only_refresh_once_per_id(self) -> None:
        worker = await self.start_worker()
        try:
            handle = await self.environment.client.start_workflow(
                DealWorkflow.run,
                self.input,
                id=f"deal/{self.input.deal_id}/lifecycle",
                task_queue=self.task_queue,
            )
            first = new_notification()
            second = new_notification()
            await handle.signal(DealWorkflow.notify, second)
            await handle.signal(DealWorkflow.notify, first)
            await handle.signal(DealWorkflow.notify, second)

            await self._wait_for_calls(2)
            self.assertEqual(
                {call.notification.notification_id for call in self.activity.calls},
                {first.notification_id, second.notification_id},
            )
            self.assertTrue(
                all(call.workflow_input.deal_id == self.input.deal_id for call in self.activity.calls)
            )
            await handle.cancel()
        finally:
            await worker.__aexit__(None, None, None)

    async def test_pending_workflow_resumes_after_worker_restart(self) -> None:
        first_worker = await self.start_worker()
        handle = await self.environment.client.start_workflow(
            DealWorkflow.run,
            self.input,
            id=f"deal/{self.input.deal_id}/lifecycle",
            task_queue=self.task_queue,
        )
        first = new_notification()
        await handle.signal(DealWorkflow.notify, first)
        await self._wait_for_calls(1)
        await self._wait_for_processed_notifications(handle, 1)
        await first_worker.__aexit__(None, None, None)

        # The workflow must replay its durable history on the replacement worker.
        duplicate = first
        terminal_record_id = str(uuid4())
        terminal = new_notification(record_id=terminal_record_id)
        self.activity.terminal_record_ids.add(terminal_record_id)

        second_worker = await self.start_worker()
        try:
            await handle.signal(DealWorkflow.notify, duplicate)
            await handle.signal(DealWorkflow.notify, terminal)
            await self._wait_for_processed_notifications(handle, 2)
            async with asyncio.timeout(10):
                result = await handle.result()
        finally:
            await second_worker.__aexit__(None, None, None)

        self.assertEqual(result.status, DealWorkflowStatus.DOMAIN_TERMINAL)
        self.assertEqual(
            [call.notification.notification_id for call in self.activity.calls],
            [first.notification_id, terminal.notification_id],
        )

    async def test_wait_timeout_returns_neutral_status_without_approving_or_paying(self) -> None:
        worker = await self.start_worker()
        try:
            handle = await self.environment.client.start_workflow(
                DealWorkflow.run,
                self.input,
                id=f"deal/{self.input.deal_id}/lifecycle",
                task_queue=self.task_queue,
            )

            result = await handle.result()

            self.assertEqual(result, DealWorkflowResult(DealWorkflowStatus.WAIT_EXPIRED, 0))
            self.assertEqual(self.activity.calls, [])
        finally:
            await worker.__aexit__(None, None, None)

    async def test_activity_retries_are_bounded(self) -> None:
        self.activity.failures_remaining = 5
        worker = await self.start_worker()
        try:
            handle = await self.environment.client.start_workflow(
                DealWorkflow.run,
                self.input,
                id=f"deal/{self.input.deal_id}/lifecycle",
                task_queue=self.task_queue,
            )
            await handle.signal(DealWorkflow.notify, new_notification())

            with self.assertRaises(WorkflowFailureError):
                await handle.result()

            self.assertEqual(self.activity.failures_remaining, 2)
        finally:
            await worker.__aexit__(None, None, None)

    async def _wait_for_calls(self, count: int) -> None:
        async with asyncio.timeout(5):
            while len(self.activity.calls) < count:
                await asyncio.sleep(0.01)

    async def _wait_for_processed_notifications(self, handle, count: int) -> None:
        async with asyncio.timeout(5):
            while await handle.query(DealWorkflow.processed_notification_count) < count:
                await asyncio.sleep(0.01)


if __name__ == "__main__":
    unittest.main()
