"""HTTP contract tests for the development-only sandbox endpoints."""

from __future__ import annotations

import asyncio
import hashlib
import unittest
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import patch
from uuid import UUID

import httpx
import jwt
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.auth import _encode_access_token
from syncally.api.main import app
from syncally.application.passwords import verify_password
from syncally.cli.demo_fixture import DEMO_DEAL_ID
from syncally.cli.seed_demo import DEMO_IDENTITIES, seed_demo_data
from syncally.config import settings
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import (
    AgreementVersion,
    Approval,
    AuditEvent,
    Base,
    Constraint,
    Conversation,
    Deal,
    DemoFixture,
    Message,
    NegotiationSession,
    Obligation,
    Organization,
    OutboxEvent,
    PaymentIntent,
    PaymentMilestone,
    Proposal,
    RefreshToken,
    User,
    WebhookEvent,
)

_BUYER_EMAIL = DEMO_IDENTITIES[0].email
_SELLER_EMAIL = DEMO_IDENTITIES[1].email
_BUYER_PASSWORD = "buyer-pass-123456"
_SELLER_PASSWORD = "seller-pass-123456"
_TEST_JWT_SECRET = "test-secret-at-least-32-bytes-long-for-jwt-signing"


class DevRoutesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        event.listen(
            self.engine,
            "connect",
            lambda dbapi_connection, _record: dbapi_connection.execute("PRAGMA foreign_keys=ON"),
        )
        Base.metadata.create_all(self.engine)
        with self.engine.connect() as connection:
            self.assertEqual(connection.exec_driver_sql("PRAGMA foreign_keys").scalar(), 1)
        self.db = Session(self.engine, expire_on_commit=False)
        self.env_patch = patch.object(settings, "app_env", "test")
        self.secret_patch = patch.object(settings, "jwt_secret", _TEST_JWT_SECRET)
        self.env_patch.start()
        self.secret_patch.start()
        seed_demo_data(self.db, (_BUYER_PASSWORD, _SELLER_PASSWORD))
        self.buyer_user_id = self._user(_BUYER_EMAIL).id
        self.seller_user_id = self._user(_SELLER_EMAIL).id
        app.dependency_overrides.clear()
        app.dependency_overrides[get_db] = lambda: self.db

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.env_patch.stop()
        self.secret_patch.stop()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        authenticated: bool = True,
        user_id: UUID | None = None,
    ) -> httpx.Response:
        headers = None
        if authenticated:
            headers = {
                "Authorization": f"Bearer {_encode_access_token(user_id or self.buyer_user_id)}"
            }

        async def send() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                return await client.request(method, path, json=json, headers=headers)

        return asyncio.run(send())

    def _user(self, email: str) -> User:
        user = self.db.scalar(select(User).where(User.email == email))
        assert user is not None
        return user

    def test_dev_endpoints_require_an_authenticated_demo_admin(self) -> None:
        deal = self._create_minimal_deal()

        unauthenticated_switch = self._request(
            "POST",
            "/dev/switch-role",
            json={"target_role": "SELLER"},
            authenticated=False,
        )
        unauthenticated_reset = self._request("POST", "/dev/reset-demo", authenticated=False)

        self.assertEqual(unauthenticated_switch.status_code, 401)
        self.assertEqual(unauthenticated_reset.status_code, 401)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Deal)), 2)

        self.assertIsNotNone(self.db.get(Deal, deal.id))

        outsider = User(
            email="outsider@example.test",
            display_name="Outsider",
            password_hash="unused-test-hash",
            status="ACTIVE",
        )
        self.db.add(outsider)
        self.db.commit()
        forbidden = self._request(
            "POST",
            "/dev/switch-role",
            json={"target_role": "SELLER"},
            user_id=outsider.id,
        )

        self.assertEqual(forbidden.status_code, 403, forbidden.text)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Deal)), 2)

    def test_payment_simulation_is_dev_protected_and_never_accepts_client_authority(self) -> None:
        path = f"/dev/payments/{DEMO_DEAL_ID}/simulate-reconciliation"
        payload = {"idempotency_key": "offline", "expected_version": 0, "outcome": "PAID", "paid_amount": "10"}
        self.assertEqual(self._request("POST", path, json=payload, authenticated=False).status_code, 401)
        with patch.object(settings, "app_env", "production"):
            self.assertEqual(self._request("POST", path, json=payload).status_code, 403)
        self.assertEqual(self._request("POST", path, json={**payload, "actor_user_id": str(self.seller_user_id)}).status_code, 422)
        self.assertEqual(self._request("POST", path, json=payload).status_code, 404)

    def _organization(self, legal_name: str) -> Organization:
        organization = self.db.scalar(
            select(Organization).where(Organization.legal_name == legal_name)
        )
        assert organization is not None
        return organization

    def _create_minimal_deal(self) -> Deal:
        buyer_org = self._organization("Demo Buyer Co")
        seller_org = self._organization("Demo Seller Co")
        deal = Deal(
            buyer_organization_id=buyer_org.id,
            seller_organization_id=seller_org.id,
            status="DRAFT",
            version=0,
        )
        self.db.add(deal)
        self.db.commit()
        return deal

    def _create_external_organization(self, legal_name: str) -> Organization:
        organization = Organization(
            legal_name=legal_name,
            country_code="GB",
            status="ACTIVE",
        )
        self.db.add(organization)
        self.db.commit()
        return organization

    def _create_deal(self, buyer_organization_id: Any, seller_organization_id: Any) -> Deal:
        deal = Deal(
            buyer_organization_id=buyer_organization_id,
            seller_organization_id=seller_organization_id,
        )
        self.db.add(deal)
        self.db.commit()
        return deal

    def _add_deal_activity(self, deal: Deal, participant_organization_id: Any) -> None:
        author = self._user(_BUYER_EMAIL)
        conversation = Conversation(
            deal_id=deal.id,
            participant_organization_id=participant_organization_id,
        )
        self.db.add(conversation)
        self.db.flush()
        self.db.add(
            Message(
                conversation_id=conversation.id,
                author_user_id=author.id,
                body="Activity outside the demo scope",
                visibility="SHAREABLE",
                source_type="USER",
            )
        )
        self.db.add_all(
            [
                OutboxEvent(
                    aggregate_type="deal",
                    aggregate_id=deal.id,
                    event_type="deal.preserved_test",
                    payload={"deal_id": str(deal.id)},
                ),
                AuditEvent(
                    aggregate_type="deal",
                    aggregate_id=deal.id,
                    event_type="deal.preserved_test",
                    actor_type="USER",
                    actor_id=str(author.id),
                    occurred_at=datetime.now(UTC),
                    payload={"deal_id": str(deal.id)},
                ),
            ]
        )
        self.db.commit()

    def _create_full_demo_graph(self) -> Deal:
        buyer = self._user(_BUYER_EMAIL)
        buyer_org = self._organization("Demo Buyer Co")
        seller_org = self._organization("Demo Seller Co")

        deal = self.db.get(Deal, DEMO_DEAL_ID)
        assert deal is not None
        conversation = self.db.scalar(
            select(Conversation).where(
                Conversation.deal_id == deal.id,
                Conversation.participant_organization_id == buyer_org.id,
            )
        )
        assert conversation is not None

        message = Message(
            conversation_id=conversation.id,
            author_user_id=buyer.id,
            body="Demo message",
            visibility="SHAREABLE",
            source_type="USER",
        )
        self.db.add(message)
        self.db.flush()

        constraint = Constraint(
            deal_id=deal.id,
            owner_organization_id=buyer_org.id,
            field="unit_price",
            typed_value="25.00",
            kind="HARD_LIMIT",
            status="EXTRACTED",
            visibility="PRIVATE",
            source_message_id=message.id,
            version=0,
        )
        negotiation = self.db.scalar(
            select(NegotiationSession).where(NegotiationSession.deal_id == deal.id)
        )
        assert negotiation is not None
        self.db.add(constraint)
        self.db.flush()

        proposal = Proposal(
            deal_id=deal.id,
            negotiation_session_id=negotiation.id,
            proposal_number=2,
            author_organization_id=buyer_org.id,
            terms_json={"unit_price": "25.00"},
            terms_hash="a" * 64,
            status="DRAFT",
        )
        self.db.add(proposal)
        self.db.flush()

        counter_proposal = Proposal(
            deal_id=deal.id,
            negotiation_session_id=negotiation.id,
            proposal_number=3,
            author_organization_id=seller_org.id,
            based_on_proposal_id=proposal.id,
            terms_json={"unit_price": "24.00"},
            terms_hash="c" * 64,
            status="DRAFT",
        )
        self.db.add(counter_proposal)
        self.db.flush()

        for pending in self.db.scalars(select(AgreementVersion).where(
            AgreementVersion.deal_id == deal.id, AgreementVersion.status == "PENDING_APPROVAL"
        )):
            pending.status = "SUPERSEDED"
        self.db.flush()
        agreement = AgreementVersion(
            deal_id=deal.id,
            proposal_id=proposal.id,
            version_number=2,
            canonical_terms_json={"unit_price": "25.00"},
            terms_hash="b" * 64,
            status="PENDING_APPROVAL",
            created_by=buyer.id,
        )
        self.db.add(agreement)
        self.db.flush()

        approval = Approval(
            deal_id=deal.id,
            agreement_version_id=agreement.id,
            organization_id=buyer_org.id,
            user_id=buyer.id,
            decision="APPROVED",
            terms_hash="b" * 64,
        )
        obligation = Obligation(
            deal_id=deal.id,
            agreement_version_id=agreement.id,
            obligation_type="PAYMENT",
            owner_organization_id=buyer_org.id,
            counterparty_organization_id=seller_org.id,
            status="PENDING",
        )
        self.db.add_all([approval, obligation])
        self.db.flush()

        milestone = PaymentMilestone(
            deal_id=deal.id,
            agreement_version_id=agreement.id,
            obligation_id=obligation.id,
            sequence_number=1,
            payer_organization_id=buyer_org.id,
            amount=Decimal("25.00"),
            currency="USD",
            trigger_type="ON_COMMIT",
            due_condition="On agreement commit",
            status="PENDING",
        )
        self.db.add(milestone)
        self.db.flush()

        intent = PaymentIntent(
            deal_id=deal.id,
            agreement_version_id=agreement.id,
            payment_milestone_id=milestone.id,
            seller_organization_id=seller_org.id,
            payer_organization_id=buyer_org.id,
            authorized_by=buyer.id,
            amount=Decimal("25.00"),
            currency="USD",
            status="AUTHORIZED",
            provider="PAYPAL",
            idempotency_key="dev-reset-test-intent",
        )
        self.db.add(intent)
        self.db.flush()

        self.db.add(
            WebhookEvent(
                provider="PAYPAL",
                provider_event_id="dev-reset-test-event",
                event_type="INVOICE.PAID",
                raw_payload={"id": "dev-reset-test-event"},
                payment_intent_id=intent.id,
                processed=False,
            )
        )
        self.db.add_all(
            [
                OutboxEvent(
                    aggregate_type="deal",
                    aggregate_id=deal.id,
                    event_type="deal.reset_test",
                    payload={"deal_id": str(deal.id)},
                ),
                AuditEvent(
                    aggregate_type="deal",
                    aggregate_id=deal.id,
                    event_type="deal.reset_test",
                    actor_type="USER",
                    actor_id=str(buyer.id),
                    occurred_at=datetime.now(UTC),
                    payload={"deal_id": str(deal.id)},
                ),
            ]
        )
        self.db.commit()
        return deal

    def test_switch_role_returns_valid_tokens_for_buyer_and_seller(self) -> None:
        for role, email in (("BUYER", _BUYER_EMAIL), ("SELLER", _SELLER_EMAIL)):
            with self.subTest(role=role):
                response = self._request("POST", "/dev/switch-role", json={"target_role": role})

                self.assertEqual(response.status_code, 200, response.text)
                body = response.json()
                self.assertEqual(set(body), {"access_token", "refresh_token", "token_type"})
                self.assertEqual(body["token_type"], "bearer")

                claims = jwt.decode(
                    body["access_token"],
                    _TEST_JWT_SECRET,
                    algorithms=[settings.jwt_algorithm],
                )
                self.assertEqual(claims["sub"], str(self._user(email).id))
                self.assertEqual(claims["typ"], "access")
                self.assertGreater(claims["exp"], claims["iat"])

                stored = self.db.scalar(
                    select(RefreshToken).where(RefreshToken.user_id == self._user(email).id)
                )
                self.assertIsNotNone(stored)
                assert stored is not None
                self.assertEqual(
                    stored.token_hash,
                    hashlib.sha256(body["refresh_token"].encode("utf-8")).hexdigest(),
                )

    def test_switch_role_normalizes_case_and_whitespace(self) -> None:
        response = self._request("POST", "/dev/switch-role", json={"target_role": "  seller  "})

        self.assertEqual(response.status_code, 200, response.text)
        claims = jwt.decode(
            response.json()["access_token"],
            _TEST_JWT_SECRET,
            algorithms=[settings.jwt_algorithm],
        )
        self.assertEqual(claims["sub"], str(self._user(_SELLER_EMAIL).id))

    def test_switch_role_admin_uses_the_seeded_admin_identity(self) -> None:
        response = self._request("POST", "/dev/switch-role", json={"target_role": "ADMIN"})

        self.assertEqual(response.status_code, 200, response.text)
        claims = jwt.decode(
            response.json()["access_token"],
            _TEST_JWT_SECRET,
            algorithms=[settings.jwt_algorithm],
        )
        self.assertEqual(claims["sub"], str(self._user(_BUYER_EMAIL).id))

    def test_switch_role_rejects_unknown_role(self) -> None:
        for role in ("SUPERUSER", ""):
            with self.subTest(role=role):
                response = self._request("POST", "/dev/switch-role", json={"target_role": role})

                self.assertEqual(response.status_code, 422, response.text)

    def test_switch_role_returns_404_when_demo_user_is_missing(self) -> None:
        self._user(_BUYER_EMAIL).email = "renamed-buyer@example.test"
        self.db.commit()

        response = self._request(
            "POST",
            "/dev/switch-role",
            json={"target_role": "BUYER"},
            user_id=self.seller_user_id,
        )

        self.assertEqual(response.status_code, 404, response.text)

    def test_dev_endpoints_are_forbidden_outside_dev_and_test(self) -> None:
        self._create_minimal_deal()

        with patch.object(settings, "app_env", "staging"):
            switch_response = self._request(
                "POST", "/dev/switch-role", json={"target_role": "BUYER"}
            )
            reset_response = self._request("POST", "/dev/reset-demo")

        for response in (switch_response, reset_response):
            self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Deal)), 2)

    def test_dev_endpoints_are_forbidden_in_production(self) -> None:
        self._create_minimal_deal()

        with patch.object(settings, "app_env", "production"):
            switch_response = self._request(
                "POST", "/dev/switch-role", json={"target_role": "BUYER"}
            )
            reset_response = self._request("POST", "/dev/reset-demo")
            invalid_body_response = self._request(
                "POST", "/dev/switch-role", json={"target_role": "not-a-role"}
            )

        for response in (switch_response, reset_response, invalid_body_response):
            self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Deal)), 2)

    def _snapshot(self) -> dict:
        return {
            table.name: [
                tuple(row)
                for row in self.db.execute(select(table).order_by(*table.primary_key.columns))
            ]
            for table in Base.metadata.sorted_tables
        }

    def test_reset_demo_refuses_payment_history_and_retains_all_rows_and_passwords(self) -> None:
        self._create_full_demo_graph()
        for deal_status, status in (("COMMITTED", "PAID"), ("DRAFT", "PAID"), ("DRAFT", "CREATE_UNKNOWN"), ("DRAFT", "AUTHORIZED")):
            with self.subTest(deal_status=deal_status, status=status):
                intent = self.db.scalar(select(PaymentIntent))
                intent.status = status
                intent.provider_invoice_id = "synthetic-provider-invoice"
                intent.provider_create_started_at = datetime.now(UTC)
                intent.reconciled_amount = Decimal("25.00") if status == "PAID" else None
                intent.last_reconciled_at = datetime.now(UTC) if status == "PAID" else None
                self.db.get(Deal, DEMO_DEAL_ID).status = deal_status
                self.db.commit()
                original = self._snapshot()
                with patch("syncally.cli.seed_demo._delete_scoped") as deletion:
                    response = self._request("POST", "/dev/reset-demo", user_id=self.seller_user_id)
                    deletion.assert_not_called()
                self.assertEqual(response.status_code, 409, response.text)
                self.assertIn("history retained", response.json()["detail"])
                if deal_status == "DRAFT":
                    self.assertIn("payment_intents", response.json()["detail"])
                self.assertEqual(self._snapshot(), original)
                for email, password in ((_BUYER_EMAIL, _BUYER_PASSWORD), (_SELLER_EMAIL, _SELLER_PASSWORD)):
                    self.assertTrue(verify_password(password, self._user(email).password_hash))

    def test_reset_demo_refuses_processing_and_delivered_outbox_with_all_rows_retained(self) -> None:
        event = OutboxEvent(
            aggregate_type="deal",
            aggregate_id=DEMO_DEAL_ID,
            event_type="DEAL_NOTIFICATION",
            payload={"deal_id": str(DEMO_DEAL_ID), "kind": "MESSAGE_RECEIVED"},
        )
        self.db.add(event)
        for status in ("PROCESSING", "DELIVERED"):
            with self.subTest(status=status):
                event.status = status
                self.db.commit()
                original = self._snapshot()
                response = self._request("POST", "/dev/reset-demo")
                self.assertEqual(response.status_code, 409, response.text)
                self.assertEqual(self._snapshot(), original)

    def test_reset_demo_reactivates_demo_identities(self) -> None:
        seller = self._user(_SELLER_EMAIL)
        seller.status = "SUSPENDED"
        self.db.commit()

        response = self._request("POST", "/dev/reset-demo")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self._user(_SELLER_EMAIL).status, "ACTIVE")

    def test_reset_demo_refuses_to_delete_when_demo_identities_are_missing(self) -> None:
        self._create_minimal_deal()
        self._user(_BUYER_EMAIL).email = "renamed-buyer@example.test"
        self.db.commit()

        response = self._request("POST", "/dev/reset-demo", user_id=self.seller_user_id)

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Deal)), 2)

    def test_reset_demo_preserves_unrelated_organization_data(self) -> None:
        external_buyer = self._create_external_organization("External Buyer Co")
        external_seller = self._create_external_organization("External Seller Co")
        external_deal = self._create_deal(external_buyer.id, external_seller.id)
        self._add_deal_activity(external_deal, external_buyer.id)

        response = self._request("POST", "/dev/reset-demo")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            self.db.scalar(
                select(func.count()).select_from(Deal).where(Deal.id == external_deal.id)
            ),
            1,
        )
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(Conversation)
                .where(Conversation.deal_id == external_deal.id)
            ),
            1,
        )
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.aggregate_id == external_deal.id)
            ),
            1,
        )
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(OutboxEvent)
                .where(OutboxEvent.aggregate_id == external_deal.id)
            ),
            1,
        )

    def test_reset_demo_preserves_deals_with_non_demo_party(self) -> None:
        demo_buyer = self._organization("Demo Buyer Co")
        external_seller = self._create_external_organization("External Seller Co")
        mixed_deal = self._create_deal(demo_buyer.id, external_seller.id)
        self._add_deal_activity(mixed_deal, demo_buyer.id)
        self._create_minimal_deal()

        response = self._request("POST", "/dev/reset-demo")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            self.db.scalar(select(func.count()).select_from(Deal).where(Deal.id == mixed_deal.id)),
            1,
        )
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(Conversation)
                .where(Conversation.deal_id == mixed_deal.id)
            ),
            1,
        )
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Deal)), 3)

    def test_reset_demo_is_idempotent(self) -> None:
        first = self._request("POST", "/dev/reset-demo")
        second = self._request("POST", "/dev/reset-demo")

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json()["deleted"]["deals"], 1)
        self.assertEqual(second.json()["deleted"]["deals"], 1)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Deal)), 1)

    def test_reset_preserves_unmarked_same_party_deals_and_their_audit(self) -> None:
        legacy = self._create_minimal_deal()
        self._add_deal_activity(legacy, legacy.buyer_organization_id)
        original = {
            model: [tuple(row) for row in self.db.execute(select(model.__table__))]
            for model in (AuditEvent, OutboxEvent)
        }
        response = self._request("POST", "/dev/reset-demo")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNotNone(self.db.get(Deal, legacy.id))
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(Message)
                .join(Conversation)
                .where(Conversation.deal_id == legacy.id)
            ),
            1,
        )
        for model, rows in original.items():
            self.assertEqual([tuple(row) for row in self.db.execute(select(model.__table__))], rows)

    def test_reset_marker_collision_is_atomic_http_conflict(self) -> None:
        marker = self.db.get(DemoFixture, "curated-buyer-seller")
        marker.fixture_version = 2
        self.db.commit()
        with patch("syncally.cli.seed_demo._clear_fixture") as cleanup:
            response = self._request("POST", "/dev/reset-demo")
            cleanup.assert_not_called()
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIsNotNone(self.db.get(Deal, DEMO_DEAL_ID))
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Message)), 6)

    def test_missing_password_reset_never_prompts_or_deletes(self) -> None:
        self._user(_SELLER_EMAIL).password_hash = None
        self.db.commit()
        with patch(
            "syncally.cli.seed_demo.getpass.getpass",
            side_effect=AssertionError("API must never prompt"),
        ):
            response = self._request("POST", "/dev/reset-demo")
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIsNotNone(self.db.get(Deal, DEMO_DEAL_ID))
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Message)), 6)

    def test_curated_sources_are_party_private_and_draft_has_no_approvals(self) -> None:
        for user_id, own_note, other_note in (
            (self.buyer_user_id, "28.00", "22.00"),
            (self.seller_user_id, "22.00", "28.00"),
        ):
            with self.subTest(user_id=user_id):
                messages = self._request("GET", f"/deals/{DEMO_DEAL_ID}/messages", user_id=user_id)
                facts = self._request("GET", f"/deals/{DEMO_DEAL_ID}/facts", user_id=user_id)
                draft = self._request(
                    "GET", f"/deals/{DEMO_DEAL_ID}/agreements/current", user_id=user_id
                )
                self.assertEqual(messages.status_code, 200, messages.text)
                self.assertEqual(facts.status_code, 200, facts.text)
                self.assertEqual(draft.status_code, 200, draft.text)
                self.assertIn(own_note, messages.text)
                self.assertIn(own_note, facts.text)
                self.assertNotIn(other_note, messages.text)
                self.assertNotIn(other_note, facts.text)
                self.assertTrue(all(fact["status"] == "EXTRACTED" for fact in facts.json()))
                self.assertEqual(draft.json()["status"], "PENDING_APPROVAL")
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Approval)), 0)


if __name__ == "__main__":
    unittest.main()
