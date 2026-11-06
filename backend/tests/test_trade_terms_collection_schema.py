import json
from datetime import date
from decimal import Decimal
from unittest import TestCase
from uuid import uuid4

from syncally.application.agreements import compare_agreement_terms
from syncally.application.documents import export_display_terms
from syncally.domain.agreements.obligations import build_obligations, build_payment_milestones
from syncally.domain.agreements.trade_terms import (
    COLLECTION_TRADE_TERMS_SCHEMA_VERSION,
    TRADE_TERMS_SCHEMA_VERSION_LEGACY,
    PaymentObligationAllocation,
    PaymentTerm,
    ShipmentItemAllocation,
    ShipmentTerm,
    TradeLineItem,
    TradeTerms,
)
from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import OrganizationId
from syncally.domain.shared.money import Money, bounded_decimal


class BoundedDecimalTests(TestCase):
    def test_bounded_decimal_accepts_valid_decimals(self) -> None:
        self.assertEqual(bounded_decimal(Decimal("0")), Decimal("0"))
        self.assertEqual(bounded_decimal(Decimal("100.5")), Decimal("100.5"))
        self.assertEqual(
            bounded_decimal(Decimal("-10.5"), allow_negative=True),
            Decimal("-10.5"),
        )
        # 40 integer digits, 18 fractional digits
        max_decimal = Decimal("9" * 40 + "." + "9" * 18)
        self.assertEqual(bounded_decimal(max_decimal), max_decimal)

    def test_bounded_decimal_rejects_non_decimal_type(self) -> None:
        with self.assertRaises(TypeError):
            bounded_decimal("100")  # type: ignore[arg-type]

    def test_bounded_decimal_rejects_non_finite(self) -> None:
        with self.assertRaises(InvariantViolation):
            bounded_decimal(Decimal("NaN"))
        with self.assertRaises(InvariantViolation):
            bounded_decimal(Decimal("Infinity"))
        with self.assertRaises(InvariantViolation):
            bounded_decimal(Decimal("-Infinity"), allow_negative=True)

    def test_bounded_decimal_rejects_out_of_range_exponents(self) -> None:
        with self.assertRaises(InvariantViolation):
            bounded_decimal(Decimal("1e105"))
        with self.assertRaises(InvariantViolation):
            bounded_decimal(Decimal("1e-105"))

    def test_bounded_decimal_rejects_negative_and_zero_when_disallowed(self) -> None:
        with self.assertRaises(InvariantViolation):
            bounded_decimal(Decimal("-1"), allow_negative=False)
        with self.assertRaises(InvariantViolation):
            bounded_decimal(Decimal("0"), allow_zero=False)

    def test_bounded_decimal_rejects_places_exceeding_bounds(self) -> None:
        # 41 integer digits
        with self.assertRaises(InvariantViolation):
            bounded_decimal(Decimal("1" + "0" * 41))
        # 19 fractional digits
        with self.assertRaises(InvariantViolation):
            bounded_decimal(Decimal("0." + "0" * 18 + "1"))


