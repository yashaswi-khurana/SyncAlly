"""Append-only shipment, observation, and confirmation records."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from syncally.infrastructure.models.base import UUID_TYPE, Base


class FulfillmentEvent(Base):
    __tablename__ = "fulfillment_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('SHIPPED', 'OBSERVED', 'CONFIRMED')",
            name="ck_fulfillment_event_type",
        ),
        CheckConstraint("source_type = 'USER_ATTESTATION'", name="ck_fulfillment_source_type"),
        CheckConstraint("version > 0", name="ck_fulfillment_version_positive"),
        UniqueConstraint(
            "deal_id", "actor_user_id", "idempotency_key", name="uq_fulfillment_idempotency"
        ),
        UniqueConstraint("obligation_id", "version", name="uq_fulfillment_obligation_version"),
        ForeignKeyConstraint(
            ["agreement_version_id", "deal_id", "terms_hash"],
            ["agreement_versions.id", "agreement_versions.deal_id", "agreement_versions.terms_hash"],
            name="fk_fulfillment_agreement_scope",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["obligation_id", "deal_id", "agreement_version_id"],
            ["obligations.id", "obligations.deal_id", "obligations.agreement_version_id"],
            name="fk_fulfillment_obligation_scope",
            ondelete="CASCADE",
        ),
        Index(
            "ix_fulfillment_events_version_obligation_recorded",
            "agreement_version_id",
            "obligation_id",
            "recorded_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    agreement_version_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, nullable=False)
    terms_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    obligation_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, nullable=False)
    actor_organization_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("organizations.id"), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str] = mapped_column(String(100), nullable=False)
    carrier: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    dispatch_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="USER_ATTESTATION")
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
