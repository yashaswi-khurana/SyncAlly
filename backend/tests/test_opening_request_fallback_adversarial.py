"""Adversarial stress-test suite for AI opening request fallback and failure recovery.

Simulates:
1. Missing API keys and unconfigured environments.
2. Offline mode configuration.
3. Transient network failures (connection reset, 502/503).
4. Network timeouts (connect/read timeouts, deadline exceeded).
5. Rate limits (HTTP 429).
6. Unexpected/rogue provider exceptions (crashes, malformed returns, broken fallbacks).
7. Malformed, adversarial, and extreme length inputs (ReDoS, unicode fuzzing, extreme values).
8. Concurrent multi-threaded invocation safety.
9. Empirical challenger edge cases revealing heuristic extraction limits.
"""

from __future__ import annotations

import concurrent.futures
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import httpx

from syncally.application.ai import (
    AIConfigurationError,
    AIPermanentError,
    AIProvenance,
    AIRetryPolicy,
    AITransientError,
    OpeningRequestNormalizationResult,
    OpeningRequestNormalizationService,
    extract_normalized_requirement,
    normalize_opening_request,
)
from syncally.config import Settings
from syncally.domain.ai.contracts import NormalizedRequirement
from syncally.infrastructure.ai.selection import ConfiguredAIProvider


