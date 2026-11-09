"""Adversarial stress-testing suite for Milestone M1 (Buyer Sourcing Core Engine).

Author: challenger_sourcing_m1_1
Purpose: Adversarial validation of scoring boundaries, category mismatch disqualification,
         numerical extremes, negative schema rejection, execution determinism,
         and boundary vulnerability analysis.
"""

from __future__ import annotations

import hashlib
import random
from decimal import Decimal

import pydantic
import pytest

from syncally.application.sourcing.comparison_engine import ComparisonEngine
from syncally.application.sourcing.gap_analyzer import GapAnalyzer
from syncally.application.sourcing.interpreter import RequirementInterpreter
from syncally.application.sourcing.service import SourcingService
from syncally.domain.sourcing.contracts import (
    BuyerRequirements,
    CommercialTermsRequirement,
    DeliveryConstraint,
    GapCategory,
    Incoterm,
    MarketplaceListingDetail,
    MatchTier,
    PaymentMethodPreference,
    PricingConstraint,
    QuantityRequirement,
)
from syncally.infrastructure.sourcing.bundled_dataset import (
    get_bundled_listings,
)

# =============================================================================
# Helper Fixtures
# =============================================================================

@pytest.fixture
def baseline_requirements() -> BuyerRequirements:
    return BuyerRequirements(
        title="M8 Hex Cap Screws DIN 933",
        category="Industrial Fasteners",
        quantity=QuantityRequirement(target_quantity=Decimal("1000"), unit="boxes"),
        delivery=DeliveryConstraint(destination_country_code="DE", max_lead_time_days=30),
        pricing=PricingConstraint(
            target_unit_price=Decimal("12.00"),
            max_unit_price=Decimal("15.00"),
            currency="USD",
        ),
        commercial_terms=CommercialTermsRequirement(
            preferred_incoterm=Incoterm.DDP,
            preferred_payment_term=PaymentMethodPreference.NET_30,
            min_warranty_months=12,
        ),
    )


@pytest.fixture
def baseline_listing() -> MarketplaceListingDetail:
    listings = get_bundled_listings(category="Industrial Fasteners")
    assert len(listings) > 0
    return listings[0]


# =============================================================================
# 1. Scoring Boundaries Stress Tests
# =============================================================================

