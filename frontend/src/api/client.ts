import { getAccessToken } from "./tokenStore";
import type {
  CreateDealInput,
  CounterpartyInvitationInput,
  Invitation,
  InvitationAcceptance,
  InvitationAcceptanceInput,
  CreateMessageInput,
  CreateOrganizationInput,
  AgreementApproval,
  AgreementHistory,
  AgreementComparison,
  AgreementVersion,
  CommercialDocumentDraft,
  CreateDealFactInput,
  Deal,
  DealFact,
  DealMessage,
  DealSummary,
  FactCorrectionResult,
  FactSuggestionResult,
  FactReviewAction,
  MessageExistence,
  NegotiationAction,
  NegotiationInput,
  NegotiationResult,
  NegotiationView,
  Organization,
  OrganizationDirectoryItem,
  OrganizationMember,
  PaymentAuthorization,
  PaymentMode,
  PaymentPreview,
  PaymentStatus,
  ProposalSuggestion,
  ReviewedProposalTerms,
  TokenResponse,
  ThreadImportInput,
  ThreadImportPreview,
  ThreadPreviewInput,
  Visibility,
} from "./types";

const DEFAULT_ERROR_MESSAGE = "Something went wrong. Please try again.";

/**
 * Upper bound for any API call, above the AI boundary's 20.5-second remote budget.
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

export async function apiRequest<T>(path: string, init: RequestInit = {}, responseType: "json" | "blob" = "json"): Promise<T> {
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
  }, API_REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${apiBaseUrl()}${path}`, {
      ...init,
      headers,
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new ApiError(response.status, await readErrorDetail(response));
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
  });
}

export function listOrganizations(): Promise<Organization[]> {
  return apiRequest<Organization[]>("/organizations");
}

export function getOrganization(organizationId: string): Promise<OrganizationDirectoryItem> {
  return apiRequest<OrganizationDirectoryItem>(`/organizations/${encodeURIComponent(organizationId)}`);
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
): Promise<OrganizationMember> {
  return apiRequest<OrganizationMember>(
    `/organizations/${encodeURIComponent(organizationId)}/members`,
    {
      method: "POST",
      body: JSON.stringify({ email }),
    },
  );
}

export function listDeals(): Promise<DealSummary[]> {
  return apiRequest<DealSummary[]>("/deals");
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

export function acceptInvitation(input: InvitationAcceptanceInput): Promise<InvitationAcceptance> {
  return apiRequest<InvitationAcceptance>("/invitations/accept", {
    method: "POST", body: JSON.stringify(input),
  });
}

export function getDeal(dealId: string): Promise<Deal> {
  return apiRequest<Deal>(`/deals/${encodeURIComponent(dealId)}`);
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
  options?: { signal?: AbortSignal },
): Promise<PaymentStatus[]> {
  return apiRequest<PaymentStatus[]>(`/deals/${encodeURIComponent(dealId)}/payments`, {
    signal: options?.signal,
  });
}

export function authorizeDealPayment(
  dealId: string,
  idempotencyKey: string,
  expectedMode?: PaymentMode,
): Promise<PaymentAuthorization> {
  return apiRequest<PaymentAuthorization>(`/deals/${encodeURIComponent(dealId)}/payments`, {
    method: "POST",
    body: JSON.stringify({ idempotency_key: idempotencyKey, expected_mode: expectedMode }),
  });
}

export function previewDealPayment(dealId: string, signal?: AbortSignal): Promise<PaymentPreview> {
  return apiRequest<PaymentPreview>(`/deals/${encodeURIComponent(dealId)}/payments/preview`, { signal });
}

export function getCommercialDocumentDraft(dealId: string): Promise<CommercialDocumentDraft> {
  return apiRequest<CommercialDocumentDraft>(
    `/deals/${encodeURIComponent(dealId)}/documents/commercial-draft`,
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
  });
}

export function draftDealProposal(
  dealId: string,
  organizationId: string,
): Promise<ProposalSuggestion> {
  return apiRequest<ProposalSuggestion>(`/deals/${encodeURIComponent(dealId)}/ai/proposal`, {
    method: "POST",
    body: JSON.stringify({ organization_id: organizationId }),
  });
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
