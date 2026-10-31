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

export interface OrganizationDirectoryItem {
  id: string;
  legal_name: string;
  country_code: string;
}

export interface Deal {
  id: string;
  buyer_organization_id: string;
  seller_organization_id: string;
  status: string;
  version: number;
  pending_counterparty?: boolean;
}

export interface CounterpartyInvitationInput {
  buyer_organization_id: string;
  recipient_email: string;
  legal_name: string;
  country_code: string;
}

export interface Invitation {
  token: string;
  invite_url: string;
  organization_id: string;
  organization_legal_name: string;
  deal_id: string | null;
  role: string;
  expires_at: string;
  kind?: "TEAM" | "COUNTERPARTY" | null;
  pending_counterparty?: boolean;
}

export interface InvitationAcceptanceInput {
  token: string;
  email?: string;
  password?: string;
  display_name?: string;
  organization_legal_name?: string;
  country_code?: string;
}

export interface InvitationAcceptance {
  status: string;
  organization_id: string;
  organization_legal_name: string;
  user_id: string;
  role: string;
  deal_id: string | null;
  access_token?: string;
  refresh_token?: string;
  token_type?: string;
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
  id?: string | null;
  proposal_id?: string | null;
  is_current?: boolean | null;
  evidence?: AgreementEvidence[];
  grounding?: "UNMAPPED";
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
  id?: string | null;
  agreement_version_id?: string | null;
  deal_id: string;
  version_number: number;
  organization_id: string;
  user_id: string;
  decision: "APPROVE" | "REJECT";
  terms_hash: string;
  created_at: string;
}

export interface AgreementEvidence {
  trace_enabled: boolean;
  state: "AVAILABLE" | "UNAVAILABLE" | "CHANGED" | "UNKNOWN";
  grounding: "UNMAPPED";
  fact_id?: string;
  version?: number;
  agreement_version_id?: string;
  terms_hash?: string;
  organization_id?: string;
  source_message_id?: string;
  source_span?: string;
}

export interface AgreementHistory {
  deal_id: string;
  organization_id: string;
  current_version_id: string | null;
  versions: AgreementVersion[];
}

export interface AgreementComparison {
  before: AgreementVersion;
  after: AgreementVersion;
  changes: {
    fields: Array<{ field: string; before: unknown; after: unknown }>;
    collections: Record<string, {
      added: unknown[];
      removed: unknown[];
      modified: Array<{ before: unknown; after: unknown }>;
    }>;
  };
}

export type PaymentIntentStatus =
  | "AUTHORIZED"
  | "CREATE_PENDING"
  | "CREATE_UNKNOWN"
  | "PROVIDER_CREATED"
  | "SENT"
  | "PENDING"
  | "PARTIALLY_PAID"
  | "PAID"
  | "FAILED"
  | "CANCELLED";

export type PaymentMode = "PAYPAL_SANDBOX" | "OFFLINE_DEMO";

export interface PaymentPreview {
  execution_mode: PaymentMode;
  provider: "PAYPAL" | "OFFLINE_DEMO";
}

export interface PaymentStatus {
  id: string;
  milestone_sequence: number;
  amount: string;
  currency: string;
  status: PaymentIntentStatus;
  requires_polling?: boolean;
  reconciled_amount: string | null;
  last_checked_at: string | null;
  last_reconciled_at: string | null;
  invoice_url?: string | null;
  recipient_email?: string | null;
  recipient_name?: string | null;
  retry_count?: number;
  next_retry_at?: string | null;
  outbox_status?: "PENDING" | "PROCESSING" | "RETRYING" | "DELIVERED" | "FAILED" | "DEAD_LETTER" | null;
  retry_scheduled_at?: string | null;
  lease_expires_at?: string | null;
  failure_reason?: string | null;
  provider?: string;
  execution_mode?: PaymentMode | "LEGACY_UNRESOLVED";
  reconciliation_source?: "NONE" | "LEGACY_UNVERIFIED" | PaymentMode;
  invoice_reference?: string | null;
  version?: number;
}

