import { getAccessToken } from "./tokenStore";
import type {
  CreateDealInput,
  CreateMessageInput,
  CreateOrganizationInput,
  AgreementApproval,
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
  Organization,
  OrganizationDirectoryItem,
  OrganizationMember,
  PaymentAuthorization,
  PaymentStatus,
  ProposalSuggestion,
  ReviewedProposalTerms,
  TokenResponse,
  Visibility,
} from "./types";

const DEFAULT_ERROR_MESSAGE = "Something went wrong. Please try again.";

/**
 * Upper bound for any API call. Matches the backend's provider timeout so a
 * request cannot outlive the server-side work it is waiting on.
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

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
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
    return (await response.json()) as T;
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

export function getDeal(dealId: string): Promise<Deal> {
  return apiRequest<Deal>(`/deals/${encodeURIComponent(dealId)}`);
}

export function getCurrentAgreement(dealId: string): Promise<AgreementVersion> {
  return apiRequest<AgreementVersion>(
    `/deals/${encodeURIComponent(dealId)}/agreements/current`,
  );
}

export function listPaymentStatuses(dealId: string): Promise<PaymentStatus[]> {
  return apiRequest<PaymentStatus[]>(`/deals/${encodeURIComponent(dealId)}/payments`);
}

export function authorizeDealPayment(
  dealId: string,
  idempotencyKey: string,
): Promise<PaymentAuthorization> {
  return apiRequest<PaymentAuthorization>(`/deals/${encodeURIComponent(dealId)}/payments`, {
    method: "POST",
    body: JSON.stringify({ idempotency_key: idempotencyKey }),
  });
}

export function getCommercialDocumentDraft(dealId: string): Promise<CommercialDocumentDraft> {
  return apiRequest<CommercialDocumentDraft>(
    `/deals/${encodeURIComponent(dealId)}/documents/commercial-draft`,
  );
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
): Promise<AgreementVersion> {
  return apiRequest<AgreementVersion>(
    `/deals/${encodeURIComponent(dealId)}/agreements/${versionNumber}/commit`,
    { method: "POST", body: JSON.stringify({ terms_hash: termsHash }) },
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
