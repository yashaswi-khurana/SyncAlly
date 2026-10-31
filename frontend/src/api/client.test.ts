import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  API_REQUEST_TIMEOUT_MS,
  ApiError,
  createDealMessage,
  importDealThread,
  previewDealThreadImport,
  getDealMessageExistence,
  getOrganization,
  listPaymentStatuses,
  suggestDealFacts,
  draftDealProposal,
  getAgreementHistory,
  getAgreementVersion,
  compareAgreementVersions,
  previewDealPayment,
  authorizeDealPayment,
  getTradePack,
} from "./client";
import { clearAccessToken, setAccessToken } from "./tokenStore";
import type { CreateMessageInput, DealMessage, PaymentStatus } from "./types";

const DEAL_ID = "11111111-1111-1111-1111-111111111111";
const IDEMPOTENCY_KEY = "message-request-1";

function messageInput(overrides: Partial<CreateMessageInput> = {}): CreateMessageInput {
  return {
    body: "x",
    visibility: "PRIVATE",
    idempotency_key: IDEMPOTENCY_KEY,
    ...overrides,
  };
}

const CREATED_MESSAGE: DealMessage = {
  id: "message-1",
  conversation_id: "conversation-1",
  author_user_id: "user-1",
  author_agent_id: null,
  body: "Delivery by November 1 works for us.",
  visibility: "SHAREABLE",
  source_type: "USER",
  source_reference: null,
  created_at: "2026-10-25T09:00:00Z",
};

const fetchMock = vi.fn();

describe("trade pack binary client", () => {
  beforeEach(() => { vi.stubGlobal("fetch", fetchMock); setAccessToken("access-token"); });
  afterEach(() => { vi.clearAllMocks(); vi.unstubAllGlobals(); clearAccessToken(); vi.useRealTimers(); });
  const snapshot = { id: "version/1", version_number: 7, terms_hash: "a".repeat(64) };

  it("reads authenticated binary with exact identity and no write body", async () => {
    fetchMock.mockResolvedValue(new Response(new Uint8Array([80, 75, 0, 255]), { headers: { "Content-Type": "application/zip" } }));
    const blob = await getTradePack("deal/1", snapshot, "party/1", "zip");
    expect(Array.from(new Uint8Array(await blob.arrayBuffer()))).toEqual([80, 75, 0, 255]);
    expect(lastRequest().url).toBe(`/deals/deal%2F1/documents/versions/7/trade-pack?agreement_version_id=version%2F1&terms_hash=${snapshot.terms_hash}&organization_id=party%2F1&format=zip`);
    expect(new Headers(lastRequest().init.headers).get("Authorization")).toBe("Bearer access-token");
    expect(lastRequest().init.body).toBeUndefined();
  });
  it.each([401, 404, 409, 413, 422])("keeps JSON error detail for binary %s responses", async (status) => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: "Export unavailable" }, status));
    await expect(getTradePack("deal", snapshot, "party", "html")).rejects.toMatchObject({ status, message: "Export unavailable" });
  });
  it.each(["caller", "timeout"])("cancels binary requests on %s and releases deadline", async (reason) => {
    vi.useFakeTimers();
    const controller = new AbortController();
    fetchMock.mockImplementation((_url: string, init: RequestInit) => new Promise<Response>((_resolve, reject) => {
      init.signal?.addEventListener("abort", () => reject(init.signal?.reason));
    }));
    const result = getTradePack("deal", snapshot, "party", "zip", controller.signal).catch((error: unknown) => error);
    if (reason === "caller") controller.abort();
    else await vi.advanceTimersByTimeAsync(API_REQUEST_TIMEOUT_MS);
    expect(lastRequest().init.signal?.aborted).toBe(true);
    expect(await result).toMatchObject(reason === "caller" ? { name: "AbortError" } : { status: 0 });
    expect(vi.getTimerCount()).toBe(0);
  });
});

