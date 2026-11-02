"""SQLAlchemy adapters for organizations and organization memberships."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
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
    OrganizationContact as DomainOrganizationContact,
)
from syncally.domain.organizations.organization import (
    OrganizationMember as DomainOrganizationMember,
)
from syncally.domain.organizations.organization import (
    OrganizationProfile as DomainOrganizationProfile,
)
from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import OrganizationId, UserId
from syncally.infrastructure.models import (
    Organization,
    OrganizationMember,
    OrganizationProfile,
)
from syncally.infrastructure.repositories._timestamps import as_utc


def _contact_to_dict(contact: DomainOrganizationContact) -> dict[str, Any]:
    return {
        "id": str(contact.id),
        "name": contact.name,
        "purpose": contact.purpose,
        "consent_obtained": contact.consent_obtained,
        "visibility": contact.visibility.value,
        "role_title": contact.role_title,
        "email": contact.email,
        "phone": contact.phone,
        "created_at": contact.created_at.isoformat() if contact.created_at else None,
        "updated_at": contact.updated_at.isoformat() if contact.updated_at else None,
    }


def _contact_to_domain(data: dict[str, Any]) -> DomainOrganizationContact:
    return DomainOrganizationContact(
        id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
        name=data["name"],
        purpose=data["purpose"],
        consent_obtained=bool(data.get("consent_obtained", True)),
        visibility=ContactVisibility(data.get("visibility", ContactVisibility.PRIVATE.value)),
        role_title=data.get("role_title"),
        email=data.get("email"),
        phone=data.get("phone"),
        created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
        updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
    )


def _profile_to_domain(row: OrganizationProfile) -> DomainOrganizationProfile:
    contacts = [_contact_to_domain(c) for c in (row.contacts or [])]
    return DomainOrganizationProfile(
        organization_id=OrganizationId(row.organization_id),
        capabilities=list(row.capabilities or []),
        products=list(row.products or []),
        regions=list(row.regions or []),
        contacts=contacts,
        verification_status=OrganizationVerificationStatus(row.verification_status),
        version=row.version,
        created_at=as_utc(row.created_at) if row.created_at else None,
        updated_at=as_utc(row.updated_at) if row.updated_at else None,
        updated_by_user_id=UserId(row.updated_by_user_id) if row.updated_by_user_id else None,
    )


def _organization_to_domain(row: Organization) -> DomainOrganization:
    return DomainOrganization(
        id=OrganizationId(row.id),
        legal_name=row.legal_name,
        country_code=row.country_code,
        created_at=as_utc(row.created_at),
        status=OrganizationStatus(row.status),
    )


def _membership_to_domain(row: OrganizationMember) -> DomainOrganizationMember:
    return DomainOrganizationMember(
        organization_id=OrganizationId(row.organization_id),
        user_id=UserId(row.user_id),
        created_at=as_utc(row.created_at),
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
            created_at=as_utc(organization.created_at),
        )
        self._db.add(row)
        self._db.flush()
        return _organization_to_domain(row)

    def get(self, organization_id: UUID) -> DomainOrganization | None:
        row = self._db.get(Organization, organization_id)
        return _organization_to_domain(row) if row is not None else None

    def get_profile(self, organization_id: UUID) -> DomainOrganizationProfile | None:
        row = self._db.get(OrganizationProfile, organization_id)
        return _profile_to_domain(row) if row is not None else None

    def save_profile(
        self,
        profile: DomainOrganizationProfile,
        expected_version: int | None = None,
    ) -> DomainOrganizationProfile:
        row = self._db.get(OrganizationProfile, profile.organization_id)
        serialized_contacts = [_contact_to_dict(c) for c in profile.contacts]

        if row is None:
            if expected_version not in (None, 0):
                raise InvariantViolation("Profile version conflict; stale write rejected")
            now = datetime.now(UTC)
            new_row = OrganizationProfile(
                organization_id=profile.organization_id,
                capabilities=profile.capabilities,
                products=profile.products,
                regions=profile.regions,
                contacts=serialized_contacts,
                verification_status=OrganizationVerificationStatus.UNVERIFIED.value,
                version=1,
                updated_by_user_id=profile.updated_by_user_id,
                created_at=as_utc(profile.created_at or now),
                updated_at=as_utc(profile.updated_at or now),
            )
            self._db.add(new_row)
            self._db.flush()
            return _profile_to_domain(new_row)

        if expected_version is not None and row.version != expected_version:
            raise InvariantViolation("Profile version conflict; stale write rejected")

        row.capabilities = profile.capabilities
        row.products = profile.products
        row.regions = profile.regions
        row.contacts = serialized_contacts
        row.verification_status = OrganizationVerificationStatus.UNVERIFIED.value
        row.version = row.version + 1
        row.updated_by_user_id = profile.updated_by_user_id
        row.updated_at = datetime.now(UTC)
        self._db.flush()
        return _profile_to_domain(row)


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
            created_at=as_utc(membership.created_at),
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
