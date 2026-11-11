"""Adversarial challenger test suite for Milestone M1 Sourcing Engine.

Empirically verifies:
1. All 14 bundled marketplace listings across all 6 completeness tiers produce expected gap classifications.
2. Every detected gap is properly reflected in generated seller inquiry letters across single and multi-gap combinations.
3. Zero-gap listings generate valid purchase commitment RFQs with complete commercial framework.
4. Compromise logic generates actionable proposals:
   - Pilot lots for high MOQ barriers
   - Volume discounts for over-budget pricing
   - Expedited shipping / priority shifts for lead time bottlenecks
   - Escrow / milestone payment compromises for advance payment demands
5. Stress / boundary tests: extreme numbers, currency divergence, unicode handling, and thread concurrency.
"""

from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

from syncally.application.sourcing.gap_analyzer import GapAnalyzer
from syncally.application.sourcing.inquiry_drafter import InquiryDrafter
from syncally.domain.sourcing.contracts import (
    BuyerRequirements,
    CommercialGap,
    CommercialTermsRequirement,
    DeliveryConstraint,
    GapCategory,
    GapSeverity,
    Incoterm,
    InquiryDraft,
    InspectionPreference,
    MarketplaceListingDetail,
    PaymentMethodPreference,
    PricingConstraint,
    QuantityRequirement,
    TechnicalSpecification,
)
from syncally.infrastructure.sourcing.bundled_dataset import (
    BUNDLED_MARKETPLACE_LISTINGS,
    get_bundled_listing_by_id,
)

# =============================================================================
# Helper Fixtures & Builders
# =============================================================================


def build_compliant_requirements_for_listing(listing: MarketplaceListingDetail) -> BuyerRequirements:
    """Construct a BuyerRequirements object perfectly aligned with the given listing's parameters."""
    return BuyerRequirements(
        title=f"Procurement for {listing.title}",
        category=listing.category,
        description="Standard compliant requirements for benchmarking zero-gap baseline.",
        technical_specs=TechnicalSpecification(
            materials=list(listing.technical_specs.materials),
            tolerances=listing.technical_specs.tolerances,
            certifications=list(listing.technical_specs.certifications),
            standards=list(listing.technical_specs.standards),
            quality_grade=listing.technical_specs.quality_grade,
        ),
        pricing=PricingConstraint(
            target_unit_price=listing.unit_price,
            max_unit_price=listing.unit_price * Decimal("1.20"),
            currency=listing.currency,
        ),
        quantity=QuantityRequirement(
            target_quantity=listing.moq if listing.moq is not None else Decimal("100"),
            unit=listing.unit,
        ),
        delivery=DeliveryConstraint(
            destination_country_code="DE" if listing.country_code != "DE" else "US",
            destination_port_or_city="Rotterdam Port",
            max_lead_time_days=listing.lead_time_days if listing.lead_time_days is not None else 30,
        ),
        commercial_terms=CommercialTermsRequirement(
            preferred_incoterm=listing.incoterms[0] if listing.incoterms else Incoterm.DDP,
            acceptable_incoterms=list(listing.incoterms) if listing.incoterms else [Incoterm.DDP],
            preferred_payment_term=PaymentMethodPreference.ESCROW,
            min_warranty_months=listing.warranty_months if listing.warranty_months is not None else 12,
            inspection_requirement=InspectionPreference.FACTORY_MILL_CERTIFICATE,
        ),
    )


# =============================================================================
# 1. Verification of All 14 Bundled Listings across 6 Completeness Tiers
# =============================================================================


class TestAll14BundledListingsGapClassification:
    """Verifies that all 14 bundled marketplace listings across all 6 tiers produce expected gap classifications."""

    def test_listing_count_and_tier_distribution(self) -> None:
        """Verify the dataset contains exactly 14 listings covering all 6 completeness tiers."""
        assert len(BUNDLED_MARKETPLACE_LISTINGS) == 14

        tiers_found = {item.completeness_tier for item in BUNDLED_MARKETPLACE_LISTINGS}
        expected_tiers = {
            "FULL_COMPLETE",
            "PARTIAL_MISSING_LEAD_TIME_OR_TERMS",
            "AMBIGUOUS_SPECS_OR_TERMS",
            "NON_COMPLIANT_MOQ",
            "NON_COMPLIANT_PRICE",
            "NON_COMPLIANT_LEAD_TIME",
        }
        assert tiers_found == expected_tiers, f"Missing tiers: {expected_tiers - tiers_found}"

    @pytest.mark.parametrize(
        "listing_id",
        [
            "00000000-0000-4000-8000-000000000101",  # Berlin Fastener (Fasteners)
            "00000000-0000-4000-8000-000000000109",  # Silicon Valley Sensors (Electronics)
            "00000000-0000-4000-8000-000000000110",  # Sao Paulo Agri (Agri)
            "00000000-0000-4000-8000-000000000113",  # Istanbul Technical (Textiles)
            "00000000-0000-4000-8000-000000000108",  # MediShield (Medical)
        ],
    )
    def test_full_complete_listings_zero_gap_baseline(self, listing_id: str) -> None:
        """FULL_COMPLETE listings evaluated against matching buyer requirements yield 0 gaps."""
        listing = get_bundled_listing_by_id(listing_id)
        assert listing is not None
        assert listing.completeness_tier == "FULL_COMPLETE"

        req = build_compliant_requirements_for_listing(listing)
        gaps = GapAnalyzer.detect_gaps(req, listing)
        assert gaps == [], f"Listing {listing_id} expected 0 gaps but found: {[g.field_name for g in gaps]}"

    def test_partial_missing_listing_102(self) -> None:
        """Apex Hardware (102) has missing lead_time_days, empty incoterms, and advance deposit."""
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000102")
        assert listing is not None
        assert listing.completeness_tier == "PARTIAL_MISSING_LEAD_TIME_OR_TERMS"

        req = BuyerRequirements(
            title="M8 Hex Bolts",
            category="Industrial Fasteners",
            quantity=QuantityRequirement(target_quantity=Decimal("500"), unit="boxes"),
            delivery=DeliveryConstraint(destination_country_code="US", max_lead_time_days=30),
            commercial_terms=CommercialTermsRequirement(
                preferred_incoterm=Incoterm.DDP,
                preferred_payment_term=PaymentMethodPreference.NET_30,
            ),
        )
        gaps = GapAnalyzer.detect_gaps(req, listing)
        missing_fields = {g.field_name: g.category for g in gaps}

        # Must detect missing lead time and missing incoterms
        assert "lead_time_days" in missing_fields
        assert missing_fields["lead_time_days"] == GapCategory.MISSING
        assert "incoterms" in missing_fields
        assert missing_fields["incoterms"] == GapCategory.MISSING
        # Payment terms is advance deposit vs Net 30 -> NON_COMPLIANT
        assert "payment_terms" in missing_fields
        assert missing_fields["payment_terms"] == GapCategory.NON_COMPLIANT

    def test_partial_missing_listing_112(self) -> None:
        """Valley Organic Farms (112) has missing inspection_terms."""
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000112")
        assert listing is not None
        assert listing.completeness_tier == "PARTIAL_MISSING_LEAD_TIME_OR_TERMS"

        req = BuyerRequirements(
            title="Organic Arabica Green Coffee",
            category="Agricultural Commodities",
            quantity=QuantityRequirement(target_quantity=Decimal("100"), unit="bags"),
            delivery=DeliveryConstraint(destination_country_code="US", max_lead_time_days=45),
            commercial_terms=CommercialTermsRequirement(
                preferred_incoterm=Incoterm.FOB,
                preferred_payment_term=PaymentMethodPreference.NET_30,
                inspection_requirement=InspectionPreference.PRE_SHIPMENT_THIRD_PARTY,
            ),
        )
        gaps = GapAnalyzer.detect_gaps(req, listing)
        missing_fields = {g.field_name: g.category for g in gaps}

        assert "inspection_terms" in missing_fields
        assert missing_fields["inspection_terms"] == GapCategory.MISSING

    def test_ambiguous_listing_103(self) -> None:
        """Tokyo Micro-Conductor (103) has ambiguous payment, ambiguous warranty, and vague inspection."""
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000103")
        assert listing is not None
        assert listing.completeness_tier == "AMBIGUOUS_SPECS_OR_TERMS"

        req = BuyerRequirements(
            title="Copper Wire Harness",
            category="Electronics & Electrical",
            quantity=QuantityRequirement(target_quantity=Decimal("1000"), unit="units"),
            delivery=DeliveryConstraint(destination_country_code="JP", max_lead_time_days=30),
            commercial_terms=CommercialTermsRequirement(
                preferred_incoterm=Incoterm.FOB,
                preferred_payment_term=PaymentMethodPreference.NET_30,
                min_warranty_months=12,
            ),
        )
        gaps = GapAnalyzer.detect_gaps(req, listing)
        gap_map = {g.field_name: g.category for g in gaps}

        assert gap_map.get("payment_terms") == GapCategory.AMBIGUOUS
        assert gap_map.get("warranty_months") == GapCategory.AMBIGUOUS
        assert gap_map.get("inspection_terms") == GapCategory.AMBIGUOUS

    def test_ambiguous_listing_111(self) -> None:
        """Danubian Grains (111) has missing lead time and ambiguous payment/warranty terms."""
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000111")
        assert listing is not None
        assert listing.completeness_tier == "AMBIGUOUS_SPECS_OR_TERMS"

        req = BuyerRequirements(
            title="High Protein Milling Wheat",
            category="Agricultural Commodities",
            quantity=QuantityRequirement(target_quantity=Decimal("500"), unit="metric tons"),
            delivery=DeliveryConstraint(destination_country_code="RO", max_lead_time_days=30),
            commercial_terms=CommercialTermsRequirement(
                preferred_incoterm=Incoterm.FOB,
                preferred_payment_term=PaymentMethodPreference.NET_30,
                min_warranty_months=6,
            ),
        )
        gaps = GapAnalyzer.detect_gaps(req, listing)
        gap_map = {g.field_name: g.category for g in gaps}

        assert gap_map.get("lead_time_days") == GapCategory.MISSING
        assert gap_map.get("payment_terms") == GapCategory.AMBIGUOUS
        assert gap_map.get("warranty_months") == GapCategory.AMBIGUOUS

    def test_ambiguous_listing_106(self) -> None:
        """Lancashire Weaving (106) has restrictive EXW, missing lead time, ambiguous export payment, missing warranty."""
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000106")
        assert listing is not None
        assert listing.completeness_tier == "AMBIGUOUS_SPECS_OR_TERMS"

        req = BuyerRequirements(
            title="Heavy Industrial Canvas",
            category="Textiles & Fabrics",
            quantity=QuantityRequirement(target_quantity=Decimal("2000"), unit="yards"),
            delivery=DeliveryConstraint(destination_country_code="GB", max_lead_time_days=30),
            commercial_terms=CommercialTermsRequirement(
                preferred_incoterm=Incoterm.DDP,
                preferred_payment_term=PaymentMethodPreference.NET_30,
                min_warranty_months=12,
            ),
        )
        gaps = GapAnalyzer.detect_gaps(req, listing)
        gap_map = {g.field_name: g.category for g in gaps}

        assert gap_map.get("lead_time_days") == GapCategory.MISSING
        assert gap_map.get("incoterms") == GapCategory.NON_COMPLIANT  # EXW only vs DDP
        assert gap_map.get("payment_terms") == GapCategory.AMBIGUOUS
        assert gap_map.get("warranty_months") == GapCategory.MISSING
        assert gap_map.get("inspection_terms") == GapCategory.MISSING

    def test_non_compliant_moq_listing_104(self) -> None:
        """Baltic Fastener Works (104) has MOQ=5000 boxes, violating buyer target of 1000 boxes."""
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000104")
        assert listing is not None
        assert listing.completeness_tier == "NON_COMPLIANT_MOQ"

        req = BuyerRequirements(
            title="Marine-Grade Fasteners",
            category="Industrial Fasteners",
            quantity=QuantityRequirement(target_quantity=Decimal("1000"), unit="boxes"),
            delivery=DeliveryConstraint(destination_country_code="PL", max_lead_time_days=40),
            commercial_terms=CommercialTermsRequirement(
                preferred_incoterm=Incoterm.FOB,
                preferred_payment_term=PaymentMethodPreference.NET_30,
            ),
        )
        gaps = GapAnalyzer.detect_gaps(req, listing)
        moq_gaps = [g for g in gaps if g.field_name == "moq"]
        assert len(moq_gaps) == 1
        gap = moq_gaps[0]
        assert gap.category == GapCategory.NON_COMPLIANT
        assert gap.severity == GapSeverity.CRITICAL
        assert "5000" in gap.seller_offered_value
        assert "1000" in gap.buyer_requirement_value
        assert "+400%" in gap.explanation

    @pytest.mark.parametrize(
        ("listing_id", "expected_price", "max_price"),
        [
            ("00000000-0000-4000-8000-000000000105", Decimal("24.00"), Decimal("15.00")),
            ("00000000-0000-4000-8000-000000000115", Decimal("45.00"), Decimal("25.00")),
        ],
    )
    def test_non_compliant_price_listings(self, listing_id: str, expected_price: Decimal, max_price: Decimal) -> None:
        """Listings 105 & 115 exceed maximum budget ceiling with CRITICAL severity."""
        listing = get_bundled_listing_by_id(listing_id)
        assert listing is not None
        assert listing.completeness_tier == "NON_COMPLIANT_PRICE"

        req = BuyerRequirements(
            title=listing.title,
            category=listing.category,
            pricing=PricingConstraint(max_unit_price=max_price, currency="USD"),
            quantity=QuantityRequirement(target_quantity=Decimal("100"), unit=listing.unit),
            delivery=DeliveryConstraint(destination_country_code=listing.country_code, max_lead_time_days=30),
            commercial_terms=CommercialTermsRequirement(
                preferred_incoterm=listing.incoterms[0] if listing.incoterms else Incoterm.DDP,
                preferred_payment_term=PaymentMethodPreference.NET_30,
            ),
        )
        gaps = GapAnalyzer.detect_gaps(req, listing)
        price_gaps = [g for g in gaps if g.field_name == "unit_price"]
        assert len(price_gaps) == 1
        gap = price_gaps[0]
        assert gap.category == GapCategory.NON_COMPLIANT
        assert gap.severity == GapSeverity.CRITICAL
        delta = expected_price - max_price
        assert f"{delta:.2f}" in gap.explanation

    def test_non_compliant_lead_time_listing_107(self) -> None:
        """Shenzhen Precision (107) has lead_time_days=75, violating buyer maximum of 30 days."""
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000107")
        assert listing is not None
        assert listing.completeness_tier == "NON_COMPLIANT_LEAD_TIME"

        req = BuyerRequirements(
            title="Coaxial Cable Assembly",
            category="Electronics & Electrical",
            pricing=PricingConstraint(max_unit_price=Decimal("10.00"), currency="USD"),
            quantity=QuantityRequirement(target_quantity=Decimal("1500"), unit="units"),
            delivery=DeliveryConstraint(destination_country_code="CN", max_lead_time_days=30),
            commercial_terms=CommercialTermsRequirement(
                preferred_incoterm=Incoterm.FOB,
                preferred_payment_term=PaymentMethodPreference.NET_30,
            ),
        )
        gaps = GapAnalyzer.detect_gaps(req, listing)
        lt_gaps = [g for g in gaps if g.field_name == "lead_time_days"]
        assert len(lt_gaps) == 1
        gap = lt_gaps[0]
        assert gap.category == GapCategory.NON_COMPLIANT
        assert gap.severity == GapSeverity.CRITICAL
        assert "75 days" in gap.seller_offered_value
        assert "30 days" in gap.buyer_requirement_value
        assert "45 days" in gap.explanation


