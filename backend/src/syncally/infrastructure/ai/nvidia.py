"""One-call, bounded NVIDIA Chat Completions adapter using OpenAI-compatible wire format."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from pydantic import SecretStr

from syncally.application.ai import (
    AIPermanentError,
    AITransientError,
)
from syncally.infrastructure.ai.openai import (
    MAX_BYTES,
    OpenAIChatCompletions,
    _json,
)
from syncally.operations import Operation, log_operation

NVIDIA_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"
logger = logging.getLogger(__name__)


class NvidiaChatCompletions(OpenAIChatCompletions):
    """NVIDIA NIM Chat Completions adapter reusing the shared contracts and validators."""

    def __init__(
        self,
        *,
        api_key: SecretStr,
        model: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not model or not model.strip():
            raise ValueError("Model must be specified for NvidiaChatCompletions")
        if len(model) > 200:
            raise ValueError("Invalid NVIDIA model name length")
        super().__init__(api_key=api_key, model=model.strip(), transport=transport)

    async def _http(self, raw: bytes, timeout: float) -> Any:
        async with httpx.AsyncClient(
            transport=self._transport,
            verify=True,
            trust_env=False,
            follow_redirects=False,
            timeout=httpx.Timeout(timeout),
        ) as client:
            async with client.stream(
                "POST",
                NVIDIA_ENDPOINT,
                content=raw,
                headers={
                    "Authorization": f"Bearer {self._api_key.get_secret_value()}",
                    "Content-Type": "application/json",
                    "Accept-Encoding": "identity",
                },
            ) as response:
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    raise AIPermanentError("AI response encoding is unsupported")
                length = response.headers.get("content-length")
                if length is not None and (not length.isdecimal() or int(length) > MAX_BYTES):
                    raise AIPermanentError("AI response exceeds the size limit")
                body = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=4096):
                    if len(body) + len(chunk) > MAX_BYTES:
                        raise AIPermanentError("AI response exceeds the size limit")
                    body.extend(chunk)

                if response.status_code == 429 or 500 <= response.status_code <= 599:
                    log_operation(
                        logger,
                        Operation.AI_PROVIDER_FAILURE,
                        failure_kind="TRANSIENT",
                        http_status=response.status_code,
                    )
                    raise AITransientError("AI provider is temporarily unavailable")
                if response.status_code in {401, 403}:
                    log_operation(
                        logger,
                        Operation.AI_PROVIDER_FAILURE,
                        failure_kind="PERMANENT",
                        http_status=response.status_code,
                    )
                    raise AIPermanentError(
                        f"NVIDIA API authentication/authorization failed (HTTP {response.status_code})"
                    )
                if response.status_code != 200:
                    raise AIPermanentError(
                        f"NVIDIA API rejected the request (HTTP {response.status_code})"
                    )

                envelope = _json(body)
                if not isinstance(envelope, dict) or envelope.get("object") != "chat.completion":
                    raise ValueError("Invalid completion envelope")
                model = envelope.get("model")
                if not isinstance(model, str) or not model.strip() or len(model) > 200:
                    raise ValueError("Invalid completion model")
                choices = envelope.get("choices")
                if not isinstance(choices, list) or len(choices) != 1:
                    raise ValueError("Invalid choices")
                choice = choices[0]
                message = choice.get("message")
                if not isinstance(message, dict):
                    raise ValueError("Invalid choice message")
                if (
                    choice.get("finish_reason") != "stop"
                    or type(choice.get("index")) is not int
                    or choice["index"] != 0
                ):
                    raise ValueError("Incomplete completion")
                if (
                    message.get("role") != "assistant"
                    or message.get("refusal") is not None
                    or message.get("tool_calls")
                    or message.get("function_call")
                ):
                    raise ValueError("Refused or unsupported completion")

                content = message.get("content")
                if not isinstance(content, str):
                    raise ValueError("Invalid content")

                self.response_model = model
                return _json(content)
