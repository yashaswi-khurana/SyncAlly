"""Durable deal reminder persistence model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from syncally.infrastructure.models.base import UUID_TYPE, Base
from syncally.infrastructure.models.mixins import TimestampMixin


class DealReminderModel(TimestampMixin, Base):
    __tablename__ = "deal_reminders"
    __table_args__ = (
        CheckConstraint(
            "scope IN ('FULFILLMENT', 'MILESTONE', 'CASE', 'ROUTING')",
            name="ck_deal_reminders_scope",
        ),
        CheckConstraint(
            "status IN ('SCHEDULED', 'PENDING', 'DELIVERED', 'SUPPRESSED', 'FAILED')",
            name="ck_deal_reminders_status",
        ),
        CheckConstraint("channel IN ('IN_APP')", name="ck_deal_reminders_channel"),
        CheckConstraint("recurrence_cap >= 1", name="ck_deal_reminders_recurrence_cap_positive"),
        CheckConstraint("recurrence_count >= 0", name="ck_deal_reminders_recurrence_count_nonneg"),
        CheckConstraint("retry_count >= 0", name="ck_deal_reminders_retry_count_nonneg"),
        Index("ix_deal_reminders_deal_status", "deal_id", "status"),
        Index("ix_deal_reminders_pending_due", "status", "due_at", "next_attempt_at"),
        Index("ix_deal_reminders_dedup", "deduplication_key", unique=True),
        Index("ix_deal_reminders_recipient", "recipient_organization_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, nullable=False, index=True)
    recipient_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id"), nullable=False, index=True
    )
    recipient_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("users.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SCHEDULED", index=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    recurrence_cap: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    recurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deduplication_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="IN_APP")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suppressed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suppression_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
