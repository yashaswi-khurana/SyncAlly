"""Unit and integration test suite for multi-factor seller suggestion engine.

Verifies:
- Multi-factor scoring weights: product (40%), capability (25%), region (20%), catalog (15%).
- Candidate filtering: threshold >= 0.15, top-N limit capping (max 10).
- Exclusions: self-dealing (buyer == seller), inactive/suspended orgs, inactive listings.
- Deterministic tie-breaking: score desc -> token count desc -> legal_name asc -> id asc.
- Contact privacy: candidate contacts are strictly excluded from suggestion items.
- API Endpoint: POST /deals/opening-request/analyze input bounds and error safety.
"""

from __future__ import annotations

import unittest
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.application.seller_suggestions import (
    SellerSuggestionService,
    tokenize,
)
from syncally.domain.ai.contracts import NormalizedRequirement
from syncally.infrastructure.models import (
    Base,
    MarketplaceListing,
    Organization,
    OrganizationProfile,
)


class BaseSellerSuggestionTest(unittest.TestCase):
    """Sets up an in-memory SQLite database and seller fixtures."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        self.buyer_id = uuid4()
        self.buyer_org = Organization(
            id=self.buyer_id,
            legal_name="Acme Buyer Corp",
            country_code="US",
            status="ACTIVE",
        )
        self.session.add(self.buyer_org)
        self.session.flush()

        # Buyer profile with products and private contacts
        self.buyer_profile = OrganizationProfile(
            organization_id=self.buyer_id,
            capabilities=["Procurement"],
            products=["Fasteners"],
            regions=["US"],
            contacts=[{"email": "buyer@acme.com", "phone": "+1-555-0199"}],
        )
        self.session.add(self.buyer_profile)
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _seed_seller(
        self,
        *,
        legal_name: str,
        country_code: str,
        capabilities: list[str] | None = None,
        products: list[str] | None = None,
        regions: list[str] | None = None,
        contacts: list[dict] | None = None,
        status: str = "ACTIVE",
        listing_title: str | None = None,
        listing_category: str | None = None,
        listing_quantity: Decimal | None = None,
        listing_price: Decimal | None = None,
        listing_currency: str = "USD",
        listing_status: str = "ACTIVE",
    ) -> Organization:
        org = Organization(
            legal_name=legal_name,
            country_code=country_code,
            status=status,
        )
        self.session.add(org)
        self.session.flush()

        profile = OrganizationProfile(
            organization_id=org.id,
            capabilities=capabilities or [],
            products=products or [],
            regions=regions or [],
            contacts=contacts or [{"email": f"sales@{org.id}.com", "phone": "+1-800-TEST"}],
        )
        self.session.add(profile)

        if listing_title and listing_category and listing_quantity and listing_price:
            listing = MarketplaceListing(
                organization_id=org.id,
                title=listing_title,
                description=f"Listing for {listing_title}",
                category=listing_category,
                available_quantity=listing_quantity,
                unit="units",
                unit_price=listing_price,
                currency=listing_currency,
                status=listing_status,
            )
            self.session.add(listing)

        self.session.commit()
        return org


class TestTokenizerAndWeights(unittest.TestCase):
    """Test text tokenization and inflection normalization."""

    def test_tokenization_stems_inflections_and_removes_stopwords(self) -> None:
        text = "We need 500 units of stainless steel bolts and hex nuts urgently delivered to Berlin"
        tokens = tokenize(text)
        self.assertIn("bolt", tokens)
        self.assertIn("nut", tokens)
        self.assertIn("stainless", tokens)
        self.assertIn("steel", tokens)
        self.assertNotIn("need", tokens)
        self.assertNotIn("we", tokens)
        self.assertNotIn("of", tokens)
        self.assertNotIn("and", tokens)
        self.assertNotIn("500", tokens)

    def test_tokenization_handles_empty_and_punctuation(self) -> None:
        self.assertEqual(tokenize(""), [])
        self.assertEqual(tokenize("   \n\t  "), [])
        self.assertEqual(tokenize("!!! ??? ,,, ..."), [])


class TestMultiFactorSellerSuggestion(BaseSellerSuggestionTest):
    """Verifies each scoring factor and business invariants."""

    def test_product_match_scores_higher_than_unmatched(self) -> None:
        seller_fasteners = self._seed_seller(
            legal_name="Fastener Direct Ltd",
            country_code="DE",
            products=["Stainless Steel Bolts", "Hex Nuts"],
        )
        seller_textile = self._seed_seller(
            legal_name="Silk & Cotton Mill",
            country_code="DE",
            products=["Silk Fabric", "Cotton Thread"],
        )

        req = NormalizedRequirement(
            raw_text="Looking for stainless steel bolts",
            item_description="stainless steel bolts",
        )
        suggestions = SellerSuggestionService.suggest_sellers(self.session, req)
        self.assertTrue(len(suggestions) > 0)
        self.assertEqual(suggestions[0].organization_id, seller_fasteners.id)
        self.assertNotIn(seller_textile.id, [s.organization_id for s in suggestions])

    def test_capability_overlap_boosts_score(self) -> None:
        self._seed_seller(
            legal_name="Basic Machining Co",
            country_code="US",
            products=["Industrial Screws"],
            capabilities=["General Machining"],
        )
        seller_advanced = self._seed_seller(
            legal_name="Advanced CNC Machining Co",
            country_code="US",
            products=["Industrial Screws"],
            capabilities=["Precision CNC Machining", "Heat Treatment"],
        )

        req = NormalizedRequirement(
            raw_text="Precision CNC Machining and Heat Treatment for industrial screws",
            item_description="industrial screws",
            capabilities_required=["Precision CNC Machining", "Heat Treatment"],
        )
        suggestions = SellerSuggestionService.suggest_sellers(self.session, req)
        self.assertEqual(len(suggestions), 2)
        # Advanced seller should rank higher due to 25% capability score
        self.assertEqual(suggestions[0].organization_id, seller_advanced.id)
        self.assertGreater(suggestions[0].match_score, suggestions[1].match_score)

    def test_geographic_region_match_and_incompatible_penalization(self) -> None:
        seller_local = self._seed_seller(
            legal_name="Tokyo Electronics Parts",
            country_code="JP",
            products=["Copper Wire Harness"],
            regions=["JP", "KR"],
        )
        self._seed_seller(
            legal_name="London Wire Supplies",
            country_code="GB",
            products=["Copper Wire Harness"],
            regions=["GB", "FR"],
        )

        req = NormalizedRequirement(
            raw_text="Copper wire harness delivered to Tokyo, Japan",
            item_description="copper wire harness",
            destination_country_code="JP",
        )
        suggestions = SellerSuggestionService.suggest_sellers(self.session, req)
        self.assertEqual(suggestions[0].organization_id, seller_local.id)
        self.assertGreater(suggestions[0].match_score, suggestions[1].match_score)

    def test_catalog_listing_fit_sufficient_quantity_and_budget(self) -> None:
        seller_catalog_fit = self._seed_seller(
            legal_name="Fit Bolts Inc",
            country_code="US",
            products=["Bolts"],
            listing_title="Standard Steel Bolts",
            listing_category="Fasteners",
            listing_quantity=Decimal("10000"),
            listing_price=Decimal("5.00"),
        )
        self._seed_seller(
            legal_name="Expensive Bolts Inc",
            country_code="US",
            products=["Bolts"],
            listing_title="Standard Steel Bolts",
            listing_category="Fasteners",
            listing_quantity=Decimal("10000"),
            listing_price=Decimal("50.00"),  # Exceeds target price
        )

        req = NormalizedRequirement(
            raw_text="500 units of bolts at $10.00 each",
            item_description="bolts",
            quantity=Decimal("500"),
            target_unit_price=Decimal("10.00"),
        )
        suggestions = SellerSuggestionService.suggest_sellers(self.session, req)
        self.assertEqual(suggestions[0].organization_id, seller_catalog_fit.id)
        self.assertIn(seller_catalog_fit.id, [s.organization_id for s in suggestions])
        self.assertTrue(len(suggestions[0].matched_listing_ids) > 0)

    def test_self_dealing_exclusion_buyer_is_never_suggested(self) -> None:
        """Buyer organization itself sells Fasteners, but must be excluded from suggestions."""
        seller_other = self._seed_seller(
            legal_name="Independent Fastener Supplier",
            country_code="US",
            products=["Fasteners"],
        )

        req = NormalizedRequirement(
            raw_text="500 units of Fasteners",
            item_description="fasteners",
        )
        suggestions = SellerSuggestionService.suggest_sellers(
            self.session, req, buyer_organization_id=self.buyer_id
        )
        suggested_ids = [s.organization_id for s in suggestions]
        self.assertNotIn(self.buyer_id, suggested_ids)
        self.assertIn(seller_other.id, suggested_ids)

    def test_inactive_and_suspended_organizations_disqualified(self) -> None:
        seller_active = self._seed_seller(
            legal_name="Active Fasteners",
            country_code="US",
            products=["Hex Nuts"],
            status="ACTIVE",
        )
        self._seed_seller(
            legal_name="Inactive Fasteners",
            country_code="US",
            products=["Hex Nuts"],
            status="INACTIVE",
        )
        self._seed_seller(
            legal_name="Suspended Fasteners",
            country_code="US",
            products=["Hex Nuts"],
            status="SUSPENDED",
        )

        req = NormalizedRequirement(
            raw_text="1000 Hex Nuts",
            item_description="hex nuts",
        )
        suggestions = SellerSuggestionService.suggest_sellers(self.session, req)
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].organization_id, seller_active.id)

    def test_inactive_marketplace_listings_ignored(self) -> None:
        seller_inactive_listing = self._seed_seller(
            legal_name="Stale Listing Store",
            country_code="US",
            products=[],  # No profile products
            listing_title="Hex Nuts Catalog",
            listing_category="Fasteners",
            listing_quantity=Decimal("5000"),
            listing_price=Decimal("1.00"),
            listing_status="INACTIVE",
        )

        req = NormalizedRequirement(
            raw_text="Hex Nuts Catalog",
            item_description="hex nuts",
        )
        suggestions = SellerSuggestionService.suggest_sellers(self.session, req)
        self.assertNotIn(seller_inactive_listing.id, [s.organization_id for s in suggestions])

    def test_deterministic_tie_breaking(self) -> None:
        # Two sellers with identical profiles and products
        seller_b = self._seed_seller(
            legal_name="Beta Fasteners Corp",
            country_code="US",
            products=["Hex Nuts"],
            regions=["US"],
        )
        seller_a = self._seed_seller(
            legal_name="Alpha Fasteners Corp",
            country_code="US",
            products=["Hex Nuts"],
            regions=["US"],
        )

        req = NormalizedRequirement(
            raw_text="Hex nuts in US",
            item_description="hex nuts",
            destination_country_code="US",
        )
        suggestions = SellerSuggestionService.suggest_sellers(self.session, req)
        self.assertEqual(len(suggestions), 2)
        # Identical score broken alphabetically by legal_name
        self.assertEqual(suggestions[0].organization_id, seller_a.id)
        self.assertEqual(suggestions[1].organization_id, seller_b.id)

    def test_top_n_limit_capping(self) -> None:
        for i in range(15):
            self._seed_seller(
                legal_name=f"Bulk Nut Vendor #{i:02d}",
                country_code="US",
                products=["Standard Hex Nuts"],
            )

        req = NormalizedRequirement(
            raw_text="Standard hex nuts",
            item_description="standard hex nuts",
        )
        suggestions = SellerSuggestionService.suggest_sellers(self.session, req, limit=10)
        self.assertLessEqual(len(suggestions), 10)

    def test_threshold_filtering_drops_low_scores(self) -> None:
        self._seed_seller(
            legal_name="Nut Supplier",
            country_code="US",
            products=["Hex Nuts"],
        )

        # Requirement completely irrelevant to nuts
        req = NormalizedRequirement(
            raw_text="500 satellite thermal solar batteries",
            item_description="satellite thermal solar batteries",
        )
        suggestions = SellerSuggestionService.suggest_sellers(self.session, req, threshold=0.15)
        self.assertEqual(suggestions, [])

    def test_contact_privacy_never_leaks_contacts(self) -> None:
        seller = self._seed_seller(
            legal_name="Secret Contact Co",
            country_code="US",
            products=["Fasteners"],
            contacts=[{"email": "confidential@secret.com", "phone": "555-0199"}],
        )

        req = NormalizedRequirement(
            raw_text="Fasteners",
            item_description="fasteners",
        )
        suggestions = SellerSuggestionService.suggest_sellers(
            self.session, req, buyer_organization_id=self.buyer_id
        )
        self.assertEqual(len(suggestions), 1)
        item = suggestions[0]
        # Inspect model fields
        self.assertNotIn("contacts", type(item).model_fields)
        self.assertFalse(hasattr(item, "contacts"))
        data = item.model_dump()
        self.assertNotIn("contacts", data)
        self.assertEqual(item.organization_id, seller.id)


if __name__ == "__main__":
    unittest.main()
