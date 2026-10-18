"""Conversation privacy and human confirmation contracts."""

import unittest
from datetime import UTC, datetime
from uuid import UUID, uuid4

from syncally.application.conversations import (
    ConstraintNotFound,
    can_view_constraint,
    can_view_message,
    confirm_constraint,
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
from syncally.domain.deals.deal import Deal, DealStatus
from syncally.domain.shared.errors import InvalidTransition, InvariantViolation
from syncally.domain.shared.identifiers import (
    ConstraintId,
    ConversationId,
    DealId,
    MessageId,
    OrganizationId,
    UserId,
)


class FakeConstraintRepository:
    def __init__(self, deal: Deal | None, constraint: Constraint | None) -> None:
        self.deal = deal
        self.constraint = constraint
        self.saved: list[Constraint] = []

    def get_deal_for_participant(self, deal_id: UUID, user_id: UUID) -> Deal | None:
        return self.deal if self.deal is not None and self.deal.id == deal_id else None

    def get_constraint_for_deal(
        self, deal_id: UUID, constraint_id: UUID
    ) -> Constraint | None:
        if (
            self.constraint is None
            or self.constraint.deal_id != deal_id
            or self.constraint.id != constraint_id
        ):
            return None
        return self.constraint

    def save_constraint(self, constraint: Constraint) -> Constraint:
        self.saved.append(constraint)
        return constraint


class ConversationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.buyer_id = OrganizationId(uuid4())
        self.seller_id = OrganizationId(uuid4())
        self.deal = Deal(
            id=DealId(uuid4()),
            buyer_organization_id=self.buyer_id,
            seller_organization_id=self.seller_id,
            created_at=datetime(2026, 10, 18, tzinfo=UTC),
        )
        self.conversation = Conversation(
            id=ConversationId(uuid4()),
            deal_id=self.deal.id,
            owner_organization_id=self.buyer_id,
            created_at=datetime(2026, 10, 18, tzinfo=UTC),
        )
        self.message = Message(
            id=MessageId(uuid4()),
            conversation_id=self.conversation.id,
            author_user_id=UserId(uuid4()),
            author_agent_id=None,
            body="Delivery needed before 30 June",
            visibility=Visibility.PRIVATE,
            source_type=MessageSourceType.USER,
            created_at=datetime(2026, 10, 18, tzinfo=UTC),
        )
        self.constraint = Constraint(
            id=ConstraintId(uuid4()),
            deal_id=self.deal.id,
            owner_organization_id=self.buyer_id,
            field="delivery_deadline",
            typed_value="2027-06-30",
            kind=ConstraintKind.HARD_LIMIT,
            visibility=Visibility.PRIVATE,
            created_at=datetime(2026, 10, 18, tzinfo=UTC),
            source_message_id=self.message.id,
            source_span="before 30 June",
        )

    def test_conversation_requires_deal_and_organization_owner(self) -> None:
        with self.assertRaises(InvariantViolation):
            Conversation(
                id=ConversationId(uuid4()),
                deal_id=None,  # type: ignore[arg-type]
                owner_organization_id=self.buyer_id,
                created_at=datetime.now(UTC),
            )
        with self.assertRaises(InvariantViolation):
            Conversation(
                id=ConversationId(uuid4()),
                deal_id=self.deal.id,
                owner_organization_id=None,  # type: ignore[arg-type]
                created_at=datetime.now(UTC),
            )

    def test_message_requires_visibility_and_exactly_one_author(self) -> None:
        with self.assertRaises(InvariantViolation):
            Message(
                id=MessageId(uuid4()),
                conversation_id=self.conversation.id,
                author_user_id=UserId(uuid4()),
                author_agent_id=None,
                body="hello",
                visibility=None,  # type: ignore[arg-type]
                source_type=MessageSourceType.USER,
                created_at=datetime.now(UTC),
            )

    def test_message_requires_a_conversation_scope(self) -> None:
        with self.assertRaises(InvariantViolation):
            Message(
                id=MessageId(uuid4()),
                conversation_id=None,  # type: ignore[arg-type]
                author_user_id=UserId(uuid4()),
                author_agent_id=None,
                body="hello",
                visibility=Visibility.PRIVATE,
                source_type=MessageSourceType.USER,
                created_at=datetime.now(UTC),
            )
        with self.assertRaises(InvariantViolation):
            Message(
                id=MessageId(uuid4()),
                conversation_id=self.conversation.id,
                author_user_id=None,
                author_agent_id=None,
                body="hello",
                visibility=Visibility.PRIVATE,
                source_type=MessageSourceType.AGENT,
                created_at=datetime.now(UTC),
            )

    def test_constraint_requires_deal_owner_and_visibility(self) -> None:
        with self.assertRaises(InvariantViolation):
            Constraint(
                id=ConstraintId(uuid4()),
                deal_id=None,  # type: ignore[arg-type]
                owner_organization_id=self.buyer_id,
                field="price",
                typed_value="10 USD",
                kind=ConstraintKind.HARD_LIMIT,
                visibility=Visibility.PRIVATE,
                created_at=datetime.now(UTC),
            )
        with self.assertRaises(InvariantViolation):
            Constraint(
                id=ConstraintId(uuid4()),
                deal_id=self.deal.id,
                owner_organization_id=None,  # type: ignore[arg-type]
                field="price",
                typed_value="10 USD",
                kind=ConstraintKind.HARD_LIMIT,
                visibility=Visibility.PRIVATE,
                created_at=datetime.now(UTC),
            )
        with self.assertRaises(InvariantViolation):
            Constraint(
                id=ConstraintId(uuid4()),
                deal_id=self.deal.id,
                owner_organization_id=self.buyer_id,
                field="price",
                typed_value="10 USD",
                kind=ConstraintKind.HARD_LIMIT,
                visibility=None,  # type: ignore[arg-type]
                created_at=datetime.now(UTC),
            )

    def test_extracted_constraint_starts_unconfirmed_with_provenance(self) -> None:
        self.assertEqual(self.constraint.status, ConstraintStatus.EXTRACTED)
        self.assertIsNone(self.constraint.confirmed_by)
        self.assertIsNone(self.constraint.confirmed_at)
        self.assertEqual(self.constraint.source_message_id, self.message.id)
        self.assertEqual(self.constraint.source_span, "before 30 June")

    def test_private_and_shareable_message_access_is_party_and_owner_scoped(self) -> None:
        buyer = ActorContext(uuid4(), frozenset({self.buyer_id}))
        seller = ActorContext(uuid4(), frozenset({self.seller_id}))
        outsider = ActorContext(uuid4(), frozenset({OrganizationId(uuid4())}))

        self.assertTrue(can_view_message(buyer, self.deal, self.conversation, self.message))
        self.assertFalse(can_view_message(seller, self.deal, self.conversation, self.message))
        self.assertFalse(can_view_message(outsider, self.deal, self.conversation, self.message))

        shareable = Message(
            id=MessageId(uuid4()),
            conversation_id=self.conversation.id,
            author_user_id=None,
            author_agent_id="extractor-v1",
            body="The buyer needs delivery by 30 June",
            visibility=Visibility.SHAREABLE,
            source_type=MessageSourceType.AGENT,
            created_at=datetime.now(UTC),
        )
        self.assertTrue(can_view_message(buyer, self.deal, self.conversation, shareable))
        self.assertTrue(can_view_message(seller, self.deal, self.conversation, shareable))
        self.assertFalse(can_view_message(outsider, self.deal, self.conversation, shareable))

    def test_message_scope_mismatch_is_not_visible(self) -> None:
        other_conversation = Conversation(
            id=ConversationId(uuid4()),
            deal_id=self.deal.id,
            owner_organization_id=self.buyer_id,
            created_at=datetime.now(UTC),
        )
        buyer = ActorContext(uuid4(), frozenset({self.buyer_id}))
        self.assertFalse(
            can_view_message(buyer, self.deal, other_conversation, self.message)
        )

    def test_private_and_shareable_constraint_access_is_party_and_owner_scoped(self) -> None:
        buyer = ActorContext(uuid4(), frozenset({self.buyer_id}))
        seller = ActorContext(uuid4(), frozenset({self.seller_id}))
        outsider = ActorContext(uuid4(), frozenset({OrganizationId(uuid4())}))

        self.assertTrue(can_view_constraint(buyer, self.deal, self.constraint))
        self.assertFalse(can_view_constraint(seller, self.deal, self.constraint))
        self.assertFalse(can_view_constraint(outsider, self.deal, self.constraint))

        self.constraint.visibility = Visibility.SHAREABLE
        self.assertTrue(can_view_constraint(seller, self.deal, self.constraint))
        self.assertFalse(can_view_constraint(outsider, self.deal, self.constraint))

    def test_authorized_owner_confirmation_records_human_and_does_not_approve_deal(self) -> None:
        user_id = uuid4()
        actor = ActorContext(user_id, frozenset({self.buyer_id}))
        repository = FakeConstraintRepository(self.deal, self.constraint)
        now = datetime(2026, 10, 18, 12, tzinfo=UTC)

        confirmed = confirm_constraint(
            actor,
            self.deal.id,
            self.constraint.id,
            repository,
            now=now,
        )

        self.assertIs(confirmed, self.constraint)
        self.assertEqual(confirmed.status, ConstraintStatus.CONFIRMED)
        self.assertEqual(confirmed.confirmed_by, user_id)
        self.assertEqual(confirmed.confirmed_at, now)
        self.assertEqual(confirmed.version, 1)
        self.assertEqual(repository.saved, [confirmed])
        self.assertEqual(self.deal.status, DealStatus.DRAFT)
        self.assertIsNone(self.deal.current_agreement_version_id)

    def test_counterparty_cannot_confirm_another_organizations_fact(self) -> None:
        actor = ActorContext(uuid4(), frozenset({self.seller_id}))
        repository = FakeConstraintRepository(self.deal, self.constraint)

        with self.assertRaises(ConstraintNotFound):
            confirm_constraint(actor, self.deal.id, self.constraint.id, repository)

        self.assertEqual(self.constraint.status, ConstraintStatus.EXTRACTED)
        self.assertEqual(repository.saved, [])

    def test_nonparticipant_cannot_confirm_and_missing_is_hidden(self) -> None:
        actor = ActorContext(uuid4(), frozenset({OrganizationId(uuid4())}))
        repository = FakeConstraintRepository(self.deal, self.constraint)

        with self.assertRaises(ConstraintNotFound):
            confirm_constraint(actor, self.deal.id, self.constraint.id, repository)

        self.assertEqual(repository.saved, [])

    def test_confirmation_is_single_transition(self) -> None:
        self.constraint.confirm(
            confirmed_by=UserId(uuid4()), confirmed_at=datetime.now(UTC)
        )
        with self.assertRaises(InvalidTransition):
            self.constraint.confirm(
                confirmed_by=UserId(uuid4()), confirmed_at=datetime.now(UTC)
            )

    def test_clarified_extraction_can_be_confirmed_by_owner(self) -> None:
        self.constraint.request_clarification()
        self.constraint.confirm(
            confirmed_by=UserId(uuid4()), confirmed_at=datetime.now(UTC)
        )

        self.assertEqual(self.constraint.status, ConstraintStatus.CONFIRMED)
        self.assertEqual(self.constraint.version, 2)

    def test_failed_confirmation_keeps_constraint_extracted(self) -> None:
        with self.assertRaises(InvariantViolation):
            self.constraint.confirm(
                confirmed_by=UserId(uuid4()), confirmed_at=None  # type: ignore[arg-type]
            )

        self.assertEqual(self.constraint.status, ConstraintStatus.EXTRACTED)
        self.assertIsNone(self.constraint.confirmed_by)
        self.assertIsNone(self.constraint.confirmed_at)


if __name__ == "__main__":
    unittest.main()
