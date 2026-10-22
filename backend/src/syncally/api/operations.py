"""Request correlation around the complete ASGI stack, including error responses."""

from __future__ import annotations

import logging
from time import monotonic
from uuid import uuid4

from fastapi import FastAPI
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from syncally.operations import Operation, correlation_id, log_operation

logger = logging.getLogger(__name__)


class OperationalRequestMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid4()
        token = correlation_id.set(request_id)
        started = monotonic()
        response_status = 500

        async def send_correlated(message: Message) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
                message = dict(message)
                message["headers"] = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() != b"x-correlation-id"
                ] + [(b"x-correlation-id", str(request_id).encode("ascii"))]
            await send(message)

        try:
            await self.app(scope, receive, send_correlated)
        finally:
            fields: dict[str, object] = {}
            if response_status < 400:
                fields["deal_id"] = scope.get("path_params", {}).get("deal_id")
            try:
                log_operation(
                    logger,
                    Operation.HTTP_COMPLETED,
                    correlation_id=request_id,
                    http_status=response_status,
                    duration_ms=int((monotonic() - started) * 1000),
                    **fields,
                )
            finally:
                correlation_id.reset(token)


class OperationalFastAPI(FastAPI):
    def build_middleware_stack(self) -> ASGIApp:
        return OperationalRequestMiddleware(super().build_middleware_stack())
