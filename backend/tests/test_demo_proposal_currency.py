import unittest
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from syncally.application.ai import AIPermanentError, ProposalDraftRequest
from syncally.application.conversations import AiContext
from syncally.domain.conversations import (
    Constraint,
    ConstraintKind,
    Message,
    MessageSourceType,
    Visibility,
)
from syncally.infrastructure.ai.demo import DemoAISuggestionProvider


def context_with_price(currency):
    deal_id, organization_id = uuid4(), uuid4()
    values = {
        "item_description": "widgets", "quantity": "12", "unit": "boxes",
        "unit_price": "250", "delivery_destination": "Toronto",
    }
    constraints = tuple(
        Constraint(
            id=uuid4(), deal_id=deal_id, owner_organization_id=organization_id,
            field=field, typed_value=value, kind=ConstraintKind.INFORMATIONAL,
            visibility=Visibility.SHAREABLE, created_at=datetime.now(UTC),
            currency_or_unit=currency if field == "unit_price" else None,
            source_span="manual entry",
        )
        for field, value in values.items()
    )
    return AiContext(deal_id, organization_id, (), constraints)


class DemoProposalCurrencyTests(unittest.TestCase):
    def test_stored_price_currency_is_preserved(self):
        for currency in ("INR", "USD", "EUR"):
            with self.subTest(currency=currency):
                proposal = DemoAISuggestionProvider().draft_proposal(
                    ProposalDraftRequest(context_with_price(currency)), timeout_seconds=1,
                )
                self.assertEqual(proposal.currency, currency)

    def test_missing_price_currency_does_not_invent_usd(self):
        with self.assertRaises(AIPermanentError):
            DemoAISuggestionProvider().draft_proposal(
                ProposalDraftRequest(context_with_price(None)), timeout_seconds=1,
            )

    def test_extracted_price_uses_its_own_currency(self):
        context = context_with_price("INR")
        message = Message(
            id=uuid4(), conversation_id=uuid4(), author_user_id=uuid4(),
            author_agent_id=None, body="The unit price is USD 12.",
            visibility=Visibility.SHAREABLE, source_type=MessageSourceType.USER,
            created_at=datetime.now(UTC),
        )
        proposal = DemoAISuggestionProvider().draft_proposal(
            ProposalDraftRequest(replace(context, messages=(message,))), timeout_seconds=1,
        )
        self.assertEqual(str(proposal.unit_price), "12")
        self.assertEqual(proposal.currency, "USD")
