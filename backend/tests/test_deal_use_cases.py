import unittest
from datetime import UTC, datetime
from uuid import uuid4

from syncally.application.deals import (
    DealNotFoundError,
    DealParticipationRequired,
    create_deal,
    get_deal,
)
from syncally.application.identity import ActorContext
from syncally.domain.deals.deal import Deal, DealStatus
from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import DealId, OrganizationId, UserId


class FakeDealRepository:
    def __init__(self) -> None:
        self.deals: dict[DealId, Deal] = {}
        self.added: list[Deal] = []
        self.looked_up: list[DealId] = []

    def add(self, deal: Deal) -> Deal:
        self.added.append(deal)
        self.deals[deal.id] = deal
        return deal

    def get_by_id(self, deal_id: DealId) -> Deal | None:
        self.looked_up.append(deal_id)
        return self.deals.get(deal_id)


def actor_for(*organization_ids: OrganizationId) -> ActorContext:
    return ActorContext(UserId(uuid4()), frozenset(organization_ids))


class DealUseCaseTests(unittest.TestCase):
    def test_create_persists_a_draft_when_actor_belongs_to_buyer(self) -> None:
        buyer_id = OrganizationId(uuid4())
        seller_id = OrganizationId(uuid4())
        repository = FakeDealRepository()

        deal = create_deal(actor_for(buyer_id), buyer_id, seller_id, repository)

        self.assertIs(repository.added[0], deal)
        self.assertEqual(deal.buyer_organization_id, buyer_id)
        self.assertEqual(deal.seller_organization_id, seller_id)
        self.assertEqual(deal.status, DealStatus.DRAFT)
        self.assertEqual(deal.version, 0)
        self.assertIsNotNone(deal.id)
        self.assertIsNotNone(deal.created_at.tzinfo)
        self.assertEqual(deal.created_at.tzinfo, UTC)

    def test_create_allows_a_member_of_the_seller_organization(self) -> None:
        buyer_id = OrganizationId(uuid4())
        seller_id = OrganizationId(uuid4())
        repository = FakeDealRepository()

        deal = create_deal(actor_for(seller_id), buyer_id, seller_id, repository)

        self.assertIs(repository.added[0], deal)

    def test_create_rejects_same_buyer_and_seller_without_persisting(self) -> None:
        organization_id = OrganizationId(uuid4())
        repository = FakeDealRepository()

        with self.assertRaises(InvariantViolation):
            create_deal(
                actor_for(organization_id),
                organization_id,
                organization_id,
                repository,
            )

        self.assertEqual(repository.added, [])

    def test_create_rejects_actor_without_membership(self) -> None:
        buyer_id = OrganizationId(uuid4())
        seller_id = OrganizationId(uuid4())
        repository = FakeDealRepository()

        with self.assertRaises(DealParticipationRequired):
            create_deal(actor_for(), buyer_id, seller_id, repository)

        self.assertEqual(repository.added, [])

    def test_get_returns_a_deal_for_a_participating_actor(self) -> None:
        buyer_id = OrganizationId(uuid4())
        seller_id = OrganizationId(uuid4())
        deal = Deal(DealId(uuid4()), buyer_id, seller_id, datetime.now(UTC))
        repository = FakeDealRepository()
        repository.deals[deal.id] = deal

        result = get_deal(actor_for(seller_id), deal.id, repository)

        self.assertIs(result, deal)
        self.assertEqual(repository.looked_up, [deal.id])

    def test_get_hides_missing_and_nonparticipant_deals_as_not_found(self) -> None:
        buyer_id = OrganizationId(uuid4())
        seller_id = OrganizationId(uuid4())
        existing = Deal(DealId(uuid4()), buyer_id, seller_id, datetime.now(UTC))
        repository = FakeDealRepository()
        repository.deals[existing.id] = existing
        actor = actor_for(OrganizationId(uuid4()))

        for deal_id in (existing.id, DealId(uuid4())):
            with self.subTest(deal_id=deal_id), self.assertRaises(DealNotFoundError):
                get_deal(actor, deal_id, repository)


if __name__ == "__main__":
    unittest.main()
