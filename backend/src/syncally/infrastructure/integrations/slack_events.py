"""Slack Events API verification and bounded Web API calls."""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass

import httpx

SLACK_EVENTS_MAX_AGE_SECONDS = 300


class SlackEventVerificationError(ValueError):
    """The request is not a fresh, correctly signed Slack request."""


class SlackWebAPIError(RuntimeError):
    """A Slack Web API operation failed without exposing provider response bodies."""

    def __init__(self, code: str, retry_after: float | None = None, *, uncertain: bool = False) -> None:
        super().__init__(code)
        self.code = code
        self.retry_after = retry_after
        self.uncertain = uncertain


def verify_slack_request(
    raw_body: bytes,
    *,
    timestamp: str | None,
    signature: str | None,
    signing_secret: str,
    now: float | None = None,
) -> None:
    """Verify Slack's raw-body HMAC and five-minute replay window."""
    if not timestamp or len(timestamp) > 12 or not timestamp.isascii() or not timestamp.isdigit() or not signature:
        raise SlackEventVerificationError("missing_signature")
    request_time = int(timestamp)
    current_time = time.time() if now is None else now
    if abs(current_time - request_time) > SLACK_EVENTS_MAX_AGE_SECONDS:
        raise SlackEventVerificationError("stale_signature")
    base = b"v0:" + timestamp.encode("ascii") + b":" + raw_body
    expected = "v0=" + hmac.new(
        signing_secret.encode("utf-8"), base, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise SlackEventVerificationError("invalid_signature")


@dataclass(frozen=True, slots=True)
class SlackWebAPI:
    """Minimal adapter for thread replies and private pairing-code delivery."""

    transport: httpx.AsyncBaseTransport | None = None

    async def post_message(
        self, token: str, *, channel: str, text: str, thread_ts: str
    ) -> None:
        await self._post(
            "chat.postMessage",
            token,
            {
                "channel": channel,
                "text": text,
                "thread_ts": thread_ts,
            },
        )

    async def post_ephemeral(
        self,
        token: str,
        *,
        channel: str,
        user: str,
        text: str,
        thread_ts: str | None = None,
    ) -> None:
        payload = {"channel": channel, "user": user, "text": text}
        if thread_ts is not None:
            payload["thread_ts"] = thread_ts
        await self._post(
            "chat.postEphemeral",
            token,
            payload,
        )

    async def _post(self, method: str, token: str, payload: dict[str, str]) -> None:
        try:
            async with httpx.AsyncClient(
                transport=self.transport,
                follow_redirects=False,
                timeout=httpx.Timeout(8.0),
            ) as client:
                response = await client.post(
                    f"https://slack.com/api/{method}",
                    headers={"Authorization": f"Bearer {token}"},
                    json=payload,
                )
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", "1")
                    try:
                        delay = min(max(float(retry_after), 1.0), 3600.0)
                    except ValueError:
                        delay = 1.0
                    raise SlackWebAPIError("ratelimited", delay)
                if response.status_code >= 500:
                    raise SlackWebAPIError("delivery_uncertain", uncertain=True)
                response.raise_for_status()
                try:
                    result = response.json()
                except ValueError as error:
                    raise SlackWebAPIError("delivery_uncertain", uncertain=True) from error
        except SlackWebAPIError:
            raise
        except httpx.TimeoutException as error:
            raise SlackWebAPIError("delivery_uncertain", uncertain=True) from error
        except httpx.TransportError as error:
            raise SlackWebAPIError("delivery_uncertain", uncertain=True) from error
        except httpx.HTTPStatusError as error:
            raise SlackWebAPIError("provider_http_error") from error
        except (httpx.HTTPError, ValueError) as error:
            raise SlackWebAPIError("provider_error") from error
        if not isinstance(result, dict) or result.get("ok") is not True:
            error_code = result.get("error", "provider_error") if isinstance(result, dict) else "provider_error"
            safe_code = str(error_code)[:64]
            # Slack's HTTP-200 error envelope is not enough to establish that
            # the operation had no side effect. Only explicit rate limiting
            # is safe to retry; treat every other response as ambiguous unless
            # Slack later documents a narrower, reliable classification.
            raise SlackWebAPIError(
                safe_code,
                retry_after=1.0 if safe_code == "ratelimited" else None,
                uncertain=safe_code != "ratelimited",
            )
