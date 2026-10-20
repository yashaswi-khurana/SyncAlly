"""Small, private-data-free notifications persisted through the outbox."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class NotificationKind(StrEnum):
    DEAL_CREATED = "DEAL_CREATED"
    AGREEMENT_COMMITTED = "AGREEMENT_COMMITTED"
    AGREEMENT_APPROVAL_RECORDED = "AGREEMENT_APPROVAL_RECORDED"
    MESSAGE_RECEIVED = "MESSAGE_RECEIVED"
    CONSTRAINT_CHANGED = "CONSTRAINT_CHANGED"
    PROPOSAL_SUBMITTED = "PROPOSAL_SUBMITTED"
    PAYMENT_STATE_CHANGED = "PAYMENT_STATE_CHANGED"


@dataclass(frozen=True, slots=True)
class DealWorkflowNotification:
    """A durable wake-up hint. Its referenced record is reloaded by an activity."""

    notification_id: str
    record_id: str
    kind: NotificationKind

    def __post_init__(self) -> None:
        for name, value in (
            ("notification_id", self.notification_id),
            ("record_id", self.record_id),
        ):
            if not isinstance(value, str):
                raise ValueError(f"{name} must be a UUID string")
            try:
                UUID(value)
            except ValueError as error:
                raise ValueError(f"{name} must be a UUID string") from error
        if not isinstance(self.kind, NotificationKind):
            raise ValueError("kind must be a supported notification kind")

