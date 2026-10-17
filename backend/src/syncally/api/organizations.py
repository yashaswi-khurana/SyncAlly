"""Organization creation and initial membership setup endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
from syncally.application.identity import ActorContext
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
        raise HTTPException(status_code=409, detail="User already has a membership record")

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
        raise HTTPException(status_code=409, detail="User already has a membership record") from exc

    return {"user_id": str(user.id), "email": user.email, "role": membership.role}
