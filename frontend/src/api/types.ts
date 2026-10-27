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

export type AgreementStatus = "PENDING_APPROVAL" | "COMMITTED" | "SUPERSEDED" | "VOIDED";

/**
 * One payment timing the trade contract supports.
 *
 * `trigger` and `dueCondition` mirror the canonical strings the backend stores
 * and hashes. `label` only reformats the machine trigger for reading; the due
 * condition is always rendered verbatim from the agreement, so a review screen
 * can never promise more than the hashed text (e.g. an "immediately" that the
 * agreement does not contain).
 */
export interface PaymentTimingOption {
  trigger: string;
  label: string;
  dueCondition: string;
}

export const SUPPORTED_PAYMENT_TIMING = [
  {
    trigger: "seller_invoice",
    label: "Upon Seller Invoice",
    dueCondition: "when seller invoices",
  },
] as const satisfies readonly PaymentTimingOption[];

/** A trigger a proposal may actually send; anything else cannot compile. */
export type PaymentTrigger = (typeof SUPPORTED_PAYMENT_TIMING)[number]["trigger"];

export function isPaymentTrigger(value: string): value is PaymentTrigger {
  return SUPPORTED_PAYMENT_TIMING.some((option) => option.trigger === value);
}

export function paymentTimingLabel(trigger: string): string {
  const normalized = trigger.trim().toLowerCase();
  const supported = SUPPORTED_PAYMENT_TIMING.find((option) => option.trigger === normalized);
  if (supported) return supported.label;
  if (!normalized) return "Not specified";
  return normalized
    .replaceAll("_", " ")
    .replace(/\b[a-z]/g, (character) => character.toUpperCase());
}

export interface AgreementLineItem {
  description: string;
  sku: string | null;
  quantity: string;
  unit: string;
  unit_price: { amount: string; currency: string };
}

export interface AgreementVersion {
  deal_id: string;
  version_number: number;
  terms_hash: string;
  status: AgreementStatus;
  /**
   * Explicit copy of the single payment obligation's timing, straight from the
   * hashed version. The API always sends these (null for a version with zero or
   * several payment terms); optional here so cached/older payloads still type-check.
   */
  payment_trigger?: string | null;
  payment_due_condition?: string | null;
  terms: {
    schema_version: number;
    buyer_id: string;
    seller_id: string;
    line_items: AgreementLineItem[];
    shipments: Array<{ quantity: string; destination: string; target_date: string | null }>;
    payment_terms: Array<{
      amount: { amount: string; currency: string };
      trigger: string;
      due_condition: string;
    }>;
    delivery_location: string;
    incoterm: string | null;
    cancellation_terms: string;
  };
  created_at: string;
  committed_at: string | null;
  approvals: AgreementApproval[];
}

export interface AgreementApproval {
  deal_id: string;
  version_number: number;
  organization_id: string;
  user_id: string;
  decision: "APPROVE" | "REJECT";
  terms_hash: string;
  created_at: string;
}

export interface PaymentStatus {
  id: string;
  milestone_sequence: number;
  amount: string;
  currency: string;
  status: string;
  reconciled_amount: string | null;
  last_checked_at: string | null;
  last_reconciled_at: string | null;
}

export interface PaymentAuthorization {
  id: string;
  status: string;
  already_existed: boolean;
}

export interface CommercialDocumentDraft {
  agreement_version_id: string;
  agreement_version_number: number;
  terms_hash: string;
  content: string;
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
  missing_fields: string[];
  guidance_message: string;
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

/**
 * Body of `POST /deals/{deal_id}/agreements/from-reviewed-terms`.
 *
 * `payment_trigger` is required from this client: the proposer confirms the
 * timing, and the server rejects an unsupported value. The server only accepts
 * an omitted field from older clients during rollout, where the sole supported
 * timing is unambiguous. The due condition is derived from the trigger by the
 * domain contract.
 */
export interface ReviewedProposalTerms extends Omit<ProposalSuggestion, "status"> {
  payment_trigger: PaymentTrigger;
}

export interface FactCorrectionResult {
  replaced_fact: DealFact;
  corrected_fact: DealFact;
}

export interface CreateDealInput {
  buyer_organization_id: string;
  seller_organization_id: string;
}

/**
 * Payload for `POST /deals/{deal_id}/messages`.
 *
 * `idempotency_key` must identify one logical message: generate it once and reuse
 * it for every retry so a replayed POST is committed only once. The server derives
 * the author and the stored `source_type` from the verified access token;
 * `source_type` is forwarded so the client stays compatible if the endpoint starts
 * accepting it. `organization_id` disambiguates the acting party for users who are
 * members of both the buyer and seller organizations.
 */
export interface CreateMessageInput {
  body: string;
  visibility: Visibility;
  idempotency_key: string;
  source_type?: string;
  source_reference?: string;
  organization_id?: string;
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
