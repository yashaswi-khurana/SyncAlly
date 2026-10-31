"""Poll outbox_events and relay committed-agreement events to Temporal.

Claims commit durable attempt evidence and a bounded lease under the demo
reset coordination lock. External calls run without a database transaction.
Expired leases can be reclaimed after a crash; fenced outcomes cannot overwrite
a newer claim. Temporal's stable workflow and notification IDs handle redelivery.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from random import uniform

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from syncally.application.outbox import (
    DealWorkflowStarter,
    OutboxDispatchResult,
    PendingOutboxEvent,
    dispatch_outbox_event,
)
from syncally.application.payments import (
    PAYMENT_INTENT_AUTHORIZED_EVENT_TYPE,
    PAYPAL_WEBHOOK_RECONCILIATION_EVENT_TYPE,
)
from syncally.infrastructure.demo_lifecycle import lock_outbox_dispatch
from syncally.infrastructure.models import OutboxEvent
from syncally.operations import Operation, log_operation

logger = logging.getLogger(__name__)
_DISPATCH_LEASE = timedelta(minutes=5)

# This dispatcher only knows how to talk to Temporal: a different event type
# it has never heard of still gets claimed and permanently failed (there's no
# one else coming for it). The payment worker owns these event types, so this
# dispatcher must leave them PENDING.
_NOT_HANDLED_BY_THIS_DISPATCHER = (
    PAYMENT_INTENT_AUTHORIZED_EVENT_TYPE,
    PAYPAL_WEBHOOK_RECONCILIATION_EVENT_TYPE,
)


def _claim_statement(*, now: datetime | None = None):
    return (
        select(OutboxEvent)
        .where(OutboxEvent.status == "PENDING")
        .where(OutboxEvent.event_type.not_in(_NOT_HANDLED_BY_THIS_DISPATCHER))
        .where(or_(OutboxEvent.next_attempt_at.is_(None), OutboxEvent.next_attempt_at <= (now or datetime.now(UTC))))
        .order_by(OutboxEvent.created_at, OutboxEvent.id)
        .limit(1)
    )


def claim_next_pending_event(db: Session, *, now: datetime | None = None) -> OutboxEvent | None:
    stmt = _claim_statement(now=now)
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)
    return db.scalar(stmt.execution_options(populate_existing=True))


def apply_dispatch_result(
    row: OutboxEvent, result: OutboxDispatchResult, *, now: datetime | None = None
) -> None:
    """Write one dispatch outcome onto its outbox row (no commit)."""
    if result.delivered:
        row.status = "DELIVERED"
        row.delivered_at = now or datetime.now(UTC)
        row.error_detail = None
        row.next_attempt_at = None
    elif result.permanent_failure:
        row.status = "FAILED"
        row.error_detail = result.error_detail
        row.next_attempt_at = None
    else:
        row.retry_count += 1
        row.error_detail = result.error_detail
        # Persist bounded exponential backoff with jitter so other rows can run
        # and a dispatcher restart does not reset this event's retry schedule.
        delay = min(300, 2 ** min(row.retry_count, 9))
        row.next_attempt_at = (now or datetime.now(UTC)) + timedelta(seconds=uniform(delay / 2, delay))


def dispatch_one_pending_event(
    db: Session, starter: DealWorkflowStarter, *, now: datetime | None = None
) -> bool:
    """Claim and dispatch one pending row. Returns False when none are pending."""
    now = now or datetime.now(UTC)
    lock_outbox_dispatch(db)
    row = claim_next_pending_event(db, now=now)
    if row is None:
        db.commit()
        return False

    db.expunge(row)
    lease_until = now + _DISPATCH_LEASE
    claimed_id = db.scalar(
        update(OutboxEvent)
        .where(
            OutboxEvent.id == row.id,
            OutboxEvent.status == "PENDING",
            or_(OutboxEvent.next_attempt_at.is_(None), OutboxEvent.next_attempt_at <= now),
        )
        .values(dispatch_started_at=now, next_attempt_at=lease_until)
        .returning(OutboxEvent.id)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    if claimed_id is None:
        return False
    row.dispatch_started_at = now
    row.next_attempt_at = lease_until

    result = dispatch_outbox_event(
        PendingOutboxEvent(id=row.id, event_type=row.event_type, payload=row.payload),
        starter,
    )
    apply_dispatch_result(row, result, now=now)
    completed_id = db.scalar(
        update(OutboxEvent)
        .where(
            OutboxEvent.id == row.id,
            OutboxEvent.status == "PENDING",
            OutboxEvent.dispatch_started_at == now,
            OutboxEvent.next_attempt_at == lease_until,
        )
        .values(
            status=row.status, retry_count=row.retry_count,
            delivered_at=row.delivered_at, next_attempt_at=row.next_attempt_at,
            error_detail=row.error_detail,
        )
        .returning(OutboxEvent.id)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    if completed_id is None:
        return True
    fields = dict(
        outbox_event_id=row.id,
        deal_id=row.payload.get("deal_id") if isinstance(row.payload, Mapping) else None,
        event_type=row.event_type,
        status=row.status,
        retry_count=row.retry_count,
        next_attempt_at=row.next_attempt_at,
        failure_kind="PERMANENT" if result.permanent_failure else "TRANSIENT" if not result.delivered else None,
    )
    level = {"FAILED": logging.ERROR, "PENDING": logging.WARNING}.get(fields["status"], logging.INFO)
    log_operation(logger, Operation.OUTBOX_COMPLETED, level=level, **fields)
    return True


def dispatch_pending_outbox_events(
    session_factory: Callable[[], Session], starter: DealWorkflowStarter, *, batch_size: int
) -> int:
    """Dispatch up to ``batch_size`` pending rows, one transaction per row."""
    dispatched = 0
    for _ in range(batch_size):
        with session_factory() as db:
            if not dispatch_one_pending_event(db, starter):
                break
        dispatched += 1
    return dispatched
