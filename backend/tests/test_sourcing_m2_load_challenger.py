"""Empirical challenger test suite for Milestone M2:
End-to-end evaluation pipeline, multi-candidate 5-sector evaluation,
deal room handoff bridge, and 20-request concurrent asynchronous load testing.

Author: challenger_sourcing_m2_2
Purpose: Adversarially challenge the /sourcing/evaluate pipeline under concurrent load:
- Execute multi-candidate evaluations across all 5 industrial sectors.
- Verify concurrent execution across 20 asynchronous requests.
- Verify response structures contain valid comparison results, gap breakdowns,
  and inquiry drafts with exact schema conformity.
- Verify deal room handoff data integrity.
"""

from __future__ import annotations

import asyncio
import time
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from syncally.api.auth import get_current_actor
from syncally.api.main import app
from syncally.api.sourcing import (
    EvaluateResponse,
)
from syncally.application.identity import ActorContext
from syncally.domain.sourcing.contracts import (
    GapCategory,
)
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import (
    Base,
    Organization,
    OrganizationMember,
    User,
)

# Canonical 14 listing IDs partitioned by the 5 industrial sectors
SECTOR_LISTING_IDS = {
    "Industrial Fasteners": [
        "00000000-0000-4000-8000-000000000101",  # Berlin Fastener (FULL_COMPLETE)
        "00000000-0000-4000-8000-000000000102",  # Apex Hardware (PARTIAL_MISSING_LEAD_TIME_OR_TERMS)
        "00000000-0000-4000-8000-000000000104",  # Baltic Fastener (NON_COMPLIANT_MOQ)
        "00000000-0000-4000-8000-000000000105",  # Nordic Precision (NON_COMPLIANT_PRICE / DISQUALIFIED)
    ],
    "Electronics & Electrical": [
        "00000000-0000-4000-8000-000000000109",  # Silicon Valley Sensors (FULL_COMPLETE: Transducer Module)
        "00000000-0000-4000-8000-000000000103",  # Tokyo Micro-Conductor (AMBIGUOUS_SPECS_OR_TERMS: Wire Harness)
        "00000000-0000-4000-8000-000000000107",  # Shenzhen Precision (NON_COMPLIANT_LEAD_TIME: 75d Lead Time)
    ],
    "Agricultural Commodities": [
        "00000000-0000-4000-8000-000000000110",  # São Paulo Agri-Exports (FULL_COMPLETE: Non-GMO Soybeans)
        "00000000-0000-4000-8000-000000000111",  # Danubian Grains (AMBIGUOUS_SPECS_OR_TERMS: Milling Wheat)
        "00000000-0000-4000-8000-000000000112",  # Valley Organic Farms (PARTIAL_MISSING_LEAD_TIME_OR_TERMS: Coffee)
    ],
    "Textiles & Fabrics": [
        "00000000-0000-4000-8000-000000000106",  # Porto Weaving Mills (FULL_COMPLETE: Cotton Canvas)
        "00000000-0000-4000-8000-000000000113",  # Izmir Textile Export (AMBIGUOUS_SPECS_OR_TERMS: Nomex)
    ],
    "Medical Supplies & PPE": [
        "00000000-0000-4000-8000-000000000108",  # MediShield Global (FULL_COMPLETE: Examination Gloves)
        "00000000-0000-4000-8000-000000000115",  # Bavarian MedTech (NON_COMPLIANT_PRICE / MISMATCH: Scalpels)
    ],
}


