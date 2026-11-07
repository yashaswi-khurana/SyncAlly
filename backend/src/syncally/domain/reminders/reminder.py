"""Domain entities and business rules for durable obligation reminders."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID

from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import DealId, OrganizationId, UserId

DEFAULT_RECURRENCE_CAP = 3
MAX_RECURRENCE_CAP = 10
DEFAULT_RETRY_LIMIT = 5


class ReminderScope(StrEnum):
    """The business obligation area being reminded."""

    FULFILLMENT = "FULFILLMENT"
    MILESTONE = "MILESTONE"
    CASE = "CASE"
    ROUTING = "ROUTING"


class ReminderStatus(StrEnum):
    """Durable lifecycle status of a reminder."""

    SCHEDULED = "SCHEDULED"
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    SUPPRESSED = "SUPPRESSED"
    FAILED = "FAILED"


class ReminderChannel(StrEnum):
    """Authorized delivery channel. Default is in-app only."""

    IN_APP = "IN_APP"


class SuppressionReason(StrEnum):
    """Reason why an active reminder schedule was suppressed without delivery."""

    RESOLVED = "RESOLVED"
    SUPERSEDED = "SUPERSEDED"
    RECIPIENT_REVOKED = "RECIPIENT_REVOKED"
    ORGANIZATION_SWITCHED = "ORGANIZATION_SWITCHED"
    DEAL_TERMINAL = "DEAL_TERMINAL"
    RECURRENCE_EXHAUSTED = "RECURRENCE_EXHAUSTED"


def ensure_utc(dt: datetime, field_name: str) -> datetime:
    """Validate that a datetime is timezone-aware and normalized to UTC."""
    if not isinstance(dt, datetime):
        raise InvariantViolation(f"{field_name} must be a datetime")
    if dt.tzinfo is None:
        raise InvariantViolation(f"{field_name} must be timezone-aware (UTC)")
    return dt.astimezone(UTC)


def build_deduplication_key(
    deal_id: UUID,
    scope: ReminderScope,
    reference_id: UUID,
    recurrence_count: int = 0,
    recipient_organization_id: UUID | None = None,
    recipient_user_id: UUID | None = None,
) -> str:
    """Generate a deterministic, unique deduplication key for a reminder."""
    org_suffix = f":{recipient_organization_id}" if recipient_organization_id is not None else ""
    user_suffix = f":{recipient_user_id}" if recipient_user_id is not None else ""
    return f"{deal_id}:{scope.value}:{reference_id}{org_suffix}{user_suffix}:{recurrence_count}"


@dataclass(slots=True)
class DealReminder:
    """A durable, scheduled reminder for a deal participant's obligation.

    Reminders never automatically approve, expire, pay, or escalate obligations.
    All delivery is via authorized channels (default in-app) and delivery rechecks
    underlying obligation status before dispatching.
    """

    id: UUID
    deal_id: DealId
    scope: ReminderScope
    reference_id: UUID
    recipient_organization_id: OrganizationId
    recipient_user_id: UserId | None
    status: ReminderStatus
    scheduled_for: datetime
    due_at: datetime
    recurrence_cap: int = DEFAULT_RECURRENCE_CAP
    recurrence_count: int = 0
    deduplication_key: str = ""
    channel: ReminderChannel = ReminderChannel.IN_APP
    retry_count: int = 0
    next_attempt_at: datetime | None = None
    delivered_at: datetime | None = None
    suppressed_at: datetime | None = None
    suppression_reason: SuppressionReason | None = None
    error_detail: str | None = None
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ReminderScope):
            try:
                self.scope = ReminderScope(self.scope)
            except ValueError as exc:
                raise InvariantViolation(f"Invalid reminder scope: {self.scope}") from exc

        if not isinstance(self.status, ReminderStatus):
            try:
                self.status = ReminderStatus(self.status)
            except ValueError as exc:
                raise InvariantViolation(f"Invalid reminder status: {self.status}") from exc

        if not isinstance(self.channel, ReminderChannel):
            try:
                self.channel = ReminderChannel(self.channel)
            except ValueError as exc:
                raise InvariantViolation(f"Invalid reminder channel: {self.channel}") from exc

        if self.suppression_reason is not None and not isinstance(
            self.suppression_reason, SuppressionReason
        ):
            try:
                self.suppression_reason = SuppressionReason(self.suppression_reason)
            except ValueError as exc:
                raise InvariantViolation(
                    f"Invalid suppression reason: {self.suppression_reason}"
                ) from exc

        self.scheduled_for = ensure_utc(self.scheduled_for, "scheduled_for")
        self.due_at = ensure_utc(self.due_at, "due_at")
        if self.next_attempt_at is not None:
            self.next_attempt_at = ensure_utc(self.next_attempt_at, "next_attempt_at")
        if self.delivered_at is not None:
            self.delivered_at = ensure_utc(self.delivered_at, "delivered_at")
        if self.suppressed_at is not None:
            self.suppressed_at = ensure_utc(self.suppressed_at, "suppressed_at")

        if self.recurrence_cap < 1 or self.recurrence_cap > MAX_RECURRENCE_CAP:
            raise InvariantViolation(
                f"recurrence_cap must be between 1 and {MAX_RECURRENCE_CAP}"
            )

        if self.recurrence_count < 0:
            raise InvariantViolation("recurrence_count cannot be negative")

        if self.retry_count < 0:
            raise InvariantViolation("retry_count cannot be negative")

        if not self.deduplication_key:
            self.deduplication_key = build_deduplication_key(
                self.deal_id,
                self.scope,
                self.reference_id,
                self.recurrence_count,
                self.recipient_organization_id,
                self.recipient_user_id,
            )

    def is_due(self, now: datetime) -> bool:
        """Check whether the reminder is due for delivery."""
        now_utc = ensure_utc(now, "now")
        if self.status not in (ReminderStatus.SCHEDULED, ReminderStatus.PENDING):
            return False
        effective_time = self.next_attempt_at or self.due_at
        return now_utc >= effective_time

    def mark_delivered(self, now: datetime) -> None:
        """Record successful delivery through authorized channel."""
        if self.status in (ReminderStatus.SUPPRESSED, ReminderStatus.FAILED):
            raise InvariantViolation(f"Cannot deliver reminder in {self.status} status")
        now_utc = ensure_utc(now, "now")
        self.status = ReminderStatus.DELIVERED
        self.delivered_at = now_utc
        self.recurrence_count += 1
        self.next_attempt_at = None
        self.error_detail = None
        self.updated_at = now_utc
        self.version += 1

    def mark_suppressed(self, reason: SuppressionReason, now: datetime) -> None:
        """Suppress reminder without delivering (underlying obligation resolved/superseded)."""
        now_utc = ensure_utc(now, "now")
        self.status = ReminderStatus.SUPPRESSED
        self.suppressed_at = now_utc
        self.suppression_reason = reason
        self.next_attempt_at = None
        self.updated_at = now_utc
        self.version += 1

    def record_retry(self, error: str, now: datetime) -> None:
        """Record a transient dispatch failure with bounded backoff."""
        now_utc = ensure_utc(now, "now")
        self.retry_count += 1
        self.error_detail = error[:500] if error else None
        self.updated_at = now_utc
        self.version += 1

        if self.retry_count >= DEFAULT_RETRY_LIMIT:
            self.status = ReminderStatus.FAILED
            self.next_attempt_at = None
        else:
            self.status = ReminderStatus.PENDING
            # Bounded exponential backoff: 30s, 60s, 120s, 240s...
            backoff_seconds = min(300, 30 * (2 ** (self.retry_count - 1)))
            self.next_attempt_at = now_utc + timedelta(seconds=backoff_seconds)
