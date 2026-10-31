"""Organization creation and initial membership setup endpoints."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syncally.api.auth import (
    _encode_access_token,
    bearer_scheme,
    create_refresh_token,
    get_current_actor,
)
from syncally.application.identity import ActorContext
from syncally.application.passwords import hash_password, verify_password
from syncally.config import settings
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import (
    AuditEvent,
    Conversation,
    Deal,
    Organization,
    OrganizationMember,
    User,
)

router = APIRouter(tags=["organizations"])
org_router = APIRouter(prefix="/organizations", tags=["organizations"])


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


class CreateInvitationRequest(BaseModel):
    deal_id: UUID | None = None
    role: str = Field(default="MEMBER", pattern=r"^(ADMIN|MEMBER)$")


class InvitationResponse(BaseModel):
    token: str
    invite_url: str
    organization_id: UUID
    organization_legal_name: str
    deal_id: UUID | None = None
    role: str
    expires_at: str


class AcceptInvitationRequest(BaseModel):
    token: str = Field(min_length=1)
    # Optional credentials for unauthenticated recipient sign-up
    email: str | None = Field(default=None, max_length=320)
    password: str | None = Field(default=None, min_length=8, max_length=128)
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


def _active_admin_membership(
    db: Session, organization_id: UUID, user_id: UUID
) -> tuple[Organization, OrganizationMember]:
    organization = db.scalar(
        select(Organization).where(
            Organization.id == organization_id,
            Organization.status == "ACTIVE",
        )
    )
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.status == "ACTIVE",
        )
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    if membership.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Organization admin role required")
    return organization, membership


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
        )
    )
    db.commit()
    return {
        "id": str(organization.id),
        "legal_name": organization.legal_name,
        "country_code": organization.country_code,
        "role": "ADMIN",
    }


@org_router.get("")
def list_my_organizations(
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[dict[str, str]]:
    """List active organizations and roles resolved from database membership."""
    rows = db.execute(
        select(Organization, OrganizationMember.role)
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
            "role": role,
        }
        for organization, role in rows
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
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10000),
    db: Session = Depends(get_db),
) -> list[dict[str, UUID | str]]:
    """List active organizations in the public directory with optional prefix search."""
    # PostgreSQL indexes lower(legal_name), so filter and order on the same
    # expression; a plain legal_name sort would not match the index.
    name_order = func.lower(Organization.legal_name)
    if db.get_bind().dialect.name != "postgresql":
        name_order = Organization.legal_name

    stmt = (
        select(Organization.id, Organization.legal_name, Organization.country_code)
        .where(Organization.status == "ACTIVE")
        .order_by(name_order.asc(), Organization.id.asc())
        .limit(limit)
        .offset(offset)
    )
    if q is not None:
        clean_q = q.strip()
        if clean_q:
            stmt = stmt.where(_case_insensitive_prefix(db, Organization.legal_name, clean_q))

    rows = db.execute(stmt).all()
    return [
        {
            "id": row.id,
            "legal_name": row.legal_name,
            "country_code": row.country_code,
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
) -> dict[str, UUID | str]:
    """Get active organization public details by ID."""
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
    return {
        "id": org.id,
        "legal_name": org.legal_name,
        "country_code": org.country_code,
    }


@org_router.post("/{organization_id}/members", status_code=status.HTTP_201_CREATED)
def add_organization_member(
    organization_id: UUID,
    payload: AddOrganizationMemberRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Add an existing active account to an organization as a regular member."""
    _active_admin_membership(db, organization_id, actor.user_id)
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

    existing_membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user.id,
        )
    )
    if existing_membership is not None:
        if existing_membership.status == "ACTIVE":
            raise HTTPException(status_code=409, detail="User already has an active membership")
        existing_membership.role = "MEMBER"
        existing_membership.status = "ACTIVE"
        db.commit()
        return {"user_id": str(user.id), "email": user.email, "role": existing_membership.role}

    membership = OrganizationMember(
        organization_id=organization_id,
        user_id=user.id,
        role="MEMBER",
        status="ACTIVE",
    )
    db.add(membership)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _is_duplicate_membership_error(exc):
            raise HTTPException(status_code=409, detail="User already has an active membership") from exc
        raise

    return {"user_id": str(user.id), "email": user.email, "role": membership.role}


def _create_invitation_token(
    organization: Organization,
    inviter_user_id: UUID,
    deal_id: UUID | None = None,
    role: str = "MEMBER",
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
        "inviter_user_id": str(inviter_user_id),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "typ": "organization_invitation",
    }
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
    organization, _ = _active_admin_membership(db, organization_id, actor.user_id)
    if payload.deal_id is not None:
        deal = db.scalar(select(Deal).where(Deal.id == payload.deal_id))
        if deal is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
        if organization_id not in (deal.buyer_organization_id, deal.seller_organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization is not a participant in this deal",
            )

    token, expires_at, jti = _create_invitation_token(
        organization, actor.user_id, payload.deal_id, payload.role
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
                "role": payload.role,
                "expires_at": expires_at.isoformat(),
            },
        )
    )
    db.commit()
    return {
        "token": token,
        "invite_url": f"https://app.syncally.trade/#/invite?token={token}",
        "organization_id": str(organization_id),
        "organization_legal_name": organization.legal_name,
        "deal_id": str(payload.deal_id) if payload.deal_id else None,
        "role": payload.role,
        "expires_at": expires_at.isoformat(),
    }


def _deal_awaiting_counterparty(db: Session, deal_id: UUID, inviting_org_id: UUID) -> Deal:
    """Load the deal an invitation may link a counterparty into, or reject the acceptance.

    Linking replaces the placeholder party with the organization the invitee creates, so it is
    only safe while the inviting organization still participates, the deal has not moved past
    DRAFT, and the other party is an unclaimed shell. Rejecting up front keeps the deal
    untouched and avoids creating a conversation for a non-participant.
    """
    deal = db.scalar(select(Deal).where(Deal.id == deal_id).with_for_update())
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
    )
    if inviting_org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inviting organization not found",
        )

    inviter_admin = db.scalar(
        select(OrganizationMember.id)
        .join(User, User.id == OrganizationMember.user_id)
        .where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == inviter_user_id,
            OrganizationMember.role == "ADMIN",
            OrganizationMember.status == "ACTIVE",
            User.status == "ACTIVE",
        )
    )
    if inviter_admin is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inviter is no longer an active organization admin",
        )

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

    # 1. Resolve or create user
    user: User | None = None
    if actor is not None:
        user = db.scalar(
            select(User).where(User.id == actor.user_id, User.status == "ACTIVE")
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
        user = db.scalar(select(User).where(User.email == clean_email))
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

    # 2. Handle organization membership & counterparty organization creation
    if payload.organization_legal_name:
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
                status="ACTIVE",
            )
        )
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
            existing.status = "ACTIVE"
        else:
            db.add(
                OrganizationMember(
                    organization_id=org_id,
                    user_id=user.id,
                    role=role,
                    status="ACTIVE",
                )
            )
        effective_org = inviting_org
        effective_role = role

    # 3. Handle immediate deal linking
    if linking_deal is not None:
        if linking_deal.buyer_organization_id == org_id:
            linking_deal.seller_organization_id = effective_org.id
        else:
            linking_deal.buyer_organization_id = effective_org.id
        linking_deal.version = linking_deal.version + 1

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
            payload={
                "organization_id": str(effective_org.id),
                "inviting_organization_id": str(org_id),
                "inviter_user_id": str(inviter_user_id),
                "user_id": str(user.id),
                "deal_id": deal_id_str,
                "role": effective_role,
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
