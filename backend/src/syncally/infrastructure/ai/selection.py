"""Explicit per-invocation egress and fallback policy behind the existing port."""

from dataclasses import replace

import httpx

from syncally.application.ai import (
    AIConfigurationError,
    AIProvenance,
    AITransientError,
    FactExtractionRequest,
    ProposalDraftRequest,
)
from syncally.application.conversations import AiContext
from syncally.config import Settings
from syncally.domain.ai.contracts import ExtractedFact, ProposedTerms
from syncally.domain.conversations import Visibility
from syncally.infrastructure.ai.demo import DemoAISuggestionProvider
from syncally.infrastructure.ai.openai import OpenAIChatCompletions, transmitted_context


class ConfiguredAIProvider:
    def __init__(self, config: Settings, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._offline = DemoAISuggestionProvider()
        self._config = config
        mode = config.ai_provider
        self.provenance = AIProvenance(provider="offline", mode=mode, context_scope="authorized")
        self._remote: OpenAIChatCompletions | None = None
        if mode == "offline":
            if config.app_env.lower() not in {"development", "test"}:
                raise AIConfigurationError("AI suggestions are not configured")
            return
        if not config.ai_remote_egress_enabled or not config.openai_model.strip():
            raise AIConfigurationError("AI suggestions are not configured")
        if not config.openai_api_key.get_secret_value().strip():
            if mode != "openai_with_offline_fallback":
                raise AIConfigurationError("AI suggestions are not configured")
            self.provenance = replace(self.provenance, fallback_reason="missing_credentials")
            return
        self._remote = OpenAIChatCompletions(
            api_key=config.openai_api_key, model=config.openai_model.strip(), transport=transport,
        )
        self.provenance = replace(self.provenance, provider="openai", model=self._remote.model)

    def prepare_context(self, context: AiContext) -> AiContext:
        if self._remote is None:
            return context
        private_allowed = (
            self._config.ai_remote_allow_private
            and context.organization_id in self._config.ai_remote_private_organization_ids
        )
        self.provenance = replace(
            self.provenance,
            context_scope="authorized_private" if private_allowed else "shareable_only",
        )
        filtered = replace(
            context,
            messages=tuple(message for message in context.messages if private_allowed or message.visibility is Visibility.SHAREABLE),
            constraints=tuple(term for term in context.constraints if private_allowed or term.visibility is Visibility.SHAREABLE),
        )
        return transmitted_context(filtered)

    def extract_facts(self, request: FactExtractionRequest, *, timeout_seconds: float) -> tuple[ExtractedFact, ...]:
        try:
            return (self._remote or self._offline).extract_facts(request, timeout_seconds=timeout_seconds)
        finally:
            self._record_model()

    def draft_proposal(self, request: ProposalDraftRequest, *, timeout_seconds: float) -> ProposedTerms:
        try:
            return (self._remote or self._offline).draft_proposal(request, timeout_seconds=timeout_seconds)
        finally:
            self._record_model()

    def _record_model(self) -> None:
        if self._remote is not None and self._remote.response_model is not None:
            self.provenance = replace(self.provenance, model=self._remote.response_model)

    def _fallback(self) -> None:
        if self._config.ai_provider != "openai_with_offline_fallback":
            raise AITransientError("AI provider is temporarily unavailable") from None
        self.provenance = replace(self.provenance, provider="offline", model=None, fallback_reason="transient_exhausted")

    def fallback_facts(self, request: FactExtractionRequest, *, timeout_seconds: float) -> tuple[ExtractedFact, ...]:
        self._fallback()
        return self._offline.extract_facts(request, timeout_seconds=timeout_seconds)

    def fallback_proposal(self, request: ProposalDraftRequest, *, timeout_seconds: float) -> ProposedTerms:
        self._fallback()
        return self._offline.draft_proposal(request, timeout_seconds=timeout_seconds)