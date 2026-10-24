"""FastAPI application entry point."""

from fastapi import Depends, Request, status
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from syncally.api.agreements import router as agreements_router
from syncally.api.auth import router as auth_router
from syncally.api.conversations import router as conversations_router
from syncally.api.deals import router as deals_router
from syncally.api.dev import router as dev_router
from syncally.api.documents import router as documents_router
from syncally.api.operations import OperationalFastAPI
from syncally.api.organizations import router as organizations_router
from syncally.api.payments import router as payments_router
from syncally.api.paypal_webhooks import router as paypal_webhooks_router
from syncally.infrastructure.database import get_db
from syncally.operations import configure_logging

MAX_REQUEST_BODY_BYTES = 16 * 1024


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        try:
            declared_body_size = int(content_length) if content_length is not None else None
        except ValueError:
            await JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)(
                scope, receive, send
            )
            return
        if declared_body_size is not None and declared_body_size > self.max_body_bytes:
            await JSONResponse(
                {"detail": "Request body too large"}, status_code=413
            )(scope, receive, send)
            return

        messages: list[Message] = []
        body_size = 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                messages.append(message)
                break
            body_size += len(message.get("body", b""))
            if body_size > self.max_body_bytes:
                await JSONResponse(
                    {"detail": "Request body too large"}, status_code=413
                )(scope, receive, send)
                return
            messages.append(message)
            if not message.get("more_body", False):
                break

        async def replay_receive() -> Message:
            return messages.pop(0)

        await self.app(scope, replay_receive, send)


_VALIDATION_ERROR_FIELDS = ("type", "loc", "msg", "url")


def _redacted_validation_errors(
    exc: RequestValidationError,
) -> list[dict[str, object]]:
    """Project validation errors without echoing caller-submitted values."""
    return [
        {field: error[field] for field in _VALIDATION_ERROR_FIELDS if field in error}
        for error in exc.errors()
    ]


configure_logging()

app = OperationalFastAPI(title="SyncAlly API", version="0.1.0")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return a 422 that never reflects request bodies back to the caller."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": _redacted_validation_errors(exc)},
    )


app.add_middleware(RequestBodyLimitMiddleware, max_body_bytes=MAX_REQUEST_BODY_BYTES)
app.include_router(auth_router)
app.include_router(dev_router)
app.include_router(organizations_router)
app.include_router(deals_router)
app.include_router(conversations_router)
app.include_router(agreements_router)
app.include_router(payments_router)
app.include_router(documents_router)
app.include_router(paypal_webhooks_router)


@app.get("/health", tags=["operations"])
async def health() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok"}


@app.get("/health/database", tags=["operations"])
def database_health(db: Session = Depends(get_db)) -> dict[str, str]:
    """Verify that the API can acquire and use a database connection."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
