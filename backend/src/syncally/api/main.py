"""FastAPI application entry point."""

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from syncally.api.auth import router as auth_router
from syncally.api.deals import read_deal
from syncally.infrastructure.database import get_db

app = FastAPI(title="SyncAlly API", version="0.1.0")
app.include_router(auth_router)


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
