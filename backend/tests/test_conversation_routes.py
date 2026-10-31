"""HTTP contract tests for deal message and fact-review routes."""

import asyncio
import json as json_module
import logging
import unittest
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import httpx
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.auth import get_current_actor
from syncally.api.conversations import AddMessageRequest, get_ai_suggestion_provider
from syncally.api.main import app
from syncally.application.identity import ActorContext
from syncally.config import Settings
from syncally.domain.conversations import (
    Constraint as DomainConstraint,
)
from syncally.domain.conversations import (
    ConstraintKind,
    ConstraintStatus,
    MessageSourceType,
    Visibility,
)
from syncally.domain.conversations import (
    Conversation as DomainConversation,
)
from syncally.domain.conversations import (
    Message as DomainMessage,
)
from syncally.domain.shared.identifiers import (
    ConstraintId,
    ConversationId,
    DealId,
    MessageId,
    OrganizationId,
    UserId,
)
from syncally.infrastructure.ai.selection import ConfiguredAIProvider
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import (
    AuditEvent,
    Base,
    Deal,
    Organization,
    OrganizationMember,
    OutboxEvent,
    User,
)
from syncally.infrastructure.models import (
    Constraint as ConstraintModel,
)
from syncally.infrastructure.models import (
    Message as MessageModel,
)
from syncally.infrastructure.repositories import SqlAlchemyCommunicationRepository


class AddMessageRequestTests(unittest.TestCase):
    def test_optional_opaque_idempotency_key(self) -> None:
        payload = {"body": " message ", "visibility": "PRIVATE"}
        self.assertIsNone(AddMessageRequest(**payload).idempotency_key)
        self.assertIsNone(AddMessageRequest(**payload, idempotency_key=None).idempotency_key)
        for key in ("opaque", " opaque ", "x" * 128):
            self.assertEqual(AddMessageRequest(**payload, idempotency_key=key).idempotency_key, key)
        for key in ("", " \t\n", "x" * 129):
            with self.subTest(key=key), self.assertRaises(ValidationError):
                AddMessageRequest(**payload, idempotency_key=key)


