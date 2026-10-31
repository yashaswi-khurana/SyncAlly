"""Deterministic offline invoices. No remote transport or paid-state inference."""

from uuid import UUID

from syncally.application.payment_processing import (
    PaymentInvoiceLookup,
    PaymentInvoiceRequest,
    PaymentNeedsAction,
    PaymentWorkItem,
)


class OfflineDemoInvoiceProvider:
    execution_mode = "OFFLINE_DEMO"

    def __init__(self, work: PaymentWorkItem) -> None:
        if (work.provider, work.execution_mode) != ("OFFLINE_DEMO", "OFFLINE_DEMO"):
            raise PaymentNeedsAction("PAYMENT_PROVENANCE_UNRESOLVED", "Offline invoices require persisted offline identity.")
        self._work = work
        self._reference = f"OFFLINE-{work.payment_intent_id}"

    def find_invoice(self, lookup: PaymentInvoiceLookup) -> str | None:
        if lookup != self._work.lookup:
            raise PaymentNeedsAction("PAYMENT_INVOICE_REQUEST_CHANGED", "Offline invoice identity changed.")
        return self._reference if self._work.request_payload_hash else None

    def create_invoice(self, request: PaymentInvoiceRequest) -> str:
        if request != self._work.invoice_request or (self._work.request_payload_hash and request.payload_hash != self._work.request_payload_hash):
            raise PaymentNeedsAction("PAYMENT_INVOICE_REQUEST_CHANGED", "Offline invoice request changed.")
        return self._reference

    def get_invoice_status(self, provider_invoice_id: str) -> str:
        self._require_reference(provider_invoice_id)
        return "DRAFT" if self._work.status.value in {"CREATE_PENDING", "CREATE_UNKNOWN", "PROVIDER_CREATED"} else "SENT"

    def send_invoice(self, provider_invoice_id: str, payment_intent_id: UUID) -> None:
        self._require_reference(provider_invoice_id)
        if payment_intent_id != self._work.payment_intent_id:
            raise PaymentNeedsAction("PAYMENT_PROVIDER_REFERENCE_CONFLICT", "Offline intent identity differs.")

    def _require_reference(self, reference: str) -> None:
        if reference != self._reference:
            raise PaymentNeedsAction("PAYMENT_PROVIDER_REFERENCE_CONFLICT", "Offline invoice reference differs.")


class PaymentProviderResolver:
    """Build remote adapters only for a persisted Sandbox item, never as fallback."""

    def resolve(self, work: PaymentWorkItem):
        if (work.provider, work.execution_mode) == ("OFFLINE_DEMO", "OFFLINE_DEMO"):
            from syncally.config import settings

            if settings.app_env.lower() not in {"development", "test"}:
                raise PaymentNeedsAction("PAYMENT_PROVIDER_CONFIGURATION_MISSING", "Offline dispatch is restricted to development/test.")
            return OfflineDemoInvoiceProvider(work)
        if (work.provider, work.execution_mode) != ("PAYPAL", "PAYPAL_SANDBOX"):
            raise PaymentNeedsAction("PAYMENT_PROVENANCE_UNRESOLVED", "Payment provenance is unresolved; inspect manually.")
        from syncally.config import PayPalSettings
        from syncally.infrastructure.paypal import PayPalSandboxInvoiceProvider

        config = PayPalSettings()
        if not config.paypal_client_id.strip() or not config.paypal_client_secret.get_secret_value():
            raise PaymentNeedsAction("PAYMENT_PROVIDER_CONFIGURATION_MISSING", "Sandbox credentials are missing; no fallback is permitted.")
        return PayPalSandboxInvoiceProvider(config.paypal_client_id, config.paypal_client_secret.get_secret_value())

    def notifier(self, work: PaymentWorkItem):
        if work.execution_mode != "PAYPAL_SANDBOX":
            return None
        from syncally.config import GmailSettings
        from syncally.infrastructure.gmail import GmailSMTPInvoiceNotifier

        config = GmailSettings()
        username, password, sender = config.gmail_smtp_username.strip(), config.gmail_app_password.get_secret_value(), config.gmail_from_email.strip()
        if not (username or password or sender):
            return None
        if not username or not password:
            raise PaymentNeedsAction("PAYMENT_PROVIDER_CONFIGURATION_MISSING", "Invoice email configuration is incomplete.")
        return GmailSMTPInvoiceNotifier(username, password, sender or None)