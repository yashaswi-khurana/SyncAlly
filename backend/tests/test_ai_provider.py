"""AI provider boundary: offline fake, bounded retries, parsing, and privacy."""

import ast
import asyncio
import json
import time
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

import httpx

from syncally.api.conversations import (
    FactSuggestionResponse,
    _fact_suggestion_guidance,
    _missing_trade_fields,
)
from syncally.application.ai import (
    AIConfigurationError,
    AIPermanentError,
    AIRetryPolicy,
    AISuggestionProvider,
    AITransientError,
    FactExtractionRequest,
    draft_proposal,
    draft_proposal_from_context,
    extract_facts,
    extract_facts_from_context,
    parse_extracted_facts,
    parse_proposed_terms,
    persist_fact_candidates,
)
from syncally.application.conversations import AiContext, CommunicationNotFound
from syncally.application.identity import ActorContext
from syncally.config import Settings
from syncally.domain.ai.contracts import (
    AI_SCHEMA_VERSION,
    ExtractedFact,
    ProposedTerms,
    ValidationStatus,
)
from syncally.domain.conversations import (
    Constraint,
    ConstraintKind,
    ConstraintStatus,
    Message,
    MessageSourceType,
    Visibility,
)
from syncally.domain.deals.deal import Deal
from syncally.domain.shared.identifiers import (
    ConstraintId,
    ConversationId,
    DealId,
    MessageId,
    OrganizationId,
    UserId,
)
from syncally.infrastructure.ai.demo import DemoAISuggestionProvider
from syncally.infrastructure.ai.fake import DeterministicFakeAIProvider
from syncally.infrastructure.ai.openai import MAX_BYTES
from syncally.infrastructure.ai.selection import ConfiguredAIProvider

_AI_MODULE_FILES = (
    Path(__file__).resolve().parents[1] / "src/syncally/application/ai.py",
    Path(__file__).resolve().parents[1] / "src/syncally/infrastructure/ai/fake.py",
)
_FORBIDDEN_IMPORT_ROOTS = frozenset(
    {
        "alembic",
        "anthropic",
        "fastapi",
        "google",
        "http",
        "httpx",
        "langchain",
        "langgraph",
        "openai",
        "requests",
        "socket",
        "sqlalchemy",
        "temporalio",
        "urllib",
    }
)


class FakeCommunicationRepository:
    """Minimal in-memory port covering the calls the AI use cases make."""

    def __init__(
        self, deal: Deal | None, messages: list[Message], constraints: list[Constraint]
    ) -> None:
        self.deal = deal
        self.messages = messages
        self.constraints = constraints
        self.memberships: set[tuple[UUID, UUID]] = set()
        self.conversation_owner: dict[UUID, UUID] = {}
        self.fact_persistence_locks = 0

    def get_deal_for_participant(self, deal_id: UUID, user_id: UUID) -> Deal | None:
        if self.deal is None or self.deal.id != deal_id:
            return None
        parties = (self.deal.buyer_organization_id, self.deal.seller_organization_id)
        return (
            self.deal
            if any((organization_id, user_id) in self.memberships for organization_id in parties)
            else None
        )

    def lock_deal_for_fact_persistence(self, deal_id: UUID, user_id: UUID) -> Deal | None:
        self.fact_persistence_locks += 1
        return self.get_deal_for_participant(deal_id, user_id)

    def add_constraint(self, constraint: Constraint) -> Constraint:
        self.constraints.append(constraint)
        return constraint

    def list_messages(
        self, deal_id: UUID, organization_id: UUID, *, limit: int, offset: int
    ) -> list[Message]:
        visible = [
            message
            for message in self.messages
            if self.conversation_owner[message.conversation_id] == organization_id
            or message.visibility is Visibility.SHAREABLE
        ]
        return visible[offset : offset + limit]

    def list_constraints(
        self, deal_id: UUID, organization_id: UUID, *, limit: int, offset: int
    ) -> list[Constraint]:
        visible = [
            constraint
            for constraint in self.constraints
            if constraint.owner_organization_id == organization_id
            or constraint.visibility is Visibility.SHAREABLE
        ]
        return visible[offset : offset + limit]


def _proposal_payload(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": AI_SCHEMA_VERSION,
        "description": "Widget",
        "quantity": "12",
        "unit": "boxes",
        "unit_price": "2.50",
        "currency": "USD",
        "delivery_destination": "Toronto",
        "delivery_date": "2026-12-01",
    }
    payload.update(updates)
    return payload


def _fact_payload(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": AI_SCHEMA_VERSION,
        "field": "quantity",
        "value": "12",
        "currency_or_unit": "boxes",
        "source": {
            "schema_version": AI_SCHEMA_VERSION,
            "message_id": str(uuid4()),
            "quote": "We need 12 boxes.",
            "unknown_reason": None,
        },
    }
    payload.update(updates)
    return payload


