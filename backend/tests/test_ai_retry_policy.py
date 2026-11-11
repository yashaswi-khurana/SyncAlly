"""Checks provider-specific latency bounds for interactive AI requests."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from syncally.application.ai import AIProvenance, AIRetryPolicy, _retry_policy_for_provider


class AIRetryPolicyTests(unittest.TestCase):
    def test_gemini_uses_one_longer_call(self) -> None:
        provider = SimpleNamespace(provenance=AIProvenance(provider="gemini"))

        policy = _retry_policy_for_provider(provider, None)

        self.assertEqual(policy.max_attempts, 1)
        self.assertEqual(policy.timeout_seconds, 45.0)

    def test_other_providers_keep_the_bounded_retry_default(self) -> None:
        provider = SimpleNamespace(provenance=AIProvenance(provider="openai"))

        policy = _retry_policy_for_provider(provider, None)

        self.assertEqual(policy, AIRetryPolicy())

    def test_explicit_policy_is_preserved(self) -> None:
        provider = SimpleNamespace(provenance=AIProvenance(provider="gemini"))
        explicit = AIRetryPolicy(max_attempts=3, timeout_seconds=7.0)

        self.assertIs(_retry_policy_for_provider(provider, explicit), explicit)


if __name__ == "__main__":
    unittest.main()
