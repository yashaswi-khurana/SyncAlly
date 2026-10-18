"""AI provider boundary: offline fake, bounded retries, parsing, and privacy."""

import ast
import unittest
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from syncally.application.ai import (
    AIPermanentError,
    AIRetryPolicy,
    AISuggestionProvider,
    AITransientError,
    draft_proposal,
    extract_facts,
    parse_extracted_facts,
    parse_proposed_terms,
)
from syncally.application.conversations import CommunicationNotFound
from syncally.application.identity import ActorContext
from syncally.domain.ai.contracts import (
    AI_SCHEMA_VERSION,
    ExtractedFact,
    ProposedTerms,
    ValidationStatus,
)
from syncally.domain.conversations import (
    Constraint,
    ConstraintKind,
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
from syncally.infrastructure.ai.fake import DeterministicFakeAIProvider

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

    def get_deal_for_participant(self, deal_id: UUID, user_id: UUID) -> Deal | None:
        if self.deal is None or self.deal.id != deal_id:
            return None
        parties = (self.deal.buyer_organization_id, self.deal.seller_organization_id)
        return (
            self.deal
            if any((organization_id, user_id) in self.memberships for organization_id in parties)
            else None
        )

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

        self.assertEqual(provider.call_count, 3)

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
