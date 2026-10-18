"""SQLAlchemy adapters for organizations and organization memberships."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from syncally.domain.organizations.organization import (
    Organization as DomainOrganization,
)
from syncally.domain.organizations.organization import (
    OrganizationMember as DomainOrganizationMember,
)
from syncally.domain.organizations.organization import (
    OrganizationMemberRole,
    OrganizationMemberStatus,
    OrganizationStatus,
)
from syncally.domain.shared.identifiers import OrganizationId, UserId
from syncally.infrastructure.models import Organization, OrganizationMember


def _organization_to_domain(row: Organization) -> DomainOrganization:
    return DomainOrganization(
        id=OrganizationId(row.id),
        legal_name=row.legal_name,
        country_code=row.country_code,
        created_at=row.created_at,
        status=OrganizationStatus(row.status),
    )


def _membership_to_domain(row: OrganizationMember) -> DomainOrganizationMember:
    return DomainOrganizationMember(
        organization_id=OrganizationId(row.organization_id),
        user_id=UserId(row.user_id),
        created_at=row.created_at,
        role=OrganizationMemberRole(row.role),
        status=OrganizationMemberStatus(row.status),
    )


class SqlAlchemyOrganizationRepository:
    """Create and retrieve organizations using a caller-owned session."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, organization: DomainOrganization) -> DomainOrganization:
        row = Organization(
            id=organization.id,
            legal_name=organization.legal_name,
            country_code=organization.country_code,
            status=organization.status.value,
            created_at=organization.created_at,
        )
        self._db.add(row)
        self._db.flush()
        return _organization_to_domain(row)

    def get(self, organization_id: UUID) -> DomainOrganization | None:
        row = self._db.get(Organization, organization_id)
        return _organization_to_domain(row) if row is not None else None


class SqlAlchemyOrganizationMemberRepository:
    """Create and retrieve memberships, with reads scoped to one organization."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, membership: DomainOrganizationMember) -> DomainOrganizationMember:
        row = OrganizationMember(
            organization_id=membership.organization_id,
            user_id=membership.user_id,
            role=membership.role.value,
            status=membership.status.value,
            created_at=membership.created_at,
        )
        self._db.add(row)
        self._db.flush()
        return _membership_to_domain(row)

    def get(self, organization_id: UUID, user_id: UUID) -> DomainOrganizationMember | None:
        row = self._db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
        )
        return _membership_to_domain(row) if row is not None else None

    def list_for_organization(self, organization_id: UUID) -> list[DomainOrganizationMember]:
        rows = self._db.scalars(
            select(OrganizationMember)
            .where(OrganizationMember.organization_id == organization_id)
            .order_by(OrganizationMember.created_at, OrganizationMember.user_id)
        )
        return [_membership_to_domain(row) for row in rows]
