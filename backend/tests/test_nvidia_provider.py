"""Unit tests for NvidiaChatCompletions adapter and provider selection."""

import json
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx
from pydantic import SecretStr

from syncally.application.ai import (
    AIProviderAccessError,
    AITransientError,
    FactExtractionRequest,
)
from syncally.application.conversations import AiContext
from syncally.config import Settings
from syncally.domain.ai.contracts import (
    AI_SCHEMA_VERSION,
    FactField,
)
from syncally.domain.conversations import (
    Message,
    MessageSourceType,
    Visibility,
)
from syncally.infrastructure.ai.nvidia import NvidiaChatCompletions
from syncally.infrastructure.ai.selection import ConfiguredAIProvider


class NvidiaProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.org_id = uuid4()
        self.msg_id = uuid4()
        self.message = Message(
            id=self.msg_id,
            conversation_id=uuid4(),
            author_user_id=uuid4(),
            author_agent_id=None,
            body="We offer 100 units at USD 25 per unit delivered to Hamburg by 2026-12-01.",
            visibility=Visibility.SHAREABLE,
            source_type=MessageSourceType.USER,
            created_at=None,
        )
        self.context = AiContext(
            deal_id=uuid4(),
            organization_id=self.org_id,
            messages=(self.message,),
            constraints=(),
        )

    def test_happy_path_fact_extraction(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url, "https://integrate.api.nvidia.com/v1/chat/completions")
            self.assertEqual(request.headers["authorization"], "Bearer test-nvidia-key")
            request_payload = json.loads(request.content)
            self.assertFalse(request_payload["stream"])
            self.assertEqual(request_payload["max_tokens"], 8192)
            self.assertNotIn("max_completion_tokens", request_payload)
            response_body = {
                "id": "chatcmpl-123",
                "object": "chat.completion",
                "model": "nvidia/nemotron-3.5-super-vl-120b-a12b",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": json.dumps({
                                "schema_version": AI_SCHEMA_VERSION,
                                "facts": [
                                    {
                                        "schema_version": AI_SCHEMA_VERSION,
                                        "field": FactField.QUANTITY.value,
                                        "value": "100",
                                        "currency_or_unit": "units",
                                        "source": {
                                            "schema_version": AI_SCHEMA_VERSION,
                                            "message_id": str(self.msg_id),
                                            "quote": "100 units",
                                            "unknown_reason": None,
                                        },
                                    }
                                ],
                            }),
                        },
                    }
                ],
            }
            return httpx.Response(200, json=response_body, headers={"content-encoding": "identity"})

        transport = httpx.MockTransport(handler)
        adapter = NvidiaChatCompletions(
            api_key=SecretStr("test-nvidia-key"),
            model="nvidia/nemotron-3.5-super-vl-120b-a12b",
            transport=transport,
        )
        req = FactExtractionRequest(context=self.context)
        facts = adapter.extract_facts(req, timeout_seconds=5.0)
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0].field, FactField.QUANTITY)
        self.assertEqual(facts[0].value, "100")
        self.assertEqual(adapter.response_model, "nvidia/nemotron-3.5-super-vl-120b-a12b")

    def test_transient_error_on_503(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, content=b'{"error": "Unavailable"}', headers={"content-encoding": "identity"})

        transport = httpx.MockTransport(handler)
        adapter = NvidiaChatCompletions(
            api_key=SecretStr("test-nvidia-key"),
            model="nvidia/nemotron-3.5-super-vl-120b-a12b",
            transport=transport,
        )
        req = FactExtractionRequest(context=self.context)
        with self.assertRaises(AITransientError):
            adapter.extract_facts(req, timeout_seconds=5.0)

    def test_transient_error_on_429(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, content=b'{"error": "Rate limit exceeded"}', headers={"content-encoding": "identity"})

        transport = httpx.MockTransport(handler)
        adapter = NvidiaChatCompletions(
            api_key=SecretStr("test-nvidia-key"),
            model="nvidia/nemotron-3.5-super-vl-120b-a12b",
            transport=transport,
        )
        req = FactExtractionRequest(context=self.context)
        with self.assertRaises(AITransientError):
            adapter.extract_facts(req, timeout_seconds=5.0)

    def test_access_error_on_401_or_403(self) -> None:
        for status_code in (401, 403):
            with self.subTest(status_code=status_code):
                async def handler(request: httpx.Request) -> httpx.Response:
                    return httpx.Response(
                        status_code,
                        content=b'{"error": "Unauthorized"}',
                        headers={"content-encoding": "identity"},
                    )

                adapter = NvidiaChatCompletions(
                    api_key=SecretStr("invalid-key"),
                    model="nvidia/nemotron-3.5-super-vl-120b-a12b",
                    transport=httpx.MockTransport(handler),
                )
                req = FactExtractionRequest(context=self.context)
                with self.assertRaises(AIProviderAccessError):
                    adapter.extract_facts(req, timeout_seconds=5.0)

    def test_configured_ai_provider_wiring(self) -> None:
        config = Settings(
            app_env="development",
            ai_provider="nvidia",
            ai_remote_egress_enabled=True,
            nvidia_api_key=SecretStr("test-key"),
            nvidia_model="nvidia/nemotron-3.5-super-vl-120b-a12b",
        )
        provider = ConfiguredAIProvider(config)
        self.assertEqual(provider.provenance.provider, "nvidia")
        self.assertEqual(provider.provenance.mode, "nvidia")
        self.assertEqual(provider.provenance.model, "nvidia/nemotron-3.5-super-vl-120b-a12b")

    def test_sourcing_interpretation_uses_extended_provider_deadline(self) -> None:
        config = Settings(
            app_env="development",
            ai_provider="nvidia",
            ai_remote_egress_enabled=True,
            nvidia_api_key=SecretStr("test-key"),
            nvidia_model="nvidia/nemotron-3.5-super-vl-120b-a12b",
        )
        provider = ConfiguredAIProvider(config)
        with patch(
            "syncally.infrastructure.ai.selection.interpret_sourcing_requirements",
            return_value=(object(), []),
        ) as interpret:
            provider.interpret_sourcing_requirements("test sourcing prompt")

        self.assertEqual(interpret.call_args.kwargs["timeout_seconds"], 60.0)

    def test_configured_ai_provider_missing_credentials_fallback(self) -> None:
        config = Settings(
            app_env="development",
            ai_provider="nvidia_with_offline_fallback",
            ai_remote_egress_enabled=True,
            nvidia_api_key=SecretStr(""),
            nvidia_model="nvidia/nemotron-3.5-super-vl-120b-a12b",
        )
        provider = ConfiguredAIProvider(config)
        self.assertEqual(provider.provenance.provider, "offline")
        self.assertEqual(provider.provenance.mode, "nvidia_with_offline_fallback")
        self.assertEqual(provider.provenance.fallback_reason, "missing_credentials")


if __name__ == "__main__":
    unittest.main()
