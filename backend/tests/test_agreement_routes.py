"""HTTP contract tests for the agreement draft, approval, and commit routes."""

import asyncio
import hashlib
import json
import unittest
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from typing import Any
from unittest.mock import patch
from uuid import uuid4
from zipfile import ZipFile

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
    Constraint,
    Conversation,
    Deal,
    Message,
    NegotiationSession,
    Obligation,
    Organization,
    OrganizationMember,
    OutboxEvent,
    PaymentIntent,
    PaymentMilestone,
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

    def _commit_current_agreement(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        self.assertEqual(self._create_draft().status_code, 201)
        self.assertEqual(self._approve(1).status_code, 200)
        self._authenticate(self._actor(self.seller_user, self.seller))
        self.assertEqual(self._approve(1).status_code, 200)
        self.assertEqual(self._commit(1).status_code, 200)

    def _add_pending_version(self, version_number: int, *, make_current: bool) -> AgreementVersion:
        if make_current:
            for pending in self.session.scalars(select(AgreementVersion).where(
                AgreementVersion.deal_id == self.deal.id, AgreementVersion.status == "PENDING_APPROVAL"
            )):
                pending.status = "SUPERSEDED"
            self.session.flush()
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

    def _trade_pack(self, version=None, *, format="zip", hash=None, organization=None, deal=None):
        version = version or self.session.scalar(select(AgreementVersion).where(AgreementVersion.version_number == 1))
        return self._request("GET", f"/deals/{deal or self.deal.id}/documents/versions/{version.version_number}/trade-pack"
            f"?agreement_version_id={version.id}&terms_hash={hash or version.terms_hash}"
            f"&organization_id={organization or self.seller.id}&format={format}")

    def test_trade_pack_historical_exact_identity_and_both_parties_deterministic(self):
        self._commit_current_agreement()
        old = self.session.scalar(select(AgreementVersion))
        old.canonical_terms_json = {**old.canonical_terms_json, "_f6_evidence": [{"private": "DO NOT EXPORT"}]}
        self.session.commit()
        self._add_pending_version(2, make_current=True)
        response = self._trade_pack(old)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["content-type"], "application/zip")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertIn("attachment; filename=", response.headers["content-disposition"])
        self.assertTrue(response.headers["content-disposition"].isascii())
        with ZipFile(BytesIO(response.content)) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(manifest["agreement_version_id"], str(old.id))
            self.assertNotIn("_f6_evidence", str(manifest))
            self.assertNotIn("Seller Co", archive.read("trade-pack.html").decode())
            self.assertEqual(hashlib.sha256(archive.read("canonical-terms.json")).hexdigest(), old.terms_hash)
            self.assertEqual(archive.read("trade-pack.html"), self._trade_pack(old, format="html").content)
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        self.assertEqual(response.content, self._trade_pack(old, organization=self.buyer.id).content)
        self.assertFalse(self.session.new)
        self.assertFalse(self.session.dirty)

    def test_trade_pack_required_identity_auth_and_conflicts(self):
        self._commit_current_agreement()
        version = self.session.scalar(select(AgreementVersion))
        base = f"/deals/{self.deal.id}/documents/versions/1/trade-pack"
        self.assertEqual(self._request("GET", base).status_code, 422)
        self.assertEqual(self._trade_pack(hash="0" * 64).status_code, 409)
        self.assertEqual(self._request("GET", base + f"?agreement_version_id={uuid4()}&terms_hash={version.terms_hash}&organization_id={self.seller.id}").status_code, 409)
        self.assertEqual(self._trade_pack(deal=uuid4()).status_code, 404)
        pending = self._add_pending_version(2, make_current=True)
        self.assertEqual(self._trade_pack(pending).status_code, 409)
        approval = self.session.scalar(select(Approval))
        approval.terms_hash = "0" * 64
        self.session.commit()
        self.assertEqual(self._trade_pack(version).status_code, 409)
        self._authenticate(self._actor(self.outsider_user, self.outsider))
        self.assertEqual(self._trade_pack(version).status_code, 404)
        app.dependency_overrides.pop(get_current_actor)
        self.assertEqual(self._trade_pack(version).status_code, 401)

    def test_trade_pack_renders_all_persisted_entries_without_demo_recommit_validation(self):
        self._commit_current_agreement()
        version = self.session.scalar(select(AgreementVersion))
        display = self.terms.to_storage_dict()
        for key in ("line_items", "shipments", "payment_terms"):
            display[key] *= 2
        display["incoterm"] = "FOB"
        display["cancellation_terms"] = 'Review <script>alert("x")</script>'
        from syncally.domain.agreements.trade_terms import TradeTerms
        terms = TradeTerms.from_canonical_json(display)
        version.canonical_terms_json = {**display, "_f6_evidence": [{"private": "NEVER EXPORT"}]}
        version.terms_hash = terms.terms_hash
        for approval in self.session.scalars(select(Approval)):
            approval.terms_hash = terms.terms_hash
        self.session.commit()
        original = deepcopy(version.canonical_terms_json)
        with patch.object(TradeTerms, "validate_for_commit", side_effect=AssertionError("Must not recommit")):
            response = self._trade_pack(version)
        self.assertEqual(response.status_code, 200, response.text)
        with ZipFile(BytesIO(response.content)) as archive:
            html = archive.read("trade-pack.html").decode()
            self.assertIn("Item 2", html)
            self.assertIn("Shipment 2", html)
            self.assertIn("Payment term 2", html)
            self.assertIn("FOB", html)
            self.assertIn("&lt;script&gt;", html)
            self.assertNotIn("<script>", html)
            self.assertEqual(archive.read("canonical-terms.json").decode(), terms.canonical_json())
        self.assertEqual(version.canonical_terms_json, original)
        self.assertEqual(version.terms_hash, terms.terms_hash)

    def test_trade_pack_rejects_cross_deal_version_and_stored_party_mismatch(self):
        self._commit_current_agreement()
        version = self.session.scalar(select(AgreementVersion))
        other = Deal(buyer_organization_id=self.buyer.id, seller_organization_id=self.seller.id)
        self.session.add(other)
        self.session.flush()
        foreign = AgreementVersion(deal_id=other.id, proposal_id=self.proposal.id, version_number=1,
            canonical_terms_json=self.terms.to_storage_dict(), terms_hash=self.terms.terms_hash,
            status="COMMITTED", created_by=self.buyer_user.id)
        self.session.add(foreign)
        self.session.commit()
        base = f"/deals/{self.deal.id}/documents/versions/1/trade-pack"
        self.assertEqual(self._request("GET", base + f"?agreement_version_id={foreign.id}&terms_hash={version.terms_hash}&organization_id={self.seller.id}").status_code, 409)
        display = deepcopy(version.canonical_terms_json)
        display["buyer_id"] = str(self.outsider.id)
        from syncally.domain.agreements.trade_terms import TradeTerms
        version.canonical_terms_json = display
        version.terms_hash = TradeTerms.from_canonical_json(display).terms_hash
        self.session.commit()
        self.assertEqual(self._trade_pack(version).status_code, 409)

    def test_trade_pack_rechecks_database_membership_org_user_and_size(self):
        self._commit_current_agreement()
        self.assertEqual(self._trade_pack(organization=self.buyer.id).status_code, 404)
        member = self.session.scalar(select(OrganizationMember).where(OrganizationMember.user_id == self.seller_user.id))
        for entity in (member, self.seller, self.seller_user):
            entity.status = "INACTIVE"
            self.session.commit()
            self.assertEqual(self._trade_pack().status_code, 404)
            entity.status = "ACTIVE"
            self.session.commit()
        with patch("syncally.application.documents.MAX_DISPLAY_JSON_BYTES", 10):
            self.assertEqual(self._trade_pack().status_code, 413)
        version = self.session.scalar(select(AgreementVersion))
        version.canonical_terms_json = {**version.canonical_terms_json, "unknown": "secret"}
        self.session.commit()
        self.assertEqual(self._trade_pack().status_code, 409)

    def test_history_exact_compare_keep_equal_hash_versions_and_own_decisions(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        first = self._add_pending_version(1, make_current=True)
        self.assertEqual(self._approve(1).status_code, 200)
        second = self._add_pending_version(2, make_current=True)
        base = f"/deals/{self.deal.id}/agreements"
        history = self._request("GET", base + "/history")
        self.assertEqual(history.status_code, 200, history.text)
        versions = history.json()["versions"]
        self.assertEqual([version["id"] for version in versions], [str(second.id), str(first.id)])
        self.assertEqual(versions[1]["status"], "SUPERSEDED")
        self.assertEqual(len(versions[1]["approvals"]), 1)
        self.assertEqual(versions[1]["approvals"][0]["agreement_version_id"], str(first.id))
        self.assertEqual(versions[0]["approvals"], [])
        exact = self._request("GET", base + "/versions/1")
        self.assertEqual(exact.json()["id"], str(first.id))
        comparison = self._request("GET", base + "/compare?before=1&after=2")
        self.assertEqual(comparison.status_code, 200, comparison.text)
        self.assertEqual(comparison.json()["changes"]["fields"], [])
        self.assertEqual(self._approve(1).status_code, 409)
        self.assertEqual(list(self.session.scalars(select(Obligation))), [])
        self.assertEqual(list(self.session.scalars(select(AuditEvent))), [])

    def test_history_reauthorizes_revoked_and_selected_party_before_exposure(self) -> None:
        self._add_pending_version(1, make_current=True)
        base = f"/deals/{self.deal.id}/agreements"
        self._authenticate(self._actor(self.outsider_user, self.outsider))
        self.assertEqual(self._request("GET", base + "/history").status_code, 404)
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        self.assertEqual(self._request("GET", base + f"/versions/1?organization_id={self.seller.id}").status_code, 404)
        member = self.session.scalar(select(OrganizationMember).where(OrganizationMember.user_id == self.buyer_user.id))
        member.status = "INACTIVE"
        self.session.commit()
        for suffix in ("/history", "/versions/1", "/compare?before=1&after=1"):
            response = self._request("GET", base + suffix)
            self.assertEqual(response.status_code, 404, response.text)
            self.assertNotIn(self.terms.terms_hash, response.text)

    def test_exact_history_scopes_cross_deal_numbers_and_all_stored_statuses(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        old = self._add_pending_version(1, make_current=True)
        old.status = "VOIDED"
        self.deal.current_agreement_version_id = None
        self.session.commit()
        base = f"/deals/{self.deal.id}/agreements"
        response = self._request("GET", base + "/versions/1")
        self.assertEqual(response.json()["status"], "VOIDED")
        self.assertFalse(response.json()["is_current"])
        self.assertEqual(self._get_current().status_code, 404)
        other = Deal(buyer_organization_id=self.buyer.id, seller_organization_id=self.seller.id)
        self.session.add(other)
        self.session.flush()
        negotiation = NegotiationSession(deal_id=other.id, max_rounds=5)
        self.session.add(negotiation)
        self.session.flush()
        proposal = Proposal(deal_id=other.id, negotiation_session_id=negotiation.id, proposal_number=1,
            author_organization_id=self.buyer.id, terms_json=self.terms.to_storage_dict(), terms_hash=self.terms.terms_hash)
        self.session.add(proposal)
        self.session.flush()
        self.session.add(AgreementVersion(deal_id=other.id, proposal_id=proposal.id, version_number=9,
            canonical_terms_json=self.terms.to_storage_dict(), terms_hash=self.terms.terms_hash,
            status="COMMITTED", created_by=self.buyer_user.id, committed_at=datetime.now(UTC)))
        self.session.commit()
        for suffix in ("/versions/9", "/compare?before=1&after=9"):
            response = self._request("GET", base + suffix)
            self.assertEqual(response.status_code, 404, response.text)
            self.assertNotIn(self.terms.terms_hash, response.text)
        self.assertEqual(self._request("GET", base + "/history").json()["versions"][0]["id"], str(old.id))

    def test_exact_evidence_validates_snapshot_before_tracing_and_redacts_private_refs(self) -> None:
        conversation = Conversation(
            deal_id=self.deal.id, participant_organization_id=self.buyer.id
        )
        self.session.add(conversation)
        self.session.flush()
        message = Message(
            conversation_id=conversation.id, author_user_id=self.buyer_user.id,
            body="Review-only public quote", visibility="SHAREABLE", source_type="USER",
        )
        self.session.add(message)
        self.session.flush()
        fact = Constraint(
            deal_id=self.deal.id, owner_organization_id=self.buyer.id,
            field="quantity", typed_value="1", kind="INFORMATIONAL", status="CONFIRMED",
            visibility="SHAREABLE", version=1, source_message_id=message.id,
            source_span=message.body, confirmed_by=self.buyer_user.id,
            confirmed_at=datetime.now(UTC),
        )
        self.session.add(fact)
        self.session.commit()
        version = self._add_pending_version(1, make_current=True)
        valid = {
            "metadata_schema_version": 1, "fact_id": str(fact.id), "version": 1,
            "owner_organization_id": str(self.buyer.id), "visibility": "SHAREABLE",
            "source_message_id": str(message.id), "source_span": message.body,
            "source_body_hash": hashlib.sha256(message.body.encode()).hexdigest(),
            "source_visibility": "SHAREABLE",
        }
        malformed = [
            {**valid, "version": value} for value in (True, False, "1", 1.0, 0, -1, None)
        ]
        malformed.extend(
            {**valid, "metadata_schema_version": value} for value in (999, True, "1", None)
        )
        malformed.extend(
            {**valid, "source_span": value} for value in (True, [], None, "", " ", "x" * 8_001)
        )
        for key in ("fact_id", "owner_organization_id", "source_message_id"):
            malformed.extend({**valid, key: value} for value in (True, 1, [], "invalid"))
        for key in ("visibility", "source_visibility"):
            malformed.extend({**valid, key: value} for value in (True, [], "PUBLIC"))
        malformed.extend(
            {**valid, "source_body_hash": value} for value in (True, [], "x" * 64, "a" * 63)
        )
        malformed.extend({key: value for key, value in valid.items() if key != missing}
                         for missing in valid)
        malformed.extend([None, True, "invalid", []])
        malformed.append({**valid, "version": True, "metadata_schema_version": 999})
        malformed.append({**valid, "visibility": "PRIVATE", "version": True})
        malformed.append({**valid, "source_visibility": "PRIVATE", "version": True})
        unavailable = {"trace_enabled": False, "state": "UNAVAILABLE", "grounding": "UNMAPPED"}
        path = f"/deals/{self.deal.id}/agreements/versions/1"
        for index, ref in enumerate(malformed):
            with self.subTest(index=index, ref=ref):
                snapshot = {**self.terms.to_storage_dict(), "_f6_evidence": [ref]}
                version.canonical_terms_json = deepcopy(snapshot)
                self.session.commit()
                for user, organization in ((self.buyer_user, self.buyer), (self.seller_user, self.seller)):
                    self._authenticate(self._actor(user, organization))
                    response = self._request("GET", path + f"?organization_id={organization.id}")
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json()["evidence"], [unavailable])
                    self.assertEqual(response.json()["terms_hash"], self.terms.terms_hash)
                self.session.refresh(version)
                self.assertEqual(version.canonical_terms_json, snapshot)

        version.canonical_terms_json = {**self.terms.to_storage_dict(), "_f6_evidence": [valid]}
        self.session.commit()
        for user, organization in ((self.buyer_user, self.buyer), (self.seller_user, self.seller)):
            self._authenticate(self._actor(user, organization))
            response = self._request("GET", path + f"?organization_id={organization.id}")
            self.assertEqual(response.status_code, 200, response.text)
            evidence = response.json()["evidence"][0]
            self.assertTrue(evidence["trace_enabled"])
            self.assertEqual(evidence["state"], "AVAILABLE")
            self.assertEqual(evidence["source_span"], message.body)
            self.assertEqual(evidence["source_message_id"], str(message.id))
            self.assertEqual(evidence["version"], 1)
        for private_ref in ({**valid, "visibility": "PRIVATE"},
                            {**valid, "source_visibility": "PRIVATE"}):
            version.canonical_terms_json = {**self.terms.to_storage_dict(), "_f6_evidence": [private_ref]}
            self.session.commit()
            response = self._request("GET", path + f"?organization_id={self.seller.id}")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["evidence"], [unavailable])

    def test_legacy_proposal_id_still_creates_draft_without_human_rounds(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))

        response = self._create_draft()

        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["terms_hash"], self.terms.terms_hash)
        self.assertEqual(response.json()["version_number"], 1)
        self.assertEqual(response.json()["status"], "PENDING_APPROVAL")
        self.assertEqual(self.session.scalar(select(Proposal)), self.proposal)
        self.assertEqual(list(self.session.scalars(select(Approval))), [])

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

    def _reviewed_terms(self, **overrides: object) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "description": "Desk",
            "quantity": "10",
            "unit": "pieces",
            "unit_price": "25.00",
            "currency": "USD",
            "delivery_destination": "Toronto",
            "delivery_date": "2030-01-01",
            "organization_id": str(self.buyer.id),
            **overrides,
        }

    def _human_submit(self) -> httpx.Response:
        from uuid import uuid4
        session = self.session.scalar(select(NegotiationSession))
        session.current_proposal_id = self.proposal.id
        self.session.commit()
        return self._request("POST", f"/deals/{self.deal.id}/negotiation/submit", json={
            "command_id": str(uuid4()), "expected_deal_revision": self.deal.version,
            "organization_id": str(self.buyer.id),
            "base": {"id": str(self.proposal.id), "terms_hash": self.proposal.terms_hash, "status": self.proposal.status},
            "terms": self._reviewed_terms(),
        })

    def test_human_proposal_http_journey_is_separate_from_bilateral_approval(self) -> None:
        from uuid import uuid4
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        submitted = self._human_submit()
        self.assertEqual(submitted.status_code, 200, submitted.text)
        self.assertEqual(self._get_current().status_code, 404)
        self.assertEqual(self._request("POST", f"/deals/{self.deal.id}/agreements", json={"proposal_id": submitted.json()["proposal_id"]}).status_code, 409)
        self.assertEqual(self._request("POST", f"/deals/{self.deal.id}/agreements/from-reviewed-terms", json=self._reviewed_terms()).status_code, 409)
        read = self._request("GET", f"/deals/{self.deal.id}/negotiation?organization_id={self.buyer.id}")
        self.assertEqual(read.status_code, 200, read.text)
        self.assertEqual(read.json()["eligible_actions"], ["supersede"])
        base = {field: read.json()["latest"][field] for field in ("id", "terms_hash", "status")}
        body = {"command_id": str(uuid4()), "expected_deal_revision": read.json()["deal_revision"], "base": base,
                "organization_id": str(self.seller.id)}
        self._authenticate(self._actor(self.seller_user, self.seller))
        accepted = self._request("POST", f"/deals/{self.deal.id}/negotiation/accept", json=body)
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertEqual(self._get_current().json()["approvals"], [])
        self.assertEqual(self._request("POST", f"/deals/{self.deal.id}/negotiation/accept", json=body).json(), accepted.json())
        current = self._get_current().json()
        self.assertEqual(self._request("POST", f"/deals/{self.deal.id}/agreements/1/approve", json={"terms_hash": current["terms_hash"]}).status_code, 200)
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        self.assertEqual(self._request("POST", f"/deals/{self.deal.id}/agreements/1/approve", json={"terms_hash": current["terms_hash"]}).status_code, 200)
        self.assertEqual(self._commit(1, terms_hash=current["terms_hash"]).status_code, 200)

    def test_negotiation_http_fresh_access_and_dual_selector(self) -> None:
        self._authenticate(self._actor(self.outsider_user, self.outsider))
        self.assertEqual(self._request("GET", f"/deals/{self.deal.id}/negotiation").status_code, 404)
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        self.session.add(OrganizationMember(user_id=self.buyer_user.id, organization_id=self.seller.id, status="ACTIVE"))
        self.session.commit()
        self.assertEqual(self._request("GET", f"/deals/{self.deal.id}/negotiation").status_code, 422)
        self.assertEqual(self._request("GET", f"/deals/{self.deal.id}/negotiation?organization_id={self.buyer.id}").status_code, 200)
        self.buyer_user.status = "INACTIVE"
        self.session.commit()
        self.assertEqual(self._request("GET", f"/deals/{self.deal.id}/negotiation?organization_id={self.buyer.id}").status_code, 404)

    def test_negotiation_http_rejects_naive_deadline_and_unknown_authority_fields(self) -> None:
        from uuid import uuid4
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        body = {"command_id": str(uuid4()), "expected_deal_revision": 0, "base": None,
                "organization_id": str(self.buyer.id), "terms": self._reviewed_terms(), "expires_at": "2030-01-01T00:00:00"}
        response = self._request("POST", f"/deals/{self.deal.id}/negotiation/submit", json=body)
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("2030-01-01T00:00:00", response.text)
        body.pop("expires_at")
        body["status"] = "COMMITTED"
        self.assertEqual(self._request("POST", f"/deals/{self.deal.id}/negotiation/submit", json=body).status_code, 422)

    def test_reviewed_terms_accept_an_omitted_payment_timing_during_rollout(self) -> None:
        # Older clients predate the field and may hit a new instance before the
        # new frontend is served. Backend-first rollout must keep them working.
        self._authenticate(self._actor(self.buyer_user, self.buyer))

        response = self._request(
            "POST",
            f"/deals/{self.deal.id}/agreements/from-reviewed-terms",
            json=self._reviewed_terms(),
        )

        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["payment_trigger"], "seller_invoice")
        self.assertEqual(
            response.json()["payment_due_condition"], "when seller invoices"
        )

    def test_reviewed_terms_reject_an_unsupported_payment_timing(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))

        for unsupported in ("net_30", ""):
            response = self._request(
                "POST",
                f"/deals/{self.deal.id}/agreements/from-reviewed-terms",
                json=self._reviewed_terms(payment_trigger=unsupported),
            )
            self.assertEqual(response.status_code, 422, response.text)
            self.assertEqual(
                self.session.scalars(select(AgreementVersion)).all(),
                [],
                "an unsupported payment timing must not be saved",
            )

        confirmed = self._request(
            "POST",
            f"/deals/{self.deal.id}/agreements/from-reviewed-terms",
            json=self._reviewed_terms(payment_trigger="  SELLER_INVOICE "),
        )
        self.assertEqual(confirmed.status_code, 201, confirmed.text)
        self.assertEqual(confirmed.json()["payment_trigger"], "seller_invoice")
        self.assertEqual(confirmed.json()["payment_due_condition"], "when seller invoices")

    def test_reviewed_terms_retry_returns_the_saved_agreement(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        payload = self._reviewed_terms(payment_trigger="seller_invoice")

        first = self._request(
            "POST",
            f"/deals/{self.deal.id}/agreements/from-reviewed-terms",
            json=payload,
        )
        self.assertEqual(first.status_code, 201, first.text)

        # A lost response makes the proposer submit the identical terms again.
        retry = self._request(
            "POST",
            f"/deals/{self.deal.id}/agreements/from-reviewed-terms",
            json=payload,
        )

        self.assertEqual(retry.status_code, 201, retry.text)
        self.assertEqual(retry.json()["version_number"], first.json()["version_number"])
        self.assertEqual(retry.json()["terms_hash"], first.json()["terms_hash"])

        self.session.expire_all()
        self.assertEqual(
            len(self.session.scalars(select(AgreementVersion)).all()),
            1,
            "a retry must not create a second agreement version",
        )
        self.assertEqual(
            len(self.session.scalars(select(Proposal)).all()),
            2,
            "a retry must not create a second proposal",
        )

    def test_reviewed_terms_reject_different_terms_while_one_is_pending(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        unchanged = self._request(
            "POST",
            f"/deals/{self.deal.id}/agreements/from-reviewed-terms",
            json=self._reviewed_terms(),
        )
        self.assertEqual(unchanged.status_code, 201, unchanged.text)

        changed = self._request(
            "POST",
            f"/deals/{self.deal.id}/agreements/from-reviewed-terms",
            json=self._reviewed_terms(description="Chair"),
        )

        self.assertEqual(changed.status_code, 409, changed.text)
        self.session.expire_all()
        self.assertEqual(len(self.session.scalars(select(AgreementVersion)).all()), 1)

    def test_reviewed_terms_do_not_echo_an_unsupported_payment_trigger(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        submitted = "sk_live_TRIGGER_LEAK_PROBE_123"

        response = self._request(
            "POST",
            f"/deals/{self.deal.id}/agreements/from-reviewed-terms",
            json=self._reviewed_terms(payment_trigger=submitted),
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertNotIn(submitted, response.text)
        self.assertIn("seller_invoice", response.text)

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
            self.session.scalar(
                select(OutboxEvent).where(OutboxEvent.event_type == "AGREEMENT_COMMITTED")
            ).event_type,
            "AGREEMENT_COMMITTED",
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

    def test_payment_status_is_backend_owned_and_omits_invoice_secrets(self) -> None:
        self._commit_current_agreement()
        milestone = self.session.scalar(
            select(PaymentMilestone).where(PaymentMilestone.deal_id == self.deal.id)
        )
        self.session.add(
            PaymentIntent(
                deal_id=self.deal.id,
                agreement_version_id=self.deal.current_agreement_version_id,
                payment_milestone_id=milestone.id,
                seller_organization_id=self.seller.id,
                payer_organization_id=self.buyer.id,
                authorized_by=self.seller_user.id,
                amount=milestone.amount,
                currency=milestone.currency,
                status="PARTIALLY_PAID",
                provider_invoice_id="private-invoice-token",
                idempotency_key="private-idempotency-key",
                reconciled_amount=Decimal("40"),
                failure_detail="private provider response",
            )
        )
        self.session.commit()
        self._authenticate(self._actor(self.buyer_user, self.buyer))

        response = self._request("GET", f"/deals/{self.deal.id}/payments")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()[0]["status"], "PARTIALLY_PAID")
        self.assertEqual(response.json()[0]["reconciled_amount"], "40")
        self.assertNotIn("provider_invoice_id", response.json()[0])
        self.assertNotIn("private-", response.text)
        self.assertNotIn("provider response", response.text)

    def test_payment_status_is_empty_until_a_committed_agreement_exists(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        self.assertEqual(self._create_draft().status_code, 201)

        response = self._request("GET", f"/deals/{self.deal.id}/payments")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), [])

    def test_payment_status_returns_only_the_latest_attempt_per_milestone(self) -> None:
        self._commit_current_agreement()
        milestone = self.session.scalar(
            select(PaymentMilestone).where(PaymentMilestone.deal_id == self.deal.id)
        )
        common = {
            "deal_id": self.deal.id,
            "agreement_version_id": self.deal.current_agreement_version_id,
            "payment_milestone_id": milestone.id,
            "seller_organization_id": self.seller.id,
            "payer_organization_id": self.buyer.id,
            "authorized_by": self.seller_user.id,
            "amount": milestone.amount,
            "currency": milestone.currency,
        }
        self.session.add_all(
            [
                PaymentIntent(
                    **common,
                    status="FAILED",
                    idempotency_key="older-failed-attempt",
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                ),
                PaymentIntent(
                    **common,
                    status="SENT",
                    idempotency_key="latest-sent-attempt",
                    created_at=datetime(2026, 1, 2, tzinfo=UTC),
                ),
            ]
        )
        self.session.commit()
        self._authenticate(self._actor(self.buyer_user, self.buyer))

        response = self._request("GET", f"/deals/{self.deal.id}/payments")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["status"], "SENT")

    def test_commercial_document_requires_commit_and_uses_committed_terms(self) -> None:
        self._authenticate(self._actor(self.buyer_user, self.buyer))
        self.assertEqual(self._create_draft().status_code, 201)
        unavailable = self._request(
            "GET", f"/deals/{self.deal.id}/documents/commercial-draft"
        )
        self.assertEqual(unavailable.status_code, 409)

        self._approve(1)
        self._authenticate(self._actor(self.seller_user, self.seller))
        self._approve(1)
        self._commit(1)

        response = self._request(
            "GET", f"/deals/{self.deal.id}/documents/commercial-draft"
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["agreement_version_number"], 1)
        self.assertIn(self.terms.terms_hash, response.json()["content"])
        self.assertIn("DRAFT - FOR REVIEW ONLY", response.json()["content"])

    def test_payment_and_document_reads_hide_deals_from_nonparticipants(self) -> None:
        self._authenticate(self._actor(self.outsider_user, self.outsider))

        payment_response = self._request("GET", f"/deals/{self.deal.id}/payments")
        document_response = self._request(
            "GET", f"/deals/{self.deal.id}/documents/commercial-draft"
        )

        self.assertEqual(payment_response.status_code, 404)
        self.assertEqual(document_response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
