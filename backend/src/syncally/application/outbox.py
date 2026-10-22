"""Outbox relay: deliver committed deal notifications to Temporal.

The outbox row is written in the same transaction as the business change
(see ``commit_agreement`` in ``application/agreements.py``) and read later by
a dispatcher. This module is the provider-independent boundary: it never
imports SQLAlchemy or temporalio, so the dispatch rule can be tested against
a fake starter.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol
from uuid import UUID

from syncally.application.workflow_notifications import (
    DealWorkflowNotification,
    NotificationKind,
)


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
        self,
        *,
        workflow_id: str,
        deal_id: UUID,
        agreement_version_id: UUID | None,
        notification: DealWorkflowNotification,
    ) -> WorkflowStartOutcome:
        """Start the workflow or deliver a notification to its active execution."""


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
    """Start or signal the Temporal workflow for one outbox event.

Only deal and referenced-record IDs plus a fixed notification kind are
read from the payload and passed on. No other payload field can reach
Temporal through this function.
    """
    try:
        try:
            if not isinstance(event.payload, Mapping):
                raise ValueError("payload must be an object")
            if event.event_type == "AGREEMENT_COMMITTED":
                record_key = "agreement_version_id"
                notification_kind = "AGREEMENT_COMMITTED"
            elif event.event_type == "DEAL_NOTIFICATION":
                record_key = "record_id"
                notification_kind = event.payload.get("kind")
            else:
                raise WorkflowStartPermanentError("Outbox dispatcher cannot handle this event type")
            for key in ("deal_id", record_key):
                if not isinstance(event.payload[key], str):
                    raise ValueError(f"{key} must be a UUID string")
            deal_id = UUID(event.payload["deal_id"])
            record_id = UUID(event.payload[record_key])
            notification = DealWorkflowNotification(
                notification_id=str(event.id),
                record_id=str(record_id),
                kind=NotificationKind(notification_kind),
            )
        except (KeyError, TypeError, ValueError) as error:
            # Do not persist the invalid value: it may contain private text.
            raise WorkflowStartPermanentError("Malformed outbox payload: expected UUID IDs") from error
        starter.start_deal_workflow(
            workflow_id=build_deal_workflow_id(deal_id),
            deal_id=deal_id,
            agreement_version_id=record_id if event.event_type == "AGREEMENT_COMMITTED" else None,
            notification=notification,
        )
    except WorkflowStartPermanentError:
        return OutboxDispatchResult(
            delivered=False,
            permanent_failure=True,
            error_detail="Workflow dispatch rejected; inspect event identifiers and configuration.",
        )
    except WorkflowStartError:
        return OutboxDispatchResult(
            delivered=False,
            error_detail="Workflow service unavailable; delivery will retry.",
        )
    except Exception:
        # Never persist provider/DB exception text, parameters or private payloads.
        return OutboxDispatchResult(
            delivered=False,
            error_detail="Workflow dispatch failed unexpectedly; delivery will retry.",
        )
    return OutboxDispatchResult(delivered=True)
