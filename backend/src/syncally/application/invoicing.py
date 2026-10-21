"""Provider-neutral issuance port. No HTTP, credentials, or deal decisions."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


class InvoiceFailure(Exception):
    """Only fixed, sanitized codes cross the provider boundary."""

    def __init__(self, code: str, *, ambiguous: bool = False, permanent: bool = False):
        self.code = code
        self.ambiguous = ambiguous
        self.permanent = permanent
        super().__init__(code)


@dataclass(frozen=True)
class InvoiceEvidence:
    id: str
    number: str
    reference: str
    status: str
    amount: Decimal
    currency: str
    seller_email: str
    recipient_email: str


class InvoiceClient(Protocol):
    def create(self, payload: dict, operation_id: str) -> str: ...
    def send(self, invoice_id: str, operation_id: str) -> None: ...
    def get(self, invoice_id: str) -> InvoiceEvidence: ...
    def find(self, invoice_number: str) -> list[InvoiceEvidence]: ...
