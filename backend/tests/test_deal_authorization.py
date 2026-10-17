import unittest
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.deals import get_authorized_deal
from syncally.application.identity import ActorContext
from syncally.infrastructure.models import Base, Deal, Organization, OrganizationMember, User


class DealAuthorizationTests(unittest.TestCase):
    def test_unknown_and_unauthorized_deals_have_the_same_response(self) -> None:
        actor = ActorContext(user_id=uuid4(), organization_ids=frozenset())
        existing_deal = Deal(
            id=uuid4(),
            buyer_organization_id=uuid4(),
            seller_organization_id=uuid4(),
            status="DRAFT",
        )

        class FakeSession:
            def __init__(self, deal: Deal | None) -> None:
                self.deal = deal

            def scalar(self, _query: object) -> Deal | None:
                return self.deal

        responses = []
        for deal in (None, existing_deal):
            with self.assertRaises(HTTPException) as raised:
                get_authorized_deal(uuid4(), actor, FakeSession(deal))
            responses.append((raised.exception.status_code, raised.exception.detail))

        self.assertEqual(responses[0], responses[1])
        self.assertEqual(responses[0], (404, "Deal not found"))

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
                with self.assertRaises(HTTPException) as raised:
                    get_authorized_deal(deal.id, actor, session)

            self.assertEqual((raised.exception.status_code, raised.exception.detail), (404, "Deal not found"))
        finally:
            Base.metadata.drop_all(engine)
            engine.dispose()