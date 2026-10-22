"""Transactional claims and retry policy for payment authorization events."""

from __future__ import annotations

import logging
import traceback
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from random import uniform
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from syncally.application.payment_processing import (
    PaymentInvoiceNotifier,
    PaymentInvoiceProvider,
    PaymentNeedsAction,
    PaymentProcessingRepository,
    PaymentRetryableError,
    process_payment_intent,
    reconcile_payment_intent,
)
from syncally.application.payments import (
    PAYMENT_INTENT_AUTHORIZED_EVENT_TYPE,
    PAYPAL_WEBHOOK_RECONCILIATION_EVENT_TYPE,
)
from syncally.domain.payments.intent import PaymentIntentStatus
from syncally.infrastructure.models import OutboxEvent

logger = logging.getLogger(__name__)
_PAYMENT_EVENT_LEASE = timedelta(minutes=5)


def _safe_error_location(error: BaseException) -> str:
    frames = traceback.extract_tb(error.__traceback__)[-5:]
    return " -> ".join(f"{frame.name}:{frame.lineno}" for frame in frames) or "unknown location"


@dataclass(frozen=True, slots=True)
class _ClaimedPaymentEvent:
    id: UUID
    event_type: str
    payload: object
    lease_until: datetime


def _claim_statement(now: datetime):
    due_pending = and_(
        OutboxEvent.status == "PENDING",
        or_(OutboxEvent.next_attempt_at.is_(None), OutboxEvent.next_attempt_at <= now),
    )
    expired_processing = and_(
        OutboxEvent.status == "PROCESSING",
        OutboxEvent.next_attempt_at <= now,
    )
    return (
        select(OutboxEvent)
        .where(
            OutboxEvent.event_type.in_(
                (
                    PAYMENT_INTENT_AUTHORIZED_EVENT_TYPE,
                    PAYPAL_WEBHOOK_RECONCILIATION_EVENT_TYPE,
                )
            )
        )
        .where(or_(due_pending, expired_processing))
        .order_by(OutboxEvent.created_at, OutboxEvent.id)
        .limit(1)
    )


def claim_next_payment_event(
    db: Session, *, now: datetime | None = None
) -> _ClaimedPaymentEvent | None:
    """Persist a lease, then return a detached event for external processing."""
    now = now or datetime.now(UTC)
    statement = _claim_statement(now)
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        statement = statement.with_for_update(skip_locked=True)
    row = db.scalar(statement)
    if row is None:
        return None
    lease_until = now + _PAYMENT_EVENT_LEASE
    payload = dict(row.payload) if isinstance(row.payload, Mapping) else row.payload
    event = _ClaimedPaymentEvent(
        id=row.id,
        event_type=row.event_type,
        payload=payload,
        lease_until=lease_until,
    )
    row.status = "PROCESSING"
    row.next_attempt_at = lease_until
    db.commit()
    return event


