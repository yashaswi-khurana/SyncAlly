"""HTTP contract tests for the agreement draft, approval, and commit routes."""

import asyncio
import json
import unittest
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from test_domain_fixes import build_terms

from syncally.api.auth import get_current_actor
from syncally.api.main import app
from syncally.application.identity import ActorContext
from syncally.domain.agreements.agreement import AgreementStatus, ApprovalDecision
from syncally.domain.shared.identifiers import OrganizationId
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import (
    AgreementVersion,
    Approval,
    AuditEvent,
    Base,
    Deal,
    NegotiationSession,
    Obligation,
    Organization,
    OrganizationMember,
    OutboxEvent,
    Proposal,
    User,
)


class AgreementRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self._seed()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _seed(self) -> None:
        self.buyer_user = User(email="buyer@example.com", display_name="Buyer")
        self.seller_user = User(email="seller@example.com", display_name="Seller")
        self.outsider_user = User(email="outsider@example.com", display_name="Outsider")
        self.buyer = Organization(legal_name="Buyer Co", country_code="US")
        self.seller = Organization(legal_name="Seller Co", country_code="CA")
        self.outsider = Organization(legal_name="Outsider Co", country_code="GB")
        self.session.add_all(
            [
                self.buyer_user,
                self.seller_user,
                self.outsider_user,
                self.buyer,
                self.seller,
                self.outsider,
            ]
        )
        self.session.flush()
        self.session.add_all(
            [
                OrganizationMember(
                    user_id=self.buyer_user.id, organization_id=self.buyer.id, status="ACTIVE"
                ),
                OrganizationMember(
                    user_id=self.seller_user.id, organization_id=self.seller.id, status="ACTIVE"
                ),
                OrganizationMember(
                    user_id=self.outsider_user.id,
                    organization_id=self.outsider.id,
                    status="ACTIVE",
                ),
            ]
        )
        self.deal = Deal(
            buyer_organization_id=self.buyer.id,
            seller_organization_id=self.seller.id,
            status="DRAFT",
            version=0,
        )
        self.session.add(self.deal)
        self.session.flush()

        self.terms = build_terms(
            buyer_id=OrganizationId(self.buyer.id),
            seller_id=OrganizationId(self.seller.id),
        )
        negotiation = NegotiationSession(deal_id=self.deal.id, max_rounds=5)
        self.session.add(negotiation)
        self.session.flush()
        self.proposal = Proposal(
            deal_id=self.deal.id,
            negotiation_session_id=negotiation.id,
            proposal_number=1,
            author_organization_id=self.buyer.id,
            terms_json=json.loads(self.terms.canonical_json()),
            terms_hash=self.terms.terms_hash,
            status="SUBMITTED",
        )
        self.session.add(self.proposal)
        self.session.commit()

    def _authenticate(self, actor: ActorContext) -> None:
        app.dependency_overrides[get_db] = lambda: self.session
        app.dependency_overrides[get_current_actor] = lambda: actor

    def _actor(self, user: User, *organizations: Organization) -> ActorContext:
        return ActorContext(user.id, frozenset(org.id for org in organizations))

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

    def _create_draft(self) -> httpx.Response:
        return self._request(
            "POST",
            f"/deals/{self.deal.id}/agreements",
            json={"proposal_id": str(self.proposal.id)},
        )

    def _approve(self, version_number: int, *, organization_id: str | None = None):
        body: dict[str, Any] = {"terms_hash": self.terms.terms_hash}
        if organization_id is not None:
            body["organization_id"] = organization_id
        return self._request(
            "POST",
            f"/deals/{self.deal.id}/agreements/{version_number}/approve",
            json=body,
        )

    def _commit(self, version_number: int, *, terms_hash: str | None = None):
        return self._request(
            "POST",
            f"/deals/{self.deal.id}/agreements/{version_number}/commit",
            json={"terms_hash": terms_hash or self.terms.terms_hash},
        )

    def _get_current(self):
        return self._request("GET", f"/deals/{self.deal.id}/agreements/current")

    def _add_pending_version(self, version_number: int, *, make_current: bool) -> AgreementVersion:
        version = AgreementVersion(
            deal_id=self.deal.id,
            proposal_id=self.proposal.id,
            version_number=version_number,
            canonical_terms_json=self.terms.to_storage_dict(),
            terms_hash=self.terms.terms_hash,
            status=AgreementStatus.PENDING_APPROVAL.value,
            created_by=self.buyer_user.id,
            created_at=datetime.now(UTC),
        )
        self.session.add(version)
        self.session.flush()
        if make_current:
            self.deal.current_agreement_version_id = version.id
            self.deal.status = "PENDING_APPROVALS"
        self.session.commit()
        return version

    def test_create_draft_requires_authentication(self) -> None:
        app.dependency_overrides[get_db] = lambda: self.session

        response = self._create_draft()

        self.assertEqual(response.status_code, 401)

    def test_current_agreement_read_returns_exact_terms_and_approval_state(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        self.assertEqual(self._create_draft().status_code, 201)

        pending = self._get_current()

        self.assertEqual(pending.status_code, 200, pending.text)
        body = pending.json()
        self.assertEqual(body["version_number"], 1)
        self.assertEqual(body["terms_hash"], self.terms.terms_hash)
        self.assertEqual(body["status"], "PENDING_APPROVAL")
        self.assertEqual(body["terms"]["line_items"][0]["description"], "Desk")
        self.assertEqual(body["approvals"], [])

        self.assertEqual(self._approve(1).status_code, 200)
        self._authenticate(self._actor(self.seller_user, self.seller))
        self.assertEqual(self._approve(1).status_code, 200)
        self.assertEqual(self._commit(1).status_code, 200)

        committed = self._get_current()
        self.assertEqual(committed.status_code, 200, committed.text)
        self.assertEqual(committed.json()["status"], "COMMITTED")
        self.assertEqual(len(committed.json()["approvals"]), 2)

    def test_current_agreement_read_hides_missing_and_nonparticipant_deals(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        missing = self._get_current()
        self.assertEqual(missing.status_code, 404)

        self._add_pending_version(1, make_current=True)
        self._authenticate(self._actor(self.outsider_user, self.outsider))
        forbidden = self._get_current()
        self.assertEqual(forbidden.status_code, 404)

    def test_create_draft_snapshots_proposal_and_advances_deal(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))

        response = self._create_draft()

        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["status"], "PENDING_APPROVAL")
        self.assertEqual(body["version_number"], 1)
        self.assertEqual(body["terms_hash"], self.terms.terms_hash)
        self.assertEqual(body["deal_id"], str(self.deal.id))
        self.assertEqual(body["terms"]["line_items"][0]["description"], "Desk")
        self.assertIsNone(body["committed_at"])

        self.session.expire_all()
        stored_deal = self.session.get(Deal, self.deal.id)
        self.assertEqual(stored_deal.status, "PENDING_APPROVALS")
        self.assertIsNotNone(stored_deal.current_agreement_version_id)
        self.assertEqual(stored_deal.version, 2)

    def test_create_draft_rejects_client_supplied_status(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))

        response = self._request(
            "POST",
            f"/deals/{self.deal.id}/agreements",
            json={"proposal_id": str(self.proposal.id), "status": "COMMITTED"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.session.get(Deal, self.deal.id).status, "DRAFT")

    def test_create_draft_hides_the_deal_from_a_non_participant(self) -> None:
        self._authenticate(self._actor(self.outsider_user, self.outsider))

        response = self._create_draft()

        self.assertEqual(response.status_code, 404)
        self.assertNotIn(str(self.buyer.id), response.text)

    def test_create_draft_rejects_a_second_pending_version(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        self.assertEqual(self._create_draft().status_code, 201)

        response = self._create_draft()

        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.session.get(Deal, self.deal.id).status, "PENDING_APPROVALS")

    def test_approve_derives_the_organization_and_rejects_impersonation(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        self.assertEqual(self._create_draft().status_code, 201)

        impersonation = self._approve(1, organization_id=str(self.seller.id))
        self.assertEqual(impersonation.status_code, 403)

        response = self._approve(1)

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["organization_id"], str(self.buyer.id))
        self.assertEqual(body["user_id"], str(self.buyer_user.id))
        self.assertEqual(body["decision"], "APPROVE")
        self.assertEqual(body["terms_hash"], self.terms.terms_hash)

    def test_approve_requires_authentication(self) -> None:
        app.dependency_overrides[get_db] = lambda: self.session

        response = self._approve(1)

        self.assertEqual(response.status_code, 401)

    def test_approve_hides_the_deal_from_a_non_participant(self) -> None:
        self._authenticate(self._actor(self.outsider_user, self.outsider))

        response = self._approve(1)

        self.assertEqual(response.status_code, 404)

    def test_approve_rejects_a_wrong_terms_hash_as_conflict(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        self.assertEqual(self._create_draft().status_code, 201)

        response = self._request(
            "POST",
            f"/deals/{self.deal.id}/agreements/1/approve",
            json={"terms_hash": "0" * 64},
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("current", response.json()["detail"])

    def test_approve_rejects_a_stale_version_as_conflict(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        first = self._create_draft()
        self.assertEqual(first.status_code, 201)
        self._add_pending_version(2, make_current=True)

        response = self._approve(1)

        self.assertEqual(response.status_code, 409)
        self.assertIn("reload", response.json()["detail"])

    def test_repeat_approval_returns_conflict(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        self.assertEqual(self._create_draft().status_code, 201)
        self.assertEqual(self._approve(1).status_code, 200)

        response = self._approve(1)

        self.assertEqual(response.status_code, 409)

    def test_ambiguous_actor_must_choose_a_party_and_cannot_choose_another_org(self) -> None:
        self.session.add(
            OrganizationMember(
                user_id=self.buyer_user.id, organization_id=self.seller.id, status="ACTIVE"
            )
        )
        self.session.commit()
        self._authenticate(self._actor(self.buyer_user, self.buyer, self.seller))
        self.assertEqual(self._create_draft().status_code, 201)

        ambiguous = self._approve(1)
        self.assertEqual(ambiguous.status_code, 422)
        self.assertIn("organization_id", ambiguous.json()["detail"])

        chosen = self._approve(1, organization_id=str(self.seller.id))
        self.assertEqual(chosen.status_code, 200, chosen.text)
        self.assertEqual(chosen.json()["organization_id"], str(self.seller.id))

    def test_commit_requires_both_approvals_before_succeeding(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        self.assertEqual(self._create_draft().status_code, 201)
        self.assertEqual(self._approve(1).status_code, 200)

        early = self._commit(1)
        self.assertEqual(early.status_code, 409)
        self.assertEqual(self.session.get(Deal, self.deal.id).status, "PENDING_APPROVALS")

        self._authenticate(self._actor(self.seller_user, self.seller))
        self.assertEqual(self._approve(1).status_code, 200)

        response = self._commit(1)

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["status"], "COMMITTED")
        self.assertIsNotNone(body["committed_at"])

        self.session.expire_all()
        self.assertEqual(self.session.get(Deal, self.deal.id).status, "AGREED")
        obligations = self.session.scalars(
            select(Obligation).where(Obligation.deal_id == self.deal.id)
        ).all()
        self.assertEqual({o.obligation_type for o in obligations}, {"DELIVERY", "PAYMENT"})
        self.assertEqual(self.session.scalar(select(AuditEvent)).event_type, "AGREEMENT_COMMITTED")
        self.assertEqual(
            self.session.scalar(select(OutboxEvent)).event_type, "AGREEMENT_COMMITTED"
        )

    def test_commit_is_idempotent_for_the_same_version_and_hash(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        self.assertEqual(self._create_draft().status_code, 201)
        self.assertEqual(self._approve(1).status_code, 200)
        self._authenticate(self._actor(self.seller_user, self.seller))
        self.assertEqual(self._approve(1).status_code, 200)
        self.assertEqual(self._commit(1).status_code, 200)

        retry = self._commit(1)

        self.assertEqual(retry.status_code, 200, retry.text)
        self.assertEqual(retry.json()["status"], "COMMITTED")
        self.assertEqual(
            len(
                self.session.scalars(
                    select(Obligation).where(Obligation.deal_id == self.deal.id)
                ).all()
            ),
            2,
        )

    def test_commit_rejects_a_wrong_hash_as_conflict(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        self.assertEqual(self._create_draft().status_code, 201)
        self.assertEqual(self._approve(1).status_code, 200)
        self._authenticate(self._actor(self.seller_user, self.seller))
        self.assertEqual(self._approve(1).status_code, 200)

        response = self._commit(1, terms_hash="0" * 64)

        self.assertEqual(response.status_code, 409)

    def test_commit_rejects_a_client_supplied_status(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))

        response = self._request(
            "POST",
            f"/deals/{self.deal.id}/agreements/1/commit",
            json={"terms_hash": self.terms.terms_hash, "status": "COMMITTED"},
        )

        self.assertEqual(response.status_code, 422)

    def test_commit_hides_the_deal_from_a_non_participant(self) -> None:
        self._authenticate(self._actor(self.outsider_user, self.outsider))

        response = self._commit(1)

        self.assertEqual(response.status_code, 404)

    def test_commit_rejects_a_stale_pending_version_as_conflict(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        first = self._create_draft()
        self.assertEqual(first.status_code, 201)
        first_version_id = self.session.scalar(
            select(AgreementVersion.id).where(AgreementVersion.version_number == 1)
        )
        for organization_id in (self.buyer.id, self.seller.id):
            self.session.add(
                Approval(
                    deal_id=self.deal.id,
                    agreement_version_id=first_version_id,
                    organization_id=organization_id,
                    user_id=self.buyer_user.id,
                    decision=ApprovalDecision.APPROVE.value,
                    terms_hash=self.terms.terms_hash,
                    created_at=datetime.now(UTC),
                )
            )
        self._add_pending_version(2, make_current=True)

        response = self._commit(1)

        self.assertEqual(response.status_code, 409)
        self.assertIn("reload", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
