"""Typed, append-only fulfillment facts for an agreed delivery obligation."""

from decimal import Decimal
from enum import StrEnum

from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.money import canonical_decimal


class FulfillmentStage(StrEnum):
    SHIPPED = "SHIPPED"
    OBSERVED = "OBSERVED"
    CONFIRMED = "CONFIRMED"


def bounded_quantity(value: Decimal) -> Decimal:
    """Validate a positive quantity representable as a 20,18 decimal."""
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise InvariantViolation("Fulfillment quantity must be a finite positive decimal")

    sign, digits, exponent = value.as_tuple()
    normalized = list(digits)
    while normalized and normalized[-1] == 0:
        normalized.pop()
        exponent += 1
    integer_places = max(0, len(normalized) + exponent)
    fractional_places = max(0, -exponent)
    if integer_places > 20 or fractional_places > 18:
        raise InvariantViolation("Fulfillment quantity exceeds the supported precision")
    return value


def quantity_text(value: Decimal) -> str:
    """Return the exact canonical text used by fulfillment persistence."""
    return canonical_decimal(bounded_quantity(value))
