"""Organization-scoped Slack connection lifecycle."""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
from syncally.application.identity import ActorContext
from syncally.config import settings
from syncally.domain.organizations.organization import OrganizationCapability
from syncally.infrastructure.database import get_db
from syncally.infrastructure.identity import verify_member_capability
from syncally.infrastructure.integrations.slack import (
    SLACK_BOT_SCOPES,
    SlackIntegrationError,
    SlackOAuthClient,
    SlackTokenCipher,
)
from syncally.infrastructure.models import (
    AuditEvent,
    SlackInstallation,
    SlackOAuthState,
)
from syncally.infrastructure.repositories._timestamps import as_utc

router = APIRouter(tags=["integrations"])
OAUTH_STATE_TTL = timedelta(minutes=10)
_FRONTEND_RETURN = "/#/settings/organizations?integration="
_LOGGER = logging.getLogger(__name__)


class SlackConnectionResponse(BaseModel):
    configured: bool
    connected: bool
    workspace_id: str | None = None
    workspace_name: str | None = None
    granted_scopes: list[str] = Field(default_factory=list)
    connected_at: datetime | None = None
    messaging_enabled: bool = False


def _configured() -> bool:
    return bool(
        settings.slack_client_id.strip()
        and settings.slack_client_secret.get_secret_value()
        and settings.slack_redirect_uri.strip()
        and settings.integration_token_encryption_key.get_secret_value()
    )


def _oauth_client() -> SlackOAuthClient:
    return SlackOAuthClient(
        client_id=settings.slack_client_id,
        client_secret=settings.slack_client_secret.get_secret_value(),
        redirect_uri=settings.slack_redirect_uri,
    )


def _cipher() -> SlackTokenCipher:
    return SlackTokenCipher(settings.integration_token_encryption_key.get_secret_value())


async def _revoke_unstored_token(
    db: Session, *, token: str, workspace_id: str
) -> None:
    """Best-effort cleanup when Slack issued a token we cannot persist."""
    try:
        already_mapped = db.scalar(
            select(SlackInstallation.id).where(
                SlackInstallation.workspace_id == workspace_id,
                SlackInstallation.status == "CONNECTED",
            )
        )
    except Exception:
        _LOGGER.warning(
            "Could not verify Slack workspace mapping before rejected-grant cleanup; skipped revocation"
        )
        return
    if already_mapped is not None:
        _LOGGER.warning(
            "Skipped revoking a rejected Slack grant because the workspace is already connected"
        )
        return
    try:
        await _oauth_client().revoke(token)
    except SlackIntegrationError:
        # Never log or return the credential. The failed install remains
        # unconnected locally, and an administrator can retry authorization.
        _LOGGER.warning("Failed to revoke a Slack token from a rejected authorization")
        return


def _audit(
    db: Session,
    *,
    installation_id: uuid.UUID,
    organization_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    event_type: str,
    workspace_id: str,
    outcome: str,
) -> None:
    db.add(
        AuditEvent(
            id=uuid.uuid4(),
            aggregate_type="slack_installation",
            aggregate_id=installation_id,
            event_type=event_type,
            actor_type="USER",
            actor_id=str(actor_user_id),
            occurred_at=datetime.now(UTC),
            payload={
                "provider": "SLACK",
                "organization_id": str(organization_id),
                "workspace_id": workspace_id,
                "outcome": outcome,
            },
        )
    )


def _return_to_settings(result: str) -> RedirectResponse:
    target = f"{settings.public_frontend_url.rstrip('/')}{_FRONTEND_RETURN}{quote(result)}"
    return RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)


def _connection_response(installation: SlackInstallation | None) -> SlackConnectionResponse:
    if installation is None or installation.status != "CONNECTED":
        return SlackConnectionResponse(configured=_configured(), connected=False)
    return SlackConnectionResponse(
        configured=_configured(),
        connected=True,
        workspace_id=installation.workspace_id,
        workspace_name=installation.workspace_name,
        granted_scopes=list(installation.granted_scopes or []),
        connected_at=installation.connected_at,
        messaging_enabled=False,
    )