# =============================================================================
# 2. Reflection of Detected Gaps in Inquiry Letters (Single & Combinatorial)
# =============================================================================


class TestGapReflectionInInquiryLetters:
    """Verifies every detected gap is properly reflected in generated seller inquiry letters."""

    @pytest.mark.parametrize(
        ("field_name", "category", "expected_phrase"),
        [
            ("unit_price", GapCategory.MISSING, "Pricing:"),
            ("unit_price", GapCategory.NON_COMPLIANT, "Unit Price & Volume Discount:"),
            ("currency", GapCategory.AMBIGUOUS, "Transaction Currency:"),
            ("moq", GapCategory.MISSING, "Minimum Order Quantity (MOQ):"),
            ("moq", GapCategory.NON_COMPLIANT, "Minimum Order Quantity & Pilot Batch:"),
            ("available_quantity", GapCategory.NON_COMPLIANT, "Production Capacity:"),
            ("lead_time_days", GapCategory.MISSING, "Delivery Schedule:"),
            ("lead_time_days", GapCategory.AMBIGUOUS, "Delivery Schedule:"),
            ("lead_time_days", GapCategory.NON_COMPLIANT, "Expedited Lead Time:"),
            ("incoterms", GapCategory.MISSING, "Freight & Incoterms:"),
            ("incoterms", GapCategory.NON_COMPLIANT, "Incoterm Quotation:"),
            ("payment_terms", GapCategory.MISSING, "Commercial Payment Terms:"),
            ("payment_terms", GapCategory.AMBIGUOUS, "Commercial Payment Terms:"),
            ("payment_terms", GapCategory.NON_COMPLIANT, "Payment Terms Compromise:"),
            ("warranty_months", GapCategory.MISSING, "Warranty & Defect Liability:"),
            ("warranty_months", GapCategory.AMBIGUOUS, "Warranty & Defect Liability:"),
            ("warranty_months", GapCategory.NON_COMPLIANT, "Extended Warranty:"),
            ("certifications", GapCategory.NON_COMPLIANT, "Regulatory & Quality Compliance:"),
            ("standards", GapCategory.NON_COMPLIANT, "Technical Standards Conformity:"),
            ("inspection_terms", GapCategory.MISSING, "Quality Inspection Protocol:"),
            ("inspection_terms", GapCategory.AMBIGUOUS, "Quality Inspection Protocol:"),
        ],
    )
    def test_single_gap_reflection(
        self, field_name: str, category: GapCategory, expected_phrase: str
    ) -> None:
        """Every individual gap classification maps to an inquiry bullet and appears in gaps_addressed."""
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000101")
        assert listing is not None

        req = build_compliant_requirements_for_listing(listing)

        gap = CommercialGap(
            gap_id="test-gap-1",
            field_name=field_name,
            category=category,
            severity=GapSeverity.MODERATE,
            buyer_requirement_value="RequiredValue",
            seller_offered_value="OfferedValue",
            explanation=f"Test explanation for {field_name} {category}",
            suggested_action=f"Test action for {field_name}",
        )

        inquiry: InquiryDraft = InquiryDrafter.draft_inquiry(
            requirements=req,
            listing=listing,
            gaps=[gap],
        )

        # Check gaps_addressed
        assert f"{field_name}: {category.value}" in inquiry.gaps_addressed
        # Check body text
        assert expected_phrase in inquiry.body
        # Check clarification notice is present when gaps exist
        assert "clarification and mutual alignment" in inquiry.body

    def test_adversarial_multi_gap_combinatorial_reflection(self) -> None:
        """Adversarial stress test: inquiry with 8 simultaneous gaps correctly lists and formats each one."""
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000101")
        assert listing is not None
        req = build_compliant_requirements_for_listing(listing)

        simultaneous_gaps = [
            CommercialGap(gap_id="g1", field_name="unit_price", category=GapCategory.NON_COMPLIANT, severity=GapSeverity.CRITICAL, buyer_requirement_value="10 USD", seller_offered_value="12 USD", explanation="Over", suggested_action="Discount"),
            CommercialGap(gap_id="g2", field_name="moq", category=GapCategory.NON_COMPLIANT, severity=GapSeverity.CRITICAL, buyer_requirement_value="100", seller_offered_value="1000", explanation="High MOQ", suggested_action="Pilot"),
            CommercialGap(gap_id="g3", field_name="lead_time_days", category=GapCategory.NON_COMPLIANT, severity=GapSeverity.CRITICAL, buyer_requirement_value="15", seller_offered_value="30", explanation="Late", suggested_action="Expedite"),
            CommercialGap(gap_id="g4", field_name="payment_terms", category=GapCategory.NON_COMPLIANT, severity=GapSeverity.MODERATE, buyer_requirement_value="Net 30", seller_offered_value="Advance", explanation="Deposit", suggested_action="Escrow"),
            CommercialGap(gap_id="g5", field_name="warranty_months", category=GapCategory.NON_COMPLIANT, severity=GapSeverity.MODERATE, buyer_requirement_value="24", seller_offered_value="12", explanation="Short warranty", suggested_action="Extend"),
            CommercialGap(gap_id="g6", field_name="certifications", category=GapCategory.NON_COMPLIANT, severity=GapSeverity.CRITICAL, buyer_requirement_value="AS9100D", seller_offered_value="None", explanation="Missing cert", suggested_action="Provide cert"),
            CommercialGap(gap_id="g7", field_name="standards", category=GapCategory.NON_COMPLIANT, severity=GapSeverity.MODERATE, buyer_requirement_value="DIN 933", seller_offered_value="None", explanation="Standard unlisted", suggested_action="Confirm"),
            CommercialGap(gap_id="g8", field_name="inspection_terms", category=GapCategory.MISSING, severity=GapSeverity.LOW, buyer_requirement_value="3.1 Mill Cert", seller_offered_value="Omitted", explanation="No QC", suggested_action="Inspect"),
        ]

        inquiry = InquiryDrafter.draft_inquiry(requirements=req, listing=listing, gaps=simultaneous_gaps)

        assert len(inquiry.gaps_addressed) == 8
        expected_snippets = [
            "Unit Price & Volume Discount:",
            "Minimum Order Quantity & Pilot Batch:",
            "Expedited Lead Time:",
            "Payment Terms Compromise:",
            "Extended Warranty:",
            "Regulatory & Quality Compliance:",
            "Technical Standards Conformity:",
            "Quality Inspection Protocol:",
        ]
        for snippet in expected_snippets:
            assert snippet in inquiry.body, f"Expected '{snippet}' in multi-gap letter body"


