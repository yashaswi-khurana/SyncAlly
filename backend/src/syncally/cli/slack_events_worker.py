"""Durable Slack event processor. Run with python -m syncally.cli.slack_events_worker."""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import delete, exists, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from syncally.api.authorization import require_deal_action
from syncally.application.deals import DealNotFound, get_deal
from syncally.application.payments import PaymentStatusRecord, list_current_payment_statuses
from syncally.config import settings
from syncally.domain.payments.intent import PaymentIntentStatus
from syncally.domain.shared.money import canonical_decimal
from syncally.infrastructure.database import SessionLocal
from syncally.infrastructure.identity import resolve_actor
from syncally.infrastructure.integrations.slack import SlackIntegrationError, SlackTokenCipher
from syncally.infrastructure.integrations.slack_events import SlackWebAPI, SlackWebAPIError
from syncally.infrastructure.models import (
    AgreementVersion,
    AuditEvent,
    OutboxEvent,
    PaymentIntent,
    SlackDealSubscription,
    SlackEvent,
    SlackInstallation,
    SlackLinkChallenge,
    SlackNotificationDelivery,
    SlackUserLink,
)
from syncally.infrastructure.repositories._timestamps import as_utc
from syncally.infrastructure.repositories.agreements import SqlAlchemyAgreementRepository
from syncally.infrastructure.repositories.deals import SqlAlchemyDealRepository
from syncally.infrastructure.repositories.payments import SqlAlchemyPaymentIntentRepository
from syncally.operations import configure_logging

logger = logging.getLogger(__name__)
_MAX_ATTEMPTS = 8
_LEASE_SECONDS = 60
_EVENT_RETENTION_DAYS = 30
_PRIVATE_DEAL_DENIAL = "I couldn't find an authorized deal to follow."
_SAFE_PROVIDER_FAILURES = frozenset(
    {
        "ratelimited",
        "thread_not_supported",
        "thread_not_found",
        "message_not_found",
        "invalid_auth",
        "not_in_channel",
        "channel_not_found",
        "missing_scope",
        "no_permission",
        "user_not_in_channel",
        "provider_http_error",
        "provider_error",
        "delivery_uncertain",
    }
)


def _safe_failure_kind(error: Exception) -> str:
    if isinstance(error, SlackWebAPIError):
        return error.code if error.code in _SAFE_PROVIDER_FAILURES else "provider_error"
    if isinstance(error, SlackIntegrationError):
        return "credential_error"
    if isinstance(error, SQLAlchemyError):
        return "database_error"
    return "worker_error"


def _record_failure(
    session_factory: Callable[[], Session],
    event_id: uuid.UUID,
    *,
    failure_kind: str,
    retry_after: float | None = None,
    uncertain: bool = False,
    terminal: bool = False,
) -> None:
    db = session_factory()
    try:
        event = db.get(SlackEvent, event_id)
        if event is None:
            return
        event.last_error = failure_kind
        if uncertain or terminal or event.attempts >= _MAX_ATTEMPTS:
            event.status = "FAILED"
        else:
            event.status = "PENDING"
            event.available_at = datetime.now(UTC) + timedelta(
                seconds=retry_after or min(2 ** event.attempts, 300)
            )
        db.commit()
        logger.warning(
            "Slack event failure recorded",
            extra={"failure_kind": failure_kind, "retryable": event.status == "PENDING"},
        )
    except Exception:
        db.rollback()
        # The leased event becomes eligible again and is failed at the attempt cap.
        logger.error("Could not persist Slack event failure state")
    finally:
        db.close()


async def _provider_call(method, *args, **kwargs) -> None:
    try:
        await method(*args, **kwargs)
    except SlackWebAPIError:
        raise
    except Exception as error:
        # The provider may have accepted a request before an unexpected client
        # failure. Do not automatically replay an ambiguous send.
        raise SlackWebAPIError("delivery_uncertain", uncertain=True) from error


def _cipher() -> SlackTokenCipher:
    return SlackTokenCipher(settings.integration_token_encryption_key.get_secret_value())