@pytest.fixture(scope="module")
def shared_test_db():
    """Set up an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    # Seed buyer user and organization
    seed_session = session_factory()
    user = User(
        email="challenger.lead@apexprocure.com",
        display_name="Audrey Martinez",
        password_hash="argon2-test-hash",
        status="ACTIVE",
    )
    buyer_org = Organization(
        legal_name="Apex Global Procurement AG",
        country_code="DE",
        status="ACTIVE",
    )
    seed_session.add_all([user, buyer_org])
    seed_session.flush()

    seed_session.add(
        OrganizationMember(
            user_id=user.id,
            organization_id=buyer_org.id,
            role="ADMIN",
            status="ACTIVE",
        )
    )
    seed_session.commit()

    actor = ActorContext(
        user_id=user.id,
        organization_ids=frozenset({buyer_org.id}),
    )

    yield {
        "engine": engine,
        "session_factory": session_factory,
        "user": user,
        "buyer_org": buyer_org,
        "actor": actor,
    }

    seed_session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def setup_app_dependencies(shared_test_db):
    """Override FastAPI dependencies with thread-safe session generator and actor."""
    import threading

    session_factory = shared_test_db["session_factory"]
    actor = shared_test_db["actor"]
    db_lock = threading.Lock()

    def override_get_db():
        with db_lock:
            db: Session = session_factory()
            try:
                yield db
            finally:
                db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_actor] = lambda: actor

    yield

    app.dependency_overrides.clear()


@pytest.fixture
def async_client():
    """Async HTTP client for FastAPI."""
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


# =============================================================================
# 1. Multi-Candidate Evaluations Across All 5 Industrial Sectors
# =============================================================================


class TestSectorMultiCandidateEvaluations:
    """Evaluates multi-candidate sourcing journeys across each of the 5 industrial sectors."""

    @pytest.mark.anyio
    async def test_sector_1_industrial_fasteners(self, async_client):
        """Sector 1: Industrial Fasteners (4 candidates).
        Verify parsing, ranking, gap breakdowns, and inquiry drafts.
        """
        payload = {
            "prompt": (
                "Need 2000 boxes of M8x30 stainless steel hex cap bolts DIN 933 A4-70 "
                "with CE and RoHS certification delivered to Hamburg within 25 days "
                "under $13.00/box with Net 30 or Escrow payment terms."
            ),
        }
        res = await async_client.post("/sourcing/evaluate", json=payload)
        assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}: {res.text}"

        data = res.json()
        validated_response = EvaluateResponse.model_validate(data)

        # 1. Check requirements parsed
        req = validated_response.requirements
        assert req.category == "Industrial Fasteners"
        assert req.pricing.max_unit_price is not None
        assert req.pricing.max_unit_price <= Decimal("13.00")
        assert req.quantity.target_quantity == Decimal("2000")

        # 2. Check comparisons
        comps = data["comparisons"]
        fastener_ids = set(SECTOR_LISTING_IDS["Industrial Fasteners"])
        fastener_comps = [c for c in comps if c["listing_id"] in fastener_ids]
        assert len(fastener_comps) == 4, f"Expected 4 fastener candidates, found {len(fastener_comps)}"

        # Ranking invariant: Non-disqualified listings must be ordered first, sorted descending by composite_score
        non_disq_scores = [c["composite_score"] for c in comps if not c["is_disqualified"]]
        assert non_disq_scores == sorted(non_disq_scores, reverse=True)
        is_disq_order = [c["is_disqualified"] for c in comps]
        assert is_disq_order == sorted(is_disq_order)  # False precedes True

        # Candidate 0101 (Berlin Fastener - FULL_COMPLETE) should score highest among fasteners
        top_fastener = fastener_comps[0]
        assert top_fastener["listing_id"] == "00000000-0000-4000-8000-000000000101"
        assert top_fastener["match_tier"] in ("A", "B")
        assert top_fastener["composite_score"] >= 80.0
        assert top_fastener["is_disqualified"] is False

        # Candidate 0104 (Baltic Fastener) has MOQ 5000 vs target 2000 -> must detect MOQ gap
        c0104 = next(c for c in fastener_comps if c["listing_id"] == "00000000-0000-4000-8000-000000000104")
        moq_gaps = [g for g in c0104["detected_gaps"] if g["field_name"] == "moq"]
        assert len(moq_gaps) >= 1, "Candidate 0104 must have MOQ gap detected"
        assert moq_gaps[0]["category"] == GapCategory.NON_COMPLIANT

        # Candidate 0102 (Apex Hardware) lacks lead time -> must detect lead time gap
        c0102 = next(c for c in fastener_comps if c["listing_id"] == "00000000-0000-4000-8000-000000000102")
        lt_gaps = [g for g in c0102["detected_gaps"] if g["field_name"] == "lead_time_days"]
        assert len(lt_gaps) >= 1, "Candidate 0102 must have lead time gap detected"
        assert lt_gaps[0]["category"] == GapCategory.MISSING

        # Candidate 0105 (Nordic Precision) price is $24 vs $13 max budget -> must be disqualified
        c0105 = next(c for c in fastener_comps if c["listing_id"] == "00000000-0000-4000-8000-000000000105")
        assert c0105["is_disqualified"] is True
        assert c0105["match_tier"] == "D"

        # 3. Check inquiries
        inquiries = validated_response.inquiries
        for c in fastener_comps:
            lid = c["listing_id"]
            assert lid in inquiries, f"Inquiry must exist for candidate {lid}"
            inq = inquiries[lid]
            assert inq.seller_organization_name
            assert inq.subject
            assert inq.body
            # Check proposed terms contain deal room bridge fields
            assert "target_quantity" in inq.proposed_terms
            assert "target_unit_price" in inq.proposed_terms
            assert "preferred_incoterm" in inq.proposed_terms

    @pytest.mark.anyio
    async def test_sector_2_electronics_electrical(self, async_client):
        """Sector 2: Electronics & Electrical (3 candidates).
        Verify parsing, ranking, lead time non-compliance, and inquiries.
        """
        payload = {
            "prompt": (
                "Procuring 1500 units of Industrial IoT Temperature & Pressure Transducer "
                "with CE and RoHS certification, max price $45.00/unit, "
                "delivery within 20 days, DDP terms."
            ),
        }
        res = await async_client.post("/sourcing/evaluate", json=payload)
        assert res.status_code == 200

        data = res.json()
        validated_response = EvaluateResponse.model_validate(data)

        comps = data["comparisons"]
        elec_ids = set(SECTOR_LISTING_IDS["Electronics & Electrical"])
        elec_comps = [c for c in comps if c["listing_id"] in elec_ids]
        assert len(elec_comps) == 3

        # Silicon Valley Sensors (#0109 - Full Complete) should rank highest among electronics
        assert elec_comps[0]["listing_id"] == "00000000-0000-4000-8000-000000000109"
        assert elec_comps[0]["composite_score"] >= 85.0
        assert elec_comps[0]["match_tier"] == "A"

        # Shenzhen Precision (#0107 - 75 days lead time vs 20 days max required)
        c0107 = next(c for c in elec_comps if c["listing_id"] == "00000000-0000-4000-8000-000000000107")
        lt_gaps = [g for g in c0107["detected_gaps"] if g["field_name"] == "lead_time_days"]
        assert len(lt_gaps) >= 1
        assert lt_gaps[0]["category"] == GapCategory.NON_COMPLIANT

        # Check inquiries for electronics candidates
        inquiries = validated_response.inquiries
        for c in elec_comps:
            lid = c["listing_id"]
            assert lid in inquiries
            inq = inquiries[lid]
            assert "Ref:" in inq.subject
            assert inq.seller_organization_name

    @pytest.mark.anyio
    async def test_sector_3_agricultural_commodities(self, async_client):
        """Sector 3: Agricultural Commodities (3 candidates).
        Verify bulk volume, missing inspection terms, missing lead times, and inquiries.
        """
        payload = {
            "prompt": (
                "Looking to purchase 500 metric tons of Non-GMO Soybeans Bulk Grade 1 "
                "max price $500/metric ton, delivered within 30 days, "
                "CIF terms with SGS inspection certificate."
            ),
        }
        res = await async_client.post("/sourcing/evaluate", json=payload)
        assert res.status_code == 200

        data = res.json()
        validated_response = EvaluateResponse.model_validate(data)

        comps = data["comparisons"]
        agri_ids = set(SECTOR_LISTING_IDS["Agricultural Commodities"])
        agri_comps = [c for c in comps if c["listing_id"] in agri_ids]
        assert len(agri_comps) == 3

        # Candidate 0110 (São Paulo Agri-Exports - Full Complete) should lead
        assert agri_comps[0]["listing_id"] == "00000000-0000-4000-8000-000000000110"
        assert agri_comps[0]["composite_score"] >= 85.0
        assert agri_comps[0]["match_tier"] == "A"

        # Candidate 0111 (Danubian Grains - Missing lead time) must flag lead time
        c0111 = next(c for c in agri_comps if c["listing_id"] == "00000000-0000-4000-8000-000000000111")
        lt_gaps = [g for g in c0111["detected_gaps"] if g["field_name"] == "lead_time_days"]
        assert len(lt_gaps) >= 1
        assert lt_gaps[0]["category"] == GapCategory.MISSING

        # Candidate 0112 (Valley Organic Farms - Missing inspection terms)
        c0112 = next(c for c in agri_comps if c["listing_id"] == "00000000-0000-4000-8000-000000000112")
        insp_gaps = [g for g in c0112["detected_gaps"] if g["field_name"] == "inspection_terms"]
        assert len(insp_gaps) >= 1
        assert insp_gaps[0]["category"] == GapCategory.MISSING

        # Check inquiry compromise for Danubian Grains
        inq0111 = validated_response.inquiries["00000000-0000-4000-8000-000000000111"]
        assert len(inq0111.gaps_addressed) > 0

    @pytest.mark.anyio
    async def test_sector_4_textiles_fabrics(self, async_client):
        """Sector 4: Textiles & Fabrics (2 candidates).
        Verify certification parsing, ranking, and side-by-side attribute matrix.
        """
        payload = {
            "prompt": (
                "Need 5000 meters of Heavy Duty Cotton Canvas Fabric 12oz, "
                "ISO 9001 certified, max $8.00/meter, "
                "delivery within 30 days to Lisbon, DDP terms."
            ),
        }
        res = await async_client.post("/sourcing/evaluate", json=payload)
        assert res.status_code == 200

        data = res.json()
        validated_response = EvaluateResponse.model_validate(data)
        assert validated_response.requirements.category == "Textiles & Fabrics"

        comps = data["comparisons"]
        textile_ids = set(SECTOR_LISTING_IDS["Textiles & Fabrics"])
        textile_comps = [c for c in comps if c["listing_id"] in textile_ids]
        assert len(textile_comps) == 2

        # Candidate 0106 (Porto Weaving Mills - Full Complete) should rank higher than 0113 (Izmir Textile - Ambiguous)
        assert textile_comps[0]["listing_id"] == "00000000-0000-4000-8000-000000000106"
        assert textile_comps[0]["composite_score"] > textile_comps[1]["composite_score"]

        # Verify attribute matrix has materials/spec comparison
        matrix = textile_comps[0]["attribute_matrix"]
        assert len(matrix) >= 5
        spec_row = next((r for r in matrix if "spec" in r["attribute"].lower() or "cert" in r["attribute"].lower() or "material" in r["attribute"].lower()), None)
        assert spec_row is not None

    @pytest.mark.anyio
    async def test_sector_5_medical_supplies_ppe(self, async_client):
        """Sector 5: Medical Supplies & PPE (2 candidates).
        Verify medical specs parsing, ranking, and inquiry drafts.
        """
        payload = {
            "prompt": (
                "Procuring 1000 boxes of Nitrile Examination Gloves Powder-Free Medical Grade "
                "with FDA 510(k), ISO 13485, CE certification, max price $10.00/box, "
                "delivery within 20 days to Boston with Escrow payment."
            ),
        }
        res = await async_client.post("/sourcing/evaluate", json=payload)
        assert res.status_code == 200

        data = res.json()
        validated_response = EvaluateResponse.model_validate(data)

        comps = data["comparisons"]
        med_ids = set(SECTOR_LISTING_IDS["Medical Supplies & PPE"])
        med_comps = [c for c in comps if c["listing_id"] in med_ids]
        assert len(med_comps) == 2

        # MediShield Global (0108 - Full Complete) ranks first among medical listings
        assert med_comps[0]["listing_id"] == "00000000-0000-4000-8000-000000000108"
        assert med_comps[0]["composite_score"] >= 80.0

        # Bavarian MedTech (0115 - surgical scalpel handles $45/unit) should be disqualified or score low
        c0115 = next(c for c in med_comps if c["listing_id"] == "00000000-0000-4000-8000-000000000115")
        assert c0115["match_tier"] == "D" or c0115["composite_score"] < 50.0

        # Check inquiry draft for MediShield Global
        inq0108 = validated_response.inquiries["00000000-0000-4000-8000-000000000108"]
        assert inq0108.seller_organization_name == "MediShield Global Corp"
        assert inq0108.proposed_terms["preferred_incoterm"] is not None


# =============================================================================
# 2. Deal Room Handoff Bridge Contract Verification
# =============================================================================


class TestDealRoomHandoffBridge:
    """Verifies that evaluation outputs completely fulfill the Deal Room handoff contract."""

    @pytest.mark.anyio
    async def test_deal_room_prefilled_terms_contract(self, async_client):
        """Verify inquiry drafts produce all required pre-filled deal terms for handoff URL."""
        payload = {
            "prompt": (
                "Need 1000 boxes of M8x30 stainless steel hex cap bolts DIN 933 "
                "target price $11.00 max $13.00, delivery to Hamburg in 20 days, DDP."
            ),
        }
        res = await async_client.post("/sourcing/evaluate", json=payload)
        assert res.status_code == 200
        data = res.json()

        comparisons = data["comparisons"]
        inquiries = data["inquiries"]
        assert len(comparisons) > 0

        for comp in comparisons:
            lid = comp["listing_id"]
            assert lid in inquiries
            inq = inquiries[lid]

            # Deal initiation contract:
            # #/deals/new?listingId={listingId}&sellerOrganizationId={sellerOrgId}&initiatorParty=BUYER
            assert inq["listing_id"] == lid
            assert inq["seller_organization_id"] == comp["seller_organization_id"]
            assert inq["seller_organization_name"] == comp["seller_organization_name"]

            # Deal proposed terms contract:
            terms = inq["proposed_terms"]
            assert "target_quantity" in terms
            assert Decimal(terms["target_quantity"]) > 0
            assert "target_unit_price" in terms
            assert Decimal(terms["target_unit_price"]) > 0
            assert "currency" in terms
            assert len(terms["currency"]) == 3
            assert "preferred_incoterm" in terms
            assert terms["preferred_incoterm"] in ["EXW", "FCA", "CPT", "CIP", "DAP", "DPU", "DDP", "FAS", "FOB", "CFR", "CIF"]

            # Communication contract:
            assert len(inq["subject"]) > 10
            assert len(inq["body"]) > 50
            assert "Apex Global Procurement AG" in inq["body"] or "Procurement" in inq["body"]


# =============================================================================
# 3. Concurrent Execution Across 20 Asynchronous Requests Under Load
# =============================================================================


class TestConcurrentLoadExecution:
    """Verifies that 20 simultaneous asynchronous evaluation requests complete deterministically and safely."""

    @pytest.mark.anyio
    async def test_concurrent_20_async_requests_across_5_sectors(self, async_client):
        """Fire 20 concurrent asynchronous requests to /sourcing/evaluate across all 5 sectors.
        Verify:
        - 100% success rate (HTTP 200)
        - Response determinism across identical concurrent prompts
        - Exact schema conformity across all 20 responses
        - Measure response time and throughput
        """
        prompts = [
            # 4 requests for Sector 1: Fasteners
            "Need 2000 boxes of M8x30 stainless steel hex cap bolts DIN 933 A4-70 CE certified $13/box.",
            "Need 2000 boxes of M8x30 stainless steel hex cap bolts DIN 933 A4-70 CE certified $13/box.",
            "Need 2000 boxes of M8x30 stainless steel hex cap bolts DIN 933 A4-70 CE certified $13/box.",
            "Need 2000 boxes of M8x30 stainless steel hex cap bolts DIN 933 A4-70 CE certified $13/box.",
            # 4 requests for Sector 2: Electronics
            "Require 1500 units of Industrial IoT Temperature & Pressure Transducer max $45.00.",
            "Require 1500 units of Industrial IoT Temperature & Pressure Transducer max $45.00.",
            "Require 1500 units of Industrial IoT Temperature & Pressure Transducer max $45.00.",
            "Require 1500 units of Industrial IoT Temperature & Pressure Transducer max $45.00.",
            # 4 requests for Sector 3: Agriculture
            "Bulk purchase 500 metric tons of Non-GMO Soybeans Bulk Grade 1 max $500/ton.",
            "Bulk purchase 500 metric tons of Non-GMO Soybeans Bulk Grade 1 max $500/ton.",
            "Bulk purchase 500 metric tons of Non-GMO Soybeans Bulk Grade 1 max $500/ton.",
            "Bulk purchase 500 metric tons of Non-GMO Soybeans Bulk Grade 1 max $500/ton.",
            # 4 requests for Sector 4: Textiles
            "Looking for 5000 meters of Heavy Duty Cotton Canvas Fabric 12oz max $8.00/m.",
            "Looking for 5000 meters of Heavy Duty Cotton Canvas Fabric 12oz max $8.00/m.",
            "Looking for 5000 meters of Heavy Duty Cotton Canvas Fabric 12oz max $8.00/m.",
            "Looking for 5000 meters of Heavy Duty Cotton Canvas Fabric 12oz max $8.00/m.",
            # 4 requests for Sector 5: Medical
            "Procuring 1000 boxes of Nitrile Examination Gloves Medical Grade max price $10.00/box.",
            "Procuring 1000 boxes of Nitrile Examination Gloves Medical Grade max price $10.00/box.",
            "Procuring 1000 boxes of Nitrile Examination Gloves Medical Grade max price $10.00/box.",
            "Procuring 1000 boxes of Nitrile Examination Gloves Medical Grade max price $10.00/box.",
        ]
        assert len(prompts) == 20

        start_time = time.perf_counter()

        # Execute 20 concurrent requests simultaneously
        tasks = [
            async_client.post("/sourcing/evaluate", json={"prompt": p})
            for p in prompts
        ]
        responses = await asyncio.gather(*tasks)

        total_elapsed = time.perf_counter() - start_time

        # 1. Verify 100% success rate
        status_codes = [r.status_code for r in responses]
        assert status_codes == [200] * 20, f"All 20 requests must return 200 OK. Received: {status_codes}"

        # 2. Verify schema conformity and determinism
        parsed_responses: list[EvaluateResponse] = []
        for i, r in enumerate(responses):
            try:
                ev = EvaluateResponse.model_validate(r.json())
                parsed_responses.append(ev)
            except Exception as exc:
                pytest.fail(f"Request #{i} failed schema validation: {exc}")

        assert len(parsed_responses) == 20

        # Check determinism within each 4-request group
        for group_idx in range(5):
            group_responses = parsed_responses[group_idx * 4 : (group_idx + 1) * 4]
            baseline = group_responses[0]
            for member in group_responses[1:]:
                # Requirements must match
                assert member.requirements.category == baseline.requirements.category
                assert member.requirements.quantity.target_quantity == baseline.requirements.quantity.target_quantity
                # Comparisons count must match
                assert len(member.comparisons) == len(baseline.comparisons)
                # First ranked candidate must match
                assert member.comparisons[0]["listing_id"] == baseline.comparisons[0]["listing_id"]
                assert member.comparisons[0]["composite_score"] == pytest.approx(baseline.comparisons[0]["composite_score"])
                assert member.comparisons[0]["match_tier"] == baseline.comparisons[0]["match_tier"]
                # Total listings evaluated must match
                assert member.total_listings_evaluated == baseline.total_listings_evaluated

        # Log performance metrics
        avg_latency = total_elapsed / 20.0
        throughput = 20.0 / total_elapsed if total_elapsed > 0 else 0
        print(f"\n[STRESS TEST PROOF] 20 Concurrent Requests Finished in {total_elapsed:.3f}s (Avg {avg_latency*1000:.1f}ms/req, Throughput {throughput:.1f} req/s)")

    @pytest.mark.anyio
    async def test_concurrent_heterogeneous_adversarial_load(self, async_client):
        """Stress test 20 concurrent requests with heterogeneous and adversarial conditions:
        - Very long prompts (approaching 4000 characters)
        - Boundary requests with custom listing_ids filter
        - Non-ASCII multi-lingual characters
        - Direct structured overrides without prompt
        - Custom buyer organization id resolution
        Verify all 20 succeed without unhandled exceptions or deadlocks.
        """
        stress_payloads = [
            # Long prompt
            {"prompt": ("Procure 5000 stainless bolts DIN 933. " + "Important industrial requirement specifications for aerospace testing. " * 30)[:3800]},
            # Filtered listings (only 2 listings)
            {"prompt": "Fasteners inquiry", "listing_ids": ["00000000-0000-4000-8000-000000000101", "00000000-0000-4000-8000-000000000102"]},
            # Multilingual non-ASCII
            {"prompt": "Beschaffung von 3000 Stück Edelstahl Schrauben DIN 933 für München Baustelle mit Prüfzertifikat."},
            # Structured overrides without prompt
            {"requirements": {
                "title": "Direct Structured Procurement",
                "category": "Industrial Fasteners",
                "description": "Direct structured override requirement",
                "technical_specs": {"materials": ["316 Stainless Steel"], "standards": ["DIN 933"]},
                "pricing": {"target_unit_price": "10.50", "max_unit_price": "12.00", "currency": "USD"},
                "quantity": {"target_quantity": "500", "unit": "boxes"},
                "delivery": {"destination_country_code": "DE", "max_lead_time_days": 21},
                "commercial_terms": {"preferred_incoterm": "DDP", "min_warranty_months": 12},
            }},
            # Electronics with custom buyer org id
            {"prompt": "2000 wiring harnesses UL94V-0 max $15", "buyer_organization_id": "11111111-0000-4000-8000-000000000001"},
        ] * 4  # 5 * 4 = 20 concurrent heterogeneous requests

        assert len(stress_payloads) == 20

        tasks = [
            async_client.post("/sourcing/evaluate", json=payload)
            for payload in stress_payloads
        ]
        responses = await asyncio.gather(*tasks)

        assert all(r.status_code == 200 for r in responses), f"Unexpected status codes: {[r.status_code for r in responses if r.status_code != 200]}"
        for r in responses:
            EvaluateResponse.model_validate(r.json())


# =============================================================================
# 4. Deep Exact Schema Conformity & Matrix Verification
# =============================================================================


class TestExactSchemaConformity:
    """Verifies granular compliance of all nested fields against contracts and PROJECT.md specifications."""

    @pytest.mark.anyio
    async def test_attribute_matrix_deep_conformity(self, async_client):
        """Verify attribute_matrix items have both attribute and field_name aliases and valid status."""
        payload = {"prompt": "1000 boxes M8 stainless steel hex cap bolts DIN 933 $12/box."}
        res = await async_client.post("/sourcing/evaluate", json=payload)
        assert res.status_code == 200
        data = res.json()

        for comp in data["comparisons"]:
            # Check scores
            assert "composite_score" in comp
            assert 0.0 <= comp["composite_score"] <= 100.0
            assert "match_tier" in comp
            assert comp["match_tier"] in ["A", "B", "C", "D"]
            for sub_score in ["spec_score", "price_score", "quantity_score", "lead_time_score", "terms_score"]:
                assert sub_score in comp
                assert 0.0 <= comp[sub_score] <= 100.0

            # Check attribute matrix
            assert "attribute_matrix" in comp
            matrix = comp["attribute_matrix"]
            assert len(matrix) >= 5, "Attribute matrix must contain at least 5 dimension rows"
            for row in matrix:
                assert "attribute" in row, "Matrix row must contain canonical 'attribute' key"
                assert "field_name" in row, "Matrix row must contain 'field_name' key"
                assert "buyer_value" in row
                assert "status" in row
                assert row["status"] in ["MATCH", "ACCEPTABLE_VARIANCE", "GAP"]

            # Check detected gaps
            assert "detected_gaps" in comp
            for gap in comp["detected_gaps"]:
                assert "gap_id" in gap
                assert "field_name" in gap
                assert "category" in gap
                assert gap["category"] in ["MISSING", "AMBIGUOUS", "NON_COMPLIANT"]
                assert "severity" in gap
                assert gap["severity"] in ["CRITICAL", "MODERATE", "LOW"]
                assert "explanation" in gap
                assert "suggested_action" in gap
                assert "negotiation_priority" in gap
                assert isinstance(gap["negotiation_priority"], int)
