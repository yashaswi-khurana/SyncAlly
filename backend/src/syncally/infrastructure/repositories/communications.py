"""SQLAlchemy persistence for deal conversations, messages, and constraints."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from syncally.domain.deals.communications import (
    Constraint as DomainConstraint,
)
from syncally.domain.deals.communications import (
    ConstraintKind,
    ConstraintStatus,
    Visibility,
)
from syncally.domain.deals.communications import (
    Conversation as DomainConversation,
)
from syncally.domain.deals.communications import (
    Message as DomainMessage,
)
from syncally.domain.shared.identifiers import (
    ConstraintId,
    ConversationId,
    DealId,
    MessageId,
    OrganizationId,
    UserId,
)
from syncally.infrastructure.models import (
    Constraint,
    Conversation,
    Deal,
    Message,
    OrganizationMember,
)
from syncally.infrastructure.repositories._timestamps import as_utc


class CommunicationScopeError(ValueError):
    """A conversation or constraint is outside the given deal/organization scope."""


DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500


def _page_bounds(limit: int, offset: int) -> tuple[int, int]:
    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or not 1 <= limit <= MAX_PAGE_SIZE
    ):
        raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}")
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise ValueError("offset must be zero or greater")
    return limit, offset


def _conversation_to_domain(row: Conversation) -> DomainConversation:
    return DomainConversation(
        id=ConversationId(row.id),
        deal_id=DealId(row.deal_id),
        participant_organization_id=OrganizationId(row.participant_organization_id),
        created_at=as_utc(row.created_at),
    )


def _message_to_domain(
    row: Message,
    conversation: Conversation,
    *,
    include_source_reference: bool = True,
) -> DomainMessage:
    return DomainMessage(
        id=MessageId(row.id),
        conversation_id=ConversationId(row.conversation_id),
        deal_id=DealId(conversation.deal_id),
        owner_organization_id=OrganizationId(conversation.participant_organization_id),
        author_user_id=UserId(row.author_user_id) if row.author_user_id is not None else None,
        author_agent_id=row.author_agent_id,
        body=row.body,
        visibility=Visibility(row.visibility),
        source_type=row.source_type,
        source_reference=row.source_reference if include_source_reference else None,
        created_at=as_utc(row.created_at),
    )


def _constraint_to_domain(row: Constraint) -> DomainConstraint:
    return DomainConstraint(
        id=ConstraintId(row.id),
        deal_id=DealId(row.deal_id),
        owner_organization_id=OrganizationId(row.owner_organization_id),
        field=row.field,
        typed_value=row.typed_value,
        currency_or_unit=row.currency_or_unit,
        kind=ConstraintKind(row.kind),
        status=ConstraintStatus(row.status),
        visibility=Visibility(row.visibility),
        source_message_id=(
            MessageId(row.source_message_id) if row.source_message_id is not None else None
        ),
        source_span=row.source_span,
        confirmed_by=UserId(row.confirmed_by) if row.confirmed_by is not None else None,
        confirmed_at=as_utc(row.confirmed_at) if row.confirmed_at is not None else None,
        version=row.version,
        created_at=as_utc(row.created_at),
    )


class SqlAlchemyCommunicationRepository:
    """Persist communication records and require an explicit scope for all reads.

    Private messages are visible only through their conversation's owning
    organization. Shareable messages and constraints are visible to either party.
    The caller owns commit and rollback for the session.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def add_conversation(self, conversation: DomainConversation) -> DomainConversation:
        self._require_deal_party(
            conversation.deal_id, conversation.participant_organization_id
        )
        row = Conversation(
            id=conversation.id,
            deal_id=conversation.deal_id,
            participant_organization_id=conversation.participant_organization_id,
            created_at=as_utc(conversation.created_at),
        )
        self._db.add(row)
        self._db.flush()
        return _conversation_to_domain(row)

    def list_conversations(
        self,
        deal_id: UUID,
        organization_id: UUID,
        *,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[DomainConversation]:
        self._require_deal_party(deal_id, organization_id)
        limit, offset = _page_bounds(limit, offset)
        rows = self._db.scalars(
            select(Conversation)
            .where(
                Conversation.deal_id == deal_id,
                Conversation.participant_organization_id == organization_id,
            )
            .order_by(Conversation.created_at, Conversation.id)
            .limit(limit)
            .offset(offset)
        )
        return [_conversation_to_domain(row) for row in rows]

    def get_conversation(
        self, conversation_id: UUID, deal_id: UUID, organization_id: UUID
    ) -> DomainConversation | None:
        self._require_deal_party(deal_id, organization_id)
        row = self._db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.deal_id == deal_id,
                Conversation.participant_organization_id == organization_id,
            )
        )
        return _conversation_to_domain(row) if row is not None else None

    def add_message(self, message: DomainMessage) -> DomainMessage:
        try:
            visibility = Visibility(message.visibility)
        except (TypeError, ValueError) as error:
            raise CommunicationScopeError("Message visibility is invalid") from error
        conversation = self._db.get(Conversation, message.conversation_id)
        if (
            conversation is None
            or conversation.deal_id != message.deal_id
            or conversation.participant_organization_id != message.owner_organization_id
        ):
            raise CommunicationScopeError(
                "Message conversation is missing or outside the message scope"
            )
        if message.author_user_id is not None:
            self._require_active_member(
                message.owner_organization_id, message.author_user_id
            )
        row = Message(
            id=message.id,
            conversation_id=message.conversation_id,
            author_user_id=message.author_user_id,
            author_agent_id=message.author_agent_id,
            body=message.body,
            visibility=visibility.value,
            source_type=message.source_type,
            source_reference=message.source_reference,
            created_at=as_utc(message.created_at),
        )
        self._db.add(row)
        self._db.flush()
        return _message_to_domain(row, conversation)

    def list_messages(
        self,
        deal_id: UUID,
        organization_id: UUID,
        *,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[DomainMessage]:
        self._require_deal_party(deal_id, organization_id)
        limit, offset = _page_bounds(limit, offset)
        rows = self._db.execute(
            select(Message, Conversation)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Conversation.deal_id == deal_id,
                or_(
                    Conversation.participant_organization_id == organization_id,
                    Message.visibility == Visibility.SHAREABLE.value,
                ),
            )
            .order_by(Message.created_at, Message.id)
            .limit(limit)
            .offset(offset)
        )
        return [
            _message_to_domain(
                message,
                conversation,
                include_source_reference=(
                    conversation.participant_organization_id == organization_id
                ),
            )
            for message, conversation in rows
        ]

    def get_message(
        self, message_id: UUID, deal_id: UUID, organization_id: UUID
    ) -> DomainMessage | None:
        self._require_deal_party(deal_id, organization_id)
        row = self._db.execute(
            select(Message, Conversation)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Message.id == message_id,
                Conversation.deal_id == deal_id,
                or_(
                    Conversation.participant_organization_id == organization_id,
                    Message.visibility == Visibility.SHAREABLE.value,
                ),
            )
        ).one_or_none()
        return (
            _message_to_domain(
                row[0],
                row[1],
                include_source_reference=(
                    row[1].participant_organization_id == organization_id
                ),
            )
            if row is not None
            else None
        )

    def add_constraint(self, constraint: DomainConstraint) -> DomainConstraint:
        self._require_deal_party(constraint.deal_id, constraint.owner_organization_id)
        try:
            visibility = Visibility(constraint.visibility)
            kind = ConstraintKind(constraint.kind)
            status = ConstraintStatus(constraint.status)
        except (TypeError, ValueError) as error:
            raise CommunicationScopeError("Constraint enum value is invalid") from error
        if constraint.confirmed_by is not None:
            self._require_active_member(
                constraint.owner_organization_id, constraint.confirmed_by
            )

        source_message = None
        if constraint.source_message_id is not None:
            source_message = self._db.scalar(
                select(Message)
                .join(Conversation, Conversation.id == Message.conversation_id)
                .where(
                    Message.id == constraint.source_message_id,
                    Conversation.deal_id == constraint.deal_id,
                    or_(
                        Conversation.participant_organization_id
                        == constraint.owner_organization_id,
                        Message.visibility == Visibility.SHAREABLE.value,
                    ),
                )
            )
            if source_message is None:
                raise CommunicationScopeError(
                    "Source message is missing or outside the constraint scope"
                )
        if visibility is Visibility.SHAREABLE:
            if constraint.source_span is not None and source_message is None:
                raise CommunicationScopeError(
                    "A shareable source excerpt must cite a shareable message"
                )
            if source_message is not None and source_message.visibility != Visibility.SHAREABLE:
                raise CommunicationScopeError(
                    "A shareable constraint cannot cite a private message"
                )

        row = Constraint(
            id=constraint.id,
            deal_id=constraint.deal_id,
            owner_organization_id=constraint.owner_organization_id,
            field=constraint.field,
            typed_value=constraint.typed_value,
            currency_or_unit=constraint.currency_or_unit,
            kind=kind.value,
            status=status.value,
            visibility=visibility.value,
            source_message_id=constraint.source_message_id,
            source_span=constraint.source_span,
            confirmed_by=constraint.confirmed_by,
            confirmed_at=(
                as_utc(constraint.confirmed_at)
                if constraint.confirmed_at is not None
                else None
            ),
            version=constraint.version,
            created_at=as_utc(constraint.created_at),
        )
        self._db.add(row)
        self._db.flush()
        return _constraint_to_domain(row)

    def list_constraints(
        self,
        deal_id: UUID,
        organization_id: UUID,
        *,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[DomainConstraint]:
        self._require_deal_party(deal_id, organization_id)
        limit, offset = _page_bounds(limit, offset)
        rows = self._db.scalars(
            select(Constraint)
            .where(
                Constraint.deal_id == deal_id,
                or_(
                    Constraint.owner_organization_id == organization_id,
                    Constraint.visibility == Visibility.SHAREABLE.value,
                ),
            )
            .order_by(Constraint.created_at, Constraint.id)
            .limit(limit)
            .offset(offset)
        )
        return [_constraint_to_domain(row) for row in rows]

    def get_constraint(
        self, constraint_id: UUID, deal_id: UUID, organization_id: UUID
    ) -> DomainConstraint | None:
        self._require_deal_party(deal_id, organization_id)
        row = self._db.scalar(
            select(Constraint).where(
                Constraint.id == constraint_id,
                Constraint.deal_id == deal_id,
                or_(
                    Constraint.owner_organization_id == organization_id,
                    Constraint.visibility == Visibility.SHAREABLE.value,
                ),
            )
        )
        return _constraint_to_domain(row) if row is not None else None

    def _require_deal_party(self, deal_id: UUID, organization_id: UUID) -> None:
        is_deal_party = self._db.scalar(
            select(Deal.id).where(
                Deal.id == deal_id,
                or_(
                    Deal.buyer_organization_id == organization_id,
                    Deal.seller_organization_id == organization_id,
                ),
            )
        )
        if is_deal_party is None:
            raise CommunicationScopeError(
                "Organization is not a party to the requested deal"
            )

    def _require_active_member(self, organization_id: UUID, user_id: UUID) -> None:
        is_active_member = self._db.scalar(
            select(OrganizationMember.id).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == "ACTIVE",
            )
        )
        if is_active_member is None:
            raise CommunicationScopeError(
                "User must be an active member of the owning organization"
            )
