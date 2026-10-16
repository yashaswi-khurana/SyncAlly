"""Currency-aware, immutable monetary value object."""

from dataclasses import dataclass
from decimal import Decimal

from syncally.domain.shared.errors import InvariantViolation


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError("Money.amount must be Decimal")
        if not self.amount.is_finite():
            raise InvariantViolation("Money amount must be finite")
        if len(self.currency) != 3 or not self.currency.isascii() or not self.currency.isalpha():
            raise InvariantViolation("Currency must be a three-letter code")
        object.__setattr__(self, "currency", self.currency.upper())

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise InvariantViolation("Cannot add amounts with different currencies")
        return Money(self.amount + other.amount, self.currency)

    def multiply(self, quantity: Decimal) -> "Money":
        if not quantity.is_finite():
            raise InvariantViolation("Quantity must be finite")
        return Money(self.amount * quantity, self.currency)

    def canonical_amount(self) -> str:
        """Return a stable non-exponent decimal string for hashing/serialization."""
        normalized = self.amount.normalize()
        return "0" if normalized.is_zero() else format(normalized, "f")

