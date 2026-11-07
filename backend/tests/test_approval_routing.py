"""Integration tests for F15b Approval Routing.

Covers: default bilateral continuity when no policy is configured, PARALLEL
and SEQUENTIAL routing, REJECT as an always-available veto, revoked/stale
approver handling, eligibility validation when saving a policy, and
optimistic-concurrency version conflicts.
"""

import sys
import unittest
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from test_domain_fixes import build_terms

from syncally.application.agreements import (
    CommitAgreementCommand,
    DuplicateApproval,
    NotEligibleApprover,
    OutOfSequenceApproval,
    RecordApprovalCommand,
    RecordRoutingDecisionCommand,
)
from syncally.domain.agreements.agreement import AgreementStatus, ApprovalDecision
from syncally.domain.organizations.approval_routing import (
    ApprovalRoutingMode,
    ApprovalRoutingPolicy,
    RoutingOutcomeStatus,
)
from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import OrganizationId, UserId
from syncally.infrastructure.models import (
    AgreementVersion,
    Base,
    Deal,
    NegotiationSession,
    Organization,
    OrganizationMember,
    Proposal,
    User,
)
from syncally.infrastructure.repositories.agreements import (
    commit_agreement_in_transaction,
    record_approval_in_transaction,
    record_routing_decision_in_transaction,
)
from syncally.infrastructure.repositories.approval_routing import (
    SqlAlchemyApprovalRoutingPolicyRepository,
)


