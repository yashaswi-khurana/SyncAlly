/**
 * Legacy deterministic sourcing helpers retained for isolated UI tests.
 *
 * SourcingHubPage delegates interpretation, evaluation, and inquiry drafting
 * to the backend; these helpers are not the production sourcing request path.
 */

import type {
  AttributeComparisonRow,
  BuyerRequirements,
  CandidateComparisonResult,
  CommercialGap,
  InquiryDraft,
  MarketplaceListingDetail,
} from "./sourcingTypes";

/**
 * Deterministically parses natural language sourcing prompt into structured requirements.
 */
export function interpretPrompt(rawPrompt: string): BuyerRequirements {
  const prompt = rawPrompt.trim();

  // Category detection
  let category = "Industrial Fasteners";
  if (/\b(wire|cable|coaxial|sensor|transducer|harness|copper|micro-coaxial|iot|electronics)\b/i.test(prompt)) {
    category = "Electronics";
  } else if (/\b(coffee|grain|wheat|soybean|beans|organic|arabica|agricultural|crop)\b/i.test(prompt)) {
    category = "Agricultural Commodities";
  } else if (/\b(fabric|textile|cotton|canvas|poplin|aramid|nomex|yarn|duck)\b/i.test(prompt)) {
    category = "Textiles";
  } else if (/(gloves|medical|scalpel|sterile|\bppe\b|nitrile|fda|hospital)/i.test(prompt)) {
    category = "Medical Supplies";
  } else if (/(bolt|fastener|screw|hex|stainless|a4-70|a4-80|din|nut|stud)/i.test(prompt)) {
    category = "Industrial Fasteners";
  }

  // Quantity and unit extraction
  let targetQuantity = "1000";
  let unit = "boxes";
  const qtyMatch = prompt.match(/(\d[\d,]*)\s*(boxes|units|pcs|pieces|meters|yards|metric tons|bags|kg)/i);
  if (qtyMatch) {
    targetQuantity = qtyMatch[1].replace(/,/g, "");
    unit = qtyMatch[2].toLowerCase();
  } else {
    const rawNumberMatch = prompt.match(/(\d[\d,]*)\s*(?:of|units?)/i);
    if (rawNumberMatch) {
      targetQuantity = rawNumberMatch[1].replace(/,/g, "");
      unit = "units";
    }
  }

  // Target and max price extraction
  let targetPrice = "12.00";
  let maxPrice = "14.00";
  const maxPriceMatch = prompt.match(/(?:max|target|budget|price|ceiling|at most)\s*(?:of\s*)?\$?\s*(\d+(?:\.\d{1,2})?)/i);
  if (maxPriceMatch) {
    maxPrice = maxPriceMatch[1];
    const parsed = parseFloat(maxPrice);
    targetPrice = (parsed * 0.85).toFixed(2);
  } else {
    const dollarMatch = prompt.match(/\$\s*(\d+(?:\.\d{1,2})?)/);
    if (dollarMatch) {
      targetPrice = dollarMatch[1];
      maxPrice = (parseFloat(targetPrice) * 1.15).toFixed(2);
    }
  }

  // Destination country code and city
  let destinationCountryCode = "DE";
  let destinationPortOrCity: string | null = null;
  if (/berlin/i.test(prompt)) {
    destinationPortOrCity = "Berlin";
    destinationCountryCode = "DE";
  } else if (/hamburg/i.test(prompt)) {
    destinationPortOrCity = "Hamburg";
    destinationCountryCode = "DE";
  } else if (/london/i.test(prompt)) {
    destinationPortOrCity = "London";
    destinationCountryCode = "GB";
  } else if (/usa|united states|new york/i.test(prompt)) {
    destinationPortOrCity = "New York";
    destinationCountryCode = "US";
  } else if (/poland|warsaw/i.test(prompt)) {
    destinationCountryCode = "PL";
  }

  // Lead time extraction
  let maxLeadTimeDays = 30;
  const leadMatch = prompt.match(/(\d+)\s*(?:calendar\s*)?days?/i);
  if (leadMatch) {
    maxLeadTimeDays = parseInt(leadMatch[1], 10);
  }

  // Incoterms
  let preferredIncoterm = "DDP";
  if (/\b(DDP|CIF|FOB|EXW|CIP|DAP)\b/i.test(prompt)) {
    preferredIncoterm = prompt.match(/\b(DDP|CIF|FOB|EXW|CIP|DAP)\b/i)![1].toUpperCase();
  }

  // Standards and materials
  const materials: string[] = [];
  if (/316\s*stainless/i.test(prompt)) materials.push("316 Stainless Steel");
  if (/304\s*stainless/i.test(prompt)) materials.push("304 Stainless Steel");
  if (/copper/i.test(prompt)) materials.push("Copper");
  if (/cotton/i.test(prompt)) materials.push("100% Cotton");
  if (/nitrile/i.test(prompt)) materials.push("Medical Nitrile");
  if (/coffee/i.test(prompt)) materials.push("100% Arabica Green Coffee");
  if (/soybean/i.test(prompt)) materials.push("Non-GMO Yellow Soybeans");
  if (/wheat/i.test(prompt)) materials.push("Milling Wheat");

  const standards: string[] = [];
  if (/din\s*933/i.test(prompt)) standards.push("DIN 933");
  if (/iso\s*4017/i.test(prompt)) standards.push("ISO 4017");
  if (/en\s*455/i.test(prompt)) standards.push("EN 455");

  const certifications: string[] = [];
  if (/iso\s*9001/i.test(prompt)) certifications.push("ISO 9001");
  if (/fda/i.test(prompt)) certifications.push("FDA 510(k)");
  if (/ce\b/i.test(prompt)) certifications.push("CE");
  if (/rohs/i.test(prompt)) certifications.push("RoHS");
  if (/organic/i.test(prompt)) certifications.push("USDA Organic");
  if (/fair\s*trade/i.test(prompt)) certifications.push("Fair Trade Certified");

  return {
    title: prompt.slice(0, 80),
    category,
    description: prompt,
    technical_specs: {
      materials,
      tolerances: "+/- 0.05mm",
      certifications,
      standards,
      quality_grade: "A4-70",
      notes: null,
    },
    pricing: {
      target_unit_price: targetPrice,
      max_unit_price: maxPrice,
      currency: "USD",
    },
    quantity: {
      target_quantity: targetQuantity,
      unit,
    },
    delivery: {
      destination_country_code: destinationCountryCode,
      destination_port_or_city: destinationPortOrCity,
      max_lead_time_days: maxLeadTimeDays,
    },
    commercial_terms: {
      preferred_incoterm: preferredIncoterm,
      acceptable_incoterms: ["DDP", "CIF", "FOB"],
      min_warranty_months: 12,
      inspection_requirement: "FACTORY_MILL_CERTIFICATE",
    },
    raw_prompt: prompt,
  };
}

