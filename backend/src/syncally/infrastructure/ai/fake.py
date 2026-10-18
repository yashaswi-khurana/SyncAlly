"""Deterministic, offline AI provider double.

This adapter implements the application AI port without any SDK, network call,
or credential lookup, so tests that use it need no API key and cannot flake on
network conditions. Tests script typed S4-01 suggestions to exercise the
orchestration, retry, grounding, and privacy behavior around a provider.
"""

from __future__ import annotations

from collections.abc import Sequence

from syncally.application.ai import (
    AIPermanentError,
    AIProviderError,
    FactExtractionRequest,
    ProposalDraftRequest,
)
from syncally.domain.ai.contracts import ExtractedFact, ProposedTerms


class DeterministicFakeAIProvider:
    """Return scripted suggestions with no credentials or network access.

    ``failures`` is an ordered list of provider error classes raised one per
    call before any suggestion is returned, which lets a test drive the bounded
    retry path. ``last_request`` and ``last_timeout_seconds`` record the most
    recent call so tests can assert what the application boundary passed in.
    """

    def __init__(
        self,
        *,
        facts: Sequence[ExtractedFact] = (),
        proposal: ProposedTerms | None = None,
        failures: Sequence[type[AIProviderError]] = (),
    ) -> None:
        self._facts = tuple(facts)
        self._proposal = proposal
        self._failures = list(failures)
        self.call_count = 0
        self.last_request: FactExtractionRequest | ProposalDraftRequest | None = None
        self.last_timeout_seconds: float | None = None

    def extract_facts(
        self, request: FactExtractionRequest, *, timeout_seconds: float
    ) -> tuple[ExtractedFact, ...]:
        self._begin_call(request, timeout_seconds)
        return self._facts

    def draft_proposal(
        self, request: ProposalDraftRequest, *, timeout_seconds: float
    ) -> ProposedTerms:
        self._begin_call(request, timeout_seconds)
        if self._proposal is None:
            raise AIPermanentError("fake AI provider has no proposal configured")
        return self._proposal

    def _begin_call(
        self,
        request: FactExtractionRequest | ProposalDraftRequest,
        timeout_seconds: float,
    ) -> None:
        self.call_count += 1
        self.last_request = request
        self.last_timeout_seconds = timeout_seconds
        if self._failures:
            failure = self._failures.pop(0)
            raise failure("deterministic fake AI provider failure")
