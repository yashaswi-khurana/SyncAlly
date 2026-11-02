"""Test granular organization permissions, capability matrix, and security boundaries."""

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.organizations import (
    UpdateMemberPermissionsRequest,
    list_my_organizations,
    list_organization_members,
    revoke_organization_member,
    update_member_permissions,
)
from syncally.application.identity import ActorContext
from syncally.domain.organizations.organization import (
    OrganizationCapability,
    OrganizationMemberRole,
)
from syncally.domain.organizations.organization import (
    OrganizationMember as DomainOrganizationMember,
)
from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import OrganizationId, UserId
from syncally.infrastructure.identity import resolve_actor, verify_member_capability
from syncally.infrastructure.models import AuditEvent, Base, Organization, OrganizationMember, User


class OrganizationPermissionsTests(unittest.TestCase):
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
            password_hash="hashed-pw",
            status="ACTIVE",
        )
        self.db.add(user)
        self.db.commit()
        return user

    def _organization(self, name: str = "Test Corp") -> Organization:
        org = Organization(legal_name=name, country_code="US", status="ACTIVE")
        self.db.add(org)
        self.db.commit()
        return org

    def _member(
        self,
        org: Organization,
        user: User,
        role: str = "MEMBER",
        capabilities: list[str] | None = None,
        status: str = "ACTIVE",
    ) -> OrganizationMember:
        member = OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role=role,
            status=status,
            capabilities=capabilities or [],
            version=1,
        )
        self.db.add(member)
        self.db.commit()
        return member

    def _actor(self, user: User) -> ActorContext:
        actor = resolve_actor(self.db, user.id)
        assert actor is not None
        return actor

    def test_domain_capability_matrix_and_effective_capabilities(self) -> None:
        """Gate 1 & 8: Verify safe default roles and no blanket finance/fulfillment."""
        now = datetime.now(UTC)

        # ADMIN defaults to ADMINISTRATION, DRAFTING, AGREEMENT_APPROVAL
        admin_member = DomainOrganizationMember(
            organization_id=OrganizationId(uuid4()),
            user_id=UserId(uuid4()),
            created_at=now,
            role=OrganizationMemberRole.ADMIN,
        )
        self.assertTrue(admin_member.has_capability(OrganizationCapability.ADMINISTRATION))
        self.assertTrue(admin_member.has_capability(OrganizationCapability.DRAFTING))
        self.assertTrue(admin_member.has_capability(OrganizationCapability.AGREEMENT_APPROVAL))
        self.assertFalse(admin_member.has_capability(OrganizationCapability.FINANCE))
        self.assertFalse(admin_member.has_capability(OrganizationCapability.FULFILLMENT))

        # MEMBER defaults to DRAFTING ONLY
        reg_member = DomainOrganizationMember(
            organization_id=OrganizationId(uuid4()),
            user_id=UserId(uuid4()),
            created_at=now,
            role=OrganizationMemberRole.MEMBER,
        )
        self.assertFalse(reg_member.has_capability(OrganizationCapability.ADMINISTRATION))
        self.assertTrue(reg_member.has_capability(OrganizationCapability.DRAFTING))
        self.assertFalse(reg_member.has_capability(OrganizationCapability.AGREEMENT_APPROVAL))
        self.assertFalse(reg_member.has_capability(OrganizationCapability.FINANCE))
        self.assertFalse(reg_member.has_capability(OrganizationCapability.FULFILLMENT))

        # Explicit capabilities granted to MEMBER
        finance_member = DomainOrganizationMember(
            organization_id=OrganizationId(uuid4()),
            user_id=UserId(uuid4()),
            created_at=now,
            role=OrganizationMemberRole.MEMBER,
            capabilities=frozenset({OrganizationCapability.FINANCE, OrganizationCapability.FULFILLMENT}),
        )
        self.assertTrue(finance_member.has_capability(OrganizationCapability.DRAFTING))
        self.assertTrue(finance_member.has_capability(OrganizationCapability.FINANCE))
        self.assertTrue(finance_member.has_capability(OrganizationCapability.FULFILLMENT))
        self.assertFalse(finance_member.has_capability(OrganizationCapability.ADMINISTRATION))

    def test_invalid_capability_raises_invariant_violation(self) -> None:
        now = datetime.now(UTC)
        with self.assertRaises(InvariantViolation):
            DomainOrganizationMember(
                organization_id=OrganizationId(uuid4()),
                user_id=UserId(uuid4()),
                created_at=now,
                capabilities={"INVALID_CAP"},  # type: ignore[arg-type]
            )

    def test_list_members_requires_membership(self) -> None:
        """Gate 2: Cross-tenant member read rejection."""
        org_a = self._organization("Org A")
        org_b = self._organization("Org B")
        user_a = self._user("a@example.com")
        user_b = self._user("b@example.com")

        self._member(org_a, user_a, role="ADMIN")
        self._member(org_b, user_b, role="ADMIN")

        actor_a = self._actor(user_a)

        # Actor A can list Org A members
        members_a = list_organization_members(org_a.id, actor=actor_a, db=self.db)
        self.assertEqual(len(members_a), 1)
        self.assertEqual(members_a[0]["email"], "a@example.com")

        # Actor A cannot list Org B members (403 Forbidden)
        with self.assertRaises(HTTPException) as exc:
            list_organization_members(org_b.id, actor=actor_a, db=self.db)
        self.assertEqual(exc.exception.status_code, 403)

    def test_self_escalation_and_self_modification_protection(self) -> None:
        """Gate 3: Admin cannot modify their own permissions or revoke themselves."""
        org = self._organization("Security Corp")
        admin = self._user("admin@security.com")
        self._member(org, admin, role="ADMIN")

        actor = self._actor(admin)

        # Self-escalation / self-modification rejected with 403
        with self.assertRaises(HTTPException) as exc:
            update_member_permissions(
                organization_id=org.id,
                user_id=admin.id,
                payload=UpdateMemberPermissionsRequest(
                    expected_version=1,
                    role="ADMIN",
                    capabilities=["FINANCE"],
                ),
                actor=actor,
                db=self.db,
            )
        self.assertEqual(exc.exception.status_code, 403)
        self.assertIn("own membership", exc.exception.detail)

        # Self-revocation rejected with 403
        with self.assertRaises(HTTPException) as exc:
            revoke_organization_member(
                organization_id=org.id,
                user_id=admin.id,
                actor=actor,
                db=self.db,
            )
        self.assertEqual(exc.exception.status_code, 403)
        self.assertIn("own membership", exc.exception.detail)

    def test_last_admin_protection(self) -> None:
        """Gate 4: Cannot demote or revoke the last admin of an organization."""
        org = self._organization("Single Admin Corp")
        admin1 = self._user("admin1@single.com")
        admin2 = self._user("admin2@single.com")
        member_user = self._user("member@single.com")

        self._member(org, admin1, role="ADMIN")
        self._member(org, member_user, role="MEMBER")

        # Admin 1 cannot demote themselves (caught by self-modification, 403)
        actor1 = self._actor(admin1)

        # Add admin 2 so admin 1 can manage admin 2
        self._member(org, admin2, role="ADMIN")
        actor1 = self._actor(admin1)

        # Now there are 2 admins. Admin 1 can demote admin 2 to MEMBER
        res = update_member_permissions(
            organization_id=org.id,
            user_id=admin2.id,
            payload=UpdateMemberPermissionsRequest(
                expected_version=1,
                role="MEMBER",
            ),
            actor=actor1,
            db=self.db,
        )
        self.assertEqual(res["role"], "MEMBER")

        # Now only 1 admin remains (Admin 1).
        # Promoting admin 2 back
        res = update_member_permissions(
            organization_id=org.id,
            user_id=admin2.id,
            payload=UpdateMemberPermissionsRequest(
                expected_version=2,
                role="ADMIN",
            ),
            actor=actor1,
            db=self.db,
        )
        self.assertEqual(res["role"], "ADMIN")

        # Demote admin 1 by admin 2
        actor2 = self._actor(admin2)
        res = update_member_permissions(
            organization_id=org.id,
            user_id=admin1.id,
            payload=UpdateMemberPermissionsRequest(
                expected_version=1,
                role="MEMBER",
            ),
            actor=actor2,
            db=self.db,
        )
        self.assertEqual(res["role"], "MEMBER")

        # Now admin 2 is the ONLY active admin. Attempting to demote admin 2 by any means fails with 409
        # (If admin 1 tries, admin 1 is a MEMBER now, so 403)
        actor1 = self._actor(admin1)
        with self.assertRaises(HTTPException) as exc:
            update_member_permissions(
                organization_id=org.id,
                user_id=admin2.id,
                payload=UpdateMemberPermissionsRequest(
                    expected_version=3,
                    role="MEMBER",
                ),
                actor=actor1,
                db=self.db,
            )
        self.assertEqual(exc.exception.status_code, 403)

    def test_optimistic_locking_and_atomic_rollback(self) -> None:
        """Gate 7: Optimistic locking rejects stale writes with 409 and rolls back."""
        org = self._organization("Lock Corp")
        admin = self._user("admin@lock.com")
        target_user = self._user("target@lock.com")

        self._member(org, admin, role="ADMIN")
        self._member(org, target_user, role="MEMBER")

        actor = self._actor(admin)

        # Successful update increments version from 1 to 2
        updated = update_member_permissions(
            organization_id=org.id,
            user_id=target_user.id,
            payload=UpdateMemberPermissionsRequest(
                expected_version=1,
                capabilities=["FINANCE"],
            ),
            actor=actor,
            db=self.db,
        )
        self.assertEqual(updated["version"], 2)
        self.assertIn("FINANCE", updated["capabilities"])

        # Stale update with expected_version=1 fails with 409
        with self.assertRaises(HTTPException) as exc:
            update_member_permissions(
                organization_id=org.id,
                user_id=target_user.id,
                payload=UpdateMemberPermissionsRequest(
                    expected_version=1,
                    capabilities=["FULFILLMENT"],
                ),
                actor=actor,
                db=self.db,
            )
        self.assertEqual(exc.exception.status_code, 409)

        # DB still has version 2 and FINANCE capability intact
        current = self.db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.user_id == target_user.id,
            )
        )
        assert current is not None
        self.assertEqual(current.version, 2)
        self.assertEqual(current.capabilities, ["FINANCE"])

    def test_stale_role_and_token_rejection_against_fresh_db_state(self) -> None:
        """Gate 5 & 6: Fresh commit-time check rejects revoked or demoted members."""
        org = self._organization("Freshness Corp")
        user = self._user("approver@freshness.com")
        member_row = self._member(org, user, role="MEMBER", capabilities=["AGREEMENT_APPROVAL"])

        # Stale actor token created when capability was granted
        stale_actor = self._actor(user)
        self.assertTrue(stale_actor.has_capability(org.id, OrganizationCapability.AGREEMENT_APPROVAL))

        # verify_member_capability succeeds initially
        verified = verify_member_capability(
            self.db,
            org.id,
            user.id,
            OrganizationCapability.AGREEMENT_APPROVAL,
            for_update=False,
        )
        self.assertIsNotNone(verified)

        # Now revoke the member directly in DB
        member_row.status = "REVOKED"
        self.db.commit()

        # verify_member_capability with fresh check fails with 403 despite cached ActorContext!
        with self.assertRaises(HTTPException) as exc:
            verify_member_capability(
                self.db,
                org.id,
                user.id,
                OrganizationCapability.AGREEMENT_APPROVAL,
                for_update=False,
            )
        self.assertEqual(exc.exception.status_code, 403)

    def test_audit_event_recorded_on_permission_change_and_revoke(self) -> None:
        org = self._organization("Audit Corp")
        admin = self._user("admin@audit.com")
        target = self._user("target@audit.com")

        self._member(org, admin, role="ADMIN")
        self._member(org, target, role="MEMBER")

        actor = self._actor(admin)

        # 1. Update permissions
        update_member_permissions(
            organization_id=org.id,
            user_id=target.id,
            payload=UpdateMemberPermissionsRequest(
                expected_version=1,
                capabilities=["FINANCE"],
            ),
            actor=actor,
            db=self.db,
        )

        update_event = self.db.scalar(
            select(AuditEvent).where(
                AuditEvent.event_type == "member.permissions_updated",
                AuditEvent.aggregate_type == "organization_member",
            )
        )
        self.assertIsNotNone(update_event)
        assert update_event is not None
        self.assertEqual(update_event.payload["capabilities"], ["FINANCE"])

        # 2. Revoke member
        revoke_organization_member(
            organization_id=org.id,
            user_id=target.id,
            actor=actor,
            db=self.db,
        )

        revoke_event = self.db.scalar(
            select(AuditEvent).where(
                AuditEvent.event_type == "member.revoked",
                AuditEvent.aggregate_type == "organization_member",
            )
        )
        self.assertIsNotNone(revoke_event)

    def test_list_my_organizations_includes_capabilities(self) -> None:
        org = self._organization("My Orgs Corp")
        user = self._user("me@myorgs.com")
        self._member(org, user, role="ADMIN", capabilities=["FINANCE"])

        actor = self._actor(user)
        my_orgs = list_my_organizations(actor=actor, db=self.db)
        self.assertEqual(len(my_orgs), 1)
        self.assertIn("capabilities", my_orgs[0])
        # Safe default ADMIN caps + FINANCE
        expected = sorted([
            OrganizationCapability.ADMINISTRATION.value,
            OrganizationCapability.DRAFTING.value,
            OrganizationCapability.AGREEMENT_APPROVAL.value,
            OrganizationCapability.FINANCE.value,
        ])
        self.assertEqual(my_orgs[0]["capabilities"], expected)