/**
 * Evaluates candidate listing against buyer criteria, producing composite score,
 * tier, comparison matrix, and detected commercial gaps.
 */
export function evaluateCandidateListing(
  listingOrReq: MarketplaceListingDetail | BuyerRequirements,
  reqOrListing: BuyerRequirements | MarketplaceListingDetail,
): CandidateComparisonResult {
  const listing = ("id" in listingOrReq ? listingOrReq : reqOrListing) as MarketplaceListingDetail;
  const req = ("category" in listingOrReq && !("id" in listingOrReq) ? listingOrReq : reqOrListing) as BuyerRequirements;
  const attributeMatrix: AttributeComparisonRow[] = [];
  const gaps: CommercialGap[] = [];

  let specScore: number;
  let priceScore: number;
  let qtyScore: number;
  let leadScore: number;
  let termsScore = 80;

  // 1. Specs evaluation
  const categoryMatch = listing.category.toLowerCase().includes(req.category.toLowerCase()) ||
    req.category.toLowerCase().includes(listing.category.toLowerCase());
  if (categoryMatch) {
    specScore = 95;
    attributeMatrix.push({
      attribute: "Product / Specs",
      buyer_requirement: req.title || req.category,
      candidate_value: listing.title,
      variance: "Compatible sector & specifications",
      status: "MATCH",
    });
  } else {
    specScore = 40;
    attributeMatrix.push({
      attribute: "Product / Specs",
      buyer_requirement: req.category,
      candidate_value: listing.category,
      variance: "Sector discrepancy",
      status: "GAP",
    });
    gaps.push({
      gap_id: `gap-${listing.id}-category`,
      field_name: "category",
      category: "NON_COMPLIANT",
      severity: "CRITICAL",
      buyer_requirement_value: req.category,
      seller_offered_value: listing.category,
      explanation: `Listing category '${listing.category}' does not match required sector '${req.category}'.`,
      suggested_action: "Verify if seller produces products in the requested category.",
    });
  }

  // 2. Price evaluation
  const unitPrice = parseFloat(listing.unit_price);
  const maxPrice = req.pricing.max_unit_price ? parseFloat(req.pricing.max_unit_price) : 14.0;
  if (unitPrice <= maxPrice) {
    const delta = maxPrice - unitPrice;
    priceScore = 95;
    attributeMatrix.push({
      attribute: "Unit Price",
      buyer_requirement: `Max $${maxPrice.toFixed(2)} USD`,
      candidate_value: `$${unitPrice.toFixed(2)} ${listing.currency}`,
      variance: delta > 0 ? `-$${delta.toFixed(2)} below max` : "Exact match to budget",
      status: "MATCH",
    });
  } else {
    const overPercent = (((unitPrice - maxPrice) / maxPrice) * 100).toFixed(1);
    priceScore = 30;
    attributeMatrix.push({
      attribute: "Unit Price",
      buyer_requirement: `Max $${maxPrice.toFixed(2)} USD`,
      candidate_value: `$${unitPrice.toFixed(2)} ${listing.currency}`,
      variance: `+${overPercent}% over budget`,
      status: "GAP",
    });
    gaps.push({
      gap_id: `gap-${listing.id}-price`,
      field_name: "unit_price",
      category: "NON_COMPLIANT",
      severity: "CRITICAL",
      buyer_requirement_value: `Max $${maxPrice.toFixed(2)} USD`,
      seller_offered_value: `$${unitPrice.toFixed(2)} ${listing.currency}`,
      explanation: `Quoted price of $${unitPrice.toFixed(2)} ${listing.currency} exceeds maximum budget ceiling of $${maxPrice.toFixed(2)} USD by ${overPercent}%.`,
      suggested_action: "Negotiate volume tiered discount or disqualify candidate.",
    });
  }

  // 3. Quantity & MOQ evaluation
  const targetQty = parseFloat(req.quantity.target_quantity) || 1000;
  const sellerMoq = listing.moq ? parseFloat(listing.moq) : 0;
  if (sellerMoq <= targetQty) {
    qtyScore = 95;
    attributeMatrix.push({
      attribute: "Order Quantity",
      buyer_requirement: `${targetQty.toLocaleString()} ${req.quantity.unit}`,
      candidate_value: `${parseFloat(listing.available_quantity).toLocaleString()} available (MOQ ${sellerMoq})`,
      variance: "Within capacity",
      status: "MATCH",
    });
  } else {
    const moqExcess = (((sellerMoq - targetQty) / targetQty) * 100).toFixed(0);
    qtyScore = 40;
    attributeMatrix.push({
      attribute: "Order Quantity",
      buyer_requirement: `${targetQty.toLocaleString()} ${req.quantity.unit}`,
      candidate_value: `MOQ: ${sellerMoq.toLocaleString()} ${listing.unit}`,
      variance: `+${moqExcess}% above demand`,
      status: "GAP",
    });
    gaps.push({
      gap_id: `gap-${listing.id}-moq`,
      field_name: "moq",
      category: "NON_COMPLIANT",
      severity: "CRITICAL",
      buyer_requirement_value: `${targetQty} ${req.quantity.unit}`,
      seller_offered_value: `${sellerMoq} ${listing.unit}`,
      explanation: `Seller MOQ of ${sellerMoq.toLocaleString()} ${listing.unit} exceeds requested volume of ${targetQty.toLocaleString()} ${req.quantity.unit} by ${moqExcess}%.`,
      suggested_action: `Propose an initial trial batch of ${targetQty.toLocaleString()} ${req.quantity.unit} at negotiated rate.`,
    });
  }

  // 4. Lead time evaluation
  const maxDays = req.delivery.max_lead_time_days || 30;
  if (listing.lead_time_days === null || listing.lead_time_days === undefined) {
    leadScore = 50;
    attributeMatrix.push({
      attribute: "Lead Time",
      buyer_requirement: `Max ${maxDays} days`,
      candidate_value: "Not Specified",
      variance: "Missing dispatch time",
      status: "GAP",
    });
    gaps.push({
      gap_id: `gap-${listing.id}-lead-missing`,
      field_name: "lead_time_days",
      category: "MISSING",
      severity: "MODERATE",
      buyer_requirement_value: `${maxDays} days`,
      seller_offered_value: null,
      explanation: "Production and shipment lead time is omitted from listing.",
      suggested_action: "Request explicit lead time confirmation in calendar days.",
    });
  } else if (listing.lead_time_days <= maxDays) {
    const buffer = maxDays - listing.lead_time_days;
    leadScore = 95;
    attributeMatrix.push({
      attribute: "Lead Time",
      buyer_requirement: `Max ${maxDays} days`,
      candidate_value: `${listing.lead_time_days} days`,
      variance: `+${buffer} days buffer`,
      status: "MATCH",
    });
  } else {
    const overdue = listing.lead_time_days - maxDays;
    leadScore = 35;
    attributeMatrix.push({
      attribute: "Lead Time",
      buyer_requirement: `Max ${maxDays} days`,
      candidate_value: `${listing.lead_time_days} days`,
      variance: `+${overdue} days overdue`,
      status: "GAP",
    });
    gaps.push({
      gap_id: `gap-${listing.id}-lead-overdue`,
      field_name: "lead_time_days",
      category: "NON_COMPLIANT",
      severity: "CRITICAL",
      buyer_requirement_value: `${maxDays} days`,
      seller_offered_value: `${listing.lead_time_days} days`,
      explanation: `Quoted lead time of ${listing.lead_time_days} days exceeds delivery window of ${maxDays} days.`,
      suggested_action: "Inquire whether expedited production or airfreight is available.",
    });
  }

  // 5. Commercial terms / warranty / Incoterms
  if (listing.incoterms.length > 0 && req.commercial_terms.preferred_incoterm &&
      listing.incoterms.map((i) => i.toUpperCase()).includes(req.commercial_terms.preferred_incoterm.toUpperCase())) {
    termsScore = 95;
    attributeMatrix.push({
      attribute: "Incoterm",
      buyer_requirement: req.commercial_terms.preferred_incoterm,
      candidate_value: `${req.commercial_terms.preferred_incoterm} supported`,
      variance: "Matches preference",
      status: "MATCH",
    });
  } else if (listing.incoterms.length === 0) {
    termsScore = 60;
    attributeMatrix.push({
      attribute: "Incoterm",
      buyer_requirement: req.commercial_terms.preferred_incoterm || "DDP",
      candidate_value: "Not Specified",
      variance: "Incoterms missing from listing",
      status: "GAP",
    });
    gaps.push({
      gap_id: `gap-${listing.id}-incoterm`,
      field_name: "incoterms",
      category: "MISSING",
      severity: "MODERATE",
      buyer_requirement_value: req.commercial_terms.preferred_incoterm || "DDP",
      seller_offered_value: null,
      explanation: "Trade delivery terms (Incoterms 2020) are unspecified.",
      suggested_action: "Clarify whether seller provides DDP or CIF shipping.",
    });
  } else if (listing.incoterms.includes("EXW") && req.commercial_terms.preferred_incoterm !== "EXW") {
    termsScore = 55;
    attributeMatrix.push({
      attribute: "Incoterm",
      buyer_requirement: req.commercial_terms.preferred_incoterm || "DDP",
      candidate_value: "EXW Works only",
      variance: "Buyer must arrange freight",
      status: "GAP",
    });
    gaps.push({
      gap_id: `gap-${listing.id}-exw`,
      field_name: "incoterms",
      category: "NON_COMPLIANT",
      severity: "MODERATE",
      buyer_requirement_value: req.commercial_terms.preferred_incoterm || "DDP",
      seller_offered_value: "EXW",
      explanation: "Seller only offers Ex-Works; buyer assumes all freight and customs liability.",
      suggested_action: "Request freight quote or proposal under CIF/DDP terms.",
    });
  }

  // Warranty ambiguity check
  if (listing.warranty_description && /standard warranty/i.test(listing.warranty_description)) {
    termsScore = Math.min(termsScore, 70);
    attributeMatrix.push({
      attribute: "Warranty",
      buyer_requirement: "12 months min",
      candidate_value: "Standard warranty applies",
      variance: "Ambiguous duration",
      status: "GAP",
    });
    gaps.push({
      gap_id: `gap-${listing.id}-warranty`,
      field_name: "warranty_terms",
      category: "AMBIGUOUS",
      severity: "MODERATE",
      buyer_requirement_value: "12 months replacement",
      seller_offered_value: "Standard warranty",
      explanation: "Warranty terms state 'standard' without defining defect claim protocols.",
      suggested_action: "Request formal 12-month defect warranty commitment.",
    });
  }

  // Weighted composite score (Specs 30%, Price 25%, Qty/MOQ 15%, Lead Time 15%, Terms 15%)
  const compositeScore = (specScore * 0.3) + (priceScore * 0.25) + (qtyScore * 0.15) + (leadScore * 0.15) + (termsScore * 0.15);

  const matchTier: "A" | "B" | "C" | "D" =
    compositeScore >= 90 ? "A" : compositeScore >= 75 ? "B" : compositeScore >= 50 ? "C" : "D";

  return {
    listing_id: listing.id,
    seller_organization_id: listing.organization_id,
    organization_id: listing.organization_id,
    seller_organization_name: listing.organization_name,
    country_code: listing.country_code,
    listing_title: listing.title,
    category: listing.category,
    unit_price: listing.unit_price,
    currency: listing.currency,
    available_quantity: listing.available_quantity,
    moq: listing.moq || "0",
    lead_time_days: listing.lead_time_days ?? null,
    match_tier: matchTier,
    composite_score: Math.round(compositeScore * 10) / 10,
    completeness_tier: listing.completeness_tier,
    attribute_matrix: attributeMatrix,
    gaps,
  };
}

