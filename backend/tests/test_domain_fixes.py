from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
from unittest import TestCase
from uuid import uuid4

from syncally.domain.agreements.trade_terms import (
    PaymentTerm,
    ShipmentTerm,
    TradeLineItem,
    TradeTerms,
)
from syncally.domain.negotiation.proposal import (
    NegotiationSession,
    NegotiationSubmissionOutcome,
    Proposal,
    ProposalStatus,
)
from syncally.domain.payments.intent import (
    PaymentIntent,
    PaymentIntentStatus,
    PaymentMilestone,
)
from syncally.domain.shared.errors import InvalidTransition, InvariantViolation
from syncally.domain.shared.identifiers import (
    AgreementVersionId,
    DealId,
    NegotiationSessionId,
    OrganizationId,
    PaymentIntentId,
    PaymentMilestoneId,
    ProposalId,
    UserId,
)
from syncally.domain.shared.money import Money, canonical_decimal


def build_terms(
    *,
    line_items: tuple[TradeLineItem, ...] | list[TradeLineItem] | None = None,
    shipments: tuple[ShipmentTerm, ...] | list[ShipmentTerm] | None = None,
    payment_terms: tuple[PaymentTerm, ...] | list[PaymentTerm] | None = None,
    buyer_id: OrganizationId | None = None,
    seller_id: OrganizationId | None = None,
) -> TradeTerms:
    buyer = buyer_id or OrganizationId(uuid4())
    seller = seller_id or OrganizationId(uuid4())
    return TradeTerms(
        buyer_id=buyer,
        seller_id=seller,
        line_items=line_items
        if line_items is not None
        else (TradeLineItem("Desk", Decimal("1"), "each", Money(Decimal("10"), "USD")),),
        shipments=shipments
        if shipments is not None
        else (ShipmentTerm(Decimal("1"), "Toronto"),),
        payment_terms=payment_terms
        if payment_terms is not None
        else (PaymentTerm(Money(Decimal("10"), "USD"), "order", "on order"),),
        delivery_location="Toronto",
    )