# =============================================================================
# 3. Verification of Zero-Gap Listings and Purchase Commitment RFQs
# =============================================================================


class TestZeroGapPurchaseCommitmentRFQs:
    """Verifies zero-gap inquiries request confirmation before commercial commitment."""

    @pytest.mark.parametrize(
        "listing_id",
        [
            "00000000-0000-4000-8000-000000000101",  # Industrial Fasteners (Berlin)
            "00000000-0000-4000-8000-000000000109",  # Electronics (Sensors)
            "00000000-0000-4000-8000-000000000110",  # Agriculture (Soybeans)
            "00000000-0000-4000-8000-000000000113",  # Textiles (Istanbul)
            "00000000-0000-4000-8000-000000000108",  # Medical (MediShield)
        ],
    )
    def test_zero_gap_inquiry_body_structure(self, listing_id: str) -> None:
        """Zero-gap inquiry summarizes alignment without claiming a purchase commitment."""
        listing = get_bundled_listing_by_id(listing_id)
        assert listing is not None
        req = build_compliant_requirements_for_listing(listing)

        inquiry = InquiryDrafter.draft_inquiry(
            requirements=req,
            listing=listing,
            gaps=[],  # Explicit zero gaps
            buyer_org_name="Acme Global Procurement",
            buyer_contact_name="Chief Procurement Officer",
        )

        assert inquiry.gaps_addressed == []

        # Must NOT contain clarification warning
        assert "clarification and mutual alignment" not in inquiry.body

        assert "appear to align with our stated procurement parameters" in inquiry.body
        assert "before we make any purchase commitment" in inquiry.body
        assert "immediate purchase order" not in inquiry.body

        # Must declare the formal proposed commercial framework
        assert "Proposed Commercial Framework:" in inquiry.body
        assert "- Freight Terms:" in inquiry.body
        assert "- Payment Terms:" in inquiry.body
        assert "- Quality Inspection:" in inquiry.body
        assert "- Warranty Coverage:" in inquiry.body

        # Must mention SyncAlly bilateral deal room creation
        assert "bilateral deal room on SyncAlly" in inquiry.body

        # Must include caller contact and org names
        assert "Acme Global Procurement" in inquiry.body
        assert "Chief Procurement Officer" in inquiry.body

        # Proposed terms map validation
        terms = inquiry.proposed_terms
        assert terms["target_quantity"] == str(req.quantity.target_quantity)
        assert terms["unit"] == req.quantity.unit
        assert terms["currency"] == req.pricing.currency
        assert terms["destination_country_code"] == req.delivery.destination_country_code


