"""Comprehensive tests for Milestone Payments - F10c.

Covers:
1. Exact sums, precision, bounded finite Decimal, zero-residual policy.
2. Trigger conditions, eligibility evaluation, and capability gating.
3. One active intent per milestone, DB uniqueness, transaction/outbox idempotency.
4. Schema 1 and Schema 2 deal completion requirements.
5. Additive migration 0022 and history-loss downgrade guard.
"""

import importlib.util
import unittest
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.payments import _check_milestone_delivery_confirmed
from syncally.application.payments import (
    AuthorizePaymentIntentCommand,
    DuplicateActivePaymentIntent,
    IdempotencyKeyReused,
)
from syncally.domain.agreements.trade_terms import (
    PaymentObligationAllocation as TermPaymentObligationAllocation,
)
from syncally.domain.agreements.trade_terms import (
    PaymentTerm,
    ShipmentItemAllocation,
    ShipmentTerm,
    TradeLineItem,
    TradeTerms,
)
from syncally.domain.payments.intent import (
    PaymentExecutionMode,
    PaymentMilestone,
    PaymentObligationAllocation,
    check_milestone_trigger_eligibility,
)
from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import (
    AgreementVersionId,
    DealId,
    OrganizationId,
    PaymentMilestoneId,
)
from syncally.domain.shared.money import Money
from syncally.infrastructure.deal_completion import (
    delivery_obligation_fulfilled,
    maybe_complete_deal,
    payments_reconciled,
)
from syncally.infrastructure.models import (
    AgreementVersion,
    Base,
    Deal,
    FulfillmentEvent,
    NegotiationSession,
    Obligation,
    Organization,
    OrganizationMember,
    Proposal,
    User,
)
from syncally.infrastructure.models import (
    PaymentIntent as PaymentIntentRow,
)
from syncally.infrastructure.models import (
    PaymentMilestone as PaymentMilestoneRow,
)
from syncally.infrastructure.repositories.payments import (
    _derive_lifecycle_state,
    authorize_payment_intent_in_transaction,
)


