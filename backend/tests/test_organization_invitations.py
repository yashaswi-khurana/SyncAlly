import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

import jwt
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.auth import get_current_actor
from syncally.api.main import app
from syncally.api.organizations import (
    AcceptInvitationRequest,
    CreateCounterpartyInvitationRequest,
    CreateInvitationRequest,
    _decode_invitation_token,
    accept_invitation,
    create_counterparty_invitation,
    create_organization_invitation,
    get_db,
    get_optional_actor,
)
from syncally.application.conversations import AddMessageCommand, add_message
from syncally.application.identity import ActorContext
from syncally.config import Settings, settings
from syncally.domain.conversations import Visibility
from syncally.infrastructure.database import create_database_engine
from syncally.infrastructure.models import (
    AuditEvent,
    Base,
    Conversation,
    CounterpartyOnboarding,
    Deal,
    Message,
    NegotiationSession,
    Organization,
    OrganizationMember,
    OutboxEvent,
    RefreshToken,
    User,
)
from syncally.infrastructure.repositories.communications import (
    CommunicationScopeError,
    SqlAlchemyCommunicationRepository,
)


class OrganizationInvitationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self._saved_secret = settings.jwt_secret
        if not settings.jwt_secret:
            settings.jwt_secret = "test-jwt-secret-with-minimum-length-32-chars-ok"

    def tearDown(self) -> None:
        settings.jwt_secret = self._saved_secret
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _user(self, email: str) -> User:
        user = User(
            email=email,
            display_name=email.split("@")[0],
            password_hash="provisioned-password-hash",
            status="ACTIVE",
        )
        self.db.add(user)
        self.db.commit()
        return user

    def _organization(self, admin: User) -> Organization:
        organization = Organization(legal_name="Acme Corp", country_code="US")
        self.db.add(organization)
        self.db.flush()
        self.db.add(
            OrganizationMember(
                organization_id=organization.id,
                user_id=admin.id,
                role="ADMIN",
                status="ACTIVE",
            )
        )
        self.db.commit()
        return organization

    def _deal(self, buyer_org: Organization, seller_org: Organization) -> Deal:
        deal = Deal(
            buyer_organization_id=buyer_org.id,
            seller_organization_id=seller_org.id,
            status="DRAFT",
            version=1,
        )
        self.db.add(deal)
        self.db.commit()
        return deal

    def _placeholder_organization(self, legal_name: str = "Pending Seller") -> Organization:
        """An unclaimed shell organization: no members have signed up for it yet."""
        organization = Organization(legal_name=legal_name, country_code="US")
        self.db.add(organization)
        self.db.commit()
        return organization

    def _counterparty_accept_payload(self, token: str) -> AcceptInvitationRequest:
        return AcceptInvitationRequest(
            token=token,
            email="kenji@tokyo-trade.jp",
            password="SecurePassword123!",
            display_name="Kenji Sato",
            organization_legal_name="Tokyo Exporters Ltd",
            country_code="JP",
        )

    def _invitation_for_deal(self, admin: User, org: Organization, deal: Deal) -> str:
        invitation = create_organization_invitation(
            organization_id=org.id,
            payload=CreateInvitationRequest(deal_id=deal.id),
            actor=ActorContext(user_id=admin.id, organization_ids=frozenset({org.id})),
            db=self.db,
        )
        return invitation["token"]

    def test_routes_are_registered_in_app(self) -> None:
        paths = app.openapi()["paths"]
        self.assertIn("/organizations/{organization_id}/invitations", paths)
        self.assertIn("post", paths["/organizations/{organization_id}/invitations"])
        self.assertIn("/invitations/accept", paths)
        self.assertIn("post", paths["/invitations/accept"])
        self.assertIn("post", paths["/deals/counterparty-invitations"])

    def _pending_invitation(self) -> tuple[User, Organization, dict]:
        admin = self._user("buyer@example.com")
        buyer = self._organization(admin)
        result = create_counterparty_invitation(
            CreateCounterpartyInvitationRequest(buyer_organization_id=buyer.id,
                                                recipient_email=" Kenji@Tokyo-Trade.jp ",
                                                legal_name="Tokyo Exporters", country_code="JP"),
            ActorContext(admin.id, frozenset({buyer.id})), self.db,
        )
        return admin, buyer, result

    def test_pending_public_flow_private_shell_then_own_organization(self) -> None:
        admin, buyer, invitation = self._pending_invitation()
        deal = self.db.get(Deal, UUID(invitation["deal_id"]))
        shell_id = deal.seller_organization_id
        self.assertEqual(self.db.get(Organization, shell_id).status, "INACTIVE")
        self.assertEqual(self.db.scalar(select(func.count(OutboxEvent.id))), 1)
        original_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_actor] = lambda: ActorContext(admin.id, frozenset({buyer.id}))
        app.dependency_overrides[get_optional_actor] = lambda: None
        try:
            with TestClient(app) as client:
                for suffix in ("", "?q=Tokyo", "?limit=1&offset=0"):
                    self.assertNotIn(str(shell_id), str(client.get(f"/organizations/directory{suffix}").json()))
                self.assertEqual(client.get(f"/organizations/{shell_id}").status_code, 404)
                self.assertEqual(client.post("/deals", json={"buyer_organization_id": str(buyer.id), "seller_organization_id": str(shell_id)}).status_code, 404)
                self.assertEqual(client.post(f"/organizations/{shell_id}/members", json={"email": admin.email}).status_code, 404)
                self.assertTrue(client.get(f"/deals/{deal.id}").json()["pending_counterparty"])
                self.assertNotIn("recipient_email", client.get(f"/deals/{deal.id}").text)
                before = [self.db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables]
                for visibility in ("PRIVATE", "SHAREABLE"):
                    rejected = client.post(f"/deals/{deal.id}/messages", json={"body": "Too early", "visibility": visibility})
                    self.assertEqual(rejected.status_code, 404, rejected.text)
                    self.assertEqual(before, [self.db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables])
                for path, payload in (
                    ("/agreements", {"proposal_id": str(uuid4())}),
                    ("/agreements/from-reviewed-terms", {
                        "schema_version": 1, "description": "Bolts", "quantity": "10",
                        "unit": "boxes", "unit_price": "20", "currency": "USD",
                        "delivery_destination": "Tokyo", "delivery_date": "2027-01-01",
                    }),
                ):
                    rejected = client.post(f"/deals/{deal.id}{path}", json=payload)
                    self.assertEqual(rejected.status_code, 409, rejected.text)
                    self.assertEqual(before, [self.db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables])
                prepared = client.post(f"/deals/{deal.id}/facts", json={
                    "field": "description", "typed_value": "Human draft", "visibility": "PRIVATE",
                })
                self.assertEqual(prepared.status_code, 201, prepared.text)
                outsider = self._user("unrelated@example.com")
                app.dependency_overrides[get_current_actor] = lambda: ActorContext(outsider.id, frozenset({buyer.id}))
                for suffix in ("", "/messages", "/facts"):
                    hidden = client.get(f"/deals/{deal.id}{suffix}")
                    self.assertEqual(hidden.status_code, 404, hidden.text)
                    self.assertNotIn("kenji", hidden.text.lower())
                app.dependency_overrides[get_current_actor] = lambda: ActorContext(admin.id, frozenset({buyer.id}))
                response = client.post("/invitations/accept", json=self._counterparty_accept_payload(invitation["token"]).model_dump())
                self.assertEqual(response.status_code, 200, response.text)
                accepted = response.json()
                self.assertEqual(accepted["role"], "ADMIN")
                self.assertNotEqual(accepted["organization_id"], str(buyer.id))
                self.assertNotEqual(accepted["organization_id"], str(shell_id))
                self.db.expire_all()
                self.assertEqual(self.db.get(Deal, deal.id).seller_organization_id, UUID(accepted["organization_id"]))
                self.assertEqual(self.db.get(Deal, deal.id).version, 2)
                self.assertFalse(client.get(f"/deals/{deal.id}").json()["pending_counterparty"])
                self.assertEqual(self.db.get(Organization, shell_id).status, "INACTIVE")
                self.assertEqual(self.db.scalar(select(func.count(Conversation.id)).where(Conversation.participant_organization_id == UUID(accepted["organization_id"]))), 1)
                recipient_id = UUID(accepted["user_id"])
                self.assertIsNone(self.db.scalar(select(OrganizationMember.id).where(OrganizationMember.organization_id == buyer.id, OrganizationMember.user_id == recipient_id)))
                app.dependency_overrides[get_current_actor] = lambda: ActorContext(recipient_id, frozenset({UUID(accepted["organization_id"])}))
                self.assertEqual(client.get("/deals").json()[0]["viewer_role"], "SELLER")
                self.assertEqual(client.post(f"/deals/{deal.id}/messages", json={"body": "Seller response", "visibility": "SHAREABLE"}).status_code, 201)
                replay = client.post("/invitations/accept", json=self._counterparty_accept_payload(invitation["token"]).model_dump())
                self.assertEqual(replay.status_code, 409)
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original_overrides)

    def test_bound_invitation_wrong_account_and_signup_rollback(self) -> None:
        _, _, invitation = self._pending_invitation()
        wrong = self._user("wrong@example.com")
        before = [self.db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables]
        for actor, email in ((ActorContext(wrong.id, frozenset()), "kenji@tokyo-trade.jp"), (None, "wrong@example.com")):
            payload = self._counterparty_accept_payload(invitation["token"]).model_copy(update={"email": email})
            with self.assertRaises(HTTPException) as caught:
                accept_invitation(payload, actor, self.db)
            self.assertEqual(caught.exception.status_code, 403)
            self.assertEqual(before, [self.db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables])

    def test_initiation_signing_failure_rolls_back_shell_deal_and_notification(self) -> None:
        admin = self._user("buyer@example.com")
        buyer = self._organization(admin)
        before = [self.db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables]
        with patch("syncally.api.organizations._create_invitation_token", side_effect=RuntimeError("injected")), self.assertRaises(RuntimeError):
            create_counterparty_invitation(
                CreateCounterpartyInvitationRequest(buyer_organization_id=buyer.id,
                    recipient_email="seller@example.com", legal_name="Seller", country_code="JP"),
                ActorContext(admin.id, frozenset({buyer.id})), self.db,
            )
        self.assertEqual(before, [self.db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables])

    def test_bound_team_role_is_member_and_cannot_switch_kind(self) -> None:
        admin = self._user("admin@example.com")
        invitee = self._user("invitee@example.com")
        org = self._organization(admin)
        result = create_organization_invitation(org.id, CreateInvitationRequest(recipient_email=invitee.email, role="ADMIN"), ActorContext(admin.id, frozenset({org.id})), self.db)
        self.assertEqual(result["role"], "MEMBER")
        with self.assertRaises(HTTPException):
            accept_invitation(AcceptInvitationRequest(token=result["token"], organization_legal_name="Spoof"), ActorContext(invitee.id, frozenset()), self.db)
        accepted = accept_invitation(AcceptInvitationRequest(token=result["token"]), ActorContext(invitee.id, frozenset()), self.db)
        self.assertEqual(accepted["organization_id"], str(org.id))
        self.assertEqual(accepted["role"], "MEMBER")

    def test_counterparty_claim_tampering_and_suspended_recipient_have_no_writes(self) -> None:
        _, _, invitation = self._pending_invitation()
        recipient = self._user("kenji@tokyo-trade.jp")
        claims = jwt.decode(invitation["token"], settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        mutations = (
            {"version": True}, {"version": "1"}, {"kind": "TEAM"},
            {"role": "ADMIN"}, {"shell_id": None}, {"deal_id": None},
            {"buyer_id": str(uuid4())}, {"shell_id": str(uuid4())},
            {"deal_id": str(uuid4())}, {"inviter_user_id": str(uuid4())},
            {"recipient_email": "other@example.com"},
        )
        before = [self.db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                token = jwt.encode({**claims, **mutation}, settings.jwt_secret, algorithm=settings.jwt_algorithm)
                with self.assertRaises(HTTPException) as caught:
                    accept_invitation(self._counterparty_accept_payload(token), None, self.db)
                self.assertIn(caught.exception.status_code, (400, 409))
                self.assertEqual(before, [self.db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables])
        recipient.status = "SUSPENDED"
        self.db.commit()
        with self.assertRaises(HTTPException) as caught:
            accept_invitation(self._counterparty_accept_payload(invitation["token"]), ActorContext(recipient.id, frozenset()), self.db)
        self.assertEqual(caught.exception.status_code, 401)
        self.assertEqual(before, [self.db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables])

    def test_acceptance_refresh_failure_rolls_back_everything(self) -> None:
        _, _, invitation = self._pending_invitation()
        before = [self.db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables]
        with patch("syncally.api.organizations.create_refresh_token", side_effect=RuntimeError("injected")), self.assertRaises(RuntimeError):
            accept_invitation(self._counterparty_accept_payload(invitation["token"]), None, self.db)
        self.assertEqual(before, [self.db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables])
        self.assertIsNone(self.db.scalar(select(CounterpartyOnboarding)).consumed_at)
        self.assertEqual(self.db.scalar(select(func.count(RefreshToken.id))), 0)

    def test_pending_initiation_requires_database_active_buyer_admin(self) -> None:
        admin = self._user("admin@example.com")
        buyer = self._organization(admin)
        outsider = self._user("outsider@example.com")
        payload = CreateCounterpartyInvitationRequest(buyer_organization_id=buyer.id, recipient_email="seller@example.com", legal_name="Seller", country_code="US")
        for role, account_status in (("MEMBER", "ACTIVE"), ("ADMIN", "SUSPENDED")):
            self.db.add(OrganizationMember(organization_id=buyer.id, user_id=outsider.id, role=role, status="ACTIVE"))
            outsider.status = account_status
            self.db.commit()
            before = self.db.scalar(select(func.count(Deal.id)))
            with self.assertRaises(HTTPException):
                create_counterparty_invitation(payload, ActorContext(outsider.id, frozenset({buyer.id})), self.db)
            self.assertEqual(self.db.scalar(select(func.count(Deal.id))), before)
            self.db.query(OrganizationMember).filter_by(user_id=outsider.id).delete()
            self.db.commit()

    def test_matching_authenticated_recipient_ignores_request_email(self) -> None:
        _, buyer, invitation = self._pending_invitation()
        recipient = self._user("kenji@tokyo-trade.jp")
        accepted = accept_invitation(self._counterparty_accept_payload(invitation["token"]).model_copy(update={"email": "spoof@example.com"}), ActorContext(recipient.id, frozenset()), self.db)
        self.assertEqual(accepted["user_id"], str(recipient.id))
        self.assertNotEqual(accepted["organization_id"], str(buyer.id))

    def test_bound_quota_and_revoked_inviter_rollback(self) -> None:
        admin, buyer, invitation = self._pending_invitation()
        recipient = self._user("kenji@tokyo-trade.jp")
        self._organization(recipient)
        before = [self.db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables]
        with patch.object(settings, "max_organizations_per_user", 1), self.assertRaises(HTTPException) as caught:
            accept_invitation(self._counterparty_accept_payload(invitation["token"]), ActorContext(recipient.id, frozenset()), self.db)
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(before, [self.db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables])
        member = self.db.scalar(select(OrganizationMember).where(OrganizationMember.organization_id == buyer.id, OrganizationMember.user_id == admin.id))
        member.role = "MEMBER"
        self.db.commit()
        with self.assertRaises(HTTPException) as caught:
            accept_invitation(self._counterparty_accept_payload(invitation["token"]), ActorContext(recipient.id, frozenset()), self.db)
        self.assertEqual(caught.exception.status_code, 403)
        self.assertIsNone(self.db.scalar(select(CounterpartyOnboarding)).consumed_at)

    def test_bound_stale_and_expired_state_never_creates_recipient(self) -> None:
        _, _, invitation = self._pending_invitation()
        deal = self.db.get(Deal, UUID(invitation["deal_id"]))
        original_seller = deal.seller_organization_id
        onboarding = self.db.scalar(select(CounterpartyOnboarding))
        original_expiry = onboarding.expires_at
        for change in ("expired", "status", "parties", "active_shell", "proposal_reference", "messages", "negotiation"):
            with self.subTest(change=change):
                if change == "expired":
                    onboarding.expires_at = datetime.now(UTC) - timedelta(seconds=1)
                if change == "status":
                    deal.status = "NEGOTIATING"
                if change == "parties":
                    deal.seller_organization_id = uuid4()
                if change == "active_shell":
                    self.db.get(Organization, original_seller).status = "ACTIVE"
                if change == "proposal_reference":
                    deal.current_proposal_id = uuid4()
                if change == "messages":
                    conversation = Conversation(deal_id=deal.id, participant_organization_id=deal.buyer_organization_id)
                    self.db.add(conversation)
                    self.db.flush()
                    self.db.add(Message(conversation_id=conversation.id, author_user_id=onboarding.inviter_user_id, body="Already active", visibility="SHAREABLE", source_type="USER"))
                if change == "negotiation":
                    self.db.add(NegotiationSession(deal_id=deal.id, max_rounds=5, round_count=0))
                self.db.commit()
                before = [self.db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables]
                with self.assertRaises(HTTPException):
                    accept_invitation(self._counterparty_accept_payload(invitation["token"]), None, self.db)
                self.assertEqual(before, [self.db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables])
                self.db.query(Message).delete()
                self.db.query(Conversation).delete()
                self.db.query(NegotiationSession).delete()
                onboarding.expires_at = original_expiry
                deal.status = "DRAFT"
                deal.seller_organization_id = original_seller
                deal.current_proposal_id = None
                self.db.get(Organization, original_seller).status = "INACTIVE"
                self.db.commit()

    def test_malformed_versioned_tokens_never_fall_back_to_legacy(self) -> None:
        admin = self._user("admin@example.com")
        org = self._organization(admin)
        result = create_organization_invitation(
            org.id, CreateInvitationRequest(), ActorContext(admin.id, frozenset({org.id})), self.db
        )
        legacy = jwt.decode(result["token"], settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        self.assertEqual(_decode_invitation_token(result["token"])["org_id"], str(org.id))
        valid = {**legacy, "version": 1, "kind": "TEAM", "recipient_email": "invitee@example.com"}
        for changes in (
            {"version": 2}, {"kind": "OTHER"}, {"recipient_email": None},
            {"role": "ADMIN"}, {"deal_id": str(uuid4())}, {"shell_id": str(uuid4())},
        ):
            with self.subTest(changes=changes), self.assertRaises(HTTPException):
                _decode_invitation_token(jwt.encode({**valid, **changes}, settings.jwt_secret, algorithm=settings.jwt_algorithm))
        with self.assertRaises(HTTPException):
            _decode_invitation_token(jwt.encode({**legacy, "recipient_email": "invitee@example.com"}, settings.jwt_secret, algorithm=settings.jwt_algorithm))

    def test_admin_can_generate_invitation_token(self) -> None:
        admin = self._user("admin@example.com")
        org = self._organization(admin)
        actor = ActorContext(user_id=admin.id, organization_ids=frozenset({org.id}))

        result = create_organization_invitation(
            organization_id=org.id,
            payload=CreateInvitationRequest(),
            actor=actor,
            db=self.db,
        )

        self.assertIn("token", result)
        self.assertEqual(
            result["invite_url"],
            f"{settings.public_frontend_url}/#/invite?token={result['token']}",
        )
        self.assertEqual(result["organization_id"], str(org.id))
        self.assertEqual(result["organization_legal_name"], "Acme Corp")
        self.assertEqual(result["role"], "MEMBER")

        # Verify decoded claims
        claims = jwt.decode(
            result["token"],
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "typ", "jti"]},
        )
        self.assertEqual(claims["sub"], str(org.id))
        self.assertEqual(claims["org_id"], str(org.id))
        self.assertEqual(claims["typ"], "organization_invitation")
        self.assertEqual(claims["role"], "MEMBER")

        # Expiration must be approximately 7 days (within 5 seconds tolerance)
        ttl_seconds = claims["exp"] - claims["iat"]
        self.assertEqual(ttl_seconds, 7 * 86400)

    def test_public_frontend_url_ignores_headers_and_preserves_token_roundtrip(self) -> None:
        admin = self._user("admin@example.com")
        org = self._organization(admin)
        actor = ActorContext(user_id=admin.id, organization_ids=frozenset({org.id}))
        original_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_actor] = lambda: actor
        try:
            for app_env, value in (
                ("development", None),
                ("test", "http://127.0.0.1:5174/portal/"),
                ("production", "https://app.syncally.trade/workspace/"),
            ):
                with self.subTest(app_env=app_env):
                    invitee = self._user(f"invitee-{app_env}@example.com")
                    configured = Settings(
                        _env_file=None,
                        app_env=app_env,
                        public_frontend_url=value,
                        database_url="postgresql+psycopg://configured.example/syncally",
                        jwt_secret="SBLsd2xA2yUll_ixIwVOvnukFtR4o8MwjZKlIWyG4_8",
                        temporal_tls=True,
                    )
                    with (
                        patch.object(settings, "public_frontend_url", configured.public_frontend_url),
                        patch.object(settings, "app_env", app_env),
                        TestClient(app) as client,
                    ):
                        response = client.post(
                            f"/organizations/{org.id}/invitations",
                            json={},
                            headers={
                                "Host": "evil.example",
                                "Forwarded": "for=192.0.2.1;host=evil.example;proto=http",
                                "X-Forwarded-Host": "evil.example",
                                "X-Forwarded-Proto": "http",
                                "X-Forwarded-Prefix": "/evil",
                            },
                        )
                    self.assertEqual(response.status_code, 201, response.text)
                    result = response.json()
                    self.assertEqual(
                        result["invite_url"],
                        f"{configured.public_frontend_url}/#/invite?token={result['token']}",
                    )
                    fragment = urlsplit(result["invite_url"]).fragment
                    route, query = fragment.split("?", 1)
                    self.assertEqual(route, "/invite")
                    token = parse_qs(query)["token"][0]
                    self.assertEqual(token, result["token"])
                    accepted = accept_invitation(
                        payload=AcceptInvitationRequest(token=token),
                        actor=ActorContext(user_id=invitee.id, organization_ids=frozenset()),
                        db=self.db,
                    )
                    self.assertEqual(accepted["status"], "ACCEPTED")
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original_overrides)

    def test_non_admin_cannot_generate_invitation_token(self) -> None:
        admin = self._user("admin@example.com")
        member = self._user("member@example.com")
        org = self._organization(admin)

        # Add member as regular member
        self.db.add(
            OrganizationMember(
                organization_id=org.id,
                user_id=member.id,
                role="MEMBER",
                status="ACTIVE",
            )
        )
        self.db.commit()

        actor = ActorContext(user_id=member.id, organization_ids=frozenset({org.id}))
        with self.assertRaises(HTTPException) as ctx:
            create_organization_invitation(
                organization_id=org.id,
                payload=CreateInvitationRequest(),
                actor=actor,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    def test_generate_invitation_with_deal_id_validation(self) -> None:
        admin = self._user("admin@example.com")
        buyer_org = self._organization(admin)

        other_admin = self._user("other@example.com")
        seller_org = self._organization(other_admin)
        third_admin = self._user("third@example.com")
        third_org = self._organization(third_admin)

        deal = self._deal(buyer_org, seller_org)
        actor = ActorContext(user_id=admin.id, organization_ids=frozenset({buyer_org.id}))

        # Valid deal participation succeeds
        result = create_organization_invitation(
            organization_id=buyer_org.id,
            payload=CreateInvitationRequest(deal_id=deal.id),
            actor=actor,
            db=self.db,
        )
        self.assertEqual(result["deal_id"], str(deal.id))

        # Unrelated deal fails with 403
        third_actor = ActorContext(user_id=third_admin.id, organization_ids=frozenset({third_org.id}))
        with self.assertRaises(HTTPException) as ctx:
            create_organization_invitation(
                organization_id=third_org.id,
                payload=CreateInvitationRequest(deal_id=deal.id),
                actor=third_actor,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 403)

    def test_invited_user_can_accept_and_join(self) -> None:
        admin = self._user("admin@example.com")
        invitee = self._user("invitee@example.com")
        org = self._organization(admin)
        actor_admin = ActorContext(user_id=admin.id, organization_ids=frozenset({org.id}))

        invitation = create_organization_invitation(
            organization_id=org.id,
            payload=CreateInvitationRequest(),
            actor=actor_admin,
            db=self.db,
        )

        actor_invitee = ActorContext(user_id=invitee.id, organization_ids=frozenset())
        accept_result = accept_invitation(
            payload=AcceptInvitationRequest(token=invitation["token"]),
            actor=actor_invitee,
            db=self.db,
        )

        self.assertEqual(accept_result["status"], "ACCEPTED")
        self.assertEqual(accept_result["organization_id"], str(org.id))
        self.assertEqual(accept_result["user_id"], str(invitee.id))
        self.assertEqual(accept_result["role"], "MEMBER")
        self.assertEqual(invitee.password_hash, "provisioned-password-hash")

        # Verify DB membership
        member = self.db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.user_id == invitee.id,
            )
        )
        self.assertIsNotNone(member)
        self.assertEqual(member.role, "MEMBER")
        self.assertEqual(member.status, "ACTIVE")

        # Verify AuditEvent recorded
        audit = self.db.scalar(
            select(AuditEvent).where(
                AuditEvent.aggregate_type == "organization_invitation",
                AuditEvent.event_type == "invitation.accepted",
            )
        )
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor_id, str(invitee.id))

    def test_invitation_password_boundaries_allow_subsequent_login(self) -> None:
        admin = self._user("admin@example.com")
        org = self._organization(admin)
        actor_admin = ActorContext(user_id=admin.id, organization_ids=frozenset({org.id}))
        original_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_optional_actor] = lambda: None
        try:
            with TestClient(app) as client:
                for length in (12, 128):
                    with self.subTest(length=length):
                        invitation = create_organization_invitation(
                            organization_id=org.id,
                            payload=CreateInvitationRequest(),
                            actor=actor_admin,
                            db=self.db,
                        )
                        credentials = {
                            "email": f"invitee-{length}@example.com",
                            "password": "p" * length,
                        }
                        accepted = client.post(
                            "/invitations/accept",
                            json={"token": invitation["token"], **credentials},
                        )
                        self.assertEqual(accepted.status_code, 200, accepted.text)
                        self.assertEqual(accepted.json()["status"], "ACCEPTED")
                        signed_in = client.post("/auth/login", json=credentials)
                        self.assertEqual(signed_in.status_code, 200, signed_in.text)
                        self.assertTrue(signed_in.json()["access_token"])
                        self.assertTrue(signed_in.json()["refresh_token"])
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original_overrides)

    def test_invalid_invitation_password_lengths_reject_without_writes(self) -> None:
        admin = self._user("admin@example.com")
        org = self._organization(admin)
        invitation = create_organization_invitation(
            organization_id=org.id,
            payload=CreateInvitationRequest(),
            actor=ActorContext(user_id=admin.id, organization_ids=frozenset({org.id})),
            db=self.db,
        )
        tables = Base.metadata.sorted_tables
        before = [self.db.scalar(select(func.count()).select_from(table)) for table in tables]
        original_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_optional_actor] = lambda: None
        try:
            with TestClient(app) as client:
                for length in (0, 7, 8, 9, 10, 11, 129):
                    with self.subTest(length=length):
                        response = client.post(
                            "/invitations/accept",
                            json={
                                "token": invitation["token"],
                                "email": "new-invitee@example.com",
                                "password": "p" * length,
                                "organization_legal_name": "New Invitee Co",
                                "country_code": "US",
                            },
                        )
                        self.assertEqual(response.status_code, 422, response.text)
                        self.assertEqual(response.json()["detail"][0]["loc"], ["body", "password"])
                        self.assertEqual(
                            [self.db.scalar(select(func.count()).select_from(table)) for table in tables],
                            before,
                        )
                accepted = client.post(
                    "/invitations/accept",
                    json={
                        "token": invitation["token"],
                        "email": "new-invitee@example.com",
                        "password": "p" * 12,
                    },
                )
                self.assertEqual(accepted.status_code, 200, accepted.text)
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original_overrides)

    def test_invitation_token_is_strictly_single_use(self) -> None:
        admin = self._user("admin@example.com")
        invitee1 = self._user("invitee1@example.com")
        invitee2 = self._user("invitee2@example.com")
        org = self._organization(admin)
        actor_admin = ActorContext(user_id=admin.id, organization_ids=frozenset({org.id}))

        invitation = create_organization_invitation(
            organization_id=org.id,
            payload=CreateInvitationRequest(),
            actor=actor_admin,
            db=self.db,
        )

        # First acceptance succeeds
        actor1 = ActorContext(user_id=invitee1.id, organization_ids=frozenset())
        accept_invitation(
            payload=AcceptInvitationRequest(token=invitation["token"]),
            actor=actor1,
            db=self.db,
        )

        # Second acceptance with same token fails with 409
        actor2 = ActorContext(user_id=invitee2.id, organization_ids=frozenset())
        with self.assertRaises(HTTPException) as ctx:
            accept_invitation(
                payload=AcceptInvitationRequest(token=invitation["token"]),
                actor=actor2,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("already been used", ctx.exception.detail)

    def test_acceptance_is_atomic_when_audit_event_conflicts(self) -> None:
        admin = self._user("admin@example.com")
        org = self._organization(admin)
        actor_admin = ActorContext(user_id=admin.id, organization_ids=frozenset({org.id}))

        invitation = create_organization_invitation(
            organization_id=org.id,
            payload=CreateInvitationRequest(),
            actor=actor_admin,
            db=self.db,
        )
        claims = jwt.decode(
            invitation["token"],
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        jti = UUID(claims["jti"])

        # Simulate a competing acceptance that wins between the single-use read
        # and the insert: same primary key, different event type so the pre-check
        # does not see it.
        self.db.add(
            AuditEvent(
                id=jti,
                aggregate_type="organization_invitation",
                aggregate_id=jti,
                event_type="invitation.other",
                actor_type="USER",
                actor_id=str(admin.id),
                occurred_at=datetime.now(UTC),
                payload={},
            )
        )
        self.db.commit()

        payload = AcceptInvitationRequest(
            token=invitation["token"],
            email="new-invitee@example.com",
            password="SecurePassword123!",
            display_name="New Invitee",
        )
        with self.assertRaises(HTTPException) as ctx:
            accept_invitation(payload=payload, actor=None, db=self.db)
        self.assertEqual(ctx.exception.status_code, 409)

        # No user, membership or refresh token from the failed acceptance was
        # committed alongside the conflicting audit event.
        self.assertIsNone(
            self.db.scalar(select(User).where(User.email == "new-invitee@example.com"))
        )

    def test_expired_invitation_token_fails(self) -> None:
        admin = self._user("admin@example.com")
        invitee = self._user("invitee@example.com")
        org = self._organization(admin)

        # Issue token that expired 1 second ago
        now = datetime.now(UTC)
        past = now - timedelta(days=8)
        claims = {
            "jti": str(uuid4()),
            "sub": str(org.id),
            "org_id": str(org.id),
            "org_name": org.legal_name,
            "deal_id": None,
            "role": "MEMBER",
            "inviter_user_id": str(admin.id),
            "iat": int(past.timestamp()),
            "exp": int((past + timedelta(days=7)).timestamp()),
            "typ": "organization_invitation",
        }
        expired_token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        actor_invitee = ActorContext(user_id=invitee.id, organization_ids=frozenset())
        with self.assertRaises(HTTPException) as ctx:
            accept_invitation(
                payload=AcceptInvitationRequest(token=expired_token),
                actor=actor_invitee,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("expired", ctx.exception.detail)

    def test_tampered_invitation_token_fails(self) -> None:
        invitee = self._user("invitee@example.com")
        actor_invitee = ActorContext(user_id=invitee.id, organization_ids=frozenset())

        with self.assertRaises(HTTPException) as ctx:
            accept_invitation(
                payload=AcceptInvitationRequest(token="invalid.token.here"),
                actor=actor_invitee,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Invalid invitation token", ctx.exception.detail)

    def test_accept_invitation_rejects_malformed_deal_id_claim(self) -> None:
        admin = self._user("admin@example.com")
        invitee = self._user("invitee@example.com")
        org = self._organization(admin)

        now = datetime.now(UTC)
        claims = {
            "jti": str(uuid4()),
            "sub": str(org.id),
            "org_id": str(org.id),
            "org_name": org.legal_name,
            "deal_id": "not-a-uuid",
            "role": "MEMBER",
            "inviter_user_id": str(admin.id),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(days=7)).timestamp()),
            "typ": "organization_invitation",
        }
        token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        with self.assertRaises(HTTPException) as ctx:
            accept_invitation(
                payload=self._counterparty_accept_payload(token),
                actor=ActorContext(user_id=invitee.id, organization_ids=frozenset()),
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Invalid invitation token claims", ctx.exception.detail)

    def test_accept_invitation_rejects_unknown_deal_claim(self) -> None:
        admin = self._user("admin@example.com")
        invitee = self._user("invitee@example.com")
        org = self._organization(admin)

        now = datetime.now(UTC)
        claims = {
            "jti": str(uuid4()),
            "sub": str(org.id),
            "org_id": str(org.id),
            "org_name": org.legal_name,
            "deal_id": str(uuid4()),
            "role": "MEMBER",
            "inviter_user_id": str(admin.id),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(days=7)).timestamp()),
            "typ": "organization_invitation",
        }
        token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        with self.assertRaises(HTTPException) as ctx:
            accept_invitation(
                payload=self._counterparty_accept_payload(token),
                actor=ActorContext(user_id=invitee.id, organization_ids=frozenset()),
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("Deal not found", ctx.exception.detail)

    def test_accept_invitation_rejects_when_inviting_org_left_the_deal(self) -> None:
        admin = self._user("admin@example.com")
        buyer_org = self._organization(admin)
        placeholder = self._placeholder_organization()
        deal = self._deal(buyer_org, placeholder)
        token = self._invitation_for_deal(admin, buyer_org, deal)

        # The inviting side was replaced after the link was issued.
        replacement_buyer = self._placeholder_organization("Replacement Buyer")
        deal.buyer_organization_id = replacement_buyer.id
        self.db.commit()
        version_before = deal.version

        with self.assertRaises(HTTPException) as ctx:
            accept_invitation(
                payload=self._counterparty_accept_payload(token),
                actor=None,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("no longer a participant", ctx.exception.detail)
        self.db.refresh(deal)
        self.assertEqual(deal.seller_organization_id, placeholder.id)
        self.assertEqual(deal.version, version_before)
        self.assertEqual(self.db.scalar(select(func.count(Conversation.id))), 0)

    def test_accept_invitation_rejects_deal_that_left_draft(self) -> None:
        admin = self._user("admin@example.com")
        buyer_org = self._organization(admin)
        placeholder = self._placeholder_organization()
        deal = self._deal(buyer_org, placeholder)
        token = self._invitation_for_deal(admin, buyer_org, deal)

        deal.status = "NEGOTIATING"
        self.db.commit()
        version_before = deal.version

        with self.assertRaises(HTTPException) as ctx:
            accept_invitation(
                payload=self._counterparty_accept_payload(token),
                actor=None,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("no longer open", ctx.exception.detail)
        self.db.refresh(deal)
        self.assertEqual(deal.status, "NEGOTIATING")
        self.assertEqual(deal.seller_organization_id, placeholder.id)
        self.assertEqual(deal.version, version_before)
        self.assertEqual(self.db.scalar(select(func.count(Conversation.id))), 0)

    def test_accept_invitation_rejects_claimed_counterparty(self) -> None:
        admin = self._user("admin@example.com")
        buyer_org = self._organization(admin)
        claimed_seller = self._placeholder_organization("Claimed Seller")
        self.db.add(
            OrganizationMember(
                organization_id=claimed_seller.id,
                user_id=self._user("seller@example.com").id,
                role="ADMIN",
                status="ACTIVE",
            )
        )
        self.db.commit()
        deal = self._deal(buyer_org, claimed_seller)
        token = self._invitation_for_deal(admin, buyer_org, deal)
        version_before = deal.version

        with self.assertRaises(HTTPException) as ctx:
            accept_invitation(
                payload=self._counterparty_accept_payload(token),
                actor=None,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("already claimed", ctx.exception.detail)
        self.db.refresh(deal)
        self.assertEqual(deal.seller_organization_id, claimed_seller.id)
        self.assertEqual(deal.version, version_before)
        self.assertEqual(self.db.scalar(select(func.count(Conversation.id))), 0)
        # Rejected before any recipient organization was created.
        self.assertEqual(
            self.db.scalar(
                select(func.count(Organization.id)).where(
                    Organization.legal_name == "Tokyo Exporters Ltd"
                )
            ),
            0,
        )

    def test_deal_invitation_requires_counterparty_organization(self) -> None:
        admin = self._user("admin@buyer.com")
        buyer_org = self._organization(admin)
        placeholder = self._placeholder_organization()
        deal = self._deal(buyer_org, placeholder)
        token = self._invitation_for_deal(admin, buyer_org, deal)
        version_before = deal.version

        payload = AcceptInvitationRequest(
            token=token,
            email="kenji@tokyo-trade.jp",
            password="SecurePassword123!",
            display_name="Kenji Sato",
        )
        with self.assertRaises(HTTPException) as ctx:
            accept_invitation(payload=payload, actor=None, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("organization legal name", ctx.exception.detail)

        # The recipient must not be created or silently joined to the inviting org.
        self.assertIsNone(
            self.db.scalar(select(User).where(User.email == "kenji@tokyo-trade.jp"))
        )
        self.assertEqual(
            self.db.scalar(
                select(func.count(OrganizationMember.id)).where(
                    OrganizationMember.organization_id == buyer_org.id,
                )
            ),
            1,
        )

        # The deal must be untouched and the invitation not consumed.
        self.db.refresh(deal)
        self.assertEqual(deal.seller_organization_id, placeholder.id)
        self.assertEqual(deal.version, version_before)
        self.assertEqual(self.db.scalar(select(func.count(Conversation.id))), 0)
        self.assertIsNone(
            self.db.scalar(
                select(AuditEvent.id).where(
                    AuditEvent.aggregate_type == "organization_invitation",
                    AuditEvent.event_type == "invitation.accepted",
                )
            )
        )

    def test_accept_invitation_when_already_active_member(self) -> None:
        admin = self._user("admin@example.com")
        org = self._organization(admin)
        actor_admin = ActorContext(user_id=admin.id, organization_ids=frozenset({org.id}))

        invitation = create_organization_invitation(
            organization_id=org.id,
            payload=CreateInvitationRequest(),
            actor=actor_admin,
            db=self.db,
        )

        # Admin tries to accept invitation to their own org where they are already ADMIN
        with self.assertRaises(HTTPException) as ctx:
            accept_invitation(
                payload=AcceptInvitationRequest(token=invitation["token"]),
                actor=actor_admin,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("already has an active membership", ctx.exception.detail)

    def test_unauthenticated_counterparty_signup_and_deal_linking(self) -> None:
        admin = self._user("admin@buyer.com")
        buyer_org = self._organization(admin)
        placeholder_seller = Organization(legal_name="Pending Seller", country_code="US")
        self.db.add(placeholder_seller)
        self.db.commit()

        deal = self._deal(buyer_org, placeholder_seller)
        actor_admin = ActorContext(user_id=admin.id, organization_ids=frozenset({buyer_org.id}))

        invitation = create_organization_invitation(
            organization_id=buyer_org.id,
            payload=CreateInvitationRequest(deal_id=deal.id),
            actor=actor_admin,
            db=self.db,
        )

        # Unauthenticated counterparty accepts and creates their organization
        payload = AcceptInvitationRequest(
            token=invitation["token"],
            email="kenji@tokyo-trade.jp",
            password="SecurePassword123!",
            display_name="Kenji Sato",
            organization_legal_name="Tokyo Exporters Ltd",
            country_code="JP",
        )

        result = accept_invitation(
            payload=payload,
            actor=None,
            db=self.db,
        )

        self.assertEqual(result["status"], "ACCEPTED")
        self.assertEqual(result["organization_legal_name"], "Tokyo Exporters Ltd")
        self.assertEqual(result["deal_id"], str(deal.id))
        self.assertEqual(result["role"], "ADMIN")
        self.assertIsNotNone(result["access_token"])
        self.assertIsNotNone(result["refresh_token"])

        # Check recipient user was created
        created_user = self.db.scalar(select(User).where(User.email == "kenji@tokyo-trade.jp"))
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user.display_name, "Kenji Sato")

        # Check recipient organization was created
        created_org = self.db.scalar(
            select(Organization).where(Organization.legal_name == "Tokyo Exporters Ltd")
        )
        self.assertIsNotNone(created_org)
        self.assertEqual(created_org.country_code, "JP")

        # Check user is ADMIN of the created organization
        membership = self.db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == created_org.id,
                OrganizationMember.user_id == created_user.id,
            )
        )
        self.assertIsNotNone(membership)
        self.assertEqual(membership.role, "ADMIN")

        # Verify deal counterparty (seller) is now linked to Tokyo Exporters Ltd!
        self.db.refresh(deal)
        self.assertEqual(deal.seller_organization_id, created_org.id)

        # Second attempt with the same token must fail with 409
        with self.assertRaises(HTTPException) as ctx:
            accept_invitation(
                payload=payload,
                actor=None,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 409)

    def test_unauthenticated_acceptance_requires_credentials(self) -> None:
        admin = self._user("admin@example.com")
        org = self._organization(admin)
        actor_admin = ActorContext(user_id=admin.id, organization_ids=frozenset({org.id}))

        invitation = create_organization_invitation(
            organization_id=org.id,
            payload=CreateInvitationRequest(),
            actor=actor_admin,
            db=self.db,
        )

        with self.assertRaises(HTTPException) as ctx:
            accept_invitation(
                payload=AcceptInvitationRequest(token=invitation["token"]),
                actor=None,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Email and password are required", ctx.exception.detail)

    def test_accept_invitation_rejects_missing_or_invalid_inviter_user_id(self) -> None:
        admin = self._user("admin@example.com")
        invitee = self._user("invitee@example.com")
        org = self._organization(admin)

        now = datetime.now(UTC)
        # Token missing inviter_user_id
        claims_missing = {
            "jti": str(uuid4()),
            "sub": str(org.id),
            "org_id": str(org.id),
            "org_name": org.legal_name,
            "deal_id": None,
            "role": "MEMBER",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(days=7)).timestamp()),
            "typ": "organization_invitation",
        }
        token_missing = jwt.encode(claims_missing, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        actor_invitee = ActorContext(user_id=invitee.id, organization_ids=frozenset())
        with self.assertRaises(HTTPException) as ctx:
            accept_invitation(
                payload=AcceptInvitationRequest(token=token_missing),
                actor=actor_invitee,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Invalid invitation token claims", ctx.exception.detail)

    def test_accept_invitation_rejects_when_inviter_is_no_longer_admin(self) -> None:
        admin = self._user("admin@example.com")
        invitee = self._user("invitee@example.com")
        org = self._organization(admin)
        actor_admin = ActorContext(user_id=admin.id, organization_ids=frozenset({org.id}))

        invitation = create_organization_invitation(
            organization_id=org.id,
            payload=CreateInvitationRequest(),
            actor=actor_admin,
            db=self.db,
        )

        # Demote admin to regular MEMBER before acceptance
        membership = self.db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.user_id == admin.id,
            )
        )
        self.assertIsNotNone(membership)
        membership.role = "MEMBER"
        self.db.commit()

        actor_invitee = ActorContext(user_id=invitee.id, organization_ids=frozenset())
        with self.assertRaises(HTTPException) as ctx:
            accept_invitation(
                payload=AcceptInvitationRequest(token=invitation["token"]),
                actor=actor_invitee,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Inviter is no longer an active organization admin", ctx.exception.detail)

    def test_accept_invitation_rejects_when_inviter_is_deactivated_or_removed(self) -> None:
        admin = self._user("admin@example.com")
        invitee = self._user("invitee@example.com")
        org = self._organization(admin)
        actor_admin = ActorContext(user_id=admin.id, organization_ids=frozenset({org.id}))

        invitation = create_organization_invitation(
            organization_id=org.id,
            payload=CreateInvitationRequest(),
            actor=actor_admin,
            db=self.db,
        )

        # Deactivate admin account
        admin.status = "SUSPENDED"
        self.db.commit()

        actor_invitee = ActorContext(user_id=invitee.id, organization_ids=frozenset())
        with self.assertRaises(HTTPException) as ctx:
            accept_invitation(
                payload=AcceptInvitationRequest(token=invitation["token"]),
                actor=actor_invitee,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Inviter is no longer an active organization admin", ctx.exception.detail)


class OnboardingConcurrencyCases:
    def seed(self) -> None:
        self.secret_patch = patch.object(settings, "jwt_secret", "test-secret-with-more-than-32-characters")
        self.secret_patch.start()
        self.addCleanup(self.secret_patch.stop)
        Base.metadata.create_all(self.scoped_engine)
        with Session(self.scoped_engine) as db:
            buyer_user = User(email="buyer@example.com", display_name="Buyer", status="ACTIVE")
            buyer = Organization(legal_name="Buyer", country_code="US")
            db.add_all([buyer_user, buyer])
            db.flush()
            db.add(OrganizationMember(organization_id=buyer.id, user_id=buyer_user.id, role="ADMIN", status="ACTIVE"))
            db.commit()
            self.buyer_actor = ActorContext(buyer_user.id, frozenset({buyer.id}))
            self.invitation = create_counterparty_invitation(
                CreateCounterpartyInvitationRequest(buyer_organization_id=buyer.id, recipient_email="recipient@example.com", legal_name="Pending", country_code="JP"), self.buyer_actor, db,
            )
            self.deal_id = UUID(self.invitation["deal_id"])
            self.shell_id = db.get(Deal, self.deal_id).seller_organization_id

    def recipient_payload(self) -> AcceptInvitationRequest:
        return AcceptInvitationRequest(token=self.invitation["token"], email="recipient@example.com", password="SecurePassword123!", organization_legal_name="Recipient", country_code="JP")

    def accept(self, gate: threading.Barrier | None = None) -> str:
        with Session(self.scoped_engine) as db:
            if gate is not None:
                gate.wait()
            try:
                accept_invitation(self.recipient_payload(), None, db)
                return "accepted"
            except HTTPException as exc:
                self.assertEqual(exc.status_code, 409)
                self.assertFalse(db.in_transaction())
                return "conflict"

    def assert_single_recipient(self) -> None:
        with Session(self.scoped_engine) as db:
            self.assertEqual(db.scalar(select(func.count(User.id))), 2)
            self.assertEqual(db.scalar(select(func.count(Organization.id))), 3)
            self.assertEqual(db.scalar(select(func.count(OrganizationMember.id))), 2)
            self.assertEqual(db.scalar(select(func.count(RefreshToken.id))), 1)
            self.assertEqual(db.get(Deal, self.deal_id).version, 2)
            self.assertNotEqual(db.get(Deal, self.deal_id).seller_organization_id, self.shell_id)
            self.assertIsNotNone(db.scalar(select(CounterpartyOnboarding)).consumed_at)
            self.assertEqual(db.scalar(select(func.count(AuditEvent.id)).where(AuditEvent.event_type == "invitation.accepted")), 1)

    def test_simultaneous_acceptance_one_winner_full_loser_rollback(self) -> None:
        gate = threading.Barrier(2, timeout=15)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [pool.submit(self.accept, gate) for _ in range(2)]
            self.assertEqual(sorted(result.result(timeout=30) for result in results), ["accepted", "conflict"])
        self.assert_single_recipient()

    def test_acceptance_vs_pending_message_writer(self) -> None:
        gate = threading.Barrier(2, timeout=15)

        def write_message() -> str:
            with Session(self.scoped_engine) as db:
                gate.wait()
                try:
                    add_message(self.buyer_actor, self.deal_id, AddMessageCommand(body="Buyer terms", visibility=Visibility.SHAREABLE), SqlAlchemyCommunicationRepository(db))
                    db.commit()
                    return "written"
                except CommunicationScopeError:
                    db.rollback()
                    return "pending"

        with ThreadPoolExecutor(max_workers=2) as pool:
            accepted = pool.submit(self.accept, gate)
            written = pool.submit(write_message)
            self.assertEqual(accepted.result(timeout=30), "accepted")
            write_result = written.result(timeout=30)
            self.assertIn(write_result, {"pending", "written"})
        self.assert_single_recipient()
        with Session(self.scoped_engine) as db:
            self.assertEqual(db.scalar(select(func.count(Message.id))), int(write_result == "written"))


class OnboardingSQLiteConcurrencyTests(OnboardingConcurrencyCases, unittest.TestCase):
    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.scoped_engine = create_database_engine(f"sqlite:///{temporary.name}/onboarding.db")
        self.addCleanup(self.scoped_engine.dispose)
        self.seed()


@unittest.skipUnless(os.environ.get("TEST_POSTGRES_URL"), "Set TEST_POSTGRES_URL for isolated F4 PostgreSQL races")
class OnboardingPostgresConcurrencyTests(OnboardingConcurrencyCases, unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(os.environ["TEST_POSTGRES_URL"], hide_parameters=True)
        self.schema = f"onboarding_{uuid4().hex}"
        with self.engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.scoped_engine = self.engine.execution_options(schema_translate_map={None: self.schema})
        self.addCleanup(self.cleanup_database)
        self.seed()

    def cleanup_database(self) -> None:
        try:
            with self.engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
        finally:
            self.engine.dispose()