def _payment_summary_text(payments: list[PaymentStatusRecord]) -> str:
    if not payments:
        return "No payment status is available for this deal yet."

    lines = ["Payment status:"]
    for payment in sorted(
        payments,
        key=lambda item: (item.milestone_sequence, str(item.intent_id)),
    ):
        try:
            payment_status = PaymentIntentStatus(payment.status).value
        except ValueError:
            payment_status = "UNKNOWN"
        amount = canonical_decimal(payment.amount.amount)
        lines.append(
            f"Milestone {payment.milestone_sequence}: {payment_status} — "
            f"{payment.amount.currency} {amount}"
        )
    return "\n".join(lines)


def _authorized_subscription_deal(
    db: Session,
    installation: SlackInstallation,
    link: SlackUserLink,
    deal_id: str,
    *,
    permission: str = "deal.read_assigned",
):
    """Reload the actor and enforce current deal-read and action access."""
    actor = resolve_actor(db, link.user_id)
    if actor is None or installation.organization_id not in actor.organization_ids:
        return None
    try:
        deal_uuid = uuid.UUID(deal_id)
        deal = get_deal(actor, deal_uuid, SqlAlchemyDealRepository(db))
        require_deal_action(actor, deal, installation.organization_id, permission)
    except (DealNotFound, ValueError, HTTPException):
        return None
    return deal


def _audit_subscription_change(
    db: Session,
    *,
    subscription_id: uuid.UUID,
    deal_id: uuid.UUID,
    installation: SlackInstallation,
    user_id: uuid.UUID,
    event_type: str,
    now: datetime,
) -> None:
    db.add(
        AuditEvent(
            id=uuid.uuid4(),
            aggregate_type="slack_deal_subscription",
            aggregate_id=subscription_id,
            event_type=event_type,
            actor_type="USER",
            actor_id=str(user_id),
            occurred_at=now,
            payload={
                "provider": "SLACK",
                "organization_id": str(installation.organization_id),
                "workspace_id": installation.workspace_id,
                "deal_id": str(deal_id),
                "outcome": event_type.rsplit(".", 1)[-1].upper(),
            },
        )
    )


def prune_slack_records(db: Session, now: datetime | None = None) -> tuple[int, int]:
    """Delete expired pairing codes and terminal event metadata past retention."""
    current_time = now or datetime.now(UTC)
    expired_challenges = db.execute(
        delete(SlackLinkChallenge).where(SlackLinkChallenge.expires_at <= current_time)
    ).rowcount or 0
    old_terminal_events = db.execute(
        delete(SlackEvent).where(
            SlackEvent.status.in_(("DELIVERED", "FAILED")),
            SlackEvent.created_at < current_time - timedelta(days=_EVENT_RETENTION_DAYS),
        )
    ).rowcount or 0
    db.execute(
        delete(SlackNotificationDelivery).where(
            SlackNotificationDelivery.status.in_(("DELIVERED", "FAILED")),
            SlackNotificationDelivery.created_at < current_time - timedelta(days=_EVENT_RETENTION_DAYS),
        )
    )
    db.commit()
    return expired_challenges, old_terminal_events


