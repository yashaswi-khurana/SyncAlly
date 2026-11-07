"""HTTP contract tests for F15b Approval Routing: the organizations policy
CRUD endpoints and the approve/reject routes' routed branch.
"""

import asyncio
import json
import unittest
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from test_domain_fixes import build_terms

from syncally.api.auth import get_current_actor
from syncally.api.main import app
from syncally.application.identity import ActorContext
from syncally.domain.shared.identifiers import OrganizationId
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import (
    Base,
    Deal,
    NegotiationSession,
    Organization,
    OrganizationMember,
    Proposal,
    User,
)


class ApprovalRoutingRouteTests(unittest.TestCase):
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

    def _add_member(self, organization, *, role="MEMBER", capabilities=()):
        user = User(email=f"{uuid4()}@example.com", display_name="Approver")
        self.session.add(user)
        self.session.flush()
        self.session.add(
            OrganizationMember(
                user_id=user.id, organization_id=organization.id,
                status="ACTIVE", role=role, capabilities=list(capabilities),
            )
        )
        self.session.commit()
        return user

    def _seed(self) -> None:
        self.buyer_user = User(email="buyer@example.com", display_name="Buyer")
        self.seller_user = User(email="seller@example.com", display_name="Seller")
        self.buyer = Organization(legal_name="Buyer Co", country_code="US")
        self.seller = Organization(legal_name="Seller Co", country_code="CA")
        self.session.add_all([self.buyer_user, self.seller_user, self.buyer, self.seller])
        self.session.flush()
        self.session.add_all([
            OrganizationMember(user_id=self.buyer_user.id, organization_id=self.buyer.id, status="ACTIVE", role="ADMIN", capabilities=["AGREEMENT_APPROVAL"]),
            OrganizationMember(user_id=self.seller_user.id, organization_id=self.seller.id, status="ACTIVE", role="ADMIN", capabilities=["AGREEMENT_APPROVAL"]),
        ])
        self.deal = Deal(buyer_organization_id=self.buyer.id, seller_organization_id=self.seller.id, status="DRAFT", version=0)
        self.session.add(self.deal)
        self.session.flush()

        self.terms = build_terms(buyer_id=OrganizationId(self.buyer.id), seller_id=OrganizationId(self.seller.id))
        negotiation = NegotiationSession(deal_id=self.deal.id, max_rounds=5)
        self.session.add(negotiation)
        self.session.flush()
        self.proposal = Proposal(
            deal_id=self.deal.id, negotiation_session_id=negotiation.id, proposal_number=1,
            author_organization_id=self.buyer.id, terms_json=json.loads(self.terms.canonical_json()),
            terms_hash=self.terms.terms_hash, status="SUBMITTED",
        )
        self.session.add(self.proposal)
        self.session.commit()

    def _authenticate(self, actor: ActorContext) -> None:
        app.dependency_overrides[get_db] = lambda: self.session
        app.dependency_overrides[get_current_actor] = lambda: actor

    def _actor(self, user: User, *organizations: Organization) -> ActorContext:
        return ActorContext(user.id, frozenset(org.id for org in organizations))

    def _request(self, method: str, path: str, *, json: dict[str, Any] | None = None) -> httpx.Response:
        async def send() -> httpx.Response:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                return await client.request(method, path, json=json)

        return asyncio.run(send())

    def _create_draft(self) -> httpx.Response:
        return self._request("POST", f"/deals/{self.deal.id}/agreements", json={"proposal_id": str(self.proposal.id)})

    def _approve(self, version_number: int):
        return self._request(
            "POST", f"/deals/{self.deal.id}/agreements/{version_number}/approve",
            json={"terms_hash": self.terms.terms_hash},
        )

    def _commit(self, version_number: int):
        return self._request(
            "POST", f"/deals/{self.deal.id}/agreements/{version_number}/commit",
            json={"terms_hash": self.terms.terms_hash},
        )

    # -- Policy CRUD --

    def test_non_admin_cannot_configure_policy(self) -> None:
        member = self._add_member(self.buyer, capabilities=["AGREEMENT_APPROVAL"])
        self._authenticate(self._actor(member, self.buyer))
        response = self._request(
            "PUT", f"/organizations/{self.buyer.id}/approval-routing",
            json={"mode": "PARALLEL", "approver_user_ids": [str(member.id)]},
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_configure_read_and_remove_policy(self) -> None:
        a1 = self._add_member(self.buyer, capabilities=["AGREEMENT_APPROVAL"])
        self._authenticate(self._actor(self.buyer_user, self.buyer))

        created = self._request(
            "PUT", f"/organizations/{self.buyer.id}/approval-routing",
            json={"mode": "PARALLEL", "approver_user_ids": [str(a1.id)]},
        )
        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual(created.json()["version"], 1)

        fetched = self._request("GET", f"/organizations/{self.buyer.id}/approval-routing")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["mode"], "PARALLEL")

        removed = self._request("DELETE", f"/organizations/{self.buyer.id}/approval-routing?expected_version=1")
        self.assertEqual(removed.status_code, 204)

        gone = self._request("GET", f"/organizations/{self.buyer.id}/approval-routing")
        self.assertEqual(gone.status_code, 200)
        self.assertIsNone(gone.json())

    def test_configuring_an_ineligible_approver_is_rejected(self) -> None:
        stranger = User(email="stranger@example.com", display_name="Stranger")
        self.session.add(stranger)
        self.session.commit()
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        response = self._request(
            "PUT", f"/organizations/{self.buyer.id}/approval-routing",
            json={"mode": "PARALLEL", "approver_user_ids": [str(stranger.id)]},
        )
        self.assertEqual(response.status_code, 422)

    # -- Routed approve/reject through the agreements routes --

    def test_parallel_policy_gates_the_approve_route_until_satisfied(self) -> None:
        a1 = self._add_member(self.buyer, capabilities=["AGREEMENT_APPROVAL"])
        a2 = self._add_member(self.buyer, capabilities=["AGREEMENT_APPROVAL"])
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        put_response = self._request(
            "PUT", f"/organizations/{self.buyer.id}/approval-routing",
            json={"mode": "PARALLEL", "approver_user_ids": [str(a1.id), str(a2.id)]},
        )
        self.assertEqual(put_response.status_code, 200, put_response.text)

        self.assertEqual(self._create_draft().status_code, 201)

        self._authenticate(self._actor(a1, self.buyer))
        first = self._approve(1)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["routing"]["status"], "PENDING")

        self._authenticate(self._actor(a2, self.buyer))
        second = self._approve(1)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(second.json()["routing"]["status"], "COMPLETED")
        self.assertEqual(second.json()["decision"], "APPROVE")

        self._authenticate(self._actor(self.seller_user, self.seller))
        self.assertEqual(self._approve(1).status_code, 200)
        self.assertEqual(self._commit(1).status_code, 200)

    def test_sequential_out_of_order_approve_is_a_conflict(self) -> None:
        a1 = self._add_member(self.buyer, capabilities=["AGREEMENT_APPROVAL"])
        a2 = self._add_member(self.buyer, capabilities=["AGREEMENT_APPROVAL"])
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        self._request(
            "PUT", f"/organizations/{self.buyer.id}/approval-routing",
            json={"mode": "SEQUENTIAL", "approver_user_ids": [str(a1.id), str(a2.id)]},
        )
        self.assertEqual(self._create_draft().status_code, 201)

        self._authenticate(self._actor(a2, self.buyer))
        response = self._approve(1)
        self.assertEqual(response.status_code, 409)

    def test_counterparty_view_hides_approver_identities(self) -> None:
        a1 = self._add_member(self.buyer, capabilities=["AGREEMENT_APPROVAL"])
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        self._request(
            "PUT", f"/organizations/{self.buyer.id}/approval-routing",
            json={"mode": "PARALLEL", "approver_user_ids": [str(a1.id)]},
        )
        self.assertEqual(self._create_draft().status_code, 201)

        self._authenticate(self._actor(a1, self.buyer))
        self.assertEqual(self._approve(1).status_code, 200)

        self._authenticate(self._actor(self.seller_user, self.seller))
        current = self._request("GET", f"/deals/{self.deal.id}/agreements/current")
        self.assertEqual(current.status_code, 200)
        routing_status = current.json()["routing_status"][str(self.buyer.id)]
        self.assertEqual(routing_status["status"], "COMPLETED")
        self.assertIsNone(routing_status["slots"])

        self._authenticate(self._actor(self.buyer_user, self.buyer))
        own_view = self._request("GET", f"/deals/{self.deal.id}/agreements/current")
        own_routing_status = own_view.json()["routing_status"][str(self.buyer.id)]
        self.assertIsNotNone(own_routing_status["slots"])


if __name__ == "__main__":
    unittest.main()
