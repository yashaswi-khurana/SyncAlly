import asyncio
import json
import logging
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from pydantic import SecretStr

from syncally.application.ai import AITransientError
from syncally.infrastructure.ai.gemini import GeminiGenerateContent
from syncally.operations import SafeOperationalFormatter


class GeminiDiagnosticsTests(unittest.TestCase):
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
        self.assertNotIn("responseJsonSchema", body["generationConfig"])
        self.assertIn(json.dumps(schema), body["contents"][0]["parts"][0]["text"])

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
