"""PayPal Invoicing v2, fixed Sandbox origin, no implicit HTTP retries."""

import re
from decimal import Decimal, InvalidOperation

import httpx
from pydantic import SecretStr

from syncally.application.invoicing import InvoiceEvidence, InvoiceFailure

SANDBOX_ORIGIN = "https://api-m.sandbox.paypal.com"


class SandboxPayPalAdapter:
    def __init__(self, client_id: SecretStr, client_secret: SecretStr, *, transport=None):
        if not client_id.get_secret_value() or not client_secret.get_secret_value():
            raise ValueError("Sandbox credentials are required")
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = httpx.Client(
            base_url=SANDBOX_ORIGIN,
            timeout=15,
            follow_redirects=False,
            transport=transport,
            trust_env=False,
        )

    def close(self):
        self._http.close()

    def _request(self, method, path, *, mutation=False, **kwargs):
        # Token requests are not invoice side effects. Never include provider
        # messages, URLs, headers, or bodies in exceptions or worker logs.
        try:
            token = self._http.post(
                "/v1/oauth2/token",
                data={"grant_type": "client_credentials"},
                auth=(self._client_id.get_secret_value(), self._client_secret.get_secret_value()),
            )
            self._check(token, mutation=False)
            access_token = token.json()["access_token"]
            headers = {"Authorization": f"Bearer {access_token}", **kwargs.pop("headers", {})}
        except InvoiceFailure:
            raise
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            raise InvoiceFailure("PAYPAL_AUTH_UNAVAILABLE") from None
        try:
            response = self._http.request(method, path, headers=headers, **kwargs)
            self._check(response, mutation=mutation)
            return response
        except InvoiceFailure:
            raise
        except httpx.HTTPError:
            raise InvoiceFailure("PAYPAL_TRANSPORT", ambiguous=mutation) from None

    @staticmethod
    def _check(response, *, mutation):
        if 200 <= response.status_code < 300:
            return
        if response.status_code == 429:
            raise InvoiceFailure("PAYPAL_RATE_LIMIT")
        if response.status_code >= 500 or response.status_code == 408:
            raise InvoiceFailure("PAYPAL_UNAVAILABLE", ambiguous=mutation)
        raise InvoiceFailure("PAYPAL_REQUEST_REJECTED", permanent=True)

    @staticmethod
    def _path(invoice_id):
        if not isinstance(invoice_id, str) or not re.fullmatch(r"INV2-[A-Z0-9-]+", invoice_id):
            raise InvoiceFailure("PAYPAL_INVALID_REFERENCE", permanent=True)
        return f"/v2/invoicing/invoices/{invoice_id}"

    def create(self, payload, operation_id):
        response = self._request(
            "POST",
            "/v2/invoicing/invoices",
            mutation=True,
            json=payload,
            headers={"PayPal-Request-Id": operation_id, "Prefer": "return=representation"},
        )
        try:
            data = response.json()
            invoice_id = data.get("id")
            if not invoice_id:
                # Some create responses contain only a self link. Read the ID,
                # never follow an arbitrary URL supplied by a response.
                href = data.get("href", "")
                invoice_id = href.rsplit("/", 1)[-1]
            self._path(invoice_id)
            return invoice_id
        except (ValueError, TypeError, AttributeError, InvoiceFailure):
            raise InvoiceFailure("PAYPAL_CREATE_RESPONSE_UNKNOWN", ambiguous=True) from None

    def send(self, invoice_id, operation_id):
        # Endpoint schema does not document PayPal-Request-Id for send.
        # Keep the distinct application operation ID; recovery always GETs first.
        self._request(
            "POST",
            self._path(invoice_id) + "/send",
            mutation=True,
            json={"send_to_invoicer": False, "send_to_recipient": True},
        )

    def get(self, invoice_id):
        response = self._request("GET", self._path(invoice_id))
        try:
            return self._evidence(response.json())
        except (ValueError, KeyError, TypeError, AttributeError, InvalidOperation):
            raise InvoiceFailure("PAYPAL_INVALID_EVIDENCE", permanent=True) from None

    def find(self, invoice_number):
        response = self._request(
            "POST",
            "/v2/invoicing/search-invoices",
            json={"invoice_number": invoice_number},
            params={"page_size": 100, "total_required": "true"},
        )
        try:
            data = response.json()
            items = data.get("items", [])
            # Search is not proof of absence, even when empty. Only exact hits
            # may be attached; the worker never recreates on an empty search.
            matches = [item for item in items if item["detail"]["invoice_number"] == invoice_number]
            if len(matches) > 1:
                raise InvoiceFailure("PAYPAL_DUPLICATE_INVOICE_NUMBER", permanent=True)
            return [self.get(item["id"]) for item in matches]
        except (ValueError, KeyError, TypeError, AttributeError):
            raise InvoiceFailure("PAYPAL_INVALID_SEARCH", permanent=True) from None

    @staticmethod
    def _evidence(data):
        amount = Decimal(data["amount"]["value"])
        if not amount.is_finite():
            raise ValueError("nonfinite")
        recipients = data["primary_recipients"]
        if len(recipients) != 1:
            raise ValueError("recipient count")
        return InvoiceEvidence(
            id=data["id"],
            number=data["detail"]["invoice_number"],
            reference=data["detail"]["reference"],
            status=data["status"],
            amount=amount,
            currency=data["amount"]["currency_code"],
            seller_email=data["invoicer"]["email_address"],
            recipient_email=recipients[0]["billing_info"]["email_address"],
        )
