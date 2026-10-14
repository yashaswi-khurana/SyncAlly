"""FastAPI application entry point."""

from fastapi import FastAPI

app = FastAPI(title="SyncAlly API", version="0.1.0")


@app.get("/health", tags=["operations"])
async def health() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok"}
