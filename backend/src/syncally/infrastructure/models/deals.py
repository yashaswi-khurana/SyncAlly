"""Deals, conversations, messages, and private commercial constraints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from syncally.infrastructure.models.base import Base, JSON_TYPE, UUID_TYPE
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

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    participant_organization_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("organizations.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("NOT (author_user_id IS NULL AND author_agent_id IS NULL)", name="ck_message_has_author"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    author_agent_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Constraint(Base):
    __tablename__ = "constraints"

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