class ConversationRouteTests(unittest.TestCase):
    def _openai_provider(self, handler, **updates) -> ConfiguredAIProvider:
        config = dict(app_env="test", ai_provider="openai", ai_remote_egress_enabled=True,
                      openai_api_key="test-only-key", openai_model="operator-test-model")
        config.update(updates)
        return ConfiguredAIProvider(Settings(_env_file=None, **config), transport=httpx.MockTransport(handler))

    def test_remote_http_is_transaction_free_and_revoked_selected_org_cannot_persist(self) -> None:
        source = self._message(self.buyer_conversation, "We need 12 boxes.", Visibility.SHAREABLE,
                               author_user_id=self.buyer_user.id)
        self.session.add(OrganizationMember(user_id=self.buyer_user.id, organization_id=self.seller.id, status="ACTIVE"))
        self.session.commit()
        calls = []
        def respond(request: httpx.Request) -> httpx.Response:
            self.assertFalse(self.session.in_transaction())
            calls.append(request)
            membership = self.session.scalar(select(OrganizationMember).where(
                OrganizationMember.user_id == self.buyer_user.id,
                OrganizationMember.organization_id == self.buyer.id,
            ))
            membership.status = "REVOKED"
            self.session.commit()
            return httpx.Response(200, json={"object": "chat.completion", "model": "operator-test-model", "choices": [{
                "index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": json_module.dumps({
                    "schema_version": 1, "facts": [{"schema_version": 1, "field": "quantity", "value": "12",
                    "currency_or_unit": "boxes", "source": {"schema_version": 1, "message_id": str(source.id),
                    "quote": "We need 12 boxes.", "unknown_reason": None}}],
                })},
            }]})
        app.dependency_overrides[get_ai_suggestion_provider] = lambda: self._openai_provider(respond)
        self._authenticate(ActorContext(self.buyer_user.id, frozenset({self.buyer.id, self.seller.id})))
        response = self._request("POST", f"/deals/{self.deal.id}/ai/facts", json={"organization_id": str(self.buyer.id)})
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(len(calls), 1)
        self.assertEqual(list(self.session.scalars(select(ConstraintModel))), [])
        denied = self._request("POST", f"/deals/{self.deal.id}/ai/facts", json={"organization_id": str(self.buyer.id)})
        self.assertEqual(denied.status_code, 404, denied.text)
        self.assertEqual(len(calls), 1)

    def test_remote_invalid_output_not_persisted_and_provenance_is_invocation_only(self) -> None:
        self._authenticate(self._buyer_actor())
        app.dependency_overrides[get_ai_suggestion_provider] = lambda: self._openai_provider(
            lambda _: httpx.Response(200, content=b"malformed private provider response"),
        )
        with self.assertLogs(level=logging.INFO) as captured:
            response = self._request("POST", f"/deals/{self.deal.id}/ai/facts", json={"organization_id": str(self.buyer.id)})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "INVALID")
        self.assertEqual(response.json()["facts"], [])
        self.assertEqual(response.json()["provenance"]["provider"], "openai")
        self.assertEqual(response.json()["provenance"]["context_scope"], "shareable_only")
        self.assertNotIn("private provider response", response.text)
        self.assertNotIn("test-only-key", "\n".join(captured.output))
        self.assertNotIn("private provider response", "\n".join(captured.output))
        self.assertEqual(list(self.session.scalars(select(ConstraintModel))), [])

    def test_remote_currency_evidence_controls_routes_without_retry_or_fallback(self) -> None:
        self._authenticate(self._buyer_actor())
        for claim, quote, valid in (
            ("12 boxes at CAD $2.50", "CAD $2.50", False),
            ("12 boxes at EUR $2.50", "EUR $2.50", False),
            ("12 boxes at AUD 2.50 dollars", "AUD 2.50 dollars", False),
            ("12 boxes at $2.50", "$2.50", False),
            ("12 boxes at 2.50 dollars", "2.50 dollars", False),
            ("12 boxes at USD 2.50", "USD 2.50", True),
            ("12 boxes; Budget USD 2.50; actual unit price $2.50.",
             "Budget USD 2.50; actual unit price $2.50.", False),
            ("12 boxes; Budget USD 2.50; actual unit price $2.50.", "USD 2.50", False),
            ("12 boxes; Budget USD 2.50; actual unit price $2.50.", "2.50", False),
            ("12 boxes; Budget USD 2.50; actual unit price USD 2.50.", "USD 2.50", False),
            ("12 boxes; actual unit price USD 2.50; second price $2.50",
             "actual unit price USD 2.50; second price $2.50", False),
            ("12 boxes; actual unit price USD 2.50; second price CAD 2.50",
             "actual unit price USD 2.50; second price CAD 2.50", False),
            ("12 boxes; Payment USD 2.50 per unit", "USD 2.50", False),
            ("12 boxes; Total USD 2.50 per unit", "USD 2.50", False),
            ("12 boxes; actual unit price USD 2.50", "actual unit price USD 2.50", True),
            ("12 boxes; actual unit price USD 2.50", "USD 2.50", True),
            ("12 boxes; USD 2.50 per unit", "USD 2.50 per unit", True),
            ("12 boxes; 2.50 USD/unit", "2.50 USD/unit", True),
            ("12 boxes; Budget USD 9.00; actual unit price USD 2.50",
             "actual unit price USD 2.50", True),
        ):
            with self.subTest(claim=claim, quote=quote):
                source = self._message(
                    self.buyer_conversation,
                    f"Item: Widget, {claim}, deliver to Toronto by 2026-12-01.",
                    Visibility.SHAREABLE, author_user_id=self.buyer_user.id,
                )
                self.session.commit()
                citations = [{
                    "schema_version": 1, "field": field, "value": value,
                    "currency_or_unit": currency_or_unit,
                    "source": {"schema_version": 1, "message_id": str(source.id),
                               "quote": quote, "unknown_reason": None},
                } for field, value, currency_or_unit, quote in (
                    ("item_description", "Widget", None, "Widget"),
                    ("quantity", "12", "boxes", "12 boxes"),
                    ("unit", "boxes", None, "boxes"),
                    ("unit_price", "2.50", "USD", quote),
                    ("delivery_destination", "Toronto", None, "Toronto"),
                    ("delivery_date", "2026-12-01", None, "2026-12-01"),
                )]
                for operation in ("facts", "proposal"):
                    with self.subTest(operation=operation):
                        before = {
                            table.name: [tuple(row) for row in self.session.execute(select(table))]
                            for table in Base.metadata.sorted_tables
                        }
                        output = {"schema_version": 1, "facts": citations} if operation == "facts" else {
                            "schema_version": 1, "insufficient_context": False,
                            "proposal": {"schema_version": 1, "description": "Widget", "quantity": "12",
                                         "unit": "boxes", "unit_price": "2.50", "currency": "USD",
                                         "delivery_destination": "Toronto", "delivery_date": "2026-12-01"},
                            "citations": citations,
                        }
                        calls = []
                        def respond(request: httpx.Request) -> httpx.Response:
                            self.assertFalse(self.session.in_transaction())
                            calls.append(request)
                            return httpx.Response(200, json={"object": "chat.completion", "model": "operator-test-model", "choices": [{
                                "index": 0, "finish_reason": "stop",
                                "message": {"role": "assistant", "content": json_module.dumps(output)},
                            }]})
                        provider = self._openai_provider(respond, ai_provider="openai_with_offline_fallback")
                        app.dependency_overrides[get_ai_suggestion_provider] = lambda: provider
                        response = self._request("POST", f"/deals/{self.deal.id}/ai/{operation}", json={"organization_id": str(self.buyer.id)})
                        self.assertEqual(len(calls), 1)
                        self.assertEqual(provider.provenance.provider, "openai")
                        self.assertIsNone(provider.provenance.fallback_reason)
                        if operation == "facts":
                            self.assertEqual(response.status_code, 200, response.text)
                            self.assertEqual(response.json()["status"], "VALID" if valid else "INVALID")
                            self.assertEqual(len(response.json()["facts"]), 6 if valid else 0)
                            if valid:
                                saved_price = next(fact for fact in response.json()["facts"] if fact["field"] == "unit_price")
                                self.assertEqual(saved_price["source_span"], quote)
                        else:
                            self.assertEqual(response.status_code, 200 if valid else 422, response.text)
                            if valid:
                                self.assertEqual(response.json()["status"], "DRAFT")
                                self.assertEqual(response.json()["currency"], "USD")
                            else:
                                self.assertNotIn("unit_price", response.json())
                        after = {
                            table.name: [tuple(row) for row in self.session.execute(select(table))]
                            for table in Base.metadata.sorted_tables
                        }
                        if not valid or operation == "proposal":
                            self.assertEqual(after, before)

    def test_disabled_egress_and_missing_model_return_generic_configuration_503(self) -> None:
        self._authenticate(self._buyer_actor())
        for updates in ({"ai_remote_egress_enabled": False}, {"openai_model": ""}):
            config = dict(app_env="test", ai_provider="openai", ai_remote_egress_enabled=True,
                          openai_api_key="test-only-key", openai_model="operator-test-model")
            config.update(updates)
            with patch("syncally.api.conversations.settings", Settings(_env_file=None, **config)):
                response = self._request("POST", f"/deals/{self.deal.id}/ai/facts", json={"organization_id": str(self.buyer.id)})
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["detail"], "AI suggestions are not configured")

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.repository = SqlAlchemyCommunicationRepository(self.session)

        self.buyer_user = User(email="buyer@example.com", display_name="Buyer")
        self.seller_user = User(email="seller@example.com", display_name="Seller")
        self.outsider_user = User(email="outsider@example.com", display_name="Outsider")
        self.buyer = Organization(legal_name="Buyer Co", country_code="US")
        self.seller = Organization(legal_name="Seller Co", country_code="CA")
        self.outsider = Organization(legal_name="Outsider Co", country_code="GB")
        self.session.add_all(
            [
                self.buyer_user,
                self.seller_user,
                self.outsider_user,
                self.buyer,
                self.seller,
                self.outsider,
            ]
        )
        self.session.flush()
        self.session.add_all(
            [
                OrganizationMember(
                    user_id=self.buyer_user.id, organization_id=self.buyer.id, status="ACTIVE"
                ),
                OrganizationMember(
                    user_id=self.seller_user.id, organization_id=self.seller.id, status="ACTIVE"
                ),
                OrganizationMember(
                    user_id=self.outsider_user.id,
                    organization_id=self.outsider.id,
                    status="ACTIVE",
                ),
            ]
        )
        self.deal = Deal(
            buyer_organization_id=self.buyer.id,
            seller_organization_id=self.seller.id,
            status="DRAFT",
            version=0,
        )
        self.session.add(self.deal)
        self.session.commit()
        self.buyer_conversation = self.repository.add_conversation(
            DomainConversation(
                id=ConversationId(uuid4()),
                deal_id=DealId(self.deal.id),
                participant_organization_id=OrganizationId(self.buyer.id),
                created_at=datetime.now(UTC),
            )
        )
        self.seller_conversation = self.repository.add_conversation(
            DomainConversation(
                id=ConversationId(uuid4()),
                deal_id=DealId(self.deal.id),
                participant_organization_id=OrganizationId(self.seller.id),
                created_at=datetime.now(UTC),
            )
        )
        self.session.commit()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _authenticate(self, actor: ActorContext) -> None:
        app.dependency_overrides[get_db] = lambda: self.session
        app.dependency_overrides[get_current_actor] = lambda: actor

    def _buyer_actor(self) -> ActorContext:
        return ActorContext(self.buyer_user.id, frozenset({self.buyer.id}))

    def _seller_actor(self) -> ActorContext:
        return ActorContext(self.seller_user.id, frozenset({self.seller.id}))

    def _outsider_actor(self) -> ActorContext:
        return ActorContext(self.outsider_user.id, frozenset({self.outsider.id}))

    def _request(
        self, method: str, path: str, *, json: dict[str, Any] | None = None
    ) -> httpx.Response:
        async def send() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                return await client.request(method, path, json=json)

        return asyncio.run(send())

    def _message(
        self,
        conversation: DomainConversation,
        body: str,
        visibility: Visibility,
        *,
        author_user_id,
        source_reference: str | None = None,
    ) -> DomainMessage:
        return self.repository.add_message(
            DomainMessage(
                id=MessageId(uuid4()),
                conversation_id=conversation.id,
                author_user_id=UserId(author_user_id),
                author_agent_id=None,
                body=body,
                visibility=visibility,
                source_type=MessageSourceType.USER,
                source_reference=source_reference,
                created_at=datetime.now(UTC),
            )
        )

    def _constraint(
        self,
        owner_id,
        field: str,
        visibility: Visibility,
        *,
        source_message: DomainMessage | None = None,
        status: ConstraintStatus = ConstraintStatus.EXTRACTED,
    ) -> DomainConstraint:
        owner_is_seller = owner_id == self.seller.id
        confirmer = self.seller_user.id if owner_is_seller else self.buyer_user.id
        if visibility is Visibility.SHAREABLE and source_message is None:
            source_message = self._message(
                self.seller_conversation if owner_is_seller else self.buyer_conversation,
                "shareable provenance",
                Visibility.SHAREABLE,
                author_user_id=confirmer,
            )
        constraint = DomainConstraint(
            id=ConstraintId(uuid4()),
            deal_id=DealId(self.deal.id),
            owner_organization_id=OrganizationId(owner_id),
            field=field,
            typed_value="test value",
            kind=ConstraintKind.INFORMATIONAL,
            visibility=visibility,
            source_message_id=source_message.id if source_message else None,
            source_span="source excerpt",
            created_at=datetime.now(UTC),
        )
        if status is ConstraintStatus.CONFIRMED:
            constraint.confirm(confirmed_by=UserId(confirmer), confirmed_at=datetime.now(UTC))
        return self.repository.add_constraint(constraint)

    def test_thread_import_preview_exact_persistence_and_visibility_conflict(self) -> None:
        self._authenticate(self._buyer_actor())
        path = f"/deals/{self.deal.id}/messages/import"
        text = " \nFrom: Seller\r\nSubject: Caf\u00e9\r\n\r\n> Price \u20ac9\r\nFrom: Buyer\r\nPrice \u20ac8 \U0001f600 \n "
        preview = self._request("POST", path + "/preview", json={"text": text})
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.json()["text"], text.strip())
        self.assertFalse(preview.json()["headers"][0]["verified"])
        self.assertEqual(list(self.session.scalars(select(OutboxEvent))), [])
        self.assertEqual(self._request("GET", f"/deals/{self.deal.id}/messages").json(), [])
        payload = {"text": text, "digest": preview.json()["digest"], "confirmed": True}
        first = self._request("POST", path, json=payload)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["body"], text.strip())
        self.assertEqual(first.json()["visibility"], "PRIVATE")
        self.assertEqual(first.json()["author_user_id"], str(self.buyer_user.id))
        replay = self._request("POST", path, json={**payload, "text": text.strip()})
        self.assertEqual(replay.json(), first.json())
        self.assertEqual(len(list(self.session.scalars(select(OutboxEvent)))), 1)
        conflict = self._request("POST", path, json={
            **payload, "visibility": "SHAREABLE", "shareable_confirmed": True,
        })
        self.assertEqual(conflict.status_code, 409)
        self._authenticate(self._seller_actor())
        self.assertEqual(self._request("GET", f"/deals/{self.deal.id}/messages").json(), [])

    def test_thread_import_strict_schema_confirmation_and_stale_digest(self) -> None:
        self._authenticate(self._buyer_actor())
        path = f"/deals/{self.deal.id}/messages/import"
        preview = self._request("POST", path + "/preview", json={"text": "From: Spoof\nOriginal"}).json()
        payload = {"text": preview["text"], "digest": preview["digest"], "confirmed": True}
        for field, value in (
            ("author_user_id", str(self.seller_user.id)), ("author_agent_id", "agent"),
            ("source_type", "AGENT"), ("source_reference", "client-source"),
            ("idempotency_key", "client-key"), ("created_at", "2000-01-01T00:00:00Z"),
        ):
            for endpoint, body in ((path, payload), (path + "/preview", {"text": preview["text"]})):
                with self.subTest(field=field, endpoint=endpoint):
                    response = self._request("POST", endpoint, json={**body, field: value})
                    self.assertEqual(response.status_code, 422)
                    self.assertNotIn("Spoof", response.text)
        for change in (
            {"confirmed": False}, {"confirmed": "true"}, {"confirmed": 1},
            {"visibility": "SHAREABLE"}, {"visibility": "SHAREABLE", "shareable_confirmed": "true"},
            {"digest": "invalid"},
        ):
            with self.subTest(change=change):
                self.assertEqual(self._request("POST", path, json={**payload, **change}).status_code, 422)
        self.assertEqual(self._request("POST", path, json={**payload, "text": "Changed"}).status_code, 409)
        self.assertEqual(list(self.session.scalars(select(MessageModel))), [])
        self.assertEqual(list(self.session.scalars(select(OutboxEvent))), [])

    def test_thread_import_normalized_code_point_and_raw_request_limits(self) -> None:
        self._authenticate(self._buyer_actor())
        path = f"/deals/{self.deal.id}/messages/import"
        for text in ("", " \r\n\t", "x" * 8001, "  " + "x" * 8001 + "  ", "\ufeff" + "x" * 8000):
            for endpoint in (path + "/preview", path):
                payload = {"text": text} if endpoint.endswith("/preview") else {"text": text, "digest": "plaintext-thread:v1:" + "a" * 64, "confirmed": True}
                self.assertEqual(self._request("POST", endpoint, json=payload).status_code, 422)
        for text in ("x" * 8000, "  " + "x" * 8000 + "  ", "\u0085\u001c" + "x" * 8000 + "\u2003\u3000", "\U0001f600" * 2000 + "x" * 6000):
            preview = self._request("POST", path + "/preview", json={"text": text})
            self.assertEqual(preview.status_code, 200)
            self.assertEqual(preview.json()["text"], text.strip())
            canonical = self._request("POST", path + "/preview", json={"text": text.strip()})
            self.assertEqual(preview.json()["digest"], canonical.json()["digest"])
            imported = self._request("POST", path, json={
                "text": text, "digest": canonical.json()["digest"], "confirmed": True,
            })
            self.assertEqual(imported.status_code, 201)
            self.assertEqual(imported.json()["body"], text.strip())
        for text in ("\U0001f600" * 5000, " " * 9000 + "x" * 8000):
            for endpoint in (path + "/preview", path):
                self.assertEqual(self._request("POST", endpoint, json={"text": text}).status_code, 413)
        self.assertEqual(len(list(self.session.scalars(select(MessageModel)))), 2)

    def test_thread_import_streamed_request_limit_cannot_be_bypassed_without_content_length(self) -> None:
        self._authenticate(self._buyer_actor())
        path = f"/deals/{self.deal.id}/messages/import"
        body = json_module.dumps({"text": "\U0001f600" * 5000}, ensure_ascii=False).encode("utf-8")

        async def send(endpoint: str) -> httpx.Response:
            async def chunks():
                yield body[:12000]
                yield body[12000:]

            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                request = client.build_request("POST", endpoint, content=chunks(), headers={"Content-Type": "application/json"})
                self.assertNotIn("content-length", request.headers)
                return await client.send(request)

        for endpoint in (path, path + "/preview"):
            self.assertEqual(asyncio.run(send(endpoint)).status_code, 413)
        self.assertEqual(list(self.session.scalars(select(MessageModel))), [])
        self.assertEqual(list(self.session.scalars(select(OutboxEvent))), [])

    def test_thread_import_auth_and_replay_recheck_revoked_selected_membership(self) -> None:
        path = f"/deals/{self.deal.id}/messages/import"
        for endpoint in (path + "/preview", path):
            self.assertEqual(self._request("POST", endpoint, json={"text": "Private"}).status_code, 401)
        self._authenticate(self._buyer_actor())
        preview = self._request("POST", path + "/preview", json={"text": "Private"}).json()
        payload = {"text": "Private", "digest": preview["digest"], "confirmed": True}
        self.assertEqual(self._request("POST", path, json=payload).status_code, 201)
        self._authenticate(self._outsider_actor())
        for endpoint in (path + "/preview", path):
            self.assertEqual(self._request("POST", endpoint, json=payload if endpoint == path else {"text": "Private"}).status_code, 404)
        self._authenticate(self._buyer_actor())
        for endpoint, body in ((path, payload), (path + "/preview", {"text": "Private"})):
            self.assertEqual(self._request("POST", endpoint, json={**body, "organization_id": str(self.seller.id)}).status_code, 403)
            missing_path = endpoint.replace(str(self.deal.id), str(uuid4()))
            self.assertEqual(self._request("POST", missing_path, json=body).status_code, 404)
        self.session.add(OrganizationMember(user_id=self.buyer_user.id, organization_id=self.seller.id, status="ACTIVE"))
        member = self.session.scalar(select(OrganizationMember).where(
            OrganizationMember.user_id == self.buyer_user.id, OrganizationMember.organization_id == self.buyer.id,
        ))
        member.status = "INACTIVE"
        self.session.commit()
        self._authenticate(ActorContext(self.buyer_user.id, frozenset({self.buyer.id, self.seller.id})))
        for endpoint, body in ((path, payload), (path + "/preview", {"text": "Private"})):
            response = self._request("POST", endpoint, json={**body, "organization_id": str(self.buyer.id)})
            self.assertEqual(response.status_code, 404)
            self.assertNotIn("Private", response.text)
        self.assertEqual(len(list(self.session.scalars(select(OutboxEvent)))), 1)

    def test_thread_import_scope_and_explicit_sharing_are_independent(self) -> None:
        path = f"/deals/{self.deal.id}/messages/import"
        self._authenticate(self._buyer_actor())
        text = "From: Seller <seller@example.com>\nPrivate terms"
        preview = self._request("POST", path + "/preview", json={"text": text}).json()
        payload = {"text": text, "digest": preview["digest"], "confirmed": True}
        buyer_message = self._request("POST", path, json=payload).json()
        self._authenticate(self._seller_actor())
        seller_message = self._request("POST", path, json={**payload, "visibility": "SHAREABLE", "shareable_confirmed": True})
        self.assertEqual(seller_message.status_code, 201)
        self.assertNotEqual(seller_message.json()["id"], buyer_message["id"])
        self.assertEqual(seller_message.json()["author_user_id"], str(self.seller_user.id))
        self._authenticate(self._buyer_actor())
        visible = self._request("GET", f"/deals/{self.deal.id}/messages").json()
        self.assertEqual(len(visible), 2)
        shared = next(item for item in visible if item["id"] == seller_message.json()["id"])
        self.assertIsNone(shared["source_reference"])
        self.assertEqual(list(self.session.scalars(select(ConstraintModel))), [])
        self.assertEqual(self.session.get(Deal, self.deal.id).status, "DRAFT")

    def test_thread_import_ai_only_after_explicit_review_has_exact_persisted_citations(self) -> None:
        self._authenticate(self._buyer_actor())
        path = f"/deals/{self.deal.id}/messages/import"
        text = " \nFrom: Unverified\nSubject: Order\n\nItem: Widget, 12 boxes at USD 2.50, deliver to Toronto by 2026-12-01.\n> Earlier draft \n "
        preview = self._request("POST", path + "/preview", json={"text": text}).json()
        imported = self._request("POST", path, json={"text": text, "digest": preview["digest"], "confirmed": True}).json()
        self.assertEqual(list(self.session.scalars(select(ConstraintModel))), [])
        response = self._request("POST", f"/deals/{self.deal.id}/ai/facts", json={"organization_id": str(self.buyer.id)})
        self.assertEqual(response.status_code, 200)
        facts = response.json()["facts"]
        self.assertTrue(facts)
        for fact in facts:
            self.assertEqual(fact["source_message_id"], imported["id"])
            self.assertIn(fact["source_span"], imported["body"])
            self.assertEqual(fact["status"], "EXTRACTED")
            self.assertEqual(fact["visibility"], "PRIVATE")
            self.assertIsNone(fact["confirmed_by"])
        self._authenticate(self._seller_actor())
        hidden = self._request("POST", f"/deals/{self.deal.id}/ai/facts", json={"organization_id": str(self.seller.id)})
        self.assertEqual(hidden.status_code, 200)
        self.assertEqual(hidden.json()["facts"], [])
        self.assertTrue(hidden.json()["missing_fields"])

    def test_idempotency_durable_normalized_replay_and_payload_conflicts(self) -> None:
        actor = self._buyer_actor()
        path = f"/deals/{self.deal.id}/messages"
        self.session.commit()

        def fresh_db():
            with Session(self.engine) as session:
                try:
                    yield session
                except Exception:
                    session.rollback()
                    raise

        app.dependency_overrides[get_db] = fresh_db
        app.dependency_overrides[get_current_actor] = lambda: actor
        payload = {
            "body": "  Terms agreed  ", "visibility": "PRIVATE",
            "source_reference": "  upload:1  ", "idempotency_key": "retry-key",
        }
        first = self._request("POST", path, json=payload)
        self.assertEqual(first.status_code, 201)
        replay_payload = {
            **payload, "body": "Terms agreed", "source_reference": "upload:1",
            "author_user_id": str(self.seller_user.id), "source_type": "AGENT",
            "author_agent_id": "ignored", "created_at": "2000-01-01T00:00:00Z",
        }
        replay = self._request("POST", path, json=replay_payload)
        self.assertEqual(replay.status_code, 201)
        self.assertEqual(replay.json(), first.json())
        for change in ({"body": "Changed"}, {"visibility": "SHAREABLE"}, {"source_reference": "upload:2"}):
            with self.subTest(change=change):
                response = self._request("POST", path, json={**replay_payload, **change})
                self.assertEqual(response.status_code, 409)
                self.assertNotIn("Terms agreed", response.text)
        self.assertEqual(len(self.session.scalars(select(OutboxEvent)).all()), 1)
        self.assertNotIn("idempotency_key", first.json())
        self.assertNotIn("idempotency_fingerprint", first.json())

    def test_idempotency_null_reference_normalizes_and_legacy_requests_remain_distinct(self) -> None:
        self._authenticate(self._buyer_actor())
        path = f"/deals/{self.deal.id}/messages"
        payload = {"body": "Terms", "visibility": "SHAREABLE", "idempotency_key": "empty-ref"}
        first = self._request("POST", path, json=payload)
        for reference in (None, " \t "):
            replay = self._request("POST", path, json={**payload, "source_reference": reference})
            self.assertEqual(replay.status_code, 201)
            self.assertEqual(replay.json(), first.json())
        legacy = {"body": "Terms", "visibility": "SHAREABLE"}
        responses = [self._request("POST", path, json=value) for value in
                     (legacy, legacy, {**legacy, "idempotency_key": None}, {**legacy, "idempotency_key": None})]
        self.assertEqual({response.status_code for response in responses}, {201})
        self.assertEqual(len({response.json()["id"] for response in responses}), 4)

    def test_idempotency_replay_rechecks_revoked_access(self) -> None:
        actor = self._buyer_actor()
        self._authenticate(actor)
        path = f"/deals/{self.deal.id}/messages"
        payload = {"body": "Private", "visibility": "PRIVATE", "idempotency_key": "revoked"}
        self.assertEqual(self._request("POST", path, json=payload).status_code, 201)
        member = self.session.scalar(select(OrganizationMember).where(OrganizationMember.user_id == actor.user_id))
        member.status = "INACTIVE"
        self.session.commit()
        response = self._request("POST", path, json=payload)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Private", response.text)

    def test_add_message_returns_201_and_ignores_client_supplied_author(self) -> None:
        self._authenticate(self._buyer_actor())

        response = self._request(
            "POST",
            f"/deals/{self.deal.id}/messages",
            json={
                "body": "  Delivery before 30 June  ",
                "visibility": "PRIVATE",
                "author_user_id": str(self.seller_user.id),
                "source_reference": "upload:buyer-doc-7",
            },
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(
            set(body),
            {
                "id",
                "conversation_id",
                "author_user_id",
                "author_agent_id",
                "body",
                "visibility",
                "source_type",
                "source_reference",
                "created_at",
            },
        )
        self.assertEqual(body["body"], "Delivery before 30 June")
        self.assertEqual(body["author_user_id"], str(self.buyer_user.id))
        self.assertEqual(body["visibility"], "PRIVATE")
        self.assertEqual(body["source_type"], "USER")
        self.assertEqual(body["source_reference"], "upload:buyer-doc-7")

    def test_create_manual_fact_is_audited_and_shared_only_when_requested(self) -> None:
        self._authenticate(self._buyer_actor())

        response = self._request(
            "POST",
            f"/deals/{self.deal.id}/facts",
            json={
                "organization_id": str(self.buyer.id),
                "field": "unit_price",
                "typed_value": "2.50",
                "currency_or_unit": "USD",
                "visibility": "SHAREABLE",
            },
        )

        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["owner_organization_id"], str(self.buyer.id))
        self.assertEqual(body["field"], "unit_price")
        self.assertEqual(body["typed_value"], "2.50")
        self.assertEqual(body["currency_or_unit"], "USD")
        self.assertEqual(body["kind"], "INFORMATIONAL")
        self.assertEqual(body["status"], "EXTRACTED")
        self.assertEqual(body["visibility"], "SHAREABLE")
        self.assertIsNotNone(body["source_message_id"])

        source_messages = self._request(
            "GET", f"/deals/{self.deal.id}/messages?organization_id={self.buyer.id}"
        )
        self.assertEqual(source_messages.status_code, 200, source_messages.text)
        source = next(
            message
            for message in source_messages.json()
            if message["id"] == body["source_message_id"]
        )
        self.assertEqual(source["body"], "Manual term entry — unit_price: 2.50")
        self.assertEqual(source["visibility"], "SHAREABLE")

        self._authenticate(self._seller_actor())
        visible_facts = self._request(
            "GET", f"/deals/{self.deal.id}/facts?organization_id={self.seller.id}"
        )
        self.assertEqual(visible_facts.status_code, 200, visible_facts.text)
        self.assertIn(body["id"], {item["id"] for item in visible_facts.json()})
        visible_messages = self._request(
            "GET", f"/deals/{self.deal.id}/messages?organization_id={self.seller.id}"
        )
        self.assertEqual(visible_messages.status_code, 200, visible_messages.text)
        self.assertIn(body["source_message_id"], {item["id"] for item in visible_messages.json()})

    def test_create_manual_fact_rejects_an_organization_the_actor_cannot_select(self) -> None:
        self._authenticate(self._buyer_actor())

        response = self._request(
            "POST",
            f"/deals/{self.deal.id}/facts",
            json={
                "organization_id": str(self.outsider.id),
                "field": "delivery_date",
                "typed_value": "2026-11-15",
                "visibility": "PRIVATE",
            },
        )

        self.assertEqual(response.status_code, 403, response.text)

    def test_ai_suggestions_are_explicit_scoped_persisted_and_reviewable(self) -> None:
        source = self._message(
            self.buyer_conversation,
            "Item: Widget, 12 boxes at USD 2.50, deliver to Toronto by 2026-12-01.",
            Visibility.PRIVATE,
            author_user_id=self.buyer_user.id,
        )
        self.session.commit()
        self._authenticate(self._buyer_actor())

        response = self._request(
            "POST",
            f"/deals/{self.deal.id}/ai/facts",
            json={"organization_id": str(self.buyer.id)},
        )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["status"], "VALID")
        self.assertEqual(body["provenance"]["provider"], "offline")
        self.assertIsNone(body["provenance"]["model"])
        self.assertEqual(body["missing_fields"], [])
        self.assertIn("All required trade details were found", body["guidance_message"])
        facts = body["facts"]
        self.assertEqual(
            {fact["field"] for fact in facts},
            {"item_description", "quantity", "unit", "unit_price", "delivery_destination", "delivery_date"},
        )
        self.assertTrue(all(fact["status"] == "EXTRACTED" for fact in facts))
        self.assertTrue(all(fact["visibility"] == "PRIVATE" for fact in facts))
        self.assertTrue(all(fact["source_message_id"] == str(source.id) for fact in facts))
        self.assertTrue(all(fact["source_span"] for fact in facts))

        repeated = self._request(
            "POST",
            f"/deals/{self.deal.id}/ai/facts",
            json={"organization_id": str(self.buyer.id)},
        )
        self.assertEqual(repeated.status_code, 200, repeated.text)
        self.assertEqual({fact["id"] for fact in repeated.json()["facts"]}, {fact["id"] for fact in facts})
        self.assertEqual(len(self.repository.list_constraints(self.deal.id, self.buyer.id, limit=100, offset=0)), 6)

        self._authenticate(self._seller_actor())
        seller_facts = self._request(
            "GET", f"/deals/{self.deal.id}/facts?organization_id={self.seller.id}"
        )
        self.assertEqual(seller_facts.status_code, 200)
        self.assertFalse(any(fact["id"] in {item["id"] for item in facts} for fact in seller_facts.json()))

        self._authenticate(self._buyer_actor())
        proposal = self._request(
            "POST",
            f"/deals/{self.deal.id}/ai/proposal",
            json={"organization_id": str(self.buyer.id)},
        )
        self.assertEqual(proposal.status_code, 200, proposal.text)
        self.assertEqual(proposal.json()["status"], "DRAFT")
        self.assertEqual(proposal.json()["provenance"]["provider"], "offline")
        self.assertEqual(proposal.json()["description"], "Widget")
        self.assertEqual(proposal.json()["currency"], "USD")

        candidate = next(fact for fact in facts if fact["field"] == "quantity")
        correction = self._request(
            "PATCH",
            f"/deals/{self.deal.id}/facts/{candidate['id']}",
            json={
                "expected_version": candidate["version"],
                "field": "quantity",
                "typed_value": "24",
                "currency_or_unit": "boxes",
            },
        )
        self.assertEqual(correction.status_code, 200, correction.text)
        self.assertEqual(correction.json()["replaced_fact"]["status"], "REJECTED")
        corrected = correction.json()["corrected_fact"]
        self.assertEqual(corrected["typed_value"], "24")
        self.assertEqual(corrected["status"], "EXTRACTED")
        confirmed = self._request(
            "POST", f"/deals/{self.deal.id}/facts/{corrected['id']}/confirm"
        )
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.json()["status"], "CONFIRMED")

        self._authenticate(self._outsider_actor())
        outsider_attempt = self._request(
            "POST",
            f"/deals/{self.deal.id}/ai/facts",
            json={"organization_id": str(self.buyer.id)},
        )
        self.assertEqual(outsider_attempt.status_code, 404)

    def test_fact_guidance_checks_constraints_beyond_the_first_page(self) -> None:
        base_time = datetime(2025, 1, 1, tzinfo=UTC)
        rows = [
            ConstraintModel(
                id=uuid4(),
                deal_id=self.deal.id,
                owner_organization_id=self.buyer.id,
                field="conversation_note",
                typed_value=f"note {index}",
                kind=ConstraintKind.INFORMATIONAL.value,
                status=ConstraintStatus.EXTRACTED.value,
                visibility=Visibility.PRIVATE.value,
                source_span=f"source note {index}",
                created_at=base_time + timedelta(seconds=index),
            )
            for index in range(500)
        ]
        rows.append(
            ConstraintModel(
                id=uuid4(),
                deal_id=self.deal.id,
                owner_organization_id=self.buyer.id,
                field="delivery_destination",
                typed_value="Toronto",
                kind=ConstraintKind.INFORMATIONAL.value,
                status=ConstraintStatus.EXTRACTED.value,
                visibility=Visibility.PRIVATE.value,
                source_span="delivery destination Toronto",
                created_at=base_time + timedelta(seconds=500),
            )
        )
        self.session.add_all(rows)
        self.session.commit()
        self._authenticate(self._buyer_actor())

        response = self._request(
            "POST",
            f"/deals/{self.deal.id}/ai/facts",
            json={"organization_id": str(self.buyer.id)},
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("delivery_destination", response.json()["missing_fields"])

    def test_fact_guidance_reloads_visible_constraints_after_provider_runs(self) -> None:
        source = self._message(
            self.seller_conversation,
            "Delivery destination is Vancouver.",
            Visibility.SHAREABLE,
            author_user_id=self.seller_user.id,
        )
        self.session.commit()

        class AddsShareableDestination:
            def extract_facts(_self, _request, *, timeout_seconds: float):
                self._constraint(
                    self.seller.id,
                    "delivery_destination",
                    Visibility.SHAREABLE,
                    source_message=source,
                )
                self.session.commit()
                return ()

        app.dependency_overrides[get_ai_suggestion_provider] = AddsShareableDestination
        self._authenticate(self._buyer_actor())

        response = self._request(
            "POST",
            f"/deals/{self.deal.id}/ai/facts",
            json={"organization_id": str(self.buyer.id)},
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("delivery_destination", response.json()["missing_fields"])

    def test_add_message_creates_the_actor_organization_conversation(self) -> None:
        self._authenticate(self._seller_actor())
        repository = SqlAlchemyCommunicationRepository(self.session)

        response = self._request(
            "POST",
            f"/deals/{self.deal.id}/messages",
            json={"body": "seller note", "visibility": "PRIVATE"},
        )

        self.assertEqual(response.status_code, 201)
        conversations = repository.list_conversations(self.deal.id, self.seller.id)
        self.assertEqual(len(conversations), 1)
        self.assertEqual(response.json()["conversation_id"], str(conversations[0].id))

    def test_add_message_requires_authentication(self) -> None:
        app.dependency_overrides[get_db] = lambda: self.session

        response = self._request(
            "POST",
            f"/deals/{self.deal.id}/messages",
            json={"body": "hello", "visibility": "PRIVATE"},
        )

        self.assertEqual(response.status_code, 401)

    def test_add_message_hides_a_non_participant_deal(self) -> None:
        self._authenticate(self._outsider_actor())

        response = self._request(
            "POST",
            f"/deals/{self.deal.id}/messages",
            json={"body": "sneaky", "visibility": "PRIVATE"},
        )

        self.assertEqual(response.status_code, 404)

    def test_add_message_rejects_an_organization_the_actor_does_not_belong_to(self) -> None:
        self._authenticate(self._buyer_actor())

        response = self._request(
            "POST",
            f"/deals/{self.deal.id}/messages",
            json={
                "body": "spoofed",
                "visibility": "PRIVATE",
                "organization_id": str(self.seller.id),
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_add_message_rejects_blank_body_and_unknown_visibility(self) -> None:
        self._authenticate(self._buyer_actor())

        blank = self._request(
            "POST",
            f"/deals/{self.deal.id}/messages",
            json={"body": "   ", "visibility": "PRIVATE"},
        )
        internal = self._request(
            "POST",
            f"/deals/{self.deal.id}/messages",
            json={"body": "hello", "visibility": "INTERNAL"},
        )

        self.assertEqual(blank.status_code, 422)
        self.assertEqual(internal.status_code, 422)

    def test_validation_error_does_not_echo_the_submitted_body(self) -> None:
        self._authenticate(self._buyer_actor())
        sentinel = "sensitive-message-sentinel"
        oversized_body = sentinel + ("x" * 9000)

        response = self._request(
            "POST",
            f"/deals/{self.deal.id}/messages",
            json={"body": oversized_body, "visibility": "PRIVATE"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertNotIn(sentinel, response.text)
        detail = response.json()["detail"]
        self.assertIsInstance(detail, list)
        for error in detail:
            self.assertIn("loc", error)
            self.assertIn("msg", error)
            self.assertNotIn("input", error)

    def test_list_messages_returns_only_visible_messages(self) -> None:
        buyer_private = self._message(
            self.buyer_conversation,
            "buyer private",
            Visibility.PRIVATE,
            author_user_id=self.buyer_user.id,
        )
        shareable = self._message(
            self.seller_conversation,
            "seller shareable",
            Visibility.SHAREABLE,
            author_user_id=self.seller_user.id,
            source_reference="seller:secret-upload",
        )
        seller_private = self._message(
            self.seller_conversation,
            "seller private",
            Visibility.PRIVATE,
            author_user_id=self.seller_user.id,
        )
        self.session.commit()
        self._authenticate(self._buyer_actor())

        response = self._request("GET", f"/deals/{self.deal.id}/messages")

        self.assertEqual(response.status_code, 200)
        payload = {item["id"]: item for item in response.json()}
        self.assertEqual(set(payload), {str(buyer_private.id), str(shareable.id)})
        self.assertNotIn(str(seller_private.id), payload)
        self.assertIsNone(payload[str(shareable.id)]["source_reference"])

    def test_list_messages_is_empty_for_a_non_participant(self) -> None:
        self._message(
            self.buyer_conversation,
            "buyer private",
            Visibility.PRIVATE,
            author_user_id=self.buyer_user.id,
        )
        self.session.commit()
        self._authenticate(self._outsider_actor())

        response = self._request("GET", f"/deals/{self.deal.id}/messages")

        self.assertEqual(response.status_code, 404)
        self.assertNotIn("buyer private", response.text)

    def test_list_messages_requires_authentication(self) -> None:
        app.dependency_overrides[get_db] = lambda: self.session

        response = self._request("GET", f"/deals/{self.deal.id}/messages")

        self.assertEqual(response.status_code, 401)

    def test_message_existence_is_true_for_a_private_counterparty_message(self) -> None:
        secret = "seller private note"
        self._message(
            self.seller_conversation,
            secret,
            Visibility.PRIVATE,
            author_user_id=self.seller_user.id,
        )
        self.session.commit()
        self._authenticate(self._buyer_actor())

        visible = self._request("GET", f"/deals/{self.deal.id}/messages")
        self.assertEqual(visible.status_code, 200)
        self.assertEqual(visible.json(), [])

        response = self._request("GET", f"/deals/{self.deal.id}/messages/existence")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"has_messages": True})
        self.assertNotIn(secret, response.text)

    def test_message_existence_is_false_when_no_messages_exist(self) -> None:
        self._authenticate(self._buyer_actor())

        response = self._request("GET", f"/deals/{self.deal.id}/messages/existence")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"has_messages": False})

    def test_message_existence_is_hidden_from_a_non_participant(self) -> None:
        self._message(
            self.buyer_conversation,
            "buyer private",
            Visibility.PRIVATE,
            author_user_id=self.buyer_user.id,
        )
        self.session.commit()
        self._authenticate(self._outsider_actor())

        response = self._request("GET", f"/deals/{self.deal.id}/messages/existence")

        self.assertEqual(response.status_code, 404)
        self.assertNotIn("buyer private", response.text)

    def test_message_existence_requires_authentication(self) -> None:
        app.dependency_overrides[get_db] = lambda: self.session

        response = self._request("GET", f"/deals/{self.deal.id}/messages/existence")

        self.assertEqual(response.status_code, 401)

    def test_list_facts_returns_only_visible_facts(self) -> None:
        buyer_private = self._constraint(self.buyer.id, "buyer_only", Visibility.PRIVATE)
        seller_shareable = self._constraint(
            self.seller.id, "incoterm", Visibility.SHAREABLE
        )
        self.session.commit()
        self._authenticate(self._buyer_actor())

        response = self._request("GET", f"/deals/{self.deal.id}/facts")

        self.assertEqual(response.status_code, 200)
        fields = {item["field"] for item in response.json()}
        self.assertEqual(fields, {"buyer_only", "incoterm"})
        self.assertEqual({item["owner_organization_id"] for item in response.json()}, {
            str(self.buyer.id),
            str(self.seller.id),
        })
        self.assertIn(str(buyer_private.id), response.text)
        # A private counterparty fact is never present.
        seller_private = self._constraint(self.seller.id, "seller_only", Visibility.PRIVATE)
        self.session.commit()
        second = self._request("GET", f"/deals/{self.deal.id}/facts")
        self.assertNotIn(str(seller_private.id), second.text)
        self.assertNotIn("seller_only", second.text)
        self.assertIn(str(seller_shareable.id), second.text)

    def test_confirm_fact_persists_reviewer_and_version(self) -> None:
        constraint = self._constraint(self.buyer.id, "quantity", Visibility.PRIVATE)
        self.session.commit()
        self._authenticate(self._buyer_actor())

        response = self._request(
            "POST", f"/deals/{self.deal.id}/facts/{constraint.id}/confirm"
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "CONFIRMED")
        self.assertEqual(body["confirmed_by"], str(self.buyer_user.id))
        self.assertEqual(body["version"], 1)
        self.session.expire_all()
        persisted = self.repository.get_constraint_for_deal(
            self.deal.id, constraint.id, self.buyer_user.id
        )
        self.assertEqual(persisted.status, ConstraintStatus.CONFIRMED)

    def test_counterparty_cannot_confirm_a_fact(self) -> None:
        constraint = self._constraint(self.buyer.id, "quantity", Visibility.PRIVATE)
        self.session.commit()
        self._authenticate(self._seller_actor())

        response = self._request(
            "POST", f"/deals/{self.deal.id}/facts/{constraint.id}/confirm"
        )

        self.assertEqual(response.status_code, 404)

    def test_reject_and_clarify_facts(self) -> None:
        rejected_source = self._constraint(self.buyer.id, "quantity", Visibility.PRIVATE)
        clarified_source = self._constraint(self.buyer.id, "window", Visibility.PRIVATE)
        self.session.commit()
        self._authenticate(self._buyer_actor())

        rejected = self._request(
            "POST", f"/deals/{self.deal.id}/facts/{rejected_source.id}/reject"
        )
        clarified = self._request(
            "POST", f"/deals/{self.deal.id}/facts/{clarified_source.id}/clarify"
        )

        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.json()["status"], "REJECTED")
        self.assertIsNone(rejected.json()["confirmed_by"])
        self.assertEqual(clarified.status_code, 200)
        self.assertEqual(clarified.json()["status"], "NEEDS_CLARIFICATION")

    def test_reviewing_a_confirmed_fact_returns_conflict(self) -> None:
        constraint = self._constraint(
            self.buyer.id, "quantity", Visibility.PRIVATE, status=ConstraintStatus.CONFIRMED
        )
        self.session.commit()
        self._authenticate(self._buyer_actor())

        response = self._request(
            "POST", f"/deals/{self.deal.id}/facts/{constraint.id}/reject"
        )

        self.assertEqual(response.status_code, 409)

    def test_review_fact_requires_authentication(self) -> None:
        constraint = self._constraint(self.buyer.id, "quantity", Visibility.PRIVATE)
        self.session.commit()
        app.dependency_overrides[get_db] = lambda: self.session

        response = self._request(
            "POST", f"/deals/{self.deal.id}/facts/{constraint.id}/confirm"
        )

        self.assertEqual(response.status_code, 401)

    def test_message_content_is_not_written_to_logs(self) -> None:
        sentinel = "confidential-message-body-sentinel"
        captured: list[str] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                captured.append(self.format(record))

        handler = _Capture()
        root_logger = logging.getLogger()
        previous_level = root_logger.level
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.DEBUG)
        try:
            self._authenticate(self._buyer_actor())
            response = self._request(
                "POST",
                f"/deals/{self.deal.id}/messages",
                json={"body": sentinel, "visibility": "PRIVATE"},
            )
        finally:
            root_logger.removeHandler(handler)
            root_logger.setLevel(previous_level)

        self.assertEqual(response.status_code, 201)
        self.assertNotIn(sentinel, "\n".join(captured))

    def test_owner_can_toggle_fact_visibility(self) -> None:
        constraint = self._constraint(self.buyer.id, "quantity", Visibility.PRIVATE)
        self.session.commit()
        self._authenticate(self._buyer_actor())

        # Toggle to SHAREABLE
        response = self._request(
            "PATCH",
            f"/deals/{self.deal.id}/facts/{constraint.id}/visibility",
            json={"visibility": "SHAREABLE"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["visibility"], "SHAREABLE")
        self.assertEqual(body["version"], 1)

        # Check DB state
        self.session.expire_all()
        row = self.session.scalar(
            select(ConstraintModel).where(ConstraintModel.id == constraint.id)
        )
        self.assertIsNotNone(row)
        self.assertEqual(row.visibility, "SHAREABLE")
        self.assertEqual(row.version, 1)

        # Check AuditEvent in DB
        audit_row = self.session.scalar(
            select(AuditEvent).where(
                AuditEvent.aggregate_type == "deal_fact",
                AuditEvent.aggregate_id == constraint.id,
                AuditEvent.event_type == "FACT_VISIBILITY_UPDATED",
            )
        )
        self.assertIsNotNone(audit_row)
        self.assertEqual(audit_row.actor_type, "USER")
        self.assertEqual(audit_row.actor_id, str(self.buyer_user.id))
        self.assertEqual(audit_row.payload["previous_visibility"], "PRIVATE")
        self.assertEqual(audit_row.payload["new_visibility"], "SHAREABLE")
        self.assertEqual(audit_row.payload["deal_id"], str(self.deal.id))

        # Toggle back to PRIVATE
        response2 = self._request(
            "PATCH",
            f"/deals/{self.deal.id}/facts/{constraint.id}/visibility",
            json={"visibility": "PRIVATE"},
        )
        self.assertEqual(response2.status_code, 200, response2.text)
        self.assertEqual(response2.json()["visibility"], "PRIVATE")
        self.assertEqual(response2.json()["version"], 2)

        self.session.expire_all()
        row2 = self.session.scalar(
            select(ConstraintModel).where(ConstraintModel.id == constraint.id)
        )
        self.assertEqual(row2.visibility, "PRIVATE")

    def test_non_owner_cannot_alter_fact_visibility(self) -> None:
        constraint = self._constraint(self.buyer.id, "quantity", Visibility.PRIVATE)
        self.session.commit()
        self._authenticate(self._seller_actor())

        response = self._request(
            "PATCH",
            f"/deals/{self.deal.id}/facts/{constraint.id}/visibility",
            json={"visibility": "SHAREABLE"},
        )
        self.assertEqual(response.status_code, 403)
        self.session.expire_all()
        row = self.session.scalar(
            select(ConstraintModel).where(ConstraintModel.id == constraint.id)
        )
        self.assertEqual(row.visibility, "PRIVATE")

    def test_outsider_cannot_alter_fact_visibility(self) -> None:
        constraint = self._constraint(self.buyer.id, "quantity", Visibility.PRIVATE)
        self.session.commit()
        self._authenticate(self._outsider_actor())

        response = self._request(
            "PATCH",
            f"/deals/{self.deal.id}/facts/{constraint.id}/visibility",
            json={"visibility": "SHAREABLE"},
        )
        self.assertEqual(response.status_code, 404)

    def test_alter_fact_visibility_returns_404_when_missing(self) -> None:
        self._authenticate(self._buyer_actor())
        random_id = uuid4()
        response = self._request(
            "PATCH",
            f"/deals/{self.deal.id}/facts/{random_id}/visibility",
            json={"visibility": "SHAREABLE"},
        )
        self.assertEqual(response.status_code, 404)

    def test_alter_fact_visibility_rejects_invalid_visibility(self) -> None:
        constraint = self._constraint(self.buyer.id, "quantity", Visibility.PRIVATE)
        self.session.commit()
        self._authenticate(self._buyer_actor())

        response = self._request(
            "PATCH",
            f"/deals/{self.deal.id}/facts/{constraint.id}/visibility",
            json={"visibility": "INVALID_VALUE"},
        )
        self.assertEqual(response.status_code, 422)

    def test_alter_fact_visibility_requires_authentication(self) -> None:
        constraint = self._constraint(self.buyer.id, "quantity", Visibility.PRIVATE)
        self.session.commit()
        app.dependency_overrides[get_db] = lambda: self.session

        response = self._request(
            "PATCH",
            f"/deals/{self.deal.id}/facts/{constraint.id}/visibility",
            json={"visibility": "SHAREABLE"},
        )
        self.assertEqual(response.status_code, 401)

    def test_alter_fact_visibility_rejects_shareable_when_source_message_is_private(self) -> None:
        private_message = self._message(
            self.buyer_conversation,
            "secret internal buyer note",
            Visibility.PRIVATE,
            author_user_id=self.buyer_user.id,
        )
        constraint = self._constraint(
            self.buyer.id,
            "margin_target",
            Visibility.PRIVATE,
            source_message=private_message,
        )
        self.session.commit()
        self._authenticate(self._buyer_actor())

        response = self._request(
            "PATCH",
            f"/deals/{self.deal.id}/facts/{constraint.id}/visibility",
            json={"visibility": "SHAREABLE"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"],
            "A shareable fact cannot cite a private message",
        )

        # Check DB state was unchanged
        self.session.expire_all()
        row = self.session.scalar(
            select(ConstraintModel).where(ConstraintModel.id == constraint.id)
        )
        self.assertIsNotNone(row)
        self.assertEqual(row.visibility, "PRIVATE")
        self.assertEqual(row.version, 0)

        # Ensure counterparty cannot see the fact via visible-facts endpoint
        self._authenticate(self._seller_actor())
        list_response = self._request("GET", f"/deals/{self.deal.id}/facts")
        self.assertEqual(list_response.status_code, 200)
        returned_fact_ids = [item["id"] for item in list_response.json()]
        self.assertNotIn(str(constraint.id), returned_fact_ids)

    def test_alter_fact_visibility_allows_shareable_when_source_message_is_shareable(self) -> None:
        shareable_message = self._message(
            self.buyer_conversation,
            "shared requirement",
            Visibility.SHAREABLE,
            author_user_id=self.buyer_user.id,
        )
        constraint = self._constraint(
            self.buyer.id,
            "delivery_date",
            Visibility.PRIVATE,
            source_message=shareable_message,
        )
        self.session.commit()
        self._authenticate(self._buyer_actor())

        response = self._request(
            "PATCH",
            f"/deals/{self.deal.id}/facts/{constraint.id}/visibility",
            json={"visibility": "SHAREABLE"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["visibility"], "SHAREABLE")

        # Check DB state
        self.session.expire_all()
        row = self.session.scalar(
            select(ConstraintModel).where(ConstraintModel.id == constraint.id)
        )
        self.assertIsNotNone(row)
        self.assertEqual(row.visibility, "SHAREABLE")

        # Ensure counterparty CAN see the fact via visible-facts endpoint
        self._authenticate(self._seller_actor())
        list_response = self._request("GET", f"/deals/{self.deal.id}/facts")
        self.assertEqual(list_response.status_code, 200)
        returned_fact_ids = [item["id"] for item in list_response.json()]
        self.assertIn(str(constraint.id), returned_fact_ids)

    def test_alter_fact_visibility_noop_when_visibility_is_unchanged(self) -> None:
        private_message = self._message(
            self.buyer_conversation,
            "private note",
            Visibility.PRIVATE,
            author_user_id=self.buyer_user.id,
        )
        constraint = self._constraint(
            self.buyer.id,
            "payment_terms",
            Visibility.PRIVATE,
            source_message=private_message,
        )
        self.session.commit()
        self._authenticate(self._buyer_actor())

        response = self._request(
            "PATCH",
            f"/deals/{self.deal.id}/facts/{constraint.id}/visibility",
            json={"visibility": "PRIVATE"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["visibility"], "PRIVATE")
        self.assertEqual(response.json()["version"], 0)

    def test_revoked_owner_member_cannot_alter_fact_visibility(self) -> None:
        # Give buyer user active membership in seller as well, so deal participant check passes
        seller_membership = OrganizationMember(
            id=uuid4(),
            organization_id=self.seller.id,
            user_id=self.buyer_user.id,
            role="MEMBER",
            status="ACTIVE",
        )
        self.session.add(seller_membership)

        constraint = self._constraint(self.buyer.id, "quantity", Visibility.PRIVATE)
        self.session.commit()

        # Actor snapshot contains buyer.id in actor.organization_ids
        self._authenticate(self._buyer_actor())

        # Revoke the buyer user's membership in the owner organization (buyer)
        membership = self.session.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == self.buyer.id,
                OrganizationMember.user_id == self.buyer_user.id,
            )
        )
        self.assertIsNotNone(membership)
        membership.status = "REVOKED"
        self.session.commit()

        response = self._request(
            "PATCH",
            f"/deals/{self.deal.id}/facts/{constraint.id}/visibility",
            json={"visibility": "SHAREABLE"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "Only an authorized member of the owner organization can modify fact visibility",
        )

        # Ensure no change committed in DB
        self.session.expire_all()
        row = self.session.scalar(
            select(ConstraintModel).where(ConstraintModel.id == constraint.id)
        )
        self.assertIsNotNone(row)
        self.assertEqual(row.visibility, "PRIVATE")
        self.assertEqual(row.version, 0)

    def test_deleted_owner_member_cannot_alter_fact_visibility(self) -> None:
        seller_membership = OrganizationMember(
            id=uuid4(),
            organization_id=self.seller.id,
            user_id=self.buyer_user.id,
            role="MEMBER",
            status="ACTIVE",
        )
        self.session.add(seller_membership)

        constraint = self._constraint(self.buyer.id, "quantity", Visibility.PRIVATE)
        self.session.commit()

        self._authenticate(self._buyer_actor())

        # Delete membership in owner organization completely
        membership = self.session.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == self.buyer.id,
                OrganizationMember.user_id == self.buyer_user.id,
            )
        )
        self.assertIsNotNone(membership)
        self.session.delete(membership)
        self.session.commit()

        response = self._request(
            "PATCH",
            f"/deals/{self.deal.id}/facts/{constraint.id}/visibility",
            json={"visibility": "SHAREABLE"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "Only an authorized member of the owner organization can modify fact visibility",
        )



if __name__ == "__main__":
    unittest.main()
