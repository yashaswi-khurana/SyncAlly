import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from pydantic import SecretStr

from syncally.application.ai import AIPermanentError, AITransientError, FactExtractionRequest
from syncally.infrastructure.ai.gemini import GeminiGenerateContent
from syncally.operations import SafeOperationalFormatter


class GeminiDiagnosticsTests(unittest.TestCase):
    def test_thinking_parts_are_not_parsed_as_answer_json(self):
        payload = {"schema_version": 1, "facts": []}
        response = {
            "modelVersion": "model",
            "candidates": [{
                "index": 0, "finishReason": "STOP",
                "content": {"role": "model", "parts": [
                    {"text": "Private reasoning is not JSON", "thought": True},
                    {"text": json.dumps(payload)},
                ]},
            }],
        }
        provider = GeminiGenerateContent(
            api_key=SecretStr("key"), model="gemini-test",
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response)),
        )
        self.assertEqual(asyncio.run(provider._http(b"{}", 1)), payload)
        response["candidates"][0]["index"] = False
        with self.assertRaises(ValueError):
            asyncio.run(provider._http(b"{}", 1))

    def test_invalid_fact_shape_logs_only_validation_stage(self):
        provider = GeminiGenerateContent(api_key=SecretStr("private-key"), model="gemini-3.5-flash")
        context = SimpleNamespace()
        with patch("syncally.infrastructure.ai.openai.transmitted_context", return_value=context), \
             patch.object(provider, "_call", return_value={"private": "content"}), \
             self.assertLogs("syncally.infrastructure.ai.openai", level="INFO") as captured:
            with self.assertRaises(AIPermanentError):
                provider.extract_facts(FactExtractionRequest(context=context), timeout_seconds=1)
        event = json.loads(SafeOperationalFormatter().format(captured.records[0]))
        self.assertEqual(event["error_code"], "AI_FACT_SHAPE")
        self.assertNotIn("private", json.dumps(event))

    def test_token_limit_is_logged_without_response_content(self):
        response = {"modelVersion": "model", "candidates": [{"index": 0, "finishReason": "MAX_TOKENS"}]}
        provider = GeminiGenerateContent(
            api_key=SecretStr("key"), model="gemini-3.5-flash",
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response)),
        )
        with self.assertLogs("syncally.infrastructure.ai.gemini", level="INFO") as captured:
            with self.assertRaises(ValueError):
                asyncio.run(provider._http(b"{}", 1))
        event = json.loads(SafeOperationalFormatter().format(captured.records[0]))
        self.assertEqual(event["error_code"], "GEMINI_MAX_TOKENS")

    def test_request_uses_json_mode_and_includes_schema(self):
        provider = GeminiGenerateContent(api_key=SecretStr("key"), model="gemini-3.5-flash")
        context = SimpleNamespace(messages=(), constraints=())
        schema = {"type": "object", "properties": {"facts": {"type": "array"}}}
        with patch.object(provider, "_http", new_callable=AsyncMock, return_value={}) as call:
            provider._call(context, "facts", schema, 1)
        body = json.loads(call.call_args.args[0])
        self.assertEqual(body["generationConfig"]["responseMimeType"], "application/json")
        self.assertEqual(body["generationConfig"]["thinkingConfig"], {"thinkingLevel": "low"})
        self.assertEqual(body["generationConfig"]["maxOutputTokens"], 8192)
        self.assertEqual(body["generationConfig"]["responseJsonSchema"], schema)
        self.assertIn("untrusted data", body["systemInstruction"]["parts"][0]["text"])

    def test_rate_limit_logs_only_safe_status(self):
        provider = GeminiGenerateContent(
            api_key=SecretStr("private-key"), model="gemini-3.8-flash",
            transport=httpx.MockTransport(lambda _: httpx.Response(429, text="private response")),
        )
        with self.assertLogs("syncally.infrastructure.ai.gemini", level="INFO") as captured:
            with self.assertRaises(AITransientError):
                asyncio.run(provider._http(b"{}", 1))
        event = json.loads(SafeOperationalFormatter().format(captured.records[0]))
        self.assertEqual(event["event"], "ai.provider_failure")
        self.assertEqual(event["http_status"], 429)
        self.assertNotIn("private", json.dumps(event))

    def test_bad_request_logs_safe_google_validation_diagnostics(self):
        response = {
            "error": {
                "code": 400,
                "status": "INVALID_ARGUMENT",
                "message": (
                    "Unknown name \"additionalProperties\" at "
                    "'generation_config.response_json_schema.properties': Cannot find field."
                ),
                "details": [{"private": "message content"}],
            },
        }
        provider = GeminiGenerateContent(
            api_key=SecretStr("private-key"), model="gemini-3.1-flash-lite",
            transport=httpx.MockTransport(lambda _: httpx.Response(400, json=response)),
        )
        with self.assertLogs("syncally.infrastructure.ai.gemini", level="INFO") as captured:
            with self.assertRaisesRegex(AIPermanentError, "Gemini API rejected the request"):
                asyncio.run(provider._http(b"{}", 1))

        event = json.loads(SafeOperationalFormatter().format(captured.records[0]))
        self.assertEqual(event["error_code"], "GEMINI_BAD_REQUEST")
        self.assertEqual(event["provider_error_status"], "INVALID_ARGUMENT")
        self.assertEqual(event["provider_error_field"], "additionalProperties")
        self.assertNotIn("private", json.dumps(event))
        self.assertNotIn("Cannot find field", json.dumps(event))
