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
from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError
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
    SlackEvent,
    SlackInstallation,
    SlackLinkChallenge,
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
    db.commit()
    return expired_challenges, old_terminal_events


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
    else:
        await _provider_call(api.post_message,
            token,
            channel=event.channel_id,
            thread_ts=event.thread_ts,
            text="Use `@SyncAlly link` to connect your account, `@SyncAlly status <deal-id>` for deal status, or `@SyncAlly payments <deal-id>` for payment status. Use an exact deal ID.",
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
    session = session_factory()
    try:
        event_id = _take_event(session, now or datetime.now(UTC))
        if event_id is None:
            return False
    finally:
        session.close()

    db = session_factory()
    try:
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