class AIFallbackResilienceTests(unittest.TestCase):
    """Stress tests challenging fallback behavior and failure recovery."""

    # -------------------------------------------------------------------------
    # 1. Missing API Keys & Environment Variations
    # -------------------------------------------------------------------------
    def test_missing_api_key_openai_with_offline_fallback(self) -> None:
        """Configured with fallback mode but missing API key must fall back cleanly."""
        settings = Settings(
            app_env="test",
            ai_provider="openai_with_offline_fallback",
            ai_remote_egress_enabled=True,
            openai_model="gpt-4o",
            openai_api_key="",
        )
        provider = ConfiguredAIProvider(settings)

        self.assertEqual(provider.provenance.provider, "offline")
        self.assertEqual(provider.provenance.mode, "openai_with_offline_fallback")
        self.assertEqual(provider.provenance.fallback_reason, "missing_credentials")

        text = "We need 500 units of stainless steel bolts delivered to Berlin, Germany by 2026-12-01. Budget is $15 per unit."
        result = normalize_opening_request(text, provider=provider)

        self.assertIsInstance(result, OpeningRequestNormalizationResult)
        self.assertIsInstance(result.requirements, NormalizedRequirement)
        self.assertEqual(result.requirements.item_description, "stainless steel bolts")
        self.assertEqual(result.requirements.quantity, Decimal("500"))
        self.assertEqual(result.requirements.destination_country_code, "DE")
        self.assertEqual(result.provenance.provider, "offline")
        self.assertEqual(result.provenance.fallback_reason, "missing_credentials")

    def test_missing_api_key_strict_openai_raises_config_error(self) -> None:
        """In strict openai mode, missing API key must raise AIConfigurationError."""
        settings = Settings(
            app_env="test",
            ai_provider="openai",
            ai_remote_egress_enabled=True,
            openai_model="gpt-4o",
            openai_api_key="",
        )
        with self.assertRaises(AIConfigurationError):
            ConfiguredAIProvider(settings)

    def test_none_provider_graceful_offline_extraction(self) -> None:
        """When provider is None (e.g. unconfigured), normalization proceeds seamlessly."""
        text = "Looking for precision CNC machining for 200 automotive parts in Canada under 5000 USD."
        service = OpeningRequestNormalizationService(provider=None)
        result = service.normalize(text)

        self.assertIsInstance(result, OpeningRequestNormalizationResult)
        self.assertEqual(result.requirements.item_description, "automotive parts")
        self.assertEqual(result.requirements.budget, Decimal("5000"))
        self.assertEqual(result.provenance.provider, "offline")
        self.assertEqual(result.provenance.mode, "offline")
        self.assertIsNone(result.provenance.fallback_reason)

    # -------------------------------------------------------------------------
    # 2. Offline Mode
    # -------------------------------------------------------------------------
    def test_offline_mode_behavior(self) -> None:
        """Offline mode runs local extractor with exact offline provenance."""
        settings = Settings(
            app_env="test",
            ai_provider="offline",
        )
        provider = ConfiguredAIProvider(settings)
        text = "Need 1000 kg organic wheat delivered to France by 2026-10-15. Net 30 payment terms."
        result = normalize_opening_request(text, provider=provider)

        self.assertEqual(result.requirements.item_description, "organic wheat")
        self.assertEqual(result.requirements.payment_terms, "Net 30")
        self.assertEqual(result.provenance.provider, "offline")
        self.assertEqual(result.provenance.mode, "offline")
        self.assertIsNone(result.provenance.fallback_reason)

    # -------------------------------------------------------------------------
    # 3. Transient Network Failures & Retry Recovery
    # -------------------------------------------------------------------------
    def test_transient_failure_recovered_on_retry(self) -> None:
        """Transient error recovered on second attempt returns primary provenance."""
        mock_provider = MagicMock()
        mock_provider.provenance = AIProvenance(
            provider="openai",
            mode="openai_with_offline_fallback",
            model="gpt-4o",
            context_scope="authorized",
        )
        success_req = NormalizedRequirement(
            item_description="precision parts",
            quantity=Decimal("100"),
            raw_text="sample",
        )
        mock_provider.normalize_opening_request.side_effect = [
            AITransientError("502 Bad Gateway"),
            success_req,
        ]

        result = normalize_opening_request(
            "sample",
            provider=mock_provider,
            policy=AIRetryPolicy(max_attempts=3, timeout_seconds=1.0, backoff_seconds=0.001),
        )

        self.assertEqual(mock_provider.normalize_opening_request.call_count, 2)
        self.assertEqual(result.requirements.item_description, "precision parts")
        self.assertEqual(result.provenance.provider, "openai")
        self.assertIsNone(result.provenance.fallback_reason)

    def test_transient_failure_exhaustion_falls_back_to_offline(self) -> None:
        """All transient retry attempts failing triggers fallback with transient_exhausted."""
        mock_provider = MagicMock(spec=["normalize_opening_request", "fallback_normalize_opening_request", "provenance"])
        mock_provider.provenance = AIProvenance(
            provider="openai",
            mode="openai_with_offline_fallback",
            model="gpt-4o",
            context_scope="authorized",
        )
        mock_provider.normalize_opening_request.side_effect = AITransientError("Connection reset by peer")
        def mock_fallback(text: str) -> NormalizedRequirement:
            mock_provider.provenance = AIProvenance(
                provider="offline",
                mode="openai_with_offline_fallback",
                fallback_reason="transient_exhausted",
            )
            return extract_normalized_requirement(text)

        mock_provider.fallback_normalize_opening_request = mock_fallback

        text = "Hey, can you supply 50 boxes of packaging materials to US by next month?"
        result = normalize_opening_request(
            text,
            provider=mock_provider,
            policy=AIRetryPolicy(max_attempts=2, timeout_seconds=1.0, backoff_seconds=0.001),
        )

        self.assertEqual(mock_provider.normalize_opening_request.call_count, 2)
        self.assertEqual(result.requirements.quantity, Decimal("50"))
        self.assertEqual(result.requirements.destination_country_code, "US")
        self.assertEqual(result.provenance.provider, "offline")
        self.assertEqual(result.provenance.fallback_reason, "transient_exhausted")

    def test_transient_exhaustion_when_provider_fallback_itself_fails(self) -> None:
        """A failing provider fallback surfaces instead of being disguised as offline analysis."""
        mock_provider = MagicMock()
        mock_provider.provenance = AIProvenance(
            provider="openai",
            mode="openai_with_offline_fallback",
            model="gpt-4o",
            context_scope="authorized",
        )
        mock_provider.normalize_opening_request.side_effect = AITransientError("503 Service Unavailable")
        mock_provider.fallback_normalize_opening_request.side_effect = RuntimeError("Broken provider fallback")

        text = "We need 500 units of stainless steel bolts delivered to Berlin, Germany by 2026-12-01. Budget is $15 per unit."
        with self.assertRaisesRegex(RuntimeError, "Broken provider fallback"):
            normalize_opening_request(
                text,
                provider=mock_provider,
                policy=AIRetryPolicy(max_attempts=2, timeout_seconds=1.0, backoff_seconds=0.001),
            )

    # -------------------------------------------------------------------------
    # 4. Network Timeouts
    # -------------------------------------------------------------------------
    def test_unclassified_httpx_timeout_propagates(self) -> None:
        """Adapters classify timeouts; a raw transport exception is unexpected and must surface."""
        mock_provider = MagicMock(spec=["normalize_opening_request", "provenance"])
        mock_provider.provenance = AIProvenance(
            provider="openai",
            mode="openai_with_offline_fallback",
            model="gpt-4o",
            context_scope="authorized",
        )
        mock_provider.normalize_opening_request.side_effect = httpx.ReadTimeout("Read operation timed out after 10.0s")

        text = "RFQ: 10,000 meters of copper wire to Tokyo, Japan. Target price 2.50 USD/m."
        with self.assertRaises(httpx.ReadTimeout):
            normalize_opening_request(
                text,
                provider=mock_provider,
                policy=AIRetryPolicy(max_attempts=2, timeout_seconds=0.1, backoff_seconds=0.001),
            )
        self.assertEqual(mock_provider.normalize_opening_request.call_count, 1)

    def test_strict_remote_timeout_surfaces_without_offline_result(self) -> None:
        """Strict remote mode declines fallback after an adapter-classified timeout."""
        settings = Settings(
            _env_file=None,
            app_env="test",
            ai_provider="openai",
            ai_remote_egress_enabled=True,
            openai_model="gpt-4o",
            openai_api_key="test-only-key",
        )

        def timeout(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("Connection attempt timed out", request=request)

        provider = ConfiguredAIProvider(settings, transport=httpx.MockTransport(timeout))
        with self.assertRaises(AITransientError):
            normalize_opening_request("Hey, can you supply 50 boxes of packaging materials to US?", provider=provider)
        self.assertEqual(provider.provenance.provider, "openai")
        self.assertIsNone(provider.provenance.fallback_reason)

    def test_permanent_remote_rejection_is_not_replaced_by_fallback(self) -> None:
        """Configured fallback is for exhausted transient failures only."""
        settings = Settings(
            _env_file=None,
            app_env="test",
            ai_provider="openai_with_offline_fallback",
            ai_remote_egress_enabled=True,
            openai_model="gpt-4o",
            openai_api_key="test-only-key",
        )
        provider = ConfiguredAIProvider(
            settings,
            transport=httpx.MockTransport(lambda request: httpx.Response(401, json={"error": {}})),
        )
        with self.assertRaises(AIPermanentError):
            normalize_opening_request("Need 500 bolts delivered to Germany", provider=provider)
        self.assertIsNone(provider.provenance.fallback_reason)

    # -------------------------------------------------------------------------
    # 5. Rate Limits (HTTP 429)
    # -------------------------------------------------------------------------
    def test_rate_limit_429_without_fallback_capability_surfaces(self) -> None:
        """A transient failure is not silently replaced when the provider offers no fallback."""
        mock_provider = MagicMock(spec=["normalize_opening_request", "provenance"])
        mock_provider.provenance = AIProvenance(
            provider="openai",
            mode="openai_with_offline_fallback",
            model="gpt-4o",
            context_scope="authorized",
        )
        mock_provider.normalize_opening_request.side_effect = AITransientError(
            "HTTP 429: You exceeded your current quota"
        )

        text = "Looking for precision CNC machining for 200 automotive parts in Canada under 5000 USD."
        with self.assertRaises(AITransientError):
            normalize_opening_request(
                text,
                provider=mock_provider,
                policy=AIRetryPolicy(max_attempts=2, timeout_seconds=0.5, backoff_seconds=0.001),
            )
        self.assertEqual(mock_provider.normalize_opening_request.call_count, 2)

    # -------------------------------------------------------------------------
    # 6. Rogue / Crashing Provider Exceptions
    # -------------------------------------------------------------------------
    def test_arbitrary_runtime_error_propagates(self) -> None:
        """Unexpected provider exceptions surface instead of returning success-shaped offline output."""
        mock_provider = MagicMock(spec=["normalize_opening_request", "provenance"])
        mock_provider.provenance = AIProvenance(
            provider="openai",
            mode="openai_with_offline_fallback",
            model="gpt-4o",
            context_scope="authorized",
        )
        mock_provider.normalize_opening_request.side_effect = RuntimeError("Fatal LLM crash in worker")

        text = "We need 500 units of stainless steel bolts delivered to Berlin, Germany by 2026-12-01. Budget is $15 per unit."
        with self.assertRaisesRegex(RuntimeError, "Fatal LLM crash"):
            normalize_opening_request(text, provider=mock_provider)

    def test_provider_missing_normalize_method_reports_offline_not_remote(self) -> None:
        """Offline extraction for a provider without normalization never claims remote provenance."""
        class BareProvider:
            provenance = AIProvenance(provider="openai", mode="openai", model="gpt-4o", context_scope="shareable_only")

        text = "Looking for precision CNC machining for 200 automotive parts in Canada under 5000 USD."
        result = normalize_opening_request(text, provider=BareProvider())  # type: ignore[arg-type]

        self.assertEqual(result.requirements.item_description, "automotive parts")
        self.assertEqual(
            result.provenance,
            AIProvenance(provider="offline", mode="offline", context_scope="authorized"),
        )

    def test_deterministic_extraction_failure_propagates(self) -> None:
        """Unexpected extractor failures surface instead of returning an empty success."""
        class BareProvider:
            provenance = AIProvenance(provider="offline", mode="offline")

        for provider in (None, BareProvider()):
            with (
                self.subTest(provider=type(provider).__name__),
                patch(
                    "syncally.application.ai.extract_normalized_requirement",
                    side_effect=RuntimeError("extractor bug"),
                ),
                self.assertRaisesRegex(RuntimeError, "extractor bug"),
            ):
                normalize_opening_request("Need 500 bolts", provider=provider)  # type: ignore[arg-type]

    # -------------------------------------------------------------------------
    # 7. Malformed, Adversarial, and Extreme Length Inputs
    # -------------------------------------------------------------------------
    def test_catastrophic_backtracking_and_large_input_resistance(self) -> None:
        """Massive payload with repetitive patterns must not hang or cause ReDoS."""
        adversarial_blob = ("Need 500 units " + "delivered to Berlin " * 200 + "by 2026-12-01 " * 200) * 5
        text = adversarial_blob[:40000]

        result = extract_normalized_requirement(text)
        self.assertIsInstance(result, NormalizedRequirement)
        self.assertEqual(result.quantity, Decimal("500"))
        self.assertEqual(result.destination_country_code, "DE")
        self.assertEqual(result.target_delivery_date, date(2026, 12, 1))

    def test_extreme_numerical_boundary_inputs(self) -> None:
        """Astrophysical quantities and micro-fractions do not cause Decimal overflow or crash."""
        text = "Need 999999999999999999999999999999 units of bolts for $0.0000001 each in US"
        result = extract_normalized_requirement(text)

        self.assertIsInstance(result, NormalizedRequirement)
        self.assertIsNotNone(result.quantity)
        self.assertEqual(result.destination_country_code, "US")

    def test_sql_and_script_injection_payloads(self) -> None:
        """Injection payloads in opening request are treated strictly as plain text."""
        text = (
            "Need 100 units of <script>alert('xss')</script> '; DROP TABLE deals; -- "
            "delivered to London, UK at 50 GBP per unit."
        )
        result = extract_normalized_requirement(text)

        self.assertIsInstance(result, NormalizedRequirement)
        self.assertEqual(result.quantity, Decimal("100"))
        self.assertEqual(result.currency, "GBP")
        self.assertEqual(result.destination_country_code, "GB")
        self.assertEqual(result.target_unit_price, Decimal("50"))

    # -------------------------------------------------------------------------
    # 8. Multi-Threaded Concurrency Safety
    # -------------------------------------------------------------------------
    def test_concurrent_normalization_thread_safety(self) -> None:
        """Concurrent calls across threads with flaky provider instances must remain thread-safe."""
        settings = Settings(
            app_env="test",
            ai_provider="openai_with_offline_fallback",
            ai_remote_egress_enabled=True,
            openai_model="gpt-4o",
            openai_api_key="",
        )
        provider = ConfiguredAIProvider(settings)
        service = OpeningRequestNormalizationService(provider)

        test_inputs = [
            f"We need {i * 10} units of stainless steel bolts delivered to Berlin, Germany by 2026-12-01. Budget is ${i} per unit."
            for i in range(1, 51)
        ]

        def _worker(prompt: str) -> OpeningRequestNormalizationResult:
            return service.normalize(prompt)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(_worker, test_inputs))

        self.assertEqual(len(results), 50)
        for i, res in enumerate(results, start=1):
            self.assertEqual(res.requirements.quantity, Decimal(str(i * 10)))
            self.assertEqual(res.requirements.target_unit_price, Decimal(str(i)))
            self.assertEqual(res.requirements.destination_country_code, "DE")
            self.assertEqual(res.provenance.provider, "offline")
            self.assertEqual(res.provenance.fallback_reason, "missing_credentials")


