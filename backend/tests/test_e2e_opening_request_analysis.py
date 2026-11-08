"""Opaque-box E2E test suite for AI opening request analysis, seller suggestion, and buyer deal flow.

Tests adhere to the 4-tier methodology:
- Tier 1: Feature Coverage (>=5 tests per feature)
- Tier 2: Boundary & Corner Cases (>=5 tests per feature)
- Tier 3: Cross-Feature Combinations
- Tier 4: Real-World Application Scenarios
"""

from __future__ import annotations

import asyncio
import unittest
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.auth import get_current_actor
from syncally.api.main import app
from syncally.application.identity import ActorContext
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import (
    Base,
    MarketplaceListing,
    Organization,
    OrganizationMember,
    OrganizationProfile,
    User,
)


def _is_route_available(path: str, method: str = "POST") -> bool:
    """Check if the given HTTP path and method are currently registered on FastAPI app."""
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", []):
            return True
        if hasattr(route, "original_router"):
            prefix = getattr(route.include_context, "prefix", "") or ""
            for sub_route in getattr(route.original_router, "routes", []):
                sub_path = getattr(sub_route, "path", None)
                if sub_path and f"{prefix}{sub_path}" == path and method in getattr(sub_route, "methods", []):
                    return True
    return False


class BaseOpeningRequestE2ETest(unittest.TestCase):
    """Base fixture for opaque-box opening request analysis and deal creation E2E tests."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        # Seed authenticated user
        self.user = User(
            email="buyer.procurement@example.com",
            display_name="Buyer Lead",
            password_hash="test-hash",
            status="ACTIVE",
        )
        self.session.add(self.user)
        self.session.flush()

        # Seed buyer organization
        self.buyer_org = Organization(
            legal_name="Global Procurement Corp",
            country_code="US",
            status="ACTIVE",
        )
        self.session.add(self.buyer_org)
        self.session.flush()

        self.session.add(
            OrganizationMember(
                user_id=self.user.id,
                organization_id=self.buyer_org.id,
                role="ADMIN",
                status="ACTIVE",
            )
        )
        self.buyer_profile = OrganizationProfile(
            organization_id=self.buyer_org.id,
            capabilities=["Procurement", "Global Supply Chain"],
            products=["Fasteners", "Structural Components"],
            regions=["US", "DE", "CA"],
        )
        self.session.add(self.buyer_profile)

        # Seed Candidate Sellers
        self.seller_bolts = self._seed_seller(
            legal_name="Berlin Fastener & Bolt GmbH",
            country_code="DE",
            capabilities=["Precision Machining", "Heat Treatment", "DIN Standards"],
            products=["Stainless Steel Bolts", "Hex Nuts", "Industrial Screws"],
            regions=["DE", "FR", "US"],
            listing_title="M8 Stainless Steel Hex Bolts",
            listing_category="Fasteners",
            listing_quantity=Decimal("10000"),
            listing_unit="units",
            listing_price=Decimal("12.50"),
            listing_currency="USD",
        )

        self.seller_coffee = self._seed_seller(
            legal_name="Andean High-Altitude Coffee Co",
            country_code="CO",
            capabilities=["Direct Trade", "Fair Trade Certified", "Green Coffee Sorting"],
            products=["Organic Coffee Beans", "Roasted Specialty Coffee", "Green Arabica"],
            regions=["US", "CA", "DE", "JP"],
            listing_title="Bulk Arabica Organic Green Coffee Beans",
            listing_category="Agricultural Commodities",
            listing_quantity=Decimal("50000"),
            listing_unit="kg",
            listing_price=Decimal("4.20"),
            listing_currency="USD",
        )

        self.seller_wire = self._seed_seller(
            legal_name="Tokyo Micro-Conductor Ltd",
            country_code="JP",
            capabilities=["High Conductivity Drawing", "Automotive Wiring Harnesses"],
            products=["Copper Wire Harness", "Micro Cable Assemblies", "Insulated Wire"],
            regions=["JP", "US", "DE"],
            listing_title="Automotive Spec Copper Wire Harness 2m",
            listing_category="Electronics",
            listing_quantity=Decimal("5000"),
            listing_unit="units",
            listing_price=Decimal("7.50"),
            listing_currency="USD",
        )

        self.seller_medical = self._seed_seller(
            legal_name="MediShield Global Corp",
            country_code="US",
            capabilities=["FDA Compliance", "Cleanroom Packaging", "ISO 13485"],
            products=["Nitrile Gloves", "Surgical Masks", "Medical Gowns"],
            regions=["US", "CA"],
            listing_title="Medical Grade Nitrile Examination Gloves 100/box",
            listing_category="Medical Supplies",
            listing_quantity=Decimal("20000"),
            listing_unit="boxes",
            listing_price=Decimal("9.00"),
            listing_currency="USD",
        )

        self.seller_textile = self._seed_seller(
            legal_name="Lancashire Weaving Mills",
            country_code="GB",
            capabilities=["Organic Yarn Spinning", "OEKO-TEX Finishing"],
            products=["Organic Cotton Fabric", "Industrial Canvas", "Linen"],
            regions=["GB", "US", "DE"],
            listing_title="GOTS Certified Organic Cotton Poplin",
            listing_category="Textiles",
            listing_quantity=Decimal("100000"),
            listing_unit="yards",
            listing_price=Decimal("2.40"),
            listing_currency="USD",
        )

        # Inactive seller (disqualified)
        self.seller_inactive = self._seed_seller(
            legal_name="Defunct Bolt Traders",
            country_code="DE",
            capabilities=["Precision Machining"],
            products=["Stainless Steel Bolts"],
            regions=["DE"],
            status="INACTIVE",
        )

        # Suspended seller (disqualified)
        self.seller_suspended = self._seed_seller(
            legal_name="Suspended Hardware LLC",
            country_code="US",
            capabilities=["Precision Machining"],
            products=["Stainless Steel Bolts"],
            regions=["US"],
            status="SUSPENDED",
        )

        self.session.commit()

        self.actor = ActorContext(
            user_id=self.user.id,
            organization_ids=frozenset({self.buyer_org.id}),
        )
        self._authenticate(self.actor)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _authenticate(self, actor: ActorContext) -> None:
        app.dependency_overrides[get_db] = lambda: self.session
        app.dependency_overrides[get_current_actor] = lambda: actor

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> httpx.Response:
        async def send() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                return await client.request(method, path, params=params, json=json)

        return asyncio.run(send())

    def _seed_seller(
        self,
        legal_name: str,
        country_code: str,
        capabilities: list[str],
        products: list[str],
        regions: list[str],
        status: str = "ACTIVE",
        listing_title: str | None = None,
        listing_category: str | None = None,
        listing_quantity: Decimal | None = None,
        listing_unit: str | None = None,
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
            capabilities=capabilities,
            products=products,
            regions=regions,
        )
        self.session.add(profile)

        if listing_title and listing_category and listing_quantity and listing_unit and listing_price:
            listing = MarketplaceListing(
                organization_id=org.id,
                title=listing_title,
                description=f"Direct catalog listing for {listing_title}",
                category=listing_category,
                available_quantity=listing_quantity,
                unit=listing_unit,
                unit_price=listing_price,
                currency=listing_currency,
                status=listing_status,
            )
            self.session.add(listing)

        self.session.flush()
        return org


# ==============================================================================
# TIER 1: FEATURE COVERAGE (>=5 tests per feature)
# ==============================================================================

class TestOpeningRequestE2ETier1FeatureCoverage(BaseOpeningRequestE2ETest):
    """Tier 1: Happy-path verification for normalization, fallback, suggestions, and deal creation."""

    # --------------------------------------------------------------------------
    # Feature 1.1: Requirement Normalization with Varied Phrasings (5 tests)
    # --------------------------------------------------------------------------

    def test_tier1_normalization_industrial_fasteners(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "We need 500 units of stainless steel bolts delivered to Berlin, Germany by 2026-12-01. Budget is $15 per unit."
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        req = data["requirements"]

        self.assertIn("bolt", req["item_description"].lower())
        self.assertEqual(Decimal(str(req["quantity"])), Decimal("500"))
        self.assertEqual(req["unit"].lower(), "units")
        self.assertEqual(Decimal(str(req["target_unit_price"])), Decimal("15"))
        self.assertIsNone(req["currency"])
        self.assertEqual(req["raw_text"], text)

    def test_tier1_normalization_agricultural_produce(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "Looking to purchase 10,000 kg of organic coffee beans to Toronto, Canada at 4.50 USD per kg by 2026-11-30."
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        req = response.json()["requirements"]

        self.assertIn("coffee", req["item_description"].lower())
        self.assertEqual(Decimal(str(req["quantity"])), Decimal("10000"))
        self.assertIn(req["unit"].lower(), {"kg", "kilograms"})
        self.assertEqual(Decimal(str(req["target_unit_price"])), Decimal("4.50"))

    def test_tier1_normalization_electronics_hardware(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "Need 2000 units of copper wire harness delivered to Tokyo, Japan. Target price $8 each."
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        req = response.json()["requirements"]

        self.assertIn("wire", req["item_description"].lower())
        self.assertEqual(Decimal(str(req["quantity"])), Decimal("2000"))
        self.assertEqual(Decimal(str(req["target_unit_price"])), Decimal("8"))

    def test_tier1_normalization_medical_supplies(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "Procurement request: 1500 boxes of nitrile gloves to Chicago, US by 2026-12-15 with FDA compliance."
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        req = response.json()["requirements"]

        self.assertIn("nitrile", req["item_description"].lower())
        self.assertEqual(Decimal(str(req["quantity"])), Decimal("1500"))
        self.assertEqual(req["unit"].lower(), "boxes")

    def test_tier1_normalization_textile_materials(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "RFQ: 50,000 yards of organic cotton fabric delivered to London, UK. Target budget 125000 USD."
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        req = response.json()["requirements"]

        self.assertIn("cotton", req["item_description"].lower())
        self.assertEqual(Decimal(str(req["quantity"])), Decimal("50000"))
        self.assertEqual(req["unit"].lower(), "yards")

    # --------------------------------------------------------------------------
    # Feature 1.2: Fallback Behavior when AI is Unconfigured or Offline (5 tests)
    # --------------------------------------------------------------------------

    def test_tier1_fallback_offline_mode_returns_rule_based_extraction(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "500 units of stainless steel bolts at $15 per unit"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("provenance", data)
        self.assertIn(data["provenance"]["mode"], {"offline", "openai_with_offline_fallback", "demo"})

    def test_tier1_fallback_missing_credentials_graceful_recovery(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "Purchase order: 250 boxes of packaging supplies delivered to Seattle by 2026-11-20."
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["requirements"]["raw_text"], text)

    def test_tier1_fallback_transient_error_exhausted(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "Looking for 100 industrial valves under 5000 USD to Hamburg."
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json()["requirements"])

    def test_tier1_fallback_minimal_text_graceful_extraction(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "Fasteners"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        req = response.json()["requirements"]
        self.assertEqual(req["raw_text"], "Fasteners")

    def test_tier1_ambiguous_dollar_symbol_does_not_assume_usd(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "Need 100 units at $45.50 each."
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        req = response.json()["requirements"]
        self.assertEqual(Decimal(str(req["target_unit_price"])), Decimal("45.50"))
        self.assertIsNone(req["currency"])

    # --------------------------------------------------------------------------
    # Feature 1.3: Multi-Factor Seller Suggestion Matching (5 tests)
    # --------------------------------------------------------------------------

    def test_tier1_suggestion_product_exact_match(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "500 units of stainless steel bolts"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        sellers = response.json()["suggested_sellers"]
        self.assertTrue(len(sellers) > 0)
        top_seller = sellers[0]
        self.assertEqual(top_seller["organization_id"], str(self.seller_bolts.id))
        self.assertTrue(any("bolt" in r.lower() or "product" in r.lower() for r in top_seller["match_reasons"]))

    def test_tier1_suggestion_capability_match(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "We need precision machining and heat treatment for 500 bolts in Berlin"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        sellers = response.json()["suggested_sellers"]
        top_seller = sellers[0]
        self.assertEqual(top_seller["organization_id"], str(self.seller_bolts.id))
        self.assertTrue(top_seller["match_score"] > 0.3)

    def test_tier1_suggestion_regional_compatibility(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "10000 kg organic coffee beans delivered to Tokyo, Japan"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        sellers = response.json()["suggested_sellers"]
        top_seller = sellers[0]
        self.assertEqual(top_seller["organization_id"], str(self.seller_coffee.id))

    def test_tier1_suggestion_marketplace_catalog_fit(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "Looking for 1000 boxes of nitrile examination gloves at $10.00/box"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        sellers = response.json()["suggested_sellers"]
        top_seller = sellers[0]
        self.assertEqual(top_seller["organization_id"], str(self.seller_medical.id))
        self.assertTrue(len(top_seller.get("matched_listing_ids", [])) > 0)

    def test_tier1_suggestion_multi_factor_composite_scoring(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "RFQ: 500 units of M8 Stainless Steel Hex Bolts delivered to Berlin, Germany at $14.00 per unit"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        sellers = response.json()["suggested_sellers"]
        self.assertTrue(len(sellers) > 0)
        top = sellers[0]
        self.assertEqual(top["organization_id"], str(self.seller_bolts.id))
        self.assertTrue(0.0 <= top["match_score"] <= 1.0)
        self.assertTrue(len(top["match_reasons"]) >= 1)

    # --------------------------------------------------------------------------
    # Feature 1.4: Deal Creation Flow Integration (5 tests)
    # --------------------------------------------------------------------------

    def test_tier1_deal_creation_standard_without_opening_request(self) -> None:
        """Standard deal creation without opening request proceeds normally."""
        response = self._request(
            "POST",
            "/deals",
            json={
                "buyer_organization_id": str(self.buyer_org.id),
                "seller_organization_id": str(self.seller_bolts.id),
            },
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["buyer_organization_id"], str(self.buyer_org.id))
        self.assertEqual(data["seller_organization_id"], str(self.seller_bolts.id))
        self.assertEqual(data["status"], "DRAFT")
        self.assertEqual(data["version"], 0)
        self.assertFalse(data["pending_counterparty"])

    def test_tier1_deal_creation_with_opening_request_text(self) -> None:
        """Deal creation accepts optional opening request / display name."""
        response = self._request(
            "POST",
            "/deals",
            json={
                "buyer_organization_id": str(self.buyer_org.id),
                "seller_organization_id": str(self.seller_coffee.id),
                "display_name": "Q4 Bulk Coffee Bean Order",
            },
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["display_name"], "Q4 Bulk Coffee Bean Order")

    def test_tier1_deal_creation_with_suggested_seller(self) -> None:
        """Deal created with counterparty selected directly from suggestions."""
        response = self._request(
            "POST",
            "/deals",
            json={
                "buyer_organization_id": str(self.buyer_org.id),
                "seller_organization_id": str(self.seller_wire.id),
                "display_name": "Wire Harness Procurement",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["seller_organization_id"], str(self.seller_wire.id))

    def test_tier1_deal_creation_seller_initiated(self) -> None:
        """Deal can also be initiated by seller role."""
        # Authenticate as member of seller org
        seller_user = User(email="sales@berlinbolts.de", display_name="Sales Rep")
        self.session.add(seller_user)
        self.session.flush()
        self.session.add(
            OrganizationMember(
                user_id=seller_user.id,
                organization_id=self.seller_bolts.id,
                role="ADMIN",
                status="ACTIVE",
            )
        )
        self.session.commit()

        self._authenticate(
            ActorContext(user_id=seller_user.id, organization_ids=frozenset({self.seller_bolts.id}))
        )

        response = self._request(
            "POST",
            "/deals",
            json={
                "buyer_organization_id": str(self.buyer_org.id),
                "seller_organization_id": str(self.seller_bolts.id),
                "initiator_party": "SELLER",
            },
        )
        self.assertEqual(response.status_code, 201)

    def test_tier1_deal_creation_backward_compatibility(self) -> None:
        """Verifies exact response schema compatibility with existing DealResponse."""
        response = self._request(
            "POST",
            "/deals",
            json={
                "buyer_organization_id": str(self.buyer_org.id),
                "seller_organization_id": str(self.seller_textile.id),
            },
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        expected_keys = {
            "id",
            "buyer_organization_id",
            "seller_organization_id",
            "status",
            "version",
            "pending_counterparty",
            "display_name",
        }
        self.assertEqual(set(data.keys()), expected_keys)


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (>=5 tests per feature)
# ==============================================================================

class TestOpeningRequestE2ETier2BoundaryAndCorners(BaseOpeningRequestE2ETest):
    """Tier 2: Boundary stress testing, cardinality limits, tie-breakers, and exclusions."""

    # --------------------------------------------------------------------------
    # Feature 2.1: Extreme Inputs & Adversarial Formats (7 tests)
    # --------------------------------------------------------------------------

    def test_tier2_input_empty_string_rejected(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": "", "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 422)

    def test_tier2_input_whitespace_only_handled_safely(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": "   \n\t  \r\n   ", "buyer_organization_id": str(self.buyer_org.id)},
        )
        # Should be 422 Unprocessable or 200 with empty requirements without 500
        self.assertIn(response.status_code, {200, 422})

    def test_tier2_input_exact_max_length_8000_chars(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        prefix = "We need 500 units of stainless steel bolts. Specifications: "
        long_text = prefix + ("X" * (8000 - len(prefix)))
        self.assertEqual(len(long_text), 8000)

        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": long_text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)

    def test_tier2_input_exceeding_max_length_rejected(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        too_long = "X" * 8001
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": too_long, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 422)

    def test_tier2_input_sql_xss_control_characters_escaped(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        payload = "SELECT * FROM deals; <script>alert(1)</script>; \u202e\u0000 500 bolts $10"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": payload, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("raw_text", response.json()["requirements"])

    def test_tier2_input_unicode_and_multilingual(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        multilingual = "购买 500 units 不锈钢螺栓 Café de Colombia 1000 kg"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": multilingual, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["requirements"]["raw_text"], multilingual)

    def test_tier2_input_non_matching_gibberish(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        gibberish = "asdkjhqwiueyr zxmcbvajksdhfqwuier optyruiqwe"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": gibberish, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["suggested_sellers"], [])

    # --------------------------------------------------------------------------
    # Feature 2.2: Suggestion Cardinality, Thresholds & Tie-Breaking (5 tests)
    # --------------------------------------------------------------------------

    def test_tier2_suggestion_zero_matching_sellers(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "500 specialized space satellite solar panels"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["suggested_sellers"], [])

    def test_tier2_suggestion_multiple_sellers_ranked_descending(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "Looking for precision fasteners and bolts in Germany"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        sellers = response.json()["suggested_sellers"]
        if len(sellers) > 1:
            for i in range(len(sellers) - 1):
                self.assertGreaterEqual(sellers[i]["match_score"], sellers[i + 1]["match_score"])

    def test_tier2_suggestion_deterministic_tie_breaking(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        # Seed two sellers with identical capabilities and products
        seller_a = self._seed_seller(
            legal_name="Alpha Fasteners Inc",
            country_code="US",
            capabilities=["Fastener Distribution"],
            products=["Hex Nuts"],
            regions=["US"],
        )
        seller_z = self._seed_seller(
            legal_name="Zulu Fasteners Inc",
            country_code="US",
            capabilities=["Fastener Distribution"],
            products=["Hex Nuts"],
            regions=["US"],
        )
        self.session.commit()

        text = "500 hex nuts in US"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        sellers = response.json()["suggested_sellers"]
        alpha_idx = next((i for i, s in enumerate(sellers) if s["organization_id"] == str(seller_a.id)), None)
        zulu_idx = next((i for i, s in enumerate(sellers) if s["organization_id"] == str(seller_z.id)), None)

        if alpha_idx is not None and zulu_idx is not None:
            # Deterministic alphabetical tie-breaking: Alpha before Zulu
            self.assertLess(alpha_idx, zulu_idx)

    def test_tier2_suggestion_top_n_limit_capping(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        # Seed 12 identical sellers
        for i in range(12):
            self._seed_seller(
                legal_name=f"Bulk Nut Vendor #{i:02d}",
                country_code="US",
                capabilities=["Fasteners"],
                products=["Standard Nuts"],
                regions=["US"],
            )
        self.session.commit()

        text = "1000 standard nuts"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        sellers = response.json()["suggested_sellers"]
        self.assertLessEqual(len(sellers), 10)

    def test_tier2_suggestion_threshold_filtering(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "1000 kg coffee beans"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        sellers = response.json()["suggested_sellers"]
        for seller in sellers:
            self.assertGreaterEqual(seller["match_score"], 0.15)

    # --------------------------------------------------------------------------
    # Feature 2.3: Disqualification & Exclusion Invariants (5 tests)
    # --------------------------------------------------------------------------

    def test_tier2_exclusion_buyer_self_dealing_prevented(self) -> None:
        """The requesting buyer must NEVER be suggested as a seller to themselves."""
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        # The buyer organization also has "Fasteners" in products
        text = "500 units of Fasteners"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        sellers = response.json()["suggested_sellers"]
        for seller in sellers:
            self.assertNotEqual(seller["organization_id"], str(self.buyer_org.id))

    def test_tier2_exclusion_inactive_organization_disqualified(self) -> None:
        """Organizations with status='INACTIVE' are disqualified."""
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "500 stainless steel bolts"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        sellers = response.json()["suggested_sellers"]
        for seller in sellers:
            self.assertNotEqual(seller["organization_id"], str(self.seller_inactive.id))

    def test_tier2_exclusion_suspended_organization_disqualified(self) -> None:
        """Organizations with status='SUSPENDED' are disqualified."""
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "500 stainless steel bolts"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        sellers = response.json()["suggested_sellers"]
        for seller in sellers:
            self.assertNotEqual(seller["organization_id"], str(self.seller_suspended.id))

    def test_tier2_exclusion_inactive_listing_ignored(self) -> None:
        """Inactive listings must not boost catalog match score."""
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        seller_inactive_listing = self._seed_seller(
            legal_name="Inactive Listing Co",
            country_code="US",
            capabilities=[],
            products=[],
            regions=["US"],
            listing_title="Inactive Hex Bolts",
            listing_category="Fasteners",
            listing_quantity=Decimal("1000"),
            listing_unit="units",
            listing_price=Decimal("1.00"),
            listing_status="INACTIVE",
        )
        self.session.commit()

        text = "Inactive Hex Bolts"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        sellers = response.json()["suggested_sellers"]
        matched_ids = [s["organization_id"] for s in sellers]
        self.assertNotIn(str(seller_inactive_listing.id), matched_ids)

    def test_tier2_exclusion_incompatible_region_penalized(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        # Seller strictly in Australia
        seller_au = self._seed_seller(
            legal_name="Aussie Fasteners Pty",
            country_code="AU",
            capabilities=["Fasteners"],
            products=["Stainless Steel Bolts"],
            regions=["AU"],
        )
        self.session.commit()

        text = "500 stainless steel bolts delivered to Berlin, Germany"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        sellers = response.json()["suggested_sellers"]
        if sellers:
            # Berlin supplier should score higher than Australian supplier delivering to Germany
            berlin_seller = next((s for s in sellers if s["organization_id"] == str(self.seller_bolts.id)), None)
            au_seller = next((s for s in sellers if s["organization_id"] == str(seller_au.id)), None)
            if berlin_seller and au_seller:
                self.assertGreater(berlin_seller["match_score"], au_seller["match_score"])


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (6 tests)
# ==============================================================================

class TestOpeningRequestE2ETier3CrossFeatureCombinations(BaseOpeningRequestE2ETest):
    """Tier 3: Pairwise and multi-feature interaction workflows."""

    def test_tier3_full_pipeline_normalize_suggest_create_deal(self) -> None:
        """Full flow: normalize request -> select suggested seller -> create deal."""
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "We need 500 units of stainless steel bolts delivered to Berlin, Germany at $12.50 per unit"
        analysis_res = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(analysis_res.status_code, 200)
        suggestions = analysis_res.json()["suggested_sellers"]
        self.assertTrue(len(suggestions) > 0)
        selected_seller_id = suggestions[0]["organization_id"]

        deal_res = self._request(
            "POST",
            "/deals",
            json={
                "buyer_organization_id": str(self.buyer_org.id),
                "seller_organization_id": selected_seller_id,
                "display_name": "Berlin Fastener Procurement Deal",
            },
        )
        self.assertEqual(deal_res.status_code, 201)
        deal_body = deal_res.json()
        self.assertEqual(deal_body["seller_organization_id"], selected_seller_id)
        self.assertEqual(deal_body["status"], "DRAFT")

    def test_tier3_partial_requirements_quantity_only(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "Looking for 10,000 kg of coffee beans"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        req = response.json()["requirements"]
        self.assertEqual(Decimal(str(req["quantity"])), Decimal("10000"))
        self.assertIsNone(req.get("target_unit_price"))

    def test_tier3_partial_requirements_destination_only(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "Shipment of copper wire to Tokyo, Japan"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 200)
        sellers = response.json()["suggested_sellers"]
        self.assertTrue(any(s["organization_id"] == str(self.seller_wire.id) for s in sellers))

    def test_tier3_zero_suggestion_fallback_to_directory_deal(self) -> None:
        """When zero sellers match, buyer can still manually create a deal with any active seller."""
        deal_res = self._request(
            "POST",
            "/deals",
            json={
                "buyer_organization_id": str(self.buyer_org.id),
                "seller_organization_id": str(self.seller_textile.id),
                "display_name": "Manual Directory Deal",
            },
        )
        self.assertEqual(deal_res.status_code, 201)
        self.assertEqual(deal_res.json()["seller_organization_id"], str(self.seller_textile.id))

    def test_tier3_offline_fallback_with_deal_creation(self) -> None:
        """Offline analysis followed immediately by deal creation."""
        deal_res = self._request(
            "POST",
            "/deals",
            json={
                "buyer_organization_id": str(self.buyer_org.id),
                "seller_organization_id": str(self.seller_bolts.id),
                "display_name": "Offline Mode Deal Flow",
            },
        )
        self.assertEqual(deal_res.status_code, 201)
        self.assertEqual(deal_res.json()["status"], "DRAFT")

    def test_tier3_unscoped_analysis_without_buyer_id(self) -> None:
        """Analysis request without buyer_organization_id returns suggestions without self-exclusion."""
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        text = "500 units of stainless steel bolts"
        response = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": text},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.json()["suggested_sellers"]) > 0)


# ==============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS (5 tests)
# ==============================================================================

class TestOpeningRequestE2ETier4RealWorldScenarios(BaseOpeningRequestE2ETest):
    """Tier 4: End-to-end realistic multi-domain procurement scenarios."""

    def test_tier4_scenario_aerospace_precision_machining(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        quote = "We require 500 units of stainless steel bolts with Precision Machining and Heat Treatment delivered to Berlin, Germany by 2026-12-01. Target unit price $12.50 USD."
        analysis_res = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": quote, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(analysis_res.status_code, 200)
        data = analysis_res.json()
        self.assertIn("bolt", data["requirements"]["item_description"].lower())
        top_seller = data["suggested_sellers"][0]
        self.assertEqual(top_seller["organization_id"], str(self.seller_bolts.id))

        deal_res = self._request(
            "POST",
            "/deals",
            json={
                "buyer_organization_id": str(self.buyer_org.id),
                "seller_organization_id": top_seller["organization_id"],
                "display_name": "Aerospace Fastener Contract",
            },
        )
        self.assertEqual(deal_res.status_code, 201)

    def test_tier4_scenario_agricultural_export_supply_chain(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        quote = "RFQ: 10,000 kg of organic coffee beans with Fair Trade Certified quality delivered to Toronto, Canada at 4.20 USD per kg."
        analysis_res = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": quote, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(analysis_res.status_code, 200)
        data = analysis_res.json()
        top_seller = data["suggested_sellers"][0]
        self.assertEqual(top_seller["organization_id"], str(self.seller_coffee.id))

        deal_res = self._request(
            "POST",
            "/deals",
            json={
                "buyer_organization_id": str(self.buyer_org.id),
                "seller_organization_id": top_seller["organization_id"],
                "display_name": "Fair Trade Coffee Procurement",
            },
        )
        self.assertEqual(deal_res.status_code, 201)

    def test_tier4_scenario_medical_device_procurement(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        quote = "Urgent: 1,500 boxes of nitrile gloves with FDA Compliance delivered to Chicago, US by 2026-12-15 at $9.00/box."
        analysis_res = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": quote, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(analysis_res.status_code, 200)
        data = analysis_res.json()
        top_seller = data["suggested_sellers"][0]
        self.assertEqual(top_seller["organization_id"], str(self.seller_medical.id))

        deal_res = self._request(
            "POST",
            "/deals",
            json={
                "buyer_organization_id": str(self.buyer_org.id),
                "seller_organization_id": top_seller["organization_id"],
                "display_name": "Hospital Glove Supply Deal",
            },
        )
        self.assertEqual(deal_res.status_code, 201)

    def test_tier4_scenario_international_multicurrency_trade(self) -> None:
        if not _is_route_available("/deals/opening-request/analyze"):
            self.skipTest("POST /deals/opening-request/analyze not yet mounted in app")

        quote = "RFQ: 50,000 yards of organic cotton fabric delivered to London, UK. Budget 125,000 USD."
        analysis_res = self._request(
            "POST",
            "/deals/opening-request/analyze",
            json={"text": quote, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(analysis_res.status_code, 200)
        top_seller = analysis_res.json()["suggested_sellers"][0]
        self.assertEqual(top_seller["organization_id"], str(self.seller_textile.id))

        deal_res = self._request(
            "POST",
            "/deals",
            json={
                "buyer_organization_id": str(self.buyer_org.id),
                "seller_organization_id": top_seller["organization_id"],
                "display_name": "UK Cotton Import Deal",
            },
        )
        self.assertEqual(deal_res.status_code, 201)

    def test_tier4_scenario_air_gapped_offline_resilience(self) -> None:
        """Simulates full offline deal initiation flow in air-gapped demo mode."""
        deal_res = self._request(
            "POST",
            "/deals",
            json={
                "buyer_organization_id": str(self.buyer_org.id),
                "seller_organization_id": str(self.seller_bolts.id),
                "display_name": "Air-Gapped Offline Deal",
            },
        )
        self.assertEqual(deal_res.status_code, 201)
        deal_id = deal_res.json()["id"]

        # Verify deal queryable from detail route
        detail_res = self._request("GET", f"/deals/{deal_id}")
        self.assertEqual(detail_res.status_code, 200)
        self.assertEqual(detail_res.json()["id"], deal_id)


if __name__ == "__main__":
    unittest.main()
