import { getAccessToken } from "./tokenStore";
import type {
  CreateDealInput,
  CounterpartyInvitationInput,
  Invitation,
  InvitationAcceptance,
  InvitationAcceptanceInput,
  CreateMessageInput,
  CreateOrganizationInput,
  RegisterOrganizationInput,
  CurrentUser,
  AgreementApproval,
  AgreementHistory,
  AgreementComparison,
  AgreementVersion,
  AmendmentImpact,
  ApprovalRoutingPolicy,
  ProposeAmendmentRequest,
  CommercialDocumentDraft,
  CreateDealFactInput,
  Deal,
  DealFact,
  DealMessage,
  DealSummary,
  FactCorrectionResult,
  FactSuggestionResult,
  FactReviewAction,
  FulfillmentSnapshot,
  FulfillmentEvent,
  MessageExistence,
  NegotiationAction,
  NegotiationInput,
  NegotiationResult,
  NegotiationView,
  Organization,
  OrganizationDirectoryItem,
  OrganizationDirectorySearch,
  MarketplaceListing,
  CreateMarketplaceListingInput,
  MarketplaceRFQ,
  CreateMarketplaceRFQInput,
  OrganizationMember,
  OrganizationProfile,
  PlatformOrganization,
  PlatformUser,
  PlatformOrganizationMember,
  AssignableDeal,
  PaymentAuthorization,
  PaymentMode,
  PaymentMilestoneSummary,
  PaymentPreview,
  PaymentStatus,
  RecordFulfillmentInput,
  ProposalSuggestion,
  UpdateMemberPermissionsInput,
  UpdateOrganizationProfileInput,
  ReviewedProposalTerms,
  TokenResponse,
  ThreadImportInput,
  ThreadImportPreview,
  ThreadPreviewInput,
  Visibility,
  DealCase,
  DealCaseEvidence,
  DealReminder,
  RaiseCaseInput,
  RespondCaseInput,
  AddCaseEvidenceInput,
  OpeningRequestAnalysisResult,
  MarketplaceListingDetail,
  InquiryDraft,
  InterpretSourcingRequest,
  InterpretSourcingResponse,
  CompareSourcingRequest,
  CompareSourcingResponse,
  GapAnalysisSourcingRequest,
  GapAnalysisSourcingResponse,
  DraftInquirySourcingRequest,
  EvaluateSourcingRequest,
  EvaluateSourcingResponse,
} from "./types";

export type {
  NormalizedTradeRequirements,
  SuggestedSeller,
  OpeningRequestAnalysisResult,
  BuyerRequirements,
  MarketplaceListingDetail,
  ComparisonResult,
  CommercialGap,
  InquiryDraft,
  InterpretSourcingRequest,
  InterpretSourcingResponse,
  CompareSourcingRequest,
  CompareSourcingResponse,
  GapAnalysisSourcingRequest,
  GapAnalysisSourcingResponse,
  DraftInquirySourcingRequest,
  EvaluateSourcingRequest,
  EvaluateSourcingResponse,
} from "./types";

const DEFAULT_ERROR_MESSAGE = "Something went wrong. Please try again.";

/**
 * Default upper bound for API calls.
 */
export const API_REQUEST_TIMEOUT_MS = 30_000;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isAbortError(error: unknown): boolean {
  // Name check instead of `instanceof DOMException` so errors from another realm still match.
  return isRecord(error) && error["name"] === "AbortError";
}

function describeDetail(detail: unknown): string | null {
  if (typeof detail === "string" && detail.trim() !== "") {
    return detail;
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (isRecord(item) && typeof item["msg"] === "string" ? item["msg"] : null))
      .filter((message): message is string => message !== null);
    if (messages.length > 0) {
      return messages.join("; ");
    }
    return null;
  }
  if (isRecord(detail) && typeof detail["msg"] === "string") {
    return detail["msg"];
  }
  return null;
}

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, detail: unknown, fallback: string = DEFAULT_ERROR_MESSAGE) {
    super(describeDetail(detail) ?? fallback);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function apiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL;
  return configured ? configured.replace(/\/+$/, "") : "";
}

