"""Configuration required to run database migrations."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import text
from sqlalchemy.engine import Connection

_BACKEND_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"

logger = logging.getLogger("syncally.migrations")

# Signed 64-bit integer constant for PostgreSQL advisory lock to serialize Alembic migrations.
# 'SYNCALEM' in ASCII hex = 0x53594E43414C454D (6005934509746310477).
MIGRATION_ADVISORY_LOCK_ID = 0x53594E43414C454D


@contextmanager
def serialize_migrations(connection: Connection) -> Iterator[None]:
    """Hold a PostgreSQL advisory lock across the full Alembic migration run.

    Session-level advisory locks survive transaction commits/rollbacks and
    autocommit blocks (e.g. concurrent index operations in revision 0011).
    """
    if connection.dialect.name == "postgresql":
        logger.info("Acquiring migration advisory lock (%s)...", MIGRATION_ADVISORY_LOCK_ID)
        connection.execute(
            text("SELECT pg_advisory_lock(:lock_id)"),
            {"lock_id": MIGRATION_ADVISORY_LOCK_ID},
        )
        if connection.in_transaction():
            connection.commit()
        try:
            yield
        finally:
            try:
                if not connection.closed and connection.in_transaction():
                    connection.rollback()
                if not connection.closed:
                    connection.execute(
                        text("SELECT pg_advisory_unlock(:lock_id)"),
                        {"lock_id": MIGRATION_ADVISORY_LOCK_ID},
                    )
                    if connection.in_transaction():
                        connection.commit()
                    logger.info(
                        "Released migration advisory lock (%s).", MIGRATION_ADVISORY_LOCK_ID
                    )
            except Exception:
                logger.warning(
                    "Failed to explicitly release migration advisory lock; connection close will release it.",
                    exc_info=True,
                )
    else:
        yield


class MigrationSettings(BaseSettings):
    database_url: str

    model_config = SettingsConfigDict(
        env_file=_BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )
