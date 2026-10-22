"""Opt-in end-to-end smoke test for local PostgreSQL and Temporal services."""

from __future__ import annotations

import asyncio
import json
import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import temporalio.client
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session
from temporalio.worker import Worker
from test_domain_fixes import build_terms

from syncally.application.agreements import CommitAgreementCommand, RecordApprovalCommand
from syncally.application.workflow_notifications import NotificationKind
from syncally.domain.agreements.agreement import ApprovalDecision
from syncally.domain.shared.identifiers import OrganizationId
from syncally.infrastructure.models import (
    AgreementVersion,
    Approval,
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
from syncally.infrastructure.outbox import dispatch_pending_outbox_events
from syncally.infrastructure.repositories.agreements import (
    commit_agreement_in_transaction,
    record_approval_in_transaction,
)
from syncally.infrastructure.temporal import TemporalDealWorkflowStarter
from syncally.infrastructure.workflow_notifications import queue_deal_workflow_notification
from syncally.workflows.deal import DealWorkflow
from syncally.workflows.worker import create_worker


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL") and os.environ.get("SYNCALLY_TEMPORAL_ADDRESS"),
    "Set TEST_POSTGRES_URL and SYNCALLY_TEMPORAL_ADDRESS for local service smoke test",
)
class LocalWorkflowSmokeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temporal_client = await temporalio.client.Client.connect(
            os.environ["SYNCALLY_TEMPORAL_ADDRESS"],
            namespace=os.environ.get("TEMPORAL_NAMESPACE", "default"),
        )
        self.task_queue = f"syncally-local-smoke-{uuid4()}"
        self.starter = await asyncio.to_thread(
            TemporalDealWorkflowStarter.connect,
            address=os.environ["SYNCALLY_TEMPORAL_ADDRESS"],
            namespace=os.environ.get("TEMPORAL_NAMESPACE", "default"),
            task_queue=self.task_queue,
        )

        self.engine = create_engine(os.environ["TEST_POSTGRES_URL"])
        self.schema = f"syncally_smoke_{uuid4().hex}"
        with self.engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.scoped_engine = self.engine.execution_options(schema_translate_map={None: self.schema})
        Base.metadata.create_all(self.scoped_engine)
        self._seed_agreement()
        self.workflow_id = f"deal/{self.deal_id}/lifecycle"

    async def asyncTearDown(self) -> None:
        if hasattr(self, "starter"):
            self.starter._loop.close()
        if hasattr(self, "engine"):
            with self.engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA IF EXISTS "{self.schema}" CASCADE'))
            self.engine.dispose()

    async def test_outbox_signal_and_worker_restart_preserve_single_commit(self) -> None:
        workflow_handle = None
        worker, executor = await self._start_worker()
        try:
            with Session(self.scoped_engine) as db:
                queue_deal_workflow_notification(
                    db,
                    deal_id=self.deal_id,
                    record_id=self.version_id,
                    kind=NotificationKind.DEAL_CREATED,
                )
                db.commit()

            self.assertEqual(await self._dispatch_outbox(), 1)
            workflow_handle = self.temporal_client.get_workflow_handle(self.workflow_id)
            await self._wait_for_processed(workflow_handle, 1)

            with Session(self.scoped_engine) as db:
                record_approval_in_transaction(
                    db,
                    RecordApprovalCommand(
                        deal_id=self.deal_id,
                        version_number=1,
                        terms_hash=self.terms_hash,
                        organization_id=self.buyer_id,
                        user_id=self.buyer_user_id,
                        decision=ApprovalDecision.APPROVE,
                    ),
                )
            self.assertEqual(await self._dispatch_outbox(), 1)
            await self._wait_for_processed(workflow_handle, 2)
        finally:
            await worker.__aexit__(None, None, None)
            executor.shutdown(wait=True)

        # Temporal durably accepts notifications while no worker is polling.
        with Session(self.scoped_engine) as db:
            record_approval_in_transaction(
                db,
                RecordApprovalCommand(
                    deal_id=self.deal_id,
                    version_number=1,
                    terms_hash=self.terms_hash,
                    organization_id=self.seller_id,
                    user_id=self.seller_user_id,
                    decision=ApprovalDecision.APPROVE,
                ),
            )
        command = CommitAgreementCommand(
            deal_id=self.deal_id,
            expected_version=1,
            expected_terms_hash=self.terms_hash,
        )
        concurrent_results = await asyncio.to_thread(self._commit_concurrently, command)
        self.assertEqual(concurrent_results, ["COMMITTED", "COMMITTED"])
        self.assertEqual(await self._dispatch_outbox(), 2)

        worker, executor = await self._start_worker()
        try:
            await self._wait_for_processed(workflow_handle, 4)
            self.assertEqual((await workflow_handle.describe()).status.name, "RUNNING")
            with Session(self.scoped_engine) as db:
                replay = commit_agreement_in_transaction(db, command)
            self.assertEqual(replay.status.value, "COMMITTED")
        finally:
            await worker.__aexit__(None, None, None)
            executor.shutdown(wait=True)

        with Session(self.scoped_engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Approval)), 2)
            self.assertEqual(db.scalar(select(func.count()).select_from(Obligation)), 2)
            self.assertEqual(
                db.scalar(
                    select(func.count())
                    .select_from(AuditEvent)
                    .where(AuditEvent.event_type == "AGREEMENT_COMMITTED")
                ),
                1,
            )
            self.assertEqual(
                db.scalar(
                    select(func.count())
                    .select_from(OutboxEvent)
                    .where(OutboxEvent.event_type == "AGREEMENT_COMMITTED")
                ),
                1,
            )
            self.assertEqual(db.get(Deal, self.deal_id).status, "AGREED")
            self.assertEqual(
                db.scalar(
                    select(func.count())
                    .select_from(OutboxEvent)
                    .where(OutboxEvent.status != "DELIVERED")
                ),
                0,
            )

    def _seed_agreement(self) -> None:
        self.buyer_user_id, self.seller_user_id = uuid4(), uuid4()
        self.buyer_id, self.seller_id = uuid4(), uuid4()
        self.deal_id = uuid4()
        self.terms = build_terms(
            buyer_id=OrganizationId(self.buyer_id),
            seller_id=OrganizationId(self.seller_id),
        )
        self.terms_hash = self.terms.terms_hash

        with Session(self.scoped_engine) as db:
            db.add_all(
                [
                    User(
                        id=self.buyer_user_id,
                        email=f"buyer-{uuid4()}@example.test",
                        display_name="Buyer",
                    ),
                    User(
                        id=self.seller_user_id,
                        email=f"seller-{uuid4()}@example.test",
                        display_name="Seller",
                    ),
                    Organization(id=self.buyer_id, legal_name="Buyer Co", country_code="US"),
                    Organization(id=self.seller_id, legal_name="Seller Co", country_code="CA"),
                ]
            )
            db.flush()
            db.add_all(
                [
                    OrganizationMember(
                        user_id=self.buyer_user_id, organization_id=self.buyer_id, status="ACTIVE"
                    ),
                    OrganizationMember(
                        user_id=self.seller_user_id, organization_id=self.seller_id, status="ACTIVE"
                    ),
                    Deal(
                        id=self.deal_id,
                        buyer_organization_id=self.buyer_id,
                        seller_organization_id=self.seller_id,
                        status="PENDING_APPROVALS",
                        version=1,
                    ),
                ]
            )
            db.flush()
            negotiation = NegotiationSession(deal_id=self.deal_id, max_rounds=5)
            db.add(negotiation)
            db.flush()
            proposal = Proposal(
                deal_id=self.deal_id,
                negotiation_session_id=negotiation.id,
                proposal_number=1,
                author_organization_id=self.buyer_id,
                terms_json=json.loads(self.terms.canonical_json()),
                terms_hash=self.terms_hash,
            )
            db.add(proposal)
            db.flush()
            version = AgreementVersion(
                deal_id=self.deal_id,
                proposal_id=proposal.id,
                version_number=1,
                canonical_terms_json=self.terms.to_storage_dict(),
                terms_hash=self.terms_hash,
                status="PENDING_APPROVAL",
                created_by=self.buyer_user_id,
            )
            db.add(version)
            db.flush()
            self.version_id = version.id
            db.get(Deal, self.deal_id).current_agreement_version_id = version.id
            db.commit()

    def _commit_concurrently(self, command: CommitAgreementCommand) -> list[str]:
        start_gate = threading.Barrier(2)

        def commit_once() -> str:
            with Session(self.scoped_engine) as db:
                # Both sessions contend for the same pending version. PostgreSQL's row lock
                # and compare-and-swap must serialize the commit without duplicating effects.
                start_gate.wait(timeout=10)
                return commit_agreement_in_transaction(db, command).status.value

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(commit_once) for _ in range(2)]
            return [future.result(timeout=20) for future in futures]

    async def _start_worker(self) -> tuple[Worker, ThreadPoolExecutor]:
        executor = ThreadPoolExecutor(max_workers=2)
        worker = create_worker(
            self.temporal_client,
            task_queue=self.task_queue,
            activity_executor=executor,
            session_factory=lambda: Session(self.scoped_engine),
        )
        await worker.__aenter__()
        return worker, executor

    async def _dispatch_outbox(self) -> int:
        return await asyncio.to_thread(
            dispatch_pending_outbox_events,
            lambda: Session(self.scoped_engine),
            self.starter,
            batch_size=10,
        )

    async def _wait_for_processed(self, handle, expected: int) -> None:
        # A restarted Temporal worker may wait for the server's sticky-task
        # timeout before the workflow task is offered to its new poller.
        async with asyncio.timeout(30):
            while await handle.query(DealWorkflow.processed_notification_count) < expected:
                await asyncio.sleep(0.05)


if __name__ == "__main__":
    unittest.main()
