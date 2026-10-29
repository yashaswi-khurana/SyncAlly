import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  createDealMessage,
  getCommercialDocumentDraft,
  getCurrentAgreement,
  getDeal,
  getOrganization,
  listDealFacts,
  listDealMessages,
  listOrganizations,
  listPaymentStatuses,
} from "../api/client";
import type { Deal } from "../api/types";
import DealDetailPage from "./DealDetailPage";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    createDealMessage: vi.fn(),
    getCommercialDocumentDraft: vi.fn(),
    getDeal: vi.fn(),
    getOrganization: vi.fn(),
    getCurrentAgreement: vi.fn(),
    listDealFacts: vi.fn(),
    listDealMessages: vi.fn(),
    listOrganizations: vi.fn(),
    listPaymentStatuses: vi.fn(),
  };
});

const mockedGetDeal = vi.mocked(getDeal);
const mockedGetOrganization = vi.mocked(getOrganization);
const mockedCreateDealMessage = vi.mocked(createDealMessage);
const mockedGetCommercialDocumentDraft = vi.mocked(getCommercialDocumentDraft);
const mockedGetCurrentAgreement = vi.mocked(getCurrentAgreement);
const mockedListDealFacts = vi.mocked(listDealFacts);
const mockedListDealMessages = vi.mocked(listDealMessages);
const mockedListOrganizations = vi.mocked(listOrganizations);
const mockedListPaymentStatuses = vi.mocked(listPaymentStatuses);

const DEAL: Deal = {
  id: "deal-1",
  buyer_organization_id: "11111111-1111-1111-1111-111111111111",
  seller_organization_id: "22222222-2222-2222-2222-222222222222",
  status: "DRAFT",
  version: 0,
};

