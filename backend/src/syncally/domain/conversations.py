"""Deal-scoped conversations, messages, and human-reviewed constraints."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from syncally.domain.shared.errors import InvalidTransition, InvariantViolation
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


class MessageSourceType(StrEnum):
    USER = "USER"
    AGENT = "AGENT"


class ConstraintKind(StrEnum):
    HARD_LIMIT = "HARD_LIMIT"
    PREFERENCE = "PREFERENCE"
    FLEXIBLE_OPTION = "FLEXIBLE_OPTION"
    INFORMATIONAL = "INFORMATIONAL"


class ConstraintStatus(StrEnum):
    EXTRACTED = "EXTRACTED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


@dataclass(frozen=True, slots=True)
class Conversation:
    """A container owned by one deal party; its owner scopes its messages."""

    id: ConversationId
    deal_id: DealId
    owner_organization_id: OrganizationId
    created_at: datetime

    def __post_init__(self) -> None:
        if self.id is None or self.deal_id is None or self.owner_organization_id is None:
            raise InvariantViolation("Conversation requires an ID, deal, and owner")


@dataclass(frozen=True, slots=True)
class Message:
    """A message inherits its deal and organization scope from its conversation."""

    id: MessageId
    conversation_id: ConversationId
    author_user_id: UserId | None
    author_agent_id: str | None
    body: str
    visibility: Visibility
    source_type: MessageSourceType
    created_at: datetime

    def __post_init__(self) -> None:
        if self.id is None or self.conversation_id is None:
            raise InvariantViolation("Message requires an ID and a conversation")
        if (self.author_user_id is None) == (self.author_agent_id is None):
            raise InvariantViolation("Message must have exactly one user or agent author")
        if self.author_agent_id is not None and not self.author_agent_id.strip():
            raise InvariantViolation("Agent author must not be empty")
        if not isinstance(self.body, str) or not self.body.strip():
            raise InvariantViolation("Message body must not be empty")
        if not isinstance(self.visibility, Visibility):
            raise InvariantViolation("Message requires private or shareable visibility")
        if not isinstance(self.source_type, MessageSourceType):
            raise InvariantViolation("Message requires a source type")
        if (self.source_type is MessageSourceType.USER) != (self.author_user_id is not None):
            raise InvariantViolation("Message source type must match its author")


@dataclass(slots=True)
class Constraint:
    """A deal-party fact with provenance, visibility, and a review lifecycle."""

    id: ConstraintId
    deal_id: DealId
    owner_organization_id: OrganizationId
    field: str
    typed_value: str
    kind: ConstraintKind
    visibility: Visibility
    created_at: datetime
    source_message_id: MessageId | None = None
    source_span: str | None = None
    _status: ConstraintStatus = field(default=ConstraintStatus.EXTRACTED, init=False, repr=False)
    _confirmed_by: UserId | None = field(default=None, init=False, repr=False)
    _confirmed_at: datetime | None = field(default=None, init=False, repr=False)
    version: int = field(default=0, init=False)

    @property
    def status(self) -> ConstraintStatus:
        return self._status

    @property
    def confirmed_by(self) -> UserId | None:
        return self._confirmed_by

    @property
    def confirmed_at(self) -> datetime | None:
        return self._confirmed_at

    def __post_init__(self) -> None:
        if self.id is None or self.deal_id is None or self.owner_organization_id is None:
            raise InvariantViolation("Constraint requires an ID, deal, and owner")
        if (
            not isinstance(self.field, str)
            or not self.field.strip()
            or not isinstance(self.typed_value, str)
            or not self.typed_value.strip()
        ):
            raise InvariantViolation("Constraint field and value must not be empty")
        if not isinstance(self.kind, ConstraintKind):
            raise InvariantViolation("Constraint requires a kind")
        if not isinstance(self.visibility, Visibility):
            raise InvariantViolation("Constraint requires private or shareable visibility")
        if self.version < 0:
            raise InvariantViolation("Constraint version cannot be negative")

    def confirm(self, *, confirmed_by: UserId, confirmed_at: datetime) -> None:
        """Record a human confirmation; this does not approve or create deal terms."""
        if self.status not in {
            ConstraintStatus.EXTRACTED,
            ConstraintStatus.NEEDS_CLARIFICATION,
        }:
            raise InvalidTransition(f"Cannot confirm a constraint in {self.status} state")
        if confirmed_by is None or confirmed_at is None:
            raise InvariantViolation("Constraint confirmation requires a user and time")
        self._status = ConstraintStatus.CONFIRMED
        self._confirmed_by = confirmed_by
        self._confirmed_at = confirmed_at
        self.version += 1

    def request_clarification(self) -> None:
        if self.status is not ConstraintStatus.EXTRACTED:
            raise InvalidTransition(
                f"Cannot request clarification for a constraint in {self.status} state"
            )
        self._status = ConstraintStatus.NEEDS_CLARIFICATION
        self.version += 1

    def reject(self) -> None:
        if self.status not in {
            ConstraintStatus.EXTRACTED,
            ConstraintStatus.NEEDS_CLARIFICATION,
        }:
            raise InvalidTransition(f"Cannot reject a constraint in {self.status} state")
        self._status = ConstraintStatus.REJECTED
        self.version += 1

    def supersede(self) -> None:
        if self.status is not ConstraintStatus.CONFIRMED:
            raise InvalidTransition(f"Cannot supersede a constraint in {self.status} state")
        self._status = ConstraintStatus.SUPERSEDED
        self.version += 1
