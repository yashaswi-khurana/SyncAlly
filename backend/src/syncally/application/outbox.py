"""Outbox relay: deliver committed-agreement events to Temporal.

The outbox row is written in the same transaction as the business change
(see ``commit_agreement`` in ``application/agreements.py``) and read later by
a dispatcher. This module is the provider-independent boundary: it never
imports SQLAlchemy or temporalio, so the dispatch rule can be tested against
a fake starter.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol
from uuid import UUID

logger = logging.getLogger(__name__)


def build_deal_workflow_id(deal_id: UUID) -> str:
    """The stable Temporal workflow ID for one deal's lifecycle workflow."""
    return f"deal/{deal_id}/lifecycle"


class WorkflowStartOutcome(Enum):
    STARTED = "STARTED"
    ALREADY_RUNNING = "ALREADY_RUNNING"


class WorkflowStartError(Exception):
    """Base class for a failed workflow-start attempt."""


class WorkflowStartTransientError(WorkflowStartError):
    """A retryable failure, such as Temporal being unreachable."""


class WorkflowStartPermanentError(WorkflowStartError):
    """A non-retryable failure, such as an outbox event this dispatcher cannot handle."""


class DealWorkflowStarter(Protocol):
    """The boundary a Temporal client adapter implements.

    ``already started`` must be treated as success: implementations raise
    only ``WorkflowStartTransientError``/``WorkflowStartPermanentError``,
    never surface Temporal's own "already started" error as a failure.
    """

    def start_deal_workflow(
        self, *, workflow_id: str, deal_id: UUID, agreement_version_id: UUID
    ) -> WorkflowStartOutcome:
        """Start (or confirm already running) one deal lifecycle workflow."""


@dataclass(frozen=True, slots=True)
class PendingOutboxEvent:
    """The DB-free view of one outbox row this module needs to dispatch it."""

    id: UUID
    event_type: str
    payload: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class OutboxDispatchResult:
    delivered: bool
    permanent_failure: bool = False
    error_detail: str | None = None


def dispatch_outbox_event(
    event: PendingOutboxEvent, starter: DealWorkflowStarter
) -> OutboxDispatchResult:
    """Start the Temporal workflow for one outbox event.

    Only ``deal_id`` and ``agreement_version_id`` are ever read out of the
    payload and passed on - no other payload field, present or future, can
    reach the starter through this function.
    """
    try:
        if event.event_type != "AGREEMENT_COMMITTED":
            raise WorkflowStartPermanentError(
                f"Outbox dispatcher cannot handle event_type {event.event_type!r}"
            )
        try:
            if not isinstance(event.payload, Mapping):
                raise ValueError("payload must be an object")
            for key in ("deal_id", "agreement_version_id"):
                if not isinstance(event.payload[key], str):
                    raise ValueError(f"{key} must be a UUID string")
            deal_id = UUID(event.payload["deal_id"])
            agreement_version_id = UUID(event.payload["agreement_version_id"])
        except (KeyError, ValueError) as error:
            # Do not persist the invalid value: it may contain private text.
            raise WorkflowStartPermanentError("Malformed outbox payload: expected UUID IDs") from error
        starter.start_deal_workflow(
            workflow_id=build_deal_workflow_id(deal_id),
            deal_id=deal_id,
            agreement_version_id=agreement_version_id,
        )
    except WorkflowStartPermanentError as error:
        logger.error("Outbox event %s permanently failed: %s", event.id, error)
        return OutboxDispatchResult(delivered=False, permanent_failure=True, error_detail=str(error))
    except WorkflowStartError as error:
        logger.warning("Outbox event %s failed, will retry: %s", event.id, error)
        return OutboxDispatchResult(delivered=False, error_detail=str(error))
    except Exception as error:
        # An unexpected starter error must still resolve to a retry outcome,
        # or it would escape to the caller and block every later row in the batch.
        logger.exception("Outbox event %s raised an unexpected error, will retry", event.id)
        return OutboxDispatchResult(delivered=False, error_detail=str(error))
    return OutboxDispatchResult(delivered=True)