describe("DealDetailPage", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  beforeEach(() => {
    mockedListPaymentStatuses.mockResolvedValue([]);
    mockedGetCommercialDocumentDraft.mockRejectedValue(
      new ApiError(409, "Agreement not committed"),
    );
    mockedListDealFacts.mockResolvedValue([]);
    mockedListDealMessages.mockResolvedValue([]);
    mockedGetOrganization.mockResolvedValue({
      id: DEAL.seller_organization_id,
      legal_name: "Seller Logistics Ltd",
      country_code: "US",
    });
    mockedListOrganizations.mockResolvedValue([
      {
        id: DEAL.buyer_organization_id,
        legal_name: "Buyer Co",
        country_code: "US",
        role: "ADMIN",
      },
    ]);
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));
  });

  it("fetches the deal on mount and renders its details", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);

    render(<DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} />);

    expect(screen.getByRole("status")).toHaveTextContent(/loading deal/i);
    expect(await screen.findByText("DRAFT")).toBeInTheDocument();
    expect(mockedGetDeal).toHaveBeenCalledWith("deal-1");
    expect(screen.getByText("deal-1")).toBeInTheDocument();
    expect(screen.getByText(DEAL.buyer_organization_id)).toBeInTheDocument();
    expect(screen.getByText(DEAL.seller_organization_id)).toBeInTheDocument();
  });

  it("shows a not found state for a missing or forbidden deal", async () => {
    mockedGetDeal.mockRejectedValue(new ApiError(404, "Deal not found"));

    render(<DealDetailPage dealId="missing" onBackToDeals={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "Deal not found" })).toBeInTheDocument();
  });

  it("shows an error state that can be retried", async () => {
    mockedGetDeal.mockRejectedValueOnce(new ApiError(500, "Server error"));

    render(<DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} />);

    expect(
      await screen.findByRole("heading", { name: /could not load this deal/i }),
    ).toBeInTheDocument();

    mockedGetDeal.mockResolvedValueOnce(DEAL);
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByText("DRAFT")).toBeInTheDocument();
    expect(mockedGetDeal).toHaveBeenCalledTimes(2);
  });

  it("navigates back to the deals workspace when asked", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    const onBackToDeals = vi.fn();

    render(<DealDetailPage dealId="deal-1" onBackToDeals={onBackToDeals} />);
    await screen.findByText("DRAFT");

    fireEvent.click(screen.getByRole("button", { name: "Back to deals" }));

    expect(onBackToDeals).toHaveBeenCalledTimes(1);
  });

  it("renders the 3-step onboarding walkthrough banner for a fresh deal with 0 messages and no agreement", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    mockedListOrganizations.mockResolvedValue([
      {
        id: DEAL.buyer_organization_id,
        legal_name: "Buyer Co",
        country_code: "US",
        role: "ADMIN",
      },
      {
        id: DEAL.seller_organization_id,
        legal_name: "Seller Logistics Ltd",
        country_code: "US",
        role: "MEMBER",
      },
    ]);
    mockedListDealMessages.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));

    render(<DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} />);

    // Dual member chooses Buyer Co from the Viewing as dropdown
    const orgSelector = await screen.findByLabelText("Viewing as");
    fireEvent.change(orgSelector, { target: { value: DEAL.buyer_organization_id } });

    expect(await screen.findByRole("heading", { name: /deal created with seller logistics ltd!/i })).toBeInTheDocument();
    expect(mockedListDealMessages).toHaveBeenCalledWith("deal-1", DEAL.buyer_organization_id);
    expect(screen.getByText(/next steps/i)).toBeInTheDocument();
    expect(
      screen.getByText("Introduce trade terms in the conversation below (e.g. quantity, price, delivery port)."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Review AI-extracted terms and toggle them to Shareable."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Approve the bilateral agreement to generate your invoice."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /start conversation/i })).toBeInTheDocument();
  });

  it("renders the onboarding banner immediately for single-organization members naming the actual counterparty", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    mockedListOrganizations.mockResolvedValue([
      {
        id: DEAL.buyer_organization_id,
        legal_name: "Buyer Co",
        country_code: "US",
        role: "ADMIN",
      },
    ]);
    mockedListDealMessages.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));

    render(<DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: /deal created with seller logistics ltd!/i })).toBeInTheDocument();
    expect(mockedGetOrganization).toHaveBeenCalledWith(DEAL.seller_organization_id);
    expect(mockedListDealMessages).toHaveBeenCalledWith("deal-1", DEAL.buyer_organization_id);
  });

  it("does not name an unrelated organization when user belongs to multiple organizations outside the deal", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    // User belongs to Buyer Co and an unrelated Consulting Corp
    mockedListOrganizations.mockResolvedValue([
      {
        id: DEAL.buyer_organization_id,
        legal_name: "Buyer Co",
        country_code: "US",
        role: "ADMIN",
      },
      {
        id: "unrelated-org-id",
        legal_name: "Unrelated Consulting Corp",
        country_code: "US",
        role: "ADMIN",
      },
    ]);
    mockedListDealMessages.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));

    render(<DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} />);

    // Must resolve actual counterparty from getOrganization, NOT the unrelated Consulting Corp
    expect(await screen.findByRole("heading", { name: /deal created with seller logistics ltd!/i })).toBeInTheDocument();
    expect(screen.queryByText(/unrelated consulting corp/i)).not.toBeInTheDocument();
    expect(mockedGetOrganization).toHaveBeenCalledWith(DEAL.seller_organization_id);
  });

  it("gracefully falls back to 'Counterparty' when getOrganization lookup fails", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    mockedListOrganizations.mockResolvedValue([
      {
        id: DEAL.buyer_organization_id,
        legal_name: "Buyer Co",
        country_code: "US",
        role: "ADMIN",
      },
    ]);
    mockedListDealMessages.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));
    mockedGetOrganization.mockRejectedValue(new ApiError(500, "Organization directory down"));

    render(<DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: /deal created with counterparty!/i })).toBeInTheDocument();
  });

  it("focuses the message input textarea when clicking 'Start Conversation'", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    mockedListDealMessages.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));

    render(<DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} />);
    const button = await screen.findByRole("button", { name: /start conversation/i });
    const messageInput = await screen.findByRole("textbox", { name: /post a message/i });

    fireEvent.click(button);

    expect(document.activeElement).toBe(messageInput);
    expect(messageInput).toHaveAttribute("id", "deal-message-input");
  });

  it("submitting a message via the composer posts the message and dismisses the onboarding banner", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    mockedListDealMessages.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));
    mockedCreateDealMessage.mockResolvedValue({
      id: "msg-1",
      conversation_id: "conv-1",
      author_user_id: "user-1",
      author_agent_id: null,
      body: "We need 500 units at USD 45.",
      visibility: "SHAREABLE",
      source_type: "USER",
      source_reference: null,
      created_at: "2026-10-29T10:00:00Z",
    });

    render(<DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: /deal created with seller logistics ltd!/i })).toBeInTheDocument();

    const input = await screen.findByRole("textbox", { name: /post a message/i });
    fireEvent.change(input, { target: { value: "We need 500 units at USD 45." } });

    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(mockedCreateDealMessage).toHaveBeenCalledWith(
      "deal-1",
      expect.objectContaining({
        body: "We need 500 units at USD 45.",
        visibility: "SHAREABLE",
        organization_id: DEAL.buyer_organization_id,
        idempotency_key: expect.any(String),
      }),
    );

    expect(await screen.findByText("We need 500 units at USD 45.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /deal created with/i })).not.toBeInTheDocument();
  });

  it("reruns freshness check and updates counterparty when a dual member switches party", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    mockedListOrganizations.mockResolvedValue([
      {
        id: DEAL.buyer_organization_id,
        legal_name: "Buyer Co",
        country_code: "US",
        role: "ADMIN",
      },
      {
        id: DEAL.seller_organization_id,
        legal_name: "Seller Co",
        country_code: "US",
        role: "MEMBER",
      },
    ]);
    mockedListDealMessages.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));

    render(<DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} />);

    // 1. Dual member initially has no explicit selection: banner is not rendered
    await screen.findByText("DRAFT");
    expect(screen.queryByRole("heading", { name: /deal created with/i })).not.toBeInTheDocument();

    const orgSelector = await screen.findByLabelText("Viewing as");

    // 2. Select Buyer Co: counterparty is Seller Co, freshness checked for Buyer Co
    fireEvent.change(orgSelector, { target: { value: DEAL.buyer_organization_id } });

    expect(await screen.findByRole("heading", { name: /deal created with seller co!/i })).toBeInTheDocument();
    expect(mockedListDealMessages).toHaveBeenCalledWith("deal-1", DEAL.buyer_organization_id);

    // 3. Switch to Seller Co where messages exist: freshness checked for Seller Co, banner dismissed
    mockedListDealMessages.mockResolvedValue([
      {
        id: "msg-seller-1",
        conversation_id: "conv-1",
        author_user_id: "user-2",
        author_agent_id: null,
        body: "Terms from seller.",
        visibility: "SHAREABLE",
        source_type: "USER",
        source_reference: null,
        created_at: "2026-10-29T10:00:00Z",
      },
    ]);

    fireEvent.change(orgSelector, { target: { value: DEAL.seller_organization_id } });

    await waitFor(() => {
      expect(mockedListDealMessages).toHaveBeenCalledWith("deal-1", DEAL.seller_organization_id);
    });
    expect(screen.queryByRole("heading", { name: /deal created with/i })).not.toBeInTheDocument();

    // 4. Switch back to Buyer Co where 0 messages exist: banner restored with Seller Co
    mockedListDealMessages.mockResolvedValue([]);
    fireEvent.change(orgSelector, { target: { value: DEAL.buyer_organization_id } });

    expect(await screen.findByRole("heading", { name: /deal created with seller co!/i })).toBeInTheDocument();
  });

  it("does not render the onboarding banner if messages already exist", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    mockedListOrganizations.mockResolvedValue([
      {
        id: DEAL.buyer_organization_id,
        legal_name: "Buyer Co",
        country_code: "US",
        role: "ADMIN",
      },
    ]);
    mockedListDealMessages.mockResolvedValue([
      {
        id: "msg-1",
        conversation_id: "conv-1",
        author_user_id: "user-1",
        author_agent_id: null,
        body: "Hello, here are our terms.",
        visibility: "SHAREABLE",
        source_type: "USER",
        source_reference: null,
        created_at: "2026-10-29T10:00:00Z",
      },
    ]);
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));

    render(<DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} />);
    await screen.findByText("DRAFT");

    await waitFor(() => {
      expect(mockedListDealMessages).toHaveBeenCalledWith("deal-1", DEAL.buyer_organization_id);
    });
    expect(screen.queryByRole("heading", { name: /deal created with/i })).not.toBeInTheDocument();
    expect(
      screen.queryByText(/unable to verify deal onboarding status/i),
    ).not.toBeInTheDocument();
  });

  it("does not render the onboarding banner when the selected party already has messages", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    mockedListOrganizations.mockResolvedValue([
      {
        id: DEAL.buyer_organization_id,
        legal_name: "Buyer Co",
        country_code: "US",
        role: "ADMIN",
      },
      {
        id: DEAL.seller_organization_id,
        legal_name: "Seller Co",
        country_code: "US",
        role: "MEMBER",
      },
    ]);
    // Buyer Co has messages, Seller Co does not.
    mockedListDealMessages.mockImplementation(async (_dealId, orgId) => {
      if (orgId === DEAL.buyer_organization_id) {
        return [
          {
            id: "msg-buyer-1",
            conversation_id: "conv-1",
            author_user_id: "user-1",
            author_agent_id: null,
            body: "Buyer message.",
            visibility: "SHAREABLE",
            source_type: "USER",
            source_reference: null,
            created_at: "2026-10-29T10:00:00Z",
          },
        ];
      }
      return [];
    });
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));

    render(<DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} />);
    await screen.findByText("DRAFT");

    const orgSelector = await screen.findByLabelText("Viewing as");
    // When selecting Buyer Co (who has messages):
    fireEvent.change(orgSelector, { target: { value: DEAL.buyer_organization_id } });

    await waitFor(() => {
      expect(mockedListDealMessages).toHaveBeenCalledWith("deal-1", DEAL.buyer_organization_id);
    });
    expect(screen.queryByRole("heading", { name: /deal created with/i })).not.toBeInTheDocument();

    // When switching to Seller Co (who has NO messages):
    fireEvent.change(orgSelector, { target: { value: DEAL.seller_organization_id } });

    expect(await screen.findByRole("heading", { name: /deal created with buyer co!/i })).toBeInTheDocument();
  });

  it("does not render the onboarding banner if an agreement already exists", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    mockedListOrganizations.mockResolvedValue([
      {
        id: DEAL.buyer_organization_id,
        legal_name: "Buyer Co",
        country_code: "US",
        role: "ADMIN",
      },
      {
        id: DEAL.seller_organization_id,
        legal_name: "Seller Co",
        country_code: "US",
        role: "MEMBER",
      },
    ]);
    mockedListDealMessages.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockResolvedValue({
      id: "agr-1",
      deal_id: "deal-1",
      buyer_organization_id: DEAL.buyer_organization_id,
      seller_organization_id: DEAL.seller_organization_id,
      terms_hash: "abcd",
      status: "PENDING_APPROVAL",
      version: 1,
      version_number: 1,
      payment_trigger: "COMMITTED",
      payment_due_condition: "IMMEDIATE",
      terms: {
        line_items: [],
        shipments: [],
        shipment_terms: [],
        payment_terms: [],
      },
      trade_terms: {
        schema_version: 1,
        currency: "USD",
        line_items: [],
        shipment_terms: [],
        payment_terms: [],
      },
      created_at: "2026-10-29T10:00:00Z",
      committed_at: null,
      approvals: [],
    } as unknown as Awaited<ReturnType<typeof getCurrentAgreement>>);

    render(<DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} />);
    await screen.findByText("DRAFT");

    expect(screen.queryByRole("heading", { name: /deal created with/i })).not.toBeInTheDocument();
  });

  it("treats agreement lookup failure (500) as unknown and does not show onboarding banner even when 0 messages exist", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    mockedListDealMessages.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(500, "Internal server failure"));

    render(<DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} />);
    await screen.findByText("DRAFT");

    expect(screen.queryByRole("heading", { name: /deal created with/i })).not.toBeInTheDocument();
    expect(
      await screen.findByText(/unable to verify deal onboarding status: internal server failure/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry check/i })).toBeInTheDocument();
  });

  it("allows retrying the failed agreement check via the Retry check button and displays the banner upon recovery", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    mockedListDealMessages.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(500, "Temporary server glitch"));

    render(<DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} />);
    await screen.findByText("DRAFT");

    expect(
      await screen.findByText(/unable to verify deal onboarding status: temporary server glitch/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /deal created with/i })).not.toBeInTheDocument();

    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No agreement"));
    fireEvent.click(screen.getByRole("button", { name: /retry check/i }));

    expect(await screen.findByRole("heading", { name: /deal created with/i })).toBeInTheDocument();
    expect(
      screen.queryByText(/unable to verify deal onboarding status/i),
    ).not.toBeInTheDocument();
  });

  it("treats initial message list failure (500) as unknown and does not show onboarding banner", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));
    mockedListDealMessages.mockRejectedValue(
      new ApiError(500, "Database connection lost"),
    );

    render(<DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} />);
    await screen.findByText("DRAFT");

    expect(screen.queryByRole("heading", { name: /deal created with/i })).not.toBeInTheDocument();
    expect(
      await screen.findByText(/unable to verify deal onboarding status: database connection lost/i),
    ).toBeInTheDocument();
  });

  it("does not silently retain onboarding banner when background message polling fails", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));
    mockedListDealMessages.mockResolvedValueOnce([]);

    render(
      <DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} freshnessIntervalMs={50} />,
    );

    expect(await screen.findByRole("heading", { name: /deal created with/i })).toBeInTheDocument();

    mockedListDealMessages.mockRejectedValue(new ApiError(500, "Network timeout"));

    expect(
      await screen.findByText(/unable to verify deal onboarding status: network timeout/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /deal created with/i })).not.toBeInTheDocument();
  });

  it("recovers onboarding banner when background polling succeeds after an outage", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));
    mockedListDealMessages.mockResolvedValue([]);

    render(
      <DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} freshnessIntervalMs={50} />,
    );

    expect(await screen.findByRole("heading", { name: /deal created with/i })).toBeInTheDocument();

    // Outage starts during polling
    mockedListDealMessages.mockRejectedValue(new ApiError(500, "Service unavailable"));

    expect(
      await screen.findByText(/unable to verify deal onboarding status: service unavailable/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /deal created with/i })).not.toBeInTheDocument();

    // Outage recovers on subsequent poll
    mockedListDealMessages.mockResolvedValue([]);

    expect(await screen.findByRole("heading", { name: /deal created with/i })).toBeInTheDocument();
    expect(
      screen.queryByText(/unable to verify deal onboarding status/i),
    ).not.toBeInTheDocument();
  });

  it("dismisses onboarding banner when another participant creates an agreement while the deal page is open", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    mockedListDealMessages.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));

    render(
      <DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} freshnessIntervalMs={50} />,
    );

    expect(await screen.findByRole("heading", { name: /deal created with/i })).toBeInTheDocument();

    // Another participant creates an agreement draft without posting messages
    mockedGetCurrentAgreement.mockResolvedValue({
      id: "agr-2",
      deal_id: "deal-1",
      buyer_organization_id: DEAL.buyer_organization_id,
      seller_organization_id: DEAL.seller_organization_id,
      terms_hash: "efgh",
      status: "PENDING_APPROVAL",
      version: 1,
      version_number: 1,
      payment_trigger: "COMMITTED",
      payment_due_condition: "IMMEDIATE",
      terms: {
        line_items: [],
        shipments: [],
        shipment_terms: [],
        payment_terms: [],
      },
      trade_terms: {
        schema_version: 1,
        currency: "USD",
        line_items: [],
        shipment_terms: [],
        payment_terms: [],
      },
      created_at: "2026-10-29T10:00:00Z",
      committed_at: null,
      approvals: [],
    } as unknown as Awaited<ReturnType<typeof getCurrentAgreement>>);

    // Polling effect detects the new agreement and dismisses the onboarding banner
    await waitFor(() => {
      expect(screen.queryByRole("heading", { name: /deal created with/i })).not.toBeInTheDocument();
    });
  });

  it("treats initial organization list failure (500) as unknown and exposes the Retry check button", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));
    mockedListOrganizations.mockRejectedValue(new ApiError(500, "Directory service unreachable"));

    render(<DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} />);
    await screen.findByText("DRAFT");

    expect(screen.queryByRole("heading", { name: /deal created with/i })).not.toBeInTheDocument();
    expect(
      await screen.findByText(/unable to verify deal onboarding status: directory service unreachable/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry check/i })).toBeInTheDocument();
  });

  it("allows retrying the failed organization check via the Retry check button and displays the banner upon recovery", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));
    mockedListOrganizations.mockRejectedValue(new ApiError(500, "Temporary directory failure"));

    render(<DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} />);
    await screen.findByText("DRAFT");

    expect(
      await screen.findByText(/unable to verify deal onboarding status: temporary directory failure/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /deal created with/i })).not.toBeInTheDocument();

    mockedListOrganizations.mockResolvedValue([
      {
        id: DEAL.buyer_organization_id,
        legal_name: "Buyer Co",
        country_code: "US",
        role: "ADMIN",
      },
    ]);
    fireEvent.click(screen.getByRole("button", { name: /retry check/i }));

    expect(await screen.findByRole("heading", { name: /deal created with/i })).toBeInTheDocument();
    expect(
      screen.queryByText(/unable to verify deal onboarding status/i),
    ).not.toBeInTheDocument();
  });

  it("recovers onboarding banner automatically via scheduled retry when initial organization request fails and recovers", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));
    mockedListDealMessages.mockResolvedValue([]);
    mockedListOrganizations.mockRejectedValue(new ApiError(500, "Directory outage"));

    render(
      <DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} freshnessIntervalMs={50} />,
    );

    expect(
      await screen.findByText(/unable to verify deal onboarding status: directory outage/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /deal created with/i })).not.toBeInTheDocument();

    // Directory recovers on the scheduled retry
    mockedListOrganizations.mockResolvedValue([
      {
        id: DEAL.buyer_organization_id,
        legal_name: "Buyer Co",
        country_code: "US",
        role: "ADMIN",
      },
    ]);

    expect(await screen.findByRole("heading", { name: /deal created with/i })).toBeInTheDocument();
    expect(
      screen.queryByText(/unable to verify deal onboarding status/i),
    ).not.toBeInTheDocument();
  });

  it("recovers onboarding banner automatically via scheduled retry when initial message request fails and recovers", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));
    mockedListDealMessages.mockRejectedValue(new ApiError(500, "Message store outage"));

    render(
      <DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} freshnessIntervalMs={50} />,
    );

    expect(
      await screen.findByText(/unable to verify deal onboarding status: message store outage/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /deal created with/i })).not.toBeInTheDocument();

    // Message store recovers on the scheduled retry
    mockedListDealMessages.mockResolvedValue([]);

    expect(await screen.findByRole("heading", { name: /deal created with/i })).toBeInTheDocument();
    expect(
      screen.queryByText(/unable to verify deal onboarding status/i),
    ).not.toBeInTheDocument();
  });
});
