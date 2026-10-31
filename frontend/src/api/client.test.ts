import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  API_REQUEST_TIMEOUT_MS,
  ApiError,
  createDealMessage,
  getDealMessageExistence,
  getOrganization,
} from "./client";
import { clearAccessToken, setAccessToken } from "./tokenStore";
import type { CreateMessageInput, DealMessage } from "./types";

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
