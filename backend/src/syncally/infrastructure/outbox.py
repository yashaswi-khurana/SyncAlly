"""Poll outbox_events and relay committed-agreement events to Temporal.

Each pending row is claimed, dispatched, and marked delivered (or left
pending for retry) in its own transaction - never a lease/claimed state that
could get stuck if the process dies, and never a batch-wide transaction held
open across a Temporal call. On Postgres, ``FOR UPDATE SKIP LOCKED`` lets two
dispatcher processes split a backlog without blocking each other; on SQLite
(unit tests) that clause doesn't exist, so no lock is taken at all - the real
safety net against double delivery is Temporal's own "already started"
idempotency for the deal's stable workflow ID, not the DB lock.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from random import uniform

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from syncally.application.outbox import (
    DealWorkflowStarter,
    OutboxDispatchResult,
    PendingOutboxEvent,
    dispatch_outbox_event,
)
from syncally.application.payments import PAYMENT_INTENT_AUTHORIZED_EVENT_TYPE
from syncally.infrastructure.models import OutboxEvent

# This dispatcher only knows how to talk to Temporal: a different event type
# it has never heard of still gets claimed and permanently failed (there's no
# one else coming for it). Payment events are the one exception - a future
# payment worker (S7-03) owns those rows, so this dispatcher must leave them
# PENDING rather than claim and kill them first.
_NOT_HANDLED_BY_THIS_DISPATCHER = (PAYMENT_INTENT_AUTHORIZED_EVENT_TYPE,)


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
    return db.scalar(stmt)


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
    row = claim_next_pending_event(db, now=now)
    if row is None:
        return False

    result = dispatch_outbox_event(
        PendingOutboxEvent(id=row.id, event_type=row.event_type, payload=row.payload),
        starter,
    )
    apply_dispatch_result(row, result, now=now)
    db.commit()
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
