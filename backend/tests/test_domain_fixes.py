from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, localcontext
from unittest import TestCase
from uuid import uuid4

from syncally.domain.agreements.agreement import (
    Agreement,
    AgreementStatus,
    Approval,
    ApprovalDecision,
)
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
    VerifiedProviderPaymentState,
    VerifiedProviderPaymentStatus,
)
from syncally.domain.shared.errors import InvalidTransition, InvariantViolation
from syncally.domain.shared.identifiers import (
    AgreementId,
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
    schema_version: int = 1,
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
        else (ShipmentTerm(Decimal("1"), "Toronto", date(2030, 1, 1)),),
        payment_terms=payment_terms
        if payment_terms is not None
        else (PaymentTerm(Money(Decimal("10"), "USD"), "seller_invoice", "when seller invoices"),),
        delivery_location="Toronto",
        schema_version=schema_version,
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


class HumanNegotiationTests(TestCase):
    def test_terminal_successor_preserves_snapshot_and_limit(self) -> None:
        now = datetime.now(UTC)
        terms = build_terms()
        deal_id = DealId(uuid4())
        session = NegotiationSession(NegotiationSessionId(uuid4()), deal_id, 1)
        first = build_proposal(deal_id=deal_id, terms=terms, created_at=now)
        session.submit(first, now=now)
        first.reject()
        successor = build_proposal(deal_id=deal_id, terms=terms, based_on=first.id)
        self.assertEqual(session.submit(successor, now=now, current_proposal=first), NegotiationSubmissionOutcome.ESCALATION_REQUIRED)
        self.assertEqual(first.status, ProposalStatus.REJECTED)
        self.assertEqual(session.current_proposal_id, first.id)
        session = NegotiationSession(NegotiationSessionId(uuid4()), deal_id, 5, 1, first.id)
        session.submit(successor, now=now, current_proposal=first)
        self.assertEqual(first.status, ProposalStatus.REJECTED)
        with self.assertRaises(InvalidTransition):
            first.terms = build_terms()

    def test_expiry_is_explicit_aware_and_bounded(self) -> None:
        now = datetime.now(UTC)
        terms = build_terms()
        deal_id = DealId(uuid4())
        for deadline in (now.replace(tzinfo=None), now, now + timedelta(days=30, seconds=1)):
            with self.assertRaises(InvariantViolation):
                build_proposal(deal_id=deal_id, terms=terms, created_at=now, expires_at=deadline)
        proposal = build_proposal(deal_id=deal_id, terms=terms, created_at=now, expires_at=now + timedelta(days=30))
        with self.assertRaises(InvalidTransition):
            proposal.expire(now=now)
        with self.assertRaises(InvalidTransition):
            proposal.accept_as_candidate(now=now + timedelta(days=30))
        self.assertEqual(proposal.status, ProposalStatus.SUBMITTED)
        proposal.expire(now=now + timedelta(days=30))
        self.assertEqual(proposal.status, ProposalStatus.EXPIRED)

    def test_action_authority_is_human_party_specific(self) -> None:
        proposal = build_proposal(deal_id=DealId(uuid4()), terms=build_terms())
        for action in ("counter", "accept", "reject"):
            with self.assertRaises(InvalidTransition):
                proposal.authorize_action(action, proposal.author_organization_id)
            proposal.authorize_action(action, proposal.terms.seller_id)
        with self.assertRaises(InvalidTransition):
            proposal.authorize_action("supersede", proposal.terms.seller_id)


class DecimalCanonicalizationTests(TestCase):
    def test_money_addition_is_exact_beyond_default_decimal_precision(self) -> None:
        first = Money(Decimal("999999999999999998000000000.000000001"), "USD")
        second = Money(Decimal("1"), "USD")
        with localcontext() as context:
            context.prec = 50
            expected = first.amount + second.amount

        self.assertEqual(first.add(second).amount, expected)

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
    def test_canonical_hash_ignores_order_and_formatting(self) -> None:
        buyer_id = OrganizationId(uuid4())
        seller_id = OrganizationId(uuid4())
        first = build_terms(
            line_items=(
                TradeLineItem(" Desk ", Decimal("1.00"), " each ", Money(Decimal("10.00"), "usd")),
                TradeLineItem("Lamp", Decimal("2"), "each", Money(Decimal("5"), "USD")),
            ),
            shipments=(ShipmentTerm(Decimal("1.0"), "North"), ShipmentTerm(Decimal("2"), "South")),
            payment_terms=(
                PaymentTerm(Money(Decimal("10.00"), "USD"), "seller_invoice", "When seller invoices"),
                PaymentTerm(Money(Decimal("10"), "USD"), "seller_invoice", "when seller invoices"),
            ),
            buyer_id=buyer_id,
            seller_id=seller_id,
        )
        reordered = build_terms(
            line_items=(
                TradeLineItem("Lamp", Decimal("2.0"), "each", Money(Decimal("5.00"), "USD")),
                TradeLineItem("Desk", Decimal("1"), "each", Money(Decimal("10"), "USD")),
            ),
            shipments=(ShipmentTerm(Decimal("2.00"), "South"), ShipmentTerm(Decimal("1"), "NORTH")),
            payment_terms=(
                PaymentTerm(Money(Decimal("10"), "USD"), "seller_invoice", "when seller invoices"),
                PaymentTerm(Money(Decimal("10.0"), "USD"), "seller_invoice", "when seller invoices"),
            ),
            buyer_id=buyer_id,
            seller_id=seller_id,
        )

        self.assertEqual(first.canonical_json(), reordered.canonical_json())
        self.assertEqual(first.terms_hash, reordered.terms_hash)

    def test_float_quantities_are_rejected(self) -> None:
        with self.assertRaises(TypeError):
            TradeLineItem("Desk", 1.0, "each", Money(Decimal("10"), "USD"))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            ShipmentTerm(1.0, "Toronto")  # type: ignore[arg-type]

    def test_commit_rejects_incomplete_or_unsupported_terms(self) -> None:
        missing_date = build_terms(shipments=(ShipmentTerm(Decimal("1"), "Toronto"),))
        unsupported_currency = build_terms(
            line_items=(TradeLineItem("Desk", Decimal("1"), "each", Money(Decimal("10"), "CAD")),),
            payment_terms=(PaymentTerm(Money(Decimal("10"), "CAD"), "seller_invoice", "when seller invoices"),),
        )
        unknown_payment_trigger = build_terms(
            payment_terms=(PaymentTerm(Money(Decimal("10"), "USD"), "on_delivery", "when delivered"),),
        )
        unsupported_schema = build_terms(schema_version=2)

        for terms in (missing_date, unsupported_currency, unknown_payment_trigger, unsupported_schema):
            with self.subTest(terms=terms):
                with self.assertRaises(InvariantViolation):
                    terms.validate_for_commit()

        agreement = Agreement(
            id=AgreementId(uuid4()),
            version_id=AgreementVersionId(uuid4()),
            deal_id=DealId(uuid4()),
            version_number=1,
            terms=missing_date,
            created_at=datetime(2030, 1, 1, tzinfo=UTC),
        )
        with self.assertRaises(InvariantViolation):
            agreement.commit(agreement.terms_hash, datetime(2030, 1, 2, tzinfo=UTC))
        self.assertEqual(agreement.status, AgreementStatus.PENDING_APPROVAL)

        build_terms().validate_for_commit()

    def test_committed_version_cannot_change_and_revision_creates_next_version(self) -> None:
        terms = build_terms()
        agreement = Agreement(
            id=AgreementId(uuid4()),
            version_id=AgreementVersionId(uuid4()),
            deal_id=DealId(uuid4()),
            version_number=1,
            terms=terms,
            created_at=datetime(2030, 1, 1, tzinfo=UTC),
        )
        for organization_id in (terms.buyer_id, terms.seller_id):
            agreement.record_approval(
                Approval(
                    organization_id=organization_id,
                    user_id=UserId(uuid4()),
                    decision=ApprovalDecision.APPROVE,
                    terms_hash=agreement.terms_hash,
                    created_at=datetime(2030, 1, 1, tzinfo=UTC),
                )
            )
        agreement.commit(agreement.terms_hash, datetime(2030, 1, 2, tzinfo=UTC))
        committed_hash = agreement.terms_hash
        revised_terms = build_terms(
            line_items=(TradeLineItem("Desk, walnut", Decimal("1"), "each", Money(Decimal("10"), "USD")),),
            buyer_id=terms.buyer_id,
            seller_id=terms.seller_id,
        )

        with self.assertRaises(InvalidTransition):
            agreement.terms = revised_terms
        with self.assertRaises(InvalidTransition):
            agreement.version_number = 2
        with self.assertRaises(InvalidTransition):
            agreement.status = AgreementStatus.PENDING_APPROVAL
        with self.assertRaises(TypeError):
            agreement.approvals[terms.buyer_id] = agreement.approvals[terms.buyer_id]  # type: ignore[index]

        next_version = agreement.create_next_version(
            version_id=AgreementVersionId(uuid4()),
            terms=revised_terms,
            created_at=datetime(2030, 1, 3, tzinfo=UTC),
        )
        self.assertEqual(agreement.terms_hash, committed_hash)
        self.assertEqual(agreement.status, AgreementStatus.COMMITTED)
        self.assertEqual(next_version.version_number, 2)
        self.assertNotEqual(next_version.terms_hash, committed_hash)
        self.assertEqual(next_version.status, AgreementStatus.PENDING_APPROVAL)

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
    def _intent(self, idempotency_key: str = "intent-key") -> PaymentIntent:
        buyer = OrganizationId(uuid4())
        milestone = PaymentMilestone(
            id=PaymentMilestoneId(uuid4()),
            deal_id=DealId(uuid4()),
            agreement_version_id=AgreementVersionId(uuid4()),
            sequence_number=1,
            payer_organization_id=buyer,
            amount=Money(Decimal("100"), "USD"),
            trigger="invoice",
            due_condition="on commitment",
        )
        return PaymentIntent(
            id=PaymentIntentId(uuid4()),
            milestone=milestone,
            seller_organization_id=OrganizationId(uuid4()),
            payer_organization_id=buyer,
            authorized_by=UserId(uuid4()),
            idempotency_key=idempotency_key,
            created_at=datetime.now(UTC),
        )

    def test_lower_stale_reconciliation_cannot_reduce_recorded_payment(self) -> None:
        intent = self._intent()
        intent.begin_create()
        intent.record_provider_created("provider-123")
        intent.mark_sent()
        intent.reconcile_provider_state(
            VerifiedProviderPaymentState(
                status=VerifiedProviderPaymentStatus.PARTIALLY_PAID,
                provider_reference="provider-123",
                paid_amount=Money(Decimal("40"), "USD"),
            )
        )

        with self.assertRaises(InvalidTransition):
            intent.reconcile_provider_state(
                VerifiedProviderPaymentState(
                    status=VerifiedProviderPaymentStatus.PARTIALLY_PAID,
                    provider_reference="stale-reference",
                    paid_amount=Money(Decimal("10"), "USD"),
                )
            )

        self.assertEqual(intent.status, PaymentIntentStatus.PARTIALLY_PAID)
        self.assertEqual(intent.reconciled_amount, Money(Decimal("40"), "USD"))
        self.assertEqual(intent.provider_reference, "provider-123")

    def test_pending_full_amount_does_not_mark_payment_paid(self) -> None:
        intent = self._intent("intent-pending")
        intent.begin_create()
        intent.record_provider_created("provider-123")
        intent.mark_sent()

        intent.reconcile_provider_state(
            VerifiedProviderPaymentState(
                status=VerifiedProviderPaymentStatus.PENDING,
                provider_reference="provider-123",
                paid_amount=Money(Decimal("100"), "USD"),
            )
        )

        self.assertEqual(intent.status, PaymentIntentStatus.PENDING)
        self.assertEqual(intent.reconciled_amount, Money(Decimal("100"), "USD"))

    def test_only_verified_paid_state_with_full_milestone_amount_marks_paid(self) -> None:
        intent = self._intent("intent-paid")
        intent.begin_create()
        intent.record_provider_created("provider-123")
        intent.mark_sent()
        with self.assertRaises(InvariantViolation):
            intent.reconcile_provider_state(
                VerifiedProviderPaymentState(
                    status=VerifiedProviderPaymentStatus.PAID,
                    provider_reference="provider-123",
                    paid_amount=Money(Decimal("99"), "USD"),
                )
            )
        self.assertEqual(intent.status, PaymentIntentStatus.SENT)

        intent.reconcile_provider_state(
            VerifiedProviderPaymentState(
                status=VerifiedProviderPaymentStatus.PAID,
                provider_reference="provider-123",
                paid_amount=Money(Decimal("100"), "USD"),
            )
        )

        self.assertEqual(intent.status, PaymentIntentStatus.PAID)

    def test_payment_status_cannot_be_set_directly(self) -> None:
        intent = self._intent("intent-direct-status")

        with self.assertRaises(AttributeError):
            setattr(intent, "status", PaymentIntentStatus.PAID)

        self.assertEqual(intent.status, PaymentIntentStatus.AUTHORIZED)

    def test_unknown_create_can_retry_only_after_verified_not_found(self) -> None:
        intent = self._intent("intent-unknown")
        intent.begin_create()
        intent.record_create_unknown()

        with self.assertRaises(InvalidTransition):
            intent.begin_create()

        intent.reconcile_provider_state(
            VerifiedProviderPaymentState(
                status=VerifiedProviderPaymentStatus.UNKNOWN,
                provider_reference=None,
                paid_amount=Money(Decimal("0"), "USD"),
            )
        )
        self.assertEqual(intent.status, PaymentIntentStatus.CREATE_UNKNOWN)

        intent.reconcile_provider_state(
            VerifiedProviderPaymentState(
                status=VerifiedProviderPaymentStatus.NOT_FOUND,
                provider_reference=None,
                paid_amount=Money(Decimal("0"), "USD"),
            )
        )
        self.assertEqual(intent.status, PaymentIntentStatus.AUTHORIZED)
        intent.begin_create()
        self.assertEqual(intent.status, PaymentIntentStatus.CREATE_PENDING)


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
