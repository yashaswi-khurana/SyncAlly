"""Gap taxonomy and detection engine for candidate marketplace listings.

Classifies discrepancies into:
- MISSING: Mandatory parameter absent from seller listing.
- AMBIGUOUS: Parameter stated vaguely or non-committally.
- NON_COMPLIANT: Parameter conflicts with buyer threshold or constraint.

Assigns severities:
- CRITICAL: Deal blocker requiring structural concession or counter-offer.
- MODERATE: Commercial risk or negotiation point.
- LOW: Operational or administrative clarification.
"""

from __future__ import annotations

from decimal import Decimal

from syncally.domain.sourcing.contracts import (
    BuyerRequirements,
    CommercialGap,
    GapCategory,
    GapSeverity,
    MarketplaceListingDetail,
    PaymentMethodPreference,
)

_AMBIGUOUS_LEAD_TIME_WORDS = ("fast", "prompt", "asap", "tbd", "depends", "turnaround", "schedule")
_AMBIGUOUS_PAYMENT_WORDS = ("negotiable", "upon request", "subject to approval", "tbd", "contact")
_AMBIGUOUS_WARRANTY_WORDS = ("standard", "merchantability", "customary", "industry norms", "per industry")


class GapAnalyzer:
    """Analyzes a candidate listing against buyer requirements and detects all commercial and technical gaps."""

    @classmethod
    def detect_gaps(
        cls,
        requirements: BuyerRequirements,
        listing: MarketplaceListingDetail,
    ) -> list[CommercialGap]:
        """Detect and classify all gaps between buyer requirements and candidate listing."""
        gaps: list[CommercialGap] = []
        counter = 1

        # ---------------------------------------------------------------------
        # 1. Price Gaps
        # ---------------------------------------------------------------------
        if listing.unit_price is None or listing.unit_price <= 0:
            gaps.append(
                CommercialGap(
                    gap_id=f"gap-{counter}",
                    field_name="unit_price",
                    category=GapCategory.MISSING,
                    severity=GapSeverity.MODERATE,
                    buyer_requirement_value=f"{requirements.pricing.target_unit_price or requirements.pricing.max_unit_price or 'Specified'} {requirements.pricing.currency}",
                    seller_offered_value="Not specified / $0.00",
                    explanation="Unit price is not specified in the listing (custom quotation required).",
                    suggested_action="Request formal price quotation for target volume.",
                    negotiation_priority=2,
                )
            )
            counter += 1
        elif requirements.pricing.currency.upper() != listing.currency.upper():
            gaps.append(
                CommercialGap(
                    gap_id=f"gap-{counter}",
                    field_name="currency",
                    category=GapCategory.AMBIGUOUS,
                    severity=GapSeverity.MODERATE,
                    buyer_requirement_value=requirements.pricing.currency,
                    seller_offered_value=listing.currency,
                    explanation=f"Currency mismatch: buyer requested {requirements.pricing.currency}, seller listed in {listing.currency}.",
                    suggested_action=f"Request binding quotation in {requirements.pricing.currency} or agree on fixed FX conversion rate.",
                    negotiation_priority=3,
                )
            )
            counter += 1
        else:
            # Price threshold evaluation
            if requirements.pricing.max_unit_price is not None and listing.unit_price > requirements.pricing.max_unit_price:
                delta = listing.unit_price - requirements.pricing.max_unit_price
                if requirements.pricing.max_unit_price > 0:
                    pct = (delta / requirements.pricing.max_unit_price) * Decimal("100")
                else:
                    pct = Decimal("100")
                gaps.append(
                    CommercialGap(
                        gap_id=f"gap-{counter}",
                        field_name="unit_price",
                        category=GapCategory.NON_COMPLIANT,
                        severity=GapSeverity.CRITICAL,
                        buyer_requirement_value=f"Max {requirements.pricing.max_unit_price:.2f} {requirements.pricing.currency}",
                        seller_offered_value=f"{listing.unit_price:.2f} {listing.currency}",
                        explanation=f"Quoted price of {listing.unit_price:.2f} {listing.currency} exceeds maximum budget ceiling of {requirements.pricing.max_unit_price:.2f} {requirements.pricing.currency} by {delta:.2f} (+{pct:.1f}%).",
                        suggested_action="Request volume discount or negotiate tiered pricing based on recurring purchase commitment.",
                        negotiation_priority=1,
                    )
                )
                counter += 1
            elif (
                requirements.pricing.target_unit_price is not None
                and listing.unit_price > requirements.pricing.target_unit_price
            ):
                delta = listing.unit_price - requirements.pricing.target_unit_price
                if requirements.pricing.target_unit_price > 0:
                    pct = (delta / requirements.pricing.target_unit_price) * Decimal("100")
                else:
                    pct = Decimal("100")
                gaps.append(
                    CommercialGap(
                        gap_id=f"gap-{counter}",
                        field_name="unit_price",
                        category=GapCategory.NON_COMPLIANT,
                        severity=GapSeverity.MODERATE,
                        buyer_requirement_value=f"Target {requirements.pricing.target_unit_price:.2f} {requirements.pricing.currency}",
                        seller_offered_value=f"{listing.unit_price:.2f} {listing.currency}",
                        explanation=f"Quoted price of {listing.unit_price:.2f} {listing.currency} is above target price of {requirements.pricing.target_unit_price:.2f} {requirements.pricing.currency} by {delta:.2f} (+{pct:.1f}%).",
                        suggested_action="Propose target price in exchange for favorable payment terms or larger order batch.",
                        negotiation_priority=2,
                    )
                )
                counter += 1

        # ---------------------------------------------------------------------
        # 2. Quantity & MOQ Gaps
        # ---------------------------------------------------------------------
        if listing.moq is None:
            gaps.append(
                CommercialGap(
                    gap_id=f"gap-{counter}",
                    field_name="moq",
                    category=GapCategory.MISSING,
                    severity=GapSeverity.MODERATE,
                    buyer_requirement_value=f"{requirements.quantity.target_quantity} {requirements.quantity.unit}",
                    seller_offered_value="Omitted",
                    explanation="Minimum Order Quantity (MOQ) is omitted from seller listing.",
                    suggested_action="Request explicit confirmation of MOQ and minimum pilot batch size.",
                    negotiation_priority=3,
                )
            )
            counter += 1
        elif listing.moq > requirements.quantity.target_quantity:
            delta = listing.moq - requirements.quantity.target_quantity
            if requirements.quantity.target_quantity > 0:
                ratio = listing.moq / requirements.quantity.target_quantity
                pct = (ratio - Decimal("1")) * Decimal("100")
                is_critical = ratio > Decimal("1.5")
            else:
                ratio = Decimal("999")
                pct = Decimal("99900")
                is_critical = True
            gaps.append(
                CommercialGap(
                    gap_id=f"gap-{counter}",
                    field_name="moq",
                    category=GapCategory.NON_COMPLIANT,
                    severity=GapSeverity.CRITICAL if is_critical else GapSeverity.MODERATE,
                    buyer_requirement_value=f"{requirements.quantity.target_quantity} {requirements.quantity.unit}",
                    seller_offered_value=f"{listing.moq} {listing.unit}",
                    explanation=f"Seller MOQ of {listing.moq} {listing.unit} exceeds requested volume of {requirements.quantity.target_quantity} {requirements.quantity.unit} by {delta} (+{pct:.0f}%).",
                    suggested_action="Propose initial pilot order at requested volume with option for recurring follow-on batches.",
                    negotiation_priority=1 if is_critical else 2,
                )
            )
            counter += 1

        if listing.available_quantity < requirements.quantity.target_quantity:
            deficit = requirements.quantity.target_quantity - listing.available_quantity
            gaps.append(
                CommercialGap(
                    gap_id=f"gap-{counter}",
                    field_name="available_quantity",
                    category=GapCategory.NON_COMPLIANT,
                    severity=GapSeverity.MODERATE,
                    buyer_requirement_value=f"{requirements.quantity.target_quantity} {requirements.quantity.unit}",
                    seller_offered_value=f"{listing.available_quantity} {listing.unit}",
                    explanation=f"Available stock of {listing.available_quantity} {listing.unit} is below required order volume of {requirements.quantity.target_quantity} {requirements.quantity.unit} (short by {deficit} {listing.unit}).",
                    suggested_action="Inquire about manufacturing replenishment capacity and phased delivery schedule.",
                    negotiation_priority=2,
                )
            )
            counter += 1

        # ---------------------------------------------------------------------
        # 3. Lead Time Gaps
        # ---------------------------------------------------------------------
        if listing.lead_time_days is None:
            desc_lower = (listing.description or "").lower()
            is_ambiguous = any(word in desc_lower for word in _AMBIGUOUS_LEAD_TIME_WORDS)
            gaps.append(
                CommercialGap(
                    gap_id=f"gap-{counter}",
                    field_name="lead_time_days",
                    category=GapCategory.AMBIGUOUS if is_ambiguous else GapCategory.MISSING,
                    severity=GapSeverity.MODERATE,
                    buyer_requirement_value=f"Max {requirements.delivery.max_lead_time_days or 30} days",
                    seller_offered_value="Not specified / Ambiguous description",
                    explanation="Production and shipment lead time is omitted or stated vaguely without definite days.",
                    suggested_action="Request confirmed production lead time and dispatch schedule in calendar days.",
                    negotiation_priority=2,
                )
            )
            counter += 1
        elif (
            requirements.delivery.max_lead_time_days is not None
            and listing.lead_time_days > requirements.delivery.max_lead_time_days
        ):
            delta_days = listing.lead_time_days - requirements.delivery.max_lead_time_days
            gaps.append(
                CommercialGap(
                    gap_id=f"gap-{counter}",
                    field_name="lead_time_days",
                    category=GapCategory.NON_COMPLIANT,
                    severity=GapSeverity.CRITICAL,
                    buyer_requirement_value=f"Max {requirements.delivery.max_lead_time_days} days",
                    seller_offered_value=f"{listing.lead_time_days} days",
                    explanation=f"Quoted lead time of {listing.lead_time_days} days exceeds required maximum of {requirements.delivery.max_lead_time_days} days by {delta_days} days.",
                    suggested_action="Inquire about expedited production, overtime shifts, or expedited freight alternatives.",
                    negotiation_priority=1,
                )
            )
            counter += 1

        # ---------------------------------------------------------------------
        # 4. Incoterms Gaps
        # ---------------------------------------------------------------------
        if not listing.incoterms:
            gaps.append(
                CommercialGap(
                    gap_id=f"gap-{counter}",
                    field_name="incoterms",
                    category=GapCategory.MISSING,
                    severity=GapSeverity.MODERATE,
                    buyer_requirement_value=str(requirements.commercial_terms.preferred_incoterm or "DDP"),
                    seller_offered_value="Omitted",
                    explanation="Supported Incoterms are omitted from listing.",
                    suggested_action=f"Request quotation under {requirements.commercial_terms.preferred_incoterm or 'DDP'} terms to destination.",
                    negotiation_priority=2,
                )
            )
            counter += 1
        elif requirements.commercial_terms.preferred_incoterm:
            pref = str(requirements.commercial_terms.preferred_incoterm).upper()
            seller_incos = [str(i).upper() for i in listing.incoterms]
            if pref not in seller_incos:
                is_exw_only = seller_incos == ["EXW"]
                gaps.append(
                    CommercialGap(
                        gap_id=f"gap-{counter}",
                        field_name="incoterms",
                        category=GapCategory.NON_COMPLIANT,
                        severity=GapSeverity.MODERATE if is_exw_only else GapSeverity.LOW,
                        buyer_requirement_value=pref,
                        seller_offered_value=", ".join(seller_incos),
                        explanation=(
                            f"Seller only offers restrictive EXW terms, whereas buyer requires {pref}."
                            if is_exw_only
                            else f"Seller offers {', '.join(seller_incos)}, which does not include preferred {pref}."
                        ),
                        suggested_action=f"Request quotation under {pref} to {requirements.delivery.destination_port_or_city or requirements.delivery.destination_country_code}.",
                        negotiation_priority=2 if is_exw_only else 3,
                    )
                )
                counter += 1

        # ---------------------------------------------------------------------
        # 5. Payment Terms Gaps
        # ---------------------------------------------------------------------
        if not listing.payment_terms:
            gaps.append(
                CommercialGap(
                    gap_id=f"gap-{counter}",
                    field_name="payment_terms",
                    category=GapCategory.MISSING,
                    severity=GapSeverity.MODERATE,
                    buyer_requirement_value=str(requirements.commercial_terms.preferred_payment_term or "Net 30"),
                    seller_offered_value="Omitted",
                    explanation="Payment terms are not specified in listing.",
                    suggested_action=f"Propose standard payment terms ({requirements.commercial_terms.preferred_payment_term or 'Net 30'} or SyncAlly Escrow).",
                    negotiation_priority=2,
                )
            )
            counter += 1
        else:
            pt_lower = listing.payment_terms.lower()
            if any(w in pt_lower for w in _AMBIGUOUS_PAYMENT_WORDS):
                gaps.append(
                    CommercialGap(
                        gap_id=f"gap-{counter}",
                        field_name="payment_terms",
                        category=GapCategory.AMBIGUOUS,
                        severity=GapSeverity.MODERATE,
                        buyer_requirement_value=str(requirements.commercial_terms.preferred_payment_term or "Net 30"),
                        seller_offered_value=listing.payment_terms,
                        explanation=f"Payment terms are stated vaguely: '{listing.payment_terms}'.",
                        suggested_action=f"Request formal confirmation of {requirements.commercial_terms.preferred_payment_term or 'Net 30'} or SyncAlly Escrow.",
                        negotiation_priority=2,
                    )
                )
                counter += 1
            elif any(w in pt_lower for w in ["advance", "deposit", "prior to dispatch"]) and (
                requirements.commercial_terms.preferred_payment_term in (
                    PaymentMethodPreference.NET_30,
                    PaymentMethodPreference.NET_60,
                    PaymentMethodPreference.ESCROW,
                )
            ):
                gaps.append(
                    CommercialGap(
                        gap_id=f"gap-{counter}",
                        field_name="payment_terms",
                        category=GapCategory.NON_COMPLIANT,
                        severity=GapSeverity.MODERATE,
                        buyer_requirement_value=str(requirements.commercial_terms.preferred_payment_term),
                        seller_offered_value=listing.payment_terms,
                        explanation=f"Seller requires upfront deposit/advance ('{listing.payment_terms}'), which conflicts with preferred credit terms.",
                        suggested_action="Propose compromise: 30% deposit with 70% against Bill of Lading, or full protection via SyncAlly Escrow.",
                        negotiation_priority=2,
                    )
                )
                counter += 1

        # ---------------------------------------------------------------------
        # 6. Warranty Gaps
        # ---------------------------------------------------------------------
        if listing.warranty_months is None and not listing.warranty_description:
            gaps.append(
                CommercialGap(
                    gap_id=f"gap-{counter}",
                    field_name="warranty_months",
                    category=GapCategory.MISSING,
                    severity=GapSeverity.MODERATE,
                    buyer_requirement_value=f"Min {requirements.commercial_terms.min_warranty_months} months",
                    seller_offered_value="Omitted",
                    explanation="Warranty terms and duration are omitted from listing.",
                    suggested_action=f"Request confirmation of minimum {requirements.commercial_terms.min_warranty_months}-month warranty coverage.",
                    negotiation_priority=2,
                )
            )
            counter += 1
        elif listing.warranty_months is None and listing.warranty_description:
            w_desc_lower = listing.warranty_description.lower()
            if any(w in w_desc_lower for w in _AMBIGUOUS_WARRANTY_WORDS):
                gaps.append(
                    CommercialGap(
                        gap_id=f"gap-{counter}",
                        field_name="warranty_months",
                        category=GapCategory.AMBIGUOUS,
                        severity=GapSeverity.MODERATE,
                        buyer_requirement_value=f"Min {requirements.commercial_terms.min_warranty_months} months",
                        seller_offered_value=listing.warranty_description,
                        explanation=f"Warranty is stated vaguely: '{listing.warranty_description}' without defined duration in months.",
                        suggested_action=f"Request explicit confirmation of a {requirements.commercial_terms.min_warranty_months}-month written manufacturer warranty.",
                        negotiation_priority=2,
                    )
                )
                counter += 1
        elif (
            listing.warranty_months is not None
            and listing.warranty_months < requirements.commercial_terms.min_warranty_months
        ):
            diff = requirements.commercial_terms.min_warranty_months - listing.warranty_months
            gaps.append(
                CommercialGap(
                    gap_id=f"gap-{counter}",
                    field_name="warranty_months",
                    category=GapCategory.NON_COMPLIANT,
                    severity=GapSeverity.MODERATE,
                    buyer_requirement_value=f"Min {requirements.commercial_terms.min_warranty_months} months",
                    seller_offered_value=f"{listing.warranty_months} months",
                    explanation=f"Quoted warranty of {listing.warranty_months} months is below required {requirements.commercial_terms.min_warranty_months} months (short by {diff} months).",
                    suggested_action=f"Negotiate an extended warranty period to reach {requirements.commercial_terms.min_warranty_months} months.",
                    negotiation_priority=3,
                )
            )
            counter += 1

        # ---------------------------------------------------------------------
        # 7. Technical Specifications & Certifications Gaps
        # ---------------------------------------------------------------------
        for cert in requirements.technical_specs.certifications:
            if not any(cert.lower() == c.lower() for c in listing.technical_specs.certifications):
                is_crit = cert.upper() in ("CE", "FDA", "FDA 510(K)", "ISO 13485", "AS9100D")
                gaps.append(
                    CommercialGap(
                        gap_id=f"gap-{counter}",
                        field_name="certifications",
                        category=GapCategory.NON_COMPLIANT,
                        severity=GapSeverity.CRITICAL if is_crit else GapSeverity.MODERATE,
                        buyer_requirement_value=cert,
                        seller_offered_value=", ".join(listing.technical_specs.certifications) or "None",
                        explanation=f"Mandatory certification '{cert}' is not documented in seller listing.",
                        suggested_action=f"Request seller to provide official '{cert}' certification document or Declaration of Conformity.",
                        negotiation_priority=1 if is_crit else 2,
                    )
                )
                counter += 1

        for std in requirements.technical_specs.standards:
            if not any(std.lower() == s.lower() for s in listing.technical_specs.standards):
                gaps.append(
                    CommercialGap(
                        gap_id=f"gap-{counter}",
                        field_name="standards",
                        category=GapCategory.NON_COMPLIANT,
                        severity=GapSeverity.MODERATE,
                        buyer_requirement_value=std,
                        seller_offered_value=", ".join(listing.technical_specs.standards) or "None",
                        explanation=f"Required standard '{std}' is not documented in seller listing.",
                        suggested_action=f"Confirm product compliance with {std} and request test reports.",
                        negotiation_priority=2,
                    )
                )
                counter += 1

        # ---------------------------------------------------------------------
        # 8. Inspection Gaps
        # ---------------------------------------------------------------------
        if not listing.inspection_terms:
            gaps.append(
                CommercialGap(
                    gap_id=f"gap-{counter}",
                    field_name="inspection_terms",
                    category=GapCategory.MISSING,
                    severity=GapSeverity.LOW,
                    buyer_requirement_value=str(requirements.commercial_terms.inspection_requirement),
                    seller_offered_value="Omitted",
                    explanation="Quality control and pre-shipment inspection terms are not defined in listing.",
                    suggested_action=f"Request agreement for {requirements.commercial_terms.inspection_requirement} prior to dispatch.",
                    negotiation_priority=3,
                )
            )
            counter += 1
        elif (
            "standard" in listing.inspection_terms.lower()
            and "check" in listing.inspection_terms.lower()
        ):
            gaps.append(
                CommercialGap(
                    gap_id=f"gap-{counter}",
                    field_name="inspection_terms",
                    category=GapCategory.AMBIGUOUS,
                    severity=GapSeverity.LOW,
                    buyer_requirement_value=str(requirements.commercial_terms.inspection_requirement),
                    seller_offered_value=listing.inspection_terms,
                    explanation=f"Inspection protocol is vague: '{listing.inspection_terms}'.",
                    suggested_action="Specify formal quality release criteria and pre-shipment test documentation.",
                    negotiation_priority=3,
                )
            )
            counter += 1

        # Sort gaps by negotiation_priority (1 first)
        gaps.sort(key=lambda g: (g.negotiation_priority, 0 if g.severity == GapSeverity.CRITICAL else (1 if g.severity == GapSeverity.MODERATE else 2)))
        return gaps