@router.get(
    "/organizations/{organization_id}/integrations/slack",
    response_model=SlackConnectionResponse,
)
def get_slack_connection(
    organization_id: uuid.UUID,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> SlackConnectionResponse:
    verify_member_capability(
        db, organization_id, actor.user_id, OrganizationCapability.ADMINISTRATION
    )
    installation = db.scalar(
        select(SlackInstallation).where(
            SlackInstallation.organization_id == organization_id,
            SlackInstallation.status == "CONNECTED",
        )
    )
    return _connection_response(installation)


@router.post("/organizations/{organization_id}/integrations/slack/oauth/start")
def start_slack_oauth(
    organization_id: uuid.UUID,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    verify_member_capability(
        db, organization_id, actor.user_id, OrganizationCapability.ADMINISTRATION
    )
    if not _configured():
        raise HTTPException(status_code=503, detail="Slack connection is not configured")
    existing = db.scalar(
        select(SlackInstallation.id).where(
            SlackInstallation.organization_id == organization_id,
            SlackInstallation.status == "CONNECTED",
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="A Slack workspace is already connected")

    now = datetime.now(UTC)
    db.execute(delete(SlackOAuthState).where(or_(
        SlackOAuthState.expires_at < now,
        SlackOAuthState.consumed_at.is_not(None),
    )))
    raw_state = secrets.token_urlsafe(32)
    state_hash = hashlib.sha256(raw_state.encode("ascii")).hexdigest()
    db.add(
        SlackOAuthState(
            state_hash=state_hash,
            organization_id=organization_id,
            user_id=actor.user_id,
            created_at=now,
            expires_at=now + OAUTH_STATE_TTL,
        )
    )
    db.commit()
    return {"authorization_url": _oauth_client().authorization_url(raw_state)}


@router.get("/integrations/slack/oauth/callback", include_in_schema=False)
async def slack_oauth_callback(
    state: str | None = Query(default=None, max_length=256),
    code: str | None = Query(default=None, max_length=4096),
    error: str | None = Query(default=None, max_length=128),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if not state or not _configured():
        return _return_to_settings("failed")
    state_hash = hashlib.sha256(state.encode("utf-8")).hexdigest()
    now = datetime.now(UTC)
    saved_state = db.scalar(
        select(SlackOAuthState)
        .where(SlackOAuthState.state_hash == state_hash)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        saved_state is None
        or saved_state.consumed_at is not None
        or as_utc(saved_state.expires_at) <= now
    ):
        return _return_to_settings("failed")
    saved_state.consumed_at = now
    organization_id = saved_state.organization_id
    actor_user_id = saved_state.user_id
    db.commit()

    if error or not code:
        return _return_to_settings("cancelled")

    try:
        provider_install = await _oauth_client().exchange_code(code)
    except SlackIntegrationError:
        return _return_to_settings("failed")
    if not set(SLACK_BOT_SCOPES).issubset(provider_install.granted_scopes):
        await _revoke_unstored_token(
            db, token=provider_install.access_token, workspace_id=provider_install.workspace_id
        )
        return _return_to_settings("failed")
    try:
        encrypted_token = _cipher().encrypt(provider_install.access_token)
    except SlackIntegrationError:
        await _revoke_unstored_token(
            db, token=provider_install.access_token, workspace_id=provider_install.workspace_id
        )
        return _return_to_settings("failed")

    try:
        verify_member_capability(
            db,
            organization_id,
            actor_user_id,
            OrganizationCapability.ADMINISTRATION,
        )
        existing_org_installation = db.scalar(
            select(SlackInstallation)
            .where(SlackInstallation.organization_id == organization_id)
            .with_for_update()
        )
        other_org_installation = db.scalar(
            select(SlackInstallation.id).where(
                SlackInstallation.workspace_id == provider_install.workspace_id,
                SlackInstallation.status == "CONNECTED",
            )
        )
        if other_org_installation is not None and (
            existing_org_installation is None
            or existing_org_installation.id != other_org_installation
        ):
            db.rollback()
            return _return_to_settings("workspace_in_use")

        if existing_org_installation is not None:
            if existing_org_installation.status == "CONNECTED":
                db.rollback()
                await _revoke_unstored_token(
                    db,
                    token=provider_install.access_token,
                    workspace_id=provider_install.workspace_id,
                )
                return _return_to_settings("already_connected")
            installation = existing_org_installation
            installation.workspace_id = provider_install.workspace_id
            installation.workspace_name = provider_install.workspace_name
            installation.bot_user_id = provider_install.bot_user_id
            installation.encrypted_bot_token = encrypted_token
            installation.granted_scopes = list(provider_install.granted_scopes)
            installation.status = "CONNECTED"
            installation.connected_by_user_id = actor_user_id
            installation.connected_at = now
            installation.disconnected_at = None
        else:
            installation = SlackInstallation(
                id=uuid.uuid4(),
                organization_id=organization_id,
                workspace_id=provider_install.workspace_id,
                workspace_name=provider_install.workspace_name,
                bot_user_id=provider_install.bot_user_id,
                encrypted_bot_token=encrypted_token,
                granted_scopes=list(provider_install.granted_scopes),
                status="CONNECTED",
                connected_by_user_id=actor_user_id,
                connected_at=now,
            )
            db.add(installation)
            db.flush()

        _audit(
            db,
            installation_id=installation.id,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            event_type="integration.connected",
            workspace_id=provider_install.workspace_id,
            outcome="CONNECTED",
        )
        db.commit()
    except HTTPException:
        db.rollback()
        await _revoke_unstored_token(
            db, token=provider_install.access_token, workspace_id=provider_install.workspace_id
        )
        return _return_to_settings("authorization_changed")
    except IntegrityError:
        db.rollback()
        await _revoke_unstored_token(
            db, token=provider_install.access_token, workspace_id=provider_install.workspace_id
        )
        return _return_to_settings("workspace_in_use")
    except Exception:
        db.rollback()
        await _revoke_unstored_token(
            db, token=provider_install.access_token, workspace_id=provider_install.workspace_id
        )
        raise

    return _return_to_settings("connected")


@router.delete(
    "/organizations/{organization_id}/integrations/slack",
    response_model=SlackConnectionResponse,
)
async def disconnect_slack(
    organization_id: uuid.UUID,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> SlackConnectionResponse:
    verify_member_capability(
        db, organization_id, actor.user_id, OrganizationCapability.ADMINISTRATION
    )
    installation = db.scalar(
        select(SlackInstallation)
        .where(
            SlackInstallation.organization_id == organization_id,
            SlackInstallation.status == "CONNECTED",
        )
        .with_for_update()
    )
    if installation is None or not installation.encrypted_bot_token:
        raise HTTPException(status_code=404, detail="Slack workspace is not connected")
    try:
        token = _cipher().decrypt(installation.encrypted_bot_token)
        await _oauth_client().revoke(token)
    except SlackIntegrationError as error:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="Slack disconnection could not be confirmed. Please retry.",
        ) from error

    installation.status = "DISCONNECTED"
    installation.encrypted_bot_token = None
    installation.disconnected_at = datetime.now(UTC)
    _audit(
        db,
        installation_id=installation.id,
        organization_id=organization_id,
        actor_user_id=actor.user_id,
        event_type="integration.disconnected",
        workspace_id=installation.workspace_id,
        outcome="DISCONNECTED",
    )
    db.commit()
    return _connection_response(None)
