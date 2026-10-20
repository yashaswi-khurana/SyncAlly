"""Deterministic Temporal orchestration for one deal's durable lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

from syncally.application.workflow_notifications import (
    DealWorkflowNotification,
)
from syncally.application.workflow_notifications import (
    NotificationKind as NotificationKind,
)
from syncally.workflows.errors import NON_RETRYABLE_ACTIVITY_ERROR_TYPES

WORKFLOW_SCHEMA_VERSION = 2
MAX_WORKFLOW_WAIT = timedelta(days=30)
ACTIVITY_TIMEOUT = timedelta(seconds=30)
MAX_PENDING_NOTIFICATIONS = 256
MAX_REMEMBERED_NOTIFICATION_IDS = 1024
MAX_NOTIFICATIONS_PER_RUN = 100
ACTIVITY_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=4),
    maximum_attempts=3,
    non_retryable_error_types=NON_RETRYABLE_ACTIVITY_ERROR_TYPES,
)
REFRESH_DEAL_STATE_ACTIVITY = "RefreshDealState"


class DealWorkflowStatus(StrEnum):
    """Process outcomes only; timeout does not update the commercial deal."""

    DOMAIN_TERMINAL = "DOMAIN_TERMINAL"
    WAIT_EXPIRED = "WAIT_EXPIRED"


@dataclass(frozen=True, slots=True)
class DealWorkflowInput:
    """Non-sensitive start identifiers and bounded durable continuation state."""

    deal_id: str
    agreement_version_id: str | None
    schema_version: int = WORKFLOW_SCHEMA_VERSION
    deadline: datetime | None = None
    pending_notifications: tuple[DealWorkflowNotification, ...] = ()
    seen_notification_ids: tuple[str, ...] = ()
    processed_notifications: int = 0
    continue_after_notifications: int = MAX_NOTIFICATIONS_PER_RUN

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version not in (1, 2):
            raise ValueError(f"Unsupported deal workflow schema version: {self.schema_version}")
        _require_uuid(self.deal_id, "deal_id")
        if self.agreement_version_id is not None:
            _require_uuid(self.agreement_version_id, "agreement_version_id")
        if len(self.pending_notifications) > MAX_PENDING_NOTIFICATIONS:
            raise ValueError("pending_notifications exceeds the workflow limit")
        if len(self.seen_notification_ids) > MAX_REMEMBERED_NOTIFICATION_IDS:
            raise ValueError("seen_notification_ids exceeds the workflow limit")
        if (
            type(self.continue_after_notifications) is not int
            or not 1 <= self.continue_after_notifications <= MAX_NOTIFICATIONS_PER_RUN
        ):
            raise ValueError("continue_after_notifications is outside the supported range")
        if type(self.processed_notifications) is not int or self.processed_notifications < 0:
            raise ValueError("processed_notifications must be a non-negative integer")


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
        self._seen_notification_order: list[str] = []
        self._processed_notifications = 0
        self._processed_this_run = 0

    @workflow.run
    async def run(self, workflow_input: DealWorkflowInput) -> DealWorkflowResult:
        if workflow_input.schema_version not in (1, WORKFLOW_SCHEMA_VERSION):
            raise ValueError(
                f"Unsupported deal workflow schema version: {workflow_input.schema_version}"
            )

        deadline = workflow_input.deadline or (workflow.now() + MAX_WORKFLOW_WAIT)
        observed_pending = self._pending.copy()
        observed_seen_ids = tuple(self._seen_notification_order)
        self._pending = []
        self._seen_notification_ids.clear()
        self._seen_notification_order.clear()
        continuation_pending_ids = {
            notification.notification_id for notification in workflow_input.pending_notifications
        }
        observed_pending_ids = {notification.notification_id for notification in observed_pending}
        self._remember_notification_ids(
            tuple(
                notification_id
                for notification_id in workflow_input.seen_notification_ids
                if notification_id not in continuation_pending_ids
            )
        )
        self._remember_notification_ids(
            tuple(
                notification_id
                for notification_id in observed_seen_ids
                if notification_id not in observed_pending_ids
            )
        )
        for notification in (*workflow_input.pending_notifications, *observed_pending):
            self.notify(notification)
        self._processed_notifications = workflow_input.processed_notifications

        while True:
            remaining = deadline - workflow.now()
            if remaining <= timedelta(0):
                workflow.logger.warning(
                    "Deal workflow wait expired; deal requires operational review",
                    extra={"deal_id": workflow_input.deal_id},
                )
                return DealWorkflowResult(
                    DealWorkflowStatus.WAIT_EXPIRED,
                    self._processed_notifications,
                )

            if self._pending:
                notification = self._pending.pop(0)
                activity_input = replace(
                    workflow_input,
                    deadline=None,
                    pending_notifications=(),
                    seen_notification_ids=(),
                    processed_notifications=0,
                )
                try:
                    is_terminal = await workflow.execute_activity(
                        REFRESH_DEAL_STATE_ACTIVITY,
                        args=[activity_input, notification],
                        result_type=bool,
                        start_to_close_timeout=min(ACTIVITY_TIMEOUT, remaining),
                        schedule_to_close_timeout=remaining,
                        retry_policy=ACTIVITY_RETRY_POLICY,
                        activity_id=(
                            f"refresh-{self._processed_notifications + 1}-"
                            f"{notification.notification_id}"
                        ),
                        summary="Reload and validate current deal state",
                    )
                except ActivityError:
                    if deadline - workflow.now() <= timedelta(0):
                        workflow.logger.warning(
                            "Deal workflow refresh timed out at its deadline",
                            extra={"deal_id": workflow_input.deal_id},
                        )
                        return DealWorkflowResult(
                            DealWorkflowStatus.WAIT_EXPIRED,
                            self._processed_notifications,
                        )
                    raise
                self._processed_notifications += 1
                self._processed_this_run += 1
                if is_terminal:
                    return DealWorkflowResult(
                        DealWorkflowStatus.DOMAIN_TERMINAL,
                        self._processed_notifications,
                    )
                if workflow.patched("deal-workflow-history-rollover-v1") and (
                    self._processed_this_run >= workflow_input.continue_after_notifications
                ):
                    workflow.continue_as_new(
                        replace(
                            workflow_input,
                            deadline=deadline,
                            pending_notifications=tuple(self._pending),
                            seen_notification_ids=tuple(self._seen_notification_order),
                            processed_notifications=self._processed_notifications,
                        )
                    )
                continue

            try:
                await workflow.wait_condition(
                    lambda: bool(self._pending),
                    timeout=remaining,
                    timeout_summary="deal-lifecycle-wait-deadline",
                )
            except TimeoutError:
                workflow.logger.warning(
                    "Deal workflow wait expired; deal requires operational review",
                    extra={"deal_id": workflow_input.deal_id},
                )
                return DealWorkflowResult(
                    DealWorkflowStatus.WAIT_EXPIRED,
                    self._processed_notifications,
                )

    @workflow.signal
    def notify(self, notification: DealWorkflowNotification) -> None:
        """Queue one notification once; duplicated event IDs are ignored."""
        if notification.notification_id in self._seen_notification_ids:
            return
        self._remember_notification_ids((notification.notification_id,))
        if len(self._pending) < MAX_PENDING_NOTIFICATIONS:
            self._pending.append(notification)
        else:
            # Signals are wake-up hints and the activity reloads current deal
            # state. Keep a bounded queue by coalescing excess hints to latest.
            self._pending[-1] = notification

    @workflow.query
    def processed_notification_count(self) -> int:
        """Expose progress for health checks and deterministic workflow tests."""
        return self._processed_notifications

    def _remember_notification_ids(self, notification_ids: tuple[str, ...]) -> None:
        for notification_id in notification_ids:
            if notification_id in self._seen_notification_ids:
                continue
            self._seen_notification_ids.add(notification_id)
            self._seen_notification_order.append(notification_id)
            if len(self._seen_notification_order) > MAX_REMEMBERED_NOTIFICATION_IDS:
                expired = self._seen_notification_order.pop(0)
                self._seen_notification_ids.remove(expired)
