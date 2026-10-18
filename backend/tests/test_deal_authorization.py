"""Authorization behavior for the deal read use case."""

import unittest
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.application.deals import DealNotFound, get_deal
from syncally.application.identity import ActorContext
from syncally.domain.deals.deal import Deal as DomainDeal
from syncally.domain.shared.identifiers import DealId, OrganizationId
from syncally.infrastructure.models import (
    Base,
    Deal,
    Organization,
    OrganizationMember,
    User,
)
from syncally.infrastructure.repositories import SqlAlchemyDealRepository


def _domain_deal(buyer_id: UUID, seller_id: UUID) -> DomainDeal:
    return DomainDeal(
        id=DealId(uuid4()),
        buyer_organization_id=OrganizationId(buyer_id),
        seller_organization_id=OrganizationId(seller_id),
        created_at=datetime.now(UTC),
    )


class FakeDealRepository:
    """Repository fake that returns one preloaded deal regardless of scope."""

    def __init__(self, deal: DomainDeal | None) -> None:
        self._deal = deal

    def active_organization_exists(self, organization_id: UUID) -> bool:
        return True

    def add(self, deal: DomainDeal) -> DomainDeal:
        return deal

    def get_for_participant(self, deal_id: UUID, user_id: UUID) -> DomainDeal | None:
        return self._deal


class DealAuthorizationTests(unittest.TestCase):
    def test_unknown_and_unauthorized_deals_have_the_same_response(self) -> None:
        actor = ActorContext(user_id=uuid4(), organization_ids=frozenset())
        existing_deal = _domain_deal(uuid4(), uuid4())

        responses = []
        for repository in (FakeDealRepository(None), FakeDealRepository(existing_deal)):
            with self.assertRaises(DealNotFound) as raised:
                get_deal(actor, uuid4(), repository)
            responses.append(str(raised.exception))

        self.assertEqual(responses[0], responses[1])
        self.assertEqual(responses[0], "Deal not found")

    def test_revoked_membership_cannot_read_deal_with_stale_actor_context(self) -> None:
        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        try:
            user = User(email="member@example.com", display_name="Member")
            organization = Organization(legal_name="Member Co", country_code="US")
            seller = Organization(legal_name="Seller Co", country_code="CA")
            with Session(engine) as session:
                session.add_all([user, organization, seller])
                session.flush()
                session.add(
                    OrganizationMember(
                        user_id=user.id,
                        organization_id=organization.id,
                        status="ACTIVE",
                    )
                )
                deal = Deal(
                    buyer_organization_id=organization.id,
                    seller_organization_id=seller.id,
                    status="DRAFT",
                    version=0,
                )
                session.add(deal)
                session.commit()

                session.execute(
                    update(OrganizationMember)
                    .where(OrganizationMember.user_id == user.id)
                    .values(status="REVOKED")
                )
                session.commit()

                actor = ActorContext(
                    user_id=user.id,
                    organization_ids=frozenset({organization.id}),
                )
                repository = SqlAlchemyDealRepository(session)
                with self.assertRaises(DealNotFound) as raised:
                    get_deal(actor, deal.id, repository)

                # The deal still exists; only the stale authorization is rejected.
                self.assertIsNotNone(
                    session.scalar(select(Deal).where(Deal.id == deal.id))
                )

            self.assertEqual(str(raised.exception), "Deal not found")
        finally:
            Base.metadata.drop_all(engine)
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
