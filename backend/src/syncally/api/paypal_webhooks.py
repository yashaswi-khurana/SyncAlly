"""PayPal webhook intake: verify first, persist second, reconcile asynchronously."""

from __future__ import annotations

import json
from collections.abc import Mapping

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from syncally.application.payment_processing import PaymentNeedsAction, PaymentRetryableError
from syncally.config import PayPalSettings
from syncally.infrastructure.database import get_db
from syncally.infrastructure.paypal import PayPalSandboxInvoiceProvider
from syncally.infrastructure.repositories.paypal_webhooks import record_paypal_webhook_event

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_PAYPAL_SIGNATURE_HEADERS = (
    "paypal-auth-algo",
    "paypal-cert-url",
    "paypal-transmission-id",
    "paypal-transmission-sig",
    "paypal-transmission-time",
)


def get_paypal_webhook_configuration() -> tuple[PayPalSandboxInvoiceProvider, str]:
    settings = PayPalSettings()
    client_secret = settings.paypal_client_secret.get_secret_value()
    webhook_id = settings.paypal_webhook_id.strip()
    if not settings.paypal_client_id.strip() or not client_secret or not webhook_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PayPal Sandbox webhook verification is not configured.",
        )
    return (
        PayPalSandboxInvoiceProvider(settings.paypal_client_id, client_secret),
        webhook_id,
    )


@router.post("/paypal/invoicing", status_code=status.HTTP_202_ACCEPTED)
async def receive_paypal_invoice_webhook(
    request: Request,
    db: Session = Depends(get_db),
    configuration: tuple[PayPalSandboxInvoiceProvider, str] = Depends(
        get_paypal_webhook_configuration
    ),
) -> dict[str, str]:
    raw_body = await request.body()
    try:
        event = json.loads(raw_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=400, detail="Invalid webhook JSON.") from error
    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail="Invalid webhook event.")

    headers = {name: request.headers.get(name, "") for name in _PAYPAL_SIGNATURE_HEADERS}
    if not all(headers.values()):
        raise HTTPException(status_code=400, detail="Missing PayPal signature headers.")

    provider, webhook_id = configuration
    try:
        verified = provider.verify_webhook_signature(headers, event, webhook_id)
    except PaymentRetryableError as error:
        raise HTTPException(status_code=503, detail=error.detail) from error
    except PaymentNeedsAction as error:
        raise HTTPException(status_code=502, detail=error.detail) from error
    if not verified:
        raise HTTPException(status_code=400, detail="PayPal webhook signature is invalid.")

    event_id = event.get("id")
    event_type = event.get("event_type")
    resource = event.get("resource")
    invoice_id = resource.get("id") if isinstance(resource, Mapping) else None
    if (
        not isinstance(event_id, str)
        or not event_id.strip()
        or len(event_id) > 256
        or not isinstance(event_type, str)
        or not event_type.strip()
        or len(event_type) > 256
        or not isinstance(invoice_id, str)
        or not invoice_id.strip()
        or len(invoice_id) > 256
    ):
        raise HTTPException(status_code=400, detail="Invalid PayPal invoice event fields.")

    try:
        inserted = record_paypal_webhook_event(db, event)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="PayPal webhook could not be saved; PayPal may retry delivery.",
        ) from error
    return {"status": "accepted" if inserted else "duplicate"}
