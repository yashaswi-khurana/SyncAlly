"""Explicit per-invocation egress and fallback policy behind the existing port."""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

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
from syncally.domain.ai.contracts import ExtractedFact, FactField, NormalizedRequirement, ProposedTerms
from syncally.domain.conversations import Message, MessageSourceType, Visibility
from syncally.infrastructure.ai.demo import DemoAISuggestionProvider
from syncally.infrastructure.ai.gemini import GeminiGenerateContent
from syncally.infrastructure.ai.openai import OpenAIChatCompletions, transmitted_context


class ConfiguredAIProvider:
    def __init__(self, config: Settings, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._offline = DemoAISuggestionProvider()
        self._config = config
        mode = config.ai_provider
        self.provenance = AIProvenance(provider="offline", mode=mode, context_scope="authorized")
        self._remote: OpenAIChatCompletions | GeminiGenerateContent | None = None
        if mode == "offline":
            if config.app_env.lower() not in {"development", "test"}:
                raise AIConfigurationError("AI suggestions are not configured")
            return
        is_gemini = mode.startswith("gemini")
        model = config.gemini_model if is_gemini else config.openai_model
        api_key = config.google_api_key if is_gemini else config.openai_api_key
        if not config.ai_remote_egress_enabled or not model.strip():
            raise AIConfigurationError("AI suggestions are not configured")
        if not api_key.get_secret_value().strip():
            if not mode.endswith("_with_offline_fallback"):
                raise AIConfigurationError("AI suggestions are not configured")
            self.provenance = replace(self.provenance, fallback_reason="missing_credentials")
            return
        adapter = GeminiGenerateContent if is_gemini else OpenAIChatCompletions
        self._remote = adapter(api_key=api_key, model=model.strip(), transport=transport)
        self.provenance = replace(
            self.provenance,
            provider="gemini" if is_gemini else "openai",
            model=self._remote.model,
        )

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
        if not self._config.ai_provider.endswith("_with_offline_fallback"):
            raise AITransientError("AI provider is temporarily unavailable") from None
        self.provenance = replace(self.provenance, provider="offline", model=None, fallback_reason="transient_exhausted")

    def fallback_facts(self, request: FactExtractionRequest, *, timeout_seconds: float) -> tuple[ExtractedFact, ...]:
        self._fallback()
        return self._offline.extract_facts(request, timeout_seconds=timeout_seconds)

    def fallback_proposal(self, request: ProposalDraftRequest, *, timeout_seconds: float) -> ProposedTerms:
        self._fallback()
        return self._offline.draft_proposal(request, timeout_seconds=timeout_seconds)

    def normalize_opening_request(
        self, text: str, *, timeout_seconds: float = 25.0
    ) -> NormalizedRequirement:
        try:
            baseline = self._offline.normalize_opening_request(text)
            if self._remote is None:
                return baseline

            # This ephemeral context contains only the text the user chose to analyze.
            message = Message(
                id=uuid4(), conversation_id=uuid4(), author_user_id=uuid4(),
                author_agent_id=None, body=text, visibility=Visibility.SHAREABLE,
                source_type=MessageSourceType.USER, created_at=datetime.now(UTC),
            )
            context = AiContext(deal_id=uuid4(), organization_id=uuid4(), messages=(message,), constraints=())
            facts = self._remote.extract_facts(FactExtractionRequest(context=context), timeout_seconds=timeout_seconds)
            # The adapter verifies the exact source quote and value. Only fill gaps;
            # ambiguous model suggestions must not select a seller on their own.
            fields = {
                FactField.ITEM_DESCRIPTION: "item_description",
                FactField.QUANTITY: "quantity",
                FactField.UNIT: "unit",
                FactField.UNIT_PRICE: "target_unit_price",
                FactField.DELIVERY_DESTINATION: "destination_name",
                FactField.DELIVERY_DATE: "target_delivery_date",
            }
            values = baseline.model_dump()
            for field, name in fields.items():
                candidates = {(fact.value, fact.currency_or_unit) for fact in facts if fact.field == field}
                if values[name] is not None or len(candidates) != 1:
                    continue
                value, currency = candidates.pop()
                if field is FactField.UNIT_PRICE:
                    # Never combine an AI price with a different offline currency.
                    if values["currency"] is not None and values["currency"] != currency:
                        continue
                    values["currency"] = currency
                values[name] = value
            self.provenance = replace(self.provenance, context_scope="shareable_only")
            return NormalizedRequirement.model_validate(values)
        finally:
            self._record_model()

    def fallback_normalize_opening_request(
        self, text: str, *, timeout_seconds: float = 10.0
    ) -> NormalizedRequirement:
        del timeout_seconds
        self._fallback()
        return self._offline.normalize_opening_request(text)