class TestScoringBoundaries:
    """Rigorous verification that all dimension sub-scores and composite scores stay within [0.0, 100.0]."""

    def test_randomized_fuzzing_1000_iterations(self):
        """Stress-test 1,000 randomized combinatorial permutations of buyer & seller parameters."""
        random.seed(1337)
        prices = [Decimal("0.01"), Decimal("0.50"), Decimal("10.00"), Decimal("9999.99"), Decimal("10000000.00")]
        quantities = [Decimal("0.0001"), Decimal("1"), Decimal("1000"), Decimal("100000000")]
        lead_times = [0, 1, 7, 30, 90, 365, 10000]

        for i in range(1000):
            p_req = random.choice(prices)
            p_max = p_req * Decimal(str(random.choice([1.0, 1.2, 2.0, 5.0])))
            p_sell = random.choice([Decimal("0.00")] + prices)

            q_req = random.choice(quantities)
            q_avail = random.choice(quantities)
            moq = random.choice([None] + quantities)

            lt_req = random.choice(lead_times[1:])
            lt_sell = random.choice([None] + lead_times)

            req = BuyerRequirements(
                title=random.choice(["Bolt", "Cotton", "Glove", "Sensor", "Soybean"]),
                category=random.choice([
                    "Industrial Fasteners",
                    "Electronics & Electrical",
                    "Agricultural Commodities",
                    "Textiles & Fabrics",
                    "Medical Supplies & PPE",
                    "Unknown Domain",
                ]),
                quantity=QuantityRequirement(target_quantity=q_req, unit="units"),
                delivery=DeliveryConstraint(destination_country_code="DE", max_lead_time_days=lt_req),
                pricing=PricingConstraint(target_unit_price=p_req, max_unit_price=p_max, currency=random.choice(["USD", "EUR"])),
                commercial_terms=CommercialTermsRequirement(
                    preferred_incoterm=random.choice(list(Incoterm)),
                    preferred_payment_term=random.choice(list(PaymentMethodPreference)),
                ),
            )

            listing = MarketplaceListingDetail(
                id=f"fuzz-{i}",
                organization_id=f"org-{i}",
                organization_name=f"Seller {i}",
                country_code="DE",
                title=random.choice(["DIN 933 Hex Bolt", "Cotton Fabric", "Nitrile Gloves", "Unrelated Item"]),
                category=random.choice([
                    "Industrial Fasteners",
                    "Electronics & Electrical",
                    "Agricultural Commodities",
                    "Textiles & Fabrics",
                    "Medical Supplies & PPE",
                ]),
                available_quantity=q_avail,
                moq=moq,
                unit="units",
                unit_price=p_sell,
                currency="USD",
                lead_time_days=lt_sell,
                incoterms=[random.choice(list(Incoterm))],
                payment_terms=random.choice(["Net 30", "100% upfront", "30/70 split", None]),
            )

            res = ComparisonEngine.evaluate_listing(req, listing)
            sb = res.score_breakdown

            # Assert every subscore is within [0.0, 100.0]
            assert 0.0 <= sb.specifications <= 100.0, f"Specifications score {sb.specifications} out of bounds on iter {i}"
            assert 0.0 <= sb.pricing <= 100.0, f"Pricing score {sb.pricing} out of bounds on iter {i}"
            assert 0.0 <= sb.quantity_and_moq <= 100.0, f"Quantity score {sb.quantity_and_moq} out of bounds on iter {i}"
            assert 0.0 <= sb.lead_time <= 100.0, f"Lead time score {sb.lead_time} out of bounds on iter {i}"
            assert 0.0 <= sb.commercial_terms <= 100.0, f"Commercial terms score {sb.commercial_terms} out of bounds on iter {i}"
            assert 0.0 <= res.composite_score <= 100.0, f"Composite score {res.composite_score} out of bounds on iter {i}"

    def test_extreme_pricing_scores_bounded(self, baseline_requirements, baseline_listing):
        """Pricing scores must stay bounded when seller price is 1000x over budget."""
        huge_price_listing = baseline_listing.model_copy(update={"unit_price": Decimal("10000000.00")})
        res = ComparisonEngine.evaluate_listing(baseline_requirements, huge_price_listing)
        assert res.score_breakdown.pricing == 0.0
        assert 0.0 <= res.composite_score <= 100.0

    def test_extreme_lead_time_delay_bounded(self, baseline_requirements, baseline_listing):
        """Lead time score must stay at 0.0 and never go negative when delayed by 10,000 days."""
        delayed_listing = baseline_listing.model_copy(update={"lead_time_days": 10000})
        res = ComparisonEngine.evaluate_listing(baseline_requirements, delayed_listing)
        assert res.score_breakdown.lead_time == 0.0
        assert 0.0 <= res.composite_score <= 100.0

    def test_zero_lead_time_instant_dispatch(self, baseline_requirements, baseline_listing):
        """0 days lead time (instant dispatch) must receive maximum score (100.0)."""
        instant_listing = baseline_listing.model_copy(update={"lead_time_days": 0})
        res = ComparisonEngine.evaluate_listing(baseline_requirements, instant_listing)
        assert res.score_breakdown.lead_time == 100.0
        assert 0.0 <= res.composite_score <= 100.0


# =============================================================================
# 2. Category Mismatch Disqualification Tests
# =============================================================================

