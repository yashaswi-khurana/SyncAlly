export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Organization {
  id: string;
  legal_name: string;
  country_code: string;
  role: string;
}

export interface Deal {
  id: string;
  buyer_organization_id: string;
  seller_organization_id: string;
  status: string;
  version: number;
}

export type ViewerRole = "BUYER" | "SELLER" | "BOTH";

export interface DealSummary extends Deal {
  viewer_role: ViewerRole;
}

export type Visibility = "PRIVATE" | "SHAREABLE";

export type FactStatus =
  | "EXTRACTED"
  | "NEEDS_CLARIFICATION"
  | "CONFIRMED"
  | "REJECTED"
  | "SUPERSEDED";

export interface DealMessage {
  id: string;
  conversation_id: string;
  author_user_id: string | null;
  author_agent_id: string | null;
  body: string;
  visibility: Visibility;
  source_type: "USER" | "AGENT";
  source_reference: string | null;
  created_at: string;
}

export interface DealFact {
  id: string;
  deal_id: string;
  owner_organization_id: string;
  field: string;
  typed_value: string;
  currency_or_unit: string | null;
  kind: string;
  status: FactStatus;
  visibility: Visibility;
  source_message_id: string | null;
  source_span: string | null;
  confirmed_by: string | null;
  confirmed_at: string | null;
  version: number;
  created_at: string;
}

export type FactReviewAction = "confirm" | "reject" | "clarify";

export interface FactSuggestionResult {
  status: "VALID" | "INVALID" | "NEEDS_CLARIFICATION";
  issues: Array<{ schema_version: number; code: string; path: string; message: string }>;
  facts: DealFact[];
}

export interface ProposalSuggestion {
  schema_version: number;
  description: string;
  quantity: string;
  unit: string;
  unit_price: string;
  currency: "USD";
  delivery_destination: string;
  delivery_date: string | null;
  status: "DRAFT";
}

export interface FactCorrectionResult {
  replaced_fact: DealFact;
  corrected_fact: DealFact;
}

export interface CreateDealInput {
  buyer_organization_id: string;
  seller_organization_id: string;
}

export interface CreateOrganizationInput {
  legal_name: string;
  country_code: string;
}

export interface OrganizationMember {
  user_id: string;
  email: string;
  role: string;
}
