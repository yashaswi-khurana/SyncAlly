import asyncio
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier, Event
from unittest.mock import patch
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from test_domain_fixes import build_terms

from syncally.api.auth import get_current_actor
from syncally.api.main import app
from syncally.application.agreements import (
    AgreementVersionConflict,
    CommitAgreementCommand,
    CreateAgreementDraftCommand,
    CreateReviewedAgreementDraftCommand,
    RecordApprovalCommand,
    StaleAgreementVersion,
    UnauthorizedApproval,
)
from syncally.application.identity import ActorContext
from syncally.application.negotiation import (
    CandidateAcknowledgement,
    EvidenceReference,
    NegotiationCommand,
    NegotiationConflict,
    NegotiationNotFound,
    NegotiationOrganizationRequired,
    ProposalBase,
)
from syncally.domain.agreements.agreement import ApprovalDecision
from syncally.domain.shared.errors import InvalidTransition
from syncally.domain.shared.identifiers import OrganizationId
from syncally.infrastructure.database import create_database_engine, get_db
from syncally.infrastructure.models import (
    AgreementVersion,
    Approval,
    AuditEvent,
    Base,
    Constraint,
    Conversation,
    CounterpartyOnboarding,
    Deal,
    Message,
    NegotiationAction,
    NegotiationSession,
    Obligation,
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
    create_agreement_draft_in_transaction,
    create_reviewed_agreement_draft_in_transaction,
    record_approval_in_transaction,
)
from syncally.infrastructure.repositories.negotiation import (
    SqlAlchemyNegotiationRepository,
    negotiate_in_transaction,
)


class NegotiationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = getattr(self, "provided_engine", None) or create_database_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.buyer = Organization(legal_name="Buyer", country_code="US")
        self.seller = Organization(legal_name="Seller", country_code="CA")
        self.buyer_user = User(email="buyer@f5.test", display_name="Buyer")
        self.seller_user = User(email="seller@f5.test", display_name="Seller")
        self.db.add_all([self.buyer, self.seller, self.buyer_user, self.seller_user])
        self.db.flush()
        self.db.add_all([
            OrganizationMember(organization_id=self.buyer.id, user_id=self.buyer_user.id, status="ACTIVE"),
            OrganizationMember(organization_id=self.seller.id, user_id=self.seller_user.id, status="ACTIVE"),
        ])
        self.deal = Deal(buyer_organization_id=self.buyer.id, seller_organization_id=self.seller.id)
        self.db.add(self.deal)
        self.db.commit()
        self.terms = build_terms(buyer_id=OrganizationId(self.buyer.id), seller_id=OrganizationId(self.seller.id))

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_schema_scope_and_positive_count_constraints(self) -> None:
        self.assertIn("negotiation_actions", inspect(self.engine).get_table_names())
        session = NegotiationSession(deal_id=self.deal.id, max_rounds=5, round_count=-1)
        self.db.add(session)
        with self.assertRaises(IntegrityError):
            self.db.flush()
        self.db.rollback()
        session = NegotiationSession(deal_id=self.deal.id, max_rounds=5)
        self.db.add(session)
        self.db.flush()
        other = Deal(buyer_organization_id=self.buyer.id, seller_organization_id=self.seller.id)
        self.db.add(other)
        self.db.flush()
        self.db.add(Proposal(deal_id=other.id, negotiation_session_id=session.id, proposal_number=1,
                             author_organization_id=self.buyer.id, terms_json=self.terms.to_storage_dict(), terms_hash=self.terms.terms_hash))
        with self.assertRaises(IntegrityError):
            self.db.flush()
        self.db.rollback()

    def test_empty_history_has_no_fabricated_events(self) -> None:
        self.assertEqual(list(self.db.scalars(select(NegotiationAction))), [])

    def submit(self) -> dict:
        self.command = NegotiationCommand(self.deal.id, self.buyer_user.id, self.buyer.id,
                                          uuid4(), "submit", self.deal.version, None, self.terms)
        return negotiate_in_transaction(self.db, self.command)

    def test_submit_replay_and_counter_accept_creates_unapproved_candidate(self) -> None:
        result = self.submit()
        self.assertEqual(negotiate_in_transaction(self.db, self.command), result)
        first = self.db.scalar(select(Proposal))
        counter = replace(self.command, user_id=self.seller_user.id, organization_id=self.seller.id,
                          command_id=uuid4(), action="counter", expected_deal_revision=result["deal_revision"],
                          base=ProposalBase(first.id, first.terms_hash, first.status))
        result = negotiate_in_transaction(self.db, counter)
        self.assertEqual(first.status, "SUPERSEDED")
        latest = self.db.scalar(select(Proposal).order_by(Proposal.proposal_number.desc()))
        accept = replace(self.command, command_id=uuid4(), action="accept", terms=None,
                         expected_deal_revision=result["deal_revision"], base=ProposalBase(latest.id, latest.terms_hash, latest.status))
        result = negotiate_in_transaction(self.db, accept)
        self.assertIsNotNone(result["candidate_id"])
        self.assertEqual(self.db.scalar(select(AgreementVersion)).status, "PENDING_APPROVAL")
        self.assertEqual(latest.status, "ACCEPTED_AS_CANDIDATE")
        self.assertEqual(self.deal.status, "PENDING_APPROVALS")
        self.assertEqual(len(list(self.db.scalars(select(NegotiationAction)))), 3)

    def test_legacy_draft_cannot_bypass_human_acceptance(self) -> None:
        result = self.submit()
        from uuid import UUID
        with self.assertRaises(AgreementVersionConflict):
            create_agreement_draft_in_transaction(self.db, CreateAgreementDraftCommand(
                self.deal.id, UUID(result["proposal_id"]), self.buyer_user.id))
        self.assertEqual(list(self.db.scalars(select(AgreementVersion))), [])

    def current_command(self, action: str, *, seller: bool = True, **changes) -> NegotiationCommand:
        latest = self.db.scalar(select(Proposal).order_by(Proposal.proposal_number.desc()))
        return replace(self.command, command_id=uuid4(), action=action,
                       user_id=self.seller_user.id if seller else self.buyer_user.id,
                       organization_id=self.seller.id if seller else self.buyer.id,
                       expected_deal_revision=self.deal.version, terms=self.terms if action in ("submit", "counter") else None,
                       base=ProposalBase(latest.id, latest.terms_hash, latest.status), **changes)

    def accept(self) -> AgreementVersion:
        negotiate_in_transaction(self.db, self.current_command("accept"))
        return self.db.scalar(select(AgreementVersion).order_by(AgreementVersion.version_number.desc()))

    def ack(self, version: AgreementVersion) -> CandidateAcknowledgement:
        return CandidateAcknowledgement(version.id, version.version_number, version.terms_hash, version.proposal_id)

    def approve(self, version: AgreementVersion, *, seller: bool = False) -> None:
        record_approval_in_transaction(self.db, RecordApprovalCommand(self.deal.id, version.version_number, version.terms_hash,
            self.seller.id if seller else self.buyer.id, self.seller_user.id if seller else self.buyer_user.id, ApprovalDecision.APPROVE))

    def assert_no_execution(self) -> None:
        for model in (Obligation, PaymentMilestone, PaymentIntent, OutboxEvent, AuditEvent):
            self.assertEqual(list(self.db.scalars(select(model))), [])

    def test_equal_hash_replacement_requires_exact_ack_and_never_carries_approval(self) -> None:
        self.submit()
        old = self.accept()
        self.approve(old)
        command = self.current_command("submit", seller=False)
        for ack in (None, replace(self.ack(old), terms_hash="0" * 64)):
            with self.assertRaises(NegotiationConflict):
                negotiate_in_transaction(self.db, replace(command, supersede_current_candidate=ack))
            self.assertEqual(old.status, "PENDING_APPROVAL")
            self.assertEqual(len(list(self.db.scalars(select(Proposal)))), 1)
        negotiate_in_transaction(self.db, replace(command, supersede_current_candidate=self.ack(old)))
        self.assertEqual(old.status, "SUPERSEDED")
        self.assertEqual(self.deal.status, "NEGOTIATING")
        self.assertIsNone(self.deal.current_agreement_version_id)
        new = self.accept()
        self.assertNotEqual(new.id, old.id)
        self.assertEqual(new.terms_hash, old.terms_hash)
        self.assertEqual(new.version_number, 2)
        approvals = list(self.db.scalars(select(Approval)))
        self.assertEqual(len(approvals), 1)
        self.assertEqual(approvals[0].agreement_version_id, old.id)
        with self.assertRaises(StaleAgreementVersion):
            self.approve(old, seller=True)
        with self.assertRaises(InvalidTransition):
            commit_agreement_in_transaction(self.db, CommitAgreementCommand(self.deal.id, 2, new.terms_hash, self.seller_user.id, self.seller.id))
        history = SqlAlchemyNegotiationRepository(self.db).read(self.deal.id, self.buyer_user.id, self.buyer.id)
        self.assertIn(str(old.id), [event["invalidated_candidate_id"] for event in history["history"]])

    def test_replacement_failure_rolls_back_every_record(self) -> None:
        self.submit()
        old = self.accept()
        revision = self.deal.version
        with patch.object(SqlAlchemyNegotiationRepository, "_record", side_effect=RuntimeError("injected history failure")):
            with self.assertRaises(RuntimeError):
                negotiate_in_transaction(self.db, self.current_command("submit", seller=False, supersede_current_candidate=self.ack(old)))
        self.assertEqual(self.deal.version, revision)
        self.assertEqual(old.status, "PENDING_APPROVAL")
        self.assertEqual(self.deal.current_agreement_version_id, old.id)
        self.assertEqual(len(list(self.db.scalars(select(Proposal)))), 1)
        self.assertEqual(len(list(self.db.scalars(select(NegotiationAction)))), 2)

    def test_five_round_cap_escalation_is_durable_without_partial_supersession(self) -> None:
        self.submit()
        for number in range(2, 6):
            negotiate_in_transaction(self.db, self.current_command("counter", seller=number % 2 == 0))
        latest = self.db.scalar(select(Proposal).order_by(Proposal.proposal_number.desc()))
        command = self.current_command("counter", seller=True)
        result = negotiate_in_transaction(self.db, command)
        self.assertEqual(result["outcome"], "ESCALATION_REQUIRED")
        self.assertEqual(latest.status, "SUBMITTED")
        self.assertEqual(len(list(self.db.scalars(select(Proposal)))), 5)
        session = self.db.scalar(select(NegotiationSession))
        self.assertTrue(session.escalated)
        self.assertEqual(session.round_count, 5)
        with Session(self.engine) as restarted:
            self.assertEqual(negotiate_in_transaction(restarted, command), result)
        with self.assertRaises(NegotiationConflict):
            negotiate_in_transaction(self.db, self.current_command("reject", seller=True))
        self.assert_no_execution()

    def test_overlimit_pending_candidate_is_not_invalidated(self) -> None:
        self.submit()
        old = self.accept()
        session = self.db.scalar(select(NegotiationSession))
        session.max_rounds = 1
        self.db.commit()
        result = negotiate_in_transaction(self.db, self.current_command("submit", seller=False, supersede_current_candidate=self.ack(old)))
        self.assertEqual(result["outcome"], "ESCALATION_REQUIRED")
        self.assertEqual(old.status, "PENDING_APPROVAL")
        self.assertEqual(self.deal.current_agreement_version_id, old.id)
        self.assertEqual(self.db.scalar(select(Proposal)).status, "ACCEPTED_AS_CANDIDATE")

    def test_expiry_requires_explicit_action_then_allows_terminal_successor(self) -> None:
        self.submit()
        negotiate_in_transaction(self.db, self.current_command("supersede", seller=False))
        now = datetime.now(UTC)
        negotiate_in_transaction(self.db, self.current_command("submit", expires_at=now + timedelta(seconds=1)), now=now)
        late = now + timedelta(seconds=1)
        with self.assertRaises(InvalidTransition):
            negotiate_in_transaction(self.db, self.current_command("accept", seller=False), now=late)
        self.assertEqual(self.db.scalar(select(Proposal).order_by(Proposal.proposal_number.desc())).status, "SUBMITTED")
        negotiate_in_transaction(self.db, self.current_command("expire", seller=False), now=late)
        negotiate_in_transaction(self.db, self.current_command("submit", seller=False), now=late)
        self.assertEqual(len(list(self.db.scalars(select(Proposal)))), 3)
        self.assert_no_execution()

    def test_fresh_membership_and_organization_state_gate_replay(self) -> None:
        self.submit()
        self.buyer.status = "INACTIVE"
        self.db.commit()
        with self.assertRaises(NegotiationNotFound):
            negotiate_in_transaction(self.db, self.command)
        self.buyer.status = "ACTIVE"
        member = self.db.scalar(select(OrganizationMember).where(OrganizationMember.user_id == self.buyer_user.id))
        member.status = "INACTIVE"
        self.db.commit()
        with self.assertRaises(NegotiationNotFound):
            negotiate_in_transaction(self.db, self.command)
        self.assertEqual(len(list(self.db.scalars(select(NegotiationAction)))), 1)

    def test_dual_membership_requires_explicit_selection_at_database_boundary(self) -> None:
        self.submit()
        self.db.add(OrganizationMember(user_id=self.buyer_user.id, organization_id=self.seller.id, status="ACTIVE"))
        self.db.commit()
        with self.assertRaises(NegotiationOrganizationRequired):
            negotiate_in_transaction(self.db, replace(self.command, organization_id=None))
        self.assertEqual(negotiate_in_transaction(self.db, self.command)["outcome"], "APPLIED")

    def test_f4_pending_rejects_all_actions_even_replay(self) -> None:
        self.submit()
        self.db.add(CounterpartyOnboarding(invitation_jti=uuid4(), deal_id=self.deal.id,
            buyer_organization_id=self.buyer.id, shell_organization_id=self.seller.id,
            inviter_user_id=self.buyer_user.id, recipient_email="seller@f5.test", expires_at=datetime.now(UTC) + timedelta(days=1)))
        self.db.commit()
        for action in ("submit", "counter", "accept", "reject", "supersede", "expire"):
            with self.subTest(action=action), self.assertRaises(NegotiationConflict):
                negotiate_in_transaction(self.db, self.current_command(action))
        with self.assertRaises(NegotiationConflict):
            negotiate_in_transaction(self.db, self.command)
        self.assertEqual(len(list(self.db.scalars(select(NegotiationAction)))), 1)
        self.assert_no_execution()

    def test_stale_revision_base_and_replay_collision_have_no_mutation(self) -> None:
        self.submit()
        command = self.current_command("counter")
        for bad in (replace(command, expected_deal_revision=0), replace(command, base=replace(command.base, id=uuid4())),
                    replace(command, base=replace(command.base, terms_hash="0" * 64)), replace(command, base=None),
                    replace(self.command, action="reject", terms=None)):
            with self.subTest(command=bad), self.assertRaises(NegotiationConflict):
                negotiate_in_transaction(self.db, bad)
        self.assertEqual(len(list(self.db.scalars(select(Proposal)))), 1)
        self.assertEqual(self.db.scalar(select(Proposal)).status, "SUBMITTED")

    def test_committed_winner_cannot_be_replaced_and_revoked_commit_is_denied(self) -> None:
        self.submit()
        old = self.accept()
        self.approve(old)
        self.approve(old, seller=True)
        command = self.current_command("submit", seller=False, supersede_current_candidate=self.ack(old))
        commit = CommitAgreementCommand(self.deal.id, old.version_number, old.terms_hash, self.seller_user.id, self.seller.id)
        self.seller_user.status = "INACTIVE"
        self.db.commit()
        with self.assertRaises(UnauthorizedApproval):
            commit_agreement_in_transaction(self.db, commit)
        self.seller_user.status = "ACTIVE"
        self.db.commit()
        commit_agreement_in_transaction(self.db, commit)
        with self.assertRaises(NegotiationConflict):
            negotiate_in_transaction(self.db, command)
        self.assertEqual(old.status, "COMMITTED")

    def test_legacy_reviewed_replay_remains_but_cannot_replace_human_rounds(self) -> None:
        command = CreateReviewedAgreementDraftCommand(self.deal.id, self.buyer.id, self.buyer_user.id, self.terms)
        first = create_reviewed_agreement_draft_in_transaction(self.db, command)
        replay = create_reviewed_agreement_draft_in_transaction(self.db, command)
        self.assertEqual(first.version_id, replay.version_id)
        row = self.db.scalar(select(Proposal))
        old = self.db.scalar(select(AgreementVersion))
        human = NegotiationCommand(self.deal.id, self.buyer_user.id, self.buyer.id, uuid4(), "submit", self.deal.version,
                                   ProposalBase(row.id, row.terms_hash, row.status), self.terms,
                                   supersede_current_candidate=self.ack(old))
        negotiate_in_transaction(self.db, human)
        with self.assertRaises(AgreementVersionConflict):
            create_reviewed_agreement_draft_in_transaction(self.db, command)

    def test_ambiguous_legacy_chain_is_preserved_and_fails_closed(self) -> None:
        session = NegotiationSession(deal_id=self.deal.id, max_rounds=3, round_count=0)
        self.db.add(session)
        self.db.flush()
        row = Proposal(deal_id=self.deal.id, negotiation_session_id=session.id, proposal_number=1,
                       author_organization_id=self.buyer.id, terms_json=self.terms.to_storage_dict(), terms_hash=self.terms.terms_hash, status="DRAFT")
        self.db.add(row)
        self.db.commit()
        with self.assertRaises(NegotiationConflict):
            self.submit()
        self.assertEqual(row.status, "DRAFT")
        self.assertEqual(session.max_rounds, 3)
        self.assertEqual(session.round_count, 0)
        self.assertTrue(SqlAlchemyNegotiationRepository(self.db).read(self.deal.id, self.buyer_user.id, self.buyer.id)["history_ambiguous"])

    def test_evidence_is_immutable_private_redacted_and_source_access_rechecked(self) -> None:
        conversation = Conversation(deal_id=self.deal.id, participant_organization_id=self.buyer.id)
        self.db.add(conversation)
        self.db.flush()
        source = Message(conversation_id=conversation.id, author_user_id=self.buyer_user.id,
                         body="Private source", visibility="PRIVATE", source_type="USER")
        self.db.add(source)
        self.db.flush()
        fact = Constraint(deal_id=self.deal.id, owner_organization_id=self.buyer.id, field="quantity", typed_value="1",
                          kind="INFORMATIONAL", status="CONFIRMED", visibility="PRIVATE", version=1,
                          source_message_id=source.id, source_span="Private source", confirmed_by=self.buyer_user.id, confirmed_at=datetime.now(UTC))
        self.db.add(fact)
        self.db.commit()
        self.submit()
        negotiate_in_transaction(self.db, self.current_command("supersede", seller=False))
        negotiate_in_transaction(self.db, self.current_command("submit", seller=False, evidence=(EvidenceReference(fact.id, 1),)))
        repo = SqlAlchemyNegotiationRepository(self.db)
        owner = repo.read(self.deal.id, self.buyer_user.id, self.buyer.id)
        other = repo.read(self.deal.id, self.seller_user.id, self.seller.id)
        self.assertEqual(len(owner["latest"]["evidence_refs"]), 1)
        self.assertEqual(other["latest"]["evidence_refs"], [])
        self.assertNotIn(str(fact.id), str(other))
        self.assertNotIn("Private source", str(other))
        snapshot = self.db.scalar(select(Proposal).order_by(Proposal.proposal_number.desc())).evidence_refs
        source.visibility = "SHAREABLE"
        fact.visibility = "SHAREABLE"
        fact.version = 2
        self.db.commit()
        self.assertEqual(repo.read(self.deal.id, self.seller_user.id, self.seller.id)["latest"]["evidence_refs"], [])
        self.assertEqual(self.db.scalar(select(Proposal).order_by(Proposal.proposal_number.desc())).evidence_refs, snapshot)

    def test_agreement_evidence_is_frozen_exact_private_and_source_changes_disable_trace(self) -> None:
        from copy import deepcopy

        conversation = Conversation(deal_id=self.deal.id, participant_organization_id=self.buyer.id)
        self.db.add(conversation)
        self.db.flush()
        source = Message(conversation_id=conversation.id, author_user_id=self.buyer_user.id,
                         body="Private original quote", visibility="PRIVATE", source_type="USER",
                         source_reference="secret-provider-id")
        self.db.add(source)
        self.db.flush()
        fact = Constraint(deal_id=self.deal.id, owner_organization_id=self.buyer.id,
                          field="quantity", typed_value="1", kind="INFORMATIONAL", status="CONFIRMED",
                          visibility="PRIVATE", version=1, source_message_id=source.id,
                          source_span=source.body, confirmed_by=self.buyer_user.id, confirmed_at=datetime.now(UTC))
        self.db.add(fact)
        self.db.commit()
        self.command = NegotiationCommand(self.deal.id, self.buyer_user.id, self.buyer.id,
            uuid4(), "submit", self.deal.version, None, self.terms, evidence=(EvidenceReference(fact.id, 1),))
        negotiate_in_transaction(self.db, self.command)
        negotiate_in_transaction(self.db, replace(self.current_command("accept", seller=True), evidence=()))
        version = self.db.scalar(select(AgreementVersion))
        saved = deepcopy(version.canonical_terms_json)
        repo = SqlAlchemyAgreementRepository(self.db)
        owner = repo.read_versions(self.deal.id, self.buyer_user.id, self.buyer.id)["versions"][0]
        self.assertEqual(owner["terms_hash"], self.terms.terms_hash)
        self.assertEqual(owner["evidence"][0]["source_span"], source.body)
        self.assertTrue(owner["evidence"][0]["trace_enabled"])
        self.assertEqual(owner["evidence"][0]["agreement_version_id"], str(version.id))
        self.assertEqual(owner["grounding"], "UNMAPPED")
        other = repo.read_versions(self.deal.id, self.seller_user.id, self.seller.id)
        for private in (str(fact.id), str(source.id), source.body, "secret-provider-id"):
            self.assertNotIn(private, str(other))
        source.visibility = "SHAREABLE"
        fact.visibility = "SHAREABLE"
        self.db.commit()
        other = repo.read_versions(self.deal.id, self.seller_user.id, self.seller.id)
        self.assertNotIn(str(fact.id), str(other))
        self.assertNotIn(source.body, str(other))
        source.body = "New source with Private original quote still present"
        self.db.commit()
        changed = repo.read_versions(self.deal.id, self.buyer_user.id, self.buyer.id)["versions"][0]["evidence"][0]
        self.assertFalse(changed["trace_enabled"])
        self.assertNotIn("source_span", changed)
        fact.version = 2
        fact.typed_value = "999-private-new-value"
        self.db.commit()
        changed = repo.read_versions(self.deal.id, self.buyer_user.id, self.buyer.id)["versions"][0]["evidence"][0]
        self.assertEqual(changed["version"], 1)
        self.assertNotIn("999-private-new-value", str(changed))
        self.assertEqual(version.canonical_terms_json, saved)
        for model in (AuditEvent, OutboxEvent, Obligation, PaymentMilestone):
            self.assertEqual(list(self.db.scalars(select(model))), [])

    def test_agreement_shareable_source_revocation_redacts_even_changed_fact_ids(self) -> None:
        conversation = Conversation(deal_id=self.deal.id, participant_organization_id=self.buyer.id)
        self.db.add(conversation)
        self.db.flush()
        source = Message(conversation_id=conversation.id, author_user_id=self.buyer_user.id,
                         body="Shareable quote", visibility="SHAREABLE", source_type="USER")
        self.db.add(source)
        self.db.flush()
        fact = Constraint(deal_id=self.deal.id, owner_organization_id=self.buyer.id, field="quantity", typed_value="1",
                          kind="INFORMATIONAL", status="CONFIRMED", visibility="SHAREABLE", version=1,
                          source_message_id=source.id, source_span=source.body,
                          confirmed_by=self.buyer_user.id, confirmed_at=datetime.now(UTC))
        self.db.add(fact)
        self.db.commit()
        self.command = NegotiationCommand(self.deal.id, self.buyer_user.id, self.buyer.id,
            uuid4(), "submit", self.deal.version, None, self.terms, evidence=(EvidenceReference(fact.id, 1),))
        negotiate_in_transaction(self.db, self.command)
        negotiate_in_transaction(self.db, replace(self.current_command("accept", seller=True), evidence=()))
        repo = SqlAlchemyAgreementRepository(self.db)
        visible = repo.read_versions(self.deal.id, self.seller_user.id, self.seller.id)["versions"][0]["evidence"][0]
        self.assertTrue(visible["trace_enabled"])
        source.visibility = "PRIVATE"
        fact.version = 2
        self.db.commit()
        redacted = repo.read_versions(self.deal.id, self.seller_user.id, self.seller.id)
        self.assertNotIn(str(fact.id), str(redacted))
        self.assertNotIn(str(source.id), str(redacted))
        self.assertNotIn("Shareable quote", str(redacted))


class NegotiationRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = NegotiationTests()
        self.fixture.provided_engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        with self.fixture.provided_engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        self.fixture.setUp()
        app.dependency_overrides[get_db] = lambda: self.fixture.db
        self.actor = self.fixture.buyer_user
        app.dependency_overrides[get_current_actor] = lambda: ActorContext(
            self.actor.id, frozenset({self.fixture.buyer.id, self.fixture.seller.id})
        )

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.fixture.tearDown()

    def request(self, method: str, action: str = "", payload: dict | None = None) -> httpx.Response:
        async def send() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                return await client.request(
                    method, f"/deals/{self.fixture.deal.id}/negotiation{action}", json=payload
                )
        return asyncio.run(send())

    def submission(self) -> dict:
        return {
            "command_id": str(uuid4()), "expected_deal_revision": 0, "base": None,
            "organization_id": str(self.fixture.buyer.id),
            "terms": {"schema_version": 1, "description": "Desk", "quantity": "1",
                      "unit": "each", "unit_price": "10", "currency": "USD",
                      "delivery_destination": "Toronto", "delivery_date": "2030-01-01",
                      "payment_trigger": "seller_invoice"},
        }

    def test_two_party_http_journey_keeps_candidate_unapproved(self) -> None:
        payload = self.submission()
        submitted = self.request("POST", "/submit", payload)
        self.assertEqual(submitted.status_code, 200, submitted.text)
        self.assertEqual(self.request("POST", "/submit", payload).json(), submitted.json())
        self.actor = self.fixture.seller_user
        history = self.request("GET")
        self.assertEqual(history.status_code, 200, history.text)
        view = history.json()
        self.assertEqual(view["organization_id"], str(self.fixture.seller.id))
        self.assertEqual(set(view["eligible_actions"]), {"counter", "accept", "reject"})
        latest = view["latest"]
        accepted = self.request("POST", "/accept", {
            "command_id": str(uuid4()), "expected_deal_revision": view["deal_revision"],
            "organization_id": str(self.fixture.seller.id),
            "base": {key: latest[key] for key in ("id", "terms_hash", "status")},
        })
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertIsNotNone(accepted.json()["candidate_id"])
        candidate_view = self.request("GET").json()
        self.assertEqual(candidate_view["current_candidate"]["status"], "PENDING_APPROVAL")
        self.assertEqual(candidate_view["latest"]["status"], "ACCEPTED_AS_CANDIDATE")
        self.assertEqual(list(self.fixture.db.scalars(select(Approval))), [])
        self.fixture.assert_no_execution()

    def test_database_membership_overrides_forged_actor_scope_and_replay(self) -> None:
        payload = self.submission()
        self.assertEqual(self.request("POST", "/submit", payload).status_code, 200)
        denied = dict(payload, organization_id=str(self.fixture.seller.id), command_id=str(uuid4()))
        self.assertEqual(self.request("POST", "/submit", denied).status_code, 404)
        membership = self.fixture.db.scalar(select(OrganizationMember).where(
            OrganizationMember.user_id == self.fixture.buyer_user.id
        ))
        membership.status = "INACTIVE"
        self.fixture.db.commit()
        self.assertEqual(self.request("GET").status_code, 404)
        self.assertEqual(self.request("POST", "/submit", payload).status_code, 404)
        self.assertEqual(len(list(self.fixture.db.scalars(select(NegotiationAction)))), 1)

    def test_invalid_transport_is_redacted_and_has_no_side_effects(self) -> None:
        payload = self.submission()
        payload["terms"]["payment_trigger"] = "PRIVATE-UNSUPPORTED-TIMING"
        response = self.request("POST", "/submit", payload)
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("PRIVATE-UNSUPPORTED-TIMING", response.text)
        self.assertEqual(list(self.fixture.db.scalars(select(Proposal))), [])
        self.assertEqual(list(self.fixture.db.scalars(select(NegotiationAction))), [])
        self.fixture.assert_no_execution()

    def test_retained_legacy_proposal_id_cannot_replace_human_terms_over_http(self) -> None:
        fixture = self.fixture
        create_reviewed_agreement_draft_in_transaction(
            fixture.db,
            CreateReviewedAgreementDraftCommand(
                fixture.deal.id, fixture.buyer.id, fixture.buyer_user.id, fixture.terms
            ),
        )
        legacy = fixture.db.scalar(select(Proposal))
        old = fixture.db.scalar(select(AgreementVersion))
        human_terms = replace(
            fixture.terms,
            line_items=(replace(fixture.terms.line_items[0], description="Human revised goods"),),
        )
        negotiate_in_transaction(
            fixture.db,
            NegotiationCommand(
                fixture.deal.id, fixture.buyer_user.id, fixture.buyer.id, uuid4(),
                "submit", fixture.deal.version,
                ProposalBase(legacy.id, legacy.terms_hash, legacy.status), human_terms,
                supersede_current_candidate=fixture.ack(old),
            ),
        )
        latest = fixture.db.scalar(select(Proposal).order_by(Proposal.proposal_number.desc()))
        self.assertNotEqual(latest.terms_hash, legacy.terms_hash)
        self.assertEqual(latest.status, "SUBMITTED")
        self.assertEqual(old.status, "SUPERSEDED")
        self.assertEqual(legacy.lifecycle_origin, "LEGACY")
        models = (Deal, NegotiationSession, Proposal, AgreementVersion, Approval,
                  NegotiationAction, AuditEvent, OutboxEvent, Obligation,
                  PaymentMilestone, PaymentIntent)

        def snapshot() -> dict:
            return {
                model.__tablename__: list(fixture.db.execute(
                    select(model.__table__).order_by(*model.__table__.primary_key.columns)
                ).mappings())
                for model in models
            }

        before = snapshot()

        async def send() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                return await client.post(
                    f"/deals/{fixture.deal.id}/agreements",
                    json={"proposal_id": str(legacy.id)},
                )

        response = asyncio.run(send())
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(
            response.json()["detail"],
            "Human rounds require explicit negotiation and candidate replacement",
        )
        self.assertEqual(snapshot(), before)
        self.assertEqual(fixture.deal.status, "NEGOTIATING")
        self.assertIsNone(fixture.deal.current_agreement_version_id)
        self.assertEqual([row.action for row in fixture.db.scalars(select(NegotiationAction))], ["submit"])