class MilestoneDomainValidationTests(unittest.TestCase):
    """Domain model validation: bounded finite Decimal, sums, zero-residual, currency balance."""

    def test_milestone_bounded_decimal_valid(self) -> None:
        milestone = PaymentMilestone(
            id=PaymentMilestoneId(uuid4()),
            deal_id=DealId(uuid4()),
            agreement_version_id=AgreementVersionId(uuid4()),
            sequence_number=1,
            payer_organization_id=OrganizationId(uuid4()),
            amount=Money(Decimal("1500.50"), "USD"),
            trigger="UPON_COMMIT",
            due_condition="Immediate",
            source_terms_reference="m-1",
        )
        self.assertEqual(milestone.amount.amount, Decimal("1500.50"))
        self.assertEqual(milestone.amount.currency, "USD")
        self.assertEqual(milestone.source_terms_reference, "m-1")

    def test_milestone_rejects_giant_decimal(self) -> None:
        with self.assertRaises(InvariantViolation):
            PaymentMilestone(
                id=PaymentMilestoneId(uuid4()),
                deal_id=DealId(uuid4()),
                agreement_version_id=AgreementVersionId(uuid4()),
                sequence_number=1,
                payer_organization_id=OrganizationId(uuid4()),
                amount=Money(Decimal("1" + "0" * 45), "USD"),
                trigger="UPON_COMMIT",
                due_condition="Immediate",
            )

    def test_milestone_rejects_non_finite_decimal(self) -> None:
        for non_finite in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
            with self.subTest(val=str(non_finite)):
                with self.assertRaises(InvariantViolation):
                    PaymentMilestone(
                        id=PaymentMilestoneId(uuid4()),
                        deal_id=DealId(uuid4()),
                        agreement_version_id=AgreementVersionId(uuid4()),
                        sequence_number=1,
                        payer_organization_id=OrganizationId(uuid4()),
                        amount=Money(non_finite, "USD"),
                        trigger="UPON_COMMIT",
                        due_condition="Immediate",
                    )

    def test_milestone_rejects_negative_and_zero_amount(self) -> None:
        for bad_amount in (Decimal("-10.00"), Decimal("0")):
            with self.subTest(val=str(bad_amount)):
                with self.assertRaises(InvariantViolation):
                    PaymentMilestone(
                        id=PaymentMilestoneId(uuid4()),
                        deal_id=DealId(uuid4()),
                        agreement_version_id=AgreementVersionId(uuid4()),
                        sequence_number=1,
                        payer_organization_id=OrganizationId(uuid4()),
                        amount=Money(bad_amount, "USD"),
                        trigger="UPON_COMMIT",
                        due_condition="Immediate",
                    )

    def test_milestone_rejects_empty_or_whitespace_fields(self) -> None:
        with self.assertRaises(InvariantViolation):
            PaymentMilestone(
                id=PaymentMilestoneId(uuid4()),
                deal_id=DealId(uuid4()),
                agreement_version_id=AgreementVersionId(uuid4()),
                sequence_number=1,
                payer_organization_id=OrganizationId(uuid4()),
                amount=Money(Decimal("100.00"), "USD"),
                trigger="   ",
                due_condition="Immediate",
            )
        with self.assertRaises(InvariantViolation):
            PaymentMilestone(
                id=PaymentMilestoneId(uuid4()),
                deal_id=DealId(uuid4()),
                agreement_version_id=AgreementVersionId(uuid4()),
                sequence_number=1,
                payer_organization_id=OrganizationId(uuid4()),
                amount=Money(Decimal("100.00"), "USD"),
                trigger="UPON_COMMIT",
                due_condition="",
            )

    def test_milestone_zero_residual_policy_enforced(self) -> None:
        alloc1 = PaymentObligationAllocation(
            obligation_id="ship-1",
            amount=Money(Decimal("600.00"), "USD"),
        )
        alloc2 = PaymentObligationAllocation(
            obligation_id="ship-2",
            amount=Money(Decimal("400.00"), "USD"),
        )
        # Exact sum: 600 + 400 == 1000.00
        milestone = PaymentMilestone(
            id=PaymentMilestoneId(uuid4()),
            deal_id=DealId(uuid4()),
            agreement_version_id=AgreementVersionId(uuid4()),
            sequence_number=1,
            payer_organization_id=OrganizationId(uuid4()),
            amount=Money(Decimal("1000.00"), "USD"),
            trigger="UPON_COMMIT",
            due_condition="Immediate",
            allocations=(alloc1, alloc2),
        )
        self.assertEqual(len(milestone.allocations), 2)

        # Residual discrepancy: sum is 999.00 != 1000.00
        alloc_bad = PaymentObligationAllocation(
            obligation_id="ship-2",
            amount=Money(Decimal("399.00"), "USD"),
        )
        with self.assertRaises(InvariantViolation):
            PaymentMilestone(
                id=PaymentMilestoneId(uuid4()),
                deal_id=DealId(uuid4()),
                agreement_version_id=AgreementVersionId(uuid4()),
                sequence_number=1,
                payer_organization_id=OrganizationId(uuid4()),
                amount=Money(Decimal("1000.00"), "USD"),
                trigger="UPON_COMMIT",
                due_condition="Immediate",
                allocations=(alloc1, alloc_bad),
            )

    def test_milestone_allocation_currency_mismatch_rejected(self) -> None:
        alloc_eur = PaymentObligationAllocation(
            obligation_id="ship-1",
            amount=Money(Decimal("1000.00"), "EUR"),
        )
        with self.assertRaises(InvariantViolation):
            PaymentMilestone(
                id=PaymentMilestoneId(uuid4()),
                deal_id=DealId(uuid4()),
                agreement_version_id=AgreementVersionId(uuid4()),
                sequence_number=1,
                payer_organization_id=OrganizationId(uuid4()),
                amount=Money(Decimal("1000.00"), "USD"),
                trigger="UPON_COMMIT",
                due_condition="Immediate",
                allocations=(alloc_eur,),
            )

    def test_milestone_rejects_excess_currency_precision(self) -> None:
        # USD allows 2 decimal places; 3 should be rejected
        with self.assertRaises(InvariantViolation):
            PaymentMilestone(
                id=PaymentMilestoneId(uuid4()),
                deal_id=DealId(uuid4()),
                agreement_version_id=AgreementVersionId(uuid4()),
                sequence_number=1,
                payer_organization_id=OrganizationId(uuid4()),
                amount=Money(Decimal("100.005"), "USD"),
                trigger="UPON_COMMIT",
                due_condition="Immediate",
            )
        # JPY allows 0 decimal places; 1 should be rejected
        with self.assertRaises(InvariantViolation):
            PaymentMilestone(
                id=PaymentMilestoneId(uuid4()),
                deal_id=DealId(uuid4()),
                agreement_version_id=AgreementVersionId(uuid4()),
                sequence_number=1,
                payer_organization_id=OrganizationId(uuid4()),
                amount=Money(Decimal("100.5"), "JPY"),
                trigger="UPON_COMMIT",
                due_condition="Immediate",
            )
        # Allocation with excess precision should be rejected
        alloc_bad = PaymentObligationAllocation(
            obligation_id="ship-1",
            amount=Money(Decimal("100.001"), "USD"),
        )
        with self.assertRaises(InvariantViolation):
            PaymentMilestone(
                id=PaymentMilestoneId(uuid4()),
                deal_id=DealId(uuid4()),
                agreement_version_id=AgreementVersionId(uuid4()),
                sequence_number=1,
                payer_organization_id=OrganizationId(uuid4()),
                amount=Money(Decimal("100.00"), "USD"),
                trigger="UPON_COMMIT",
                due_condition="Immediate",
                allocations=(alloc_bad,),
            )


