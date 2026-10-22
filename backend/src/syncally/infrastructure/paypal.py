"""PayPal Sandbox Invoicing API adapter."""

from __future__ import annotations

import base64
import json
import re
import threading
import time
from collections.abc import Callable
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import NAMESPACE_URL, UUID, uuid5

from syncally.application.payment_processing import (
    PaymentInvoiceLookup,
    PaymentInvoiceProvider,
    PaymentInvoiceRequest,
    PaymentNeedsAction,
    PaymentOutcomeUnknown,
    PaymentRetryableError,
)
from syncally.domain.shared.money import canonical_decimal

PAYPAL_SANDBOX_BASE_URL = "https://api-m.sandbox.paypal.com"
_PAYPAL_TIMEOUT_SECONDS = 15.0


class PayPalSandboxInvoiceProvider(PaymentInvoiceProvider):
    """Creates, searches, and sends invoices using only PayPal Sandbox."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        send_request: Callable[[Request], tuple[int, bytes]] | None = None,
    ) -> None:
        if not client_id.strip() or not client_secret.strip():
            raise ValueError("PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET are required.")
        self._client_id = client_id
        self._client_secret = client_secret
        self._send_request = send_request or _send_request
        self._token: str | None = None
        self._token_expires_at = 0.0
        self._token_lock = threading.Lock()

    def find_invoice(self, lookup: PaymentInvoiceLookup) -> str | None:
        query = "?page=1&page_size=2"
        response = self._api_request(
            "POST",
            f"/v2/invoicing/search-invoices{query}",
            {"invoice_number": lookup.invoice_number},
        )
        items = response.get("items")
        if not isinstance(items, list):
            raise PaymentNeedsAction(
                "PAYPAL_SEARCH_RESPONSE_INVALID",
                "PayPal returned an invalid invoice search response; reconcile manually.",
            )
        if not items:
            return None
        if len(items) != 1 or not isinstance(items[0], dict):
            raise PaymentNeedsAction(
                "PAYPAL_INVOICE_MATCH_AMBIGUOUS",
                "Multiple PayPal invoices match this payment; reconcile manually.",
            )
        invoice = items[0]
        detail = invoice.get("detail") or {}
        amount = invoice.get("amount") or {}
        recipients = invoice.get("primary_recipients") or []
        recipient = (
            (recipients[0].get("billing_info") or {}).get("email_address")
            if recipients and isinstance(recipients[0], dict)
            else None
        )
        try:
            matches = (
                isinstance(invoice.get("id"), str)
                and invoice.get("id")
                and detail.get("invoice_number") == lookup.invoice_number
                and detail.get("reference") == lookup.reference
                and amount.get("currency_code") == lookup.amount.currency
                and Decimal(str(amount.get("value"))) == lookup.amount.amount
                and (
                    lookup.recipient_email is None
                    or (
                        isinstance(recipient, str)
                        and recipient.casefold() == lookup.recipient_email.casefold()
                    )
                )
            )
        except (AttributeError, ArithmeticError, TypeError, ValueError):
            matches = False
        if not matches:
            raise PaymentNeedsAction(
                "PAYPAL_INVOICE_MATCH_MISMATCH",
                "The PayPal invoice does not match the authorized payment; reconcile manually.",
            )
        return invoice["id"]

    def create_invoice(self, request: PaymentInvoiceRequest) -> str:
        response = self._api_request(
            "POST",
            "/v2/invoicing/invoices",
            self._invoice_payload(request),
            request_id=_provider_request_id(request.payment_intent_id, "create"),
            may_have_effect=True,
        )
        invoice_id = response.get("id")
        if not isinstance(invoice_id, str) or not invoice_id.strip():
            raise PaymentOutcomeUnknown(
                "PAYPAL_CREATE_RESPONSE_INCOMPLETE",
                "PayPal may have created the invoice but returned no invoice ID; reconciliation is required.",
            )
        return invoice_id

    def send_invoice(self, provider_invoice_id: str, payment_intent_id: UUID) -> None:
        self._api_request(
            "POST",
            f"/v2/invoicing/invoices/{quote(provider_invoice_id, safe='')}/send",
            {"send_to_invoicer": False, "send_to_recipient": True},
            request_id=_provider_request_id(payment_intent_id, "send"),
            may_have_effect=True,
        )

    def _invoice_payload(self, request: PaymentInvoiceRequest) -> dict:
        if (
            not request.invoice_number
            or len(request.invoice_number) > 25
            or not request.seller_business_name
            or len(request.seller_business_name) > 300
            or not request.buyer_business_name
            or len(request.buyer_business_name) > 300
            or not request.buyer_contact_name
            or len(request.buyer_contact_name) > 300
            or not request.buyer_contact_email
            or len(request.buyer_contact_email) > 254
            or not request.line_items
        ):
            raise PaymentNeedsAction(
                "PAYPAL_INVOICE_DATA_INVALID",
                "Required invoice details are missing or exceed PayPal limits; correct the agreement or contact.",
            )

        items = []
        total = Decimal("0")
        for item in request.line_items:
            if (
                not item.name.strip()
                or len(item.name) > 200
                or item.quantity <= 0
                or item.quantity > Decimal("1000000")
                or item.quantity.as_tuple().exponent < -5
                or len(item.description or "") > 1000
                or item.unit_price.currency != request.amount.currency
            ):
                raise PaymentNeedsAction(
                    "PAYPAL_INVOICE_ITEM_INVALID",
                    "An agreed invoice item cannot be represented by PayPal; correct the agreement.",
                )
            total += item.quantity * item.unit_price.amount
            description = item.description or ""
            if item.unit:
                description = f"{description}; Unit: {item.unit}".strip("; ")
            if len(description) > 1000:
                raise PaymentNeedsAction(
                    "PAYPAL_INVOICE_ITEM_INVALID",
                    "An agreed invoice item description exceeds PayPal limits.",
                )
            payload_item = {
                "name": item.name,
                "quantity": canonical_decimal(item.quantity),
                "unit_amount": {
                    "currency_code": item.unit_price.currency,
                    "value": canonical_decimal(item.unit_price.amount),
                },
            }
            if description:
                payload_item["description"] = description
            items.append(payload_item)

        if total != request.amount.amount:
            raise PaymentNeedsAction(
                "PAYPAL_INVOICE_TOTAL_MISMATCH",
                "The committed line items do not match the authorized payment amount.",
            )

        return {
            "detail": {
                "invoice_number": request.invoice_number,
                "reference": request.reference,
                "currency_code": request.amount.currency,
                "payment_term": {"term_type": "DUE_ON_RECEIPT"},
            },
            "invoicer": {"business_name": request.seller_business_name},
            "primary_recipients": [
                {
                    "billing_info": {
                        "business_name": request.buyer_business_name,
                        "name": {"full_name": request.buyer_contact_name},
                        "email_address": request.buyer_contact_email,
                    }
                }
            ],
            "items": items,
        }

    def _api_request(
        self,
        method: str,
        path: str,
        payload: dict,
        *,
        request_id: str | None = None,
        may_have_effect: bool = False,
    ) -> dict:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._access_token()}",
        }
        if request_id:
            headers["PayPal-Request-Id"] = request_id
        request = Request(
            f"{PAYPAL_SANDBOX_BASE_URL}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        status_code, response_body = self._send(request, may_have_effect=may_have_effect)
        self._raise_for_status(status_code, response_body, may_have_effect=may_have_effect)
        if not response_body:
            return {}
        try:
            result = json.loads(response_body)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            if may_have_effect:
                raise PaymentOutcomeUnknown(
                    "PAYPAL_RESPONSE_INVALID",
                    "PayPal may have processed the request but returned an invalid response.",
                ) from error
            raise PaymentNeedsAction(
                "PAYPAL_RESPONSE_INVALID",
                "PayPal returned an invalid response; inspect the Sandbox integration.",
            ) from error
        if not isinstance(result, dict):
            raise PaymentNeedsAction(
                "PAYPAL_RESPONSE_INVALID",
                "PayPal returned an invalid response; inspect the Sandbox integration.",
            )
        return result

    def _access_token(self) -> str:
        now = time.monotonic()
        if self._token and now < self._token_expires_at:
            return self._token
        with self._token_lock:
            now = time.monotonic()
            if self._token and now < self._token_expires_at:
                return self._token
            credentials = base64.b64encode(
                f"{self._client_id}:{self._client_secret}".encode()
            ).decode("ascii")
            request = Request(
                f"{PAYPAL_SANDBOX_BASE_URL}/v1/oauth2/token",
                data=b"grant_type=client_credentials",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {credentials}",
                },
                method="POST",
            )
            status_code, response_body = self._send(request, may_have_effect=False)
            self._raise_for_status(status_code, response_body, may_have_effect=False)
            try:
                response = json.loads(response_body)
                token = response["access_token"]
                expires_in = int(response["expires_in"])
            except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise PaymentNeedsAction(
                    "PAYPAL_OAUTH_RESPONSE_INVALID",
                    "PayPal returned invalid Sandbox credentials metadata.",
                ) from error
            if not isinstance(token, str) or not token or expires_in <= 0:
                raise PaymentNeedsAction(
                    "PAYPAL_OAUTH_RESPONSE_INVALID",
                    "PayPal returned invalid Sandbox credentials metadata.",
                )
            self._token = token
            self._token_expires_at = time.monotonic() + max(0, expires_in - 60)
            return token

    def _send(self, request: Request, *, may_have_effect: bool) -> tuple[int, bytes]:
        try:
            return self._send_request(request)
        except HTTPError as error:
            return error.code, error.read()
        except (TimeoutError, URLError, OSError) as error:
            if may_have_effect:
                raise PaymentOutcomeUnknown(
                    "PAYPAL_OUTCOME_UNKNOWN",
                    "PayPal may have processed the request; the worker will reconcile before retrying.",
                ) from error
            raise PaymentRetryableError(
                "PAYPAL_TEMPORARILY_UNAVAILABLE",
                "PayPal is temporarily unavailable; the payment will be retried.",
            ) from error

    @staticmethod
    def _raise_for_status(
        status_code: int, response_body: bytes, *, may_have_effect: bool
    ) -> None:
        if 200 <= status_code < 300:
            return
        code = _provider_error_code(response_body, status_code)
        if status_code in {408, 429} or status_code >= 500:
            if may_have_effect:
                raise PaymentOutcomeUnknown(
                    code,
                    "PayPal may have processed the request; the worker will reconcile before retrying.",
                )
            raise PaymentRetryableError(
                code,
                "PayPal is temporarily unavailable; the payment will be retried.",
            )
        raise PaymentNeedsAction(
            code,
            f"PayPal rejected the request ({code}); check Sandbox configuration and invoice data.",
        )


def _provider_error_code(response_body: bytes, status_code: int) -> str:
    name = None
    try:
        data = json.loads(response_body)
        if isinstance(data, dict):
            name = data.get("name")
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass
    if isinstance(name, str):
        normalized = re.sub(r"[^A-Z0-9_]", "_", name.upper()).strip("_")[:48]
    else:
        normalized = ""
    return f"PAYPAL_{normalized or f'HTTP_{status_code}'}"


def _provider_request_id(payment_intent_id: UUID, operation: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"syncally/paypal/{payment_intent_id}/{operation}"))


def _send_request(request: Request) -> tuple[int, bytes]:
    try:
        with urlopen(request, timeout=_PAYPAL_TIMEOUT_SECONDS) as response:
            return response.status, response.read()
    except HTTPError:
        raise
