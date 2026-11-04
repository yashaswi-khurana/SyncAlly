"""Domain-level organization, membership, and deal invariants."""

import subprocess
import sys
import unittest
from datetime import UTC, date, datetime
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
    ContactVisibility,
    Organization,
    OrganizationContact,
    OrganizationMember,
    OrganizationMemberRole,
    OrganizationMemberStatus,
    OrganizationProfile,
    OrganizationStatus,
    OrganizationVerificationStatus,
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
            shipments=(ShipmentTerm(Decimal("1"), "Toronto", date(2030, 1, 1)),),
            payment_terms=(
                PaymentTerm(Money(Decimal("10"), "USD"), "seller_invoice", "when seller invoices"),
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
        deal.mark_agreed(agreement.version_id)

        self.assertEqual(agreement.status, AgreementStatus.COMMITTED)
        self.assertEqual(deal.status, DealStatus.AGREED)

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

    def test_deal_completes_execution_and_increments_version_once(self) -> None:
        deal = make_deal()
        deal.start_negotiation()
        agreement_version_id = AgreementVersionId(uuid4())
        deal.request_approval(agreement_version_id)
        deal.mark_agreed(agreement_version_id)
        deal.begin_execution()
        version_before_completion = deal.version

        deal.complete(fulfillment_complete=True, payments_reconciled=True)

        self.assertEqual(deal.status, DealStatus.COMPLETED)
        self.assertEqual(deal.version, version_before_completion + 1)

    def test_deal_completion_rejects_other_states_without_mutation(self) -> None:
        for status in DealStatus:
            if status is DealStatus.EXECUTING:
                continue
            with self.subTest(status=status):
                deal = Deal(
                    id=DealId(uuid4()),
                    buyer_organization_id=OrganizationId(uuid4()),
                    seller_organization_id=OrganizationId(uuid4()),
                    created_at=datetime.now(UTC),
                    status=status,
                    version=3,
                )

                with self.assertRaises(InvalidTransition):
                    deal.complete(fulfillment_complete=True, payments_reconciled=True)

                self.assertEqual(deal.status, status)
                self.assertEqual(deal.version, 3)

    def test_deal_completion_requires_fulfillment_and_reconciled_payments(self) -> None:
        for fulfillment_complete, payments_reconciled in (
            (False, False),
            (False, True),
            (True, False),
        ):
            with self.subTest(
                fulfillment_complete=fulfillment_complete,
                payments_reconciled=payments_reconciled,
            ):
                deal = make_deal()
                deal.start_negotiation()
                agreement_version_id = AgreementVersionId(uuid4())
                deal.request_approval(agreement_version_id)
                deal.mark_agreed(agreement_version_id)
                deal.begin_execution()
                version_before = deal.version

                with self.assertRaises(InvalidTransition):
                    deal.complete(
                        fulfillment_complete=fulfillment_complete,
                        payments_reconciled=payments_reconciled,
                    )

                self.assertEqual(deal.status, DealStatus.EXECUTING)
                self.assertEqual(deal.version, version_before)


class OrganizationContactDomainTests(unittest.TestCase):
    def test_contact_normalizes_and_defaults(self) -> None:
        contact_id = uuid4()
        contact = OrganizationContact(
            id=contact_id,
            name="  Alice Smith  ",
            purpose="  Commercial Operations  ",
            email=" Alice@Example.COM ",
            phone=" +1-555-0199 ",
        )
        self.assertEqual(contact.name, "Alice Smith")
        self.assertEqual(contact.purpose, "Commercial Operations")
        self.assertEqual(contact.email, "alice@example.com")
        self.assertEqual(contact.phone, "+1-555-0199")
        self.assertEqual(contact.visibility, ContactVisibility.PRIVATE)
        self.assertTrue(contact.consent_obtained)

    def test_contact_requires_consent(self) -> None:
        with self.assertRaises(InvariantViolation):
            OrganizationContact(
                id=uuid4(),
                name="Alice",
                purpose="Sales",
                consent_obtained=False,
                email="alice@example.com",
            )

    def test_contact_requires_name_and_purpose(self) -> None:
        with self.assertRaises(InvariantViolation):
            OrganizationContact(
                id=uuid4(),
                name="   ",
                purpose="Sales",
                email="alice@example.com",
            )
        with self.assertRaises(InvariantViolation):
            OrganizationContact(
                id=uuid4(),
                name="Alice",
                purpose="",
                email="alice@example.com",
            )

    def test_contact_requires_at_least_one_channel(self) -> None:
        with self.assertRaises(InvariantViolation):
            OrganizationContact(
                id=uuid4(),
                name="Alice",
                purpose="Sales",
            )

    def test_contact_validates_email_format(self) -> None:
        with self.assertRaises(InvariantViolation):
            OrganizationContact(
                id=uuid4(),
                name="Alice",
                purpose="Sales",
                email="not-an-email",
            )


class OrganizationProfileDomainTests(unittest.TestCase):
    def test_profile_defaults_and_normalizes(self) -> None:
        org_id = OrganizationId(uuid4())
        profile = OrganizationProfile(
            organization_id=org_id,
            capabilities=[" Freight Forwarding ", "freight forwarding", "Logistics"],
            products=[" Bulk Grain ", "bulk grain"],
            regions=["us", "GB", "us"],
        )
        self.assertEqual(profile.organization_id, org_id)
        self.assertEqual(profile.capabilities, ["Freight Forwarding", "Logistics"])
        self.assertEqual(profile.products, ["Bulk Grain"])
        self.assertEqual(profile.regions, ["US", "GB"])
        self.assertEqual(profile.verification_status, OrganizationVerificationStatus.UNVERIFIED)
        self.assertEqual(profile.version, 1)

    def test_profile_bounds_checks(self) -> None:
        org_id = OrganizationId(uuid4())
        with self.assertRaises(InvariantViolation):
            OrganizationProfile(
                organization_id=org_id,
                capabilities=[f"cap-{i}" for i in range(51)],
            )
        with self.assertRaises(InvariantViolation):
            OrganizationProfile(
                organization_id=org_id,
                capabilities=["x" * 201],
            )
        with self.assertRaises(InvariantViolation):
            OrganizationProfile(
                organization_id=org_id,
                products=[f"prod-{i}" for i in range(51)],
            )
        with self.assertRaises(InvariantViolation):
            OrganizationProfile(
                organization_id=org_id,
                products=["y" * 201],
            )
        with self.assertRaises(InvariantViolation):
            OrganizationProfile(
                organization_id=org_id,
                regions=[f"{chr(65 + i // 26)}{chr(65 + i % 26)}" for i in range(51)],
            )

        # 200 characters is allowed
        valid_profile = OrganizationProfile(
            organization_id=org_id,
            capabilities=["c" * 200],
            products=["p" * 200],
        )
        self.assertEqual(len(valid_profile.capabilities[0]), 200)
        self.assertEqual(len(valid_profile.products[0]), 200)

    def test_profile_invalid_region_rejected(self) -> None:
        org_id = OrganizationId(uuid4())
        for invalid_region in ("USA", "1A", "U", "éU"):
            with self.subTest(invalid_region=invalid_region):
                with self.assertRaises(InvariantViolation):
                    OrganizationProfile(
                        organization_id=org_id,
                        regions=[invalid_region],
                    )

    def test_profile_unique_contact_channels(self) -> None:
        org_id = OrganizationId(uuid4())
        c1 = OrganizationContact(id=uuid4(), name="Alice", purpose="Sales", email="shared@example.com")
        c2 = OrganizationContact(id=uuid4(), name="Bob", purpose="Ops", email="SHARED@example.com")
        with self.assertRaises(InvariantViolation):
            OrganizationProfile(
                organization_id=org_id,
                contacts=[c1, c2],
            )

        c3 = OrganizationContact(id=uuid4(), name="Charlie", purpose="Support", phone="+1-555-0100")
        c4 = OrganizationContact(id=uuid4(), name="Dave", purpose="Billing", phone="+1-555-0100")
        with self.assertRaises(InvariantViolation):
            OrganizationProfile(
                organization_id=org_id,
                contacts=[c3, c4],
            )

    def test_profile_contacts_bounds(self) -> None:
        org_id = OrganizationId(uuid4())
        contacts = [
            OrganizationContact(id=uuid4(), name=f"User {i}", purpose="Test", email=f"user{i}@example.com")
            for i in range(21)
        ]
        with self.assertRaises(InvariantViolation):
            OrganizationProfile(
                organization_id=org_id,
                contacts=contacts,
            )

    def test_profile_immutable_unverified_and_version(self) -> None:
        org_id = OrganizationId(uuid4())
        with self.assertRaises(InvariantViolation):
            OrganizationProfile(
                organization_id=org_id,
                version=0,
            )


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
