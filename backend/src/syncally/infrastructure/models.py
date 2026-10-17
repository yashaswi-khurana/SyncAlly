"""SQLAlchemy persistence models for the SyncAlly commercial ledger."""

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
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")
UUID_TYPE = UUID(as_uuid=True)


class Base(DeclarativeBase):
    """Base class for all persistence models."""


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    legal_name: Mapped[str] = mapped_column(Text, nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class OrganizationMember(TimestampMixin, Base):
    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("organization_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="MEMBER")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class Deal(TimestampMixin, Base):
    __tablename__ = "deals"
    __table_args__ = (
        CheckConstraint("buyer_organization_id <> seller_organization_id", name="ck_deal_distinct_parties"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    buyer_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id"), nullable=False
    )
    seller_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    current_proposal_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE, nullable=True)
    current_agreement_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    participant_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "NOT (author_user_id IS NULL AND author_agent_id IS NULL)",
            name="ck_message_has_author",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("users.id"), nullable=True
    )
    author_agent_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class NegotiationSession(TimestampMixin, Base):
    __tablename__ = "negotiation_sessions"
    __table_args__ = (CheckConstraint("max_rounds > 0", name="ck_negotiation_max_rounds_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    max_rounds: Mapped[int] = mapped_column(Integer, nullable=False)
    round_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_proposal_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE, nullable=True)
    escalated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Proposal(Base):
    __tablename__ = "proposals"
    __table_args__ = (UniqueConstraint("deal_id", "proposal_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    negotiation_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("negotiation_sessions.id", ondelete="CASCADE"), nullable=False
    )
    proposal_number: Mapped[int] = mapped_column(Integer, nullable=False)
    author_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id"), nullable=False
    )
    based_on_proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("proposals.id"), nullable=True
    )
    terms_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    terms_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Constraint(Base):
    __tablename__ = "constraints"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    owner_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id"), nullable=False
    )
    field: Mapped[str] = mapped_column(Text, nullable=False)
    typed_value: Mapped[str] = mapped_column(Text, nullable=False)
    currency_or_unit: Mapped[str | None] = mapped_column(Text, nullable=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="EXTRACTED")
    visibility: Mapped[str] = mapped_column(String(32), nullable=False)
    source_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("messages.id"), nullable=True
    )
    source_span: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AgreementVersion(Base):
    __tablename__ = "agreement_versions"
    __table_args__ = (UniqueConstraint("deal_id", "version_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    proposal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("proposals.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    canonical_terms_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    terms_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING_APPROVAL")
    created_by: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Approval(Base):
    __tablename__ = "approvals"
    __table_args__ = (UniqueConstraint("agreement_version_id", "organization_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    agreement_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("agreement_versions.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    terms_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    auth_context: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Obligation(TimestampMixin, Base):
    __tablename__ = "obligations"
    __table_args__ = (
        CheckConstraint("owner_organization_id <> counterparty_organization_id", name="ck_obligation_distinct_parties"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    agreement_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("agreement_versions.id", ondelete="CASCADE"), nullable=False
    )
    obligation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    owner_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id"), nullable=False
    )
    counterparty_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    due_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_terms_reference: Mapped[str | None] = mapped_column(Text, nullable=True)


class PaymentMilestone(TimestampMixin, Base):
    __tablename__ = "payment_milestones"
    __table_args__ = (
        UniqueConstraint("agreement_version_id", "sequence_number"),
        CheckConstraint("amount > 0", name="ck_payment_milestone_amount_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    agreement_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("agreement_versions.id", ondelete="CASCADE"), nullable=False
    )
    obligation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("obligations.id"), nullable=True
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    payer_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(64), nullable=False)
    due_condition: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")


class PaymentIntent(TimestampMixin, Base):
    __tablename__ = "payment_intents"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_payment_intent_amount_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    agreement_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("agreement_versions.id"), nullable=False
    )
    payment_milestone_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("payment_milestones.id"), nullable=False
    )
    seller_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id"), nullable=False
    )
    payer_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id"), nullable=False
    )
    authorized_by: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="AUTHORIZED")
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="PAYPAL")
    provider_invoice_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    request_payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reconciled_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    last_reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    payment_intent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("payment_intents.id"), nullable=True
    )
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)
