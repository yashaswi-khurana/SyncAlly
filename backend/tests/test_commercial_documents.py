from datetime import UTC, datetime
from unittest import TestCase
from uuid import uuid4

from test_domain_fixes import build_terms

from syncally.application.deals import DealNotFound
from syncally.application.documents import (
    AgreementNotCommitted,
    generate_commercial_document_draft,
)
from syncally.application.identity import ActorContext
from syncally.domain.agreements.agreement import (
    Agreement,
    Approval,
    ApprovalDecision,
)
from syncally.domain.deals.deal import Deal
from syncally.domain.shared.identifiers import (
    AgreementId,
    AgreementVersionId,
    DealId,
    OrganizationId,
    UserId,
)


class FakeDealRepository:
    def __init__(self, deal: Deal) -> None:
        self.deal = deal

    def get_for_participant(self, deal_id, user_id):
        return self.deal if deal_id == self.deal.id else None


class FakeAgreementRepository:
    def __init__(self, agreement: Agreement) -> None:
        self.agreement = agreement

    def get_current(self, deal_id):
        return self.agreement if deal_id == self.agreement.deal_id else None


class CommercialDocumentDraftTests(TestCase):
    def setUp(self) -> None:
        now = datetime(2030, 1, 1, tzinfo=UTC)
        buyer_id = OrganizationId(uuid4())
        seller_id = OrganizationId(uuid4())
        self.deal_id = DealId(uuid4())
        self.terms = build_terms(buyer_id=buyer_id, seller_id=seller_id)
        self.deal = Deal(
            id=self.deal_id,
            buyer_organization_id=buyer_id,
            seller_organization_id=seller_id,
            created_at=now,
        )
        self.agreement = Agreement(
            id=AgreementId(uuid4()),
            version_id=AgreementVersionId(uuid4()),
            deal_id=self.deal_id,
            version_number=2,
            terms=self.terms,
            created_at=now,
        )
        for organization_id in (buyer_id, seller_id):
            self.agreement.record_approval(
                Approval(
                    organization_id=organization_id,
                    user_id=UserId(uuid4()),
                    decision=ApprovalDecision.APPROVE,
                    terms_hash=self.terms.terms_hash,
                    created_at=now,
                )
            )
        self.actor = ActorContext(uuid4(), frozenset({buyer_id}))
        self.deal_repository = FakeDealRepository(self.deal)
        self.agreement_repository = FakeAgreementRepository(self.agreement)

    def test_generates_draft_from_committed_terms_with_source_version(self) -> None:
        self.agreement.commit(self.terms.terms_hash, datetime(2030, 1, 2, tzinfo=UTC))

        draft = generate_commercial_document_draft(
            self.actor,
            self.deal_id,
            self.deal_repository,
            self.agreement_repository,
        )

        self.assertEqual(draft.agreement_version_id, self.agreement.version_id)
        self.assertEqual(draft.agreement_version_number, 2)
        self.assertEqual(draft.terms_hash, self.terms.terms_hash)
        self.assertIn("DRAFT - FOR REVIEW ONLY", draft.content)
        self.assertIn(f"Agreement version: 2 ({self.agreement.version_id})", draft.content)
        self.assertIn("Item: Desk", draft.content)
        self.assertIn("Unit price: 10 USD", draft.content)
        self.assertIn("Line total: 10 USD", draft.content)
        self.assertIn("Delivery destination: Toronto", draft.content)
        self.assertIn("Target delivery date: 2030-01-01", draft.content)
        self.assertIn("Payment amount: 10 USD", draft.content)
        self.assertIn("Payment due condition: when seller invoices", draft.content)
        self.assertIn("SKU: Not specified in committed terms", draft.content)
        self.assertIn("Incoterm: Not specified in committed terms", draft.content)
        self.assertIn("Buyer legal/business name: Not specified in committed terms", draft.content)
        self.assertIn("Cancellation terms: Not specified in committed terms", draft.content)
        self.assertIn(
            "Taxes, freight, customs classification, and other fees: Not specified in committed terms",
            draft.content,
        )
        self.assertIn("does not certify legal, tax, or customs compliance", draft.content)

    def test_editing_rendered_draft_does_not_mutate_agreement(self) -> None:
        self.agreement.commit(self.terms.terms_hash, datetime(2030, 1, 2, tzinfo=UTC))
        original_terms = self.agreement.terms.canonical_json()
        draft = generate_commercial_document_draft(
            self.actor,
            self.deal_id,
            self.deal_repository,
            self.agreement_repository,
        )

        edited_draft = draft.content.replace("Desk", "Edited desk")

        self.assertIn("Edited desk", edited_draft)
        self.assertEqual(self.agreement.terms.canonical_json(), original_terms)

    def test_pending_agreement_cannot_generate_draft(self) -> None:
        with self.assertRaises(AgreementNotCommitted):
            generate_commercial_document_draft(
                self.actor,
                self.deal_id,
                self.deal_repository,
                self.agreement_repository,
            )

    def test_nonparticipant_cannot_generate_draft(self) -> None:
        self.agreement.commit(self.terms.terms_hash, datetime(2030, 1, 2, tzinfo=UTC))
        actor = ActorContext(uuid4(), frozenset({OrganizationId(uuid4())}))

        with self.assertRaises(DealNotFound):
            generate_commercial_document_draft(
                actor,
                self.deal_id,
                self.deal_repository,
                self.agreement_repository,
            )