describe("payment mode contracts", () => {
  beforeEach(() => { vi.stubGlobal("fetch", fetchMock); setAccessToken("access-token"); });
  afterEach(() => { vi.clearAllMocks(); vi.unstubAllGlobals(); clearAccessToken(); });

  it("reads typed mode and sends only an expected-mode guard, never a provider override", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ provider: "OFFLINE_DEMO", execution_mode: "OFFLINE_DEMO" }));
    expect((await previewDealPayment("deal/1")).execution_mode).toBe("OFFLINE_DEMO");
    expect(lastRequest().url).toBe("/deals/deal%2F1/payments/preview");
    expect(lastRequest().init.body).toBeUndefined();
    fetchMock.mockResolvedValueOnce(jsonResponse({ id: "original", execution_mode: "PAYPAL_SANDBOX", already_existed: true }, 202));
    const replay = await authorizeDealPayment("deal/1", "stable-key", "OFFLINE_DEMO");
    expect(replay.execution_mode).toBe("PAYPAL_SANDBOX");
    expect(sentBody()).toEqual({ idempotency_key: "stable-key", expected_mode: "OFFLINE_DEMO" });
  });
});

describe("agreement history GET contracts", () => {
  beforeEach(() => { vi.stubGlobal("fetch", fetchMock); setAccessToken("access-token"); });
  afterEach(() => { vi.clearAllMocks(); vi.unstubAllGlobals(); clearAccessToken(); });

  it("encodes party/deal and binds exact before/after versions without a write body", async () => {
    fetchMock.mockImplementation(async () => jsonResponse({ versions: [] }));
    const controller = new AbortController();
    await getAgreementHistory("deal/1", "party/1", controller.signal);
    expect(lastRequest().url).toBe("/deals/deal%2F1/agreements/history?organization_id=party%2F1");
    await getAgreementVersion("deal/1", 7, "party/1", controller.signal);
    expect(lastRequest().url).toBe("/deals/deal%2F1/agreements/versions/7?organization_id=party%2F1");
    await compareAgreementVersions("deal/1", 3, 7, "party/1", controller.signal);
    expect(lastRequest().url).toBe("/deals/deal%2F1/agreements/compare?before=3&after=7&organization_id=party%2F1");
    expect(lastRequest().init.body).toBeUndefined();
    expect(lastRequest().init.signal).toBeInstanceOf(AbortSignal);
  });
});

describe("AI invocation contract", () => {
  beforeEach(() => { vi.stubGlobal("fetch", fetchMock); setAccessToken("access-token"); });
  afterEach(() => { vi.clearAllMocks(); vi.unstubAllGlobals(); clearAccessToken(); });

  it.each([suggestDealFacts, draftDealProposal])("preserves additive provenance and sends only the selected organization", async (operation) => {
    const provenance = { provider: "openai", mode: "openai", model: "operator-test-model", context_scope: "shareable_only", fallback_reason: null };
    fetchMock.mockResolvedValue(jsonResponse({ provenance }));
    expect(await operation(DEAL_ID, "buyer")).toEqual({ provenance });
    expect(sentBody()).toEqual({ organization_id: "buyer" });
    expect(lastRequest().init.method).toBe("POST");
  });

  it("does not fabricate provenance for legacy responses", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ status: "VALID", facts: [] }));
    expect(await suggestDealFacts(DEAL_ID, "buyer")).not.toHaveProperty("provenance");
  });
});

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function lastRequest(): { url: string; init: RequestInit } {
  const call = fetchMock.mock.calls.at(-1);
  if (call === undefined) {
    throw new Error("fetch was not called");
  }
  const [url, init] = call as [string, RequestInit];
  return { url, init };
}

function sentBody(): Record<string, unknown> {
  const { init } = lastRequest();
  return JSON.parse(String(init.body)) as Record<string, unknown>;
}

