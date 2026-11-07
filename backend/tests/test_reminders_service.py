"""Comprehensive tests for reminders scheduling, evaluation, dispatch, and suppression."""

import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from syncally.application.reminders import (
    ReminderAccessDenied,
    dispatch_due_reminders,
    list_deal_reminders,
    schedule_deal_reminders,
)
from syncally.domain.reminders.reminder import (
    ReminderScope,
    ReminderStatus,
    SuppressionReason,
)
from syncally.infrastructure.models import (
    AgreementRoutingDecision,
    AgreementVersion,
    AuditEvent,
    Base,
    Deal,
    DealCaseModel,
    DealReminderModel,
    FulfillmentEvent,
    NegotiationSession,
    Obligation,
    Organization,
    OrganizationApprovalRoutingPolicy,
    OrganizationMember,
    OutboxEvent,
    PaymentIntent,
    PaymentMilestone,
    Proposal,
    User,
)
from syncally.infrastructure.repositories.reminders import SqlAlchemyReminderRepository


class RemindersServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.db: Session = self.SessionLocal()

        self.buyer_org = Organization(
            id=uuid4(), legal_name="Buyer Corp", country_code="US", status="ACTIVE"
        )
        self.seller_org = Organization(
            id=uuid4(), legal_name="Seller Corp", country_code="US", status="ACTIVE"
        )
        self.other_org = Organization(
            id=uuid4(), legal_name="Other Corp", country_code="US", status="ACTIVE"
        )
        self.buyer_user = User(
            id=uuid4(), email="buyer@example.com", display_name="Buyer User", password_hash="hash"
        )
        self.seller_user = User(
            id=uuid4(), email="seller@example.com", display_name="Seller User", password_hash="hash"
        )
        self.approver_user = User(
            id=uuid4(), email="approver@example.com", display_name="Approver User", password_hash="hash"
        )

        self.db.add_all(
            [
                self.buyer_org,
                self.seller_org,
                self.other_org,
                self.buyer_user,
                self.seller_user,
                self.approver_user,
            ]
        )
        self.db.flush()

        self.db.add(
            OrganizationMember(
                organization_id=self.buyer_org.id,
                user_id=self.buyer_user.id,
                role="ADMIN",
            )
        )
        self.db.add(
            OrganizationMember(
                organization_id=self.buyer_org.id,
                user_id=self.approver_user.id,
                role="MEMBER",
            )
        )
        self.db.add(
            OrganizationMember(
                organization_id=self.seller_org.id,
                user_id=self.seller_user.id,
                role="ADMIN",
            )
        )
        self.db.flush()

        self.now = datetime(2026, 11, 7, 12, 0, 0, tzinfo=UTC)

        self.deal = Deal(
            id=uuid4(),
            buyer_organization_id=self.buyer_org.id,
            seller_organization_id=self.seller_org.id,
            status="AGREED",
            version=1,
            created_at=self.now,
        )
        self.db.add(self.deal)

        self.session = NegotiationSession(
            id=uuid4(),
            deal_id=self.deal.id,
            max_rounds=5,
            round_count=1,
        )
        self.db.add(self.session)
        self.db.flush()

        self.proposal = Proposal(
            id=uuid4(),
            deal_id=self.deal.id,
            negotiation_session_id=self.session.id,
            proposal_number=1,
            author_organization_id=self.buyer_org.id,
            terms_json={"description": "Test Terms"},
            terms_hash="a" * 64,
        )
        self.db.add(self.proposal)
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def _create_version(self, status: str = "COMMITTED", version_number: int = 1) -> AgreementVersion:
        version = AgreementVersion(
            id=uuid4(),
            deal_id=self.deal.id,
            proposal_id=self.proposal.id,
            version_number=version_number,
            canonical_terms_json={"shipments": [{"quantity": "100.00"}]},
            terms_hash=f"{version_number}" * 64,
            status=status,
            created_by=self.buyer_user.id,
            created_at=self.now,
        )
        self.db.add(version)
        self.db.flush()
        return version

    def test_fulfillment_reminder_scheduling_and_resolution(self) -> None:
        version = self._create_version(status="COMMITTED", version_number=1)
        obligation = Obligation(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=version.id,
            owner_organization_id=self.seller_org.id,
            counterparty_organization_id=self.buyer_org.id,
            obligation_type="DELIVERY",
            status="PENDING",
            created_at=self.now,
        )
        self.db.add(obligation)
        self.db.commit()

        # Step 1: schedule reminders -> should create fulfillment reminder for seller
        reminders = schedule_deal_reminders(self.db, self.deal.id, self.now)
        self.db.commit()
        fulfillment_rems = [r for r in reminders if r.scope is ReminderScope.FULFILLMENT]
        self.assertEqual(len(fulfillment_rems), 1)
        rem = fulfillment_rems[0]
        self.assertEqual(rem.recipient_organization_id, self.seller_org.id)
        self.assertEqual(rem.status, ReminderStatus.SCHEDULED)

        # Idempotency check: rescheduling does not duplicate
        reminders2 = schedule_deal_reminders(self.db, self.deal.id, self.now)
        self.db.commit()
        self.assertEqual(len([r for r in reminders2 if r.scope is ReminderScope.FULFILLMENT]), 0)

        # Step 2: Obligation confirmed -> next schedule suppresses reminder
        self.db.add(
            FulfillmentEvent(
                id=uuid4(),
                deal_id=self.deal.id,
                agreement_version_id=version.id,
                terms_hash="a" * 64,
                obligation_id=obligation.id,
                actor_organization_id=self.buyer_org.id,
                actor_user_id=self.buyer_user.id,
                event_type="CONFIRMED",
                quantity="100.00",
                unit="MT",
                source_type="USER_ATTESTATION",
                idempotency_key=str(uuid4()),
                request_hash="b" * 64,
                version=1,
                recorded_at=self.now,
            )
        )
        self.db.commit()

        schedule_deal_reminders(self.db, self.deal.id, self.now)
        self.db.commit()

        updated_rem = self.db.get(DealReminderModel, rem.id)
        self.assertEqual(updated_rem.status, ReminderStatus.SUPPRESSED.value)
        self.assertEqual(updated_rem.suppression_reason, SuppressionReason.RESOLVED.value)

    def test_milestone_reminder_scheduling_and_resolution(self) -> None:
        version = self._create_version(status="COMMITTED", version_number=1)
        milestone = PaymentMilestone(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=version.id,
            sequence_number=1,
            payer_organization_id=self.buyer_org.id,
            amount=Decimal("5000.00"),
            currency="USD",
            trigger_type="IMMEDIATE",
            due_condition="Upon commitment",
            status="PENDING",
            created_at=self.now,
        )
        self.db.add(milestone)
        self.db.commit()

        # Step 1: Schedule reminder -> milestone reminder for buyer
        reminders = schedule_deal_reminders(self.db, self.deal.id, self.now)
        self.db.commit()
        ms_rems = [r for r in reminders if r.scope is ReminderScope.MILESTONE]
        self.assertEqual(len(ms_rems), 1)
        self.assertEqual(ms_rems[0].recipient_organization_id, self.buyer_org.id)

        # Step 2: Milestone is paid -> next schedule suppresses
        milestone.status = "PAID"
        self.db.commit()

        schedule_deal_reminders(self.db, self.deal.id, self.now)
        self.db.commit()

        updated = self.db.get(DealReminderModel, ms_rems[0].id)
        self.assertEqual(updated.status, ReminderStatus.SUPPRESSED.value)
        self.assertEqual(updated.suppression_reason, SuppressionReason.RESOLVED.value)

    def test_case_reminder_scheduling_and_resolution(self) -> None:
        version = self._create_version(status="COMMITTED", version_number=1)
        # Buyer raises a dispute case
        case = DealCaseModel(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=version.id,
            agreement_terms_hash="c" * 64,
            case_type="DISPUTE",
            reason="Damaged cargo on delivery",
            requested_by_user_id=self.buyer_user.id,
            requested_by_organization_id=self.buyer_org.id,
            status="OPEN",
            created_at=self.now,
        )
        self.db.add(case)
        self.db.commit()

        # Step 1: Schedule reminder -> assigned to seller (counterparty)
        reminders = schedule_deal_reminders(self.db, self.deal.id, self.now)
        self.db.commit()
        case_rems = [r for r in reminders if r.scope is ReminderScope.CASE]
        self.assertEqual(len(case_rems), 1)
        self.assertEqual(case_rems[0].recipient_organization_id, self.seller_org.id)

        # Step 2: Case resolved -> suppressed
        case.status = "RESOLVED"
        case.resolution = "Seller issued credit note"
        self.db.commit()

        schedule_deal_reminders(self.db, self.deal.id, self.now)
        self.db.commit()

        updated = self.db.get(DealReminderModel, case_rems[0].id)
        self.assertEqual(updated.status, ReminderStatus.SUPPRESSED.value)
        self.assertEqual(updated.suppression_reason, SuppressionReason.RESOLVED.value)

    def test_routing_reminder_scheduling_and_decision_suppression(self) -> None:
        draft = self._create_version(status="PENDING_APPROVAL", version_number=2)
        # Buyer has approval routing policy with approver_user
        policy = OrganizationApprovalRoutingPolicy(
            organization_id=self.buyer_org.id,
            mode="SEQUENTIAL",
            approver_user_ids=[str(self.approver_user.id)],
            version=1,
            created_at=self.now,
        )
        self.db.add(policy)
        self.db.commit()

        # Step 1: Schedule reminder -> assigned to approver_user
        reminders = schedule_deal_reminders(self.db, self.deal.id, self.now)
        self.db.commit()
        routing_rems = [r for r in reminders if r.scope is ReminderScope.ROUTING]
        self.assertEqual(len(routing_rems), 1)
        rem = routing_rems[0]
        self.assertEqual(rem.recipient_user_id, self.approver_user.id)
        self.assertEqual(rem.recipient_organization_id, self.buyer_org.id)

        # Step 2: Approver records decision -> suppressed on dispatch recheck
        self.db.add(
            AgreementRoutingDecision(
                id=uuid4(),
                agreement_version_id=draft.id,
                organization_id=self.buyer_org.id,
                user_id=self.approver_user.id,
                decision="APPROVE",
                terms_hash=draft.terms_hash,
                policy_version=1,
                created_at=self.now,
            )
        )
        self.db.commit()

        # Due time arrives -> dispatch rechecks truth and suppresses
        due_time = rem.due_at + timedelta(seconds=1)
        dispatched = dispatch_due_reminders(self.db, due_time)
        self.db.commit()

        self.assertEqual(len(dispatched), 1)
        self.assertEqual(dispatched[0].status, ReminderStatus.SUPPRESSED)
        self.assertEqual(dispatched[0].suppression_reason, SuppressionReason.RESOLVED)

    def test_recipient_revocation_suppresses_reminder(self) -> None:
        self._create_version(status="PENDING_APPROVAL", version_number=2)
        policy = OrganizationApprovalRoutingPolicy(
            organization_id=self.buyer_org.id,
            mode="PARALLEL",
            approver_user_ids=[str(self.approver_user.id)],
            version=1,
            created_at=self.now,
        )
        self.db.add(policy)
        self.db.commit()

        reminders = schedule_deal_reminders(self.db, self.deal.id, self.now)
        self.db.commit()
        rem = [r for r in reminders if r.scope is ReminderScope.ROUTING][0]

        # Revoke approver's membership
        member = self.db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == self.buyer_org.id,
                OrganizationMember.user_id == self.approver_user.id,
            )
        )
        self.db.delete(member)
        self.db.commit()

        # Dispatch recheck finds user revoked -> suppresses with RECIPIENT_REVOKED
        due_time = rem.due_at + timedelta(seconds=1)
        dispatched = dispatch_due_reminders(self.db, due_time)
        self.db.commit()

        self.assertEqual(len(dispatched), 1)
        self.assertEqual(dispatched[0].status, ReminderStatus.SUPPRESSED)
        self.assertEqual(dispatched[0].suppression_reason, SuppressionReason.RECIPIENT_REVOKED)

    def test_terminal_deal_suppresses_all_reminders(self) -> None:
        version = self._create_version(status="COMMITTED", version_number=1)
        milestone = PaymentMilestone(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=version.id,
            sequence_number=1,
            payer_organization_id=self.buyer_org.id,
            amount=Decimal("1000.00"),
            currency="USD",
            trigger_type="IMMEDIATE",
            due_condition="Due",
            status="PENDING",
            created_at=self.now,
        )
        self.db.add(milestone)
        self.db.commit()

        reminders = schedule_deal_reminders(self.db, self.deal.id, self.now)
        self.db.commit()
        self.assertEqual(len(reminders), 1)

        # Mark deal CANCELLED
        self.deal.status = "CANCELLED"
        self.db.commit()

        schedule_deal_reminders(self.db, self.deal.id, self.now)
        self.db.commit()

        updated = self.db.get(DealReminderModel, reminders[0].id)
        self.assertEqual(updated.status, ReminderStatus.SUPPRESSED.value)
        self.assertEqual(updated.suppression_reason, SuppressionReason.DEAL_TERMINAL.value)

    def test_dispatch_delivery_audit_and_workflow_notification(self) -> None:
        version = self._create_version(status="COMMITTED", version_number=1)
        milestone = PaymentMilestone(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=version.id,
            sequence_number=1,
            payer_organization_id=self.buyer_org.id,
            amount=Decimal("1000.00"),
            currency="USD",
            trigger_type="IMMEDIATE",
            due_condition="Due",
            status="PENDING",
            created_at=self.now,
        )
        self.db.add(milestone)
        self.db.commit()

        reminders = schedule_deal_reminders(self.db, self.deal.id, self.now)
        self.db.commit()
        rem = reminders[0]

        # Trigger dispatch at due time
        due_time = rem.due_at + timedelta(seconds=1)
        dispatched = dispatch_due_reminders(self.db, due_time)
        self.db.commit()

        self.assertEqual(len(dispatched), 1)
        delivered_rem = dispatched[0]
        self.assertEqual(delivered_rem.status, ReminderStatus.DELIVERED)
        self.assertEqual(delivered_rem.recurrence_count, 1)

        # Audit event recorded
        audit = self.db.scalar(
            select(AuditEvent).where(
                AuditEvent.aggregate_id == self.deal.id,
                AuditEvent.event_type == "REMINDER_DELIVERED",
            )
        )
        self.assertIsNotNone(audit)
        self.assertEqual(audit.payload["reminder_id"], str(rem.id))

        # Workflow notification queued in outbox
        outbox = self.db.scalar(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == self.deal.id,
                OutboxEvent.event_type == "DEAL_NOTIFICATION",
            )
        )
        self.assertIsNotNone(outbox)
        self.assertEqual(outbox.payload["kind"], "REMINDER_TRIGGERED")
        self.assertEqual(outbox.payload["record_id"], str(rem.id))

    def test_counterparty_privacy_isolation(self) -> None:
        version = self._create_version(status="COMMITTED", version_number=1)
        # Buyer milestone
        self.db.add(
            PaymentMilestone(
                id=uuid4(),
                deal_id=self.deal.id,
                agreement_version_id=version.id,
                sequence_number=1,
                payer_organization_id=self.buyer_org.id,
                amount=Decimal("1000.00"),
                currency="USD",
                trigger_type="IMMEDIATE",
                due_condition="Due",
                status="PENDING",
                created_at=self.now,
            )
        )
        # Seller obligation
        self.db.add(
            Obligation(
                id=uuid4(),
                deal_id=self.deal.id,
                agreement_version_id=version.id,
                owner_organization_id=self.seller_org.id,
                counterparty_organization_id=self.buyer_org.id,
                obligation_type="DELIVERY",
                status="PENDING",
                created_at=self.now,
            )
        )
        self.db.commit()

        schedule_deal_reminders(self.db, self.deal.id, self.now)
        self.db.commit()

        # Buyer lists reminders: sees ONLY buyer reminders
        buyer_list = list_deal_reminders(self.db, self.deal.id, self.buyer_org.id)
        self.assertTrue(all(r.recipient_organization_id == self.buyer_org.id for r in buyer_list))

        # Seller lists reminders: sees ONLY seller reminders
        seller_list = list_deal_reminders(self.db, self.deal.id, self.seller_org.id)
        self.assertTrue(all(r.recipient_organization_id == self.seller_org.id for r in seller_list))

        # Unrelated party gets AccessDenied
        with self.assertRaises(ReminderAccessDenied):
            list_deal_reminders(self.db, self.deal.id, self.other_org.id)

    def test_fulfillment_organization_switched_on_shipment(self) -> None:
        version = self._create_version(status="COMMITTED", version_number=1)
        obligation = Obligation(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=version.id,
            owner_organization_id=self.seller_org.id,
            counterparty_organization_id=self.buyer_org.id,
            obligation_type="DELIVERY",
            status="PENDING",
            created_at=self.now,
        )
        self.db.add(obligation)
        self.db.commit()

        # Initially, seller has scheduled fulfillment reminder
        reminders = schedule_deal_reminders(self.db, self.deal.id, self.now)
        self.db.commit()
        seller_rems = [r for r in reminders if r.scope is ReminderScope.FULFILLMENT]
        self.assertEqual(len(seller_rems), 1)
        self.assertEqual(seller_rems[0].recipient_organization_id, self.seller_org.id)

        # Seller ships all 100 MT
        self.db.add(
            FulfillmentEvent(
                id=uuid4(),
                deal_id=self.deal.id,
                agreement_version_id=version.id,
                terms_hash="a" * 64,
                obligation_id=obligation.id,
                actor_organization_id=self.seller_org.id,
                actor_user_id=self.seller_user.id,
                event_type="SHIPPED",
                quantity="100.00",
                unit="MT",
                source_type="USER_ATTESTATION",
                idempotency_key=str(uuid4()),
                request_hash="s" * 64,
                version=1,
                recorded_at=self.now,
            )
        )
        self.db.commit()

        # Reschedule: seller reminder must be suppressed with ORGANIZATION_SWITCHED
        # and buyer reminder scheduled to confirm goods
        new_rems = schedule_deal_reminders(self.db, self.deal.id, self.now)
        self.db.commit()

        old_rem = self.db.get(DealReminderModel, seller_rems[0].id)
        self.assertEqual(old_rem.status, ReminderStatus.SUPPRESSED.value)
        self.assertEqual(old_rem.suppression_reason, SuppressionReason.ORGANIZATION_SWITCHED.value)

        buyer_rems = [r for r in new_rems if r.scope is ReminderScope.FULFILLMENT]
        self.assertEqual(len(buyer_rems), 1)
        self.assertEqual(buyer_rems[0].recipient_organization_id, self.buyer_org.id)

    def test_milestone_reminder_deferred_when_payment_in_flight(self) -> None:
        version = self._create_version(status="COMMITTED", version_number=1)
        milestone = PaymentMilestone(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=version.id,
            sequence_number=1,
            payer_organization_id=self.buyer_org.id,
            amount=Decimal("5000.00"),
            currency="USD",
            trigger_type="IMMEDIATE",
            due_condition="Upon commitment",
            status="PENDING",
            created_at=self.now,
        )
        self.db.add(milestone)
        self.db.commit()

        reminders = schedule_deal_reminders(self.db, self.deal.id, self.now)
        self.db.commit()
        rem = reminders[0]

        # Buyer initiates payment intent (status: CREATED / AUTHORIZED)
        intent = PaymentIntent(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=version.id,
            payment_milestone_id=milestone.id,
            payer_organization_id=self.buyer_org.id,
            seller_organization_id=self.seller_org.id,
            authorized_by=self.buyer_user.id,
            amount=milestone.amount,
            currency="USD",
            status="AUTHORIZED",
            provider="OFFLINE_DEMO",
            execution_mode="OFFLINE_DEMO",
            reconciliation_source="OFFLINE_DEMO",
            idempotency_key=str(uuid4()),
            created_at=self.now,
        )
        self.db.add(intent)
        self.db.commit()

        # Dispatch at due time: should defer attempt instead of delivering reminder
        due_time = rem.due_at + timedelta(seconds=1)
        dispatched = dispatch_due_reminders(self.db, due_time)
        self.db.commit()

        self.assertEqual(len(dispatched), 1)
        repo = SqlAlchemyReminderRepository(self.db)
        updated = repo.get(rem.id)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, ReminderStatus.SCHEDULED)
        self.assertIsNotNone(updated.next_attempt_at)
        self.assertEqual(updated.next_attempt_at, due_time + timedelta(hours=6))

    def test_routing_policy_removal_suppresses_approver_reminder(self) -> None:
        self._create_version(status="PENDING_APPROVAL", version_number=2)
        policy = OrganizationApprovalRoutingPolicy(
            organization_id=self.buyer_org.id,
            mode="SEQUENTIAL",
            approver_user_ids=[str(self.approver_user.id)],
            version=1,
            created_at=self.now,
        )
        self.db.add(policy)
        self.db.commit()

        reminders = schedule_deal_reminders(self.db, self.deal.id, self.now)
        self.db.commit()
        self.assertEqual(len(reminders), 1)
        rem = reminders[0]

        # Policy changes: approver is removed from approver_user_ids
        policy.approver_user_ids = []
        policy.version = 2
        self.db.commit()

        # Rescheduling suppresses the active reminder with RECIPIENT_REVOKED
        schedule_deal_reminders(self.db, self.deal.id, self.now)
        self.db.commit()

        updated = self.db.get(DealReminderModel, rem.id)
        self.assertEqual(updated.status, ReminderStatus.SUPPRESSED.value)
        self.assertEqual(updated.suppression_reason, SuppressionReason.RECIPIENT_REVOKED.value)

    def test_dispatch_scoped_to_deal_id(self) -> None:
        # Create second deal
        deal2 = Deal(
            id=uuid4(),
            buyer_organization_id=self.buyer_org.id,
            seller_organization_id=self.seller_org.id,
            status="AGREED",
            version=1,
            created_at=self.now,
        )
        self.db.add(deal2)
        self.db.commit()

        # Create due reminders for both deals
        repo = SqlAlchemyReminderRepository(self.db)
        from syncally.domain.reminders.reminder import DealReminder
        r1 = DealReminder(
            id=uuid4(),
            deal_id=self.deal.id,
            scope=ReminderScope.CASE,
            reference_id=uuid4(),
            recipient_organization_id=self.buyer_org.id,
            recipient_user_id=None,
            status=ReminderStatus.SCHEDULED,
            scheduled_for=self.now - timedelta(days=3),
            due_at=self.now - timedelta(days=1),
        )
        r2 = DealReminder(
            id=uuid4(),
            deal_id=deal2.id,
            scope=ReminderScope.CASE,
            reference_id=uuid4(),
            recipient_organization_id=self.buyer_org.id,
            recipient_user_id=None,
            status=ReminderStatus.SCHEDULED,
            scheduled_for=self.now - timedelta(days=3),
            due_at=self.now - timedelta(days=1),
        )
        repo.save(r1)
        repo.save(r2)
        self.db.commit()

        # Dispatch scoped only to deal1
        dispatched = dispatch_due_reminders(self.db, self.now, deal_id=self.deal.id)
        self.db.commit()

        dispatched_ids = [d.id for d in dispatched]
        self.assertIn(r1.id, dispatched_ids)
        self.assertNotIn(r2.id, dispatched_ids)


if __name__ == "__main__":
    unittest.main()
