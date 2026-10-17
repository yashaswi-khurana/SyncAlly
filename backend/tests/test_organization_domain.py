"""Domain-level organization, membership, and deal invariants."""

import subprocess
import sys
import unittest
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from syncally.domain.agreements.agreement import (
    Agreement,
    AgreementStatus,
    Approval,
    ApprovalDecision,
)
from syncally.domain.agreements.trade_terms import (
    PaymentTerm,
    ShipmentTerm,
    TradeLineItem,
    TradeTerms,
)
from syncally.domain.deals.deal import Deal, DealStatus
from syncally.domain.organizations import (
    Organization,
    OrganizationMember,
    OrganizationMemberRole,
    OrganizationMemberStatus,
    OrganizationStatus,
)
from syncally.domain.shared.errors import InvalidTransition, InvariantViolation
from syncally.domain.shared.identifiers import (
    AgreementId,
    AgreementVersionId,
    DealId,
    OrganizationId,
    UserId,
)
from syncally.domain.shared.money import Money


def make_deal(
    buyer_id: OrganizationId | None = None,
    seller_id: OrganizationId | None = None,
) -> Deal:
    return Deal(
        id=DealId(uuid4()),
        buyer_organization_id=buyer_id or OrganizationId(uuid4()),
        seller_organization_id=seller_id or OrganizationId(uuid4()),
        created_at=datetime.now(UTC),
    )


class OrganizationDomainTests(unittest.TestCase):
    def test_organization_normalizes_country_code_and_defaults_active(self) -> None:
        organization = Organization(
            id=OrganizationId(uuid4()),
            legal_name="Acme Trading",
            country_code="us",
            created_at=datetime.now(UTC),
        )

        self.assertEqual(organization.country_code, "US")
        self.assertEqual(organization.status, OrganizationStatus.ACTIVE)
        self.assertTrue(organization.is_active)

    def test_blank_legal_name_is_rejected(self) -> None:
        with self.assertRaises(InvariantViolation):
            Organization(
                id=OrganizationId(uuid4()),
                legal_name="  ",
                country_code="US",
                created_at=datetime.now(UTC),
            )

    def test_country_code_must_be_two_ascii_letters(self) -> None:
        for country_code in ("U", "USA", "1A", "éU"):
            with self.subTest(country_code=country_code):
                with self.assertRaises(InvariantViolation):
                    Organization(
                        id=OrganizationId(uuid4()),
                        legal_name="Acme Trading",
                        country_code=country_code,
                        created_at=datetime.now(UTC),
                    )


class OrganizationMemberDomainTests(unittest.TestCase):
    def test_membership_defaults_to_active_member(self) -> None:
        membership = OrganizationMember(
            organization_id=OrganizationId(uuid4()),
            user_id=UserId(uuid4()),
            created_at=datetime.now(UTC),
        )

        self.assertEqual(membership.role, OrganizationMemberRole.MEMBER)
        self.assertEqual(membership.status, OrganizationMemberStatus.ACTIVE)
        self.assertTrue(membership.is_active)

    def test_inactive_or_revoked_membership_is_not_active(self) -> None:
        for status in (OrganizationMemberStatus.INACTIVE, OrganizationMemberStatus.REVOKED):
            with self.subTest(status=status):
                membership = OrganizationMember(
                    organization_id=OrganizationId(uuid4()),
                    user_id=UserId(uuid4()),
                    created_at=datetime.now(UTC),
                    status=status,
                )

                self.assertFalse(membership.is_active)


