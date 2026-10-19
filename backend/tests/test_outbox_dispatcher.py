"""Tests for the outbox-to-Temporal dispatcher (S6-01)."""

import asyncio
import os
import unittest
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import temporalio.common
import temporalio.exceptions
from sqlalchemy import create_engine, select, text
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from test_domain_fixes import build_terms

from syncally.application.agreements import (
    CommitAgreementCommand,
    RecordApprovalCommand,
    record_approval,
)
from syncally.application.outbox import (
    PendingOutboxEvent,
    WorkflowStartOutcome,
    WorkflowStartTransientError,
    build_deal_workflow_id,
    dispatch_outbox_event,
)
from syncally.domain.agreements.agreement import ApprovalDecision
from syncally.domain.shared.identifiers import OrganizationId
from syncally.infrastructure.models import (
    AgreementVersion,
    Base,
    Deal,
    NegotiationSession,
    Organization,
    OrganizationMember,
    OutboxEvent,
    Proposal,
    User,
)
from syncally.infrastructure.outbox import (
    _claim_statement,
    apply_dispatch_result,
    claim_next_pending_event,
    dispatch_one_pending_event,
    dispatch_pending_outbox_events,
)
from syncally.infrastructure.repositories.agreements import (
    SqlAlchemyAgreementRepository,
    commit_agreement_in_transaction,
)
from syncally.infrastructure.temporal import TemporalDealWorkflowStarter


class FakeDealWorkflowStarter:
    """Scripted Temporal double: no network, deterministic already-started behavior."""

    def __init__(self, *, failures: Sequence[Exception] = ()) -> None:
        self._failures = list(failures)
        self._started_ids: set[str] = set()
        self.calls: list[dict] = []

    def start_deal_workflow(self, *, workflow_id, deal_id, agreement_version_id):
        self.calls.append(
            {
                "workflow_id": workflow_id,
                "deal_id": deal_id,
                "agreement_version_id": agreement_version_id,
            }
        )
        if self._failures:
            raise self._failures.pop(0)
        if workflow_id in self._started_ids:
            return WorkflowStartOutcome.ALREADY_RUNNING
        self._started_ids.add(workflow_id)
        return WorkflowStartOutcome.STARTED


class OutboxDispatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self._seed_committed_agreement()

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _seed_committed_agreement(self) -> None:
        """Commit one agreement through the real write path, leaving one pending outbox row."""
        buyer_user = User(email="buyer@example.com", display_name="Buyer")
        seller_user = User(email="seller@example.com", display_name="Seller")
        buyer_org = Organization(legal_name="Buyer Co", country_code="US")
        seller_org = Organization(legal_name="Seller Co", country_code="CA")
        self.session.add_all([buyer_user, seller_user, buyer_org, seller_org])
        self.session.flush()
        self.session.add_all(
            [
                OrganizationMember(
                    user_id=buyer_user.id, organization_id=buyer_org.id, status="ACTIVE"
                ),
                OrganizationMember(
                    user_id=seller_user.id, organization_id=seller_org.id, status="ACTIVE"
                ),
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

        terms = build_terms(
            buyer_id=OrganizationId(buyer_org.id), seller_id=OrganizationId(seller_org.id)
        )
        import json

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
        self.version = AgreementVersion(
            deal_id=self.deal.id,
            proposal_id=proposal.id,
            version_number=1,
            canonical_terms_json=json.loads(terms.canonical_json()),
            terms_hash=terms.terms_hash,
            status="PENDING_APPROVAL",
            created_by=buyer_user.id,
        )
        self.session.add(self.version)
        self.session.flush()
        self.deal.current_agreement_version_id = self.version.id
        self.session.commit()

        for org_id, user_id in ((buyer_org.id, buyer_user.id), (seller_org.id, seller_user.id)):
            record_approval(
                RecordApprovalCommand(
                    deal_id=self.deal.id,
                    version_number=self.version.version_number,
                    terms_hash=terms.terms_hash,
                    organization_id=org_id,
                    user_id=user_id,
                    decision=ApprovalDecision.APPROVE,
                ),
                SqlAlchemyAgreementRepository(self.session),
            )

        commit_agreement_in_transaction(
            self.session,
            CommitAgreementCommand(
                deal_id=self.deal.id,
                expected_version=self.version.version_number,
                expected_terms_hash=terms.terms_hash,
            ),
        )

    def _pending_row(self) -> OutboxEvent:
        return self.session.scalar(select(OutboxEvent).where(OutboxEvent.status == "PENDING"))

    # -- Acceptance criteria --------------------------------------------

    def test_dispatch_starts_workflow_and_marks_delivered(self) -> None:
        starter = FakeDealWorkflowStarter()

        dispatched = dispatch_one_pending_event(self.session, starter)

        self.assertTrue(dispatched)
        row = self.session.scalar(select(OutboxEvent))
        self.assertEqual(row.status, "DELIVERED")
        self.assertIsNotNone(row.delivered_at)
        self.assertEqual(len(starter.calls), 1)
        self.assertEqual(starter.calls[0]["workflow_id"], build_deal_workflow_id(self.deal.id))

    def test_already_running_workflow_is_treated_as_delivered(self) -> None:
        starter = FakeDealWorkflowStarter()
        starter._started_ids.add(build_deal_workflow_id(self.deal.id))

        dispatch_one_pending_event(self.session, starter)

        row = self.session.scalar(select(OutboxEvent))
        self.assertEqual(row.status, "DELIVERED")
        self.assertEqual(len(starter.calls), 1)

    def test_temporal_down_leaves_row_pending_for_retry(self) -> None:
        starter = FakeDealWorkflowStarter(failures=[WorkflowStartTransientError("down")])

        dispatch_one_pending_event(self.session, starter)

        row = self.session.scalar(select(OutboxEvent))
        self.assertEqual(row.status, "PENDING")
        self.assertEqual(row.retry_count, 1)
        self.assertIn("down", row.error_detail)
        self.assertIsNone(row.delivered_at)
        self.assertIsNotNone(row.next_attempt_at)

    def test_temporal_recovery_obeys_persisted_retry_schedule(self) -> None:
        now = datetime.now(UTC)
        starter = FakeDealWorkflowStarter(failures=[WorkflowStartTransientError("down")])
        dispatch_one_pending_event(self.session, starter, now=now)
        self.assertFalse(dispatch_one_pending_event(self.session, starter, now=now))
        # A fresh session models restarting the dispatcher after the service recovers.
        with Session(self.engine) as recovered:
            self.assertTrue(dispatch_one_pending_event(recovered, starter, now=now + timedelta(seconds=3)))
            row = recovered.scalar(select(OutboxEvent))
            self.assertEqual(row.status, "DELIVERED")
            self.assertIsNone(row.next_attempt_at)
        self.assertEqual(len(starter.calls), 2)

    def test_failing_oldest_event_does_not_block_later_events(self) -> None:
        first = self._pending_row()
        first.created_at = datetime.now(UTC) - timedelta(minutes=1)
        later_deal_id = uuid4()
        self.session.add(OutboxEvent(
            aggregate_type="agreement", aggregate_id=uuid4(), event_type="AGREEMENT_COMMITTED",
            payload={"deal_id": str(later_deal_id), "agreement_version_id": str(uuid4())},
        ))
        self.session.commit()
        starter = FakeDealWorkflowStarter(failures=[WorkflowStartTransientError("down")])

        self.assertEqual(dispatch_pending_outbox_events(lambda: Session(self.engine), starter, batch_size=5), 2)
        self.assertEqual([call["deal_id"] for call in starter.calls], [self.deal.id, later_deal_id])
        with Session(self.engine) as verify:
            rows = list(verify.scalars(select(OutboxEvent).order_by(OutboxEvent.created_at)))
            self.assertEqual([row.status for row in rows], ["PENDING", "DELIVERED"])

    def test_crash_after_start_before_delivery_commit_is_safe_to_retry(self) -> None:
        starter = FakeDealWorkflowStarter()
        with Session(self.engine) as crashed:
            with patch.object(crashed, "commit", side_effect=RuntimeError("process stopped")):
                with self.assertRaisesRegex(RuntimeError, "process stopped"):
                    dispatch_one_pending_event(crashed, starter)
        with Session(self.engine) as recovered:
            self.assertEqual(recovered.scalar(select(OutboxEvent)).status, "PENDING")
            self.assertTrue(dispatch_one_pending_event(recovered, starter))
            self.assertEqual(recovered.scalar(select(OutboxEvent)).status, "DELIVERED")
        self.assertEqual(len(starter.calls), 2)
        self.assertEqual(len(starter._started_ids), 1)

    def test_invalid_payload_shapes_are_failed_and_do_not_block_queue(self) -> None:
        for payload in (None, [], {}, {"deal_id": None}, {"deal_id": 123},
                        {"deal_id": {}}, {"deal_id": str(uuid4()), "agreement_version_id": []}):
            with self.subTest(payload=payload):
                row = self.session.scalar(select(OutboxEvent))
                row.payload = payload
                row.status = "PENDING"
                self.session.commit()
                starter = FakeDealWorkflowStarter()
                self.assertTrue(dispatch_one_pending_event(self.session, starter))
                self.assertEqual(row.status, "FAILED")
                self.assertEqual(starter.calls, [])
                self.assertIsNone(claim_next_pending_event(self.session))

    def test_stopped_dispatcher_then_recovery_delivers_pending_row(self) -> None:
        # "Stopped": nothing has run yet, the row just sits there.
        row = self._pending_row()
        self.assertIsNotNone(row)

        # "Recovered": a dispatcher runs later and picks it up with no special
        # age/lease handling - status alone is enough.
        starter = FakeDealWorkflowStarter()
        dispatched = dispatch_pending_outbox_events(
            lambda: Session(self.engine), starter, batch_size=5
        )

        self.assertEqual(dispatched, 1)
        with Session(self.engine) as verify_session:
            self.assertEqual(verify_session.scalar(select(OutboxEvent)).status, "DELIVERED")

    def test_two_dispatchers_racing_on_same_row_cause_no_duplicate_start(self) -> None:
        # Two dispatchers both read the row while it is still PENDING - SQLite
        # has no row lock to stop this, so this is the real worst case.
        shared_starter = FakeDealWorkflowStarter()
        row_id = self._pending_row().id
        with Session(self.engine) as session_a, Session(self.engine) as session_b:
            row_a = session_a.get(OutboxEvent, row_id)
            row_b = session_b.get(OutboxEvent, row_id)
            self.assertEqual(row_a.status, "PENDING")
            self.assertEqual(row_b.status, "PENDING")

            event = PendingOutboxEvent(id=row_id, event_type=row_a.event_type, payload=row_a.payload)
            result_a = dispatch_outbox_event(event, shared_starter)
            result_b = dispatch_outbox_event(event, shared_starter)

            apply_dispatch_result(row_a, result_a)
            session_a.commit()
            apply_dispatch_result(row_b, result_b)
            session_b.commit()

        # Both calls happened, but only one workflow was ever actually started -
        # the second got Temporal's own "already started" answer, not a
        # duplicate side effect. The row converges to delivered exactly once.
        self.assertEqual(len(shared_starter.calls), 2)
        self.assertEqual(len(shared_starter._started_ids), 1)
        with Session(self.engine) as verify:
            self.assertEqual(verify.scalar(select(OutboxEvent)).status, "DELIVERED")

    def test_dispatch_never_forwards_full_payload_to_starter(self) -> None:
        starter = FakeDealWorkflowStarter()
        row = self._pending_row()
        leaky_payload = dict(row.payload, message_body="private conversation text")

        dispatch_outbox_event(
            PendingOutboxEvent(id=row.id, event_type=row.event_type, payload=leaky_payload),
            starter,
        )

        self.assertEqual(
            set(starter.calls[0].keys()), {"workflow_id", "deal_id", "agreement_version_id"}
        )

    def test_unknown_event_type_is_a_permanent_error(self) -> None:
        starter = FakeDealWorkflowStarter()
        event = PendingOutboxEvent(id=self.version.id, event_type="SOMETHING_ELSE", payload={})

        result = dispatch_outbox_event(event, starter)

        self.assertFalse(result.delivered)
        self.assertTrue(result.permanent_failure)
        self.assertEqual(starter.calls, [])

    def test_permanent_failure_moves_row_out_of_pending(self) -> None:
        # A permanent error must not leave the row re-claimable, or it would
        # block every later outbox row forever.
        row = self._pending_row()
        row.event_type = "SOMETHING_ELSE"
        self.session.commit()
        starter = FakeDealWorkflowStarter()

        dispatch_one_pending_event(self.session, starter)

        row = self.session.scalar(select(OutboxEvent))
        self.assertEqual(row.status, "FAILED")
        self.assertIsNotNone(row.error_detail)
        self.assertIsNone(claim_next_pending_event(self.session))

    def test_malformed_payload_is_a_permanent_error(self) -> None:
        starter = FakeDealWorkflowStarter()
        event = PendingOutboxEvent(
            id=self.version.id, event_type="AGREEMENT_COMMITTED", payload={"deal_id": "not-a-uuid"}
        )

        result = dispatch_outbox_event(event, starter)

        self.assertFalse(result.delivered)
        self.assertTrue(result.permanent_failure)
        self.assertEqual(starter.calls, [])

    # -- Pure helpers, no DB -----------------------------------------------

    def test_claim_statement_uses_skip_locked_only_on_postgresql(self) -> None:
        fake_db = MagicMock()
        fake_db.bind.dialect.name = "postgresql"
        claim_next_pending_event(fake_db)
        pg_stmt = fake_db.scalar.call_args[0][0]
        self.assertIn("FOR UPDATE SKIP LOCKED", str(pg_stmt.compile(dialect=postgresql.dialect())).upper())

        sqlite_sql = str(_claim_statement().compile(dialect=sqlite.dialect())).upper()
        self.assertNotIn("FOR UPDATE", sqlite_sql)

    def test_build_deal_workflow_id_is_stable(self) -> None:
        self.assertEqual(
            build_deal_workflow_id(self.deal.id), f"deal/{self.deal.id}/lifecycle"
        )
        self.assertEqual(build_deal_workflow_id(self.deal.id), build_deal_workflow_id(self.deal.id))


@unittest.skipUnless(os.environ.get("TEST_POSTGRES_URL"), "Set TEST_POSTGRES_URL for PostgreSQL locking tests")
class PostgresDispatcherTests(unittest.TestCase):
    def test_dispatchers_skip_locked_row_and_recover_after_rollback(self) -> None:
        engine = create_engine(os.environ["TEST_POSTGRES_URL"])
        schema = f"outbox_test_{uuid4().hex}"
        try:
            with engine.begin() as connection:
                connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            scoped_engine = engine.execution_options(schema_translate_map={None: schema})
            Base.metadata.create_all(scoped_engine)
            first_id, second_id = uuid4(), uuid4()
            with Session(scoped_engine) as seed:
                for offset, event_id in enumerate((first_id, second_id)):
                    seed.add(OutboxEvent(
                        id=event_id, aggregate_type="agreement", aggregate_id=uuid4(),
                        event_type="AGREEMENT_COMMITTED",
                        created_at=datetime.now(UTC) + timedelta(seconds=offset),
                        payload={"deal_id": str(uuid4()), "agreement_version_id": str(uuid4())},
                    ))
                seed.commit()
            starter = FakeDealWorkflowStarter()
            with Session(scoped_engine) as dispatcher_a, Session(scoped_engine) as dispatcher_b:
                # Keep A's transaction open while B uses the real dispatch path.
                dispatcher_b.execute(text("SET statement_timeout = '2s'"))
                self.assertEqual(claim_next_pending_event(dispatcher_a).id, first_id)
                self.assertTrue(dispatch_one_pending_event(dispatcher_b, starter))
                self.assertEqual(dispatcher_b.get(OutboxEvent, second_id).status, "DELIVERED")
                self.assertFalse(dispatch_one_pending_event(dispatcher_b, starter))
                # A stopping releases its transaction lock without losing work.
                dispatcher_a.rollback()
                self.assertTrue(dispatch_one_pending_event(dispatcher_b, starter))
                self.assertEqual(dispatcher_b.get(OutboxEvent, first_id).status, "DELIVERED")
                self.assertEqual(len(starter.calls), 2)
        finally:
            with engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            engine.dispose()


class TemporalAdapterTests(unittest.TestCase):
    def test_rejects_reuse_after_workflow_completes(self) -> None:
        # Exercise the real adapter. The client models a closed execution:
        # ALLOW_DUPLICATE would start again, REJECT_DUPLICATE must reject it.
        calls = []

        async def start(workflow, **kwargs):
            calls.append(kwargs)
            if kwargs.get("id_reuse_policy") == temporalio.common.WorkflowIDReusePolicy.REJECT_DUPLICATE:
                raise temporalio.exceptions.WorkflowAlreadyStartedError(kwargs["id"], workflow)
            self.fail("A completed lifecycle workflow would be started again")

        client = AsyncMock()
        client.start_workflow.side_effect = start
        loop = asyncio.new_event_loop()
        try:
            starter = TemporalDealWorkflowStarter(client, task_queue="test", loop=loop)
            deal_id, agreement_id = uuid4(), uuid4()
            outcome = starter.start_deal_workflow(
                workflow_id=build_deal_workflow_id(deal_id), deal_id=deal_id,
                agreement_version_id=agreement_id,
            )
            self.assertEqual(outcome, WorkflowStartOutcome.ALREADY_RUNNING)
            self.assertEqual(calls[0]["id_conflict_policy"], temporalio.common.WorkflowIDConflictPolicy.FAIL)
            self.assertEqual(calls[0]["args"], [{"deal_id": str(deal_id), "agreement_version_id": str(agreement_id)}])
            self.assertEqual(calls[0]["rpc_timeout"], timedelta(seconds=10))
        finally:
            loop.close()

    def test_network_failure_is_retryable(self) -> None:
        client = AsyncMock()
        client.start_workflow.side_effect = OSError("Temporal down")
        loop = asyncio.new_event_loop()
        try:
            starter = TemporalDealWorkflowStarter(client, task_queue="test", loop=loop)
            with self.assertRaises(WorkflowStartTransientError):
                starter.start_deal_workflow(workflow_id="deal/test/lifecycle", deal_id=uuid4(), agreement_version_id=uuid4())
        finally:
            loop.close()


if __name__ == "__main__":
    unittest.main()
