"""Unit coverage for message and fact-review use cases with an in-memory port."""

import unittest
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from syncally.application.conversations import (
    AddMessageCommand,
    AmbiguousOrganization,
    CommunicationNotFound,
    ConstraintNotFound,
    ConstraintReviewAction,
    OrganizationAccessDenied,
    add_message,
    deal_has_any_message,
    list_visible_constraints,
    list_visible_messages,
    review_constraint,
)
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
from syncally.domain.shared.errors import InvalidTransition
from syncally.domain.shared.identifiers import (
    ConstraintId,
    ConversationId,
    DealId,
    OrganizationId,
    UserId,
)


class FakeCommunicationRepository:
    """In-memory stand-in that enforces the same privacy rules as the adapter."""

    def __init__(self) -> None:
        self.deals: dict[UUID, Deal] = {}
        self.memberships: set[tuple[UUID, UUID]] = set()
        self.conversations: dict[tuple[UUID, UUID], Conversation] = {}
        self.messages: list[Message] = []
        self.constraints: dict[UUID, Constraint] = {}

    def get_deal_for_participant(self, deal_id: UUID, user_id: UUID) -> Deal | None:
        deal = self.deals.get(deal_id)
        if deal is None:
            return None
        parties = (deal.buyer_organization_id, deal.seller_organization_id)
        return deal if any((org, user_id) in self.memberships for org in parties) else None

    def get_or_create_conversation(
        self, deal_id: UUID, organization_id: UUID
    ) -> Conversation:
        key = (deal_id, organization_id)
        conversation = self.conversations.get(key)
        if conversation is None:
            conversation = Conversation(
                id=ConversationId(uuid4()),
                deal_id=DealId(deal_id),
                participant_organization_id=OrganizationId(organization_id),
                created_at=datetime.now(UTC),
            )
            self.conversations[key] = conversation
        return conversation

    def add_message(self, message: Message) -> Message:
        conversation = next(
            (item for item in self.conversations.values() if item.id == message.conversation_id),
            None,
        )
        if conversation is None:
            raise AssertionError("conversation must exist before a message is stored")
        if (conversation.participant_organization_id, message.author_user_id) not in self.memberships:
            raise AssertionError("message author must be an active owner member")
        self.messages.append(message)
        return message

    def _visible_messages(self, deal_id: UUID, organization_id: UUID) -> list[Message]:
        visible = []
        for message in self.messages:
            conversation = next(
                item for item in self.conversations.values() if item.id == message.conversation_id
            )
            if conversation.deal_id != deal_id:
                continue
            if (
                conversation.participant_organization_id == organization_id
                or message.visibility is Visibility.SHAREABLE
            ):
                visible.append(message)
        return visible

    def list_messages(
        self, deal_id: UUID, organization_id: UUID, *, limit: int, offset: int
    ) -> list[Message]:
        return self._visible_messages(deal_id, organization_id)[offset : offset + limit]

    def has_any_message(self, deal_id: UUID, organization_id: UUID) -> bool:
        deal = self.deals.get(deal_id)
        if deal is None or organization_id not in (
            deal.buyer_organization_id,
            deal.seller_organization_id,
        ):
            raise AssertionError("organization must be a party to the deal")
        conversation_ids = {
            conversation.id
            for conversation in self.conversations.values()
            if conversation.deal_id == deal_id
        }
        return any(
            message.conversation_id in conversation_ids for message in self.messages
        )

    def get_constraint_for_deal(
        self, deal_id: UUID, constraint_id: UUID, user_id: UUID
    ) -> Constraint | None:
        constraint = self.constraints.get(constraint_id)
        if constraint is None or constraint.deal_id != deal_id:
            return None
        if (constraint.owner_organization_id, user_id) not in self.memberships:
            return None
        return constraint

    def list_constraints(
        self, deal_id: UUID, organization_id: UUID, *, limit: int, offset: int
    ) -> list[Constraint]:
        visible = [
            constraint
            for constraint in self.constraints.values()
            if constraint.deal_id == deal_id
            and (
                constraint.owner_organization_id == organization_id
                or constraint.visibility is Visibility.SHAREABLE
            )
        ]
        return visible[offset : offset + limit]

    def save_constraint(
        self, constraint: Constraint, *, expected_version: int, actor_user_id: UUID
    ) -> Constraint:
        stored = self.constraints.get(constraint.id)
        if stored is None or stored.version != expected_version:
            raise AssertionError("version conflict")
        if (constraint.owner_organization_id, actor_user_id) not in self.memberships:
            raise AssertionError("reviewer must be an active owner member")
        self.constraints[constraint.id] = constraint
        return constraint


class ConversationUseCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.buyer_id = OrganizationId(uuid4())
        self.seller_id = OrganizationId(uuid4())
        self.buyer_user = uuid4()
        self.seller_user = uuid4()
        self.deal = Deal(
            id=DealId(uuid4()),
            buyer_organization_id=self.buyer_id,
            seller_organization_id=self.seller_id,
            created_at=datetime(2026, 10, 18, tzinfo=UTC),
        )
        self.repository = FakeCommunicationRepository()
        self.repository.deals[self.deal.id] = self.deal
        self.repository.memberships.add((self.buyer_id, self.buyer_user))
        self.repository.memberships.add((self.seller_id, self.seller_user))
        self.buyer = ActorContext(self.buyer_user, frozenset({self.buyer_id}))
        self.seller = ActorContext(self.seller_user, frozenset({self.seller_id}))
        self.constraint = Constraint(
            id=ConstraintId(uuid4()),
            deal_id=self.deal.id,
            owner_organization_id=self.buyer_id,
            field="delivery_deadline",
            typed_value="2027-06-30",
            kind=ConstraintKind.HARD_LIMIT,
            visibility=Visibility.PRIVATE,
            created_at=datetime(2026, 10, 18, tzinfo=UTC),
            source_span="before 30 June",
        )
        self.repository.constraints[self.constraint.id] = self.constraint

    def test_add_message_derives_author_and_owner_from_the_actor(self) -> None:
        message = add_message(
            self.buyer,
            self.deal.id,
            AddMessageCommand(body="Delivery before 30 June", visibility=Visibility.PRIVATE),
            self.repository,
        )

        self.assertEqual(message.author_user_id, UserId(self.buyer_user))
        self.assertIsNone(message.author_agent_id)
        self.assertEqual(message.source_type, MessageSourceType.USER)
        conversation = self.repository.conversations[(self.deal.id, self.buyer_id)]
        self.assertEqual(message.conversation_id, conversation.id)
        self.assertEqual(self.repository.messages, [message])

    def test_add_message_rejects_an_organization_the_actor_does_not_belong_to(self) -> None:
        with self.assertRaises(OrganizationAccessDenied):
            add_message(
                self.buyer,
                self.deal.id,
                AddMessageCommand(
                    body="spoofed",
                    visibility=Visibility.PRIVATE,
                    organization_id=self.seller_id,
                ),
                self.repository,
            )
        self.assertEqual(self.repository.messages, [])

    def test_add_message_requires_a_selector_when_the_actor_holds_both_parties(self) -> None:
        self.repository.memberships.add((self.seller_id, self.buyer_user))
        both = ActorContext(self.buyer_user, frozenset({self.buyer_id, self.seller_id}))
        with self.assertRaises(AmbiguousOrganization):
            add_message(
                both,
                self.deal.id,
                AddMessageCommand(body="ambiguous", visibility=Visibility.PRIVATE),
                self.repository,
            )

        selected = add_message(
            both,
            self.deal.id,
            AddMessageCommand(
                body="explicit",
                visibility=Visibility.PRIVATE,
                organization_id=self.seller_id,
            ),
            self.repository,
        )
        self.assertEqual(
            self.repository.conversations[(self.deal.id, self.seller_id)].id,
            selected.conversation_id,
        )

    def test_add_message_hides_a_non_party_organization_and_missing_deal(self) -> None:
        with self.assertRaises(CommunicationNotFound):
            add_message(
                self.buyer,
                uuid4(),
                AddMessageCommand(body="missing", visibility=Visibility.PRIVATE),
                self.repository,
            )
        actor = ActorContext(uuid4(), frozenset({self.buyer_id}))
        with self.assertRaises(CommunicationNotFound):
            add_message(
                actor,
                self.deal.id,
                AddMessageCommand(body="outsider", visibility=Visibility.PRIVATE),
                self.repository,
            )

    def test_list_messages_applies_visibility_for_each_party(self) -> None:
        buyer_private = add_message(
            self.buyer,
            self.deal.id,
            AddMessageCommand(body="buyer private", visibility=Visibility.PRIVATE),
            self.repository,
        )
        shareable = add_message(
            self.buyer,
            self.deal.id,
            AddMessageCommand(body="buyer shareable", visibility=Visibility.SHAREABLE),
            self.repository,
        )
        seller_private = add_message(
            self.seller,
            self.deal.id,
            AddMessageCommand(body="seller private", visibility=Visibility.PRIVATE),
            self.repository,
        )

        buyer_view = list_visible_messages(self.buyer, self.deal.id, self.repository)
        seller_view = list_visible_messages(self.seller, self.deal.id, self.repository)
        self.assertEqual({item.id for item in buyer_view}, {buyer_private.id, shareable.id})
        self.assertEqual({item.id for item in seller_view}, {seller_private.id, shareable.id})

    def test_deal_has_any_message_ignores_visibility_for_both_parties(self) -> None:
        self.assertFalse(deal_has_any_message(self.buyer, self.deal.id, self.repository))

        add_message(
            self.seller,
            self.deal.id,
            AddMessageCommand(body="seller private", visibility=Visibility.PRIVATE),
            self.repository,
        )

        self.assertTrue(deal_has_any_message(self.buyer, self.deal.id, self.repository))
        self.assertTrue(deal_has_any_message(self.seller, self.deal.id, self.repository))
        self.assertEqual(
            list_visible_messages(self.buyer, self.deal.id, self.repository), []
        )

        outsider = ActorContext(uuid4(), frozenset({self.buyer_id}))
        with self.assertRaises(CommunicationNotFound):
            deal_has_any_message(outsider, self.deal.id, self.repository)

    def test_list_facts_applies_visibility_for_each_party(self) -> None:
        seller_shareable = replace(
            self.constraint,
            id=ConstraintId(uuid4()),
            owner_organization_id=self.seller_id,
            visibility=Visibility.SHAREABLE,
            field="incoterm",
            typed_value="FOB",
        )
        self.repository.constraints[seller_shareable.id] = seller_shareable

        buyer_view = list_visible_constraints(self.buyer, self.deal.id, self.repository)
        seller_view = list_visible_constraints(self.seller, self.deal.id, self.repository)
        self.assertEqual({item.id for item in buyer_view}, {self.constraint.id, seller_shareable.id})
        self.assertEqual({item.id for item in seller_view}, {seller_shareable.id})

    def test_reject_and_clarify_advance_review_state_for_the_owner(self) -> None:
        rejected = review_constraint(
            self.buyer,
            self.deal.id,
            self.constraint.id,
            ConstraintReviewAction.REJECT,
            self.repository,
        )
        self.assertEqual(rejected.status, ConstraintStatus.REJECTED)
        self.assertIsNone(rejected.confirmed_by)
        self.assertEqual(rejected.version, 1)
        self.assertEqual(
            review_constraint(
                self.buyer,
                self.deal.id,
                self.constraint.id,
                ConstraintReviewAction.REJECT,
                self.repository,
            ),
            rejected,
        )

        clarified = Constraint(
            id=ConstraintId(uuid4()),
            deal_id=self.deal.id,
            owner_organization_id=self.buyer_id,
            field="price",
            typed_value="10 USD",
            kind=ConstraintKind.FLEXIBLE_OPTION,
            visibility=Visibility.PRIVATE,
            created_at=datetime(2026, 10, 18, tzinfo=UTC),
            source_span="ten dollars",
        )
        self.repository.constraints[clarified.id] = clarified
        result = review_constraint(
            self.buyer,
            self.deal.id,
            clarified.id,
            ConstraintReviewAction.REQUEST_CLARIFICATION,
            self.repository,
        )
        self.assertEqual(result.status, ConstraintStatus.NEEDS_CLARIFICATION)
        self.assertEqual(result.version, 1)

    def test_counterparty_cannot_review_another_organizations_fact(self) -> None:
        with self.assertRaises(ConstraintNotFound):
            review_constraint(
                self.seller,
                self.deal.id,
                self.constraint.id,
                ConstraintReviewAction.REJECT,
                self.repository,
            )
        self.assertEqual(self.constraint.status, ConstraintStatus.EXTRACTED)

    def test_review_rejects_an_invalid_transition(self) -> None:
        confirmed = review_constraint(
            self.buyer,
            self.deal.id,
            self.constraint.id,
            ConstraintReviewAction.CONFIRM,
            self.repository,
        )
        self.assertEqual(confirmed.status, ConstraintStatus.CONFIRMED)
        with self.assertRaises(InvalidTransition):
            review_constraint(
                self.buyer,
                self.deal.id,
                self.constraint.id,
                ConstraintReviewAction.REJECT,
                self.repository,
            )


if __name__ == "__main__":
    unittest.main()
