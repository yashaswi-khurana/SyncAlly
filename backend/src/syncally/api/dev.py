"""Development-only endpoints for role switching and demo data reset."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

# Reuse the production login pipeline so dev tokens cannot drift from real claims or TTLs.
from syncally.api.auth import TokenResponse, _issue_tokens
from syncally.cli.seed_demo import DEMO_IDENTITIES, seed_demo_data
from syncally.config import settings
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import (
    AgreementVersion,
    Approval,
    AuditEvent,
    Base,
    Constraint,
    Conversation,
    Deal,
    Message,
    NegotiationSession,
    Obligation,
    OutboxEvent,
    PaymentIntent,
    PaymentMilestone,
    Proposal,
    User,
    WebhookEvent,
)

_DEMO_PASSWORDS = (None, None)
_DEMO_ROLE_EMAILS = {
    "BUYER": DEMO_IDENTITIES[0].email,
    "SELLER": DEMO_IDENTITIES[1].email,
    # Both seeded demo users are organization admins and there is no separate
    # admin identity, so ADMIN resolves deterministically to the buyer account.
    "ADMIN": DEMO_IDENTITIES[0].email,
}

# Child rows must be removed before the rows they reference.
_DELETE_ORDER = (
    ("webhook_events", WebhookEvent),
    ("payment_intents", PaymentIntent),
    ("payment_milestones", PaymentMilestone),
    ("obligations", Obligation),
    ("approvals", Approval),
    ("agreement_versions", AgreementVersion),
    ("proposals", Proposal),
    ("negotiation_sessions", NegotiationSession),
    ("constraints", Constraint),
    ("messages", Message),
    ("conversations", Conversation),
    ("outbox_events", OutboxEvent),
    ("audit_events", AuditEvent),
    ("deals", Deal),
)


def _require_dev_environment() -> None:
    """Fail closed unless explicitly enabled in development and test."""
    if not settings.enable_dev_endpoints or not settings.is_local_environment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Development endpoints require ENABLE_DEV_ENDPOINTS=true "
                "in a development or test environment"
            ),
        )


router = APIRouter(
    prefix="/dev",
    tags=["development"],
    dependencies=[Depends(_require_dev_environment)],
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


def _missing_demo_emails(db: Session) -> list[str]:
    missing: list[str] = []
    for identity in DEMO_IDENTITIES:
        # Inactive identities are still repairable by the seed; only a missing
        # password would make seed_demo_data prompt interactively.
        user = db.scalar(select(User).where(User.email == identity.email))
        if user is None or not user.password_hash:
            missing.append(identity.email)
    return missing


def _require_seeded_demo_identities(db: Session) -> None:
    if _missing_demo_emails(db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Demo identities are not seeded. Run "
                "`python -m syncally.cli.seed_demo` from backend/ first."
            ),
        )


def _delete_all(db: Session, model: type[Base]) -> int:
    count = int(db.scalar(select(func.count()).select_from(model)) or 0)
    db.execute(delete(model))
    return count


@router.post("/switch-role", response_model=TokenResponse)
def switch_role(
    payload: DevRoleSwitchRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Issue valid tokens for the seeded demo user representing the target role."""
    _require_dev_environment()
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
    """Clear ALL deal-domain data in the configured database, then re-seed demo data.

    This is not scoped to demo organizations: it unconditionally deletes every
    row in the deal domain, including all ``audit_events`` and ``outbox_events``
    for every organization in this database. Only the demo identities and
    organizations are restored afterwards. Use this only against a disposable
    local database; running it on a shared development or QA database destroys
    unrelated scenarios and the audit trail.
    """
    _require_dev_environment()
    _require_seeded_demo_identities(db)

    deleted = {name: _delete_all(db, model) for name, model in _DELETE_ORDER}
    seed_demo_data(db, _DEMO_PASSWORDS, allow_prompt=False)
    db.commit()
    return DevResetResponse(
        status="success",
        message="All local deal data cleared; demo identities and organizations restored.",
        deleted=deleted,
    )
