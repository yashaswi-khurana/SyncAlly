"""Negotiation sessions and immutable proposal snapshots."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, CheckConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from syncally.infrastructure.models.base import Base, UUID_TYPE
from syncally.infrastructure.models.mixins import TimestampMixin

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class NegotiationSession(TimestampMixin, Base):
    __tablename__ = "negotiation_sessions"
    __table_args__ = (CheckConstraint("max_rounds > 0", name="ck_negotiation_max_rounds_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, unique=True)
    max_rounds: Mapped[int] = mapped_column(Integer, nullable=False)
    round_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_proposal_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE, nullable=True)
    escalated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Proposal(Base):
    __tablename__ = "proposals"
    __table_args__ = (UniqueConstraint("deal_id", "proposal_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    negotiation_session_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("negotiation_sessions.id", ondelete="CASCADE"), nullable=False)
    proposal_number: Mapped[int] = mapped_column(Integer, nullable=False)
    author_organization_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("organizations.id"), nullable=False)
    based_on_proposal_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE, ForeignKey("proposals.id"), nullable=True)
    terms_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    terms_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
