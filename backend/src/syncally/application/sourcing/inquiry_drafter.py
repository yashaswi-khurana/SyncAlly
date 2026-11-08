"""Seller inquiry drafting engine.

Synthesizes professional, polite, targeted B2B inquiry letters addressing each detected
gap with constructive commercial compromises (e.g., pilot batches, volume discounts,
expedited freight, warranty extensions, escrow terms).
"""

from __future__ import annotations

from typing import Any

from syncally.domain.sourcing.contracts import (
    BuyerRequirements,
    CommercialGap,
    GapCategory,
    InquiryDraft,
    MarketplaceListingDetail,
)


class InquiryDrafter:
    """Generates formal B2B inquiry correspondence tailored to candidate listings and detected gaps."""

    @classmethod
    def draft_inquiry(
        cls,
        requirements: BuyerRequirements,
        listing: MarketplaceListingDetail,
        gaps: list[CommercialGap] | None = None,
        buyer_org_name: str | None = None,
        buyer_contact_name: str | None = None,
    ) -> InquiryDraft:
        """Draft a structured, targeted B2B inquiry letter."""
        org_name = buyer_org_name or "Procurement Division"
        contact_name = buyer_contact_name or "Global Sourcing Lead"
        listing_ref = listing.id[:8].upper()

        subject = f"Commercial Inquiry: {listing.title} — Ref: {listing_ref} — {org_name}"

        # If gaps are not provided, detect them
        if gaps is None:
            from syncally.application.sourcing.gap_analyzer import GapAnalyzer
            gaps = GapAnalyzer.detect_gaps(requirements, listing)

        gaps_addressed: list[str] = []
        gap_paragraphs: list[str] = []

        # Generate targeted paragraph for each gap
        for gap in gaps:
            para = cls._generate_gap_paragraph(gap, requirements, listing)
            if para:
                gap_paragraphs.append(para)
                gaps_addressed.append(f"{gap.field_name}: {gap.category.value}")

        # Assemble full letter body
        body = cls._compose_body(
            requirements=requirements,
            listing=listing,
            gap_paragraphs=gap_paragraphs,
            org_name=org_name,
            contact_name=contact_name,
        )

        proposed_terms: dict[str, Any] = {
            "target_quantity": str(requirements.quantity.target_quantity),
            "unit": requirements.quantity.unit,
            "target_unit_price": str(requirements.pricing.target_unit_price or listing.unit_price),
            "currency": requirements.pricing.currency,
            "preferred_incoterm": str(requirements.commercial_terms.preferred_incoterm or "DDP"),
            "preferred_payment_term": str(requirements.commercial_terms.preferred_payment_term or "Net 30"),
            "destination_country_code": requirements.delivery.destination_country_code,
            "destination_port_or_city": requirements.delivery.destination_port_or_city,
        }

        return InquiryDraft(
            listing_id=listing.id,
            seller_organization_id=listing.organization_id,
            seller_organization_name=listing.organization_name,
            subject=subject,
            body=body,
            gaps_addressed=gaps_addressed,
            proposed_terms=proposed_terms,
        )

    @classmethod
    def _generate_gap_paragraph(
        cls,
        gap: CommercialGap,
        req: BuyerRequirements,
        listing: MarketplaceListingDetail,
    ) -> str | None:
        """Generate targeted compromise paragraph for a specific detected gap."""
        fn = gap.field_name
        cat = gap.category

        # 1. Price Gaps
        if fn == "unit_price":
            if cat == GapCategory.MISSING:
                return (
                    f"• Pricing: As your listing does not state a published unit price, could you provide "
                    f"a binding quotation for an order volume of {req.quantity.target_quantity} {req.quantity.unit} "
                    f"in {req.pricing.currency}?"
                )
            elif cat == GapCategory.NON_COMPLIANT:
                target_p = req.pricing.target_unit_price or req.pricing.max_unit_price
                return (
                    f"• Unit Price & Volume Discount: Your listed unit price is ${listing.unit_price:.2f} {listing.currency}, "
                    f"whereas our procurement budget target for this line item is ${target_p:.2f} {req.pricing.currency}. "
                    f"In consideration of our volume and potential for recurring quarterly purchase orders, would your team "
                    f"be open to offering a volume concession to bring the unit price closer to ${target_p:.2f} {req.pricing.currency}?"
                )

        if fn == "currency":
            return (
                f"• Transaction Currency: Our purchasing system operates primarily in {req.pricing.currency}. "
                f"Could you confirm whether invoicing and settlement can be issued directly in {req.pricing.currency}, "
                f"or propose a fixed exchange rate for the duration of the agreement?"
            )

        # 2. MOQ & Available Quantity Gaps
        if fn == "moq":
            if cat == GapCategory.MISSING:
                return (
                    f"• Minimum Order Quantity (MOQ): Your listing does not specify minimum order parameters. "
                    f"Could you confirm your standard MOQ and whether an order of {req.quantity.target_quantity} "
                    f"{req.quantity.unit} satisfies your production batch thresholds?"
                )
            elif cat == GapCategory.NON_COMPLIANT:
                return (
                    f"• Minimum Order Quantity & Pilot Batch: We note your listed MOQ of {listing.moq} {listing.unit}, "
                    f"whereas our initial scheduled requirement for this production cycle is {req.quantity.target_quantity} "
                    f"{req.quantity.unit}. Would your team be open to accepting an initial pilot lot of {req.quantity.target_quantity} "
                    f"{req.quantity.unit} (at an agreed sample price if necessary), with the contractual option to scale into "
                    f"full recurring production upon incoming quality validation?"
                )

        if fn == "available_quantity":
            return (
                f"• Production Capacity: Our required order volume is {req.quantity.target_quantity} {req.quantity.unit}, "
                f"which exceeds the currently listed available quantity of {listing.available_quantity} {listing.unit}. "
                f"Could you advise on your current factory capacity and lead time to produce the full requested quantity, "
                f"or whether a split shipment schedule is feasible?"
            )

        # 3. Lead Time Gaps
        if fn == "lead_time_days":
            if cat in (GapCategory.MISSING, GapCategory.AMBIGUOUS):
                dest_str = req.delivery.destination_port_or_city or req.delivery.destination_country_code
                return (
                    f"• Delivery Schedule: Our manufacturing assembly schedule requires confirmed delivery within "
                    f"{req.delivery.max_lead_time_days or 30} days. Could you confirm your guaranteed manufacturing "
                    f"and dispatch lead time in calendar days for an order of {req.quantity.target_quantity} {req.quantity.unit} "
                    f"shipped to {dest_str}?"
                )
            elif cat == GapCategory.NON_COMPLIANT:
                max_days = req.delivery.max_lead_time_days or 30
                return (
                    f"• Expedited Lead Time: Your quoted lead time of {listing.lead_time_days} days exceeds our maximum "
                    f"procurement window of {max_days} days. Are expedited production shifts, priority scheduling, or "
                    f"expedited air/express freight arrangements available to meet our required timeline?"
                )

        # 4. Incoterms Gaps
        if fn == "incoterms":
            pref = str(req.commercial_terms.preferred_incoterm or "DDP")
            dest_str = req.delivery.destination_port_or_city or req.delivery.destination_country_code
            if cat == GapCategory.MISSING:
                return (
                    f"• Freight & Incoterms: As Incoterms are omitted from your listing, please confirm whether your team "
                    f"can quote under {pref} terms to our receiving facility in {dest_str}."
                )
            elif cat == GapCategory.NON_COMPLIANT:
                return (
                    f"• Incoterm Quotation: Your listing quotes under {', '.join(str(i) for i in listing.incoterms)} terms. "
                    f"Due to our logistics protocols, we require quotation under {pref} terms to {dest_str}. Could you provide "
                    f"an updated quotation including comprehensive door-to-door freight, customs clearance, and insurance?"
                )

        # 5. Payment Terms Gaps
        if fn == "payment_terms":
            pref_pt = str(req.commercial_terms.preferred_payment_term or "Net 30")
            if cat in (GapCategory.MISSING, GapCategory.AMBIGUOUS):
                return (
                    f"• Commercial Payment Terms: To establish standard billing, we propose settlement under {pref_pt} "
                    f"or through SyncAlly Milestone Escrow to ensure mutual commercial security."
                )
            elif cat == GapCategory.NON_COMPLIANT:
                return (
                    f"• Payment Terms Compromise: Your listing specifies upfront deposit terms ('{listing.payment_terms}'). "
                    f"Under our corporate treasury guidelines, we propose a balanced compromise: 30% advance deposit upon "
                    f"order confirmation, with the remaining 70% balance payable against the original Bill of Lading, "
                    f"or full escrow deposit released upon destination inspection."
                )

        # 6. Warranty Gaps
        if fn == "warranty_months":
            req_w = req.commercial_terms.min_warranty_months
            if cat in (GapCategory.MISSING, GapCategory.AMBIGUOUS):
                return (
                    f"• Warranty & Defect Liability: Our quality governance requires a formal {req_w}-month warranty "
                    f"covering material and manufacturing defects. Could you confirm your standard defect liability protocol "
                    f"and provide your written {req_w}-month replacement guarantee?"
                )
            elif cat == GapCategory.NON_COMPLIANT:
                return (
                    f"• Extended Warranty: Your listed warranty is {listing.warranty_months} months, whereas our project requires "
                    f"a minimum of {req_w} months. Could you confirm whether an extended warranty package can be incorporated "
                    f"into our commercial contract?"
                )

        # 7. Certifications & Standards Gaps
        if fn == "certifications":
            return (
                f"• Regulatory & Quality Compliance: Our regulatory compliance mandate requires {gap.buyer_requirement_value} "
                f"certification. Could your quality assurance team furnish a valid copy of the {gap.buyer_requirement_value} "
                f"certificate or formal Declaration of Conformity for this production batch?"
            )

        if fn == "standards":
            return (
                f"• Technical Standards Conformity: Please confirm that the offered product fully conforms to the "
                f"{gap.buyer_requirement_value} standard and provide recent third-party test reports."
            )

        # 8. Inspection Gaps
        if fn == "inspection_terms":
            return (
                f"• Quality Inspection Protocol: We require verification via {req.commercial_terms.inspection_requirement} "
                f"prior to final shipment release. Could you confirm your facility's acceptance of this inspection protocol?"
            )

        return None

    @classmethod
    def _compose_body(
        cls,
        requirements: BuyerRequirements,
        listing: MarketplaceListingDetail,
        gap_paragraphs: list[str],
        org_name: str,
        contact_name: str,
    ) -> str:
        """Compose the complete B2B inquiry letter text."""
        dest_loc = requirements.delivery.destination_port_or_city or requirements.delivery.destination_country_code
        lines: list[str] = [
            f"Dear Commercial & Sales Team at {listing.organization_name},",
            "",
            f"I am writing on behalf of {org_name} regarding your listing for \"{listing.title}\" "
            f"(Listing ID: {listing.id}) on SyncAlly. We have reviewed your offering against our current "
            f"procurement specifications and would like to explore opening a formal commercial trade deal.",
            "",
            "Order Overview & Requirements:",
            f"- Requested Item: {requirements.title} ({requirements.category})",
            f"- Order Volume: {requirements.quantity.target_quantity} {requirements.quantity.unit}",
            f"- Destination Facility: {dest_loc}, {requirements.delivery.destination_country_code}",
            f"- Target Delivery Window: Within {requirements.delivery.max_lead_time_days or 30} days",
            f"- Target Unit Price: ${requirements.pricing.target_unit_price or listing.unit_price:.2f} {requirements.pricing.currency}",
            "",
        ]

        if gap_paragraphs:
            lines.extend([
                "To finalize our evaluation and advance to bilateral contract initiation, we would appreciate "
                "your clarification and mutual alignment on the following commercial points:",
                "",
            ])
            lines.extend(gap_paragraphs)
            lines.append("")
        else:
            lines.extend([
                "We are pleased to inform you that your published commercial terms and technical specifications "
                "fully align with our procurement parameters. We are prepared to commit to an immediate purchase order.",
                "",
            ])

        lines.extend([
            "Proposed Commercial Framework:",
            f"- Freight Terms: {requirements.commercial_terms.preferred_incoterm or 'DDP'} {dest_loc}",
            f"- Payment Terms: {requirements.commercial_terms.preferred_payment_term or 'Net 30'} or SyncAlly Escrow",
            f"- Quality Inspection: {requirements.commercial_terms.inspection_requirement}",
            f"- Warranty Coverage: Minimum {requirements.commercial_terms.min_warranty_months} months defect guarantee",
            "",
            "Could you please review these details and confirm if your organization can accommodate these terms? "
            "Upon your confirmation, we will promptly establish a bilateral deal room on SyncAlly to finalize "
            "and sign the canonical trade terms.",
            "",
            "Thank you for your prompt attention and cooperation. We look forward to building a productive partnership.",
            "",
            "Sincerely,",
            f"{contact_name}",
            f"{org_name}",
        ])

        return "\n".join(lines)
