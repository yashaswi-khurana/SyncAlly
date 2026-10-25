import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, createDealMessage } from "./client";
import { clearAccessToken, setAccessToken } from "./tokenStore";
import type { DealMessage } from "./types";

const DEAL_ID = "11111111-1111-1111-1111-111111111111";

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
    clearAccessToken();
  });

  it("posts the message and returns the created deal message", async () => {
    fetchMock.mockResolvedValue(jsonResponse(CREATED_MESSAGE, 201));

    const created = await createDealMessage(DEAL_ID, {
      body: "Delivery by November 1 works for us.",
      visibility: "SHAREABLE",
    });

    const { url, init } = lastRequest();
    expect(url).toBe(`/deals/${DEAL_ID}/messages`);
    expect(init.method).toBe("POST");
    expect(sentBody()).toEqual({
      body: "Delivery by November 1 works for us.",
      visibility: "SHAREABLE",
    });
    expect(created).toEqual(CREATED_MESSAGE);
  });

  it("sends the bearer token and JSON content type", async () => {
    fetchMock.mockResolvedValue(jsonResponse(CREATED_MESSAGE, 201));

    await createDealMessage(DEAL_ID, { body: "Hello", visibility: "PRIVATE" });

    const headers = new Headers(lastRequest().init.headers);
    expect(headers.get("Authorization")).toBe("Bearer access-token");
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("Accept")).toBe("application/json");
  });

  it("skips the authorization header when no token is stored", async () => {
    clearAccessToken();
    fetchMock.mockResolvedValue(jsonResponse(CREATED_MESSAGE, 201));

    await createDealMessage(DEAL_ID, { body: "Hello", visibility: "PRIVATE" });

    expect(new Headers(lastRequest().init.headers).get("Authorization")).toBeNull();
  });

  it("encodes the deal id in the request path", async () => {
    fetchMock.mockResolvedValue(jsonResponse(CREATED_MESSAGE, 201));

    await createDealMessage("deal/with space", { body: "Hello", visibility: "PRIVATE" });

    expect(lastRequest().url).toBe("/deals/deal%2Fwith%20space/messages");
  });

  it("drops the derived source_type but forwards the contract fields", async () => {
    fetchMock.mockResolvedValue(jsonResponse(CREATED_MESSAGE, 201));

    await createDealMessage(DEAL_ID, {
      body: "Quoted from the RFQ",
      visibility: "PRIVATE",
      source_type: "USER",
      source_reference: "rfq-2026-10",
      organization_id: "22222222-2222-2222-2222-222222222222",
    });

    expect(sentBody()).toEqual({
      body: "Quoted from the RFQ",
      visibility: "PRIVATE",
      source_reference: "rfq-2026-10",
      organization_id: "22222222-2222-2222-2222-222222222222",
    });
    expect(sentBody()).not.toHaveProperty("source_type");
  });

  it("posts only body and visibility when source_type is the sole optional field", async () => {
    fetchMock.mockResolvedValue(jsonResponse(CREATED_MESSAGE, 201));

    await createDealMessage(DEAL_ID, {
      body: "x",
      visibility: "PRIVATE",
      source_type: "USER",
    });

    expect(sentBody()).toEqual({ body: "x", visibility: "PRIVATE" });
  });

  it("forwards an abort signal to fetch", async () => {
    fetchMock.mockResolvedValue(jsonResponse(CREATED_MESSAGE, 201));
    const controller = new AbortController();

    await createDealMessage(
      DEAL_ID,
      { body: "x", visibility: "PRIVATE" },
      { signal: controller.signal },
    );

    expect(lastRequest().init.signal).toBe(controller.signal);
  });

  it("still accepts callers that pass no options", async () => {
    fetchMock.mockResolvedValue(jsonResponse(CREATED_MESSAGE, 201));

    await createDealMessage(DEAL_ID, { body: "x", visibility: "PRIVATE" });

    expect(lastRequest().init.signal).toBeUndefined();
  });

  it("surfaces a 401 session expiry as an ApiError", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ detail: "Could not validate credentials" }, 401),
    );

    const caught = await createDealMessage(DEAL_ID, { body: "Hi", visibility: "PRIVATE" })
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

    const caught = await createDealMessage(DEAL_ID, { body: "Hi", visibility: "PRIVATE" })
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

    const caught = await createDealMessage(DEAL_ID, { body: " ", visibility: "PRIVATE" })
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

    const caught = await createDealMessage(DEAL_ID, { body: "", visibility: "PRIVATE" })
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

    const caught = await createDealMessage(DEAL_ID, { body: "Hi", visibility: "PRIVATE" })
      .catch((error: unknown) => error);

    expect(caught).toBeInstanceOf(ApiError);
    expect(caught).toMatchObject({
      status: 500,
      message: "Something went wrong. Please try again.",
    });
  });

  it("surfaces a network failure as an ApiError with status 0", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));

    const caught = await createDealMessage(DEAL_ID, { body: "Hi", visibility: "PRIVATE" })
      .catch((error: unknown) => error);

    expect(caught).toBeInstanceOf(ApiError);
    expect(caught).toMatchObject({
      status: 0,
      message: "Unable to reach the SyncAlly API. Check that it is running.",
    });
  });
});
