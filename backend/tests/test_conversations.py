"""Conversation privacy and human confirmation contracts."""

import unittest
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from syncally.application.conversations import (
    ConcurrentConstraintUpdate,
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
        self.active_memberships: set[tuple[UUID, UUID]] = set()
        self.source_message_deals = (
            {constraint.source_message_id: constraint.deal_id}
            if constraint is not None and constraint.source_message_id is not None
            else {}
        )
        self.stored_version = constraint.version if constraint is not None else 0
        self.fail_save = False
        self.concurrent_update = False
        self.return_wrong_id = False

    def get_deal_for_participant(self, deal_id: UUID, user_id: UUID) -> Deal | None:
        if self.deal is None or self.deal.id != deal_id:
            return None
        parties = (self.deal.buyer_organization_id, self.deal.seller_organization_id)
        return self.deal if any(
            (organization_id, user_id) in self.active_memberships
            for organization_id in parties
        ) else None

    def get_constraint_for_deal(
        self, deal_id: UUID, constraint_id: UUID, user_id: UUID
    ) -> Constraint | None:
        if (
            self.constraint is None
            or self.constraint.deal_id != deal_id
            or (not self.return_wrong_id and self.constraint.id != constraint_id)
            or (self.constraint.owner_organization_id, user_id) not in self.active_memberships
        ):
            return None
        return self.constraint

    def save_constraint(
        self,
        constraint: Constraint,
        *,
        expected_version: int,
        actor_user_id: UUID,
    ) -> Constraint:
        if self.fail_save:
            raise RuntimeError("save failed")
        if self.concurrent_update:
            self.stored_version += 1
            self.concurrent_update = False
        if (
            self.constraint is None
            or (constraint.owner_organization_id, actor_user_id) not in self.active_memberships
            or (
                constraint.source_message_id is not None
                and self.source_message_deals.get(constraint.source_message_id) != constraint.deal_id
            )
        ):
            raise ConstraintNotFound("Constraint not found")
        if expected_version != self.stored_version:
            raise ConcurrentConstraintUpdate("Constraint changed concurrently")
        if constraint.version != expected_version + 1:
            raise AssertionError("Constraint version must advance once")
        self.stored_version = constraint.version
        self.constraint = constraint
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
            participant_organization_id=self.buyer_id,
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
                participant_organization_id=self.buyer_id,
                created_at=datetime.now(UTC),
            )
        with self.assertRaises(InvariantViolation):
            Conversation(
                id=ConversationId(uuid4()),
                deal_id=self.deal.id,
                participant_organization_id=None,  # type: ignore[arg-type]
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

    def test_constraint_requires_nonempty_provenance(self) -> None:
        with self.assertRaises(InvariantViolation):
            replace(self.constraint, source_message_id=None, source_span=None)
        with self.assertRaises(InvariantViolation):
            replace(self.constraint, source_span="  ")

    def test_visibility_maps_legacy_internal_storage_value(self) -> None:
        self.assertIs(Visibility.from_storage("INTERNAL"), Visibility.PRIVATE)
        self.assertIs(Visibility.from_storage("SHAREABLE"), Visibility.SHAREABLE)

    def test_constraint_visibility_cannot_be_changed_after_creation(self) -> None:
        with self.assertRaises(AttributeError):
            self.constraint.visibility = Visibility.SHAREABLE
        with self.assertRaises(AttributeError):
            del self.constraint.visibility

    def test_reconstitute_restores_review_state_version_and_unit(self) -> None:
        reviewer = UserId(uuid4())
        confirmed_at = datetime(2026, 10, 18, 12, tzinfo=UTC)
        restored = Constraint.reconstitute(
            id=self.constraint.id,
            deal_id=self.constraint.deal_id,
            owner_organization_id=self.constraint.owner_organization_id,
            field=self.constraint.field,
            typed_value=self.constraint.typed_value,
            kind=self.constraint.kind,
            visibility=self.constraint.visibility,
            created_at=self.constraint.created_at,
            status=ConstraintStatus.SUPERSEDED,
            confirmed_by=reviewer,
            confirmed_at=confirmed_at,
            version=3,
            currency_or_unit="USD",
            source_message_id=self.constraint.source_message_id,
            source_span=self.constraint.source_span,
        )

        self.assertEqual(restored.status, ConstraintStatus.SUPERSEDED)
        self.assertEqual(restored.confirmed_by, reviewer)
        self.assertEqual(restored.confirmed_at, confirmed_at)
        self.assertEqual(restored.version, 3)
        self.assertEqual(restored.currency_or_unit, "USD")

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
            participant_organization_id=self.buyer_id,
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

        shareable = replace(
            self.constraint,
            id=ConstraintId(uuid4()),
            visibility=Visibility.SHAREABLE,
        )
        self.assertTrue(can_view_constraint(seller, self.deal, shareable))
        self.assertFalse(can_view_constraint(outsider, self.deal, self.constraint))

    def test_authorized_owner_confirmation_records_human_and_does_not_approve_deal(self) -> None:
        user_id = uuid4()
        actor = ActorContext(user_id, frozenset({self.buyer_id}))
        repository = FakeConstraintRepository(self.deal, self.constraint)
        repository.active_memberships.add((self.buyer_id, user_id))
        now = datetime(2026, 10, 18, 12, tzinfo=UTC)

        confirmed = confirm_constraint(
            actor,
            self.deal.id,
            self.constraint.id,
            repository,
            now=now,
        )

        self.assertIsNot(confirmed, self.constraint)
        self.assertEqual(confirmed.status, ConstraintStatus.CONFIRMED)
        self.assertEqual(confirmed.confirmed_by, user_id)
        self.assertEqual(confirmed.confirmed_at, now)
        self.assertEqual(confirmed.version, 1)
        self.assertEqual(repository.saved, [confirmed])
        self.assertEqual(self.constraint.status, ConstraintStatus.EXTRACTED)
        self.assertEqual(self.deal.status, DealStatus.DRAFT)
        self.assertIsNone(self.deal.current_agreement_version_id)

    def test_counterparty_cannot_confirm_another_organizations_fact(self) -> None:
        user_id = uuid4()
        actor = ActorContext(user_id, frozenset({self.seller_id}))
        repository = FakeConstraintRepository(self.deal, self.constraint)
        repository.active_memberships.add((self.seller_id, user_id))

        with self.assertRaises(ConstraintNotFound):
            confirm_constraint(actor, self.deal.id, self.constraint.id, repository)

        self.assertEqual(self.constraint.status, ConstraintStatus.EXTRACTED)
        self.assertEqual(repository.saved, [])

    def test_revoked_owner_membership_in_stale_actor_context_cannot_confirm(self) -> None:
        user_id = uuid4()
        actor = ActorContext(user_id, frozenset({self.buyer_id, self.seller_id}))
        repository = FakeConstraintRepository(self.deal, self.constraint)
        repository.active_memberships.add((self.seller_id, user_id))

        with self.assertRaises(ConstraintNotFound):
            confirm_constraint(actor, self.deal.id, self.constraint.id, repository)

        self.assertEqual(self.constraint.status, ConstraintStatus.EXTRACTED)
        self.assertEqual(repository.saved, [])

    def test_repository_result_with_wrong_constraint_id_is_rejected(self) -> None:
        user_id = uuid4()
        actor = ActorContext(user_id, frozenset({self.buyer_id}))
        repository = FakeConstraintRepository(self.deal, self.constraint)
        repository.active_memberships.add((self.buyer_id, user_id))
        repository.return_wrong_id = True

        with self.assertRaises(ConstraintNotFound):
            confirm_constraint(actor, self.deal.id, ConstraintId(uuid4()), repository)

        self.assertEqual(self.constraint.status, ConstraintStatus.EXTRACTED)
        self.assertEqual(repository.saved, [])

    def test_nonparticipant_cannot_confirm_and_missing_is_hidden(self) -> None:
        actor = ActorContext(uuid4(), frozenset({OrganizationId(uuid4())}))
        repository = FakeConstraintRepository(self.deal, self.constraint)

        with self.assertRaises(ConstraintNotFound):
            confirm_constraint(actor, self.deal.id, self.constraint.id, repository)

        self.assertEqual(repository.saved, [])

    def test_same_actor_confirmation_retry_returns_saved_result(self) -> None:
        actor = ActorContext(uuid4(), frozenset({self.buyer_id}))
        repository = FakeConstraintRepository(self.deal, self.constraint)
        repository.active_memberships.add((self.buyer_id, actor.user_id))

        confirmed = confirm_constraint(actor, self.deal.id, self.constraint.id, repository)
        retried = confirm_constraint(actor, self.deal.id, self.constraint.id, repository)

        self.assertIs(retried, confirmed)
        self.assertEqual(repository.saved, [confirmed])

    def test_failed_save_does_not_mutate_loaded_constraint(self) -> None:
        actor = ActorContext(uuid4(), frozenset({self.buyer_id}))
        repository = FakeConstraintRepository(self.deal, self.constraint)
        repository.active_memberships.add((self.buyer_id, actor.user_id))
        repository.fail_save = True

        with self.assertRaisesRegex(RuntimeError, "save failed"):
            confirm_constraint(actor, self.deal.id, self.constraint.id, repository)

        self.assertEqual(self.constraint.status, ConstraintStatus.EXTRACTED)
        self.assertEqual(self.constraint.version, 0)
        self.assertIsNone(self.constraint.confirmed_by)

    def test_stale_confirmation_version_is_rejected(self) -> None:
        actor = ActorContext(uuid4(), frozenset({self.buyer_id}))
        repository = FakeConstraintRepository(self.deal, self.constraint)
        repository.active_memberships.add((self.buyer_id, actor.user_id))
        repository.concurrent_update = True

        with self.assertRaises(ConcurrentConstraintUpdate):
            confirm_constraint(actor, self.deal.id, self.constraint.id, repository)

        self.assertEqual(self.constraint.status, ConstraintStatus.EXTRACTED)
        self.assertEqual(repository.saved, [])

    def test_cross_deal_source_is_rejected_before_confirmation_is_saved(self) -> None:
        actor = ActorContext(uuid4(), frozenset({self.buyer_id}))
        repository = FakeConstraintRepository(self.deal, self.constraint)
        repository.active_memberships.add((self.buyer_id, actor.user_id))
        repository.source_message_deals[self.message.id] = DealId(uuid4())

        with self.assertRaises(ConstraintNotFound):
            confirm_constraint(actor, self.deal.id, self.constraint.id, repository)

        self.assertEqual(self.constraint.status, ConstraintStatus.EXTRACTED)
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
