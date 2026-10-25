"""Organization creation and initial membership setup endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
from syncally.application.identity import ActorContext
from syncally.config import settings
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import Organization, OrganizationMember, User

router = APIRouter(prefix="/organizations", tags=["organizations"])


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


@router.post("", status_code=status.HTTP_201_CREATED)
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


@router.get("")
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


@router.get(
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
    stmt = (
        select(Organization.id, Organization.legal_name, Organization.country_code)
        .where(Organization.status == "ACTIVE")
        .order_by(Organization.legal_name.asc(), Organization.id.asc())
        .limit(limit)
        .offset(offset)
    )
    if q is not None:
        clean_q = q.strip()
        if clean_q:
            stmt = stmt.where(
                Organization.legal_name.ilike(f"{_escape_like(clean_q)}%", escape="\\")
            )

    rows = db.execute(stmt).all()
    return [
        {
            "id": row.id,
            "legal_name": row.legal_name,
            "country_code": row.country_code,
        }
        for row in rows
    ]


@router.post("/{organization_id}/members", status_code=status.HTTP_201_CREATED)
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
