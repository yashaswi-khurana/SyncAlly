"""Conversation visibility and message/constraint-review use cases.

This module owns the authorization and orchestration for deal conversations:
it derives the acting organization from the authenticated ``ActorContext`` and a
persistence port, never from data the caller supplies as authority. It must stay
free of HTTP parsing, request/response schemas, and SQLAlchemy.
"""

from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID, uuid4

from syncally.application.identity import ActorContext
from syncally.domain.conversations import (
    Constraint,
    ConstraintKind,
    ConstraintStatus,
    Conversation,
    Message,
    MessageSourceType,
    Visibility,
)
from syncally.domain.deals.deal import Deal
from syncally.domain.shared.errors import DomainError, InvalidTransition
from syncally.domain.shared.identifiers import (
    ConstraintId,
    ConversationId,
    DealId,
    MessageId,
    OrganizationId,
    UserId,
)

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500


class ConstraintRepository(Protocol):
    """Persistence boundary needed to confirm a deal-scoped constraint."""

    def get_deal_for_participant(self, deal_id: UUID, user_id: UUID) -> Deal | None:
        """Load a deal only when the user is an active member of a party."""

    def lock_deal_for_fact_persistence(
        self, deal_id: UUID, user_id: UUID
    ) -> Deal | None:
        """Lock the deal through transaction commit while fact signatures are saved.

        Concurrent fact-suggestion requests for one deal serialize on this row so
        their signature reads and inserts cannot race each other.
        """

    def get_constraint_for_deal(
        self, deal_id: UUID, constraint_id: UUID, user_id: UUID
    ) -> Constraint | None:
        """Load only when the user is currently active in the constraint owner org."""

    def save_constraint(
        self,
        constraint: Constraint,
        *,
        expected_version: int,
        actor_user_id: UUID,
    ) -> Constraint:
        """Atomically validate owner membership and source deal, then compare-and-save.

        The adapter must lock/recheck the active user, organization, and membership
        through commit, verify the source message's conversation belongs to this deal,
        and update only when the stored version equals ``expected_version``. It raises
        ``ConstraintNotFound`` for revoked membership or invalid provenance and
        ``ConcurrentConstraintUpdate`` when another write won the version check.
        """

    def add_constraint(self, constraint: Constraint) -> Constraint:
        """Persist a new unreviewed constraint after checking its deal and source scope."""