describe("plaintext thread import client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    setAccessToken("access-token");
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
    vi.useRealTimers();
    clearAccessToken();
  });

  it("posts raw preview text and exact confirmed text without author or source claims", async () => {
    const text = " \nFrom: Spoof\r\n> Caf\u00e9 \u{1f600}\r\nPrice: EUR 9 \n ";
    const preview = { text: text.trim(), digest: "plaintext-thread:v1:" + "a".repeat(64), headers: [], warnings: ["Unverified text"] };
    fetchMock.mockResolvedValueOnce(jsonResponse(preview));
    expect(await previewDealThreadImport("deal/with space", { text, organization_id: "buyer" })).toEqual(preview);
    expect(lastRequest().url).toBe("/deals/deal%2Fwith%20space/messages/import/preview");
    expect(lastRequest().init.method).toBe("POST");
    expect(sentBody()).toEqual({ text, organization_id: "buyer" });
    expect(new Headers(lastRequest().init.headers).get("Authorization")).toBe("Bearer access-token");
    fetchMock.mockResolvedValueOnce(jsonResponse({ ...CREATED_MESSAGE, body: preview.text }, 201));
    const created = await importDealThread(DEAL_ID, { text: preview.text, organization_id: "buyer", digest: preview.digest, confirmed: true });
    expect(created.body).toBe(preview.text);
    expect(lastRequest().url).toBe(`/deals/${DEAL_ID}/messages/import`);
    expect(sentBody()).toEqual({ text: preview.text, organization_id: "buyer", digest: preview.digest, confirmed: true, visibility: "PRIVATE", shareable_confirmed: false });
  });

  it.each([409, 413, 422])("preserves the %s import error for draft-safe handling", async (status) => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: "Preview required" }, status));
    await expect(importDealThread(DEAL_ID, { text: "Original", organization_id: "buyer", digest: "digest", confirmed: true }))
      .rejects.toMatchObject({ status, message: "Preview required" });
  });

  it.each(["preview", "import"])("forwards cancellation for %s and releases its deadline", async (operation) => {
    vi.useFakeTimers();
    const controller = new AbortController();
    fetchMock.mockImplementation((_url: string, init: RequestInit) => new Promise<Response>((_resolve, reject) => {
      init.signal?.addEventListener("abort", () => reject(init.signal?.reason));
    }));
    const input = { text: "Terms", organization_id: "buyer", digest: "digest", confirmed: true };
    const pending = (operation === "preview"
      ? previewDealThreadImport(DEAL_ID, input, { signal: controller.signal })
      : importDealThread(DEAL_ID, input, { signal: controller.signal }))
      .catch((error: unknown) => error);
    controller.abort();
    expect(lastRequest().init.signal?.aborted).toBe(true);
    expect(await pending).toHaveProperty("name", "AbortError");
    expect(vi.getTimerCount()).toBe(0);
  });
});

describe("listPaymentStatuses", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    setAccessToken("access-token");
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
    vi.useRealTimers();
    clearAccessToken();
  });

  it.each<PaymentStatus["status"]>([
    "AUTHORIZED", "CREATE_PENDING", "CREATE_UNKNOWN", "PROVIDER_CREATED", "SENT",
    "PENDING", "PARTIALLY_PAID", "PAID", "FAILED", "CANCELLED",
  ])("returns the typed %s snapshot without rewriting diagnostics", async (status) => {
    const payment: PaymentStatus = {
      id: "payment-1", milestone_sequence: 1, amount: "100", currency: "USD", status,
      requires_polling: !["PAID", "FAILED", "CANCELLED"].includes(status),
      reconciled_amount: null, last_checked_at: "2026-10-31T10:40:00Z",
      last_reconciled_at: null, invoice_url: null, recipient_email: "buyer@example.com",
      recipient_name: "Buyer", retry_count: 2, outbox_status: "PROCESSING",
      next_retry_at: "2026-10-31T10:42:00Z", retry_scheduled_at: null,
      lease_expires_at: "2026-10-31T10:42:00Z", failure_reason: null,
    };
    fetchMock.mockResolvedValue(jsonResponse([payment]));
    expect(await listPaymentStatuses("deal/with space")).toEqual([payment]);
    expect(lastRequest().url).toBe("/deals/deal%2Fwith%20space/payments");
    expect(lastRequest().init.method ?? "GET").toBe("GET");
    expect(lastRequest().init.body).toBeUndefined();
    expect(new Headers(lastRequest().init.headers).get("Authorization")).toBe("Bearer access-token");
  });

  it("preserves missing legacy diagnostics rather than fabricating a polling signal", async () => {
    const payment: PaymentStatus = {
      id: "payment-1", milestone_sequence: 1, amount: "100", currency: "USD",
      status: "CREATE_UNKNOWN", reconciled_amount: null,
      last_checked_at: null, last_reconciled_at: null,
    };
    fetchMock.mockResolvedValue(jsonResponse([payment]));
    const [snapshot] = await listPaymentStatuses(DEAL_ID);
    expect(snapshot).toEqual(payment);
    expect(snapshot).not.toHaveProperty("requires_polling");
    expect(snapshot).not.toHaveProperty("retry_scheduled_at");
  });

  it("forwards caller cancellation and clears the request deadline", async () => {
    vi.useFakeTimers();
    const controller = new AbortController();
    fetchMock.mockImplementation(
      (_url: string, init: RequestInit) => new Promise<Response>((_resolve, reject) => {
        init.signal?.addEventListener("abort", () => reject(init.signal?.reason));
      }),
    );
    const pending = listPaymentStatuses(DEAL_ID, { signal: controller.signal })
      .catch((error: unknown) => error);
    const sentSignal = lastRequest().init.signal;
    expect(sentSignal?.aborted).toBe(false);
    controller.abort();
    expect(sentSignal?.aborted).toBe(true);
    expect(await pending).toHaveProperty("name", "AbortError");
    expect(vi.getTimerCount()).toBe(0);
  });
});

