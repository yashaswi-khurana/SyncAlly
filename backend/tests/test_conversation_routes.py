"""HTTP contract tests for deal message and fact-review routes."""

import asyncio
import logging
import unittest
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.auth import get_current_actor
from syncally.api.main import app
from syncally.application.identity import ActorContext
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
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import (
    AuditEvent,
    Base,
    Constraint as ConstraintModel,
    Deal,
    Organization,
    OrganizationMember,
    User,
)
from syncally.infrastructure.repositories import SqlAlchemyCommunicationRepository


class ConversationRouteTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
