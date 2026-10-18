"""Immutable canonical commercial terms shared by proposals and agreements."""

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any
from unicodedata import normalize
from uuid import UUID

from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import OrganizationId
from syncally.domain.shared.money import Money, canonical_decimal

TRADE_TERMS_SCHEMA_VERSION = 1
SUPPORTED_DEMO_CURRENCY = "USD"
SUPPORTED_DEMO_PAYMENT_TRIGGER = "seller_invoice"
SUPPORTED_DEMO_PAYMENT_DUE_CONDITION = "when seller invoices"


def _normalized_text(value: str, field_name: str, *, required: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    result = normalize("NFC", value.strip())
    if required and not result:
        raise InvariantViolation(f"{field_name} is required")
    return result


def _require_decimal(value: Decimal, field_name: str) -> None:
    if not isinstance(value, Decimal):
        raise TypeError(f"{field_name} must be Decimal")
    if not value.is_finite():
        raise InvariantViolation(f"{field_name} must be finite")


@dataclass(frozen=True, slots=True)
class TradeLineItem:
    description: str
    quantity: Decimal
    unit: str
    unit_price: Money
    sku: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "description", _normalized_text(self.description, "Description", required=True))
        object.__setattr__(self, "unit", _normalized_text(self.unit, "Unit", required=True))
        if self.sku is not None:
            sku = _normalized_text(self.sku, "SKU")
            object.__setattr__(self, "sku", sku or None)
        if not isinstance(self.unit_price, Money):
            raise TypeError("Line item unit_price must be Money")
        _require_decimal(self.quantity, "Line item quantity")
        if self.quantity <= 0:
            raise InvariantViolation("Line item quantity must be finite and positive")
        if self.unit_price.amount < 0:
            raise InvariantViolation("Line item unit price cannot be negative")

    @property
    def total(self) -> Money:
        return self.unit_price.multiply(self.quantity)


@dataclass(frozen=True, slots=True)
class ShipmentTerm:
    quantity: Decimal
    destination: str
    target_date: date | None = None

    def __post_init__(self) -> None:
        _require_decimal(self.quantity, "Shipment quantity")
        if self.quantity <= 0:
            raise InvariantViolation("Shipment quantity must be finite and positive")
        object.__setattr__(self, "destination", _normalized_text(self.destination, "Shipment destination", required=True))
        if self.target_date is not None and type(self.target_date) is not date:
            raise TypeError("Shipment target_date must be a date or None")


@dataclass(frozen=True, slots=True)
class PaymentTerm:
    amount: Money
    trigger: str
    due_condition: str

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Money):
            raise TypeError("Payment term amount must be Money")
        if self.amount.amount <= 0:
            raise InvariantViolation("Payment term amount must be positive")
        object.__setattr__(self, "trigger", _normalized_text(self.trigger, "Payment trigger", required=True).casefold())
        object.__setattr__(self, "due_condition", _normalized_text(self.due_condition, "Payment due condition", required=True).casefold())


