"""SQLAlchemy persistence for deal conversations, messages, and constraints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syncally.application.conversations import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    ConcurrentConstraintUpdate,
    ConstraintNotFound,
    MessageIdempotencyConflict,
    message_fingerprint,
)
from syncally.application.workflow_notifications import NotificationKind
from syncally.domain.conversations import (
    Constraint as DomainConstraint,
)
from syncally.domain.conversations import (
    ConstraintKind,
    ConstraintStatus,
    MessageSourceType,
    Visibility,
)
from syncally.domain.conversations import (
    Conversation as DomainConversation,
)
from syncally.domain.conversations import (
    Message as DomainMessage,
)
from syncally.domain.deals.deal import Deal as DomainDeal
from syncally.domain.shared.identifiers import (
    ConstraintId,
    ConversationId,
    DealId,
    MessageId,
    OrganizationId,
    UserId,
)
from syncally.infrastructure.counterparty_onboarding import is_pending, lock_deal
from syncally.infrastructure.models import (
    Constraint,
    Conversation,
    Deal,
    Message,
    Organization,
    OrganizationMember,
    User,
)
from syncally.infrastructure.repositories._timestamps import as_utc
from syncally.infrastructure.repositories.deals import SqlAlchemyDealRepository
from syncally.infrastructure.workflow_notifications import queue_deal_workflow_notification


class CommunicationScopeError(ValueError):
    """A conversation or constraint is outside the given deal/organization scope."""


def _is_unique_violation(error: IntegrityError, name: str, columns: str) -> bool:
    original = error.orig
    diagnostic = getattr(original, "diag", None)
    if diagnostic is not None:
        return (
            getattr(original, "sqlstate", getattr(original, "pgcode", None)) == "23505"
            and diagnostic.constraint_name == name
        )
    return (
        getattr(original, "sqlite_errorcode", None) == 2067
        and str(original) == f"UNIQUE constraint failed: {columns}"
    )


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
    row: Message, *, include_source_reference: bool = True
) -> DomainMessage:
    return DomainMessage(
        id=MessageId(row.id),
        conversation_id=ConversationId(row.conversation_id),
        author_user_id=UserId(row.author_user_id) if row.author_user_id is not None else None,
        author_agent_id=row.author_agent_id,
        body=row.body,
        visibility=Visibility.from_storage(row.visibility),
        source_type=MessageSourceType(row.source_type),
        source_reference=row.source_reference if include_source_reference else None,
        idempotency_key=row.idempotency_key if include_source_reference else None,
        created_at=as_utc(row.created_at),
    )


def _constraint_to_domain(row: Constraint) -> DomainConstraint:
    return DomainConstraint.reconstitute(
        id=ConstraintId(row.id),
        deal_id=DealId(row.deal_id),
        owner_organization_id=OrganizationId(row.owner_organization_id),
        field=row.field,
        typed_value=row.typed_value,
        currency_or_unit=row.currency_or_unit,
        kind=ConstraintKind(row.kind),
        status=ConstraintStatus(row.status),
        visibility=Visibility.from_storage(row.visibility),
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

    def _ensure_outer_transaction(self) -> None:
        connection = self._db.connection()
        if connection.dialect.name == "sqlite":
            driver = connection.connection.driver_connection
            if not driver.in_transaction:
                connection.exec_driver_sql("BEGIN")

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

    def get_or_create_conversation(
        self, deal_id: UUID, organization_id: UUID
    ) -> DomainConversation:
        """Return the party's conversation, creating it once under concurrency.

        A unique constraint on ``(deal_id, participant_organization_id)`` makes the
        invariant durable. A concurrent first message that wins the race commits the
        row first; the loser's insert violates the constraint, so it rolls back to a
        savepoint and re-reads the winner instead of surfacing a 500.
        """
        lock_deal(self._db, deal_id, shared=True)
        self._require_deal_party(deal_id, organization_id)
        if is_pending(self._db, deal_id):
            raise CommunicationScopeError("Awaiting counterparty acceptance; messages are not available")
        row = self._find_conversation(deal_id, organization_id)
        if row is not None:
            return _conversation_to_domain(row)

        self._ensure_outer_transaction()
        self._db.flush()
        try:
            with self._db.begin_nested():
                row = Conversation(
                    deal_id=deal_id,
                    participant_organization_id=organization_id,
                    created_at=datetime.now(UTC),
                )
                self._db.add(row)
                self._db.flush()
        except IntegrityError as error:
            if not _is_unique_violation(
                error, "uq_conversations_deal_participant",
                "conversations.deal_id, conversations.participant_organization_id",
            ):
                raise
            self._require_deal_party(deal_id, organization_id)
            row = self._find_conversation(deal_id, organization_id)
            if row is None:
                raise
        return _conversation_to_domain(row)

    def _find_conversation(
        self, deal_id: UUID, organization_id: UUID
    ) -> Conversation | None:
        return self._db.scalar(
            select(Conversation)
            .where(
                Conversation.deal_id == deal_id,
                Conversation.participant_organization_id == organization_id,
            )
            .order_by(Conversation.created_at, Conversation.id)
            .limit(1)
        )

    def add_message(self, message: DomainMessage) -> DomainMessage:
        try:
            visibility = Visibility(message.visibility)
        except (TypeError, ValueError) as error:
            raise CommunicationScopeError("Message visibility is invalid") from error
        conversation = self._require_message_access(message)
        fingerprint = message_fingerprint(message) if message.idempotency_key is not None else None
        if message.idempotency_key is not None:
            existing = self._find_keyed_message(message)
            if existing is not None:
                return self._replay_message(existing, fingerprint)
        row = Message(
            id=message.id,
            conversation_id=message.conversation_id,
            author_user_id=message.author_user_id,
            author_agent_id=message.author_agent_id,
            body=message.body,
            visibility=visibility.value,
            source_type=message.source_type.value,
            source_reference=message.source_reference,
            idempotency_key=message.idempotency_key,
            idempotency_fingerprint=fingerprint,
            created_at=as_utc(message.created_at),
        )
        self._ensure_outer_transaction()
        self._db.flush()
        try:
            with self._db.begin_nested():
                self._db.add(row)
                self._db.flush()
                queue_deal_workflow_notification(
                    self._db,
                    deal_id=conversation.deal_id,
                    record_id=message.id,
                    kind=NotificationKind.MESSAGE_RECEIVED,
                )
        except IntegrityError as error:
            if message.idempotency_key is None or not _is_unique_violation(
                error, "uq_messages_conversation_author_idempotency_key",
                "messages.conversation_id, messages.author_user_id, messages.idempotency_key",
            ):
                raise
            self._require_message_access(message)
            existing = self._find_keyed_message(message)
            if existing is None:
                raise
            return self._replay_message(existing, fingerprint)
        return _message_to_domain(row)

    def _find_keyed_message(self, message: DomainMessage) -> Message | None:
        return self._db.scalar(
            select(Message).where(
                Message.conversation_id == message.conversation_id,
                Message.author_user_id == message.author_user_id,
                Message.idempotency_key == message.idempotency_key,
            ).execution_options(populate_existing=True)
        )

    def _replay_message(self, row: Message, fingerprint: str | None) -> DomainMessage:
        if row.idempotency_fingerprint != fingerprint:
            raise MessageIdempotencyConflict("Idempotency key already used for a different message")
        return _message_to_domain(row)

    def _require_message_access(self, message: DomainMessage) -> Conversation:
        conversation = self._db.scalar(
            select(Conversation).where(Conversation.id == message.conversation_id)
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        if conversation is None:
            raise CommunicationScopeError(
                "Message conversation is missing or outside the message scope"
            )
        lock_deal(self._db, conversation.deal_id, shared=True)
        if message.author_user_id is not None:
            allowed = self._db.scalar(
                select(Deal.id)
                .join(OrganizationMember, OrganizationMember.organization_id == conversation.participant_organization_id)
                .join(Organization, Organization.id == OrganizationMember.organization_id)
                .join(User, User.id == OrganizationMember.user_id)
                .where(
                    Deal.id == conversation.deal_id,
                    or_(Deal.buyer_organization_id == conversation.participant_organization_id,
                        Deal.seller_organization_id == conversation.participant_organization_id),
                    OrganizationMember.user_id == message.author_user_id,
                    OrganizationMember.status == "ACTIVE",
                    Organization.status == "ACTIVE",
                    User.status == "ACTIVE",
                )
                .with_for_update(read=True, of=(Deal, OrganizationMember, Organization, User))
            )
            if allowed is None:
                raise CommunicationScopeError("Deal not found")
        else:
            self._require_deal_party(conversation.deal_id, conversation.participant_organization_id)
        if is_pending(self._db, conversation.deal_id):
            raise CommunicationScopeError("Awaiting counterparty acceptance; messages are not available")
        return conversation

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
            .join(Deal, Deal.id == Conversation.deal_id)
            .where(
                Conversation.deal_id == deal_id,
                or_(
                    Conversation.participant_organization_id == Deal.buyer_organization_id,
                    Conversation.participant_organization_id == Deal.seller_organization_id,
                ),
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
                include_source_reference=(
                    conversation.participant_organization_id == organization_id
                ),
            )
            for message, conversation in rows
        ]

    def has_any_message(self, deal_id: UUID, organization_id: UUID) -> bool:
        """Report whether any message exists in the deal, ignoring visibility.

        The organization only proves the caller is scoped to a deal party; it is
        deliberately not used as a visibility filter. Only existence is exposed,
        never content, author, counts, or timestamps.
        """
        self._require_deal_party(deal_id, organization_id)
        row = self._db.scalar(
            select(Message.id)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .join(Deal, Deal.id == Conversation.deal_id)
            .where(
                Conversation.deal_id == deal_id,
                or_(
                    Conversation.participant_organization_id == Deal.buyer_organization_id,
                    Conversation.participant_organization_id == Deal.seller_organization_id,
                ),
            )
            .limit(1)
        )
        return row is not None

    def get_message(
        self, message_id: UUID, deal_id: UUID, organization_id: UUID
    ) -> DomainMessage | None:
        self._require_deal_party(deal_id, organization_id)
        row = self._db.execute(
            select(Message, Conversation)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .join(Deal, Deal.id == Conversation.deal_id)
            .where(
                Message.id == message_id,
                Conversation.deal_id == deal_id,
                or_(
                    Conversation.participant_organization_id == Deal.buyer_organization_id,
                    Conversation.participant_organization_id == Deal.seller_organization_id,
                ),
                or_(
                    Conversation.participant_organization_id == organization_id,
                    Message.visibility == Visibility.SHAREABLE.value,
                ),
            )
        ).one_or_none()
        return (
            _message_to_domain(
                row[0],
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
        queue_deal_workflow_notification(
            self._db,
            deal_id=constraint.deal_id,
            record_id=constraint.id,
            kind=NotificationKind.CONSTRAINT_CHANGED,
        )
        return _constraint_to_domain(row)

    def get_deal_for_participant(
        self, deal_id: UUID, user_id: UUID
    ) -> DomainDeal | None:
        """Load a deal only when the user is an active member of a deal party."""
        return SqlAlchemyDealRepository(self._db).get_for_participant(deal_id, user_id)

    def require_participant_membership(
        self, deal_id: UUID, organization_id: UUID, user_id: UUID
    ) -> None:
        allowed = self._db.scalar(
            select(Deal.id)
            .join(OrganizationMember, OrganizationMember.organization_id == organization_id)
            .join(Organization, Organization.id == OrganizationMember.organization_id)
            .join(User, User.id == OrganizationMember.user_id)
            .where(
                Deal.id == deal_id,
                or_(Deal.buyer_organization_id == organization_id,
                    Deal.seller_organization_id == organization_id),
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == "ACTIVE",
                Organization.status == "ACTIVE",
                User.status == "ACTIVE",
            )
        )
        if allowed is None:
            raise CommunicationScopeError("Deal not found")

    def lock_deal_for_fact_persistence(
        self, deal_id: UUID, user_id: UUID
    ) -> DomainDeal | None:
        """Serialize same-deal fact checks until the caller commits its inserts."""
        return SqlAlchemyDealRepository(self._db).get_for_participant(
            deal_id, user_id, for_update=True
        )

    def get_constraint_for_deal(
        self, deal_id: UUID, constraint_id: UUID, user_id: UUID
    ) -> DomainConstraint | None:
        """Load a constraint only for an active member of its owner organization."""
        source_belongs_to_deal = (
            select(Message.id)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Message.id == Constraint.source_message_id,
                Conversation.deal_id == Constraint.deal_id,
            )
            .exists()
        )
        row = self._db.scalar(
            select(Constraint)
            .join(Deal, Deal.id == Constraint.deal_id)
            .join(
                OrganizationMember,
                OrganizationMember.organization_id == Constraint.owner_organization_id,
            )
            .join(Organization, Organization.id == OrganizationMember.organization_id)
            .join(User, User.id == OrganizationMember.user_id)
            .where(
                Constraint.id == constraint_id,
                Constraint.deal_id == deal_id,
                or_(
                    Constraint.owner_organization_id == Deal.buyer_organization_id,
                    Constraint.owner_organization_id == Deal.seller_organization_id,
                ),
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == "ACTIVE",
                Organization.status == "ACTIVE",
                User.status == "ACTIVE",
                or_(Constraint.source_message_id.is_(None), source_belongs_to_deal),
            )
        )
        return _constraint_to_domain(row) if row is not None else None

    def save_constraint(
        self,
        constraint: DomainConstraint,
        *,
        expected_version: int,
        actor_user_id: UUID,
    ) -> DomainConstraint:
        """Compare-and-save a review decision while holding membership locks to commit."""
        if constraint.version != expected_version + 1:
            raise ConstraintNotFound("Constraint not found")
        if constraint.status is ConstraintStatus.CONFIRMED:
            if (
                constraint.confirmed_by != UserId(actor_user_id)
                or constraint.confirmed_at is None
            ):
                raise ConstraintNotFound("Constraint not found")
        elif constraint.status not in {
            ConstraintStatus.REJECTED,
            ConstraintStatus.NEEDS_CLARIFICATION,
        } or constraint.confirmed_by is not None or constraint.confirmed_at is not None:
            raise ConstraintNotFound("Constraint not found")

        deal = self._db.scalar(
            select(Deal)
            .where(Deal.id == constraint.deal_id)
            .with_for_update()
        )
        if (
            deal is None
            or constraint.owner_organization_id
            not in (deal.buyer_organization_id, deal.seller_organization_id)
        ):
            raise ConstraintNotFound("Constraint not found")

        membership_id = self._db.scalar(
            select(OrganizationMember.id)
            .join(Organization, Organization.id == OrganizationMember.organization_id)
            .join(User, User.id == OrganizationMember.user_id)
            .where(
                OrganizationMember.organization_id == constraint.owner_organization_id,
                OrganizationMember.user_id == actor_user_id,
                OrganizationMember.status == "ACTIVE",
                Organization.status == "ACTIVE",
                User.status == "ACTIVE",
            )
            .with_for_update()
        )
        if membership_id is None:
            raise ConstraintNotFound("Constraint not found")

        if constraint.source_message_id is not None:
            source_is_in_deal = self._db.scalar(
                select(Message.id)
                .join(Conversation, Conversation.id == Message.conversation_id)
                .where(
                    Message.id == constraint.source_message_id,
                    Conversation.deal_id == constraint.deal_id,
                )
            )
            if source_is_in_deal is None:
                raise ConstraintNotFound("Constraint not found")

        result = self._db.execute(
            update(Constraint)
            .where(
                Constraint.id == constraint.id,
                Constraint.deal_id == constraint.deal_id,
                Constraint.owner_organization_id == constraint.owner_organization_id,
                Constraint.version == expected_version,
            )
            .values(
                status=constraint.status.value,
                confirmed_by=constraint.confirmed_by,
                confirmed_at=(
                    as_utc(constraint.confirmed_at)
                    if constraint.confirmed_at is not None
                    else None
                ),
                version=constraint.version,
                updated_at=func.now(),
            )
            .execution_options(synchronize_session=False)
        )
        if cast(CursorResult[Any], result).rowcount != 1:
            raise ConcurrentConstraintUpdate("Constraint was changed by another request")

        row = self._db.scalar(
            select(Constraint)
            .where(Constraint.id == constraint.id)
            .execution_options(populate_existing=True)
        )
        if row is None:
            raise ConstraintNotFound("Constraint not found")
        queue_deal_workflow_notification(
            self._db,
            deal_id=constraint.deal_id,
            record_id=constraint.id,
            kind=NotificationKind.CONSTRAINT_CHANGED,
        )
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
            .join(Deal, Deal.id == Constraint.deal_id)
            .where(
                Constraint.deal_id == deal_id,
                or_(
                    Constraint.owner_organization_id == Deal.buyer_organization_id,
                    Constraint.owner_organization_id == Deal.seller_organization_id,
                ),
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
            select(Constraint)
            .join(Deal, Deal.id == Constraint.deal_id)
            .where(
                Constraint.id == constraint_id,
                Constraint.deal_id == deal_id,
                or_(
                    Constraint.owner_organization_id
                    == Deal.buyer_organization_id,
                    Constraint.owner_organization_id
                    == Deal.seller_organization_id,
                ),
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
            select(OrganizationMember.id)
            .join(Organization, Organization.id == OrganizationMember.organization_id)
            .join(User, User.id == OrganizationMember.user_id)
            .where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == "ACTIVE",
                Organization.status == "ACTIVE",
                User.status == "ACTIVE",
            )
        )
        if is_active_member is None:
            raise CommunicationScopeError(
                "User must be an active member of the owning organization"
            )
