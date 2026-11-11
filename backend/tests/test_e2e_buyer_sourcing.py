"""Buyer sourcing contract and explicitly isolated legacy demo behavior tests.

Legacy scoring, gap and inquiry scenarios override the availability gate only
inside these tests to preserve coverage of the fictional bundled dataset.
Public-contract tests use ``_public_request`` and never override the gate.
No live AI provider is used.
"""

from __future__ import annotations

import asyncio
import unittest
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import patch

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.auth import get_current_actor
from syncally.api.main import app
from syncally.api.sourcing import _scoring_unavailable
from syncally.application.ai import AIConfigurationError
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


class BaseBuyerSourcingE2ETest(unittest.TestCase):
    """HTTP fixture; demo tests explicitly enable legacy scoring in test only."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        # Seed authenticated buyer user
        self.user = User(
            email="lead.procurement@globalsupply.com",
            display_name="Senior Procurement Manager",
            password_hash="test-argon2-hash",
            status="ACTIVE",
        )
        self.session.add(self.user)
        self.session.flush()

        # Seed buyer organization
        self.buyer_org = Organization(
            legal_name="Apex Global Procurement AG",
            country_code="DE",
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
            capabilities=["Procurement", "Contract Manufacturing", "Supply Chain Management"],
            products=["Industrial Components", "Electronics", "Commercial Goods"],
            regions=["DE", "US", "JP", "GB", "PL"],
        )
        self.session.add(self.buyer_profile)

        # ----------------------------------------------------------------------
        # Seed 8 Realistic Bundled Candidate Sellers across 5 B2B sectors
        # (Intentional completeness variations: complete, ambiguous, incomplete, non-compliant)
        # ----------------------------------------------------------------------

        # Listing 1: Berlin Fastener & Bolt GmbH (Industrial Fasteners - FULL_COMPLETE)
        self.seller_fasteners_complete = self._seed_seller(
            legal_name="Berlin Fastener & Bolt GmbH",
            country_code="DE",
            capabilities=["Precision Machining", "DIN Standards", "Heat Treatment"],
            products=["Stainless Steel Bolts", "Hex Cap Screws", "Fasteners"],
            regions=["DE", "FR", "US"],
            listing_title="M8x30 Grade 316 Stainless Steel Hex Cap Bolts",
            listing_category="Industrial Fasteners",
            listing_quantity=Decimal("15000"),
            listing_unit="boxes",
            listing_price=Decimal("11.50"),
            listing_currency="USD",
        )

        # Listing 2: Apex Hardware Manufacturing (Industrial Fasteners - INCOMPLETE: missing lead time & incoterms)
        self.seller_fasteners_incomplete = self._seed_seller(
            legal_name="Apex Hardware Manufacturing",
            country_code="US",
            capabilities=["Fastener Cold Forging", "Bulk Distribution"],
            products=["Stainless Steel Bolts M8", "Industrial Screws"],
            regions=["US", "CA"],
            listing_title="Bulk Precision Stainless Steel Bolts M8",
            listing_category="Industrial Fasteners",
            listing_quantity=Decimal("8000"),
            listing_unit="boxes",
            listing_price=Decimal("10.80"),
            listing_currency="USD",
        )

        # Listing 3: Tokyo Micro-Conductor Ltd (Electronics & Wiring - AMBIGUOUS warranty & negotiable payment)
        self.seller_electronics_ambiguous = self._seed_seller(
            legal_name="Tokyo Micro-Conductor Ltd",
            country_code="JP",
            capabilities=["Automotive Wire Harness", "High Conductivity Drawing"],
            products=["Copper Wire Harness", "Micro Cable Assemblies"],
            regions=["JP", "US", "DE"],
            listing_title="Automotive Spec Copper Wire Harness 2m 28AWG",
            listing_category="Electronics",
            listing_quantity=Decimal("5000"),
            listing_unit="units",
            listing_price=Decimal("7.20"),
            listing_currency="USD",
        )

        # Listing 4: Baltic Fastener Works (Industrial Fasteners - NON_COMPLIANT MOQ: 5,000 boxes)
        self.seller_fasteners_high_moq = self._seed_seller(
            legal_name="Baltic Fastener Works",
            country_code="PL",
            capabilities=["Marine Grade Fasteners", "Heavy Forging"],
            products=["Marine-Grade A4-80 Bolts & Studs", "Industrial Fasteners"],
            regions=["PL", "DE", "SE"],
            listing_title="Industrial Marine-Grade A4-80 Bolts & Studs",
            listing_category="Industrial Fasteners",
            listing_quantity=Decimal("50000"),
            listing_unit="boxes",
            listing_price=Decimal("9.50"),
            listing_currency="USD",
        )

        # Listing 5: Nordic Precision AeroSpares (Industrial Fasteners - NON_COMPLIANT PRICE: $24.00 over budget)
        self.seller_fasteners_high_price = self._seed_seller(
            legal_name="Nordic Precision AeroSpares",
            country_code="SE",
            capabilities=["Aerospace Fasteners", "Titanium Machining"],
            products=["Aerospace Fasteners M8", "Ultra-High Tensile Hardware"],
            regions=["SE", "DE", "US"],
            listing_title="Aerospace Grade Ultra-High Tensile Fasteners M8",
            listing_category="Industrial Fasteners",
            listing_quantity=Decimal("2500"),
            listing_unit="boxes",
            listing_price=Decimal("24.00"),
            listing_currency="USD",
        )

        # Listing 6: Lancashire Weaving Mills (Textiles - AMBIGUOUS / INCOMPLETE terms)
        self.seller_textile_ambiguous = self._seed_seller(
            legal_name="Lancashire Weaving Mills",
            country_code="GB",
            capabilities=["Organic Yarn Spinning", "OEKO-TEX Finishing"],
            products=["Heavy Industrial Canvas & Poplin Fabric", "Linen"],
            regions=["GB", "US", "DE"],
            listing_title="Heavy Industrial Canvas & Poplin Fabric",
            listing_category="Textiles",
            listing_quantity=Decimal("40000"),
            listing_unit="yards",
            listing_price=Decimal("3.10"),
            listing_currency="USD",
        )

        # Listing 7: Shenzhen Precision Interconnect Co (Electronics - NON_COMPLIANT LEAD TIME: 75 days)
        self.seller_electronics_long_lead = self._seed_seller(
            legal_name="Shenzhen Precision Interconnect Co",
            country_code="CN",
            capabilities=["Custom Cable Extrusion", "Shielded Assemblies"],
            products=["Custom Shielded Micro-Coaxial Cable Assembly", "Wiring"],
            regions=["CN", "US", "DE"],
            listing_title="Custom Shielded Micro-Coaxial Cable Assembly",
            listing_category="Electronics",
            listing_quantity=Decimal("20000"),
            listing_unit="units",
            listing_price=Decimal("5.80"),
            listing_currency="USD",
        )

        # Listing 8: MediShield Global Corp (Medical Supplies - FULL_COMPLETE)
        self.seller_medical_complete = self._seed_seller(
            legal_name="MediShield Global Corp",
            country_code="US",
            capabilities=["Cleanroom Manufacturing", "FDA Compliance", "ISO 13485"],
            products=["Nitrile Examination Gloves Powder-Free Medical Grade", "PPE"],
            regions=["US", "CA", "DE"],
            listing_title="Nitrile Examination Gloves Powder-Free Medical Grade",
            listing_category="Medical Supplies",
            listing_quantity=Decimal("25000"),
            listing_unit="boxes",
            listing_price=Decimal("8.50"),
            listing_currency="USD",
        )

        # Listing 9: Andean High-Altitude Coffee Co (Agriculture - Organic Green Arabica Coffee)
        self.seller_agriculture = self._seed_seller(
            legal_name="Andean High-Altitude Coffee Co",
            country_code="CO",
            capabilities=["Direct Trade", "Fair Trade Certified", "Specialty Grading"],
            products=["Bulk Arabica Organic Green Coffee Beans", "Specialty Coffee"],
            regions=["CO", "US", "DE", "JP"],
            listing_title="Bulk Arabica Organic Green Coffee Beans Fair Trade",
            listing_category="Agricultural Commodities",
            listing_quantity=Decimal("30000"),
            listing_unit="kg",
            listing_price=Decimal("4.50"),
            listing_currency="USD",
        )

        # Disqualified Sellers (Inactive / Suspended)
        self.seller_inactive = self._seed_seller(
            legal_name="Defunct Bolt Warehouse LLC",
            country_code="DE",
            capabilities=["Fasteners"],
            products=["Stainless Steel Bolts"],
            regions=["DE"],
            status="INACTIVE",
        )

        self.session.commit()

        self.actor = ActorContext(
            user_id=self.user.id,
            organization_ids=frozenset({self.buyer_org.id}),
        )
        self._authenticate(self.actor)
        app.dependency_overrides[_scoring_unavailable] = lambda: None
        self.ai_patch = patch(
            "syncally.api.sourcing.ConfiguredAIProvider",
            side_effect=AIConfigurationError("No provider configured for this test"),
        )
        self.ai_provider_mock = self.ai_patch.start()

    def tearDown(self) -> None:
        self.ai_patch.stop()
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

    def _public_request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Exercise the real availability gate, without the legacy demo override."""
        override = app.dependency_overrides.pop(_scoring_unavailable)
        try:
            return self._request(method, path, **kwargs)
        finally:
            app.dependency_overrides[_scoring_unavailable] = override

    @staticmethod
    def _complete_overrides(overrides: dict[str, Any]) -> dict[str, Any]:
        """Supply explicit baseline controls while retaining each scenario's values."""
        result: dict[str, Any] = {
            "title": "M8 fasteners",
            "category": "Industrial Fasteners",
            "pricing": {"currency": "USD"},
            "quantity": {"target_quantity": "1000", "unit": "boxes"},
            "delivery": {"destination_country_code": "DE"},
            "commercial_terms": {
                "min_warranty_months": 12,
                "inspection_requirement": "FACTORY_MILL_CERTIFICATE",
            },
        }
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key].update(value)
            else:
                result[key] = value
        return result

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
                description=f"Catalog listing for {listing_title}",
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
# TIER 1: FEATURE COVERAGE (>=5 tests per core feature across F1-F14)
# ==============================================================================