@dataclass(frozen=True, slots=True)
class TradeTerms:
    buyer_id: OrganizationId
    seller_id: OrganizationId
    line_items: tuple[TradeLineItem, ...]
    shipments: tuple[ShipmentTerm, ...]
    payment_terms: tuple[PaymentTerm, ...]
    delivery_location: str
    incoterm: str | None = None
    cancellation_terms: str = ""
    schema_version: int = TRADE_TERMS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "line_items", tuple(self.line_items))
        object.__setattr__(self, "shipments", tuple(self.shipments))
        object.__setattr__(self, "payment_terms", tuple(self.payment_terms))
        object.__setattr__(self, "delivery_location", _normalized_text(self.delivery_location, "Delivery location", required=True))
        object.__setattr__(self, "incoterm", _normalized_text(self.incoterm, "Incoterm").upper() or None if self.incoterm is not None else None)
        object.__setattr__(self, "cancellation_terms", _normalized_text(self.cancellation_terms, "Cancellation terms"))

        if self.buyer_id == self.seller_id:
            raise InvariantViolation("Buyer and seller must be different organizations")
        if not self.line_items:
            raise InvariantViolation("At least one line item is required")
        if not self.shipments:
            raise InvariantViolation("At least one shipment term is required")
        if not self.payment_terms:
            raise InvariantViolation("At least one payment term is required")
        if type(self.schema_version) is not int or self.schema_version < 1:
            raise InvariantViolation("Schema version must be positive")

        currencies = {item.unit_price.currency for item in self.line_items}
        currencies.update(term.amount.currency for term in self.payment_terms)
        if len(currencies) != 1:
            raise InvariantViolation("All line items and payment terms must use one currency")
        line_total = self.total
        payment_total = self.payment_total
        if line_total != payment_total:
            raise InvariantViolation("Payment terms must sum to the line item total")

    @property
    def currency(self) -> str:
        return self.line_items[0].unit_price.currency

    @property
    def total(self) -> Money:
        total = Money(Decimal("0"), self.line_items[0].unit_price.currency)
        for item in self.line_items:
            total = total.add(item.total)
        return total

    @property
    def payment_total(self) -> Money:
        total = Money(Decimal("0"), self.payment_terms[0].amount.currency)
        for term in self.payment_terms:
            total = total.add(term.amount)
        return total

    def _payload(self, *, casefold_display: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "buyer_id": str(self.buyer_id),
            "seller_id": str(self.seller_id),
            "line_items": [
                {
                    "description": item.description,
                    "sku": item.sku,
                    "quantity": _decimal(item.quantity),
                    "unit": item.unit,
                    "unit_price": _money(item.unit_price),
                }
                for item in self.line_items
            ],
            "shipments": [
                {
                    "quantity": _decimal(shipment.quantity),
                    "destination": shipment.destination.casefold()
                    if casefold_display
                    else shipment.destination,
                    "target_date": shipment.target_date.isoformat()
                    if shipment.target_date
                    else None,
                }
                for shipment in self.shipments
            ],
            "payment_terms": [
                {
                    "amount": _money(term.amount),
                    "trigger": term.trigger,
                    "due_condition": term.due_condition,
                }
                for term in self.payment_terms
            ],
            "delivery_location": self.delivery_location.casefold()
            if casefold_display
            else self.delivery_location,
            "incoterm": self.incoterm,
            "cancellation_terms": self.cancellation_terms,
        }
        # The model has no sequence field, so collection order is presentation-only.
        for collection in ("line_items", "shipments", "payment_terms"):
            payload[collection].sort(
                key=lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"))
            )
        return payload

    def canonical_json(self) -> str:
        """Serialize every commitment-relevant field with deterministic ordering.

        Destination/delivery location are casefolded here because this is
        what ``terms_hash`` hashes - two terms differing only by that case
        must still hash identically. Persist ``to_storage_dict()`` instead,
        which keeps the original display case.
        """
        return json.dumps(
            self._payload(casefold_display=True),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def to_storage_dict(self) -> dict[str, Any]:
        """Same shape as ``canonical_json()``, but keeping display case.

        This is what should be persisted as ``canonical_terms_json`` so
        ``from_canonical_json`` can rebuild terms without losing the original
        capitalization of free-text display fields.
        """
        return self._payload(casefold_display=False)

    @property
    def terms_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def validate_for_commit(self) -> None:
        """Reject terms outside the documented first-demo trade contract."""
        if self.schema_version != TRADE_TERMS_SCHEMA_VERSION:
            raise InvariantViolation("Unsupported trade terms schema version")
        if self.currency != SUPPORTED_DEMO_CURRENCY:
            raise InvariantViolation("Only USD agreements are supported for the demo")
        if len(self.line_items) != 1 or len(self.shipments) != 1 or len(self.payment_terms) != 1:
            raise InvariantViolation("The demo supports one line item, shipment, and payment term")
        if self.incoterm is not None or self.cancellation_terms:
            raise InvariantViolation("Incoterms and custom cancellation terms are not supported")

        item = self.line_items[0]
        shipment = self.shipments[0]
        payment = self.payment_terms[0]
        if shipment.quantity != item.quantity:
            raise InvariantViolation("Shipment quantity must match the line item quantity")
        if shipment.destination.casefold() != self.delivery_location.casefold():
            raise InvariantViolation("Shipment destination must match the delivery location")
        if shipment.target_date is None:
            raise InvariantViolation("A target delivery date is required to commit")
        if payment.amount != self.total:
            raise InvariantViolation("The payment term must equal the full trade total")
        if (
            payment.trigger != SUPPORTED_DEMO_PAYMENT_TRIGGER
            or payment.due_condition != SUPPORTED_DEMO_PAYMENT_DUE_CONDITION
        ):
            raise InvariantViolation("The demo supports payment when the seller invoices")

    @classmethod
    def from_canonical_json(cls, data: dict[str, Any]) -> "TradeTerms":
        """Reconstruct terms from the dict produced by ``canonical_json``.

        Used to rebuild the domain aggregate from a stored ``AgreementVersion``
        row so commit/approval invariants run through the same domain code
        that produced the hash, rather than being re-derived in SQL.
        """
        return cls(
            buyer_id=OrganizationId(UUID(data["buyer_id"])),
            seller_id=OrganizationId(UUID(data["seller_id"])),
            line_items=tuple(
                TradeLineItem(
                    description=item["description"],
                    quantity=Decimal(item["quantity"]),
                    unit=item["unit"],
                    unit_price=_parse_money(item["unit_price"]),
                    sku=item["sku"],
                )
                for item in data["line_items"]
            ),
            shipments=tuple(
                ShipmentTerm(
                    quantity=Decimal(shipment["quantity"]),
                    destination=shipment["destination"],
                    target_date=(
                        date.fromisoformat(shipment["target_date"])
                        if shipment["target_date"]
                        else None
                    ),
                )
                for shipment in data["shipments"]
            ),
            payment_terms=tuple(
                PaymentTerm(
                    amount=_parse_money(term["amount"]),
                    trigger=term["trigger"],
                    due_condition=term["due_condition"],
                )
                for term in data["payment_terms"]
            ),
            delivery_location=data["delivery_location"],
            incoterm=data["incoterm"],
            cancellation_terms=data["cancellation_terms"],
            schema_version=data["schema_version"],
        )


def _decimal(value: Decimal) -> str:
    return canonical_decimal(value)


def _money(value: Money) -> dict[str, str]:
    return {"amount": value.canonical_amount(), "currency": value.currency}


def _parse_money(data: dict[str, str]) -> Money:
    return Money(Decimal(data["amount"]), data["currency"])