class ApprovalRoutingTestCase(unittest.TestCase):
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

    def _add_member(self, organization_id, *, role="MEMBER", capabilities=()):
        user = User(email=f"{uuid4()}@example.com", display_name="Approver")
        self.session.add(user)
        self.session.flush()
        self.session.add(
            OrganizationMember(
                user_id=user.id,
                organization_id=organization_id,
                status="ACTIVE",
                role=role,
                capabilities=list(capabilities),
            )
        )
        self.session.flush()
        return user

    def _seed(self) -> None:
        self.buyer_user = User(email="buyer@example.com", display_name="Buyer")
        self.seller_user = User(email="seller@example.com", display_name="Seller")
        self.buyer_org = Organization(legal_name="Buyer Co", country_code="US")
        self.seller_org = Organization(legal_name="Seller Co", country_code="CA")
        self.session.add_all([self.buyer_user, self.seller_user, self.buyer_org, self.seller_org])
        self.session.flush()

        self.session.add_all([
            OrganizationMember(
                user_id=self.buyer_user.id, organization_id=self.buyer_org.id,
                status="ACTIVE", role="ADMIN", capabilities=["AGREEMENT_APPROVAL"],
            ),
            OrganizationMember(
                user_id=self.seller_user.id, organization_id=self.seller_org.id,
                status="ACTIVE", role="ADMIN", capabilities=["AGREEMENT_APPROVAL"],
            ),
        ])
        self.deal = Deal(
            buyer_organization_id=self.buyer_org.id,
            seller_organization_id=self.seller_org.id,
            status="PENDING_APPROVALS",
            version=1,
        )
        self.session.add(self.deal)
        self.session.flush()

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

    def _approve(self, organization_id, user_id):
        return record_routing_decision_in_transaction(
            self.session,
            RecordRoutingDecisionCommand(
                deal_id=self.deal.id,
                version_number=1,
                terms_hash=self.version_1.terms_hash,
                organization_id=organization_id,
                user_id=user_id,
                decision=ApprovalDecision.APPROVE,
            ),
        )

    def _reject(self, organization_id, user_id):
        return record_routing_decision_in_transaction(
            self.session,
            RecordRoutingDecisionCommand(
                deal_id=self.deal.id,
                version_number=1,
                terms_hash=self.version_1.terms_hash,
                organization_id=organization_id,
                user_id=user_id,
                decision=ApprovalDecision.REJECT,
            ),
        )

    # -- Default continuity: zero policy means today's single-approver path --

    def test_default_continuity_without_a_policy(self) -> None:
        record_approval_in_transaction(
            self.session,
            RecordApprovalCommand(
                deal_id=self.deal.id, version_number=1, terms_hash=self.version_1.terms_hash,
                organization_id=self.buyer_org.id, user_id=self.buyer_user.id,
                decision=ApprovalDecision.APPROVE,
            ),
        )
        record_approval_in_transaction(
            self.session,
            RecordApprovalCommand(
                deal_id=self.deal.id, version_number=1, terms_hash=self.version_1.terms_hash,
                organization_id=self.seller_org.id, user_id=self.seller_user.id,
                decision=ApprovalDecision.APPROVE,
            ),
        )
        agreement = commit_agreement_in_transaction(
            self.session,
            CommitAgreementCommand(
                deal_id=self.deal.id, expected_version=1,
                expected_terms_hash=self.version_1.terms_hash,
                user_id=self.buyer_user.id, organization_id=self.buyer_org.id,
            ),
        )
        self.assertEqual(agreement.status, AgreementStatus.COMMITTED)

    # -- PARALLEL routing --

    def test_parallel_requires_all_approvers_before_finalizing(self) -> None:
        a1 = self._add_member(self.buyer_org.id, capabilities=["AGREEMENT_APPROVAL"])
        a2 = self._add_member(self.buyer_org.id, capabilities=["AGREEMENT_APPROVAL"])
        policies = SqlAlchemyApprovalRoutingPolicyRepository(self.session)
        policies.save(
            ApprovalRoutingPolicy(
                organization_id=OrganizationId(self.buyer_org.id),
                mode=ApprovalRoutingMode.PARALLEL,
                approver_user_ids=(UserId(a1.id), UserId(a2.id)),
            ),
            expected_version=None,
            updated_by_user_id=self.buyer_user.id,
        )
        self.session.commit()

        outcome_1 = self._approve(self.buyer_org.id, a1.id)
        self.assertEqual(outcome_1.evaluation.status, RoutingOutcomeStatus.PENDING)
        self.assertIsNone(outcome_1.finalized_approval)

        outcome_2 = self._approve(self.buyer_org.id, a2.id)
        self.assertEqual(outcome_2.evaluation.status, RoutingOutcomeStatus.COMPLETED)
        self.assertIsNotNone(outcome_2.finalized_approval)
        self.assertEqual(outcome_2.finalized_approval.decision, ApprovalDecision.APPROVE)

        # Seller org has no policy configured: unchanged default path.
        record_approval_in_transaction(
            self.session,
            RecordApprovalCommand(
                deal_id=self.deal.id, version_number=1, terms_hash=self.version_1.terms_hash,
                organization_id=self.seller_org.id, user_id=self.seller_user.id,
                decision=ApprovalDecision.APPROVE,
            ),
        )
        agreement = commit_agreement_in_transaction(
            self.session,
            CommitAgreementCommand(
                deal_id=self.deal.id, expected_version=1,
                expected_terms_hash=self.version_1.terms_hash,
                user_id=self.buyer_user.id, organization_id=self.buyer_org.id,
            ),
        )
        self.assertEqual(agreement.status, AgreementStatus.COMMITTED)

    # -- SEQUENTIAL routing: turn order enforced, reject is always a veto --

    def test_sequential_blocks_out_of_order_approval(self) -> None:
        a1 = self._add_member(self.buyer_org.id, capabilities=["AGREEMENT_APPROVAL"])
        a2 = self._add_member(self.buyer_org.id, capabilities=["AGREEMENT_APPROVAL"])
        SqlAlchemyApprovalRoutingPolicyRepository(self.session).save(
            ApprovalRoutingPolicy(
                organization_id=OrganizationId(self.buyer_org.id),
                mode=ApprovalRoutingMode.SEQUENTIAL,
                approver_user_ids=(UserId(a1.id), UserId(a2.id)),
            ),
            expected_version=None,
            updated_by_user_id=self.buyer_user.id,
        )
        self.session.commit()

        with self.assertRaises(OutOfSequenceApproval):
            self._approve(self.buyer_org.id, a2.id)

        outcome_1 = self._approve(self.buyer_org.id, a1.id)
        self.assertIsNone(outcome_1.finalized_approval)
        outcome_2 = self._approve(self.buyer_org.id, a2.id)
        self.assertIsNotNone(outcome_2.finalized_approval)

    def test_reject_is_a_veto_regardless_of_turn_order(self) -> None:
        a1 = self._add_member(self.buyer_org.id, capabilities=["AGREEMENT_APPROVAL"])
        a2 = self._add_member(self.buyer_org.id, capabilities=["AGREEMENT_APPROVAL"])
        SqlAlchemyApprovalRoutingPolicyRepository(self.session).save(
            ApprovalRoutingPolicy(
                organization_id=OrganizationId(self.buyer_org.id),
                mode=ApprovalRoutingMode.SEQUENTIAL,
                approver_user_ids=(UserId(a1.id), UserId(a2.id)),
            ),
            expected_version=None,
            updated_by_user_id=self.buyer_user.id,
        )
        self.session.commit()

        # a2 is not "next" yet, but may still veto immediately.
        outcome = self._reject(self.buyer_org.id, a2.id)
        self.assertEqual(outcome.evaluation.status, RoutingOutcomeStatus.COMPLETED)
        self.assertTrue(outcome.evaluation.rejected)
        self.assertEqual(outcome.finalized_approval.decision, ApprovalDecision.REJECT)

    # -- Eligibility / revocation / staleness --

    def test_non_eligible_approver_cannot_act(self) -> None:
        a1 = self._add_member(self.buyer_org.id, capabilities=["AGREEMENT_APPROVAL"])
        outsider = self._add_member(self.buyer_org.id, capabilities=["AGREEMENT_APPROVAL"])
        SqlAlchemyApprovalRoutingPolicyRepository(self.session).save(
            ApprovalRoutingPolicy(
                organization_id=OrganizationId(self.buyer_org.id),
                mode=ApprovalRoutingMode.PARALLEL,
                approver_user_ids=(UserId(a1.id),),
            ),
            expected_version=None,
            updated_by_user_id=self.buyer_user.id,
        )
        self.session.commit()
        with self.assertRaises(NotEligibleApprover):
            self._approve(self.buyer_org.id, outsider.id)

    def test_revoked_approver_blocks_completion(self) -> None:
        a1 = self._add_member(self.buyer_org.id, capabilities=["AGREEMENT_APPROVAL"])
        a2 = self._add_member(self.buyer_org.id, capabilities=["AGREEMENT_APPROVAL"])
        SqlAlchemyApprovalRoutingPolicyRepository(self.session).save(
            ApprovalRoutingPolicy(
                organization_id=OrganizationId(self.buyer_org.id),
                mode=ApprovalRoutingMode.PARALLEL,
                approver_user_ids=(UserId(a1.id), UserId(a2.id)),
            ),
            expected_version=None,
            updated_by_user_id=self.buyer_user.id,
        )
        self.session.commit()

        outcome_1 = self._approve(self.buyer_org.id, a1.id)
        self.assertEqual(outcome_1.evaluation.status, RoutingOutcomeStatus.PENDING)

        a2.status = "REVOKED"
        self.session.commit()

        # a1 revising their own decision still surfaces the blocked route.
        with self.assertRaises(DuplicateApproval):
            self._approve(self.buyer_org.id, a1.id)
        outcome_2 = self._reject(self.buyer_org.id, a1.id)
        self.assertEqual(outcome_2.evaluation.status, RoutingOutcomeStatus.ERROR)
        self.assertIsNone(outcome_2.finalized_approval)

    def test_stale_decision_after_policy_version_bump_must_be_redone(self) -> None:
        a1 = self._add_member(self.buyer_org.id, capabilities=["AGREEMENT_APPROVAL"])
        a2 = self._add_member(self.buyer_org.id, capabilities=["AGREEMENT_APPROVAL"])
        policies = SqlAlchemyApprovalRoutingPolicyRepository(self.session)
        policies.save(
            ApprovalRoutingPolicy(
                organization_id=OrganizationId(self.buyer_org.id),
                mode=ApprovalRoutingMode.PARALLEL,
                approver_user_ids=(UserId(a1.id), UserId(a2.id)),
            ),
            expected_version=None,
            updated_by_user_id=self.buyer_user.id,
        )
        self.session.commit()
        self._approve(self.buyer_org.id, a1.id)

        a3 = self._add_member(self.buyer_org.id, capabilities=["AGREEMENT_APPROVAL"])
        policies.save(
            ApprovalRoutingPolicy(
                organization_id=OrganizationId(self.buyer_org.id),
                mode=ApprovalRoutingMode.PARALLEL,
                approver_user_ids=(UserId(a1.id), UserId(a2.id), UserId(a3.id)),
            ),
            expected_version=1,
            updated_by_user_id=self.buyer_user.id,
        )
        self.session.commit()

        outcome = self._approve(self.buyer_org.id, a2.id)
        self.assertEqual(outcome.evaluation.status, RoutingOutcomeStatus.PENDING)
        a1_slot = next(s for s in outcome.evaluation.slots if s.user_id == a1.id)
        self.assertTrue(a1_slot.stale)
        self.assertIsNone(a1_slot.decision)

    # -- Policy CRUD validation --

    def test_save_rejects_ineligible_approver(self) -> None:
        non_member = User(email="stranger@example.com", display_name="Stranger")
        self.session.add(non_member)
        self.session.commit()
        with self.assertRaises(InvariantViolation):
            SqlAlchemyApprovalRoutingPolicyRepository(self.session).save(
                ApprovalRoutingPolicy(
                    organization_id=OrganizationId(self.buyer_org.id),
                    mode=ApprovalRoutingMode.PARALLEL,
                    approver_user_ids=(UserId(non_member.id),),
                ),
                expected_version=None,
                updated_by_user_id=self.buyer_user.id,
            )

    def test_save_detects_version_conflict(self) -> None:
        a1 = self._add_member(self.buyer_org.id, capabilities=["AGREEMENT_APPROVAL"])
        policies = SqlAlchemyApprovalRoutingPolicyRepository(self.session)
        policies.save(
            ApprovalRoutingPolicy(
                organization_id=OrganizationId(self.buyer_org.id),
                mode=ApprovalRoutingMode.PARALLEL,
                approver_user_ids=(UserId(a1.id),),
            ),
            expected_version=None,
            updated_by_user_id=self.buyer_user.id,
        )
        self.session.commit()
        with self.assertRaises(InvariantViolation):
            policies.save(
                ApprovalRoutingPolicy(
                    organization_id=OrganizationId(self.buyer_org.id),
                    mode=ApprovalRoutingMode.SEQUENTIAL,
                    approver_user_ids=(UserId(a1.id),),
                ),
                expected_version=99,
                updated_by_user_id=self.buyer_user.id,
            )

    def test_delete_reverts_to_default_bilateral_behavior(self) -> None:
        a1 = self._add_member(self.buyer_org.id, capabilities=["AGREEMENT_APPROVAL"])
        policies = SqlAlchemyApprovalRoutingPolicyRepository(self.session)
        policies.save(
            ApprovalRoutingPolicy(
                organization_id=OrganizationId(self.buyer_org.id),
                mode=ApprovalRoutingMode.PARALLEL,
                approver_user_ids=(UserId(a1.id),),
            ),
            expected_version=None,
            updated_by_user_id=self.buyer_user.id,
        )
        self.session.commit()
        self.assertTrue(policies.delete(self.buyer_org.id, expected_version=1))
        self.session.commit()

        record_approval_in_transaction(
            self.session,
            RecordApprovalCommand(
                deal_id=self.deal.id, version_number=1, terms_hash=self.version_1.terms_hash,
                organization_id=self.buyer_org.id, user_id=self.buyer_user.id,
                decision=ApprovalDecision.APPROVE,
            ),
        )


if __name__ == "__main__":
    unittest.main()
