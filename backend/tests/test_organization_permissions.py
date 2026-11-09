"""Test granular organization permissions, capability matrix, and security boundaries."""

import unittest
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.organizations import (
    AddOrganizationMemberRequest,
    CreateOrganizationRequest,
    DealAssignmentUpdate,
    UpdateMemberPermissionsRequest,
    _compute_effective_capabilities,
    add_organization_member,
    create_organization,
    list_my_organizations,
    list_organization_members,
    repair_organization_finance_route,
    revoke_organization_member,
    update_member_deal_assignments,
    update_member_permissions,
)
from syncally.application.identity import ActorContext
from syncally.domain.organizations.organization import (
    OrganizationCapability,
    OrganizationMemberRole,
    resolve_effective_capabilities,
)
from syncally.domain.organizations.organization import (
    OrganizationMember as DomainOrganizationMember,
)
from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import OrganizationId, UserId
from syncally.infrastructure.identity import resolve_actor, verify_member_capability
from syncally.infrastructure.models import (
    AuditEvent,
    Base,
    Deal,
    DealAssignment,
    Organization,
    OrganizationMember,
    User,
)


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

    def test_resolve_effective_capabilities_matrix_and_unrecognized_roles(self) -> None:
        """Verify centralized capability resolution and strict role validation."""
        # Valid ADMIN role defaults
        admin_caps = resolve_effective_capabilities(OrganizationMemberRole.ADMIN)
        self.assertEqual(
            admin_caps,
            frozenset({
                OrganizationCapability.ADMINISTRATION,
                OrganizationCapability.DRAFTING,
                OrganizationCapability.AGREEMENT_APPROVAL,
            }),
        )

        # Valid string "ADMIN" role with assigned capability
        admin_str_caps = resolve_effective_capabilities("ADMIN", ["FINANCE"])
        self.assertEqual(
            admin_str_caps,
            frozenset({
                OrganizationCapability.ADMINISTRATION,
                OrganizationCapability.DRAFTING,
                OrganizationCapability.AGREEMENT_APPROVAL,
                OrganizationCapability.FINANCE,
            }),
        )

        # Valid MEMBER role defaults
        member_caps = resolve_effective_capabilities(OrganizationMemberRole.MEMBER)
        self.assertEqual(member_caps, frozenset({OrganizationCapability.DRAFTING}))

        # Valid string "MEMBER" role with assigned capability and duplicate/invalid items
        member_str_caps = resolve_effective_capabilities(
            "MEMBER", ["FINANCE", "NOT_A_CAP", OrganizationCapability.FULFILLMENT]
        )
        self.assertEqual(
            member_str_caps,
            frozenset({
                OrganizationCapability.DRAFTING,
                OrganizationCapability.FINANCE,
                OrganizationCapability.FULFILLMENT,
            }),
        )

        # Unrecognized roles return empty frozenset without including assigned capabilities
        for invalid_role in ("UNKNOWN", "OBSERVER", "AUDITOR", "", None, 12345):
            res = resolve_effective_capabilities(
                invalid_role,  # type: ignore[arg-type]
                ["FINANCE", "ADMINISTRATION", OrganizationCapability.FULFILLMENT],
            )
            self.assertEqual(
                res,
                frozenset(),
                f"Expected empty frozenset for invalid role {invalid_role!r}, got {res!r}",
            )

    def test_compute_effective_capabilities_helper(self) -> None:
        """Verify _compute_effective_capabilities returns sorted string lists and rejects unknown roles."""
        self.assertEqual(
            _compute_effective_capabilities("ADMIN", None),
            ["ADMINISTRATION", "AGREEMENT_APPROVAL", "DRAFTING"],
        )
        self.assertEqual(
            _compute_effective_capabilities("MEMBER", ["FINANCE"]),
            ["DRAFTING", "FINANCE"],
        )
        self.assertEqual(
            _compute_effective_capabilities("INVALID_ROLE", ["FINANCE", "ADMINISTRATION"]),
            [],
        )

    def test_resolve_actor_and_verify_member_capability_with_unrecognized_role(self) -> None:
        """Verify unrecognized roles in DB are denied all capabilities and access."""
        org = self._organization("Bogus Org")
        user = self._user("bogus@example.com")
        self._member(org, user, role="CORRUPTED_ROLE", capabilities=["FINANCE", "ADMINISTRATION"])

        actor = resolve_actor(self.db, user.id)
        self.assertIsNotNone(actor)
        assert actor is not None
        self.assertEqual(actor.capabilities_by_organization.get(org.id), frozenset())
        self.assertNotIn(org.id, actor.roles_by_organization)
        self.assertFalse(actor.has_capability(org.id, OrganizationCapability.FINANCE))
        self.assertFalse(actor.has_capability(org.id, OrganizationCapability.DRAFTING))

        # verify_member_capability rejects with 403
        with self.assertRaises(HTTPException) as ctx:
            verify_member_capability(self.db, org.id, user.id, OrganizationCapability.DRAFTING)
        self.assertEqual(ctx.exception.status_code, 403)

        with self.assertRaises(HTTPException) as ctx:
            verify_member_capability(self.db, org.id, user.id, OrganizationCapability.FINANCE)
        self.assertEqual(ctx.exception.status_code, 403)

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

    def test_revocation_clears_capabilities_and_reactivation_resets_grants(self) -> None:
        """Verify revoking a member clears capabilities and incrementing version; reactivation resets grants."""
        org = self._organization("Reactivation Corp")
        admin = self._user("admin@reactivation.com")
        target = self._user("target@reactivation.com")

        self._member(org, admin, role="ADMIN")
        target_row = self._member(org, target, role="MEMBER", capabilities=["FINANCE", "AGREEMENT_APPROVAL"])
        self.assertEqual(target_row.version, 1)
        self.assertEqual(target_row.capabilities, ["FINANCE", "AGREEMENT_APPROVAL"])

        admin_actor = self._actor(admin)

        # 1. Revoke membership
        revoke_organization_member(
            organization_id=org.id,
            user_id=target.id,
            actor=admin_actor,
            db=self.db,
        )

        self.db.refresh(target_row)
        self.assertEqual(target_row.status, "REVOKED")
        self.assertEqual(target_row.capabilities, [])
        self.assertEqual(target_row.version, 2)

        # 2. Reactivate membership via add_organization_member
        add_result = add_organization_member(
            organization_id=org.id,
            payload=AddOrganizationMemberRequest(email=target.email),
            actor=admin_actor,
            db=self.db,
        )
        self.assertEqual(add_result["role"], "MEMBER")

        self.db.refresh(target_row)
        self.assertEqual(target_row.status, "ACTIVE")
        self.assertEqual(target_row.role, "MEMBER")
        self.assertEqual(target_row.capabilities, [])
        self.assertEqual(target_row.version, 3)

        # Target now has ONLY default MEMBER capabilities (DRAFTING) - prior grants are completely cleared!
        resolved = resolve_actor(self.db, target.id)
        self.assertEqual(
            resolved.capabilities_by_organization[org.id],
            frozenset({OrganizationCapability.DRAFTING}),
        )

    def test_repair_organization_finance_membership_supported_way(self) -> None:
        """Provide a supported way for existing organizations to repair finance membership."""
        org = self._organization("Repair Corp")
        admin = self._user("admin@repair.com")
        member = self._user("member@repair.com")

        # Admin created with NO capabilities (legacy/existing state)
        admin_row = self._member(org, admin, role="ADMIN", capabilities=[])
        self._member(org, member, role="MEMBER", capabilities=[])
        self.assertEqual(admin_row.capabilities, [])
        self.assertEqual(admin_row.version, 1)

        admin_actor = self._actor(admin)
        member_actor = self._actor(member)

        # 1. Non-admin cannot repair finance (403)
        with self.assertRaises(HTTPException) as exc:
            repair_organization_finance_route(
                organization_id=org.id,
                actor=member_actor,
                db=self.db,
            )
        self.assertEqual(exc.exception.status_code, 403)

        # 2. General self-modification via PATCH remains strictly forbidden (403)
        with self.assertRaises(HTTPException) as exc:
            update_member_permissions(
                organization_id=org.id,
                user_id=admin.id,
                payload=UpdateMemberPermissionsRequest(expected_version=1, capabilities=["FINANCE"]),
                actor=admin_actor,
                db=self.db,
            )
        self.assertEqual(exc.exception.status_code, 403)
        self.assertIn("Cannot modify your own", exc.exception.detail)

        # 3. Admin repairs finance membership via supported route
        repair_res = repair_organization_finance_route(
            organization_id=org.id,
            actor=admin_actor,
            db=self.db,
        )
        self.assertEqual(repair_res["status"], "repaired")

        self.db.refresh(admin_row)
        self.assertEqual(admin_row.capabilities, ["FINANCE"])
        self.assertEqual(admin_row.version, 2)

        # Verify durable audit event was recorded
        audit = self.db.scalar(
            select(AuditEvent).where(
                AuditEvent.event_type == "member.finance_repaired",
                AuditEvent.aggregate_id == admin_row.id,
            )
        )
        self.assertIsNotNone(audit)

        # 4. Attempting to repair again when organization ALREADY has finance member returns 409 Conflict
        with self.assertRaises(HTTPException) as exc:
            repair_organization_finance_route(
                organization_id=org.id,
                actor=admin_actor,
                db=self.db,
            )
        self.assertEqual(exc.exception.status_code, 409)

    def test_create_organization_provisions_finance_for_creator(self) -> None:
        """Onboarding creates organization and provisions FINANCE for initial supported actor."""
        creator = self._user("founder@startup.com")
        actor = self._actor(creator)

        result = create_organization(
            payload=CreateOrganizationRequest(legal_name="Startup Inc", country_code="US"),
            actor=actor,
            db=self.db,
        )
        created_org_id = UUID(result["id"])

        member = self.db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == created_org_id,
                OrganizationMember.user_id == creator.id,
            )
        )
        self.assertIsNotNone(member)
        assert member is not None
        self.assertEqual(member.role, "ADMIN")
        self.assertTrue(member.is_owner)
        self.assertEqual(member.role_bundles, [])
        self.assertEqual(member.permissions, [])

    def test_org_admin_can_delegate_ordinary_bundles_but_not_admin_or_protected_permission(self) -> None:
        org = self._organization("Delegation Corp")
        counterparty = self._organization("Counterparty Corp")
        admin = self._user("delegating-admin@example.com")
        owner = self._user("delegating-owner@example.com")
        recipient = self._user("delegated-member@example.com")
        admin_row = self._member(org, admin)
        admin_row.role_bundles = ["ORG_ADMIN"]
        owner_row = self._member(org, owner)
        owner_row.is_owner = True
        recipient_row = self._member(org, recipient)
        deal = Deal(buyer_organization_id=org.id, seller_organization_id=counterparty.id, status="OPEN", version=1)
        self.db.add(deal)
        self.db.commit()

        result = update_member_permissions(
            org.id,
            recipient.id,
            UpdateMemberPermissionsRequest(
                expected_version=recipient_row.version,
                role_bundles=["FINANCE", "APPROVER"],
                permissions=[],
                deal_ids=[deal.id],
            ),
            self._actor(admin),
            self.db,
        )
        self.assertEqual(result["role_bundles"], ["APPROVER", "FINANCE"])
        self.assertEqual(result["deal_ids"], [deal.id])

        with self.assertRaises(HTTPException) as custom_admin:
            update_member_permissions(
                org.id,
                recipient.id,
                UpdateMemberPermissionsRequest(
                    expected_version=2,
                    role_bundles=["FINANCE"],
                    permissions=["org.members.manage"],
                    deal_ids=[deal.id],
                ),
                self._actor(admin),
                self.db,
            )
        self.assertEqual(custom_admin.exception.status_code, 422)

        with self.assertRaises(HTTPException) as admin_bundle:
            update_member_permissions(
                org.id,
                recipient.id,
                UpdateMemberPermissionsRequest(
                    expected_version=2,
                    role_bundles=["ORG_ADMIN"],
                    permissions=[],
                    deal_ids=[deal.id],
                ),
                self._actor(admin),
                self.db,
            )
        self.assertEqual(admin_bundle.exception.status_code, 403)

        owner_result = update_member_permissions(
            org.id,
            recipient.id,
            UpdateMemberPermissionsRequest(
                expected_version=2,
                role_bundles=["ORG_ADMIN"],
                permissions=[],
                deal_ids=[deal.id],
            ),
            self._actor(owner),
            self.db,
        )
        self.assertEqual(owner_result["role_bundles"], ["ORG_ADMIN"])

        direct_user = self._user("direct-grant@example.com")
        added = add_organization_member(
            org.id,
            AddOrganizationMemberRequest(
                email=direct_user.email,
                role_bundles=["FINANCE"],
                deal_ids=[deal.id],
            ),
            self._actor(admin),
            self.db,
        )
        self.assertEqual(added["user_id"], str(direct_user.id))
        direct_row = self.db.scalar(select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == direct_user.id,
        ))
        self.assertEqual(direct_row.role_bundles, ["FINANCE"])
        self.assertEqual(self.db.scalar(select(DealAssignment.deal_id).where(
            DealAssignment.organization_id == org.id,
            DealAssignment.user_id == direct_user.id,
            DealAssignment.status == "ACTIVE",
        )), deal.id)

    def test_deal_manager_assignment_write_is_limited_to_its_delegated_deals(self) -> None:
        org = self._organization("Deal Manager Corp")
        counterparty = self._organization("Deal Manager Partner")
        manager = self._user("deal-manager@example.com")
        recipient = self._user("deal-assignee@example.com")
        manager_row = self._member(org, manager)
        manager_row.role_bundles = ["DEAL_MANAGER"]
        target_row = self._member(org, recipient)
        assigned_deal = Deal(buyer_organization_id=org.id, seller_organization_id=counterparty.id, status="OPEN", version=1)
        unrelated_deal = Deal(buyer_organization_id=org.id, seller_organization_id=counterparty.id, status="OPEN", version=1)
        self.db.add_all([assigned_deal, unrelated_deal])
        self.db.flush()
        self.db.add_all([
            DealAssignment(organization_id=org.id, deal_id=assigned_deal.id, user_id=manager.id, status="ACTIVE"),
            DealAssignment(organization_id=org.id, deal_id=unrelated_deal.id, user_id=recipient.id, status="ACTIVE"),
        ])
        self.db.commit()

        with self.assertRaises(HTTPException) as overreach:
            update_member_deal_assignments(
                org.id,
                recipient.id,
                DealAssignmentUpdate(expected_version=target_row.version, deal_ids=[unrelated_deal.id]),
                self._actor(manager),
                self.db,
            )
        self.assertEqual(overreach.exception.status_code, 403)

        result = update_member_deal_assignments(
            org.id,
            recipient.id,
            DealAssignmentUpdate(expected_version=target_row.version, deal_ids=[assigned_deal.id]),
            self._actor(manager),
            self.db,
        )
        self.assertEqual(set(result["deal_ids"]), {str(assigned_deal.id), str(unrelated_deal.id)})
        self.assertEqual(result["version"], target_row.version)
        self.assertEqual(result["version"], 2)