describe("createDealMessage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    setAccessToken("access-token");
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
    vi.useRealTimers();
    clearAccessToken();
  });

  it("posts the message and returns the created deal message", async () => {
    fetchMock.mockResolvedValue(jsonResponse(CREATED_MESSAGE, 201));

    const created = await createDealMessage(
      DEAL_ID,
      messageInput({ body: "Delivery by November 1 works for us.", visibility: "SHAREABLE" }),
    );

    const { url, init } = lastRequest();
    expect(url).toBe(`/deals/${DEAL_ID}/messages`);
    expect(init.method).toBe("POST");
    expect(sentBody()).toEqual({
      body: "Delivery by November 1 works for us.",
      visibility: "SHAREABLE",
      idempotency_key: IDEMPOTENCY_KEY,
    });
    expect(sentBody()).not.toHaveProperty("source_type");
    expect(created).toEqual(CREATED_MESSAGE);
  });

  it("sends the bearer token and JSON content type", async () => {
    fetchMock.mockResolvedValue(jsonResponse(CREATED_MESSAGE, 201));

    await createDealMessage(DEAL_ID, messageInput({ body: "Hello" }));

    const headers = new Headers(lastRequest().init.headers);
    expect(headers.get("Authorization")).toBe("Bearer access-token");
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("Accept")).toBe("application/json");
  });

  it("skips the authorization header when no token is stored", async () => {
    clearAccessToken();
    fetchMock.mockResolvedValue(jsonResponse(CREATED_MESSAGE, 201));

    await createDealMessage(DEAL_ID, messageInput({ body: "Hello" }));

    expect(new Headers(lastRequest().init.headers).get("Authorization")).toBeNull();
  });

  it("encodes the deal id in the request path", async () => {
    fetchMock.mockResolvedValue(jsonResponse(CREATED_MESSAGE, 201));

    await createDealMessage("deal/with space", messageInput({ body: "Hello" }));

    expect(lastRequest().url).toBe("/deals/deal%2Fwith%20space/messages");
  });

  it("forwards source_type alongside the contract fields", async () => {
    fetchMock.mockResolvedValue(jsonResponse(CREATED_MESSAGE, 201));

    await createDealMessage(
      DEAL_ID,
      messageInput({
        body: "Quoted from the RFQ",
        source_type: "USER",
        source_reference: "rfq-2026-10",
        organization_id: "22222222-2222-2222-2222-222222222222",
      }),
    );

    expect(sentBody()).toEqual({
      body: "Quoted from the RFQ",
      visibility: "PRIVATE",
      idempotency_key: IDEMPOTENCY_KEY,
      source_type: "USER",
      source_reference: "rfq-2026-10",
      organization_id: "22222222-2222-2222-2222-222222222222",
    });
  });

  it("posts source_type when it is the sole optional field", async () => {
    fetchMock.mockResolvedValue(jsonResponse(CREATED_MESSAGE, 201));

    await createDealMessage(DEAL_ID, messageInput({ source_type: "USER" }));

    expect(sentBody()).toEqual({
      body: "x",
      visibility: "PRIVATE",
      source_type: "USER",
      idempotency_key: IDEMPOTENCY_KEY,
    });
  });

  it("reuses the supplied idempotency key across retry attempts", async () => {
    fetchMock.mockImplementation(async () => jsonResponse(CREATED_MESSAGE, 201));
    const input = messageInput({ body: "Retry me" });

    await createDealMessage(DEAL_ID, input);
    const firstKey = sentBody()["idempotency_key"];
    await createDealMessage(DEAL_ID, input);
    const secondKey = sentBody()["idempotency_key"];

    expect(firstKey).toBe(IDEMPOTENCY_KEY);
    expect(secondKey).toBe(firstKey);
  });

  it("aborts the underlying request when the caller aborts", async () => {
    const controller = new AbortController();
    let sentSignal: AbortSignal | undefined;
    fetchMock.mockImplementation(
      (_url: string, init: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          sentSignal = init.signal ?? undefined;
          init.signal?.addEventListener("abort", () => reject(init.signal?.reason));
        }),
    );

    const caught = createDealMessage(
      DEAL_ID,
      messageInput(),
      { signal: controller.signal },
    ).catch((error: unknown) => error);

    expect(sentSignal?.aborted).toBe(false);
    controller.abort();

    expect(sentSignal?.aborted).toBe(true);
    expect(await caught).toHaveProperty("name", "AbortError");
  });

  it("still accepts callers that pass no options", async () => {
    fetchMock.mockResolvedValue(jsonResponse(CREATED_MESSAGE, 201));

    const created = await createDealMessage(DEAL_ID, messageInput());

    expect(created).toEqual(CREATED_MESSAGE);
    expect((lastRequest().init.signal as AbortSignal).aborted).toBe(false);
  });

  it("rethrows an abort error instead of reporting an outage", async () => {
    const controller = new AbortController();
    const abortError = new DOMException("The operation was aborted.", "AbortError");
    fetchMock.mockImplementation(async () => {
      controller.abort();
      throw abortError;
    });

    const caught = await createDealMessage(
      DEAL_ID,
      messageInput(),
      { signal: controller.signal },
    ).catch((error: unknown) => error);

    expect(caught).toBe(abortError);
    expect(caught).not.toBeInstanceOf(ApiError);
  });

  it("rethrows a custom abort reason", async () => {
    const controller = new AbortController();
    const reason = new Error("navigated away");
    controller.abort(reason);
    fetchMock.mockRejectedValue(reason);

    const caught = await createDealMessage(
      DEAL_ID,
      messageInput(),
      { signal: controller.signal },
    ).catch((error: unknown) => error);

    expect(caught).toBe(reason);
    expect(caught).not.toBeInstanceOf(ApiError);
  });

  it("fails with a timeout ApiError when the request stalls past the deadline", async () => {
    vi.useFakeTimers();
    fetchMock.mockImplementation(
      (_url: string, init: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          init.signal?.addEventListener("abort", () => {
            reject(new DOMException("The operation was aborted.", "AbortError"));
          });
        }),
    );

    const pending = createDealMessage(DEAL_ID, messageInput()).catch(
      (error: unknown) => error,
    );
    await vi.advanceTimersByTimeAsync(API_REQUEST_TIMEOUT_MS);

    const caught = await pending;
    expect(caught).toBeInstanceOf(ApiError);
    expect(caught).toMatchObject({
      status: 0,
      message: "The SyncAlly API took too long to respond. Please try again.",
    });
  });

  it("clears the request deadline once the response arrives", async () => {
    vi.useFakeTimers();
    fetchMock.mockResolvedValue(jsonResponse(CREATED_MESSAGE, 201));

    await createDealMessage(DEAL_ID, messageInput());

    expect(vi.getTimerCount()).toBe(0);
  });

  it("surfaces a 401 session expiry as an ApiError", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ detail: "Could not validate credentials" }, 401),
    );

    const caught = await createDealMessage(DEAL_ID, messageInput({ body: "Hi" }))
      .catch((error: unknown) => error);

    expect(caught).toBeInstanceOf(ApiError);
    expect(caught).toMatchObject({
      status: 401,
      message: "Could not validate credentials",
    });
  });

  it("surfaces a 403 membership denial as an ApiError", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ detail: "You are not a member of this deal" }, 403),
    );

    const caught = await createDealMessage(DEAL_ID, messageInput({ body: "Hi" }))
      .catch((error: unknown) => error);

    expect(caught).toBeInstanceOf(ApiError);
    expect(caught).toMatchObject({
      status: 403,
      message: "You are not a member of this deal",
    });
  });

  it("surfaces a 400 validation detail as an ApiError", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ detail: "Message body must not be blank" }, 400),
    );

    const caught = await createDealMessage(DEAL_ID, messageInput({ body: " " }))
      .catch((error: unknown) => error);

    expect(caught).toBeInstanceOf(ApiError);
    expect(caught).toMatchObject({
      status: 400,
      message: "Message body must not be blank",
    });
  });

  it("joins FastAPI 422 validation messages into the error text", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          detail: [
            { loc: ["body", "body"], msg: "String should have at least 1 character" },
            { loc: ["body", "visibility"], msg: "Input should be 'PRIVATE' or 'SHAREABLE'" },
          ],
        },
        422,
      ),
    );

    const caught = await createDealMessage(DEAL_ID, messageInput({ body: "" }))
      .catch((error: unknown) => error);

    expect(caught).toBeInstanceOf(ApiError);
    expect(caught).toMatchObject({
      status: 422,
      message:
        "String should have at least 1 character; Input should be 'PRIVATE' or 'SHAREABLE'",
    });
  });

  it("falls back to a safe message when a 500 response has no JSON body", async () => {
    fetchMock.mockResolvedValue(new Response("Internal Server Error", { status: 500 }));

    const caught = await createDealMessage(DEAL_ID, messageInput({ body: "Hi" }))
      .catch((error: unknown) => error);

    expect(caught).toBeInstanceOf(ApiError);
    expect(caught).toMatchObject({
      status: 500,
      message: "Something went wrong. Please try again.",
    });
  });

  it("surfaces a network failure as an ApiError with status 0", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));

    const caught = await createDealMessage(DEAL_ID, messageInput({ body: "Hi" }))
      .catch((error: unknown) => error);

    expect(caught).toBeInstanceOf(ApiError);
    expect(caught).toMatchObject({
      status: 0,
      message: "Unable to reach the SyncAlly API. Check that it is running.",
    });
  });
});

