"""PayPal Sandbox Invoicing API adapter."""

from __future__ import annotations

import base64
import json
import re
import threading
import time
from collections.abc import Callable, Mapping
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
from uuid import NAMESPACE_URL, UUID, uuid5

from syncally.application.payment_processing import (
    PaymentInvoiceLookup,
    PaymentInvoiceNotice,
    PaymentInvoiceProvider,
    PaymentInvoiceReconciliation,
    PaymentInvoiceRequest,
    PaymentNeedsAction,
    PaymentOutcomeUnknown,
    PaymentRetryableError,
)
from syncally.domain.payments.intent import (
    VerifiedProviderPaymentState,
    VerifiedProviderPaymentStatus,
)
from syncally.domain.shared.errors import DomainError
from syncally.domain.shared.money import Money, canonical_decimal

PAYPAL_SANDBOX_BASE_URL = "https://api-m.sandbox.paypal.com"
_PAYPAL_TIMEOUT_SECONDS = 15.0
_ZERO_DECIMAL_CURRENCIES = {"HUF", "JPY", "TWD"}


def _has_excess_currency_precision(value: Decimal, precision: int) -> bool:
    _, digits, exponent = value.as_tuple()
    while exponent < 0 and digits and digits[-1] == 0:
        digits = digits[:-1]
        exponent += 1
    return exponent < -precision


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
        query = "?page=1&page_size=2&total_required=true"
        response = self._api_request(
            "POST",
            f"/v2/invoicing/search-invoices{query}",
            {"invoice_number": lookup.invoice_number},
        )
        items = response.get("items")
        total_items = response.get("total_items")
        if (
            items is None
            and isinstance(total_items, int)
            and not isinstance(total_items, bool)
            and total_items == 0
        ):
            items = []
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

    def get_invoice_status(self, provider_invoice_id: str) -> str:
        response = self._api_request(
            "GET",
            f"/v2/invoicing/invoices/{quote(provider_invoice_id, safe='')}",
            None,
        )
        status = response.get("status")
        if not isinstance(status, str):
            raise PaymentNeedsAction(
                "PAYPAL_INVOICE_STATUS_INVALID",
                "PayPal returned no usable invoice status; reconcile the invoice manually.",
            )
        return status

    def verify_webhook_signature(
        self,
        headers: Mapping[str, str],
        event: Mapping[str, object],
        webhook_id: str,
    ) -> bool:
        """Ask PayPal to verify the signed transmission for this registered webhook."""
        field_names = {
            "paypal-auth-algo": "auth_algo",
            "paypal-cert-url": "cert_url",
            "paypal-transmission-id": "transmission_id",
            "paypal-transmission-sig": "transmission_sig",
            "paypal-transmission-time": "transmission_time",
        }
        payload = {
            name: headers.get(header_name, "")
            for header_name, name in field_names.items()
        }
        payload["webhook_id"] = webhook_id
        payload["webhook_event"] = dict(event)
        result = self._api_request(
            "POST", "/v1/notifications/verify-webhook-signature", payload
        )
        verification_status = result.get("verification_status")
        if verification_status not in {"SUCCESS", "FAILURE"}:
            raise PaymentNeedsAction(
                "PAYPAL_WEBHOOK_VERIFICATION_INVALID",
                "PayPal returned no usable webhook signature verification result.",
            )
        return verification_status == "SUCCESS"

    def get_invoice_reconciliation(
        self, provider_invoice_id: str
    ) -> PaymentInvoiceReconciliation:
        """Fetch the invoice's present status and aggregated paid amount."""
        response = self._api_request(
            "GET",
            f"/v2/invoicing/invoices/{quote(provider_invoice_id, safe='')}",
            None,
        )
        detail = response.get("detail")
        amount = response.get("amount")
        payments = response.get("payments")
        paid_amount = payments.get("paid_amount") if isinstance(payments, dict) else None
        if not isinstance(detail, dict) or not isinstance(amount, dict):
            raise PaymentNeedsAction(
                "PAYPAL_INVOICE_RESPONSE_INVALID",
                "PayPal returned incomplete invoice details; reconcile the payment manually.",
            )
        invoice_id = response.get("id")
        invoice_number = detail.get("invoice_number")
        reference = detail.get("reference")
        currency = amount.get("currency_code")
        amount_value = amount.get("value")
        invoice_status = response.get("status")
        if (
            not isinstance(invoice_id, str)
            or not isinstance(invoice_number, str)
            or not isinstance(reference, str)
            or not isinstance(currency, str)
            or not isinstance(amount_value, str)
            or not isinstance(invoice_status, str)
        ):
            raise PaymentNeedsAction(
                "PAYPAL_INVOICE_RESPONSE_INVALID",
                "PayPal returned incomplete invoice identity or amount details; reconcile manually.",
            )
        try:
            total_amount = Decimal(amount_value)
            paid_currency = (
                paid_amount.get("currency_code", currency)
                if isinstance(paid_amount, dict)
                else currency
            )
            paid_value = (
                Decimal(str(paid_amount.get("value")))
                if isinstance(paid_amount, dict)
                else Decimal("0")
            )
            if not isinstance(paid_currency, str):
                raise ValueError("PayPal returned an invalid payment currency")
            if not total_amount.is_finite() or not paid_value.is_finite():
                raise ValueError("PayPal returned a non-finite amount")
            total = Money(total_amount, currency)
            paid = Money(paid_value, paid_currency)
        except (ArithmeticError, TypeError, ValueError, DomainError) as error:
            raise PaymentNeedsAction(
                "PAYPAL_INVOICE_AMOUNT_INVALID",
                "PayPal returned invalid invoice payment amounts; reconcile manually.",
            ) from error

        if invoice_id != provider_invoice_id:
            raise PaymentNeedsAction(
                "PAYPAL_INVOICE_ID_MISMATCH",
                "PayPal returned a different invoice than requested; reconcile manually.",
            )

        normalized_status = invoice_status.upper()
        if normalized_status == "PAID" and paid.amount == total.amount:
            payment_status = VerifiedProviderPaymentStatus.PAID
        elif (
            normalized_status in {"PAID", "PARTIALLY_PAID", "SENT", "SCHEDULED", "UNPAID", "PAYMENT_PENDING"}
            and Decimal("0") < paid.amount < total.amount
        ):
            payment_status = VerifiedProviderPaymentStatus.PARTIALLY_PAID
        elif normalized_status in {"SENT", "SCHEDULED", "UNPAID", "PAYMENT_PENDING"} and paid.amount == 0:
            payment_status = VerifiedProviderPaymentStatus.PENDING
        else:
            payment_status = VerifiedProviderPaymentStatus.UNKNOWN

        return PaymentInvoiceReconciliation(
            provider_invoice_id=invoice_id,
            invoice_number=invoice_number,
            reference=reference,
            amount=total,
            payment_state=VerifiedProviderPaymentState(
                status=payment_status,
                paid_amount=paid,
                provider_reference=invoice_id,
            ),
        )

    def get_invoice_notice(self, provider_invoice_id: str) -> PaymentInvoiceNotice:
        response = self._api_request(
            "GET",
            f"/v2/invoicing/invoices/{quote(provider_invoice_id, safe='')}",
            None,
        )
        detail = response.get("detail")
        if not isinstance(detail, dict):
            detail = {}
        metadata = detail.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        recipients = response.get("primary_recipients")
        if not isinstance(recipients, list):
            recipients = []
        first_recipient = (
            recipients[0]
            if len(recipients) == 1 and isinstance(recipients[0], dict)
            else {}
        )
        billing_info = first_recipient.get("billing_info")
        if not isinstance(billing_info, dict):
            billing_info = {}
        recipient_email = billing_info.get("email_address")
        amount = response.get("amount")
        if not isinstance(amount, dict):
            amount = {}
        invoice_number = detail.get("invoice_number")
        currency = amount.get("currency_code")
        value = amount.get("value")
        recipient_view_url = metadata.get("recipient_view_url")

        try:
            parsed_url = urlsplit(recipient_view_url)
            host = parsed_url.hostname or ""
            is_paypal_url = (
                parsed_url.scheme == "https"
                and (host == "paypal.com" or host.endswith(".paypal.com"))
                and parsed_url.username is None
                and parsed_url.password is None
                and parsed_url.port in (None, 443)
                and parsed_url.path.startswith("/")
            )
            parsed_amount = Decimal(str(value))
        except (AttributeError, ArithmeticError, TypeError, ValueError):
            is_paypal_url = False
            parsed_amount = Decimal("0")

        if (
            not isinstance(recipient_email, str)
            or recipient_email.count("@") != 1
            or any(character.isspace() for character in recipient_email)
            or not isinstance(invoice_number, str)
            or re.fullmatch(r"[A-Za-z0-9._-]{1,25}", invoice_number) is None
            or not isinstance(currency, str)
            or len(currency) != 3
            or not currency.isascii()
            or not currency.isalpha()
            or not parsed_amount.is_finite()
            or parsed_amount <= 0
            or not isinstance(recipient_view_url, str)
            or not is_paypal_url
        ):
            raise PaymentNeedsAction(
                "PAYPAL_INVOICE_NOTICE_INVALID",
                "PayPal did not return complete, safe invoice details for the email notification.",
            )

        return PaymentInvoiceNotice(
            invoice_number=invoice_number,
            amount=Money(parsed_amount, currency),
            recipient_email=recipient_email,
            recipient_view_url=recipient_view_url,
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
            unit_price_precision = 0 if item.unit_price.currency in _ZERO_DECIMAL_CURRENCIES else 2
            if (
                not item.name.strip()
                or len(item.name) > 200
                or item.quantity <= 0
                or item.quantity > Decimal("1000000")
                or item.quantity.as_tuple().exponent < -5
                or len(item.description or "") > 1000
                or item.unit_price.currency != request.amount.currency
                or _has_excess_currency_precision(
                    item.unit_price.amount, unit_price_precision
                )
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
        payload: dict | None,
        *,
        request_id: str | None = None,
        may_have_effect: bool = False,
    ) -> dict:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._access_token()}",
        }
        body = None
        if payload is not None:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
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
            if may_have_effect:
                raise PaymentOutcomeUnknown(
                    "PAYPAL_RESPONSE_INVALID",
                    "PayPal may have processed the request but returned an invalid response.",
                )
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
            if status_code == 401:
                raise PaymentRetryableError(
                    "PAYPAL_AUTH_FAILED",
                    "PayPal Sandbox rejected the configured credentials; correct them to resume payment processing.",
                )
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