def _enqueue_slack_notification_deliveries(db: Session, now: datetime) -> int:
    """Fan out supported outbox notifications without touching Temporal state."""
    existing = exists(
        select(SlackNotificationDelivery.id).where(
            SlackNotificationDelivery.source_event_id == OutboxEvent.id,
            SlackNotificationDelivery.subscription_id == SlackDealSubscription.id,
        )
    )
    # The existing agreement outbox contract stores DomainAgreement.id (the
    # deal UUID) in aggregate_id; agreement_version_id lives in the payload.
    agreement_rows = db.execute(
        select(OutboxEvent.id, SlackDealSubscription.id, OutboxEvent.created_at)
        .join(SlackDealSubscription, SlackDealSubscription.deal_id == OutboxEvent.aggregate_id)
        .where(
            OutboxEvent.aggregate_type == "agreement",
            OutboxEvent.event_type == "AGREEMENT_COMMITTED",
            OutboxEvent.created_at >= now - timedelta(days=_EVENT_RETENTION_DAYS),
            SlackDealSubscription.created_at < OutboxEvent.created_at,
            ~existing,
        )
        .order_by(OutboxEvent.created_at, OutboxEvent.id, SlackDealSubscription.id)
        .limit(250)
    ).all()
    completion_rows = db.execute(
        select(OutboxEvent.id, SlackDealSubscription.id, OutboxEvent.created_at)
        .join(SlackDealSubscription, SlackDealSubscription.deal_id == OutboxEvent.aggregate_id)
        .where(
            OutboxEvent.aggregate_type == "deal",
            OutboxEvent.event_type == "DEAL_NOTIFICATION",
            OutboxEvent.payload["kind"].as_string() == "DEAL_COMPLETED",
            OutboxEvent.created_at >= now - timedelta(days=_EVENT_RETENTION_DAYS),
            SlackDealSubscription.created_at < OutboxEvent.created_at,
            ~existing,
        )
        .order_by(OutboxEvent.created_at, OutboxEvent.id, SlackDealSubscription.id)
        .limit(250)
    ).all()
    payment_rows = db.execute(
        select(OutboxEvent.id, SlackDealSubscription.id, OutboxEvent.created_at)
        .join(SlackDealSubscription, SlackDealSubscription.deal_id == OutboxEvent.aggregate_id)
        .where(
            OutboxEvent.aggregate_type == "deal",
            OutboxEvent.event_type == "DEAL_NOTIFICATION",
            OutboxEvent.payload["kind"].as_string() == "PAYMENT_STATE_CHANGED",
            OutboxEvent.created_at >= now - timedelta(days=_EVENT_RETENTION_DAYS),
            SlackDealSubscription.created_at < OutboxEvent.created_at,
            ~existing,
        )
        .order_by(OutboxEvent.created_at, OutboxEvent.id, SlackDealSubscription.id)
        .limit(250)
    ).all()
    rows = sorted(
        [*agreement_rows, *completion_rows, *payment_rows],
        key=lambda row: (row[2], str(row[0]), str(row[1])),
    )[:250]
    inserted = 0
    for source_event_id, subscription_id, source_created_at in rows:
        try:
            with db.begin_nested():
                source = db.get(OutboxEvent, source_event_id)
                subscription = db.get(SlackDealSubscription, subscription_id)
                payment_matches = True
                if (
                    source is not None
                    and source.aggregate_type == "deal"
                    and source.event_type == "DEAL_NOTIFICATION"
                    and isinstance(source.payload, dict)
                    and source.payload.get("kind") == "PAYMENT_STATE_CHANGED"
                ):
                    try:
                        payment_id = uuid.UUID(source.payload.get("record_id", ""))
                    except (AttributeError, TypeError, ValueError):
                        payment_id = None
                    intent = db.get(PaymentIntent, payment_id) if payment_id is not None else None
                    payment_matches = bool(
                        subscription is not None
                        and source.aggregate_id == subscription.deal_id
                        and source.payload.get("deal_id") == str(subscription.deal_id)
                        and intent is not None
                        and intent.deal_id == subscription.deal_id
                    )
                db.add(
                    SlackNotificationDelivery(
                        id=uuid.uuid4(),
                        source_event_id=source_event_id,
                        subscription_id=subscription_id,
                        status="PENDING" if payment_matches else "FAILED",
                        attempts=0,
                        available_at=as_utc(source_created_at),
                        last_error=None if payment_matches else "source_mismatch",
                    )
                )
                db.flush()
            inserted += 1
        except IntegrityError:
            # Another worker may have fanned out this exact source/subscriber
            # pair while this process was selecting it.
            continue
    db.commit()
    return inserted


