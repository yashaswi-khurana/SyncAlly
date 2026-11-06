"""Currency-aware, immutable monetary value object."""

from dataclasses import dataclass
from decimal import Decimal, localcontext

from syncally.domain.shared.errors import InvariantViolation


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        bounded_decimal(self.amount, allow_negative=True, field_name="Money amount")
        if len(self.currency) != 3 or not self.currency.isascii() or not self.currency.isalpha():
            raise InvariantViolation("Currency must be a three-letter code")
        object.__setattr__(self, "currency", self.currency.upper())

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise InvariantViolation("Cannot add amounts with different currencies")
        if self.amount.is_zero():
            return Money(other.amount, self.currency)
        if other.amount.is_zero():
            return Money(self.amount, self.currency)

        left, right = self.amount.as_tuple(), other.amount.as_tuple()
        common_exponent = min(left.exponent, right.exponent)
        precision = max(
            len(left.digits) + left.exponent - common_exponent,
            len(right.digits) + right.exponent - common_exponent,
        ) + 1
        with localcontext() as context:
            context.prec = max(context.prec, precision)
            amount = self.amount + other.amount
        return Money(amount, self.currency)

    def multiply(self, quantity: Decimal) -> "Money":
        bounded_decimal(quantity, allow_negative=True, allow_zero=True, field_name="Quantity")
        precision = max(1, len(self.amount.as_tuple().digits) + len(quantity.as_tuple().digits))
        with localcontext() as context:
            context.prec = max(context.prec, precision)
            amount = self.amount * quantity
        return Money(amount, self.currency)

    def canonical_amount(self) -> str:
        """Return a stable non-exponent decimal string for hashing/serialization."""
        return canonical_decimal(self.amount)


def bounded_decimal(
    value: Decimal,
    *,
    max_integer_places: int = 40,
    max_fractional_places: int = 18,
    allow_negative: bool = False,
    allow_zero: bool = True,
    field_name: str = "Decimal",
) -> Decimal:
    """Validate that a Decimal is finite, bounded in exponents and digit places, and respects sign bounds."""
    if not isinstance(value, Decimal):
        raise TypeError(f"{field_name} must be Decimal")
    if not value.is_finite():
        raise InvariantViolation(f"{field_name} must be finite")

    sign, digits, exponent = value.as_tuple()
    if abs(exponent) > 100:
        raise InvariantViolation(f"{field_name} exponent out of range")

    if not allow_negative and value < 0:
        raise InvariantViolation(f"{field_name} cannot be negative")
    if not allow_zero and value.is_zero():
        raise InvariantViolation(f"{field_name} cannot be zero")

    digits_list = list(digits)
    while digits_list and digits_list[-1] == 0:
        digits_list.pop()
        exponent += 1

    if not digits_list:
        integer_places = 0
        fractional_places = 0
    else:
        if exponent >= 0:
            integer_places = len(digits_list) + exponent
            fractional_places = 0
        else:
            integer_places = max(0, len(digits_list) + exponent)
            fractional_places = -exponent

    if integer_places > max_integer_places:
        raise InvariantViolation(
            f"{field_name} exceeds maximum integer places ({max_integer_places})"
        )
    if fractional_places > max_fractional_places:
        raise InvariantViolation(
            f"{field_name} exceeds maximum fractional places ({max_fractional_places})"
        )

    return value


def canonical_decimal(value: Decimal) -> str:
    """Return a context-independent, non-exponent Decimal representation."""
    bounded_decimal(value, allow_negative=True, field_name="Decimal")
    sign, digits, exponent = value.as_tuple()
    if not any(digits):
        return "0"

    digits = list(digits)
    while digits[-1] == 0:
        digits.pop()
        exponent += 1

    coefficient = "".join(str(digit) for digit in digits)
    if exponent >= 0:
        result = coefficient + ("0" * exponent)
    else:
        decimal_point = len(coefficient) + exponent
        if decimal_point > 0:
            result = f"{coefficient[:decimal_point]}.{coefficient[decimal_point:]}"
        else:
            result = f"0.{('0' * -decimal_point)}{coefficient}"

    return f"-{result}" if sign else result

