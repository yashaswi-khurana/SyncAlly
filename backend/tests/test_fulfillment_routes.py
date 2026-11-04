"""Focused fulfillment route contracts without importing unrelated API routers."""

import unittest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from test_domain_fixes import build_terms

from syncally.api.fulfillment import (
    RecordFulfillmentRequest,
    read_fulfillment_route,
    record_fulfillment_route,
)
from syncally.application.identity import ActorContext
from syncally.application.payments import PAYPAL_WEBHOOK_RECONCILIATION_EVENT_TYPE
from syncally.domain.agreements.obligations import build_obligations, build_payment_milestones
from syncally.domain.payments.intent import (
    VerifiedProviderPaymentState,
    VerifiedProviderPaymentStatus,
)
from syncally.domain.shared.identifiers import OrganizationId
from syncally.domain.shared.money import Money
from syncally.infrastructure.models import (
    AgreementVersion,
    AuditEvent,
    Base,
    Deal,
    FulfillmentEvent,
    NegotiationSession,
    Obligation,
    Organization,
    OrganizationMember,
    OutboxEvent,
    PaymentIntent,
    PaymentMilestone,
    Proposal,
    User,
    WebhookEvent,
)
from syncally.infrastructure.repositories.deals import SqlAlchemyDealRepository
from syncally.infrastructure.repositories.fulfillment import SqlAlchemyFulfillmentRepository
from syncally.infrastructure.repositories.payment_processing import (
    SqlAlchemyPaymentProcessingRepository,
)


class FulfillmentRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self._seed()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _seed(self) -> None:
        self.buyer = Organization(legal_name="Buyer Co", country_code="US")
        self.seller = Organization(legal_name="Seller Co", country_code="CA")
        self.buyer_user = User(email="buyer@example.com", display_name="Buyer")
        self.seller_user = User(email="seller@example.com", display_name="Seller")
        self.db.add_all([self.buyer, self.seller, self.buyer_user, self.seller_user])
        self.db.flush()
        self.db.add_all(
            [
                OrganizationMember(
                    user_id=self.buyer_user.id,
                    organization_id=self.buyer.id,
                    status="ACTIVE",
                    role="ADMIN",
                    capabilities=["FULFILLMENT"],
                ),
                OrganizationMember(
                    user_id=self.seller_user.id,
                    organization_id=self.seller.id,
                    status="ACTIVE",
                    role="ADMIN",
                    capabilities=["FULFILLMENT"],
                ),
            ]
        )
        self.deal = Deal(
            buyer_organization_id=self.buyer.id,
            seller_organization_id=self.seller.id,
            status="AGREED",
            version=1,
        )
        self.db.add(self.deal)
        self.db.flush()
        self.terms = build_terms(
            buyer_id=OrganizationId(self.buyer.id),
            seller_id=OrganizationId(self.seller.id),
        )
        negotiation = NegotiationSession(deal_id=self.deal.id, max_rounds=5)
        self.db.add(negotiation)
        self.db.flush()
        proposal = Proposal(
            deal_id=self.deal.id,
            negotiation_session_id=negotiation.id,
            proposal_number=1,
            author_organization_id=self.buyer.id,
            terms_json=self.terms.to_storage_dict(),
            terms_hash=self.terms.terms_hash,
            status="SUBMITTED",
        )
        self.db.add(proposal)
        self.db.flush()
        self.agreement = AgreementVersion(
            deal_id=self.deal.id,
            proposal_id=proposal.id,
            version_number=1,
            canonical_terms_json=self.terms.to_storage_dict(),
            terms_hash=self.terms.terms_hash,
            status="COMMITTED",
            created_by=self.buyer_user.id,
            committed_at=datetime.now(UTC),
        )
        self.db.add(self.agreement)
        self.db.flush()
        self.deal.current_agreement_version_id = self.agreement.id
        for draft in build_obligations(self.terms):
            self.db.add(
                Obligation(
                    deal_id=self.deal.id,
                    agreement_version_id=self.agreement.id,
                    obligation_type=draft.obligation_type,
                    owner_organization_id=draft.owner_organization_id,
                    counterparty_organization_id=draft.counterparty_organization_id,
                    due_condition=draft.due_condition,
                    due_date=draft.due_date,
                    source_terms_reference=draft.source_terms_reference,
                    status="PENDING",
                )
            )
        for draft in build_payment_milestones(self.terms):
            self.db.add(
                PaymentMilestone(
                    deal_id=self.deal.id,
                    agreement_version_id=self.agreement.id,
                    sequence_number=draft.sequence_number,
                    payer_organization_id=draft.payer_organization_id,
                    amount=draft.amount.amount,
                    currency=draft.amount.currency,
                    trigger_type=draft.trigger_type,
                    due_condition=draft.due_condition,
                    status="PENDING",
                )
            )
        self.db.commit()
        self.deal_repository = SqlAlchemyDealRepository(self.db)
        self.fulfillment_repository = SqlAlchemyFulfillmentRepository(self.db)
        self.buyer_actor = ActorContext(
            self.buyer_user.id, frozenset({self.buyer.id})
        )
        self.seller_actor = ActorContext(
            self.seller_user.id, frozenset({self.seller.id})
        )

    def _payload(
        self, stage: str, quantity: str, version: int, key: str | None = None
    ) -> RecordFulfillmentRequest:
        obligation = self.db.scalar(
            select(Obligation).where(
                Obligation.deal_id == self.deal.id,
                Obligation.agreement_version_id == self.agreement.id,
                Obligation.obligation_type == "DELIVERY",
            )
        )
        assert obligation is not None
        return RecordFulfillmentRequest(
            agreement_version_id=self.agreement.id,
            terms_hash=self.agreement.terms_hash,
            obligation_id=obligation.id,
            organization_id=self.seller.id if stage == "SHIPPED" else self.buyer.id,
            event_type=stage,
            quantity=quantity,
            expected_version=version,
            idempotency_key=key or str(uuid4()),
        )

    def _record(self, actor: ActorContext, request: RecordFulfillmentRequest):
        return record_fulfillment_route(
            self.deal.id,
            request,
            actor,
            self.deal_repository,
            self.fulfillment_repository,
            self.db,
        )

    def _add_paid_intent(self) -> None:
        milestone = self.db.scalar(
            select(PaymentMilestone).where(
                PaymentMilestone.deal_id == self.deal.id,
                PaymentMilestone.agreement_version_id == self.agreement.id,
            )
        )
        assert milestone is not None
        self.db.add(
            PaymentIntent(
                deal_id=self.deal.id,
                agreement_version_id=self.agreement.id,
                payment_milestone_id=milestone.id,
                seller_organization_id=self.seller.id,
                payer_organization_id=self.buyer.id,
                authorized_by=self.seller_user.id,
                amount=milestone.amount,
                currency=milestone.currency,
                status="PAID",
                provider="OFFLINE_DEMO",
                execution_mode="OFFLINE_DEMO",
                reconciliation_source="OFFLINE_DEMO",
                idempotency_key=str(uuid4()),
                reconciled_amount=milestone.amount,
                last_reconciled_at=datetime.now(UTC),
            )
        )
        self.db.commit()

    def test_fulfillment_is_idempotent_and_completes_only_with_reconciled_payment(self) -> None:
        snapshot = read_fulfillment_route(
            self.deal.id, self.seller_actor, self.deal_repository, self.fulfillment_repository
        )
        self.assertEqual(snapshot.state, "EMPTY")
        self.assertEqual(snapshot.planned_quantity, "1")

        shipped = self._payload("SHIPPED", "1", 0, "ship-1")
        first = self._record(self.seller_actor, shipped)
        replay = self._record(self.seller_actor, shipped)
        self.assertEqual(first.id, replay.id)
        self.assertEqual(first.source_type, "USER_ATTESTATION")
        with self.assertRaises(HTTPException) as reused_key:
            self._record(
                self.seller_actor,
                self._payload("SHIPPED", "0.5", 1, "ship-1"),
            )
        self.assertEqual(reused_key.exception.status_code, 409)
        self.assertEqual(self.deal.status, "AGREED")

        self._add_paid_intent()
        observed = self._record(self.buyer_actor, self._payload("OBSERVED", "1", 1))
        self.assertEqual(observed.event_type.value, "OBSERVED")
        self.assertEqual(self.deal.status, "AGREED")
        confirmed = self._record(self.buyer_actor, self._payload("CONFIRMED", "1", 2))

        self.assertEqual(confirmed.event_type.value, "CONFIRMED")
        self.assertEqual(self.deal.status, "COMPLETED")
        self.assertIsNotNone(
            self.db.scalar(
                select(AuditEvent).where(
                    AuditEvent.aggregate_id == self.deal.id,
                    AuditEvent.event_type == "DEAL_COMPLETED",
                )
            )
        )
        notices = list(
            self.db.scalars(
                select(OutboxEvent).where(
                    OutboxEvent.aggregate_id == self.deal.id,
                    OutboxEvent.event_type == "DEAL_NOTIFICATION",
                )
            )
        )
        self.assertTrue(any(notice.payload["kind"] == "DEAL_COMPLETED" for notice in notices))

    def test_partial_delivery_does_not_complete_and_stage_quantities_are_enforced(self) -> None:
        shipped = self._record(
            self.seller_actor, self._payload("SHIPPED", "0.5", 0, "ship-partial")
        )
        self.assertEqual(shipped.version, 1)
        with self.assertRaises(HTTPException) as seller_observation:
            self._record(self.seller_actor, self._payload("OBSERVED", "0.5", 1))
        self.assertEqual(seller_observation.exception.status_code, 403)
        with self.assertRaises(HTTPException) as confirmed_first:
            self._record(self.buyer_actor, self._payload("CONFIRMED", "0.5", 1))
        self.assertEqual(confirmed_first.exception.status_code, 422)
        with self.assertRaises(HTTPException) as too_much_observed:
            self._record(self.buyer_actor, self._payload("OBSERVED", "0.6", 1))
        self.assertEqual(too_much_observed.exception.status_code, 422)

        self._record(self.buyer_actor, self._payload("OBSERVED", "0.5", 1))
        self._record(self.buyer_actor, self._payload("CONFIRMED", "0.5", 2))
        self.assertEqual(self.deal.status, "AGREED")

    def test_saved_events_are_stale_when_the_current_agreement_is_not_committed(self) -> None:
        self._record(
            self.seller_actor, self._payload("SHIPPED", "0.5", 0, "ship-stale-terms")
        )
        self.agreement.status = "SUPERSEDED"
        self.deal.current_agreement_version_id = None
        self.db.commit()

        snapshot = read_fulfillment_route(
            self.deal.id, self.buyer_actor, self.deal_repository, self.fulfillment_repository
        )

        self.assertEqual(snapshot.state, "STALE")
        self.assertEqual(len(snapshot.events), 1)

    def test_payment_reconciliation_completes_a_fully_delivered_deal_atomically(self) -> None:
        self._record(self.seller_actor, self._payload("SHIPPED", "1", 0))
        self._record(self.buyer_actor, self._payload("OBSERVED", "1", 1))
        self._record(self.buyer_actor, self._payload("CONFIRMED", "1", 2))
        self.assertEqual(self.deal.status, "AGREED")

        milestone = self.db.scalar(
            select(PaymentMilestone).where(PaymentMilestone.agreement_version_id == self.agreement.id)
        )
        assert milestone is not None
        intent = PaymentIntent(
            id=uuid4(),
            deal_id=self.deal.id,
            agreement_version_id=self.agreement.id,
            payment_milestone_id=milestone.id,
            seller_organization_id=self.seller.id,
            payer_organization_id=self.buyer.id,
            authorized_by=self.seller_user.id,
            amount=milestone.amount,
            currency=milestone.currency,
            status="SENT",
            provider="PAYPAL",
            execution_mode="PAYPAL_SANDBOX",
            provider_invoice_id="paypal-invoice-1",
            idempotency_key=str(uuid4()),
            version=1,
        )
        webhook_id, outbox_id = uuid4(), uuid4()
        lease_until = datetime.now(UTC) + timedelta(minutes=5)
        webhook = WebhookEvent(
            id=webhook_id,
            provider="PAYPAL",
            provider_event_id="WH-fulfillment-1",
            event_type=PAYPAL_WEBHOOK_RECONCILIATION_EVENT_TYPE,
            raw_payload={"id": "WH-fulfillment-1"},
            payment_intent_id=intent.id,
            processed=False,
        )
        outbox = OutboxEvent(
            id=outbox_id,
            aggregate_type="payment_intent",
            aggregate_id=intent.id,
            event_type=PAYPAL_WEBHOOK_RECONCILIATION_EVENT_TYPE,
            payload={"payment_intent_id": str(intent.id), "webhook_event_id": str(webhook.id)},
            status="PROCESSING",
            next_attempt_at=lease_until,
        )
        self.db.add_all([intent, webhook, outbox])
        self.db.commit()
        repository = SqlAlchemyPaymentProcessingRepository(
            lambda: Session(self.engine, expire_on_commit=False)
        )

        repository.record_reconciliation(
            intent.id,
            VerifiedProviderPaymentState(
                status=VerifiedProviderPaymentStatus.PAID,
                paid_amount=Money(milestone.amount, milestone.currency),
                provider_reference=intent.provider_invoice_id,
            ),
            outbox_event_id=outbox.id,
            webhook_event_id=webhook.id,
            lease_until=lease_until,
        )

        self.db.expire_all()
        self.assertEqual(self.deal.status, "COMPLETED")
        self.assertIsNotNone(
            self.db.scalar(
                select(AuditEvent).where(
                    AuditEvent.aggregate_id == self.deal.id,
                    AuditEvent.event_type == "DEAL_COMPLETED",
                )
            )
        )

    def test_fresh_capability_and_version_conflicts_are_enforced(self) -> None:
        member = self.db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == self.seller.id,
                OrganizationMember.user_id == self.seller_user.id,
            )
        )
        assert member is not None
        member.capabilities = []
        self.db.commit()
        with self.assertRaises(HTTPException) as denied:
            self._record(self.seller_actor, self._payload("SHIPPED", "1", 0))
        self.assertEqual(denied.exception.status_code, 403)
        self.assertEqual(
            self.db.scalar(
                select(FulfillmentEvent).where(FulfillmentEvent.deal_id == self.deal.id)
            ),
            None,
        )

        member.capabilities = ["FULFILLMENT"]
        self.db.commit()
        self._record(self.seller_actor, self._payload("SHIPPED", "0.5", 0))
        with self.assertRaises(HTTPException) as stale:
            self._record(self.seller_actor, self._payload("SHIPPED", "0.1", 0))
        self.assertEqual(stale.exception.status_code, 409)

    def test_request_rejects_float_and_unbounded_decimal_quantities(self) -> None:
        payload = self._payload("SHIPPED", "1", 0).model_dump()
        for quantity in (1.0, "NaN", "0", "0.0000000000000000001"):
            with self.subTest(quantity=quantity), self.assertRaises(ValidationError):
                RecordFulfillmentRequest.model_validate({**payload, "quantity": quantity})


if __name__ == "__main__":
    unittest.main()
