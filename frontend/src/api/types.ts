export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface CurrentUser {
  email: string;
  display_name: string;
  system_role: string;
}

export interface PlatformOrganization {
  id: string;
  legal_name: string;
  country_code: string;
  status: string;
  created_at: string;
}

export type OrganizationCapability =
  | "ADMINISTRATION"
  | "DRAFTING"
  | "AGREEMENT_APPROVAL"
  | "FINANCE"
  | "FULFILLMENT";

export interface Organization {
  id: string;
  legal_name: string;
  country_code: string;
  role: string;
  capabilities?: OrganizationCapability[] | string[];
  products?: string[];
  regions?: string[];
}

export interface OrganizationDirectoryItem {
  id: string;
  legal_name: string;
  country_code: string;
  capabilities?: string[];
  products?: string[];
  regions?: string[];
}

export interface OrganizationDirectorySearch {
  q?: string;
  product?: string;
  capability?: string;
  region?: string;
  country_code?: string;
}

export interface MarketplaceListing {
  id: string;
  organization_id: string;
  organization_name: string;
  country_code: string;
  title: string;
  description: string;
  category: string;
  available_quantity: string;
  unit: string;
  unit_price: string;
  currency: string;
}

export interface CreateMarketplaceListingInput {
  organization_id: string;
  title: string;
  description: string;
  category: string;
  available_quantity: string;
  unit: string;
  unit_price: string;
  currency: string;
}

export interface MarketplaceRFQ {
  id: string;
  organization_id: string;
  organization_name: string;
  organization_country_code: string;
  title: string;
  description: string;
  category: string;
  quantity: string;
  unit: string;
  destination_country_code: string;
  target_delivery_date: string | null;
  target_unit_price: string | null;
  currency: string | null;
}

export interface CreateMarketplaceRFQInput {
  organization_id: string;
  title: string;
  description: string;
  category: string;
  quantity: string;
  unit: string;
  destination_country_code: string;
  target_delivery_date?: string | null;
  target_unit_price?: string | null;
  currency?: string | null;
}

export type ContactVisibility = "PRIVATE" | "PARTICIPANTS";

export interface OrganizationContact {
  id?: string;
  name: string;
  purpose: string;
  consent_obtained?: boolean;
  visibility: ContactVisibility;
  role_title?: string | null;
  email?: string | null;
  phone?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface OrganizationProfile {
  organization_id: string;
  capabilities: string[];
  products: string[];
  regions: string[];
  contacts: OrganizationContact[];
  verification_status: "UNVERIFIED" | string;
  version: number;
  created_at?: string | null;
  updated_at?: string | null;
  updated_by_user_id?: string | null;
}

export interface UpdateOrganizationProfileInput {
  expected_version: number;
  capabilities: string[];
  products: string[];
  regions: string[];
  contacts: OrganizationContact[];
}

export interface Deal {
  id: string;
  display_name?: string | null;
  buyer_organization_id: string;
  seller_organization_id: string;
  status: string;
  version: number;
  pending_counterparty?: boolean;
}

export interface CounterpartyInvitationInput {
  buyer_organization_id?: string;
  inviting_organization_id?: string;
  inviter_party?: "BUYER" | "SELLER";
  recipient_email: string;
  legal_name: string;
  country_code: string;
  display_name?: string;
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
  id?: string;
  description: string;
  sku: string | null;
  quantity: string;
  unit: string;
  unit_price: { amount: string; currency: string };
}

export interface ShipmentItemAllocation {
  line_item_id: string;
  quantity: string;
  unit: string;
}

export interface AgreementShipment {
  id?: string;
  quantity: string | null;
  destination: string;
  target_date: string | null;
  allocations?: ShipmentItemAllocation[];
}

export interface PaymentObligationAllocation {
  obligation_id: string;
  amount: { amount: string; currency: string };
}

export interface AgreementPaymentTerm {
  id?: string;
  amount: { amount: string; currency: string };
  trigger: string;
  due_condition: string;
  allocations?: PaymentObligationAllocation[];
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
    shipments: AgreementShipment[];
    payment_terms: AgreementPaymentTerm[];
    delivery_location: string;
    incoterm: string | null;
    cancellation_terms: string;
  };
  created_at: string;
  committed_at: string | null;
  prior_agreement_version_id?: string | null;
  prior_terms_hash?: string | null;
  amendment_rationale?: string | null;
  approvals: AgreementApproval[];
  /** Keyed by organization_id; only present for organizations with a routing policy configured. */
  routing_status?: Record<string, RoutingStatus>;
}

