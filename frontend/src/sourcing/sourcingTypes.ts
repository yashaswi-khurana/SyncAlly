/**
 * Sourcing domain types and UI component interfaces.
 */

export interface TechnicalSpecification {
  materials: string[];
  tolerances?: string | null;
  certifications: string[];
  standards: string[];
  quality_grade?: string | null;
  notes?: string | null;
}

export interface PricingConstraint {
  target_unit_price?: string | null;
  max_unit_price?: string | null;
  max_total_budget?: string | null;
  currency: string;
}

export interface QuantityRequirement {
  target_quantity: string;
  min_acceptable_quantity?: string | null;
  unit: string;
  packaging_preference?: string | null;
}

export interface DeliveryConstraint {
  destination_country_code: string;
  destination_port_or_city?: string | null;
  required_delivery_date?: string | null;
  max_lead_time_days?: number | null;
}

export interface CommercialTermsRequirement {
  preferred_incoterm?: string | null;
  acceptable_incoterms: string[];
  preferred_payment_term?: string | null;
  min_warranty_months: number;
  inspection_requirement: string;
}

export interface BuyerRequirements {
  title: string;
  category: string;
  description: string;
  technical_specs: TechnicalSpecification;
  pricing: PricingConstraint;
  quantity: QuantityRequirement;
  delivery: DeliveryConstraint;
  commercial_terms: CommercialTermsRequirement;
  raw_prompt?: string | null;
}

export interface AttributeComparisonRow {
  attribute: string;
  buyer_requirement: string;
  candidate_value: string;
  variance: string;
  status: "MATCH" | "ACCEPTABLE" | "GAP";
}

export interface CommercialGap {
  gap_id: string;
  field_name: string;
  category: "MISSING" | "AMBIGUOUS" | "NON_COMPLIANT";
  severity: "CRITICAL" | "MODERATE" | "LOW";
  buyer_requirement_value: string;
  seller_offered_value: string | null;
  explanation: string;
  suggested_action: string;
  negotiation_priority?: number;
}

export interface CandidateComparisonResult {
  listing_id: string;
  seller_organization_id: string;
  organization_id?: string;
  seller_organization_name: string;
  country_code: string;
  listing_title: string;
  category: string;
  unit_price: string;
  currency: string;
  available_quantity: string;
  moq: string;
  lead_time_days: number | null;
  match_tier: "A" | "B" | "C" | "D";
  composite_score: number;
  completeness_tier: string;
  attribute_matrix: AttributeComparisonRow[];
  gaps: CommercialGap[];
}

export interface MarketplaceListingDetail {
  id: string;
  organization_id: string;
  organization_name: string;
  country_code: string;
  title: string;
  category: string;
  description: string;
  available_quantity: string;
  moq?: string | null;
  unit: string;
  unit_price: string;
  currency: string;
  lead_time_days?: number | null;
  incoterms: string[];
  payment_terms?: string | null;
  technical_specs: TechnicalSpecification;
  warranty_months?: number | null;
  warranty_description?: string | null;
  inspection_terms?: string | null;
  completeness_tier: string;
}

export interface InquiryDraft {
  listing_id?: string;
  seller_organization_id?: string;
  seller_organization_name?: string;
  subject: string;
  body: string;
  gaps_addressed: string[];
  proposed_terms?: Record<string, unknown>;
}

export interface SourcingHubProps {
  organizations?: Array<{ id: string; legal_name?: string; role?: string }>;
  initialListingId?: string;
  onDealInitiated?: (dealUrl: string) => void;
  initialListings?: CandidateComparisonResult[];
}
