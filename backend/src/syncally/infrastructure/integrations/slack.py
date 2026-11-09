"""Slack OAuth adapter and encrypted credential handling."""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken

SLACK_AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
SLACK_ACCESS_URL = "https://slack.com/api/oauth.v2.access"
SLACK_REVOKE_URL = "https://slack.com/api/auth.revoke"
SLACK_BOT_SCOPES = ("app_mentions:read", "chat:write")


class SlackIntegrationError(Exception):
    """A provider failure that is safe to map to a generic client error."""


@dataclass(frozen=True, slots=True)
class SlackOAuthResult:
    workspace_id: str
    workspace_name: str
    bot_user_id: str
    access_token: str = field(repr=False)
    granted_scopes: tuple[str, ...]


class SlackTokenCipher:
    """Encrypt/decrypt Slack tokens with a separately managed Fernet key."""

    def __init__(self, key: str) -> None:
        try:
            self._fernet = Fernet(key.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as error:
            raise SlackIntegrationError("Integration token encryption is not configured") from error

    def encrypt(self, token: str) -> str:
        return self._fernet.encrypt(token.encode("utf-8")).decode("ascii")

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError, UnicodeEncodeError) as error:
            raise SlackIntegrationError("Stored integration credential cannot be read") from error


class SlackOAuthClient:
    """Small provider adapter for Slack installation and token revocation."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._transport = transport

    def authorization_url(self, state: str) -> str:
        query = urlencode({
            "client_id": self._client_id,
            "scope": ",".join(SLACK_BOT_SCOPES),
            "redirect_uri": self._redirect_uri,
            "state": state,
        })
        return f"{SLACK_AUTHORIZE_URL}?{query}"

    async def exchange_code(self, code: str) -> SlackOAuthResult:
        try:
            async with httpx.AsyncClient(
                transport=self._transport,
                follow_redirects=False,
                timeout=httpx.Timeout(10.0),
            ) as client:
                response = await client.post(
                    SLACK_ACCESS_URL,
                    data={
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "code": code,
                        "redirect_uri": self._redirect_uri,
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise SlackIntegrationError("Slack authorization could not be completed") from error

        if not isinstance(payload, dict):
            raise SlackIntegrationError("Slack returned an invalid authorization response")
        team = payload.get("team")
        token = payload.get("access_token") if isinstance(payload, dict) else None
        bot_user_id = payload.get("bot_user_id") if isinstance(payload, dict) else None
        scopes_raw = payload.get("scope") if isinstance(payload, dict) else None
        if (
            payload.get("ok") is not True
            or not isinstance(team, dict)
            or not isinstance(team.get("id"), str)
            or not team.get("id")
            or not isinstance(team.get("name"), str)
            or not team.get("name")
            or not isinstance(bot_user_id, str)
            or not bot_user_id
            or not isinstance(token, str)
            or not token
            or not isinstance(scopes_raw, str)
        ):
            raise SlackIntegrationError("Slack returned an invalid authorization response")

        granted = tuple(sorted(scope.strip() for scope in scopes_raw.split(",") if scope.strip()))
        return SlackOAuthResult(
            workspace_id=team["id"],
            workspace_name=team["name"],
            bot_user_id=bot_user_id,
            access_token=token,
            granted_scopes=granted,
        )

    async def revoke(self, token: str) -> None:
        try:
            async with httpx.AsyncClient(
                transport=self._transport,
                follow_redirects=False,
                timeout=httpx.Timeout(10.0),
            ) as client:
                response = await client.post(
                    SLACK_REVOKE_URL,
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise SlackIntegrationError("Slack could not confirm app disconnection") from error
        if (
            not isinstance(payload, dict)
            or payload.get("ok") is not True
            or payload.get("revoked") is not True
        ):
            raise SlackIntegrationError("Slack could not confirm app disconnection")
