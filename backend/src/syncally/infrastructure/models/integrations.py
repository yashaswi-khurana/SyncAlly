"""Persistence records for organization-scoped external integrations."""

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
    text,
)
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


class SlackEvent(Base):
    """Minimal durable queue record for one verified Slack event."""

    __tablename__ = "slack_events"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'PROCESSING', 'DELIVERED', 'FAILED')", name="ck_slack_event_status"),
        Index("ix_slack_events_pending", "status", "available_at"),
        Index("ix_slack_events_retention", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("slack_installations.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    slack_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    channel_id: Mapped[str] = mapped_column(String(64), nullable=False)
    message_ts: Mapped[str] = mapped_column(String(32), nullable=False)
    thread_ts: Mapped[str] = mapped_column(String(32), nullable=False)
    command: Mapped[str] = mapped_column(String(32), nullable=False)
    deal_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_error: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SlackUserLink(Base):
    """Explicit mapping between one Slack identity and one SyncAlly actor."""

    __tablename__ = "slack_user_links"
    __table_args__ = (
        UniqueConstraint("installation_id", "slack_user_id", name="uq_slack_user_link_slack_identity"),
        UniqueConstraint("installation_id", "user_id", name="uq_slack_user_link_syncally_identity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("slack_installations.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    slack_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SlackLinkChallenge(Base):
    """Short-lived hashed pairing challenge; encrypted code enables safe retries."""

    __tablename__ = "slack_link_challenges"
    __table_args__ = (
        Index("ix_slack_link_challenges_expires_at", "expires_at"),
        UniqueConstraint("event_id", name="uq_slack_link_challenge_event"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("slack_installations.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    slack_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    encrypted_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SlackDealSubscription(Base):
    """Private Slack thread subscription to one SyncAlly deal's updates."""

    __tablename__ = "slack_deal_subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "installation_id", "user_id", "deal_id", "channel_id", "thread_ts",
            name="uq_slack_deal_subscription_thread",
        ),
        Index("ix_slack_deal_subscriptions_deal", "deal_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("slack_installations.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    slack_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False
    )
    channel_id: Mapped[str] = mapped_column(String(64), nullable=False)
    thread_ts: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SlackNotificationDelivery(Base):
    """Durable per-subscription delivery for one SyncAlly outbox event."""

    __tablename__ = "slack_notification_deliveries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'DELIVERED', 'FAILED')",
            name="ck_slack_notification_delivery_status",
        ),
        UniqueConstraint(
            "source_event_id", "subscription_id",
            name="uq_slack_notification_source_subscription",
        ),
        Index("ix_slack_notification_deliveries_pending", "status", "available_at"),
        Index("ix_slack_notification_deliveries_retention", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    source_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("outbox_events.id", ondelete="CASCADE"), nullable=False
    )
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID_TYPE, ForeignKey("slack_deal_subscriptions.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_error: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
