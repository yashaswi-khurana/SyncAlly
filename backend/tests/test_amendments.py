"""Comprehensive unit and integration tests for F7 Agreement Amendments."""

import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from test_domain_fixes import build_terms

from syncally.application.agreements import (
    CommitAgreementCommand,
    ProposeAmendmentCommand,
    RecordApprovalCommand,
    WithdrawAmendmentCommand,
)
from syncally.application.documents import export_display_terms
from syncally.application.identity import ActorContext
from syncally.domain.agreements.agreement import AgreementStatus, ApprovalDecision
from syncally.domain.agreements.amendment import (
    AmendmentConflict,
    StalePriorVersion,
    WrongPriorHash,
)
from syncally.domain.agreements.trade_terms import (
    PaymentObligationAllocation,
    PaymentTerm,
    ShipmentItemAllocation,
    ShipmentTerm,
    TradeLineItem,
    TradeTerms,
)
from syncally.domain.shared.identifiers import OrganizationId
from syncally.domain.shared.money import Money
from syncally.infrastructure.models import (
    AgreementVersion,
    Base,
    Deal,
    FulfillmentEvent,
    NegotiationSession,
    Obligation,
    Organization,
    OrganizationMember,
    PaymentMilestone,
    Proposal,
    User,
)
from syncally.infrastructure.repositories.agreements import (
    SqlAlchemyAgreementRepository,
    commit_agreement_in_transaction,
    propose_amendment_in_transaction,
    record_approval_in_transaction,
    withdraw_amendment_in_transaction,
)
from syncally.infrastructure.repositories.fulfillment import SqlAlchemyFulfillmentRepository


class AmendmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self._seed()

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _seed(self) -> None:
        self.buyer_user = User(email="buyer@example.com", display_name="Buyer")
        self.seller_user = User(email="seller@example.com", display_name="Seller")
        self.buyer_org = Organization(legal_name="Buyer Co", country_code="US")
        self.seller_org = Organization(legal_name="Seller Co", country_code="CA")
        self.session.add_all([self.buyer_user, self.seller_user, self.buyer_org, self.seller_org])
        self.session.flush()

        self.session.add_all([
            OrganizationMember(user_id=self.buyer_user.id, organization_id=self.buyer_org.id, status="ACTIVE"),
            OrganizationMember(user_id=self.seller_user.id, organization_id=self.seller_org.id, status="ACTIVE"),
        ])
        self.deal = Deal(
            buyer_organization_id=self.buyer_org.id,
            seller_organization_id=self.seller_org.id,
            status="PENDING_APPROVALS",
            version=1,
        )
        self.session.add(self.deal)
        self.session.flush()

        # Build initial valid Schema 2 terms with quantity 100
        item = TradeLineItem(
            id="item-1",
            description="Desk",
            quantity=Decimal("100"),
            unit="each",
            unit_price=Money(Decimal("10"), "USD"),
        )
        shipment = ShipmentTerm(
            id="ship-1",
            destination="Toronto",
            target_date=date(2030, 1, 1),
            allocations=(ShipmentItemAllocation(line_item_id="item-1", quantity=Decimal("100"), unit="each"),),
        )
        payment = PaymentTerm(
            id="pay-1",
            amount=Money(Decimal("1000"), "USD"),
            trigger="seller_invoice",
            due_condition="when seller invoices",
            allocations=(PaymentObligationAllocation(obligation_id="ship-1", amount=Money(Decimal("1000"), "USD")),),
        )
        self.terms = build_terms(
            buyer_id=OrganizationId(self.buyer_org.id),
            seller_id=OrganizationId(self.seller_org.id),
            line_items=(item,),
            shipments=(shipment,),
            payment_terms=(payment,),
            schema_version=2,
        )
        session_row = NegotiationSession(deal_id=self.deal.id, max_rounds=5)
        self.session.add(session_row)
        self.session.flush()

        proposal = Proposal(
            deal_id=self.deal.id,
            negotiation_session_id=session_row.id,
            proposal_number=1,
            author_organization_id=self.buyer_org.id,
            terms_json=self.terms.to_storage_dict(),
            terms_hash=self.terms.terms_hash,
            schema_version=self.terms.schema_version,
            lifecycle_origin="LEGACY",
            status="ACCEPTED_AS_CANDIDATE",
        )
        self.session.add(proposal)
        self.session.flush()

        self.version_1 = AgreementVersion(
            deal_id=self.deal.id,
            proposal_id=proposal.id,
            version_number=1,
            canonical_terms_json=self.terms.to_storage_dict(),
            terms_hash=self.terms.terms_hash,
            schema_version=self.terms.schema_version,
            status="PENDING_APPROVAL",
            created_by=self.buyer_user.id,
        )
        self.session.add(self.version_1)
        self.session.flush()
        self.deal.current_agreement_version_id = self.version_1.id
        self.session.commit()

    def _commit_v1(self) -> None:
        # Both parties approve and commit v1
        record_approval_in_transaction(
            self.session,
            RecordApprovalCommand(
                deal_id=self.deal.id,
                version_number=1,
                terms_hash=self.version_1.terms_hash,
                organization_id=self.buyer_org.id,
                user_id=self.buyer_user.id,
                decision=ApprovalDecision.APPROVE,
            ),
        )
        record_approval_in_transaction(
            self.session,
            RecordApprovalCommand(
                deal_id=self.deal.id,
                version_number=1,
                terms_hash=self.version_1.terms_hash,
                organization_id=self.seller_org.id,
                user_id=self.seller_user.id,
                decision=ApprovalDecision.APPROVE,
            ),
        )
        commit_agreement_in_transaction(
            self.session,
            CommitAgreementCommand(
                deal_id=self.deal.id,
                expected_version=1,
                expected_terms_hash=self.version_1.terms_hash,
                user_id=self.buyer_user.id,
                organization_id=self.buyer_org.id,
            ),
        )

    def _make_amended_terms(self, quantity_delta: Decimal = Decimal("50")) -> TradeTerms:
        """Create new terms based on self.terms with updated line item quantity."""
        new_items = []
        for item in self.terms.line_items:
            new_qty = Decimal(item.quantity) + quantity_delta
            new_items.append(
                TradeLineItem(
                    id=item.id,
                    description=item.description,
                    sku=item.sku,
                    quantity=new_qty,
                    unit=item.unit,
                    unit_price=item.unit_price,
                )
            )
        new_shipments = []
        for s in self.terms.shipments:
            new_shipments.append(
                ShipmentTerm(
                    id=s.id,
                    destination=s.destination,
                    quantity=Decimal(s.quantity) + quantity_delta if s.quantity else None,
                    target_date=s.target_date,
                    allocations=tuple(
                        ShipmentItemAllocation(
                            line_item_id=a.line_item_id,
                            quantity=Decimal(a.quantity) + quantity_delta,
                            unit=a.unit,
                        )
                        for a in s.allocations
                    ),
                )
            )
        # Total amount update
        new_price = new_items[0].unit_price.amount * Decimal(new_items[0].quantity)
        new_payment_terms = (
            PaymentTerm(
                id=self.terms.payment_terms[0].id,
                amount=Money(new_price, self.terms.payment_terms[0].amount.currency),
                trigger=self.terms.payment_terms[0].trigger,
                due_condition=self.terms.payment_terms[0].due_condition,
                allocations=tuple(
                    PaymentObligationAllocation(
                        obligation_id=alloc.obligation_id,
                        amount=Money(new_price, alloc.amount.currency),
                    )
                    for alloc in self.terms.payment_terms[0].allocations
                ),
            ),
        )
        return TradeTerms(
            buyer_id=self.terms.buyer_id,
            seller_id=self.terms.seller_id,
            line_items=tuple(new_items),
            shipments=tuple(new_shipments),
            payment_terms=new_payment_terms,
            delivery_location=self.terms.delivery_location,
            incoterm=self.terms.incoterm,
            cancellation_terms=self.terms.cancellation_terms,
            schema_version=self.terms.schema_version,
        )

    def test_propose_amendment_on_uncommitted_deal_fails(self) -> None:
        """Cannot propose an amendment until deal is committed."""
        amended = self._make_amended_terms()
        with self.assertRaises(Exception):
            propose_amendment_in_transaction(
                self.session,
                ProposeAmendmentCommand(
                    deal_id=self.deal.id,
                    author_organization_id=self.buyer_org.id,
                    user_id=self.buyer_user.id,
                    prior_version_number=1,
                    prior_terms_hash=self.version_1.terms_hash,
                    terms=amended,
                ),
            )

    def test_propose_amendment_on_committed_deal_succeeds(self) -> None:
        """Proposing creates pending candidate v2 with lineage pointing to v1."""
        self._commit_v1()
        amended = self._make_amended_terms()
        rationale = "Customer increased order by 50 units."

        cand = propose_amendment_in_transaction(
            self.session,
            ProposeAmendmentCommand(
                deal_id=self.deal.id,
                author_organization_id=self.buyer_org.id,
                user_id=self.buyer_user.id,
                prior_version_number=1,
                prior_terms_hash=self.version_1.terms_hash,
                terms=amended,
                rationale=rationale,
            ),
        )

        self.assertEqual(cand.version_number, 2)
        self.assertEqual(cand.status, AgreementStatus.PENDING_APPROVAL)
        self.assertEqual(cand.prior_terms_hash, self.version_1.terms_hash)
        self.assertEqual(cand.amendment_rationale, rationale)
        self.assertEqual(str(cand.prior_agreement_version_id), str(self.version_1.id))

        # Check in DB that deal current_agreement_version_id is STILL version 1 while candidate is pending!
        deal_row = self.session.get(Deal, self.deal.id)
        self.assertEqual(deal_row.current_agreement_version_id, self.version_1.id)

    def test_propose_amendment_stale_prior_version_or_wrong_hash_rejected(self) -> None:
        self._commit_v1()
        amended = self._make_amended_terms()

        # Wrong prior version number
        with self.assertRaises(StalePriorVersion):
            propose_amendment_in_transaction(
                self.session,
                ProposeAmendmentCommand(
                    deal_id=self.deal.id,
                    author_organization_id=self.buyer_org.id,
                    user_id=self.buyer_user.id,
                    prior_version_number=99,
                    prior_terms_hash=self.version_1.terms_hash,
                    terms=amended,
                ),
            )

        # Wrong prior terms hash
        with self.assertRaises(WrongPriorHash):
            propose_amendment_in_transaction(
                self.session,
                ProposeAmendmentCommand(
                    deal_id=self.deal.id,
                    author_organization_id=self.buyer_org.id,
                    user_id=self.buyer_user.id,
                    prior_version_number=1,
                    prior_terms_hash="0" * 64,
                    terms=amended,
                ),
            )

    def test_propose_amendment_identical_terms_rejected(self) -> None:
        self._commit_v1()
        with self.assertRaises(AmendmentConflict):
            propose_amendment_in_transaction(
                self.session,
                ProposeAmendmentCommand(
                    deal_id=self.deal.id,
                    author_organization_id=self.buyer_org.id,
                    user_id=self.buyer_user.id,
                    prior_version_number=1,
                    prior_terms_hash=self.version_1.terms_hash,
                    terms=self.terms,  # identical to v1
                ),
            )

    def test_propose_amendment_conflict_and_replace_pending(self) -> None:
        self._commit_v1()
        amended_v2 = self._make_amended_terms(Decimal("50"))
        propose_amendment_in_transaction(
            self.session,
            ProposeAmendmentCommand(
                deal_id=self.deal.id,
                author_organization_id=self.buyer_org.id,
                user_id=self.buyer_user.id,
                prior_version_number=1,
                prior_terms_hash=self.version_1.terms_hash,
                terms=amended_v2,
            ),
        )

        amended_v3 = self._make_amended_terms(Decimal("100"))
        # Second propose without replace flag fails with AmendmentConflict
        with self.assertRaises(AmendmentConflict):
            propose_amendment_in_transaction(
                self.session,
                ProposeAmendmentCommand(
                    deal_id=self.deal.id,
                    author_organization_id=self.buyer_org.id,
                    user_id=self.buyer_user.id,
                    prior_version_number=1,
                    prior_terms_hash=self.version_1.terms_hash,
                    terms=amended_v3,
                    replace_pending_draft=False,
                ),
            )

        # Second propose with replace_pending_draft=True voids v2 and creates v3
        v3 = propose_amendment_in_transaction(
            self.session,
            ProposeAmendmentCommand(
                deal_id=self.deal.id,
                author_organization_id=self.buyer_org.id,
                user_id=self.buyer_user.id,
                prior_version_number=1,
                prior_terms_hash=self.version_1.terms_hash,
                terms=amended_v3,
                replace_pending_draft=True,
            ),
        )
        self.assertEqual(v3.version_number, 3)
        v2_row = self.session.scalar(
            select(AgreementVersion).where(
                AgreementVersion.deal_id == self.deal.id,
                AgreementVersion.version_number == 2,
            )
        )
        self.assertEqual(v2_row.status, AgreementStatus.VOIDED.value)

    def test_withdraw_amendment(self) -> None:
        self._commit_v1()
        amended = self._make_amended_terms()
        cand = propose_amendment_in_transaction(
            self.session,
            ProposeAmendmentCommand(
                deal_id=self.deal.id,
                author_organization_id=self.buyer_org.id,
                user_id=self.buyer_user.id,
                prior_version_number=1,
                prior_terms_hash=self.version_1.terms_hash,
                terms=amended,
            ),
        )

        withdrawn = withdraw_amendment_in_transaction(
            self.session,
            WithdrawAmendmentCommand(
                deal_id=self.deal.id,
                version_number=cand.version_number,
                terms_hash=cand.terms_hash,
                user_id=self.buyer_user.id,
                organization_id=self.buyer_org.id,
            ),
        )
        self.assertEqual(withdrawn.status, AgreementStatus.VOIDED)

        # Verify DB status is VOIDED
        cand_row = self.session.scalar(
            select(AgreementVersion).where(
                AgreementVersion.id == cand.version_id,
            )
        )
        self.assertEqual(cand_row.status, "VOIDED")

    def test_assess_impact_blockers(self) -> None:
        self._commit_v1()
        repo = SqlAlchemyAgreementRepository(self.session)

        # Case A: Reducing delivery below fulfilled quantity
        # Add a delivery obligation and a fulfilled event (100 confirmed)
        v1_row = self.session.get(AgreementVersion, self.version_1.id)
        obl = self.session.scalar(
            select(Obligation).where(
                Obligation.deal_id == self.deal.id,
                Obligation.obligation_type == "DELIVERY",
            )
        )
        self.session.add(
            FulfillmentEvent(
                deal_id=self.deal.id,
                agreement_version_id=v1_row.id,
                terms_hash=v1_row.terms_hash,
                obligation_id=obl.id,
                actor_organization_id=self.seller_org.id,
                actor_user_id=self.seller_user.id,
                event_type="CONFIRMED",
                quantity="100",
                unit=self.terms.line_items[0].unit,
                idempotency_key=str(uuid4()),
                request_hash="a" * 64,
                version=1,
            )
        )
        self.session.flush()

        # Attempt to reduce shipment quantity below 100
        reduced_terms = self._make_amended_terms(Decimal("-50"))  # original was 100, now 50
        impact = repo.assess_amendment_impact(self.deal.id, proposed_terms=reduced_terms)
        self.assertFalse(impact.can_commit)
        self.assertTrue(any("already been fulfilled" in b for b in impact.blockers))

        # Case B: Modifying or deleting a paid milestone
        # Mark milestone as PAID
        m = self.session.scalar(
            select(PaymentMilestone).where(PaymentMilestone.deal_id == self.deal.id)
        )
        m.status = "PAID"
        self.session.flush()

        # Delete or alter the paid milestone amount
        impact_paid = repo.assess_amendment_impact(self.deal.id, proposed_terms=reduced_terms)
        self.assertFalse(impact_paid.can_commit)
        self.assertTrue(any("Paid milestone" in b for b in impact_paid.blockers))

    def test_commit_clean_amendment_succeeds_and_updates_deal(self) -> None:
        self._commit_v1()
        amended = self._make_amended_terms(Decimal("50"))

        cand = propose_amendment_in_transaction(
            self.session,
            ProposeAmendmentCommand(
                deal_id=self.deal.id,
                author_organization_id=self.buyer_org.id,
                user_id=self.buyer_user.id,
                prior_version_number=1,
                prior_terms_hash=self.version_1.terms_hash,
                terms=amended,
            ),
        )

        # Both parties approve candidate v2
        record_approval_in_transaction(
            self.session,
            RecordApprovalCommand(
                deal_id=self.deal.id,
                version_number=cand.version_number,
                terms_hash=cand.terms_hash,
                organization_id=self.buyer_org.id,
                user_id=self.buyer_user.id,
                decision=ApprovalDecision.APPROVE,
            ),
        )
        record_approval_in_transaction(
            self.session,
            RecordApprovalCommand(
                deal_id=self.deal.id,
                version_number=cand.version_number,
                terms_hash=cand.terms_hash,
                organization_id=self.seller_org.id,
                user_id=self.seller_user.id,
                decision=ApprovalDecision.APPROVE,
            ),
        )

        # Commit v2
        committed = commit_agreement_in_transaction(
            self.session,
            CommitAgreementCommand(
                deal_id=self.deal.id,
                expected_version=cand.version_number,
                expected_terms_hash=cand.terms_hash,
                user_id=self.buyer_user.id,
                organization_id=self.buyer_org.id,
            ),
        )

        self.assertEqual(committed.version_number, 2)
        self.assertEqual(committed.status, AgreementStatus.COMMITTED)

        # Check DB states
        v1_row = self.session.get(AgreementVersion, self.version_1.id)
        v2_row = self.session.get(AgreementVersion, cand.version_id)
        deal_row = self.session.get(Deal, self.deal.id)

        self.assertEqual(v1_row.status, AgreementStatus.SUPERSEDED.value)
        self.assertEqual(v2_row.status, AgreementStatus.COMMITTED.value)
        self.assertEqual(deal_row.current_agreement_version_id, v2_row.id)
        self.assertEqual(deal_row.version, 3)

        # Derived obligations and milestones exist for v2
        v2_obligations = list(
            self.session.scalars(
                select(Obligation).where(Obligation.agreement_version_id == v2_row.id)
            )
        )
        v2_milestones = list(
            self.session.scalars(
                select(PaymentMilestone).where(
                    PaymentMilestone.agreement_version_id == v2_row.id
                )
            )
        )
        self.assertGreater(len(v2_obligations), 0)
        self.assertGreater(len(v2_milestones), 0)

    def test_historical_export_bytes_preservation(self) -> None:
        """Historical export display terms remain 100% byte-accurate after amendment."""
        self._commit_v1()
        v1_initial_display = export_display_terms(self.version_1.canonical_terms_json)

        # Amend and commit v2
        amended = self._make_amended_terms(Decimal("50"))
        cand = propose_amendment_in_transaction(
            self.session,
            ProposeAmendmentCommand(
                deal_id=self.deal.id,
                author_organization_id=self.buyer_org.id,
                user_id=self.buyer_user.id,
                prior_version_number=1,
                prior_terms_hash=self.version_1.terms_hash,
                terms=amended,
            ),
        )
        record_approval_in_transaction(
            self.session,
            RecordApprovalCommand(
                deal_id=self.deal.id,
                version_number=2,
                terms_hash=cand.terms_hash,
                organization_id=self.buyer_org.id,
                user_id=self.buyer_user.id,
                decision=ApprovalDecision.APPROVE,
            ),
        )
        record_approval_in_transaction(
            self.session,
            RecordApprovalCommand(
                deal_id=self.deal.id,
                version_number=2,
                terms_hash=cand.terms_hash,
                organization_id=self.seller_org.id,
                user_id=self.seller_user.id,
                decision=ApprovalDecision.APPROVE,
            ),
        )
        commit_agreement_in_transaction(
            self.session,
            CommitAgreementCommand(
                deal_id=self.deal.id,
                expected_version=2,
                expected_terms_hash=cand.terms_hash,
                user_id=self.buyer_user.id,
                organization_id=self.buyer_org.id,
            ),
        )

        # Re-fetch v1 and verify export display terms are identical
        self.session.expire_all()
        v1_reloaded = self.session.get(AgreementVersion, self.version_1.id)
        v1_after_display = export_display_terms(v1_reloaded.canonical_terms_json)
        self.assertEqual(v1_initial_display, v1_after_display)
        self.assertEqual(v1_reloaded.terms_hash, self.version_1.terms_hash)

    def test_fulfillment_tracking_carries_forward_across_amendments(self) -> None:
        """Fulfillment events recorded against prior versions are preserved and carried forward after amendment."""
        self._commit_v1()
        fulfillment_repo = SqlAlchemyFulfillmentRepository(self.session)

        # Initial snapshot on v1
        snap1 = fulfillment_repo.get_snapshot(self.deal.id)
        self.assertEqual(snap1.shipped_quantity, Decimal("0"))
        self.assertEqual(snap1.confirmed_quantity, Decimal("0"))

        obl1 = self.session.scalar(
            select(Obligation).where(
                Obligation.deal_id == self.deal.id,
                Obligation.agreement_version_id == self.version_1.id,
                Obligation.obligation_type == "DELIVERY",
            )
        )
        assert obl1 is not None

        # Record SHIPPED and CONFIRMED events (5 units) on v1
        self.session.add(
            FulfillmentEvent(
                id=uuid4(),
                deal_id=self.deal.id,
                agreement_version_id=self.version_1.id,
                terms_hash=self.version_1.terms_hash,
                obligation_id=obl1.id,
                actor_organization_id=self.seller_org.id,
                actor_user_id=self.seller_user.id,
                event_type="SHIPPED",
                quantity="5",
                unit="pieces",
                request_hash="0" * 64,
                version=1,
                source_type="USER_ATTESTATION",
                idempotency_key=str(uuid4()),
            )
        )
        self.session.add(
            FulfillmentEvent(
                id=uuid4(),
                deal_id=self.deal.id,
                agreement_version_id=self.version_1.id,
                terms_hash=self.version_1.terms_hash,
                obligation_id=obl1.id,
                actor_organization_id=self.buyer_org.id,
                actor_user_id=self.buyer_user.id,
                event_type="CONFIRMED",
                quantity="5",
                unit="pieces",
                request_hash="1" * 64,
                version=2,
                source_type="USER_ATTESTATION",
                idempotency_key=str(uuid4()),
            )
        )
        self.session.commit()

        snap_after_events = fulfillment_repo.get_snapshot(self.deal.id)
        self.assertEqual(snap_after_events.shipped_quantity, Decimal("5"))
        self.assertEqual(snap_after_events.confirmed_quantity, Decimal("5"))

        # Amend to quantity 12 and commit v2
        amended = self._make_amended_terms(Decimal("12"))
        cand = propose_amendment_in_transaction(
            self.session,
            ProposeAmendmentCommand(
                deal_id=self.deal.id,
                author_organization_id=self.buyer_org.id,
                user_id=self.buyer_user.id,
                prior_version_number=1,
                prior_terms_hash=self.version_1.terms_hash,
                terms=amended,
            ),
        )
        record_approval_in_transaction(
            self.session,
            RecordApprovalCommand(
                deal_id=self.deal.id,
                version_number=2,
                terms_hash=cand.terms_hash,
                organization_id=self.buyer_org.id,
                user_id=self.buyer_user.id,
                decision=ApprovalDecision.APPROVE,
            ),
        )
        record_approval_in_transaction(
            self.session,
            RecordApprovalCommand(
                deal_id=self.deal.id,
                version_number=2,
                terms_hash=cand.terms_hash,
                organization_id=self.seller_org.id,
                user_id=self.seller_user.id,
                decision=ApprovalDecision.APPROVE,
            ),
        )
        commit_agreement_in_transaction(
            self.session,
            CommitAgreementCommand(
                deal_id=self.deal.id,
                expected_version=2,
                expected_terms_hash=cand.terms_hash,
                user_id=self.buyer_user.id,
                organization_id=self.buyer_org.id,
            ),
        )
        self.session.commit()

        # Snapshot on v2 MUST carry forward the 5 shipped / 5 confirmed!
        snap_v2 = fulfillment_repo.get_snapshot(self.deal.id)
        self.assertEqual(snap_v2.shipped_quantity, Decimal("5"))
        self.assertEqual(snap_v2.confirmed_quantity, Decimal("5"))
        self.assertEqual(snap_v2.planned_quantity, Decimal("112"))

        # Now append a new event on v2 (ship remaining 7 units)
        v2_row = self.session.scalar(
            select(AgreementVersion).where(
                AgreementVersion.deal_id == self.deal.id,
                AgreementVersion.version_number == 2,
            )
        )
        obl2 = self.session.scalar(
            select(Obligation).where(
                Obligation.deal_id == self.deal.id,
                Obligation.agreement_version_id == v2_row.id,
                Obligation.obligation_type == "DELIVERY",
            )
        )
        self.session.add(
            FulfillmentEvent(
                id=uuid4(),
                deal_id=self.deal.id,
                agreement_version_id=v2_row.id,
                terms_hash=v2_row.terms_hash,
                obligation_id=obl2.id,
                actor_organization_id=self.seller_org.id,
                actor_user_id=self.seller_user.id,
                event_type="SHIPPED",
                quantity="7",
                unit="pieces",
                request_hash="2" * 64,
                version=3,
                source_type="USER_ATTESTATION",
                idempotency_key=str(uuid4()),
            )
        )
        self.session.commit()

        snap_v2_final = fulfillment_repo.get_snapshot(self.deal.id)
        self.assertEqual(snap_v2_final.shipped_quantity, Decimal("12"))
        self.assertEqual(snap_v2_final.confirmed_quantity, Decimal("5"))

    def test_paid_milestone_preserved_and_prevents_duplicate_charge(self) -> None:
        """Paid milestone on prior version is preserved and cannot be double-charged on amended version."""
        self._commit_v1()

        # Grant seller_user FINANCE capability
        seller_member = self.session.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == self.seller_org.id,
                OrganizationMember.user_id == self.seller_user.id,
            )
        )
        assert seller_member is not None
        seller_member.capabilities = ["FINANCE"]

        # Mark milestone on v1 as PAID
        m1 = self.session.scalar(
            select(PaymentMilestone).where(
                PaymentMilestone.deal_id == self.deal.id,
                PaymentMilestone.agreement_version_id == self.version_1.id,
            )
        )
        assert m1 is not None
        m1.status = "PAID"
        self.session.commit()

        # Amend agreement and commit v2
        amended = self._make_amended_terms(Decimal("15"))
        cand = propose_amendment_in_transaction(
            self.session,
            ProposeAmendmentCommand(
                deal_id=self.deal.id,
                author_organization_id=self.buyer_org.id,
                user_id=self.buyer_user.id,
                prior_version_number=1,
                prior_terms_hash=self.version_1.terms_hash,
                terms=amended,
            ),
        )
        record_approval_in_transaction(
            self.session,
            RecordApprovalCommand(
                deal_id=self.deal.id,
                version_number=2,
                terms_hash=cand.terms_hash,
                organization_id=self.buyer_org.id,
                user_id=self.buyer_user.id,
                decision=ApprovalDecision.APPROVE,
            ),
        )
        record_approval_in_transaction(
            self.session,
            RecordApprovalCommand(
                deal_id=self.deal.id,
                version_number=2,
                terms_hash=cand.terms_hash,
                organization_id=self.seller_org.id,
                user_id=self.seller_user.id,
                decision=ApprovalDecision.APPROVE,
            ),
        )
        commit_agreement_in_transaction(
            self.session,
            CommitAgreementCommand(
                deal_id=self.deal.id,
                expected_version=2,
                expected_terms_hash=cand.terms_hash,
                user_id=self.buyer_user.id,
                organization_id=self.buyer_org.id,
            ),
        )
        self.session.commit()

        # Verify milestone on v2 carried forward status == 'PAID'
        v2_row = self.session.scalar(
            select(AgreementVersion).where(
                AgreementVersion.deal_id == self.deal.id,
                AgreementVersion.version_number == 2,
            )
        )
        m2 = self.session.scalar(
            select(PaymentMilestone).where(
                PaymentMilestone.deal_id == self.deal.id,
                PaymentMilestone.agreement_version_id == v2_row.id,
            )
        )
        self.assertIsNotNone(m2)
        self.assertEqual(m2.status, "PAID")

        # Attempting to authorize payment intent for m2 must raise HTTPException(409)
        from fastapi import HTTPException

        from syncally.api.payments import (
            AuthorizePaymentRequest,
            authorize_payment_route,
        )
        from syncally.infrastructure.repositories.deals import SqlAlchemyDealRepository

        seller_actor = ActorContext(
            user_id=self.seller_user.id,
            organization_ids=frozenset({self.seller_org.id}),
        )
        deal_repo = SqlAlchemyDealRepository(self.session)
        with self.assertRaises(HTTPException) as cm:
            authorize_payment_route(
                deal_id=self.deal.id,
                payload=AuthorizePaymentRequest(
                    payment_milestone_id=m2.id,
                    idempotency_key=str(uuid4()),
                ),
                actor=seller_actor,
                deal_repository=deal_repo,
                db=self.session,
            )
        self.assertEqual(cm.exception.status_code, 409)
        self.assertIn("already been paid", cm.exception.detail.lower())


if __name__ == "__main__":
    unittest.main()
