"""Shared ORM base types and SQLAlchemy type aliases."""

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")
UUID_TYPE = UUID(as_uuid=True)


class Base(DeclarativeBase):
    """Metadata registry shared by every persistence model."""
