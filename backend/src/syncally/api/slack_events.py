"""Verified Slack event intake and explicit user-link redemption."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
from syncally.application.identity import ActorContext
from syncally.config import settings
from syncally.infrastructure.database import get_db
from syncally.infrastructure.integrations.slack_events import (
    SlackEventVerificationError,
    verify_slack_request,
)
from syncally.infrastructure.models import (
    AuditEvent,
    SlackEvent,
    SlackInstallation,
    SlackLinkChallenge,
    SlackUserLink,
    User,
)
from syncally.infrastructure.repositories._timestamps import as_utc

router = APIRouter(tags=["integrations"])
MAX_SLACK_EVENT_BODY_BYTES = 256 * 1024
_DEAL_ID = re.compile(r"^[0-9a-fA-F-]{36}$")


def _event_command(text: object, bot_user_id: str) -> tuple[str, str | None]:
    if not isinstance(text, str) or len(text) > 20_000:
        return "HELP", None
    without_mentions = re.sub(r"<@[A-Z0-9]+>", " ", text, flags=re.IGNORECASE).strip()
    parts = without_mentions.split()
    if len(parts) == 1 and parts[0].casefold() == "link":
        return "LINK", None
    if len(parts) == 1 and parts[0].casefold() == "status":
        return "STATUS", None
    if len(parts) == 1 and parts[0].casefold() == "payments":
        return "PAYMENTS", None
    if (
        len(parts) == 3
        and parts[0].casefold() == "start"
        and parts[1].casefold() in {"buyer", "seller"}
        and _DEAL_ID.fullmatch(parts[2])
    ):
        try:
            return f"START_{parts[1].upper()}", str(uuid.UUID(parts[2]))
        except ValueError:
            pass
    if (
        len(parts) == 2
        and parts[0].casefold() in {"follow", "unfollow"}
        and _DEAL_ID.fullmatch(parts[1])
    ):
        try:
            return parts[0].upper(), str(uuid.UUID(parts[1]))
        except ValueError:
            pass
    if (
        len(parts) == 2
        and parts[0].casefold() == "status"
        and _DEAL_ID.fullmatch(parts[1])
    ):
        try:
            return "STATUS", str(uuid.UUID(parts[1]))
        except ValueError:
            pass
    if (
        len(parts) == 2
        and parts[0].casefold() == "payments"
        and _DEAL_ID.fullmatch(parts[1])
    ):
        try:
            return "PAYMENTS", str(uuid.UUID(parts[1]))
        except ValueError:
            pass
    return "HELP", None


@router.post("/integrations/slack/events", include_in_schema=False)
async def receive_slack_event(request: Request, db: Session = Depends(get_db)):
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
        return JSONResponse({"detail": "Unsupported content type"}, status_code=415)
    raw_body = await request.body()
    if len(raw_body) > MAX_SLACK_EVENT_BODY_BYTES:
        return JSONResponse({"detail": "Request body too large"}, status_code=413)
    signing_secret = settings.slack_signing_secret.get_secret_value()
    if not signing_secret:
        return JSONResponse({"detail": "Slack Events API is not configured"}, status_code=503)
    try:
        verify_slack_request(
            raw_body,
            timestamp=request.headers.get("x-slack-request-timestamp"),
            signature=request.headers.get("x-slack-signature"),
            signing_secret=signing_secret,
        )
    except SlackEventVerificationError:
        return JSONResponse({"detail": "Invalid Slack request"}, status_code=401)
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse({"detail": "Invalid JSON"}, status_code=400)
    if not isinstance(payload, dict):
        return JSONResponse({"detail": "Invalid Slack event"}, status_code=400)
    if payload.get("type") == "url_verification":
        challenge = payload.get("challenge")
        if not isinstance(challenge, str) or len(challenge) > 512:
            return JSONResponse({"detail": "Invalid challenge"}, status_code=400)
        return {"challenge": challenge}
    if payload.get("type") != "event_callback":
        return {"ok": True}

    event_id = payload.get("event_id")
    workspace_id = payload.get("team_id")
    event = payload.get("event")
    if (
        not isinstance(event_id, str) or not event_id or len(event_id) > 128
        or not isinstance(workspace_id, str) or not workspace_id or len(workspace_id) > 64
        or not isinstance(event, dict) or event.get("type") != "app_mention"
    ):
        return {"ok": True}
    user_id = event.get("user")
    channel_id = event.get("channel")
    message_ts = event.get("ts")
    if (
        not isinstance(user_id, str) or not user_id or len(user_id) > 64
        or not isinstance(channel_id, str) or not channel_id or len(channel_id) > 64
        or not isinstance(message_ts, str) or not message_ts or len(message_ts) > 32
        or event.get("bot_id") or event.get("subtype")
    ):
        return {"ok": True}

    installation = db.scalar(
        select(SlackInstallation).where(
            SlackInstallation.workspace_id == workspace_id,
            SlackInstallation.status == "CONNECTED",
        )
    )
    if installation is None or user_id == installation.bot_user_id:
        return {"ok": True}
    command, deal_id = _event_command(event.get("text"), installation.bot_user_id)
    db.add(
        SlackEvent(
            id=uuid.uuid4(),
            event_id=event_id,
            installation_id=installation.id,
            workspace_id=workspace_id,
            slack_user_id=user_id,
            channel_id=channel_id,
            message_ts=message_ts,
            thread_ts=event.get("thread_ts") or message_ts,
            command=command,
            deal_id=deal_id,
            status="PENDING",
            attempts=0,
            available_at=datetime.now(UTC),
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Only a confirmed event_id collision is a safe Slack retry to ACK.
        # Unexpected FK/constraint failures must surface as 5xx so Slack retries.
        duplicate = db.scalar(select(SlackEvent.id).where(SlackEvent.event_id == event_id))
        if duplicate is None:
            raise
    return {"ok": True}


class SlackLinkRequest(BaseModel):
    code: str = Field(min_length=8, max_length=64)


class SlackLinkResponse(BaseModel):
    linked: bool


@router.post(
    "/integrations/slack/link",
    response_model=SlackLinkResponse,
    status_code=status.HTTP_200_OK,
)
def redeem_slack_link(
    payload: SlackLinkRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> SlackLinkResponse:
    code = payload.code.strip().upper()
    if re.fullmatch(r"[A-Z0-9_-]{8,64}", code) is None:
        raise HTTPException(status_code=400, detail="Slack link code is invalid or expired")
    code_hash = hashlib.sha256(code.encode("ascii")).hexdigest()
    now = datetime.now(UTC)
    challenge = db.scalar(
        select(SlackLinkChallenge)
        .where(SlackLinkChallenge.code_hash == code_hash)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if challenge is None or as_utc(challenge.expires_at) <= now:
        raise HTTPException(status_code=400, detail="Slack link code is invalid or expired")
    installation = db.scalar(
        select(SlackInstallation).where(
            SlackInstallation.id == challenge.installation_id,
            SlackInstallation.workspace_id == challenge.workspace_id,
            SlackInstallation.organization_id == challenge.organization_id,
            SlackInstallation.status == "CONNECTED",
        )
    )
    user = db.scalar(select(User).where(User.id == actor.user_id, User.status == "ACTIVE"))
    from syncally.infrastructure.identity import resolve_actor

    current_actor = resolve_actor(db, actor.user_id)
    if (
        installation is None
        or user is None
        or current_actor is None
        or challenge.organization_id not in current_actor.organization_ids
    ):
        db.rollback()
        raise HTTPException(status_code=403, detail="Active organization membership required")

    if challenge.consumed_at is not None:
        prior_link = db.scalar(
            select(SlackUserLink).where(
                SlackUserLink.installation_id == challenge.installation_id,
                SlackUserLink.slack_user_id == challenge.slack_user_id,
                SlackUserLink.user_id == actor.user_id,
            )
        )
        if prior_link is not None:
            return SlackLinkResponse(linked=True)
        raise HTTPException(status_code=400, detail="Slack link code is invalid or expired")

    existing_slack = db.scalar(
        select(SlackUserLink).where(
            SlackUserLink.installation_id == challenge.installation_id,
            SlackUserLink.slack_user_id == challenge.slack_user_id,
        )
    )
    existing_user = db.scalar(
        select(SlackUserLink).where(
            SlackUserLink.installation_id == challenge.installation_id,
            SlackUserLink.user_id == actor.user_id,
        )
    )
    if existing_slack is not None or existing_user is not None:
        if (
            existing_slack is not None
            and existing_slack.user_id == actor.user_id
            and existing_user is not None
            and existing_user.slack_user_id == challenge.slack_user_id
        ):
            challenge.consumed_at = now
            challenge.encrypted_code = None
            db.commit()
            return SlackLinkResponse(linked=True)
        raise HTTPException(status_code=409, detail="Slack identity is already linked")

    challenge.consumed_at = now
    challenge.encrypted_code = None
    db.add(
        SlackUserLink(
            id=uuid.uuid4(),
            installation_id=challenge.installation_id,
            organization_id=challenge.organization_id,
            workspace_id=challenge.workspace_id,
            slack_user_id=challenge.slack_user_id,
            user_id=actor.user_id,
            created_at=now,
        )
    )
    db.add(
        AuditEvent(
            id=uuid.uuid4(),
            aggregate_type="slack_user_link",
            aggregate_id=challenge.id,
            event_type="integration.user_linked",
            actor_type="USER",
            actor_id=str(actor.user_id),
            occurred_at=now,
            payload={
                "provider": "SLACK",
                "organization_id": str(challenge.organization_id),
                "workspace_id": challenge.workspace_id,
                "slack_user_id": challenge.slack_user_id,
                "outcome": "LINKED",
            },
        )
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Slack identity is already linked") from error
    return SlackLinkResponse(linked=True)
