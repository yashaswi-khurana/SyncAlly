"""Deal conversation and extracted constraint records.

These framework-independent records define the persistence shape. Authorization,
message submission, and constraint confirmation policies belong to application use
cases and are intentionally outside this module.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import (
    ConstraintId,
    ConversationId,
    DealId,
    MessageId,
    OrganizationId,
    UserId,
)


class Visibility(StrEnum):
    PRIVATE = "PRIVATE"
    SHAREABLE = "SHAREABLE"
    INTERNAL = "INTERNAL"


class ConstraintKind(StrEnum):
    HARD_LIMIT = "HARD_LIMIT"
    PREFERENCE = "PREFERENCE"
    FLEXIBLE_OPTION = "FLEXIBLE_OPTION"
    INFORMATIONAL = "INFORMATIONAL"


class ConstraintStatus(StrEnum):
    EXTRACTED = "EXTRACTED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    CONFIRMED = "CONFIRMED"
    SUPERSEDED = "SUPERSEDED"


@dataclass(slots=True)
class Conversation:
    id: ConversationId
    deal_id: DealId
    participant_organization_id: OrganizationId
    created_at: datetime


@dataclass(slots=True)
class Message:
    id: MessageId
    conversation_id: ConversationId
    deal_id: DealId
    owner_organization_id: OrganizationId
    author_user_id: UserId | None
    author_agent_id: str | None
    body: str = field(repr=False)
    visibility: Visibility
    source_type: str
    created_at: datetime
    source_reference: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if (self.author_user_id is None) == (self.author_agent_id is None):
            raise InvariantViolation("A message must have exactly one user or agent author")


@dataclass(slots=True)
class Constraint:
    id: ConstraintId
    deal_id: DealId
    owner_organization_id: OrganizationId
    field: str
    typed_value: str = field(repr=False)
    kind: ConstraintKind
    visibility: Visibility
    created_at: datetime
    currency_or_unit: str | None = None
    status: ConstraintStatus = ConstraintStatus.EXTRACTED
    source_message_id: MessageId | None = None
    source_span: str | None = field(default=None, repr=False)
    confirmed_by: UserId | None = None
    confirmed_at: datetime | None = None
    version: int = 0
