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
from syncally.domain.shared.money import Money, bounded_decimal, canonical_decimal

TRADE_TERMS_SCHEMA_VERSION_LEGACY: int = 1
COLLECTION_TRADE_TERMS_SCHEMA_VERSION: int = 2
TRADE_TERMS_SCHEMA_VERSION: int = TRADE_TERMS_SCHEMA_VERSION_LEGACY
SUPPORTED_SCHEMA_VERSIONS: frozenset[int] = frozenset({
    TRADE_TERMS_SCHEMA_VERSION_LEGACY,
    COLLECTION_TRADE_TERMS_SCHEMA_VERSION,
})
SUPPORTED_DEMO_PAYMENT_TRIGGER = "seller_invoice"
SUPPORTED_DEMO_PAYMENT_DUE_CONDITION = "when seller invoices"


def _normalized_text(
    value: str, field_name: str, *, required: bool = False, max_length: int | None = None
) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    result = normalize("NFC", value.strip())
    if required and not result:
        raise InvariantViolation(f"{field_name} is required")
    if max_length is not None and len(result) > max_length:
        raise InvariantViolation(f"{field_name} exceeds maximum length of {max_length} characters")
    return result


def _require_decimal(
    value: Decimal,
    field_name: str,
    *,
    allow_negative: bool = False,
    allow_zero: bool = True,
) -> Decimal:
    return bounded_decimal(
        value,
        allow_negative=allow_negative,
        allow_zero=allow_zero,
        field_name=field_name,
    )


@dataclass(frozen=True, slots=True)
class ShipmentItemAllocation:
    line_item_id: str
    quantity: Decimal
    unit: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "line_item_id",
            _normalized_text(self.line_item_id, "Allocation line_item_id", required=True, max_length=64),
        )
        object.__setattr__(
            self,
            "unit",
            _normalized_text(self.unit, "Allocation unit", required=True),
        )
        _require_decimal(self.quantity, "Allocation quantity", allow_negative=False, allow_zero=False)
        if self.quantity <= 0:
            raise InvariantViolation("Allocation quantity must be positive")


@dataclass(frozen=True, slots=True)
class PaymentObligationAllocation:
    obligation_id: str
    amount: Money

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "obligation_id",
            _normalized_text(self.obligation_id, "Allocation obligation_id", required=True, max_length=64),
        )
        if not isinstance(self.amount, Money):
            raise TypeError("Allocation amount must be Money")
        if self.amount.amount <= 0:
            raise InvariantViolation("Allocation amount must be positive")


@dataclass(frozen=True, slots=True)
class TradeLineItem:
    description: str
    quantity: Decimal
    unit: str
    unit_price: Money
    sku: str | None = None
    id: str | None = None

    def __post_init__(self) -> None:
        if self.id is not None:
            object.__setattr__(
                self,
                "id",
                _normalized_text(self.id, "Line item id", required=True, max_length=64),
            )
        object.__setattr__(self, "description", _normalized_text(self.description, "Description", required=True))
        object.__setattr__(self, "unit", _normalized_text(self.unit, "Unit", required=True))
        if self.sku is not None:
            sku = _normalized_text(self.sku, "SKU")
            object.__setattr__(self, "sku", sku or None)
        if not isinstance(self.unit_price, Money):
            raise TypeError("Line item unit_price must be Money")
        _require_decimal(self.quantity, "Line item quantity", allow_negative=False, allow_zero=False)
        if self.quantity <= 0:
            raise InvariantViolation("Line item quantity must be finite and positive")
        if self.unit_price.amount < 0:
            raise InvariantViolation("Line item unit price cannot be negative")

    @property
    def total(self) -> Money:
        return self.unit_price.multiply(self.quantity)


@dataclass(frozen=True, slots=True)
class ShipmentTerm:
    quantity: Decimal | None = None
    destination: str = ""
    target_date: date | None = None
    id: str | None = None
    allocations: tuple[ShipmentItemAllocation, ...] = ()

    def __post_init__(self) -> None:
        if self.id is not None:
            object.__setattr__(
                self,
                "id",
                _normalized_text(self.id, "Shipment id", required=True, max_length=64),
            )
        object.__setattr__(self, "allocations", tuple(self.allocations))
        object.__setattr__(self, "destination", _normalized_text(self.destination, "Shipment destination", required=True))
        if self.target_date is not None and type(self.target_date) is not date:
            raise TypeError("Shipment target_date must be a date or None")

        if self.allocations:
            alloc_item_ids = [a.line_item_id for a in self.allocations]
            if len(alloc_item_ids) != len(set(alloc_item_ids)):
                raise InvariantViolation("Duplicate line item allocation within shipment")
            units = {a.unit for a in self.allocations}
            if len(units) == 1:
                derived_qty = sum(a.quantity for a in self.allocations)
                if self.quantity is None:
                    object.__setattr__(self, "quantity", derived_qty)
                elif self.quantity != derived_qty:
                    raise InvariantViolation(f"Shipment quantity {self.quantity} does not match allocation sum {derived_qty}")

        if self.quantity is not None:
            _require_decimal(self.quantity, "Shipment quantity", allow_negative=False, allow_zero=False)
            if self.quantity <= 0:
                raise InvariantViolation("Shipment quantity must be finite and positive")


