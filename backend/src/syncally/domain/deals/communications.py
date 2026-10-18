"""Compatibility exports for the canonical conversation domain contract."""

from syncally.domain.conversations import (
    Constraint,
    ConstraintKind,
    ConstraintStatus,
    Conversation,
    Message,
    MessageSourceType,
    Visibility,
)

__all__ = [
    "Constraint",
    "ConstraintKind",
    "ConstraintStatus",
    "Conversation",
    "Message",
    "MessageSourceType",
    "Visibility",
]
