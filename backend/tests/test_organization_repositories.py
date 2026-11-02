"""Database-backed tests for organization repository adapters."""

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syncally.domain.organizations.organization import (
    ContactVisibility,
    OrganizationMemberRole,
    OrganizationMemberStatus,
    OrganizationStatus,
    OrganizationVerificationStatus,
)
from syncally.domain.organizations.organization import (
    Organization as DomainOrganization,
)
from syncally.domain.organizations.organization import (
    OrganizationContact as DomainContact,
)
from syncally.domain.organizations.organization import (
    OrganizationMember as DomainMembership,
)
from syncally.domain.organizations.organization import (
    OrganizationProfile as DomainProfile,
)
from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import OrganizationId, UserId
from syncally.infrastructure.database import create_database_engine
from syncally.infrastructure.models import (
    Base,
    Organization,
    OrganizationMember,
    OrganizationProfile,
    User,
)
from syncally.infrastructure.repositories import (
    SqlAlchemyOrganizationMemberRepository,
    SqlAlchemyOrganizationRepository,
)


class OrganizationRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_database_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _seed(self) -> tuple[DomainOrganization, User]:
        organization = DomainOrganization(
            id=OrganizationId(uuid4()),
            legal_name="Buyer Co",
            country_code="us",
            created_at=datetime.now(UTC),
        )
        user = User(email="member@example.com", display_name="Member")
        organizations = SqlAlchemyOrganizationRepository(self.session)
        organizations.add(organization)
        self.session.add(user)
        self.session.commit()
        return organization, user

    def test_organization_and_membership_round_trip_as_domain_types(self) -> None:
        organization, user = self._seed()
        organizations = SqlAlchemyOrganizationRepository(self.session)
        memberships = SqlAlchemyOrganizationMemberRepository(self.session)
        membership = DomainMembership(
            organization_id=organization.id,
            user_id=UserId(user.id),
            created_at=datetime.now(UTC),
            role=OrganizationMemberRole.ADMIN,
            status=OrganizationMemberStatus.ACTIVE,
        )

        stored_membership = memberships.add(membership)
        self.session.commit()

        loaded_organization = organizations.get(organization.id)
        loaded_membership = memberships.get(organization.id, user.id)
        self.assertIsInstance(loaded_organization, DomainOrganization)
        self.assertEqual(loaded_organization.id, organization.id)
        self.assertEqual(loaded_organization.country_code, "US")
        self.assertEqual(loaded_organization.status, OrganizationStatus.ACTIVE)
        self.assertEqual(loaded_organization.created_at, organization.created_at)
        self.assertIsInstance(loaded_membership, DomainMembership)
        self.assertEqual(loaded_membership.organization_id, stored_membership.organization_id)
        self.assertEqual(loaded_membership.user_id, stored_membership.user_id)
        self.assertEqual(loaded_membership.created_at, membership.created_at)
        self.assertEqual(loaded_membership.created_at.utcoffset(), UTC.utcoffset(None))
        self.assertEqual(loaded_membership.role, OrganizationMemberRole.ADMIN)

    def test_missing_records_return_none_and_membership_reads_are_org_scoped(self) -> None:
        first, first_user = self._seed()
        second = DomainOrganization(
            id=OrganizationId(uuid4()),
            legal_name="Seller Co",
            country_code="CA",
            created_at=datetime.now(UTC),
        )
        organizations = SqlAlchemyOrganizationRepository(self.session)
        organizations.add(second)
        memberships = SqlAlchemyOrganizationMemberRepository(self.session)
        membership = DomainMembership(
            organization_id=second.id,
            user_id=UserId(first_user.id),
            created_at=datetime.now(UTC),
        )
        memberships.add(membership)
        self.session.commit()

        self.assertIsNone(organizations.get(uuid4()))
        self.assertIsNone(memberships.get(first.id, first_user.id))
        self.assertEqual(memberships.list_for_organization(first.id), [])
        loaded_memberships = memberships.list_for_organization(second.id)
        self.assertEqual(len(loaded_memberships), 1)
        self.assertEqual(loaded_memberships[0].organization_id, second.id)
        self.assertEqual(loaded_memberships[0].user_id, UserId(first_user.id))

    def test_duplicate_membership_fails_and_transaction_can_be_rolled_back(self) -> None:
        organization, user = self._seed()
        repository = SqlAlchemyOrganizationMemberRepository(self.session)
        membership = DomainMembership(
            organization_id=organization.id,
            user_id=UserId(user.id),
            created_at=datetime.now(UTC),
        )
        repository.add(membership)
        self.session.commit()

        with self.assertRaises(IntegrityError):
            repository.add(membership)
            self.session.flush()
        self.session.rollback()
        self.assertEqual(len(repository.list_for_organization(organization.id)), 1)

    def test_missing_membership_references_fail_at_database_boundary(self) -> None:
        repository = SqlAlchemyOrganizationMemberRepository(self.session)
        membership = DomainMembership(
            organization_id=OrganizationId(uuid4()),
            user_id=UserId(uuid4()),
            created_at=datetime.now(UTC),
        )

        with self.assertRaises(IntegrityError):
            repository.add(membership)
            self.session.flush()
        self.session.rollback()
        self.assertEqual(self.session.query(OrganizationMember).count(), 0)

    def test_organization_profile_lifecycle_and_optimistic_locking(self) -> None:
        org, user = self._seed()
        repo = SqlAlchemyOrganizationRepository(self.session)

        # 1. Missing profile returns None
        self.assertIsNone(repo.get_profile(org.id))

        # 2. Save profile initially creates version 1
        contact_id = uuid4()
        contact = DomainContact(
            id=contact_id,
            name="Alice Lead",
            purpose="Commercial",
            consent_obtained=True,
            visibility=ContactVisibility.PARTICIPANTS,
            email="alice@buyer.com",
            phone="+1-555-0199",
        )
        profile = DomainProfile(
            organization_id=org.id,
            capabilities=["Freight", "Inspection"],
            products=["Wheat", "Barley"],
            regions=["US", "CA"],
            contacts=[contact],
            updated_by_user_id=UserId(user.id),
        )

        created = repo.save_profile(profile, expected_version=None)
        self.session.commit()

        self.assertEqual(created.version, 1)
        self.assertEqual(created.capabilities, ["Freight", "Inspection"])
        self.assertEqual(created.products, ["Wheat", "Barley"])
        self.assertEqual(created.regions, ["US", "CA"])
        self.assertEqual(len(created.contacts), 1)
        self.assertEqual(created.contacts[0].id, contact_id)
        self.assertEqual(created.contacts[0].visibility, ContactVisibility.PARTICIPANTS)
        self.assertEqual(created.verification_status, OrganizationVerificationStatus.UNVERIFIED)

        # 3. Optimistic locking: update with matching expected_version increments version to 2
        profile.capabilities = ["Freight", "Inspection", "Warehousing"]
        updated = repo.save_profile(profile, expected_version=1)
        self.session.commit()
        self.assertEqual(updated.version, 2)
        self.assertIn("Warehousing", updated.capabilities)

        # 4. Optimistic locking: stale write with wrong expected_version raises InvariantViolation
        with self.assertRaises(InvariantViolation):
            repo.save_profile(profile, expected_version=1)

        # 5. Profile is cascade deleted when organization is removed
        org_row = self.session.get(Organization, org.id)
        self.assertIsNotNone(org_row)
        self.session.delete(org_row)
        self.session.commit()
        self.assertIsNone(self.session.get(OrganizationProfile, org.id))
        self.assertIsNone(repo.get_profile(org.id))


if __name__ == "__main__":
    unittest.main()
