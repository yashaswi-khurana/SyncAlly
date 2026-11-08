"""Comparison scoring engine for evaluating candidate marketplace listings against buyer requirements.

Computes 5 weighted dimension scores:
- Specifications & Quality: 30%
- Pricing & Budget: 25%
- Quantity & MOQ: 15%
- Lead Time & Feasibility: 15%
- Commercial Terms: 15%

Produces:
- Composite score (0.0 to 100.0)
- Match tier (Tier A, Tier B, Tier C, Tier D)
- Attribute-by-attribute comparison matrix with MATCH / ACCEPTABLE_VARIANCE / GAP flags
- Disqualification assessment for category or threshold violations
"""

import re
from decimal import Decimal

from syncally.application.sourcing.gap_analyzer import GapAnalyzer
from syncally.domain.sourcing.contracts import (
    AttributeComparison,
    BuyerRequirements,
    CommercialGap,
    ComparisonResult,
    ComparisonStatus,
    MarketplaceListingDetail,
    MatchTier,
    ScoreBreakdown,
)

# Dimension Weights
WEIGHT_SPECS = 0.30
WEIGHT_PRICE = 0.25
WEIGHT_QTY = 0.15
WEIGHT_LEAD_TIME = 0.15
WEIGHT_TERMS = 0.15


def _tokenize(text: str) -> set[str]:
    """Tokenize text into lowercase alphanumeric tokens."""
    return {w for w in re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower())}


def _token_jaccard_similarity(text_a: str, text_b: str) -> float:
    """Calculate Jaccard similarity between two texts."""
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    return len(intersection) / len(union)