class CommunicationRepository(ConstraintRepository, Protocol):
    """Persistence boundary for deal-scoped messages and constraint reads."""

    def get_or_create_conversation(
        self, deal_id: UUID, organization_id: UUID
    ) -> Conversation:
        """Return the party's conversation for a deal, creating it when absent."""

    def add_message(self, message: Message) -> Message:
        """Persist a message whose author is an active member of its conversation owner."""

    def list_messages(
        self,
        deal_id: UUID,
        organization_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> list[Message]:
        """List messages visible to an organization under the visibility rules."""

    def has_any_message(self, deal_id: UUID, organization_id: UUID) -> bool:
        """Report whether any message exists in the deal, ignoring visibility.

        ``organization_id`` must be one of the deal's parties and keeps reads
        explicitly scoped; it does not filter the result. The caller must have
        already authorized the actor's access to the deal.
        """

    def list_constraints(
        self,
        deal_id: UUID,
        organization_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> list[Constraint]:
        """List constraints visible to an organization under the visibility rules."""


class ConstraintNotFound(DomainError):
    """The constraint, its deal, or the actor's deal access is unavailable."""


class ConcurrentConstraintUpdate(DomainError):
    """Another request changed the constraint after it was loaded."""


class CommunicationNotFound(DomainError):
    """The deal or record is missing or hidden from the authenticated actor."""


class OrganizationAccessDenied(DomainError):
    """The actor may not act on behalf of the requested organization."""


class AmbiguousOrganization(DomainError):
    """The actor belongs to both deal parties and must name the acting organization."""


class ConstraintReviewAction(StrEnum):
    """A human review decision applied to an extracted fact."""

    CONFIRM = "CONFIRM"
    REJECT = "REJECT"
    REQUEST_CLARIFICATION = "REQUEST_CLARIFICATION"


_REVIEW_TARGET_STATUS: dict[ConstraintReviewAction, ConstraintStatus] = {
    ConstraintReviewAction.CONFIRM: ConstraintStatus.CONFIRMED,
    ConstraintReviewAction.REJECT: ConstraintStatus.REJECTED,
    ConstraintReviewAction.REQUEST_CLARIFICATION: ConstraintStatus.NEEDS_CLARIFICATION,
}


def visible_to_viewer(
    visibility: Visibility,
    owner_organization_id: UUID,
    viewer_organization_ids: frozenset[UUID],
) -> bool:
    """A SHAREABLE item is visible to anyone; a PRIVATE item only to its owner org."""
    return visibility is Visibility.SHAREABLE or owner_organization_id in viewer_organization_ids


def can_view_message(
    actor: ActorContext,
    deal: Deal,
    conversation: Conversation,
    message: Message,
) -> bool:
    """Apply deal membership and message visibility to a conversation message."""
    if (
        conversation.deal_id != deal.id
        or conversation.participant_organization_id
        not in (deal.buyer_organization_id, deal.seller_organization_id)
        or message.conversation_id != conversation.id
        or not actor.can_access_deal(deal)
    ):
        return False
    return visible_to_viewer(
        message.visibility, conversation.participant_organization_id, actor.organization_ids
    )


def can_view_constraint(actor: ActorContext, deal: Deal, constraint: Constraint) -> bool:
    """Apply deal membership and organization ownership to a constraint read."""
    if (
        constraint.deal_id != deal.id
        or constraint.owner_organization_id
        not in (deal.buyer_organization_id, deal.seller_organization_id)
        or not actor.can_access_deal(deal)
    ):
        return False
    return visible_to_viewer(
        constraint.visibility, constraint.owner_organization_id, actor.organization_ids
    )


def resolve_participant_organization(
    actor: ActorContext,
    deal: Deal,
    requested_organization_id: UUID | None = None,
) -> UUID:
    """Derive the deal party the actor acts for, ignoring caller-supplied authority.

    A requested organization is only a selector among the memberships the actor
    already holds; it can never grant access the verified actor does not have.
    """
    if requested_organization_id is not None:
        if requested_organization_id not in actor.organization_ids:
            raise OrganizationAccessDenied("Actor cannot act for this organization")
        if requested_organization_id not in (
            deal.buyer_organization_id,
            deal.seller_organization_id,
        ):
            raise CommunicationNotFound("Deal not found")
        return requested_organization_id

    participant_organizations = [
        organization_id
        for organization_id in (
            deal.buyer_organization_id,
            deal.seller_organization_id,
        )
        if organization_id in actor.organization_ids
    ]
    if len(participant_organizations) == 1:
        return participant_organizations[0]
    raise AmbiguousOrganization("Actor must name one of its deal organizations")


def _load_deal_for_participant(
    actor: ActorContext, deal_id: UUID, repository: CommunicationRepository
) -> Deal:
    """Load a deal the actor participates in, hiding missing and forbidden deals alike."""
    deal = repository.get_deal_for_participant(deal_id, actor.user_id)
    if deal is None or deal.id != deal_id or not actor.can_access_deal(deal):
        raise CommunicationNotFound("Deal not found")
    return deal


@dataclass(frozen=True)
class AddMessageCommand:
    """Input for a user-authored message attributed from the verified actor."""

    body: str
    visibility: Visibility
    source_reference: str | None = None
    organization_id: UUID | None = None


def add_message(
    actor: ActorContext,
    deal_id: UUID,
    command: AddMessageCommand,
    repository: CommunicationRepository,
    *,
    now: datetime | None = None,
) -> Message:
    """Store a message authored by the authenticated user for its deal party."""
    deal = _load_deal_for_participant(actor, deal_id, repository)
    organization_id = resolve_participant_organization(actor, deal, command.organization_id)
    conversation = repository.get_or_create_conversation(deal_id, organization_id)
    message = Message(
        id=MessageId(uuid4()),
        conversation_id=ConversationId(conversation.id),
        author_user_id=UserId(actor.user_id),
        author_agent_id=None,
        body=command.body,
        visibility=command.visibility,
        source_type=MessageSourceType.USER,
        source_reference=command.source_reference,
        created_at=now or datetime.now(UTC),
    )
    return repository.add_message(message)


@dataclass(frozen=True)
class CreateManualConstraintCommand:
    """A user-entered fact attributed to one authorized deal organization."""

    field: str
    typed_value: str
    visibility: Visibility
    organization_id: UUID | None = None
    currency_or_unit: str | None = None
    kind: ConstraintKind = ConstraintKind.INFORMATIONAL


def create_manual_constraint(
    actor: ActorContext,
    deal_id: UUID,
    command: CreateManualConstraintCommand,
    repository: CommunicationRepository,
    *,
    now: datetime | None = None,
) -> Constraint:
    """Create an auditable fact sourced from a message authored by the actor."""
    deal = _load_deal_for_participant(actor, deal_id, repository)
    organization_id = resolve_participant_organization(actor, deal, command.organization_id)
    timestamp = now or datetime.now(UTC)
    conversation = repository.get_or_create_conversation(deal_id, organization_id)
    source_text = f"Manual term entry — {command.field}: {command.typed_value}"
    source_message = repository.add_message(
        Message(
            id=MessageId(uuid4()),
            conversation_id=ConversationId(conversation.id),
            author_user_id=UserId(actor.user_id),
            author_agent_id=None,
            body=source_text,
            visibility=command.visibility,
            source_type=MessageSourceType.USER,
            source_reference="manual-term-entry",
            created_at=timestamp,
        )
    )
    constraint = Constraint(
        id=ConstraintId(uuid4()),
        deal_id=DealId(deal_id),
        owner_organization_id=OrganizationId(organization_id),
        field=command.field,
        typed_value=command.typed_value,
        currency_or_unit=command.currency_or_unit,
        kind=command.kind,
        visibility=command.visibility,
        source_message_id=MessageId(source_message.id),
        source_span=command.typed_value,
        created_at=timestamp,
    )
    return repository.add_constraint(constraint)


def list_visible_messages(
    actor: ActorContext,
    deal_id: UUID,
    repository: CommunicationRepository,
    *,
    organization_id: UUID | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
) -> list[Message]:
    """List messages a party of the deal may read under the visibility rules."""
    deal = _load_deal_for_participant(actor, deal_id, repository)
    resolved = resolve_participant_organization(actor, deal, organization_id)
    return repository.list_messages(deal_id, resolved, limit=limit, offset=offset)


def deal_has_any_message(
    actor: ActorContext,
    deal_id: UUID,
    repository: CommunicationRepository,
) -> bool:
    """Report whether any party's conversation in the deal contains a message.

    Visibility is irrelevant: onboarding only needs to know whether the deal has
    started, not what was said. Existence is the only fact that crosses the
    private-message boundary; content and metadata stay with their owner.
    """
    deal = _load_deal_for_participant(actor, deal_id, repository)
    party_organization_id = next(
        organization_id
        for organization_id in (deal.buyer_organization_id, deal.seller_organization_id)
        if organization_id in actor.organization_ids
    )
    return repository.has_any_message(deal_id, party_organization_id)


def list_visible_constraints(
    actor: ActorContext,
    deal_id: UUID,
    repository: CommunicationRepository,
    *,
    organization_id: UUID | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
) -> list[Constraint]:
    """List facts a party of the deal may read under the visibility rules."""
    deal = _load_deal_for_participant(actor, deal_id, repository)
    resolved = resolve_participant_organization(actor, deal, organization_id)
    return repository.list_constraints(deal_id, resolved, limit=limit, offset=offset)


@dataclass(frozen=True, slots=True, repr=False)
class AiContext:
    """The messages and constraints one organization's AI prompt may see."""

    deal_id: UUID
    organization_id: UUID
    messages: tuple[Message, ...]
    constraints: tuple[Constraint, ...]

    def __repr__(self) -> str:
        # Never interpolate message.body / constraint.typed_value here - this is
        # the guard against raw private content reaching logs or workflow input.
        return (
            f"AiContext(deal_id={self.deal_id}, organization_id={self.organization_id}, "
            f"messages={len(self.messages)}, constraints={len(self.constraints)})"
        )


def select_ai_context(
    actor: ActorContext,
    deal_id: UUID,
    organization_id: UUID,
    repository: CommunicationRepository,
) -> AiContext:
    """Select what one organization's AI assistant may see for this deal.

    The acting organization (`organization_id`) is the "owner" here: the one
    whose side the AI is helping. It may see:
      - its own PRIVATE chats and terms for this deal (its internal notes,
        negotiating positions, draft facts not yet shared), and
      - anything either party marked SHAREABLE (terms/chats both sides agreed
        to expose across the table).
    It may never see the counterparty's PRIVATE chats or terms - those never
    enter this result, so no downstream prompt can leak them by accident.

    A thin composition of `list_visible_messages`/`list_visible_constraints`: no
    new privacy rule and no prompt-building, so it is testable without an AI
    service. `organization_id` is required explicitly so an actor who belongs to
    both deal parties still gets one deliberate, single-sided view.
    """
    messages = list_visible_messages(
        actor, deal_id, repository, organization_id=organization_id, limit=MAX_PAGE_SIZE
    )
    constraints = list_visible_constraints(
        actor, deal_id, repository, organization_id=organization_id, limit=MAX_PAGE_SIZE
    )
    return AiContext(
        deal_id=deal_id,
        organization_id=organization_id,
        messages=tuple(messages),
        constraints=tuple(constraints),
    )


def review_constraint(
    actor: ActorContext,
    deal_id: UUID,
    constraint_id: UUID,
    action: ConstraintReviewAction,
    repository: ConstraintRepository,
    *,
    now: datetime | None = None,
) -> Constraint:
    """Apply a human review decision to a fact for a member of its owning party."""
    deal = repository.get_deal_for_participant(deal_id, actor.user_id)
    if deal is None or deal.id != deal_id or not actor.can_access_deal(deal):
        raise ConstraintNotFound("Constraint not found")

    constraint = repository.get_constraint_for_deal(deal_id, constraint_id, actor.user_id)
    if (
        constraint is None
        or constraint.id != constraint_id
        or constraint.deal_id != deal.id
    ):
        raise ConstraintNotFound("Constraint not found")
    if constraint.owner_organization_id not in (
        deal.buyer_organization_id,
        deal.seller_organization_id,
    ):
        raise ConstraintNotFound("Constraint not found")
    if constraint.owner_organization_id not in actor.organization_ids:
        raise ConstraintNotFound("Constraint not found")

    target_status = _REVIEW_TARGET_STATUS[action]
    if constraint.status is target_status:
        return constraint

    expected_version = constraint.version
    pending = copy(constraint)
    if action is ConstraintReviewAction.CONFIRM:
        pending.confirm(
            confirmed_by=UserId(actor.user_id),
            confirmed_at=now or datetime.now(UTC),
        )
    elif action is ConstraintReviewAction.REJECT:
        pending.reject()
    elif action is ConstraintReviewAction.REQUEST_CLARIFICATION:
        pending.request_clarification()
    else:  # pragma: no cover - guards future enum members
        raise ValueError(f"Unsupported constraint review action: {action}")
    return repository.save_constraint(
        pending,
        expected_version=expected_version,
        actor_user_id=actor.user_id,
    )


def correct_constraint(
    actor: ActorContext,
    deal_id: UUID,
    constraint_id: UUID,
    *,
    expected_version: int,
    field: str,
    typed_value: str,
    currency_or_unit: str | None,
    repository: CommunicationRepository,
    now: datetime | None = None,
) -> tuple[Constraint, Constraint]:
    """Replace an unreviewed candidate with a corrected private fact, atomically."""
    deal = repository.get_deal_for_participant(deal_id, actor.user_id)
    if deal is None or not actor.can_access_deal(deal):
        raise ConstraintNotFound("Constraint not found")
    original = repository.get_constraint_for_deal(deal_id, constraint_id, actor.user_id)
    if original is None or original.deal_id != deal.id:
        raise ConstraintNotFound("Constraint not found")
    if original.version != expected_version:
        raise ConcurrentConstraintUpdate("Constraint was changed by another request")
    if original.status not in {
        ConstraintStatus.EXTRACTED,
        ConstraintStatus.NEEDS_CLARIFICATION,
    }:
        raise InvalidTransition("Only unreviewed facts can be corrected")

    rejected = copy(original)
    rejected.reject()
    saved_original = repository.save_constraint(
        rejected,
        expected_version=expected_version,
        actor_user_id=actor.user_id,
    )
    corrected = Constraint(
        id=ConstraintId(uuid4()),
        deal_id=DealId(deal_id),
        owner_organization_id=OrganizationId(original.owner_organization_id),
        field=field,
        typed_value=typed_value,
        currency_or_unit=currency_or_unit,
        kind=original.kind,
        visibility=Visibility.PRIVATE,
        source_message_id=original.source_message_id,
        source_span=original.source_span,
        created_at=now or datetime.now(UTC),
    )
    return saved_original, repository.add_constraint(corrected)


def confirm_constraint(
    actor: ActorContext,
    deal_id: UUID,
    constraint_id: UUID,
    repository: ConstraintRepository,
    *,
    now: datetime | None = None,
) -> Constraint:
    """Confirm an extracted fact only for a member of its owning deal party."""
    return review_constraint(
        actor,
        deal_id,
        constraint_id,
        ConstraintReviewAction.CONFIRM,
        repository,
        now=now,
    )
