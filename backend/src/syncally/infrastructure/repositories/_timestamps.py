"""Timestamp conversions at the database-to-domain boundary."""

from datetime import UTC, datetime


def as_utc(value: datetime) -> datetime:
    """Return a UTC-aware timestamp, treating naive database values as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
