"""Persistence records for organization-scoped external integrations."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from syncally.infrastructure.models.base import JSON_TYPE, UUID_TYPE, Base


class SlackInstallation(Base):
    """One Slack workspace installation mapped to a SyncAlly organization."""

    __tablename__ = "slack_installations"
    __table_args__ = (
        CheckConstraint("status IN ('CONNECTED', 'DISCONNECTED')", name="ck_slack_installation_status"),
        CheckConstraint(
            "(status = 'CONNECTED' AND encrypted_bot_token IS NOT NULL AND disconnected_at IS NULL) "
            "OR (status = 'DISCONNECTED' AND encrypted_bot_token IS NULL AND disconnected_at IS NOT NULL)",
            name="ck_slack_installation_credential_lifecycle",
        ),
        Index(
            "uq_slack_installation_org_connected",
            "organization_id",
            unique=True,
            postgresql_where=text("status = 'CONNECTED'"),
            sqlite_where=text("status = 'CONNECTED'"),
        ),
        Index(
            "uq_slack_installation_workspace_connected",
            "workspace_id",
            unique=True,
            postgresql_where=text("status = 'CONNECTED'"),
            sqlite_where=text("status = 'CONNECTED'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    workspace_name: Mapped[str] = mapped_column(String(256), nullable=False)
    bot_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    encrypted_bot_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    granted_scopes: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="CONNECTED")
    connected_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("users.id"), nullable=False
    )
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SlackOAuthState(Base):
    """Hashed, one-use OAuth state bound to an initiating actor and organization."""

    __tablename__ = "slack_oauth_states"
    __table_args__ = (Index("ix_slack_oauth_states_expires_at", "expires_at"),)

    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