export interface FulfillmentObligationImpact {
  obligation_reference: string;
  item_id?: string | null;
  planned_quantity: string;
  unit: string;
  shipped_quantity: string;
  confirmed_quantity: string;
  preserved: boolean;
  status: string;
  details?: string | null;
}

export interface PaymentMilestoneImpact {
  milestone_reference: string;
  amount: string;
  currency: string;
  payment_status: string;
  has_active_intent: boolean;
  preserved: boolean;
  status: string;
  details?: string | null;
}

export interface AmendmentImpact {
  prior_version_number: number;
  prior_terms_hash: string;
  proposed_version_number: number;
  proposed_terms_hash: string;
  diff: {
    fields?: Array<{ path: string; before: unknown; after: unknown }>;
    collections?: Record<string, { added: unknown[]; removed: unknown[]; modified: unknown[] }>;
  };
  fulfillment_impact: FulfillmentObligationImpact[];
  payment_impact: PaymentMilestoneImpact[];
  active_cases: Array<Record<string, unknown>>;
  blockers: string[];
  can_commit: boolean;
}

export interface ProposeAmendmentRequest extends ReviewedProposalTerms {
  prior_version_number: number;
  prior_terms_hash: string;
  rationale?: string | null;
  replace_pending_draft?: boolean;
}

export interface WithdrawAmendmentRequest {
  terms_hash: string;
  organization_id?: string | null;
}

export type RoutingSlotStatus = "REQUIRED" | "PENDING" | "COMPLETED" | "REVOKED";
export type RoutingOutcomeStatus = "REQUIRED" | "PENDING" | "COMPLETED" | "ERROR";

export interface RoutingSlot {
  user_id: string | null;
  status: RoutingSlotStatus;
  decision: "APPROVE" | "REJECT" | null;
  stale: boolean;
}

export interface RoutingStatus {
  organization_id: string;
  mode: "SEQUENTIAL" | "PARALLEL";
  policy_version: number;
  status: RoutingOutcomeStatus;
  required_approvers: number;
  completed_approvers: number;
  /** Full per-approver detail only for a viewer who belongs to this organization. */
  slots: RoutingSlot[] | null;
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
  /** Present when this organization has a routing policy configured. */
  routing?: RoutingStatus | null;
}

