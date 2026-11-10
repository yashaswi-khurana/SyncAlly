"""Focused tests for verified Slack events, account linking, and deal replies."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import httpx
from cryptography.fernet import Fernet
from fastapi import HTTPException
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from starlette.requests import Request
from starlette.responses import JSONResponse

from syncally.api import slack_events
from syncally.application.identity import ActorContext
from syncally.application.payments import PaymentStatusRecord
from syncally.domain.deals.deal import DealStatus
from syncally.domain.shared.money import Money
from syncally.infrastructure.integrations.slack import SlackTokenCipher
from syncally.infrastructure.integrations.slack_events import (
    SlackEventVerificationError,
    SlackWebAPI,
    SlackWebAPIError,
    verify_slack_request,
)
from syncally.infrastructure.models import (
    AgreementVersion,
    AuditEvent,
    Base,
    Deal,
    Organization,
    OrganizationMember,
    OutboxEvent,
    SlackDealSubscription,
    SlackEvent,
    SlackInstallation,
    SlackLinkChallenge,
    SlackNotificationDelivery,
    SlackUserLink,
    User,
)

SIGNING_SECRET = "test-signing-secret"
FERNET_KEY = Fernet.generate_key().decode("ascii")


class SlackEventCommandTests(unittest.TestCase):
    def test_payment_command_requires_exact_verb_and_deal_id(self) -> None:
        self.assertEqual(
            slack_events._event_command("<@BBOT> payments 11111111-1111-1111-1111-111111111111", "BBOT"),
            ("PAYMENTS", "11111111-1111-1111-1111-111111111111"),
        )
        self.assertEqual(
            slack_events._event_command("<@BBOT> payments 11111111-1111-1111-1111-111111111111 extra", "BBOT"),
            ("HELP", None),
        )
        self.assertEqual(
            slack_events._event_command("<@BBOT> payment 11111111-1111-1111-1111-111111111111", "BBOT"),
            ("HELP", None),
        )

    def test_follow_commands_require_exact_deal_ids(self) -> None:
        deal_id = "11111111-1111-1111-1111-111111111111"
        for word, command in (("follow", "FOLLOW"), ("unfollow", "UNFOLLOW")):
            self.assertEqual(
                slack_events._event_command(f"<@BBOT> {word} {deal_id}", "BBOT"),
                (command, deal_id),
            )
            self.assertEqual(
                slack_events._event_command(f"<@BBOT> {word} {deal_id} extra", "BBOT"),
                ("HELP", None),
            )


def _signed_request(payload: dict[str, object], *, timestamp: int | None = None) -> Request:
    timestamp = int(time.time()) if timestamp is None else timestamp
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    timestamp_header = str(timestamp)
    base = b"v0:" + timestamp_header.encode("ascii") + b":" + body
    signature = "v0=" + hmac.new(SIGNING_SECRET.encode(), base, hashlib.sha256).hexdigest()
    headers = [
        (b"content-type", b"application/json"),
        (b"x-slack-request-timestamp", timestamp_header.encode("ascii")),
        (b"x-slack-signature", signature.encode("ascii")),
    ]
    sent = False

    async def receive() -> dict[str, object]:
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {"type": "http", "method": "POST", "path": "/integrations/slack/events", "headers": headers},
        receive,
    )


class SlackRequestVerificationTests(unittest.TestCase):
    def test_verifies_raw_body_signature_and_rejects_stale_or_tampered_requests(self) -> None:
        body = b'{"type":"event_callback"}'
        timestamp = "1800000000"
        signature = "v0=" + hmac.new(
            SIGNING_SECRET.encode(), b"v0:" + timestamp.encode() + b":" + body, hashlib.sha256
        ).hexdigest()

        verify_slack_request(
            body, timestamp=timestamp, signature=signature,
            signing_secret=SIGNING_SECRET, now=1_800_000_000,
        )
        with self.assertRaises(SlackEventVerificationError):
            verify_slack_request(
                body, timestamp=timestamp, signature=signature,
                signing_secret=SIGNING_SECRET, now=1_800_000_301,
            )
        with self.assertRaises(SlackEventVerificationError):
            verify_slack_request(
                body + b" ", timestamp=timestamp, signature=signature,
                signing_secret=SIGNING_SECRET, now=1_800_000_000,
            )


class SlackWebAPITests(unittest.TestCase):
    def test_thread_reply_uses_parent_timestamp(self) -> None:
        requests: list[httpx.Request] = []

        async def provider(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={"ok": True, "ts": "123.456"})

        api = SlackWebAPI(transport=httpx.MockTransport(provider))
        asyncio.run(api.post_message(
            "xoxb-test", channel="C-channel", text="Deal status: NEGOTIATING.",
            thread_ts="123.100",
        ))

        self.assertEqual(requests[0].url.path, "/api/chat.postMessage")
        self.assertEqual(requests[0].headers["authorization"], "Bearer xoxb-test")
        body = json.loads(requests[0].content)
        self.assertEqual(body["thread_ts"], "123.100")
        self.assertEqual(body["channel"], "C-channel")

    def test_private_thread_reply_targets_requesting_user(self) -> None:
        requests: list[httpx.Request] = []

        async def provider(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={"ok": True, "message_ts": "123.500"})

        api = SlackWebAPI(transport=httpx.MockTransport(provider))
        asyncio.run(api.post_ephemeral(
            "xoxb-test", channel="C-channel", user="U-requester", text="Deal status: NEGOTIATING.",
            thread_ts="123.100",
        ))

        body = json.loads(requests[0].content)
        self.assertEqual(requests[0].url.path, "/api/chat.postEphemeral")
        self.assertEqual(body["channel"], "C-channel")
        self.assertEqual(body["user"], "U-requester")
        self.assertEqual(body["thread_ts"], "123.100")

    def test_rate_limit_preserves_retry_after(self) -> None:
        async def provider(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, headers={"Retry-After": "17"})

        api = SlackWebAPI(transport=httpx.MockTransport(provider))
        with self.assertRaises(SlackWebAPIError) as raised:
            asyncio.run(api.post_message(
                "xoxb-test", channel="C-channel", text="reply", thread_ts="1.2",
            ))
        self.assertEqual(raised.exception.code, "ratelimited")
        self.assertEqual(raised.exception.retry_after, 17.0)

    def test_ambiguous_timeout_is_not_reported_as_a_confirmed_delivery(self) -> None:
        async def provider(_request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("response may have been lost")

        api = SlackWebAPI(transport=httpx.MockTransport(provider))
        with self.assertRaises(SlackWebAPIError) as raised:
            asyncio.run(api.post_message(
                "xoxb-test", channel="C-channel", text="reply", thread_ts="1.2",
            ))
        self.assertEqual(raised.exception.code, "delivery_uncertain")
        self.assertTrue(raised.exception.uncertain)

    def test_ambiguous_slack_error_envelope_is_not_safe_to_retry(self) -> None:
        async def provider(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"ok": False, "error": "internal_error"})

        api = SlackWebAPI(transport=httpx.MockTransport(provider))
        with self.assertRaises(SlackWebAPIError) as raised:
            asyncio.run(api.post_message(
                "xoxb-test", channel="C-channel", text="reply", thread_ts="1.2",
            ))
        self.assertEqual(raised.exception.code, "internal_error")
        self.assertTrue(raised.exception.uncertain)


class SlackEventRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine, expire_on_commit=False)
        self.admin = User(email="slack-admin@example.com", display_name="Admin", status="ACTIVE")
        self.member = User(email="slack-member@example.com", display_name="Member", status="ACTIVE")
        self.other = User(email="other@example.com", display_name="Other", status="ACTIVE")
        self.org = Organization(legal_name="Acme", country_code="US", status="ACTIVE")
        self.other_org = Organization(legal_name="Other", country_code="CA", status="ACTIVE")
        self.db.add_all([self.admin, self.member, self.other, self.org, self.other_org])
        self.db.flush()
        self.db.add_all([
            OrganizationMember(
                organization_id=self.org.id, user_id=self.admin.id, role="ADMIN", status="ACTIVE",
                capabilities=[], permissions=["org.members.manage", "deal.read_all"], is_owner=True,
            ),
            OrganizationMember(
                organization_id=self.org.id, user_id=self.member.id, role="MEMBER", status="ACTIVE",
                capabilities=[], permissions=[],
            ),
            OrganizationMember(
                organization_id=self.other_org.id, user_id=self.other.id, role="MEMBER", status="ACTIVE",
                capabilities=[], permissions=[],
            ),
        ])
        self.installation = SlackInstallation(
            id=uuid4(), organization_id=self.org.id, workspace_id="T-workspace",
            workspace_name="Acme Slack", bot_user_id="B-bot",
            encrypted_bot_token=SlackTokenCipher(FERNET_KEY).encrypt("xoxb-test-token"),
            granted_scopes=["app_mentions:read", "chat:write"], status="CONNECTED",
            connected_by_user_id=self.admin.id, connected_at=datetime.now(UTC),
        )
        self.db.add(self.installation)
        self.db.commit()
        self.admin_actor = ActorContext(
            user_id=self.admin.id, organization_ids=frozenset({self.org.id})
        )
        self.member_actor = ActorContext(
            user_id=self.member.id, organization_ids=frozenset({self.org.id})
        )
        self.other_actor = ActorContext(
            user_id=self.other.id, organization_ids=frozenset({self.other_org.id})
        )
        self.signing_patch = patch.object(
            slack_events.settings, "slack_signing_secret", SecretStr(SIGNING_SECRET)
        )
        self.signing_patch.start()

    def tearDown(self) -> None:
        self.signing_patch.stop()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _mention_payload(
        self,
        *,
        event_id: str = "Ev-unique",
        user_id: str = "U-person",
        text: str = "<@BBOT> status 11111111-1111-1111-1111-111111111111",
        event_fields: dict[str, object] | None = None,
        event_type: str = "app_mention",
    ) -> dict[str, object]:
        event: dict[str, object] = {
            "type": event_type, "user": user_id, "channel": "C-channel",
            "text": text, "ts": "123.456",
        }
        event.update(event_fields or {})
        return {"type": "event_callback", "event_id": event_id, "team_id": "T-workspace", "event": event}

    def _receive(self, payload: dict[str, object]):
        return asyncio.run(slack_events.receive_slack_event(_signed_request(payload), self.db))

    def test_url_verification_is_returned_only_after_signature_check(self) -> None:
        response = self._receive({"type": "url_verification", "challenge": "opaque-challenge"})
        self.assertEqual(response, {"challenge": "opaque-challenge"})
        invalid_request = _signed_request({"type": "url_verification", "challenge": "opaque-challenge"})
        raw = b'{"type":"url_verification","challenge":"tampered"}'
        sent = False

        async def receive():
            nonlocal sent
            if sent:
                return {"type": "http.request", "body": b"", "more_body": False}
            sent = True
            return {"type": "http.request", "body": raw, "more_body": False}

        invalid_request._receive = receive
        rejected = asyncio.run(slack_events.receive_slack_event(invalid_request, self.db))
        self.assertIsInstance(rejected, JSONResponse)
        self.assertEqual(rejected.status_code, 401)

    def test_event_intake_normalizes_command_deduplicates_and_ignores_bots(self) -> None:
        payload = self._mention_payload(event_fields={"thread_ts": "123.000"})
        self.assertEqual(self._receive(payload), {"ok": True})
        self.assertEqual(self._receive(payload), {"ok": True})
        event = self.db.scalar(select(SlackEvent).where(SlackEvent.event_id == "Ev-unique"))
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.command, "STATUS")
        self.assertEqual(event.deal_id, "11111111-1111-1111-1111-111111111111")
        self.assertEqual(event.thread_ts, "123.000")
        self.assertFalse(hasattr(event, "message_text"))

        self._receive(self._mention_payload(event_id="Ev-bot", user_id="B-bot"))
        self._receive(self._mention_payload(event_id="Ev-botid", event_fields={"bot_id": "B-other"}))
        self._receive(self._mention_payload(event_id="Ev-message", event_type="message"))
        self.assertEqual(self.db.scalar(select(SlackEvent.event_id)), "Ev-unique")

        payments_payload = self._mention_payload(
            event_id="Ev-payments",
            text="<@BBOT> payments 11111111-1111-1111-1111-111111111111",
        )
        self._receive(payments_payload)
        self._receive(payments_payload)
        payments_event = self.db.scalar(
            select(SlackEvent).where(SlackEvent.event_id == "Ev-payments")
        )
        self.assertIsNotNone(payments_event)
        assert payments_event is not None
        self.assertEqual(payments_event.command, "PAYMENTS")
        self.assertEqual(self.db.scalar(
            select(SlackEvent.id).where(SlackEvent.event_id == "Ev-payments")
        ), payments_event.id)

    def test_unconfirmed_integrity_failure_is_raised_for_slack_retry(self) -> None:
        error = IntegrityError("insert slack event", {}, RuntimeError("unexpected constraint"))
        with patch.object(self.db, "commit", side_effect=error):
            with self.assertRaises(IntegrityError):
                self._receive(self._mention_payload(event_id="Ev-db-failure"))
        self.assertIsNone(
            self.db.scalar(select(SlackEvent.id).where(SlackEvent.event_id == "Ev-db-failure"))
        )

    def test_event_rejects_stale_and_oversized_requests(self) -> None:
        stale = _signed_request(self._mention_payload(), timestamp=int(time.time()) - 301)
        response = asyncio.run(slack_events.receive_slack_event(stale, self.db))
        self.assertEqual(response.status_code, 401)

        raw = b" " * (slack_events.MAX_SLACK_EVENT_BODY_BYTES + 1)
        sent = False

        async def receive():
            nonlocal sent
            if sent:
                return {"type": "http.request", "body": b"", "more_body": False}
            sent = True
            return {"type": "http.request", "body": raw, "more_body": False}

        request = Request(
            {"type": "http", "method": "POST", "path": "/integrations/slack/events",
             "headers": [(b"content-type", b"application/json")]}, receive
        )
        response = asyncio.run(slack_events.receive_slack_event(request, self.db))
        self.assertEqual(response.status_code, 413)

    def _challenge(self, code: str = "AbCdEfGh1234", *, expires_at: datetime | None = None) -> SlackLinkChallenge:
        challenge = SlackLinkChallenge(
            id=uuid4(), event_id=f"Ev-link-{uuid4()}", installation_id=self.installation.id,
            organization_id=self.org.id, workspace_id="T-workspace", slack_user_id="U-person",
            code_hash=hashlib.sha256(code.upper().encode("ascii")).hexdigest(),
            encrypted_code=SlackTokenCipher(FERNET_KEY).encrypt(code.upper()),
            expires_at=expires_at or datetime.now(UTC) + timedelta(minutes=10), attempts=0,
        )
        self.db.add(challenge)
        self.db.commit()
        return challenge

    def test_link_redemption_is_one_use_and_audited_without_granting_permissions(self) -> None:
        challenge = self._challenge()
        response = slack_events.redeem_slack_link(
            slack_events.SlackLinkRequest(code="  AbCdEfGh1234 "), self.member_actor, self.db
        )
        self.assertTrue(response.linked)
        link = self.db.scalar(select(SlackUserLink).where(SlackUserLink.slack_user_id == "U-person"))
        self.assertIsNotNone(link)
        assert link is not None
        self.assertEqual(link.user_id, self.member.id)
        self.assertEqual(link.organization_id, self.org.id)
        redeemed_challenge = self.db.get(SlackLinkChallenge, challenge.id)
        self.assertIsNotNone(redeemed_challenge.consumed_at)
        self.assertIsNone(redeemed_challenge.encrypted_code)
        self.assertEqual(redeemed_challenge.code_hash, hashlib.sha256(b"ABCDEFGH1234").hexdigest())
        self.assertIsNotNone(self.db.scalar(select(AuditEvent).where(AuditEvent.event_type == "integration.user_linked")))
        replay = slack_events.redeem_slack_link(
            slack_events.SlackLinkRequest(code="AbCdEfGh1234"), self.member_actor, self.db
        )
        self.assertTrue(replay.linked)

    def test_link_redemption_requires_active_member_of_installation_organization(self) -> None:
        self._challenge()
        with self.assertRaises(HTTPException) as denied:
            slack_events.redeem_slack_link(
                slack_events.SlackLinkRequest(code="AbCdEfGh1234"), self.other_actor, self.db
            )
        self.assertEqual(denied.exception.status_code, 403)
        self.assertIsNone(self.db.scalar(select(SlackUserLink)))

    def test_expired_link_code_cannot_be_redeemed(self) -> None:
        self._challenge(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        with self.assertRaises(HTTPException) as expired:
            slack_events.redeem_slack_link(
                slack_events.SlackLinkRequest(code="AbCdEfGh1234"), self.member_actor, self.db
            )
        self.assertEqual(expired.exception.status_code, 400)

    def test_worker_returns_only_status_and_same_denial_for_missing_or_unauthorized_deal(self) -> None:
        deal_id = uuid4()
        self.db.add(Deal(
            id=deal_id, buyer_organization_id=self.org.id, seller_organization_id=self.other_org.id,
            display_name="Private deal title", status=DealStatus.NEGOTIATING.value,
        ))
        self.db.add(SlackUserLink(
            id=uuid4(), installation_id=self.installation.id, organization_id=self.org.id,
            workspace_id="T-workspace", slack_user_id="U-authorized", user_id=self.admin.id,
            created_at=datetime.now(UTC),
        ))
        unauthorized = User(email="no-read@example.com", display_name="No read", status="ACTIVE")
        self.db.add(unauthorized)
        self.db.flush()
        self.db.add(OrganizationMember(
            organization_id=self.org.id, user_id=unauthorized.id, role="MEMBER", status="ACTIVE",
            capabilities=[], permissions=[],
        ))
        self.db.add(SlackUserLink(
            id=uuid4(), installation_id=self.installation.id, organization_id=self.org.id,
            workspace_id="T-workspace", slack_user_id="U-no-read", user_id=unauthorized.id,
            created_at=datetime.now(UTC),
        ))
        now = datetime.now(UTC)
        events = [
            SlackEvent(
                id=uuid4(), event_id="Ev-authorized", installation_id=self.installation.id,
                workspace_id="T-workspace", slack_user_id="U-authorized", channel_id="C-channel",
                message_ts="123.400", thread_ts="123.000", command="STATUS", deal_id=str(deal_id),
                status="PENDING", attempts=0, available_at=now,
            ),
            SlackEvent(
                id=uuid4(), event_id="Ev-denied", installation_id=self.installation.id,
                workspace_id="T-workspace", slack_user_id="U-no-read", channel_id="C-channel",
                message_ts="123.500", thread_ts="123.000", command="STATUS", deal_id=str(deal_id),
                status="PENDING", attempts=0, available_at=now + timedelta(milliseconds=1),
            ),
            SlackEvent(
                id=uuid4(), event_id="Ev-missing", installation_id=self.installation.id,
                workspace_id="T-workspace", slack_user_id="U-authorized", channel_id="C-channel",
                message_ts="123.600", thread_ts="123.000", command="STATUS", deal_id=str(uuid4()),
                status="PENDING", attempts=0, available_at=now + timedelta(milliseconds=2),
            ),
        ]
        self.db.add_all(events)
        self.db.commit()

        class FakeAPI:
            def __init__(self) -> None:
                self.messages: list[dict[str, str]] = []
                self.public_messages: list[dict[str, str]] = []

            async def post_message(self, token: str, **kwargs: str) -> None:
                self.public_messages.append(kwargs)

            async def post_ephemeral(self, token: str, **kwargs: str) -> None:
                self.messages.append(kwargs)

        from syncally.cli import slack_events_worker

        api = FakeAPI()

        def factory() -> Session:
            return Session(self.engine, expire_on_commit=False)

        with patch.object(slack_events_worker, "_cipher", return_value=SlackTokenCipher(FERNET_KEY)):
            for index in range(3):
                self.assertTrue(asyncio.run(
                    slack_events_worker.process_one(factory, api, now=now + timedelta(seconds=index))
                ))

        self.assertEqual(api.public_messages, [], "deal data and denials must not be broadcast to the channel")
        self.assertEqual(len(api.messages), 3)
        authorized_reply = next(message for message in api.messages if message["text"].startswith("Deal status:"))
        self.assertEqual(authorized_reply["thread_ts"], "123.000")
        self.assertEqual(authorized_reply["user"], "U-authorized")
        self.assertEqual(authorized_reply["text"], "Deal status: NEGOTIATING.")
        self.assertNotIn("Private deal title", authorized_reply["text"])
        denials = [message for message in api.messages if "authorized deal" in message["text"]]
        self.assertEqual(len(denials), 2)
        self.assertEqual(denials[0]["text"], denials[1]["text"])
        self.assertEqual({message["user"] for message in denials}, {"U-no-read", "U-authorized"})

    def _add_payment_lookup(self, deal_id, *, event_id: str, user_id: str = "U-payments", delay: int = 0):
        now = datetime.now(UTC)
        self.db.add(Deal(
            id=deal_id, buyer_organization_id=self.org.id, seller_organization_id=self.other_org.id,
            display_name="Payment lookup private deal", status=DealStatus.NEGOTIATING.value,
        ))
        if self.db.scalar(
            select(SlackUserLink.id).where(
                SlackUserLink.installation_id == self.installation.id,
                SlackUserLink.slack_user_id == user_id,
            )
        ) is None:
            self.db.add(SlackUserLink(
                id=uuid4(), installation_id=self.installation.id, organization_id=self.org.id,
                workspace_id="T-workspace", slack_user_id=user_id, user_id=self.admin.id,
                created_at=now,
            ))
        self.db.add(SlackEvent(
            id=uuid4(), event_id=event_id, installation_id=self.installation.id,
            workspace_id="T-workspace", slack_user_id=user_id, channel_id="C-channel",
            message_ts=f"124.{delay:03d}", thread_ts="124.000", command="PAYMENTS",
            deal_id=str(deal_id), status="PENDING", attempts=0,
            available_at=now + timedelta(milliseconds=delay), created_at=now + timedelta(milliseconds=delay),
        ))
        self.db.commit()

    def _add_follow_setup(self, *, deal_id=None, user_id: str = "U-follow", now=None):
        now = now or datetime.now(UTC)
        deal_id = deal_id or uuid4()
        agreement_id = uuid4()
        source_event_id = uuid4()
        deal = Deal(
            id=deal_id,
            buyer_organization_id=self.org.id,
            seller_organization_id=self.other_org.id,
            display_name="Sensitive agreement title",
            status=DealStatus.NEGOTIATING.value,
            current_agreement_version_id=agreement_id,
        )
        agreement = AgreementVersion(
            id=agreement_id,
            deal_id=deal_id,
            proposal_id=uuid4(),
            version_number=1,
            canonical_terms_json={"secret": "private commercial terms"},
            terms_hash="a" * 64,
            status="COMMITTED",
            created_by=self.admin.id,
            created_at=now - timedelta(minutes=5),
            committed_at=now - timedelta(minutes=1),
        )
        source_event = OutboxEvent(
            id=source_event_id,
            aggregate_type="agreement",
            aggregate_id=agreement_id,
            event_type="AGREEMENT_COMMITTED",
            payload={
                "deal_id": str(deal_id),
                "agreement_version_id": str(agreement_id),
                "version_number": 1,
                "private_terms": "should never be copied to Slack",
            },
            status="DELIVERED",
            retry_count=1,
            created_at=now - timedelta(seconds=30),
            delivered_at=now - timedelta(seconds=29),
        )
        link = SlackUserLink(
            id=uuid4(),
            installation_id=self.installation.id,
            organization_id=self.org.id,
            workspace_id=self.installation.workspace_id,
            slack_user_id=user_id,
            user_id=self.admin.id,
            created_at=now - timedelta(minutes=10),
        )
        self.db.add_all([deal, agreement, source_event, link])
        self.db.flush()
        subscription = SlackDealSubscription(
            id=uuid4(),
            installation_id=self.installation.id,
            organization_id=self.org.id,
            workspace_id=self.installation.workspace_id,
            slack_user_id=user_id,
            user_id=self.admin.id,
            deal_id=deal_id,
            channel_id="C-channel",
            thread_ts="125.000",
            created_at=now - timedelta(minutes=2),
        )
        self.db.add(subscription)
        self.db.commit()
        return deal_id, agreement_id, source_event_id, subscription

    def _add_slack_command_event(
        self,
        *,
        event_id: str,
        command: str,
        deal_id,
        user_id: str = "U-follow",
        now=None,
    ) -> SlackEvent:
        now = now or datetime.now(UTC)
        event = SlackEvent(
            id=uuid4(),
            event_id=event_id,
            installation_id=self.installation.id,
            workspace_id=self.installation.workspace_id,
            slack_user_id=user_id,
            channel_id="C-channel",
            message_ts=f"126.{len(event_id):03d}",
            thread_ts="125.000",
            command=command,
            deal_id=str(deal_id),
            status="PENDING",
            attempts=0,
            available_at=now,
            created_at=now,
        )
        self.db.add(event)
        self.db.commit()
        return event

    def test_follow_command_is_private_audited_and_idempotent_then_unfollow_cancels_delivery(self) -> None:
        from syncally.cli import slack_events_worker

        now = datetime.now(UTC)
        deal_id = uuid4()
        self.db.add(Deal(
            id=deal_id,
            buyer_organization_id=self.org.id,
            seller_organization_id=self.other_org.id,
            display_name="Private deal",
            status=DealStatus.NEGOTIATING.value,
        ))
        self.db.add(SlackUserLink(
            id=uuid4(), installation_id=self.installation.id, organization_id=self.org.id,
            workspace_id=self.installation.workspace_id, slack_user_id="U-follow",
            user_id=self.admin.id, created_at=now,
        ))
        self.db.commit()
        self._add_slack_command_event(
            event_id="Ev-follow-1", command="FOLLOW", deal_id=deal_id, now=now,
        )

        class FakeAPI:
            def __init__(self) -> None:
                self.private_messages: list[dict[str, str]] = []
                self.public_messages: list[dict[str, str]] = []

            async def post_ephemeral(self, _token: str, **kwargs: str) -> None:
                self.private_messages.append(kwargs)

            async def post_message(self, _token: str, **kwargs: str) -> None:
                self.public_messages.append(kwargs)

        def factory() -> Session:
            return Session(self.engine, expire_on_commit=False)

        api = FakeAPI()
        with patch.object(slack_events_worker, "_cipher", return_value=SlackTokenCipher(FERNET_KEY)):
            self.assertTrue(asyncio.run(slack_events_worker.process_one(factory, api, now=now)))

        subscription = self.db.scalar(select(SlackDealSubscription))
        self.assertIsNotNone(subscription)
        assert subscription is not None
        self.assertEqual(subscription.deal_id, deal_id)
        self.assertEqual(subscription.slack_user_id, "U-follow")
        self.assertEqual(subscription.thread_ts, "125.000")
        self.assertEqual(api.public_messages, [])
        self.assertEqual(api.private_messages[0]["user"], "U-follow")
        self.assertIn(str(deal_id), api.private_messages[0]["text"])
        self.assertIsNotNone(self.db.scalar(
            select(AuditEvent).where(AuditEvent.event_type == "integration.deal_followed")
        ))

        self._add_slack_command_event(
            event_id="Ev-follow-2", command="FOLLOW", deal_id=deal_id,
            now=now + timedelta(seconds=1),
        )
        with patch.object(slack_events_worker, "_cipher", return_value=SlackTokenCipher(FERNET_KEY)):
            self.assertTrue(asyncio.run(slack_events_worker.process_one(
                factory, api, now=now + timedelta(seconds=1),
            )))
        self.assertEqual(self.db.scalar(select(SlackDealSubscription.id)), subscription.id)

        agreement_id = uuid4()
        source_event_id = uuid4()
        self.db.add_all([
            AgreementVersion(
                id=agreement_id, deal_id=deal_id, proposal_id=uuid4(), version_number=1,
                canonical_terms_json={}, terms_hash="b" * 64, status="COMMITTED",
                created_by=self.admin.id, created_at=now + timedelta(seconds=1),
                committed_at=now + timedelta(seconds=1),
            ),
            OutboxEvent(
                id=source_event_id, aggregate_type="agreement", aggregate_id=agreement_id,
                event_type="AGREEMENT_COMMITTED", payload={"deal_id": str(deal_id)},
                status="DELIVERED", created_at=now + timedelta(seconds=1),
            ),
        ])
        self.db.flush()
        delivery = SlackNotificationDelivery(
            id=uuid4(), source_event_id=source_event_id,
            subscription_id=subscription.id, status="PENDING", attempts=0,
            available_at=now + timedelta(seconds=1),
        )
        self.db.add(delivery)
        self.db.commit()

        self._add_slack_command_event(
            event_id="Ev-unfollow", command="UNFOLLOW", deal_id=deal_id,
            now=now + timedelta(seconds=2),
        )
        with patch.object(slack_events_worker, "_cipher", return_value=SlackTokenCipher(FERNET_KEY)):
            self.assertTrue(asyncio.run(slack_events_worker.process_one(
                factory, api, now=now + timedelta(seconds=2),
            )))
        self.assertIsNone(self.db.scalar(
            select(SlackDealSubscription.id).where(SlackDealSubscription.id == subscription.id)
        ))
        self.assertIsNone(self.db.scalar(
            select(SlackNotificationDelivery.id).where(SlackNotificationDelivery.id == delivery.id)
        ))
        self.assertIsNotNone(self.db.scalar(
            select(AuditEvent).where(AuditEvent.event_type == "integration.deal_unfollowed")
        ))

    def test_agreement_commit_fanout_is_idempotent_and_sends_minimal_private_update(self) -> None:
        from syncally.cli import slack_events_worker

        now = datetime.now(UTC)
        deal_id, agreement_id, source_event_id, subscription = self._add_follow_setup(now=now)
        source = self.db.get(OutboxEvent, source_event_id)
        self.assertIsNotNone(source)
        assert source is not None

        self.assertEqual(
            slack_events_worker._enqueue_agreement_commit_deliveries(self.db, now), 1
        )
        self.assertEqual(
            slack_events_worker._enqueue_agreement_commit_deliveries(self.db, now), 0
        )
        self.db.refresh(source)
        self.assertEqual(source.status, "DELIVERED", "Slack fanout must not mutate Temporal outbox state")
        delivery = self.db.scalar(
            select(SlackNotificationDelivery).where(
                SlackNotificationDelivery.source_event_id == source_event_id,
                SlackNotificationDelivery.subscription_id == subscription.id,
            )
        )
        self.assertIsNotNone(delivery)

        class FakeAPI:
            def __init__(self) -> None:
                self.private_messages: list[dict[str, str]] = []
                self.public_messages: list[dict[str, str]] = []

            async def post_ephemeral(self, _token: str, **kwargs: str) -> None:
                self.private_messages.append(kwargs)

            async def post_message(self, _token: str, **kwargs: str) -> None:
                self.public_messages.append(kwargs)

        def factory() -> Session:
            return Session(self.engine, expire_on_commit=False)

        api = FakeAPI()
        with patch.object(slack_events_worker, "_cipher", return_value=SlackTokenCipher(FERNET_KEY)):
            self.assertTrue(asyncio.run(slack_events_worker.process_one(
                factory, api, now=now + timedelta(minutes=1),
            )))

        self.assertEqual(api.public_messages, [])
        self.assertEqual(len(api.private_messages), 1)
        reply = api.private_messages[0]
        self.assertEqual(reply["user"], subscription.slack_user_id)
        self.assertEqual(reply["channel"], subscription.channel_id)
        self.assertEqual(reply["thread_ts"], subscription.thread_ts)
        self.assertIn(str(deal_id), reply["text"])
        self.assertNotIn("Sensitive agreement title", reply["text"])
        self.assertNotIn("private commercial terms", reply["text"])
        self.assertNotIn("should never be copied", reply["text"])
        self.assertNotIn(str(agreement_id), reply["text"])

        self.db.refresh(source)
        self.assertEqual(source.status, "DELIVERED")

    def test_follow_requires_current_deal_read_permission(self) -> None:
        from syncally.cli import slack_events_worker

        now = datetime.now(UTC)
        deal_id = uuid4()
        self.db.add(Deal(
            id=deal_id,
            buyer_organization_id=self.org.id,
            seller_organization_id=self.other_org.id,
            display_name="Private deal",
            status=DealStatus.NEGOTIATING.value,
        ))
        self.db.add(SlackUserLink(
            id=uuid4(), installation_id=self.installation.id, organization_id=self.org.id,
            workspace_id=self.installation.workspace_id, slack_user_id="U-follow",
            user_id=self.admin.id, created_at=now,
        ))
        self.db.commit()
        self._add_slack_command_event(
            event_id="Ev-follow-unauthorized", command="FOLLOW", deal_id=deal_id, now=now,
        )
        actor_without_deal_read = ActorContext(
            user_id=self.admin.id,
            organization_ids=frozenset({self.org.id}),
        )

        class FakeAPI:
            def __init__(self) -> None:
                self.private_messages: list[dict[str, str]] = []

            async def post_ephemeral(self, _token: str, **kwargs: str) -> None:
                self.private_messages.append(kwargs)

        def factory() -> Session:
            return Session(self.engine, expire_on_commit=False)

        api = FakeAPI()
        with patch.object(slack_events_worker, "_cipher", return_value=SlackTokenCipher(FERNET_KEY)), \
             patch.object(slack_events_worker, "resolve_actor", return_value=actor_without_deal_read):
            self.assertTrue(asyncio.run(slack_events_worker.process_one(
                factory, api, now=now,
            )))

        self.assertEqual(len(api.private_messages), 1)
        self.assertEqual(api.private_messages[0]["text"], slack_events_worker._PRIVATE_DEAL_DENIAL)
        self.assertIsNone(self.db.scalar(select(SlackDealSubscription.id)))

    def test_notification_delivery_retries_rate_limit_but_not_ambiguous_send(self) -> None:
        from syncally.cli import slack_events_worker

        now = datetime.now(UTC)
        _deal_id, _agreement_id, _source_event_id, _subscription = self._add_follow_setup(now=now)

        class RateLimitedAPI:
            async def post_ephemeral(self, _token: str, **_kwargs: str) -> None:
                raise SlackWebAPIError("ratelimited", retry_after=30)

        class AmbiguousAPI:
            async def post_ephemeral(self, _token: str, **_kwargs: str) -> None:
                raise SlackWebAPIError("delivery_uncertain", uncertain=True)

        def factory() -> Session:
            return Session(self.engine, expire_on_commit=False)

        with patch.object(slack_events_worker, "_cipher", return_value=SlackTokenCipher(FERNET_KEY)):
            self.assertTrue(asyncio.run(slack_events_worker.process_one(
                factory, RateLimitedAPI(), now=now + timedelta(minutes=1),
            )))

        delivery = self.db.scalar(select(SlackNotificationDelivery))
        self.assertIsNotNone(delivery)
        assert delivery is not None
        self.assertEqual(delivery.status, "PENDING")
        self.assertEqual(delivery.last_error, "ratelimited")
        retry_at = delivery.available_at

        with patch.object(slack_events_worker, "_cipher", return_value=SlackTokenCipher(FERNET_KEY)):
            self.assertTrue(asyncio.run(slack_events_worker.process_one(
                factory, AmbiguousAPI(), now=retry_at + timedelta(seconds=1),
            )))

        self.db.refresh(delivery)
        self.assertEqual(delivery.status, "FAILED")
        self.assertEqual(delivery.last_error, "delivery_uncertain")
        self.assertEqual(delivery.attempts, 2)

    def test_agreement_notification_rechecks_access_before_send(self) -> None:
        from syncally.cli import slack_events_worker

        now = datetime.now(UTC)
        _deal_id, _agreement_id, source_event_id, subscription = self._add_follow_setup(now=now)
        delivery = SlackNotificationDelivery(
            id=uuid4(), source_event_id=source_event_id, subscription_id=subscription.id,
            status="PENDING", attempts=0, available_at=now - timedelta(seconds=1),
        )
        self.db.add(delivery)
        self.db.commit()

        class FakeAPI:
            def __init__(self) -> None:
                self.messages: list[dict[str, str]] = []

            async def post_ephemeral(self, _token: str, **kwargs: str) -> None:
                self.messages.append(kwargs)

        def factory() -> Session:
            return Session(self.engine, expire_on_commit=False)

        api = FakeAPI()
        with patch.object(slack_events_worker, "_cipher", return_value=SlackTokenCipher(FERNET_KEY)), \
             patch.object(slack_events_worker, "resolve_actor", return_value=None):
            self.assertTrue(asyncio.run(slack_events_worker.process_one(
                factory, api, now=now,
            )))

        self.assertEqual(api.messages, [])
        self.db.refresh(delivery)
        self.assertEqual(delivery.status, "FAILED")
        self.assertEqual(delivery.last_error, "authorization_revoked")

    def test_payment_lookup_requires_payments_read_and_hides_missing_deal_identically(self) -> None:
        from syncally.cli import slack_events_worker

        now = datetime.now(UTC)
        deal_id = uuid4()
        self._add_payment_lookup(deal_id, event_id="Ev-payments-denied", delay=0)
        self.db.add(SlackEvent(
            id=uuid4(), event_id="Ev-payments-missing", installation_id=self.installation.id,
            workspace_id="T-workspace", slack_user_id="U-payments", channel_id="C-channel",
            message_ts="124.100", thread_ts="124.000", command="PAYMENTS",
            deal_id=str(uuid4()), status="PENDING", attempts=0,
            available_at=now + timedelta(seconds=1), created_at=now + timedelta(seconds=1),
        ))
        self.db.commit()

        # The user can read the deal through deal.read_all but lacks payments.read.
        actor_without_payment_permission = ActorContext(
            user_id=self.admin.id,
            organization_ids=frozenset({self.org.id}),
            permissions_by_organization={self.org.id: frozenset({"deal.read_all"})},
        )

        class FakeAPI:
            def __init__(self) -> None:
                self.private_messages: list[dict[str, str]] = []
                self.public_messages: list[dict[str, str]] = []

            async def post_ephemeral(self, _token: str, **kwargs: str) -> None:
                self.private_messages.append(kwargs)

            async def post_message(self, _token: str, **kwargs: str) -> None:
                self.public_messages.append(kwargs)

        def factory() -> Session:
            return Session(self.engine, expire_on_commit=False)

        api = FakeAPI()
        with patch.object(slack_events_worker, "_cipher", return_value=SlackTokenCipher(FERNET_KEY)), \
             patch.object(slack_events_worker, "resolve_actor", return_value=actor_without_payment_permission):
            self.assertTrue(asyncio.run(slack_events_worker.process_one(
                factory, api, now=now + timedelta(seconds=5),
            )))
            self.assertTrue(asyncio.run(slack_events_worker.process_one(
                factory, api, now=now + timedelta(seconds=6),
            )))

        self.assertEqual(api.public_messages, [])
        self.assertEqual(len(api.private_messages), 2)
        self.assertEqual(
            {message["text"] for message in api.private_messages},
            {"I couldn't find authorized payment information for that deal."},
        )
        self.assertTrue(all(message["user"] == "U-payments" for message in api.private_messages))
        self.assertTrue(all(message["thread_ts"] == "124.000" for message in api.private_messages))

    def test_payment_lookup_sends_sorted_minimal_summary_only_to_requester(self) -> None:
        from syncally.cli import slack_events_worker

        now = datetime.now(UTC)
        deal_id = uuid4()
        self._add_payment_lookup(deal_id, event_id="Ev-payments-authorized")
        actor_with_payment_permission = ActorContext(
            user_id=self.admin.id,
            organization_ids=frozenset({self.org.id}),
            permissions_by_organization={
                self.org.id: frozenset({"deal.read_all", "payments.read"})
            },
        )
        payment_records = [
            PaymentStatusRecord(
                intent_id=uuid4(), milestone_sequence=2, amount=Money(Decimal("75.00"), "USD"),
                status="PAID", reconciled_amount=None, last_checked_at=None, last_reconciled_at=None,
                invoice_reference="private-provider-invoice-id",
            ),
            PaymentStatusRecord(
                intent_id=uuid4(), milestone_sequence=1, amount=Money(Decimal("25.00"), "EUR"),
                status="PENDING", reconciled_amount=None, last_checked_at=None, last_reconciled_at=None,
                invoice_reference="private-provider-invoice-id",
            ),
        ]

        class FakeAPI:
            def __init__(self) -> None:
                self.private_messages: list[dict[str, str]] = []
                self.public_messages: list[dict[str, str]] = []

            async def post_ephemeral(self, _token: str, **kwargs: str) -> None:
                self.private_messages.append(kwargs)

            async def post_message(self, _token: str, **kwargs: str) -> None:
                self.public_messages.append(kwargs)

        def factory() -> Session:
            return Session(self.engine, expire_on_commit=False)

        api = FakeAPI()
        with patch.object(slack_events_worker, "_cipher", return_value=SlackTokenCipher(FERNET_KEY)), \
             patch.object(slack_events_worker, "resolve_actor", return_value=actor_with_payment_permission), \
             patch.object(slack_events_worker, "list_current_payment_statuses", return_value=payment_records):
            self.assertTrue(asyncio.run(slack_events_worker.process_one(
                factory, api, now=now + timedelta(seconds=5),
            )))

        self.assertEqual(api.public_messages, [])
        self.assertEqual(len(api.private_messages), 1)
        reply = api.private_messages[0]
        self.assertEqual(reply["user"], "U-payments")
        self.assertEqual(reply["thread_ts"], "124.000")
        self.assertEqual(
            reply["text"],
            "Payment status:\nMilestone 1: PENDING — EUR 25\nMilestone 2: PAID — USD 75",
        )
        for secret in (
            "private-provider-invoice-id", "invoice_url", "recipient_email", "provider",
            "retry_count", "failure_reason", "Payment lookup private deal",
        ):
            self.assertNotIn(secret, reply["text"])

    def test_payment_lookup_without_status_rows_returns_safe_message(self) -> None:
        from syncally.cli import slack_events_worker

        now = datetime.now(UTC)
        self._add_payment_lookup(uuid4(), event_id="Ev-payments-no-rows")
        actor = ActorContext(
            user_id=self.admin.id,
            organization_ids=frozenset({self.org.id}),
            permissions_by_organization={
                self.org.id: frozenset({"deal.read_all", "payments.read"})
            },
        )

        class FakeAPI:
            def __init__(self) -> None:
                self.messages: list[dict[str, str]] = []

            async def post_ephemeral(self, _token: str, **kwargs: str) -> None:
                self.messages.append(kwargs)

        def factory() -> Session:
            return Session(self.engine, expire_on_commit=False)

        api = FakeAPI()
        with patch.object(slack_events_worker, "_cipher", return_value=SlackTokenCipher(FERNET_KEY)), \
             patch.object(slack_events_worker, "resolve_actor", return_value=actor), \
             patch.object(slack_events_worker, "list_current_payment_statuses", return_value=[]):
            self.assertTrue(asyncio.run(slack_events_worker.process_one(
                factory, api, now=now + timedelta(seconds=5),
            )))

        self.assertEqual(len(api.messages), 1)
        self.assertEqual(api.messages[0]["text"], "No payment status is available for this deal yet.")
        self.assertEqual(api.messages[0]["user"], "U-payments")

    def test_worker_bounds_unexpected_pre_send_failures_without_logging_secrets(self) -> None:
        from syncally.cli import slack_events_worker

        now = datetime.now(UTC)
        self.db.add(SlackEvent(
            id=uuid4(), event_id="Ev-worker-error", installation_id=self.installation.id,
            workspace_id="T-workspace", slack_user_id="U-person", channel_id="C-channel",
            message_ts="123.700", thread_ts="123.700", command="HELP", deal_id=None,
            status="PENDING", attempts=0, available_at=now,
        ))
        self.db.commit()

        def factory() -> Session:
            return Session(self.engine, expire_on_commit=False)

        with patch.object(slack_events_worker, "_cipher", side_effect=RuntimeError("token-secret-value")):
            with self.assertLogs("syncally.cli.slack_events_worker", level="WARNING") as captured:
                for attempt in range(slack_events_worker._MAX_ATTEMPTS):
                    self.assertTrue(asyncio.run(slack_events_worker.process_one(
                        factory, api=object(), now=now + timedelta(days=attempt),
                    )))

        event = self.db.scalar(select(SlackEvent).where(SlackEvent.event_id == "Ev-worker-error"))
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.status, "FAILED")
        self.assertEqual(event.attempts, slack_events_worker._MAX_ATTEMPTS)
        self.assertEqual(event.last_error, "worker_error")
        self.assertNotIn("token-secret-value", "\n".join(captured.output))

    def test_expired_processing_event_fails_as_uncertain_without_replay(self) -> None:
        from syncally.cli import slack_events_worker

        now = datetime.now(UTC)
        event = SlackEvent(
            id=uuid4(), event_id="Ev-expired-lease", installation_id=self.installation.id,
            workspace_id="T-workspace", slack_user_id="U-person", channel_id="C-channel",
            message_ts="123.800", thread_ts="123.800", command="STATUS",
            deal_id="11111111-1111-1111-1111-111111111111", status="PROCESSING",
            attempts=2, available_at=now - timedelta(seconds=1),
        )
        self.db.add(event)
        self.db.commit()

        def factory() -> Session:
            return Session(self.engine, expire_on_commit=False)

        self.assertFalse(asyncio.run(slack_events_worker.process_one(
            factory, api=object(), now=now,
        )))
        self.db.refresh(event)
        self.assertEqual(event.status, "FAILED")
        self.assertEqual(event.last_error, "delivery_uncertain")
        self.assertEqual(event.attempts, 2)

    def test_ambiguous_slack_error_envelope_fails_without_retry(self) -> None:
        from syncally.cli import slack_events_worker

        now = datetime.now(UTC)
        event = SlackEvent(
            id=uuid4(), event_id="Ev-ambiguous-provider-error", installation_id=self.installation.id,
            workspace_id="T-workspace", slack_user_id="U-person", channel_id="C-channel",
            message_ts="123.850", thread_ts="123.850", command="HELP", deal_id=None,
            status="PENDING", attempts=0, available_at=now,
        )
        self.db.add(event)
        self.db.commit()

        class AmbiguousAPI:
            async def post_message(self, *_args, **_kwargs) -> None:
                raise SlackWebAPIError("internal_error", uncertain=True)

        def factory() -> Session:
            return Session(self.engine, expire_on_commit=False)

        with patch.object(slack_events_worker, "_cipher", return_value=SlackTokenCipher(FERNET_KEY)):
            self.assertTrue(asyncio.run(slack_events_worker.process_one(factory, AmbiguousAPI(), now=now)))

        self.db.refresh(event)
        self.assertEqual(event.status, "FAILED")
        self.assertEqual(event.last_error, "delivery_uncertain")
        self.assertEqual(event.attempts, 1)

    def test_worker_prunes_expired_challenges_and_only_terminal_events_past_30_days(self) -> None:
        from syncally.cli.slack_events_worker import prune_slack_records

        now = datetime.now(UTC)
        expired_challenge = self._challenge(expires_at=now - timedelta(seconds=1))
        active_challenge = self._challenge(
            code="NewCode1234", expires_at=now + timedelta(minutes=5)
        )
        old_events = []
        for index, status_value in enumerate(("DELIVERED", "FAILED", "PENDING", "PROCESSING", "FAILED")):
            created_at = now - timedelta(days=31 if index < 4 else 10)
            old_events.append(SlackEvent(
                id=uuid4(), event_id=f"Ev-retention-{index}", installation_id=self.installation.id,
                workspace_id="T-workspace", slack_user_id="U-person", channel_id="C-channel",
                message_ts=f"123.{900 + index}", thread_ts="123.000", command="HELP", deal_id=None,
                status=status_value, attempts=1, available_at=now, created_at=created_at,
                delivered_at=created_at if status_value == "DELIVERED" else None,
            ))
        self.db.add_all(old_events)
        old_deliveries = []
        for index, status_value in enumerate(("DELIVERED", "FAILED", "PENDING", "FAILED")):
            created_at = now - timedelta(days=31 if index < 3 else 10)
            old_deliveries.append(SlackNotificationDelivery(
                id=uuid4(), source_event_id=uuid4(), subscription_id=uuid4(),
                status=status_value, attempts=1, available_at=now, created_at=created_at,
                delivered_at=created_at if status_value == "DELIVERED" else None,
            ))
        self.db.add_all(old_deliveries)
        self.db.commit()

        challenges_deleted, events_deleted = prune_slack_records(self.db, now=now)

        self.assertEqual(challenges_deleted, 1)
        self.assertEqual(events_deleted, 2)
        self.assertIsNone(self.db.get(SlackLinkChallenge, expired_challenge.id))
        self.assertIsNotNone(self.db.get(SlackLinkChallenge, active_challenge.id))
        self.assertIsNone(self.db.get(SlackEvent, old_events[0].id))
        self.assertIsNone(self.db.get(SlackEvent, old_events[1].id))
        for preserved in (old_events[2], old_events[3], old_events[4]):
            self.assertIsNotNone(self.db.get(SlackEvent, preserved.id))
        for removed in (old_deliveries[0], old_deliveries[1]):
            self.assertIsNone(self.db.scalar(
                select(SlackNotificationDelivery.id).where(
                    SlackNotificationDelivery.id == removed.id
                )
            ))
        for preserved in (old_deliveries[2], old_deliveries[3]):
            self.assertIsNotNone(self.db.scalar(
                select(SlackNotificationDelivery.id).where(
                    SlackNotificationDelivery.id == preserved.id
                )
            ))


if __name__ == "__main__":
    unittest.main()