@dataclass(frozen=True, slots=True)
class PaymentTerm:
    amount: Money
    trigger: str
    due_condition: str
    id: str | None = None
    allocations: tuple[PaymentObligationAllocation, ...] = ()

    def __post_init__(self) -> None:
        if self.id is not None:
            object.__setattr__(
                self,
                "id",
                _normalized_text(self.id, "Payment term id", required=True, max_length=64),
            )
        object.__setattr__(self, "allocations", tuple(self.allocations))
        if not isinstance(self.amount, Money):
            raise TypeError("Payment term amount must be Money")
        if self.amount.amount <= 0:
            raise InvariantViolation("Payment term amount must be positive")
        object.__setattr__(self, "trigger", _normalized_text(self.trigger, "Payment trigger", required=True).casefold())
        object.__setattr__(self, "due_condition", _normalized_text(self.due_condition, "Payment due condition", required=True).casefold())

        if self.allocations:
            alloc_ids = [a.obligation_id for a in self.allocations]
            if len(alloc_ids) != len(set(alloc_ids)):
                raise InvariantViolation("Duplicate obligation allocation within payment term")


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
        if type(self.schema_version) is not int or self.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise InvariantViolation(f"Unsupported trade terms schema version: {self.schema_version}")

        if self.schema_version == TRADE_TERMS_SCHEMA_VERSION_LEGACY:
            for item in self.line_items:
                if item.id is not None:
                    raise InvariantViolation("Schema version 1 line items must not have an id")
            for shipment in self.shipments:
                if shipment.id is not None or shipment.allocations:
                    raise InvariantViolation("Schema version 1 shipments must not have id or allocations")
                if shipment.quantity is None:
                    raise InvariantViolation("Schema version 1 shipments require a quantity")
            for term in self.payment_terms:
                if term.id is not None or term.allocations:
                    raise InvariantViolation("Schema version 1 payment terms must not have id or allocations")

            currencies = {item.unit_price.currency for item in self.line_items}
            currencies.update(term.amount.currency for term in self.payment_terms)
            if len(currencies) != 1:
                raise InvariantViolation("All line items and payment terms must use one currency")
        elif self.schema_version == COLLECTION_TRADE_TERMS_SCHEMA_VERSION:
            seen_ids: set[str] = set()
            for item in self.line_items:
                if item.id is None:
                    raise InvariantViolation("Schema version 2 line items must have an id")
                if item.id in seen_ids:
                    raise InvariantViolation(f"Duplicate id '{item.id}' in trade terms")
                seen_ids.add(item.id)

            for shipment in self.shipments:
                if shipment.id is None:
                    raise InvariantViolation("Schema version 2 shipments must have an id")
                if shipment.id in seen_ids:
                    raise InvariantViolation(f"Duplicate id '{shipment.id}' in trade terms")
                seen_ids.add(shipment.id)
                if not shipment.allocations:
                    raise InvariantViolation("Shipment allocations cannot be empty in schema version 2")

            for term in self.payment_terms:
                if term.id is None:
                    raise InvariantViolation("Schema version 2 payment terms must have an id")
                if term.id in seen_ids:
                    raise InvariantViolation(f"Duplicate id '{term.id}' in trade terms")
                seen_ids.add(term.id)
                if not term.allocations:
                    raise InvariantViolation("Payment term allocations cannot be empty in schema version 2")

            currencies = {item.unit_price.currency for item in self.line_items}
            currencies.update(term.amount.currency for term in self.payment_terms)
            for term in self.payment_terms:
                currencies.update(a.amount.currency for a in term.allocations)
            if len(currencies) != 1:
                raise InvariantViolation("All line items, payment terms, and allocations must use one currency")

            line_item_map = {item.id: item for item in self.line_items}

            # Shipment item allocations validation
            cumulative_item_qty: dict[str, Decimal] = {item.id: Decimal("0") for item in self.line_items}
            for shipment in self.shipments:
                for alloc in shipment.allocations:
                    if alloc.line_item_id not in line_item_map:
                        raise InvariantViolation(f"Allocation references unknown line item '{alloc.line_item_id}'")
                    ref_item = line_item_map[alloc.line_item_id]
                    if alloc.unit != ref_item.unit:
                        raise InvariantViolation(
                            f"Allocation unit '{alloc.unit}' does not match line item unit '{ref_item.unit}'"
                        )
                    cumulative_item_qty[alloc.line_item_id] += alloc.quantity

            for item_id, allocated_qty in cumulative_item_qty.items():
                if allocated_qty > line_item_map[item_id].quantity:
                    raise InvariantViolation(
                        f"Cumulative allocated quantity {allocated_qty} exceeds line item '{item_id}' quantity {line_item_map[item_id].quantity}"
                    )

            # Obligations validation
            valid_obligations: dict[str, Any] = {s.id: s for s in self.shipments}
            valid_obligations.update({item.id: item for item in self.line_items})

            obligation_values: dict[str, Money] = {}
            for item in self.line_items:
                obligation_values[item.id] = item.total
            for shipment in self.shipments:
                s_val = Money(Decimal("0"), self.currency)
                for alloc in shipment.allocations:
                    s_val = s_val.add(line_item_map[alloc.line_item_id].unit_price.multiply(alloc.quantity))
                obligation_values[shipment.id] = s_val

            cumulative_paid: dict[str, Money] = {oid: Money(Decimal("0"), self.currency) for oid in valid_obligations}
            for term in self.payment_terms:
                term_alloc_sum = Money(Decimal("0"), self.currency)
                for alloc in term.allocations:
                    if alloc.obligation_id not in valid_obligations:
                        raise InvariantViolation(
                            f"Payment allocation references unknown obligation '{alloc.obligation_id}'"
                        )
                    term_alloc_sum = term_alloc_sum.add(alloc.amount)
                    cumulative_paid[alloc.obligation_id] = cumulative_paid[alloc.obligation_id].add(alloc.amount)
                if term_alloc_sum != term.amount:
                    raise InvariantViolation("Payment term allocations must sum to payment term amount")

            for obligation_id, paid_val in cumulative_paid.items():
                max_val = obligation_values[obligation_id]
                if paid_val.amount > max_val.amount:
                    raise InvariantViolation(
                        f"Cumulative payment allocation {paid_val.canonical_amount()} exceeds obligation value {max_val.canonical_amount()} for '{obligation_id}'"
                    )

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
            "delivery_location": self.delivery_location.casefold()
            if casefold_display
            else self.delivery_location,
            "incoterm": self.incoterm,
            "cancellation_terms": self.cancellation_terms,
        }
        if self.schema_version == TRADE_TERMS_SCHEMA_VERSION_LEGACY:
            payload["line_items"] = [
                {
                    "description": item.description,
                    "sku": item.sku,
                    "quantity": _decimal(item.quantity),
                    "unit": item.unit,
                    "unit_price": _money(item.unit_price),
                }
                for item in self.line_items
            ]
            payload["shipments"] = [
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
            ]
            payload["payment_terms"] = [
                {
                    "amount": _money(term.amount),
                    "trigger": term.trigger,
                    "due_condition": term.due_condition,
                }
                for term in self.payment_terms
            ]
            # The model has no sequence field, so collection order is presentation-only.
            for collection in ("line_items", "shipments", "payment_terms"):
                payload[collection].sort(
                    key=lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"))
                )
        else:
            payload["line_items"] = [
                {
                    "id": item.id,
                    "description": item.description,
                    "sku": item.sku,
                    "quantity": _decimal(item.quantity),
                    "unit": item.unit,
                    "unit_price": _money(item.unit_price),
                }
                for item in sorted(self.line_items, key=lambda x: x.id or "")
            ]
            payload["shipments"] = [
                {
                    "id": shipment.id,
                    "quantity": _decimal(shipment.quantity) if shipment.quantity is not None else None,
                    "destination": shipment.destination.casefold()
                    if casefold_display
                    else shipment.destination,
                    "target_date": shipment.target_date.isoformat()
                    if shipment.target_date
                    else None,
                    "allocations": [
                        {
                            "line_item_id": alloc.line_item_id,
                            "quantity": _decimal(alloc.quantity),
                            "unit": alloc.unit,
                        }
                        for alloc in sorted(shipment.allocations, key=lambda a: a.line_item_id)
                    ],
                }
                for shipment in sorted(self.shipments, key=lambda s: s.id or "")
            ]
            payload["payment_terms"] = [
                {
                    "id": term.id,
                    "amount": _money(term.amount),
                    "trigger": term.trigger,
                    "due_condition": term.due_condition,
                    "allocations": [
                        {
                            "obligation_id": alloc.obligation_id,
                            "amount": _money(alloc.amount),
                        }
                        for alloc in sorted(term.allocations, key=lambda a: a.obligation_id)
                    ],
                }
                for term in sorted(self.payment_terms, key=lambda t: t.id or "")
            ]
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
        """Reject terms outside the documented trade contract."""
        if self.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise InvariantViolation("Unsupported trade terms schema version")

        if self.schema_version == TRADE_TERMS_SCHEMA_VERSION_LEGACY:
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
        elif self.schema_version == COLLECTION_TRADE_TERMS_SCHEMA_VERSION:
            allocated_per_item = {item.id: Decimal("0") for item in self.line_items}
            for shipment in self.shipments:
                for alloc in shipment.allocations:
                    allocated_per_item[alloc.line_item_id] += alloc.quantity
            for item in self.line_items:
                if allocated_per_item[item.id] != item.quantity:
                    raise InvariantViolation(
                        f"Line item '{item.id}' must be fully allocated before commit "
                        f"(allocated {allocated_per_item[item.id]} of {item.quantity})"
                    )

            for shipment in self.shipments:
                if shipment.target_date is None:
                    raise InvariantViolation(f"Shipment '{shipment.id}' requires a target delivery date to commit")
                if not shipment.destination.strip():
                    raise InvariantViolation(f"Shipment '{shipment.id}' requires a destination to commit")

            for term in self.payment_terms:
                if not term.trigger.strip():
                    raise InvariantViolation(f"Payment term '{term.id}' requires a trigger to commit")
                if not term.due_condition.strip():
                    raise InvariantViolation(f"Payment term '{term.id}' requires a due condition to commit")

    @classmethod
    def from_canonical_json(cls, data: dict[str, Any]) -> "TradeTerms":
        """Reconstruct terms from the dict produced by ``canonical_json``.

        Used to rebuild the domain aggregate from a stored ``AgreementVersion``
        row so commit/approval invariants run through the same domain code
        that produced the hash, rather than being re-derived in SQL.
        """
        schema_version = data.get("schema_version", TRADE_TERMS_SCHEMA_VERSION_LEGACY)
        if schema_version == TRADE_TERMS_SCHEMA_VERSION_LEGACY:
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
                schema_version=schema_version,
            )
        elif schema_version == COLLECTION_TRADE_TERMS_SCHEMA_VERSION:
            return cls(
                buyer_id=OrganizationId(UUID(data["buyer_id"])),
                seller_id=OrganizationId(UUID(data["seller_id"])),
                line_items=tuple(
                    TradeLineItem(
                        id=item["id"],
                        description=item["description"],
                        quantity=Decimal(item["quantity"]),
                        unit=item["unit"],
                        unit_price=_parse_money(item["unit_price"]),
                        sku=item.get("sku"),
                    )
                    for item in data["line_items"]
                ),
                shipments=tuple(
                    ShipmentTerm(
                        id=shipment["id"],
                        quantity=(
                            Decimal(shipment["quantity"])
                            if shipment.get("quantity") is not None
                            else None
                        ),
                        destination=shipment["destination"],
                        target_date=(
                            date.fromisoformat(shipment["target_date"])
                            if shipment.get("target_date")
                            else None
                        ),
                        allocations=tuple(
                            ShipmentItemAllocation(
                                line_item_id=alloc["line_item_id"],
                                quantity=Decimal(alloc["quantity"]),
                                unit=alloc["unit"],
                            )
                            for alloc in shipment.get("allocations", [])
                        ),
                    )
                    for shipment in data["shipments"]
                ),
                payment_terms=tuple(
                    PaymentTerm(
                        id=term["id"],
                        amount=_parse_money(term["amount"]),
                        trigger=term["trigger"],
                        due_condition=term["due_condition"],
                        allocations=tuple(
                            PaymentObligationAllocation(
                                obligation_id=alloc["obligation_id"],
                                amount=_parse_money(alloc["amount"]),
                            )
                            for alloc in term.get("allocations", [])
                        ),
                    )
                    for term in data["payment_terms"]
                ),
                delivery_location=data["delivery_location"],
                incoterm=data.get("incoterm"),
                cancellation_terms=data.get("cancellation_terms", ""),
                schema_version=schema_version,
            )
        else:
            raise InvariantViolation(f"Unsupported trade terms schema version: {schema_version}")


def _decimal(value: Decimal) -> str:
    return canonical_decimal(value)


def _money(value: Money) -> dict[str, str]:
    return {"amount": value.canonical_amount(), "currency": value.currency}


def _parse_money(data: dict[str, str]) -> Money:
    return Money(Decimal(data["amount"]), data["currency"])