class AISuggestionProviderTests(unittest.TestCase):
    def _remote_config(self, **updates: object) -> Settings:
        values = dict(
            app_env="test", ai_provider="openai", ai_remote_egress_enabled=True,
            openai_model="operator-test-model", openai_api_key="test-only-key",
        )
        values.update(updates)
        return Settings(_env_file=None, **values)

    def _completion(self, payload: object, **message_updates: object) -> httpx.Response:
        message = {"role": "assistant", "content": json.dumps(payload), "refusal": None}
        message.update(message_updates)
        return httpx.Response(200, json={
            "object": "chat.completion", "model": "operator-test-model", "choices": [
                {"index": 0, "finish_reason": "stop", "message": message},
            ],
        })

    def _remote_context(self) -> AiContext:
        return AiContext(self.deal.id, self.buyer_id, (self.buyer_private_message,), tuple(self.constraints))

    def _remote_facts(self) -> dict[str, object]:
        return {"schema_version": 1, "facts": [_fact_payload(source={
            "schema_version": 1, "message_id": str(self.buyer_private_message.id),
            "quote": "We need 12 boxes.", "unknown_reason": None,
        })]}

    def test_remote_config_fail_closed_without_http(self) -> None:
        requests = []
        transport = httpx.MockTransport(lambda request: requests.append(request))
        for updates in (
            {"ai_remote_egress_enabled": False}, {"openai_model": ""},
            {"openai_model": "  "}, {"openai_api_key": ""},
            {"ai_provider": "openai_with_offline_fallback", "ai_remote_egress_enabled": False},
        ):
            with self.subTest(updates=updates), self.assertRaises(AIConfigurationError):
                ConfiguredAIProvider(self._remote_config(**updates), transport=transport)
        self.assertEqual(requests, [])
        nonlocal_offline = self._remote_config(ai_provider="offline")
        nonlocal_offline.app_env = "production"
        with self.assertRaises(AIConfigurationError):
            ConfiguredAIProvider(nonlocal_offline, transport=transport)
        self.assertEqual(requests, [])

    def test_explicit_offline_and_credential_fallback_have_accurate_provenance(self) -> None:
        for mode, reason in (("offline", None), ("openai_with_offline_fallback", "missing_credentials")):
            provider = ConfiguredAIProvider(self._remote_config(ai_provider=mode, openai_api_key=""))
            result = extract_facts_from_context(self._remote_context(), provider)
            self.assertEqual(len(result.candidates), 2)
            self.assertEqual(result.provenance.provider, "offline")
            self.assertEqual(result.provenance.mode, mode)
            self.assertEqual(result.provenance.fallback_reason, reason)
            self.assertIsNone(result.provenance.model)
            self.assertEqual(result.provenance.context_scope, "authorized")

    def test_private_messages_and_constraints_require_both_gates_for_selected_org(self) -> None:
        self.constraints[0].field = "item_description"
        cases = (
            (False, frozenset(), False),
            (True, frozenset(), False),
            (False, frozenset({self.buyer_id}), False),
            (True, frozenset({self.seller_id}), False),
            (True, frozenset({self.buyer_id}), True),
        )
        for allow, ids, expected in cases:
            requests: list[httpx.Request] = []
            def respond(request: httpx.Request) -> httpx.Response:
                requests.append(request)
                return self._completion({"schema_version": 1, "facts": []})
            provider = ConfiguredAIProvider(self._remote_config(
                ai_remote_allow_private=allow, ai_remote_private_organization_ids=ids,
            ), transport=httpx.MockTransport(respond))
            result = extract_facts_from_context(self._remote_context(), provider)
            request_text = requests[0].content.decode()
            self.assertEqual("We need 12 boxes" in request_text, expected)
            self.assertEqual("secret-9999-usd" in request_text, expected)
            self.assertNotIn("seller secret", request_text)
            self.assertEqual(result.provenance.context_scope, "authorized_private" if expected else "shareable_only")

    def test_remote_request_contract_and_grounding_use_exact_transmitted_context(self) -> None:
        requests: list[httpx.Request] = []
        def respond(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return self._completion(self._remote_facts())
        provider = ConfiguredAIProvider(self._remote_config(), transport=httpx.MockTransport(respond))
        excluded = extract_facts_from_context(self._remote_context(), provider)
        self.assertIs(excluded.result.status, ValidationStatus.INVALID)
        self.assertEqual(excluded.candidates, ())
        public = replace(self.buyer_private_message, visibility=Visibility.SHAREABLE)
        accepted = extract_facts_from_context(replace(self._remote_context(), messages=(public,)), provider)
        self.assertIs(accepted.result.status, ValidationStatus.VALID)
        self.assertEqual(accepted.provenance.provider, "openai")
        self.assertEqual(accepted.provenance.model, "operator-test-model")
        raw = json.loads(requests[-1].content)
        self.assertEqual(str(requests[-1].url), "https://api.openai.com/v1/chat/completions")
        self.assertFalse(raw["store"])
        self.assertEqual(raw["max_completion_tokens"], 4096)
        self.assertNotIn("tools", raw)
        self.assertNotIn("test-only-key", requests[-1].content.decode())
        self.assertNotIn(str(self.buyer_id), requests[-1].content.decode())
        minimal = json.loads(raw["messages"][1]["content"])
        self.assertEqual(set(minimal["messages"][0]), {"message_id", "text"})
        def assert_schema(schema: dict) -> None:
            if schema.get("type") == "object":
                self.assertFalse(schema["additionalProperties"])
                self.assertEqual(set(schema["required"]), set(schema["properties"]))
                for child in schema["properties"].values():
                    assert_schema(child)
            if "items" in schema:
                assert_schema(schema["items"])
            for child in schema.get("anyOf", []):
                assert_schema(child)
        assert_schema(raw["response_format"]["json_schema"]["schema"])

    def test_remote_permanent_responses_never_retry_or_fallback(self) -> None:
        variants = [
            httpx.Response(code, json={"error": {"message": "test-only-key private prompt"}})
            for code in (301, 400, 401, 403, 404, 422)
        ] + [
            httpx.Response(429, json={"error": {"code": "insufficient_quota"}}),
            httpx.Response(503, json={"error": {"type": "insufficient_quota"}}),
            self._completion(self._remote_facts(), refusal="private refusal"),
            self._completion(self._remote_facts(), tool_calls=[{"id": "tool"}]),
            httpx.Response(200, content=b'{"choices":[],"choices":[]}'),
            self._completion({"schema_version": 2, "facts": []}),
            self._completion({"schema_version": 1, "facts": [], "extra": True}),
            self._completion({"schema_version": 1, "facts": [_fact_payload(field="unsupported")]}),
            self._completion({"schema_version": 1, "facts": [_fact_payload()] * 101}),
            self._completion({}, content='{"schema_version":1,"facts":[],"facts":[]}'),
            self._completion({}, content='{"schema_version":NaN,"facts":[]}'),
            httpx.Response(200, content=b"not json"),
            self._completion({}, content=None),
            self._completion({}, role="user"),
        ]
        for response in variants:
            requests = []
            def respond(request: httpx.Request) -> httpx.Response:
                requests.append(request)
                return response
            provider = ConfiguredAIProvider(self._remote_config(
                ai_provider="openai_with_offline_fallback",
            ), transport=httpx.MockTransport(respond))
            result = extract_facts_from_context(self._remote_context(), provider, sleep=lambda _: None)
            self.assertIs(result.result.status, ValidationStatus.INVALID)
            self.assertEqual(len(requests), 1)
            self.assertEqual(result.provenance.provider, "openai")
            self.assertIsNone(result.provenance.fallback_reason)
            self.assertNotIn("test-only-key", str(result))
            self.assertNotIn("private prompt", str(result))

    def test_remote_transient_errors_retry_exactly_twice_then_explicit_fallback(self) -> None:
        for status in (429, 500, 502, 503):
            for mode in ("openai", "openai_with_offline_fallback"):
                requests = []
                sleeps = []
                def respond(request: httpx.Request) -> httpx.Response:
                    requests.append(request)
                    return httpx.Response(status, json={"error": {"code": "rate_limit_exceeded"}})
                provider = ConfiguredAIProvider(self._remote_config(ai_provider=mode), transport=httpx.MockTransport(respond))
                if mode == "openai":
                    with self.assertRaises(AITransientError):
                        extract_facts_from_context(self._remote_context(), provider, sleep=sleeps.append)
                else:
                    result = extract_facts_from_context(self._remote_context(), provider, sleep=sleeps.append)
                    self.assertEqual(result.provenance.provider, "offline")
                    self.assertEqual(result.provenance.fallback_reason, "transient_exhausted")
                    self.assertEqual(result.provenance.context_scope, "shareable_only")
                    self.assertEqual(result.candidates, ())
                self.assertEqual(len(requests), 2)
                self.assertEqual(sleeps, [0.5])

    def test_remote_oversized_request_never_sends_and_streamed_response_is_closed(self) -> None:
        requests = []
        def respond(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return self._completion({"schema_version": 1, "facts": []})
        provider = ConfiguredAIProvider(self._remote_config(), transport=httpx.MockTransport(respond))
        huge = replace(self.buyer_private_message, visibility=Visibility.SHAREABLE, body="\U0001f600" * MAX_BYTES)
        result = extract_facts_from_context(replace(self._remote_context(), messages=(huge,)), provider)
        self.assertIs(result.result.status, ValidationStatus.INVALID)
        self.assertEqual(requests, [])

        class Chunks(httpx.AsyncByteStream):
            closed = False
            yielded = 0
            async def __aiter__(self):
                for _ in range(40):
                    self.yielded += 1
                    yield b"x" * 4096
            async def aclose(self):
                self.closed = True
        stream = Chunks()
        provider = ConfiguredAIProvider(self._remote_config(), transport=httpx.MockTransport(
            lambda _: httpx.Response(200, stream=stream),
        ))
        result = extract_facts_from_context(self._remote_context(), provider)
        self.assertIs(result.result.status, ValidationStatus.INVALID)
        self.assertTrue(stream.closed)
        self.assertLess(stream.yielded, 40)
        for headers in ({"content-length": str(MAX_BYTES + 1)}, {"content-encoding": "gzip"}):
            stream = Chunks()
            provider = ConfiguredAIProvider(self._remote_config(), transport=httpx.MockTransport(
                lambda _: httpx.Response(200, headers=headers, stream=stream),
            ))
            result = extract_facts_from_context(self._remote_context(), provider)
            self.assertIs(result.result.status, ValidationStatus.INVALID)
            self.assertEqual(stream.yielded, 0)
            self.assertTrue(stream.closed)

    def test_remote_elapsed_deadline_cancels_and_closes_each_attempt(self) -> None:
        calls = []
        cancellations = []
        async def respond(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            try:
                await asyncio.sleep(1)
            finally:
                cancellations.append(True)
            return self._completion({"schema_version": 1, "facts": []})
        provider = ConfiguredAIProvider(self._remote_config(), transport=httpx.MockTransport(respond))
        start = time.monotonic()
        with self.assertRaises(AITransientError):
            extract_facts_from_context(self._remote_context(), provider,
                policy=AIRetryPolicy(timeout_seconds=0.1, backoff_seconds=0), sleep=lambda _: None)
        self.assertLess(time.monotonic() - start, 0.75)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(cancellations), 2)

    def test_remote_network_errors_safe_and_unsupported_transport_permanent(self) -> None:
        for error_type, count in ((httpx.ConnectError, 2), (httpx.ReadTimeout, 2), (httpx.UnsupportedProtocol, 1)):
            calls = []
            def respond(request: httpx.Request) -> httpx.Response:
                calls.append(request)
                raise error_type("test-only-key private exception", request=request)
            provider = ConfiguredAIProvider(self._remote_config(), transport=httpx.MockTransport(respond))
            if count == 2:
                with self.assertRaises(AITransientError) as captured:
                    extract_facts_from_context(self._remote_context(), provider, sleep=lambda _: None)
                self.assertNotIn("private exception", str(captured.exception))
                self.assertIsNone(captured.exception.__cause__)
            else:
                result = extract_facts_from_context(self._remote_context(), provider)
                self.assertIs(result.result.status, ValidationStatus.INVALID)
            self.assertEqual(len(calls), count)

    def test_remote_proposal_requires_grounded_citations_for_every_populated_field(self) -> None:
        context = self._demo_context("Item: Widget, 12 boxes at USD 2.50, deliver to Toronto by 2026-12-01.")
        context = replace(context, messages=tuple(replace(message, visibility=Visibility.SHAREABLE) for message in context.messages))
        facts = DemoAISuggestionProvider().extract_facts(FactExtractionRequest(context), timeout_seconds=1)
        citations = [{
            "schema_version": 1, "field": fact.field.value, "value": fact.value,
            "currency_or_unit": fact.currency_or_unit,
            "source": {"schema_version": 1, "message_id": str(fact.source.message_id), "quote": fact.source.quote, "unknown_reason": None},
        } for fact in facts]
        payload = {"schema_version": 1, "insufficient_context": False,
                   "proposal": _proposal_payload(), "citations": citations}
        responses = [payload,
            {**payload, "citations": citations[:-1]},
            {**payload, "proposal": _proposal_payload(quantity="13")},
            {**payload, "proposal": _proposal_payload(currency="EUR")},
            {**payload, "proposal": _proposal_payload(quantity="1e100")},
            {**payload, "proposal": _proposal_payload(quantity="1.2e1")},
            {**payload, "proposal": _proposal_payload(delivery_date="20261201")},
            {**payload, "insufficient_context": True, "proposal": None, "citations": []},
        ]
        for index, output in enumerate(responses):
            calls = []
            def respond(request: httpx.Request) -> httpx.Response:
                calls.append(request)
                return self._completion(output)
            provider = ConfiguredAIProvider(self._remote_config(ai_provider="openai_with_offline_fallback"), transport=httpx.MockTransport(respond))
            result = draft_proposal_from_context(context, provider)
            self.assertEqual(result.result.status is ValidationStatus.VALID, index == 0)
            self.assertEqual(len(calls), 1)
            self.assertIsNone(result.provenance.fallback_reason)
            if index == 0:
                self.assertEqual(result.proposal, self.proposal)

    def test_remote_currency_requires_explicit_noncontradictory_cited_usd(self) -> None:
        for price, valid in (
            ("CAD $2.50", False), ("EUR $2.50", False),
            ("AUD 2.50 dollars", False), ("$2.50", False),
            ("2.50 dollars", False), ("USD 2.50", True),
            ("USD $2.50", True), ("2.50 USD", True),
            ("CAD USD 2.50", False),
        ):
            with self.subTest(price=price):
                context = self._demo_context(f"Item: Widget, 12 boxes at {price}, deliver to Toronto by 2026-12-01.")
                context = replace(context, messages=tuple(replace(message, visibility=Visibility.SHAREABLE) for message in context.messages))
                baseline = self._demo_context("Item: Widget, 12 boxes at USD 2.50, deliver to Toronto by 2026-12-01.")
                facts = DemoAISuggestionProvider().extract_facts(FactExtractionRequest(baseline), timeout_seconds=1)
                citations = [{
                    "schema_version": 1, "field": fact.field.value, "value": fact.value,
                    "currency_or_unit": fact.currency_or_unit,
                    "source": {"schema_version": 1, "message_id": str(context.messages[0].id),
                               "quote": price if fact.field.value == "unit_price" else fact.source.quote,
                               "unknown_reason": None},
                } for fact in facts]
                for operation in ("facts", "proposal"):
                    calls = []
                    output = {"schema_version": 1, "facts": citations} if operation == "facts" else {
                        "schema_version": 1, "insufficient_context": False,
                        "proposal": _proposal_payload(), "citations": citations,
                    }
                    def respond(request: httpx.Request) -> httpx.Response:
                        calls.append(request)
                        return self._completion(output)
                    provider = ConfiguredAIProvider(self._remote_config(ai_provider="openai_with_offline_fallback"), transport=httpx.MockTransport(respond))
                    result = extract_facts_from_context(context, provider) if operation == "facts" else draft_proposal_from_context(context, provider)
                    self.assertEqual(result.result.status is ValidationStatus.VALID, valid)
                    self.assertEqual(len(calls), 1)
                    self.assertIsNone(result.provenance.fallback_reason)
                    if not valid:
                        if operation == "facts":
                            self.assertEqual(result.candidates, ())
                        else:
                            self.assertIsNone(result.proposal)

    def test_remote_currency_cannot_borrow_uncited_context_or_hide_qualifiers(self) -> None:
        for body, quote in (
            ("CAD $2.50", "$2.50"),
            ("EUR $2.50", "$2.50"),
            ("AUD 2.50 dollars", "2.50 dollars"),
            ("USD budget, price $2.50", "$2.50"),
            ("CAD price USD 2.50", "USD 2.50"),
            ("Budget USD 2.50; actual unit price $2.50.", "Budget USD 2.50; actual unit price $2.50."),
            ("Budget USD 2.50; actual unit price $2.50.", "USD 2.50"),
            ("Budget USD 2.50; actual unit price $2.50.", "2.50"),
            ("Budget USD 2.50; actual unit price USD 2.50.", "USD 2.50"),
            ("Payment USD 2.50 per unit", "USD 2.50"),
            ("Total USD 2.50 per unit", "USD 2.50"),
        ):
            with self.subTest(body=body, quote=quote):
                context = self._demo_context(body)
                context = replace(context, messages=tuple(replace(message, visibility=Visibility.SHAREABLE) for message in context.messages))
                fact = _fact_payload(field="unit_price", value="2.50", currency_or_unit="USD", source={
                    "schema_version": 1, "message_id": str(context.messages[0].id),
                    "quote": quote, "unknown_reason": None,
                })
                calls = []
                def respond(request: httpx.Request) -> httpx.Response:
                    calls.append(request)
                    return self._completion({"schema_version": 1, "facts": [fact]})
                provider = ConfiguredAIProvider(self._remote_config(ai_provider="openai_with_offline_fallback"), transport=httpx.MockTransport(respond))
                result = extract_facts_from_context(context, provider)
                self.assertIs(result.result.status, ValidationStatus.INVALID)
                self.assertEqual(result.candidates, ())
                self.assertEqual(len(calls), 1)
                self.assertIsNone(result.provenance.fallback_reason)

    def test_retry_elapsed_budget_disallows_late_success(self) -> None:
        from syncally.application.ai import call_with_bounded_retry
        with patch("syncally.application.ai.monotonic", side_effect=[0, 0, 21, 21, 21]):
            with self.assertRaises(AITransientError):
                call_with_bounded_retry(lambda: "late", AIRetryPolicy(), sleep=lambda _: None)

    def test_remote_envelope_finish_model_and_choices_are_strict(self) -> None:
        for mutate in (
            lambda body: body.update(model=None),
            lambda body: body.update(choices=[None]),
            lambda body: body["choices"][0].update(index=False),
            lambda body: body["choices"][0].update(finish_reason="length"),
            lambda body: body["choices"][0].update(finish_reason="content_filter"),
        ):
            envelope = self._completion({"schema_version": 1, "facts": []}).json()
            mutate(envelope)
            calls = []
            def respond(request: httpx.Request) -> httpx.Response:
                calls.append(request)
                return httpx.Response(200, json=envelope)
            provider = ConfiguredAIProvider(self._remote_config(ai_provider="openai_with_offline_fallback"), transport=httpx.MockTransport(respond))
            result = extract_facts_from_context(self._remote_context(), provider)
            self.assertIs(result.result.status, ValidationStatus.INVALID)
            self.assertEqual(len(calls), 1)
            self.assertIsNone(result.provenance.fallback_reason)

    def test_remote_reports_resolved_completion_model(self) -> None:
        envelope = self._completion({"schema_version": 1, "facts": []}).json()
        envelope["model"] = "operator-test-resolved-snapshot"
        provider = ConfiguredAIProvider(self._remote_config(), transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json=envelope),
        ))
        result = extract_facts_from_context(self._remote_context(), provider)
        self.assertEqual(result.provenance.model, "operator-test-resolved-snapshot")

    def test_remote_stream_timeout_closes_open_responses(self) -> None:
        streams = []
        class SlowStream(httpx.AsyncByteStream):
            closed = False
            async def __aiter__(self):
                yield b"{"
                await asyncio.sleep(1)
                yield b"}"
            async def aclose(self):
                self.closed = True
        def respond(_: httpx.Request) -> httpx.Response:
            stream = SlowStream()
            streams.append(stream)
            return httpx.Response(200, stream=stream)
        provider = ConfiguredAIProvider(self._remote_config(), transport=httpx.MockTransport(respond))
        with self.assertRaises(AITransientError):
            extract_facts_from_context(self._remote_context(), provider,
                policy=AIRetryPolicy(timeout_seconds=0.1, backoff_seconds=0), sleep=lambda _: None)
        self.assertEqual(len(streams), 2)
        self.assertTrue(all(stream.closed for stream in streams))

    def test_stray_secret_does_not_enable_remote_provider_or_egress(self) -> None:
        from syncally.config import Settings

        configured = Settings(_env_file=None, app_env="test", openai_api_key="test-only-key")
        self.assertEqual(configured.ai_provider, "offline")
        self.assertFalse(configured.ai_remote_egress_enabled)
        self.assertFalse(configured.ai_remote_allow_private)
        self.assertEqual(configured.ai_remote_private_organization_ids, frozenset())
        self.assertNotIn("test-only-key", repr(configured))

    def setUp(self) -> None:
        self.buyer_id = OrganizationId(uuid4())
        self.seller_id = OrganizationId(uuid4())
        self.user_id = uuid4()
        self.deal = Deal(
            id=DealId(uuid4()),
            buyer_organization_id=self.buyer_id,
            seller_organization_id=self.seller_id,
            created_at=datetime(2026, 10, 18, tzinfo=UTC),
        )
        self.buyer_conversation_id = ConversationId(uuid4())
        self.seller_conversation_id = ConversationId(uuid4())

        self.buyer_private_message = self._message(
            self.buyer_conversation_id,
            Visibility.PRIVATE,
            "We need 12 boxes. Please confirm.",
        )
        self.seller_private_message = self._message(
            self.seller_conversation_id, Visibility.PRIVATE, "seller secret cost basis"
        )
        self.messages = [self.buyer_private_message, self.seller_private_message]

        self.constraints = [
            Constraint(
                id=ConstraintId(uuid4()),
                deal_id=self.deal.id,
                owner_organization_id=self.buyer_id,
                field="max_budget",
                typed_value="secret-9999-usd",
                kind=ConstraintKind.HARD_LIMIT,
                visibility=Visibility.PRIVATE,
                created_at=datetime(2026, 10, 18, tzinfo=UTC),
                source_span="n/a",
            )
        ]

        self.repository = FakeCommunicationRepository(self.deal, self.messages, self.constraints)
        self.repository.memberships.add((self.buyer_id, self.user_id))
        self.repository.conversation_owner[self.buyer_conversation_id] = self.buyer_id
        self.repository.conversation_owner[self.seller_conversation_id] = self.seller_id
        self.actor = ActorContext(self.user_id, frozenset({self.buyer_id}))

        self.proposal = ProposedTerms.from_mapping(_proposal_payload())

    def _message(self, conversation_id: UUID, visibility: Visibility, body: str) -> Message:
        return Message(
            id=MessageId(uuid4()),
            conversation_id=conversation_id,
            author_user_id=UserId(uuid4()),
            author_agent_id=None,
            body=body,
            visibility=visibility,
            source_type=MessageSourceType.USER,
            created_at=datetime(2026, 10, 18, tzinfo=UTC),
        )

    def _grounded_fact(self, message: Message, *, value: str = "12") -> ExtractedFact:
        return ExtractedFact.from_mapping(
            _fact_payload(
                value=value,
                source={
                    "schema_version": AI_SCHEMA_VERSION,
                    "message_id": str(message.id),
                    "quote": "We need 12 boxes.",
                    "unknown_reason": None,
                },
            )
        )

    def _extract(self, provider: DeterministicFakeAIProvider, **policy_updates: object):
        policy = AIRetryPolicy(**policy_updates)
        return extract_facts(
            self.actor,
            self.deal.id,
            self.buyer_id,
            self.repository,
            provider,
            policy=policy,
            sleep=lambda _seconds: None,
        )

    def _demo_context(self, body: str) -> AiContext:
        message = self._message(self.buyer_conversation_id, Visibility.PRIVATE, body)
        return AiContext(
            deal_id=self.deal.id,
            organization_id=self.buyer_id,
            messages=(message,),
            constraints=(),
        )

    def _demo_extract(self, body: str) -> tuple[ExtractedFact, ...]:
        context = self._demo_context(body)
        return DemoAISuggestionProvider().extract_facts(
            FactExtractionRequest(context), timeout_seconds=1.0
        )

    def test_demo_provider_extracts_colloquial_trade_terms(self) -> None:
        facts = self._demo_extract(
            "We're buying 1,000 bags of coffee at USD 45/unit; "
            "please deliver at Port of Seattle by November 15, 2026."
        )
        values = {fact.field.value: fact.value for fact in facts}

        self.assertEqual(values["item_description"], "coffee")
        self.assertEqual(values["quantity"], "1000")
        self.assertEqual(values["unit"], "bags")
        self.assertEqual(values["unit_price"], "45")
        self.assertEqual(values["delivery_destination"], "Port of Seattle")
        self.assertEqual(values["delivery_date"], "2026-11-15")

    def test_colloquial_demo_facts_pass_grounding_validation(self) -> None:
        examples = (
            (
                "We're buying 1,000 bags of coffee at $45 each; "
                "ship to Port of Seattle by November 15, 2026.",
                {"item_description", "quantity", "unit", "unit_price", "delivery_destination", "delivery_date"},
            ),
            ("Item: copper wire at 45 dollars.", {"item_description", "unit_price"}),
            ("Item: steel at USD 45.", {"item_description", "unit_price"}),
            ("Item: rice at 45 USD/unit.", {"item_description", "unit_price"}),
            ("Item: beans at 45 each.", {"item_description", "unit_price"}),
            (
                "Order of 50 tons of grain; destination: Toronto, delivery date: 2026-11-15.",
                {"item_description", "quantity", "unit", "delivery_destination", "delivery_date"},
            ),
            (
                "Order of grain; ship to Toronto by Nov 15 2026.",
                {"item_description", "delivery_destination", "delivery_date"},
            ),
        )
        provider = DemoAISuggestionProvider()
        for body, expected_fields in examples:
            with self.subTest(body=body):
                result = extract_facts_from_context(self._demo_context(body), provider)
                self.assertIs(result.result.status, ValidationStatus.VALID)
                self.assertEqual(
                    {candidate.fact.field.value for candidate in result.candidates},
                    expected_fields,
                )

    def test_demo_provider_recognizes_price_and_quantity_variants(self) -> None:
        examples = (
            ("item: copper wire at $45", "45"),
            ("item: copper wire costs 45 dollars", "45"),
            ("item: copper wire priced at 45 USD/unit", "45"),
            ("item: copper wire at 45 each", "45"),
            (
                "Item: Widget, 12 boxes at USD 2.50, deliver to Toronto by 2026-12-01.",
                "2.50",
            ),
        )
        for message, expected_price in examples:
            with self.subTest(message=message):
                facts = self._demo_extract(message)
                values = {fact.field.value: fact.value for fact in facts}
                self.assertEqual(values["unit_price"], expected_price)

        quantities = ("500 units", "1,000 cases", "50 tons", "200 bags")
        for quantity in quantities:
            with self.subTest(quantity=quantity):
                facts = self._demo_extract(f"Order of grain, quantity {quantity}.")
                values = {fact.field.value: fact.value for fact in facts}
                self.assertEqual(values["quantity"], quantity.split()[0].replace(",", ""))

    def test_demo_provider_recognizes_item_destination_and_date_phrasings(self) -> None:
        examples = (
            ("Order of steel rods; ship to Toronto by Nov 15 2026.", "steel rods", "Toronto"),
            ("Supplying cocoa beans, destination: Accra, 2026-11-15.", "cocoa beans", "Accra"),
            ("We are buying rice; deliver at Port Klang by Nov 15 2026.", "rice", "Port Klang"),
        )
        for message, expected_item, expected_destination in examples:
            with self.subTest(message=message):
                facts = self._demo_extract(message)
                values = {fact.field.value: fact.value for fact in facts}
                self.assertEqual(values["item_description"], expected_item)
                self.assertEqual(values["delivery_destination"], expected_destination)
                self.assertEqual(values["delivery_date"], "2026-11-15")

    def test_demo_provider_leaves_ranges_unknown_and_keeps_qualified_terms(self) -> None:
        range_messages = (
            "Item: steel, 500-600 units at $45-$50, ship to Toronto by November 15, 2026.",
            "Item: steel, 500 to 600 units at USD 45 to 50, ship to Toronto by November 15, 2026.",
            "Item: steel, between 500 and 600 units at between $45 and $50, "
            "ship to Toronto by November 15, 2026.",
            "Item: steel, about 500 units at about $45 each.",
            "Item: steel, at least 500 units for $45+ each.",
            "Item: steel, up to 500 cases priced at $45 maximum.",
            "Item: steel, 500 or 600 units at $45 or $50.",
            "Item: steel, 500 units and up at $45 and up.",
        )
        for message in range_messages:
            with self.subTest(message=message):
                values = {fact.field.value: fact.value for fact in self._demo_extract(message)}
                self.assertNotIn("quantity", values)
                self.assertNotIn("unit", values)
                self.assertNotIn("unit_price", values)

        values = {
            fact.field.value: fact.value
            for fact in self._demo_extract(
                "Item: steel, 1.5 metric tons at USD 45 per unit; "
                "destination: New York, NY; delivery by November 15, 2026."
            )
        }
        self.assertEqual(values["quantity"], "1.5")
        self.assertEqual(values["unit"], "metric tons")
        self.assertEqual(values["delivery_destination"], "New York, NY")

    def test_demo_provider_skips_ranges_but_keeps_later_exact_values(self) -> None:
        message = (
            "Item: steel, tentative 500-600 units and $45-$50; "
            "final quantity 550 units at USD 47 each."
        )
        result = extract_facts_from_context(
            self._demo_context(message), DemoAISuggestionProvider()
        )

        self.assertIs(result.result.status, ValidationStatus.VALID)
        values = {candidate.fact.field.value: candidate.fact.value for candidate in result.candidates}
        self.assertEqual(values["quantity"], "550")
        self.assertEqual(values["unit"], "units")
        self.assertEqual(values["unit_price"], "47")

        qualified = extract_facts_from_context(
            self._demo_context(
                "Item: steel, about 500 units and about $45; "
                "final quantity 450 units at $47 each."
            ),
            DemoAISuggestionProvider(),
        )
        values = {
            candidate.fact.field.value: candidate.fact.value for candidate in qualified.candidates
        }
        self.assertEqual(values["quantity"], "450")
        self.assertEqual(values["unit_price"], "47")

    def test_demo_provider_does_not_treat_a_currency_code_as_a_region(self) -> None:
        values = {
            fact.field.value: fact.value
            for fact in self._demo_extract("Item: steel; destination: Toronto, USD 45 each.")
        }

        self.assertEqual(values["delivery_destination"], "Toronto")
        self.assertEqual(values["unit_price"], "45")

    def test_demo_provider_skips_fee_amounts_and_approximate_prices(self) -> None:
        values = {
            fact.field.value: fact.value
            for fact in self._demo_extract(
                "The handling fee is $12, with a $3 delivery fee; "
                "copper wire unit price is $45 each."
            )
        }
        self.assertEqual(values["unit_price"], "45")

        approximate = self._demo_extract("Item: copper wire, unit price is $45 or so.")
        self.assertNotIn("unit_price", {fact.field.value for fact in approximate})

    def test_demo_provider_cleans_decimal_quantities_and_matches_flexible_units(self) -> None:
        examples = (
            ("Order of 2.5 tons of rice, USD 45 each.", "rice", "tons", "2.5"),
            ("Item: steel 1.5   metric   tons at $45.", "steel", "metric tons", "1.5"),
        )
        provider = DemoAISuggestionProvider()
        for body, expected_item, expected_unit, expected_quantity in examples:
            with self.subTest(body=body):
                result = extract_facts_from_context(self._demo_context(body), provider)
                self.assertIs(result.result.status, ValidationStatus.VALID)
                values = {candidate.fact.field.value: candidate.fact.value for candidate in result.candidates}
                self.assertEqual(values["item_description"], expected_item)
                self.assertEqual(values["quantity"], expected_quantity)
                self.assertEqual(values["unit"], expected_unit)

    def test_demo_provider_keeps_destination_boundaries_and_full_regions(self) -> None:
        examples = (
            ("Ship to Toronto at USD 45 each.", "Toronto"),
            ("Ship to Toronto, California by 2026-11-15.", "Toronto, California"),
            ("Ship to Toronto, ON by 2026-11-15.", "Toronto, ON"),
            ("Ship to Toronto, Ontario by 2026-11-15.", "Toronto, Ontario"),
            ("Ship to Toronto, on by 2026-11-15.", "Toronto"),
            ("Ship to Toronto, now.", "Toronto"),
            ("Ship to Toronto, pls.", "Toronto"),
        )
        for body, expected in examples:
            with self.subTest(body=body):
                facts = self._demo_extract(body)
                values = {fact.field.value: fact.value for fact in facts}
                self.assertEqual(values["delivery_destination"], expected)

    def test_demo_provider_uses_delivery_dates_not_unrelated_event_dates(self) -> None:
        body = (
            "The trade meeting is on November 1, 2026; "
            "ship to Toronto by December 15, 2026."
        )
        values = {fact.field.value: fact.value for fact in self._demo_extract(body)}
        self.assertEqual(values["delivery_date"], "2026-12-15")
        self.assertNotIn("delivery_date", {
            fact.field.value for fact in self._demo_extract("Meeting on November 1, 2026.")
        })

    def test_fact_suggestion_response_reports_missing_trade_fields(self) -> None:
        detected = [
            SimpleNamespace(field="item_description", status=ConstraintStatus.EXTRACTED),
            SimpleNamespace(field="quantity", status=ConstraintStatus.CONFIRMED),
            SimpleNamespace(field="unit_price", status=ConstraintStatus.REJECTED),
            SimpleNamespace(
                field="delivery_destination",
                status=ConstraintStatus.NEEDS_CLARIFICATION,
            ),
        ]
        missing = _missing_trade_fields(detected)
        response = FactSuggestionResponse(
            status="VALID",
            issues=[],
            facts=[],
            missing_fields=missing,
            guidance_message=_fact_suggestion_guidance(missing),
        )

        self.assertEqual(
            response.missing_fields,
            ["unit", "unit_price", "delivery_destination", "delivery_date"],
        )
        self.assertTrue(
            response.guidance_message.startswith(
                "Add the missing details: unit, unit price, delivery destination, delivery date."
            )
        )
        self.assertIn("YYYY-MM-DD", response.guidance_message)

    def test_fact_candidate_persistence_checks_duplicates_under_deal_lock(self) -> None:
        result = self._extract(
            DeterministicFakeAIProvider(
                facts=[self._grounded_fact(self.buyer_private_message)]
            )
        )

        first = persist_fact_candidates(self.actor, self.deal.id, result, self.repository)
        second = persist_fact_candidates(self.actor, self.deal.id, result, self.repository)

        self.assertEqual(len(first), 1)
        self.assertEqual([fact.id for fact in second], [first[0].id])
        self.assertEqual(self.repository.fact_persistence_locks, 2)

    def test_deterministic_fake_satisfies_the_port_contract(self) -> None:
        provider = DeterministicFakeAIProvider()

        self.assertIsInstance(provider, AISuggestionProvider)

    def test_ai_modules_import_no_network_or_provider_sdks(self) -> None:
        imported: set[str] = set()
        for path in _AI_MODULE_FILES:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])

        self.assertEqual(imported & _FORBIDDEN_IMPORT_ROOTS, set())

    def test_extract_facts_binds_grounded_candidates_to_the_owner(self) -> None:
        provider = DeterministicFakeAIProvider(
            facts=[self._grounded_fact(self.buyer_private_message)]
        )

        result = self._extract(provider)

        self.assertIs(result.result.status, ValidationStatus.VALID)
        self.assertEqual(len(result.candidates), 1)
        candidate = result.candidates[0]
        self.assertEqual(candidate.owner_organization_id, self.buyer_id)
        self.assertEqual(candidate.source_message_id, self.buyer_private_message.id)

    def test_extract_facts_without_suggestions_is_valid_and_empty(self) -> None:
        result = self._extract(DeterministicFakeAIProvider())

        self.assertIs(result.result.status, ValidationStatus.VALID)
        self.assertEqual(result.candidates, ())

    def test_ungrounded_provider_output_is_rejected_and_never_returned(self) -> None:
        fabricated = self._grounded_fact(self.seller_private_message)
        provider = DeterministicFakeAIProvider(facts=[fabricated])

        result = self._extract(provider)

        self.assertIs(result.result.status, ValidationStatus.INVALID)
        self.assertEqual(result.candidates, ())
        self.assertEqual(result.result.issues[0].code, "AI_OUTPUT_UNGROUNDED")

    def test_transient_failure_retries_within_the_bound(self) -> None:
        sleeps: list[float] = []
        provider = DeterministicFakeAIProvider(
            facts=[self._grounded_fact(self.buyer_private_message)],
            failures=[AITransientError, AITransientError],
        )
        policy = AIRetryPolicy(max_attempts=3, backoff_seconds=0.25)

        result = extract_facts(
            self.actor,
            self.deal.id,
            self.buyer_id,
            self.repository,
            provider,
            policy=policy,
            sleep=sleeps.append,
        )

        self.assertIs(result.result.status, ValidationStatus.VALID)
        self.assertEqual(provider.call_count, 3)
        self.assertEqual(sleeps, [0.25, 0.25])

    def test_transient_failure_past_the_bound_raises_without_candidates(self) -> None:
        provider = DeterministicFakeAIProvider(
            facts=[self._grounded_fact(self.buyer_private_message)],
            failures=[AITransientError, AITransientError, AITransientError],
        )

        with self.assertRaises(AITransientError):
            self._extract(provider)

        self.assertEqual(provider.call_count, 2)

    def test_permanent_failure_is_not_retried_and_yields_an_invalid_result(self) -> None:
        provider = DeterministicFakeAIProvider(failures=[AIPermanentError])

        result = self._extract(provider)

        self.assertIs(result.result.status, ValidationStatus.INVALID)
        self.assertEqual(result.candidates, ())
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(result.result.issues[0].code, "AI_OUTPUT_INVALID")

    def test_timeout_is_passed_to_the_provider(self) -> None:
        provider = DeterministicFakeAIProvider(
            facts=[self._grounded_fact(self.buyer_private_message)]
        )

        self._extract(provider, timeout_seconds=7.5)

        self.assertEqual(provider.last_timeout_seconds, 7.5)

    def test_provider_receives_only_the_authorized_context(self) -> None:
        provider = DeterministicFakeAIProvider()

        self._extract(provider)

        request = provider.last_request
        assert request is not None
        delivered = {message.id for message in request.context.messages}
        self.assertIn(self.buyer_private_message.id, delivered)
        self.assertNotIn(self.seller_private_message.id, delivered)
        rendered = repr(request)
        self.assertNotIn("secret cost basis", rendered)
        self.assertNotIn("secret-9999-usd", rendered)

    def test_ai_use_case_fails_closed_for_an_outsider(self) -> None:
        outsider = ActorContext(uuid4(), frozenset({OrganizationId(uuid4())}))

        with self.assertRaises(CommunicationNotFound):
            extract_facts(
                outsider,
                self.deal.id,
                self.buyer_id,
                self.repository,
                DeterministicFakeAIProvider(),
                sleep=lambda _seconds: None,
            )

    def test_draft_proposal_returns_a_non_binding_draft(self) -> None:
        provider = DeterministicFakeAIProvider(proposal=self.proposal)

        result = draft_proposal(
            self.actor,
            self.deal.id,
            self.buyer_id,
            self.repository,
            provider,
            sleep=lambda _seconds: None,
        )

        self.assertIs(result.result.status, ValidationStatus.VALID)
        self.assertEqual(result.proposal, self.proposal)

    def test_invalid_proposal_output_is_rejected(self) -> None:
        provider = DeterministicFakeAIProvider(failures=[AIPermanentError])

        result = draft_proposal(
            self.actor,
            self.deal.id,
            self.buyer_id,
            self.repository,
            provider,
            sleep=lambda _seconds: None,
        )

        self.assertIs(result.result.status, ValidationStatus.INVALID)
        self.assertIsNone(result.proposal)
        self.assertEqual(provider.call_count, 1)

    def test_retry_policy_rejects_invalid_limits(self) -> None:
        with self.assertRaises(ValueError):
            AIRetryPolicy(max_attempts=0)
        with self.assertRaises(ValueError):
            AIRetryPolicy(timeout_seconds=0)
        with self.assertRaises(ValueError):
            AIRetryPolicy(backoff_seconds=-1)

    def test_parse_helpers_validate_with_the_s4_01_schemas(self) -> None:
        facts = parse_extracted_facts([_fact_payload()])
        self.assertEqual(len(facts), 1)
        self.assertEqual(
            parse_proposed_terms(_proposal_payload()).unit_price, self.proposal.unit_price
        )

        with self.assertRaises(AIPermanentError):
            parse_extracted_facts([_fact_payload(field="bank_account")])
        with self.assertRaises(AIPermanentError):
            parse_proposed_terms(_proposal_payload(currency="CAD"))

    def test_parse_errors_do_not_echo_provider_payload_content(self) -> None:
        secret = "sk-live-do-not-log-1234567890"

        with self.assertRaises(AIPermanentError) as raised:
            parse_extracted_facts([_fact_payload(value=secret, field="quantity")])

        self.assertNotIn(secret, str(raised.exception))


if __name__ == "__main__":
    unittest.main()
