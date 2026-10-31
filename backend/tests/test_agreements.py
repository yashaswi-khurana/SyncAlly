"""Database-backed tests for approval recording and CommitAgreement."""

import json
import unittest
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from test_domain_fixes import build_terms

from syncally.application.agreements import (
    AgreementAlreadyCommitted,
    CommitAgreementCommand,
    DuplicateApproval,
    RecordApprovalCommand,
    StaleAgreementVersion,
    UnauthorizedApproval,
    WrongTermsHash,
    compare_agreement_terms,
)
from syncally.domain.agreements.agreement import ApprovalDecision
from syncally.domain.agreements.trade_terms import (
    PaymentTerm,
    ShipmentTerm,
    TradeLineItem,
    TradeTerms,
)
from syncally.domain.shared.errors import InvalidTransition
from syncally.domain.shared.identifiers import OrganizationId
from syncally.domain.shared.money import Money
from syncally.infrastructure.models import (
    AgreementVersion,
    AuditEvent,
    Base,
    Deal,
    NegotiationSession,
    Obligation,
    Organization,
    OrganizationMember,
    OutboxEvent,
    PaymentMilestone,
    Proposal,
    User,
)
from syncally.infrastructure.repositories.agreements import (
    commit_agreement_in_transaction,
    record_approval_in_transaction,
)