class TestBuyerSourcingTier1FeatureCoverage(BaseBuyerSourcingE2ETest):
    """Tier 1: Systematic coverage of all buyer sourcing core features."""

    # --------------------------------------------------------------------------
    # Group 1: Natural Language & Technical Specification Parsing (F1 & F2)
    # --------------------------------------------------------------------------

    def test_tier1_interpret_fasteners_material_tolerance_standards(self) -> None:
        """Fastener prompts cannot be interpreted without a configured provider."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        prompt = (
            "Procurement requirement: We need 1,000 boxes of M8x30 DIN 933 Grade 316 stainless steel "
            "hex cap bolts with ISO 965-1 6g tolerance. Must have ISO 9001, CE, and RoHS certifications. "
            "Target price $12.00/box, max $14.00 USD. Deliver to Berlin, Germany by 2026-12-08 under DDP terms."
        )
        response = self._request("POST", "/sourcing/interpret", json={"prompt": prompt})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("requirements", response.json())

    def test_tier1_interpret_electronics_wire_gauge_jaso(self) -> None:
        """Electronics prompts cannot be interpreted without a configured provider."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        prompt = (
            "We need 2000 units of 28AWG automotive copper wire harness compliant with JASO D611 standard "
            "and RoHS certified. Budget is target $7.00 per unit, max $8.00 USD. Deliver to Tokyo, Japan."
        )
        response = self._request("POST", "/sourcing/interpret", json={"prompt": prompt})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("requirements", response.json())

    def test_tier1_interpret_agriculture_fair_trade_organic(self) -> None:
        """Agricultural prompts cannot be interpreted without a configured provider."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        prompt = (
            "Sourcing 20,000 kg of organic Arabica green coffee beans, Fair Trade certified. "
            "Max budget $5.00/kg USD. CIF Hamburg, Germany by 2026-12-15. Pre-shipment SGS inspection required."
        )
        response = self._request("POST", "/sourcing/interpret", json={"prompt": prompt})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("requirements", response.json())

    def test_tier1_interpret_textiles_oeko_tex_gsm(self) -> None:
        """Textile prompts cannot be interpreted without a configured provider."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        prompt = (
            "Requirement: 5,000 yards 100% cotton canvas 320 GSM, OEKO-TEX Standard 100 certified. "
            "Target unit price $3.00, max $3.50 USD. Destination London, GB under DDP terms."
        )
        response = self._request("POST", "/sourcing/interpret", json={"prompt": prompt})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("requirements", response.json())

    def test_tier1_interpret_medical_fda_astm_cleanroom(self) -> None:
        """Medical prompts cannot be interpreted without a configured provider."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        prompt = (
            "Urgent medical procurement: 10,000 boxes powder-free nitrile examination gloves 4 mil. "
            "Must comply with ASTM D6319 and FDA 510(k) clearance. Target $8.50, max $9.50/box USD. Destination Chicago, US."
        )
        response = self._request("POST", "/sourcing/interpret", json={"prompt": prompt})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("requirements", response.json())

    # --------------------------------------------------------------------------
    # Group 2: Pricing & Volume MOQ Validation (F3 & F4)
    # --------------------------------------------------------------------------

    def test_tier1_pricing_unit_price_constraint(self) -> None:
        """F3: Validates pricing constraints with target price and budget ceiling."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        overrides = {
            "pricing": {
                "target_unit_price": "12.00",
                "max_unit_price": "14.00",
                "currency": "USD",
            }
        }
        response = self._request("POST", "/sourcing/interpret", json={"structured_overrides": self._complete_overrides(overrides)})
        self.assertEqual(response.status_code, 200)
        pricing = response.json()["requirements"]["pricing"]
        self.assertEqual(Decimal(str(pricing["target_unit_price"])), Decimal("12.00"))
        self.assertEqual(Decimal(str(pricing["max_unit_price"])), Decimal("14.00"))

    def test_tier1_pricing_total_budget_cap(self) -> None:
        """F3: Validates total ceiling budget constraint."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        overrides = {
            "pricing": {
                "max_total_budget": "50000.00",
                "currency": "USD",
            }
        }
        response = self._request("POST", "/sourcing/interpret", json={"structured_overrides": self._complete_overrides(overrides)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(str(response.json()["requirements"]["pricing"]["max_total_budget"])), Decimal("50000.00"))

    def test_tier1_quantity_target_and_min_acceptable(self) -> None:
        """F4: Validates quantity requirements including target and minimum acceptable batches."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        overrides = {
            "quantity": {
                "target_quantity": "5000",
                "min_acceptable_quantity": "1000",
                "unit": "boxes",
            }
        }
        response = self._request("POST", "/sourcing/interpret", json={"structured_overrides": self._complete_overrides(overrides)})
        self.assertEqual(response.status_code, 200)
        qty = response.json()["requirements"]["quantity"]
        self.assertEqual(Decimal(str(qty["target_quantity"])), Decimal("5000"))
        self.assertEqual(Decimal(str(qty["min_acceptable_quantity"])), Decimal("1000"))

    def test_tier1_quantity_moq_compatibility_within_limits(self) -> None:
        """F4: Evaluates candidate listing where seller MOQ <= buyer quantity (compliant MOQ)."""
        if not _is_route_available("/sourcing/compare"):
            self.skipTest("POST /sourcing/compare not yet mounted in app")

        req = self._make_sample_requirements(target_qty=1000, max_price="14.00")
        response = self._request("POST", "/sourcing/compare", json={"requirements": req})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        # Find Berlin listing (MOQ: 500)
        berlin = next((r for r in results if "Berlin" in r.get("seller_organization_name", "")), None)
        self.assertIsNotNone(berlin)
        if berlin:
            self.assertGreaterEqual(berlin["quantity_score"], 90.0)

    def test_tier1_quantity_unit_packaging_preference(self) -> None:
        """F4: Preserves packaging specification (e.g. 100 pcs per carton)."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        overrides = {
            "quantity": {
                "target_quantity": "1000",
                "unit": "boxes",
                "packaging_preference": "100 pcs per moisture-sealed box",
            }
        }
        response = self._request("POST", "/sourcing/interpret", json={"structured_overrides": self._complete_overrides(overrides)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["requirements"]["quantity"]["packaging_preference"], "100 pcs per moisture-sealed box")

    # --------------------------------------------------------------------------
    # Group 3: Lead Time & Commercial Terms Normalization (F5 & F6)
    # --------------------------------------------------------------------------

    def test_tier1_lead_time_days_delivery_feasibility(self) -> None:
        """F5: Evaluates max lead time days and delivery arrival date calculation."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        delivery_date = (date.today() + timedelta(days=45)).isoformat()
        overrides = {
            "delivery": {
                "destination_country_code": "DE",
                "destination_port_or_city": "Hamburg",
                "required_delivery_date": delivery_date,
                "max_lead_time_days": 30,
            }
        }
        response = self._request("POST", "/sourcing/interpret", json={"structured_overrides": self._complete_overrides(overrides)})
        self.assertEqual(response.status_code, 200)
        deliv = response.json()["requirements"]["delivery"]
        self.assertEqual(deliv["max_lead_time_days"], 30)
        self.assertEqual(deliv["destination_port_or_city"], "Hamburg")

    def test_tier1_commercial_terms_incoterms_normalization(self) -> None:
        """F6: Normalizes Incoterms 2020 preference and acceptable alternatives list."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        overrides = {
            "commercial_terms": {
                "preferred_incoterm": "DDP",
                "acceptable_incoterms": ["DDP", "CIF", "FOB"],
                "min_warranty_months": 12,
            }
        }
        response = self._request("POST", "/sourcing/interpret", json={"structured_overrides": self._complete_overrides(overrides)})
        self.assertEqual(response.status_code, 200)
        terms = response.json()["requirements"]["commercial_terms"]
        self.assertEqual(terms["preferred_incoterm"], "DDP")
        self.assertIn("CIF", terms["acceptable_incoterms"])

    def test_tier1_commercial_terms_payment_methods(self) -> None:
        """F6: Normalizes buyer payment preference (Net 30, Escrow, LC)."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        overrides = {
            "commercial_terms": {
                "preferred_payment_term": "NET_30",
            }
        }
        response = self._request("POST", "/sourcing/interpret", json={"structured_overrides": self._complete_overrides(overrides)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["requirements"]["commercial_terms"]["preferred_payment_term"], "NET_30")

    def test_tier1_commercial_terms_warranty_duration(self) -> None:
        """F6: Normalizes minimum warranty duration threshold in months."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        overrides = {
            "commercial_terms": {
                "min_warranty_months": 24,
            }
        }
        response = self._request("POST", "/sourcing/interpret", json={"structured_overrides": self._complete_overrides(overrides)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["requirements"]["commercial_terms"]["min_warranty_months"], 24)

    def test_tier1_commercial_terms_inspection_preferences(self) -> None:
        """F6: Normalizes inspection requirements (EN 10204 3.1 Mill Certificate or Third-Party SGS)."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        overrides = {
            "commercial_terms": {
                "inspection_requirement": "FACTORY_MILL_CERTIFICATE",
            }
        }
        response = self._request("POST", "/sourcing/interpret", json={"structured_overrides": self._complete_overrides(overrides)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["requirements"]["commercial_terms"]["inspection_requirement"], "FACTORY_MILL_CERTIFICATE")

    # --------------------------------------------------------------------------
    # Group 4: Bundled Dataset & Multi-Factor Scoring Engine (F7 & F8)
    # --------------------------------------------------------------------------

    def test_tier1_marketplace_listings_repository_retrieval(self) -> None:
        """Active persisted marketplace offers remain browsable across sectors."""
        if not _is_route_available("/sourcing/listings", "GET"):
            self.skipTest("GET /sourcing/listings not yet mounted in app")

        unavailable = self._public_request("GET", "/sourcing/listings")
        self.assertEqual(unavailable.status_code, 503)
        self.assertNotIn("listings", unavailable.json())
        response = self._public_request("GET", "/marketplace/listings")
        self.assertEqual(response.status_code, 200)
        listings = response.json()
        self.assertGreaterEqual(len(listings), 8)

        categories = {item["category"].lower() for item in listings}
        self.assertTrue(any("fastener" in c for c in categories))
        self.assertTrue(any("electronic" in c for c in categories))
        self.assertTrue(any("medical" in c for c in categories))

    def test_tier1_scoring_engine_5_dimension_weights(self) -> None:
        """F8: Verifies 5-dimension weighted scoring math (specs 30%, price 25%, qty 15%, lead 15%, terms 15%)."""
        if not _is_route_available("/sourcing/compare"):
            self.skipTest("POST /sourcing/compare not yet mounted in app")

        req = self._make_sample_requirements()
        response = self._request("POST", "/sourcing/compare", json={"requirements": req})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertTrue(len(results) > 0)

        for res in results:
            self.assertIn("spec_score", res)
            self.assertIn("price_score", res)
            self.assertIn("quantity_score", res)
            self.assertIn("lead_time_score", res)
            self.assertIn("terms_score", res)
            self.assertIn("composite_score", res)
            self.assertIn("match_tier", res)
            self.assertIn(res["match_tier"], ["A", "B", "C", "D"])

    def test_tier1_scoring_engine_tier_a_ideal_match(self) -> None:
        """F8: Verifies fully compliant candidate listing achieves Tier A rating (score >= 90%)."""
        if not _is_route_available("/sourcing/compare"):
            self.skipTest("POST /sourcing/compare not yet mounted in app")

        req = self._make_sample_requirements(target_qty=1000, max_price="14.00", max_lead_days=30)
        response = self._request("POST", "/sourcing/compare", json={"requirements": req})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]

        berlin = next((r for r in results if "Berlin" in r.get("seller_organization_name", "")), None)
        self.assertIsNotNone(berlin)
        if berlin:
            self.assertEqual(berlin["match_tier"], "A")
            self.assertGreaterEqual(berlin["composite_score"], 90.0)

    def test_tier1_scoring_engine_tier_b_minor_variance(self) -> None:
        """F8: Candidate with minor commercial variance (e.g. FOB vs DDP, 304 vs 316) receives Tier B (75-89%)."""
        if not _is_route_available("/sourcing/compare"):
            self.skipTest("POST /sourcing/compare not yet mounted in app")

        req = self._make_sample_requirements(target_qty=500, max_price="12.00")
        response = self._request("POST", "/sourcing/compare", json={"requirements": req})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        tiers = {r["match_tier"] for r in results}
        self.assertTrue("B" in tiers or "A" in tiers)

    def test_tier1_scoring_engine_tier_d_disqualified(self) -> None:
        """F8: Candidate with extreme mismatch (over-budget price or excessive MOQ) receives Tier D (<50%)."""
        if not _is_route_available("/sourcing/compare"):
            self.skipTest("POST /sourcing/compare not yet mounted in app")

        # Buyer max budget is $12.00, Nordic listing is $24.00
        req = self._make_sample_requirements(target_qty=100, max_price="12.00")
        response = self._request("POST", "/sourcing/compare", json={"requirements": req})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]

        nordic = next((r for r in results if "Nordic" in r.get("seller_organization_name", "")), None)
        self.assertIsNotNone(nordic)
        if nordic:
            self.assertEqual(nordic["match_tier"], "D")
            self.assertLess(nordic["composite_score"], 50.0)

    # --------------------------------------------------------------------------
    # Group 5: Attribute-by-Attribute Comparison Matrix (F9)
    # --------------------------------------------------------------------------

    def test_tier1_comparison_matrix_exact_match_status(self) -> None:
        """F9: Verifies exact matching attributes are tagged with MATCH status."""
        if not _is_route_available("/sourcing/compare"):
            self.skipTest("POST /sourcing/compare not yet mounted in app")

        req = self._make_sample_requirements(target_qty=1000, max_price="14.00")
        response = self._request("POST", "/sourcing/compare", json={"requirements": req})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        berlin = next((r for r in results if "Berlin" in r.get("seller_organization_name", "")), None)
        self.assertIsNotNone(berlin)
        self.assertIn("attribute_matrix", berlin)
        if berlin and "attribute_matrix" in berlin:
            statuses = [row["status"] for row in berlin["attribute_matrix"]]
            self.assertIn("MATCH", statuses)

    def test_tier1_comparison_matrix_acceptable_variance_status(self) -> None:
        """F9: Verifies minor commercial variance is tagged with ACCEPTABLE_VARIANCE status."""
        if not _is_route_available("/sourcing/compare"):
            self.skipTest("POST /sourcing/compare not yet mounted in app")

        req = self._make_sample_requirements(target_qty=1000, max_price="14.00")
        response = self._request("POST", "/sourcing/compare", json={"requirements": req})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertTrue(results)
        self.assertIn("attribute_matrix", results[0])
        if results and "attribute_matrix" in results[0]:
            matrix = results[0]["attribute_matrix"]
            self.assertTrue(any(row.get("attribute") for row in matrix))

    def test_tier1_comparison_matrix_gap_status(self) -> None:
        """F9: Verifies non-compliant or missing attributes are tagged with GAP status."""
        if not _is_route_available("/sourcing/compare"):
            self.skipTest("POST /sourcing/compare not yet mounted in app")

        req = self._make_sample_requirements(target_qty=500, max_price="12.00")
        response = self._request("POST", "/sourcing/compare", json={"requirements": req})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        baltic = next((r for r in results if "Baltic" in r.get("seller_organization_name", "")), None)
        self.assertIsNotNone(baltic)
        self.assertIn("attribute_matrix", baltic)
        if baltic and "attribute_matrix" in baltic:
            statuses = [row["status"] for row in baltic["attribute_matrix"]]
            self.assertIn("GAP", statuses)

    def test_tier1_comparison_matrix_numerical_delta_formatting(self) -> None:
        """F9: Verifies numerical deltas for price and lead times are formatted canonically."""
        if not _is_route_available("/sourcing/compare"):
            self.skipTest("POST /sourcing/compare not yet mounted in app")

        req = self._make_sample_requirements(target_qty=1000, max_price="12.00")
        response = self._request("POST", "/sourcing/compare", json={"requirements": req})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        berlin = next((r for r in results if "Berlin" in r.get("seller_organization_name", "")), None)
        self.assertIsNotNone(berlin)
        if berlin and "attribute_matrix" in berlin:
            price_row = next((r for r in berlin["attribute_matrix"] if "price" in r["attribute"].lower()), None)
            self.assertIsNotNone(price_row)
            if price_row:
                self.assertTrue(len(price_row.get("variance", "")) > 0)

    def test_tier1_comparison_matrix_omitted_attributes_rendered(self) -> None:
        """F9: Verifies attributes missing in listing are rendered cleanly (e.g. 'Not Specified')."""
        if not _is_route_available("/sourcing/compare"):
            self.skipTest("POST /sourcing/compare not yet mounted in app")

        req = self._make_sample_requirements(target_qty=500)
        response = self._request("POST", "/sourcing/compare", json={"requirements": req})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        apex = next((r for r in results if "Apex" in r.get("seller_organization_name", "")), None)
        self.assertIsNotNone(apex)
        if apex and "attribute_matrix" in apex:
            lead_row = next((r for r in apex["attribute_matrix"] if "lead" in r["attribute"].lower()), None)
            self.assertIsNotNone(lead_row)
            if lead_row:
                self.assertEqual(lead_row["status"], "GAP")

    # --------------------------------------------------------------------------
    # Group 6: Gap Taxonomy & Detection Engine (F10 & F11)
    # --------------------------------------------------------------------------

    def test_tier1_gap_detection_missing_classification(self) -> None:
        """F10: Classifies completely omitted attributes as MISSING category."""
        if not _is_route_available("/sourcing/gap-analysis"):
            self.skipTest("POST /sourcing/gap-analysis not yet mounted in app")

        req = self._make_sample_requirements()
        # Apex is missing lead time and Incoterms
        response = self._request(
            "POST",
            "/sourcing/gap-analysis",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000102"},
        )
        self.assertEqual(response.status_code, 200)
        gaps = response.json()["gaps"]
        categories = {g["category"] for g in gaps}
        self.assertIn("MISSING", categories)

    def test_tier1_gap_detection_ambiguous_classification(self) -> None:
        """F10: Classifies vague terms ('standard warranty', 'negotiable payment') as AMBIGUOUS category."""
        if not _is_route_available("/sourcing/gap-analysis"):
            self.skipTest("POST /sourcing/gap-analysis not yet mounted in app")

        req = self._make_sample_requirements(category="Electronics", title="Copper Wire Harness")
        # Tokyo listing has ambiguous payment and warranty
        response = self._request(
            "POST",
            "/sourcing/gap-analysis",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000103"},
        )
        self.assertEqual(response.status_code, 200)
        gaps = response.json()["gaps"]
        categories = {g["category"] for g in gaps}
        self.assertIn("AMBIGUOUS", categories)

    def test_tier1_gap_detection_non_compliant_classification(self) -> None:
        """F10: Classifies hard constraint violations (high MOQ, high price) as NON_COMPLIANT category."""
        if not _is_route_available("/sourcing/gap-analysis"):
            self.skipTest("POST /sourcing/gap-analysis not yet mounted in app")

        # Baltic MOQ is 5,000 boxes; buyer needs 1,000 boxes
        req = self._make_sample_requirements(target_qty=1000)
        response = self._request(
            "POST",
            "/sourcing/gap-analysis",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000104"},
        )
        self.assertEqual(response.status_code, 200)
        gaps = response.json()["gaps"]
        categories = {g["category"] for g in gaps}
        self.assertIn("NON_COMPLIANT", categories)

    def test_tier1_gap_severity_critical_deal_blocker(self) -> None:
        """F10: Violations exceeding 1.5x MOQ or max budget are tagged with CRITICAL severity."""
        if not _is_route_available("/sourcing/gap-analysis"):
            self.skipTest("POST /sourcing/gap-analysis not yet mounted in app")

        req = self._make_sample_requirements(target_qty=1000, max_price="14.00")
        # Baltic MOQ 5,000 is 5x buyer demand (CRITICAL)
        response = self._request(
            "POST",
            "/sourcing/gap-analysis",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000104"},
        )
        self.assertEqual(response.status_code, 200)
        gaps = response.json()["gaps"]
        moq_gap = next((g for g in gaps if "moq" in g["field_name"].lower()), None)
        self.assertIsNotNone(moq_gap)
        if moq_gap:
            self.assertEqual(moq_gap["severity"], "CRITICAL")

    def test_tier1_gap_explanation_generator_mathematical_delta(self) -> None:
        """F11: Generates human-readable risk explanation detailing the exact mathematical delta."""
        if not _is_route_available("/sourcing/gap-analysis"):
            self.skipTest("POST /sourcing/gap-analysis not yet mounted in app")

        # Nordic price is $24.00, buyer max is $14.00
        req = self._make_sample_requirements(target_qty=100, max_price="14.00")
        response = self._request(
            "POST",
            "/sourcing/gap-analysis",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000105"},
        )
        self.assertEqual(response.status_code, 200)
        gaps = response.json()["gaps"]
        price_gap = next((g for g in gaps if "price" in g["field_name"].lower()), None)
        self.assertIsNotNone(price_gap)
        if price_gap:
            self.assertIn("24", price_gap["explanation"])
            self.assertIn("14", price_gap["explanation"])

    # --------------------------------------------------------------------------
    # Group 7: Targeted Seller Inquiry Drafting Engine (F12)
    # --------------------------------------------------------------------------

    def test_tier1_inquiry_drafting_missing_lead_time(self) -> None:
        """F12: Generates inquiry specifically requesting lead time commitment when missing."""
        if not _is_route_available("/sourcing/draft-inquiry"):
            self.skipTest("POST /sourcing/draft-inquiry not yet mounted in app")

        req = self._make_sample_requirements()
        # Apex is missing lead time
        response = self._request(
            "POST",
            "/sourcing/draft-inquiry",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000102"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("subject", data)
        self.assertIn("body", data)
        body = data["body"].lower()
        self.assertTrue("lead time" in body or "dispatch" in body or "delivery" in body)

    def test_tier1_inquiry_drafting_ambiguous_warranty(self) -> None:
        """F12: Generates inquiry clarifying ambiguous warranty terms."""
        if not _is_route_available("/sourcing/draft-inquiry"):
            self.skipTest("POST /sourcing/draft-inquiry not yet mounted in app")

        req = self._make_sample_requirements(category="Electronics", title="Copper Wire Harness")
        # Tokyo has ambiguous warranty
        response = self._request(
            "POST",
            "/sourcing/draft-inquiry",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000103"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["body"].lower()
        self.assertTrue("warranty" in body or "defect" in body)

    def test_tier1_inquiry_drafting_non_compliant_moq(self) -> None:
        """F12: Generates inquiry proposing pilot lot or tiered pricing for high MOQ listings."""
        if not _is_route_available("/sourcing/draft-inquiry"):
            self.skipTest("POST /sourcing/draft-inquiry not yet mounted in app")

        req = self._make_sample_requirements(target_qty=1000)
        # Baltic has 5,000 MOQ
        response = self._request(
            "POST",
            "/sourcing/draft-inquiry",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000104"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["body"].lower()
        self.assertTrue("moq" in body or "pilot" in body or "batch" in body or "minimum order" in body)

    def test_tier1_inquiry_drafting_non_compliant_price(self) -> None:
        """F12: Generates inquiry requesting volume discount for over-budget listing."""
        if not _is_route_available("/sourcing/draft-inquiry"):
            self.skipTest("POST /sourcing/draft-inquiry not yet mounted in app")

        req = self._make_sample_requirements(target_qty=100, max_price="14.00")
        # Nordic is $24.00
        response = self._request(
            "POST",
            "/sourcing/draft-inquiry",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000105"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["body"].lower()
        self.assertTrue("discount" in body or "budget" in body or "unit price" in body or "target" in body)

    def test_tier1_inquiry_drafting_zero_gaps_purchase_intent(self) -> None:
        """F12: Generates formal purchase intent RFQ when listing has zero gaps."""
        if not _is_route_available("/sourcing/draft-inquiry"):
            self.skipTest("POST /sourcing/draft-inquiry not yet mounted in app")

        req = self._make_sample_requirements(target_qty=1000, max_price="14.00", max_lead_days=30)
        # Berlin is 100% compliant
        response = self._request(
            "POST",
            "/sourcing/draft-inquiry",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000101"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("subject", data)
        self.assertTrue("order" in data["body"].lower() or "deal" in data["body"].lower() or "purchase" in data["body"].lower())

    # --------------------------------------------------------------------------
    # Group 8: REST API Endpoints & Deal Bridge (F13 & F14)
    # --------------------------------------------------------------------------

    def test_tier1_api_interpret_endpoint(self) -> None:
        """Natural interpretation reports the unavailable provider without guessing."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        response = self._request(
            "POST",
            "/sourcing/interpret",
            json={"prompt": "1000 units M8 bolts at $10 each to Berlin, Germany."},
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn("not configured", response.json()["detail"])

    def test_tier1_api_listings_endpoint_filtering(self) -> None:
        """Unavailable sourcing catalogue directs clients to marketplace filtering."""
        if not _is_route_available("/sourcing/listings", "GET"):
            self.skipTest("GET /sourcing/listings not yet mounted in app")

        response = self._public_request("GET", "/sourcing/listings", params={"category": "Fasteners"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("/marketplace/listings", response.json()["detail"])
        response = self._public_request("GET", "/marketplace/listings", params={"category": "Fasteners"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data), 0)
        for item in data:
            self.assertIn("fastener", item["category"].lower())

    def test_tier1_api_compare_endpoint(self) -> None:
        """Public comparison fails closed."""
        if not _is_route_available("/sourcing/compare"):
            self.skipTest("POST /sourcing/compare not yet mounted in app")

        req = self._make_sample_requirements()
        response = self._public_request("POST", "/sourcing/compare", json={"requirements": req})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("results", response.json())

    def test_tier1_api_gap_analysis_endpoint(self) -> None:
        """Public gap analysis fails closed."""
        if not _is_route_available("/sourcing/gap-analysis"):
            self.skipTest("POST /sourcing/gap-analysis not yet mounted in app")

        req = self._make_sample_requirements()
        response = self._public_request(
            "POST",
            "/sourcing/gap-analysis",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000101"},
        )
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("gaps", response.json())

    def test_tier1_deal_handoff_bridge_prefilled_terms(self) -> None:
        """Public evaluation does not produce a deal handoff or inquiry drafts."""
        if not _is_route_available("/sourcing/evaluate"):
            self.skipTest("POST /sourcing/evaluate not yet mounted in app")

        req = self._make_sample_requirements()
        response = self._public_request(
            "POST",
            "/sourcing/evaluate",
            json={"requirements": req, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("comparisons", response.json())
        self.assertNotIn("inquiries", response.json())

    def test_public_draft_inquiry_fails_closed(self) -> None:
        response = self._public_request(
            "POST",
            "/sourcing/draft-inquiry",
            json={"requirements": self._make_sample_requirements(), "listing_id": "demo-id"},
        )
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("body", response.json())

    def test_public_sourcing_requires_authentication(self) -> None:
        app.dependency_overrides.pop(get_current_actor)
        try:
            response = self._public_request("GET", "/sourcing/listings")
            self.assertEqual(response.status_code, 401)
            response = self._public_request(
                "POST", "/sourcing/compare", json={"requirements": self._make_sample_requirements()}
            )
            self.assertEqual(response.status_code, 401)
        finally:
            app.dependency_overrides[get_current_actor] = lambda: self.actor

    def _make_sample_requirements(
        self,
        category: str = "Industrial Fasteners",
        title: str = "M8 Stainless Steel Hex Cap Bolts",
        target_qty: int = 1000,
        max_price: str = "14.00",
        max_lead_days: int = 30,
    ) -> dict[str, Any]:
        return {
            "title": title,
            "category": category,
            "description": f"Standard procurement for {title}",
            "technical_specs": {
                "materials": ["316 Stainless Steel"],
                "tolerances": "ISO 965-1 6g",
                "certifications": ["ISO 9001", "CE", "RoHS"],
                "standards": ["DIN 933"],
            },
            "pricing": {
                "target_unit_price": "12.00",
                "max_unit_price": max_price,
                "currency": "USD",
            },
            "quantity": {
                "target_quantity": str(target_qty),
                "unit": "boxes",
            },
            "delivery": {
                "destination_country_code": "DE",
                "destination_port_or_city": "Berlin",
                "max_lead_time_days": max_lead_days,
            },
            "commercial_terms": {
                "preferred_incoterm": "DDP",
                "acceptable_incoterms": ["DDP", "CIF", "FOB"],
                "preferred_payment_term": "NET_30",
                "min_warranty_months": 12,
                "inspection_requirement": "FACTORY_MILL_CERTIFICATE",
            },
        }


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (>=5 tests per boundary feature)
# ==============================================================================


class TestBuyerSourcingTier2BoundaryCases(BaseBuyerSourcingE2ETest):
    """Tier 2: Extreme values, invalid inputs, edge cases, and graceful recovery."""

    # --------------------------------------------------------------------------
    # Boundary 2.1: Requirement Parsing Edge Cases
    # --------------------------------------------------------------------------

    def test_tier2_parsing_empty_string(self) -> None:
        """Empty input requests clarification instead of fabricated requirements."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        response = self._request("POST", "/sourcing/interpret", json={"prompt": ""})
        self.assertEqual(response.status_code, 422)
        self.assertIn("Please enter or confirm", response.json()["detail"])

    def test_tier2_parsing_whitespace_only(self) -> None:
        """Whitespace input requests clarification."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        response = self._request("POST", "/sourcing/interpret", json={"prompt": "   \n\t   "})
        self.assertEqual(response.status_code, 422)

    def test_tier2_parsing_extreme_long_prompt(self) -> None:
        """A long valid prompt does not bypass the provider requirement."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        prompt = "We require 500 units of bolts. " + ("Additional technical specifications and notes. " * 150)
        response = self._request("POST", "/sourcing/interpret", json={"prompt": prompt})
        self.assertEqual(response.status_code, 503)

    def test_tier2_parsing_conflicting_budget_and_unit_price(self) -> None:
        """A conflicting prompt cannot be interpreted without a provider."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        prompt = "Need 100 units of bolts at $10 each, but total budget is $50,000."
        response = self._request("POST", "/sourcing/interpret", json={"prompt": prompt})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("requirements", response.json())

    def test_tier2_parsing_past_delivery_date(self) -> None:
        """A past-date prompt cannot be interpreted without a provider."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        prompt = "Deliver 1000 units bolts by 2020-01-01 to Berlin, Germany."
        response = self._request("POST", "/sourcing/interpret", json={"prompt": prompt})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("requirements", response.json())

    def test_tier2_parsing_unparseable_alphanumeric_quantity(self) -> None:
        """A vague-quantity prompt cannot be interpreted without a provider."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        prompt = "Need a few hundred boxes of bolts to Berlin."
        response = self._request("POST", "/sourcing/interpret", json={"prompt": prompt})
        self.assertEqual(response.status_code, 503)

    # --------------------------------------------------------------------------
    # Boundary 2.2: Pricing Boundaries
    # --------------------------------------------------------------------------

    def test_tier2_pricing_zero_unit_price(self) -> None:
        """Boundary: Zero unit price ($0.00) treated as price-on-inquiry / ambiguous."""
        if not _is_route_available("/sourcing/compare"):
            self.skipTest("POST /sourcing/compare not yet mounted in app")

        req = self._make_sample_requirements(target_qty=100)
        req["pricing"]["target_unit_price"] = "0.00"
        response = self._request("POST", "/sourcing/compare", json={"requirements": req})
        self.assertEqual(response.status_code, 200)

    def test_tier2_pricing_extreme_large_price(self) -> None:
        """Boundary: Multi-million unit price handled without numerical overflow."""
        if not _is_route_available("/sourcing/compare"):
            self.skipTest("POST /sourcing/compare not yet mounted in app")

        req = self._make_sample_requirements()
        req["pricing"]["target_unit_price"] = "1000000.00"
        req["pricing"]["max_unit_price"] = "2000000.00"
        response = self._request("POST", "/sourcing/compare", json={"requirements": req})
        self.assertEqual(response.status_code, 200)

    def test_tier2_pricing_zero_max_budget(self) -> None:
        """Boundary: Max budget of $0.00 handled gracefully."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        overrides = {"pricing": {"max_total_budget": "0.00"}}
        response = self._request("POST", "/sourcing/interpret", json={"structured_overrides": self._complete_overrides(overrides)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.json()["requirements"]["pricing"]["max_total_budget"]), 0)

    def test_tier2_pricing_currency_mismatch_without_fx(self) -> None:
        """Boundary: Currency mismatch (USD buyer vs EUR seller) flagged as MODERATE gap rather than crash."""
        if not _is_route_available("/sourcing/gap-analysis"):
            self.skipTest("POST /sourcing/gap-analysis not yet mounted in app")

        req = self._make_sample_requirements()
        req["pricing"]["currency"] = "EUR"
        response = self._request(
            "POST",
            "/sourcing/gap-analysis",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000101"},
        )
        self.assertEqual(response.status_code, 200)

    def test_tier2_pricing_fractional_cent_precision(self) -> None:
        """Boundary: Fractional cent pricing ($0.0075) handled with Decimal precision."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        overrides = {"pricing": {"target_unit_price": "0.0075"}}
        response = self._request("POST", "/sourcing/interpret", json={"structured_overrides": self._complete_overrides(overrides)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.json()["requirements"]["pricing"]["target_unit_price"]), Decimal("0.0075"))

    # --------------------------------------------------------------------------
    # Boundary 2.3: Quantity & MOQ Boundaries
    # --------------------------------------------------------------------------

    def test_tier2_quantity_extreme_large_volume(self) -> None:
        """Boundary: High volume (100,000,000 units) compared without precision loss."""
        if not _is_route_available("/sourcing/compare"):
            self.skipTest("POST /sourcing/compare not yet mounted in app")

        req = self._make_sample_requirements(target_qty=100000000)
        response = self._request("POST", "/sourcing/compare", json={"requirements": req})
        self.assertEqual(response.status_code, 200)

    def test_tier2_quantity_fractional_decimal_quantity(self) -> None:
        """Boundary: Fractional quantities (0.25 metric tons) handled accurately."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        overrides = {"quantity": {"target_quantity": "0.25", "unit": "metric_tons"}}
        response = self._request("POST", "/sourcing/interpret", json={"structured_overrides": self._complete_overrides(overrides)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.json()["requirements"]["quantity"]["target_quantity"]), Decimal("0.25"))

    def test_tier2_quantity_seller_moq_100x_buyer_demand(self) -> None:
        """Boundary: Seller MOQ 100x buyer demand triggers CRITICAL deal blocker."""
        if not _is_route_available("/sourcing/gap-analysis"):
            self.skipTest("POST /sourcing/gap-analysis not yet mounted in app")

        # Buyer wants 50 boxes, Baltic MOQ is 5,000 boxes (100x)
        req = self._make_sample_requirements(target_qty=50)
        response = self._request(
            "POST",
            "/sourcing/gap-analysis",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000104"},
        )
        self.assertEqual(response.status_code, 200)
        moq_gap = next((g for g in response.json()["gaps"] if "moq" in g["field_name"].lower()), None)
        self.assertIsNotNone(moq_gap)
        if moq_gap:
            self.assertEqual(moq_gap["severity"], "CRITICAL")

    def test_tier2_quantity_missing_seller_moq(self) -> None:
        """Boundary: Missing seller MOQ scored at baseline 30 pts and flagged MISSING."""
        if not _is_route_available("/sourcing/gap-analysis"):
            self.skipTest("POST /sourcing/gap-analysis not yet mounted in app")

        req = self._make_sample_requirements()
        response = self._request(
            "POST",
            "/sourcing/gap-analysis",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000102"},
        )
        self.assertEqual(response.status_code, 200)

    def test_tier2_quantity_incompatible_unit_types(self) -> None:
        """Boundary: Incompatible units (e.g. buyer asks 'liters' for steel bolts) handled safely."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        overrides = {"quantity": {"target_quantity": "500", "unit": "liters"}}
        response = self._request("POST", "/sourcing/interpret", json={"structured_overrides": self._complete_overrides(overrides)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["requirements"]["quantity"]["unit"], "liters")

    # --------------------------------------------------------------------------
    # Boundary 2.4: Lead Time & Delivery Boundaries
    # --------------------------------------------------------------------------

    def test_tier2_lead_time_zero_days(self) -> None:
        """A one-day maximum lead time is preserved."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        overrides = {"delivery": {"max_lead_time_days": 1, "destination_country_code": "DE"}}
        response = self._request("POST", "/sourcing/interpret", json={"structured_overrides": self._complete_overrides(overrides)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["requirements"]["delivery"]["max_lead_time_days"], 1)

    def test_tier2_lead_time_extreme_days(self) -> None:
        """Boundary: Lead time of 730 days (2 years) flagged as deal-blocking non-compliant."""
        if not _is_route_available("/sourcing/compare"):
            self.skipTest("POST /sourcing/compare not yet mounted in app")

        req = self._make_sample_requirements(max_lead_days=14)
        # Shenzhen has 75 days lead time
        response = self._request("POST", "/sourcing/compare", json={"requirements": req})
        self.assertEqual(response.status_code, 200)

    def test_tier2_lead_time_vague_qualitative_phrase(self) -> None:
        """Boundary: Vague lead time ('fast dispatch upon factory opening') tagged AMBIGUOUS."""
        if not _is_route_available("/sourcing/gap-analysis"):
            self.skipTest("POST /sourcing/gap-analysis not yet mounted in app")

        req = self._make_sample_requirements(category="Textiles", title="Canvas Fabric")
        # Lancashire has vague lead time
        response = self._request(
            "POST",
            "/sourcing/gap-analysis",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000106"},
        )
        self.assertEqual(response.status_code, 200)

    def test_tier2_lead_time_delivery_deadline_tomorrow(self) -> None:
        """Boundary: 1-day delivery deadline vs 21-day lead time flags CRITICAL."""
        if not _is_route_available("/sourcing/compare"):
            self.skipTest("POST /sourcing/compare not yet mounted in app")

        req = self._make_sample_requirements(max_lead_days=1)
        response = self._request("POST", "/sourcing/compare", json={"requirements": req})
        self.assertEqual(response.status_code, 200)

    def test_tier2_lead_time_missing_in_listing(self) -> None:
        """Boundary: None lead time in candidate listing flagged as MISSING."""
        if not _is_route_available("/sourcing/gap-analysis"):
            self.skipTest("POST /sourcing/gap-analysis not yet mounted in app")

        req = self._make_sample_requirements()
        # Apex is missing lead time
        response = self._request(
            "POST",
            "/sourcing/gap-analysis",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000102"},
        )
        self.assertEqual(response.status_code, 200)
        lead_gap = next((g for g in response.json()["gaps"] if "lead" in g["field_name"].lower()), None)
        self.assertIsNotNone(lead_gap)
        if lead_gap:
            self.assertEqual(lead_gap["category"], "MISSING")

    # --------------------------------------------------------------------------
    # Boundary 2.5: Commercial Terms Boundaries
    # --------------------------------------------------------------------------

    def test_tier2_commercial_terms_unrecognized_incoterm(self) -> None:
        """An explicitly requested EXW Incoterm is preserved."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        overrides = {"commercial_terms": {"preferred_incoterm": "EXW"}}
        response = self._request("POST", "/sourcing/interpret", json={"structured_overrides": self._complete_overrides(overrides)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["requirements"]["commercial_terms"]["preferred_incoterm"], "EXW")

    def test_tier2_commercial_terms_missing_warranty(self) -> None:
        """Boundary: None warranty scored 0 pts and flagged MISSING."""
        if not _is_route_available("/sourcing/gap-analysis"):
            self.skipTest("POST /sourcing/gap-analysis not yet mounted in app")

        req = self._make_sample_requirements(category="Textiles")
        # Lancashire has no warranty
        response = self._request(
            "POST",
            "/sourcing/gap-analysis",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000106"},
        )
        self.assertEqual(response.status_code, 200)

    def test_tier2_commercial_terms_100_percent_advance_demand(self) -> None:
        """Boundary: 100% upfront advance payment demand penalized and flagged NON_COMPLIANT."""
        if not _is_route_available("/sourcing/gap-analysis"):
            self.skipTest("POST /sourcing/gap-analysis not yet mounted in app")

        req = self._make_sample_requirements()
        req["commercial_terms"]["preferred_payment_term"] = "NET_30"
        response = self._request(
            "POST",
            "/sourcing/gap-analysis",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000102"},
        )
        self.assertEqual(response.status_code, 200)

    def test_tier2_commercial_terms_ambiguous_standard_warranty(self) -> None:
        """Boundary: 'standard warranty applies' flagged as AMBIGUOUS."""
        if not _is_route_available("/sourcing/gap-analysis"):
            self.skipTest("POST /sourcing/gap-analysis not yet mounted in app")

        req = self._make_sample_requirements(category="Electronics", title="Copper Wire Harness")
        response = self._request(
            "POST",
            "/sourcing/gap-analysis",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000103"},
        )
        self.assertEqual(response.status_code, 200)
        warranty_gap = next((g for g in response.json()["gaps"] if "warranty" in g["field_name"].lower()), None)
        self.assertIsNotNone(warranty_gap)
        if warranty_gap:
            self.assertEqual(warranty_gap["category"], "AMBIGUOUS")

    def test_tier2_commercial_terms_empty_acceptable_incoterms_list(self) -> None:
        """Boundary: Empty acceptable incoterms list defaults cleanly."""
        if not _is_route_available("/sourcing/interpret"):
            self.skipTest("POST /sourcing/interpret not yet mounted in app")

        overrides = {"commercial_terms": {"acceptable_incoterms": []}}
        response = self._request("POST", "/sourcing/interpret", json={"structured_overrides": self._complete_overrides(overrides)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["requirements"]["commercial_terms"]["acceptable_incoterms"], [])

    def _make_sample_requirements(self, **kwargs: Any) -> dict[str, Any]:
        return TestBuyerSourcingTier1FeatureCoverage._make_sample_requirements(self, **kwargs)


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (Pairwise Interactions)
# ==============================================================================


class TestBuyerSourcingTier3CrossFeatureCombinations(BaseBuyerSourcingE2ETest):
    """Tier 3: Pairwise and multi-attribute commercial trade-offs."""

    def test_tier3_combo_high_price_plus_missing_lead_time(self) -> None:
        """Combo: Over-budget price (CRITICAL) + missing lead time (MODERATE) synthesizes 2-point targeted inquiry."""
        if not _is_route_available("/sourcing/draft-inquiry"):
            self.skipTest("POST /sourcing/draft-inquiry not yet mounted in app")

        req = self._make_sample_requirements(max_price="10.00")
        # Apex is $10.80 (over-budget) and missing lead time
        response = self._request(
            "POST",
            "/sourcing/draft-inquiry",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000102"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        body = data["body"].lower()
        self.assertTrue("price" in body or "budget" in body)
        self.assertTrue("lead time" in body or "dispatch" in body)

    def test_tier3_combo_non_compliant_moq_plus_ambiguous_warranty(self) -> None:
        """Combo: High MOQ barrier (5,000 vs 1,000) + ambiguous warranty generates pilot batch and warranty clarification."""
        if not _is_route_available("/sourcing/gap-analysis"):
            self.skipTest("POST /sourcing/gap-analysis not yet mounted in app")

        req = self._make_sample_requirements(target_qty=1000)
        response = self._request(
            "POST",
            "/sourcing/gap-analysis",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000104"},
        )
        self.assertEqual(response.status_code, 200)
        gaps = response.json()["gaps"]
        categories = {g["category"] for g in gaps}
        self.assertIn("NON_COMPLIANT", categories)

    def test_tier3_combo_missing_regulatory_cert_plus_tight_deadline(self) -> None:
        """Combo: Missing mandatory CE/FDA + 14-day deadline yields composite disqualification score (<40%)."""
        if not _is_route_available("/sourcing/compare"):
            self.skipTest("POST /sourcing/compare not yet mounted in app")

        req = self._make_sample_requirements(max_lead_days=14)
        req["technical_specs"]["certifications"] = ["AS9100D", "CE", "FDA"]
        response = self._request("POST", "/sourcing/compare", json={"requirements": req})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        # Fasteners without aerospace or medical certs should have penalized scores
        apex = next((r for r in results if "Apex" in r.get("seller_organization_name", "")), None)
        self.assertIsNotNone(apex)
        if apex:
            self.assertLess(apex["composite_score"], 60.0)

    def test_tier3_combo_currency_mismatch_plus_restrictive_exw(self) -> None:
        """Combo: EUR price for USD buyer + EXW shipping drafts currency lock and freight quote request."""
        if not _is_route_available("/sourcing/draft-inquiry"):
            self.skipTest("POST /sourcing/draft-inquiry not yet mounted in app")

        req = self._make_sample_requirements(category="Textiles", title="Canvas Fabric")
        req["pricing"]["currency"] = "USD"
        req["commercial_terms"]["preferred_incoterm"] = "DDP"
        # Lancashire has EXW terms
        response = self._request(
            "POST",
            "/sourcing/draft-inquiry",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000106"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["body"].lower()
        self.assertTrue("exw" in body or "freight" in body or "shipping" in body or "ddp" in body)

    def test_tier3_combo_category_disqualification_with_attractive_pricing(self) -> None:
        """Combo: Perfect price and quantity but completely wrong sector (Medical Gloves vs Fasteners) receives 0 spec score."""
        if not _is_route_available("/sourcing/compare"):
            self.skipTest("POST /sourcing/compare not yet mounted in app")

        req = self._make_sample_requirements(category="Industrial Fasteners", title="M8 Stainless Steel Bolts", max_price="15.00")
        response = self._request("POST", "/sourcing/compare", json={"requirements": req})
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        # MediShield (Medical Gloves) should be heavily penalized on specs despite $8.50 price
        medishield = next((r for r in results if "MediShield" in r.get("seller_organization_name", "")), None)
        self.assertIsNotNone(medishield)
        if medishield:
            self.assertLess(medishield["spec_score"], 30.0)

    def test_tier3_combo_partial_material_match_with_high_volume_discount(self) -> None:
        """Combo: 304 vs 316 Stainless Steel with $10.80 price drafts specification variance clarification."""
        if not _is_route_available("/sourcing/gap-analysis"):
            self.skipTest("POST /sourcing/gap-analysis not yet mounted in app")

        req = self._make_sample_requirements()
        # Apex offers 304 Stainless Steel while buyer requires 316
        response = self._request(
            "POST",
            "/sourcing/gap-analysis",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000102"},
        )
        self.assertEqual(response.status_code, 200)

    def test_tier3_combo_100_percent_advance_plus_unverified_seller(self) -> None:
        """Combo: 50% or 100% advance payment demand triggers SyncAlly Escrow recommendation."""
        if not _is_route_available("/sourcing/draft-inquiry"):
            self.skipTest("POST /sourcing/draft-inquiry not yet mounted in app")

        req = self._make_sample_requirements()
        req["commercial_terms"]["preferred_payment_term"] = "ESCROW"
        response = self._request(
            "POST",
            "/sourcing/draft-inquiry",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000102"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["body"].lower()
        self.assertTrue("escrow" in body or "payment" in body or "net" in body)

    def test_tier3_combo_extreme_lead_time_with_acceptable_price_and_specs(self) -> None:
        """Combo: 75-day lead time when buyer needs 30 days triggers expedited freight counter-proposal."""
        if not _is_route_available("/sourcing/draft-inquiry"):
            self.skipTest("POST /sourcing/draft-inquiry not yet mounted in app")

        req = self._make_sample_requirements(category="Electronics", title="Cable Assembly", max_lead_days=30)
        # Shenzhen has 75 days lead time
        response = self._request(
            "POST",
            "/sourcing/draft-inquiry",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000107"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["body"].lower()
        self.assertTrue("lead time" in body or "expedited" in body or "airfreight" in body or "schedule" in body)

    def _make_sample_requirements(self, **kwargs: Any) -> dict[str, Any]:
        return TestBuyerSourcingTier1FeatureCoverage._make_sample_requirements(self, **kwargs)


# ==============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS (End-to-End Buyer Procurement Journeys)
# ==============================================================================


class TestBuyerSourcingTier4RealWorldJourneys(BaseBuyerSourcingE2ETest):
    """Public buyers can browse offers but cannot evaluate or draft inquiries."""

    def _assert_browse_and_unavailable(self, prompt: str, category: str) -> None:
        browse = self._public_request("GET", "/marketplace/listings", params={"category": category})
        self.assertEqual(browse.status_code, 200)
        self.assertGreater(len(browse.json()), 0)
        self.assertTrue(all(category.lower() in item["category"].lower() for item in browse.json()))
        response = self._public_request(
            "POST",
            "/sourcing/evaluate",
            json={"prompt": prompt, "buyer_organization_id": str(self.buyer_org.id)},
        )
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("comparisons", response.json())
        self.assertNotIn("inquiries", response.json())
        self.ai_provider_mock.assert_not_called()

    def test_tier4_journey_fasteners_automotive_oem(self) -> None:
        """Fastener buyers browse real offers; evaluation remains unavailable."""
        if not _is_route_available("/sourcing/evaluate"):
            self.skipTest("POST /sourcing/evaluate not yet mounted in app")

        prompt = (
            "We are sourcing 1,000 boxes of M8x30 Grade 316 stainless steel hex cap bolts for our automotive "
            "assembly facility in Berlin, Germany. Delivery required within 30 days under DDP terms. "
            "Target price $12.00, maximum budget $14.00 USD per box. Minimum 12-month warranty with EN 10204 3.1 Mill Certificate."
        )

        self._assert_browse_and_unavailable(prompt, "Fasteners")

    def test_tier4_journey_electronics_iot_cable_harness(self) -> None:
        """Electronics buyers browse real offers; evaluation remains unavailable."""
        if not _is_route_available("/sourcing/evaluate"):
            self.skipTest("POST /sourcing/evaluate not yet mounted in app")

        prompt = (
            "Procurement for 2,000 units 28AWG copper automotive wire harness 2m length compliant with "
            "JASO D611 and RoHS. Target price $7.00, max $8.00 USD to Tokyo, Japan. Need delivery in 35 days."
        )

        self._assert_browse_and_unavailable(prompt, "Electronics")

    def test_tier4_journey_agriculture_specialty_coffee(self) -> None:
        """Agricultural buyers browse real offers; evaluation remains unavailable."""
        if not _is_route_available("/sourcing/evaluate"):
            self.skipTest("POST /sourcing/evaluate not yet mounted in app")

        prompt = (
            "We are procuring 20,000 kg of bulk organic green Arabica coffee beans Fair Trade certified. "
            "Max budget $5.00/kg USD delivered CIF Hamburg port by 2026-12-15. Pre-shipment SGS inspection certificate required."
        )

        self._assert_browse_and_unavailable(prompt, "Agricultural")

    def test_tier4_journey_textiles_organic_canvas(self) -> None:
        """Textile buyers browse real offers; evaluation remains unavailable."""
        if not _is_route_available("/sourcing/evaluate"):
            self.skipTest("POST /sourcing/evaluate not yet mounted in app")

        prompt = (
            "Need 5,000 yards of 100% cotton canvas 320 GSM with OEKO-TEX Standard 100 certification. "
            "Budget max $3.50/yard USD. Destination London, GB under DDP terms."
        )

        self._assert_browse_and_unavailable(prompt, "Textiles")

    def test_tier4_journey_medical_ppe_hospital_replenishment(self) -> None:
        """Medical buyers browse real offers; evaluation remains unavailable."""
        if not _is_route_available("/sourcing/evaluate"):
            self.skipTest("POST /sourcing/evaluate not yet mounted in app")

        prompt = (
            "Hospital procurement: 10,000 boxes powder-free nitrile examination gloves 4 mil medical grade. "
            "Must have FDA 510(k), ISO 13485, CE certifications. Target price $8.50, max $9.00 USD/box to Chicago, US. "
            "Delivery within 14 days under DDP terms."
        )

        self._assert_browse_and_unavailable(prompt, "Medical")
