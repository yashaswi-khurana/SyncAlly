"""Real Temporal adapter for the outbox dispatcher.

The only file in this codebase that imports ``temporalio``. Starts the deal
lifecycle workflow by its string type name rather than an imported class,
since the workflow itself (S6-02) isn't built yet - this dispatcher only
needs to be able to start it once that lands.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from uuid import UUID

import temporalio.client
import temporalio.common
import temporalio.exceptions
import temporalio.service

from syncally.application.outbox import WorkflowStartOutcome, WorkflowStartTransientError

_DEAL_WORKFLOW_TYPE_NAME = "DealWorkflow"


class TemporalDealWorkflowStarter:
    """Implements ``application.outbox.DealWorkflowStarter`` against a real Temporal client."""

    def __init__(
        self, client: temporalio.client.Client, *, task_queue: str, loop: asyncio.AbstractEventLoop
    ) -> None:
        self._client = client
        self._task_queue = task_queue
        self._loop = loop

    @classmethod
    def connect(
        cls, *, address: str, namespace: str, task_queue: str
    ) -> TemporalDealWorkflowStarter:
        # One event loop for the worker process's whole lifetime,
        # shared by connect() and every start_deal_workflow() call, instead
        # of a fresh loop per dispatch.
        loop = asyncio.new_event_loop()
        try:
            client = loop.run_until_complete(temporalio.client.Client.connect(address, namespace=namespace))
        except BaseException:
            loop.close()
            raise
        return cls(client, task_queue=task_queue, loop=loop)

    def start_deal_workflow(
        self, *, workflow_id: str, deal_id: UUID, agreement_version_id: UUID
    ) -> WorkflowStartOutcome:
        try:
            self._loop.run_until_complete(
                self._client.start_workflow(
                    _DEAL_WORKFLOW_TYPE_NAME,
                    args=[{"deal_id": str(deal_id), "agreement_version_id": str(agreement_version_id)}],
                    id=workflow_id,
                    task_queue=self._task_queue,
                    id_reuse_policy=temporalio.common.WorkflowIDReusePolicy.REJECT_DUPLICATE,
                    id_conflict_policy=temporalio.common.WorkflowIDConflictPolicy.FAIL,
                    rpc_timeout=timedelta(seconds=10),
                )
            )
            return WorkflowStartOutcome.STARTED
        except temporalio.exceptions.WorkflowAlreadyStartedError:
            return WorkflowStartOutcome.ALREADY_RUNNING
        except (temporalio.service.RPCError, OSError) as error:
            raise WorkflowStartTransientError(str(error)) from error
