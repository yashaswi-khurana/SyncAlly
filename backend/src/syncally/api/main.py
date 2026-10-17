"""FastAPI application entry point."""

from fastapi import Depends, FastAPI
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from sqlalchemy import text
from sqlalchemy.orm import Session

from syncally.api.auth import router as auth_router
from syncally.api.deals import read_deal
from syncally.api.organizations import router as organizations_router
from syncally.infrastructure.database import get_db

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


app = FastAPI(title="SyncAlly API", version="0.1.0")
app.add_middleware(RequestBodyLimitMiddleware, max_body_bytes=MAX_REQUEST_BODY_BYTES)
app.include_router(auth_router)
app.include_router(organizations_router)


@app.get("/health", tags=["operations"])
async def health() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok"}


@app.get("/health/database", tags=["operations"])
def database_health(db: Session = Depends(get_db)) -> dict[str, str]:
    """Verify that the API can acquire and use a database connection."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


app.add_api_route("/deals/{deal_id}", read_deal, methods=["GET"], tags=["deals"])