class ComparisonEngine:
    """Evaluates candidate listings against buyer requirements and builds comparison matrices."""

    @classmethod
    def evaluate_listing(
        cls,
        requirements: BuyerRequirements,
        listing: MarketplaceListingDetail,
    ) -> ComparisonResult:
        """Perform full multi-dimensional evaluation of a single listing."""
        # 1. Detect Gaps
        detected_gaps = GapAnalyzer.detect_gaps(requirements, listing)

        # 2. Check Disqualification
        is_disqualified = False
        disqualification_reasons: list[str] = []

        # Category mismatch check
        buyer_cat = requirements.category.strip().lower()
        seller_cat = listing.category.strip().lower()
        cat_overlap = (
            buyer_cat in seller_cat
            or seller_cat in buyer_cat
            or _token_jaccard_similarity(buyer_cat, seller_cat) > 0.2
        )
        if not cat_overlap:
            # Check if title or specs has any overlap
            title_sim = _token_jaccard_similarity(requirements.title, listing.title)
            if title_sim < 0.1:
                is_disqualified = True
                disqualification_reasons.append(
                    f"Irrelevant product category: buyer requested '{requirements.category}', listing is '{listing.category}'."
                )

        # Check severe price mismatch (>=50% over maximum budget ceiling)
        if requirements.pricing.max_unit_price is not None and requirements.pricing.max_unit_price > 0:
            if listing.unit_price >= requirements.pricing.max_unit_price * Decimal("1.5"):
                is_disqualified = True
                disqualification_reasons.append(
                    f"Severe price mismatch: quoted price {listing.unit_price} {listing.currency} exceeds maximum budget ceiling {requirements.pricing.max_unit_price} {requirements.pricing.currency} by >=50%."
                )

        # 3. Sub-scores computation
        s_specs = cls._compute_specifications_score(requirements, listing, cat_overlap)
        s_price = cls._compute_pricing_score(requirements, listing)
        s_qty = cls._compute_quantity_score(requirements, listing)
        s_lead = cls._compute_lead_time_score(requirements, listing)
        s_terms = cls._compute_terms_score(requirements, listing)

        # If disqualified, specs score drops significantly
        if is_disqualified:
            s_specs = min(s_specs, 10.0)

        # 4. Composite Score
        composite = (
            (s_specs * WEIGHT_SPECS)
            + (s_price * WEIGHT_PRICE)
            + (s_qty * WEIGHT_QTY)
            + (s_lead * WEIGHT_LEAD_TIME)
            + (s_terms * WEIGHT_TERMS)
        )
        composite = round(max(0.0, min(100.0, composite)), 2)

        # 5. Determine Tier
        if is_disqualified or composite < 50.0:
            tier = MatchTier.TIER_D
        elif composite >= 90.0:
            tier = MatchTier.TIER_A
        elif composite >= 75.0:
            tier = MatchTier.TIER_B
        else:
            tier = MatchTier.TIER_C

        score_breakdown = ScoreBreakdown(
            specifications=round(s_specs, 2),
            pricing=round(s_price, 2),
            quantity_and_moq=round(s_qty, 2),
            lead_time=round(s_lead, 2),
            commercial_terms=round(s_terms, 2),
            composite=composite,
        )

        # 6. Build Attribute Comparison Matrix
        attribute_comparisons = cls._build_comparison_matrix(requirements, listing, detected_gaps)

        return ComparisonResult(
            listing_id=listing.id,
            listing_title=listing.title,
            seller_organization_id=listing.organization_id,
            seller_organization_name=listing.organization_name,
            country_code=listing.country_code,
            unit_price=listing.unit_price,
            currency=listing.currency,
            available_quantity=listing.available_quantity,
            moq=listing.moq,
            unit=listing.unit,
            lead_time_days=listing.lead_time_days,
            composite_score=composite,
            tier=tier,
            score_breakdown=score_breakdown,
            attribute_comparisons=attribute_comparisons,
            detected_gaps=detected_gaps,
            is_disqualified=is_disqualified,
            disqualification_reasons=disqualification_reasons,
        )

    @classmethod
    def compare_multiple(
        cls,
        requirements: BuyerRequirements,
        listings: list[MarketplaceListingDetail],
    ) -> list[ComparisonResult]:
        """Evaluate and rank a collection of marketplace listings."""
        results = [cls.evaluate_listing(requirements, listing_item) for listing_item in listings]
        # Sort: Non-disqualified first, then by composite_score desc, then by fewest gaps
        results.sort(
            key=lambda r: (
                0 if not r.is_disqualified else 1,
                -r.composite_score,
                len(r.detected_gaps),
            )
        )
        return results

    # -------------------------------------------------------------------------
    # Scoring Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def _compute_specifications_score(
        cls,
        req: BuyerRequirements,
        listing: MarketplaceListingDetail,
        cat_overlap: bool,
    ) -> float:
        """Specifications score: 0 to 100."""
        score = 0.0

        # Category match (20 pts)
        if cat_overlap:
            if req.category.strip().lower() == listing.category.strip().lower():
                score += 20.0
            else:
                score += 15.0

        # Title / keyword similarity (up to 25 pts)
        buyer_text = f"{req.title} {req.description}"
        sim_title = _token_jaccard_similarity(req.title, listing.title)
        sim_desc = _token_jaccard_similarity(buyer_text, listing.title)
        listing_tokens = _tokenize(listing.title)
        buyer_tokens = _tokenize(buyer_text)
        token_recall = (
            len(listing_tokens.intersection(buyer_tokens)) / max(1, len(listing_tokens))
            if listing_tokens
            else 0.0
        )
        keyword_score = max(sim_title * 30.0, sim_desc * 35.0, token_recall * 25.0)
        score += min(25.0, max(0.0, keyword_score))

        # Materials match (20 pts)
        req_mats = req.technical_specs.materials
        listing_mats = listing.technical_specs.materials
        if not req_mats:
            score += 20.0  # Buyer has no strict material requirement
        else:
            req_set = {m.lower().strip() for m in req_mats}
            list_set = {m.lower().strip() for m in listing_mats}
            overlap = req_set.intersection(list_set)
            if overlap:
                score += (len(overlap) / len(req_set)) * 20.0
            else:
                # Check substring match
                partial_match = any(
                    any(rm in lm or lm in rm for lm in list_set)
                    for rm in req_set
                )
                if partial_match:
                    score += 10.0

        # Certifications overlap (25 pts)
        req_certs = req.technical_specs.certifications
        listing_certs = listing.technical_specs.certifications
        if not req_certs:
            score += 25.0
        else:
            req_c_set = {c.lower().strip() for c in req_certs}
            list_c_set = {c.lower().strip() for c in listing_certs}
            overlap_c = req_c_set.intersection(list_c_set)
            if overlap_c:
                score += (len(overlap_c) / len(req_c_set)) * 25.0
            else:
                score = max(0.0, score - 20.0)

        # Standards conformity (10 pts)
        req_stds = req.technical_specs.standards
        listing_stds = listing.technical_specs.standards
        if not req_stds:
            score += 10.0
        else:
            req_s_set = {s.lower().strip() for s in req_stds}
            list_s_set = {s.lower().strip() for s in listing_stds}
            overlap_s = req_s_set.intersection(list_s_set)
            score += (len(overlap_s) / len(req_s_set)) * 10.0

        return max(0.0, min(100.0, score))

    @classmethod
    def _compute_pricing_score(
        cls,
        req: BuyerRequirements,
        listing: MarketplaceListingDetail,
    ) -> float:
        """Pricing score: 0 to 100."""
        # Currency mismatch penalty
        if req.pricing.currency.upper() != listing.currency.upper():
            return 10.0

        p_seller = listing.unit_price
        if p_seller is None or p_seller <= 0:
            return 10.0

        p_target = req.pricing.target_unit_price
        p_max = req.pricing.max_unit_price

        # If neither target nor max is provided or both <= 0
        if (p_target is None or p_target <= 0) and (p_max is None or p_max <= 0):
            return 75.0

        if p_target is not None and p_target > 0:
            if p_seller <= p_target:
                return 100.0

            if p_max is not None and p_max > p_target:
                if p_seller <= p_max:
                    ratio = (p_seller - p_target) / (p_max - p_target)
                    return float(Decimal("100.0") - (Decimal("70.0") * ratio))
                else:
                    # Exceeds max budget
                    ratio = (p_seller - p_max) / p_max if p_max > 0 else Decimal("1.0")
                    return max(0.0, float(Decimal("30.0") - (Decimal("30.0") * ratio)))
            else:
                # No max price, only target price
                ratio = (p_seller - p_target) / p_target
                return max(0.0, float(Decimal("100.0") - (Decimal("100.0") * ratio)))

        # If only max_unit_price is provided and > 0
        if p_max is not None and p_max > 0:
            if p_seller <= p_max:
                return 90.0
            else:
                ratio = (p_seller - p_max) / p_max
                return max(0.0, float(Decimal("30.0") - (Decimal("30.0") * ratio)))

        return 50.0

    @classmethod
    def _compute_quantity_score(
        cls,
        req: BuyerRequirements,
        listing: MarketplaceListingDetail,
    ) -> float:
        """Quantity & MOQ score: 0 to 100 (Availability 50 pts, MOQ Fit 50 pts)."""
        q_req = req.quantity.target_quantity
        q_avail = listing.available_quantity
        score = 0.0

        # Availability (50 pts)
        if q_avail >= q_req:
            score += 50.0
        elif q_req > 0:
            ratio = float(q_avail / q_req)
            score += max(0.0, ratio * 50.0)

        # MOQ Fit (50 pts)
        if listing.moq is None:
            score += 30.0  # missing moq
        elif listing.moq <= q_req:
            score += 50.0
        elif listing.moq <= q_req * Decimal("1.5"):
            score += 25.0  # negotiable threshold
        else:
            score += 0.0  # high barrier

        return max(0.0, min(100.0, score))

    @classmethod
    def _compute_lead_time_score(
        cls,
        req: BuyerRequirements,
        listing: MarketplaceListingDetail,
    ) -> float:
        """Lead time score: 0 to 100."""
        l_seller = listing.lead_time_days
        l_buyer = req.delivery.max_lead_time_days or 30

        if l_seller is None:
            return 5.0 if l_buyer <= 14 else 25.0

        if l_seller <= (l_buyer - 7):
            return 100.0  # comfortable buffer
        elif l_seller <= l_buyer:
            return 80.0  # tight schedule
        else:
            # Over deadline
            delay = l_seller - l_buyer
            return max(0.0, 50.0 - (5.0 * delay))

    @classmethod
    def _compute_terms_score(
        cls,
        req: BuyerRequirements,
        listing: MarketplaceListingDetail,
    ) -> float:
        """Commercial terms score: 0 to 100 (Incoterms 35, Payment 35, Warranty 15, Inspection 15)."""
        score = 0.0

        # 1. Incoterms (35 pts)
        pref_inco = str(req.commercial_terms.preferred_incoterm or "").upper()
        seller_incos = [str(i).upper() for i in listing.incoterms]
        acceptable_incos = [str(i).upper() for i in req.commercial_terms.acceptable_incoterms]

        if not seller_incos:
            score += 5.0
        elif pref_inco and pref_inco in seller_incos:
            score += 35.0
        elif any(ai in seller_incos for ai in acceptable_incos):
            score += 25.0
        elif seller_incos == ["EXW"]:
            score += 10.0
        else:
            score += 15.0

        # 2. Payment Terms (35 pts)
        pt = (listing.payment_terms or "").lower()
        if not pt:
            score += 5.0
        elif any(w in pt for w in ["net 30", "net 60", "escrow"]):
            score += 35.0
        elif any(w in pt for w in ["30/70", "split"]):
            score += 25.0
        elif "50%" in pt or "deposit" in pt:
            score += 15.0
        elif "negotiable" in pt or "upon request" in pt:
            score += 10.0
        elif "100%" in pt or "prior to dispatch" in pt:
            score += 5.0
        else:
            score += 20.0

        # 3. Warranty (15 pts)
        req_w = req.commercial_terms.min_warranty_months
        if listing.warranty_months is not None:
            if listing.warranty_months >= req_w:
                score += 15.0
            elif listing.warranty_months > 0:
                score += 8.0
            else:
                score += 0.0
        elif listing.warranty_description:
            score += 5.0
        else:
            score += 0.0

        # 4. Inspection (15 pts)
        it = (listing.inspection_terms or "").lower()
        if not it:
            score += 0.0
        elif any(w in it for w in ["en 10204", "3.1", "third-party", "sgs", "lloyd"]):
            score += 15.0
        elif "factory" in it or "internal" in it or "qc" in it:
            score += 10.0
        else:
            score += 5.0

        return max(0.0, min(100.0, score))

    # -------------------------------------------------------------------------
    # Attribute Matrix Builder
    # -------------------------------------------------------------------------

    @classmethod
    def _build_comparison_matrix(
        cls,
        req: BuyerRequirements,
        listing: MarketplaceListingDetail,
        gaps: list[CommercialGap],
    ) -> list[AttributeComparison]:
        """Construct side-by-side comparison matrix items."""
        gap_map = {g.field_name: g for g in gaps}
        rows: list[AttributeComparison] = []

        # 1. Product & Specifications
        has_cat_gap = "category" in gap_map
        rows.append(
            AttributeComparison(
                field_name="product_specs",
                display_name="Product Category & Description",
                buyer_value=f"{req.category} — {req.title}",
                seller_value=f"{listing.category} — {listing.title}",
                variance=(
                    "Category mismatch"
                    if has_cat_gap
                    else "Specification aligned"
                ),
                status=ComparisonStatus.GAP if has_cat_gap else ComparisonStatus.MATCH,
                gap_category=gap_map.get("category").category if has_cat_gap else None,
                explanation=gap_map.get("category").explanation if has_cat_gap else "Category and product domain match buyer requirements.",
            )
        )

        # 2. Materials & Standards
        req_mats = ", ".join(req.technical_specs.materials) or "Standard"
        seller_mats = ", ".join(listing.technical_specs.materials) or "Standard"
        has_std_gap = "standards" in gap_map
        rows.append(
            AttributeComparison(
                field_name="materials_standards",
                display_name="Materials & Standards",
                buyer_value=f"{req_mats} | Standards: {', '.join(req.technical_specs.standards) or 'Any'}",
                seller_value=f"{seller_mats} | Standards: {', '.join(listing.technical_specs.standards) or 'Standard'}",
                variance="Standards gap identified" if has_std_gap else "Material & standard compatible",
                status=ComparisonStatus.GAP if has_std_gap else ComparisonStatus.MATCH,
                gap_category=gap_map.get("standards").category if has_std_gap else None,
                explanation=gap_map.get("standards").explanation if has_std_gap else "Materials and engineering standards satisfy specifications.",
            )
        )

        # 3. Certifications
        has_cert_gap = "certifications" in gap_map
        req_certs_str = ", ".join(req.technical_specs.certifications) or "None required"
        seller_certs_str = ", ".join(listing.technical_specs.certifications) or "None listed"
        rows.append(
            AttributeComparison(
                field_name="certifications",
                display_name="Quality & Regulatory Certifications",
                buyer_value=req_certs_str,
                seller_value=seller_certs_str,
                variance="Missing required certification(s)" if has_cert_gap else "Full certification coverage",
                status=ComparisonStatus.GAP if has_cert_gap else ComparisonStatus.MATCH,
                gap_category=gap_map.get("certifications").category if has_cert_gap else None,
                explanation=gap_map.get("certifications").explanation if has_cert_gap else "Seller possesses all requested regulatory certifications.",
            )
        )

        # 4. Unit Price
        has_price_gap = "unit_price" in gap_map
        p_target = req.pricing.target_unit_price
        p_max = req.pricing.max_unit_price
        buyer_p_str = f"Target: ${p_target:.2f}" if p_target else ""
        if p_max:
            buyer_p_str += f" (Max: ${p_max:.2f})"
        buyer_p_str += f" {req.pricing.currency}"

        seller_p_str = f"${listing.unit_price:.2f} {listing.currency}"
        if p_target and listing.unit_price <= p_target:
            diff = p_target - listing.unit_price
            variance = f"-${diff:.2f} savings below target"
            p_status = ComparisonStatus.MATCH
        elif p_max and listing.unit_price <= p_max:
            diff = listing.unit_price - (p_target or p_max)
            variance = f"+${diff:.2f} above target (within max ceiling)"
            p_status = ComparisonStatus.ACCEPTABLE_VARIANCE
        else:
            variance = "Above budget ceiling"
            p_status = ComparisonStatus.GAP

        rows.append(
            AttributeComparison(
                field_name="unit_price",
                display_name="Unit Price",
                buyer_value=buyer_p_str,
                seller_value=seller_p_str,
                variance=variance,
                status=p_status,
                gap_category=gap_map.get("unit_price").category if has_price_gap else None,
                explanation=gap_map.get("unit_price").explanation if has_price_gap else "Unit price aligns with procurement budget.",
            )
        )

        # 5. Order Quantity & MOQ
        has_moq_gap = "moq" in gap_map
        has_qty_gap = "available_quantity" in gap_map
        buyer_q_str = f"{req.quantity.target_quantity} {req.quantity.unit}"
        seller_q_str = f"Stock: {listing.available_quantity} (MOQ: {listing.moq or 'Unstated'}) {listing.unit}"
        if has_moq_gap or has_qty_gap:
            q_status = ComparisonStatus.GAP
            q_var = "MOQ barrier or capacity deficit"
        else:
            q_status = ComparisonStatus.MATCH
            q_var = "Inventory available; MOQ satisfied"

        rows.append(
            AttributeComparison(
                field_name="quantity_and_moq",
                display_name="Order Quantity & MOQ",
                buyer_value=buyer_q_str,
                seller_value=seller_q_str,
                variance=q_var,
                status=q_status,
                gap_category=gap_map.get("moq", gap_map.get("available_quantity", None)).category if (has_moq_gap or has_qty_gap) else None,
                explanation=(
                    gap_map.get("moq", gap_map.get("available_quantity")).explanation
                    if (has_moq_gap or has_qty_gap)
                    else "Seller available stock exceeds requirement and MOQ is satisfied."
                ),
            )
        )

        # 6. Lead Time
        has_lt_gap = "lead_time_days" in gap_map
        req_lt = req.delivery.max_lead_time_days or 30
        buyer_lt_str = f"Max {req_lt} days"
        seller_lt_str = f"{listing.lead_time_days} days" if listing.lead_time_days is not None else "Not specified"
        if has_lt_gap:
            lt_status = ComparisonStatus.GAP
            lt_var = "Lead time exceeds target or omitted"
        elif listing.lead_time_days is not None and listing.lead_time_days <= req_lt:
            buf = req_lt - listing.lead_time_days
            lt_status = ComparisonStatus.MATCH
            lt_var = f"+{buf} days delivery buffer"
        else:
            lt_status = ComparisonStatus.ACCEPTABLE_VARIANCE
            lt_var = "Close to deadline"

        rows.append(
            AttributeComparison(
                field_name="lead_time",
                display_name="Production & Dispatch Lead Time",
                buyer_value=buyer_lt_str,
                seller_value=seller_lt_str,
                variance=lt_var,
                status=lt_status,
                gap_category=gap_map.get("lead_time_days").category if has_lt_gap else None,
                explanation=gap_map.get("lead_time_days").explanation if has_lt_gap else "Lead time allows sufficient logistics buffer for on-time delivery.",
            )
        )

        # 7. Incoterm
        has_inco_gap = "incoterms" in gap_map
        buyer_inco_str = str(req.commercial_terms.preferred_incoterm or "DDP")
        seller_inco_str = ", ".join(str(i) for i in listing.incoterms) or "None listed"
        if has_inco_gap:
            inco_status = ComparisonStatus.GAP
            inco_var = "Preferred Incoterm unsupported"
        elif buyer_inco_str in seller_inco_str:
            inco_status = ComparisonStatus.MATCH
            inco_var = f"Direct {buyer_inco_str} support"
        else:
            inco_status = ComparisonStatus.ACCEPTABLE_VARIANCE
            inco_var = "Alternative Incoterm available"

        rows.append(
            AttributeComparison(
                field_name="incoterm",
                display_name="Incoterms (Delivery Terms)",
                buyer_value=buyer_inco_str,
                seller_value=seller_inco_str,
                variance=inco_var,
                status=inco_status,
                gap_category=gap_map.get("incoterms").category if has_inco_gap else None,
                explanation=gap_map.get("incoterms").explanation if has_inco_gap else f"Seller supports preferred freight term {buyer_inco_str}.",
            )
        )

        # 8. Payment Terms
        has_pt_gap = "payment_terms" in gap_map
        buyer_pt_str = str(req.commercial_terms.preferred_payment_term or "Net 30")
        seller_pt_str = listing.payment_terms or "Not specified"
        rows.append(
            AttributeComparison(
                field_name="payment_terms",
                display_name="Commercial Payment Terms",
                buyer_value=buyer_pt_str,
                seller_value=seller_pt_str,
                variance="Credit variance or advance required" if has_pt_gap else "Mutually compatible terms",
                status=ComparisonStatus.GAP if has_pt_gap else ComparisonStatus.MATCH,
                gap_category=gap_map.get("payment_terms").category if has_pt_gap else None,
                explanation=gap_map.get("payment_terms").explanation if has_pt_gap else "Payment terms align with corporate credit policy.",
            )
        )

        # 9. Warranty
        has_w_gap = "warranty_months" in gap_map
        buyer_w_str = f"Min {req.commercial_terms.min_warranty_months} months"
        seller_w_str = (
            f"{listing.warranty_months} months"
            if listing.warranty_months is not None
            else (listing.warranty_description or "None")
        )
        rows.append(
            AttributeComparison(
                field_name="warranty",
                display_name="Warranty & Defect Coverage",
                buyer_value=buyer_w_str,
                seller_value=seller_w_str,
                variance="Shortfall or ambiguous duration" if has_w_gap else "Warranty policy satisfied",
                status=ComparisonStatus.GAP if has_w_gap else ComparisonStatus.MATCH,
                gap_category=gap_map.get("warranty_months").category if has_w_gap else None,
                explanation=gap_map.get("warranty_months").explanation if has_w_gap else "Warranty coverage meets or exceeds requested duration.",
            )
        )

        # 10. Inspection & QC
        has_insp_gap = "inspection_terms" in gap_map
        buyer_insp_str = str(req.commercial_terms.inspection_requirement)
        seller_insp_str = listing.inspection_terms or "Not specified"
        rows.append(
            AttributeComparison(
                field_name="inspection",
                display_name="Quality Control & Inspection",
                buyer_value=buyer_insp_str,
                seller_value=seller_insp_str,
                variance="Quality verification undefined" if has_insp_gap else "Inspection terms verified",
                status=ComparisonStatus.GAP if has_insp_gap else ComparisonStatus.MATCH,
                gap_category=gap_map.get("inspection_terms").category if has_insp_gap else None,
                explanation=gap_map.get("inspection_terms").explanation if has_insp_gap else "Seller supports required inspection and certification protocols.",
            )
        )

        return rows