class MilestoneTriggerEligibilityTests(unittest.TestCase):
    """Trigger policy evaluation: UPON_COMMIT, INVOICE, UPON_DELIVERY."""

    def test_commit_triggers_eligible_when_committed(self) -> None:
        for trigger in ("UPON_COMMIT", "COMMIT", "AGREEMENT_COMMIT", "commit"):
            with self.subTest(trigger=trigger):
                eligible, reason = check_milestone_trigger_eligibility(
                    trigger, agreement_committed=True
                )
                self.assertTrue(eligible)
                self.assertIsNone(reason)

        # Ineligible if agreement not committed
        eligible, reason = check_milestone_trigger_eligibility(
            "UPON_COMMIT", agreement_committed=False
        )
        self.assertFalse(eligible)
        self.assertIsNotNone(reason)
        self.assertIn("committed", reason.casefold())

    def test_delivery_triggers_require_delivery_confirmed(self) -> None:
        for trigger in ("UPON_DELIVERY", "DELIVERY", "CONFIRMED_DELIVERY"):
            with self.subTest(trigger=trigger):
                # When delivery is not confirmed: ineligible
                eligible, reason = check_milestone_trigger_eligibility(
                    trigger, agreement_committed=True, delivery_confirmed=False
                )
                self.assertFalse(eligible)
                self.assertIsNotNone(reason)
                self.assertIn("delivery", reason.casefold())

                # When delivery is confirmed: eligible
                eligible, reason = check_milestone_trigger_eligibility(
                    trigger, agreement_committed=True, delivery_confirmed=True
                )
                self.assertTrue(eligible)
                self.assertIsNone(reason)

    def test_unapproved_trigger_rejected(self) -> None:
        eligible, reason = check_milestone_trigger_eligibility(
            "MAGIC_PAYMENT_TRIGGER", agreement_committed=True
        )
        self.assertFalse(eligible)
        self.assertIsNotNone(reason)
        self.assertIn("unapproved", reason.casefold())


