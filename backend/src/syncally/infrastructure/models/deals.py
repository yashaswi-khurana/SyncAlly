"""Deals, conversations, messages, and private commercial constraints."""

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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from syncally.infrastructure.models.base import UUID_TYPE, Base
from syncally.infrastructure.models.mixins import TimestampMixin


class Deal(TimestampMixin, Base):
    __tablename__ = "deals"
    __table_args__ = (
        CheckConstraint("buyer_organization_id <> seller_organization_id", name="ck_deal_distinct_parties"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    buyer_organization_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("organizations.id"), nullable=False)
    seller_organization_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("organizations.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    current_proposal_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE, nullable=True)
    current_agreement_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint(
            "deal_id",
            "participant_organization_id",
            name="uq_conversations_deal_participant",
        ),
        Index(
            "ix_conversations_deal_participant_created",
            "deal_id",
            "participant_organization_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    participant_organization_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("organizations.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "(author_user_id IS NOT NULL AND author_agent_id IS NULL) "
            "OR (author_user_id IS NULL AND author_agent_id IS NOT NULL)",
            name="ck_message_has_author",
        ),
        CheckConstraint(
            "visibility IN ('PRIVATE', 'SHAREABLE', 'INTERNAL')",
            name="ck_message_visibility",
        ),
        CheckConstraint(
            "source_type IN ('USER', 'AGENT')",
            name="ck_message_source_type",
        ),
        CheckConstraint(
            "(source_type = 'USER' AND author_user_id IS NOT NULL AND author_agent_id IS NULL) "
            "OR (source_type = 'AGENT' AND author_user_id IS NULL AND author_agent_id IS NOT NULL)",
            name="ck_message_source_matches_author",
        ),
        CheckConstraint("length(trim(body)) > 0", name="ck_message_body_nonempty"),
        Index("ix_messages_conversation_visibility_created", "conversation_id", "visibility", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    author_agent_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Constraint(Base):
    __tablename__ = "constraints"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('HARD_LIMIT', 'PREFERENCE', 'FLEXIBLE_OPTION', 'INFORMATIONAL')",
            name="ck_constraint_kind",
        ),
        CheckConstraint(
            "status IN ('EXTRACTED', 'NEEDS_CLARIFICATION', 'CONFIRMED', 'REJECTED', 'SUPERSEDED')",
            name="ck_constraint_status",
        ),
        CheckConstraint(
            "visibility IN ('PRIVATE', 'SHAREABLE', 'INTERNAL')",
            name="ck_constraint_visibility",
        ),
        CheckConstraint(
            "length(trim(field)) > 0 AND length(trim(typed_value)) > 0",
            name="ck_constraint_fact_nonempty",
        ),
        CheckConstraint(
            "(source_message_id IS NOT NULL) OR "
            "(source_span IS NOT NULL AND length(trim(source_span)) > 0)",
            name="ck_constraint_source_present",
        ),
        CheckConstraint(
            "source_span IS NULL OR length(trim(source_span)) > 0",
            name="ck_constraint_source_span_nonempty",
        ),
        CheckConstraint("version >= 0", name="ck_constraint_version_nonnegative"),
        CheckConstraint(
            "(confirmed_by IS NULL AND confirmed_at IS NULL) "
            "OR (confirmed_by IS NOT NULL AND confirmed_at IS NOT NULL)",
            name="ck_constraint_confirmation_metadata_pair",
        ),
        CheckConstraint(
            "(status IN ('CONFIRMED', 'SUPERSEDED') AND confirmed_by IS NOT NULL) "
            "OR (status NOT IN ('CONFIRMED', 'SUPERSEDED') AND confirmed_by IS NULL)",
            name="ck_constraint_confirmation_status",
        ),
        Index(
            "ix_constraints_deal_owner_visibility_created",
            "deal_id",
            "owner_organization_id",
            "visibility",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    owner_organization_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("organizations.id"), nullable=False)
    field: Mapped[str] = mapped_column(Text, nullable=False)
    typed_value: Mapped[str] = mapped_column(Text, nullable=False)
    currency_or_unit: Mapped[str | None] = mapped_column(Text, nullable=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="EXTRACTED")
    visibility: Mapped[str] = mapped_column(String(32), nullable=False)
    source_message_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE, ForeignKey("messages.id"), nullable=True)
    source_span: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
