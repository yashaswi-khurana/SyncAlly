"""Unit tests for the deal create/get use cases using a fake repository."""

import unittest
from datetime import UTC, datetime
from uuid import UUID, uuid4

from syncally.application.deals import (
    CreateDealCommand,
    DealAccessDenied,
    DealNotFound,
    create_deal,
    get_deal,
)
from syncally.application.identity import ActorContext
from syncally.domain.deals.deal import Deal, DealStatus
from syncally.domain.shared.errors import InvariantViolation


class FakeDealRepository:
    """In-memory repository recording the calls the use cases make."""

    def __init__(self, active_organizations: set[UUID] | None = None) -> None:
        self.active_organizations = active_organizations or set()
        self.deals: dict[UUID, Deal] = {}
        self.added: list[Deal] = []

    def active_organization_exists(self, organization_id: UUID) -> bool:
        return organization_id in self.active_organizations

    def add(self, deal: Deal) -> Deal:
        self.deals[deal.id] = deal
        self.added.append(deal)
        return deal

    def get_for_participant(self, deal_id: UUID, user_id: UUID) -> Deal | None:
        return self.deals.get(deal_id)


class DealUseCaseTests(unittest.TestCase):
    def test_create_deal_starts_a_draft_for_the_buyer_organization(self) -> None:
        buyer_id, seller_id = uuid4(), uuid4()
        repository = FakeDealRepository({buyer_id, seller_id})
        actor = ActorContext(user_id=uuid4(), organization_ids=frozenset({buyer_id}))
        now = datetime(2026, 10, 18, tzinfo=UTC)

        deal = create_deal(
            actor,
            CreateDealCommand(buyer_id, seller_id),
            repository,
            now=now,
        )

        self.assertEqual(deal.buyer_organization_id, buyer_id)
        self.assertEqual(deal.seller_organization_id, seller_id)
        self.assertEqual(deal.status, DealStatus.DRAFT)
        self.assertEqual(deal.version, 0)
        self.assertEqual(deal.created_at, now)
        self.assertEqual(repository.added, [deal])

    def test_create_deal_rejects_actor_without_buyer_membership(self) -> None:
        buyer_id, seller_id = uuid4(), uuid4()
        repository = FakeDealRepository({buyer_id, seller_id})
        actor = ActorContext(user_id=uuid4(), organization_ids=frozenset({uuid4()}))

        with self.assertRaises(DealAccessDenied):
            create_deal(actor, CreateDealCommand(buyer_id, seller_id), repository)

        self.assertEqual(repository.added, [])

    def test_create_deal_rejects_identical_buyer_and_seller(self) -> None:
        organization_id = uuid4()
        repository = FakeDealRepository({organization_id})
        actor = ActorContext(
            user_id=uuid4(), organization_ids=frozenset({organization_id})
        )

        with self.assertRaises(InvariantViolation):
            create_deal(
                actor,
                CreateDealCommand(organization_id, organization_id),
                repository,
            )

        self.assertEqual(repository.added, [])

    def test_create_deal_rejects_unknown_organizations(self) -> None:
        buyer_id, seller_id = uuid4(), uuid4()
        actor = ActorContext(user_id=uuid4(), organization_ids=frozenset({buyer_id}))

        with self.assertRaises(DealNotFound):
            create_deal(
                actor,
                CreateDealCommand(buyer_id, seller_id),
                FakeDealRepository({buyer_id}),
            )

    def test_get_deal_returns_a_deal_for_a_participant(self) -> None:
        buyer_id, seller_id = uuid4(), uuid4()
        repository = FakeDealRepository({buyer_id, seller_id})
        actor = ActorContext(user_id=uuid4(), organization_ids=frozenset({buyer_id}))
        deal = create_deal(actor, CreateDealCommand(buyer_id, seller_id), repository)

        loaded = get_deal(actor, deal.id, repository)

        self.assertIs(loaded, deal)

    def test_get_deal_hides_missing_and_non_participating_deals(self) -> None:
        repository = FakeDealRepository()
        actor = ActorContext(user_id=uuid4(), organization_ids=frozenset({uuid4()}))

        with self.assertRaises(DealNotFound):
            get_deal(actor, uuid4(), repository)


if __name__ == "__main__":
    unittest.main()
