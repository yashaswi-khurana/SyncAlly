import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from io import BytesIO
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4
from zipfile import ZipFile

from test_domain_fixes import build_terms

from syncally.application.deals import DealNotFound
from syncally.application.documents import (
    AgreementNotCommitted,
    InvalidTradePack,
    TradePackTooLarge,
    generate_commercial_document_draft,
    generate_trade_pack,
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

    def projection(self):
        return {"id": str(self.agreement.version_id), "deal_id": str(self.deal_id),
                "version_number": 2, "terms_hash": self.terms.terms_hash, "status": "COMMITTED",
                "created_at": self.agreement.created_at, "committed_at": self.agreement.created_at,
                "terms": self.terms.to_storage_dict(),
                "approvals": [{"organization_id": str(approval.organization_id),
                    "agreement_version_id": str(self.agreement.version_id), "deal_id": str(self.deal_id),
                    "version_number": 2, "decision": "APPROVE", "terms_hash": self.terms.terms_hash}
                    for approval in self.agreement.approvals.values()]}

    def pack(self, projection, format="zip"):
        return generate_trade_pack(projection, deal_id=self.deal_id, number=2,
            agreement_version_id=self.agreement.version_id, terms_hash=projection["terms_hash"], format=format)

    def test_pack_all_entries_escaped_private_free_deterministic_and_exact_hash(self):
        projection = self.projection()
        display = projection["terms"]
        display["line_items"] *= 2
        display["shipments"] *= 2
        display["payment_terms"] *= 2
        display["line_items"][0]["description"] = '<img src="x" onerror="alert(1)"> & dangerous'
        from syncally.domain.agreements.trade_terms import TradeTerms
        canonical = TradeTerms.from_canonical_json(display).canonical_json().encode()
        projection["terms_hash"] = hashlib.sha256(canonical).hexdigest()
        for approval in projection["approvals"]:
            approval["terms_hash"] = projection["terms_hash"]
        display["_f6_evidence"] = [{"private": "NEVER EXPORT"}]
        before = deepcopy(projection)
        pack = self.pack(projection)
        self.assertEqual(pack.content, self.pack(projection).content)
        self.assertEqual(projection, before)
        with ZipFile(BytesIO(pack.content)) as archive:
            self.assertEqual(archive.namelist(), ["trade-pack.html", "canonical-terms.json", "manifest.json"])
            self.assertEqual(archive.read("canonical-terms.json"), canonical)
            html = archive.read("trade-pack.html").decode()
            self.assertIn("Item 2", html)
            self.assertIn("Shipment 2", html)
            self.assertIn("Payment term 2", html)
            self.assertIn("&lt;img src=&quot;x&quot; onerror=&quot;alert(1)&quot;&gt;", html)
            self.assertNotIn("NEVER EXPORT", str(pack.content))
            self.assertNotIn("_f6_evidence", archive.read("manifest.json").decode())
            self.assertEqual(json.loads(archive.read("manifest.json"))["counts"]["line_items"], 2)
            self.assertIn("Toronto", html)
            self.assertIn("toronto", canonical.decode())
            self.assertIn("Not recorded in committed terms", html)
            self.assertNotIn("<script", html)

    def test_pack_fails_closed_for_unknown_schema_hash_and_approval(self):
        for mutation in (lambda value: value["terms"].update(unknown="x"),
                         lambda value: value["terms"].update(schema_version=2),
                         lambda value: value.update(terms_hash="0" * 64),
                         lambda value: value["approvals"].pop(),
                         lambda value: value["approvals"][0].update(decision="REJECT")):
            with self.subTest(mutation=mutation):
                projection = self.projection()
                mutation(projection)
                with self.assertRaises(InvalidTradePack):
                    self.pack(projection)

    def test_pack_size_limits_and_decimal_expansion(self):
        projection = self.projection()
        projection["terms"]["line_items"][0]["quantity"] = "1e999999999"
        with self.assertRaises(TradePackTooLarge):
            self.pack(projection)
        with patch("syncally.application.documents.MAX_DISPLAY_JSON_BYTES", 10):
            with self.assertRaises(TradePackTooLarge):
                self.pack(self.projection())
        with patch("syncally.application.documents.MAX_TRADE_PACK_BYTES", 3000):
            with self.assertRaises(TradePackTooLarge):
                self.pack(self.projection(), "html")

    def test_pack_cumulative_expansion_rejected_before_domain_formatting(self):
        projection = self.projection()
        projection["terms"]["line_items"] *= 20
        for item in projection["terms"]["line_items"]:
            item["quantity"] = "1e200000"
        with patch("syncally.application.documents.TradeTerms.from_canonical_json") as reconstruct:
            with self.assertRaises(TradePackTooLarge):
                self.pack(projection)
            reconstruct.assert_not_called()

    def test_pack_oversized_display_rejected_before_renderer_or_compression(self):
        projection = self.projection()
        projection["terms"]["line_items"][0]["description"] = "x" * (2 * 1024 * 1024)
        with patch("syncally.application.documents._trade_pack_html") as renderer, patch("syncally.application.documents.ZipFile") as compress:
            with self.assertRaises(TradePackTooLarge):
                self.pack(projection)
            renderer.assert_not_called()
            compress.assert_not_called()
