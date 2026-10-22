"""Payment invoice processing, independent of PayPal and database details."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from syncally.domain.payments.intent import PaymentIntentStatus
from syncally.domain.shared.money import Money, canonical_decimal

PAYPAL_REQUEST_ID_RETRY_WINDOW = timedelta(days=44)


class PaymentRetryableError(Exception):
    """A provider or infrastructure failure that should be retried later."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)


class PaymentOutcomeUnknown(PaymentRetryableError):
    """A create request may have reached the provider; reconcile before retrying."""


class PaymentNeedsAction(Exception):
    """A permanent failure that requires operator or user intervention."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class PaymentInvoiceLineItem:
    name: str
    description: str | None
    quantity: Decimal
    unit: str
    unit_price: Money


@dataclass(frozen=True, slots=True)
class PaymentInvoiceLookup:
    payment_intent_id: UUID
    invoice_number: str
    reference: str
    amount: Money
    recipient_email: str | None


@dataclass(frozen=True, slots=True)
class PaymentInvoiceRequest:
    payment_intent_id: UUID
    deal_id: UUID
    invoice_number: str
    reference: str
    amount: Money
    seller_business_name: str
    buyer_business_name: str
    buyer_contact_name: str
    buyer_contact_email: str
    line_items: tuple[PaymentInvoiceLineItem, ...]

    @property
    def lookup(self) -> PaymentInvoiceLookup:
        return PaymentInvoiceLookup(
            payment_intent_id=self.payment_intent_id,
            invoice_number=self.invoice_number,
            reference=self.reference,
            amount=self.amount,
            recipient_email=self.buyer_contact_email,
        )

    @property
    def payload_hash(self) -> str:
        """Hash stable request inputs without storing contact or invoice payload data."""
        payload = {
            "schema_version": 1,
            "payment_intent_id": str(self.payment_intent_id),
            "deal_id": str(self.deal_id),
            "invoice_number": self.invoice_number,
            "reference": self.reference,
            "amount": {
                "currency": self.amount.currency,
                "value": canonical_decimal(self.amount.amount),
            },
            "seller_business_name": self.seller_business_name,
            "buyer_business_name": self.buyer_business_name,
            "buyer_contact_name": self.buyer_contact_name,
            "buyer_contact_email": self.buyer_contact_email.casefold(),
            "line_items": [
                {
                    "name": item.name,
                    "description": item.description,
                    "quantity": canonical_decimal(item.quantity),
                    "unit": item.unit,
                    "currency": item.unit_price.currency,
                    "unit_price": canonical_decimal(item.unit_price.amount),
                }
                for item in self.line_items
            ],
            "payment_term": "DUE_ON_RECEIPT",
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class PaymentWorkItem:
    payment_intent_id: UUID
    status: PaymentIntentStatus
    amount: Money
    invoice_number: str
    reference: str
    provider_invoice_id: str | None
    request_payload_hash: str | None
    invoice_request: PaymentInvoiceRequest | None
    request_error_code: str | None = None
    request_error_detail: str | None = None
    failure_code: str | None = None
    failure_detail: str | None = None
    provider_create_started_at: datetime | None = None

    @property
    def lookup(self) -> PaymentInvoiceLookup:
        request_is_unchanged = (
            self.invoice_request is not None
            and self.request_payload_hash == self.invoice_request.payload_hash
        )
        return PaymentInvoiceLookup(
            payment_intent_id=self.payment_intent_id,
            invoice_number=self.invoice_number,
            reference=self.reference,
            amount=self.amount,
            recipient_email=(self.invoice_request.buyer_contact_email if request_is_unchanged else None),
        )


class PaymentProcessingRepository(Protocol):
    def load(self, payment_intent_id: UUID) -> PaymentWorkItem | None:
        """Load committed payment and invoice data, closing its DB transaction first."""

    def begin_create(self, payment_intent_id: UUID, request_payload_hash: str) -> None:
        """Persist CREATE_PENDING and the stable request hash before calling PayPal."""

    def mark_create_unknown(self, payment_intent_id: UUID) -> None:
        """Persist that a create may have reached PayPal."""

    def reconcile_create_not_found(self, payment_intent_id: UUID) -> None:
        """Return a verified-not-found CREATE_UNKNOWN intent to AUTHORIZED."""

    def record_provider_created(self, payment_intent_id: UUID, provider_invoice_id: str) -> None:
        """Persist the provider ID before attempting to send the invoice."""

    def mark_sent(self, payment_intent_id: UUID) -> None:
        """Persist that PayPal accepted the send request."""

    def mark_failure(self, payment_intent_id: UUID, code: str, detail: str) -> None:
        """Persist a definitive failure as FAILED."""

    def mark_manual_action(self, payment_intent_id: UUID, code: str, detail: str) -> None:
        """Persist a safe manual-action message while preserving unknown outcomes."""


class PaymentInvoiceProvider(Protocol):
    def find_invoice(self, lookup: PaymentInvoiceLookup) -> str | None:
        """Find an invoice by its stable invoice number and validate its identity."""

    def create_invoice(self, request: PaymentInvoiceRequest) -> str:
        """Create a draft invoice using a stable provider request ID."""

    def send_invoice(self, provider_invoice_id: str, payment_intent_id: UUID) -> None:
        """Send the persisted invoice ID as a separate operation."""


def payment_invoice_number(payment_intent_id: UUID) -> str:
    """Return a stable, non-PII invoice number within PayPal's 25-character limit."""
    encoded_id = base64.urlsafe_b64encode(payment_intent_id.bytes).decode("ascii").rstrip("=")
    return f"SA-{encoded_id}"