class MilestoneRepositoryAndIsolationTests(unittest.TestCase):
    """Database tests: one active intent per milestone, idempotency, multi-milestone isolation."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self._seed_deal_with_two_milestones()

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _seed_deal_with_two_milestones(self) -> None:
        self.buyer_user = User(email="buyer@example.com", display_name="Buyer")
        self.seller_user = User(email="seller@example.com", display_name="Seller")
        self.buyer_org = Organization(legal_name="Buyer Co", country_code="US")
        self.seller_org = Organization(legal_name="Seller Co", country_code="CA")
        self.session.add_all([self.buyer_user, self.seller_user, self.buyer_org, self.seller_org])
        self.session.flush()

        self.session.add_all(
            [
                OrganizationMember(
                    user_id=self.buyer_user.id,
                    organization_id=self.buyer_org.id,
                    status="ACTIVE",
                    role="ADMIN",
                ),
                OrganizationMember(
                    user_id=self.seller_user.id,
                    organization_id=self.seller_org.id,
                    status="ACTIVE",
                    role="ADMIN",
                    capabilities=["FINANCE"],
                ),
            ]
        )

        self.deal = Deal(
            buyer_organization_id=self.buyer_org.id,
            seller_organization_id=self.seller_org.id,
            status="ACTIVE",
            version=1,
        )
        self.session.add(self.deal)
        self.session.flush()

        session_row = NegotiationSession(
            deal_id=self.deal.id,
            max_rounds=5,
            round_count=1,
        )
        self.session.add(session_row)
        self.session.flush()

        proposal = Proposal(
            deal_id=self.deal.id,
            negotiation_session_id=session_row.id,
            proposal_number=1,
            author_organization_id=self.buyer_org.id,
            terms_json={"schema_version": 2},
            terms_hash="mock-hash-1",
            schema_version=2,
            status="ACCEPTED",
        )
        self.session.add(proposal)
        self.session.flush()

        self.agreement_version = AgreementVersion(
            deal_id=self.deal.id,
            proposal_id=proposal.id,
            version_number=1,
            terms_hash="mock-hash-1",
            canonical_terms_json={"schema_version": 2},
            status="COMMITTED",
            created_by=self.buyer_user.id,
        )
        self.session.add(self.agreement_version)
        self.session.flush()

        self.deal.current_agreement_version_id = self.agreement_version.id

        # Seed two distinct payment milestones
        self.milestone1 = PaymentMilestoneRow(
            deal_id=self.deal.id,
            agreement_version_id=self.agreement_version.id,
            sequence_number=1,
            payer_organization_id=self.buyer_org.id,
            amount=Decimal("5000.00"),
            currency="USD",
            trigger_type="UPON_COMMIT",
            due_condition="Immediate",
            source_terms_reference="deposit",
        )
        self.milestone2 = PaymentMilestoneRow(
            deal_id=self.deal.id,
            agreement_version_id=self.agreement_version.id,
            sequence_number=2,
            payer_organization_id=self.buyer_org.id,
            amount=Decimal("5000.00"),
            currency="USD",
            trigger_type="UPON_DELIVERY",
            due_condition="Net 30",
            source_terms_reference="final",
        )
        self.session.add_all([self.milestone1, self.milestone2])
        self.session.commit()

    def test_one_active_intent_per_milestone_enforced(self) -> None:
        cmd1 = AuthorizePaymentIntentCommand(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=self.agreement_version.id,
            payment_milestone_id=self.milestone1.id,
            seller_organization_id=self.deal.seller_organization_id,
            payer_organization_id=self.deal.buyer_organization_id,
            authorized_by=self.seller_user.id,
            amount=Money(Decimal("5000.00"), "USD"),
            idempotency_key="key-m1-first",
            execution_mode=PaymentExecutionMode.OFFLINE_DEMO,
            source_terms_reference="deposit",
        )
        outcome1 = authorize_payment_intent_in_transaction(self.session, cmd1)
        self.assertFalse(outcome1.already_existed)

        # Attempting a second active intent for milestone 1 raises DuplicateActivePaymentIntent
        cmd1_duplicate = AuthorizePaymentIntentCommand(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=self.agreement_version.id,
            payment_milestone_id=self.milestone1.id,
            seller_organization_id=self.deal.seller_organization_id,
            payer_organization_id=self.deal.buyer_organization_id,
            authorized_by=self.seller_user.id,
            amount=Money(Decimal("5000.00"), "USD"),
            idempotency_key="key-m1-second",
            execution_mode=PaymentExecutionMode.OFFLINE_DEMO,
            source_terms_reference="deposit",
        )
        with self.assertRaises(DuplicateActivePaymentIntent):
            authorize_payment_intent_in_transaction(self.session, cmd1_duplicate)

        # But Milestone 2 CAN be authorized independently!
        cmd2 = AuthorizePaymentIntentCommand(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=self.agreement_version.id,
            payment_milestone_id=self.milestone2.id,
            seller_organization_id=self.deal.seller_organization_id,
            payer_organization_id=self.deal.buyer_organization_id,
            authorized_by=self.seller_user.id,
            amount=Money(Decimal("5000.00"), "USD"),
            idempotency_key="key-m2-first",
            execution_mode=PaymentExecutionMode.OFFLINE_DEMO,
            source_terms_reference="final",
        )
        outcome2 = authorize_payment_intent_in_transaction(self.session, cmd2)
        self.assertFalse(outcome2.already_existed)
        self.assertNotEqual(outcome1.intent_id, outcome2.intent_id)

    def test_idempotent_replay_and_key_reuse_mismatch(self) -> None:
        cmd = AuthorizePaymentIntentCommand(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=self.agreement_version.id,
            payment_milestone_id=self.milestone1.id,
            seller_organization_id=self.deal.seller_organization_id,
            payer_organization_id=self.deal.buyer_organization_id,
            authorized_by=self.seller_user.id,
            amount=Money(Decimal("5000.00"), "USD"),
            idempotency_key="idempotency-token-123",
            execution_mode=PaymentExecutionMode.OFFLINE_DEMO,
            source_terms_reference="deposit",
        )
        outcome1 = authorize_payment_intent_in_transaction(self.session, cmd)
        self.assertFalse(outcome1.already_existed)

        # Exact replay returns already_existed=True
        outcome_replay = authorize_payment_intent_in_transaction(self.session, cmd)
        self.assertTrue(outcome_replay.already_existed)
        self.assertEqual(outcome1.intent_id, outcome_replay.intent_id)

        # Key reused for different milestone or amount raises IdempotencyKeyReused
        cmd_mismatch = AuthorizePaymentIntentCommand(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=self.agreement_version.id,
            payment_milestone_id=self.milestone2.id,  # different milestone
            seller_organization_id=self.deal.seller_organization_id,
            payer_organization_id=self.deal.buyer_organization_id,
            authorized_by=self.seller_user.id,
            amount=Money(Decimal("5000.00"), "USD"),
            idempotency_key="idempotency-token-123",  # same key!
            execution_mode=PaymentExecutionMode.OFFLINE_DEMO,
            source_terms_reference="final",
        )
        with self.assertRaises(IdempotencyKeyReused):
            authorize_payment_intent_in_transaction(self.session, cmd_mismatch)

    def test_cannot_authorize_payment_for_already_paid_milestone(self) -> None:
        cmd = AuthorizePaymentIntentCommand(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=self.agreement_version.id,
            payment_milestone_id=self.milestone1.id,
            seller_organization_id=self.deal.seller_organization_id,
            payer_organization_id=self.deal.buyer_organization_id,
            authorized_by=self.seller_user.id,
            amount=Money(Decimal("5000.00"), "USD"),
            idempotency_key="key-for-settled-milestone",
            execution_mode=PaymentExecutionMode.OFFLINE_DEMO,
            source_terms_reference="deposit",
        )
        outcome = authorize_payment_intent_in_transaction(self.session, cmd)
        intent_row = self.session.get(PaymentIntentRow, outcome.intent_id)
        assert intent_row is not None
        # Transition intent to PAID
        intent_row.status = "PAID"
        intent_row.reconciled_amount = intent_row.amount
        intent_row.reconciliation_source = "OFFLINE_DEMO"
        self.session.commit()

        # Attempting to authorize another intent for this paid milestone must be rejected
        new_cmd = AuthorizePaymentIntentCommand(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=self.agreement_version.id,
            payment_milestone_id=self.milestone1.id,
            seller_organization_id=self.deal.seller_organization_id,
            payer_organization_id=self.deal.buyer_organization_id,
            authorized_by=self.seller_user.id,
            amount=Money(Decimal("5000.00"), "USD"),
            idempotency_key="new-key-for-already-paid-milestone",
            execution_mode=PaymentExecutionMode.OFFLINE_DEMO,
            source_terms_reference="deposit",
        )
        with self.assertRaises(DuplicateActivePaymentIntent) as ctx:
            authorize_payment_intent_in_transaction(self.session, new_cmd)
        self.assertIn("already been paid", str(ctx.exception))

        # But replay with original idempotency key still succeeds
        replay_outcome = authorize_payment_intent_in_transaction(self.session, cmd)
        self.assertTrue(replay_outcome.already_existed)
        self.assertEqual(replay_outcome.intent_id, outcome.intent_id)

    def test_derive_lifecycle_states(self) -> None:
        self.assertEqual(_derive_lifecycle_state("AUTHORIZED"), "authorized")
        self.assertEqual(_derive_lifecycle_state("CREATE_PENDING"), "queued")
        self.assertEqual(_derive_lifecycle_state("CREATE_UNKNOWN"), "unknown")
        self.assertEqual(_derive_lifecycle_state("PROVIDER_CREATED"), "sent")
        self.assertEqual(_derive_lifecycle_state("SENT"), "sent")
        self.assertEqual(_derive_lifecycle_state("PENDING"), "sent")
        self.assertEqual(_derive_lifecycle_state("PARTIALLY_PAID"), "reconciled")
        self.assertEqual(_derive_lifecycle_state("PAID"), "reconciled")
        self.assertEqual(_derive_lifecycle_state("FAILED"), "failed")
        self.assertEqual(_derive_lifecycle_state("CANCELLED"), "cancelled")


class DealCompletionRequirementTests(unittest.TestCase):
    """Fulfillment and payment reconciliation completion requirements."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        self.buyer_user = User(email="buyer@example.com", display_name="Buyer")
        self.buyer_org = Organization(legal_name="Buyer Co", country_code="US")
        self.seller_org = Organization(legal_name="Seller Co", country_code="CA")
        self.session.add_all([self.buyer_user, self.buyer_org, self.seller_org])
        self.session.flush()

        self.deal = Deal(
            buyer_organization_id=self.buyer_org.id,
            seller_organization_id=self.seller_org.id,
            status="AGREED",
            version=1,
        )
        self.session.add(self.deal)
        self.session.flush()

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _create_version(self, terms: TradeTerms, version_number: int = 1) -> AgreementVersion:
        session_row = NegotiationSession(
            deal_id=self.deal.id,
            max_rounds=5,
            round_count=1,
        )
        self.session.add(session_row)
        self.session.flush()

        proposal = Proposal(
            deal_id=self.deal.id,
            negotiation_session_id=session_row.id,
            proposal_number=version_number,
            author_organization_id=self.buyer_org.id,
            terms_json=terms.to_storage_dict(),
            terms_hash=terms.terms_hash,
            schema_version=terms.schema_version,
            status="ACCEPTED",
        )
        self.session.add(proposal)
        self.session.flush()

        version = AgreementVersion(
            deal_id=self.deal.id,
            proposal_id=proposal.id,
            version_number=version_number,
            terms_hash=terms.terms_hash,
            canonical_terms_json=terms.to_storage_dict(),
            status="COMMITTED",
            created_by=self.buyer_user.id,
        )
        self.session.add(version)
        self.session.flush()
        return version

    def test_schema2_multishipment_and_payment_completion(self) -> None:
        # Schema 2 agreement with 2 shipments and 2 payment milestones
        terms = TradeTerms(
            buyer_id=OrganizationId(self.buyer_org.id),
            seller_id=OrganizationId(self.seller_org.id),
            line_items=(
                TradeLineItem(
                    id="item-1",
                    description="Widget A",
                    quantity=Decimal("10"),
                    unit="each",
                    unit_price=Money(Decimal("100.00"), "USD"),
                ),
            ),
            shipments=(
                ShipmentTerm(
                    id="ship-1",
                    destination="New York",
                    target_date=date(2026, 12, 1),
                    allocations=(
                        ShipmentItemAllocation(
                            line_item_id="item-1", quantity=Decimal("5"), unit="each"
                        ),
                    ),
                ),
                ShipmentTerm(
                    id="ship-2",
                    destination="Los Angeles",
                    target_date=date(2026, 12, 15),
                    allocations=(
                        ShipmentItemAllocation(
                            line_item_id="item-1", quantity=Decimal("5"), unit="each"
                        ),
                    ),
                ),
            ),
            payment_terms=(
                PaymentTerm(
                    id="pay-1",
                    amount=Money(Decimal("500.00"), "USD"),
                    trigger="UPON_COMMIT",
                    due_condition="Immediate",
                    allocations=(
                        TermPaymentObligationAllocation(
                            obligation_id="ship-1", amount=Money(Decimal("500.00"), "USD")
                        ),
                    ),
                ),
                PaymentTerm(
                    id="pay-2",
                    amount=Money(Decimal("500.00"), "USD"),
                    trigger="UPON_DELIVERY",
                    due_condition="Net 30",
                    allocations=(
                        TermPaymentObligationAllocation(
                            obligation_id="ship-2", amount=Money(Decimal("500.00"), "USD")
                        ),
                    ),
                ),
            ),
            delivery_location="Various",
            schema_version=2,
        )

        version = self._create_version(terms, version_number=1)

        # Create obligations for the shipments
        ob_ship1 = Obligation(
            deal_id=self.deal.id,
            agreement_version_id=version.id,
            obligation_type="DELIVERY",
            owner_organization_id=self.seller_org.id,
            counterparty_organization_id=self.buyer_org.id,
            due_date=datetime.now(UTC),
            status="PENDING",
            source_terms_reference="ship-1",
        )
        ob_ship2 = Obligation(
            deal_id=self.deal.id,
            agreement_version_id=version.id,
            obligation_type="DELIVERY",
            owner_organization_id=self.seller_org.id,
            counterparty_organization_id=self.buyer_org.id,
            due_date=datetime.now(UTC),
            status="PENDING",
            source_terms_reference="ship-2",
        )
        m1 = PaymentMilestoneRow(
            deal_id=self.deal.id,
            agreement_version_id=version.id,
            sequence_number=1,
            payer_organization_id=self.buyer_org.id,
            amount=Decimal("500.00"),
            currency="USD",
            trigger_type="UPON_COMMIT",
            due_condition="Immediate",
            source_terms_reference="pay-1",
        )
        m2 = PaymentMilestoneRow(
            deal_id=self.deal.id,
            agreement_version_id=version.id,
            sequence_number=2,
            payer_organization_id=self.buyer_org.id,
            amount=Decimal("500.00"),
            currency="USD",
            trigger_type="UPON_DELIVERY",
            due_condition="Net 30",
            source_terms_reference="pay-2",
        )
        self.session.add_all([ob_ship1, ob_ship2, m1, m2])
        self.session.commit()

        # 1. Neither delivery nor payment fulfilled yet:
        self.assertFalse(delivery_obligation_fulfilled(self.session, self.deal.id, version, terms))
        self.assertFalse(payments_reconciled(self.session, self.deal.id, version.id, terms))
        self.assertFalse(maybe_complete_deal(self.session, self.deal.id, self.deal.id))

        # 2. Record full fulfillment lifecycle (SHIPPED, OBSERVED, CONFIRMED) for ship-1 only:
        for idx, stage in enumerate(["SHIPPED", "OBSERVED", "CONFIRMED"], start=1):
            self.session.add(
                FulfillmentEvent(
                    id=uuid4(),
                    deal_id=self.deal.id,
                    agreement_version_id=version.id,
                    terms_hash=version.terms_hash,
                    obligation_id=ob_ship1.id,
                    actor_organization_id=self.seller_org.id,
                    actor_user_id=self.buyer_user.id,
                    event_type=stage,
                    quantity="5",
                    unit="each",
                    source_type="USER_ATTESTATION",
                    idempotency_key=f"fulfill-1-{stage}",
                    request_hash=f"req-1-{stage}",
                    version=idx,
                )
            )
        self.session.commit()
        # Delivery not yet fulfilled because ship-2 is unconfirmed
        self.assertFalse(delivery_obligation_fulfilled(self.session, self.deal.id, version, terms))

        # 3. Record full fulfillment lifecycle for ship-2:
        for idx, stage in enumerate(["SHIPPED", "OBSERVED", "CONFIRMED"], start=1):
            self.session.add(
                FulfillmentEvent(
                    id=uuid4(),
                    deal_id=self.deal.id,
                    agreement_version_id=version.id,
                    terms_hash=version.terms_hash,
                    obligation_id=ob_ship2.id,
                    actor_organization_id=self.seller_org.id,
                    actor_user_id=self.buyer_user.id,
                    event_type=stage,
                    quantity="5",
                    unit="each",
                    source_type="USER_ATTESTATION",
                    idempotency_key=f"fulfill-2-{stage}",
                    request_hash=f"req-2-{stage}",
                    version=idx,
                )
            )
        self.session.commit()
        self.assertTrue(delivery_obligation_fulfilled(self.session, self.deal.id, version, terms))
        # But payment is not yet reconciled:
        self.assertFalse(payments_reconciled(self.session, self.deal.id, version.id, terms))

        # 4. Reconcile payment for milestone 1 (PAID), but milestone 2 is PENDING:
        intent1 = PaymentIntentRow(
            deal_id=self.deal.id,
            agreement_version_id=version.id,
            payment_milestone_id=m1.id,
            seller_organization_id=self.seller_org.id,
            payer_organization_id=self.buyer_org.id,
            authorized_by=self.buyer_user.id,
            amount=Decimal("500.00"),
            currency="USD",
            status="PAID",
            reconciliation_source="OFFLINE_DEMO",
            reconciled_amount=Decimal("500.00"),
            last_reconciled_at=datetime.now(UTC),
            idempotency_key="key-1",
            execution_mode="OFFLINE_DEMO",
            provider="OFFLINE_DEMO",
            source_terms_reference="pay-1",
        )
        intent2 = PaymentIntentRow(
            deal_id=self.deal.id,
            agreement_version_id=version.id,
            payment_milestone_id=m2.id,
            seller_organization_id=self.seller_org.id,
            payer_organization_id=self.buyer_org.id,
            authorized_by=self.buyer_user.id,
            amount=Decimal("500.00"),
            currency="USD",
            status="PENDING",
            idempotency_key="key-2",
            execution_mode="OFFLINE_DEMO",
            provider="OFFLINE_DEMO",
            source_terms_reference="pay-2",
        )
        self.session.add_all([intent1, intent2])
        self.session.commit()
        # Milestone 2 is not paid yet
        self.assertFalse(payments_reconciled(self.session, self.deal.id, version.id, terms))
        self.assertFalse(maybe_complete_deal(self.session, self.deal.id, intent1.id))

        # 5. Milestone 2 marked PAID:
        intent2.status = "PAID"
        intent2.reconciliation_source = "OFFLINE_DEMO"
        intent2.reconciled_amount = Decimal("500.00")
        intent2.last_reconciled_at = datetime.now(UTC)
        self.deal.current_agreement_version_id = version.id
        version.committed_at = datetime.now(UTC)
        self.session.commit()
        self.assertTrue(payments_reconciled(self.session, self.deal.id, version.id, terms))
        completed = maybe_complete_deal(self.session, self.deal.id, intent2.id)
        self.assertTrue(completed)
        self.assertEqual(self.session.get(Deal, self.deal.id).status, "COMPLETED")

    def test_delivery_trigger_milestone_requires_full_quantity_confirmation(self) -> None:
        item = TradeLineItem(
            id="item-1",
            description="Widget",
            quantity=Decimal("10"),
            unit="units",
            unit_price=Money(Decimal("10.00"), "USD"),
        )
        ship = ShipmentTerm(
            id="ship-1",
            destination="Hub",
            target_date=date(2030, 1, 1),
            allocations=(ShipmentItemAllocation("item-1", Decimal("10"), "units"),),
        )
        pay = PaymentTerm(
            id="pay-1",
            amount=Money(Decimal("100.00"), "USD"),
            trigger="UPON_DELIVERY",
            due_condition="On delivery",
            allocations=(TermPaymentObligationAllocation("ship-1", Money(Decimal("100.00"), "USD")),),
        )
        terms = TradeTerms(
            buyer_id=OrganizationId(self.buyer_org.id),
            seller_id=OrganizationId(self.seller_org.id),
            line_items=(item,),
            shipments=(ship,),
            payment_terms=(pay,),
            delivery_location="Hub",
            schema_version=2,
        )
        terms.validate_for_commit()

        version = self._create_version(terms, version_number=2)

        ob_ship = Obligation(
            deal_id=self.deal.id,
            agreement_version_id=version.id,
            obligation_type="DELIVERY",
            owner_organization_id=self.seller_org.id,
            counterparty_organization_id=self.buyer_org.id,
            source_terms_reference="ship-1",
        )
        m = PaymentMilestoneRow(
            deal_id=self.deal.id,
            agreement_version_id=version.id,
            sequence_number=1,
            payer_organization_id=self.buyer_org.id,
            amount=Decimal("100.00"),
            currency="USD",
            trigger_type="UPON_DELIVERY",
            due_condition="On delivery",
            source_terms_reference="pay-1",
        )
        self.session.add_all([ob_ship, m])
        self.session.commit()

        # Partial delivery confirmed (2 of 10)
        self.session.add(
            FulfillmentEvent(
                id=uuid4(),
                deal_id=self.deal.id,
                agreement_version_id=version.id,
                terms_hash=version.terms_hash,
                obligation_id=ob_ship.id,
                actor_organization_id=self.seller_org.id,
                actor_user_id=self.buyer_user.id,
                event_type="CONFIRMED",
                quantity="2",
                unit="units",
                source_type="USER_ATTESTATION",
                idempotency_key="fulfill-partial-conf",
                request_hash="req-partial",
                version=1,
            )
        )
        self.session.commit()

        # Must NOT be delivery confirmed!
        confirmed = _check_milestone_delivery_confirmed(
            self.session, self.deal.id, version.id, m, pay, terms
        )
        self.assertFalse(confirmed)

        # Confirm remaining 8 units (total 10)
        self.session.add(
            FulfillmentEvent(
                id=uuid4(),
                deal_id=self.deal.id,
                agreement_version_id=version.id,
                terms_hash=version.terms_hash,
                obligation_id=ob_ship.id,
                actor_organization_id=self.seller_org.id,
                actor_user_id=self.buyer_user.id,
                event_type="CONFIRMED",
                quantity="8",
                unit="units",
                source_type="USER_ATTESTATION",
                idempotency_key="fulfill-full-conf",
                request_hash="req-full",
                version=2,
            )
        )
        self.session.commit()

        confirmed = _check_milestone_delivery_confirmed(
            self.session, self.deal.id, version.id, m, pay, terms
        )
        self.assertTrue(confirmed)

    def test_deal_completion_handles_multiunit_shipment_without_quantity(self) -> None:
        item1 = TradeLineItem(
            id="item-kg",
            description="Flour",
            quantity=Decimal("5"),
            unit="kg",
            unit_price=Money(Decimal("10.00"), "USD"),
        )
        item2 = TradeLineItem(
            id="item-ltr",
            description="Oil",
            quantity=Decimal("10"),
            unit="liters",
            unit_price=Money(Decimal("5.00"), "USD"),
        )
        # Multi-unit shipment: shipment.quantity is None because units differ (kg vs liters)
        ship = ShipmentTerm(
            id="ship-multi",
            destination="Bakery",
            target_date=date(2030, 1, 1),
            allocations=(
                ShipmentItemAllocation("item-kg", Decimal("5"), "kg"),
                ShipmentItemAllocation("item-ltr", Decimal("10"), "liters"),
            ),
        )
        pay = PaymentTerm(
            id="pay-all",
            amount=Money(Decimal("100.00"), "USD"),
            trigger="seller_invoice",
            due_condition="Net 30",
            allocations=(TermPaymentObligationAllocation("ship-multi", Money(Decimal("100.00"), "USD")),),
        )
        terms = TradeTerms(
            buyer_id=OrganizationId(self.buyer_org.id),
            seller_id=OrganizationId(self.seller_org.id),
            line_items=(item1, item2),
            shipments=(ship,),
            payment_terms=(pay,),
            delivery_location="Bakery",
            schema_version=2,
        )
        terms.validate_for_commit()
        self.assertIsNone(ship.quantity)

        version = self._create_version(terms, version_number=3)

        ob_ship = Obligation(
            deal_id=self.deal.id,
            agreement_version_id=version.id,
            obligation_type="DELIVERY",
            owner_organization_id=self.seller_org.id,
            counterparty_organization_id=self.buyer_org.id,
            source_terms_reference="ship-multi",
        )
        self.session.add(ob_ship)
        self.session.commit()

        # delivery_obligation_fulfilled should not raise TypeError when shipment.quantity is None
        self.assertFalse(delivery_obligation_fulfilled(self.session, self.deal.id, version, terms))

        # Add all stages for both allocation quantities (5 + 10 = 15 total scaled)
        for idx, stage in enumerate(("SHIPPED", "OBSERVED", "CONFIRMED"), start=1):
            self.session.add(
                FulfillmentEvent(
                    id=uuid4(),
                    deal_id=self.deal.id,
                    agreement_version_id=version.id,
                    terms_hash=version.terms_hash,
                    obligation_id=ob_ship.id,
                    actor_organization_id=self.seller_org.id,
                    actor_user_id=self.buyer_user.id,
                    event_type=stage,
                    quantity="15",
                    unit="kg",
                    source_type="USER_ATTESTATION",
                    idempotency_key=f"multi-{stage}",
                    request_hash=f"req-multi-{stage}",
                    version=idx,
                )
            )
        self.session.commit()
        # Evaluates cleanly without raising TypeError
        self.assertTrue(delivery_obligation_fulfilled(self.session, self.deal.id, version, terms))


