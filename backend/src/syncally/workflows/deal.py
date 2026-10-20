"""Deterministic Temporal orchestration for one deal's durable lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from uuid import UUID

from temporalio import workflow
from temporalio.common import RetryPolicy

WORKFLOW_SCHEMA_VERSION = 1
MAX_WORKFLOW_WAIT = timedelta(days=30)
ACTIVITY_TIMEOUT = timedelta(seconds=30)
ACTIVITY_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=4),
    maximum_attempts=3,
)
REFRESH_DEAL_STATE_ACTIVITY = "RefreshDealState"


class NotificationKind(StrEnum):
    """Small notification categories; signals never carry commercial content."""

    MESSAGE_RECEIVED = "MESSAGE_RECEIVED"
    PROPOSAL_SUBMITTED = "PROPOSAL_SUBMITTED"
    AGREEMENT_APPROVAL_RECORDED = "AGREEMENT_APPROVAL_RECORDED"
    PAYMENT_STATE_CHANGED = "PAYMENT_STATE_CHANGED"


class DealWorkflowStatus(StrEnum):
    """Process outcomes only; timeout does not update the commercial deal."""

    DOMAIN_TERMINAL = "DOMAIN_TERMINAL"
    WAIT_EXPIRED = "WAIT_EXPIRED"


@dataclass(frozen=True, slots=True)
class DealWorkflowInput:
    """Minimal, non-sensitive identifiers provided by the outbox starter."""

    deal_id: str
    agreement_version_id: str
    schema_version: int = WORKFLOW_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != WORKFLOW_SCHEMA_VERSION:
            raise ValueError(f"Unsupported deal workflow schema version: {self.schema_version}")
        _require_uuid(self.deal_id, "deal_id")
        _require_uuid(self.agreement_version_id, "agreement_version_id")


@dataclass(frozen=True, slots=True)
class DealWorkflowNotification:
    """An ID-only signal; activities reload and validate the referenced record."""

    notification_id: str
    record_id: str
    kind: NotificationKind

    def __post_init__(self) -> None:
        _require_uuid(self.notification_id, "notification_id")
        _require_uuid(self.record_id, "record_id")
        if not isinstance(self.kind, NotificationKind):
            raise ValueError("kind must be a supported notification kind")


@dataclass(frozen=True, slots=True)
class DealWorkflowResult:
    status: DealWorkflowStatus
    processed_notifications: int


def _require_uuid(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a UUID string")
    try:
        UUID(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must be a UUID string") from error


@workflow.defn(name="DealWorkflow")
class DealWorkflow:
    """Wait for durable notifications and ask an activity to reload truth.

    The activity named ``RefreshDealState`` is implemented and registered by
    the S6-03 worker. Signals are deliberately only wake-up hints: they cannot
    approve an agreement, create a payment, or otherwise change domain state.
    """

    def __init__(self) -> None:
        self._pending: list[DealWorkflowNotification] = []
        self._seen_notification_ids: set[str] = set()
        self._processed_notifications = 0

    @workflow.run
    async def run(self, workflow_input: DealWorkflowInput) -> DealWorkflowResult:
        if workflow_input.schema_version != WORKFLOW_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported deal workflow schema version: {workflow_input.schema_version}"
            )

        deadline = workflow.now() + MAX_WORKFLOW_WAIT
        while True:
            if self._pending:
                notification = self._pending.pop(0)
                is_terminal = await workflow.execute_activity(
                    REFRESH_DEAL_STATE_ACTIVITY,
                    args=[workflow_input, notification],
                    result_type=bool,
                    start_to_close_timeout=ACTIVITY_TIMEOUT,
                    retry_policy=ACTIVITY_RETRY_POLICY,
                    activity_id=f"refresh-{notification.notification_id}",
                    summary="Reload and validate current deal state",
                )
                self._processed_notifications += 1
                if is_terminal:
                    return DealWorkflowResult(
                        DealWorkflowStatus.DOMAIN_TERMINAL,
                        self._processed_notifications,
                    )
                continue

            remaining = deadline - workflow.now()
            if remaining <= timedelta(0):
                return DealWorkflowResult(
                    DealWorkflowStatus.WAIT_EXPIRED,
                    self._processed_notifications,
                )
            try:
                await workflow.wait_condition(
                    lambda: bool(self._pending),
                    timeout=remaining,
                    timeout_summary="deal-lifecycle-wait-deadline",
                )
            except TimeoutError:
                return DealWorkflowResult(
                    DealWorkflowStatus.WAIT_EXPIRED,
                    self._processed_notifications,
                )

    @workflow.signal
    def notify(self, notification: DealWorkflowNotification) -> None:
        """Queue one notification once; duplicated event IDs are ignored."""
        if notification.notification_id in self._seen_notification_ids:
            return
        self._seen_notification_ids.add(notification.notification_id)
        self._pending.append(notification)

    @workflow.query
    def processed_notification_count(self) -> int:
        """Expose progress for health checks and deterministic workflow tests."""
        return self._processed_notifications
