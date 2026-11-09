"""Standalone adversarial empirical verification runner for Milestone M1 Sourcing Core Engine.

Executes and logs proof for:
1. All 14 bundled marketplace listings across all 6 completeness tiers producing expected gap classifications.
2. Every detected gap being properly reflected in generated seller inquiry letters.
3. Zero-gap listings generating valid purchase commitment RFQs.
4. Compromise logic generating actionable proposals:
   - pilot lots
   - volume discounts
   - expedited shipping
   - escrow payment
"""

from __future__ import annotations

from decimal import Decimal

from syncally.application.sourcing.gap_analyzer import GapAnalyzer
from syncally.application.sourcing.inquiry_drafter import InquiryDrafter
from syncally.domain.sourcing.contracts import (
    BuyerRequirements,
    CommercialTermsRequirement,
    DeliveryConstraint,
    GapCategory,
    Incoterm,
    InspectionPreference,
    PaymentMethodPreference,
    PricingConstraint,
    QuantityRequirement,
    TechnicalSpecification,
)
from syncally.infrastructure.sourcing.bundled_dataset import (
    BUNDLED_MARKETPLACE_LISTINGS,
    get_bundled_listing_by_id,
)


def run_empirical_verification() -> None:
    print("=" * 80)
    print("EMPIRICAL ADVERSARIAL VERIFICATION: MILESTONE M1 SOURCING CORE ENGINE")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # Check 1: 14 Bundled Listings Across 6 Completeness Tiers
    # -------------------------------------------------------------------------
    print("\n--- CHECK 1: ALL 14 BUNDLED LISTINGS & 6 COMPLETENESS TIERS ---")
    print(f"Total bundled listings loaded: {len(BUNDLED_MARKETPLACE_LISTINGS)}")
    assert len(BUNDLED_MARKETPLACE_LISTINGS) == 14, "Must have exactly 14 listings"

    tier_counts: dict[str, int] = {}
    for item in BUNDLED_MARKETPLACE_LISTINGS:
        tier_counts[item.completeness_tier] = tier_counts.get(item.completeness_tier, 0) + 1

    print("\nCompleteness Tier Breakdown:")
    for tier, count in sorted(tier_counts.items()):
        print(f"  - {tier}: {count} listing(s)")
    assert len(tier_counts) == 6, f"Expected 6 completeness tiers, got {len(tier_counts)}"

    print("\nIndividual Listing Classification Audit:")
    for idx, listing in enumerate(BUNDLED_MARKETPLACE_LISTINGS, start=1):
        print(f"[{idx:02d}/14] ID: {listing.id} | Tier: {listing.completeness_tier:<35} | Title: {listing.title[:40]}")

        # Baseline compliant requirements to observe native listing gaps
        req = BuyerRequirements(
            title=f"Req for {listing.title}",
            category=listing.category,
            pricing=PricingConstraint(
                target_unit_price=listing.unit_price,
                max_unit_price=listing.unit_price if listing.completeness_tier != "NON_COMPLIANT_PRICE" else listing.unit_price * Decimal("0.70"),
                currency=listing.currency,
            ),
            quantity=QuantityRequirement(
                target_quantity=listing.moq if (listing.moq and listing.completeness_tier != "NON_COMPLIANT_MOQ") else Decimal("100"),
                unit=listing.unit,
            ),
            delivery=DeliveryConstraint(
                destination_country_code="DE" if listing.country_code != "DE" else "US",
                max_lead_time_days=listing.lead_time_days if (listing.lead_time_days and listing.completeness_tier != "NON_COMPLIANT_LEAD_TIME") else 20,
            ),
            commercial_terms=CommercialTermsRequirement(
                preferred_incoterm=listing.incoterms[0] if listing.incoterms else Incoterm.DDP,
                preferred_payment_term=PaymentMethodPreference.NET_30,
                min_warranty_months=listing.warranty_months if (listing.warranty_months is not None and listing.completeness_tier != "AMBIGUOUS_SPECS_OR_TERMS") else 12,
                inspection_requirement=InspectionPreference.FACTORY_MILL_CERTIFICATE,
            ),
        )

        detected_gaps = GapAnalyzer.detect_gaps(req, listing)
        gap_summary = [f"{g.field_name}({g.category.value}:{g.severity.value})" for g in detected_gaps]
        print(f"       Gaps Detected ({len(detected_gaps)}): {', '.join(gap_summary) if gap_summary else 'NONE (ZERO-GAP MATCH)'}")

        # Tier specific assertion
        if listing.completeness_tier == "FULL_COMPLETE":
            assert len(detected_gaps) == 0, f"FULL_COMPLETE listing {listing.id} should have 0 gaps under compliant reqs"
        elif listing.completeness_tier == "PARTIAL_MISSING_LEAD_TIME_OR_TERMS":
            missing_cats = [g.category for g in detected_gaps]
            assert GapCategory.MISSING in missing_cats, f"Listing {listing.id} missing MISSING category"
        elif listing.completeness_tier == "AMBIGUOUS_SPECS_OR_TERMS":
            ambiguous_cats = [g.category for g in detected_gaps]
            assert GapCategory.AMBIGUOUS in ambiguous_cats, f"Listing {listing.id} missing AMBIGUOUS category"
        elif listing.completeness_tier == "NON_COMPLIANT_MOQ":
            fields = {g.field_name: g.category for g in detected_gaps}
            assert fields.get("moq") == GapCategory.NON_COMPLIANT
        elif listing.completeness_tier == "NON_COMPLIANT_PRICE":
            fields = {g.field_name: g.category for g in detected_gaps}
            assert fields.get("unit_price") == GapCategory.NON_COMPLIANT
        elif listing.completeness_tier == "NON_COMPLIANT_LEAD_TIME":
            fields = {g.field_name: g.category for g in detected_gaps}
            assert fields.get("lead_time_days") == GapCategory.NON_COMPLIANT

    print("\n>>> CHECK 1 PASSED: All 14 listings & 6 completeness tiers verified.")

    # -------------------------------------------------------------------------
    # Check 2: Every Detected Gap Reflected in Seller Inquiry Letter
    # -------------------------------------------------------------------------
    print("\n--- CHECK 2: GAP REFLECTION IN SELLER INQUIRY LETTERS ---")
    all_categories_tested = 0
    all_fields_tested = set()

    for listing in BUNDLED_MARKETPLACE_LISTINGS:
        # Create a requirement designed to trigger gaps for this listing
        stress_req = BuyerRequirements(
            title=f"Stress Req for {listing.title}",
            category=listing.category,
            technical_specs=TechnicalSpecification(
                certifications=["NON_EXISTENT_CERT_ISO99999"],
                standards=["NON_EXISTENT_STD_XYZ123"],
            ),
            pricing=PricingConstraint(
                max_unit_price=listing.unit_price * Decimal("0.80"),
                currency=listing.currency,
            ),
            quantity=QuantityRequirement(
                target_quantity=Decimal("50"),
                unit=listing.unit,
            ),
            delivery=DeliveryConstraint(
                destination_country_code="FR",
                max_lead_time_days=7,
            ),
            commercial_terms=CommercialTermsRequirement(
                preferred_incoterm=Incoterm.DDP,
                preferred_payment_term=PaymentMethodPreference.NET_30,
                min_warranty_months=60,
                inspection_requirement=InspectionPreference.PRE_SHIPMENT_THIRD_PARTY,
            ),
        )

        gaps = GapAnalyzer.detect_gaps(stress_req, listing)
        inquiry = InquiryDrafter.draft_inquiry(stress_req, listing, gaps)

        assert len(inquiry.gaps_addressed) == len(gaps), (
            f"Listing {listing.id}: gaps count ({len(gaps)}) != gaps_addressed count ({len(inquiry.gaps_addressed)})"
        )

        for gap in gaps:
            expected_key = f"{gap.field_name}: {gap.category.value}"
            assert expected_key in inquiry.gaps_addressed, f"Key '{expected_key}' missing from inquiry.gaps_addressed"
            all_fields_tested.add(gap.field_name)
            all_categories_tested += 1

    print(f"Verified {all_categories_tested} detected gap instances across {len(all_fields_tested)} unique commercial fields.")
    print(f"Fields verified: {sorted(list(all_fields_tested))}")
    print(">>> CHECK 2 PASSED: 100% of detected gaps reflected in inquiry letters.")

    # -------------------------------------------------------------------------
    # Check 3: Zero-Gap Listings Generate Purchase Commitment RFQs
    # -------------------------------------------------------------------------
    print("\n--- CHECK 3: ZERO-GAP PURCHASE COMMITMENT RFQS ---")
    full_complete_ids = [
        "00000000-0000-4000-8000-000000000101",
        "00000000-0000-4000-8000-000000000109",
        "00000000-0000-4000-8000-000000000110",
        "00000000-0000-4000-8000-000000000113",
        "00000000-0000-4000-8000-000000000108",
    ]

    for lid in full_complete_ids:
        listing = get_bundled_listing_by_id(lid)
        assert listing is not None

        req = BuyerRequirements(
            title=listing.title,
            category=listing.category,
            technical_specs=TechnicalSpecification(
                materials=list(listing.technical_specs.materials),
                tolerances=listing.technical_specs.tolerances,
                certifications=list(listing.technical_specs.certifications),
                standards=list(listing.technical_specs.standards),
                quality_grade=listing.technical_specs.quality_grade,
            ),
            pricing=PricingConstraint(
                target_unit_price=listing.unit_price,
                max_unit_price=listing.unit_price,
                currency=listing.currency,
            ),
            quantity=QuantityRequirement(
                target_quantity=listing.moq or Decimal("100"),
                unit=listing.unit,
            ),
            delivery=DeliveryConstraint(
                destination_country_code="DE" if listing.country_code != "DE" else "US",
                max_lead_time_days=listing.lead_time_days or 30,
            ),
            commercial_terms=CommercialTermsRequirement(
                preferred_incoterm=listing.incoterms[0],
                preferred_payment_term=PaymentMethodPreference.ESCROW,
                min_warranty_months=listing.warranty_months or 12,
                inspection_requirement=InspectionPreference.FACTORY_MILL_CERTIFICATE,
            ),
        )

        gaps = GapAnalyzer.detect_gaps(req, listing)
        assert len(gaps) == 0

        inquiry = InquiryDrafter.draft_inquiry(req, listing, gaps)
        assert inquiry.gaps_addressed == []

        # Verification of RFQ commitment phrases
        assert "prepared to commit to an immediate purchase order" in inquiry.body
        assert "clarification and mutual alignment" not in inquiry.body
        assert "Proposed Commercial Framework:" in inquiry.body
        assert "- Freight Terms:" in inquiry.body
        assert "- Payment Terms:" in inquiry.body
        assert "- Quality Inspection:" in inquiry.body
        assert "- Warranty Coverage:" in inquiry.body
        assert "bilateral deal room on SyncAlly" in inquiry.body
        print(f"Verified Zero-Gap RFQ for [{listing.id}] '{listing.title[:35]}...' -> Purchase Commitment Confirmed")

    print(">>> CHECK 3 PASSED: Zero-gap listings generate valid purchase commitment RFQs.")

    # -------------------------------------------------------------------------
    # Check 4: Compromise Logic Generates Actionable Proposals
    # -------------------------------------------------------------------------
    print("\n--- CHECK 4: COMPROMISE LOGIC GENERATES ACTIONABLE PROPOSALS ---")

    # 4a. Pilot lot compromise
    l_moq = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000104")
    assert l_moq is not None
    r_moq = BuyerRequirements(
        title="Fastener Req",
        category="Industrial Fasteners",
        quantity=QuantityRequirement(target_quantity=Decimal("500"), unit="boxes"),
        delivery=DeliveryConstraint(destination_country_code="PL"),
    )
    g_moq = GapAnalyzer.detect_gaps(r_moq, l_moq)
    inq_moq = InquiryDrafter.draft_inquiry(r_moq, l_moq, g_moq)
    assert "initial pilot lot of 500 boxes" in inq_moq.body
    assert "option to scale into full recurring production" in inq_moq.body
    print("  [4a: Pilot Lot Proposal] -> VERIFIED (target: 500 boxes vs MOQ: 5000 boxes)")

    # 4b. Volume discount compromise
    l_price = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000105")
    assert l_price is not None
    r_price = BuyerRequirements(
        title="Aero Spares Req",
        category="Industrial Fasteners",
        pricing=PricingConstraint(target_unit_price=Decimal("15.00"), max_unit_price=Decimal("18.00"), currency="USD"),
        quantity=QuantityRequirement(target_quantity=Decimal("100"), unit="boxes"),
        delivery=DeliveryConstraint(destination_country_code="SE"),
    )
    g_price = GapAnalyzer.detect_gaps(r_price, l_price)
    inq_price = InquiryDrafter.draft_inquiry(r_price, l_price, g_price)
    assert "recurring quarterly purchase orders" in inq_price.body
    assert "volume concession to bring the unit price closer to $15.00 USD" in inq_price.body
    print("  [4b: Volume Discount Proposal] -> VERIFIED ($24.00 quoted vs $15.00 target)")

    # 4c. Expedited shipping compromise
    l_lead = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000107")
    assert l_lead is not None
    r_lead = BuyerRequirements(
        title="Cables Req",
        category="Electronics & Electrical",
        quantity=QuantityRequirement(target_quantity=Decimal("1000"), unit="units"),
        delivery=DeliveryConstraint(destination_country_code="CN", max_lead_time_days=25),
    )
    g_lead = GapAnalyzer.detect_gaps(r_lead, l_lead)
    inq_lead = InquiryDrafter.draft_inquiry(r_lead, l_lead, g_lead)
    assert "expedited production shifts, priority scheduling, or expedited air/express freight" in inq_lead.body
    assert "quoted lead time of 75 days exceeds our maximum procurement window of 25 days" in inq_lead.body
    print("  [4c: Expedited Shipping Proposal] -> VERIFIED (75 days quoted vs 25 days max)")

    # 4d. Escrow payment compromise
    l_pay = get_bundled_listing_by_id("00000000-0000-4000-8000-000000000102")
    assert l_pay is not None
    r_pay = BuyerRequirements(
        title="Hardware Req",
        category="Industrial Fasteners",
        quantity=QuantityRequirement(target_quantity=Decimal("500"), unit="boxes"),
        delivery=DeliveryConstraint(destination_country_code="US"),
        commercial_terms=CommercialTermsRequirement(
            preferred_payment_term=PaymentMethodPreference.NET_30,
        ),
    )
    g_pay = GapAnalyzer.detect_gaps(r_pay, l_pay)
    inq_pay = InquiryDrafter.draft_inquiry(r_pay, l_pay, g_pay)
    assert "30% advance deposit" in inq_pay.body
    assert "70% balance payable against the original Bill of Lading" in inq_pay.body
    assert "full escrow deposit released upon destination inspection" in inq_pay.body
    print("  [4d: Escrow / Split Terms Proposal] -> VERIFIED (Upfront deposit vs 30/70 BL / Escrow)")

    print("\n>>> CHECK 4 PASSED: All 4 compromise proposals verified.")

    print("\n" + "=" * 80)
    print("EMPIRICAL VERIFICATION COMPLETE: ALL 4 CHECKS PASSED WITH ZERO ERRORS")
    print("=" * 80)


if __name__ == "__main__":
    run_empirical_verification()
