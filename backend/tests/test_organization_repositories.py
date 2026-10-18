"""Database-backed tests for organization repository adapters."""

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.domain.organizations.organization import (
    Organization as DomainOrganization,
)
from syncally.domain.organizations.organization import (
    OrganizationMember as DomainMembership,
)
from syncally.domain.organizations.organization import (
    OrganizationMemberRole,
    OrganizationMemberStatus,
    OrganizationStatus,
)
from syncally.domain.shared.identifiers import OrganizationId, UserId
from syncally.infrastructure.models import Base, OrganizationMember, User
from syncally.infrastructure.repositories import (
    SqlAlchemyOrganizationMemberRepository,
    SqlAlchemyOrganizationRepository,
)


class OrganizationRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _record) -> None:
            connection.execute("PRAGMA foreign_keys=ON")

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
        self.assertIsInstance(loaded_membership, DomainMembership)
        self.assertEqual(loaded_membership.organization_id, stored_membership.organization_id)
        self.assertEqual(loaded_membership.user_id, stored_membership.user_id)
        self.assertEqual(loaded_membership.created_at.replace(tzinfo=UTC), membership.created_at)
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


if __name__ == "__main__":
    unittest.main()