def _take_notification_delivery(db: Session, now: datetime) -> uuid.UUID | None:
    _enqueue_slack_notification_deliveries(db, now)
    db.execute(
        update(SlackNotificationDelivery)
        .where(
            SlackNotificationDelivery.status == "PROCESSING",
            SlackNotificationDelivery.available_at <= now,
        )
        .values(status="FAILED", last_error="delivery_uncertain")
    )
    db.execute(
        update(SlackNotificationDelivery)
        .where(
            SlackNotificationDelivery.available_at <= now,
            SlackNotificationDelivery.status == "PENDING",
            SlackNotificationDelivery.attempts >= _MAX_ATTEMPTS,
        )
        .values(status="FAILED", last_error="attempts_exhausted")
    )
    db.commit()
    delivery = db.scalar(
        select(SlackNotificationDelivery)
        .where(
            SlackNotificationDelivery.available_at <= now,
            SlackNotificationDelivery.status == "PENDING",
            SlackNotificationDelivery.attempts < _MAX_ATTEMPTS,
        )
        .order_by(SlackNotificationDelivery.available_at, SlackNotificationDelivery.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if delivery is None:
        return None
    delivery.status = "PROCESSING"
    delivery.attempts += 1
    delivery.available_at = now + timedelta(seconds=_LEASE_SECONDS)
    db.commit()
    return delivery.id


def _record_notification_failure(
    session_factory: Callable[[], Session],
    delivery_id: uuid.UUID,
    *,
    failure_kind: str,
    retry_after: float | None = None,
    uncertain: bool = False,
    terminal: bool = False,
) -> None:
    db = session_factory()
    try:
        delivery = db.get(SlackNotificationDelivery, delivery_id)
        if delivery is None:
            return
        delivery.last_error = failure_kind
        if uncertain or terminal or delivery.attempts >= _MAX_ATTEMPTS:
            delivery.status = "FAILED"
        else:
            delivery.status = "PENDING"
            delivery.available_at = datetime.now(UTC) + timedelta(
                seconds=retry_after or min(2 ** delivery.attempts, 300)
            )
        db.commit()
        logger.warning(
            "Slack notification delivery failure recorded",
            extra={"failure_kind": failure_kind, "retryable": delivery.status == "PENDING"},
        )
    except Exception:
        db.rollback()
        logger.error("Could not persist Slack notification delivery failure state")
    finally:
        db.close()


async def _deliver_notification(
    db: Session,
    delivery_id: uuid.UUID,
    api: SlackWebAPI,
) -> None:
    delivery = db.get(SlackNotificationDelivery, delivery_id)
    if delivery is None:
        return
    subscription = db.get(SlackDealSubscription, delivery.subscription_id)
    source = db.get(OutboxEvent, delivery.source_event_id)
    if subscription is None or source is None:
        delivery.status = "FAILED"
        delivery.last_error = "source_or_subscription_missing"
        db.commit()
        return

    source_payload = source.payload if isinstance(source.payload, dict) else {}
    notification_kind: str | None = None
    if source.aggregate_type == "agreement" and source.event_type == "AGREEMENT_COMMITTED":
        # Keep the aggregate deal scope and version record independently
        # checked because this event's aggregate_id is the deal UUID.
        version_id_value = source_payload.get("agreement_version_id")
        try:
            version_id = uuid.UUID(version_id_value) if isinstance(version_id_value, str) else None
        except ValueError:
            version_id = None
        agreement = db.get(AgreementVersion, version_id) if version_id is not None else None
        if (
            agreement is not None
            and source.aggregate_id == subscription.deal_id
            and agreement.deal_id == subscription.deal_id
            and source_payload.get("deal_id") == str(subscription.deal_id)
            and source_payload.get("agreement_version_id") == str(agreement.id)
        ):
            notification_kind = "AGREEMENT_COMMITTED"
    elif (
        source.aggregate_type == "deal"
        and source.event_type == "DEAL_NOTIFICATION"
        and source_payload.get("kind") == "DEAL_COMPLETED"
        and source.aggregate_id == subscription.deal_id
        and source_payload.get("deal_id") == str(subscription.deal_id)
    ):
        notification_kind = "DEAL_COMPLETED"
    elif (
        source.aggregate_type == "deal"
        and source.event_type == "DEAL_NOTIFICATION"
        and source_payload.get("kind") == "PAYMENT_STATE_CHANGED"
        and source.aggregate_id == subscription.deal_id
        and source_payload.get("deal_id") == str(subscription.deal_id)
    ):
        try:
            payment_id = uuid.UUID(source_payload.get("record_id", ""))
        except (TypeError, ValueError):
            payment_id = None
        intent = db.get(PaymentIntent, payment_id) if payment_id is not None else None
        if intent is not None and intent.deal_id == subscription.deal_id:
            notification_kind = "PAYMENT_STATE_CHANGED"

    if notification_kind is None:
        delivery.status = "FAILED"
        delivery.last_error = "source_mismatch"
        db.commit()
        return

    installation = db.scalar(
        select(SlackInstallation).where(
            SlackInstallation.id == subscription.installation_id,
            SlackInstallation.organization_id == subscription.organization_id,
            SlackInstallation.workspace_id == subscription.workspace_id,
            SlackInstallation.status == "CONNECTED",
        )
    )
    if installation is None or not installation.encrypted_bot_token:
        delivery.status = "FAILED"
        delivery.last_error = "installation_inactive"
        db.commit()
        return

    link = db.scalar(
        select(SlackUserLink).where(
            SlackUserLink.installation_id == subscription.installation_id,
            SlackUserLink.organization_id == subscription.organization_id,
            SlackUserLink.workspace_id == subscription.workspace_id,
            SlackUserLink.slack_user_id == subscription.slack_user_id,
            SlackUserLink.user_id == subscription.user_id,
        )
    )
    deal = (
        _authorized_subscription_deal(
            db,
            installation,
            link,
            str(subscription.deal_id),
            permission="payments.read" if notification_kind == "PAYMENT_STATE_CHANGED" else "deal.read_assigned",
        )
        if link is not None
        else None
    )
    if deal is None:
        # Revoked membership, deal access, or identity mapping suppresses a
        # queued update instead of revealing whether the deal changed.
        delivery.status = "FAILED"
        delivery.last_error = "authorization_revoked"
        db.commit()
        return

    token = _cipher().decrypt(installation.encrypted_bot_token)
    await _provider_call(
        api.post_ephemeral,
        token,
        channel=subscription.channel_id,
        user=subscription.slack_user_id,
        thread_ts=subscription.thread_ts,
        text=(
            (
                "A SyncAlly agreement was committed for a deal you follow. "
                f"Mention `@SyncAlly status {subscription.deal_id}` or "
                f"`@SyncAlly payments {subscription.deal_id}` in this thread "
                "to check its current state."
            )
            if notification_kind == "AGREEMENT_COMMITTED"
            else (
                (
                    "A payment update is available for a deal you follow. "
                    f"Mention @SyncAlly payments {subscription.deal_id} in this thread to view the current status."
                )
                if notification_kind == "PAYMENT_STATE_CHANGED"
                else (
                    "A SyncAlly deal you follow has been completed. "
                    f"Mention `@SyncAlly status {subscription.deal_id}` in this thread "
                    "to check its current status."
                )
            )
        ),
    )
    delivery.status = "DELIVERED"
    delivery.last_error = None
    delivery.delivered_at = datetime.now(UTC)
    try:
        db.commit()
    except Exception as error:
        raise SlackWebAPIError("delivery_uncertain", uncertain=True) from error


def _take_event(db: Session, now: datetime) -> uuid.UUID | None:
    prune_slack_records(db, now)
    db.execute(
        update(SlackEvent)
        .where(
            SlackEvent.status == "PROCESSING",
            SlackEvent.available_at <= now,
        )
        .values(status="FAILED", last_error="delivery_uncertain")
    )
    db.execute(
        update(SlackEvent)
        .where(
            SlackEvent.available_at <= now,
            SlackEvent.status == "PENDING",
            SlackEvent.attempts >= _MAX_ATTEMPTS,
        )
        .values(status="FAILED", last_error="attempts_exhausted")
    )
    db.commit()
    event = db.scalar(
        select(SlackEvent)
        .where(
            SlackEvent.available_at <= now,
            SlackEvent.status == "PENDING",
            SlackEvent.attempts < _MAX_ATTEMPTS,
        )
        .order_by(SlackEvent.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if event is None:
        return None
    event.status = "PROCESSING"
    event.attempts += 1
    event.available_at = now + timedelta(seconds=_LEASE_SECONDS)
    db.commit()
    return event.id


def _link_code(event: SlackEvent, installation: SlackInstallation, db: Session) -> str:
    challenge = db.scalar(
        select(SlackLinkChallenge).where(SlackLinkChallenge.event_id == event.event_id)
    )
    if challenge is not None and challenge.consumed_at is not None:
        return ""
    if challenge is not None and as_utc(challenge.expires_at) > datetime.now(UTC):
        return _cipher().decrypt(challenge.encrypted_code)
    if challenge is not None:
        db.delete(challenge)
        db.flush()
    code = secrets.token_urlsafe(12).upper()
    now = datetime.now(UTC)
    db.add(
        SlackLinkChallenge(
            id=uuid.uuid4(),
            event_id=event.event_id,
            installation_id=installation.id,
            organization_id=installation.organization_id,
            workspace_id=installation.workspace_id,
            slack_user_id=event.slack_user_id,
            code_hash=hashlib.sha256(code.encode("ascii")).hexdigest(),
            encrypted_code=_cipher().encrypt(code),
            expires_at=now + timedelta(minutes=10),
            attempts=0,
        )
    )
    db.commit()
    return code


async def _deliver(db: Session, event_id: uuid.UUID, api: SlackWebAPI) -> None:
    event = db.get(SlackEvent, event_id)
    if event is None:
        return
    installation = db.scalar(
        select(SlackInstallation).where(
            SlackInstallation.id == event.installation_id,
            SlackInstallation.status == "CONNECTED",
            SlackInstallation.workspace_id == event.workspace_id,
        )
    )
    if installation is None or not installation.encrypted_bot_token:
        event.status = "FAILED"
        event.last_error = "installation_inactive"
        db.commit()
        return
    token = _cipher().decrypt(installation.encrypted_bot_token)

    if event.command == "LINK":
        existing = db.scalar(
            select(SlackUserLink).where(
                SlackUserLink.installation_id == installation.id,
                SlackUserLink.slack_user_id == event.slack_user_id,
            )
        )
        if existing is not None:
            await _provider_call(api.post_message,
                token,
                channel=event.channel_id,
                thread_ts=event.thread_ts,
                text="Your Slack account is already linked to SyncAlly. You can ask for `status <deal-id> ` followed by an exact deal ID.",
            )
        else:
            code = _link_code(event, installation, db)
            if not code:
                await _provider_call(api.post_message,
                    token,
                    channel=event.channel_id,
                    thread_ts=event.thread_ts,
                    text="Your Slack account is linked to SyncAlly. You can ask for `status <deal-id>` followed by an exact deal ID.",
                )
                event.status = "DELIVERED"
                event.delivered_at = datetime.now(UTC)
                db.commit()
                return
            await _provider_call(api.post_ephemeral,
                token,
                channel=event.channel_id,
                user=event.slack_user_id,
                text=(
                    f"Your temporary SyncAlly link code is `{code}` (valid for 10 minutes). "
                    "Sign in to SyncAlly, open your organization's Integrations tab, and enter this code. "
                    "The code is private to you and grants no additional deal permissions."
                ),
            )
    elif event.command == "STATUS" and event.deal_id is not None:
        link = db.scalar(
            select(SlackUserLink).where(
                SlackUserLink.installation_id == installation.id,
                SlackUserLink.slack_user_id == event.slack_user_id,
                SlackUserLink.organization_id == installation.organization_id,
                SlackUserLink.workspace_id == installation.workspace_id,
            )
        )
        if link is None:
            text = "Link your SyncAlly account first: mention `@SyncAlly link` and follow the private instructions."
        else:
            actor = resolve_actor(db, link.user_id)
            if actor is None or installation.organization_id not in actor.organization_ids:
                text = "I couldn't find an authorized deal with that ID."
            else:
                try:
                    deal = get_deal(actor, uuid.UUID(event.deal_id), SqlAlchemyDealRepository(db))
                except (DealNotFound, ValueError):
                    text = "I couldn't find an authorized deal with that ID."
                else:
                    text = f"Deal status: {deal.status.value}."
        await _provider_call(api.post_ephemeral,
            token,
            channel=event.channel_id,
            user=event.slack_user_id,
            thread_ts=event.thread_ts,
            text=text,
        )
    elif event.command == "PAYMENTS" and event.deal_id is not None:
        link = db.scalar(
            select(SlackUserLink).where(
                SlackUserLink.installation_id == installation.id,
                SlackUserLink.slack_user_id == event.slack_user_id,
                SlackUserLink.organization_id == installation.organization_id,
                SlackUserLink.workspace_id == installation.workspace_id,
            )
        )
        if link is None:
            text = "Link your SyncAlly account first: mention `@SyncAlly link` and follow the private instructions."
        else:
            actor = resolve_actor(db, link.user_id)
            if actor is None or installation.organization_id not in actor.organization_ids:
                text = "I couldn't find authorized payment information for that deal."
            else:
                try:
                    deal_id_value = uuid.UUID(event.deal_id)
                    deal = get_deal(actor, deal_id_value, SqlAlchemyDealRepository(db))
                    require_deal_action(actor, deal, installation.organization_id, "payments.read")
                    payments = list_current_payment_statuses(
                        actor,
                        deal_id_value,
                        SqlAlchemyDealRepository(db),
                        SqlAlchemyAgreementRepository(db),
                        SqlAlchemyPaymentIntentRepository(db),
                    )
                except (DealNotFound, HTTPException):
                    text = "I couldn't find authorized payment information for that deal."
                else:
                    text = _payment_summary_text(payments)
        await _provider_call(api.post_ephemeral,
            token,
            channel=event.channel_id,
            user=event.slack_user_id,
            thread_ts=event.thread_ts,
            text=text,
        )
    elif event.command in {"FOLLOW", "UNFOLLOW"} and event.deal_id is not None:
        link = db.scalar(
            select(SlackUserLink).where(
                SlackUserLink.installation_id == installation.id,
                SlackUserLink.slack_user_id == event.slack_user_id,
                SlackUserLink.organization_id == installation.organization_id,
                SlackUserLink.workspace_id == installation.workspace_id,
            )
        )
        if link is None:
            text = "Link your SyncAlly account first: mention `@SyncAlly link` and follow the private instructions."
        elif event.command == "FOLLOW":
            deal = _authorized_subscription_deal(
                db, installation, link, event.deal_id
            )
            if deal is None:
                text = _PRIVATE_DEAL_DENIAL
            else:
                subscription = db.scalar(
                    select(SlackDealSubscription).where(
                        SlackDealSubscription.installation_id == installation.id,
                        SlackDealSubscription.user_id == link.user_id,
                        SlackDealSubscription.deal_id == deal.id,
                        SlackDealSubscription.channel_id == event.channel_id,
                        SlackDealSubscription.thread_ts == event.thread_ts,
                    )
                )
                if subscription is None:
                    now = datetime.now(UTC)
                    subscription = SlackDealSubscription(
                        id=uuid.uuid4(),
                        installation_id=installation.id,
                        organization_id=installation.organization_id,
                        workspace_id=installation.workspace_id,
                        slack_user_id=event.slack_user_id,
                        user_id=link.user_id,
                        deal_id=deal.id,
                        channel_id=event.channel_id,
                        thread_ts=event.thread_ts,
                        created_at=now,
                    )
                    db.add(subscription)
                    _audit_subscription_change(
                        db,
                        subscription_id=subscription.id,
                        deal_id=deal.id,
                        installation=installation,
                        user_id=link.user_id,
                        event_type="integration.deal_followed",
                        now=now,
                    )
                    try:
                        db.commit()
                        text = (
                            "You're following agreement, completion, and payment updates for this deal in this thread. "
                            f"Mention `@SyncAlly unfollow {deal.id}` to stop."
                        )
                    except IntegrityError:
                        db.rollback()
                        subscription = db.scalar(
                            select(SlackDealSubscription).where(
                                SlackDealSubscription.installation_id == installation.id,
                                SlackDealSubscription.user_id == link.user_id,
                                SlackDealSubscription.deal_id == deal.id,
                                SlackDealSubscription.channel_id == event.channel_id,
                                SlackDealSubscription.thread_ts == event.thread_ts,
                            )
                        )
                        if subscription is None:
                            raise
                        text = (
                            "You're already following agreement, completion, and payment updates for this deal in this thread. "
                            f"Mention `@SyncAlly unfollow {deal.id}` to stop."
                        )
                else:
                    text = (
                        "You're already following agreement, completion, and payment updates for this deal in this thread. "
                        f"Mention `@SyncAlly unfollow {deal.id}` to stop."
                    )
        else:
            subscription = db.scalar(
                select(SlackDealSubscription).where(
                    SlackDealSubscription.installation_id == installation.id,
                    SlackDealSubscription.user_id == link.user_id,
                    SlackDealSubscription.deal_id == uuid.UUID(event.deal_id),
                    SlackDealSubscription.channel_id == event.channel_id,
                    SlackDealSubscription.thread_ts == event.thread_ts,
                )
            )
            if subscription is None:
                text = "You're not following this deal in this thread."
            else:
                now = datetime.now(UTC)
                db.execute(
                    delete(SlackNotificationDelivery).where(
                        SlackNotificationDelivery.subscription_id == subscription.id
                    )
                )
                db.delete(subscription)
                _audit_subscription_change(
                    db,
                    subscription_id=subscription.id,
                    deal_id=subscription.deal_id,
                    installation=installation,
                    user_id=link.user_id,
                    event_type="integration.deal_unfollowed",
                    now=now,
                )
                db.commit()
                text = "You're no longer following agreement, completion, and payment updates for this deal in this thread."
        await _provider_call(
            api.post_ephemeral,
            token,
            channel=event.channel_id,
            user=event.slack_user_id,
            thread_ts=event.thread_ts,
            text=text,
        )
    else:
        await _provider_call(api.post_message,
            token,
            channel=event.channel_id,
            thread_ts=event.thread_ts,
            text=(
                "Use `@SyncAlly link` to connect your account, `@SyncAlly status <deal-id>` "
                "for deal status, `@SyncAlly payments <deal-id>` for payment status, "
                "or `@SyncAlly follow <deal-id>` to get agreement, completion, and payment updates in this thread. "
                "Use an exact deal ID."
            ),
        )
    event.status = "DELIVERED"
    event.last_error = None
    event.delivered_at = datetime.now(UTC)
    try:
        db.commit()
    except Exception as error:
        raise SlackWebAPIError("delivery_uncertain", uncertain=True) from error


async def process_one(
    session_factory: Callable[[], Session] = SessionLocal,
    api: SlackWebAPI | None = None,
    now: datetime | None = None,
) -> bool:
    current_time = now or datetime.now(UTC)
    session = session_factory()
    try:
        # Handle user controls such as UNFOLLOW before attempting any queued
        # notification, so an opt-out can suppress pending deliveries.
        event_id = _take_event(session, current_time)
        delivery_id = (
            None if event_id is not None else _take_notification_delivery(session, current_time)
        )
        if delivery_id is None and event_id is None:
            return False
    finally:
        session.close()

    db = session_factory()
    try:
        if delivery_id is not None:
            try:
                await _deliver_notification(db, delivery_id, api or SlackWebAPI())
            except SlackWebAPIError as error:
                db.rollback()
                db.close()
                failure_kind = _safe_failure_kind(error)
                _record_notification_failure(
                    session_factory,
                    delivery_id,
                    failure_kind="delivery_uncertain" if error.uncertain else failure_kind,
                    retry_after=error.retry_after,
                    uncertain=error.uncertain,
                    terminal=failure_kind in {
                        "thread_not_supported", "thread_not_found", "message_not_found"
                    },
                )
            except Exception as error:
                db.rollback()
                db.close()
                _record_notification_failure(
                    session_factory,
                    delivery_id,
                    failure_kind=_safe_failure_kind(error),
                    uncertain=isinstance(error, SQLAlchemyError),
                )
            return True

        assert event_id is not None
        event = db.get(SlackEvent, event_id)
        if event is None:
            return True
        try:
            await _deliver(db, event_id, api or SlackWebAPI())
        except SlackWebAPIError as error:
            db.rollback()
            db.close()
            failure_kind = _safe_failure_kind(error)
            _record_failure(
                session_factory,
                event_id,
                failure_kind="delivery_uncertain" if error.uncertain else failure_kind,
                retry_after=error.retry_after,
                uncertain=error.uncertain,
                terminal=failure_kind in {"thread_not_supported", "thread_not_found", "message_not_found"},
            )
        except Exception as error:
            db.rollback()
            db.close()
            _record_failure(
                session_factory,
                event_id,
                failure_kind=_safe_failure_kind(error),
            )
        return True
    finally:
        db.close()


def run_forever() -> None:
    configure_logging()
    logger.info("Slack Events worker started")
    while True:
        try:
            processed = False
            for _ in range(settings.slack_events_batch_size):
                import asyncio

                if not asyncio.run(process_one()):
                    break
                processed = True
            if not processed:
                time.sleep(settings.slack_events_poll_interval_seconds)
        except Exception:
            logger.error("Slack Events worker iteration failed")
            time.sleep(settings.slack_events_poll_interval_seconds)


def main() -> None:
    run_forever()


if __name__ == "__main__":
    main()
