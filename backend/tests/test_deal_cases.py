"""Comprehensive unit and API tests for Deal Cases (Step 08 F8 Cancel Disputes)."""

import importlib.util
import unittest
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from syncally.api.auth import get_current_actor
from syncally.api.main import app
from syncally.application.deal_cases import assess_deal_case_blockers
from syncally.application.identity import ActorContext
from syncally.domain.deals.deal import Deal as DomainDeal
from syncally.domain.deals.deal import DealStatus
from syncally.domain.shared.errors import InvalidTransition
from syncally.domain.shared.identifiers import AgreementVersionId, DealId, OrganizationId
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import (
    AgreementVersion,
    AuditEvent,
    Base,
    Deal,
    FulfillmentEvent,
    Obligation,
    Organization,
    OrganizationMember,
    OutboxEvent,
    PaymentMilestone,
    User,
)


class DealCasesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.db: Session = self.SessionLocal()

        # Seed default test actors
        self.buyer_org = Organization(
            id=uuid4(), legal_name="Buyer Corp", country_code="US", status="ACTIVE"
        )
        self.seller_org = Organization(
            id=uuid4(), legal_name="Seller Corp", country_code="US", status="ACTIVE"
        )
        self.unrelated_org = Organization(
            id=uuid4(), legal_name="Other Corp", country_code="US", status="ACTIVE"
        )
        self.buyer_user = User(id=uuid4(), email="buyer@corp.com", display_name="Buyer User", status="ACTIVE")
        self.seller_user = User(id=uuid4(), email="seller@corp.com", display_name="Seller User", status="ACTIVE")
        self.other_user = User(id=uuid4(), email="other@corp.com", display_name="Other User", status="ACTIVE")

        self.db.add_all([
            self.buyer_org,
            self.seller_org,
            self.unrelated_org,
            self.buyer_user,
            self.seller_user,
            self.other_user,
        ])
        self.db.flush()

        self.db.add_all([
            OrganizationMember(
                organization_id=self.buyer_org.id,
                user_id=self.buyer_user.id,
                role="ADMIN",
                status="ACTIVE",
            ),
            OrganizationMember(
                organization_id=self.seller_org.id,
                user_id=self.seller_user.id,
                role="ADMIN",
                status="ACTIVE",
            ),
            OrganizationMember(
                organization_id=self.unrelated_org.id,
                user_id=self.other_user.id,
                role="ADMIN",
                status="ACTIVE",
            ),
        ])
        self.db.flush()

        # Seed committed deal, negotiation, proposal and agreement version
        deal_id = uuid4()
        self.deal = Deal(
            id=deal_id,
            buyer_organization_id=self.buyer_org.id,
            seller_organization_id=self.seller_org.id,
            status="EXECUTING",
            version=1,
        )
        self.db.add(self.deal)
        self.db.flush()

        from syncally.infrastructure.models import NegotiationSession, Proposal
        self.session = NegotiationSession(
            id=uuid4(),
            deal_id=deal_id,
            max_rounds=5,
            round_count=1,
        )
        self.terms_hash = "a" * 64
        self.proposal = Proposal(
            id=uuid4(),
            deal_id=deal_id,
            negotiation_session_id=self.session.id,
            proposal_number=1,
            author_organization_id=self.buyer_org.id,
            terms_json={"description": "Test Terms"},
            terms_hash=self.terms_hash,
        )
        self.db.add_all([self.session, self.proposal])
        self.db.flush()

        self.agreement_version = AgreementVersion(
            id=uuid4(),
            deal_id=deal_id,
            proposal_id=self.proposal.id,
            version_number=1,
            canonical_terms_json={"description": "Test Terms"},
            terms_hash=self.terms_hash,
            status="COMMITTED",
            created_by=self.buyer_user.id,
        )
        self.deal.current_agreement_version_id = self.agreement_version.id
        self.db.add(self.agreement_version)
        self.db.commit()

        # Setup test client dependency overrides
        self.original_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = lambda: self.db
        self.buyer_actor = ActorContext(
            user_id=self.buyer_user.id,
            organization_ids=frozenset({self.buyer_org.id}),
        )
        self.seller_actor = ActorContext(
            user_id=self.seller_user.id,
            organization_ids=frozenset({self.seller_org.id}),
        )
        self.other_actor = ActorContext(
            user_id=self.other_user.id,
            organization_ids=frozenset({self.unrelated_org.id}),
        )

    def tearDown(self) -> None:
        app.dependency_overrides = self.original_overrides
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_domain_deal_cancellation_and_dispute_transitions(self) -> None:
        now = datetime.now(UTC)
        deal = DomainDeal(
            id=DealId(uuid4()),
            buyer_organization_id=OrganizationId(self.buyer_org.id),
            seller_organization_id=OrganizationId(self.seller_org.id),
            created_at=now,
            status=DealStatus.DRAFT,
        )
        # Pre-commit cancel works
        deal.cancel()
        self.assertEqual(deal.status, DealStatus.CANCELLED)

        # Committed deal cannot call pre-commit cancel
        executing_deal = DomainDeal(
            id=DealId(uuid4()),
            buyer_organization_id=OrganizationId(self.buyer_org.id),
            seller_organization_id=OrganizationId(self.seller_org.id),
            created_at=now,
            status=DealStatus.EXECUTING,
            current_agreement_version_id=AgreementVersionId(uuid4()),
        )
        with self.assertRaises(InvalidTransition):
            executing_deal.cancel()

        # Mark disputed and resolve
        executing_deal.mark_disputed()
        self.assertEqual(executing_deal.status, DealStatus.DISPUTED)
        executing_deal.resolve_dispute(has_active_disputes=False)
        self.assertEqual(executing_deal.status, DealStatus.EXECUTING)

        # Mutual cancellation requires bilateral consent and no blockers
        with self.assertRaises(InvalidTransition):
            executing_deal.cancel_committed(bilateral_consent=False, blockers=[])
        with self.assertRaises(InvalidTransition):
            executing_deal.cancel_committed(bilateral_consent=True, blockers=["Paid milestone blocker"])
        executing_deal.cancel_committed(bilateral_consent=True, blockers=[])
        self.assertEqual(executing_deal.status, DealStatus.CANCELLED)

    def test_raise_case_dispute_and_mark_deal_disputed(self) -> None:
        app.dependency_overrides[get_current_actor] = lambda: self.buyer_actor
        with TestClient(app) as client:
            res = client.post(
                f"/deals/{self.deal.id}/cases",
                json={
                    "case_type": "DISPUTE",
                    "reason": "Specification discrepancy in batch A",
                    "agreement_version_id": str(self.agreement_version.id),
                    "agreement_terms_hash": self.terms_hash,
                    "evidence_visibility": "MUTUAL_VISIBLE",
                    "evidence_notes": "Initial batch lab report attached",
                },
            )
            self.assertEqual(res.status_code, 201, res.text)
            data = res.json()
            self.assertEqual(data["case_type"], "DISPUTE")
            self.assertEqual(data["status"], "OPEN")
            self.assertEqual(len(data["evidence_items"]), 1)
            self.assertEqual(data["evidence_items"][0]["notes"], "Initial batch lab report attached")

            # Check deal is now DISPUTED
            self.db.refresh(self.deal)
            self.assertEqual(self.deal.status, "DISPUTED")

            # Check atomic outbox and audit events
            outbox = self.db.scalars(
                select(OutboxEvent).where(
                    OutboxEvent.aggregate_id == self.deal.id,
                    OutboxEvent.event_type == "deal.case.raised",
                )
            ).all()
            self.assertEqual(len(outbox), 1)

            audit = self.db.scalars(
                select(AuditEvent).where(
                    AuditEvent.aggregate_type == "deal_case",
                    AuditEvent.event_type == "DEAL_CASE_RAISED",
                )
            ).all()
            self.assertEqual(len(audit), 1)

    def test_raise_case_cancellation_does_not_cancel_deal(self) -> None:
        app.dependency_overrides[get_current_actor] = lambda: self.buyer_actor
        with TestClient(app) as client:
            res = client.post(
                f"/deals/{self.deal.id}/cases",
                json={
                    "case_type": "CANCELLATION",
                    "reason": "Mutual project restructuring requested",
                    "agreement_version_id": str(self.agreement_version.id),
                    "agreement_terms_hash": self.terms_hash,
                    "evidence_visibility": "MUTUAL_VISIBLE",
                },
            )
            self.assertEqual(res.status_code, 201, res.text)
            # Case is OPEN, but deal remains EXECUTING
            self.db.refresh(self.deal)
            self.assertEqual(self.deal.status, "EXECUTING")

    def test_raise_case_stale_hash_rejected_409(self) -> None:
        app.dependency_overrides[get_current_actor] = lambda: self.buyer_actor
        with TestClient(app) as client:
            res = client.post(
                f"/deals/{self.deal.id}/cases",
                json={
                    "case_type": "DISPUTE",
                    "reason": "Test stale",
                    "agreement_version_id": str(self.agreement_version.id),
                    "agreement_terms_hash": "b" * 64,  # Mismatched hash
                },
            )
            self.assertEqual(res.status_code, 409, res.text)

    def test_forged_tenant_rejected_403(self) -> None:
        app.dependency_overrides[get_current_actor] = lambda: self.other_actor
        with TestClient(app) as client:
            # Unrelated actor attempting to raise case on deal
            res = client.post(
                f"/deals/{self.deal.id}/cases",
                json={
                    "case_type": "DISPUTE",
                    "reason": "Intruder",
                    "agreement_version_id": str(self.agreement_version.id),
                    "agreement_terms_hash": self.terms_hash,
                },
            )
            self.assertEqual(res.status_code, 403, res.text)

    def test_bilateral_consent_cancels_deal_when_no_blockers(self) -> None:
        app.dependency_overrides[get_current_actor] = lambda: self.buyer_actor
        with TestClient(app) as client:
            create_res = client.post(
                f"/deals/{self.deal.id}/cases",
                json={
                    "case_type": "CANCELLATION",
                    "reason": "Clean mutual agreement to cancel",
                    "agreement_version_id": str(self.agreement_version.id),
                    "agreement_terms_hash": self.terms_hash,
                },
            )
            self.assertEqual(create_res.status_code, 201)
            case_id = create_res.json()["id"]

        # Counterparty (seller) consents
        app.dependency_overrides[get_current_actor] = lambda: self.seller_actor
        with TestClient(app) as client:
            resp_res = client.post(
                f"/deals/{self.deal.id}/cases/{case_id}/respond",
                json={
                    "decision": "CONSENT",
                    "rationale": "Counterparty agrees to cancel",
                },
            )
            self.assertEqual(resp_res.status_code, 200, resp_res.text)
            self.assertEqual(resp_res.json()["status"], "RESOLVED")

            # Deal is now CANCELLED
            self.db.refresh(self.deal)
            self.assertEqual(self.deal.status, "CANCELLED")

    def test_initiator_cannot_self_consent_403(self) -> None:
        app.dependency_overrides[get_current_actor] = lambda: self.buyer_actor
        with TestClient(app) as client:
            create_res = client.post(
                f"/deals/{self.deal.id}/cases",
                json={
                    "case_type": "CANCELLATION",
                    "reason": "Testing self consent",
                    "agreement_version_id": str(self.agreement_version.id),
                    "agreement_terms_hash": self.terms_hash,
                },
            )
            case_id = create_res.json()["id"]

            # Buyer tries to self-consent
            resp_res = client.post(
                f"/deals/{self.deal.id}/cases/{case_id}/respond",
                json={
                    "decision": "CONSENT",
                    "rationale": "Self approving my own cancellation",
                },
            )
            self.assertEqual(resp_res.status_code, 403, resp_res.text)

    def test_initiator_can_withdraw_case_and_restore_disputed_deal(self) -> None:
        app.dependency_overrides[get_current_actor] = lambda: self.buyer_actor
        with TestClient(app) as client:
            create_res = client.post(
                f"/deals/{self.deal.id}/cases",
                json={
                    "case_type": "DISPUTE",
                    "reason": "Temporary misunderstanding",
                    "agreement_version_id": str(self.agreement_version.id),
                    "agreement_terms_hash": self.terms_hash,
                },
            )
            case_id = create_res.json()["id"]
            self.db.refresh(self.deal)
            self.assertEqual(self.deal.status, "DISPUTED")

            # Buyer withdraws case
            withdraw_res = client.post(
                f"/deals/{self.deal.id}/cases/{case_id}/respond",
                json={
                    "decision": "WITHDRAW",
                    "rationale": "Clarified terms, withdrawing dispute",
                },
            )
            self.assertEqual(withdraw_res.status_code, 200, withdraw_res.text)
            self.assertEqual(withdraw_res.json()["status"], "WITHDRAWN")

            # Deal status restored to EXECUTING
            self.db.refresh(self.deal)
            self.assertEqual(self.deal.status, "EXECUTING")

    def test_operational_impact_blockers_for_paid_milestone_and_fulfilled_shipment(self) -> None:
        # Add a paid milestone and a shipped obligation
        milestone = PaymentMilestone(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=self.agreement_version.id,
            payer_organization_id=self.buyer_org.id,
            sequence_number=1,
            amount=Decimal("15000.00"),
            currency="USD",
            trigger_type="IMMEDIATE",
            due_condition="On signing",
            status="PAID",
        )
        obligation = Obligation(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=self.agreement_version.id,
            obligation_type="SHIPMENT",
            owner_organization_id=self.seller_org.id,
            counterparty_organization_id=self.buyer_org.id,
            status="SHIPPED",
            source_terms_reference="shipments[0]",
        )
        fulfillment = FulfillmentEvent(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=self.agreement_version.id,
            terms_hash=self.terms_hash,
            obligation_id=obligation.id,
            actor_organization_id=self.seller_org.id,
            actor_user_id=self.seller_user.id,
            event_type="SHIPPED",
            quantity="50",
            unit="units",
            idempotency_key="shipped-1",
            request_hash="h" * 64,
            version=1,
        )
        self.db.add_all([milestone, obligation, fulfillment])
        self.db.commit()

        # Blocker assessment detects both
        blockers = assess_deal_case_blockers(self.db, self.deal.id, self.agreement_version.id)
        self.assertEqual(len(blockers), 2)
        self.assertTrue(any("PAID" in b for b in blockers))
        self.assertTrue(any("fulfilled quantity" in b for b in blockers))

        # Raising case captures blockers
        app.dependency_overrides[get_current_actor] = lambda: self.buyer_actor
        with TestClient(app) as client:
            create_res = client.post(
                f"/deals/{self.deal.id}/cases",
                json={
                    "case_type": "CANCELLATION",
                    "reason": "Attempting cancellation with paid milestone and shipped goods",
                    "agreement_version_id": str(self.agreement_version.id),
                    "agreement_terms_hash": self.terms_hash,
                },
            )
            self.assertEqual(create_res.status_code, 201)
            case_data = create_res.json()
            case_id = case_data["id"]
            self.assertEqual(len(case_data["operational_impact_blockers"]), 2)

        # Counterparty consents, but automated closure is blocked
        app.dependency_overrides[get_current_actor] = lambda: self.seller_actor
        with TestClient(app) as client:
            resp_res = client.post(
                f"/deals/{self.deal.id}/cases/{case_id}/respond",
                json={
                    "decision": "CONSENT",
                    "rationale": "I consent to cancel",
                },
            )
            self.assertEqual(resp_res.status_code, 200)
            resp_data = resp_res.json()
            # Status moves to UNDER_REVIEW, NOT RESOLVED
            self.assertEqual(resp_data["status"], "UNDER_REVIEW")
            self.assertIn("Automated closure blocked", resp_data["resolution"])

            # Deal remains EXECUTING (not cancelled)
            self.db.refresh(self.deal)
            self.assertEqual(self.deal.status, "EXECUTING")

    def test_evidence_visibility_tenant_filtering(self) -> None:
        # Buyer raises case
        app.dependency_overrides[get_current_actor] = lambda: self.buyer_actor
        with TestClient(app) as client:
            create_res = client.post(
                f"/deals/{self.deal.id}/cases",
                json={
                    "case_type": "DISPUTE",
                    "reason": "Evidence visibility test",
                    "agreement_version_id": str(self.agreement_version.id),
                    "agreement_terms_hash": self.terms_hash,
                },
            )
            case_id = create_res.json()["id"]

            # Buyer adds counterparty-restricted evidence
            ev_res1 = client.post(
                f"/deals/{self.deal.id}/cases/{case_id}/evidence",
                json={
                    "notes": "Internal attorney notes (buyer only)",
                    "visibility": "COUNTERPARTY_RESTRICTED",
                },
            )
            self.assertEqual(ev_res1.status_code, 201)

            # Buyer adds mutual visible evidence
            ev_res2 = client.post(
                f"/deals/{self.deal.id}/cases/{case_id}/evidence",
                json={
                    "notes": "Shared inspection certificate",
                    "visibility": "MUTUAL_VISIBLE",
                },
            )
            self.assertEqual(ev_res2.status_code, 201)

            # Buyer lists cases: sees both evidence items
            buyer_list = client.get(f"/deals/{self.deal.id}/cases").json()
            self.assertEqual(len(buyer_list[0]["evidence_items"]), 2)

        # Seller lists cases: sees only the mutual item
        app.dependency_overrides[get_current_actor] = lambda: self.seller_actor
        with TestClient(app) as client:
            seller_list = client.get(f"/deals/{self.deal.id}/cases").json()
            self.assertEqual(len(seller_list[0]["evidence_items"]), 1)
            self.assertEqual(
                seller_list[0]["evidence_items"][0]["notes"], "Shared inspection certificate"
            )

    def test_api_v1_alias_routes_work_identically(self) -> None:
        app.dependency_overrides[get_current_actor] = lambda: self.buyer_actor
        with TestClient(app) as client:
            res = client.post(
                f"/api/v1/deals/{self.deal.id}/cases",
                json={
                    "case_type": "DISPUTE",
                    "reason": "Testing /api/v1 prefix alias",
                    "agreement_version_id": str(self.agreement_version.id),
                    "agreement_terms_hash": self.terms_hash,
                },
            )
            self.assertEqual(res.status_code, 201, res.text)
            case_id = res.json()["id"]

            list_res = client.get(f"/api/v1/deals/{self.deal.id}/cases")
            self.assertEqual(list_res.status_code, 200)
            self.assertTrue(any(c["id"] == case_id for c in list_res.json()))

    def test_alembic_migration_0025_and_downgrade_block(self) -> None:
        path = (
            Path(__file__).resolve().parents[1]
            / "alembic"
            / "versions"
            / "0025_cancel_disputes.py"
        )
        spec = importlib.util.spec_from_file_location("migration_0025", path)
        migration = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(migration)

        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as connection:
            # Create minimal prerequisite tables
            connection.execute(text("CREATE TABLE deals (id TEXT PRIMARY KEY)"))
            connection.execute(text("CREATE TABLE agreement_versions (id TEXT PRIMARY KEY)"))
            connection.execute(text("CREATE TABLE users (id TEXT PRIMARY KEY)"))
            connection.execute(text("CREATE TABLE organizations (id TEXT PRIMARY KEY)"))

            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()

            # Verify tables exist
            connection.execute(
                text(
                    "INSERT INTO deal_cases (id, deal_id, agreement_version_id, agreement_terms_hash, case_type, reason, obligation_references, requested_by_user_id, requested_by_organization_id, operational_impact_blockers) "
                    "VALUES ('case1', 'd1', 'av1', 'hash1', 'DISPUTE', 'test', '[]', 'u1', 'o1', '[]')"
                )
            )

            # Downgrade blocked while history exists
            with self.assertRaises(RuntimeError):
                migration.downgrade()

            # Remove history and downgrade cleanly
            connection.execute(text("DELETE FROM deal_cases"))
            migration.downgrade()
            # Verify deal_cases is dropped
            table_count = connection.execute(
                text("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='deal_cases'")
            ).scalar_one()
            self.assertEqual(table_count, 0)
        engine.dispose()
