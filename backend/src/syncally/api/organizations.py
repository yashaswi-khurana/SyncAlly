"""Organization creation and initial membership setup endpoints."""

import logging
import unicodedata
from datetime import UTC, datetime, timedelta
from ipaddress import ip_address
from typing import Annotated, Any, Literal
from urllib.parse import quote, urlsplit
from uuid import UUID, uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import ColumnElement, String, cast, func, or_, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from syncally.api.auth import (
    _encode_access_token,
    bearer_scheme,
    create_refresh_token,
    get_current_actor,
)
from syncally.application.identity import ActorContext
from syncally.application.passwords import hash_password, verify_password
from syncally.config import GmailSettings, settings
from syncally.domain.deals.deal import Deal as DomainDeal
from syncally.domain.organizations.approval_routing import ApprovalRoutingMode
from syncally.domain.organizations.approval_routing import (
    ApprovalRoutingPolicy as DomainApprovalRoutingPolicy,
)
from syncally.domain.organizations.authorization import (
    OWNER_ONLY_BUNDLES,
    OWNER_ONLY_PERMISSIONS,
    expand_grants,
    validate_grants,
)
from syncally.domain.organizations.organization import (
    ContactVisibility,
    OrganizationVerificationStatus,
    resolve_effective_capabilities,
)
from syncally.domain.organizations.organization import (
    OrganizationContact as DomainOrganizationContact,
)
from syncally.domain.organizations.organization import (
    OrganizationProfile as DomainOrganizationProfile,
)
from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import DealId, OrganizationId, UserId
from syncally.infrastructure.counterparty_onboarding import lock_deal
from syncally.infrastructure.database import get_db
from syncally.infrastructure.demo_lifecycle import lock_demo_deal_creation
from syncally.infrastructure.gmail import GmailSMTPInvitationNotifier, InvitationEmailDeliveryError
from syncally.infrastructure.models import (
    AgreementVersion,
    AuditEvent,
    Conversation,
    CounterpartyOnboarding,
    Deal,
    DealAssignment,
    Message,
    NegotiationSession,
    Organization,
    OrganizationMember,
    OrganizationProfile,
    Proposal,
    User,
)
from syncally.infrastructure.repositories._timestamps import as_utc
from syncally.infrastructure.repositories.approval_routing import (
    SqlAlchemyApprovalRoutingPolicyRepository,
)
from syncally.infrastructure.repositories.deals import SqlAlchemyDealRepository
from syncally.infrastructure.repositories.organizations import (
    SqlAlchemyOrganizationRepository,
)
from syncally.operations import correlation_id

router = APIRouter(tags=["organizations"])
org_router = APIRouter(prefix="/organizations", tags=["organizations"])


