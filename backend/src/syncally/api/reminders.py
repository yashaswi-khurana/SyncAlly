"""FastAPI routes for obligation reminders."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
from syncally.application.agreements import (
    AgreementAccessDenied,
    AmbiguousAgreementOrganization,
    resolve_party_organization,
)
from syncally.application.identity import ActorContext
from syncally.application.reminders import (
    ReminderAccessDenied,
    dispatch_due_reminders,
    list_deal_reminders,
    schedule_deal_reminders,
)
from syncally.domain.reminders.reminder import (
    DealReminder,
    SuppressionReason,
)
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models.deals import Deal
from syncally.infrastructure.repositories.reminders import SqlAlchemyReminderRepository

router = APIRouter(prefix="/deals/{deal_id}/reminders", tags=["reminders"])


class ReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deal_id: UUID
    scope: str
    reference_id: UUID
    recipient_organization_id: UUID
    recipient_user_id: UUID | None = None
    status: str
    scheduled_for: datetime
    due_at: datetime
    recurrence_cap: int
    recurrence_count: int
    deduplication_key: str
    channel: str
    next_attempt_at: datetime | None = None
    delivered_at: datetime | None = None
    suppressed_at: datetime | None = None
    suppression_reason: str | None = None
    error_detail: str | None = None
    version: int
    created_at: datetime
    updated_at: datetime


def _to_response(r: DealReminder) -> ReminderResponse:
    return ReminderResponse(
        id=r.id,
        deal_id=r.deal_id,
        scope=r.scope.value,
        reference_id=r.reference_id,
        recipient_organization_id=r.recipient_organization_id,
        recipient_user_id=r.recipient_user_id,
        status=r.status.value,
        scheduled_for=r.scheduled_for,
        due_at=r.due_at,
        recurrence_cap=r.recurrence_cap,
        recurrence_count=r.recurrence_count,
        deduplication_key=r.deduplication_key,
        channel=r.channel.value,
        next_attempt_at=r.next_attempt_at,
        delivered_at=r.delivered_at,
        suppressed_at=r.suppressed_at,
        suppression_reason=r.suppression_reason.value if r.suppression_reason else None,
        error_detail=r.error_detail,
        version=r.version,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


def _resolve_actor_deal_org(
    deal: Deal | None,
    actor: ActorContext,
    requested_org_id: UUID | None = None,
) -> UUID:
    if deal is None or not actor.can_access_deal(deal):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found",
        )
    try:
        return resolve_party_organization(actor, deal, requested_org_id)
    except AgreementAccessDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except AmbiguousAgreementOrganization as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[ReminderResponse])
def get_deal_reminders(
    deal_id: UUID,
    organization_id: UUID | None = Query(default=None),
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[ReminderResponse]:
    """List reminders for a deal.

    Counterparty privacy: viewers only see reminders scoped to their own active
    organization, never counterparty-internal reminders.
    """
    deal = db.get(Deal, deal_id)
    target_org = _resolve_actor_deal_org(deal, actor, organization_id)

    try:
        reminders = list_deal_reminders(db, deal_id, viewer_organization_id=target_org)
        return [_to_response(r) for r in reminders]
    except ReminderAccessDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.post("/sync", response_model=list[ReminderResponse])
def sync_reminders(
    deal_id: UUID,
    organization_id: UUID | None = Query(default=None),
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[ReminderResponse]:
    """Sync and schedule reminders for outstanding obligations on the deal."""
    deal = db.get(Deal, deal_id)
    target_org = _resolve_actor_deal_org(deal, actor, organization_id)

    schedule_deal_reminders(db, deal_id)
    db.commit()
    reminders = list_deal_reminders(db, deal_id, viewer_organization_id=target_org)
    return [_to_response(r) for r in reminders]


@router.post("/dispatch", response_model=list[ReminderResponse])
def trigger_dispatch(
    deal_id: UUID,
    organization_id: UUID | None = Query(default=None),
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[ReminderResponse]:
    """Dispatch due reminders, strictly verifying truth and resolved/superseded facts."""
    deal = db.get(Deal, deal_id)
    target_org = _resolve_actor_deal_org(deal, actor, organization_id)

    dispatched = dispatch_due_reminders(db, deal_id=deal_id)
    db.commit()
    return [_to_response(r) for r in dispatched if r.recipient_organization_id == target_org]


@router.post("/{reminder_id}/suppress", response_model=ReminderResponse)
def suppress_reminder(
    deal_id: UUID,
    reminder_id: UUID,
    organization_id: UUID | None = Query(default=None),
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> ReminderResponse:
    """Allow an authorized recipient to dismiss/suppress a reminder."""
    deal = db.get(Deal, deal_id)
    target_org = _resolve_actor_deal_org(deal, actor, organization_id)

    repo = SqlAlchemyReminderRepository(db)
    reminder = repo.get(reminder_id)
    if reminder is None or reminder.deal_id != deal_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found",
        )
    if reminder.recipient_organization_id != target_org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Actor organization does not own this reminder",
        )

    now = datetime.now(UTC)
    reminder.mark_suppressed(SuppressionReason.RESOLVED, now)
    saved = repo.save(reminder)
    db.commit()
    return _to_response(saved)
