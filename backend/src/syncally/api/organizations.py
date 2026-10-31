"""Organization creation and initial membership setup endpoints."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import ColumnElement, func, select
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
from syncally.config import settings
from syncally.domain.deals.deal import Deal as DomainDeal
from syncally.domain.shared.identifiers import DealId, OrganizationId
from syncally.infrastructure.counterparty_onboarding import lock_deal
from syncally.infrastructure.database import get_db
from syncally.infrastructure.demo_lifecycle import lock_demo_deal_creation
from syncally.infrastructure.models import (
    AgreementVersion,
    AuditEvent,
    Conversation,
    CounterpartyOnboarding,
    Deal,
    Message,
    NegotiationSession,
    Organization,
    OrganizationMember,
    Proposal,
    User,
)
from syncally.infrastructure.repositories._timestamps import as_utc
from syncally.infrastructure.repositories.deals import SqlAlchemyDealRepository

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
    recipient_email: str | None = Field(default=None, max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

    @field_validator("recipient_email", mode="before")
    @classmethod
    def normalize_recipient(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class CreateCounterpartyInvitationRequest(CreateOrganizationRequest):
    buyer_organization_id: UUID
    recipient_email: str = Field(max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

    @field_validator("recipient_email", mode="before")
    @classmethod
    def normalize_recipient(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class InvitationResponse(BaseModel):
    token: str
    invite_url: str
    organization_id: UUID
    organization_legal_name: str
    deal_id: UUID | None = None
    role: str
    expires_at: str
    kind: str | None = None


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
    *,
    recipient_email: str | None = None,
    shell_id: UUID | None = None,
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
    if recipient_email is not None:
        claims.update(version=1, kind="COUNTERPARTY" if shell_id else "TEAM",
                      recipient_email=recipient_email, role="MEMBER")
        if shell_id is not None:
            claims.update(shell_id=str(shell_id), buyer_id=str(organization.id))
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
        typed_keys = {"version", "kind", "recipient_email", "shell_id", "buyer_id"}
        if typed_keys.intersection(claims):
            if type(claims.get("version")) is not int or claims["version"] != 1:
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
                if claims.get("deal_id") or "shell_id" in claims or "buyer_id" in claims:
                    raise jwt.InvalidTokenError("Invalid team invitation binding")
            else:
                for key in ("deal_id", "shell_id", "buyer_id"):
                    UUID(str(claims[key]))
                if claims["buyer_id"] != claims["org_id"] or claims["shell_id"] == claims["buyer_id"]:
                    raise jwt.InvalidTokenError("Invalid counterparty binding")
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

    token, expires_at, jti = _create_invitation_token(
        organization, actor.user_id, payload.deal_id, payload.role,
        recipient_email=payload.recipient_email,
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
                "expires_at": expires_at.isoformat(),
            },
        )
    )
    db.commit()
    return {
        "token": token,
        "invite_url": f"{settings.public_frontend_url}/#/invite?token={token}",
        "organization_id": str(organization_id),
        "organization_legal_name": organization.legal_name,
        "deal_id": str(payload.deal_id) if payload.deal_id else None,
        "role": "MEMBER" if payload.recipient_email else payload.role,
        "expires_at": expires_at.isoformat(),
        "kind": "TEAM" if payload.recipient_email else None,
    }


@router.post("/deals/counterparty-invitations", status_code=201, response_model=CounterpartyInvitationResponse)
def create_counterparty_invitation(
    payload: CreateCounterpartyInvitationRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        buyer, _ = _active_admin_membership(db, payload.buyer_organization_id, actor.user_id)
        active_user = db.scalar(select(User.id).where(User.id == actor.user_id, User.status == "ACTIVE").with_for_update())
        if active_user is None:
            raise HTTPException(status_code=401, detail="Active user session not found")
        shell = Organization(legal_name=payload.legal_name, country_code=payload.country_code, status="INACTIVE")
        db.add(shell)
        db.flush()
        lock_demo_deal_creation(db, buyer.id, shell.id)
        now = datetime.now(UTC)
        deal = DomainDeal(id=DealId(uuid4()), buyer_organization_id=OrganizationId(buyer.id),
                          seller_organization_id=OrganizationId(shell.id), created_at=now, version=1)
        SqlAlchemyDealRepository(db).stage(deal)
        token, expires_at, jti = _create_invitation_token(
            buyer, actor.user_id, deal.id, recipient_email=payload.recipient_email, shell_id=shell.id
        )
        db.flush()
        db.add(CounterpartyOnboarding(invitation_jti=jti, deal_id=deal.id,
                                     buyer_organization_id=buyer.id, shell_organization_id=shell.id,
                                     inviter_user_id=actor.user_id, recipient_email=payload.recipient_email,
                                     expires_at=expires_at))
        db.add(AuditEvent(id=uuid4(), aggregate_type="organization_invitation", aggregate_id=jti,
                          event_type="invitation.created", actor_type="USER", actor_id=str(actor.user_id),
                          occurred_at=now, payload={"kind": "COUNTERPARTY", "deal_id": str(deal.id),
                                                    "organization_id": str(buyer.id), "expires_at": expires_at.isoformat()}))
        db.commit()
        return {"token": token, "invite_url": f"{settings.public_frontend_url}/#/invite?token={token}",
                "organization_id": str(buyer.id), "organization_legal_name": buyer.legal_name,
                "deal_id": str(deal.id), "role": "ADMIN", "kind": "COUNTERPARTY",
                "expires_at": expires_at.isoformat(), "pending_counterparty": True}
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
    onboarding: CounterpartyOnboarding | None = None
    if kind == "TEAM" and payload.organization_legal_name:
        raise HTTPException(status_code=400, detail="Team invitations do not create a counterparty organization")
    if kind == "COUNTERPARTY":
        lock_deal(db, deal_uuid)
        onboarding = db.scalar(select(CounterpartyOnboarding).where(CounterpartyOnboarding.invitation_jti == jti)
                               .with_for_update().execution_options(populate_existing=True))
        if onboarding is None or (
            onboarding.deal_id != deal_uuid or str(onboarding.buyer_organization_id) != claims["buyer_id"]
            or str(onboarding.shell_organization_id) != claims["shell_id"]
            or onboarding.inviter_user_id != inviter_user_id or onboarding.recipient_email != claims["recipient_email"]
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
        select(OrganizationMember.id)
        .join(User, User.id == OrganizationMember.user_id)
        .where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == inviter_user_id,
            OrganizationMember.role == "ADMIN",
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
            if linking_deal.buyer_organization_id != onboarding.buyer_organization_id or linking_deal.seller_organization_id != onboarding.shell_organization_id:
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