export interface ApprovalRoutingPolicy {
  organization_id: string;
  mode: "SEQUENTIAL" | "PARALLEL";
  approver_user_ids: string[];
  version: number;
  updated_by_user_id?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
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

export type PaymentLifecycleState =
  | "ineligible"
  | "eligible"
  | "authorized"
  | "queued"
  | "unknown"
  | "sent"
  | "reconciled"
  | "failed"
  | "cancelled";

export interface PaymentMilestoneAllocation {
  obligation_id: string;
  amount: string;
  currency: string;
}

export interface PaymentMilestoneSummary {
  id: string;
  sequence_number: number;
  milestone_id?: string | null;
  source_terms_reference?: string | null;
  amount: string;
  currency: string;
  trigger_type: string;
  due_condition: string;
  lifecycle_state: PaymentLifecycleState;
  is_eligible: boolean;
  ineligibility_reason?: string | null;
  allocations: PaymentMilestoneAllocation[];
  active_intent_id?: string | null;
  intent_status?: PaymentIntentStatus | null;
  reconciled_amount?: string | null;
  last_checked_at?: string | null;
  last_reconciled_at?: string | null;
  invoice_url?: string | null;
  invoice_reference?: string | null;
  failure_reason?: string | null;
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
  payment_milestone_id?: string | null;
  milestone_id?: string | null;
  source_terms_reference?: string | null;
  lifecycle_state?: PaymentLifecycleState | null;
  is_eligible?: boolean | null;
}

export type FulfillmentStage = "SHIPPED" | "OBSERVED" | "CONFIRMED";

export interface FulfillmentEvent {
  id: string;
  deal_id: string;
  agreement_version_id: string;
  terms_hash: string;
  obligation_id: string;
  organization_id: string;
  user_id: string;
  event_type: FulfillmentStage;
  quantity: string;
  unit: string;
  carrier: string | null;
  tracking_number: string | null;
  dispatch_date: string | null;
  expected_delivery_date: string | null;
  source_type: "USER_ATTESTATION";
  recorded_at: string;
  version: number;
}

export interface FulfillmentSnapshot {
  deal_id: string;
  state: "PENDING" | "EMPTY" | "STALE" | "READY";
  agreement_version_id: string | null;
  agreement_version_number: number | null;
  terms_hash: string | null;
  obligation_id: string | null;
  obligation_reference?: string | null;
  planned_quantity: string | null;
  unit: string | null;
  destination: string | null;
  target_date: string | null;
  shipped_quantity: string;
  observed_quantity: string;
  confirmed_quantity: string;
  fulfillment_version: number;
  payment_complete: boolean;
  deal_completed: boolean;
  events: FulfillmentEvent[];
}

interface RecordFulfillmentInputBase {
  agreement_version_id: string;
  terms_hash: string;
  obligation_id: string;
  organization_id: string;
  quantity: string;
  expected_version: number;
  idempotency_key: string;
}

export type RecordFulfillmentInput =
  | (RecordFulfillmentInputBase & {
      event_type: "SHIPPED";
      carrier: string;
      tracking_number?: string | null;
      dispatch_date: string;
      expected_delivery_date?: string | null;
    })
  | (RecordFulfillmentInputBase & {
      event_type: "OBSERVED" | "CONFIRMED";
    });

export interface PaymentAuthorization {
  id: string;
  status: string;
  already_existed: boolean;
  provider?: string;
  execution_mode?: PaymentMode | "LEGACY_UNRESOLVED";
  payment_milestone_id?: string | null;
  milestone_id?: string | null;
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
export interface ReviewedProposalTerms {
  schema_version: number;
  description?: string;
  quantity?: string;
  unit?: string;
  unit_price?: string;
  currency?: "USD" | string;
  delivery_destination?: string;
  delivery_date?: string | null;
  payment_trigger?: PaymentTrigger;
  organization_id?: string;
  line_items?: AgreementLineItem[];
  shipments?: AgreementShipment[];
  payment_terms?: AgreementPaymentTerm[];
  delivery_location?: string;
  incoterm?: string | null;
  cancellation_terms?: string;
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
  display_name?: string;
  initiator_party?: "BUYER" | "SELLER";
  opening_request?: string | null;
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

export interface RegisterOrganizationInput extends CreateOrganizationInput {
  email: string;
  display_name: string;
  password: string;
}

export interface OrganizationMember {
  user_id: string;
  email: string;
  display_name?: string | null;
  role: "ADMIN" | "MEMBER" | string;
  status: "ACTIVE" | "INACTIVE" | "REVOKED" | string;
  capabilities: OrganizationCapability[];
  assigned_capabilities?: OrganizationCapability[];
  version: number;
}

export interface UpdateMemberPermissionsInput {
  expected_version: number;
  role?: "ADMIN" | "MEMBER" | string;
  capabilities?: OrganizationCapability[];
}

export type CaseType = "CANCELLATION" | "DISPUTE";
export type CaseStatus = "OPEN" | "UNDER_REVIEW" | "RESOLVED" | "REJECTED" | "WITHDRAWN";
export type EvidenceVisibility = "PRIVATE_OPERATOR" | "COUNTERPARTY_RESTRICTED" | "MUTUAL_VISIBLE";
export type BilateralDecision = "CONSENT" | "REJECT" | "WITHDRAW";

export interface DealCaseEvidence {
  evidence_id: string;
  case_id: string;
  submitted_by_user_id: string;
  submitted_by_organization_id: string;
  visibility: EvidenceVisibility;
  notes: string;
  submitted_at: string;
  metadata?: Record<string, unknown>;
}

export interface DealCase {
  id: string;
  deal_id: string;
  agreement_version_id: string;
  agreement_terms_hash: string;
  case_type: CaseType;
  reason: string;
  obligation_references: string[];
  requested_by_user_id: string;
  requested_by_organization_id: string;
  created_at: string;
  status: CaseStatus;
  resolution?: string | null;
  resolved_by_user_id?: string | null;
  resolved_at?: string | null;
  evidence_visibility: EvidenceVisibility;
  evidence_items: DealCaseEvidence[];
  bilateral_consent_counterparty_id?: string | null;
  bilateral_consent_at?: string | null;
  operational_impact_blockers: string[];
  version: number;
}

export interface RaiseCaseInput {
  case_type: CaseType;
  reason: string;
  agreement_version_id: string;
  agreement_terms_hash: string;
  case_id?: string;
  obligation_references?: string[];
  evidence_visibility?: EvidenceVisibility;
  evidence_notes?: string | null;
  delivery_exception?: {
    kind: "DELIVERY_EXCEPTION";
    exception_type: "SHORTAGE" | "DAMAGE" | "OTHER";
    affected_quantity?: string | null;
    unit: string;
    fulfillment_event_id: string;
  };
  acting_organization_id?: string | null;
}

export interface RespondCaseInput {
  decision: BilateralDecision;
  rationale: string;
  acting_organization_id?: string | null;
}

export interface AddCaseEvidenceInput {
  notes: string;
  visibility: EvidenceVisibility;
  metadata?: Record<string, unknown>;
  acting_organization_id?: string | null;
}

export type ReminderScope = "FULFILLMENT" | "MILESTONE" | "CASE" | "ROUTING";

export type ReminderStatus =
  | "SCHEDULED"
  | "PENDING"
  | "DELIVERED"
  | "SUPPRESSED"
  | "FAILED";

export type ReminderChannel = "IN_APP";

export type SuppressionReason =
  | "RESOLVED"
  | "SUPERSEDED"
  | "ORGANIZATION_SWITCHED"
  | "RECIPIENT_REVOKED"
  | "DEAL_TERMINAL"
  | "RECURRENCE_EXHAUSTED";

export interface DealReminder {
  id: string;
  deal_id: string;
  scope: ReminderScope;
  reference_id: string;
  recipient_organization_id: string;
  recipient_user_id?: string | null;
  status: ReminderStatus;
  scheduled_for: string;
  due_at: string;
  recurrence_cap: number;
  recurrence_count: number;
  deduplication_key: string;
  channel: ReminderChannel;
  suppression_reason?: SuppressionReason | string | null;
  delivered_at?: string | null;
  suppressed_at?: string | null;
  error_detail?: string | null;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface NormalizedTradeRequirements {
  category?: string | null;
  item_description?: string | null;
  quantity?: string | null;
  unit?: string | null;
  target_unit_price?: string | null;
  budget?: string | null;
  currency?: string | null;
  destination_country_code?: string | null;
  destination_name?: string | null;
  delivery_destination?: string | null;
  target_delivery_date?: string | null;
  delivery_date?: string | null;
  capabilities_required?: string[];
  payment_terms?: string | null;
  raw_text: string;
}

export interface SuggestedSeller {
  id: string;
  organization_id?: string;
  legal_name: string;
  country_code: string;
  match_score?: number;
  match_reasons?: string[];
  capabilities?: string[];
  products?: string[];
  regions?: string[];
  matched_products?: string[];
  matched_capabilities?: string[];
  matched_listing_ids?: string[];
}

export interface OpeningRequestAnalysisResult {
  requirements: NormalizedTradeRequirements;
  suggested_sellers: SuggestedSeller[];
  provenance?: AIProvenance;
}