# =============================================================================
# 4. Verification of Actionable Compromise Proposals
# =============================================================================


class TestCompromiseProposalsLogic:
    """Verifies compromise logic generates actionable proposals across all 4 required mechanisms."""

    def test_pilot_lot_proposal_under_stress(self) -> None:
        """When MOQ exceeds buyer demand, inquiry proposes pilot lot with follow-on scale option."""
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000104")
        assert listing is not None
        req = BuyerRequirements(
            title="Fasteners",
            category="Industrial Fasteners",
            quantity=QuantityRequirement(target_quantity=Decimal("250"), unit="boxes"),
            delivery=DeliveryConstraint(destination_country_code="DE"),
        )
        gaps = GapAnalyzer.detect_gaps(req, listing)
        inquiry = InquiryDrafter.draft_inquiry(req, listing, gaps)

        assert "moq: NON_COMPLIANT" in inquiry.gaps_addressed
        assert "Minimum Order Quantity & Pilot Batch:" in inquiry.body
        assert "initial pilot lot of 250 boxes" in inquiry.body
        assert "option to scale into full recurring production" in inquiry.body

    def test_volume_discount_proposal_under_stress(self) -> None:
        """When price exceeds budget target, inquiry proposes volume concession for recurring POs."""
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000105")
        assert listing is not None
        req = BuyerRequirements(
            title="Aero Fasteners",
            category="Industrial Fasteners",
            pricing=PricingConstraint(target_unit_price=Decimal("16.00"), max_unit_price=Decimal("18.00"), currency="USD"),
            quantity=QuantityRequirement(target_quantity=Decimal("100"), unit="boxes"),
            delivery=DeliveryConstraint(destination_country_code="SE"),
        )
        gaps = GapAnalyzer.detect_gaps(req, listing)
        inquiry = InquiryDrafter.draft_inquiry(req, listing, gaps)

        assert "unit_price: NON_COMPLIANT" in inquiry.gaps_addressed
        assert "Unit Price & Volume Discount:" in inquiry.body
        assert "listed unit price is 24.00 USD" in inquiry.body
        assert "budget target for this line item is 16.00 USD" in inquiry.body
        assert "recurring quarterly purchase orders" in inquiry.body
        assert "volume concession to bring the unit price closer to 16.00 USD" in inquiry.body

    def test_expedited_shipping_proposal_under_stress(self) -> None:
        """When lead time exceeds buyer window, inquiry proposes expedited shifts / air freight."""
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000107")
        assert listing is not None
        req = BuyerRequirements(
            title="Micro-Coaxial Cables",
            category="Electronics & Electrical",
            quantity=QuantityRequirement(target_quantity=Decimal("1000"), unit="units"),
            delivery=DeliveryConstraint(destination_country_code="CN", max_lead_time_days=20),
        )
        gaps = GapAnalyzer.detect_gaps(req, listing)
        inquiry = InquiryDrafter.draft_inquiry(req, listing, gaps)

        assert "lead_time_days: NON_COMPLIANT" in inquiry.gaps_addressed
        assert "Expedited Lead Time:" in inquiry.body
        assert "quoted lead time of 75 days exceeds our maximum procurement window of 20 days" in inquiry.body
        assert "expedited production shifts, priority scheduling, or expedited air/express freight" in inquiry.body

    def test_escrow_payment_proposal_under_stress(self) -> None:
        """When seller requires an advance deposit, inquiry asks for alternative terms without inventing escrow."""
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000102")
        assert listing is not None
        req = BuyerRequirements(
            title="Hex Bolts",
            category="Industrial Fasteners",
            quantity=QuantityRequirement(target_quantity=Decimal("500"), unit="boxes"),
            delivery=DeliveryConstraint(destination_country_code="US"),
            commercial_terms=CommercialTermsRequirement(
                preferred_payment_term=PaymentMethodPreference.NET_30,
            ),
        )
        gaps = GapAnalyzer.detect_gaps(req, listing)
        inquiry = InquiryDrafter.draft_inquiry(req, listing, gaps)

        assert "payment_terms: NON_COMPLIANT" in inquiry.gaps_addressed
        assert "Payment Terms Compromise:" in inquiry.body
        assert "Could you share alternative payment terms for our review?" in inquiry.body
        assert "30% advance deposit" not in inquiry.body
        assert "full escrow deposit released upon destination inspection" not in inquiry.body


