import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  apiRequest,
  createDeal,
  createCounterpartyInvitation,
  listOrganizations,
} from "../api/client";
import type { Organization } from "../api/types";
import CreateDealPage from "./CreateDealPage";

const mockAnalyzeOpeningRequest = vi.fn();

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    listOrganizations: vi.fn(),
    createDeal: vi.fn(),
    createCounterpartyInvitation: vi.fn(),
    apiRequest: vi.fn(),
    analyzeOpeningRequest: (...args: unknown[]) => mockAnalyzeOpeningRequest(...args),
  };
});

const mockedListOrganizations = vi.mocked(listOrganizations);
const mockedCreateDeal = vi.mocked(createDeal);
const mockedCreateCounterpartyInvitation = vi.mocked(createCounterpartyInvitation);
const mockedSearch = vi.mocked(apiRequest);

const BUYER_ORG_ID = "11111111-1111-1111-1111-111111111111";
const SELLER_ORG_ID = "22222222-2222-2222-2222-222222222222";

function org(overrides: Partial<Organization> = {}): Organization {
  return {
    id: BUYER_ORG_ID,
    legal_name: "Apex Global Trade",
    country_code: "US",
    role: "ADMIN",
    ...overrides,
  };
}

describe("Tier 5 Adversarial Coverage Hardening: CreateDealPage Edge Cases", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mockedListOrganizations.mockResolvedValue([org()]);
    mockedSearch.mockResolvedValue([
      org({
        id: SELLER_ORG_ID,
        legal_name: "Apex Partner Seller",
        country_code: "DE",
      }),
    ]);
    mockAnalyzeOpeningRequest.mockResolvedValue({
      requirements: {
        item_description: "Precision Bearings",
        quantity: "100",
        unit: "units",
        raw_text: "100 precision bearings",
      },
      suggested_sellers: [
        {
          id: SELLER_ORG_ID,
          legal_name: "Apex Partner Seller",
          country_code: "DE",
          match_score: 0.88,
          match_reasons: ["Product match"],
        },
      ],
      provenance: {
        provider: "offline",
        mode: "offline",
      },
    });
    window.location.hash = "";
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("submits a deal with opening request typed in WITHOUT running normalization", async () => {
    const handleCreated = vi.fn();
    mockedCreateDeal.mockResolvedValue({
      id: "deal-no-norm-123",
      buyer_organization_id: BUYER_ORG_ID,
      seller_organization_id: SELLER_ORG_ID,
      status: "DRAFT",
      version: 0,
      pending_counterparty: false,
    });

    render(<CreateDealPage onCreated={handleCreated} />);
    await screen.findByLabelText("Buyer organization");

    // Type opening request but DO NOT click analyze
    const textarea = screen.getByLabelText(/opening request or quote/i);
    fireEvent.change(textarea, { target: { value: "Looking for 500 bearings without AI analysis" } });

    // Manually search and select seller from directory
    const searchInput = screen.getByLabelText("Seller organization");
    fireEvent.change(searchInput, { target: { value: "Apex Partner" } });
    const option = await screen.findByRole("option", { name: "Apex Partner Seller DE" });
    fireEvent.click(option);

    // Submit deal
    fireEvent.click(screen.getByRole("button", { name: "Create deal" }));

    await waitFor(() => {
      expect(mockedCreateDeal).toHaveBeenCalledWith({
        buyer_organization_id: BUYER_ORG_ID,
        seller_organization_id: SELLER_ORG_ID,
      });
    });

    expect(handleCreated).toHaveBeenCalledWith("deal-no-norm-123", {
      organizationId: BUYER_ORG_ID,
      body: "Looking for 500 bearings without AI analysis",
      visibility: "SHAREABLE",
      idempotencyKey: null,
    });
    expect(mockAnalyzeOpeningRequest).not.toHaveBeenCalled();
  });

  it("submits a deal cleanly after selecting a suggested seller", async () => {
    const handleCreated = vi.fn();
    mockedCreateDeal.mockResolvedValue({
      id: "deal-suggested-456",
      buyer_organization_id: BUYER_ORG_ID,
      seller_organization_id: SELLER_ORG_ID,
      status: "DRAFT",
      version: 0,
      pending_counterparty: false,
    });

    render(<CreateDealPage onCreated={handleCreated} />);
    await screen.findByLabelText("Buyer organization");

    const textarea = screen.getByLabelText(/opening request or quote/i);
    fireEvent.change(textarea, { target: { value: "100 precision bearings" } });

    const analyzeBtn = screen.getByRole("button", { name: /analyze & suggest sellers/i });
    fireEvent.click(analyzeBtn);

    const selectSellerBtn = await screen.findByRole("button", { name: /select seller/i });
    fireEvent.click(selectSellerBtn);

    fireEvent.click(screen.getByRole("button", { name: "Create deal" }));

    await waitFor(() => {
      expect(mockedCreateDeal).toHaveBeenCalledWith({
        buyer_organization_id: BUYER_ORG_ID,
        seller_organization_id: SELLER_ORG_ID,
        initiator_party: "BUYER",
        display_name: undefined,
      });
    });

    expect(handleCreated).toHaveBeenCalledWith("deal-suggested-456", {
      text: "100 precision bearings",
      source: "BUYER_QUOTE",
    });
  });

  it("changing opening text after normalization resets analysis card and enables re-analysis", async () => {
    const handleCreated = vi.fn();
    mockedCreateDeal.mockResolvedValue({
      id: "deal-reanalyzed-789",
      buyer_organization_id: BUYER_ORG_ID,
      seller_organization_id: SELLER_ORG_ID,
      status: "DRAFT",
      version: 0,
      pending_counterparty: false,
    });

    render(<CreateDealPage onCreated={handleCreated} />);
    await screen.findByLabelText("Buyer organization");

    const textarea = screen.getByLabelText(/opening request or quote/i);
    fireEvent.change(textarea, { target: { value: "100 precision bearings" } });

    const analyzeBtn = screen.getByRole("button", { name: /analyze & suggest sellers/i });
    fireEvent.click(analyzeBtn);

    expect(await screen.findByText("Structured Requirements")).toBeInTheDocument();
    expect(screen.getByText("Precision Bearings")).toBeInTheDocument();

    // Now edit text to something else
    fireEvent.change(textarea, { target: { value: "200 hydraulic valves" } });

    // Structured requirements card should be cleared
    expect(screen.queryByText("Structured Requirements")).not.toBeInTheDocument();

    // Mock second analysis
    mockAnalyzeOpeningRequest.mockResolvedValueOnce({
      requirements: {
        item_description: "Hydraulic Valves",
        quantity: "200",
        unit: "units",
        raw_text: "200 hydraulic valves",
      },
      suggested_sellers: [
        {
          id: SELLER_ORG_ID,
          legal_name: "Apex Partner Seller",
          country_code: "DE",
          match_score: 0.95,
          match_reasons: ["Product match: Hydraulic Valves"],
        },
      ],
      provenance: {
        provider: "offline",
        mode: "offline",
      },
    });

    // Re-click analyze
    fireEvent.click(analyzeBtn);

    expect(await screen.findByText("Structured Requirements")).toBeInTheDocument();
    expect(screen.getByText("Hydraulic Valves")).toBeInTheDocument();

    const selectSellerBtn = await screen.findByRole("button", { name: /select seller/i });
    fireEvent.click(selectSellerBtn);

    fireEvent.click(screen.getByRole("button", { name: "Create deal" }));

    await waitFor(() => {
      expect(mockedCreateDeal).toHaveBeenCalled();
    });

    expect(handleCreated).toHaveBeenCalledWith("deal-reanalyzed-789", {
      text: "200 hydraulic valves",
      source: "BUYER_QUOTE",
    });
  });

  it("network failure during normalization displays inline error and does NOT block manual deal creation", async () => {
    mockAnalyzeOpeningRequest.mockRejectedValueOnce(new ApiError(503, "Service Unavailable"));

    const handleCreated = vi.fn();
    mockedCreateDeal.mockResolvedValue({
      id: "deal-fallback-after-error-999",
      buyer_organization_id: BUYER_ORG_ID,
      seller_organization_id: SELLER_ORG_ID,
      status: "DRAFT",
      version: 0,
      pending_counterparty: false,
    });

    render(<CreateDealPage onCreated={handleCreated} />);
    await screen.findByLabelText("Buyer organization");

    const textarea = screen.getByLabelText(/opening request or quote/i);
    fireEvent.change(textarea, { target: { value: "500 specialized components" } });

    const analyzeBtn = screen.getByRole("button", { name: /analyze & suggest sellers/i });
    fireEvent.click(analyzeBtn);

    // Error alert is displayed
    expect(await screen.findByRole("alert")).toHaveTextContent("Service Unavailable");

    // Button should be re-enabled after failure
    expect(analyzeBtn).not.toBeDisabled();

    // User can still proceed with normal manual deal creation
    const searchInput = screen.getByLabelText("Seller organization");
    fireEvent.change(searchInput, { target: { value: "Apex Partner" } });
    const option = await screen.findByRole("option", { name: "Apex Partner Seller DE" });
    fireEvent.click(option);

    fireEvent.click(screen.getByRole("button", { name: "Create deal" }));

    await waitFor(() => {
      expect(mockedCreateDeal).toHaveBeenCalledWith({
        buyer_organization_id: BUYER_ORG_ID,
        seller_organization_id: SELLER_ORG_ID,
      });
    });

    expect(handleCreated).toHaveBeenCalledWith("deal-fallback-after-error-999", {
      organizationId: BUYER_ORG_ID,
      body: "500 specialized components",
      visibility: "SHAREABLE",
      idempotencyKey: null,
    });
  });

  it("creating deal via counterparty invitation carries opening request draft", async () => {
    mockedCreateCounterpartyInvitation.mockResolvedValue({
      deal_id: "deal-invite-111",
      token: "secret-token-xyz",
      invite_url: "https://syncally.test/#/invite?token=secret-token-xyz",
      expires_at: "2026-12-01T00:00:00Z",
      organization_id: BUYER_ORG_ID,
      organization_legal_name: "Apex Global Trade",
      role: "ADMIN",
    });

    render(<CreateDealPage onCreated={vi.fn()} />);
    await screen.findByLabelText("Buyer organization");

    const textarea = screen.getByLabelText(/opening request or quote/i);
    fireEvent.change(textarea, { target: { value: "Looking for supplier of titanium bolts" } });

    // Switch to Invite mode
    const inviteRadio = screen.getByRole("radio", { name: /invite counterparty/i });
    fireEvent.click(inviteRadio);

    // Fill invitation fields
    fireEvent.change(screen.getByLabelText(/counterparty email/i), {
      target: { value: "partner@titanium.de" },
    });
    fireEvent.change(screen.getByLabelText(/legal name/i), {
      target: { value: "Titanium Works GmbH" },
    });
    fireEvent.change(screen.getByLabelText(/country code/i), {
      target: { value: "DE" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Create deal" }));

    await waitFor(() => {
      expect(mockedCreateCounterpartyInvitation).toHaveBeenCalledWith(
        expect.objectContaining({
          buyer_organization_id: BUYER_ORG_ID,
          recipient_email: "partner@titanium.de",
          legal_name: "Titanium Works GmbH",
          country_code: "DE",
        })
      );
    });

    expect(await screen.findByRole("heading", { name: /awaiting counterparty/i })).toBeInTheDocument();
  });
});
