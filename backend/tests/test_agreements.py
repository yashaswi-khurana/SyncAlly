"""Database-backed tests for approval recording and CommitAgreement."""

import json
import unittest
from datetime import UTC, datetime

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
    record_approval,
)
from syncally.domain.agreements.agreement import ApprovalDecision
from syncally.domain.shared.identifiers import OrganizationId
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
    Proposal,
    User,
)
from syncally.infrastructure.repositories.agreements import (
    SqlAlchemyAgreementRepository,
    commit_agreement_in_transaction,
)


class AgreementCommitTests(unittest.TestCase):
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
        canonical = json.loads(self.terms.canonical_json())
        proposal = Proposal(
            deal_id=self.deal.id,
            negotiation_session_id=session_row.id,
            proposal_number=1,
            author_organization_id=self.buyer_org.id,
            terms_json=canonical,
            terms_hash=self.terms.terms_hash,
        )
        self.session.add(proposal)
        self.session.flush()
        self.version = AgreementVersion(
            deal_id=self.deal.id,
            proposal_id=proposal.id,
            version_number=version_number,
            canonical_terms_json=canonical,
            terms_hash=self.terms.terms_hash,
            status=status,
            created_by=self.buyer_user.id,
        )
        self.session.add(self.version)
        self.session.flush()
        self.deal.current_agreement_version_id = self.version.id
        self.session.commit()

    def _approve(self, organization_id, user_id) -> None:
        record_approval(
            RecordApprovalCommand(
                deal_id=self.deal.id,
                version_number=self.version.version_number,
                terms_hash=self.terms.terms_hash,
                organization_id=organization_id,
                user_id=user_id,
                decision=ApprovalDecision.APPROVE,
            ),
            SqlAlchemyAgreementRepository(self.session),
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
            self.session.scalar(select(OutboxEvent)).event_type, "AGREEMENT_COMMITTED"
        )

    def test_commit_rejects_only_one_side_approved(self) -> None:
        self._approve(self.buyer_org.id, self.buyer_user.id)

        with self.assertRaises(Exception):
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
            record_approval(
                RecordApprovalCommand(
                    deal_id=self.deal.id,
                    version_number=self.version.version_number,
                    terms_hash="0" * 64,
                    organization_id=self.buyer_org.id,
                    user_id=self.buyer_user.id,
                    decision=ApprovalDecision.APPROVE,
                ),
                SqlAlchemyAgreementRepository(self.session),
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

        with Session(self.engine) as other_session:
            with self.assertRaises(AgreementAlreadyCommitted):
                commit_agreement_in_transaction(other_session, command, now=datetime.now(UTC))

        self.assertEqual(self.session.get(AgreementVersion, self.version.id).status, "COMMITTED")
        self.assertEqual(len(self.session.scalars(select(Obligation)).all()), 2)
        self.assertEqual(len(self.session.scalars(select(AuditEvent)).all()), 1)
        self.assertEqual(len(self.session.scalars(select(OutboxEvent)).all()), 1)


if __name__ == "__main__":
    unittest.main()
