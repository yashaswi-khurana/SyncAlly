"""Platform management that deliberately exposes organization metadata only."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from syncally.api.auth import require_system_admin
from syncally.application.identity import ActorContext
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import AuditEvent, Organization

router = APIRouter(prefix="/platform", tags=["platform administration"])


class OrganizationStatusUpdate(BaseModel):
    status: Literal["ACTIVE", "SUSPENDED"]


def _organization_summary(organization: Organization) -> dict[str, str]:
    return {
        "id": str(organization.id),
        "legal_name": organization.legal_name,
        "country_code": organization.country_code,
        "status": organization.status,
        "created_at": organization.created_at.isoformat() if organization.created_at else "",
    }


@router.get("/organizations")
def list_platform_organizations(
    _actor: ActorContext = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, str]]:
    organizations = db.scalars(
        select(Organization).order_by(func.lower(Organization.legal_name), Organization.id)
    ).all()
    return [_organization_summary(organization) for organization in organizations]


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
    return _organization_summary(organization)
