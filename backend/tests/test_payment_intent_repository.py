"""Tests for persisting an authorized payment intent and its outbox row (S7-02)."""

import json
import unittest
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from test_domain_fixes import build_terms

from syncally.application.agreements import (
    CommitAgreementCommand,
    RecordApprovalCommand,
    record_approval,
)
from syncally.application.payments import (
    AuthorizePaymentIntentCommand,
    DuplicateActivePaymentIntent,
    IdempotencyKeyReused,
    PaymentIntentCommandMismatch,
    PaymentMilestoneNotFound,
    UnauthorizedPaymentAuthorization,
)
from syncally.domain.agreements.agreement import ApprovalDecision
from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import OrganizationId
from syncally.domain.shared.money import Money
from syncally.infrastructure.models import (
    AgreementVersion,
    Base,
    Deal,
    NegotiationSession,
    Organization,
    OrganizationMember,
    OutboxEvent,
    PaymentIntent,
    PaymentMilestone,
    Proposal,
    User,
)
from syncally.infrastructure.repositories.agreements import (
    SqlAlchemyAgreementRepository,
    commit_agreement_in_transaction,
)
from syncally.infrastructure.repositories.payments import (
    _is_idempotency_key_violation,
    _is_one_active_per_milestone_violation,
    authorize_payment_intent_in_transaction,
)


class PaymentIntentRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self._seed_committed_agreement_with_milestone()

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _seed_committed_agreement_with_milestone(self) -> None:
        """Commit one agreement through the real write path, leaving one payment milestone."""
        buyer_user = User(email="buyer@example.com", display_name="Buyer")
        seller_user = User(email="seller@example.com", display_name="Seller")
        buyer_org = Organization(legal_name="Buyer Co", country_code="US")
        seller_org = Organization(legal_name="Seller Co", country_code="CA")
        self.session.add_all([buyer_user, seller_user, buyer_org, seller_org])
        self.session.flush()
        self.session.add_all(
            [
                OrganizationMember(user_id=buyer_user.id, organization_id=buyer_org.id, status="ACTIVE"),
                OrganizationMember(user_id=seller_user.id, organization_id=seller_org.id, status="ACTIVE"),
            ]
        )
        self.deal = Deal(
            buyer_organization_id=buyer_org.id,
            seller_organization_id=seller_org.id,
            status="PENDING_APPROVALS",
            version=2,
        )
        self.session.add(self.deal)
        self.session.flush()

        terms = build_terms(buyer_id=OrganizationId(buyer_org.id), seller_id=OrganizationId(seller_org.id))
        session_row = NegotiationSession(deal_id=self.deal.id, max_rounds=5)
        self.session.add(session_row)
        self.session.flush()
        proposal = Proposal(
            deal_id=self.deal.id,
            negotiation_session_id=session_row.id,
            proposal_number=1,
            author_organization_id=buyer_org.id,
            terms_json=json.loads(terms.canonical_json()),
            terms_hash=terms.terms_hash,
        )
        self.session.add(proposal)
        self.session.flush()
        version = AgreementVersion(
            deal_id=self.deal.id,
            proposal_id=proposal.id,
            version_number=1,
            canonical_terms_json=json.loads(terms.canonical_json()),
            terms_hash=terms.terms_hash,
            status="PENDING_APPROVAL",
            created_by=buyer_user.id,
        )
        self.session.add(version)
        self.session.flush()
        self.deal.current_agreement_version_id = version.id
        self.session.commit()

        for org_id, user_id in ((buyer_org.id, buyer_user.id), (seller_org.id, seller_user.id)):
            record_approval(
                RecordApprovalCommand(
                    deal_id=self.deal.id,
                    version_number=version.version_number,
                    terms_hash=terms.terms_hash,
                    organization_id=org_id,
                    user_id=user_id,
                    decision=ApprovalDecision.APPROVE,
                ),
                SqlAlchemyAgreementRepository(self.session),
            )

        agreement = commit_agreement_in_transaction(
            self.session,
            CommitAgreementCommand(
                deal_id=self.deal.id,
                expected_version=version.version_number,
                expected_terms_hash=terms.terms_hash,
            ),
        )
        self.agreement_version_id = agreement.version_id
        self.buyer_org_id = buyer_org.id
        self.seller_org_id = seller_org.id
        self.buyer_user_id = buyer_user.id
        self.milestone_id = self.session.scalar(
            select(PaymentMilestone.id).where(PaymentMilestone.agreement_version_id == self.agreement_version_id)
        )
        self.assertIsNotNone(self.milestone_id)

    def _command(
        self,
        *,
        milestone_id=None,
        idempotency_key: str | None = None,
        authorized_by=None,
        amount: Money | None = None,
    ) -> AuthorizePaymentIntentCommand:
        return AuthorizePaymentIntentCommand(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=self.agreement_version_id,
            payment_milestone_id=milestone_id or self.milestone_id,
            seller_organization_id=self.seller_org_id,
            payer_organization_id=self.buyer_org_id,
            authorized_by=authorized_by or self.buyer_user_id,
            amount=amount or Money(Decimal("10"), "USD"),
            idempotency_key=idempotency_key or f"intent-{uuid4()}",
        )

    def _outbox_rows(self) -> list[OutboxEvent]:
        # Seeding the agreement already leaves its own AGREEMENT_COMMITTED
        # row - only this module's event type is this test's concern.
        return list(
            self.session.scalars(
                select(OutboxEvent).where(OutboxEvent.event_type == "PAYMENT_INTENT_AUTHORIZED")
            )
        )

    # -- Acceptance criteria --------------------------------------------

    def test_authorize_persists_intent_and_outbox_row_atomically(self) -> None:
        command = self._command(idempotency_key="intent-1")

        authorize_payment_intent_in_transaction(self.session, command)

        intent = self.session.scalar(select(PaymentIntent).where(PaymentIntent.id == command.id))
        self.assertIsNotNone(intent)
        self.assertEqual(intent.status, "AUTHORIZED")
        self.assertEqual(intent.payment_milestone_id, self.milestone_id)
        self.assertEqual(intent.deal_id, self.deal.id)
        self.assertEqual(intent.amount, Decimal("10"))
        self.assertEqual(intent.currency, "USD")
        self.assertEqual(intent.idempotency_key, "intent-1")

        outbox_rows = self._outbox_rows()
        self.assertEqual(len(outbox_rows), 1)
        self.assertEqual(outbox_rows[0].event_type, "PAYMENT_INTENT_AUTHORIZED")
        self.assertEqual(outbox_rows[0].status, "PENDING")
        self.assertEqual(
            outbox_rows[0].payload,
            {
                "payment_intent_id": str(command.id),
                "deal_id": str(self.deal.id),
                "agreement_version_id": str(self.agreement_version_id),
                "payment_milestone_id": str(self.milestone_id),
            },
        )

    def _add_second_milestone(self) -> "PaymentMilestone":
        second_milestone = PaymentMilestone(
            deal_id=self.deal.id,
            agreement_version_id=self.agreement_version_id,
            sequence_number=2,
            payer_organization_id=self.buyer_org_id,
            amount=Decimal("10"),
            currency="USD",
            trigger_type="MANUAL",
            due_condition="On delivery",
            status="PENDING",
        )
        self.session.add(second_milestone)
        self.session.flush()
        return second_milestone

    def test_reusing_an_idempotency_key_for_a_different_authorization_is_rejected(self) -> None:
        # Two intents for *different* milestones that collide only on
        # idempotency_key is a client bug, not a retry - it must not be
        # silently merged into either row, nor reported as a milestone conflict.
        second_milestone = self._add_second_milestone()

        first = self._command(idempotency_key="shared-key")
        authorize_payment_intent_in_transaction(self.session, first)

        second = self._command(milestone_id=second_milestone.id, idempotency_key="shared-key")
        with self.assertRaises(IdempotencyKeyReused):
            authorize_payment_intent_in_transaction(self.session, second)

        self.assertEqual(len(list(self.session.scalars(select(PaymentIntent)))), 1)

    def test_unrelated_integrity_violation_is_not_classified_as_either_known_conflict(self) -> None:
        # A check constraint or FK violation must not be mistaken for the
        # milestone-conflict or idempotency-key-reuse cases above.
        error = IntegrityError("INSERT", {}, Exception("CHECK constraint failed: ck_payment_intent_amount_positive"))
        self.assertFalse(_is_one_active_per_milestone_violation(error))
        self.assertFalse(_is_idempotency_key_violation(error))

    def test_retrying_with_the_same_idempotency_key_replays_the_original_result(self) -> None:
        # Commit succeeds but the caller loses the acknowledgement and retries
        # with a fresh attempt id but the same idempotency key - it must get
        # back the original intent, not a duplicate or a false conflict.
        first = self._command(idempotency_key="shared-key")
        first_outcome = authorize_payment_intent_in_transaction(self.session, first)
        self.assertFalse(first_outcome.already_existed)
        self.assertEqual(first_outcome.intent_id, first.id)

        retry = self._command(idempotency_key="shared-key")
        retry_outcome = authorize_payment_intent_in_transaction(self.session, retry)

        self.assertTrue(retry_outcome.already_existed)
        self.assertEqual(retry_outcome.intent_id, first.id)
        self.assertEqual(len(list(self.session.scalars(select(PaymentIntent)))), 1)
        # No second outbox dispatch for a replay that reported nothing new.
        self.assertEqual(len(self._outbox_rows()), 1)

    def test_unknown_milestone_is_rejected(self) -> None:
        command = self._command(milestone_id=uuid4())
        with self.assertRaises(PaymentMilestoneNotFound):
            authorize_payment_intent_in_transaction(self.session, command)

    def test_amount_mismatched_with_the_milestone_is_rejected(self) -> None:
        command = self._command(amount=Money(Decimal("999"), "USD"))
        with self.assertRaises(PaymentIntentCommandMismatch):
            authorize_payment_intent_in_transaction(self.session, command)

    def test_inactive_authorizer_is_rejected(self) -> None:
        inactive_user = User(email="inactive@example.com", display_name="Inactive", status="SUSPENDED")
        self.session.add(inactive_user)
        self.session.flush()
        self.session.add(
            OrganizationMember(user_id=inactive_user.id, organization_id=self.buyer_org_id, status="ACTIVE")
        )
        self.session.commit()

        command = self._command(authorized_by=inactive_user.id)
        with self.assertRaises(UnauthorizedPaymentAuthorization):
            authorize_payment_intent_in_transaction(self.session, command)

    def test_blank_idempotency_key_is_rejected(self) -> None:
        command = self._command(idempotency_key=" ")
        with self.assertRaises(InvariantViolation):
            authorize_payment_intent_in_transaction(self.session, command)

    def test_second_active_intent_for_same_milestone_is_rejected(self) -> None:
        first = self._command(idempotency_key="intent-1")
        authorize_payment_intent_in_transaction(self.session, first)

        second = self._command(idempotency_key="intent-2")
        with self.assertRaises(DuplicateActivePaymentIntent):
            authorize_payment_intent_in_transaction(self.session, second)

        # The rejected attempt leaves no trace: one intent, one outbox row.
        intents = list(self.session.scalars(select(PaymentIntent)))
        self.assertEqual(len(intents), 1)
        self.assertEqual(intents[0].id, first.id)
        self.assertEqual(len(self._outbox_rows()), 1)

    def test_terminal_intent_does_not_block_a_new_one_for_the_same_milestone(self) -> None:
        # A milestone's first intent failed outright; a fresh authorization
        # for the same milestone must still be allowed.
        failed = PaymentIntent(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=self.agreement_version_id,
            payment_milestone_id=self.milestone_id,
            seller_organization_id=self.seller_org_id,
            payer_organization_id=self.buyer_org_id,
            authorized_by=self.buyer_user_id,
            amount=Decimal("10"),
            currency="USD",
            status="FAILED",
            idempotency_key="intent-failed",
        )
        self.session.add(failed)
        self.session.commit()

        retry = self._command(idempotency_key="intent-retry")
        authorize_payment_intent_in_transaction(self.session, retry)

        intents = list(self.session.scalars(select(PaymentIntent)))
        self.assertEqual(len(intents), 2)
        self.assertEqual(len(self._outbox_rows()), 1)

    def test_crash_before_commit_rolls_back_intent_and_outbox_together(self) -> None:
        command = self._command(idempotency_key="intent-1")
        with patch.object(self.session, "commit", side_effect=RuntimeError("process stopped")):
            with self.assertRaisesRegex(RuntimeError, "process stopped"):
                authorize_payment_intent_in_transaction(self.session, command)

        self.assertEqual(list(self.session.scalars(select(PaymentIntent))), [])
        self.assertEqual(self._outbox_rows(), [])

    def test_recovery_after_crash_allows_exactly_one_successful_retry(self) -> None:
        command = self._command(idempotency_key="intent-1")
        with patch.object(self.session, "commit", side_effect=RuntimeError("process stopped")):
            with self.assertRaisesRegex(RuntimeError, "process stopped"):
                authorize_payment_intent_in_transaction(self.session, command)

        # The worker resumes and retries the same operation after the crash.
        authorize_payment_intent_in_transaction(self.session, command)

        intents = list(self.session.scalars(select(PaymentIntent)))
        self.assertEqual(len(intents), 1)
        self.assertEqual(intents[0].id, command.id)
        self.assertEqual(len(self._outbox_rows()), 1)

    def test_outbox_payload_carries_no_secrets_or_unnecessary_fields(self) -> None:
        command = self._command(idempotency_key="intent-1")

        authorize_payment_intent_in_transaction(self.session, command)

        payload = self._outbox_rows()[0].payload
        self.assertEqual(
            set(payload.keys()),
            {"payment_intent_id", "deal_id", "agreement_version_id", "payment_milestone_id"},
        )


if __name__ == "__main__":
    unittest.main()
