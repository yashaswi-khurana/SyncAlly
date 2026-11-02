"""Organizations and their user memberships, independent of persistence."""

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import OrganizationId, UserId

_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _normalize_string(val: str) -> str:
    return unicodedata.normalize("NFC", val.strip())


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


class OrganizationVerificationStatus(StrEnum):
    UNVERIFIED = "UNVERIFIED"


class ContactVisibility(StrEnum):
    PRIVATE = "PRIVATE"
    PARTICIPANTS = "PARTICIPANTS"


@dataclass(slots=True)
class OrganizationContact:
    id: UUID
    name: str
    purpose: str
    consent_obtained: bool = True
    visibility: ContactVisibility = ContactVisibility.PRIVATE
    role_title: str | None = None
    email: str | None = None
    phone: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self.name = _normalize_string(self.name)
        if not self.name:
            raise InvariantViolation("Contact name is required and cannot be empty")
        self.purpose = _normalize_string(self.purpose)
        if not self.purpose:
            raise InvariantViolation("Contact purpose is required and cannot be empty")
        if not self.consent_obtained:
            raise InvariantViolation("Contact consent must be obtained")
        if not isinstance(self.visibility, ContactVisibility):
            try:
                self.visibility = ContactVisibility(self.visibility)
            except ValueError as exc:
                raise InvariantViolation(f"Invalid contact visibility: {self.visibility}") from exc
        if self.role_title is not None:
            cleaned_role = _normalize_string(self.role_title)
            self.role_title = cleaned_role if cleaned_role else None
        if self.email is not None:
            cleaned_email = _normalize_string(self.email).lower()
            if cleaned_email:
                if not _EMAIL_PATTERN.match(cleaned_email):
                    raise InvariantViolation(f"Invalid contact email format: {self.email}")
                self.email = cleaned_email
            else:
                self.email = None
        if self.phone is not None:
            cleaned_phone = _normalize_string(self.phone)
            self.phone = cleaned_phone if cleaned_phone else None
        if not self.email and not self.phone:
            raise InvariantViolation("Contact requires at least one channel (email or phone)")


@dataclass(slots=True)
class OrganizationProfile:
    organization_id: OrganizationId
    capabilities: list[str] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    contacts: list[OrganizationContact] = field(default_factory=list)
    verification_status: OrganizationVerificationStatus = OrganizationVerificationStatus.UNVERIFIED
    version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
    updated_by_user_id: UserId | None = None

    def __post_init__(self) -> None:
        if self.verification_status != OrganizationVerificationStatus.UNVERIFIED:
            raise InvariantViolation("Organization profile verification status must be UNVERIFIED")
        if self.version < 1:
            raise InvariantViolation("Organization profile version must be at least 1")
        if len(self.capabilities) > 50:
            raise InvariantViolation("Organization profile capabilities cannot exceed 50 items")
        if len(self.products) > 50:
            raise InvariantViolation("Organization profile products cannot exceed 50 items")
        if len(self.regions) > 50:
            raise InvariantViolation("Organization profile regions cannot exceed 50 items")
        if len(self.contacts) > 20:
            raise InvariantViolation("Organization profile contacts cannot exceed 20 items")

        cleaned_caps: list[str] = []
        seen_caps: set[str] = set()
        for item in self.capabilities:
            cleaned = _normalize_string(item)
            if not cleaned:
                continue
            if len(cleaned) > 200:
                raise InvariantViolation(f"Capability exceeds maximum length of 200 characters: '{cleaned[:20]}...'")
            key = cleaned.casefold()
            if key not in seen_caps:
                seen_caps.add(key)
                cleaned_caps.append(cleaned)
        if len(cleaned_caps) > 50:
            raise InvariantViolation("Organization profile capabilities cannot exceed 50 items")
        self.capabilities = cleaned_caps

        cleaned_prods: list[str] = []
        seen_prods: set[str] = set()
        for item in self.products:
            cleaned = _normalize_string(item)
            if not cleaned:
                continue
            if len(cleaned) > 200:
                raise InvariantViolation(f"Product exceeds maximum length of 200 characters: '{cleaned[:20]}...'")
            key = cleaned.casefold()
            if key not in seen_prods:
                seen_prods.add(key)
                cleaned_prods.append(cleaned)
        if len(cleaned_prods) > 50:
            raise InvariantViolation("Organization profile products cannot exceed 50 items")
        self.products = cleaned_prods

        cleaned_regions: list[str] = []
        seen_regions: set[str] = set()
        for item in self.regions:
            code = _normalize_string(item).upper()
            if len(code) != 2 or not code.isascii() or not code.isalpha():
                raise InvariantViolation(f"Invalid region country code '{item}'; must be two ASCII letters")
            if code not in seen_regions:
                seen_regions.add(code)
                cleaned_regions.append(code)
        if len(cleaned_regions) > 50:
            raise InvariantViolation("Organization profile regions cannot exceed 50 items")
        self.regions = cleaned_regions

        if len(self.contacts) > 20:
            raise InvariantViolation("Organization profile contacts cannot exceed 20 items")

        seen_emails: set[str] = set()
        seen_phones: set[str] = set()
        for contact in self.contacts:
            if contact.email:
                email_key = contact.email.casefold()
                if email_key in seen_emails:
                    raise InvariantViolation(f"Duplicate contact email '{contact.email}' across contacts in profile")
                seen_emails.add(email_key)
            if contact.phone:
                phone_key = contact.phone.strip()
                if phone_key in seen_phones:
                    raise InvariantViolation(f"Duplicate contact phone '{contact.phone}' across contacts in profile")
                seen_phones.add(phone_key)
        self.contacts = list(self.contacts)


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