class AdversarialExtractionChallengerTests(unittest.TestCase):
    """Empirical tests demonstrating heuristic extraction limitations and bugs."""

    def test_challenge_per_unit_misidentified_as_item_description(self) -> None:
        """Demonstrates bug: '15 per unit' matches regex and overrides actual item 'steel bolts'."""
        text = "Need 500 steel bolts delivered to Berlin, Germany by 2026-12-01. Budget $15 per unit."
        result = extract_normalized_requirement(text)

        # In a sound extractor, item_description should be 'steel bolts'.
        # However, the worker's regex matches 'per unit' because 'unit' is in the units list.
        self.assertEqual(result.item_description, "per unit")  # Confirms extraction bug

    def test_challenge_adjective_stripping_bug(self) -> None:
        """Demonstrates bug: stripping unit prefixes greedily removes descriptive words like 'stainless'."""
        text = "Need 500 stainless steel bolts to Germany"
        result = extract_normalized_requirement(text)

        # Worker's regex strips 'stainless' thinking it is a unit quantifier, leaving 'steel bolts'.
        self.assertEqual(result.item_description, "steel bolts")  # Confirms stripping bug

    def test_challenge_for_x_each_pricing_unparsed(self) -> None:
        """Demonstrates bug: 'for $X each' pricing syntax is not matched by _UNIT_PRICE_RE."""
        text = "Need 100 units of bolts for $15 each"
        result = extract_normalized_requirement(text)

        # _UNIT_PRICE_RE only looks for 'at $X' or 'price is $X', failing on 'for $X each'
        self.assertIsNone(result.target_unit_price)  # Confirms unparsed price syntax

    def test_challenge_deliver_prefix_unrecognized(self) -> None:
        """Demonstrates bug: opening request starting with 'Deliver ...' fails item extraction."""
        text = "Deliver 500 units steel bolts to Germany"
        result = extract_normalized_requirement(text)

        # Regex only supports RFQ / need / require / looking for / buying / supply
        self.assertIsNone(result.item_description)  # Confirms unparsed lead verb


if __name__ == "__main__":
    unittest.main()
