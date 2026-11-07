"""SQLAlchemy repository for durable deal reminders."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from syncally.domain.reminders.reminder import (
    DealReminder,
    ReminderChannel,
    ReminderScope,
    ReminderStatus,
    SuppressionReason,
    ensure_utc,
)
from syncally.domain.shared.identifiers import DealId, OrganizationId, UserId
from syncally.infrastructure.models.reminders import DealReminderModel
from syncally.infrastructure.repositories._timestamps import as_utc


def _to_domain(model: DealReminderModel) -> DealReminder:
    """Map an ORM model to a domain entity with strictly UTC datetimes."""
    return DealReminder(
        id=model.id,
        deal_id=DealId(model.deal_id),
        scope=ReminderScope(model.scope),
        reference_id=model.reference_id,
        recipient_organization_id=OrganizationId(model.recipient_organization_id),
        recipient_user_id=UserId(model.recipient_user_id) if model.recipient_user_id else None,
        status=ReminderStatus(model.status),
        scheduled_for=as_utc(model.scheduled_for),
        due_at=as_utc(model.due_at),
        recurrence_cap=model.recurrence_cap,
        recurrence_count=model.recurrence_count,
        deduplication_key=model.deduplication_key,
        channel=ReminderChannel(model.channel),
        retry_count=model.retry_count,
        next_attempt_at=as_utc(model.next_attempt_at) if model.next_attempt_at else None,
        delivered_at=as_utc(model.delivered_at) if model.delivered_at else None,
        suppressed_at=as_utc(model.suppressed_at) if model.suppressed_at else None,
        suppression_reason=SuppressionReason(model.suppression_reason)
        if model.suppression_reason
        else None,
        error_detail=model.error_detail,
        version=model.version,
        created_at=as_utc(model.created_at),
        updated_at=as_utc(model.updated_at),
    )


class SqlAlchemyReminderRepository:
    """Transactional persistence for DealReminder entities."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def save(self, reminder: DealReminder) -> DealReminder:
        """Insert or update a reminder row."""
        model = self._db.get(DealReminderModel, reminder.id)
        if model is None:
            model = DealReminderModel(
                id=reminder.id,
                deal_id=reminder.deal_id,
                scope=reminder.scope.value,
                reference_id=reminder.reference_id,
                recipient_organization_id=reminder.recipient_organization_id,
                recipient_user_id=reminder.recipient_user_id,
                status=reminder.status.value,
                scheduled_for=reminder.scheduled_for,
                due_at=reminder.due_at,
                recurrence_cap=reminder.recurrence_cap,
                recurrence_count=reminder.recurrence_count,
                deduplication_key=reminder.deduplication_key,
                channel=reminder.channel.value,
                retry_count=reminder.retry_count,
                next_attempt_at=reminder.next_attempt_at,
                delivered_at=reminder.delivered_at,
                suppressed_at=reminder.suppressed_at,
                suppression_reason=reminder.suppression_reason.value
                if reminder.suppression_reason
                else None,
                error_detail=reminder.error_detail,
                version=reminder.version,
                created_at=reminder.created_at,
                updated_at=reminder.updated_at,
            )
            self._db.add(model)
        else:
            model.status = reminder.status.value
            model.scheduled_for = reminder.scheduled_for
            model.due_at = reminder.due_at
            model.recurrence_cap = reminder.recurrence_cap
            model.recurrence_count = reminder.recurrence_count
            model.retry_count = reminder.retry_count
            model.next_attempt_at = reminder.next_attempt_at
            model.delivered_at = reminder.delivered_at
            model.suppressed_at = reminder.suppressed_at
            model.suppression_reason = (
                reminder.suppression_reason.value if reminder.suppression_reason else None
            )
            model.error_detail = reminder.error_detail
            model.version = reminder.version
            model.updated_at = reminder.updated_at

        self._db.flush()
        return _to_domain(model)

    def get(self, reminder_id: UUID) -> DealReminder | None:
        """Load a reminder by its primary key."""
        model = self._db.get(DealReminderModel, reminder_id)
        return _to_domain(model) if model is not None else None

    def get_by_deduplication_key(self, deduplication_key: str) -> DealReminder | None:
        """Find an existing reminder by its unique deduplication key."""
        stmt = select(DealReminderModel).where(
            DealReminderModel.deduplication_key == deduplication_key
        )
        model = self._db.scalar(stmt)
        return _to_domain(model) if model is not None else None

    def list_for_deal(
        self, deal_id: UUID, organization_id: UUID | None = None
    ) -> list[DealReminder]:
        """List all reminders for a deal, scoped to an organization for counterparty privacy."""
        stmt = select(DealReminderModel).where(DealReminderModel.deal_id == deal_id)
        if organization_id is not None:
            stmt = stmt.where(DealReminderModel.recipient_organization_id == organization_id)
        stmt = stmt.order_by(DealReminderModel.created_at.desc(), DealReminderModel.id.desc())
        models = self._db.scalars(stmt).all()
        return [_to_domain(m) for m in models]

    def claim_due_reminders(
        self, now: datetime, limit: int = 20, deal_id: UUID | None = None
    ) -> list[DealReminder]:
        """Claim reminders that are due for delivery or retry."""
        now_utc = ensure_utc(now, "now")
        stmt = (
            select(DealReminderModel)
            .where(
                DealReminderModel.status.in_(
                    [ReminderStatus.SCHEDULED.value, ReminderStatus.PENDING.value]
                )
            )
            .where(DealReminderModel.due_at <= now_utc)
            .where(
                (DealReminderModel.next_attempt_at.is_(None))
                | (DealReminderModel.next_attempt_at <= now_utc)
            )
        )
        if deal_id is not None:
            stmt = stmt.where(DealReminderModel.deal_id == deal_id)
        stmt = stmt.order_by(DealReminderModel.due_at.asc(), DealReminderModel.id.asc()).limit(limit)
        if self._db.bind is not None and self._db.bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)

        models = self._db.scalars(stmt).all()
        return [_to_domain(m) for m in models]

    def suppress_active_for_reference(
        self,
        deal_id: UUID,
        scope: ReminderScope,
        reference_id: UUID,
        reason: SuppressionReason,
        now: datetime,
        recipient_organization_id: UUID | None = None,
        recipient_user_id: UUID | None = None,
    ) -> int:
        """Suppress any active (scheduled or pending) reminders for a resolved/superseded reference."""
        now_utc = ensure_utc(now, "now")
        stmt = (
            update(DealReminderModel)
            .where(
                DealReminderModel.deal_id == deal_id,
                DealReminderModel.scope == scope.value,
                DealReminderModel.reference_id == reference_id,
                DealReminderModel.status.in_(
                    [ReminderStatus.SCHEDULED.value, ReminderStatus.PENDING.value]
                ),
            )
        )
        if recipient_organization_id is not None:
            stmt = stmt.where(DealReminderModel.recipient_organization_id == recipient_organization_id)
        if recipient_user_id is not None:
            stmt = stmt.where(DealReminderModel.recipient_user_id == recipient_user_id)
        stmt = stmt.values(
            status=ReminderStatus.SUPPRESSED.value,
            suppressed_at=now_utc,
            suppression_reason=reason.value,
            next_attempt_at=None,
            updated_at=now_utc,
            version=DealReminderModel.version + 1,
        )
        result = self._db.execute(stmt)
        return result.rowcount

    def suppress_active_for_deal(
        self, deal_id: UUID, reason: SuppressionReason, now: datetime
    ) -> int:
        """Suppress all active reminders when a deal reaches a terminal status."""
        now_utc = ensure_utc(now, "now")
        stmt = (
            update(DealReminderModel)
            .where(
                DealReminderModel.deal_id == deal_id,
                DealReminderModel.status.in_(
                    [ReminderStatus.SCHEDULED.value, ReminderStatus.PENDING.value]
                ),
            )
            .values(
                status=ReminderStatus.SUPPRESSED.value,
                suppressed_at=now_utc,
                suppression_reason=reason.value,
                next_attempt_at=None,
                updated_at=now_utc,
                version=DealReminderModel.version + 1,
            )
        )
        result = self._db.execute(stmt)
        return result.rowcount
