"""Stateful fake for issuance tests; no credentials or network."""

from dataclasses import replace
from decimal import Decimal

from syncally.application.invoicing import InvoiceEvidence


class FakeInvoiceClient:
    def __init__(self):
        self.invoices = {}
        self.calls = []
        self.failures = {}
        self.after_mutation = {}
        self.before_call = lambda: None

    def _call(self, name, identity):
        self.before_call()
        self.calls.append((name, identity))
        if failure := self.failures.pop(name, None):
            raise failure

    def create(self, payload, operation_id):
        self._call("create", operation_id)
        invoice_id = "INV2-FAKE-0001"
        self.invoices[invoice_id] = InvoiceEvidence(
            id=invoice_id,
            number=payload["detail"]["invoice_number"],
            reference=payload["detail"]["reference"],
            status="DRAFT",
            amount=sum(
                Decimal(i["quantity"]) * Decimal(i["unit_amount"]["value"])
                for i in payload["items"]
            ),
            currency=payload["detail"]["currency_code"],
            seller_email=payload["invoicer"]["email_address"],
            recipient_email=payload["primary_recipients"][0]["billing_info"]["email_address"],
        )
        if failure := self.after_mutation.pop("create", None):
            raise failure
        return invoice_id

    def send(self, invoice_id, operation_id):
        self._call("send", operation_id)
        self.invoices[invoice_id] = replace(self.invoices[invoice_id], status="SENT")
        if failure := self.after_mutation.pop("send", None):
            raise failure

    def get(self, invoice_id):
        self._call("get", invoice_id)
        return self.invoices[invoice_id]

    def find(self, invoice_number):
        self._call("find", invoice_number)
        return [i for i in self.invoices.values() if i.number == invoice_number]