class TestCategoryMismatchDisqualification:
    """Verifies that completely disjoint categories trigger disqualification."""

    def test_cross_sector_disqualification(self):
        """Buyer requests Medical Supplies; candidate listing is Industrial Fasteners."""
        req = BuyerRequirements(
            title="Sterile Surgical Scalpels No. 10",
            category="Medical Supplies & PPE",
            quantity=QuantityRequirement(target_quantity=Decimal("500"), unit="boxes"),
            delivery=DeliveryConstraint(destination_country_code="US"),
            pricing=PricingConstraint(target_unit_price=Decimal("15.00")),
        )

        listing = MarketplaceListingDetail(
            id="bolt-test-01",
            organization_id="org-bolt",
            organization_name="Bolt Corp",
            country_code="DE",
            title="DIN 933 Hex Head Machine Bolt Grade 8.8",
            category="Industrial Fasteners",
            available_quantity=Decimal("50000"),
            unit="boxes",
            unit_price=Decimal("12.00"),
        )

        res = ComparisonEngine.evaluate_listing(req, listing)
        assert res.is_disqualified is True
        assert len(res.disqualification_reasons) > 0
        assert "Irrelevant product category" in res.disqualification_reasons[0]
        assert res.tier == MatchTier.TIER_D
        assert res.score_breakdown.specifications <= 10.0

    def test_disqualified_candidate_ranking_priority(self):
        """Disqualified candidate must rank below non-disqualified candidate even if score is higher."""
        req = BuyerRequirements(
            title="Nitrile Examination Gloves",
            category="Medical Supplies & PPE",
            quantity=QuantityRequirement(target_quantity=Decimal("500"), unit="boxes"),
            delivery=DeliveryConstraint(destination_country_code="US"),
            pricing=PricingConstraint(target_unit_price=Decimal("15.00")),
        )

        # Disqualified candidate has higher subscores in price/qty
        disqualified_listing = MarketplaceListingDetail(
            id="disqualified-fastener",
            organization_id="org-1",
            organization_name="Bolt Factory",
            country_code="DE",
            title="DIN 933 Hex Head Machine Bolt Grade 8.8",
            category="Industrial Fasteners",
            available_quantity=Decimal("50000"),
            unit="boxes",
            unit_price=Decimal("12.00"),
        )

        # Relevant candidate has lower pricing score
        relevant_listing = MarketplaceListingDetail(
            id="relevant-gloves",
            organization_id="org-2",
            organization_name="Glove Factory",
            country_code="MY",
            title="Nitrile Gloves Powder Free",
            category="Medical Supplies & PPE",
            available_quantity=Decimal("1000"),
            unit="boxes",
            unit_price=Decimal("18.00"),
        )

        results = ComparisonEngine.compare_multiple(req, [disqualified_listing, relevant_listing])
        assert results[0].listing_id == "relevant-gloves"
        assert results[0].is_disqualified is False
        assert results[1].listing_id == "disqualified-fastener"
        assert results[1].is_disqualified is True

    def test_all_5_sectors_cross_disqualification(self):
        """Ensure all 5 sectors cleanly disqualify candidates from any of the other 4 sectors."""
        sectors = [
            ("Industrial Fasteners", "M8 Hex Bolts"),
            ("Electronics & Electrical", "Shielded Sensor Cable"),
            ("Agricultural Commodities", "Non-GMO Milling Wheat"),
            ("Textiles & Fabrics", "100% Cotton Canvas"),
            ("Medical Supplies & PPE", "Nitrile Gloves Examination"),
        ]

        for b_idx, (b_cat, b_title) in enumerate(sectors):
            for s_idx, (s_cat, s_title) in enumerate(sectors):
                if b_idx == s_idx:
                    continue
                req = BuyerRequirements(
                    title=b_title,
                    category=b_cat,
                    quantity=QuantityRequirement(target_quantity=Decimal("1000"), unit="units"),
                    delivery=DeliveryConstraint(destination_country_code="DE"),
                )
                listing = MarketplaceListingDetail(
                    id=f"sec-{b_idx}-{s_idx}",
                    organization_id="org-test",
                    organization_name="Seller Test",
                    country_code="DE",
                    title=s_title,
                    category=s_cat,
                    available_quantity=Decimal("10000"),
                    unit="units",
                    unit_price=Decimal("10.00"),
                )
                res = ComparisonEngine.evaluate_listing(req, listing)
                assert res.is_disqualified is True, f"Failed to disqualify {s_cat} against {b_cat}"
                assert res.tier == MatchTier.TIER_D


# =============================================================================
# 3. Extremes and Schema Rejections Tests
# =============================================================================

