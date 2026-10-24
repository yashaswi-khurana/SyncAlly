"""Development-only endpoints for role switching and demo data reset."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import and_, delete, func, or_, select
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
    Organization,
    OutboxEvent,
    PaymentIntent,
    PaymentMilestone,
    Proposal,
    User,
    WebhookEvent,
)

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
        # A missing password would make seed_demo_data prompt interactively.
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


def _demo_organization_ids(db: Session) -> list[UUID]:
    names = [identity.organization_name for identity in DEMO_IDENTITIES]
    return list(
        db.scalars(
            select(Organization.id).where(
                Organization.legal_name.in_(names),
                Organization.country_code == "US",
            )
        )
    )


def _related_ids(
    db: Session, model: type[Base], column: Any, values: list[UUID]
) -> list[UUID]:
    if not values:
        return []
    return list(db.scalars(select(model.id).where(column.in_(values))))


def _aggregate_scope(
    model: type[Base],
    deal_ids: list[UUID],
    agreement_ids: list[UUID],
    payment_intent_ids: list[UUID],
) -> Any:
    return or_(
        and_(model.aggregate_type == "deal", model.aggregate_id.in_(deal_ids)),
        and_(
            model.aggregate_type == "agreement",
            model.aggregate_id.in_(agreement_ids),
        ),
        and_(
            model.aggregate_type == "payment_intent",
            model.aggregate_id.in_(payment_intent_ids),
        ),
    )


def _delete_scoped(db: Session, model: type[Base], *criteria: Any) -> int:
    count = int(db.scalar(select(func.count()).select_from(model).where(*criteria)) or 0)
    if count:
        db.execute(delete(model).where(*criteria))
    return count


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
    """Clear deal data for the seeded demo organizations, then re-seed demo identities.

    A deal is in scope only when both its buyer and seller are the seeded demo
    organizations. Deals involving any non-demo organization, and their audit and
    outbox rows, are left untouched.
    """
    _require_seeded_demo_identities(db)

    organization_ids = _demo_organization_ids(db)
    if organization_ids:
        deal_ids = list(
            db.scalars(
                select(Deal.id).where(
                    Deal.buyer_organization_id.in_(organization_ids),
                    Deal.seller_organization_id.in_(organization_ids),
                )
            )
        )
    else:
        deal_ids = []

    agreement_ids = _related_ids(
        db, AgreementVersion, AgreementVersion.deal_id, deal_ids
    )
    conversation_ids = _related_ids(db, Conversation, Conversation.deal_id, deal_ids)
    payment_intent_ids = _related_ids(db, PaymentIntent, PaymentIntent.deal_id, deal_ids)

    # Child rows must be removed before the rows they reference.
    deleted: dict[str, int] = {}
    deleted["webhook_events"] = _delete_scoped(
        db, WebhookEvent, WebhookEvent.payment_intent_id.in_(payment_intent_ids)
    )
    deleted["payment_intents"] = _delete_scoped(
        db, PaymentIntent, PaymentIntent.deal_id.in_(deal_ids)
    )
    deleted["payment_milestones"] = _delete_scoped(
        db, PaymentMilestone, PaymentMilestone.deal_id.in_(deal_ids)
    )
    deleted["obligations"] = _delete_scoped(
        db, Obligation, Obligation.deal_id.in_(deal_ids)
    )
    deleted["approvals"] = _delete_scoped(db, Approval, Approval.deal_id.in_(deal_ids))
    deleted["agreement_versions"] = _delete_scoped(
        db, AgreementVersion, AgreementVersion.deal_id.in_(deal_ids)
    )
    deleted["proposals"] = _delete_scoped(db, Proposal, Proposal.deal_id.in_(deal_ids))
    deleted["negotiation_sessions"] = _delete_scoped(
        db, NegotiationSession, NegotiationSession.deal_id.in_(deal_ids)
    )
    deleted["constraints"] = _delete_scoped(
        db, Constraint, Constraint.deal_id.in_(deal_ids)
    )
    deleted["messages"] = _delete_scoped(
        db, Message, Message.conversation_id.in_(conversation_ids)
    )
    deleted["conversations"] = _delete_scoped(
        db, Conversation, Conversation.deal_id.in_(deal_ids)
    )
    deleted["outbox_events"] = _delete_scoped(
        db,
        OutboxEvent,
        _aggregate_scope(OutboxEvent, deal_ids, agreement_ids, payment_intent_ids),
    )
    deleted["audit_events"] = _delete_scoped(
        db,
        AuditEvent,
        _aggregate_scope(AuditEvent, deal_ids, agreement_ids, payment_intent_ids),
    )
    deleted["deals"] = _delete_scoped(db, Deal, Deal.id.in_(deal_ids))

    seed_demo_data(db, (None, None))
    db.commit()
    return DevResetResponse(
        status="success",
        message="Demo deal data cleared; demo identities and organizations restored.",
        deleted=deleted,
    )