class MilestonePaymentsMigrationTests(unittest.TestCase):
    """Tests for Alembic migration 0022_milestone_payments and its history-loss downgrade guard."""

    def setUp(self) -> None:
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "alembic"
            / "versions"
            / "0022_milestone_payments.py"
        )
        spec = importlib.util.spec_from_file_location("milestone_payments_migration", migration_path)
        assert spec is not None and spec.loader is not None
        self.migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.migration)
        self.engine = sa.create_engine("sqlite:///:memory:")
        self.connection = self.engine.connect()
        self._create_prior_schema()
        self.migration.op = Operations(MigrationContext.configure(self.connection))

    def tearDown(self) -> None:
        self.connection.close()
        self.engine.dispose()

    def _create_prior_schema(self) -> None:
        metadata = sa.MetaData()
        sa.Table(
            "payment_milestones",
            metadata,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("amount", sa.Numeric(precision=38, scale=18), nullable=False),
        )
        sa.Table(
            "payment_intents",
            metadata,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("amount", sa.Numeric(precision=38, scale=18), nullable=False),
        )
        metadata.create_all(self.engine)

    def test_upgrade_adds_source_terms_reference(self) -> None:
        self.migration.upgrade()
        cols_milestones = [
            row[1]
            for row in self.connection.exec_driver_sql("PRAGMA table_info(payment_milestones)").fetchall()
        ]
        self.assertIn("source_terms_reference", cols_milestones)

        cols_intents = [
            row[1]
            for row in self.connection.exec_driver_sql("PRAGMA table_info(payment_intents)").fetchall()
        ]
        self.assertIn("source_terms_reference", cols_intents)

    def test_downgrade_guard_blocks_when_milestone_has_reference(self) -> None:
        self.migration.upgrade()
        self.connection.execute(
            sa.text("INSERT INTO payment_milestones (id, amount, source_terms_reference) VALUES (:id, 100, :ref)"),
            {"id": uuid4().hex, "ref": "m-1"},
        )
        with self.assertRaises(RuntimeError) as ctx:
            self.migration.downgrade()
        self.assertIn("data loss prevented", str(ctx.exception))

    def test_downgrade_guard_blocks_when_intent_has_reference(self) -> None:
        self.migration.upgrade()
        self.connection.execute(
            sa.text("INSERT INTO payment_intents (id, amount, source_terms_reference) VALUES (:id, 100, :ref)"),
            {"id": uuid4().hex, "ref": "pay-1"},
        )
        with self.assertRaises(RuntimeError) as ctx:
            self.migration.downgrade()
        self.assertIn("data loss prevented", str(ctx.exception))

    def test_downgrade_succeeds_when_references_are_null(self) -> None:
        self.migration.upgrade()
        self.connection.execute(
            sa.text("INSERT INTO payment_milestones (id, amount, source_terms_reference) VALUES (:id, 100, NULL)"),
            {"id": uuid4().hex},
        )
        self.connection.execute(
            sa.text("INSERT INTO payment_intents (id, amount, source_terms_reference) VALUES (:id, 100, NULL)"),
            {"id": uuid4().hex},
        )
        self.migration.downgrade()

        cols_milestones = [
            row[1]
            for row in self.connection.exec_driver_sql("PRAGMA table_info(payment_milestones)").fetchall()
        ]
        self.assertNotIn("source_terms_reference", cols_milestones)

        cols_intents = [
            row[1]
            for row in self.connection.exec_driver_sql("PRAGMA table_info(payment_intents)").fetchall()
        ]
        self.assertNotIn("source_terms_reference", cols_intents)


if __name__ == "__main__":
    unittest.main()
