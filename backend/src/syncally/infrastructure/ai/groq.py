"""Groq Chat Completions provider.

Implements the same OpenAI‑compatible HTTP wire format as the existing
OpenAIChatCompletions and NvidiaChatCompletions adapters. The Groq API
expects the request payload to be posted to
`https://api.groq.com/openai/v1/chat/completions` with an `Authorization`
header bearing a Groq API key.

The implementation mirrors `OpenAIChatCompletions` but overrides the
endpoint and keeps the same validation, timeout handling and schema usage.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import replace
from typing import Any

import httpx
from pydantic import SecretStr

from syncally.application.ai import (
    AIPermanentError,
    AITransientError,
    FactExtractionRequest,
    ProposalDraftRequest,
    parse_extracted_facts,
    parse_proposed_terms,
)
from syncally.application.conversations import AiContext
from syncally.domain.ai.contracts import (
    AI_SCHEMA_VERSION,
    AIContractError,
    ExtractedFact,
    FactField,
    ProposedTerms,
    scope_extracted_facts,
)
from syncally.domain.conversations import ConstraintStatus
from syncally.operations import Operation, log_operation

ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
MAX_BYTES = 128 * 1024
MAX_FACTS = 100
MAX_OUTPUT_TOKENS = 4096
logger = logging.getLogger(__name__)

# The schema definitions are identical to those in `openai.py` – we import them
# to avoid duplication and keep a single source of truth.
from syncally.infrastructure.ai.openai import (
    FACTS_SCHEMA,
    PROPOSAL_SCHEMA,
    _object,
    _STRING,
    _NULLABLE_STRING,
    _VERSION,
    SOURCE_SCHEMA,
    FACT_SCHEMA,
    FACT_ARRAY_SCHEMA,
    _json,
    _shape,
)

class GroqChatCompletions:
    """Adapter for Groq's OpenAI‑compatible chat completion endpoint.

    Parameters
    ----------
    api_key: SecretStr
        Groq API secret.
    model: str
        The model name to use (e.g. ``"groq/gpt-oss-20b"``).
    transport: httpx.AsyncBaseTransport | None, optional
        Allows injection of a custom transport for testing.
    """

    def __init__(self, *, api_key: SecretStr, model: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._api_key = api_key
        self.model = model
        self._transport = transport
        self.response_model: str | None = None

    # ---------------------------------------------------------------------
    # Helper methods – these are copies of the OpenAI implementation with the
    # singular change of using the Groq endpoint.
    # ---------------------------------------------------------------------
    async def _http(self, raw: bytes, timeout: float) -> Any:
        async with httpx.AsyncClient(
            transport=self._transport,
            verify=True,
            trust_env=False,
            headers={"Authorization": f"Bearer {self._api_key.get_secret_value()}"},
        ) as client:
            response = await client.post(ENDPOINT, content=raw, timeout=timeout)
            if response.status_code == 401:
                raise AIPermanentError("AI provider misconfigured: bad API key")
            if response.status_code == 429:
                raise AITransientError("AI provider is throttled")
            if response.status_code >= 500:
                raise AITransientError("AI provider is temporarily unavailable")
            if response.is_error:
                raise AIPermanentError(f"AI provider returned error: {response.status_code} {response.text}")
            return response.json()

    def _call(self, context: AiContext, operation: Operation, schema: Any, timeout: float) -> Any:
        instruction = (
            "You are a strict JSON extractor. Return ONLY a JSON object that conforms to the supplied schema."
            " Do NOT add any explanatory text, comments or extra fields."
        )
        user_payload = {
            "facts": [
                {"message_id": str(message.id), "author": "user", "text": message.body}
                for message in context.messages
            ],
            "constraints": [
                {"field": term.field.value, "value": term.value, "currency_or_unit": term.currency_or_unit}
                for term in context.constraints
                if term.field in FactField
            ],
        }
        raw = json.dumps(
            {
                "model": self.model,
                "store": False,
                "max_completion_tokens": MAX_OUTPUT_TOKENS,
                "messages": [
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                ],
                "response_format": {"type": "json_schema", "json_schema": {"name": operation, "strict": True, "schema": schema}},
            },
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        if len(raw) > MAX_BYTES:
            raise AIPermanentError("AI request exceeds the size limit")
        try:
            return asyncio.run(asyncio.wait_for(self._http(raw, timeout), timeout=timeout))
        except (TimeoutError, httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError):
            raise AITransientError("AI provider is temporarily unavailable") from None
        except (ValueError, TypeError, KeyError, AttributeError, UnicodeError, RecursionError, httpx.HTTPError):
            raise AIPermanentError("AI provider returned invalid output") from None

    # ---------------------------------------------------------------------
    # Public API – matches the abstract contract used by `ConfiguredAIProvider`.
    # ---------------------------------------------------------------------
    def extract_facts(self, request: FactExtractionRequest, *, timeout_seconds: float) -> list[ExtractedFact]:
        raw = self._call(request.context, "facts", FACTS_SCHEMA, timeout_seconds)
        try:
            # Groq returns a parsed JSON dict directly, no need to decode
            payload = raw
            shaped = _shape(payload, {"schema_version", "facts"})
            return parse_extracted_facts(scope_extracted_facts(shaped["facts"]))
        except Exception as exc:
            raise AIContractError(str(exc)) from exc

    def draft_proposal(self, request: ProposalDraftRequest, *, timeout_seconds: float) -> ProposedTerms:
        raw = self._call(request.context, "proposal", PROPOSAL_SCHEMA, timeout_seconds)
        payload = raw
        shaped = _shape(payload, {"schema_version", "proposal", "insufficient_context", "citations"})
        if shaped["insufficient_context"]:
            raise AIPermanentError("AI provider does not have enough grounded context for a proposal")
        proposal = shaped["proposal"]
        if proposal is None:
            raise AIContractError("Missing proposal object")
        try:
            terms = parse_proposed_terms(_shape(proposal, set(TERMS_SCHEMA["properties"].keys())))
            citations = parse_extracted_facts(scope_extracted_facts(shaped["citations"]))
            return ProposedTerms(terms=terms, citations=citations)
        except Exception as exc:
            raise AIContractError(str(exc)) from exc