async function readErrorDetail(response: Response): Promise<unknown> {
  try {
    const body: unknown = await response.json();
    if (isRecord(body) && "detail" in body) {
      return body["detail"];
    }
    return null;
  } catch {
    return null;
  }
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  responseType: "json" | "blob" = "json",
  authRequired = true,
  timeoutMs = API_REQUEST_TIMEOUT_MS,
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", responseType === "blob" ? "application/zip, text/html" : "application/json");
  if (init.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  const token = getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  // Compose the caller's signal with a deadline so a stalled connection cannot
  // hang the UI forever. The caller's abort reason is preserved for identity.
  const callerSignal = init.signal;
  const controller = new AbortController();
  const forwardAbort = () => controller.abort(callerSignal?.reason);
  if (callerSignal?.aborted) {
    controller.abort(callerSignal.reason);
  }
  callerSignal?.addEventListener("abort", forwardAbort, { once: true });
  let timedOut = false;
  const deadline = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);

  try {
    const response = await fetch(`${apiBaseUrl()}${path}`, {
      ...init,
      headers,
      signal: controller.signal,
    });
    if (!response.ok) {
      const detail = await readErrorDetail(response);
      if (response.status === 401 && authRequired && token && token === getAccessToken() && typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("syncally:session-expired", { detail: { token } }));
      }
      throw new ApiError(response.status, detail);
    }
    if (response.status === 204) {
      return undefined as T;
    }
    return (await (responseType === "blob" ? response.blob() : response.json())) as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    // Caller cancellation wins over the deadline if both landed together.
    if (timedOut && !callerSignal?.aborted) {
      throw new ApiError(0, null, "The SyncAlly API took too long to respond. Please try again.");
    }
    // Caller-initiated cancellation is not an outage: keep the abort error intact so
    // callers can distinguish it (name === "AbortError" or their own signal state).
    if (callerSignal?.aborted || isAbortError(error)) {
      throw error;
    }
    throw new ApiError(0, null, "Unable to reach the SyncAlly API. Check that it is running.");
  } finally {
    clearTimeout(deadline);
    callerSignal?.removeEventListener("abort", forwardAbort);
  }
}

export function login(email: string, password: string): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  }, "json", false);
}

export function registerOrganization(input: RegisterOrganizationInput): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/auth/register-organization", {
    method: "POST",
    body: JSON.stringify(input),
  }, "json", false);
}

export function getCurrentUser(): Promise<CurrentUser> {
  return apiRequest<CurrentUser>("/auth/me");
}

export function listPlatformOrganizations(): Promise<PlatformOrganization[]> {
  return apiRequest<PlatformOrganization[]>("/platform/organizations");
}

export function updatePlatformOrganizationStatus(
  organizationId: string,
  status: "ACTIVE" | "SUSPENDED",
): Promise<PlatformOrganization> {
  return apiRequest<PlatformOrganization>(
    `/platform/organizations/${encodeURIComponent(organizationId)}`,
    { method: "PATCH", body: JSON.stringify({ status }) },
  );
}

export function listPlatformOrganizationMembers(organizationId: string): Promise<PlatformOrganizationMember[]> {
  return apiRequest<PlatformOrganizationMember[]>(`/platform/organizations/${encodeURIComponent(organizationId)}/members`);
}

export function setPlatformOrganizationOwner(organizationId: string, userId: string, reason: string): Promise<{ organization_id: string; owner_user_id: string; status: string }> {
  return apiRequest(`/platform/organizations/${encodeURIComponent(organizationId)}/owner`, {
    method: "PUT",
    body: JSON.stringify({ user_id: userId, reason }),
  });
}

export function listPlatformUsers(): Promise<PlatformUser[]> {
  return apiRequest<PlatformUser[]>("/platform/users");
}

export function updatePlatformUserStatus(
  userId: string,
  status: "ACTIVE" | "LOCKED",
  reason?: string,
): Promise<PlatformUser> {
  return apiRequest<PlatformUser>(
    `/platform/users/${encodeURIComponent(userId)}`,
    { method: "PATCH", body: JSON.stringify({ status, reason }) },
  );
}

export function listOrganizations(): Promise<Organization[]> {
  return apiRequest<Organization[]>("/organizations");
}

export function getOrganization(organizationId: string, options?: { signal?: AbortSignal }): Promise<OrganizationDirectoryItem> {
  return apiRequest<OrganizationDirectoryItem>(`/organizations/${encodeURIComponent(organizationId)}`, { signal: options?.signal });
}

export function searchOrganizationDirectory(
  filters: OrganizationDirectorySearch = {},
  options?: { signal?: AbortSignal },
): Promise<OrganizationDirectoryItem[]> {
  const params = new URLSearchParams({ limit: "100" });
  for (const [key, value] of Object.entries(filters)) {
    if (value?.trim()) params.set(key, value.trim());
  }
  return apiRequest<OrganizationDirectoryItem[]>(`/organizations/directory?${params.toString()}`, { signal: options?.signal });
}

export function searchMarketplaceListings(
  filters: { q?: string; country_code?: string; category?: string } = {},
  options?: { signal?: AbortSignal },
): Promise<MarketplaceListing[]> {
  const params = new URLSearchParams({ limit: "100" });
  for (const [key, value] of Object.entries(filters)) {
    if (value?.trim()) params.set(key, value.trim());
  }
  return apiRequest<MarketplaceListing[]>(`/marketplace/listings?${params.toString()}`, { signal: options?.signal });
}

