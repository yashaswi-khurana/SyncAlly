import unittest
from uuid import uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.infrastructure.models import (
    Base,
    Deal,
    Organization,
    OrganizationMember,
    OutboxEvent,
    User,
)


class DatabasePersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def test_initial_records_can_be_saved_and_loaded(self) -> None:
        organization_id = uuid4()
        user_id = uuid4()
        organization = Organization(id=organization_id, legal_name="Buyer Co", country_code="US")
        user = User(id=user_id, email="buyer@example.com", display_name="Buyer")
        with Session(self.engine) as session:
            session.add_all([organization, user])
            session.flush()
            membership = OrganizationMember(
                organization_id=organization.id,
                user_id=user.id,
                role="ADMIN",
            )
            session.add(membership)
            session.commit()

        with Session(self.engine) as session:
            loaded_membership = session.scalar(select(OrganizationMember))
            loaded_organization = session.get(Organization, organization_id)
            loaded_user = session.get(User, user_id)

        self.assertIsNotNone(loaded_membership)
        self.assertEqual(loaded_membership.organization_id, organization_id)
        self.assertEqual(loaded_organization.legal_name, "Buyer Co")
        self.assertEqual(loaded_user.email, "buyer@example.com")

    def test_session_rollback_discards_records_after_an_error(self) -> None:
        organization = Organization(legal_name="Rollback Co", country_code="GB")
        with Session(self.engine) as session:
            session.add(organization)
            session.flush()
            session.rollback()

            self.assertIsNone(session.get(Organization, organization.id))

    def test_deal_and_outbox_event_commit_and_rollback_together(self) -> None:
        buyer_id = uuid4()
        seller_id = uuid4()
        buyer = Organization(id=buyer_id, legal_name="Buyer Co", country_code="US")
        seller = Organization(id=seller_id, legal_name="Seller Co", country_code="CA")
        with Session(self.engine) as session:
            session.add_all([buyer, seller])
            session.commit()

        deal_id = uuid4()
        with self.assertRaises(RuntimeError):
            with Session(self.engine) as session, session.begin():
                session.add(
                    Deal(
                        id=deal_id,
                        buyer_organization_id=buyer_id,
                        seller_organization_id=seller_id,
                    )
                )
                session.add(
                    OutboxEvent(
                        aggregate_type="deal",
                        aggregate_id=deal_id,
                        event_type="deal.created",
                        payload={"deal_id": str(deal_id)},
                    )
                )
                session.flush()
                raise RuntimeError("simulate transaction failure")

        with Session(self.engine) as session:
            deal_count = session.scalar(
                select(func.count()).select_from(Deal).where(Deal.id == deal_id)
            )
            event_count = session.scalar(
                select(func.count())
                .select_from(OutboxEvent)
                .where(OutboxEvent.aggregate_id == deal_id)
            )

        self.assertEqual(deal_count, 0)
        self.assertEqual(event_count, 0)
