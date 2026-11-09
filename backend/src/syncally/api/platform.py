"""Platform management that deliberately exposes organization metadata only."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from syncally.api.auth import require_system_admin
from syncally.application.identity import ActorContext
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import (
    AuditEvent,
    Organization,
    OrganizationMember,
    RefreshToken,
    User,
)
from syncally.operations import correlation_id

router = APIRouter(prefix="/platform", tags=["platform administration"])


class OrganizationStatusUpdate(BaseModel):
    status: Literal["ACTIVE", "SUSPENDED"]


class UserStatusUpdate(BaseModel):
    status: Literal["ACTIVE", "LOCKED"]
    reason: str | None = None


class OrganizationOwnerUpdate(BaseModel):
    user_id: UUID
    reason: str = Field(min_length=3, max_length=500)


def _user_summary(user: User) -> dict[str, str]:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "status": user.status,
        "system_role": user.system_role,
        "created_at": user.created_at.isoformat() if user.created_at else "",
    }


@router.get("/users")
def list_platform_users(
    _actor: ActorContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, str]]:
    users = db.scalars(select(User).order_by(func.lower(User.email), User.id)).all()
    return [_user_summary(user) for user in users]


@router.patch("/users/{user_id}")
def update_platform_user_status(
    user_id: UUID,
    payload: UserStatusUpdate,
    actor: ActorContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = db.scalar(
        select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True)
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.status not in {"ACTIVE", "LOCKED"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is not in a lockable state")
    if actor.user_id == user.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You cannot lock or unlock your own account")
    if user.status not in {"ACTIVE", "LOCKED"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is not in a lockable state")
    if payload.status == "LOCKED" and user.status != "LOCKED":
        admin_ids = db.scalars(
            select(User.id).where(User.system_role == "SYSTEM_ADMIN", User.status == "ACTIVE").with_for_update()
        ).all()
        if user.system_role == "SYSTEM_ADMIN" and len(admin_ids) <= 1:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot lock the only active system administrator")
        owner_organization_ids = db.scalars(select(OrganizationMember.organization_id).where(
            OrganizationMember.user_id == user.id,
            OrganizationMember.is_owner.is_(True),
            OrganizationMember.status == "ACTIVE",
            OrganizationMember.organization_id.in_(select(Organization.id).where(Organization.status == "ACTIVE")),
        )).all()
        for organization_id in owner_organization_ids:
            owner_count = db.scalar(select(func.count(OrganizationMember.id)).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.is_owner.is_(True),
                OrganizationMember.status == "ACTIVE",
            )) or 0
            if owner_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Transfer organization ownership before locking this account",
                )

    previous = user.status
    user.status = payload.status
    now = datetime.now(UTC)
    if previous == "ACTIVE" and payload.status == "LOCKED":
        db.execute(
            update(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
            ).values(revoked_at=now)
        )
    if previous != payload.status:
        db.add(AuditEvent(
            id=uuid4(),
            aggregate_type="user",
            aggregate_id=user.id,
            event_type="user.account_status_changed",
            actor_type="USER",
            actor_id=str(actor.user_id),
            occurred_at=now,
            correlation_id=str(correlation_id.get()) if correlation_id.get() else None,
            payload={"from": previous, "to": payload.status, "reason": (payload.reason or "").strip()[:500]},
        ))
    db.commit()
    return _user_summary(user)


@router.put("/organizations/{organization_id}/owner")
def set_platform_organization_owner(
    organization_id: UUID,
    payload: OrganizationOwnerUpdate,
    actor: ActorContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    organization = db.scalar(select(Organization).where(
        Organization.id == organization_id, Organization.status == "ACTIVE"
    ).with_for_update())
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    members = db.scalars(select(OrganizationMember).where(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.status == "ACTIVE",
    ).with_for_update()).all()
    target = next((member for member in members if member.user_id == payload.user_id), None)
    target_user = db.scalar(select(User).where(User.id == payload.user_id, User.status == "ACTIVE"))
    if target is None or target_user is None:
        raise HTTPException(status_code=422, detail="New owner must be an active organization member")
    current = [member for member in members if member.is_owner]
    if len(current) > 1:
        raise HTTPException(status_code=409, detail="Organization has multiple owner grants and needs manual recovery")
    if len(current) == 1 and current[0].user_id == target.user_id:
        return {"organization_id": str(organization_id), "owner_user_id": str(target.user_id), "status": "unchanged"}
    previous_user_id = current[0].user_id if current else None
    if current:
        current[0].is_owner = False
        current[0].role_bundles = ["ORG_ADMIN"]
        current[0].permissions = []
        current[0].version += 1
    target.is_owner = True
    target.role_bundles = []
    target.permissions = []
    target.version += 1
    db.add(AuditEvent(id=uuid4(), aggregate_type="organization", aggregate_id=organization_id,
                      event_type="organization.owner_transferred", actor_type="USER", actor_id=str(actor.user_id),
                      occurred_at=datetime.now(UTC), correlation_id=str(correlation_id.get()) if correlation_id.get() else None,
                      payload={"from_user_id": str(previous_user_id) if previous_user_id else None,
                      "to_user_id": str(target.user_id), "reason": payload.reason.strip()}))
    db.commit()
    return {"organization_id": str(organization_id), "owner_user_id": str(target.user_id), "status": "transferred"}


def _organization_summary(organization: Organization, owner_user_id: UUID | None = None) -> dict[str, str | None]:
    return {
        "id": str(organization.id),
        "legal_name": organization.legal_name,
        "country_code": organization.country_code,
        "status": organization.status,
        "created_at": organization.created_at.isoformat() if organization.created_at else "",
        "owner_user_id": str(owner_user_id) if owner_user_id else None,
    }


@router.get("/organizations")
def list_platform_organizations(
    _actor: ActorContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, str | None]]:
    organizations = db.scalars(
        select(Organization).order_by(func.lower(Organization.legal_name), Organization.id)
    ).all()
    owners = db.execute(select(OrganizationMember.organization_id, OrganizationMember.user_id).where(
        OrganizationMember.status == "ACTIVE", OrganizationMember.is_owner.is_(True)
    )).all()
    owners_by_org = {organization_id: user_id for organization_id, user_id in owners}
    return [_organization_summary(organization, owners_by_org.get(organization.id)) for organization in organizations]


@router.get("/organizations/{organization_id}/members")
def list_platform_organization_members(
    organization_id: UUID,
    _actor: ActorContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, str | bool]]:
    rows = db.execute(select(OrganizationMember, User.email, User.display_name).join(
        User, User.id == OrganizationMember.user_id
    ).where(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.status == "ACTIVE",
        User.status == "ACTIVE",
    ).order_by(func.lower(User.email), User.id)).all()
    return [{"user_id": str(member.user_id), "email": email, "display_name": display_name,
             "is_owner": member.is_owner} for member, email, display_name in rows]


@router.patch("/organizations/{organization_id}")
def update_platform_organization_status(
    organization_id: UUID,
    payload: OrganizationStatusUpdate,
    actor: ActorContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    organization = db.scalar(
        select(Organization)
        .where(Organization.id == organization_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    if organization.status not in {"ACTIVE", "SUSPENDED"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization is not provisioned")

    previous_status = organization.status
    organization.status = payload.status
    if previous_status != payload.status:
        db.add(
            AuditEvent(
                id=uuid4(),
                aggregate_type="organization",
                aggregate_id=organization.id,
                event_type="organization.status_changed",
                actor_type="USER",
                actor_id=str(actor.user_id),
                occurred_at=datetime.now(UTC),
                payload={"from": previous_status, "to": payload.status},
            )
        )
    db.commit()
    owner_id = db.scalar(select(OrganizationMember.user_id).where(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.status == "ACTIVE", OrganizationMember.is_owner.is_(True),
    ).limit(1))
    return _organization_summary(organization, owner_id)