class AgreementCommitTests(unittest.TestCase):
    def test_comparison_normalizes_copies_and_preserves_duplicate_counts(self) -> None:
        from copy import deepcopy

        before = build_terms().to_storage_dict()
        after = deepcopy(before)
        after["line_items"][0]["quantity"] += ".000"
        after["delivery_location"] = after["delivery_location"].upper()
        saved = deepcopy(after)
        result = compare_agreement_terms(before, after)
        self.assertEqual(result["fields"], [])
        self.assertTrue(all(not value for group in result["collections"].values() for value in group.values()))
        self.assertEqual(after, saved)
        before["shipments"] *= 2
        result = compare_agreement_terms(before, after)
        self.assertEqual(len(result["collections"]["shipments"]["removed"]), 1)
        self.assertEqual(result["collections"]["shipments"]["modified"], [])

    def test_comparison_all_collections_exact_matches_first_and_ambiguous_pairs(self) -> None:
        from copy import deepcopy

        before = build_terms().to_storage_dict()
        for name in ("line_items", "shipments", "payment_terms"):
            before[name] = [deepcopy(before[name][0]) for _ in range(3)]
        after = deepcopy(before)
        after["line_items"][0]["description"] = "Chair"
        after["line_items"][1]["description"] = "Table"
        after["shipments"][0]["destination"] = "New warehouse"
        after["payment_terms"][0]["trigger"] = "delivery"
        saved_before, saved_after = deepcopy(before), deepcopy(after)
        result = compare_agreement_terms(before, after)
        self.assertEqual(len(result["collections"]["line_items"]["added"]), 2)
        self.assertEqual(len(result["collections"]["line_items"]["removed"]), 2)
        self.assertEqual(result["collections"]["line_items"]["modified"], [])
        for name in ("shipments", "payment_terms"):
            self.assertEqual(len(result["collections"][name]["modified"]), 1)
        for name in ("line_items", "shipments", "payment_terms"):
            after[name].reverse()
        self.assertEqual(compare_agreement_terms(before, after), result)
        self.assertEqual(before, saved_before)
        for name in ("line_items", "shipments", "payment_terms"):
            after[name].reverse()
        self.assertEqual(after, saved_after)

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

    def _seed(self, *, version_number: int = 1, status: str = "PENDING_APPROVAL") -> None:
        self.buyer_user = User(email="buyer@example.com", display_name="Buyer")
        self.seller_user = User(email="seller@example.com", display_name="Seller")
        self.buyer_org = Organization(legal_name="Buyer Co", country_code="US")
        self.seller_org = Organization(legal_name="Seller Co", country_code="CA")
        self.session.add_all(
            [self.buyer_user, self.seller_user, self.buyer_org, self.seller_org]
        )
        self.session.flush()
        self.session.add_all(
            [
                OrganizationMember(
                    user_id=self.buyer_user.id, organization_id=self.buyer_org.id, status="ACTIVE"
                ),
                OrganizationMember(
                    user_id=self.seller_user.id,
                    organization_id=self.seller_org.id,
                    status="ACTIVE",
                ),
            ]
        )
        self.deal = Deal(
            buyer_organization_id=self.buyer_org.id,
            seller_organization_id=self.seller_org.id,
            status="PENDING_APPROVALS",
            version=2,
        )
        self.session.add(self.deal)
        self.session.flush()

        # Demo-compliant terms (single USD line item/shipment/payment term,
        # seller_invoice trigger, a target delivery date) so Agreement.commit's
        # validate_for_commit() accepts them - see trade_terms.py.
        self.terms = build_terms(
            buyer_id=OrganizationId(self.buyer_org.id),
            seller_id=OrganizationId(self.seller_org.id),
        )
        session_row = NegotiationSession(deal_id=self.deal.id, max_rounds=5)
        self.session.add(session_row)
        self.session.flush()
        proposal = Proposal(
            deal_id=self.deal.id,
            negotiation_session_id=session_row.id,
            proposal_number=1,
            author_organization_id=self.buyer_org.id,
            terms_json=json.loads(self.terms.canonical_json()),
            terms_hash=self.terms.terms_hash,
        )
        self.session.add(proposal)
        self.session.flush()
        self.version = AgreementVersion(
            deal_id=self.deal.id,
            proposal_id=proposal.id,
            version_number=version_number,
            canonical_terms_json=self.terms.to_storage_dict(),
            terms_hash=self.terms.terms_hash,
            status=status,
            created_by=self.buyer_user.id,
        )
        self.session.add(self.version)
        self.session.flush()
        self.deal.current_agreement_version_id = self.version.id
        self.session.commit()

    def _approve(self, organization_id, user_id, decision=ApprovalDecision.APPROVE) -> None:
        record_approval_in_transaction(
            self.session,
            RecordApprovalCommand(
                deal_id=self.deal.id,
                version_number=self.version.version_number,
                terms_hash=self.terms.terms_hash,
                organization_id=organization_id,
                user_id=user_id,
                decision=decision,
            ),
        )

    def test_bilateral_approval_commits_agreement_deal_and_obligations(self) -> None:
        self._approve(self.buyer_org.id, self.buyer_user.id)
        self._approve(self.seller_org.id, self.seller_user.id)

        agreement = commit_agreement_in_transaction(
            self.session,
            CommitAgreementCommand(
                deal_id=self.deal.id,
                expected_version=self.version.version_number,
                expected_terms_hash=self.terms.terms_hash,
            ),
        )

        self.assertEqual(agreement.status.value, "COMMITTED")

        stored_version = self.session.get(AgreementVersion, self.version.id)
        self.assertEqual(stored_version.status, "COMMITTED")
        self.assertIsNotNone(stored_version.committed_at)

        stored_deal = self.session.get(Deal, self.deal.id)
        self.assertEqual(stored_deal.status, "AGREED")
        self.assertEqual(stored_deal.version, 3)

        obligations = self.session.scalars(
            select(Obligation).where(Obligation.agreement_version_id == self.version.id)
        ).all()
        self.assertEqual({o.obligation_type for o in obligations}, {"DELIVERY", "PAYMENT"})
        self.assertEqual(len(obligations), 2)

        self.assertEqual(self.session.scalar(select(AuditEvent)).event_type, "AGREEMENT_COMMITTED")
        self.assertEqual(
            self.session.scalar(
                select(OutboxEvent).where(OutboxEvent.event_type == "AGREEMENT_COMMITTED")
            ).event_type,
            "AGREEMENT_COMMITTED",
        )
        approval_notifications = self.session.scalars(
            select(OutboxEvent).where(OutboxEvent.event_type == "DEAL_NOTIFICATION")
        ).all()
        self.assertEqual(len(approval_notifications), 2)
        self.assertTrue(
            all(
                row.payload
                == {
                    "deal_id": str(self.deal.id),
                    "record_id": str(self.version.id),
                    "kind": "AGREEMENT_APPROVAL_RECORDED",
                }
                for row in approval_notifications
            )
        )

    def test_commit_rejects_only_one_side_approved(self) -> None:
        self._approve(self.buyer_org.id, self.buyer_user.id)

        with self.assertRaises(InvalidTransition):
            commit_agreement_in_transaction(
                self.session,
                CommitAgreementCommand(
                    deal_id=self.deal.id,
                    expected_version=self.version.version_number,
                    expected_terms_hash=self.terms.terms_hash,
                ),
            )
        self.assertEqual(
            self.session.get(AgreementVersion, self.version.id).status, "PENDING_APPROVAL"
        )
        self.assertEqual(self.session.scalars(select(Obligation)).all(), [])

    def test_record_approval_rejects_unauthorized_organization(self) -> None:
        outsider = Organization(legal_name="Outsider", country_code="GB")
        outsider_user = User(email="outsider@example.com", display_name="Outsider")
        self.session.add_all([outsider, outsider_user])
        self.session.flush()
        self.session.add(
            OrganizationMember(
                user_id=outsider_user.id, organization_id=outsider.id, status="ACTIVE"
            )
        )
        self.session.commit()

        with self.assertRaises(UnauthorizedApproval):
            self._approve(outsider.id, outsider_user.id)

    def test_record_approval_rejects_stale_version(self) -> None:
        self.version.status = "SUPERSEDED"
        self.session.commit()

        with self.assertRaises(StaleAgreementVersion):
            self._approve(self.buyer_org.id, self.buyer_user.id)

    def test_record_approval_rejects_wrong_hash(self) -> None:
        with self.assertRaises(WrongTermsHash):
            record_approval_in_transaction(
                self.session,
                RecordApprovalCommand(
                    deal_id=self.deal.id,
                    version_number=self.version.version_number,
                    terms_hash="0" * 64,
                    organization_id=self.buyer_org.id,
                    user_id=self.buyer_user.id,
                    decision=ApprovalDecision.APPROVE,
                ),
            )

    def test_record_approval_rejects_repeated_approval(self) -> None:
        self._approve(self.buyer_org.id, self.buyer_user.id)

        with self.assertRaises(DuplicateApproval):
            self._approve(self.buyer_org.id, self.buyer_user.id)

    def test_concurrent_commit_attempts_commit_at_most_once(self) -> None:
        # ponytail: SQLite can't give a real two-transaction race (table-level
        # locking, no row locks for with_for_update), so this drives the two
        # requests back to back instead of with real threads. The guard that
        # matters - the compare-and-swap UPDATE in commit() - still runs on
        # every call; it would also catch two transactions that both passed
        # the initial status check before either wrote, which only genuine
        # concurrent transactions (Postgres in production) could trigger.
        self._approve(self.buyer_org.id, self.buyer_user.id)
        self._approve(self.seller_org.id, self.seller_user.id)
        command = CommitAgreementCommand(
            deal_id=self.deal.id,
            expected_version=self.version.version_number,
            expected_terms_hash=self.terms.terms_hash,
        )

        first = commit_agreement_in_transaction(self.session, command, now=datetime.now(UTC))
        self.assertEqual(first.status.value, "COMMITTED")

        # A retry of the exact same request (e.g. the caller lost the first
        # response) replays idempotently instead of erroring, and must not
        # re-derive obligations/milestones/audit/outbox rows.
        with Session(self.engine) as other_session:
            replay = commit_agreement_in_transaction(other_session, command, now=datetime.now(UTC))
            self.assertEqual(replay.status.value, "COMMITTED")

        self.assertEqual(self.session.get(AgreementVersion, self.version.id).status, "COMMITTED")
        self.assertEqual(len(self.session.scalars(select(Obligation)).all()), 2)
        self.assertEqual(len(self.session.scalars(select(AuditEvent)).all()), 1)
        self.assertEqual(len(self.session.scalars(select(OutboxEvent)).all()), 3)

    def test_commit_retry_with_mismatched_hash_is_rejected(self) -> None:
        self._approve(self.buyer_org.id, self.buyer_user.id)
        self._approve(self.seller_org.id, self.seller_user.id)
        command = CommitAgreementCommand(
            deal_id=self.deal.id,
            expected_version=self.version.version_number,
            expected_terms_hash=self.terms.terms_hash,
        )
        commit_agreement_in_transaction(self.session, command, now=datetime.now(UTC))

        with self.assertRaises(AgreementAlreadyCommitted):
            commit_agreement_in_transaction(
                self.session,
                CommitAgreementCommand(
                    deal_id=self.deal.id,
                    expected_version=self.version.version_number,
                    expected_terms_hash="0" * 64,
                ),
                now=datetime.now(UTC),
            )

    def test_reject_can_be_revised_to_approve(self) -> None:
        self._approve(self.buyer_org.id, self.buyer_user.id, decision=ApprovalDecision.REJECT)
        self._approve(self.buyer_org.id, self.buyer_user.id, decision=ApprovalDecision.APPROVE)
        self._approve(self.seller_org.id, self.seller_user.id)

        agreement = commit_agreement_in_transaction(
            self.session,
            CommitAgreementCommand(
                deal_id=self.deal.id,
                expected_version=self.version.version_number,
                expected_terms_hash=self.terms.terms_hash,
            ),
        )
        self.assertEqual(agreement.status.value, "COMMITTED")

    def test_record_approval_rejects_version_whose_terms_do_not_match_the_deal(self) -> None:
        other_seller = Organization(legal_name="Other Seller", country_code="FR")
        self.session.add(other_seller)
        self.session.flush()
        mismatched_terms = build_terms(
            buyer_id=OrganizationId(self.buyer_org.id),
            seller_id=OrganizationId(other_seller.id),
        )
        self.version.canonical_terms_json = mismatched_terms.to_storage_dict()
        self.version.terms_hash = mismatched_terms.terms_hash
        self.session.commit()

        with self.assertRaises(UnauthorizedApproval):
            record_approval_in_transaction(
                self.session,
                RecordApprovalCommand(
                    deal_id=self.deal.id,
                    version_number=self.version.version_number,
                    terms_hash=mismatched_terms.terms_hash,
                    organization_id=self.buyer_org.id,
                    user_id=self.buyer_user.id,
                    decision=ApprovalDecision.APPROVE,
                ),
            )

    def test_commit_creates_payment_milestone_linked_to_obligation(self) -> None:
        self._approve(self.buyer_org.id, self.buyer_user.id)
        self._approve(self.seller_org.id, self.seller_user.id)

        commit_agreement_in_transaction(
            self.session,
            CommitAgreementCommand(
                deal_id=self.deal.id,
                expected_version=self.version.version_number,
                expected_terms_hash=self.terms.terms_hash,
            ),
        )

        milestone = self.session.scalar(select(PaymentMilestone))
        payment_obligation = self.session.scalar(
            select(Obligation).where(Obligation.obligation_type == "PAYMENT")
        )
        self.assertIsNotNone(milestone)
        self.assertEqual(milestone.obligation_id, payment_obligation.id)
        self.assertEqual(milestone.amount, self.terms.payment_terms[0].amount.amount)
        self.assertEqual(milestone.currency, self.terms.payment_terms[0].amount.currency)
        self.assertEqual(milestone.payer_organization_id, self.buyer_org.id)

    def test_payment_terms_are_part_of_the_terms_hash(self) -> None:
        """Payment timing is a hashed commitment, not presentation-only metadata."""
        canonical = self.terms.canonical_json()
        self.assertIn('"trigger":"seller_invoice"', canonical)
        self.assertIn('"due_condition":"when seller invoices"', canonical)

        def with_timing(trigger: str, due_condition: str) -> TradeTerms:
            return TradeTerms(
                buyer_id=self.terms.buyer_id,
                seller_id=self.terms.seller_id,
                line_items=self.terms.line_items,
                shipments=self.terms.shipments,
                payment_terms=(
                    PaymentTerm(
                        self.terms.payment_terms[0].amount, trigger, due_condition
                    ),
                ),
                delivery_location=self.terms.delivery_location,
            )

        same = with_timing("seller_invoice", "when seller invoices")
        self.assertEqual(same.terms_hash, self.terms.terms_hash)

        self.assertNotEqual(
            with_timing("on_delivery", "when seller invoices").terms_hash,
            self.terms.terms_hash,
        )
        self.assertNotEqual(
            with_timing("seller_invoice", "on delivery").terms_hash,
            self.terms.terms_hash,
        )

    def test_storage_dict_round_trip_preserves_destination_case(self) -> None:
        terms = TradeTerms(
            buyer_id=OrganizationId(self.buyer_org.id),
            seller_id=OrganizationId(self.seller_org.id),
            line_items=(TradeLineItem("Desk", Decimal("1"), "each", Money(Decimal("10"), "USD")),),
            shipments=(ShipmentTerm(Decimal("1"), "Rotterdam Port", date(2030, 1, 1)),),
            payment_terms=(
                PaymentTerm(Money(Decimal("10"), "USD"), "seller_invoice", "when seller invoices"),
            ),
            delivery_location="Rotterdam Port",
        )
        # The hash-oriented canonical_json() casefolds display text so terms
        # differing only by case still hash identically...
        self.assertEqual(json.loads(terms.canonical_json())["delivery_location"], "rotterdam port")

        # ...but to_storage_dict() - what actually gets persisted - keeps it.
        stored = terms.to_storage_dict()
        self.assertEqual(stored["delivery_location"], "Rotterdam Port")

        rebuilt = TradeTerms.from_canonical_json(stored)
        self.assertEqual(rebuilt.delivery_location, "Rotterdam Port")
        self.assertEqual(rebuilt.shipments[0].destination, "Rotterdam Port")
        self.assertEqual(rebuilt.terms_hash, terms.terms_hash)


if __name__ == "__main__":
    unittest.main()
