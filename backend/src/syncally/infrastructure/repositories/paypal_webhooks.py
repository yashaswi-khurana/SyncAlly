"""Durably accept verified PayPal invoice webhook events."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syncally.application.payments import PAYPAL_WEBHOOK_RECONCILIATION_EVENT_TYPE
from syncally.infrastructure.models import OutboxEvent, PaymentIntent, WebhookEvent


def record_paypal_webhook_event(db: Session, event: Mapping[str, Any]) -> bool:
    """Save an event once and atomically queue reconciliation for a known invoice.

    Returns False for a delivery already recorded under the same PayPal event ID.
    """
    event_id = event["id"]
    event_type = event["event_type"]
    invoice_id = event["resource"]["id"]
    existing = db.scalar(
        select(WebhookEvent.id).where(
            WebhookEvent.provider == "PAYPAL",
            WebhookEvent.provider_event_id == event_id,
        )
    )
    if existing is not None:
        return False

    intent = db.scalar(
        select(PaymentIntent).where(
            PaymentIntent.provider == "PAYPAL",
            PaymentIntent.provider_invoice_id == invoice_id,
        )
    )
    webhook = WebhookEvent(
        provider="PAYPAL",
        provider_event_id=event_id,
        event_type=event_type,
        # The signature is already verified and reconciliation reads PayPal's
        # current state. Keep only identifiers; the provider event can contain
        # payer email and transaction details that are not needed here.
        raw_payload={
            "id": event_id,
            "event_type": event_type,
            "resource": {"id": invoice_id},
        },
        payment_intent_id=intent.id if intent is not None else None,
        processed=intent is None,
    )
    db.add(webhook)
    db.flush()
    if intent is not None:
        db.add(
            OutboxEvent(
                aggregate_type="payment_intent",
                aggregate_id=intent.id,
                event_type=PAYPAL_WEBHOOK_RECONCILIATION_EVENT_TYPE,
                payload={
                    "payment_intent_id": str(intent.id),
                    "webhook_event_id": str(webhook.id),
                },
                status="PENDING",
                retry_count=0,
            )
        )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        duplicate = db.scalar(
            select(WebhookEvent.id).where(
                WebhookEvent.provider == "PAYPAL",
                WebhookEvent.provider_event_id == event_id,
            )
        )
        if duplicate is not None:
            return False
        raise
    return True
