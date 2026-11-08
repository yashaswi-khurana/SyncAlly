import asyncio
import json
import logging
import unittest

import httpx
from pydantic import SecretStr

from syncally.application.ai import AITransientError
from syncally.infrastructure.ai.gemini import GeminiGenerateContent
from syncally.operations import SafeOperationalFormatter


class GeminiDiagnosticsTests(unittest.TestCase):
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
