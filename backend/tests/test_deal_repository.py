"""Database-backed tests for the SQLAlchemy deal repository adapter."""

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syncally.domain.deals.deal import Deal as DomainDeal
from syncally.domain.deals.deal import DealStatus
from syncally.domain.shared.identifiers import DealId, OrganizationId
from syncally.infrastructure.database import create_database_engine
from syncally.infrastructure.models import (
    Base,
    Deal,
    Organization,
    OrganizationMember,
    OutboxEvent,
    User,
)
from syncally.infrastructure.repositories import SqlAlchemyDealRepository


class DealRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_database_engine("sqlite+pysqlite:///:memory:")
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
        self.assertEqual(loaded.created_at, deal.created_at)
        notification = self.session.scalar(select(OutboxEvent))
        self.assertEqual(notification.event_type, "DEAL_NOTIFICATION")
        self.assertEqual(notification.payload["deal_id"], str(deal.id))
        self.assertEqual(notification.payload["record_id"], str(deal.id))
        self.assertEqual(notification.payload["kind"], "DEAL_CREATED")

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

    def test_add_rejects_missing_buyer_or_seller_reference_without_partial_deal(self) -> None:
        _, buyer, seller = self._seed_participants()
        repository = SqlAlchemyDealRepository(self.session)

        for deal in (
            self._new_deal(uuid4(), seller.id),
            self._new_deal(buyer.id, uuid4()),
        ):
            with self.subTest(deal=deal):
                with self.assertRaises(IntegrityError):
                    repository.add(deal)
                self.session.rollback()
                self.assertIsNone(self.session.get(Deal, deal.id))

    def test_add_rejects_duplicate_deal_id_and_rollback_preserves_original(self) -> None:
        _, buyer, seller = self._seed_participants()
        repository = SqlAlchemyDealRepository(self.session)
        original = self._new_deal(buyer.id, seller.id)
        repository.add(original)
        duplicate = DomainDeal(
            id=original.id,
            buyer_organization_id=original.buyer_organization_id,
            seller_organization_id=original.seller_organization_id,
            created_at=datetime.now(UTC),
        )

        with self.assertRaises(IntegrityError):
            repository.add(duplicate)
        self.session.rollback()

        stored = self.session.get(Deal, original.id)
        self.assertIsNotNone(stored)
        self.assertEqual(stored.buyer_organization_id, buyer.id)
        self.assertEqual(stored.seller_organization_id, seller.id)

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

    def test_list_for_participant_scopes_to_active_memberships(self) -> None:
        user, buyer, seller = self._seed_participants()
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
        first = repository.add(self._new_deal(buyer.id, seller.id))
        second = repository.add(self._new_deal(buyer.id, seller.id))

        listed = repository.list_for_participant(user.id)

        self.assertEqual({deal.id for deal in listed}, {first.id, second.id})
        self.assertEqual(repository.list_for_participant(outsider.id), [])

    def test_list_for_participant_includes_deals_where_the_user_is_the_seller(self) -> None:
        _, buyer, seller = self._seed_participants()
        seller_user = User(email="seller@example.com", display_name="Seller")
        self.session.add(seller_user)
        self.session.flush()
        self.session.add(
            OrganizationMember(
                user_id=seller_user.id,
                organization_id=seller.id,
                status="ACTIVE",
            )
        )
        self.session.commit()
        repository = SqlAlchemyDealRepository(self.session)
        deal = repository.add(self._new_deal(buyer.id, seller.id))

        listed = repository.list_for_participant(seller_user.id)

        self.assertEqual([stored.id for stored in listed], [deal.id])

    def test_list_for_participant_excludes_deals_after_membership_revoked(self) -> None:
        user, buyer, seller = self._seed_participants()
        repository = SqlAlchemyDealRepository(self.session)
        repository.add(self._new_deal(buyer.id, seller.id))

        membership = self.session.scalar(
            select(OrganizationMember).where(
                OrganizationMember.user_id == user.id,
                OrganizationMember.organization_id == buyer.id,
            )
        )
        membership.status = "REVOKED"
        self.session.commit()

        self.assertEqual(repository.list_for_participant(user.id), [])


if __name__ == "__main__":
    unittest.main()