def build_proposal(
    *,
    deal_id: DealId,
    terms: TradeTerms,
    based_on: ProposalId | None = None,
    created_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> Proposal:
    return Proposal(
        id=ProposalId(uuid4()),
        deal_id=deal_id,
        author_organization_id=terms.buyer_id,
        terms=terms,
        created_at=created_at or datetime.now(UTC),
        based_on_proposal_id=based_on,
        expires_at=expires_at,
    )


class DecimalCanonicalizationTests(TestCase):
    def test_canonicalization_is_exact_and_context_independent(self) -> None:
        first = Decimal("1.234567890123456789012345678901")
        second = Decimal("1.234567890123456789012345678902")

        with localcontext() as context:
            context.prec = 28
            first_text = canonical_decimal(first)
            second_text = canonical_decimal(second)

        self.assertNotEqual(first_text, second_text)
        self.assertEqual(first_text, "1.234567890123456789012345678901")
        self.assertEqual(canonical_decimal(Decimal("1.2300")), "1.23")
        self.assertEqual(canonical_decimal(Decimal("-0.000")), "0")

    def test_distinct_precise_shipments_produce_distinct_terms_hashes(self) -> None:
        buyer_id = OrganizationId(uuid4())
        seller_id = OrganizationId(uuid4())
        with localcontext() as context:
            context.prec = 28
            first = build_terms(
                shipments=(ShipmentTerm(Decimal("1.234567890123456789012345678901"), "Toronto"),),
                buyer_id=buyer_id,
                seller_id=seller_id,
            )
            second = build_terms(
                shipments=(ShipmentTerm(Decimal("1.234567890123456789012345678902"), "Toronto"),),
                buyer_id=buyer_id,
                seller_id=seller_id,
            )

        self.assertNotEqual(first.terms_hash, second.terms_hash)


class TradeTermsTests(TestCase):
    def test_trade_terms_defensively_copy_mutable_collections(self) -> None:
        items = [TradeLineItem("Desk", Decimal("1"), "each", Money(Decimal("10"), "USD"))]
        shipments = [ShipmentTerm(Decimal("1"), "Toronto")]
        payments = [PaymentTerm(Money(Decimal("10"), "USD"), "order", "on order")]
        terms = build_terms(line_items=items, shipments=shipments, payment_terms=payments)
        original_hash = terms.terms_hash

        items.clear()
        shipments.clear()
        payments.clear()

        self.assertIsInstance(terms.line_items, tuple)
        self.assertIsInstance(terms.shipments, tuple)
        self.assertIsInstance(terms.payment_terms, tuple)
        self.assertEqual(len(terms.line_items), 1)
        self.assertEqual(len(terms.shipments), 1)
        self.assertEqual(len(terms.payment_terms), 1)
        self.assertEqual(terms.terms_hash, original_hash)

    def test_negative_line_item_price_is_rejected(self) -> None:
        with self.assertRaises(InvariantViolation):
            TradeLineItem("Desk", Decimal("1"), "each", Money(Decimal("-1"), "USD"))


class PaymentReconciliationTests(TestCase):
    def test_lower_stale_reconciliation_cannot_reduce_recorded_payment(self) -> None:
        buyer = OrganizationId(uuid4())
        milestone = PaymentMilestone(
            id=PaymentMilestoneId(uuid4()),
            deal_id=DealId(uuid4()),
            agreement_version_id=AgreementVersionId(uuid4()),
            sequence_number=1,
            payer_organization_id=buyer,
            amount=Money(Decimal("100"), "USD"),
            trigger="order",
            due_condition="on order",
        )
        intent = PaymentIntent(
            id=PaymentIntentId(uuid4()),
            milestone=milestone,
            payer_organization_id=buyer,
            authorized_by=UserId(uuid4()),
            idempotency_key="intent-key",
            created_at=datetime.now(UTC),
        )
        intent.begin_create()
        intent.record_provider_created("provider-123")
        intent.mark_sent()
        intent.reconcile_provider_state(
            provider_reference="provider-123",
            paid_amount=Money(Decimal("40"), "USD"),
        )

        with self.assertRaises(InvalidTransition):
            intent.reconcile_provider_state(
                provider_reference="stale-reference",
                paid_amount=Money(Decimal("10"), "USD"),
            )

        self.assertEqual(intent.status, PaymentIntentStatus.PARTIALLY_PAID)
        self.assertEqual(intent.reconciled_amount, Money(Decimal("40"), "USD"))
        self.assertEqual(intent.provider_reference, "provider-123")


class NegotiationTests(TestCase):
    def test_expired_proposal_cannot_advance_session_or_become_candidate(self) -> None:
        now = datetime.now(UTC)
        deal_id = DealId(uuid4())
        terms = build_terms()
        expired = build_proposal(
            deal_id=deal_id,
            terms=terms,
            created_at=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1),
        )
        session = NegotiationSession(NegotiationSessionId(uuid4()), deal_id, max_rounds=3)

        with self.assertRaises(InvalidTransition):
            session.submit(expired, now=now)
        with self.assertRaises(InvalidTransition):
            expired.accept_as_candidate(now=now)

        self.assertEqual(session.round_count, 0)
        self.assertIsNone(session.current_proposal_id)
        self.assertEqual(expired.status, ProposalStatus.SUBMITTED)

    def test_submitting_successor_supersedes_previous_proposal(self) -> None:
        now = datetime.now(UTC)
        deal_id = DealId(uuid4())
        terms = build_terms()
        session = NegotiationSession(NegotiationSessionId(uuid4()), deal_id, max_rounds=3)
        first = build_proposal(deal_id=deal_id, terms=terms, created_at=now)
        self.assertEqual(
            session.submit(first, now=now), NegotiationSubmissionOutcome.SUBMITTED
        )
        successor = build_proposal(
            deal_id=deal_id,
            terms=terms,
            based_on=first.id,
            created_at=now,
        )

        outcome = session.submit(successor, now=now, current_proposal=first)

        self.assertEqual(outcome, NegotiationSubmissionOutcome.SUBMITTED)
        self.assertEqual(first.status, ProposalStatus.SUPERSEDED)
        self.assertEqual(successor.status, ProposalStatus.SUBMITTED)
        self.assertEqual(session.current_proposal_id, successor.id)

    def test_round_limit_returns_escalation_outcome_without_raising(self) -> None:
        now = datetime.now(UTC)
        deal_id = DealId(uuid4())
        terms = build_terms()
        session = NegotiationSession(NegotiationSessionId(uuid4()), deal_id, max_rounds=1)
        first = build_proposal(deal_id=deal_id, terms=terms, created_at=now)
        session.submit(first, now=now)
        successor = build_proposal(
            deal_id=deal_id,
            terms=terms,
            based_on=first.id,
            created_at=now,
        )

        outcome = session.submit(successor, now=now, current_proposal=first)

        self.assertEqual(outcome, NegotiationSubmissionOutcome.ESCALATION_REQUIRED)
        self.assertTrue(session.escalated)
        self.assertEqual(session.round_count, 1)
        self.assertEqual(session.current_proposal_id, first.id)
        self.assertEqual(first.status, ProposalStatus.SUBMITTED)
