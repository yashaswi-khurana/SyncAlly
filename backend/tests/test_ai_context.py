"""Organization-scoped AI prompt context selection."""

import unittest
from datetime import UTC, datetime
from uuid import UUID, uuid4

from syncally.application.conversations import (
    CommunicationNotFound,
    OrganizationAccessDenied,
    select_ai_context,
)
from syncally.application.identity import ActorContext
from syncally.domain.conversations import (
    Constraint,
    ConstraintKind,
    Message,
    MessageSourceType,
    Visibility,
)
from syncally.domain.deals.deal import Deal
from syncally.domain.shared.identifiers import (
    ConstraintId,
    ConversationId,
    DealId,
    MessageId,
    OrganizationId,
    UserId,
)


class FakeCommunicationRepository:
    """Minimal fake covering only what `select_ai_context` calls."""

    def __init__(self, deal: Deal | None, messages: list[Message], constraints: list[Constraint]) -> None:
        self.deal = deal
        self.messages = messages
        self.constraints = constraints
        self.memberships: set[tuple[UUID, UUID]] = set()
        self.conversation_owner: dict[UUID, UUID] = {}

    def get_deal_for_participant(self, deal_id: UUID, user_id: UUID) -> Deal | None:
        if self.deal is None or self.deal.id != deal_id:
            return None
        parties = (self.deal.buyer_organization_id, self.deal.seller_organization_id)
        return self.deal if any(
            (organization_id, user_id) in self.memberships for organization_id in parties
        ) else None

    def list_messages(
        self, deal_id: UUID, organization_id: UUID, *, limit: int, offset: int
    ) -> list[Message]:
        visible = [
            message
            for message in self.messages
            if self.conversation_owner[message.conversation_id] == organization_id
            or message.visibility is Visibility.SHAREABLE
        ]
        return visible[offset : offset + limit]

    def list_constraints(
        self, deal_id: UUID, organization_id: UUID, *, limit: int, offset: int
    ) -> list[Constraint]:
        visible = [
            constraint
            for constraint in self.constraints
            if constraint.owner_organization_id == organization_id
            or constraint.visibility is Visibility.SHAREABLE
        ]
        return visible[offset : offset + limit]


class AiContextSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.buyer_id = OrganizationId(uuid4())
        self.seller_id = OrganizationId(uuid4())
        self.deal = Deal(
            id=DealId(uuid4()),
            buyer_organization_id=self.buyer_id,
            seller_organization_id=self.seller_id,
            created_at=datetime(2026, 10, 18, tzinfo=UTC),
        )
        self.buyer_conversation_id = ConversationId(uuid4())
        self.seller_conversation_id = ConversationId(uuid4())

        def message(conversation_id, visibility, body) -> Message:
            return Message(
                id=MessageId(uuid4()),
                conversation_id=conversation_id,
                author_user_id=UserId(uuid4()),
                author_agent_id=None,
                body=body,
                visibility=visibility,
                source_type=MessageSourceType.USER,
                created_at=datetime(2026, 10, 18, tzinfo=UTC),
            )

        self.buyer_private_message = message(
            self.buyer_conversation_id, Visibility.PRIVATE, "buyer secret margin"
        )
        self.buyer_shareable_message = message(
            self.buyer_conversation_id, Visibility.SHAREABLE, "buyer wants 30 day delivery"
        )
        self.seller_private_message = message(
            self.seller_conversation_id, Visibility.PRIVATE, "seller secret cost basis"
        )
        self.seller_shareable_message = message(
            self.seller_conversation_id, Visibility.SHAREABLE, "seller can ship in 20 days"
        )
        self.messages = [
            self.buyer_private_message,
            self.buyer_shareable_message,
            self.seller_private_message,
            self.seller_shareable_message,
        ]

        def constraint(owner, visibility, field, value) -> Constraint:
            return Constraint(
                id=ConstraintId(uuid4()),
                deal_id=self.deal.id,
                owner_organization_id=owner,
                field=field,
                typed_value=value,
                kind=ConstraintKind.HARD_LIMIT,
                visibility=visibility,
                created_at=datetime(2026, 10, 18, tzinfo=UTC),
                source_span="n/a",
            )

        self.buyer_private_constraint = constraint(
            self.buyer_id, Visibility.PRIVATE, "max_budget", "secret-9999-usd"
        )
        self.seller_private_constraint = constraint(
            self.seller_id, Visibility.PRIVATE, "min_price", "secret-8000-usd"
        )
        self.shared_constraint = constraint(self.buyer_id, Visibility.SHAREABLE, "currency", "USD")
        self.constraints = [
            self.buyer_private_constraint,
            self.seller_private_constraint,
            self.shared_constraint,
        ]

        self.repository = FakeCommunicationRepository(self.deal, self.messages, self.constraints)
        self.repository.conversation_owner[self.buyer_conversation_id] = self.buyer_id
        self.repository.conversation_owner[self.seller_conversation_id] = self.seller_id

    def _grant(self, organization_id: UUID, user_id: UUID) -> None:
        self.repository.memberships.add((organization_id, user_id))

    def test_buyer_perspective_sees_buyer_private_and_both_shareable(self) -> None:
        user_id = uuid4()
        self._grant(self.buyer_id, user_id)
        actor = ActorContext(user_id, frozenset({self.buyer_id}))

        context = select_ai_context(actor, self.deal.id, self.buyer_id, self.repository)

        self.assertEqual(
            set(context.messages),
            {self.buyer_private_message, self.buyer_shareable_message, self.seller_shareable_message},
        )
        self.assertEqual(
            list(context.constraints), [self.buyer_private_constraint, self.shared_constraint]
        )

    def test_seller_perspective_sees_seller_private_and_both_shareable(self) -> None:
        user_id = uuid4()
        self._grant(self.seller_id, user_id)
        actor = ActorContext(user_id, frozenset({self.seller_id}))

        context = select_ai_context(actor, self.deal.id, self.seller_id, self.repository)

        self.assertEqual(
            set(context.messages),
            {self.seller_private_message, self.seller_shareable_message, self.buyer_shareable_message},
        )
        self.assertEqual(
            list(context.constraints), [self.seller_private_constraint, self.shared_constraint]
        )

    def test_outsider_actor_is_denied(self) -> None:
        actor = ActorContext(uuid4(), frozenset({OrganizationId(uuid4())}))

        with self.assertRaises(CommunicationNotFound):
            select_ai_context(actor, self.deal.id, self.buyer_id, self.repository)

    def test_actor_not_member_of_requested_perspective_organization_is_denied(self) -> None:
        user_id = uuid4()
        self._grant(self.buyer_id, user_id)
        actor = ActorContext(user_id, frozenset({self.buyer_id}))

        with self.assertRaises(OrganizationAccessDenied):
            select_ai_context(actor, self.deal.id, self.seller_id, self.repository)

    def test_perspective_organization_not_a_party_to_deal_is_denied(self) -> None:
        user_id = uuid4()
        outsider_org = OrganizationId(uuid4())
        self._grant(self.buyer_id, user_id)
        actor = ActorContext(user_id, frozenset({self.buyer_id, outsider_org}))

        with self.assertRaises(CommunicationNotFound):
            select_ai_context(actor, self.deal.id, outsider_org, self.repository)

    def test_missing_deal_is_denied_same_as_inaccessible(self) -> None:
        user_id = uuid4()
        self._grant(self.buyer_id, user_id)
        actor = ActorContext(user_id, frozenset({self.buyer_id}))

        with self.assertRaises(CommunicationNotFound):
            select_ai_context(actor, DealId(uuid4()), self.buyer_id, self.repository)

    def test_context_repr_does_not_leak_message_or_constraint_content(self) -> None:
        user_id = uuid4()
        self._grant(self.buyer_id, user_id)
        actor = ActorContext(user_id, frozenset({self.buyer_id}))

        context = select_ai_context(actor, self.deal.id, self.buyer_id, self.repository)

        rendered = repr(context) + str(context)
        self.assertNotIn("buyer secret margin", rendered)
        self.assertNotIn("secret-9999-usd", rendered)


if __name__ == "__main__":
    unittest.main()