def _public_invitation_base_url() -> str:
    """Allow loopback only for local testing; deployed invites must use public HTTPS."""
    value = settings.public_frontend_url
    if not value:
        raise HTTPException(status_code=503, detail="A public invitation URL is not configured.")
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="Configure a public HTTPS invitation URL.") from exc
    if (
        not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise HTTPException(status_code=503, detail="Configure a public HTTPS invitation URL.")
    normalized_host = hostname.lower().rstrip(".")
    local_environment = settings.app_env.lower() in {"development", "test"}
    is_loopback = normalized_host == "localhost"
    try:
        is_loopback = is_loopback or ip_address(normalized_host).is_loopback
    except ValueError:
        pass
    if local_environment and is_loopback:
        if parsed.scheme not in {"http", "https"}:
            raise HTTPException(status_code=503, detail="Configure a local HTTP or HTTPS invitation URL.")
        return value.rstrip("/")

    if parsed.scheme != "https":
        raise HTTPException(status_code=503, detail="Configure a public HTTPS invitation URL.")
    local_suffixes = (".localhost", ".local", ".internal", ".test", ".invalid", ".example")
    try:
        address = ip_address(normalized_host)
    except ValueError:
        if (
            normalized_host == "localhost"
            or normalized_host.endswith(local_suffixes)
            or "." not in normalized_host
        ):
            raise HTTPException(status_code=503, detail="Configure a public HTTPS invitation URL.")
    else:
        if not address.is_global or address.is_multicast or getattr(address, "is_site_local", False):
            raise HTTPException(status_code=503, detail="Configure a public HTTPS invitation URL.")
    return value.rstrip("/")


def _invitation_delivery() -> tuple[GmailSMTPInvitationNotifier | None, str, str | None]:
    base_url = _public_invitation_base_url()
    config = GmailSettings()
    username = config.gmail_smtp_username.strip()
    password = config.gmail_app_password.get_secret_value()
    if not username or not password.strip():
        return None, base_url, "Email delivery is not configured. Set the Gmail SMTP sender credentials."
    try:
        notifier = GmailSMTPInvitationNotifier(
            username,
            password,
            config.gmail_from_email.strip() or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="Invitation email sender configuration is invalid.") from exc
    return notifier, base_url, None


def _invite_url(base_url: str, token: str) -> str:
    return f"{base_url}/#/invite?token={quote(token, safe='')}"


def _send_invitation_email(send_email: Any, *args: str) -> tuple[bool, str | None]:
    if send_email is None:
        return False, "Email delivery is not configured. Set the Gmail SMTP sender credentials."
    try:
        send_email(*args)
    except InvitationEmailDeliveryError:
        logging.getLogger(__name__).warning("Invitation email delivery failed")
        return False, "The invitation was created, but its email could not be delivered. Copy the link and try again later."
    return True, None


def get_optional_actor(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> ActorContext | None:
    """Resolve actor if valid credentials are supplied, otherwise return None."""
    try:
        return get_current_actor(request, credentials, db)
    except HTTPException:
        return None


class CreateOrganizationRequest(BaseModel):
    legal_name: str = Field(min_length=1, max_length=200)
    country_code: str = Field(pattern=r"^[A-Z]{2}$")

    @field_validator("legal_name", mode="before")
    @classmethod
    def strip_legal_name(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("country_code", mode="before")
    @classmethod
    def normalize_country_code(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value


class AddOrganizationMemberRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    role_bundles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    deal_ids: list[UUID] = Field(default_factory=list)


class OrganizationMemberResponse(BaseModel):
    user_id: UUID
    email: str
    display_name: str | None = None
    role: str
    status: str
    capabilities: list[str] = Field(default_factory=list)
    assigned_capabilities: list[str] = Field(default_factory=list)
    role_bundles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    deal_ids: list[UUID] = Field(default_factory=list)
    is_owner: bool = False
    version: int


class UpdateMemberPermissionsRequest(BaseModel):
    expected_version: int = Field(ge=1)
    role: str | None = Field(default=None, pattern=r"^(ADMIN|MEMBER)$")
    capabilities: list[str] | None = None
    role_bundles: list[str] | None = None
    permissions: list[str] | None = None
    deal_ids: list[UUID] | None = None


class DealAssignmentUpdate(BaseModel):
    expected_version: int = Field(ge=1)
    deal_ids: list[UUID] = Field(default_factory=list)


class CreateInvitationRequest(BaseModel):
    deal_id: UUID | None = None
    role: str = Field(default="MEMBER", pattern=r"^(ADMIN|MEMBER)$")
    role_bundles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    deal_ids: list[UUID] = Field(default_factory=list)
    recipient_email: str | None = Field(default=None, max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

    @field_validator("recipient_email", mode="before")
    @classmethod
    def normalize_recipient(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class CreateCounterpartyInvitationRequest(CreateOrganizationRequest):
    buyer_organization_id: UUID | None = None
    inviting_organization_id: UUID | None = None
    inviter_party: Literal["BUYER", "SELLER"] = "BUYER"
    recipient_email: str = Field(max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    display_name: str | None = Field(default=None, max_length=160)

    @field_validator("recipient_email", mode="before")
    @classmethod
    def normalize_recipient(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class InvitationResponse(BaseModel):
    invitation_id: UUID | None = None
    token: str
    invite_url: str
    organization_id: UUID
    organization_legal_name: str
    deal_id: UUID | None = None
    role: str
    expires_at: str
    kind: str | None = None
    email_sent: bool = False
    email_error: str | None = None


class CounterpartyInvitationResponse(InvitationResponse):
    pending_counterparty: bool = True


class AcceptInvitationRequest(BaseModel):
    token: str = Field(min_length=1)
    # Optional credentials for unauthenticated recipient sign-up
    email: str | None = Field(default=None, max_length=320)
    password: str | None = Field(default=None, min_length=12, max_length=128)
    display_name: str | None = Field(default=None, max_length=200)
    # Recipient counterparty organization details
    organization_legal_name: str | None = Field(default=None, max_length=200)
    country_code: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")

    @field_validator("country_code", mode="before")
    @classmethod
    def normalize_country_code(cls, value: object) -> object:
        if isinstance(value, str):
            clean = value.strip().upper()
            return clean if clean else None
        return value

    @field_validator("organization_legal_name", mode="before")
    @classmethod
    def strip_org_name(cls, value: object) -> object:
        if isinstance(value, str):
            clean = value.strip()
            return clean if clean else None
        return value


class AcceptInvitationResponse(BaseModel):
    status: str = "ACCEPTED"
    organization_id: UUID
    organization_legal_name: str
    user_id: UUID
    role: str
    deal_id: UUID | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"


class OrganizationDirectoryItem(BaseModel):
    id: UUID
    legal_name: str
    country_code: str
    capabilities: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)


class ContactPayload(BaseModel):
    id: UUID | None = None
    name: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=200)
    consent_obtained: bool = Field(default=True)
    visibility: str = Field(default="PRIVATE", pattern=r"^(PRIVATE|PARTICIPANTS)$")
    role_title: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    phone: str | None = Field(default=None, max_length=50)

    @field_validator("name", "purpose", mode="before")
    @classmethod
    def normalize_req_text(cls, value: object) -> object:
        if isinstance(value, str):
            clean = unicodedata.normalize("NFC", value.strip())
            return clean
        return value

    @field_validator("role_title", "phone", mode="before")
    @classmethod
    def normalize_opt_text(cls, value: object) -> object:
        if isinstance(value, str):
            clean = unicodedata.normalize("NFC", value.strip())
            return clean if clean else None
        return value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            clean = unicodedata.normalize("NFC", value.strip().lower())
            return clean if clean else None
        return value

    @field_validator("consent_obtained")
    @classmethod
    def check_consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Consent must be obtained for contact")
        return value


class ContactResponse(BaseModel):
    id: UUID
    name: str
    purpose: str
    consent_obtained: bool = True
    visibility: str
    role_title: str | None = None
    email: str | None = None
    phone: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class UpdateProfileRequest(BaseModel):
    expected_version: int = Field(ge=0)
    capabilities: list[Annotated[str, Field(min_length=1, max_length=200)]] = Field(
        default_factory=list, max_length=50
    )
    products: list[Annotated[str, Field(min_length=1, max_length=200)]] = Field(
        default_factory=list, max_length=50
    )
    regions: list[str] = Field(default_factory=list, max_length=50)
    contacts: list[ContactPayload] = Field(default_factory=list, max_length=20)

    @field_validator("capabilities", "products", mode="before")
    @classmethod
    def normalize_string_list(cls, value: object) -> object:
        if isinstance(value, list):
            cleaned: list[str] = []
            seen: set[str] = set()
            for item in value:
                if isinstance(item, str):
                    norm = unicodedata.normalize("NFC", item.strip())
                    if not norm:
                        continue
                    if len(norm) > 200:
                        raise ValueError("Capability and product items cannot exceed 200 characters")
                    key = norm.casefold()
                    if key not in seen:
                        seen.add(key)
                        cleaned.append(norm)
            return cleaned
        return value

    @field_validator("regions", mode="before")
    @classmethod
    def normalize_regions(cls, value: object) -> object:
        if isinstance(value, list):
            cleaned: list[str] = []
            seen: set[str] = set()
            for item in value:
                if isinstance(item, str):
                    code = unicodedata.normalize("NFC", item.strip().upper())
                    if len(code) != 2 or not code.isascii() or not code.isalpha():
                        raise ValueError(f"Invalid country code '{item}'; must be 2 ASCII letters")
                    if code not in seen:
                        seen.add(code)
                        cleaned.append(code)
            return cleaned
        return value

    @field_validator("contacts")
    @classmethod
    def validate_contacts(cls, contacts: list[ContactPayload]) -> list[ContactPayload]:
        seen_emails: set[str] = set()
        seen_phones: set[str] = set()
        for c in contacts:
            if not c.email and not c.phone:
                raise ValueError("Contact requires at least one channel (email or phone)")
            if c.email:
                key = c.email.casefold()
                if key in seen_emails:
                    raise ValueError(f"Duplicate email across contacts: {c.email}")
                seen_emails.add(key)
            if c.phone:
                phone_key = c.phone.strip()
                if phone_key in seen_phones:
                    raise ValueError(f"Duplicate phone across contacts: {c.phone}")
                seen_phones.add(phone_key)
        return contacts


class ProfileResponse(BaseModel):
    organization_id: UUID
    capabilities: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    contacts: list[ContactResponse] = Field(default_factory=list)
    verification_status: str = "UNVERIFIED"
    version: int
    created_at: str | None = None
    updated_at: str | None = None
    updated_by_user_id: UUID | None = None


class ApprovalRoutingPolicyRequest(BaseModel):
    """An organization admin's explicit, opt-in approval routing configuration."""

    mode: Literal["SEQUENTIAL", "PARALLEL"]
    approver_user_ids: list[UUID] = Field(min_length=1, max_length=10)
    expected_version: int | None = None

    @field_validator("approver_user_ids")
    @classmethod
    def distinct_approvers(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Approval routing approvers must be distinct")
        return value


class ApprovalRoutingPolicyResponse(BaseModel):
    organization_id: UUID
    mode: str
    approver_user_ids: list[UUID]
    version: int
    updated_by_user_id: UUID | None = None
    created_at: str | None = None
    updated_at: str | None = None


def _to_approval_routing_policy_response(policy: DomainApprovalRoutingPolicy) -> dict[str, Any]:
    return {
        "organization_id": policy.organization_id,
        "mode": policy.mode.value,
        "approver_user_ids": list(policy.approver_user_ids),
        "version": policy.version,
        "updated_by_user_id": policy.updated_by_user_id,
        "created_at": policy.created_at.isoformat() if policy.created_at else None,
        "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
    }


def _active_admin_membership(
    db: Session, organization_id: UUID, user_id: UUID
) -> tuple[Organization, OrganizationMember]:
    organization = db.scalar(
        select(Organization).where(
            Organization.id == organization_id,
            Organization.status == "ACTIVE",
        )
        .with_for_update().execution_options(populate_existing=True)
    )
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.status == "ACTIVE",
        )
        .with_for_update().execution_options(populate_existing=True)
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    if "org.members.manage" not in expand_grants(membership.role_bundles, membership.permissions, owner=membership.is_owner):
        raise HTTPException(status_code=403, detail="Organization admin role required")
    return organization, membership


def _validate_member_grants(
    db: Session,
    organization: Organization,
    delegator: OrganizationMember,
    role_bundles: list[str],
    permissions: list[str],
    deal_ids: list[UUID],
) -> tuple[list[str], list[str], list[UUID]]:
    try:
        bundles, custom_permissions = validate_grants(role_bundles, permissions)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    owner = bool(delegator.is_owner)
    delegated = expand_grants(delegator.role_bundles, delegator.permissions, owner=owner)
    requested = expand_grants(bundles, custom_permissions)
    can_delegate_ordinary_bundles = "org.members.manage" in delegated
    if not owner:
        if bundles.intersection(OWNER_ONLY_BUNDLES) or requested.intersection(OWNER_ONLY_PERMISSIONS):
            raise HTTPException(status_code=403, detail="Only the organization owner may grant organization-wide access")
        if can_delegate_ordinary_bundles:
            custom_requested = expand_grants((), custom_permissions)
            if not custom_requested.issubset(delegated):
                raise HTTPException(status_code=403, detail="You may only grant custom permissions delegated to your account")
        elif not requested.issubset(delegated):
            raise HTTPException(status_code=403, detail="You may only grant permissions delegated to your account")
    unique_deal_ids = list(dict.fromkeys(deal_ids))
    if unique_deal_ids:
        if not owner and "deal.assign" not in delegated:
            raise HTTPException(status_code=403, detail="Deal assignment authority required")
        if not owner and not can_delegate_ordinary_bundles:
            delegator_deal_ids = set(db.scalars(select(DealAssignment.deal_id).where(
                DealAssignment.organization_id == organization.id,
                DealAssignment.user_id == delegator.user_id,
                DealAssignment.status == "ACTIVE",
            )).all())
            if not set(unique_deal_ids).issubset(delegator_deal_ids):
                raise HTTPException(status_code=403, detail="You may only delegate deals assigned to your account")
        deals = db.scalars(
            select(Deal).where(
                Deal.id.in_(unique_deal_ids),
                or_(Deal.buyer_organization_id == organization.id, Deal.seller_organization_id == organization.id),
            )
        ).all()
        if {deal.id for deal in deals} != set(unique_deal_ids):
            raise HTTPException(status_code=422, detail="Every selected deal must belong to this organization")
    return sorted(bundles), sorted(custom_permissions), unique_deal_ids


def _replace_member_assignments(
    db: Session, organization_id: UUID, user_id: UUID, deal_ids: list[UUID], actor_id: UUID
) -> None:
    existing = db.scalars(select(DealAssignment).where(
        DealAssignment.organization_id == organization_id,
        DealAssignment.user_id == user_id,
        DealAssignment.status == "ACTIVE",
    ).with_for_update()).all()
    before = sorted(str(item.deal_id) for item in existing)
    by_deal = {assignment.deal_id: assignment for assignment in existing}
    for assignment in existing:
        assignment.status = "ACTIVE" if assignment.deal_id in deal_ids else "REVOKED"
    for deal_id in deal_ids:
        if deal_id not in by_deal:
            db.add(DealAssignment(organization_id=organization_id, deal_id=deal_id, user_id=user_id, status="ACTIVE"))
    if before != sorted(str(item) for item in deal_ids):
        db.add(AuditEvent(
            id=uuid4(), aggregate_type="organization_member", aggregate_id=user_id,
            event_type="member.deal_assignments_changed", actor_type="USER", actor_id=str(actor_id),
            occurred_at=datetime.now(UTC), correlation_id=str(correlation_id.get()) if correlation_id.get() else None,
            payload={"organization_id": str(organization_id), "before": before, "after": sorted(str(item) for item in deal_ids)},
        ))


def _is_org_admin(member: OrganizationMember) -> bool:
    return "org.members.manage" in expand_grants(member.role_bundles, member.permissions, owner=member.is_owner)


def _active_org_admin_count(db: Session, organization_id: UUID) -> int:
    members = db.scalars(select(OrganizationMember).where(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.status == "ACTIVE",
    )).all()
    return sum(1 for member in members if _is_org_admin(member))


@org_router.post("", status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: CreateOrganizationRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Create an organization and make its creator the first active admin."""
    # Serialize organization creation for this account so concurrent requests
    # cannot both pass the quota check.
    db.scalar(select(User.id).where(User.id == actor.user_id).with_for_update())
    active_organization_count = db.scalar(
        select(func.count(OrganizationMember.id))
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .where(
            OrganizationMember.user_id == actor.user_id,
            OrganizationMember.status == "ACTIVE",
            Organization.status == "ACTIVE",
        )
    )
    if active_organization_count >= settings.max_organizations_per_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization limit reached for this account",
        )

    organization = Organization(
        legal_name=payload.legal_name,
        country_code=payload.country_code,
    )
    db.add(organization)
    db.flush()
    db.add(
        OrganizationMember(
            organization_id=organization.id,
            user_id=actor.user_id,
            role="ADMIN",
            status="ACTIVE",
            capabilities=["FINANCE"],
            role_bundles=[],
            permissions=[],
            is_owner=True,
        )
    )
    db.add(AuditEvent(id=uuid4(), aggregate_type="organization", aggregate_id=organization.id,
                      event_type="organization.owner_registered", actor_type="USER", actor_id=str(actor.user_id),
                      occurred_at=datetime.now(UTC), correlation_id=str(correlation_id.get()) if correlation_id.get() else None,
                      payload={"user_id": str(actor.user_id), "source": "authenticated_organization_creation"}))
    db.commit()
    return {
        "id": str(organization.id),
        "legal_name": organization.legal_name,
        "country_code": organization.country_code,
        "role": "ADMIN",
    }


def _compute_effective_capabilities(role: str, assigned: list[str] | None) -> list[str]:
    return sorted(cap.value for cap in resolve_effective_capabilities(role, assigned))


@org_router.get("")
def list_my_organizations(
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """List active organizations and roles resolved from database membership."""
    rows = db.execute(
        select(Organization, OrganizationMember.role, OrganizationMember.is_owner)
        .join(
            OrganizationMember,
            OrganizationMember.organization_id == Organization.id,
        )
        .where(
            OrganizationMember.user_id == actor.user_id,
            OrganizationMember.status == "ACTIVE",
            Organization.status == "ACTIVE",
        )
        .order_by(Organization.legal_name)
    )
    return [
        {
            "id": str(organization.id),
            "legal_name": organization.legal_name,
            "country_code": organization.country_code,
            "role": "ADMIN" if actor.has_permission(organization.id, "org.members.manage") else "MEMBER",
            "is_owner": is_owner,
            "capabilities": sorted([
                c.value for c in actor.capabilities_by_organization.get(organization.id, frozenset())
            ]),
        }
        for organization, _legacy_role, is_owner in rows
    ]


def _escape_like(value: str) -> str:
    """Escape SQL LIKE/ILIKE special wildcard and escape characters."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _case_insensitive_prefix(
    db: Session, column: ColumnElement[str], prefix: str
) -> ColumnElement[bool]:
    """Match a prefix ignoring case, including non-ASCII letters on SQLite.

    PostgreSQL indexes ``lower(legal_name)``, so comparing against ``lower()``
    keeps the prefix filter on that index; ``ILIKE`` cannot use it. SQLite
    implements ``lower()`` (which SQLAlchemy's ``ilike`` relies on) with
    ASCII-only folding, so it compares against a Unicode-aware function
    registered on the connection instead.
    """
    escaped_prefix = _escape_like(prefix)
    if db.get_bind().dialect.name != "sqlite":
        # Fold the pattern in SQL too: Python's lower() disagrees with PostgreSQL's
        # for some scripts (e.g. "İ", "Σ"), which would drop valid matches.
        return func.lower(column).like(func.lower(f"{escaped_prefix}%"), escape="\\")

    dbapi_connection = db.connection().connection.dbapi_connection
    dbapi_connection.create_function(
        "syncally_casefold",
        1,
        lambda value: value.casefold() if isinstance(value, str) else value,
        deterministic=True,
    )
    return func.syncally_casefold(column).like(f"{escaped_prefix.casefold()}%", escape="\\")


@org_router.get(
    "/directory",
    response_model=list[OrganizationDirectoryItem],
    dependencies=[Depends(get_current_actor)],
)
def list_organization_directory(
    q: str | None = Query(default=None, max_length=100),
    product: str | None = Query(default=None, max_length=100),
    capability: str | None = Query(default=None, max_length=100),
    region: str | None = Query(default=None, max_length=100),
    country_code: str | None = Query(default=None, min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10000),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """List active organizations in the public directory with optional prefix search."""
    # PostgreSQL indexes lower(legal_name), so filter and order on the same
    # expression; a plain legal_name sort would not match the index.
    name_order = func.lower(Organization.legal_name)
    if db.get_bind().dialect.name != "postgresql":
        name_order = Organization.legal_name

    stmt = (
        select(
            Organization.id,
            Organization.legal_name,
            Organization.country_code,
            OrganizationProfile.capabilities,
            OrganizationProfile.products,
            OrganizationProfile.regions,
        )
        .outerjoin(OrganizationProfile, OrganizationProfile.organization_id == Organization.id)
        .where(Organization.status == "ACTIVE")
        .order_by(name_order.asc(), Organization.id.asc())
        .limit(limit)
        .offset(offset)
    )
    if q is not None:
        clean_q = q.strip()
        if clean_q:
            stmt = stmt.where(_case_insensitive_prefix(db, Organization.legal_name, clean_q))
    if country_code:
        stmt = stmt.where(Organization.country_code == country_code.upper())
    # ponytail: scan profile JSON for the MVP; use indexed listings when catalogs grow.
    for value, column in (
        (product, OrganizationProfile.products),
        (capability, OrganizationProfile.capabilities),
        (region, OrganizationProfile.regions),
    ):
        if value and value.strip():
            pattern = f"%{_escape_like(value.strip())}%"
            stmt = stmt.where(cast(column, String).ilike(pattern, escape="\\"))

    rows = db.execute(stmt).all()
    return [
        {
            "id": row.id,
            "legal_name": row.legal_name,
            "country_code": row.country_code,
            "capabilities": row.capabilities or [],
            "products": row.products or [],
            "regions": row.regions or [],
        }
        for row in rows
    ]


@org_router.get(
    "/{organization_id}",
    response_model=OrganizationDirectoryItem,
    dependencies=[Depends(get_current_actor)],
)
def get_organization_route(
    organization_id: UUID,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get active organization public details by ID."""
    row = db.execute(
        select(
            Organization.id,
            Organization.legal_name,
            Organization.country_code,
            OrganizationProfile.capabilities,
            OrganizationProfile.products,
            OrganizationProfile.regions,
        )
        .outerjoin(OrganizationProfile, OrganizationProfile.organization_id == Organization.id)
        .where(
            Organization.id == organization_id,
            Organization.status == "ACTIVE",
        )
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )
    return {
        "id": row.id,
        "legal_name": row.legal_name,
        "country_code": row.country_code,
        "capabilities": row.capabilities or [],
        "products": row.products or [],
        "regions": row.regions or [],
    }


_PARTICIPANT_CONTACT_ELIGIBLE_DEAL_STATUSES = (
    "AGREED",
    "EXECUTING",
    "COMPLETED",
    "DISPUTED",
)


@org_router.get(
    "/{organization_id}/profile",
    response_model=ProfileResponse,
)
def get_organization_profile_route(
    organization_id: UUID,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    org = db.scalar(
        select(Organization).where(
            Organization.id == organization_id,
            Organization.status == "ACTIVE",
        )
    )
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )

    repo = SqlAlchemyOrganizationRepository(db)
    profile = repo.get_profile(organization_id)
    if profile is None:
        return {
            "organization_id": organization_id,
            "capabilities": [],
            "products": [],
            "regions": [],
            "contacts": [],
            "verification_status": "UNVERIFIED",
            "version": 0,
            "created_at": None,
            "updated_at": None,
            "updated_by_user_id": None,
        }

    is_member = organization_id in actor.organization_ids
    is_deal_participant = False
    if not is_member and actor.organization_ids:
        active_deal = db.scalar(
            select(Deal.id).where(
                (
                    (Deal.buyer_organization_id == organization_id)
                    & Deal.seller_organization_id.in_(actor.organization_ids)
                )
                | (
                    (Deal.seller_organization_id == organization_id)
                    & Deal.buyer_organization_id.in_(actor.organization_ids)
                ),
                Deal.status.in_(_PARTICIPANT_CONTACT_ELIGIBLE_DEAL_STATUSES),
            ).limit(1)
        )
        is_deal_participant = active_deal is not None

    if is_member:
        allowed_contacts = profile.contacts
    elif is_deal_participant:
        allowed_contacts = [
            c
            for c in profile.contacts
            if (c.visibility == ContactVisibility.PARTICIPANTS or c.visibility == "PARTICIPANTS")
        ]
    else:
        allowed_contacts = []

    contact_responses = [
        {
            "id": c.id,
            "name": c.name,
            "purpose": c.purpose,
            "consent_obtained": c.consent_obtained,
            "visibility": c.visibility.value if hasattr(c.visibility, "value") else str(c.visibility),
            "role_title": c.role_title,
            "email": c.email,
            "phone": c.phone,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in allowed_contacts
    ]

    return {
        "organization_id": profile.organization_id,
        "capabilities": profile.capabilities,
        "products": profile.products,
        "regions": profile.regions,
        "contacts": contact_responses,
        "verification_status": profile.verification_status.value
        if hasattr(profile.verification_status, "value")
        else str(profile.verification_status),
        "version": profile.version,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        "updated_by_user_id": profile.updated_by_user_id,
    }


@org_router.put(
    "/{organization_id}/profile",
    response_model=ProfileResponse,
)
def update_organization_profile_route(
    organization_id: UUID,
    payload: UpdateProfileRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _active_admin_membership(db, organization_id, actor.user_id)

    domain_contacts = [
        DomainOrganizationContact(
            id=c.id or uuid4(),
            name=c.name,
            purpose=c.purpose,
            consent_obtained=c.consent_obtained,
            visibility=ContactVisibility(c.visibility),
            role_title=c.role_title,
            email=c.email,
            phone=c.phone,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        for c in payload.contacts
    ]

    domain_profile = DomainOrganizationProfile(
        organization_id=OrganizationId(organization_id),
        capabilities=payload.capabilities,
        products=payload.products,
        regions=payload.regions,
        contacts=domain_contacts,
        verification_status=OrganizationVerificationStatus.UNVERIFIED,
        version=max(1, payload.expected_version + 1),
        updated_by_user_id=UserId(actor.user_id),
    )

    repo = SqlAlchemyOrganizationRepository(db)
    try:
        saved = repo.save_profile(domain_profile, expected_version=payload.expected_version)
        db.commit()
    except InvariantViolation as exc:
        db.rollback()
        if "version conflict" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Profile version conflict; please refresh",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    contact_responses = [
        {
            "id": c.id,
            "name": c.name,
            "purpose": c.purpose,
            "consent_obtained": c.consent_obtained,
            "visibility": c.visibility.value if hasattr(c.visibility, "value") else str(c.visibility),
            "role_title": c.role_title,
            "email": c.email,
            "phone": c.phone,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in saved.contacts
    ]

    return {
        "organization_id": saved.organization_id,
        "capabilities": saved.capabilities,
        "products": saved.products,
        "regions": saved.regions,
        "contacts": contact_responses,
        "verification_status": saved.verification_status.value
        if hasattr(saved.verification_status, "value")
        else str(saved.verification_status),
        "version": saved.version,
        "created_at": saved.created_at.isoformat() if saved.created_at else None,
        "updated_at": saved.updated_at.isoformat() if saved.updated_at else None,
        "updated_by_user_id": saved.updated_by_user_id,
    }


@org_router.post("/{organization_id}/members", status_code=status.HTTP_201_CREATED)
def add_organization_member(
    organization_id: UUID,
    payload: AddOrganizationMemberRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Add an existing active account to an organization as a regular member."""
    organization, delegator = _active_admin_membership(db, organization_id, actor.user_id)
    role_bundles, permissions, deal_ids = _validate_member_grants(
        db, organization, delegator, payload.role_bundles, payload.permissions, payload.deal_ids
    )
    email = payload.email.strip().lower()
    user = db.scalar(
        select(User).where(
            User.email == email,
            User.status == "ACTIVE",
            User.password_hash.is_not(None),
        )
    )
    if user is None:
        raise HTTPException(status_code=404, detail="Active provisioned user not found")
    notifier, public_base_url, _configuration_error = _invitation_delivery()

    existing_membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user.id,
        )
    )
    if existing_membership is not None:
        if existing_membership.status == "ACTIVE":
            raise HTTPException(status_code=409, detail="User already has an active membership; edit access instead")
        existing_membership.role = "MEMBER"
        existing_membership.status = "ACTIVE"
        existing_membership.capabilities = []
        existing_membership.role_bundles = role_bundles
        existing_membership.permissions = permissions
        existing_membership.version = existing_membership.version + 1
        _replace_member_assignments(db, organization_id, user.id, deal_ids, actor.user_id)
        db.add(AuditEvent(id=uuid4(), aggregate_type="organization_member", aggregate_id=existing_membership.id,
                          event_type="member.access_granted", actor_type="USER", actor_id=str(actor.user_id),
                          occurred_at=datetime.now(UTC), correlation_id=str(correlation_id.get()) if correlation_id.get() else None,
                          payload={"organization_id": str(organization_id),
                          "user_id": str(user.id), "role_bundles": role_bundles, "permissions": permissions}))
        db.commit()
        email_sent, email_error = _send_invitation_email(
            notifier.send_member_added_notice if notifier else None,
            user.email,
            organization.legal_name,
            f"{public_base_url}/#/deals",
        )
        return {
            "user_id": str(user.id),
            "email": user.email,
            "role": existing_membership.role,
            "email_sent": email_sent,
            "email_error": email_error,
        }

    membership = OrganizationMember(
        organization_id=organization_id,
        user_id=user.id,
        role="MEMBER",
        status="ACTIVE",
        role_bundles=role_bundles,
        permissions=permissions,
    )
    db.add(membership)
    db.flush()
    _replace_member_assignments(db, organization_id, user.id, deal_ids, actor.user_id)
    db.add(AuditEvent(id=uuid4(), aggregate_type="organization_member", aggregate_id=membership.id,
                      event_type="member.access_granted", actor_type="USER", actor_id=str(actor.user_id),
                      occurred_at=datetime.now(UTC), correlation_id=str(correlation_id.get()) if correlation_id.get() else None,
                      payload={"organization_id": str(organization_id),
                      "user_id": str(user.id), "role_bundles": role_bundles, "permissions": permissions}))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _is_duplicate_membership_error(exc):
            raise HTTPException(status_code=409, detail="User already has an active membership") from exc
        raise

    email_sent, email_error = _send_invitation_email(
        notifier.send_member_added_notice if notifier else None,
        user.email,
        organization.legal_name,
        f"{public_base_url}/#/deals",
    )
    return {
        "user_id": str(user.id),
        "email": user.email,
        "role": membership.role,
        "email_sent": email_sent,
        "email_error": email_error,
    }


@org_router.get(
    "/{organization_id}/members",
    response_model=list[OrganizationMemberResponse],
)
def list_organization_members(
    organization_id: UUID,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """List active members of an organization with effective capabilities."""
    if not actor.has_permission(organization_id, "org.members.manage"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active organization membership required",
        )

    rows = db.execute(
        select(OrganizationMember, User.email, User.display_name)
        .join(User, User.id == OrganizationMember.user_id)
        .where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.status == "ACTIVE",
            User.status == "ACTIVE",
        )
        .order_by(OrganizationMember.created_at, OrganizationMember.user_id)
    ).all()

    return [
        {
            "user_id": member.user_id,
            "email": email,
            "display_name": display_name,
            "role": member.role,
            "status": member.status,
            "capabilities": _compute_effective_capabilities(member.role, member.capabilities),
            "assigned_capabilities": sorted(member.capabilities or []),
            "role_bundles": list(member.role_bundles or []),
            "permissions": list(member.permissions or []),
            "deal_ids": db.scalars(select(DealAssignment.deal_id).where(
                DealAssignment.organization_id == organization_id,
                DealAssignment.user_id == member.user_id,
                DealAssignment.status == "ACTIVE",
            )).all(),
            "is_owner": member.is_owner,
            "version": member.version,
        }
        for member, email, display_name in rows
    ]


@org_router.get("/{organization_id}/assignable-deals")
def list_assignable_organization_deals(
    organization_id: UUID,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    organization = db.scalar(select(Organization).where(Organization.id == organization_id, Organization.status == "ACTIVE"))
    if organization is None or organization_id not in actor.organization_ids:
        raise HTTPException(status_code=404, detail="Organization not found")
    if not actor.has_permission(organization_id, "deal.assign"):
        raise HTTPException(status_code=403, detail="Deal assignment permission required")
    deals = db.scalars(select(Deal).where(
        or_(Deal.buyer_organization_id == organization_id, Deal.seller_organization_id == organization_id)
    ).order_by(Deal.created_at.desc(), Deal.id)).all()
    return [{"id": str(deal.id), "display_name": deal.display_name or "Untitled deal", "status": deal.status}
            for deal in deals]


@org_router.put("/{organization_id}/members/{user_id}/deal-assignments")
def update_member_deal_assignments(
    organization_id: UUID,
    user_id: UUID,
    payload: DealAssignmentUpdate,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Let a deal manager assign only deals already delegated to their own account."""
    organization = db.scalar(select(Organization).where(
        Organization.id == organization_id,
        Organization.status == "ACTIVE",
    ).with_for_update().execution_options(populate_existing=True))
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    manager = db.scalar(select(OrganizationMember).where(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == actor.user_id,
        OrganizationMember.status == "ACTIVE",
    ).with_for_update().execution_options(populate_existing=True))
    if manager is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    manager_grants = expand_grants(manager.role_bundles, manager.permissions, owner=manager.is_owner)
    if "deal.assign" not in manager_grants:
        raise HTTPException(status_code=403, detail="Deal assignment permission required")
    if user_id == actor.user_id:
        raise HTTPException(status_code=403, detail="Cannot change your own deal assignments")

    target = db.scalar(select(OrganizationMember).where(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == user_id,
        OrganizationMember.status == "ACTIVE",
    ).with_for_update().execution_options(populate_existing=True))
    if target is None:
        raise HTTPException(status_code=404, detail="Member not found in organization")
    if target.is_owner:
        raise HTTPException(status_code=409, detail="Owner deal scope cannot be edited")
    if target.version != payload.expected_version:
        raise HTTPException(status_code=409, detail="Member permissions conflict; please refresh")

    requested_deal_ids = list(dict.fromkeys(payload.deal_ids))
    deals = db.scalars(select(Deal).where(
        Deal.id.in_(requested_deal_ids),
        or_(Deal.buyer_organization_id == organization_id, Deal.seller_organization_id == organization_id),
    )).all()
    if {deal.id for deal in deals} != set(requested_deal_ids):
        raise HTTPException(status_code=422, detail="Every selected deal must belong to this organization")

    is_admin_delegator = "org.members.manage" in manager_grants
    current_deal_ids = set(db.scalars(select(DealAssignment.deal_id).where(
        DealAssignment.organization_id == organization_id,
        DealAssignment.user_id == user_id,
        DealAssignment.status == "ACTIVE",
    )).all())
    if not manager.is_owner and not is_admin_delegator:
        own_deal_ids = set(db.scalars(select(DealAssignment.deal_id).where(
            DealAssignment.organization_id == organization_id,
            DealAssignment.user_id == actor.user_id,
            DealAssignment.status == "ACTIVE",
        )).all())
        if not set(requested_deal_ids).issubset(own_deal_ids):
            raise HTTPException(status_code=403, detail="You may only delegate deals assigned to your account")
        deal_ids = sorted((current_deal_ids - own_deal_ids) | set(requested_deal_ids), key=str)
    else:
        deal_ids = requested_deal_ids

    _replace_member_assignments(db, organization_id, user_id, deal_ids, actor.user_id)
    target.version += 1
    db.commit()
    return {"organization_id": str(organization_id), "user_id": str(user_id),
            "deal_ids": [str(item) for item in deal_ids], "version": target.version}


@org_router.post("/{organization_id}/claim-ownership")
def claim_legacy_organization_ownership(
    organization_id: UUID,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Recover a legacy ownerless organization only when one admin is unambiguous."""
    organization, member = _active_admin_membership(db, organization_id, actor.user_id)
    existing_owner = db.scalar(select(OrganizationMember.id).where(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.status == "ACTIVE",
        OrganizationMember.is_owner.is_(True),
    ).limit(1))
    if existing_owner is not None:
        raise HTTPException(status_code=409, detail="Organization already has an owner")
    if _active_org_admin_count(db, organization_id) != 1:
        raise HTTPException(status_code=409, detail="A system administrator must resolve ownership because multiple admins exist")
    member.is_owner = True
    member.role_bundles = []
    member.permissions = []
    member.version += 1
    db.add(AuditEvent(id=uuid4(), aggregate_type="organization", aggregate_id=organization_id,
                      event_type="organization.owner_recovered", actor_type="USER", actor_id=str(actor.user_id),
                      occurred_at=datetime.now(UTC), correlation_id=str(correlation_id.get()) if correlation_id.get() else None,
                      payload={"user_id": str(actor.user_id), "method": "sole_admin_claim"}))
    db.commit()
    return {"organization_id": str(organization.id), "owner_user_id": str(actor.user_id), "status": "recovered"}


@org_router.patch(
    "/{organization_id}/members/{user_id}",
    response_model=OrganizationMemberResponse,
)
def update_member_permissions(
    organization_id: UUID,
    user_id: UUID,
    payload: UpdateMemberPermissionsRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Update an organization member's role and capabilities with optimistic locking."""
    organization, delegator = _active_admin_membership(db, organization_id, actor.user_id)

    if user_id == actor.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify your own membership role or capabilities",
        )

    target = db.scalar(
        select(OrganizationMember)
        .where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.status == "ACTIVE",
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in organization",
        )

    if target.is_owner:
        raise HTTPException(status_code=409, detail="Transfer ownership before editing this member's access")

    user = db.scalar(
        select(User).where(User.id == target.user_id, User.status == "ACTIVE")
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active user not found",
        )

    if target.version != payload.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Member permissions conflict; please refresh",
        )

    if payload.role is not None or payload.capabilities is not None:
        raise HTTPException(status_code=422, detail="Use role_bundles and permissions")
    before_bundles = list(target.role_bundles or [])
    before_permissions = list(target.permissions or [])
    before_deal_ids = list(db.scalars(select(DealAssignment.deal_id).where(
        DealAssignment.organization_id == organization_id,
        DealAssignment.user_id == user_id,
        DealAssignment.status == "ACTIVE",
    )).all())
    bundles = payload.role_bundles if payload.role_bundles is not None else list(target.role_bundles or [])
    permissions = payload.permissions if payload.permissions is not None else list(target.permissions or [])
    deal_ids = payload.deal_ids if payload.deal_ids is not None else list(db.scalars(select(DealAssignment.deal_id).where(
        DealAssignment.organization_id == organization_id,
        DealAssignment.user_id == user_id,
        DealAssignment.status == "ACTIVE",
    )).all())
    bundles, permissions, deal_ids = _validate_member_grants(
        db, organization, delegator, bundles, permissions, deal_ids
    )
    if _is_org_admin(target) and "org.members.manage" not in expand_grants(bundles, permissions, owner=target.is_owner) and _active_org_admin_count(db, organization_id) <= 1:
        raise HTTPException(status_code=409, detail="Cannot remove the last organization administrator")
    target.role_bundles = bundles
    target.permissions = permissions
    _replace_member_assignments(db, organization_id, user_id, deal_ids, actor.user_id)

    target.version = target.version + 1

    now = datetime.now(UTC)
    db.add(
        AuditEvent(
            id=uuid4(),
            aggregate_type="organization_member",
            aggregate_id=target.id,
            event_type="member.permissions_updated",
            actor_type="USER",
            actor_id=str(actor.user_id),
            occurred_at=now,
            correlation_id=str(correlation_id.get()) if correlation_id.get() else None,
            payload={
                "organization_id": str(organization_id),
                "target_user_id": str(user_id),
                "role": target.role,
                "capabilities": target.capabilities,
                "role_bundles": bundles,
                "permissions": permissions,
                "deal_ids": [str(item) for item in deal_ids],
                "before": {"role_bundles": before_bundles, "permissions": before_permissions,
                           "deal_ids": [str(item) for item in before_deal_ids]},
                "after": {"role_bundles": bundles, "permissions": permissions,
                          "deal_ids": [str(item) for item in deal_ids]},
                "version": target.version,
            },
        )
    )
    db.commit()

    return {
        "user_id": target.user_id,
        "email": user.email,
        "display_name": user.display_name,
        "role": target.role,
        "status": target.status,
        "capabilities": _compute_effective_capabilities(target.role, target.capabilities),
        "assigned_capabilities": sorted(target.capabilities or []),
        "role_bundles": bundles,
        "permissions": permissions,
        "deal_ids": deal_ids,
        "is_owner": target.is_owner,
        "version": target.version,
    }


@org_router.delete(
    "/{organization_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_organization_member(
    organization_id: UUID,
    user_id: UUID,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> None:
    """Revoke an active member from an organization."""
    _active_admin_membership(db, organization_id, actor.user_id)

    if user_id == actor.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot revoke your own membership",
        )

    target = db.scalar(
        select(OrganizationMember)
        .where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.status == "ACTIVE",
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in organization",
        )

    if target.is_owner:
        raise HTTPException(status_code=409, detail="Transfer ownership before removing this member")

    if _is_org_admin(target) and _active_org_admin_count(db, organization_id) <= 1:
        raise HTTPException(status_code=409, detail="Cannot revoke the last organization administrator")

    before_bundles = list(target.role_bundles or [])
    before_permissions = list(target.permissions or [])
    target.status = "REVOKED"
    target.capabilities = []
    target.role_bundles = []
    target.permissions = []
    target.version = target.version + 1
    assignments = db.scalars(select(DealAssignment).where(
        DealAssignment.organization_id == organization_id,
        DealAssignment.user_id == user_id,
        DealAssignment.status == "ACTIVE",
    ).with_for_update()).all()
    for assignment in assignments:
        assignment.status = "REVOKED"

    now = datetime.now(UTC)
    db.add(
        AuditEvent(
            id=uuid4(),
            aggregate_type="organization_member",
            aggregate_id=target.id,
            event_type="member.revoked",
            actor_type="USER",
            actor_id=str(actor.user_id),
            occurred_at=now,
            correlation_id=str(correlation_id.get()) if correlation_id.get() else None,
            payload={
                "organization_id": str(organization_id),
                "target_user_id": str(user_id),
                "before": {"role_bundles": before_bundles,
                           "permissions": before_permissions,
                           "deal_ids": [str(item.deal_id) for item in assignments]},
                "after": {"role_bundles": [], "permissions": [], "deal_ids": []},
            },
        )
    )
    db.commit()


@org_router.get(
    "/{organization_id}/approval-routing",
    response_model=ApprovalRoutingPolicyResponse | None,
)
def get_approval_routing_policy_route(
    organization_id: UUID,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, Any] | None:
    """Read this organization's approval routing policy, if one is configured.

    Absent (``null``) means the default: existing single-approver bilateral
    approval behavior.
    """
    if not actor.has_permission(organization_id, "approval_routing.manage"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active organization membership required",
        )
    policy = SqlAlchemyApprovalRoutingPolicyRepository(db).get(organization_id)
    return _to_approval_routing_policy_response(policy) if policy is not None else None


@org_router.put(
    "/{organization_id}/approval-routing",
    response_model=ApprovalRoutingPolicyResponse,
)
def put_approval_routing_policy_route(
    organization_id: UUID,
    payload: ApprovalRoutingPolicyRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Create or update this organization's approval routing policy.

    Every listed approver must already be an active member of this
    organization with AGREEMENT_APPROVAL capability - routing can only
    sequence existing approval authority, never grant new authority.
    """
    if not actor.has_permission(organization_id, "approval_routing.manage"):
        raise HTTPException(status_code=403, detail="Approval routing permission required")

    domain_policy = DomainApprovalRoutingPolicy(
        organization_id=OrganizationId(organization_id),
        mode=ApprovalRoutingMode(payload.mode),
        approver_user_ids=tuple(UserId(uid) for uid in payload.approver_user_ids),
    )
    repo = SqlAlchemyApprovalRoutingPolicyRepository(db)
    try:
        saved = repo.save(
            domain_policy,
            expected_version=payload.expected_version,
            updated_by_user_id=actor.user_id,
        )
        db.commit()
    except InvariantViolation as exc:
        db.rollback()
        if "version conflict" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Approval routing policy version conflict; please refresh",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return _to_approval_routing_policy_response(saved)


@org_router.delete(
    "/{organization_id}/approval-routing",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_approval_routing_policy_route(
    organization_id: UUID,
    expected_version: int | None = Query(default=None),
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> None:
    """Remove this organization's approval routing policy.

    Reverts the organization to the default: existing single-approver
    bilateral approval behavior.
    """
    if not actor.has_permission(organization_id, "approval_routing.manage"):
        raise HTTPException(status_code=403, detail="Approval routing permission required")
    repo = SqlAlchemyApprovalRoutingPolicyRepository(db)
    try:
        repo.delete(organization_id, expected_version=expected_version)
        db.commit()
    except InvariantViolation as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approval routing policy version conflict; please refresh",
        ) from exc


@org_router.post("/{organization_id}/repair-finance")
def repair_organization_finance_route(
    organization_id: UUID,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Provide a supported way for existing organizations to repair finance membership.

    Preserves the self-modification restriction on general member editing and avoids blanket admin
    grants by only provisioning FINANCE if the organization currently has zero members with FINANCE capability.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Finance access must be granted explicitly through member access settings",
    )


def _create_invitation_token(
    organization: Organization,
    inviter_user_id: UUID,
    deal_id: UUID | None = None,
    role: str = "MEMBER",
    *,
    recipient_email: str | None = None,
    shell_id: UUID | None = None,
    inviter_party: str = "BUYER",
    role_bundles: list[str] | None = None,
    permissions: list[str] | None = None,
    deal_ids: list[UUID] | None = None,
) -> tuple[str, datetime, UUID]:
    if not settings.jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication is not configured",
        )
    jti = uuid4()
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=7)
    claims: dict[str, object] = {
        "jti": str(jti),
        "sub": str(organization.id),
        "org_id": str(organization.id),
        "org_name": organization.legal_name,
        "deal_id": str(deal_id) if deal_id else None,
        "role": role,
        "role_bundles": list(role_bundles or []),
        "permissions": list(permissions or []),
        "granted_deal_ids": [str(item) for item in (deal_ids or [])],
        "inviter_user_id": str(inviter_user_id),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "typ": "organization_invitation",
    }
    if recipient_email is not None:
        claims.update(version=1, kind="COUNTERPARTY" if shell_id else "TEAM",
                      recipient_email=recipient_email, role="MEMBER")
        if shell_id is not None:
            if inviter_party == "BUYER":
                claims.update(shell_id=str(shell_id), buyer_id=str(organization.id))
            else:
                claims.update(version=2, shell_id=str(shell_id), inviting_org_id=str(organization.id), inviter_party=inviter_party)
    token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at, jti


def _decode_invitation_token(token: str) -> dict[str, object]:
    if not settings.jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication is not configured",
        )
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "typ", "jti"]},
        )
        if claims.get("typ") != "organization_invitation":
            raise jwt.InvalidTokenError("Token type is not valid for invitation")
        typed_keys = {"version", "kind", "recipient_email", "shell_id", "buyer_id", "inviting_org_id", "inviter_party"}
        if typed_keys.intersection(claims):
            if type(claims.get("version")) is not int or claims["version"] not in (1, 2):
                raise jwt.InvalidTokenError("Unknown invitation version")
            if claims.get("kind") not in {"TEAM", "COUNTERPARTY"}:
                raise jwt.InvalidTokenError("Unknown invitation kind")
            email = claims.get("recipient_email")
            if not isinstance(email, str) or email != email.strip().lower() or "@" not in email:
                raise jwt.InvalidTokenError("Missing invitation recipient")
            if claims.get("role") != "MEMBER" or claims.get("sub") != claims.get("org_id"):
                raise jwt.InvalidTokenError("Invalid invitation authority")
            for key in ("jti", "org_id", "inviter_user_id"):
                UUID(str(claims[key]))
            if claims["kind"] == "TEAM":
                if claims["version"] != 1 or claims.get("deal_id") or any(key in claims for key in ("shell_id", "buyer_id", "inviting_org_id", "inviter_party")):
                    raise jwt.InvalidTokenError("Invalid team invitation binding")
            else:
                party_key = "buyer_id" if claims["version"] == 1 else "inviting_org_id"
                for key in ("deal_id", "shell_id", party_key):
                    UUID(str(claims[key]))
                if claims[party_key] != claims["org_id"] or claims["shell_id"] == claims[party_key]:
                    raise jwt.InvalidTokenError("Invalid counterparty binding")
                if claims["version"] == 2 and (claims.get("inviter_party") != "SELLER" or "buyer_id" in claims):
                    raise jwt.InvalidTokenError("Invalid inviting party")
                if claims["version"] == 1 and ("inviting_org_id" in claims or "inviter_party" in claims):
                    raise jwt.InvalidTokenError("Invalid legacy binding")
        return claims
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation token has expired",
        ) from exc
    except (jwt.InvalidTokenError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invitation token",
        ) from exc


@org_router.post(
    "/{organization_id}/invitations",
    status_code=status.HTTP_201_CREATED,
    response_model=InvitationResponse,
)
def create_organization_invitation(
    organization_id: UUID,
    payload: CreateInvitationRequest = CreateInvitationRequest(),
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Generate a signed single-use invitation token valid for 7 days."""
    organization, delegator = _active_admin_membership(db, organization_id, actor.user_id)
    if payload.recipient_email is not None and payload.deal_id is not None:
        raise HTTPException(status_code=422, detail="Use counterparty deal creation for recipient-bound deal invitations")
    if payload.deal_id is not None:
        deal = db.scalar(select(Deal).where(Deal.id == payload.deal_id))
        if deal is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
        if deal.onboarding is not None:
            raise HTTPException(status_code=409, detail="This deal already has a bound counterparty invitation")
        if organization_id not in (deal.buyer_organization_id, deal.seller_organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization is not a participant in this deal",
            )
    role_bundles, permissions, deal_ids = _validate_member_grants(
        db, organization, delegator, payload.role_bundles, payload.permissions, payload.deal_ids
    )
    notifier, public_base_url, configuration_error = _invitation_delivery()
    token, expires_at, jti = _create_invitation_token(
        organization, actor.user_id, payload.deal_id, payload.role,
        recipient_email=payload.recipient_email,
        role_bundles=role_bundles, permissions=permissions, deal_ids=deal_ids,
    )
    db.add(
        AuditEvent(
            id=uuid4(),
            aggregate_type="organization_invitation",
            aggregate_id=jti,
            event_type="invitation.created",
            actor_type="USER",
            actor_id=str(actor.user_id),
            occurred_at=datetime.now(UTC),
            payload={
                "organization_id": str(organization_id),
                "deal_id": str(payload.deal_id) if payload.deal_id else None,
                "role": "MEMBER" if payload.recipient_email else payload.role,
                "role_bundles": role_bundles,
                "permissions": permissions,
                "deal_ids": [str(item) for item in deal_ids],
                "expires_at": expires_at.isoformat(),
            },
        )
    )
    db.commit()
    invite_url = _invite_url(public_base_url, token)
    email_sent, email_error = (False, None)
    if payload.recipient_email is not None:
        if configuration_error is None:
            email_sent, email_error = _send_invitation_email(
                notifier.send_team_invitation if notifier else None,
                payload.recipient_email,
                organization.legal_name,
                invite_url,
                expires_at.isoformat(),
            )
        else:
            email_error = configuration_error
    return {
        "invitation_id": jti,
        "token": token,
        "invite_url": invite_url,
        "organization_id": str(organization_id),
        "organization_legal_name": organization.legal_name,
        "deal_id": str(payload.deal_id) if payload.deal_id else None,
        "role": "MEMBER" if payload.recipient_email else payload.role,
        "expires_at": expires_at.isoformat(),
        "kind": "TEAM" if payload.recipient_email else None,
        "email_sent": email_sent,
        "email_error": email_error,
    }


@org_router.delete("/{organization_id}/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_organization_invitation(
    organization_id: UUID,
    invitation_id: UUID,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> None:
    """Persist an invitation revocation so its signed token can no longer be accepted."""
    _active_admin_membership(db, organization_id, actor.user_id)
    created = db.scalar(select(AuditEvent).where(
        AuditEvent.aggregate_type == "organization_invitation",
        AuditEvent.aggregate_id == invitation_id,
        AuditEvent.event_type == "invitation.created",
    ).with_for_update().execution_options(populate_existing=True))
    if created is None or created.payload.get("organization_id") != str(organization_id):
        raise HTTPException(status_code=404, detail="Invitation not found")
    completed = db.scalar(select(AuditEvent.id).where(
        AuditEvent.aggregate_type == "organization_invitation",
        AuditEvent.aggregate_id == invitation_id,
        AuditEvent.event_type.in_(("invitation.accepted", "invitation.revoked")),
    ).limit(1))
    if completed is not None:
        raise HTTPException(status_code=409, detail="Invitation has already been accepted or revoked")
    db.add(AuditEvent(
        id=uuid4(), aggregate_type="organization_invitation", aggregate_id=invitation_id,
        event_type="invitation.revoked", actor_type="USER", actor_id=str(actor.user_id),
        occurred_at=datetime.now(UTC),
        correlation_id=str(correlation_id.get()) if correlation_id.get() else None,
        payload={"organization_id": str(organization_id), "inviter_user_id": str(actor.user_id)},
    ))
    db.commit()


@router.post("/deals/counterparty-invitations", status_code=201, response_model=CounterpartyInvitationResponse)
def create_counterparty_invitation(
    payload: CreateCounterpartyInvitationRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        if payload.inviting_organization_id and payload.buyer_organization_id:
            raise HTTPException(status_code=422, detail="Specify one inviting organization")
        if payload.inviter_party == "SELLER" and (payload.buyer_organization_id or not payload.inviting_organization_id):
            raise HTTPException(status_code=422, detail="Seller invitations require the inviting organization")
        inviting_id = payload.inviting_organization_id or payload.buyer_organization_id
        if inviting_id is None:
            raise HTTPException(status_code=422, detail="An inviting organization is required")
        inviter, _ = _active_admin_membership(db, inviting_id, actor.user_id)
        notifier, public_base_url, configuration_error = _invitation_delivery()
        active_user = db.scalar(select(User.id).where(User.id == actor.user_id, User.status == "ACTIVE").with_for_update())
        if active_user is None:
            raise HTTPException(status_code=401, detail="Active user session not found")
        shell = Organization(legal_name=payload.legal_name, country_code=payload.country_code, status="INACTIVE")
        db.add(shell)
        db.flush()
        buyer_id = inviter.id if payload.inviter_party == "BUYER" else shell.id
        seller_id = shell.id if payload.inviter_party == "BUYER" else inviter.id
        lock_demo_deal_creation(db, buyer_id, seller_id)
        now = datetime.now(UTC)
        deal = DomainDeal(id=DealId(uuid4()), buyer_organization_id=OrganizationId(buyer_id),
                          seller_organization_id=OrganizationId(seller_id), created_at=now,
                          display_name=payload.display_name, version=1)
        SqlAlchemyDealRepository(db).stage(deal)
        token, expires_at, jti = _create_invitation_token(
            inviter, actor.user_id, deal.id, recipient_email=payload.recipient_email, shell_id=shell.id,
            inviter_party=payload.inviter_party,
        )
        db.flush()
        db.add(CounterpartyOnboarding(invitation_jti=jti, deal_id=deal.id,
                                     inviting_organization_id=inviter.id, inviter_party=payload.inviter_party, shell_organization_id=shell.id,
                                     inviter_user_id=actor.user_id, recipient_email=payload.recipient_email,
                                     expires_at=expires_at))
        db.add(AuditEvent(id=uuid4(), aggregate_type="organization_invitation", aggregate_id=jti,
                          event_type="invitation.created", actor_type="USER", actor_id=str(actor.user_id),
                          occurred_at=now, correlation_id=str(correlation_id.get()) if correlation_id.get() else None,
                          payload={"kind": "COUNTERPARTY", "deal_id": str(deal.id),
                                                    "organization_id": str(inviter.id), "expires_at": expires_at.isoformat()}))
        db.commit()
        invite_url = _invite_url(public_base_url, token)
        if configuration_error is None:
            email_sent, email_error = _send_invitation_email(
                notifier.send_counterparty_invitation if notifier else None,
                payload.recipient_email,
                inviter.legal_name,
                deal.display_name or "your shared trade deal",
                invite_url,
                expires_at.isoformat(),
            )
        else:
            email_sent, email_error = False, configuration_error
        return {"token": token, "invite_url": invite_url, "invitation_id": jti,
                "organization_id": str(inviter.id), "organization_legal_name": inviter.legal_name,
                "deal_id": str(deal.id), "role": "ADMIN", "kind": "COUNTERPARTY",
                "expires_at": expires_at.isoformat(), "pending_counterparty": True,
                "email_sent": email_sent, "email_error": email_error}
    except Exception:
        db.rollback()
        raise


def _deal_awaiting_counterparty(db: Session, deal_id: UUID, inviting_org_id: UUID) -> Deal:
    """Load the deal an invitation may link a counterparty into, or reject the acceptance.

    Linking replaces the placeholder party with the organization the invitee creates, so it is
    only safe while the inviting organization still participates, the deal has not moved past
    DRAFT, and the other party is an unclaimed shell. Rejecting up front keeps the deal
    untouched and avoids creating a conversation for a non-participant.
    """
    deal = lock_deal(db, deal_id)
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    if inviting_org_id == deal.buyer_organization_id:
        counterparty_org_id = deal.seller_organization_id
    elif inviting_org_id == deal.seller_organization_id:
        counterparty_org_id = deal.buyer_organization_id
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inviting organization is no longer a participant in this deal",
        )
    if deal.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Deal is no longer open for counterparty onboarding",
        )
    claimed_counterparty = db.scalar(
        select(OrganizationMember.id)
        .where(
            OrganizationMember.organization_id == counterparty_org_id,
            OrganizationMember.status == "ACTIVE",
        )
        .limit(1)
    )
    if claimed_counterparty is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Deal counterparty is already claimed by an active organization",
        )
    return deal


@router.post(
    "/invitations/accept",
    status_code=status.HTTP_200_OK,
    response_model=AcceptInvitationResponse,
)
def accept_invitation(
    payload: AcceptInvitationRequest,
    actor: ActorContext | None = Depends(get_optional_actor),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return _accept_invitation(payload, actor, db)
    except (IntegrityError, OperationalError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Invitation acceptance conflicts with another request") from exc
    except Exception:
        db.rollback()
        raise


def _accept_invitation(
    payload: AcceptInvitationRequest, actor: ActorContext | None, db: Session
) -> dict[str, object]:
    """Accept an invitation token to sign up, join an organization, or link a counterparty into a deal."""
    claims = _decode_invitation_token(payload.token)
    try:
        jti = UUID(str(claims["jti"]))
        org_id = UUID(str(claims["org_id"]))
        inviter_user_id = UUID(str(claims["inviter_user_id"]))
        deal_uuid = UUID(str(claims["deal_id"])) if claims.get("deal_id") else None
    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invitation token claims",
        ) from exc
    role = str(claims.get("role", "MEMBER"))
    deal_id_str = claims.get("deal_id")
    kind = claims.get("kind")
    created_invite = db.scalar(select(AuditEvent).where(
        AuditEvent.aggregate_type == "organization_invitation",
        AuditEvent.aggregate_id == jti,
        AuditEvent.event_type == "invitation.created",
    ).with_for_update().execution_options(populate_existing=True))
    if created_invite is None or created_invite.payload.get("organization_id") != str(org_id):
        raise HTTPException(status_code=409, detail="Invitation is no longer valid")
    revoked = db.scalar(select(AuditEvent.id).where(
        AuditEvent.aggregate_type == "organization_invitation",
        AuditEvent.aggregate_id == jti,
        AuditEvent.event_type == "invitation.revoked",
    ).limit(1))
    if revoked is not None:
        raise HTTPException(status_code=409, detail="Invitation was revoked")
    onboarding: CounterpartyOnboarding | None = None
    if kind == "TEAM" and payload.organization_legal_name:
        raise HTTPException(status_code=400, detail="Team invitations do not create a counterparty organization")
    if kind == "COUNTERPARTY":
        lock_deal(db, deal_uuid)
        onboarding = db.scalar(select(CounterpartyOnboarding).where(CounterpartyOnboarding.invitation_jti == jti)
                               .with_for_update().execution_options(populate_existing=True))
        if onboarding is None or (
            onboarding.deal_id != deal_uuid or str(onboarding.inviting_organization_id) != str(org_id)
            or str(onboarding.shell_organization_id) != claims["shell_id"]
            or onboarding.inviter_user_id != inviter_user_id or onboarding.recipient_email != claims["recipient_email"]
            or onboarding.inviter_party != (claims.get("inviter_party") if claims["version"] == 2 else "BUYER")
        ):
            raise HTTPException(status_code=409, detail="Counterparty invitation binding is no longer valid")
        if onboarding.consumed_at is not None:
            raise HTTPException(status_code=409, detail="Invitation token has already been used")
        if as_utc(onboarding.expires_at) <= datetime.now(UTC):
            raise HTTPException(status_code=400, detail="Invitation token has expired")
        shell = db.scalar(select(Organization).where(Organization.id == onboarding.shell_organization_id)
                          .with_for_update().execution_options(populate_existing=True))
        if shell is None or shell.status != "INACTIVE":
            raise HTTPException(status_code=409, detail="Counterparty shell is no longer unclaimed")

    # Atomic single-use check
    already_used = db.scalar(
        select(AuditEvent.id).where(
            AuditEvent.aggregate_type == "organization_invitation",
            AuditEvent.aggregate_id == jti,
            AuditEvent.event_type == "invitation.accepted",
        )
    )
    if already_used is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitation token has already been used",
        )

    inviting_org = db.scalar(
        select(Organization).where(Organization.id == org_id, Organization.status == "ACTIVE")
        .with_for_update().execution_options(populate_existing=True)
    )
    if inviting_org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inviting organization not found",
        )

    inviter_admin = db.scalar(
        select(OrganizationMember)
        .join(User, User.id == OrganizationMember.user_id)
        .where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == inviter_user_id,
            OrganizationMember.status == "ACTIVE",
            User.status == "ACTIVE",
        )
        .with_for_update(of=(OrganizationMember, User))
    )
    if inviter_admin is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inviter is no longer an active organization admin",
        )
    if "org.members.manage" not in expand_grants(inviter_admin.role_bundles, inviter_admin.permissions, owner=inviter_admin.is_owner):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inviter no longer has member administration authority")
    grant_bundles: list[str] = []
    grant_permissions: list[str] = []
    grant_deal_ids: list[UUID] = []
    if kind == "TEAM":
        raw_bundles = claims.get("role_bundles", [])
        raw_permissions = claims.get("permissions", [])
        raw_deals = claims.get("granted_deal_ids", [])
        try:
            grant_bundles, grant_permissions, grant_deal_ids = _validate_member_grants(
                db, inviting_org, inviter_admin,
                [str(item) for item in raw_bundles],
                [str(item) for item in raw_permissions],
                [UUID(str(item)) for item in raw_deals],
            )
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Invitation grant snapshot is invalid") from exc

    # Validate the deal claim before writing any user or organization state, so a stale or
    # invalid invitation cannot leave partial changes behind. A deal invitation onboards a
    # counterparty, so the recipient must create their own organization instead of silently
    # joining the inviting organization as a team member.
    linking_deal: Deal | None = None
    if deal_uuid is not None:
        if not payload.organization_legal_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An organization legal name is required to accept a deal invitation",
            )
        linking_deal = _deal_awaiting_counterparty(db, deal_uuid, org_id)
        if onboarding is None and linking_deal.onboarding is not None:
            raise HTTPException(status_code=409, detail="This deal requires its bound counterparty invitation")
        if onboarding is not None:
            expected_parties = ((onboarding.inviting_organization_id, onboarding.shell_organization_id)
                                if onboarding.inviter_party == "BUYER" else
                                (onboarding.shell_organization_id, onboarding.inviting_organization_id))
            if (linking_deal.buyer_organization_id, linking_deal.seller_organization_id) != expected_parties:
                raise HTTPException(status_code=409, detail="Deal parties have changed")
            has_messages = db.scalar(select(Message.id).join(Conversation, Conversation.id == Message.conversation_id)
                                     .where(Conversation.deal_id == deal_uuid).limit(1))
            commercial_state = any(db.scalar(select(model.id).where(model.deal_id == deal_uuid).limit(1)) is not None
                                   for model in (Proposal, NegotiationSession, AgreementVersion))
            if has_messages is not None or commercial_state or linking_deal.current_proposal_id or linking_deal.current_agreement_version_id:
                raise HTTPException(status_code=409, detail="Deal is no longer open for counterparty onboarding")
            _decode_invitation_token(payload.token)

    # 1. Resolve or create user
    user: User | None = None
    if actor is not None:
        user = db.scalar(
            select(User).where(User.id == actor.user_id, User.status == "ACTIVE")
            .with_for_update().execution_options(populate_existing=True)
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Active user session not found",
            )
    else:
        if not payload.email or not payload.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and password are required to accept an invitation when not signed in",
            )
        clean_email = payload.email.strip().lower()
        if kind and clean_email != claims["recipient_email"]:
            raise HTTPException(status_code=403, detail="Invitation is addressed to a different account")
        user = db.scalar(select(User).where(User.email == clean_email).with_for_update().execution_options(populate_existing=True))
        if user is not None:
            if not verify_password(payload.password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials for existing account",
                )
            if user.status != "ACTIVE":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is suspended",
                )
        else:
            display_name = (payload.display_name or "").strip() or clean_email.split("@")[0]
            user = User(
                email=clean_email,
                display_name=display_name,
                password_hash=hash_password(payload.password),
                status="ACTIVE",
            )
            db.add(user)
            db.flush()

    if kind and user.email.strip().lower() != claims["recipient_email"]:
        raise HTTPException(status_code=403, detail="Invitation is addressed to a different account")

    # 2. Handle organization membership & counterparty organization creation
    membership_status = "PENDING_SETUP" if actor is None and user.password_hash is None else "ACTIVE"
    if payload.organization_legal_name:
        active_count = db.scalar(select(func.count(OrganizationMember.id)).join(Organization, Organization.id == OrganizationMember.organization_id)
                    .where(OrganizationMember.user_id == user.id, OrganizationMember.status == "ACTIVE", Organization.status == "ACTIVE"))
        if active_count >= settings.max_organizations_per_user:
            raise HTTPException(status_code=409, detail="Organization limit reached for this account")
        # Counterparty onboarding: create recipient's organization
        recipient_org = Organization(
            legal_name=payload.organization_legal_name,
            country_code=payload.country_code or "US",
            status="ACTIVE",
        )
        db.add(recipient_org)
        db.flush()
        db.add(
            OrganizationMember(
                organization_id=recipient_org.id,
                user_id=user.id,
                role="ADMIN",
                status=membership_status,
                capabilities=["FINANCE"],
                role_bundles=[],
                permissions=[],
                is_owner=True,
            )
        )
        db.add(AuditEvent(id=uuid4(), aggregate_type="organization", aggregate_id=recipient_org.id,
                          event_type="organization.owner_registered", actor_type="USER", actor_id=str(user.id),
                          occurred_at=datetime.now(UTC), correlation_id=str(correlation_id.get()) if correlation_id.get() else None,
                          payload={"user_id": str(user.id), "source": "counterparty_onboarding"}))
        effective_org = recipient_org
        effective_role = "ADMIN"
    else:
        # Team membership invitation to the inviting org
        existing = db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user.id,
            )
        )
        if existing is not None:
            if existing.status == "ACTIVE":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User already has an active membership in this organization",
                )
            existing.role = role
            existing.status = membership_status
            existing.capabilities = []
            existing.role_bundles = grant_bundles
            existing.permissions = grant_permissions
            existing.version = existing.version + 1
            _replace_member_assignments(db, org_id, user.id, grant_deal_ids, inviter_user_id)
        else:
            membership = OrganizationMember(
                    organization_id=org_id,
                    user_id=user.id,
                    role=role,
                    status=membership_status,
                    role_bundles=grant_bundles,
                    permissions=grant_permissions,
                )
            db.add(membership)
            db.flush()
            _replace_member_assignments(db, org_id, user.id, grant_deal_ids, inviter_user_id)
        effective_org = inviting_org
        effective_role = role

    # 3. Handle immediate deal linking
    if linking_deal is not None:
        if linking_deal.buyer_organization_id == org_id:
            linking_deal.seller_organization_id = effective_org.id
        else:
            linking_deal.buyer_organization_id = effective_org.id
        linking_deal.version = linking_deal.version + 1
        if onboarding is not None:
            onboarding.consumed_at = datetime.now(UTC)
            onboarding.recipient_organization_id = effective_org.id

        # Ensure participant conversation exists for effective_org
        existing_conv = db.scalar(
            select(Conversation).where(
                Conversation.deal_id == linking_deal.id,
                Conversation.participant_organization_id == effective_org.id,
            )
        )
        if existing_conv is None:
            db.add(
                Conversation(
                    deal_id=linking_deal.id,
                    participant_organization_id=effective_org.id,
                )
            )

    # 4. Record single-use AuditEvent and flush it before issuing tokens, so a
    # duplicate token is rejected before any acceptance side effects commit.
    now = datetime.now(UTC)
    db.add(
        AuditEvent(
            id=jti,
            aggregate_type="organization_invitation",
            aggregate_id=jti,
            event_type="invitation.accepted",
            actor_type="USER",
            actor_id=str(user.id),
            occurred_at=now,
            correlation_id=str(correlation_id.get()) if correlation_id.get() else None,
            payload={
                "organization_id": str(effective_org.id),
                "inviting_organization_id": str(org_id),
                "inviter_user_id": str(inviter_user_id),
                "user_id": str(user.id),
                "deal_id": deal_id_str,
                "role": effective_role,
                "role_bundles": grant_bundles if kind == "TEAM" else [],
                "permissions": grant_permissions if kind == "TEAM" else [],
                "deal_ids": [str(item) for item in grant_deal_ids] if kind == "TEAM" else [],
            },
        )
    )
    try:
        db.flush()

        # 5. Issue auth tokens for seamless sign-in in the same transaction.
        access_token = _encode_access_token(user.id, now)
        refresh_token = create_refresh_token(db, user.id, now, commit=False)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitation token has already been used",
        ) from exc

    return {
        "status": "ACCEPTED",
        "organization_id": str(effective_org.id),
        "organization_legal_name": effective_org.legal_name,
        "user_id": str(user.id),
        "role": effective_role,
        "deal_id": deal_id_str,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


router.include_router(org_router)


def _is_duplicate_membership_error(error: IntegrityError) -> bool:
    """Recognize only the organization/user unique constraint across supported DBs."""
    original = error.orig
    diagnostic = getattr(original, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)
    if constraint_name is not None:
        return constraint_name == "organization_members_organization_id_user_id_key"

    # SQLite reports the constrained columns in the exception text instead of
    # exposing a PostgreSQL-style constraint name.
    message = str(original).lower()
    return (
        "unique constraint failed" in message
        and "organization_members.organization_id" in message
        and "organization_members.user_id" in message
    )
