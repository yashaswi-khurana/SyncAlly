"""Comprehensive test suite for opening request normalization and AI integration.

Verifies schema compliance, diverse phrasings (colloquial, formal, RFQs),
offline rule-based extraction, graceful fallback handling, and provenance tracking.
"""

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from pydantic import ValidationError

from syncally.application.ai import (
    AIProvenance,
    AIRetryPolicy,
    AITransientError,
    OpeningRequestNormalizationResult,
    OpeningRequestNormalizationService,
    extract_normalized_requirement,
    normalize_opening_request,
)
from syncally.config import Settings
from syncally.domain.ai.contracts import (
    NormalizedRequirement,
    NormalizedTradeRequirements,
)
from syncally.infrastructure.ai.demo import DemoAISuggestionProvider
from syncally.infrastructure.ai.selection import ConfiguredAIProvider


class OpeningRequestNormalizationTests(unittest.TestCase):
    def test_opening_request_does_not_retry_transient_failures_by_default(self) -> None:
        provider = MagicMock()
        provider.provenance = AIProvenance(provider="gemini", mode="gemini")
        provider.normalize_opening_request.side_effect = AITransientError("timeout")
        provider.fallback_normalize_opening_request.side_effect = AITransientError("no fallback")
        result = normalize_opening_request("We need 12 boxes", provider)
        self.assertEqual(provider.normalize_opening_request.call_count, 1)
        self.assertEqual(result.provenance.provider, "offline")

    def test_remote_configuration_reports_ai_assisted_normalization(self) -> None:
        config = Settings(_env_file=None, app_env="test", ai_provider="openai",
                          ai_remote_egress_enabled=True, openai_model="test-model",
                          openai_api_key="test-key")
        with patch("syncally.infrastructure.ai.openai.OpenAIChatCompletions.extract_facts", return_value=()):
            result = normalize_opening_request("We need 12 boxes", ConfiguredAIProvider(config))
        self.assertEqual(result.provenance.provider, "openai")
        self.assertEqual(result.provenance.mode, "openai")
        self.assertEqual(result.provenance.model, "test-model")

    def test_schema_contract_and_alias(self) -> None:
        self.assertIs(NormalizedTradeRequirements, NormalizedRequirement)
        req = NormalizedRequirement(
            item_description="precision bolts",
            category="Fasteners",
            quantity=Decimal("500"),
            unit="units",
            target_unit_price=Decimal("15.00"),
            budget=Decimal("7500.00"),
            currency="USD",
            destination_country_code="DE",
            destination_name="Berlin, Germany",
            target_delivery_date=date(2026, 12, 1),
            capabilities_required=["Manufacturing"],
            payment_terms="Net 30",
            raw_text="Test prompt",
        )
        self.assertEqual(req.item_description, "precision bolts")
        self.assertEqual(req.category, "Fasteners")
        self.assertEqual(req.quantity, Decimal("500"))
        self.assertEqual(req.unit, "units")
        self.assertEqual(req.target_unit_price, Decimal("15.00"))
        self.assertEqual(req.budget, Decimal("7500.00"))
        self.assertEqual(req.currency, "USD")
        self.assertEqual(req.destination_country_code, "DE")
        self.assertEqual(req.destination_name, "Berlin, Germany")
        self.assertEqual(req.target_delivery_date, date(2026, 12, 1))
        self.assertEqual(req.capabilities_required, ["Manufacturing"])
        self.assertEqual(req.payment_terms, "Net 30")
        self.assertEqual(req.raw_text, "Test prompt")

        # Immutability check
        with self.assertRaises(ValidationError):
            req.item_description = "mutated"  # type: ignore[misc]

    def test_formal_rfq_phrasing_normalization(self) -> None:
        text = (
            "We need 500 units of stainless steel bolts delivered to Berlin, Germany "
            "by 2026-12-01. Budget is $15 per unit."
        )
        result = extract_normalized_requirement(text)

        self.assertEqual(result.item_description, "stainless steel bolts")
        self.assertEqual(result.category, "Fasteners")
        self.assertEqual(result.quantity, Decimal("500"))
        self.assertEqual(result.unit, "units")
        self.assertEqual(result.target_unit_price, Decimal("15"))
        self.assertEqual(result.budget, Decimal("7500"))
        self.assertIsNone(result.currency)
        self.assertEqual(result.destination_country_code, "DE")
        self.assertEqual(result.destination_name, "Berlin, Germany")
        self.assertEqual(result.target_delivery_date, date(2026, 12, 1))
        self.assertEqual(result.raw_text, text)

    def test_technical_capabilities_and_budget_phrasing(self) -> None:
        text = "Looking for precision CNC machining for 200 automotive parts in Canada under 5000 USD."
        result = extract_normalized_requirement(text)

        self.assertEqual(result.item_description, "automotive parts")
        self.assertEqual(result.category, "Automotive")
        self.assertEqual(result.quantity, Decimal("200"))
        self.assertEqual(result.unit, "parts")
        self.assertEqual(result.budget, Decimal("5000"))
        self.assertEqual(result.target_unit_price, Decimal("25"))
        self.assertEqual(result.currency, "USD")
        self.assertEqual(result.destination_country_code, "CA")
        self.assertEqual(result.destination_name, "Canada")
        self.assertIn("precision CNC machining", result.capabilities_required)
        self.assertIsNone(result.target_delivery_date)
        self.assertEqual(result.raw_text, text)

    def test_rfq_metric_units_and_unit_price_phrasing(self) -> None:
        text = "RFQ: 10,000 meters of copper wire to Tokyo, Japan. Target price 2.50 USD/m."
        result = extract_normalized_requirement(text)

        self.assertEqual(result.item_description, "copper wire")
        self.assertEqual(result.category, "Electronics")
        self.assertEqual(result.quantity, Decimal("10000"))
        self.assertEqual(result.unit, "meters")
        self.assertEqual(result.target_unit_price, Decimal("2.50"))
        self.assertEqual(result.budget, Decimal("25000.00"))
        self.assertEqual(result.currency, "USD")
        self.assertEqual(result.destination_country_code, "JP")
        self.assertEqual(result.destination_name, "Tokyo, Japan")

    def test_colloquial_informal_phrasing_normalization(self) -> None:
        text = "Hey, can you supply 50 boxes of packaging materials to US by next month?"
        result = extract_normalized_requirement(text)

        self.assertEqual(result.item_description, "packaging materials")
        self.assertEqual(result.category, "Packaging")
        self.assertEqual(result.quantity, Decimal("50"))
        self.assertEqual(result.unit, "boxes")
        self.assertEqual(result.destination_country_code, "US")
        self.assertEqual(result.destination_name, "US")
        self.assertIn("Packaging", result.capabilities_required)
        today = date.today()
        next_month_year = today.year + (1 if today.month == 12 else 0)
        next_month = 1 if today.month == 12 else today.month + 1
        self.assertEqual(result.target_delivery_date, date(next_month_year, next_month, 1))

    def test_agriculture_and_payment_terms_phrasing(self) -> None:
        text = "Need 1000 kg organic wheat delivered to France by 2026-10-15. Net 30 payment terms."
        result = extract_normalized_requirement(text)

        self.assertEqual(result.item_description, "organic wheat")
        self.assertEqual(result.category, "Agriculture")
        self.assertEqual(result.quantity, Decimal("1000"))
        self.assertEqual(result.unit, "kg")
        self.assertEqual(result.destination_country_code, "FR")
        self.assertEqual(result.destination_name, "France")
        self.assertEqual(result.target_delivery_date, date(2026, 10, 15))
        self.assertEqual(result.payment_terms, "Net 30")

    def test_injection_molding_and_total_budget(self) -> None:
        text = "Seeking injection molding supplier for 5,000 plastic housings in Germany. Total budget $20,000."
        result = extract_normalized_requirement(text)

        self.assertEqual(result.item_description, "plastic housings")
        self.assertEqual(result.category, "Plastics & Polymers")
        self.assertEqual(result.quantity, Decimal("5000"))
        self.assertEqual(result.unit, "housings")
        self.assertEqual(result.budget, Decimal("20000"))
        self.assertEqual(result.target_unit_price, Decimal("4"))
        self.assertIsNone(result.currency)
        self.assertEqual(result.destination_country_code, "DE")
        self.assertEqual(result.destination_name, "Germany")
        self.assertIn("Injection Molding", result.capabilities_required)

    def test_empty_and_whitespace_inputs(self) -> None:
        for empty_text in ("", "   ", "\n\t  "):
            result = extract_normalized_requirement(empty_text)
            self.assertEqual(result.raw_text, empty_text)
            self.assertIsNone(result.item_description)
            self.assertIsNone(result.quantity)
            self.assertIsNone(result.unit)
            self.assertIsNone(result.budget)
            self.assertIsNone(result.target_unit_price)
            self.assertIsNone(result.currency)
            self.assertIsNone(result.destination_country_code)
            self.assertIsNone(result.destination_name)
            self.assertIsNone(result.target_delivery_date)
            self.assertEqual(result.capabilities_required, [])
            self.assertIsNone(result.payment_terms)

    def test_conversational_non_procurement_input(self) -> None:
        text = "Good afternoon! I would love to connect and learn more about what your company offers."
        result = extract_normalized_requirement(text)
        self.assertEqual(result.raw_text, text)
        self.assertIsNone(result.item_description)
        self.assertIsNone(result.quantity)
        self.assertIsNone(result.target_unit_price)

    def test_geographic_resolution_various_destinations(self) -> None:
        cases = (
            ("Deliver to Seattle, WA by 2026-11-20", "Seattle, WA", "US"),
            ("Shipment to Toronto, ON", "Toronto, ON", "CA"),
            ("Destination: London, UK", "London, UK", "GB"),
            ("To be delivered in Paris, France", "Paris, France", "FR"),
            ("Delivery at Sydney, Australia", "Sydney, Australia", "AU"),
            ("Destination: Tokyo, Japan", "Tokyo, Japan", "JP"),
        )
        for text, expected_dest, expected_cc in cases:
            res = extract_normalized_requirement(text)
            self.assertEqual(res.destination_name, expected_dest)
            self.assertEqual(res.destination_country_code, expected_cc)

    def test_currency_symbols_and_formats(self) -> None:
        currencies = (
            ("Order of 100 widgets at €50 each", "EUR", Decimal("50")),
            ("Order of 100 widgets at £25.50 each", "GBP", Decimal("25.50")),
            ("100 units under C$ 3000", "CAD", Decimal("3000")),
            ("100 units under NZ$ 3000", "NZD", Decimal("3000")),
            ("100 units under HK$ 3000", "HKD", Decimal("3000")),
            ("100 units under S$ 3000", "SGD", Decimal("3000")),
            ("100 units at 5000 JPY each", "JPY", Decimal("5000")),
            ("100 units budget 15000 INR", "INR", Decimal("15000")),
            ("100 units budget 15000 BRL", "BRL", Decimal("15000")),
        )
        for text, curr, amount in currencies:
            res = extract_normalized_requirement(text)
            self.assertEqual(res.currency, curr)
            if res.target_unit_price is not None:
                self.assertIn(amount, (res.target_unit_price, res.budget))

    def test_ambiguous_dollar_symbol_does_not_assume_usd(self) -> None:
        result = extract_normalized_requirement("Need 100 units at $45.50 each.")
        self.assertEqual(result.target_unit_price, Decimal("45.50"))
        self.assertIsNone(result.currency)

    def test_demo_provider_normalize_opening_request_method(self) -> None:
        provider = DemoAISuggestionProvider()
        text = "We need 500 units of stainless steel bolts delivered to Berlin, Germany by 2026-12-01. Budget is $15 per unit."
        req = provider.normalize_opening_request(text)
        self.assertIsInstance(req, NormalizedRequirement)
        self.assertEqual(req.item_description, "stainless steel bolts")
        self.assertEqual(req.destination_country_code, "DE")

    def test_configured_ai_provider_offline_mode_normalization(self) -> None:
        settings = Settings(
            app_env="test",
            ai_provider="offline",
        )
        provider = ConfiguredAIProvider(settings)
        text = "RFQ: 10,000 meters of copper wire to Tokyo, Japan. Target price 2.50 USD/m."

        result = normalize_opening_request(text, provider=provider)
        self.assertIsInstance(result, OpeningRequestNormalizationResult)
        self.assertEqual(result.requirements.item_description, "copper wire")
        self.assertEqual(result.provenance.provider, "offline")
        self.assertEqual(result.provenance.mode, "offline")
        self.assertIsNone(result.provenance.fallback_reason)

    def test_configured_ai_provider_unconfigured_credentials_fallback(self) -> None:
        settings = Settings(
            app_env="test",
            ai_provider="openai_with_offline_fallback",
            ai_remote_egress_enabled=True,
            openai_model="gpt-4o",
            openai_api_key="",  # unconfigured key
        )
        provider = ConfiguredAIProvider(settings)
        text = "Looking for precision CNC machining for 200 automotive parts in Canada under 5000 USD."

        result = normalize_opening_request(text, provider=provider)
        self.assertIsInstance(result, OpeningRequestNormalizationResult)
        self.assertEqual(result.requirements.item_description, "automotive parts")
        self.assertEqual(result.provenance.provider, "offline")
        self.assertEqual(result.provenance.mode, "openai_with_offline_fallback")
        self.assertEqual(result.provenance.fallback_reason, "missing_credentials")

    def test_transient_error_fallback_handling(self) -> None:
        mock_provider = MagicMock()
        mock_provider.normalize_opening_request.side_effect = AITransientError("Network connection reset")
        mock_provider.provenance = AIProvenance(
            provider="openai",
            mode="openai_with_offline_fallback",
            model="gpt-4o",
            context_scope="authorized",
        )
        # fallback method sets provenance to fallback
        def mock_fallback(text: str) -> NormalizedRequirement:
            mock_provider.provenance = AIProvenance(
                provider="offline",
                mode="openai_with_offline_fallback",
                fallback_reason="transient_exhausted",
            )
            return extract_normalized_requirement(text)

        mock_provider.fallback_normalize_opening_request = mock_fallback

        text = "Need 1000 kg organic wheat delivered to France by 2026-10-15. Net 30 payment terms."
        result = normalize_opening_request(
            text,
            provider=mock_provider,
            policy=AIRetryPolicy(max_attempts=2, timeout_seconds=1.0, backoff_seconds=0.01),
        )

        self.assertEqual(result.requirements.item_description, "organic wheat")
        self.assertEqual(result.provenance.provider, "offline")
        self.assertEqual(result.provenance.fallback_reason, "transient_exhausted")

    def test_opening_request_normalization_service(self) -> None:
        service = OpeningRequestNormalizationService()
        text = "Hey, can you supply 50 boxes of packaging materials to US by next month?"
        result = service.normalize(text)

        self.assertIsInstance(result, OpeningRequestNormalizationResult)
        self.assertEqual(result.requirements.item_description, "packaging materials")
        self.assertEqual(result.provenance.provider, "offline")
        self.assertEqual(result.provenance.mode, "offline")

    def test_extreme_length_and_boundary_resilience(self) -> None:
        large_padding = " " * 5000 + "Important note: Please review details carefully. " * 50
        text = f"We need 500 units of stainless steel bolts delivered to Berlin, Germany by 2026-12-01. Budget is $15 per unit. {large_padding}"
        result = extract_normalized_requirement(text)

        self.assertEqual(result.item_description, "stainless steel bolts")
        self.assertEqual(result.quantity, Decimal("500"))
        self.assertEqual(result.destination_country_code, "DE")
        self.assertEqual(result.raw_text, text)


if __name__ == "__main__":
    unittest.main()