# =============================================================================
# 5. Adversarial Stress & Robustness Tests
# =============================================================================


class TestAdversarialStressAndBoundaries:
    """Stress tests boundary conditions, extreme numbers, currency divergence, and thread safety."""

    def test_exact_boundary_thresholds_produce_no_false_positive_gaps(self) -> None:
        """When listing values exactly equal the thresholds, no gaps must be generated."""
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000101")
        assert listing is not None

        # Exact matching numbers
        req = BuyerRequirements(
            title=listing.title,
            category=listing.category,
            pricing=PricingConstraint(
                target_unit_price=listing.unit_price,
                max_unit_price=listing.unit_price,
                currency=listing.currency,
            ),
            quantity=QuantityRequirement(target_quantity=listing.moq, unit=listing.unit),  # type: ignore[arg-type]
            delivery=DeliveryConstraint(
                destination_country_code="DE",
                max_lead_time_days=listing.lead_time_days,
            ),
            commercial_terms=CommercialTermsRequirement(
                preferred_incoterm=listing.incoterms[0],
                preferred_payment_term=PaymentMethodPreference.ESCROW,
                min_warranty_months=listing.warranty_months,  # type: ignore[arg-type]
                inspection_requirement=InspectionPreference.FACTORY_MILL_CERTIFICATE,
            ),
        )
        gaps = GapAnalyzer.detect_gaps(req, listing)
        assert len(gaps) == 0, f"False positive gaps detected at exact boundary: {[g.field_name for g in gaps]}"

    def test_slight_threshold_breach_produces_exact_mathematical_delta(self) -> None:
        """A unit price breach by exactly $0.01 produces NON_COMPLIANT gap with exact delta."""
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000101")
        assert listing is not None

        # Max price is 0.01 lower than listing price (11.50) -> max 11.49
        req = BuyerRequirements(
            title=listing.title,
            category=listing.category,
            pricing=PricingConstraint(max_unit_price=Decimal("11.49"), currency="USD"),
            quantity=QuantityRequirement(target_quantity=listing.moq, unit=listing.unit),  # type: ignore[arg-type]
            delivery=DeliveryConstraint(destination_country_code="DE"),
        )
        gaps = GapAnalyzer.detect_gaps(req, listing)
        price_gaps = [g for g in gaps if g.field_name == "unit_price"]
        assert len(price_gaps) == 1
        gap = price_gaps[0]
        assert gap.category == GapCategory.NON_COMPLIANT
        assert "0.01" in gap.explanation

    def test_currency_mismatch_adversarial_classification(self) -> None:
        """EUR buyer vs USD seller flags currency as AMBIGUOUS with priority 3."""
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000101")
        assert listing is not None

        req = BuyerRequirements(
            title=listing.title,
            category=listing.category,
            pricing=PricingConstraint(max_unit_price=Decimal("20.00"), currency="EUR"),
            quantity=QuantityRequirement(target_quantity=Decimal("500"), unit="boxes"),
            delivery=DeliveryConstraint(destination_country_code="DE"),
        )
        gaps = GapAnalyzer.detect_gaps(req, listing)
        curr_gaps = [g for g in gaps if g.field_name == "currency"]
        assert len(curr_gaps) == 1
        gap = curr_gaps[0]
        assert gap.category == GapCategory.AMBIGUOUS
        assert gap.severity == GapSeverity.MODERATE
        assert "buyer requested EUR, seller listed in USD" in gap.explanation

        inquiry = InquiryDrafter.draft_inquiry(req, listing, gaps)
        assert "currency: AMBIGUOUS" in inquiry.gaps_addressed
        assert "Transaction Currency:" in inquiry.body
        assert "operates primarily in EUR" in inquiry.body

    def test_extreme_quantities_and_values(self) -> None:
        """Engine handles massive numbers without overflow, division by zero, or float rounding bugs."""
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000101")
        assert listing is not None

        huge_req = BuyerRequirements(
            title=listing.title,
            category=listing.category,
            pricing=PricingConstraint(max_unit_price=Decimal("999999999.99"), currency="USD"),
            quantity=QuantityRequirement(target_quantity=Decimal("999999999"), unit="boxes"),
            delivery=DeliveryConstraint(destination_country_code="DE"),
        )
        # Should detect available_quantity deficit (seller has 15,000 vs 999,999,999)
        gaps = GapAnalyzer.detect_gaps(huge_req, listing)
        avail_gaps = [g for g in gaps if g.field_name == "available_quantity"]
        assert len(avail_gaps) == 1
        assert "999984999" in avail_gaps[0].explanation

        inquiry = InquiryDrafter.draft_inquiry(huge_req, listing, gaps)
        assert "Production Capacity:" in inquiry.body
        assert "999999999 boxes" in inquiry.body

    def test_concurrent_evaluation_thread_safety(self) -> None:
        """Runs 50 concurrent evaluation calls to verify thread-safety and absence of mutable shared state."""
        listing = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000101")
        assert listing is not None
        req = build_compliant_requirements_for_listing(listing)

        def eval_task(idx: int) -> tuple[int, int, str]:
            # Alternate between zero-gap and forced-gap evaluation
            if idx % 2 == 0:
                gaps = GapAnalyzer.detect_gaps(req, listing)
                inquiry = InquiryDrafter.draft_inquiry(req, listing, gaps)
                return idx, len(gaps), inquiry.subject
            else:
                tight_req = BuyerRequirements(
                    title=req.title,
                    category=req.category,
                    pricing=PricingConstraint(max_unit_price=Decimal("5.00"), currency="USD"),
                    quantity=req.quantity,
                    delivery=req.delivery,
                )
                gaps = GapAnalyzer.detect_gaps(tight_req, listing)
                inquiry = InquiryDrafter.draft_inquiry(tight_req, listing, gaps)
                return idx, len(gaps), inquiry.subject

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(eval_task, i) for i in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 50
        even_results = [r for r in results if r[0] % 2 == 0]
        odd_results = [r for r in results if r[0] % 2 != 0]

        # All even executions must be strictly 0 gaps
        assert all(r[1] == 0 for r in even_results)
        # All odd executions must have detected price gap
        assert all(r[1] >= 1 for r in odd_results)