@unittest.skipUnless(os.environ.get("TEST_POSTGRES_URL"), "Set TEST_POSTGRES_URL for isolated F5 PostgreSQL races")
class NegotiationPostgresRaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.admin_engine = create_database_engine(os.environ["TEST_POSTGRES_URL"])
        self.schema = "negotiation_race_" + uuid4().hex
        with self.admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.addCleanup(self.cleanup_schema)
        url = make_url(os.environ["TEST_POSTGRES_URL"]).update_query_dict({
            "options": f"-csearch_path={self.schema} -clock_timeout=10000 -cstatement_timeout=15000"
        }).render_as_string(hide_password=False)
        self.fixture = NegotiationTests()
        self.fixture.provided_engine = create_database_engine(url)
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)

    def cleanup_schema(self) -> None:
        with self.admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{self.schema}" CASCADE'))
        self.admin_engine.dispose()

    def race(self, *operations) -> list[object]:
        barrier = Barrier(len(operations))
        def run(operation):
            with Session(self.fixture.engine) as db:
                barrier.wait(timeout=10)
                try:
                    return operation(db)
                except (NegotiationConflict, StaleAgreementVersion, InvalidTransition) as error:
                    return error
        with ThreadPoolExecutor(max_workers=len(operations)) as executor:
            futures = [executor.submit(run, operation) for operation in operations]
            results = [future.result(timeout=30) for future in futures]
        self.fixture.db.expire_all()
        return results

    def test_simultaneous_counters_have_one_successor(self) -> None:
        self.fixture.submit()
        commands = [self.fixture.current_command("counter") for _ in range(2)]
        results = self.race(*(lambda db, command=command: negotiate_in_transaction(db, command) for command in commands))
        self.assertEqual(sum(isinstance(result, dict) for result in results), 1)
        proposals = list(self.fixture.db.scalars(select(Proposal).order_by(Proposal.proposal_number)))
        self.assertEqual([row.status for row in proposals], ["SUPERSEDED", "SUBMITTED"])
        self.assertEqual(proposals[1].based_on_proposal_id, proposals[0].id)
        self.assertEqual(len(list(self.fixture.db.scalars(select(NegotiationAction)))), 2)
        self.fixture.assert_no_execution()

    def test_simultaneous_acceptances_create_one_empty_candidate(self) -> None:
        self.fixture.submit()
        commands = [self.fixture.current_command("accept") for _ in range(2)]
        results = self.race(*(lambda db, command=command: negotiate_in_transaction(db, command) for command in commands))
        self.assertEqual(sum(isinstance(result, dict) for result in results), 1)
        self.assertEqual(len(list(self.fixture.db.scalars(select(AgreementVersion)))), 1)
        self.assertEqual(list(self.fixture.db.scalars(select(Approval))), [])
        self.fixture.assert_no_execution()

    def test_accept_versus_expire_has_one_terminal_transition(self) -> None:
        now = datetime.now(UTC)
        self.fixture.command = NegotiationCommand(
            self.fixture.deal.id, self.fixture.buyer_user.id, self.fixture.buyer.id,
            uuid4(), "submit", 0, None, self.fixture.terms, expires_at=now + timedelta(seconds=1)
        )
        negotiate_in_transaction(self.fixture.db, self.fixture.command, now=now)
        accept = replace(self.fixture.current_command("accept"), expires_at=None)
        expire = replace(self.fixture.current_command("expire"), expires_at=None)
        results = self.race(
            lambda db: negotiate_in_transaction(db, accept, now=now),
            lambda db: negotiate_in_transaction(db, expire, now=now + timedelta(seconds=1)),
        )
        self.assertEqual(sum(isinstance(result, dict) for result in results), 1)
        latest = self.fixture.db.scalar(select(Proposal))
        self.assertIn(latest.status, ("ACCEPTED_AS_CANDIDATE", "EXPIRED"))
        self.assertEqual(len(list(self.fixture.db.scalars(select(NegotiationAction)))), 2)
        self.assertEqual(len(list(self.fixture.db.scalars(select(AgreementVersion)))), int(latest.status == "ACCEPTED_AS_CANDIDATE"))

    def test_replacement_serializes_with_approval_and_commit(self) -> None:
        self.fixture.submit()
        old = self.fixture.accept()
        replacement = self.fixture.current_command("submit", seller=False, supersede_current_candidate=self.fixture.ack(old))
        approval = RecordApprovalCommand(
            self.fixture.deal.id, old.version_number, old.terms_hash,
            self.fixture.buyer.id, self.fixture.buyer_user.id, ApprovalDecision.APPROVE
        )
        self.race(
            lambda db: negotiate_in_transaction(db, replacement),
            lambda db: record_approval_in_transaction(db, approval),
        )
        self.assertEqual(old.status, "SUPERSEDED")
        current = self.fixture.accept()
        self.assertEqual(list(self.fixture.db.scalars(select(Approval).where(Approval.agreement_version_id == current.id))), [])
        self.fixture.approve(current)
        self.fixture.approve(current, seller=True)
        approvals = list(self.fixture.db.scalars(select(Approval)))
        expected_notifications = [
            {
                "deal_id": str(self.fixture.deal.id),
                "record_id": str(row.agreement_version_id),
                "kind": "AGREEMENT_APPROVAL_RECORDED",
            }
            for row in approvals
        ]
        notifications = list(self.fixture.db.execute(
            select(OutboxEvent.__table__).order_by(OutboxEvent.id)
        ).mappings())
        self.assertIn(len(notifications), (2, 3))
        self.assertEqual(len(notifications), len(expected_notifications))
        self.assertCountEqual([row["payload"] for row in notifications], expected_notifications)
        for row in notifications:
            self.assertEqual(row["event_type"], "DEAL_NOTIFICATION")
            self.assertEqual(row["aggregate_type"], "deal")
            self.assertEqual(row["aggregate_id"], self.fixture.deal.id)
        replacement = self.fixture.current_command("submit", seller=False, supersede_current_candidate=self.fixture.ack(current))
        commit = CommitAgreementCommand(
            self.fixture.deal.id, current.version_number, current.terms_hash,
            self.fixture.seller_user.id, self.fixture.seller.id
        )
        results = self.race(
            lambda db: negotiate_in_transaction(db, replacement),
            lambda db: commit_agreement_in_transaction(db, commit),
        )
        self.assertEqual(sum(not isinstance(result, Exception) for result in results), 1)
        self.assertIn(current.status, ("SUPERSEDED", "COMMITTED"))
        if current.status == "SUPERSEDED":
            self.assertEqual(list(self.fixture.db.execute(
                select(OutboxEvent.__table__).order_by(OutboxEvent.id)
            ).mappings()), notifications)
            for model in (Obligation, PaymentMilestone, PaymentIntent, AuditEvent):
                self.assertEqual(list(self.fixture.db.scalars(select(model))), [])
        else:
            self.assertEqual(self.fixture.deal.status, "AGREED")

    def test_failed_lock_winner_rolls_back_before_successor_runs(self) -> None:
        self.fixture.submit()
        old = self.fixture.accept()
        replacement = self.fixture.current_command("submit", seller=False, supersede_current_candidate=self.fixture.ack(old))
        original_record = SqlAlchemyNegotiationRepository._record
        def fail_one(repository, command, *args, **kwargs):
            if command.command_id == replacement.command_id:
                raise RuntimeError("injected winner rollback")
            return original_record(repository, command, *args, **kwargs)
        succeeding = replace(replacement, command_id=uuid4())
        winner_locked = Event()
        contender_started = Event()
        def failing(db):
            from syncally.infrastructure.counterparty_onboarding import lock_deal
            lock_deal(db, replacement.deal_id)
            winner_locked.set()
            self.assertTrue(contender_started.wait(timeout=10))
            try:
                negotiate_in_transaction(db, replacement)
            except RuntimeError as error:
                return error
            self.fail("Injected history failure must roll back")
        def succeed(db):
            self.assertTrue(winner_locked.wait(timeout=10))
            contender_started.set()
            return negotiate_in_transaction(db, succeeding)
        with patch.object(SqlAlchemyNegotiationRepository, "_record", fail_one):
            results = self.race(failing, succeed)
        self.assertEqual(sum(isinstance(result, dict) for result in results), 1)
        self.assertEqual(sum(isinstance(result, RuntimeError) for result in results), 1)
        self.assertEqual(old.status, "SUPERSEDED")
        self.assertEqual(len(list(self.fixture.db.scalars(select(Proposal)))), 2)
        self.assertEqual(len(list(self.fixture.db.scalars(select(NegotiationAction)))), 3)
        self.fixture.assert_no_execution()

    def test_legacy_draft_checks_human_rounds_after_replacement_lock_winner(self) -> None:
        fixture = self.fixture
        create_reviewed_agreement_draft_in_transaction(
            fixture.db,
            CreateReviewedAgreementDraftCommand(
                fixture.deal.id, fixture.buyer.id, fixture.buyer_user.id, fixture.terms
            ),
        )
        legacy = fixture.db.scalar(select(Proposal))
        old = fixture.db.scalar(select(AgreementVersion))
        replacement = NegotiationCommand(
            fixture.deal.id, fixture.buyer_user.id, fixture.buyer.id, uuid4(),
            "submit", fixture.deal.version,
            ProposalBase(legacy.id, legacy.terms_hash, legacy.status),
            replace(fixture.terms, line_items=(
                replace(fixture.terms.line_items[0], description="Human revised goods"),
            )),
            supersede_current_candidate=fixture.ack(old),
        )
        draft = CreateAgreementDraftCommand(fixture.deal.id, legacy.id, fixture.buyer_user.id)
        winner_locked = Event()
        contender_started = Event()

        def replace_candidate(db):
            from syncally.infrastructure.counterparty_onboarding import lock_deal
            lock_deal(db, replacement.deal_id)
            winner_locked.set()
            self.assertTrue(contender_started.wait(timeout=10))
            return negotiate_in_transaction(db, replacement)

        def create_legacy_draft(db):
            self.assertTrue(winner_locked.wait(timeout=10))
            contender_started.set()
            try:
                return create_agreement_draft_in_transaction(db, draft)
            except AgreementVersionConflict as error:
                return error

        results = self.race(replace_candidate, create_legacy_draft)
        self.assertIsInstance(results[0], dict)
        self.assertIsInstance(results[1], AgreementVersionConflict)
        self.assertEqual(str(results[1]), "Human rounds require explicit negotiation and candidate replacement")
        self.assertEqual(old.status, "SUPERSEDED")
        self.assertEqual(fixture.deal.status, "NEGOTIATING")
        self.assertIsNone(fixture.deal.current_agreement_version_id)
        self.assertEqual(list(fixture.db.scalars(select(AgreementVersion))), [old])
        latest = fixture.db.scalar(select(Proposal).order_by(Proposal.proposal_number.desc()))
        self.assertEqual(latest.status, "SUBMITTED")
        self.assertNotEqual(latest.terms_hash, legacy.terms_hash)
        self.assertEqual([row.action for row in fixture.db.scalars(select(NegotiationAction))], ["submit"])
        self.assertEqual(list(fixture.db.scalars(select(Approval))), [])
        fixture.assert_no_execution()


class NegotiationSqliteRaceTests(NegotiationPostgresRaceTests):
    __unittest_skip__ = False

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.fixture = NegotiationTests()
        self.fixture.provided_engine = create_database_engine(
            "sqlite:///" + (Path(temporary.name) / "negotiation.db").as_posix()
        )
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)