export interface PaymentAuthorization {
  id: string;
  status: string;
  already_existed: boolean;
  provider?: string;
  execution_mode?: PaymentMode | "LEGACY_UNRESOLVED";
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

export interface CreateDealFactInput {
  organization_id: string;
  field: string;
  typed_value: string;
  currency_or_unit: string | null;
  kind: DealFact["kind"];
  visibility: Visibility;
}

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

export interface MessageExistence {
  has_messages: boolean;
}

export interface ThreadPreviewInput {
  text: string;
  organization_id: string;
}

export interface ThreadImportInput extends ThreadPreviewInput {
  digest: string;
  confirmed: boolean;
  visibility?: Visibility;
  shareable_confirmed?: boolean;
}

export interface ThreadImportPreview {
  text: string;
  digest: string;
  headers: Array<{ label: string; value: string; verified: false }>;
  warnings: string[];
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

export interface AIProvenance {
  provider: "offline" | "openai" | "unknown";
  mode: "offline" | "openai" | "openai_with_offline_fallback" | "unknown";
  model: string | null;
  context_scope: "authorized" | "shareable_only" | "authorized_private" | "unknown";
  fallback_reason: "missing_credentials" | "transient_exhausted" | null;
}

export interface FactSuggestionResult {
  status: "VALID" | "INVALID" | "NEEDS_CLARIFICATION";
  issues: Array<{ schema_version: number; code: string; path: string; message: string }>;
  facts: DealFact[];
  missing_fields: string[];
  guidance_message: string;
  provenance?: AIProvenance;
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
  provenance?: AIProvenance;
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
export interface ReviewedProposalTerms extends Omit<ProposalSuggestion, "status" | "provenance"> {
  payment_trigger: PaymentTrigger;
}

export interface FactCorrectionResult {
  replaced_fact: DealFact;
  corrected_fact: DealFact;
}

export type NegotiationAction = "submit" | "counter" | "accept" | "reject" | "supersede" | "expire";

export interface ProposalBase {
  id: string;
  terms_hash: string;
  status: string;
}

export interface CandidateAcknowledgement {
  id: string;
  version_number: number;
  terms_hash: string;
  proposal_id: string;
}

export interface NegotiationProposal extends ProposalBase {
  proposal_number: number;
  author_organization_id: string;
  based_on_proposal_id: string | null;
  terms: AgreementVersion["terms"];
  lifecycle_origin: "LEGACY" | "HUMAN_ROUNDS";
  created_at: string;
  expires_at: string | null;
  metadata_schema_version: number;
  evidence_refs: Array<{
    metadata_schema_version: number;
    fact_id: string;
    version: number;
    owner_organization_id: string;
    visibility: string;
    source_message_id: string | null;
    source_span: string | null;
  }>;
}

export interface NegotiationView {
  deal_id: string;
  deal_revision: number;
  organization_id: string;
  max_rounds: number;
  round_count: number;
  escalated: boolean;
  history_ambiguous: boolean;
  eligible_actions: NegotiationAction[];
  latest: NegotiationProposal | null;
  proposals: NegotiationProposal[];
  current_candidate: CandidateAcknowledgement | null;
  history: Array<{
    id: string;
    action: NegotiationAction | "escalate";
    proposal_id: string | null;
    predecessor_id: string | null;
    candidate_id: string | null;
    invalidated_candidate_id: string | null;
    actor_organization_id: string;
    from_status: string | null;
    to_status: string | null;
    created_at: string;
  }>;
}

export interface NegotiationInput {
  command_id: string;
  expected_deal_revision: number;
  organization_id: string;
  base: ProposalBase | null;
  terms?: ReviewedProposalTerms;
  expires_at?: string | null;
  supersede_current_candidate?: CandidateAcknowledgement | null;
  evidence?: Array<{ fact_id: string; version: number }>;
}

export interface NegotiationResult {
  outcome: "APPLIED" | "ESCALATION_REQUIRED";
  deal_revision: number;
  proposal_id: string | null;
  candidate_id: string | null;
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
  idempotency_key?: string | null;
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
