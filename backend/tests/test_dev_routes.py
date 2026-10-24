"""HTTP contract tests for the development-only sandbox endpoints."""

from __future__ import annotations

import asyncio
import hashlib
import unittest
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import patch

import httpx
import jwt
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.main import app
from syncally.application.passwords import verify_password
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
    Message,
    NegotiationSession,
    Obligation,
    Organization,
    OrganizationMember,
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
            lambda dbapi_connection, _record: dbapi_connection.execute(
                "PRAGMA foreign_keys=ON"
            ),
        )
        Base.metadata.create_all(self.engine)
        with self.engine.connect() as connection:
            self.assertEqual(
                connection.exec_driver_sql("PRAGMA foreign_keys").scalar(), 1
            )
        self.db = Session(self.engine, expire_on_commit=False)
        self.env_patch = patch.object(settings, "app_env", "test")
        self.secret_patch = patch.object(settings, "jwt_secret", _TEST_JWT_SECRET)
        self.env_patch.start()
        self.secret_patch.start()
        seed_demo_data(self.db, (_BUYER_PASSWORD, _SELLER_PASSWORD))
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
        self, method: str, path: str, *, json: dict[str, Any] | None = None
    ) -> httpx.Response:
        async def send() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                return await client.request(method, path, json=json)

        return asyncio.run(send())

    def _user(self, email: str) -> User:
        user = self.db.scalar(select(User).where(User.email == email))
        assert user is not None
        return user

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

        deal = Deal(
            buyer_organization_id=buyer_org.id,
            seller_organization_id=seller_org.id,
        )
        self.db.add(deal)
        self.db.flush()

        conversation = Conversation(
            deal_id=deal.id,
            participant_organization_id=buyer_org.id,
        )
        self.db.add(conversation)
        self.db.flush()

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
        negotiation = NegotiationSession(deal_id=deal.id, max_rounds=3)
        self.db.add_all([constraint, negotiation])
        self.db.flush()

        proposal = Proposal(
            deal_id=deal.id,
            negotiation_session_id=negotiation.id,
            proposal_number=1,
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
            proposal_number=2,
            author_organization_id=seller_org.id,
            based_on_proposal_id=proposal.id,
            terms_json={"unit_price": "24.00"},
            terms_hash="c" * 64,
            status="DRAFT",
        )
        self.db.add(counter_proposal)
        self.db.flush()

        agreement = AgreementVersion(
            deal_id=deal.id,
            proposal_id=proposal.id,
            version_number=1,
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
                response = self._request(
                    "POST", "/dev/switch-role", json={"target_role": role}
                )

                self.assertEqual(response.status_code, 200, response.text)
                body = response.json()
                self.assertEqual(
                    set(body), {"access_token", "refresh_token", "token_type"}
                )
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
                    select(RefreshToken).where(
                        RefreshToken.user_id == self._user(email).id
                    )
                )
                self.assertIsNotNone(stored)
                assert stored is not None
                self.assertEqual(
                    stored.token_hash,
                    hashlib.sha256(body["refresh_token"].encode("utf-8")).hexdigest(),
                )

    def test_switch_role_normalizes_case_and_whitespace(self) -> None:
        response = self._request(
            "POST", "/dev/switch-role", json={"target_role": "  seller  "}
        )

        self.assertEqual(response.status_code, 200, response.text)
        claims = jwt.decode(
            response.json()["access_token"],
            _TEST_JWT_SECRET,
            algorithms=[settings.jwt_algorithm],
        )
        self.assertEqual(claims["sub"], str(self._user(_SELLER_EMAIL).id))

    def test_switch_role_admin_uses_the_seeded_admin_identity(self) -> None:
        response = self._request(
            "POST", "/dev/switch-role", json={"target_role": "ADMIN"}
        )

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
                response = self._request(
                    "POST", "/dev/switch-role", json={"target_role": role}
                )

                self.assertEqual(response.status_code, 422, response.text)

    def test_switch_role_returns_404_when_demo_user_is_missing(self) -> None:
        self.db.delete(self._user(_BUYER_EMAIL))
        self.db.commit()

        response = self._request(
            "POST", "/dev/switch-role", json={"target_role": "BUYER"}
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
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Deal)), 1)

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
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Deal)), 1)

    def test_reset_demo_clears_business_data_and_retains_demo_identities(self) -> None:
        self._create_full_demo_graph()
        original_hashes = {
            identity.email: self._user(identity.email).password_hash
            for identity in DEMO_IDENTITIES
        }

        response = self._request("POST", "/dev/reset-demo")

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(
            body["message"],
            "Demo deal data cleared; demo identities and organizations restored.",
        )
        self.assertEqual(
            body["deleted"],
            {
                "deals": 1,
                "conversations": 1,
                "messages": 1,
                "constraints": 1,
                "negotiation_sessions": 1,
                "proposals": 2,
                "agreement_versions": 1,
                "approvals": 1,
                "obligations": 1,
                "payment_milestones": 1,
                "payment_intents": 1,
                "webhook_events": 1,
                "outbox_events": 1,
                "audit_events": 1,
            },
        )

        for model in (
            WebhookEvent,
            PaymentIntent,
            PaymentMilestone,
            Obligation,
            Approval,
            AgreementVersion,
            Proposal,
            NegotiationSession,
            Constraint,
            Message,
            Conversation,
            OutboxEvent,
            AuditEvent,
            Deal,
        ):
            self.assertEqual(
                self.db.scalar(select(func.count()).select_from(model)),
                0,
                model.__name__,
            )

        for identity, password in (
            (DEMO_IDENTITIES[0], _BUYER_PASSWORD),
            (DEMO_IDENTITIES[1], _SELLER_PASSWORD),
        ):
            user = self._user(identity.email)
            self.assertEqual(user.password_hash, original_hashes[identity.email])
            self.assertIsNotNone(user.password_hash)
            assert user.password_hash is not None
            self.assertTrue(verify_password(password, user.password_hash))

        self.assertEqual(
            self.db.scalar(select(func.count()).select_from(Organization)), 2
        )
        self.assertEqual(
            self.db.scalar(select(func.count()).select_from(OrganizationMember)), 2
        )

    def test_reset_demo_reactivates_demo_identities(self) -> None:
        seller = self._user(_SELLER_EMAIL)
        seller.status = "SUSPENDED"
        self.db.commit()

        response = self._request("POST", "/dev/reset-demo")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self._user(_SELLER_EMAIL).status, "ACTIVE")

    def test_reset_demo_refuses_to_delete_when_demo_identities_are_missing(self) -> None:
        self._create_minimal_deal()
        self.db.delete(self._user(_BUYER_EMAIL))
        self.db.commit()

        response = self._request("POST", "/dev/reset-demo")

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Deal)), 1)

    def test_reset_demo_preserves_unrelated_organization_data(self) -> None:
        external_buyer = self._create_external_organization("External Buyer Co")
        external_seller = self._create_external_organization("External Seller Co")
        external_deal = self._create_deal(external_buyer.id, external_seller.id)
        self._add_deal_activity(external_deal, external_buyer.id)
        self._create_full_demo_graph()

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
            self.db.scalar(
                select(func.count()).select_from(Deal).where(Deal.id == mixed_deal.id)
            ),
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
        self.assertEqual(
            self.db.scalar(select(func.count()).select_from(Deal)), 1
        )

    def test_reset_demo_is_idempotent(self) -> None:
        self._create_full_demo_graph()

        first = self._request("POST", "/dev/reset-demo")
        second = self._request("POST", "/dev/reset-demo")

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json()["deleted"]["deals"], 1)
        self.assertTrue(all(count == 0 for count in second.json()["deleted"].values()))


if __name__ == "__main__":
    unittest.main()