/**
 * Re-scores candidates dynamically based on budget or quantity override.
 */
export function rescoreCandidatesWithOverrides(
  candidates: CandidateComparisonResult[],
  maxPrice: number,
): CandidateComparisonResult[] {
  return candidates.map((candidate) => {
    const price = parseFloat(candidate.unit_price);
    if (price > maxPrice) {
      const overRatio = (price - maxPrice) / maxPrice;
      const penalty = Math.min(50, 25 + overRatio * 25);
      const rescoredScore = Math.max(10, Math.round((candidate.composite_score - penalty) * 10) / 10);
      return {
        ...candidate,
        match_tier: "D" as const,
        composite_score: rescoredScore,
      };
    }
    return candidate;
  });
}

/**
 * Synthesizes targeted professional B2B inquiry letter addressing candidate and identified gaps.
 */
export function draftSellerInquiry(
  candidate: CandidateComparisonResult,
  targetQuantity: string,
  unit: string,
): InquiryDraft {
  const subject = `Commercial Sourcing Inquiry: ${candidate.listing_title} — RFQ`;

  const body =
    candidate.gaps.length === 0
      ? `Dear ${candidate.seller_organization_name},\n\nWe evaluated your listing for ${candidate.listing_title} and would like to proceed with a purchase order of ${targetQuantity} ${unit} under DDP terms.`
      : `Dear ${candidate.seller_organization_name},\n\nWe are interested in your listing for ${candidate.listing_title}. We noted the following commercial points:\n\n${candidate.gaps
          .map((g, idx) => `${idx + 1}. ${g.explanation} (Suggested action: ${g.suggested_action})`)
          .join("\n\n")}\n\nPlease let us know if you can accommodate these terms.`;

  return {
    listing_id: candidate.listing_id,
    seller_organization_name: candidate.seller_organization_name,
    subject,
    body,
    gaps_addressed: candidate.gaps.map((g) => g.field_name),
  };
}
