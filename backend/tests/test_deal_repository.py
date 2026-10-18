"""Database-backed tests for the SQLAlchemy deal repository adapter."""

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.domain.deals.deal import Deal as DomainDeal
from syncally.domain.deals.deal import DealStatus
from syncally.domain.shared.identifiers import DealId, OrganizationId
from syncally.infrastructure.models import (
    Base,
    Deal,
    Organization,
    OrganizationMember,
    User,
)
from syncally.infrastructure.repositories import SqlAlchemyDealRepository


class DealRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _seed_participants(self) -> tuple[User, Organization, Organization]:
        user = User(email="member@example.com", display_name="Member")
        buyer = Organization(legal_name="Buyer Co", country_code="US")
        seller = Organization(legal_name="Seller Co", country_code="CA")
        self.session.add_all([user, buyer, seller])
        self.session.flush()
        self.session.add(
            OrganizationMember(
                user_id=user.id,
                organization_id=buyer.id,
                status="ACTIVE",
            )
        )
        self.session.commit()
        return user, buyer, seller

    def _new_deal(self, buyer_id, seller_id) -> DomainDeal:
        return DomainDeal(
            id=DealId(uuid4()),
            buyer_organization_id=OrganizationId(buyer_id),
            seller_organization_id=OrganizationId(seller_id),
            created_at=datetime.now(UTC),
        )

    def test_add_persists_and_get_for_participant_loads_the_domain_deal(self) -> None:
        user, buyer, seller = self._seed_participants()
        repository = SqlAlchemyDealRepository(self.session)
        deal = self._new_deal(buyer.id, seller.id)

        stored = repository.add(deal)
        loaded = repository.get_for_participant(deal.id, user.id)

        self.assertEqual(stored.id, deal.id)
        self.assertEqual(loaded, stored)
        self.assertEqual(loaded.status, DealStatus.DRAFT)
        self.assertEqual(loaded.version, 0)
        self.assertEqual(loaded.buyer_organization_id, buyer.id)
        self.assertEqual(loaded.seller_organization_id, seller.id)

    def test_active_organization_exists_only_for_active_organizations(self) -> None:
        _, buyer, _ = self._seed_participants()
        inactive = Organization(
            legal_name="Inactive Co", country_code="GB", status="INACTIVE"
        )
        self.session.add(inactive)
        self.session.commit()
        repository = SqlAlchemyDealRepository(self.session)

        self.assertTrue(repository.active_organization_exists(buyer.id))
        self.assertFalse(repository.active_organization_exists(inactive.id))
        self.assertFalse(repository.active_organization_exists(uuid4()))

    def test_get_for_participant_hides_deals_for_non_members(self) -> None:
        _, buyer, seller = self._seed_participants()
        outsider = User(email="outsider@example.com", display_name="Outsider")
        outsider_org = Organization(legal_name="Outsider Co", country_code="DE")
        self.session.add_all([outsider, outsider_org])
        self.session.flush()
        self.session.add(
            OrganizationMember(
                user_id=outsider.id,
                organization_id=outsider_org.id,
                status="ACTIVE",
            )
        )
        self.session.commit()
        repository = SqlAlchemyDealRepository(self.session)
        deal = repository.add(self._new_deal(buyer.id, seller.id))

        self.assertIsNone(repository.get_for_participant(deal.id, outsider.id))
        self.assertIsNone(repository.get_for_participant(uuid4(), uuid4()))

    def test_get_for_participant_hides_deals_after_membership_revoked(self) -> None:
        user, buyer, seller = self._seed_participants()
        repository = SqlAlchemyDealRepository(self.session)
        deal = repository.add(self._new_deal(buyer.id, seller.id))

        membership = self.session.scalar(
            select(OrganizationMember).where(
                OrganizationMember.user_id == user.id,
                OrganizationMember.organization_id == buyer.id,
            )
        )
        membership.status = "REVOKED"
        self.session.commit()

        self.assertIsNotNone(self.session.scalar(select(Deal).where(Deal.id == deal.id)))
        self.assertIsNone(repository.get_for_participant(deal.id, user.id))


if __name__ == "__main__":
    unittest.main()
