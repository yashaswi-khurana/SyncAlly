"""Agreement versions, approvals, and executable obligations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from syncally.infrastructure.models.base import Base, JSON_TYPE, UUID_TYPE
from syncally.infrastructure.models.mixins import TimestampMixin


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
    agreement_version_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("agreement_versions.id", ondelete="CASCADE"), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    terms_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    auth_context: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Obligation(TimestampMixin, Base):
    __tablename__ = "obligations"
    __table_args__ = (CheckConstraint("owner_organization_id <> counterparty_organization_id", name="ck_obligation_distinct_parties"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    agreement_version_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("agreement_versions.id", ondelete="CASCADE"), nullable=False)
    obligation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    owner_organization_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("organizations.id"), nullable=False)
    counterparty_organization_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("organizations.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    due_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_terms_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
