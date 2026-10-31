"""Development-only endpoints for role switching and demo data reset."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

# Reuse the production login pipeline so dev tokens cannot drift from real claims or TTLs.
from syncally.api.auth import TokenResponse, _decode_token, _issue_tokens, bearer_scheme
from syncally.application.identity import ActorContext
from syncally.application.payment_processing import PaymentNeedsAction
from syncally.cli.seed_demo import DEMO_IDENTITIES, DemoCollisionError, seed_demo_data
from syncally.config import settings
from syncally.infrastructure.database import get_db
from syncally.infrastructure.identity import resolve_actor
from syncally.infrastructure.models import (
    OrganizationMember,
    User,
)
from syncally.infrastructure.repositories.offline_payments import queue_simulated_reconciliation

_LOCAL_ENVIRONMENTS = frozenset({"development", "test"})
_DEMO_ROLE_EMAILS = {
    "BUYER": DEMO_IDENTITIES[0].email,
    "SELLER": DEMO_IDENTITIES[1].email,
    # Both seeded demo users are organization admins and there is no separate
    # admin identity, so ADMIN resolves deterministically to the buyer account.
    "ADMIN": DEMO_IDENTITIES[0].email,
}


def _require_dev_environment() -> None:
    """Fail closed unless the application is running in development or test."""
    if settings.app_env.strip().lower() not in _LOCAL_ENVIRONMENTS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Development endpoints are disabled outside development and test",
        )


def _require_demo_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> ActorContext:
    """Require a bearer token belonging to an active seeded demo administrator."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    actor = resolve_actor(db, _decode_token(credentials.credentials))
    if actor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive or does not exist",
            headers={"WWW-Authenticate": "Bearer"},
        )

    has_demo_admin_membership = db.scalar(
        select(User.id)
        .join(OrganizationMember, OrganizationMember.user_id == User.id)
        .where(
            User.id == actor.user_id,
            User.email.in_([identity.email for identity in DEMO_IDENTITIES]),
            User.status == "ACTIVE",
            OrganizationMember.organization_id.in_(actor.organization_ids),
            OrganizationMember.status == "ACTIVE",
            OrganizationMember.role == "ADMIN",
        )
        .limit(1)
    )
    if has_demo_admin_membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An active demo administrator session is required",
        )
    return actor


router = APIRouter(
    prefix="/dev",
    tags=["development"],
    dependencies=[Depends(_require_dev_environment), Depends(_require_demo_admin)],
)


class DevRoleSwitchRequest(BaseModel):
    target_role: Literal["BUYER", "SELLER", "ADMIN"]

    @field_validator("target_role", mode="before")
    @classmethod
    def normalize_target_role(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value


class DevResetResponse(BaseModel):
    status: str
    message: str
    deleted: dict[str, int]


class SimulatePaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(min_length=1, max_length=256, pattern=r"\S")
    expected_version: int = Field(ge=0, strict=True)
    outcome: Literal["PENDING", "PARTIALLY_PAID", "PAID"]
    paid_amount: str = Field(min_length=1, max_length=64)


@router.post("/payments/{intent_id}/simulate-reconciliation", status_code=202)
def simulate_payment(intent_id: UUID, payload: SimulatePaymentRequest,
                     actor: ActorContext = Depends(_require_demo_admin), db: Session = Depends(get_db)) -> dict:
    try:
        event = queue_simulated_reconciliation(db, intent_id, user_id=actor.user_id, **payload.model_dump())
        return {"event_id": str(event.id), "intent_id": str(intent_id), "execution_mode": "OFFLINE_DEMO", "status": "QUEUED"}
    except PaymentNeedsAction as error:
        code = 404 if error.code == "PAYMENT_INTENT_NOT_FOUND" else 403 if error.code == "PAYMENT_SIMULATION_FORBIDDEN" else 422 if error.code == "PAYMENT_RECONCILIATION_REJECTED" else 409
        raise HTTPException(status_code=code, detail=error.detail) from error


@router.post("/switch-role", response_model=TokenResponse)
def switch_role(
    payload: DevRoleSwitchRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Issue valid tokens for the seeded demo user representing the target role."""
    email = _DEMO_ROLE_EMAILS[payload.target_role]
    user = db.scalar(select(User).where(User.email == email, User.status == "ACTIVE"))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Demo user for {payload.target_role} is not seeded.",
        )
    return _issue_tokens(db, user.id, datetime.now(UTC))


@router.post("/reset-demo", response_model=DevResetResponse)
def reset_demo(db: Session = Depends(get_db)) -> DevResetResponse:
    """Atomically restore only the explicitly marked curated fixture."""
    try:
        deleted = seed_demo_data(db, reset=True, require_existing_passwords=True)
    except DemoCollisionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return DevResetResponse(
        status="success",
        message="Curated demo draft restored; unmarked deals and passwords preserved.",
        deleted=deleted,
    )
