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
)
from syncally.infrastructure.repositories._timestamps import as_utc


class CommunicationScopeError(ValueError):
    """A conversation or constraint is outside the given deal/organization scope."""


def _conversation_to_domain(row: Conversation) -> DomainConversation:
    return DomainConversation(
        id=ConversationId(row.id),
        deal_id=DealId(row.deal_id),
        participant_organization_id=OrganizationId(row.participant_organization_id),
        created_at=as_utc(row.created_at),
    )


def _message_to_domain(row: Message, conversation: Conversation) -> DomainMessage:
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
        source_reference=row.source_reference,
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
        self, deal_id: UUID, organization_id: UUID
    ) -> list[DomainConversation]:
        self._require_deal_party(deal_id, organization_id)
        rows = self._db.scalars(
            select(Conversation)
            .where(
                Conversation.deal_id == deal_id,
                Conversation.participant_organization_id == organization_id,
            )
            .order_by(Conversation.created_at, Conversation.id)
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
        conversation = self._db.get(Conversation, message.conversation_id)
        if (
            conversation is None
            or conversation.deal_id != message.deal_id
            or conversation.participant_organization_id != message.owner_organization_id
        ):
            raise CommunicationScopeError(
                "Message conversation is missing or outside the message scope"
            )
        row = Message(
            id=message.id,
            conversation_id=message.conversation_id,
            author_user_id=message.author_user_id,
            author_agent_id=message.author_agent_id,
            body=message.body,
            visibility=message.visibility.value,
            source_type=message.source_type,
            source_reference=message.source_reference,
            created_at=as_utc(message.created_at),
        )
        self._db.add(row)
        self._db.flush()
        return _message_to_domain(row, conversation)

    def list_messages(
        self, deal_id: UUID, organization_id: UUID
    ) -> list[DomainMessage]:
        self._require_deal_party(deal_id, organization_id)
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
        )
        return [_message_to_domain(message, conversation) for message, conversation in rows]

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
        return _message_to_domain(*row) if row is not None else None

    def add_constraint(self, constraint: DomainConstraint) -> DomainConstraint:
        self._require_deal_party(constraint.deal_id, constraint.owner_organization_id)
        if constraint.source_message_id is not None:
            source_is_visible_in_scope = self._db.scalar(
                select(Message.id)
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
            if source_is_visible_in_scope is None:
                raise CommunicationScopeError(
                    "Source message is missing or outside the constraint scope"
                )

        row = Constraint(
            id=constraint.id,
            deal_id=constraint.deal_id,
            owner_organization_id=constraint.owner_organization_id,
            field=constraint.field,
            typed_value=constraint.typed_value,
            currency_or_unit=constraint.currency_or_unit,
            kind=constraint.kind.value,
            status=constraint.status.value,
            visibility=constraint.visibility.value,
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
        self, deal_id: UUID, organization_id: UUID
    ) -> list[DomainConstraint]:
        self._require_deal_party(deal_id, organization_id)
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