export function createMarketplaceListing(input: CreateMarketplaceListingInput): Promise<MarketplaceListing> {
  return apiRequest<MarketplaceListing>("/marketplace/listings", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getMarketplaceListing(listingId: string): Promise<MarketplaceListing> {
  return apiRequest<MarketplaceListing>(`/marketplace/listings/${encodeURIComponent(listingId)}`);
}

export function deactivateMarketplaceListing(listingId: string): Promise<{ status: string }> {
  return apiRequest<{ status: string }>(`/marketplace/listings/${encodeURIComponent(listingId)}`, {
    method: "DELETE",
  });
}

export function searchMarketplaceRFQs(
  filters: { q?: string; destination_country_code?: string; category?: string } = {},
  options?: { signal?: AbortSignal },
): Promise<MarketplaceRFQ[]> {
  const params = new URLSearchParams({ limit: "100" });
  for (const [key, value] of Object.entries(filters)) {
    if (value?.trim()) params.set(key, value.trim());
  }
  return apiRequest<MarketplaceRFQ[]>(`/marketplace/rfqs?${params.toString()}`, { signal: options?.signal });
}

export function createMarketplaceRFQ(input: CreateMarketplaceRFQInput): Promise<MarketplaceRFQ> {
  return apiRequest<MarketplaceRFQ>("/marketplace/rfqs", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getMarketplaceRFQ(rfqId: string): Promise<MarketplaceRFQ> {
  return apiRequest<MarketplaceRFQ>(`/marketplace/rfqs/${encodeURIComponent(rfqId)}`);
}

export function closeMarketplaceRFQ(rfqId: string): Promise<{ status: string }> {
  return apiRequest<{ status: string }>(`/marketplace/rfqs/${encodeURIComponent(rfqId)}`, {
    method: "DELETE",
  });
}

export function getOrganizationProfile(organizationId: string): Promise<OrganizationProfile> {
  return apiRequest<OrganizationProfile>(`/organizations/${encodeURIComponent(organizationId)}/profile`);
}

export function updateOrganizationProfile(
  organizationId: string,
  input: UpdateOrganizationProfileInput,
): Promise<OrganizationProfile> {
  return apiRequest<OrganizationProfile>(`/organizations/${encodeURIComponent(organizationId)}/profile`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export function createOrganization(input: CreateOrganizationInput): Promise<Organization> {
  return apiRequest<Organization>("/organizations", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function addOrganizationMember(
  organizationId: string,
  email: string,
  grants: { role_bundles: string[]; permissions: string[]; deal_ids: string[] } = { role_bundles: [], permissions: [], deal_ids: [] },
): Promise<OrganizationMember> {
  return apiRequest<OrganizationMember>(
    `/organizations/${encodeURIComponent(organizationId)}/members`,
    {
      method: "POST",
      body: JSON.stringify({ email, ...grants }),
    },
  );
}

export function listAssignableOrganizationDeals(organizationId: string): Promise<AssignableDeal[]> {
  return apiRequest<AssignableDeal[]>(`/organizations/${encodeURIComponent(organizationId)}/assignable-deals`);
}

export function listOrganizationMembers(
  organizationId: string,
  options?: { signal?: AbortSignal },
): Promise<OrganizationMember[]> {
  return apiRequest<OrganizationMember[]>(
    `/organizations/${encodeURIComponent(organizationId)}/members`,
    { signal: options?.signal },
  );
}

export function updateMemberPermissions(
  organizationId: string,
  userId: string,
  payload: UpdateMemberPermissionsInput,
): Promise<OrganizationMember> {
  return apiRequest<OrganizationMember>(
    `/organizations/${encodeURIComponent(organizationId)}/members/${encodeURIComponent(userId)}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );
}

export function updateMemberDealAssignments(
  organizationId: string,
  userId: string,
  payload: { expected_version: number; deal_ids: string[] },
): Promise<{ organization_id: string; user_id: string; deal_ids: string[]; version: number }> {
  return apiRequest(
    `/organizations/${encodeURIComponent(organizationId)}/members/${encodeURIComponent(userId)}/deal-assignments`,
    { method: "PUT", body: JSON.stringify(payload) },
  );
}

export function revokeOrganizationMember(
  organizationId: string,
  userId: string,
): Promise<void> {
  return apiRequest<void>(
    `/organizations/${encodeURIComponent(organizationId)}/members/${encodeURIComponent(userId)}`,
    {
      method: "DELETE",
    },
  );
}

export function getApprovalRoutingPolicy(
  organizationId: string,
): Promise<ApprovalRoutingPolicy | null> {
  return apiRequest<ApprovalRoutingPolicy | null>(
    `/organizations/${encodeURIComponent(organizationId)}/approval-routing`,
  );
}

export function putApprovalRoutingPolicy(
  organizationId: string,
  input: { mode: "SEQUENTIAL" | "PARALLEL"; approver_user_ids: string[]; expected_version: number | null },
): Promise<ApprovalRoutingPolicy> {
  return apiRequest<ApprovalRoutingPolicy>(
    `/organizations/${encodeURIComponent(organizationId)}/approval-routing`,
    { method: "PUT", body: JSON.stringify(input) },
  );
}

export function deleteApprovalRoutingPolicy(
  organizationId: string,
  expectedVersion: number,
): Promise<void> {
  return apiRequest<void>(
    `/organizations/${encodeURIComponent(organizationId)}/approval-routing?expected_version=${expectedVersion}`,
    { method: "DELETE" },
  );
}

export function listDeals(organizationId?: string): Promise<DealSummary[]> {
  const party = organizationId ? `?organization_id=${encodeURIComponent(organizationId)}` : "";
  return apiRequest<DealSummary[]>(`/deals${party}`);
}

export function createDeal(input: CreateDealInput): Promise<Deal> {
  return apiRequest<Deal>("/deals", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function createCounterpartyInvitation(input: CounterpartyInvitationInput): Promise<Invitation> {
  return apiRequest<Invitation>("/deals/counterparty-invitations", {
    method: "POST", body: JSON.stringify(input),
  });
}

export function cancelOrganizationInvitation(organizationId: string, invitationId: string): Promise<void> {
  return apiRequest<void>(
    `/organizations/${encodeURIComponent(organizationId)}/invitations/${encodeURIComponent(invitationId)}`,
    { method: "DELETE" },
  );
}

export function acceptInvitation(input: InvitationAcceptanceInput): Promise<InvitationAcceptance> {
  return apiRequest<InvitationAcceptance>("/invitations/accept", {
    method: "POST", body: JSON.stringify(input),
  }, "json", false);
}

export function getDeal(dealId: string, organizationId?: string): Promise<Deal> {
  const party = organizationId ? `?organization_id=${encodeURIComponent(organizationId)}` : "";
  return apiRequest<Deal>(`/deals/${encodeURIComponent(dealId)}${party}`);
}

export function getCurrentAgreement(dealId: string, options?: { organizationId?: string; signal?: AbortSignal }): Promise<AgreementVersion> {
  const party = options?.organizationId ? `?organization_id=${encodeURIComponent(options.organizationId)}` : "";
  return apiRequest<AgreementVersion>(
    `/deals/${encodeURIComponent(dealId)}/agreements/current${party}`, { signal: options?.signal },
  );
}

export function getAgreementHistory(dealId: string, organizationId: string, signal?: AbortSignal): Promise<AgreementHistory> {
  return apiRequest<AgreementHistory>(`/deals/${encodeURIComponent(dealId)}/agreements/history?organization_id=${encodeURIComponent(organizationId)}`, { signal });
}

export function getAgreementVersion(dealId: string, number: number, organizationId: string, signal?: AbortSignal): Promise<AgreementVersion> {
  return apiRequest<AgreementVersion>(`/deals/${encodeURIComponent(dealId)}/agreements/versions/${number}?organization_id=${encodeURIComponent(organizationId)}`, { signal });
}

export function compareAgreementVersions(dealId: string, before: number, after: number, organizationId: string, signal?: AbortSignal): Promise<AgreementComparison> {
  const params = new URLSearchParams({ before: String(before), after: String(after), organization_id: organizationId });
  return apiRequest<AgreementComparison>(`/deals/${encodeURIComponent(dealId)}/agreements/compare?${params}`, { signal });
}

export function listPaymentStatuses(
  dealId: string,
  options?: { organizationId?: string; signal?: AbortSignal },
): Promise<PaymentStatus[]> {
  const party = options?.organizationId ? `?organization_id=${encodeURIComponent(options.organizationId)}` : "";
  return apiRequest<PaymentStatus[]>(`/deals/${encodeURIComponent(dealId)}/payments${party}`, {
    signal: options?.signal,
  });
}

export function listDealPaymentMilestones(
  dealId: string,
  options?: { organizationId?: string; signal?: AbortSignal },
): Promise<PaymentMilestoneSummary[]> {
  const party = options?.organizationId ? `?organization_id=${encodeURIComponent(options.organizationId)}` : "";
  return apiRequest<PaymentMilestoneSummary[]>(
    `/deals/${encodeURIComponent(dealId)}/payments/milestones${party}`,
    { signal: options?.signal },
  );
}

export function authorizeDealPayment(
  dealId: string,
  idempotencyKey: string,
  expectedMode?: PaymentMode,
  options?: {
    organizationId?: string;
    paymentMilestoneId?: string;
    milestoneId?: string;
  },
): Promise<PaymentAuthorization> {
  const body: Record<string, unknown> = {
    idempotency_key: idempotencyKey,
  };
  if (expectedMode) body.expected_mode = expectedMode;
  const party = options?.organizationId ? `?organization_id=${encodeURIComponent(options.organizationId)}` : "";
  if (options?.paymentMilestoneId) body.payment_milestone_id = options.paymentMilestoneId;
  if (options?.milestoneId) body.milestone_id = options.milestoneId;

  return apiRequest<PaymentAuthorization>(`/deals/${encodeURIComponent(dealId)}/payments${party}`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function previewDealPayment(dealId: string, organizationId?: string, signal?: AbortSignal): Promise<PaymentPreview> {
  const party = organizationId ? `?organization_id=${encodeURIComponent(organizationId)}` : "";
  return apiRequest<PaymentPreview>(`/deals/${encodeURIComponent(dealId)}/payments/preview${party}`, { signal });
}

export function getDealFulfillment(dealId: string, organizationId: string, signal?: AbortSignal): Promise<FulfillmentSnapshot> {
  const party = `?organization_id=${encodeURIComponent(organizationId)}`;
  return apiRequest<FulfillmentSnapshot>(`/deals/${encodeURIComponent(dealId)}/fulfillment${party}`, { signal });
}

export function recordDealFulfillment(
  dealId: string,
  input: RecordFulfillmentInput,
): Promise<FulfillmentEvent> {
  const endpoint = input.event_type === "SHIPPED" ? "shipments" : "events";
  return apiRequest<FulfillmentEvent>(`/deals/${encodeURIComponent(dealId)}/fulfillment/${endpoint}`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getCommercialDocumentDraft(dealId: string, organizationId?: string): Promise<CommercialDocumentDraft> {
  const party = organizationId ? `?organization_id=${encodeURIComponent(organizationId)}` : "";
  return apiRequest<CommercialDocumentDraft>(
    `/deals/${encodeURIComponent(dealId)}/documents/commercial-draft${party}`,
  );
}

export type TradePackFormat = "html" | "zip";

export function getTradePack(
  dealId: string, agreement: Pick<AgreementVersion, "id" | "version_number" | "terms_hash">,
  organizationId: string, format: TradePackFormat, signal?: AbortSignal,
): Promise<Blob> {
  if (!agreement.id || !organizationId) return Promise.reject(new ApiError(409, "An exact saved version and organization are required"));
  const params = new URLSearchParams({ agreement_version_id: agreement.id,
    terms_hash: agreement.terms_hash, organization_id: organizationId, format });
  return apiRequest<Blob>(`/deals/${encodeURIComponent(dealId)}/documents/versions/${agreement.version_number}/trade-pack?${params}`, { signal }, "blob");
}

export function recordAgreementDecision(
  dealId: string,
  versionNumber: number,
  termsHash: string,
  decision: "approve" | "reject",
  organizationId?: string,
): Promise<AgreementApproval> {
  return apiRequest<AgreementApproval>(
    `/deals/${encodeURIComponent(dealId)}/agreements/${versionNumber}/${decision}`,
    {
      method: "POST",
      body: JSON.stringify({
        terms_hash: termsHash,
        ...(organizationId ? { organization_id: organizationId } : {}),
      }),
    },
  );
}

export function commitAgreementVersion(
  dealId: string,
  versionNumber: number,
  termsHash: string,
  organizationId?: string,
): Promise<AgreementVersion> {
  return apiRequest<AgreementVersion>(
    `/deals/${encodeURIComponent(dealId)}/agreements/${versionNumber}/commit`,
    { method: "POST", body: JSON.stringify({ terms_hash: termsHash, ...(organizationId ? { organization_id: organizationId } : {}) }) },
  );
}

export function createAgreementFromReviewedTerms(
  dealId: string,
  organizationId: string,
  terms: ReviewedProposalTerms,
): Promise<AgreementVersion> {
  return apiRequest<AgreementVersion>(
    `/deals/${encodeURIComponent(dealId)}/agreements/from-reviewed-terms`,
    {
      method: "POST",
      body: JSON.stringify({
        ...terms,
        organization_id: organizationId,
      }),
    },
  );
}

export function proposeAmendment(
  dealId: string,
  input: ProposeAmendmentRequest,
): Promise<AgreementVersion> {
  return apiRequest<AgreementVersion>(
    `/deals/${encodeURIComponent(dealId)}/agreements/amendments/propose`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}
export function getAmendmentImpact(
  dealId: string,
  options?: { versionNumber?: number; organizationId?: string; signal?: AbortSignal },
): Promise<AmendmentImpact> {
  const query = new URLSearchParams();
  if (options?.versionNumber) query.set("version_number", String(options.versionNumber));
  if (options?.organizationId) query.set("organization_id", options.organizationId);
  const suffix = query.size ? `?${query.toString()}` : "";
  return apiRequest<AmendmentImpact>(
    `/deals/${encodeURIComponent(dealId)}/agreements/amendments/impact${suffix}`,
    { signal: options?.signal },
  );
}

export function previewAmendmentImpact(
  dealId: string,
  input: ReviewedProposalTerms,
  signal?: AbortSignal,
): Promise<AmendmentImpact> {
  return apiRequest<AmendmentImpact>(
    `/deals/${encodeURIComponent(dealId)}/agreements/amendments/preview-impact`,
    {
      method: "POST",
      body: JSON.stringify(input),
      signal,
    },
  );
}

export function withdrawAmendment(
  dealId: string,
  versionNumber: number,
  termsHash: string,
  organizationId?: string,
): Promise<AgreementVersion> {
  return apiRequest<AgreementVersion>(
    `/deals/${encodeURIComponent(dealId)}/agreements/amendments/${versionNumber}/withdraw`,
    {
      method: "POST",
      body: JSON.stringify({
        terms_hash: termsHash,
        ...(organizationId ? { organization_id: organizationId } : {}),
      }),
    },
  );
}

export function getNegotiation(
  dealId: string,
  organizationId: string,
  options?: { signal?: AbortSignal; offset?: number },
): Promise<NegotiationView> {
  const query = new URLSearchParams({ organization_id: organizationId });
  if (options?.offset !== undefined) query.set("offset", String(options.offset));
  return apiRequest<NegotiationView>(`/deals/${encodeURIComponent(dealId)}/negotiation?${query}`, { signal: options?.signal });
}

export function negotiateDeal(
  dealId: string,
  action: NegotiationAction,
  input: NegotiationInput,
  options?: { signal?: AbortSignal },
): Promise<NegotiationResult> {
  return apiRequest<NegotiationResult>(`/deals/${encodeURIComponent(dealId)}/negotiation/${action}`, {
    method: "POST", body: JSON.stringify(input), signal: options?.signal,
  });
}

export function createDealMessage(
  dealId: string,
  input: CreateMessageInput,
  options?: { signal?: AbortSignal },
): Promise<DealMessage> {
  // source_type is forwarded as supplied. The server currently derives it from the
  // verified actor and ignores this field, so it has no effect until the endpoint
  // accepts it.
  const { body, visibility, idempotency_key, source_type, source_reference, organization_id } =
    input;
  return apiRequest<DealMessage>(`/deals/${encodeURIComponent(dealId)}/messages`, {
    method: "POST",
    body: JSON.stringify({
      body,
      visibility,
      idempotency_key,
      source_type,
      source_reference,
      organization_id,
    }),
    signal: options?.signal,
  });
}

export function previewDealThreadImport(
  dealId: string,
  input: ThreadPreviewInput,
  options?: { signal?: AbortSignal },
): Promise<ThreadImportPreview> {
  return apiRequest<ThreadImportPreview>(`/deals/${encodeURIComponent(dealId)}/messages/import/preview`, {
    method: "POST",
    body: JSON.stringify({ text: input.text, organization_id: input.organization_id }),
    signal: options?.signal,
  });
}

export function importDealThread(
  dealId: string,
  input: ThreadImportInput,
  options?: { signal?: AbortSignal },
): Promise<DealMessage> {
  return apiRequest<DealMessage>(`/deals/${encodeURIComponent(dealId)}/messages/import`, {
    method: "POST",
    body: JSON.stringify({
      text: input.text, organization_id: input.organization_id, digest: input.digest,
      confirmed: input.confirmed, visibility: input.visibility ?? "PRIVATE",
      shareable_confirmed: input.shareable_confirmed ?? false,
    }),
    signal: options?.signal,
  });
}

export function listDealMessages(
  dealId: string,
  organizationId: string,
): Promise<DealMessage[]> {
  const query = new URLSearchParams({ organization_id: organizationId });
  return apiRequest<DealMessage[]>(
    `/deals/${encodeURIComponent(dealId)}/messages?${query.toString()}`,
  );
}

/**
 * Report whether any message exists anywhere in the deal, including messages
 * private to the counterparty organization. Only a boolean is exposed.
 */
export async function getDealMessageExistence(dealId: string): Promise<boolean> {
  const payload = await apiRequest<MessageExistence>(
    `/deals/${encodeURIComponent(dealId)}/messages/existence`,
  );
  if (!isRecord(payload) || typeof payload["has_messages"] !== "boolean") {
    throw new Error("The server returned an unexpected onboarding status.");
  }
  return payload["has_messages"];
}

export async function listDealFacts(
  dealId: string,
  organizationId: string,
  options?: { limit?: number; offset?: number; signal?: AbortSignal },
): Promise<DealFact[]> {
  if (options?.limit !== undefined || options?.offset !== undefined) {
    const query = new URLSearchParams({ organization_id: organizationId });
    if (options.limit !== undefined) query.set("limit", String(options.limit));
    if (options.offset !== undefined) query.set("offset", String(options.offset));
    return apiRequest<DealFact[]>(`/deals/${encodeURIComponent(dealId)}/facts?${query.toString()}`, {
      signal: options.signal,
    });
  }

  const PAGE_SIZE = 100;
  const MAX_PAGES = 100;
  const allFacts: DealFact[] = [];
  let offset = 0;
  for (let pageIdx = 0; pageIdx < MAX_PAGES; pageIdx += 1) {
    const query = new URLSearchParams({
      organization_id: organizationId,
      limit: String(PAGE_SIZE),
      offset: String(offset),
    });
    const page = await apiRequest<DealFact[]>(
      `/deals/${encodeURIComponent(dealId)}/facts?${query.toString()}`,
      { signal: options?.signal },
    );
    allFacts.push(...page);
    if (page.length < PAGE_SIZE) {
      break;
    }
    offset += page.length;
  }
  return allFacts;
}

export function createDealFact(dealId: string, input: CreateDealFactInput): Promise<DealFact> {
  return apiRequest<DealFact>(`/deals/${encodeURIComponent(dealId)}/facts`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function reviewDealFact(
  dealId: string,
  factId: string,
  action: FactReviewAction,
): Promise<DealFact> {
  return apiRequest<DealFact>(
    `/deals/${encodeURIComponent(dealId)}/facts/${encodeURIComponent(factId)}/${action}`,
    { method: "POST" },
  );
}

export function suggestDealFacts(
  dealId: string,
  organizationId: string,
): Promise<FactSuggestionResult> {
  return apiRequest<FactSuggestionResult>(`/deals/${encodeURIComponent(dealId)}/ai/facts`, {
    method: "POST",
    body: JSON.stringify({ organization_id: organizationId }),
  }, "json", true, 60_000);
}

export function draftDealProposal(
  dealId: string,
  organizationId: string,
): Promise<ProposalSuggestion> {
  return apiRequest<ProposalSuggestion>(`/deals/${encodeURIComponent(dealId)}/ai/proposal`, {
    method: "POST",
    body: JSON.stringify({ organization_id: organizationId }),
  }, "json", true, 60_000);
}

export function correctDealFact(
  dealId: string,
  factId: string,
  input: {
    expected_version: number;
    field: string;
    typed_value: string;
    currency_or_unit: string | null;
  },
): Promise<FactCorrectionResult> {
  return apiRequest<FactCorrectionResult>(
    `/deals/${encodeURIComponent(dealId)}/facts/${encodeURIComponent(factId)}`,
    { method: "PATCH", body: JSON.stringify(input) },
  );
}

export function updateFactVisibility(
  dealId: string,
  factId: string,
  visibility: Visibility,
): Promise<DealFact> {
  return apiRequest<DealFact>(
    `/deals/${encodeURIComponent(dealId)}/facts/${encodeURIComponent(factId)}/visibility`,
    {
      method: "PATCH",
      body: JSON.stringify({ visibility }),
    },
  );
}

export function listDealCases(
  dealId: string,
  organizationId?: string,
  options?: { signal?: AbortSignal },
): Promise<DealCase[]> {
  const query = organizationId ? `?organization_id=${encodeURIComponent(organizationId)}` : "";
  return apiRequest<DealCase[]>(`/deals/${encodeURIComponent(dealId)}/cases${query}`, {
    signal: options?.signal,
  });
}

export function raiseDealCase(
  dealId: string,
  input: RaiseCaseInput,
): Promise<DealCase> {
  return apiRequest<DealCase>(`/deals/${encodeURIComponent(dealId)}/cases`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function respondToDealCase(
  dealId: string,
  caseId: string,
  input: RespondCaseInput,
): Promise<DealCase> {
  return apiRequest<DealCase>(
    `/deals/${encodeURIComponent(dealId)}/cases/${encodeURIComponent(caseId)}/respond`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}
export function addCaseEvidence(
  dealId: string,
  caseId: string,
  input: AddCaseEvidenceInput,
): Promise<DealCaseEvidence> {
  return apiRequest<DealCaseEvidence>(
    `/deals/${encodeURIComponent(dealId)}/cases/${encodeURIComponent(caseId)}/evidence`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}

export function listDealReminders(
  dealId: string,
  organizationId?: string,
  options?: { signal?: AbortSignal },
): Promise<DealReminder[]> {
  const query = organizationId ? `?organization_id=${encodeURIComponent(organizationId)}` : "";
  return apiRequest<DealReminder[]>(`/deals/${encodeURIComponent(dealId)}/reminders${query}`, {
    signal: options?.signal,
  });
}

export function syncDealReminders(
  dealId: string,
  organizationId?: string,
): Promise<DealReminder[]> {
  const query = organizationId ? `?organization_id=${encodeURIComponent(organizationId)}` : "";
  return apiRequest<DealReminder[]>(`/deals/${encodeURIComponent(dealId)}/reminders/sync${query}`, {
    method: "POST",
  });
}

export function suppressDealReminder(
  dealId: string,
  reminderId: string,
  organizationId?: string,
): Promise<DealReminder> {
  const query = organizationId ? `?organization_id=${encodeURIComponent(organizationId)}` : "";
  return apiRequest<DealReminder>(
    `/deals/${encodeURIComponent(dealId)}/reminders/${encodeURIComponent(reminderId)}/suppress${query}`,
    {
      method: "POST",
    },
  );
}

export function analyzeOpeningRequest(
  input: string | { text: string; buyer_organization_id?: string },
  buyerOrgOrOptions?: string | { signal?: AbortSignal },
  options?: { signal?: AbortSignal },
): Promise<OpeningRequestAnalysisResult> {
  let text: string;
  let buyer_organization_id: string | undefined;
  let signal: AbortSignal | undefined;

  if (typeof input === "string") {
    text = input;
    if (typeof buyerOrgOrOptions === "string") {
      buyer_organization_id = buyerOrgOrOptions;
      signal = options?.signal;
    } else {
      signal = buyerOrgOrOptions?.signal;
    }
  } else {
    text = input.text;
    buyer_organization_id = input.buyer_organization_id;
    if (typeof buyerOrgOrOptions === "object" && buyerOrgOrOptions !== null && "signal" in buyerOrgOrOptions) {
      signal = buyerOrgOrOptions.signal;
    } else if (options?.signal) {
      signal = options.signal;
    }
  }

  return apiRequest<OpeningRequestAnalysisResult>("/deals/opening-request/analyze", {
    method: "POST",
    body: JSON.stringify({
      text,
      ...(buyer_organization_id ? { buyer_organization_id } : {}),
    }),
    signal,
  }).then((res) => ({
    ...res,
    suggested_sellers: (res.suggested_sellers || []).map((seller) => ({
      ...seller,
      id: seller.id || seller.organization_id || "",
    })),
  }));
}

export function interpretSourcingRequirements(
  input: InterpretSourcingRequest,
  options?: { signal?: AbortSignal },
): Promise<InterpretSourcingResponse> {
  return apiRequest<InterpretSourcingResponse>("/sourcing/interpret", {
    method: "POST",
    body: JSON.stringify(input),
    signal: options?.signal,
  });
}

export function getSourcingListings(
  params: { category?: string; completeness?: string; q?: string } = {},
  options?: { signal?: AbortSignal },
): Promise<{ listings: MarketplaceListingDetail[]; total: number }> {
  const query = new URLSearchParams();
  if (params.category) query.set("category", params.category);
  if (params.completeness) query.set("completeness", params.completeness);
  if (params.q) query.set("q", params.q);
  const qs = query.toString();
  return apiRequest<{ listings: MarketplaceListingDetail[]; total: number }>(
    `/sourcing/listings${qs ? `?${qs}` : ""}`,
    { signal: options?.signal },
  );
}

export function compareSourcingListings(
  input: CompareSourcingRequest,
  options?: { signal?: AbortSignal },
): Promise<CompareSourcingResponse> {
  return apiRequest<CompareSourcingResponse>("/sourcing/compare", {
    method: "POST",
    body: JSON.stringify(input),
    signal: options?.signal,
  });
}

export function analyzeSourcingGaps(
  input: GapAnalysisSourcingRequest,
  options?: { signal?: AbortSignal },
): Promise<GapAnalysisSourcingResponse> {
  return apiRequest<GapAnalysisSourcingResponse>("/sourcing/gap-analysis", {
    method: "POST",
    body: JSON.stringify(input),
    signal: options?.signal,
  });
}

export function draftSourcingInquiry(
  input: DraftInquirySourcingRequest,
  options?: { signal?: AbortSignal },
): Promise<InquiryDraft> {
  return apiRequest<InquiryDraft>("/sourcing/draft-inquiry", {
    method: "POST",
    body: JSON.stringify(input),
    signal: options?.signal,
  });
}

export function evaluateSourcing(
  input: EvaluateSourcingRequest,
  options?: { signal?: AbortSignal },
): Promise<EvaluateSourcingResponse> {
  return apiRequest<EvaluateSourcingResponse>("/sourcing/evaluate", {
    method: "POST",
    body: JSON.stringify(input),
    signal: options?.signal,
  });
}