def process_payment_intent(
    payment_intent_id: UUID,
    repository: PaymentProcessingRepository,
    provider: PaymentInvoiceProvider,
    *,
    now: datetime | None = None,
) -> None:
    """Create and send one invoice, reconciling every uncertain create before retry."""
    try:
        work = repository.load(payment_intent_id)
    except PaymentNeedsAction as error:
        repository.mark_manual_action(payment_intent_id, error.code, error.detail)
        raise
    if work is None:
        raise PaymentNeedsAction(
            "PAYMENT_INTENT_NOT_FOUND",
            "The authorized payment intent no longer exists; inspect the outbox event.",
        )

    if work.status in {
        PaymentIntentStatus.SENT,
        PaymentIntentStatus.PENDING,
        PaymentIntentStatus.PARTIALLY_PAID,
        PaymentIntentStatus.PAID,
        PaymentIntentStatus.CANCELLED,
    }:
        return
    if work.status is PaymentIntentStatus.FAILED:
        raise PaymentNeedsAction(
            work.failure_code or "PAYMENT_FAILED",
            work.failure_detail or "The payment request needs manual action.",
        )

    if work.status is PaymentIntentStatus.CREATE_PENDING:
        # A restarted worker cannot know whether the process stopped before or
        # after the external POST. Treat it like a timeout and search first.
        repository.mark_create_unknown(payment_intent_id)
        work = repository.load(payment_intent_id)
        if work is None:
            raise PaymentNeedsAction("PAYMENT_INTENT_NOT_FOUND", "Payment intent is unavailable.")

    if work.status is PaymentIntentStatus.CREATE_UNKNOWN:
        try:
            provider_invoice_id = provider.find_invoice(work.lookup)
        except PaymentNeedsAction as error:
            repository.mark_manual_action(payment_intent_id, error.code, error.detail)
            raise
        if provider_invoice_id is not None:
            repository.record_provider_created(payment_intent_id, provider_invoice_id)
            work = repository.load(payment_intent_id)
            if work is None:
                raise PaymentNeedsAction("PAYMENT_INTENT_NOT_FOUND", "Payment intent is unavailable.")
        else:
            if work.invoice_request is None:
                code = work.request_error_code or "PAYMENT_INVOICE_DATA_UNAVAILABLE"
                detail = work.request_error_detail or "Invoice data needs manual action."
                repository.mark_manual_action(payment_intent_id, code, detail)
                raise PaymentNeedsAction(code, detail)
            if (
                work.request_payload_hash is not None
                and work.request_payload_hash != work.invoice_request.payload_hash
            ):
                detail = "Invoice details changed after an uncertain provider create; reconcile manually."
                repository.mark_manual_action(
                    payment_intent_id, "PAYMENT_INVOICE_REQUEST_CHANGED", detail
                )
                raise PaymentNeedsAction("PAYMENT_INVOICE_REQUEST_CHANGED", detail)
            if work.provider_create_started_at is None:
                detail = "The original PayPal create time is unknown; reconcile the invoice manually."
                repository.mark_manual_action(
                    payment_intent_id, "PAYMENT_CREATE_TIME_UNKNOWN", detail
                )
                raise PaymentNeedsAction("PAYMENT_CREATE_TIME_UNKNOWN", detail)
            if _request_id_retry_window_expired(work.provider_create_started_at, now):
                detail = "PayPal's safe request-ID retry window expired; reconcile the invoice manually."
                repository.mark_manual_action(
                    payment_intent_id, "PAYMENT_CREATE_RETRY_WINDOW_EXPIRED", detail
                )
                raise PaymentNeedsAction("PAYMENT_CREATE_RETRY_WINDOW_EXPIRED", detail)
            repository.reconcile_create_not_found(payment_intent_id)
            work = repository.load(payment_intent_id)
            if work is None:
                raise PaymentNeedsAction("PAYMENT_INTENT_NOT_FOUND", "Payment intent is unavailable.")

    if work.status is PaymentIntentStatus.AUTHORIZED:
        if work.invoice_request is None:
            code = work.request_error_code or "PAYMENT_INVOICE_DATA_UNAVAILABLE"
            detail = work.request_error_detail or "Invoice data needs manual action."
            repository.mark_failure(payment_intent_id, code, detail)
            raise PaymentNeedsAction(code, detail)
        if (
            work.provider_create_started_at is not None
            and _request_id_retry_window_expired(work.provider_create_started_at, now)
        ):
            detail = "PayPal's safe request-ID retry window expired; reconcile the invoice manually."
            repository.mark_manual_action(
                payment_intent_id, "PAYMENT_CREATE_RETRY_WINDOW_EXPIRED", detail
            )
            raise PaymentNeedsAction("PAYMENT_CREATE_RETRY_WINDOW_EXPIRED", detail)
        request_hash = work.invoice_request.payload_hash
        try:
            repository.begin_create(payment_intent_id, request_hash)
        except PaymentNeedsAction as error:
            repository.mark_manual_action(payment_intent_id, error.code, error.detail)
            raise
        try:
            provider_invoice_id = provider.create_invoice(work.invoice_request)
        except PaymentOutcomeUnknown:
            repository.mark_create_unknown(payment_intent_id)
            raise
        except PaymentRetryableError:
            # Conservatively reconcile before another create even when the
            # client cannot prove whether PayPal processed the request.
            repository.mark_create_unknown(payment_intent_id)
            raise
        except PaymentNeedsAction as error:
            repository.mark_failure(payment_intent_id, error.code, error.detail)
            raise
        repository.record_provider_created(payment_intent_id, provider_invoice_id)
        work = repository.load(payment_intent_id)
        if work is None:
            raise PaymentNeedsAction("PAYMENT_INTENT_NOT_FOUND", "Payment intent is unavailable.")

    if work.status is PaymentIntentStatus.PROVIDER_CREATED:
        if not work.provider_invoice_id:
            detail = "PayPal invoice ID is missing; inspect the payment intent before sending."
            repository.mark_manual_action(
                payment_intent_id, "PAYMENT_PROVIDER_REFERENCE_MISSING", detail
            )
            raise PaymentNeedsAction("PAYMENT_PROVIDER_REFERENCE_MISSING", detail)
        try:
            provider.send_invoice(work.provider_invoice_id, payment_intent_id)
        except PaymentNeedsAction as error:
            repository.mark_failure(payment_intent_id, error.code, error.detail)
            raise
        repository.mark_sent(payment_intent_id)
        return

    if work.status not in {
        PaymentIntentStatus.CREATE_PENDING,
        PaymentIntentStatus.CREATE_UNKNOWN,
        PaymentIntentStatus.AUTHORIZED,
        PaymentIntentStatus.PROVIDER_CREATED,
    }:
        detail = f"Payment intent state {work.status.value} is not supported by the invoice worker."
        repository.mark_manual_action(payment_intent_id, "PAYMENT_STATE_UNSUPPORTED", detail)
        raise PaymentNeedsAction("PAYMENT_STATE_UNSUPPORTED", detail)


def _request_id_retry_window_expired(started_at: datetime, now: datetime | None) -> bool:
    current_time = now or datetime.now(UTC)
    start_time = started_at
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)
    return current_time - start_time >= PAYPAL_REQUEST_ID_RETRY_WINDOW
