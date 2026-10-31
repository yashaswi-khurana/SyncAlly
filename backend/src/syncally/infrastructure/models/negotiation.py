"""Negotiation sessions and immutable proposal snapshots."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from syncally.infrastructure.models.base import UUID_TYPE, Base
from syncally.infrastructure.models.mixins import TimestampMixin

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class NegotiationSession(TimestampMixin, Base):
    __tablename__ = "negotiation_sessions"
    __table_args__ = (
        CheckConstraint("max_rounds > 0", name="ck_negotiation_max_rounds_positive"),
        CheckConstraint("round_count >= 0 AND round_count <= max_rounds", name="ck_negotiation_round_count"),
        UniqueConstraint("id", "deal_id", name="uq_negotiation_session_scope"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, unique=True)
    max_rounds: Mapped[int] = mapped_column(Integer, nullable=False)
    round_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_proposal_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE, nullable=True)
    escalated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Proposal(Base):
    __tablename__ = "proposals"
    __table_args__ = (
        UniqueConstraint("deal_id", "proposal_number"),
        UniqueConstraint("id", "deal_id", name="uq_proposal_scope"),
        ForeignKeyConstraint(["negotiation_session_id", "deal_id"], ["negotiation_sessions.id", "negotiation_sessions.deal_id"], name="fk_proposal_session_scope"),
        ForeignKeyConstraint(["based_on_proposal_id", "deal_id"], ["proposals.id", "proposals.deal_id"], name="fk_proposal_predecessor_scope"),
        CheckConstraint("proposal_number > 0", name="ck_proposal_number_positive"),
        CheckConstraint("lifecycle_origin IN ('LEGACY', 'HUMAN_ROUNDS')", name="ck_proposal_origin"),
        CheckConstraint("lifecycle_origin = 'LEGACY' OR (created_by IS NOT NULL AND status IN ('SUBMITTED', 'ACCEPTED_AS_CANDIDATE', 'REJECTED', 'SUPERSEDED', 'EXPIRED'))", name="ck_human_proposal_state"),
        CheckConstraint("lifecycle_origin = 'LEGACY' OR expires_at IS NULL OR expires_at > created_at", name="ck_human_proposal_expiry"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    negotiation_session_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("negotiation_sessions.id", ondelete="CASCADE"), nullable=False)
    proposal_number: Mapped[int] = mapped_column(Integer, nullable=False)
    author_organization_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("organizations.id"), nullable=False)
    based_on_proposal_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE, ForeignKey("proposals.id"), nullable=True)
    terms_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    terms_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    lifecycle_origin: Mapped[str] = mapped_column(String(16), nullable=False, default="LEGACY", server_default="LEGACY")
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE, ForeignKey("users.id"))
    evidence_refs: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON_TYPE)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class NegotiationAction(Base):
    __tablename__ = "negotiation_actions"
    __table_args__ = (
        UniqueConstraint("deal_id", "command_id", name="uq_negotiation_command"),
        ForeignKeyConstraint(["session_id", "deal_id"], ["negotiation_sessions.id", "negotiation_sessions.deal_id"], name="fk_action_session_scope"),
        ForeignKeyConstraint(["proposal_id", "deal_id"], ["proposals.id", "proposals.deal_id"], name="fk_action_proposal_scope"),
        ForeignKeyConstraint(["predecessor_id", "deal_id"], ["proposals.id", "proposals.deal_id"], name="fk_action_predecessor_scope"),
        ForeignKeyConstraint(["candidate_id", "deal_id"], ["agreement_versions.id", "agreement_versions.deal_id"], name="fk_action_candidate_scope"),
        ForeignKeyConstraint(["invalidated_candidate_id", "deal_id"], ["agreement_versions.id", "agreement_versions.deal_id"], name="fk_action_invalidated_scope"),
        CheckConstraint("action IN ('submit', 'counter', 'accept', 'reject', 'supersede', 'expire', 'escalate')", name="ck_negotiation_action"),
        CheckConstraint("expected_deal_revision >= 0", name="ck_negotiation_action_revision"),
        Index("uq_negotiation_terminal_action", "proposal_id", unique=True,
              sqlite_where=text("action IN ('accept', 'reject', 'supersede', 'expire')"),
              postgresql_where=text("action IN ('accept', 'reject', 'supersede', 'expire')")),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id"), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, nullable=False)
    command_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_organization_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("organizations.id"), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    expected_deal_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE)
    predecessor_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE)
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE)
    invalidated_candidate_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE)
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str | None] = mapped_column(String(32))
    result: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
