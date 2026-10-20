"""Real Temporal adapter for the outbox dispatcher.

The adapter starts the workflow by its stable type name, keeping workflow
definitions out of the dispatcher and API process imports.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from uuid import UUID

import temporalio.client
import temporalio.common
import temporalio.exceptions
import temporalio.service

from syncally.application.outbox import (
    WorkflowStartOutcome,
    WorkflowStartPermanentError,
    WorkflowStartTransientError,
)

_DEAL_WORKFLOW_TYPE_NAME = "DealWorkflow"

# Non-retryable gRPC statuses: retrying these (bad credentials, unknown
# namespace, malformed request) just burns time until a human fixes the config.
_PERMANENT_RPC_STATUS_CODES = frozenset(
    {
        temporalio.service.RPCStatusCode.INVALID_ARGUMENT,
        temporalio.service.RPCStatusCode.NOT_FOUND,
        temporalio.service.RPCStatusCode.PERMISSION_DENIED,
        temporalio.service.RPCStatusCode.UNAUTHENTICATED,
        temporalio.service.RPCStatusCode.UNIMPLEMENTED,
    }
)


def is_permanent_rpc_error(error: temporalio.service.RPCError) -> bool:
    return error.status in _PERMANENT_RPC_STATUS_CODES


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
        cls, *, address: str, namespace: str, task_queue: str, tls: bool = False
    ) -> TemporalDealWorkflowStarter:
        # One event loop for the worker process's whole lifetime,
        # shared by connect() and every start_deal_workflow() call, instead
        # of a fresh loop per dispatch.
        loop = asyncio.new_event_loop()
        try:
            client = loop.run_until_complete(
                temporalio.client.Client.connect(address, namespace=namespace, tls=tls)
            )
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
        except temporalio.service.RPCError as error:
            if is_permanent_rpc_error(error):
                raise WorkflowStartPermanentError(str(error)) from error
            raise WorkflowStartTransientError(str(error)) from error
        except OSError as error:
            raise WorkflowStartTransientError(str(error)) from error
