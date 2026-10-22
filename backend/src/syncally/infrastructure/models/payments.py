"""Payment milestones, intents, and provider webhook records."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from syncally.infrastructure.models.base import JSON_TYPE, UUID_TYPE, Base
from syncally.infrastructure.models.mixins import TimestampMixin


class PaymentMilestone(TimestampMixin, Base):
    __tablename__ = "payment_milestones"
    __table_args__ = (
        UniqueConstraint("agreement_version_id", "sequence_number"),
        CheckConstraint("sequence_number > 0", name="ck_payment_milestone_sequence_positive"),
        CheckConstraint("amount > 0", name="ck_payment_milestone_amount_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    agreement_version_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("agreement_versions.id", ondelete="CASCADE"), nullable=False)
    obligation_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE, ForeignKey("obligations.id"), nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    payer_organization_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("organizations.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(64), nullable=False)
    due_condition: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")


# Matches syncally.domain.payments.intent.PaymentIntentStatus's terminal states.
# Kept as a literal here (not imported from the domain layer) to match this
# file's existing CheckConstraint style of inlined status literals.
_ACTIVE_PAYMENT_INTENT_WHERE = text("status NOT IN ('PAID', 'FAILED', 'CANCELLED')")


class PaymentIntent(TimestampMixin, Base):
    __tablename__ = "payment_intents"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_intent_amount_positive"),
        # At most one non-terminal intent per milestone: the persistence-level
        # guard against starting a second PayPal invoice for the same money.
        Index(
            "ix_payment_intents_one_active_per_milestone",
            "payment_milestone_id",
            unique=True,
            postgresql_where=_ACTIVE_PAYMENT_INTENT_WHERE,
            sqlite_where=_ACTIVE_PAYMENT_INTENT_WHERE,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id"), nullable=False)
    agreement_version_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("agreement_versions.id"), nullable=False)
    payment_milestone_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("payment_milestones.id"), nullable=False)
    seller_organization_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("organizations.id"), nullable=False)
    payer_organization_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("organizations.id"), nullable=False)
    authorized_by: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="AUTHORIZED")
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="PAYPAL")
    provider_invoice_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    request_payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_create_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reconciled_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    last_reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (UniqueConstraint("provider", "provider_event_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    payment_intent_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE, ForeignKey("payment_intents.id"), nullable=True)
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
