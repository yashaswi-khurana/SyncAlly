"""Organizations and their user memberships, independent of persistence."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import OrganizationId, UserId


class OrganizationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class OrganizationMemberRole(StrEnum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class OrganizationMemberStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    REVOKED = "REVOKED"


@dataclass(slots=True)
class Organization:
    id: OrganizationId
    legal_name: str
    country_code: str
    created_at: datetime
    status: OrganizationStatus = OrganizationStatus.ACTIVE

    def __post_init__(self) -> None:
        if not self.legal_name.strip():
            raise InvariantViolation("Organization legal name is required")
        if (
            len(self.country_code) != 2
            or not self.country_code.isascii()
            or not self.country_code.isalpha()
        ):
            raise InvariantViolation("Organization country code must be two ASCII letters")
        self.country_code = self.country_code.upper()

    @property
    def is_active(self) -> bool:
        return self.status is OrganizationStatus.ACTIVE


@dataclass(slots=True)
class OrganizationMember:
    """A user's membership in one organization; identity is the ID pair."""

    organization_id: OrganizationId
    user_id: UserId
    created_at: datetime
    role: OrganizationMemberRole = OrganizationMemberRole.MEMBER
    status: OrganizationMemberStatus = OrganizationMemberStatus.ACTIVE

    @property
    def is_active(self) -> bool:
        return self.status is OrganizationMemberStatus.ACTIVE
