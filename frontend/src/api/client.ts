import { getAccessToken } from "./tokenStore";
import type {
  CreateDealInput,
  CreateOrganizationInput,
  Deal,
  DealSummary,
  Organization,
  OrganizationMember,
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
