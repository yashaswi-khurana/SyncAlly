"""Validation and authority-boundary tests for versioned AI contracts."""

import unittest
from decimal import Decimal
from uuid import uuid4

from syncally.domain.agreements.trade_terms import TRADE_TERMS_SCHEMA_VERSION
from syncally.domain.ai.contracts import (
    AI_SCHEMA_VERSION,
    AIContractError,
    AIValidationClaim,
    ExtractedFact,
    FactField,
    ProposedTerms,
    ValidationResult,
    scope_extracted_facts,
)
from syncally.domain.conversations import ConstraintStatus
from syncally.domain.shared.identifiers import MessageId, OrganizationId


class AIContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.message_id = MessageId(uuid4())
        self.owner_id = OrganizationId(uuid4())

    def fact_payload(self, **updates: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": AI_SCHEMA_VERSION,
            "field": "quantity",
            "value": "12",
            "currency_or_unit": None,
            "source": {
                "schema_version": AI_SCHEMA_VERSION,
                "message_id": str(self.message_id),
                "quote": "We need 12 boxes.",
                "unknown_reason": None,
            },
        }
        payload.update(updates)
        return payload

    def terms_payload(self, **updates: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": AI_SCHEMA_VERSION,
            "description": "Desk",
            "quantity": "2",
            "unit": "each",
            "unit_price": "12.50",
            "currency": "USD",
            "delivery_destination": "Toronto",
            "delivery_date": "2026-12-01",
        }
        payload.update(updates)
        return payload

    def test_fact_requires_supported_fields_and_complete_versioned_shape(self) -> None:
        fact = ExtractedFact.from_mapping(self.fact_payload())
        self.assertEqual(fact.field, FactField.QUANTITY)
        self.assertEqual(fact.value, "12")
        with self.assertRaisesRegex(AIContractError, "missing required"):
            ExtractedFact.from_mapping({"schema_version": 1, "field": "quantity"})
        with self.assertRaisesRegex(AIContractError, "unsupported fields"):
            ExtractedFact.from_mapping(self.fact_payload(approval="approved"))
        with self.assertRaisesRegex(AIContractError, "unsupported extracted fact field"):
            ExtractedFact.from_mapping(self.fact_payload(field="bank_account"))
        with self.assertRaisesRegex(AIContractError, "schema_version"):
            ExtractedFact.from_mapping(self.fact_payload(schema_version=2))

    def test_fact_values_are_validated_by_their_field_contract(self) -> None:
        with self.assertRaisesRegex(AIContractError, "quantity must be a plain decimal"):
            ExtractedFact.from_mapping(self.fact_payload(value="12 boxes"))
        with self.assertRaisesRegex(AIContractError, "quantity must be finite and positive"):
            ExtractedFact.from_mapping(self.fact_payload(value="0"))
        with self.assertRaisesRegex(AIContractError, "unit_price must be a plain decimal"):
            ExtractedFact.from_mapping(
                self.fact_payload(field="unit_price", value="twelve", currency_or_unit="USD")
            )
        with self.assertRaisesRegex(AIContractError, "requires currency_or_unit USD"):
            ExtractedFact.from_mapping(
                self.fact_payload(field="unit_price", value="12.50", currency_or_unit=None)
            )
        with self.assertRaisesRegex(AIContractError, "ISO date"):
            ExtractedFact.from_mapping(
                self.fact_payload(field="delivery_date", value="tomorrow")
            )
        with self.assertRaisesRegex(AIContractError, "YYYY-MM-DD"):
            ExtractedFact.from_mapping(
                self.fact_payload(field="delivery_date", value="20261201")
            )
        with self.assertRaisesRegex(AIContractError, "well-formed plain text"):
            ExtractedFact.from_mapping(
                self.fact_payload(field="unit", value="invalid/unit")
            )

    def test_grounded_facts_are_bound_to_authorized_source_and_trusted_owner(self) -> None:
        fact = ExtractedFact.from_mapping(self.fact_payload())
        authorized = scope_extracted_facts(
            [fact],
            authorized_messages={self.message_id: "Buyer wrote: We need 12 boxes. Please confirm."},
            owner_organization_id=self.owner_id,
        )
        self.assertEqual(authorized[0].source_message_id, self.message_id)
        self.assertEqual(authorized[0].owner_organization_id, self.owner_id)
        self.assertIs(authorized[0].review_status, ConstraintStatus.EXTRACTED)
        with self.assertRaisesRegex(AIContractError, "unauthorized message"):
            scope_extracted_facts(
                [fact], authorized_messages={}, owner_organization_id=self.owner_id
            )
        with self.assertRaisesRegex(AIContractError, "quote is not present"):
            scope_extracted_facts(
                [fact],
                authorized_messages={self.message_id: "We need 10 boxes."},
                owner_organization_id=self.owner_id,
            )
        fabricated = ExtractedFact.from_mapping(self.fact_payload(value="99"))
        with self.assertRaisesRegex(AIContractError, "not supported by its source quote"):
            scope_extracted_facts(
                [fabricated],
                authorized_messages={self.message_id: "We need 12 boxes."},
                owner_organization_id=self.owner_id,
            )

    def test_unknown_source_is_explicit_but_cannot_become_authorized_fact(self) -> None:
        source = {
            "schema_version": 1,
            "message_id": None,
            "quote": None,
            "unknown_reason": "No source text was available",
        }
        fact = ExtractedFact.from_mapping(self.fact_payload(source=source))
        with self.assertRaisesRegex(AIContractError, "ungrounded"):
            scope_extracted_facts(
                [fact], authorized_messages={}, owner_organization_id=self.owner_id
            )
        with self.assertRaisesRegex(AIContractError, "source requires"):
            ExtractedFact.from_mapping(
                self.fact_payload(
                    source={
                        "schema_version": 1,
                        "message_id": None,
                        "quote": None,
                        "unknown_reason": None,
                    }
                )
            )

    def test_terms_require_supported_exact_decimal_usd_shape(self) -> None:
        terms = ProposedTerms.from_mapping(self.terms_payload())
        self.assertEqual(terms.quantity, Decimal("2"))
        self.assertEqual(terms.unit_price, Decimal("12.50"))
        with self.assertRaisesRegex(AIContractError, "only USD"):
            ProposedTerms.from_mapping(self.terms_payload(currency="CAD"))
        with self.assertRaisesRegex(AIContractError, "decimal string"):
            ProposedTerms.from_mapping(self.terms_payload(quantity=2.0))
        with self.assertRaisesRegex(AIContractError, "positive"):
            ProposedTerms.from_mapping(self.terms_payload(quantity="0"))
        with self.assertRaisesRegex(AIContractError, "supported decimal magnitude"):
            ProposedTerms.from_mapping(self.terms_payload(quantity="1e100000000"))
        with self.assertRaisesRegex(AIContractError, "supported decimal magnitude"):
            ProposedTerms.from_mapping(self.terms_payload(unit_price="1e-100000000"))
        with self.assertRaisesRegex(AIContractError, "input length"):
            ProposedTerms.from_mapping(self.terms_payload(quantity="1" * 65))
        with self.assertRaisesRegex(AIContractError, "unsupported fields"):
            ProposedTerms.from_mapping(self.terms_payload(payment_action="send"))

    def test_largest_supported_decimals_hash_to_a_bounded_representation(self) -> None:
        terms = ProposedTerms.from_mapping(
            self.terms_payload(quantity="1e17", unit_price="1e17")
        ).to_trade_terms(
            buyer_id=OrganizationId(uuid4()),
            seller_id=OrganizationId(uuid4()),
        )
        self.assertEqual(terms.total.amount, Decimal("1e34"))
        self.assertEqual(len(terms.terms_hash), 64)

    def test_terms_conversion_uses_trusted_parties_and_derives_single_full_payment(self) -> None:
        proposal = ProposedTerms.from_mapping(self.terms_payload())
        buyer_id, seller_id = OrganizationId(uuid4()), OrganizationId(uuid4())
        terms = proposal.to_trade_terms(buyer_id=buyer_id, seller_id=seller_id)
        self.assertEqual(terms.buyer_id, buyer_id)
        self.assertEqual(terms.seller_id, seller_id)
        self.assertEqual(terms.total.amount, Decimal("25.00"))
        self.assertEqual(len(terms.payment_terms), 1)
        self.assertEqual(terms.payment_total, terms.total)
        self.assertEqual(terms.schema_version, TRADE_TERMS_SCHEMA_VERSION)

    def test_direct_construction_enforces_the_same_fact_and_proposal_invariants(self) -> None:
        source = ExtractedFact.from_mapping(self.fact_payload()).source
        with self.assertRaisesRegex(AIContractError, "plain decimal"):
            ExtractedFact(
                schema_version=AI_SCHEMA_VERSION,
                field=FactField.QUANTITY,
                value="twelve",
                source=source,
            )
        valid = ProposedTerms.from_mapping(self.terms_payload())
        with self.assertRaisesRegex(AIContractError, "only USD"):
            ProposedTerms(
                schema_version=valid.schema_version,
                description=valid.description,
                quantity=valid.quantity,
                unit=valid.unit,
                unit_price=valid.unit_price,
                currency="CAD",
                delivery_destination=valid.delivery_destination,
                delivery_date=valid.delivery_date,
            )
        with self.assertRaisesRegex(AIContractError, "schema_version"):
            ProposedTerms(
                schema_version=2,
                description=valid.description,
                quantity=valid.quantity,
                unit=valid.unit,
                unit_price=valid.unit_price,
                currency=valid.currency,
                delivery_destination=valid.delivery_destination,
                delivery_date=valid.delivery_date,
            )
        with self.assertRaisesRegex(AIContractError, "supported decimal magnitude"):
            ProposedTerms(
                schema_version=AI_SCHEMA_VERSION,
                description=valid.description,
                quantity=Decimal("1e100000000"),
                unit=valid.unit,
                unit_price=valid.unit_price,
                currency=valid.currency,
                delivery_destination=valid.delivery_destination,
                delivery_date=valid.delivery_date,
            )

    def test_grounding_matches_complete_numbers_and_claimed_units_and_currency(self) -> None:
        partial_number = ExtractedFact.from_mapping(
            self.fact_payload(source={
                "schema_version": 1,
                "message_id": str(self.message_id),
                "quote": "We need 120 boxes.",
                "unknown_reason": None,
            })
        )
        with self.assertRaisesRegex(AIContractError, "not supported by its source quote"):
            scope_extracted_facts(
                [partial_number],
                authorized_messages={self.message_id: "We need 120 boxes."},
                owner_organization_id=self.owner_id,
            )

        wrong_unit = ExtractedFact.from_mapping(
            self.fact_payload(
                currency_or_unit="cases",
                source={
                    "schema_version": 1,
                    "message_id": str(self.message_id),
                    "quote": "We need 12 boxes.",
                    "unknown_reason": None,
                },
            )
        )
        with self.assertRaisesRegex(AIContractError, "not supported by its source quote"):
            scope_extracted_facts(
                [wrong_unit],
                authorized_messages={self.message_id: "We need 12 boxes."},
                owner_organization_id=self.owner_id,
            )
        correct_unit = ExtractedFact.from_mapping(
            self.fact_payload(
                currency_or_unit="boxes",
                source={
                    "schema_version": 1,
                    "message_id": str(self.message_id),
                    "quote": "We need 12 boxes.",
                    "unknown_reason": None,
                },
            )
        )
        self.assertEqual(
            len(
                scope_extracted_facts(
                    [correct_unit],
                    authorized_messages={self.message_id: "We need 12 boxes."},
                    owner_organization_id=self.owner_id,
                )
            ),
            1,
        )

        price_payload = self.fact_payload(
            field="unit_price",
            value="12.50",
            currency_or_unit="USD",
            source={
                "schema_version": 1,
                "message_id": str(self.message_id),
                "quote": "Price: CAD 12.50 each.",
                "unknown_reason": None,
            },
        )
        price_fact = ExtractedFact.from_mapping(price_payload)
        with self.assertRaisesRegex(AIContractError, "not supported by its source quote"):
            scope_extracted_facts(
                [price_fact],
                authorized_messages={self.message_id: "Price: CAD 12.50 each."},
                owner_organization_id=self.owner_id,
            )

        usd_quote = "Price: USD 12.50 each."
        usd_payload = self.fact_payload(
            field="unit_price",
            value="12.50",
            currency_or_unit="USD",
            source={
                "schema_version": 1,
                "message_id": str(self.message_id),
                "quote": usd_quote,
                "unknown_reason": None,
            },
        )
        usd_fact = ExtractedFact.from_mapping(usd_payload)
        candidates = scope_extracted_facts(
            [usd_fact],
            authorized_messages={self.message_id: usd_quote},
            owner_organization_id=self.owner_id,
        )
        self.assertEqual(len(candidates), 1)

        no_currency_quote = "The price is 12.50 each."
        no_currency_payload = self.fact_payload(
            field="unit_price",
            value="12.50",
            currency_or_unit="USD",
            source={
                "schema_version": 1,
                "message_id": str(self.message_id),
                "quote": no_currency_quote,
                "unknown_reason": None,
            },
        )
        no_currency_fact = ExtractedFact.from_mapping(no_currency_payload)
        with self.assertRaisesRegex(AIContractError, "not supported by its source quote"):
            scope_extracted_facts(
                [no_currency_fact],
                authorized_messages={self.message_id: no_currency_quote},
                owner_organization_id=self.owner_id,
            )

    def test_validation_results_are_typed_and_consistent(self) -> None:
        issue = {"schema_version": 1, "code": "MISSING", "path": "quantity", "message": "Required"}
        with self.assertRaisesRegex(AIContractError, "requires validation issues"):
            AIValidationClaim.from_mapping(
                {"schema_version": 1, "status": "INVALID", "issues": []}
            )
        with self.assertRaisesRegex(AIContractError, "unsupported validation status"):
            AIValidationClaim.from_mapping(
                {"schema_version": 1, "status": "APPROVED", "issues": [issue]}
            )
        with self.assertRaisesRegex(AIContractError, "unsupported fields"):
            AIValidationClaim.from_mapping(
                {"schema_version": 1, "status": "VALID", "issues": [], "commit": True}
            )
        claim = AIValidationClaim.from_mapping(
            {"schema_version": 1, "status": "VALID", "issues": []}
        )
        self.assertIs(claim.status, ValidationResult.valid().status)
        self.assertNotIsInstance(claim, ValidationResult)


if __name__ == "__main__":
    unittest.main()