class DealDomainTests(unittest.TestCase):
    def test_deal_rejects_same_organization_as_buyer_and_seller(self) -> None:
        organization_id = OrganizationId(uuid4())

        with self.assertRaises(InvariantViolation):
            make_deal(buyer_id=organization_id, seller_id=organization_id)

    def test_deal_rejects_transition_from_draft_directly_to_execution(self) -> None:
        deal = make_deal()

        with self.assertRaises(InvalidTransition):
            deal.begin_execution()

        self.assertEqual(deal.status, DealStatus.DRAFT)
        self.assertEqual(deal.version, 0)

    def test_deal_status_cannot_be_changed_outside_domain_methods(self) -> None:
        deal = make_deal()

        with self.assertRaises(AttributeError):
            deal.status = DealStatus.EXECUTING

        self.assertEqual(deal.status, DealStatus.DRAFT)

    def test_deal_constructor_preserves_status_keyword_and_positional_arguments(self) -> None:
        keyword_deal = Deal(
            DealId(uuid4()),
            OrganizationId(uuid4()),
            OrganizationId(uuid4()),
            datetime.now(UTC),
            status=DealStatus.NEGOTIATING,
        )
        positional_deal = Deal(
            DealId(uuid4()),
            OrganizationId(uuid4()),
            OrganizationId(uuid4()),
            datetime.now(UTC),
            DealStatus.NEGOTIATING,
        )
        agreement_version_id = AgreementVersionId(uuid4())
        fully_positional_deal = Deal(
            DealId(uuid4()),
            OrganizationId(uuid4()),
            OrganizationId(uuid4()),
            datetime.now(UTC),
            DealStatus.PENDING_APPROVALS,
            agreement_version_id,
            7,
        )

        self.assertEqual(keyword_deal.status, DealStatus.NEGOTIATING)
        self.assertEqual(positional_deal.status, DealStatus.NEGOTIATING)
        self.assertEqual(fully_positional_deal.status, DealStatus.PENDING_APPROVALS)
        self.assertEqual(fully_positional_deal.current_agreement_version_id, agreement_version_id)
        self.assertEqual(fully_positional_deal.version, 7)
        with self.assertRaises(AttributeError):
            keyword_deal.status = DealStatus.EXECUTING

    def test_cancel_closes_deal_before_agreement_and_increments_version(self) -> None:
        deal = make_deal()
        deal.start_negotiation()
        deal.cancel()

        self.assertEqual(deal.status, DealStatus.CANCELLED)
        self.assertEqual(deal.version, 2)

    def test_expire_closes_deal_before_agreement_and_increments_version(self) -> None:
        deal = make_deal()
        deal.start_negotiation()
        deal.expire()

        self.assertEqual(deal.status, DealStatus.EXPIRED)
        self.assertEqual(deal.version, 2)

    def test_cancel_and_expire_reject_pending_approvals_without_mutation(self) -> None:
        for method_name, expected_status in (
            ("cancel", DealStatus.CANCELLED),
            ("expire", DealStatus.EXPIRED),
        ):
            with self.subTest(method=method_name):
                deal = make_deal()
                deal.start_negotiation()
                agreement_version_id = AgreementVersionId(uuid4())
                deal.request_approval(agreement_version_id)
                before = (deal.status, deal.version, deal.current_agreement_version_id)

                with self.assertRaises(InvalidTransition):
                    getattr(deal, method_name)()

                self.assertEqual(deal.status, before[0])
                self.assertEqual(deal.version, before[1])
                self.assertEqual(deal.current_agreement_version_id, before[2])
                self.assertNotEqual(deal.status, expected_status)

    def test_rejected_closure_keeps_approved_agreement_committable(self) -> None:
        deal = make_deal()
        deal.start_negotiation()
        agreement_version_id = AgreementVersionId(uuid4())
        deal.request_approval(agreement_version_id)
        terms = TradeTerms(
            buyer_id=deal.buyer_organization_id,
            seller_id=deal.seller_organization_id,
            line_items=(
                TradeLineItem("Desk", Decimal("1"), "each", Money(Decimal("10"), "USD")),
            ),
            shipments=(ShipmentTerm(Decimal("1"), "Toronto"),),
            payment_terms=(
                PaymentTerm(Money(Decimal("10"), "USD"), "order", "on order"),
            ),
            delivery_location="Toronto",
        )
        agreement = Agreement(
            id=AgreementId(uuid4()),
            version_id=agreement_version_id,
            deal_id=deal.id,
            version_number=1,
            terms=terms,
            created_at=datetime.now(UTC),
        )
        for organization_id in (deal.buyer_organization_id, deal.seller_organization_id):
            agreement.record_approval(
                Approval(
                    organization_id=organization_id,
                    user_id=UserId(uuid4()),
                    decision=ApprovalDecision.APPROVE,
                    terms_hash=agreement.terms_hash,
                    created_at=datetime.now(UTC),
                )
            )

        with self.assertRaises(InvalidTransition):
            deal.cancel()

        agreement.commit(agreement.terms_hash, datetime.now(UTC))

        self.assertEqual(agreement.status, AgreementStatus.COMMITTED)
        self.assertEqual(deal.status, DealStatus.PENDING_APPROVALS)

    def test_cancel_and_expire_reject_committed_or_executing_deals(self) -> None:
        for method_name in ("cancel", "expire"):
            for status in (DealStatus.AGREED, DealStatus.EXECUTING):
                with self.subTest(method=method_name, status=status):
                    deal = make_deal()
                    deal.start_negotiation()
                    agreement_version_id = AgreementVersionId(uuid4())
                    deal.request_approval(agreement_version_id)
                    deal.mark_agreed(agreement_version_id)
                    if status is DealStatus.EXECUTING:
                        deal.begin_execution()

                    previous_version = deal.version
                    with self.assertRaises(InvalidTransition):
                        getattr(deal, method_name)()

                    self.assertEqual(deal.status, status)
                    self.assertEqual(deal.version, previous_version)

    def test_cancelled_and_expired_deals_cannot_be_transitioned_again(self) -> None:
        for close_method in ("cancel", "expire"):
            for retry_method in ("cancel", "expire"):
                with self.subTest(close=close_method, retry=retry_method):
                    deal = make_deal()
                    getattr(deal, close_method)()
                    previous_status = deal.status
                    with self.assertRaises(InvalidTransition):
                        getattr(deal, retry_method)()
                    self.assertEqual(deal.status, previous_status)
                    self.assertEqual(deal.version, 1)

    def test_agreement_from_an_old_version_cannot_agree_the_deal(self) -> None:
        deal = make_deal()
        deal.start_negotiation()
        current_version = AgreementVersionId(uuid4())
        deal.request_approval(current_version)

        with self.assertRaises(InvariantViolation):
            deal.mark_agreed(AgreementVersionId(uuid4()))

        self.assertEqual(deal.status, DealStatus.PENDING_APPROVALS)
        self.assertEqual(deal.current_agreement_version_id, current_version)
        self.assertEqual(deal.version, 2)

    def test_deal_can_advance_through_approval_into_execution(self) -> None:
        deal = make_deal()

        deal.start_negotiation()
        agreement_version_id = AgreementVersionId(uuid4())
        deal.request_approval(agreement_version_id)
        deal.mark_agreed(agreement_version_id)
        deal.begin_execution()

        self.assertEqual(deal.status, DealStatus.EXECUTING)
        self.assertEqual(deal.version, 4)


class DomainDependencyTests(unittest.TestCase):
    def test_importing_domain_models_does_not_load_framework_or_provider_code(self) -> None:
        script = """
import importlib
import pkgutil
import sys
import syncally.domain

for module in pkgutil.walk_packages(
    syncally.domain.__path__, syncally.domain.__name__ + "."
):
    importlib.import_module(module.name)

forbidden_roots = ("fastapi", "sqlalchemy", "alembic", "psycopg", "temporalio", "paypal")
loaded = sorted(
    name for name in sys.modules
    if any(name == root or name.startswith(root + ".") for root in forbidden_roots)
)
if loaded:
    raise SystemExit("Domain imported forbidden modules: " + ", ".join(loaded))
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