describe("getDealMessageExistence", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    setAccessToken("access-token");
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
    clearAccessToken();
  });

  it("requests the deal-wide existence endpoint and returns the boolean", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ has_messages: true }));

    await expect(getDealMessageExistence(DEAL_ID)).resolves.toBe(true);
    expect(lastRequest().url).toBe(`/deals/${DEAL_ID}/messages/existence`);
  });

  it("throws instead of treating a malformed payload as fresh", async () => {
    fetchMock.mockResolvedValue(jsonResponse({}));

    await expect(getDealMessageExistence(DEAL_ID)).rejects.toThrow(
      "The server returned an unexpected onboarding status.",
    );
  });
});

describe("getOrganization", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    setAccessToken("access-token");
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
    clearAccessToken();
  });

  it("fetches public organization details by ID", async () => {
    const orgId = "22222222-2222-2222-2222-222222222222";
    fetchMock.mockResolvedValue(
      jsonResponse({
        id: orgId,
        legal_name: "Global Freight Ltd",
        country_code: "US",
      }),
    );

    const result = await getOrganization(orgId);

    expect(result).toEqual({
      id: orgId,
      legal_name: "Global Freight Ltd",
      country_code: "US",
    });
    expect(lastRequest().url).toBe(`/organizations/${orgId}`);
  });

  it("propagates ApiError on 404 not found", async () => {
    const missingId = "33333333-3333-3333-3333-333333333333";
    fetchMock.mockResolvedValue(
      jsonResponse({ detail: "Organization not found" }, 404),
    );

    await expect(getOrganization(missingId)).rejects.toThrow("Organization not found");
  });
});
