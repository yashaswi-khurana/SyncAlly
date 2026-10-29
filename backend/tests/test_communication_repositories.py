"""Database-backed coverage for communication persistence and tenant isolation."""

import unittest
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syncally.application.conversations import (
    ConcurrentConstraintUpdate,
    ConstraintNotFound,
    ConstraintReviewAction,
    confirm_constraint,
    review_constraint,
)
from syncally.application.identity import ActorContext
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
from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import (
    ConstraintId,
    ConversationId,
    DealId,
    MessageId,
    OrganizationId,
    UserId,
)
from syncally.infrastructure.database import create_database_engine
from syncally.infrastructure.models import (
    Base,
    Deal,
    Organization,
    OrganizationMember,
    OutboxEvent,
    User,
)
from syncally.infrastructure.models import (
    Constraint as ConstraintRow,
)
from syncally.infrastructure.models import (
    Conversation as ConversationRow,
)
from syncally.infrastructure.models import (
    Message as MessageRow,
)
from syncally.infrastructure.repositories import (
    CommunicationScopeError,
    SqlAlchemyCommunicationRepository,
)


class CommunicationRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_database_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.repository = SqlAlchemyCommunicationRepository(self.session)
        self.buyer = Organization(legal_name="Buyer", country_code="US")
        self.seller = Organization(legal_name="Seller", country_code="CA")
        self.outsider = Organization(legal_name="Outsider", country_code="GB")
        self.user = User(email="buyer@example.com", display_name="Buyer")
        self.seller_user = User(email="seller@example.com", display_name="Seller")
        self.session.add_all([self.buyer, self.seller, self.outsider, self.user])
        self.session.add(self.seller_user)
        self.session.flush()
        self.session.add_all(
            [
                OrganizationMember(
                    organization_id=self.buyer.id,
                    user_id=self.user.id,
                    role="MEMBER",
                    status="ACTIVE",
                ),
                OrganizationMember(
                    organization_id=self.seller.id,
                    user_id=self.seller_user.id,
                    role="MEMBER",
                    status="ACTIVE",
                ),
            ]
        )
        self.session.flush()
        self.deal = Deal(
            buyer_organization_id=self.buyer.id,
            seller_organization_id=self.seller.id,
        )
        self.session.add(self.deal)
        self.session.commit()
        self.buyer_conversation = self._conversation(self.buyer.id)
        self.seller_conversation = self._conversation(self.seller.id)
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _conversation(self, organization_id) -> DomainConversation:
        return self.repository.add_conversation(
            DomainConversation(
                id=ConversationId(uuid4()),
                deal_id=DealId(self.deal.id),
                participant_organization_id=OrganizationId(organization_id),
                created_at=datetime.now(UTC),
            )
        )

    def _message(
        self,
        conversation: DomainConversation,
        body: str,
        visibility: Visibility,
        source_reference: str | None = None,
        author_user_id: UserId | None = None,
    ) -> DomainMessage:
        return self.repository.add_message(
            DomainMessage(
                id=MessageId(uuid4()),
                conversation_id=conversation.id,
                author_user_id=author_user_id
                or UserId(
                    self.seller_user.id
                    if conversation.participant_organization_id
                    == OrganizationId(self.seller.id)
                    else self.user.id
                ),
                author_agent_id=None,
                body=body,
                visibility=visibility,
                source_type=MessageSourceType.USER,
                source_reference=source_reference,
                created_at=datetime.now(UTC),
            )
        )

    def _constraint(
        self,
        owner_id,
        field: str,
        visibility: Visibility,
        *,
        source_message: DomainMessage | None = None,
        status: ConstraintStatus = ConstraintStatus.EXTRACTED,
    ) -> DomainConstraint:
        if visibility is Visibility.SHAREABLE and source_message is None:
            source_conversation = (
                self.seller_conversation
                if owner_id == self.seller.id
                else self.buyer_conversation
            )
            source_message = self._message(
                source_conversation,
                "shared provenance",
                Visibility.SHAREABLE,
                author_user_id=UserId(
                    self.seller_user.id if owner_id == self.seller.id else self.user.id
                ),
            )
        confirmer = UserId(
            self.seller_user.id if owner_id == self.seller.id else self.user.id
        )
        constraint = DomainConstraint(
                id=ConstraintId(uuid4()),
                deal_id=DealId(self.deal.id),
                owner_organization_id=OrganizationId(owner_id),
                field=field,
                typed_value="test value",
                kind=ConstraintKind.INFORMATIONAL,
                visibility=visibility,
                source_message_id=(source_message.id if source_message else None),
                source_span="source excerpt" if source_message else "extracted source note",
                created_at=datetime.now(UTC),
        )
        if status is ConstraintStatus.CONFIRMED:
            constraint.confirm(confirmed_by=confirmer, confirmed_at=datetime.now(UTC))
        return self.repository.add_constraint(constraint)

    def test_messages_round_trip_owner_visibility_source_and_utc_timestamp(self) -> None:
        message = self._message(
            self.buyer_conversation,
            "private buyer text",
            Visibility.PRIVATE,
            source_reference="upload:buyer-document-7",
        )
        shareable = self._message(
            self.seller_conversation,
            "public seller text",
            Visibility.SHAREABLE,
            source_reference="seller:confidential-upload-id",
            author_user_id=UserId(self.seller_user.id),
        )
        seller_private = self._message(
            self.seller_conversation,
            "private seller text",
            Visibility.PRIVATE,
            author_user_id=UserId(self.seller_user.id),
        )
        self.session.commit()

        notifications = self.session.scalars(select(OutboxEvent)).all()
        self.assertEqual(len(notifications), 3)
        self.assertTrue(
            all(
                notification.event_type == "DEAL_NOTIFICATION"
                and "body" not in notification.payload
                and "source_reference" not in notification.payload
                for notification in notifications
            )
        )
        self.assertEqual(
            {notification.payload["record_id"] for notification in notifications},
            {str(message.id), str(shareable.id), str(seller_private.id)},
        )

        buyer_messages = self.repository.list_messages(self.deal.id, self.buyer.id)
        seller_messages = self.repository.list_messages(self.deal.id, self.seller.id)
        self.assertEqual(
            {row.body for row in buyer_messages}, {message.body, shareable.body}
        )
        self.assertEqual(
            {row.body for row in seller_messages}, {seller_private.body, shareable.body}
        )
        loaded = next(row for row in buyer_messages if row.id == message.id)
        self.assertEqual(loaded.conversation_id, self.buyer_conversation.id)
        self.assertEqual(loaded.source_reference, "upload:buyer-document-7")
        self.assertEqual(loaded.created_at.utcoffset(), UTC.utcoffset(None))
        self.assertEqual(
            self.repository.get_message(message.id, self.deal.id, self.buyer.id), message
        )
        self.assertIsNone(
            self.repository.get_message(message.id, self.deal.id, self.seller.id)
        )
        self.assertEqual(
            self.repository.get_message(shareable.id, self.deal.id, self.buyer.id),
            replace(shareable, source_reference=None),
        )
        seller_shareable = self.repository.get_message(
            shareable.id, self.deal.id, self.seller.id
        )
        self.assertEqual(
            seller_shareable.source_reference, "seller:confidential-upload-id"
        )
        self.assertIsNone(
            self.repository.get_message(uuid4(), self.deal.id, self.buyer.id)
        )

    def test_has_any_message_is_deal_scoped_and_ignores_visibility(self) -> None:
        self.assertFalse(self.repository.has_any_message(self.deal.id, self.buyer.id))

        other_deal = Deal(
            buyer_organization_id=self.buyer.id,
            seller_organization_id=self.seller.id,
        )
        self.session.add(other_deal)
        self.session.flush()
        other_conversation = self.repository.add_conversation(
            DomainConversation(
                id=ConversationId(uuid4()),
                deal_id=DealId(other_deal.id),
                participant_organization_id=OrganizationId(self.seller.id),
                created_at=datetime.now(UTC),
            )
        )
        self._message(
            other_conversation,
            "other deal message",
            Visibility.SHAREABLE,
            author_user_id=UserId(self.seller_user.id),
        )
        self.session.commit()

        self.assertFalse(self.repository.has_any_message(self.deal.id, self.buyer.id))

        self._message(
            self.seller_conversation,
            "private seller note",
            Visibility.PRIVATE,
            author_user_id=UserId(self.seller_user.id),
        )
        self.session.commit()

        self.assertTrue(self.repository.has_any_message(self.deal.id, self.buyer.id))
        self.assertTrue(self.repository.has_any_message(self.deal.id, self.seller.id))
        self.assertTrue(self.repository.has_any_message(other_deal.id, self.seller.id))

    def test_private_and_shareable_constraints_round_trip_with_review_state(self) -> None:
        buyer_source = self._message(
            self.buyer_conversation,
            "buyer requested twelve units",
            Visibility.PRIVATE,
        )
        buyer_private = self._constraint(
            self.buyer.id,
            "quantity",
            Visibility.PRIVATE,
            source_message=buyer_source,
        )
        seller_private = self._constraint(
            self.seller.id, "min_price", Visibility.PRIVATE
        )
        seller_shareable = self._constraint(
            self.seller.id,
            "delivery_date",
            Visibility.SHAREABLE,
            status=ConstraintStatus.CONFIRMED,
        )
        self.session.commit()

        buyer_constraints = self.repository.list_constraints(self.deal.id, self.buyer.id)
        seller_constraints = self.repository.list_constraints(self.deal.id, self.seller.id)
        self.assertEqual(
            {constraint.field for constraint in buyer_constraints},
            {"quantity", "delivery_date"},
        )
        self.assertEqual(
            {constraint.field for constraint in seller_constraints},
            {"min_price", "delivery_date"},
        )
        loaded_private = next(item for item in buyer_constraints if item.id == buyer_private.id)
        self.assertEqual(loaded_private.owner_organization_id, OrganizationId(self.buyer.id))
        self.assertEqual(loaded_private.source_message_id, buyer_source.id)
        self.assertEqual(loaded_private.source_span, "source excerpt")
        self.assertEqual(loaded_private.status, ConstraintStatus.EXTRACTED)
        self.assertNotIn("test value", repr(loaded_private))
        self.assertNotIn("source excerpt", repr(loaded_private))
        loaded_shareable = next(
            item for item in buyer_constraints if item.id == seller_shareable.id
        )
        self.assertEqual(loaded_shareable.status, ConstraintStatus.CONFIRMED)
        self.assertEqual(loaded_shareable.confirmed_by, UserId(self.seller_user.id))
        self.assertEqual(loaded_shareable.confirmed_at.utcoffset(), UTC.utcoffset(None))
        self.assertEqual(loaded_shareable.version, 1)
        self.assertNotIn(seller_private.id, {item.id for item in buyer_constraints})
        self.assertIsNone(
            self.repository.get_constraint(seller_private.id, self.deal.id, self.buyer.id)
        )
        self.assertEqual(
            self.repository.get_constraint(
                seller_shareable.id, self.deal.id, self.buyer.id
            ),
            seller_shareable,
        )

    def test_reads_require_a_party_scope_and_are_deal_scoped(self) -> None:
        self._message(self.buyer_conversation, "deal one", Visibility.PRIVATE)
        self.session.commit()
        second_deal = Deal(
            buyer_organization_id=self.buyer.id,
            seller_organization_id=self.seller.id,
        )
        self.session.add(second_deal)
        self.session.commit()
        second_conversation = self.repository.add_conversation(
            DomainConversation(
                id=ConversationId(uuid4()),
                deal_id=DealId(second_deal.id),
                participant_organization_id=OrganizationId(self.buyer.id),
                created_at=datetime.now(UTC),
            )
        )
        self._message(second_conversation, "deal two", Visibility.PRIVATE)
        self.session.commit()

        first_results = self.repository.list_messages(self.deal.id, self.buyer.id)
        self.assertEqual({item.body for item in first_results}, {"deal one"})
        self.assertEqual(
            self.repository.list_conversations(self.deal.id, self.buyer.id),
            [self.buyer_conversation],
        )
        self.assertEqual(
            self.repository.list_conversations(self.deal.id, self.seller.id),
            [self.seller_conversation],
        )
        self.assertEqual(
            self.repository.get_conversation(
                self.buyer_conversation.id, self.deal.id, self.buyer.id
            ),
            self.buyer_conversation,
        )
        self.assertIsNone(
            self.repository.get_conversation(
                self.buyer_conversation.id, self.deal.id, self.seller.id
            )
        )
        with self.assertRaises(CommunicationScopeError):
            self.repository.list_conversations(self.deal.id, self.outsider.id)
        with self.assertRaises(CommunicationScopeError):
            self.repository.list_messages(self.deal.id, self.outsider.id)
        with self.assertRaises(CommunicationScopeError):
            self.repository.list_constraints(self.deal.id, self.outsider.id)

    def test_constraint_cannot_cite_another_organizations_private_message(self) -> None:
        seller_private = self._message(
            self.seller_conversation, "seller only", Visibility.PRIVATE
        )

        with self.assertRaises(CommunicationScopeError):
            self._constraint(
                self.buyer.id,
                "price",
                Visibility.PRIVATE,
                source_message=seller_private,
            )
        self.session.rollback()

    def test_shareable_constraint_cannot_cite_private_message_or_excerpt(self) -> None:
        private_message = self._message(
            self.buyer_conversation,
            "buyer private source",
            Visibility.PRIVATE,
        )
        with self.assertRaises(CommunicationScopeError):
            self._constraint(
                self.buyer.id,
                "quantity",
                Visibility.SHAREABLE,
                source_message=private_message,
            )
        self.session.rollback()

        orphaned_excerpt = DomainConstraint(
            id=ConstraintId(uuid4()),
            deal_id=DealId(self.deal.id),
            owner_organization_id=OrganizationId(self.buyer.id),
            field="quantity",
            typed_value="12",
            kind=ConstraintKind.INFORMATIONAL,
            visibility=Visibility.SHAREABLE,
            source_span="copied private words",
            created_at=datetime.now(UTC),
        )
        with self.assertRaises(CommunicationScopeError):
            self.repository.add_constraint(orphaned_excerpt)

    def test_user_authorship_and_confirmation_require_active_owner_membership(self) -> None:
        outsider_user = User(email="outsider@example.com", display_name="Outsider")
        self.session.add(outsider_user)
        self.session.flush()
        self.session.add(
            OrganizationMember(
                organization_id=self.buyer.id,
                user_id=outsider_user.id,
                role="MEMBER",
                status="INACTIVE",
            )
        )
        self.session.flush()

        invalid_author = DomainMessage(
            id=MessageId(uuid4()),
            conversation_id=self.buyer_conversation.id,
            author_user_id=UserId(outsider_user.id),
            author_agent_id=None,
            body="misattributed",
            visibility=Visibility.PRIVATE,
            source_type=MessageSourceType.USER,
            created_at=datetime.now(UTC),
        )
        with self.assertRaises(CommunicationScopeError):
            self.repository.add_message(invalid_author)

        invalid_confirmation = DomainConstraint(
            id=ConstraintId(uuid4()),
            deal_id=DealId(self.deal.id),
            owner_organization_id=OrganizationId(self.buyer.id),
            field="quantity",
            typed_value="12",
            kind=ConstraintKind.INFORMATIONAL,
            visibility=Visibility.PRIVATE,
            source_span="source excerpt",
            created_at=datetime.now(UTC),
        )
        invalid_confirmation.confirm(
            confirmed_by=UserId(outsider_user.id), confirmed_at=datetime.now(UTC)
        )
        with self.assertRaises(CommunicationScopeError):
            self.repository.add_constraint(invalid_confirmation)

    def test_s3_01_confirmation_use_case_integrates_with_database_repository(self) -> None:
        constraint = self._constraint(
            self.buyer.id, "quantity", Visibility.PRIVATE
        )
        self.session.commit()
        actor = ActorContext(
            user_id=self.user.id,
            organization_ids=frozenset({self.buyer.id}),
        )

        confirmed = confirm_constraint(
            actor, self.deal.id, constraint.id, self.repository
        )
        self.assertEqual(confirmed.status, ConstraintStatus.CONFIRMED)
        self.assertEqual(confirmed.confirmed_by, UserId(self.user.id))
        self.assertEqual(confirmed.version, 1)

        self.session.commit()
        persisted = self.repository.get_constraint_for_deal(
            self.deal.id, constraint.id, self.user.id
        )
        self.assertEqual(persisted, confirmed)
        self.assertEqual(
            confirm_constraint(actor, self.deal.id, constraint.id, self.repository),
            confirmed,
        )
        with self.assertRaises(ConcurrentConstraintUpdate):
            self.repository.save_constraint(
                confirmed,
                expected_version=0,
                actor_user_id=self.user.id,
            )
        self.session.rollback()

        with self.assertRaises(ConstraintNotFound):
            confirm_constraint(
                ActorContext(
                    user_id=self.seller_user.id,
                    organization_ids=frozenset({self.seller.id}),
                ),
                self.deal.id,
                constraint.id,
                self.repository,
            )

        self.user.status = "INACTIVE"
        self.session.commit()
        self.assertIsNone(
            self.repository.get_deal_for_participant(self.deal.id, self.user.id)
        )
        with self.assertRaises(ConstraintNotFound):
            confirm_constraint(actor, self.deal.id, constraint.id, self.repository)

    def test_get_or_create_conversation_is_idempotent_and_party_scoped(self) -> None:
        first = self.repository.get_or_create_conversation(self.deal.id, self.buyer.id)
        second = self.repository.get_or_create_conversation(self.deal.id, self.buyer.id)
        self.assertEqual(first, self.buyer_conversation)
        self.assertEqual(first, second)
        self.assertEqual(first.participant_organization_id, OrganizationId(self.buyer.id))
        self.session.commit()
        self.assertEqual(
            self.repository.list_conversations(self.deal.id, self.buyer.id),
            [self.buyer_conversation],
        )
        with self.assertRaises(CommunicationScopeError):
            self.repository.get_or_create_conversation(self.deal.id, self.outsider.id)

    def test_get_or_create_conversation_recovers_when_a_concurrent_insert_wins(self) -> None:
        original = self.repository._find_conversation
        calls = {"count": 0}

        def miss_once(deal_id, organization_id):
            calls["count"] += 1
            if calls["count"] == 1:
                return None
            return original(deal_id, organization_id)

        self.repository._find_conversation = miss_once
        try:
            recovered = self.repository.get_or_create_conversation(
                self.deal.id, self.buyer.id
            )
        finally:
            del self.repository._find_conversation

        self.assertEqual(recovered, self.buyer_conversation)
        self.session.commit()
        self.assertEqual(
            self.repository.list_conversations(self.deal.id, self.buyer.id),
            [self.buyer_conversation],
        )

    def test_reject_and_clarify_review_transitions_persist_for_the_owner(self) -> None:
        actor = ActorContext(
            user_id=self.user.id,
            organization_ids=frozenset({self.buyer.id}),
        )
        rejected_source = self._constraint(
            self.buyer.id, "quantity", Visibility.PRIVATE
        )
        clarified_source = self._constraint(
            self.buyer.id, "delivery_window", Visibility.PRIVATE
        )
        self.session.commit()

        rejected = review_constraint(
            actor,
            self.deal.id,
            rejected_source.id,
            ConstraintReviewAction.REJECT,
            self.repository,
        )
        self.session.commit()
        self.assertEqual(rejected.status, ConstraintStatus.REJECTED)
        self.assertIsNone(rejected.confirmed_by)
        self.assertEqual(rejected.version, 1)
        persisted = self.repository.get_constraint_for_deal(
            self.deal.id, rejected_source.id, self.user.id
        )
        self.assertEqual(persisted, rejected)

        clarified = review_constraint(
            actor,
            self.deal.id,
            clarified_source.id,
            ConstraintReviewAction.REQUEST_CLARIFICATION,
            self.repository,
        )
        self.session.commit()
        self.assertEqual(clarified.status, ConstraintStatus.NEEDS_CLARIFICATION)
        self.assertEqual(clarified.version, 1)

        with self.assertRaises(ConstraintNotFound):
            review_constraint(
                ActorContext(
                    user_id=self.seller_user.id,
                    organization_ids=frozenset({self.seller.id}),
                ),
                self.deal.id,
                clarified_source.id,
                ConstraintReviewAction.REJECT,
                self.repository,
            )

    def test_list_methods_return_bounded_pages_and_validate_bounds(self) -> None:
        for body in ("first", "second", "third"):
            self._message(self.buyer_conversation, body, Visibility.PRIVATE)
        for field_name in ("one", "two", "three"):
            self._constraint(self.buyer.id, field_name, Visibility.PRIVATE)
        self.session.commit()

        message_page = self.repository.list_messages(
            self.deal.id, self.buyer.id, limit=2, offset=1
        )
        first_message_page = self.repository.list_messages(
            self.deal.id, self.buyer.id, limit=2
        )
        constraint_page = self.repository.list_constraints(
            self.deal.id, self.buyer.id, limit=2, offset=1
        )
        conversation_page = self.repository.list_conversations(
            self.deal.id, self.buyer.id, limit=1
        )
        self.assertEqual(len(message_page), 2)
        self.assertEqual(len(first_message_page), 2)
        self.assertEqual(
            len(
                {message.id for message in first_message_page}
                | {message.id for message in message_page}
            ),
            3,
        )
        self.assertEqual(len(constraint_page), 2)
        self.assertEqual(len(conversation_page), 1)
        with self.assertRaises(ValueError):
            self.repository.list_messages(self.deal.id, self.buyer.id, limit=0)
        with self.assertRaises(ValueError):
            self.repository.list_constraints(self.deal.id, self.buyer.id, offset=-1)

    def test_enum_values_are_validated_before_write_and_constrained_in_database(self) -> None:
        with self.assertRaises(InvariantViolation):
            self._message(
                self.buyer_conversation,
                "invalid visibility",
                "UNRECOGNIZED",  # type: ignore[arg-type]
            )

        with self.assertRaises(InvariantViolation):
            DomainConstraint(
                id=ConstraintId(uuid4()),
                deal_id=DealId(self.deal.id),
                owner_organization_id=OrganizationId(self.buyer.id),
                field="quantity",
                typed_value="12",
                kind="UNKNOWN",  # type: ignore[arg-type]
                visibility=Visibility.PRIVATE,
                source_span="source excerpt",
                created_at=datetime.now(UTC),
            )

        self.session.add(
            MessageRow(
                conversation_id=self.buyer_conversation.id,
                author_user_id=self.user.id,
                body="invalid direct row",
                visibility="UNKNOWN",
                source_type="USER",
            )
        )
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()

    def test_writes_reject_wrong_party_and_message_author_shape(self) -> None:
        with self.assertRaises(CommunicationScopeError):
            self.repository.add_conversation(
                DomainConversation(
                    id=ConversationId(uuid4()),
                    deal_id=DealId(self.deal.id),
                    participant_organization_id=OrganizationId(self.outsider.id),
                    created_at=datetime.now(UTC),
                )
            )

        mismatched_message = DomainMessage(
            id=MessageId(uuid4()),
            conversation_id=self.seller_conversation.id,
            author_user_id=UserId(self.user.id),
            author_agent_id=None,
            body="cross scoped",
            visibility=Visibility.PRIVATE,
            source_type=MessageSourceType.USER,
            created_at=datetime.now(UTC),
        )
        with self.assertRaises(CommunicationScopeError):
            self.repository.add_message(mismatched_message)

        with self.assertRaises(InvariantViolation):
            DomainMessage(
                id=MessageId(uuid4()),
                conversation_id=self.buyer_conversation.id,
                author_user_id=None,
                author_agent_id=None,
                body="no author",
                visibility=Visibility.PRIVATE,
                source_type=MessageSourceType.USER,
                created_at=datetime.now(UTC),
            )

    def test_caller_transaction_rollback_discards_communication_records(self) -> None:
        # The party already owns a conversation on self.deal, so use a second deal to
        # exercise conversation rollback without breaking the one-per-party invariant.
        rollback_deal = Deal(
            buyer_organization_id=self.buyer.id,
            seller_organization_id=self.seller.id,
        )
        self.session.add(rollback_deal)
        self.session.flush()
        conversation = DomainConversation(
            id=ConversationId(uuid4()),
            deal_id=DealId(rollback_deal.id),
            participant_organization_id=OrganizationId(self.buyer.id),
            created_at=datetime.now(UTC),
        )
        self.repository.add_conversation(conversation)
        message = self._message(conversation, "rolled back", Visibility.PRIVATE)
        constraint = self.repository.add_constraint(
            DomainConstraint(
                id=ConstraintId(uuid4()),
                deal_id=DealId(rollback_deal.id),
                owner_organization_id=OrganizationId(self.buyer.id),
                field="quantity",
                typed_value="test value",
                kind=ConstraintKind.INFORMATIONAL,
                visibility=Visibility.PRIVATE,
                source_message_id=message.id,
                source_span="source excerpt",
                created_at=datetime.now(UTC),
            )
        )
        self.session.rollback()

        self.assertIsNone(self.session.get(ConversationRow, conversation.id))
        self.assertIsNone(self.session.get(MessageRow, message.id))
        self.assertIsNone(self.session.get(ConstraintRow, constraint.id))
        self.assertNotIn(
            str(rollback_deal.id),
            {
                event.payload["deal_id"]
                for event in self.session.scalars(select(OutboxEvent)).all()
            },
        )


if __name__ == "__main__":
    unittest.main()
