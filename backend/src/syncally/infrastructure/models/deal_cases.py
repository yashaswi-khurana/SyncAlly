"""Deal cancellation and dispute case persistence models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from syncally.infrastructure.models.base import JSON_TYPE, UUID_TYPE, Base
from syncally.infrastructure.models.mixins import TimestampMixin


class DealCaseModel(TimestampMixin, Base):
    __tablename__ = "deal_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("deals.id"), nullable=False, index=True)
    agreement_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("agreement_versions.id"), nullable=False
    )
    agreement_terms_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    case_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    obligation_references: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False, default=list)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    requested_by_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN", index=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_visibility: Mapped[str] = mapped_column(String(32), nullable=False, default="MUTUAL_VISIBLE")
    bilateral_consent_counterparty_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id"), nullable=True
    )
    bilateral_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    operational_impact_blockers: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    evidence_items: Mapped[list[DealCaseEvidenceModel]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DealCaseEvidenceModel.submitted_at",
    )


class DealCaseEvidenceModel(Base):
    __tablename__ = "deal_case_evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("deal_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    submitted_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, ForeignKey("users.id"), nullable=False)
    submitted_by_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id"), nullable=False
    )
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, default="MUTUAL_VISIBLE")
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    case: Mapped[DealCaseModel] = relationship(back_populates="evidence_items")
