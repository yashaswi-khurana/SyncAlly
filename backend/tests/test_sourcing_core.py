"""Unit and integration test suite for Milestone M1: Backend Sourcing Core Engine.

Verifies:
1. Pydantic v2 domain contracts (validation, immutability, serialization).
2. Bundled marketplace dataset (14 curated listings across 5 sectors, completeness tiers, filtering).
3. Local requirement interpreter (NLP extraction, structured overrides, edge cases).
4. Comparison scoring engine (5 weighted dimensions, composite 0-100%, Tier A-D, attribute matrix, ranking).
5. Gap taxonomy & detection (MISSING, AMBIGUOUS, NON_COMPLIANT with CRITICAL, MODERATE, LOW severities, mathematical deltas).
6. Seller inquiry drafting (targeted gap paragraphs, proposed compromises, zero-gap RFQs).
7. Sourcing orchestration service (end-to-end evaluation, error handling).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from syncally.application.sourcing.comparison_engine import ComparisonEngine
from syncally.application.sourcing.gap_analyzer import GapAnalyzer
from syncally.application.sourcing.inquiry_drafter import InquiryDrafter
from syncally.application.sourcing.interpreter import RequirementInterpreter
from syncally.application.sourcing.service import SourcingService
from syncally.domain.sourcing.contracts import (
    BuyerRequirements,
    CommercialGap,
    CommercialTermsRequirement,
    ComparisonStatus,
    DeliveryConstraint,
    GapCategory,
    GapSeverity,
    Incoterm,
    InquiryDraft,
    InspectionPreference,
    MatchTier,
    PaymentMethodPreference,
    PricingConstraint,
    QuantityRequirement,
    SourcingEvaluationReport,
    TechnicalSpecification,
)
from syncally.infrastructure.sourcing.bundled_dataset import (
    BUNDLED_MARKETPLACE_LISTINGS,
    get_bundled_listing_by_id,
    get_bundled_listings,
)

# =============================================================================
# 1. Domain Contracts Tests
# =============================================================================


class TestDomainContracts:
    """Verifies domain schemas, validations, and frozen immutability."""

    def test_technical_specification_instantiation(self) -> None:
        spec = TechnicalSpecification(
            materials=["316 Stainless Steel"],
            tolerances="+/- 0.05mm",
            certifications=["ISO 9001", "CE"],
            standards=["DIN 933"],
            quality_grade="A4-70",
        )
        assert spec.materials == ["316 Stainless Steel"]
        assert spec.tolerances == "+/- 0.05mm"
        assert "CE" in spec.certifications
        assert spec.standards == ["DIN 933"]
        assert spec.quality_grade == "A4-70"

        # Verify frozen immutability
        with pytest.raises(ValidationError):
            spec.tolerances = "+/- 0.1mm"  # type: ignore[misc]

    def test_pricing_constraint_validation(self) -> None:
        pricing = PricingConstraint(
            target_unit_price=Decimal("12.50"),
            max_unit_price=Decimal("15.00"),
            max_total_budget=Decimal("50000.00"),
            currency="USD",
        )
        assert pricing.target_unit_price == Decimal("12.50")
        assert pricing.currency == "USD"

        # Negative price should fail validation
        with pytest.raises(ValidationError):
            PricingConstraint(target_unit_price=Decimal("-5.00"))

        # Currency code must be exactly 3 characters
        with pytest.raises(ValidationError):
            PricingConstraint(currency="US_DOLLAR")

    def test_quantity_requirement_validation(self) -> None:
        qty = QuantityRequirement(
            target_quantity=Decimal("500"),
            unit="boxes",
        )
        assert qty.target_quantity == Decimal("500")
        assert qty.unit == "boxes"

        # Zero or negative target quantity should fail
        with pytest.raises(ValidationError):
            QuantityRequirement(target_quantity=Decimal("0"), unit="boxes")
        with pytest.raises(ValidationError):
            QuantityRequirement(target_quantity=Decimal("-10"), unit="boxes")

    def test_delivery_constraint_validation(self) -> None:
        deliv = DeliveryConstraint(
            destination_country_code="DE",
            destination_port_or_city="Hamburg",
            max_lead_time_days=25,
        )
        assert deliv.destination_country_code == "DE"
        assert deliv.destination_port_or_city == "Hamburg"
        assert deliv.max_lead_time_days == 25

        # Country code must be 2 letters
        with pytest.raises(ValidationError):
            DeliveryConstraint(destination_country_code="DEU")

    def test_commercial_terms_requirement_instantiation(self) -> None:
        ct = CommercialTermsRequirement(
            preferred_incoterm=Incoterm.DDP,
            acceptable_incoterms=[Incoterm.DDP, Incoterm.CIF],
            preferred_payment_term=PaymentMethodPreference.NET_30,
            min_warranty_months=24,
            inspection_requirement=InspectionPreference.FACTORY_MILL_CERTIFICATE,
        )
        assert ct.preferred_incoterm == Incoterm.DDP
        assert ct.min_warranty_months == 24

    def test_buyer_requirements_full_model(self) -> None:
        req = BuyerRequirements(
            title="M8 Hex Bolts Procurement",
            category="Industrial Fasteners",
            quantity=QuantityRequirement(target_quantity=Decimal("1000"), unit="boxes"),
            delivery=DeliveryConstraint(destination_country_code="DE"),
        )
        assert req.title == "M8 Hex Bolts Procurement"
        assert req.quantity.target_quantity == Decimal("1000")
        assert req.pricing.currency == "USD"
        assert req.commercial_terms.min_warranty_months == 12

    def test_commercial_gap_model(self) -> None:
        gap = CommercialGap(
            gap_id="gap-1",
            field_name="unit_price",
            category=GapCategory.NON_COMPLIANT,
            severity=GapSeverity.CRITICAL,
            buyer_requirement_value="Max $14.00 USD",
            seller_offered_value="$24.00 USD",
            explanation="Price exceeds ceiling by $10.00 (+71.4%).",
            suggested_action="Request volume discount.",
            negotiation_priority=1,
        )
        assert gap.category == GapCategory.NON_COMPLIANT
        assert gap.severity == GapSeverity.CRITICAL
        assert gap.negotiation_priority == 1


# =============================================================================
# 2. Bundled Dataset Tests
# =============================================================================


class TestBundledDataset:
    """Verifies realism, completeness tiers, and category distribution of bundled dataset."""

    def test_bundled_listings_count_and_sectors(self) -> None:
        assert len(BUNDLED_MARKETPLACE_LISTINGS) == 14

        categories = {item.category for item in BUNDLED_MARKETPLACE_LISTINGS}
        expected_categories = {
            "Industrial Fasteners",
            "Electronics & Electrical",
            "Agricultural Commodities",
            "Textiles & Fabrics",
            "Medical Supplies & PPE",
        }
        assert expected_categories.issubset(categories)

    def test_completeness_tiers_represented(self) -> None:
        tiers = {item.completeness_tier for item in BUNDLED_MARKETPLACE_LISTINGS}
        expected_tiers = {
            "FULL_COMPLETE",
            "PARTIAL_MISSING_LEAD_TIME_OR_TERMS",
            "AMBIGUOUS_SPECS_OR_TERMS",
            "NON_COMPLIANT_MOQ",
            "NON_COMPLIANT_PRICE",
            "NON_COMPLIANT_LEAD_TIME",
        }
        assert expected_tiers.issubset(tiers)

    def test_benchmark_complete_listing_integrity(self) -> None:
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000101")
        assert listing is not None
        assert listing.organization_name == "Berlin Fastener & Bolt GmbH"
        assert listing.country_code == "DE"
        assert listing.lead_time_days == 21
        assert Incoterm.DDP in listing.incoterms
        assert listing.warranty_months == 24
        assert "EN 10204 3.1" in (listing.inspection_terms or "")
        assert listing.completeness_tier == "FULL_COMPLETE"

    def test_incomplete_listing_attributes(self) -> None:
        # Listing 102 has missing lead time and missing incoterms
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000102")
        assert listing is not None
        assert listing.lead_time_days is None
        assert listing.incoterms == []
        assert listing.completeness_tier == "PARTIAL_MISSING_LEAD_TIME_OR_TERMS"

    def test_ambiguous_listing_attributes(self) -> None:
        # Listing 103 has ambiguous payment terms and ambiguous warranty
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000103")
        assert listing is not None
        assert "negotiable" in (listing.payment_terms or "").lower()
        assert listing.warranty_months is None
        assert "standard warranty" in (listing.warranty_description or "").lower()
        assert listing.completeness_tier == "AMBIGUOUS_SPECS_OR_TERMS"

    def test_filtering_by_category_and_completeness(self) -> None:
        fasteners = get_bundled_listings(category="Fasteners")
        assert len(fasteners) == 4
        assert all(f.category == "Industrial Fasteners" for f in fasteners)

        full_complete = get_bundled_listings(completeness="FULL_COMPLETE")
        assert len(full_complete) >= 5
        assert all(fc.completeness_tier == "FULL_COMPLETE" for fc in full_complete)

    def test_filtering_by_search_query(self) -> None:
        nitrile_results = get_bundled_listings(query="nitrile")
        assert len(nitrile_results) >= 1
        assert any("nitrile" in item.title.lower() for item in nitrile_results)

        unknown = get_bundled_listings(query="nonexistent_xyz_item")
        assert len(unknown) == 0


# =============================================================================
# 3. Requirement Interpreter Tests
# =============================================================================


class TestRequirementInterpreter:
    """Verifies local NLP parameter extraction and structured overrides."""

    def test_natural_language_full_extraction(self) -> None:
        prompt = (
            "We require 1,000 boxes of M8x30 Grade 316 Stainless Steel Hex Cap Bolts DIN 933. "
            "Must have ISO 9001, CE, and RoHS certifications. "
            "Target price $12.00 per box, ceiling max $14.00, total budget $15,000 USD. "
            "Need delivery within 30 days to Hamburg, Germany. "
            "Preferred freight DDP, Net 30 payment terms, 24 months warranty, EN 10204 3.1 mill test certificate."
        )

        req, parsed_fields = RequirementInterpreter.interpret(prompt)

        assert req.category == "Industrial Fasteners"
        assert req.quantity.target_quantity == Decimal("1000")
        assert req.quantity.unit == "boxes"
        assert req.pricing.target_unit_price == Decimal("12.00")
        assert req.pricing.max_unit_price == Decimal("14.00")
        assert req.pricing.max_total_budget == Decimal("15000.00")
        assert req.pricing.currency == "USD"
        assert "316 Stainless Steel" in req.technical_specs.materials
        assert "ISO 9001" in req.technical_specs.certifications
        assert "CE" in req.technical_specs.certifications
        assert "DIN 933" in req.technical_specs.standards
        assert req.delivery.destination_country_code == "DE"
        assert req.delivery.destination_port_or_city == "Hamburg"
        assert req.delivery.max_lead_time_days == 30
        assert req.commercial_terms.preferred_incoterm == Incoterm.DDP
        assert req.commercial_terms.preferred_payment_term == PaymentMethodPreference.NET_30
        assert req.commercial_terms.min_warranty_months == 24
        assert req.commercial_terms.inspection_requirement == InspectionPreference.FACTORY_MILL_CERTIFICATE

        assert "quantity" in parsed_fields
        assert "target_unit_price" in parsed_fields
        assert "max_lead_time_days" in parsed_fields

    def test_structured_overrides_take_priority(self) -> None:
        prompt = "Need 500 units of sensors for US delivery."
        overrides = {
            "title": "Custom High-Precision Sensor Order",
            "quantity": {"target_quantity": "2500", "unit": "units"},
            "pricing": {"target_unit_price": "35.00", "max_unit_price": "40.00", "currency": "USD"},
            "delivery": {"destination_country_code": "JP", "destination_port_or_city": "Tokyo", "max_lead_time_days": 14},
            "commercial_terms": {"preferred_incoterm": "CIF", "min_warranty_months": 36},
        }

        req, parsed_fields = RequirementInterpreter.interpret(prompt, structured_overrides=overrides)

        assert req.title == "Custom High-Precision Sensor Order"
        assert req.quantity.target_quantity == Decimal("2500")
        assert req.pricing.target_unit_price == Decimal("35.00")
        assert req.delivery.destination_country_code == "JP"
        assert req.delivery.destination_port_or_city == "Tokyo"
        assert req.delivery.max_lead_time_days == 14
        assert req.commercial_terms.preferred_incoterm == Incoterm.CIF
        assert req.commercial_terms.min_warranty_months == 36

    def test_empty_and_whitespace_prompt(self) -> None:
        req, parsed_fields = RequirementInterpreter.interpret("")
        assert req.quantity.target_quantity > 0
        assert req.pricing.currency == "USD"
        assert isinstance(req.title, str)

        req_space, _ = RequirementInterpreter.interpret("     \n\t   ")
        assert req_space.quantity.target_quantity > 0

    def test_relative_timescale_parsing(self) -> None:
        prompt = "Need 200 bags of coffee delivered in 4 weeks."
        req, _ = RequirementInterpreter.interpret(prompt)
        assert req.delivery.max_lead_time_days == 28


# =============================================================================
# 4. Comparison Scoring Engine Tests
# =============================================================================


class TestComparisonEngine:
    """Verifies 5-dimension scoring, composite calculation, match tiers, and comparison matrices."""

    @pytest.fixture
    def fastener_requirements(self) -> BuyerRequirements:
        req, _ = RequirementInterpreter.interpret(
            "Order for 1,000 boxes of M8x30 Grade 316 Stainless Steel Hex Cap Bolts DIN 933. "
            "ISO 9001, CE, RoHS certified. "
            "Target price $12.00/box, max $14.00 USD. "
            "Delivery within 30 days to Hamburg, Germany. "
            "Preferred DDP, Net 30 payment, 24 months warranty, EN 10204 3.1 mill test certificate."
        )
        return req

    def test_benchmark_full_match_scores_tier_a(self, fastener_requirements: BuyerRequirements) -> None:
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000101")
        assert listing is not None

        result = ComparisonEngine.evaluate_listing(fastener_requirements, listing)

        assert not result.is_disqualified
        assert result.composite_score >= 90.0
        assert result.tier == MatchTier.TIER_A
        assert result.score_breakdown.specifications >= 90.0
        assert result.score_breakdown.pricing == 100.0  # $11.50 <= $12.00 target
        assert result.score_breakdown.quantity_and_moq == 100.0
        assert result.score_breakdown.lead_time == 100.0  # 21 days <= (30 - 7)
        assert result.score_breakdown.commercial_terms >= 90.0

    def test_over_budget_penalty(self, fastener_requirements: BuyerRequirements) -> None:
        # Listing 105: Nordic Precision AeroSpares - $24.00/box vs max $14.00
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000105")
        assert listing is not None

        result = ComparisonEngine.evaluate_listing(fastener_requirements, listing)

        assert result.score_breakdown.pricing < 30.0
        assert result.composite_score < 75.0
        assert any(g.field_name == "unit_price" and g.severity == GapSeverity.CRITICAL for g in result.detected_gaps)

    def test_moq_barrier_penalty(self, fastener_requirements: BuyerRequirements) -> None:
        # Listing 104: Baltic Fastener Works - MOQ 5,000 vs buyer 1,000 (5x)
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000104")
        assert listing is not None

        result = ComparisonEngine.evaluate_listing(fastener_requirements, listing)

        # MOQ fit component gets 0 pts out of 50
        assert result.score_breakdown.quantity_and_moq <= 50.0
        assert any(g.field_name == "moq" and g.severity == GapSeverity.CRITICAL for g in result.detected_gaps)

    def test_category_mismatch_disqualification(self, fastener_requirements: BuyerRequirements) -> None:
        # Medical listing evaluated against fastener requirement
        medical_listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000108")
        assert medical_listing is not None

        result = ComparisonEngine.evaluate_listing(fastener_requirements, medical_listing)

        assert result.is_disqualified
        assert result.tier == MatchTier.TIER_D
        assert len(result.disqualification_reasons) > 0

    def test_attribute_comparison_matrix_structure(self, fastener_requirements: BuyerRequirements) -> None:
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000101")
        assert listing is not None

        result = ComparisonEngine.evaluate_listing(fastener_requirements, listing)

        assert len(result.attribute_comparisons) == 10
        field_names = [a.field_name for a in result.attribute_comparisons]
        expected_fields = [
            "product_specs",
            "materials_standards",
            "certifications",
            "unit_price",
            "quantity_and_moq",
            "lead_time",
            "incoterm",
            "payment_terms",
            "warranty",
            "inspection",
        ]
        assert field_names == expected_fields
        assert all(isinstance(a.status, ComparisonStatus) for a in result.attribute_comparisons)

    def test_multiple_listings_ranking(self, fastener_requirements: BuyerRequirements) -> None:
        all_listings = get_bundled_listings()
        ranked = ComparisonEngine.compare_multiple(fastener_requirements, all_listings)

        assert len(ranked) == 14
        # Top listing should be non-disqualified and high score
        assert not ranked[0].is_disqualified
        assert ranked[0].composite_score >= 85.0
        assert ranked[0].listing_id == "00000000-0000-4000-8000-000000000101"

        # Disqualified listings should be at the bottom
        assert ranked[-1].is_disqualified


# =============================================================================
# 5. Gap Taxonomy & Detection Engine Tests
# =============================================================================


class TestGapAnalyzer:
    """Verifies MISSING, AMBIGUOUS, and NON_COMPLIANT detection with exact deltas."""

    @pytest.fixture
    def buyer_req(self) -> BuyerRequirements:
        req, _ = RequirementInterpreter.interpret(
            "1,000 boxes of M8 bolts. Target price $12.00, max $14.00 USD. "
            "Delivery within 30 days to Hamburg, Germany. Preferred DDP. "
            "Net 30 payment, 24 months warranty, ISO 9001 and CE certified."
        )
        return req

    def test_missing_lead_time_and_incoterms_detection(self, buyer_req: BuyerRequirements) -> None:
        # Listing 102 has lead_time_days=None and incoterms=[]
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000102")
        assert listing is not None

        gaps = GapAnalyzer.detect_gaps(buyer_req, listing)
        gap_fields = {g.field_name: g for g in gaps}

        assert "lead_time_days" in gap_fields
        assert gap_fields["lead_time_days"].category == GapCategory.MISSING
        assert gap_fields["lead_time_days"].severity == GapSeverity.MODERATE

        assert "incoterms" in gap_fields
        assert gap_fields["incoterms"].category == GapCategory.MISSING

    def test_ambiguous_terms_detection(self, buyer_req: BuyerRequirements) -> None:
        # Listing 103 has ambiguous payment terms and ambiguous warranty
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000103")
        assert listing is not None

        gaps = GapAnalyzer.detect_gaps(buyer_req, listing)
        gap_fields = {g.field_name: g for g in gaps}

        assert "payment_terms" in gap_fields
        assert gap_fields["payment_terms"].category == GapCategory.AMBIGUOUS
        assert "negotiable" in gap_fields["payment_terms"].explanation.lower()

        assert "warranty_months" in gap_fields
        assert gap_fields["warranty_months"].category == GapCategory.AMBIGUOUS
        assert "standard" in gap_fields["warranty_months"].explanation.lower()

    def test_non_compliant_price_delta_calculation(self, buyer_req: BuyerRequirements) -> None:
        # Listing 105: Unit price $24.00 vs max $14.00
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000105")
        assert listing is not None

        gaps = GapAnalyzer.detect_gaps(buyer_req, listing)
        price_gap = next(g for g in gaps if g.field_name == "unit_price")

        assert price_gap.category == GapCategory.NON_COMPLIANT
        assert price_gap.severity == GapSeverity.CRITICAL
        assert "24.00" in price_gap.explanation
        assert "14.00" in price_gap.explanation
        assert "+71.4%" in price_gap.explanation

    def test_non_compliant_moq_delta_calculation(self, buyer_req: BuyerRequirements) -> None:
        # Listing 104: MOQ 5,000 vs buyer 1,000
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000104")
        assert listing is not None

        gaps = GapAnalyzer.detect_gaps(buyer_req, listing)
        moq_gap = next(g for g in gaps if g.field_name == "moq")

        assert moq_gap.category == GapCategory.NON_COMPLIANT
        assert moq_gap.severity == GapSeverity.CRITICAL
        assert "5000" in moq_gap.explanation
        assert "1000" in moq_gap.explanation
        assert "+400%" in moq_gap.explanation

    def test_non_compliant_lead_time_delta_calculation(self, buyer_req: BuyerRequirements) -> None:
        # Listing 107: Lead time 75 days vs buyer max 30 days
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000107")
        assert listing is not None

        gaps = GapAnalyzer.detect_gaps(buyer_req, listing)
        lt_gap = next(g for g in gaps if g.field_name == "lead_time_days")

        assert lt_gap.category == GapCategory.NON_COMPLIANT
        assert lt_gap.severity == GapSeverity.CRITICAL
        assert "75 days" in lt_gap.explanation
        assert "30 days" in lt_gap.explanation
        assert "45 days" in lt_gap.explanation


# =============================================================================
# 6. Seller Inquiry Drafter Tests
# =============================================================================


class TestInquiryDrafter:
    """Verifies targeted seller inquiry generation and compromise proposals."""

    @pytest.fixture
    def buyer_req(self) -> BuyerRequirements:
        req, _ = RequirementInterpreter.interpret(
            "1,000 boxes of M8 bolts. Target price $12.00, max $14.00 USD. "
            "Delivery within 30 days to Hamburg, Germany. Preferred DDP. "
            "Net 30 payment, 24 months warranty, ISO 9001 and CE certified."
        )
        return req

    def test_inquiry_targeting_high_moq_proposes_pilot_batch(self, buyer_req: BuyerRequirements) -> None:
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000104")
        assert listing is not None

        draft = InquiryDrafter.draft_inquiry(
            requirements=buyer_req,
            listing=listing,
            buyer_org_name="Global Fasteners Purchasing Corp",
            buyer_contact_name="Alex Schmidt",
        )

        assert "Alex Schmidt" in draft.body
        assert "Global Fasteners Purchasing Corp" in draft.body
        assert "pilot lot" in draft.body.lower() or "pilot batch" in draft.body.lower()
        assert any("moq" in g.lower() for g in draft.gaps_addressed)

    def test_inquiry_targeting_price_over_budget_proposes_volume_discount(self, buyer_req: BuyerRequirements) -> None:
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000105")
        assert listing is not None

        draft = InquiryDrafter.draft_inquiry(requirements=buyer_req, listing=listing)

        assert "volume" in draft.body.lower()
        assert "24.00 USD" in draft.body
        assert "12.00 USD" in draft.body or "14.00 USD" in draft.body

    def test_inquiry_price_gap_uses_explicit_non_usd_currency(self, buyer_req: BuyerRequirements) -> None:
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000105")
        assert listing is not None
        listing = listing.model_copy(update={"currency": "EUR"})
        req = buyer_req.model_copy(update={
            "pricing": PricingConstraint(
                target_unit_price=Decimal("12.00"), max_unit_price=Decimal("14.00"), currency="EUR"
            ),
        })

        draft = InquiryDrafter.draft_inquiry(requirements=req, listing=listing)

        assert "listed unit price is 24.00 EUR" in draft.body
        assert "budget target for this line item is 12.00 EUR" in draft.body
        assert "$" not in draft.body

    def test_inquiry_targeting_missing_lead_time_requests_confirmation(self, buyer_req: BuyerRequirements) -> None:
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000102")
        assert listing is not None

        draft = InquiryDrafter.draft_inquiry(requirements=buyer_req, listing=listing)

        assert "within 30 days" in draft.body.lower()
        assert any("lead_time_days" in g for g in draft.gaps_addressed)

    def test_inquiry_zero_gaps_generates_order_confirmation_rfq(self) -> None:
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000101")
        assert listing is not None

        # Build requirement exactly matching listing 101
        req = BuyerRequirements(
            title=listing.title,
            category=listing.category,
            quantity=QuantityRequirement(target_quantity=Decimal("1000"), unit="boxes"),
            pricing=PricingConstraint(target_unit_price=Decimal("12.00"), currency="USD"),
            delivery=DeliveryConstraint(destination_country_code="DE", max_lead_time_days=30),
            commercial_terms=CommercialTermsRequirement(
                preferred_incoterm=Incoterm.DDP,
                preferred_payment_term=PaymentMethodPreference.NET_30,
                min_warranty_months=24,
            ),
        )

        draft = InquiryDrafter.draft_inquiry(requirements=req, listing=listing, gaps=[])

        assert "appear to align" in draft.body.lower()
        assert "before we make any purchase commitment" in draft.body.lower()
        assert "immediate purchase order" not in draft.body.lower()
        assert len(draft.gaps_addressed) == 0

    def test_inquiry_does_not_fill_unspecified_price_or_trade_terms(self) -> None:
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000101")
        assert listing is not None
        req = BuyerRequirements(
            title=listing.title,
            category=listing.category,
            quantity=QuantityRequirement(target_quantity=Decimal("1000"), unit="boxes"),
            delivery=DeliveryConstraint(destination_country_code="DE"),
        )

        draft = InquiryDrafter.draft_inquiry(requirements=req, listing=listing, gaps=[])

        assert draft.proposed_terms["target_unit_price"] is None
        assert draft.proposed_terms["preferred_incoterm"] is None
        assert draft.proposed_terms["preferred_payment_term"] is None
        assert "no maximum lead time specified" in draft.body.lower()
        assert "no preferred incoterm specified" in draft.body.lower()
        assert "no preferred payment term specified" in draft.body.lower()
        assert "prepared to commit to an immediate purchase order" not in draft.body.lower()


# =============================================================================
# 7. Sourcing Service Integration Tests
# =============================================================================


class TestSourcingService:
    """Verifies end-to-end orchestration workflows in SourcingService."""

    def test_service_interpret_and_get_listings(self) -> None:
        req, parsed = SourcingService.interpret_requirements("1000 units of medical gloves")
        assert req.category == "Medical Supplies & PPE"
        assert req.quantity.target_quantity == Decimal("1000")

        listings = SourcingService.get_listings(category="Medical Supplies & PPE")
        assert len(listings) >= 2

    def test_service_compare_and_analyze_gaps(self) -> None:
        req, _ = SourcingService.interpret_requirements("500 boxes bolts under $14 USD")
        comparisons = SourcingService.compare_listings(req)
        assert len(comparisons) == 14

        listing, gaps, overall_severity = SourcingService.analyze_gaps(
            req, "00000000-0000-4000-8000-000000000105"
        )
        assert listing.id == "00000000-0000-4000-8000-000000000105"
        assert overall_severity == "CRITICAL"
        assert len(gaps) > 0

    def test_service_analyze_gaps_invalid_id_raises_value_error(self) -> None:
        req, _ = SourcingService.interpret_requirements("500 boxes bolts")
        with pytest.raises(ValueError, match="not found"):
            SourcingService.analyze_gaps(req, "invalid-uuid-999")

    def test_service_draft_inquiry_workflow(self) -> None:
        req, _ = SourcingService.interpret_requirements("1000 boxes bolts")
        draft = SourcingService.draft_inquiry(
            requirements=req,
            listing_id="00000000-0000-4000-8000-000000000101",
            buyer_org_name="Test Enterprise Buyer",
        )
        assert isinstance(draft, InquiryDraft)
        assert "Test Enterprise Buyer" in draft.body

    def test_service_end_to_end_evaluate(self) -> None:
        prompt = (
            "We want to purchase 1,000 boxes of M8 hex bolts in 316 stainless steel. "
            "Target price $12.00, budget ceiling $14.00 USD. "
            "Delivery within 30 days to Hamburg, Germany."
        )
        report = SourcingService.evaluate(
            prompt=prompt,
            buyer_org_name="Hamburg Assembly Works GmbH",
        )

        assert isinstance(report, SourcingEvaluationReport)
        assert report.total_listings_evaluated == 14
        assert len(report.comparisons) == 14
        assert len(report.inquiries) == 14

        # Top comparison should be Tier A or B
        top_comp = report.comparisons[0]
        assert not top_comp.is_disqualified
        assert top_comp.tier in (MatchTier.TIER_A, MatchTier.TIER_B)

        # Inquiries dictionary maps listing IDs to InquiryDrafts
        top_inquiry = report.inquiries[top_comp.listing_id]
        assert top_inquiry.seller_organization_name == top_comp.seller_organization_name
        assert "Hamburg Assembly Works GmbH" in top_inquiry.body
