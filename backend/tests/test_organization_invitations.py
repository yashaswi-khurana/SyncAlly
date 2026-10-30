import unittest
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.main import app
from syncally.api.organizations import (
    AcceptInvitationRequest,
    CreateInvitationRequest,
    accept_invitation,
    create_organization_invitation,
)
from syncally.application.identity import ActorContext
from syncally.config import settings
from syncally.infrastructure.models import (
    AuditEvent,
    Base,
    Deal,
    Organization,
    OrganizationMember,
    User,
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

    def test_routes_are_registered_in_app(self) -> None:
        paths = app.openapi()["paths"]
        self.assertIn("/organizations/{organization_id}/invitations", paths)
        self.assertIn("post", paths["/organizations/{organization_id}/invitations"])
        self.assertIn("/invitations/accept", paths)
        self.assertIn("post", paths["/invitations/accept"])

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
        self.assertTrue(result["invite_url"].startswith("https://app.syncally.trade/#/invite?token="))
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