class TestExtremesAndSchemaRejections:
    """Verifies handling of numerical extremes and schema validation on negative values."""

    def test_listing_unit_price_zero_handled_as_missing(self, baseline_requirements):
        """Seller listing with unit_price = $0.00 is treated as missing quotation without crashing."""
        free_listing = MarketplaceListingDetail(
            id="zero-price-listing",
            organization_id="org-free",
            organization_name="Sample Supply Co",
            country_code="DE",
            title="Free Fastener Samples",
            category="Industrial Fasteners",
            available_quantity=Decimal("1000"),
            unit="boxes",
            unit_price=Decimal("0.00"),
        )
        gaps = GapAnalyzer.detect_gaps(baseline_requirements, free_listing)
        price_gaps = [g for g in gaps if g.field_name == "unit_price"]
        assert len(price_gaps) == 1
        assert price_gaps[0].category == GapCategory.MISSING

        res = ComparisonEngine.evaluate_listing(baseline_requirements, free_listing)
        assert res.score_breakdown.pricing == 10.0
        assert 0.0 <= res.composite_score <= 100.0

    def test_extreme_high_price_ten_million(self):
        """$10,000,000 unit price operates smoothly without overflow."""
        req, _ = RequirementInterpreter.interpret("Need 100 boxes target price $10000000.00 delivery to Hamburg")
        assert req.pricing.target_unit_price == Decimal("10000000.00")

        report = SourcingService.evaluate(requirements=req)
        assert report.total_listings_evaluated == 14
        assert report.comparisons[0].score_breakdown.pricing == 100.0

    def test_extreme_high_quantity_one_hundred_million(self):
        """100,000,000 order quantity evaluates stock capacity and MOQ deltas smoothly."""
        req = BuyerRequirements(
            title="Bulk Fasteners",
            category="Industrial Fasteners",
            quantity=QuantityRequirement(target_quantity=Decimal("100000000"), unit="boxes"),
            delivery=DeliveryConstraint(destination_country_code="DE"),
            pricing=PricingConstraint(target_unit_price=Decimal("10.00")),
        )
        report = SourcingService.evaluate(requirements=req)
        assert report.total_listings_evaluated == 14
        for comp in report.comparisons:
            assert 0.0 <= comp.score_breakdown.quantity_and_moq <= 55.0
            # Every candidate has < 100M units available, so available_quantity gap must be detected
            gap_fields = {g.field_name for g in comp.detected_gaps}
            assert "available_quantity" in gap_fields

    def test_fractional_quantities(self):
        """Fractional quantities (0.0001 and 123.456) preserve Decimal precision."""
        req_small = BuyerRequirements(
            title="Agricultural Commodities Bulk",
            category="Agricultural Commodities",
            quantity=QuantityRequirement(target_quantity=Decimal("0.0001"), unit="metric tons"),
            delivery=DeliveryConstraint(destination_country_code="DE"),
            pricing=PricingConstraint(target_unit_price=Decimal("500.00")),
        )
        res_small = SourcingService.evaluate(requirements=req_small)
        assert res_small.total_listings_evaluated == 14

        req_fractional = BuyerRequirements(
            title="Agricultural Commodities Bulk",
            category="Agricultural Commodities",
            quantity=QuantityRequirement(target_quantity=Decimal("123.456"), unit="metric tons"),
            delivery=DeliveryConstraint(destination_country_code="DE"),
            pricing=PricingConstraint(target_unit_price=Decimal("500.00")),
        )
        res_fractional = SourcingService.evaluate(requirements=req_fractional)
        assert res_fractional.total_listings_evaluated == 14

    def test_all_14_negative_schema_rejections(self):
        """Empirically prove all 14 negative / zero boundary rules are rejected by Pydantic."""
        rejected_count = 0

        # 1. target_unit_price < 0
        with pytest.raises(pydantic.ValidationError):
            PricingConstraint(target_unit_price=Decimal("-0.01"))
        rejected_count += 1

        # 2. max_unit_price < 0
        with pytest.raises(pydantic.ValidationError):
            PricingConstraint(max_unit_price=Decimal("-1.00"))
        rejected_count += 1

        # 3. max_total_budget < 0
        with pytest.raises(pydantic.ValidationError):
            PricingConstraint(max_total_budget=Decimal("-500.00"))
        rejected_count += 1

        # 4. target_quantity < 0
        with pytest.raises(pydantic.ValidationError):
            QuantityRequirement(target_quantity=Decimal("-10"), unit="units")
        rejected_count += 1

        # 5. target_quantity == 0
        with pytest.raises(pydantic.ValidationError):
            QuantityRequirement(target_quantity=Decimal("0"), unit="units")
        rejected_count += 1

        # 6. min_acceptable_quantity < 0
        with pytest.raises(pydantic.ValidationError):
            QuantityRequirement(target_quantity=Decimal("10"), min_acceptable_quantity=Decimal("-1"), unit="units")
        rejected_count += 1

        # 7. max_lead_time_days < 0
        with pytest.raises(pydantic.ValidationError):
            DeliveryConstraint(destination_country_code="DE", max_lead_time_days=-15)
        rejected_count += 1

        # 8. max_lead_time_days == 0
        with pytest.raises(pydantic.ValidationError):
            DeliveryConstraint(destination_country_code="DE", max_lead_time_days=0)
        rejected_count += 1

        # 9. min_warranty_months < 0
        with pytest.raises(pydantic.ValidationError):
            CommercialTermsRequirement(min_warranty_months=-6)
        rejected_count += 1

        # 10. listing unit_price < 0
        with pytest.raises(pydantic.ValidationError):
            MarketplaceListingDetail(
                id="neg-price", organization_id="o1", organization_name="O", country_code="DE",
                title="T", category="C", available_quantity=Decimal("10"), unit="u",
                unit_price=Decimal("-5.00")
            )
        rejected_count += 1

        # 11. listing available_quantity < 0
        with pytest.raises(pydantic.ValidationError):
            MarketplaceListingDetail(
                id="neg-avail", organization_id="o1", organization_name="O", country_code="DE",
                title="T", category="C", available_quantity=Decimal("-10"), unit="u",
                unit_price=Decimal("1.00")
            )
        rejected_count += 1

        # 12. listing moq < 0
        with pytest.raises(pydantic.ValidationError):
            MarketplaceListingDetail(
                id="neg-moq", organization_id="o1", organization_name="O", country_code="DE",
                title="T", category="C", available_quantity=Decimal("10"), moq=Decimal("-1"), unit="u",
                unit_price=Decimal("1.00")
            )
        rejected_count += 1

        # 13. listing lead_time_days < 0
        with pytest.raises(pydantic.ValidationError):
            MarketplaceListingDetail(
                id="neg-lt", organization_id="o1", organization_name="O", country_code="DE",
                title="T", category="C", available_quantity=Decimal("10"), unit="u",
                unit_price=Decimal("1.00"), lead_time_days=-1
            )
        rejected_count += 1

        # 14. listing warranty_months < 0
        with pytest.raises(pydantic.ValidationError):
            MarketplaceListingDetail(
                id="neg-w", organization_id="o1", organization_name="O", country_code="DE",
                title="T", category="C", available_quantity=Decimal("10"), unit="u",
                unit_price=Decimal("1.00"), warranty_months=-1
            )
        rejected_count += 1

        assert rejected_count == 14

    def test_zero_target_unit_price_division_by_zero_vulnerability(self, baseline_listing):
        """VERIFY RESILIENCE TO ZERO TARGET PRICE:

        When buyer specifies target_unit_price = Decimal('0.00'), which is accepted
        by the schema (ge=0), GapAnalyzer and ComparisonEngine handle it safely without DivisionByZero.
        """
        zero_price_req = BuyerRequirements(
            title="Zero Price Procurement Request",
            category="Industrial Fasteners",
            quantity=QuantityRequirement(target_quantity=Decimal("1000"), unit="boxes"),
            delivery=DeliveryConstraint(destination_country_code="DE"),
            pricing=PricingConstraint(target_unit_price=Decimal("0.00")),
        )

        # GapAnalyzer must handle zero target price without ArithmeticError
        gaps = GapAnalyzer.detect_gaps(zero_price_req, baseline_listing)
        assert isinstance(gaps, list)

        # ComparisonEngine must evaluate without ArithmeticError
        evaluation = ComparisonEngine.evaluate_listing(zero_price_req, baseline_listing)
        assert evaluation is not None
        assert evaluation.composite_score >= 0


# =============================================================================
# 4. Local Execution Determinism Tests
# =============================================================================

class TestExecutionDeterminism:
    """Verifies that 100 consecutive executions produce 100% identical outputs and hashes."""

    @pytest.mark.parametrize("prompt", [
        "RFQ: 2500 boxes DIN 933 A4-70 hex cap screws target price $35.00 delivery in 21 days to Hamburg",
        "Need 500 metric tons non-GMO soybeans bulk delivery in 45 days to Rotterdam target price $480.00 per mt",
        "Procure 10,000 boxes powder-free nitrile examination gloves CE certified delivery within 14 days to Chicago",
    ])
    def test_100_iterations_exact_hash_match(self, prompt: str):
        """100 iterations of SourcingService.evaluate on the same prompt produce identical sha256 hashes."""
        hashes: set[str] = set()

        for _ in range(100):
            report = SourcingService.evaluate(prompt=prompt)
            payload = report.model_dump_json(indent=None)
            h = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            hashes.add(h)

        assert len(hashes) == 1, f"Determinism failure: expected 1 unique hash, got {len(hashes)}"
