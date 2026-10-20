"""Tests for authoritative workflow-state refresh and its Temporal activity."""

from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from temporalio.exceptions import ApplicationError

from syncally.application.workflow_notifications import (
    DealWorkflowNotification,
    NotificationKind,
)
from syncally.application.workflow_state import (
    TERMINAL_DEAL_STATUSES,
    WorkflowDealNotFound,
    load_deal_workflow_state,
)
from syncally.domain.agreements.agreement import Agreement
from syncally.domain.agreements.trade_terms import (
    PaymentTerm,
    ShipmentTerm,
    TradeLineItem,
    TradeTerms,
)
from syncally.domain.deals.deal import Deal, DealStatus
from syncally.domain.shared.identifiers import (
    AgreementId,
    AgreementVersionId,
    DealId,
    OrganizationId,
)
from syncally.domain.shared.money import Money
from syncally.infrastructure.models import Base, Organization
from syncally.infrastructure.models import Deal as DealRow
from syncally.workflows.activities import RefreshDealStateActivity
from syncally.workflows.deal import DealWorkflowInput


def _domain_deal(deal_id: UUID, status: DealStatus) -> Deal:
    return Deal(
        id=DealId(deal_id),
        buyer_organization_id=OrganizationId(uuid4()),
        seller_organization_id=OrganizationId(uuid4()),
        created_at=datetime.now(UTC),
        status=status,
    )


@dataclass
class _FakeDealRepository:
    deal: Deal | None

    def get(self, deal_id: UUID) -> Deal | None:
        return self.deal


@dataclass
class _FakeAgreementRepository:
    agreements: dict[UUID, Agreement]

    def get_current(self, deal_id: UUID) -> Agreement | None:
        return self.agreements.get(deal_id)


def _agreement(deal_id: UUID, version_number: int) -> Agreement:
    buyer_id = OrganizationId(uuid4())
    seller_id = OrganizationId(uuid4())
    terms = TradeTerms(
        buyer_id=buyer_id,
        seller_id=seller_id,
        line_items=(
            TradeLineItem("Desk", Decimal("1"), "each", Money(Decimal("10"), "USD")),
        ),
        shipments=(ShipmentTerm(Decimal("1"), "Toronto", date(2030, 1, 1)),),
        payment_terms=(
            PaymentTerm(
                Money(Decimal("10"), "USD"),
                "seller_invoice",
                "when seller invoices",
            ),
        ),
        delivery_location="Toronto",
    )
    return Agreement(
        id=AgreementId(deal_id),
        version_id=AgreementVersionId(uuid4()),
        deal_id=DealId(deal_id),
        version_number=version_number,
        terms=terms,
        created_at=datetime.now(UTC),
    )


class WorkflowStateApplicationTests(unittest.TestCase):
    def test_terminal_and_active_deal_statuses(self) -> None:
        deal_id = uuid4()
        self.assertEqual(
            TERMINAL_DEAL_STATUSES,
            {DealStatus.COMPLETED, DealStatus.CANCELLED, DealStatus.EXPIRED},
        )
        for status in TERMINAL_DEAL_STATUSES:
            state = load_deal_workflow_state(
                deal_id,
                _FakeDealRepository(_domain_deal(deal_id, status)),
                _FakeAgreementRepository({}),
            )
            self.assertTrue(state.is_terminal)

        for status in (DealStatus.DRAFT, DealStatus.PENDING_APPROVALS, DealStatus.AGREED):
            state = load_deal_workflow_state(
                deal_id,
                _FakeDealRepository(_domain_deal(deal_id, status)),
                _FakeAgreementRepository({}),
            )
            self.assertFalse(state.is_terminal)

    def test_loads_current_agreement_instead_of_an_older_version(self) -> None:
        deal_id = uuid4()
        current = _agreement(deal_id, version_number=2)
        state = load_deal_workflow_state(
            deal_id,
            _FakeDealRepository(_domain_deal(deal_id, DealStatus.PENDING_APPROVALS)),
            _FakeAgreementRepository({deal_id: current}),
        )
        self.assertIs(state.current_agreement, current)
        self.assertEqual(state.current_agreement.version_number, 2)

    def test_missing_deal_is_a_business_rejection(self) -> None:
        with self.assertRaises(WorkflowDealNotFound):
            load_deal_workflow_state(
                uuid4(),
                _FakeDealRepository(None),
                _FakeAgreementRepository({}),
            )


class RefreshDealStateActivityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.buyer_id = uuid4()
        self.seller_id = uuid4()
        self.deal_id = uuid4()
        with Session(self.engine) as db:
            db.add_all(
                [
                    Organization(
                        id=self.buyer_id, legal_name="Buyer Co", country_code="US"
                    ),
                    Organization(
                        id=self.seller_id, legal_name="Seller Co", country_code="CA"
                    ),
                    DealRow(
                        id=self.deal_id,
                        buyer_organization_id=self.buyer_id,
                        seller_organization_id=self.seller_id,
                        status=DealStatus.DRAFT.value,
                        version=0,
                    ),
                ]
            )
            db.commit()
        self.activity = RefreshDealStateActivity(lambda: Session(self.engine))
        self.notification = DealWorkflowNotification(
            notification_id=str(uuid4()),
            record_id=str(uuid4()),
            kind=NotificationKind.AGREEMENT_APPROVAL_RECORDED,
        )

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _input(self, *, agreement_version_id: str | None = None) -> DealWorkflowInput:
        return DealWorkflowInput(
            deal_id=str(self.deal_id),
            agreement_version_id=agreement_version_id or str(uuid4()),
        )

    def test_reloads_latest_persisted_status_not_workflow_input(self) -> None:
        stale_version_id = str(uuid4())
        workflow_input = self._input(agreement_version_id=stale_version_id)

        self.assertFalse(self.activity.refresh_deal_state(workflow_input, self.notification))

        with Session(self.engine) as db:
            db.execute(
                update(DealRow)
                .where(DealRow.id == self.deal_id)
                .values(status=DealStatus.COMPLETED.value)
            )
            db.commit()

        self.assertTrue(self.activity.refresh_deal_state(workflow_input, self.notification))

    def test_accepts_runtime_decoded_input_dict(self) -> None:
        self.assertFalse(
            self.activity.refresh_deal_state(
                {"deal_id": str(self.deal_id)}, self.notification
            )
        )

    def test_session_is_closed_after_refresh(self) -> None:
        sessions: list[Session] = []

        def factory() -> Session:
            session = Session(self.engine)
            sessions.append(session)
            return session

        RefreshDealStateActivity(factory).refresh_deal_state(
            self._input(), self.notification
        )

        self.assertEqual(len(sessions), 1)
        self.assertFalse(sessions[0].in_transaction())

    def test_missing_deal_is_non_retryable(self) -> None:
        missing_input = DealWorkflowInput(
            deal_id=str(uuid4()),
            agreement_version_id=None,
        )

        with self.assertRaises(ApplicationError) as raised:
            self.activity.refresh_deal_state(missing_input, self.notification)

        self.assertEqual(raised.exception.type, "BusinessRejectionError")
        self.assertTrue(raised.exception.non_retryable)

    def test_malformed_input_is_non_retryable(self) -> None:
        with self.assertRaises(ApplicationError) as raised:
            self.activity.refresh_deal_state(
                {"deal_id": "not-a-uuid"}, self.notification
            )

        self.assertEqual(raised.exception.type, "ValidationError")
        self.assertTrue(raised.exception.non_retryable)

    def test_transient_database_error_is_left_for_retry(self) -> None:
        class DatabaseUnavailable(RuntimeError):
            pass

        def factory() -> Session:
            raise DatabaseUnavailable("temporary connection failure")

        with self.assertRaises(DatabaseUnavailable):
            RefreshDealStateActivity(factory).refresh_deal_state(
                self._input(), self.notification
            )


if __name__ == "__main__":
    unittest.main()
