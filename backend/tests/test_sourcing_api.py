"""Integration tests for the buyer sourcing REST API router (/sourcing/*).

Tests all endpoints via httpx.AsyncClient with in-memory SQLite and mock actor dependencies:
- POST /sourcing/interpret
- GET  /sourcing/listings
- POST /sourcing/compare
- POST /sourcing/gap-analysis
- POST /sourcing/draft-inquiry
- POST /sourcing/evaluate
- Security & Middleware: 401 unauthorized and 413 payload limit.
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
    Organization,
    OrganizationMember,
    User,
)


class SourcingApiIntegrationTests(unittest.TestCase):
    """Full HTTP contract test suite for the /sourcing/* router."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        self.user, self.buyer_org = self._seed_buyer()
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

    def _seed_buyer(self) -> tuple[User, Organization]:
        user = User(
            email="sourcing.lead@apexprocure.com",
            display_name="Elena Vance",
            password_hash="test-argon2-hash",
            status="ACTIVE",
        )
        buyer_org = Organization(
            legal_name="Apex Global Procurement AG",
            country_code="DE",
            status="ACTIVE",
        )
        self.session.add_all([user, buyer_org])
        self.session.flush()

        self.session.add(
            OrganizationMember(
                user_id=user.id,
                organization_id=buyer_org.id,
                role="ADMIN",
                status="ACTIVE",
            )
        )
        self.session.commit()
        return user, buyer_org

    def _authenticate(self, actor: ActorContext | None) -> None:
        app.dependency_overrides[get_db] = lambda: self.session
        if actor is not None:
            app.dependency_overrides[get_current_actor] = lambda: actor
        else:
            app.dependency_overrides.pop(get_current_actor, None)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        async def send() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                return await client.request(
                    method, path, params=params, json=json, headers=headers
                )

        return asyncio.run(send())

    def _sample_requirements(
        self,
        category: str = "Industrial Fasteners",
        title: str = "M8 Stainless Steel Hex Cap Bolts",
        target_qty: int = 1000,
        max_price: str = "14.00",
        target_price: str = "12.00",
        max_lead_days: int = 30,
    ) -> dict[str, Any]:
        return {
            "title": title,
            "category": category,
            "description": f"Detailed requirement for {title}",
            "technical_specs": {
                "materials": ["316 Stainless Steel"],
                "tolerances": "ISO 965-1 6g",
                "certifications": ["ISO 9001", "CE", "RoHS"],
                "standards": ["DIN 933"],
            },
            "pricing": {
                "target_unit_price": target_price,
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

    # =========================================================================
    # 1. POST /sourcing/interpret
    # =========================================================================

    def test_interpret_nlp_prompt_extracts_fasteners_specification(self) -> None:
        prompt = (
            "Procurement requirement: We need 1,000 boxes of M8x30 DIN 933 Grade 316 stainless steel "
            "hex cap bolts with ISO 965-1 6g tolerance. Must have ISO 9001, CE, and RoHS certifications. "
            "Target price $12.00/box, max $14.00 USD. Deliver to Berlin, Germany by 2026-12-08 under DDP terms."
        )
        res = self._request("POST", "/sourcing/interpret", json={"prompt": prompt})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("requirements", data)
        self.assertIn("parsed_fields", data)

        req = data["requirements"]
        self.assertIn("fastener", req["category"].lower())
        self.assertEqual(Decimal(str(req["quantity"]["target_quantity"])), Decimal("1000"))
        self.assertEqual(req["quantity"]["unit"].lower(), "boxes")
        self.assertEqual(Decimal(str(req["pricing"]["target_unit_price"])), Decimal("12.00"))
        self.assertEqual(Decimal(str(req["pricing"]["max_unit_price"])), Decimal("14.00"))
        self.assertEqual(req["pricing"]["currency"], "USD")
        self.assertEqual(req["delivery"]["destination_country_code"], "DE")

        specs = req["technical_specs"]
        self.assertTrue(any("316" in m for m in specs.get("materials", [])))
        self.assertIn("CE", specs.get("certifications", []))
        self.assertIn("RoHS", specs.get("certifications", []))

    def test_interpret_structured_overrides_priority(self) -> None:
        prompt = "Need 500 units of bolts at $10.00 each."
        overrides = {
            "quantity": {"target_quantity": "2500", "unit": "boxes"},
            "pricing": {"target_unit_price": "8.50", "max_unit_price": "9.50", "currency": "EUR"},
            "delivery": {"destination_country_code": "FR", "max_lead_time_days": 15},
        }
        res = self._request("POST", "/sourcing/interpret", json={"prompt": prompt, "structured_overrides": overrides})
        self.assertEqual(res.status_code, 200)
        req = res.json()["requirements"]

        self.assertEqual(Decimal(str(req["quantity"]["target_quantity"])), Decimal("2500"))
        self.assertEqual(req["quantity"]["unit"], "boxes")
        self.assertEqual(Decimal(str(req["pricing"]["target_unit_price"])), Decimal("8.50"))
        self.assertEqual(req["pricing"]["currency"], "EUR")
        self.assertEqual(req["delivery"]["destination_country_code"], "FR")
        self.assertEqual(req["delivery"]["max_lead_time_days"], 15)

    def test_interpret_empty_payload_returns_defaults(self) -> None:
        res = self._request("POST", "/sourcing/interpret", json={})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("requirements", data)
        req = data["requirements"]
        self.assertEqual(Decimal(str(req["quantity"]["target_quantity"])), Decimal("1000"))
        self.assertEqual(req["pricing"]["currency"], "USD")

    def test_interpret_long_prompt_within_limits(self) -> None:
        prompt = "Need 500 boxes of M8 bolts. " + ("Additional technical specifications and standard notes. " * 80)
        res = self._request("POST", "/sourcing/interpret", json={"prompt": prompt})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("requirements", data)

    # =========================================================================
    # 2. GET /sourcing/listings
    # =========================================================================

    def test_get_listings_all(self) -> None:
        res = self._request("GET", "/sourcing/listings")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("listings", data)
        self.assertIn("total", data)
        self.assertGreaterEqual(data["total"], 14)
        self.assertEqual(len(data["listings"]), data["total"])

    def test_get_listings_filter_by_category(self) -> None:
        res = self._request("GET", "/sourcing/listings", params={"category": "Fasteners"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data["total"], 4)
        for item in data["listings"]:
            self.assertIn("fastener", item["category"].lower())

    def test_get_listings_filter_by_completeness(self) -> None:
        res = self._request("GET", "/sourcing/listings", params={"completeness": "FULL_COMPLETE"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data["total"], 5)
        for item in data["listings"]:
            self.assertEqual(item["completeness_tier"], "FULL_COMPLETE")

    def test_get_listings_filter_by_query_text(self) -> None:
        res = self._request("GET", "/sourcing/listings", params={"q": "Berlin"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data["total"], 1)
        self.assertTrue(any("berlin" in item["organization_name"].lower() for item in data["listings"]))

    def test_get_listings_nonexistent_filter_returns_empty(self) -> None:
        res = self._request("GET", "/sourcing/listings", params={"category": "NonExistentSector999"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total"], 0)
        self.assertEqual(len(data["listings"]), 0)

    # =========================================================================
    # 3. POST /sourcing/compare
    # =========================================================================

    def test_compare_evaluates_and_ranks_candidates(self) -> None:
        req = self._sample_requirements()
        res = self._request("POST", "/sourcing/compare", json={"requirements": req})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("results", data)
        results = data["results"]
        self.assertGreaterEqual(len(results), 8)

        # Verify Berlin is top match (Tier A)
        top = results[0]
        self.assertIn("Berlin", top["seller_organization_name"])
        self.assertEqual(top["match_tier"], "A")
        self.assertGreaterEqual(top["composite_score"], 90.0)

        # Check required schema fields
        for item in results:
            self.assertIn("spec_score", item)
            self.assertIn("price_score", item)
            self.assertIn("quantity_score", item)
            self.assertIn("lead_time_score", item)
            self.assertIn("terms_score", item)
            self.assertIn("composite_score", item)
            self.assertIn("match_tier", item)
            self.assertIn(item["match_tier"], ["A", "B", "C", "D"])
            self.assertIn("attribute_matrix", item)
            self.assertGreaterEqual(len(item["attribute_matrix"]), 5)

    def test_compare_with_specific_listing_ids(self) -> None:
        req = self._sample_requirements()
        chosen_ids = [
            "00000000-0000-4000-8000-000000000101",
            "00000000-0000-4000-8000-000000000102",
        ]
        res = self._request("POST", "/sourcing/compare", json={"requirements": req, "listing_ids": chosen_ids})
        self.assertEqual(res.status_code, 200)
        results = res.json()["results"]
        self.assertEqual(len(results), 2)
        returned_ids = {r["listing_id"] for r in results}
        self.assertEqual(returned_ids, set(chosen_ids))

    def test_compare_boundary_zero_target_price_safe(self) -> None:
        req = self._sample_requirements(target_price="0.00", max_price="0.00")
        res = self._request("POST", "/sourcing/compare", json={"requirements": req})
        self.assertEqual(res.status_code, 200)
        results = res.json()["results"]
        self.assertTrue(len(results) > 0)

    # =========================================================================
    # 4. POST /sourcing/gap-analysis
    # =========================================================================

    def test_gap_analysis_compliant_listing(self) -> None:
        req = self._sample_requirements()
        # Berlin listing is benchmark compliant
        res = self._request(
            "POST",
            "/sourcing/gap-analysis",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000101"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("listing", data)
        self.assertIn("gaps", data)
        self.assertIn("overall_severity", data)
        self.assertEqual(data["overall_severity"], "NONE")
        self.assertEqual(len(data["gaps"]), 0)

    def test_gap_analysis_missing_lead_time_gap(self) -> None:
        req = self._sample_requirements()
        # Apex is missing lead time and Incoterms
        res = self._request(
            "POST",
            "/sourcing/gap-analysis",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000102"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        categories = {g["category"] for g in data["gaps"]}
        self.assertIn("MISSING", categories)
        self.assertIn(data["overall_severity"], ["MODERATE", "CRITICAL"])

    def test_gap_analysis_critical_moq_barrier(self) -> None:
        # Baltic has 5,000 MOQ vs buyer demand of 500
        req = self._sample_requirements(target_qty=500)
        res = self._request(
            "POST",
            "/sourcing/gap-analysis",
            json={"requirements": req, "listing_id": "00000000-0000-4000-8000-000000000104"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        moq_gap = next((g for g in data["gaps"] if "moq" in g["field_name"].lower()), None)
        self.assertIsNotNone(moq_gap)
        self.assertEqual(moq_gap["severity"], "CRITICAL")
        self.assertEqual(data["overall_severity"], "CRITICAL")

    def test_gap_analysis_not_found(self) -> None:
        req = self._sample_requirements()
        res = self._request(
            "POST",
            "/sourcing/gap-analysis",
            json={"requirements": req, "listing_id": "99999999-9999-9999-9999-999999999999"},
        )
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"].lower())

    # =========================================================================
    # 5. POST /sourcing/draft-inquiry
    # =========================================================================

    def test_draft_inquiry_compliant_listing_purchase_intent(self) -> None:
        req = self._sample_requirements()
        res = self._request(
            "POST",
            "/sourcing/draft-inquiry",
            json={
                "requirements": req,
                "listing_id": "00000000-0000-4000-8000-000000000101",
                "buyer_organization_id": str(self.buyer_org.id),
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("subject", data)
        self.assertIn("body", data)
        self.assertIn("gaps_addressed", data)
        self.assertIn("proposed_terms", data)

        body = data["body"]
        self.assertIn("Apex Global Procurement AG", body)
        self.assertIn("Elena Vance", body)
        self.assertTrue("order confirmation" in body.lower() or "rfq" in body.lower() or "purchase" in body.lower())

    def test_draft_inquiry_addresses_specific_gaps(self) -> None:
        req = self._sample_requirements()
        # Apex has missing lead time
        res = self._request(
            "POST",
            "/sourcing/draft-inquiry",
            json={
                "requirements": req,
                "listing_id": "00000000-0000-4000-8000-000000000102",
                "buyer_organization_id": str(self.buyer_org.id),
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        body = data["body"].lower()
        self.assertTrue("lead time" in body or "delivery" in body or "dispatch" in body)

    def test_draft_inquiry_not_found(self) -> None:
        req = self._sample_requirements()
        res = self._request(
            "POST",
            "/sourcing/draft-inquiry",
            json={
                "requirements": req,
                "listing_id": "99999999-9999-9999-9999-999999999999",
            },
        )
        self.assertEqual(res.status_code, 404)

    # =========================================================================
    # 6. POST /sourcing/evaluate
    # =========================================================================

    def test_evaluate_end_to_end_from_prompt(self) -> None:
        prompt = (
            "We are sourcing 1,000 boxes of M8x30 Grade 316 stainless steel hex cap bolts for our automotive "
            "assembly facility in Berlin, Germany. Delivery required within 30 days under DDP terms. "
            "Target price $12.00, maximum budget $14.00 USD per box. Minimum 12-month warranty with EN 10204 3.1 Mill Certificate."
        )
        res = self._request(
            "POST",
            "/sourcing/evaluate",
            json={
                "prompt": prompt,
                "buyer_organization_id": str(self.buyer_org.id),
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("requirements", data)
        self.assertIn("comparisons", data)
        self.assertIn("inquiries", data)
        self.assertIn("total_listings_evaluated", data)

        comparisons = data["comparisons"]
        self.assertGreaterEqual(len(comparisons), 3)
        top = comparisons[0]
        self.assertIn("Berlin", top["seller_organization_name"])
        self.assertEqual(top["match_tier"], "A")
        self.assertGreaterEqual(top["composite_score"], 90.0)

        inquiries = data["inquiries"]
        self.assertIn("00000000-0000-4000-8000-000000000101", inquiries)
        berlin_inquiry = inquiries["00000000-0000-4000-8000-000000000101"]
        self.assertIn("subject", berlin_inquiry)
        self.assertIn("body", berlin_inquiry)

    def test_evaluate_with_explicit_requirements(self) -> None:
        req = self._sample_requirements()
        res = self._request(
            "POST",
            "/sourcing/evaluate",
            json={
                "requirements": req,
                "buyer_organization_id": str(self.buyer_org.id),
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["requirements"]["category"], "Industrial Fasteners")
        self.assertGreaterEqual(len(data["comparisons"]), 1)

    # =========================================================================
    # 7. Security, Auth, and Middleware
    # =========================================================================

    def test_unauthenticated_requests_rejected(self) -> None:
        # Clear dependency override to test live auth enforcement
        self._authenticate(actor=None)

        res = self._request("GET", "/sourcing/listings")
        self.assertEqual(res.status_code, 401)

        res = self._request("POST", "/sourcing/interpret", json={"prompt": "Fasteners"})
        self.assertEqual(res.status_code, 401)

    def test_request_body_size_limit_middleware(self) -> None:
        # Middleware limits body size to 16 KB
        huge_prompt = "A" * (20 * 1024)
        res = self._request("POST", "/sourcing/interpret", json={"prompt": huge_prompt})
        self.assertEqual(res.status_code, 413)
        self.assertIn("too large", res.json()["detail"].lower())