def dispatch_one_payment_event(
    session_factory: Callable[[], Session],
    repository: PaymentProcessingRepository,
    provider: PaymentInvoiceProvider,
    *,
    notifier: PaymentInvoiceNotifier | None = None,
    now: datetime | None = None,
) -> bool:
    """Claim one event, call PayPal outside database transactions, and persist its result."""
    with session_factory() as db:
        event = claim_next_payment_event(db, now=now)
    if event is None:
        return False

    try:
        if not isinstance(event.payload, Mapping):
            raise PaymentNeedsAction(
                "PAYMENT_OUTBOX_PAYLOAD_INVALID",
                "The payment outbox payload is invalid; inspect the event manually.",
            )
        raw_intent_id = event.payload.get("payment_intent_id")
        if not isinstance(raw_intent_id, str):
            raise PaymentNeedsAction(
                "PAYMENT_OUTBOX_PAYLOAD_INVALID",
                "The payment outbox payload is missing its intent ID.",
            )
        try:
            payment_intent_id = UUID(raw_intent_id)
        except ValueError as error:
            raise PaymentNeedsAction(
                "PAYMENT_OUTBOX_PAYLOAD_INVALID",
                "The payment outbox payload contains an invalid intent ID.",
            ) from error
        if event.event_type == PAYMENT_INTENT_AUTHORIZED_EVENT_TYPE:
            process_payment_intent(payment_intent_id, repository, provider)
            if notifier is not None:
                work = repository.load(payment_intent_id)
                if work is None:
                    raise PaymentNeedsAction(
                        "PAYMENT_INTENT_NOT_FOUND",
                        "The payment intent disappeared before its invoice email could be sent.",
                    )
                if work.status in {
                    PaymentIntentStatus.SENT,
                    PaymentIntentStatus.PENDING,
                    PaymentIntentStatus.PARTIALLY_PAID,
                    PaymentIntentStatus.PAID,
                }:
                    if not work.provider_invoice_id:
                        raise PaymentNeedsAction(
                            "PAYMENT_PROVIDER_REFERENCE_MISSING",
                            "The PayPal invoice ID is missing; inspect the payment before emailing.",
                        )
                    notice = provider.get_invoice_notice(work.provider_invoice_id)
                    if notice.invoice_number != work.invoice_number or notice.amount != work.amount:
                        raise PaymentNeedsAction(
                            "PAYPAL_INVOICE_NOTICE_MISMATCH",
                            "PayPal invoice details do not match the authorized payment; inspect manually.",
                        )
                    notifier.send_invoice_notice(notice)
        else:
            if event.event_type != PAYPAL_WEBHOOK_RECONCILIATION_EVENT_TYPE:
                raise PaymentNeedsAction(
                    "PAYMENT_OUTBOX_EVENT_UNSUPPORTED",
                    "The payment outbox event type is unsupported; inspect it manually.",
                )
            raw_webhook_id = event.payload.get("webhook_event_id")
            if not isinstance(raw_webhook_id, str):
                raise PaymentNeedsAction(
                    "PAYMENT_OUTBOX_PAYLOAD_INVALID",
                    "The payment outbox payload is missing its webhook event ID.",
                )
            try:
                webhook_event_id = UUID(raw_webhook_id)
            except ValueError as error:
                raise PaymentNeedsAction(
                    "PAYMENT_OUTBOX_PAYLOAD_INVALID",
                    "The payment outbox payload contains an invalid webhook event ID.",
                ) from error
            reconcile_payment_intent(
                payment_intent_id,
                outbox_event_id=event.id,
                webhook_event_id=webhook_event_id,
                lease_until=event.lease_until,
                repository=repository,
                provider=provider,
            )
    except PaymentRetryableError as error:
        _finish_event(
            session_factory,
            event,
            status="PENDING",
            error_detail=error.detail,
            retry=True,
            now=now,
        )
    except PaymentNeedsAction as error:
        logger.error("Payment outbox event %s needs manual action (%s)", event.id, error.code)
        _finish_event(
            session_factory,
            event,
            status="FAILED",
            error_detail=error.detail,
            retry=False,
            now=now,
        )
    except Exception as error:
        # Avoid logging database parameters or provider bodies that may contain
        # private commercial details. The persisted message is intentionally generic.
        logger.error(
            "Payment outbox event %s failed unexpectedly (%s at %s)",
            event.id,
            type(error).__name__,
            _safe_error_location(error),
        )
        _finish_event(
            session_factory,
            event,
            status="PENDING",
            error_detail="Payment processing failed unexpectedly; the event will be retried.",
            retry=True,
            now=now,
        )
    else:
        _finish_event(
            session_factory,
            event,
            status="DELIVERED",
            error_detail=None,
            retry=False,
            now=now,
        )
    return True


def dispatch_pending_payment_events(
    session_factory: Callable[[], Session],
    repository: PaymentProcessingRepository,
    provider: PaymentInvoiceProvider,
    *,
    batch_size: int,
    notifier: PaymentInvoiceNotifier | None = None,
) -> int:
    processed = 0
    for _ in range(batch_size):
        if not dispatch_one_payment_event(
            session_factory,
            repository,
            provider,
            notifier=notifier,
        ):
            break
        processed += 1
    return processed


def _finish_event(
    session_factory: Callable[[], Session],
    event: _ClaimedPaymentEvent,
    *,
    status: str,
    error_detail: str | None,
    retry: bool,
    now: datetime | None,
) -> None:
    now = now or datetime.now(UTC)
    with session_factory() as db:
        row = db.scalar(
            select(OutboxEvent).where(
                OutboxEvent.id == event.id,
                OutboxEvent.status == "PROCESSING",
                OutboxEvent.next_attempt_at == event.lease_until,
            )
        )
        if row is None:
            return
        row.status = status
        row.error_detail = error_detail
        if status == "DELIVERED":
            row.delivered_at = now
            row.next_attempt_at = None
        elif retry:
            row.retry_count += 1
            delay = min(300, 2 ** min(row.retry_count, 9))
            row.next_attempt_at = now + timedelta(seconds=uniform(delay / 2, delay))
        else:
            row.next_attempt_at = None
        db.commit()
