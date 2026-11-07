"""HTTP endpoint tests for deal reminders API."""

import asyncio
import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.auth import get_current_actor
from syncally.api.main import app
from syncally.application.identity import ActorContext
from syncally.domain.reminders.reminder import (
    DealReminder,
    ReminderScope,
    ReminderStatus,
)
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import (
    AgreementVersion,
    Base,
    Deal,
    Organization,
    OrganizationMember,
    PaymentMilestone,
    User,
)
from syncally.infrastructure.repositories.reminders import SqlAlchemyReminderRepository


class RemindersRoutesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.now = datetime.now(UTC)
        self._seed()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _seed(self) -> None:
        self.buyer_org = Organization(id=uuid4(), legal_name="Buyer Corp", country_code="US")
        self.seller_org = Organization(id=uuid4(), legal_name="Seller Corp", country_code="DE")
        self.outsider_org = Organization(id=uuid4(), legal_name="Outsider Corp", country_code="FR")

        self.buyer_user = User(id=uuid4(), email="buyer@test.com", display_name="Buyer User")
        self.seller_user = User(id=uuid4(), email="seller@test.com", display_name="Seller User")
        self.outsider_user = User(id=uuid4(), email="outsider@test.com", display_name="Outsider User")

        self.session.add_all([
            self.buyer_org, self.seller_org, self.outsider_org,
            self.buyer_user, self.seller_user, self.outsider_user,
        ])
        self.session.flush()

        self.session.add_all([
            OrganizationMember(user_id=self.buyer_user.id, organization_id=self.buyer_org.id, role="ADMIN", status="ACTIVE"),
            OrganizationMember(user_id=self.seller_user.id, organization_id=self.seller_org.id, role="ADMIN", status="ACTIVE"),
            OrganizationMember(user_id=self.outsider_user.id, organization_id=self.outsider_org.id, role="ADMIN", status="ACTIVE"),
        ])

        self.deal = Deal(
            id=uuid4(),
            buyer_organization_id=self.buyer_org.id,
            seller_organization_id=self.seller_org.id,
            status="AGREED",
            version=1,
        )
        self.session.add(self.deal)
        self.session.commit()

    def _authenticate(self, user_id: Any, org_id: Any) -> None:
        actor = ActorContext(
            user_id=user_id,
            organization_ids=frozenset({org_id}),
        )
        app.dependency_overrides[get_db] = lambda: self.session
        app.dependency_overrides[get_current_actor] = lambda: actor

    def _request(
        self, method: str, path: str, *, json: dict[str, Any] | None = None
    ) -> httpx.Response:
        async def send() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                return await client.request(method, path, json=json)

        return asyncio.run(send())

    def test_get_reminders_counterparty_isolation(self) -> None:
        repo = SqlAlchemyReminderRepository(self.session)
        # Create 1 reminder for buyer and 1 for seller
        buyer_rem = DealReminder(
            id=uuid4(),
            deal_id=self.deal.id,
            scope=ReminderScope.MILESTONE,
            reference_id=uuid4(),
            recipient_organization_id=self.buyer_org.id,
            recipient_user_id=self.buyer_user.id,
            status=ReminderStatus.SCHEDULED,
            scheduled_for=self.now,
            due_at=self.now + timedelta(hours=12),
            deduplication_key="key-buyer-1",
        )
        seller_rem = DealReminder(
            id=uuid4(),
            deal_id=self.deal.id,
            scope=ReminderScope.FULFILLMENT,
            reference_id=uuid4(),
            recipient_organization_id=self.seller_org.id,
            recipient_user_id=self.seller_user.id,
            status=ReminderStatus.SCHEDULED,
            scheduled_for=self.now,
            due_at=self.now + timedelta(hours=24),
            deduplication_key="key-seller-1",
        )
        repo.save(buyer_rem)
        repo.save(seller_rem)
        self.session.commit()

        # Buyer queries reminders
        self._authenticate(self.buyer_user.id, self.buyer_org.id)
        resp = self._request("GET", f"/deals/{self.deal.id}/reminders")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], str(buyer_rem.id))
        self.assertEqual(data[0]["scope"], "MILESTONE")
        self.assertEqual(data[0]["status"], "SCHEDULED")

        # Seller queries reminders
        self._authenticate(self.seller_user.id, self.seller_org.id)
        resp = self._request("GET", f"/deals/{self.deal.id}/reminders")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], str(seller_rem.id))
        self.assertEqual(data[0]["scope"], "FULFILLMENT")

        # Outsider queries reminders -> 404
        self._authenticate(self.outsider_user.id, self.outsider_org.id)
        resp = self._request("GET", f"/deals/{self.deal.id}/reminders")
        self.assertEqual(resp.status_code, 404)

    def test_get_reminders_counterparty_org_param_forbidden(self) -> None:
        self._authenticate(self.buyer_user.id, self.buyer_org.id)
        # Buyer tries to inspect seller's reminders via query param
        resp = self._request("GET", f"/deals/{self.deal.id}/reminders?organization_id={self.seller_org.id}")
        self.assertEqual(resp.status_code, 403)

    def test_sync_reminders_endpoint(self) -> None:
        # Commit a version with a milestone
        version = AgreementVersion(
            id=uuid4(),
            deal_id=self.deal.id,
            proposal_id=uuid4(),
            version_number=1,
            canonical_terms_json={"shipments": [{"quantity": "100.00", "unit": "MT"}]},
            terms_hash="t" * 64,
            status="COMMITTED",
            created_by=self.buyer_user.id,
            committed_at=self.now,
        )
        self.session.add(version)
        self.deal.current_agreement_version_id = version.id
        milestone = PaymentMilestone(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=version.id,
            sequence_number=1,
            payer_organization_id=self.buyer_org.id,
            amount=Decimal("1000.00"),
            currency="USD",
            trigger_type="IMMEDIATE",
            due_condition="Immediate",
            status="PENDING",
            created_at=self.now,
        )
        self.session.add(milestone)
        self.session.commit()

        self._authenticate(self.buyer_user.id, self.buyer_org.id)
        resp = self._request("POST", f"/deals/{self.deal.id}/reminders/sync")
        self.assertEqual(resp.status_code, 200)
        items = resp.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["scope"], "MILESTONE")
        self.assertEqual(items[0]["recipient_organization_id"], str(self.buyer_org.id))

    def test_suppress_reminder_endpoint(self) -> None:
        repo = SqlAlchemyReminderRepository(self.session)
        buyer_rem = DealReminder(
            id=uuid4(),
            deal_id=self.deal.id,
            scope=ReminderScope.MILESTONE,
            reference_id=uuid4(),
            recipient_organization_id=self.buyer_org.id,
            recipient_user_id=self.buyer_user.id,
            status=ReminderStatus.SCHEDULED,
            scheduled_for=self.now,
            due_at=self.now + timedelta(hours=12),
            deduplication_key="key-buyer-suppress",
        )
        repo.save(buyer_rem)
        self.session.commit()

        # Seller cannot suppress buyer's reminder
        self._authenticate(self.seller_user.id, self.seller_org.id)
        resp = self._request("POST", f"/deals/{self.deal.id}/reminders/{buyer_rem.id}/suppress")
        self.assertEqual(resp.status_code, 403)

        # Buyer suppresses their own reminder
        self._authenticate(self.buyer_user.id, self.buyer_org.id)
        resp = self._request("POST", f"/deals/{self.deal.id}/reminders/{buyer_rem.id}/suppress")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUPPRESSED")
        self.assertEqual(data["suppression_reason"], "RESOLVED")

    def test_dispatch_reminders_endpoint(self) -> None:
        from syncally.infrastructure.models.deal_cases import DealCaseModel

        case_id = uuid4()
        case = DealCaseModel(
            id=case_id,
            deal_id=self.deal.id,
            agreement_version_id=uuid4(),
            agreement_terms_hash="c" * 64,
            case_type="DISPUTE",
            reason="Damaged cargo on delivery",
            requested_by_user_id=self.seller_user.id,
            requested_by_organization_id=self.seller_org.id,
            status="OPEN",
            created_at=self.now,
        )
        self.session.add(case)
        self.session.flush()

        repo = SqlAlchemyReminderRepository(self.session)
        due_time = self.now - timedelta(minutes=5)
        buyer_rem = DealReminder(
            id=uuid4(),
            deal_id=self.deal.id,
            scope=ReminderScope.CASE,
            reference_id=case_id,
            recipient_organization_id=self.buyer_org.id,
            recipient_user_id=self.buyer_user.id,
            status=ReminderStatus.SCHEDULED,
            scheduled_for=due_time - timedelta(hours=1),
            due_at=due_time,
            deduplication_key="key-dispatch-1",
        )
        repo.save(buyer_rem)
        self.session.commit()

        # Also add a reminder for another deal
        deal2 = Deal(
            id=uuid4(),
            buyer_organization_id=self.buyer_org.id,
            seller_organization_id=self.seller_org.id,
            status="AGREED",
            version=1,
        )
        self.session.add(deal2)
        other_rem = DealReminder(
            id=uuid4(),
            deal_id=deal2.id,
            scope=ReminderScope.CASE,
            reference_id=case_id,
            recipient_organization_id=self.buyer_org.id,
            recipient_user_id=self.buyer_user.id,
            status=ReminderStatus.SCHEDULED,
            scheduled_for=due_time - timedelta(hours=1),
            due_at=due_time,
            deduplication_key="key-dispatch-other",
        )
        repo.save(other_rem)
        self.session.commit()

        self._authenticate(self.buyer_user.id, self.buyer_org.id)
        resp = self._request("POST", f"/deals/{self.deal.id}/reminders/dispatch")
        self.assertEqual(resp.status_code, 200)
        dispatched = resp.json()
        self.assertEqual(len(dispatched), 1)
        self.assertEqual(dispatched[0]["id"], str(buyer_rem.id))
        self.assertEqual(dispatched[0]["status"], "DELIVERED")

        # other_rem remains SCHEDULED
        other_fresh = repo.get(other_rem.id)
        self.assertIsNotNone(other_fresh)
        self.assertEqual(other_fresh.status, ReminderStatus.SCHEDULED)
