import unittest
from decimal import Decimal

from syncally.domain.agreements.fulfillment import bounded_quantity, quantity_text
from syncally.domain.shared.errors import InvariantViolation
from syncally.infrastructure.deal_completion import _scaled


class FulfillmentDomainTests(unittest.TestCase):
    def test_quantity_is_finite_positive_and_bounded_before_formatting(self) -> None:
        self.assertEqual(quantity_text(bounded_quantity(Decimal("1.0000000000000000000"))), "1")
        self.assertEqual(quantity_text(bounded_quantity(Decimal("0.000000000000000001"))), "0.000000000000000001")

        for value in (
            Decimal("0"),
            Decimal("-1"),
            Decimal("NaN"),
            Decimal("Infinity"),
            Decimal("100000000000000000000"),
            Decimal("0.0000000000000000001"),
        ):
            with self.subTest(value=value), self.assertRaises(InvariantViolation):
                bounded_quantity(value)

    def test_scaled_quantity_is_exact_for_trailing_zero_exponents(self) -> None:
        self.assertEqual(_scaled(Decimal("1.0000000000000000000")), 10**18)
        self.assertEqual(_scaled(Decimal("0.125")), 125 * 10**15)


if __name__ == "__main__":
    unittest.main()
