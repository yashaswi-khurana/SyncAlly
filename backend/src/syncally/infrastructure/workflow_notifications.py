"""Transactional outbox helpers for private-data-free deal notifications."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from syncally.application.workflow_notifications import NotificationKind
from syncally.infrastructure.models import OutboxEvent


def queue_deal_workflow_notification(
    db: Session,
    *,
    deal_id: UUID,
    record_id: UUID,
    kind: NotificationKind,
) -> None:
    """Persist only identifiers and a fixed kind in the business transaction."""
    db.add(
        OutboxEvent(
            aggregate_type="deal",
            aggregate_id=deal_id,
            event_type="DEAL_NOTIFICATION",
            payload={
                "deal_id": str(deal_id),
                "record_id": str(record_id),
                "kind": kind.value,
            },
        )
    )
