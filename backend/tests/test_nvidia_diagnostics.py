"""Ensure NVIDIA failures are diagnosable without logging prompts or responses."""

import json
import unittest
from uuid import uuid4

import httpx
from pydantic import SecretStr

from syncally.application.ai import AIPermanentError, FactExtractionRequest
from syncally.application.conversations import AiContext
from syncally.domain.conversations import Message, MessageSourceType, Visibility
from syncally.infrastructure.ai.nvidia import NvidiaChatCompletions
from syncally.operations import SafeOperationalFormatter


class NvidiaDiagnosticsTests(unittest.TestCase):
    def setUp(self) -> None:
        message = Message(
            id=uuid4(),
            conversation_id=uuid4(),
            author_user_id=uuid4(),
            author_agent_id=None,
            body="private prompt text",
            visibility=Visibility.SHAREABLE,
            source_type=MessageSourceType.USER,
            created_at=None,
        )
        self.request = FactExtractionRequest(
            context=AiContext(
                deal_id=uuid4(), organization_id=uuid4(), messages=(message,), constraints=()
            )
        )

    def _provider(self, response: httpx.Response) -> NvidiaChatCompletions:
        return NvidiaChatCompletions(
            api_key=SecretStr("private-test-key"),
            model="nvidia/nemotron-test",
            transport=httpx.MockTransport(lambda _: response),
        )

    def test_non_success_status_logs_only_safe_status_and_code(self) -> None:
        provider = self._provider(httpx.Response(400, text="private provider response"))
        with self.assertLogs("syncally.infrastructure.ai.nvidia", level="INFO") as captured:
            with self.assertRaises(AIPermanentError):
                provider.extract_facts(self.request, timeout_seconds=1)

        event = json.loads(SafeOperationalFormatter().format(captured.records[0]))
        self.assertEqual(event["event"], "ai.provider_failure")
        self.assertEqual(event["error_code"], "NVIDIA_HTTP_REJECTED")
        self.assertEqual(event["http_status"], 400)
        self.assertNotIn("private", json.dumps(event))

    def test_invalid_completion_logs_validation_code_without_response(self) -> None:
        provider = self._provider(httpx.Response(200, json={
            "object": "chat.completion",
            "model": "nvidia/nemotron-test",
            "choices": [],
        }))
        with self.assertLogs("syncally.infrastructure.ai.nvidia", level="INFO") as captured:
            with self.assertRaises(AIPermanentError):
                provider.extract_facts(self.request, timeout_seconds=1)

        event = json.loads(SafeOperationalFormatter().format(captured.records[0]))
        self.assertEqual(event["event"], "ai.provider_failure")
        self.assertEqual(event["error_code"], "NVIDIA_INVALID_RESPONSE")
        self.assertNotIn("private", json.dumps(event))

    def test_http_rejection_carries_diagnostic_code(self) -> None:
        provider = self._provider(httpx.Response(400, text="private provider response"))
        with self.assertRaises(AIPermanentError) as raised:
            provider.extract_facts(self.request, timeout_seconds=1)

        self.assertEqual(raised.exception.diagnostic_code, "NVIDIA_HTTP_REJECTED")


if __name__ == "__main__":
    unittest.main()