class CollectionSchemaTradeTermsTests(TestCase):
    def setUp(self) -> None:
        self.buyer_id = OrganizationId(uuid4())
        self.seller_id = OrganizationId(uuid4())

    def _sample_schema_2_terms(
        self,
        *,
        item1_id: str = "item-1",
        item2_id: str = "item-2",
        ship1_id: str = "ship-1",
        ship2_id: str = "ship-2",
        pay1_id: str = "pay-1",
        pay2_id: str = "pay-2",
    ) -> TradeTerms:
        item1 = TradeLineItem(
            id=item1_id,
            description="Steel Widget",
            quantity=Decimal("10"),
            unit="pcs",
            unit_price=Money(Decimal("15.00"), "USD"),
            sku="WGT-01",
        )
        item2 = TradeLineItem(
            id=item2_id,
            description="Aluminum Bolt",
            quantity=Decimal("100"),
            unit="pcs",
            unit_price=Money(Decimal("0.50"), "USD"),
            sku="BLT-02",
        )
        # Total line items: (10 * 15.00) + (100 * 0.50) = 150.00 + 50.00 = 200.00 USD
        # Shipment 1: 10 widgets (150.00 USD)
        ship1 = ShipmentTerm(
            id=ship1_id,
            destination="Chicago Hub",
            target_date=date(2030, 6, 1),
            allocations=(
                ShipmentItemAllocation(
                    line_item_id=item1_id,
                    quantity=Decimal("10"),
                    unit="pcs",
                ),
            ),
        )
        # Shipment 2: 100 bolts (50.00 USD)
        ship2 = ShipmentTerm(
            id=ship2_id,
            destination="Detroit Plant",
            target_date=date(2030, 6, 15),
            allocations=(
                ShipmentItemAllocation(
                    line_item_id=item2_id,
                    quantity=Decimal("100"),
                    unit="pcs",
                ),
            ),
        )
        # Payment 1: 150 USD for ship1
        pay1 = PaymentTerm(
            id=pay1_id,
            amount=Money(Decimal("150.00"), "USD"),
            trigger="seller_invoice",
            due_condition="net 30",
            allocations=(
                PaymentObligationAllocation(
                    obligation_id=ship1_id,
                    amount=Money(Decimal("150.00"), "USD"),
                ),
            ),
        )
        # Payment 2: 50 USD for ship2
        pay2 = PaymentTerm(
            id=pay2_id,
            amount=Money(Decimal("50.00"), "USD"),
            trigger="delivery",
            due_condition="on receipt",
            allocations=(
                PaymentObligationAllocation(
                    obligation_id=ship2_id,
                    amount=Money(Decimal("50.00"), "USD"),
                ),
            ),
        )
        return TradeTerms(
            buyer_id=self.buyer_id,
            seller_id=self.seller_id,
            line_items=(item1, item2),
            shipments=(ship1, ship2),
            payment_terms=(pay1, pay2),
            delivery_location="Chicago Hub",
            schema_version=COLLECTION_TRADE_TERMS_SCHEMA_VERSION,
        )

    def test_legacy_schema_1_exact_bytes_and_hash_preservation(self) -> None:
        item = TradeLineItem(
            description="Standard Widget",
            quantity=Decimal("5"),
            unit="units",
            unit_price=Money(Decimal("20.00"), "USD"),
        )
        shipment = ShipmentTerm(
            quantity=Decimal("5"),
            destination="Warehouse Alpha",
            target_date=date(2030, 5, 1),
        )
        payment = PaymentTerm(
            amount=Money(Decimal("100.00"), "USD"),
            trigger="seller_invoice",
            due_condition="when seller invoices",
        )
        terms = TradeTerms(
            buyer_id=self.buyer_id,
            seller_id=self.seller_id,
            line_items=(item,),
            shipments=(shipment,),
            payment_terms=(payment,),
            delivery_location="Warehouse Alpha",
            schema_version=TRADE_TERMS_SCHEMA_VERSION_LEGACY,
        )
        # Ensure schema 1 rejects id and allocations
        with self.assertRaises(InvariantViolation):
            TradeTerms(
                buyer_id=self.buyer_id,
                seller_id=self.seller_id,
                line_items=(
                    TradeLineItem(
                        id="item-x",
                        description="Widget",
                        quantity=Decimal("1"),
                        unit="units",
                        unit_price=Money(Decimal("10"), "USD"),
                    ),
                ),
                shipments=(shipment,),
                payment_terms=(payment,),
                delivery_location="Warehouse Alpha",
                schema_version=TRADE_TERMS_SCHEMA_VERSION_LEGACY,
            )

        storage = terms.to_storage_dict()
        self.assertEqual(storage["schema_version"], 1)
        self.assertNotIn("id", storage["line_items"][0])
        self.assertNotIn("id", storage["shipments"][0])
        self.assertNotIn("allocations", storage["shipments"][0])

        reconstructed = TradeTerms.from_canonical_json(storage)
        self.assertEqual(reconstructed.canonical_json(), terms.canonical_json())
        self.assertEqual(reconstructed.terms_hash, terms.terms_hash)

    def test_schema_2_roundtrip_and_deterministic_order(self) -> None:
        terms_order_a = self._sample_schema_2_terms()

        # Build reverse declaration order
        reversed_line_items = terms_order_a.line_items[::-1]
        reversed_shipments = terms_order_a.shipments[::-1]
        reversed_payment_terms = terms_order_a.payment_terms[::-1]
        terms_order_b = TradeTerms(
            buyer_id=self.buyer_id,
            seller_id=self.seller_id,
            line_items=reversed_line_items,
            shipments=reversed_shipments,
            payment_terms=reversed_payment_terms,
            delivery_location=terms_order_a.delivery_location,
            schema_version=COLLECTION_TRADE_TERMS_SCHEMA_VERSION,
        )

        self.assertEqual(terms_order_a.canonical_json(), terms_order_b.canonical_json())
        self.assertEqual(terms_order_a.terms_hash, terms_order_b.terms_hash)

        # Roundtrip from canonical dict
        storage = terms_order_a.to_storage_dict()
        reconstructed = TradeTerms.from_canonical_json(storage)
        self.assertEqual(reconstructed.canonical_json(), terms_order_a.canonical_json())
        self.assertEqual(reconstructed.terms_hash, terms_order_a.terms_hash)

    def test_schema_2_duplicate_lines_allowed_with_distinct_ids(self) -> None:
        # Two identical items (same description, unit, unit_price, quantity) but distinct IDs
        item1 = TradeLineItem(
            id="batch-1",
            description="Same Item",
            quantity=Decimal("5"),
            unit="pcs",
            unit_price=Money(Decimal("10.00"), "USD"),
        )
        item2 = TradeLineItem(
            id="batch-2",
            description="Same Item",
            quantity=Decimal("5"),
            unit="pcs",
            unit_price=Money(Decimal("10.00"), "USD"),
        )
        ship = ShipmentTerm(
            id="ship-1",
            destination="Depot",
            target_date=date(2030, 1, 1),
            allocations=(
                ShipmentItemAllocation(line_item_id="batch-1", quantity=Decimal("5"), unit="pcs"),
                ShipmentItemAllocation(line_item_id="batch-2", quantity=Decimal("5"), unit="pcs"),
            ),
        )
        pay = PaymentTerm(
            id="pay-1",
            amount=Money(Decimal("100.00"), "USD"),
            trigger="seller_invoice",
            due_condition="immediate",
            allocations=(
                PaymentObligationAllocation(obligation_id="ship-1", amount=Money(Decimal("100.00"), "USD")),
            ),
        )
        terms = TradeTerms(
            buyer_id=self.buyer_id,
            seller_id=self.seller_id,
            line_items=(item1, item2),
            shipments=(ship,),
            payment_terms=(pay,),
            delivery_location="Depot",
            schema_version=COLLECTION_TRADE_TERMS_SCHEMA_VERSION,
        )
        self.assertEqual(terms.total, Money(Decimal("100.00"), "USD"))

    def test_schema_2_duplicate_ids_rejected(self) -> None:
        # Duplicate ID within line items
        with self.assertRaises(InvariantViolation):
            self._sample_schema_2_terms(item1_id="dup-id", item2_id="dup-id")

        # Duplicate ID across line item and shipment
        with self.assertRaises(InvariantViolation):
            self._sample_schema_2_terms(item1_id="shared-id", ship1_id="shared-id")

        # Duplicate ID across shipment and payment
        with self.assertRaises(InvariantViolation):
            self._sample_schema_2_terms(ship1_id="shared-id", pay1_id="shared-id")

    def test_schema_2_partial_allocation_and_overallocation_rejection(self) -> None:
        item = TradeLineItem(
            id="item-1",
            description="Box",
            quantity=Decimal("10"),
            unit="box",
            unit_price=Money(Decimal("10.00"), "USD"),
        )
        # Partial allocation: shipment allocates 6 of 10
        ship_partial = ShipmentTerm(
            id="ship-1",
            destination="Hub",
            target_date=date(2030, 1, 1),
            allocations=(
                ShipmentItemAllocation(line_item_id="item-1", quantity=Decimal("6"), unit="box"),
            ),
        )
        pay = PaymentTerm(
            id="pay-1",
            amount=Money(Decimal("100.00"), "USD"),
            trigger="invoice",
            due_condition="net 30",
            allocations=(
                PaymentObligationAllocation(obligation_id="item-1", amount=Money(Decimal("100.00"), "USD")),
            ),
        )
        # Partial allocation is valid at TradeTerms creation
        partial_terms = TradeTerms(
            buyer_id=self.buyer_id,
            seller_id=self.seller_id,
            line_items=(item,),
            shipments=(ship_partial,),
            payment_terms=(pay,),
            delivery_location="Hub",
            schema_version=COLLECTION_TRADE_TERMS_SCHEMA_VERSION,
        )
        # But commit validation rejects partially allocated line items
        with self.assertRaises(InvariantViolation):
            partial_terms.validate_for_commit()

        # Overallocation: shipment allocates 11 of 10
        ship_over = ShipmentTerm(
            id="ship-over",
            destination="Hub",
            target_date=date(2030, 1, 1),
            allocations=(
                ShipmentItemAllocation(line_item_id="item-1", quantity=Decimal("11"), unit="box"),
            ),
        )
        with self.assertRaises(InvariantViolation):
            TradeTerms(
                buyer_id=self.buyer_id,
                seller_id=self.seller_id,
                line_items=(item,),
                shipments=(ship_over,),
                payment_terms=(pay,),
                delivery_location="Hub",
                schema_version=COLLECTION_TRADE_TERMS_SCHEMA_VERSION,
            )

    def test_schema_2_allocation_validation_errors(self) -> None:
        item = TradeLineItem(
            id="item-1",
            description="Steel",
            quantity=Decimal("10"),
            unit="kg",
            unit_price=Money(Decimal("10.00"), "USD"),
        )
        # Unknown line item id
        with self.assertRaises(InvariantViolation):
            ShipmentTerm(
                id="ship-1",
                destination="Hub",
                allocations=(
                    ShipmentItemAllocation(line_item_id="unknown-id", quantity=Decimal("5"), unit="kg"),
                ),
            )
            TradeTerms(
                buyer_id=self.buyer_id,
                seller_id=self.seller_id,
                line_items=(item,),
                shipments=(
                    ShipmentTerm(
                        id="ship-1",
                        destination="Hub",
                        allocations=(
                            ShipmentItemAllocation(line_item_id="unknown-id", quantity=Decimal("5"), unit="kg"),
                        ),
                    ),
                ),
                payment_terms=(
                    PaymentTerm(
                        id="pay-1",
                        amount=Money(Decimal("100.00"), "USD"),
                        trigger="invoice",
                        due_condition="immediate",
                        allocations=(
                            PaymentObligationAllocation(obligation_id="item-1", amount=Money(Decimal("100.00"), "USD")),
                        ),
                    ),
                ),
                delivery_location="Hub",
                schema_version=COLLECTION_TRADE_TERMS_SCHEMA_VERSION,
            )

        # Mismatched unit
        with self.assertRaises(InvariantViolation):
            TradeTerms(
                buyer_id=self.buyer_id,
                seller_id=self.seller_id,
                line_items=(item,),
                shipments=(
                    ShipmentTerm(
                        id="ship-1",
                        destination="Hub",
                        allocations=(
                            ShipmentItemAllocation(line_item_id="item-1", quantity=Decimal("5"), unit="meters"),
                        ),
                    ),
                ),
                payment_terms=(
                    PaymentTerm(
                        id="pay-1",
                        amount=Money(Decimal("100.00"), "USD"),
                        trigger="invoice",
                        due_condition="immediate",
                        allocations=(
                            PaymentObligationAllocation(obligation_id="item-1", amount=Money(Decimal("100.00"), "USD")),
                        ),
                    ),
                ),
                delivery_location="Hub",
                schema_version=COLLECTION_TRADE_TERMS_SCHEMA_VERSION,
            )

    def test_schema_2_payment_allocation_exceeding_obligation_value_rejected(self) -> None:
        item = TradeLineItem(
            id="item-1",
            description="Wood",
            quantity=Decimal("10"),
            unit="planks",
            unit_price=Money(Decimal("10.00"), "USD"),  # Total 100 USD
        )
        ship = ShipmentTerm(
            id="ship-1",
            destination="Hub",
            allocations=(
                ShipmentItemAllocation(line_item_id="item-1", quantity=Decimal("10"), unit="planks"),
            ),
        )
        # ship-1 value is 100 USD. Trying to allocate 120 USD to ship-1
        pay = PaymentTerm(
            id="pay-1",
            amount=Money(Decimal("100.00"), "USD"),
            trigger="invoice",
            due_condition="immediate",
            allocations=(
                PaymentObligationAllocation(obligation_id="ship-1", amount=Money(Decimal("120.00"), "USD")),
            ),
        )
        with self.assertRaises(InvariantViolation):
            TradeTerms(
                buyer_id=self.buyer_id,
                seller_id=self.seller_id,
                line_items=(item,),
                shipments=(ship,),
                payment_terms=(pay,),
                delivery_location="Hub",
                schema_version=COLLECTION_TRADE_TERMS_SCHEMA_VERSION,
            )

    def test_obligations_and_milestones_derivation(self) -> None:
        terms = self._sample_schema_2_terms()
        obligations = build_obligations(terms)
        self.assertEqual(len(obligations), 4)  # 2 delivery + 2 payment
        delivery_obs = [o for o in obligations if o.obligation_type == "DELIVERY"]
        payment_obs = [o for o in obligations if o.obligation_type == "PAYMENT"]

        self.assertEqual({o.source_terms_reference for o in delivery_obs}, {"ship-1", "ship-2"})
        self.assertEqual({o.source_terms_reference for o in payment_obs}, {"pay-1", "pay-2"})

        milestones = build_payment_milestones(terms)
        self.assertEqual(len(milestones), 2)
        self.assertEqual({m.source_terms_reference for m in milestones}, {"pay-1", "pay-2"})

    def test_export_display_terms_schema_2_success_and_safety_bounds(self) -> None:
        terms = self._sample_schema_2_terms()
        storage = terms.to_storage_dict()

        exported = export_display_terms(storage)
        self.assertEqual(exported["schema_version"], 2)
        self.assertEqual(len(exported["line_items"]), 2)
        self.assertEqual(exported["line_items"][0]["id"], "item-1")

        # Corrupt storage with giant decimal in allocation
        corrupt = json.loads(json.dumps(storage))
        corrupt["shipments"][0]["allocations"][0]["quantity"] = "1" + ("0" * 3000000)
        with self.assertRaises(Exception):
            export_display_terms(corrupt)

    def test_compare_agreement_terms_schema_2(self) -> None:
        terms_before = self._sample_schema_2_terms()
        before_dict = terms_before.to_storage_dict()

        # Modify item-1 unit price and add item-3
        item1_mod = TradeLineItem(
            id="item-1",
            description="Steel Widget Modified",
            quantity=Decimal("10"),
            unit="pcs",
            unit_price=Money(Decimal("16.00"), "USD"),
        )
        item2 = terms_before.line_items[1]
        ship = ShipmentTerm(
            id="ship-1",
            destination="Chicago Hub",
            allocations=(
                ShipmentItemAllocation(line_item_id="item-1", quantity=Decimal("10"), unit="pcs"),
                ShipmentItemAllocation(line_item_id="item-2", quantity=Decimal("100"), unit="pcs"),
            ),
        )
        # Total = 160 + 50 = 210 USD
        pay = PaymentTerm(
            id="pay-1",
            amount=Money(Decimal("210.00"), "USD"),
            trigger="seller_invoice",
            due_condition="net 30",
            allocations=(
                PaymentObligationAllocation(obligation_id="ship-1", amount=Money(Decimal("210.00"), "USD")),
            ),
        )
        terms_after = TradeTerms(
            buyer_id=self.buyer_id,
            seller_id=self.seller_id,
            line_items=(item1_mod, item2),
            shipments=(ship,),
            payment_terms=(pay,),
            delivery_location="Chicago Hub",
            schema_version=COLLECTION_TRADE_TERMS_SCHEMA_VERSION,
        )
        after_dict = terms_after.to_storage_dict()

        diff = compare_agreement_terms(before_dict, after_dict)
        # item-1 should be recognized as modified because id="item-1" matches
        self.assertEqual(len(diff["collections"]["line_items"]["modified"]), 1)
        self.assertEqual(diff["collections"]["line_items"]["modified"][0]["before"]["id"], "item-1")
        self.assertEqual(diff["collections"]["line_items"]["modified"][0]["after"]["id"], "item-1")
