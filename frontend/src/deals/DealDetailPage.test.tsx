import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  getCommercialDocumentDraft,
  getCurrentAgreement,
  getDeal,
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
    getCommercialDocumentDraft: vi.fn(),
    getDeal: vi.fn(),
    getCurrentAgreement: vi.fn(),
    listDealFacts: vi.fn(),
    listDealMessages: vi.fn(),
    listOrganizations: vi.fn(),
    listPaymentStatuses: vi.fn(),
  };
});

const mockedGetDeal = vi.mocked(getDeal);
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

    expect(await screen.findByRole("heading", { name: /deal created with seller logistics ltd!/i })).toBeInTheDocument();
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

  it("focuses the message input textarea when clicking 'Start Conversation'", async () => {
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

    const messageInput = document.createElement("textarea");
    messageInput.id = "deal-message-input";
    document.body.appendChild(messageInput);

    try {
      render(<DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} />);
      const button = await screen.findByRole("button", { name: /start conversation/i });
      fireEvent.click(button);
      expect(document.activeElement).toBe(messageInput);
    } finally {
      document.body.removeChild(messageInput);
    }
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
      {
        id: DEAL.seller_organization_id,
        legal_name: "Seller Co",
        country_code: "US",
        role: "MEMBER",
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

    expect(screen.queryByRole("heading", { name: /deal created with/i })).not.toBeInTheDocument();
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
});
