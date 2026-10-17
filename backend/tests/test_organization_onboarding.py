import unittest
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.main import app
from syncally.api.organizations import (
    AddOrganizationMemberRequest,
    CreateOrganizationRequest,
    add_organization_member,
    create_organization,
    list_my_organizations,
)
from syncally.application.identity import ActorContext, resolve_actor
from syncally.config import settings
from syncally.infrastructure.models import Base, Organization, OrganizationMember, User


class OrganizationOnboardingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def tearDown(self) -> None:
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
        organization = Organization(legal_name="Buyer Co", country_code="US")
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

    def test_organization_routes_are_registered(self) -> None:
        paths = app.openapi()["paths"]

        self.assertIn("/organizations", paths)
        self.assertIn("get", paths["/organizations"])
        self.assertIn("post", paths["/organizations"])
        self.assertIn("/organizations/{organization_id}/members", paths)

    def test_creator_gets_admin_membership_in_new_organization(self) -> None:
        user = self._user("owner@example.com")
        actor = ActorContext(user_id=user.id, organization_ids=frozenset())

        result = create_organization(
            CreateOrganizationRequest(legal_name="  Buyer Co  ", country_code="us"),
            actor,
            self.db,
        )

        membership = self.db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == UUID(result["id"]),
                OrganizationMember.user_id == user.id,
            )
        )
        self.assertEqual(result["legal_name"], "Buyer Co")
        self.assertEqual(result["country_code"], "US")
        self.assertEqual(result["role"], "ADMIN")
        self.assertIsNotNone(membership)
        self.assertEqual(membership.role, "ADMIN")
        self.assertEqual(membership.status, "ACTIVE")

    def test_organization_creation_respects_per_user_limit(self) -> None:
        user = self._user("owner@example.com")
        actor = ActorContext(user_id=user.id, organization_ids=frozenset())
        original_limit = settings.max_organizations_per_user
        try:
            settings.max_organizations_per_user = 1
            create_organization(
                CreateOrganizationRequest(legal_name="First Co", country_code="US"),
                actor,
                self.db,
            )
            with self.assertRaises(HTTPException) as raised:
                create_organization(
                    CreateOrganizationRequest(legal_name="Second Co", country_code="US"),
                    actor,
                    self.db,
                )
        finally:
            settings.max_organizations_per_user = original_limit

        self.assertEqual(raised.exception.status_code, 409)

    def test_admin_can_add_an_existing_active_user_as_member(self) -> None:
        admin = self._user("admin@example.com")
        member = self._user("member@example.com")
        organization = self._organization(admin)
        actor = ActorContext(user_id=admin.id, organization_ids=frozenset({organization.id}))

        result = add_organization_member(
            organization.id,
            AddOrganizationMemberRequest(email=" MEMBER@example.com "),
            actor,
            self.db,
        )

        self.assertEqual(result, {"user_id": str(member.id), "email": member.email, "role": "MEMBER"})
        actor_context = resolve_actor(self.db, member.id)
        self.assertIsNotNone(actor_context)
        self.assertIn(organization.id, actor_context.organization_ids)
        self.assertEqual(
            list_my_organizations(actor_context, self.db),
            [
                {
                    "id": str(organization.id),
                    "legal_name": organization.legal_name,
                    "country_code": organization.country_code,
                    "role": "MEMBER",
                }
            ],
        )

    def test_non_admin_cannot_add_members(self) -> None:
        admin = self._user("admin@example.com")
        member = self._user("member@example.com")
        another_user = self._user("other@example.com")
        organization = self._organization(admin)
        self.db.add(
            OrganizationMember(
                organization_id=organization.id,
                user_id=member.id,
                role="MEMBER",
                status="ACTIVE",
            )
        )
        self.db.commit()
        actor = ActorContext(user_id=member.id, organization_ids=frozenset({organization.id}))

        with self.assertRaises(HTTPException) as raised:
            add_organization_member(
                organization.id,
                AddOrganizationMemberRequest(email=another_user.email),
                actor,
                self.db,
            )

        self.assertEqual(raised.exception.status_code, 403)

    def test_unprovisioned_user_and_duplicate_membership_are_rejected(self) -> None:
        admin = self._user("admin@example.com")
        member = self._user("member@example.com")
        unprovisioned = User(
            email="unprovisioned@example.com",
            display_name="Unprovisioned",
            password_hash=None,
            status="ACTIVE",
        )
        self.db.add(unprovisioned)
        self.db.commit()
        organization = self._organization(admin)
        actor = ActorContext(user_id=admin.id, organization_ids=frozenset({organization.id}))

        with self.assertRaises(HTTPException) as missing:
            add_organization_member(
                organization.id,
                AddOrganizationMemberRequest(email="unknown@example.com"),
                actor,
                self.db,
            )
        self.assertEqual(missing.exception.status_code, 404)

        with self.assertRaises(HTTPException) as unprovisioned_account:
            add_organization_member(
                organization.id,
                AddOrganizationMemberRequest(email=unprovisioned.email),
                actor,
                self.db,
            )
        self.assertEqual(unprovisioned_account.exception.status_code, 404)

        add_organization_member(
            organization.id,
            AddOrganizationMemberRequest(email=member.email),
            actor,
            self.db,
        )
        with self.assertRaises(HTTPException) as duplicate:
            add_organization_member(
                organization.id,
                AddOrganizationMemberRequest(email=member.email),
                actor,
                self.db,
            )
        self.assertEqual(duplicate.exception.status_code, 409)

    def test_inactive_membership_is_reactivated_as_regular_member(self) -> None:
        admin = self._user("admin@example.com")
        member = self._user("member@example.com")
        organization = self._organization(admin)
        old_membership = OrganizationMember(
            organization_id=organization.id,
            user_id=member.id,
            role="ADMIN",
            status="INACTIVE",
        )
        self.db.add(old_membership)
        self.db.commit()
        actor = ActorContext(user_id=admin.id, organization_ids=frozenset({organization.id}))

        result = add_organization_member(
            organization.id,
            AddOrganizationMemberRequest(email=member.email),
            actor,
            self.db,
        )

        self.assertEqual(result["role"], "MEMBER")
        self.assertEqual(old_membership.status, "ACTIVE")
        self.assertEqual(old_membership.role, "MEMBER")
        self.assertEqual(
            self.db.scalar(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == organization.id,
                    OrganizationMember.user_id == member.id,
                )
            ).id,
            old_membership.id,
        )


if __name__ == "__main__":
    unittest.main()
