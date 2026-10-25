import { getAccessToken } from "./tokenStore";
import type {
  CreateDealInput,
  CreateMessageInput,
  CreateOrganizationInput,
  AgreementApproval,
  AgreementVersion,
  CommercialDocumentDraft,
  Deal,
  DealFact,
  DealMessage,
  DealSummary,
  FactCorrectionResult,
  FactSuggestionResult,
  FactReviewAction,
  Organization,
  OrganizationMember,
  PaymentAuthorization,
  PaymentStatus,
  ProposalSuggestion,
  TokenResponse,
} from "./types";

const DEFAULT_ERROR_MESSAGE = "Something went wrong. Please try again.";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
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

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, null, "Unable to reach the SyncAlly API. Check that it is running.");
  }

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
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
  terms: Omit<ProposalSuggestion, "status">,
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
  // source_type is derived by the server from the verified actor; sending it would
  // fail once the request schema forbids unknown fields.
  const { body, visibility, source_reference, organization_id } = input;
  return apiRequest<DealMessage>(`/deals/${encodeURIComponent(dealId)}/messages`, {
    method: "POST",
    body: JSON.stringify({ body, visibility, source_reference, organization_id }),
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

export function listDealFacts(dealId: string, organizationId: string): Promise<DealFact[]> {
  const query = new URLSearchParams({ organization_id: organizationId });
  return apiRequest<DealFact[]>(`/deals/${encodeURIComponent(dealId)}/facts?${query.toString()}`);
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
