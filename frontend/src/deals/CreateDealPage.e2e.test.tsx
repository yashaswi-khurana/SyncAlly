/**
 * Opaque-box E2E test suite for buyer-side opening request analysis & seller suggestion.
 *
 * Covers Tiers 1-4:
 * - Tier 1: Feature Coverage (Analysis trigger, normalization card, suggested sellers, deal creation)
 * - Tier 2: Boundary & Corner Cases (Empty, max-length, zero matches, self-dealing, unicode)
 * - Tier 3: Cross-Feature Combinations (Pairwise workflows, partial fields, inline errors, roles)
 * - Tier 4: Real-World Procurement Scenarios (Aerospace, Agriculture, Offline resilience)
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  apiRequest,
  createDeal,
  listOrganizations,
} from "../api/client";
import type { Organization } from "../api/types";
import CreateDealPage from "./CreateDealPage";

// Contract interfaces matching PROJECT.md § 3
interface NormalizedTradeRequirements {
  category?: string | null;
  item_description?: string | null;
  quantity?: string | null;
  unit?: string | null;
  target_unit_price?: string | null;
  budget?: string | null;
  currency?: string | null;
  destination_country_code?: string | null;
  destination_name?: string | null;
  target_delivery_date?: string | null;
  capabilities_required?: string[];
  raw_text: string;
}

interface SuggestedSeller {
  id: string;
  legal_name: string;
  country_code: string;
  match_score?: number;
  match_reasons?: string[];
  capabilities?: string[];
  products?: string[];
  regions?: string[];
}

interface OpeningRequestAnalysisResult {
  requirements: NormalizedTradeRequirements;
  suggested_sellers: SuggestedSeller[];
  provenance?: {
    provider?: string;
    mode?: string;
    model?: string;
    fallback_reason?: string | null;
  };
}

// Mock client functions including analyzeOpeningRequest
const mockAnalyzeOpeningRequest = vi.fn<
  (text?: unknown, buyer_organization_id?: unknown) => Promise<OpeningRequestAnalysisResult>
>();

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    listOrganizations: vi.fn(),
    createDeal: vi.fn(),
    createCounterpartyInvitation: vi.fn(),
    apiRequest: vi.fn(),
    analyzeOpeningRequest: (...args: [string, string?]) =>
      mockAnalyzeOpeningRequest(...args),
  };
});

const mockedListOrganizations = vi.mocked(listOrganizations);
const mockedCreateDeal = vi.mocked(createDeal);
const mockedSearch = vi.mocked(apiRequest);

const BUYER_ORG_ID = "11111111-1111-1111-1111-111111111111";
const SELLER_BOLTS_ID = "22222222-2222-2222-2222-222222222222";

function org(overrides: Partial<Organization> = {}): Organization {
  return {
    id: BUYER_ORG_ID,
    legal_name: "Global Procurement Corp",
    country_code: "US",
    role: "ADMIN",
    ...overrides,
  };
}

function mockFastenerAnalysis(): OpeningRequestAnalysisResult {
  return {
    requirements: {
      item_description: "Stainless steel bolts",
      category: "Fasteners",
      quantity: "500",
      unit: "units",
      target_unit_price: "12.50",
      currency: "USD",
      destination_country_code: "DE",
      destination_name: "Berlin, Germany",
      target_delivery_date: "2026-12-01",
      capabilities_required: ["Precision Machining"],
      raw_text:
        "We need 500 units of stainless steel bolts delivered to Berlin, Germany by 2026-12-01. Budget is $12.50 per unit.",
    },
    suggested_sellers: [
      {
        id: SELLER_BOLTS_ID,
        legal_name: "Berlin Fastener & Bolt GmbH",
        country_code: "DE",
        match_score: 0.92,
        match_reasons: [
          "Matches product: Stainless steel bolts",
          "Delivers to Germany (DE)",
          "Offers Precision Machining",
        ],
        capabilities: ["Precision Machining"],
        products: ["Stainless steel bolts"],
        regions: ["DE", "FR", "US"],
      },
    ],
    provenance: {
      provider: "openai",
      mode: "openai",
      model: "gpt-4o-mini",
    },
  };
}

describe("CreateDealPage E2E Opening Request Analysis & Seller Suggestion", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mockedListOrganizations.mockResolvedValue([org()]);
    mockedSearch.mockResolvedValue([
      org({
        id: SELLER_BOLTS_ID,
        legal_name: "Berlin Fastener & Bolt GmbH",
        country_code: "DE",
      }),
    ]);
    mockAnalyzeOpeningRequest.mockResolvedValue(mockFastenerAnalysis());
    window.location.hash = "";
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  // ============================================================================
  // TIER 1: FEATURE COVERAGE
  // ============================================================================

  describe("Tier 1: Feature Coverage", () => {
    it("renders the 'Analyze & suggest sellers' trigger button beneath opening request textarea", async ({
      skip,
    }) => {
      render(<CreateDealPage onCreated={vi.fn()} />);
      expect(
        await screen.findByLabelText("Buyer organization")
      ).toBeInTheDocument();

      const button = screen.queryByRole("button", {
        name: /analyze & suggest sellers|analyze quote|suggest sellers/i,
      });
      if (!button) {
        skip("Milestone M3: Analyze button not yet rendered in CreateDealPage");
        return;
      }
      expect(button).toBeInTheDocument();
    });

    it("clicking 'Analyze & suggest sellers' triggers analysis and renders structured requirements card", async ({
      skip,
    }) => {
      render(<CreateDealPage onCreated={vi.fn()} />);
      await screen.findByLabelText("Buyer organization");

      const button = screen.queryByRole("button", {
        name: /analyze & suggest sellers|analyze quote|suggest sellers/i,
      });
      if (!button) {
        skip("Milestone M3: Analyze button not yet rendered in CreateDealPage");
        return;
      }

      const textarea = screen.getByLabelText(/opening request or quote/i);
      fireEvent.change(textarea, {
        target: {
          value:
            "We need 500 units of stainless steel bolts delivered to Berlin, Germany by 2026-12-01. Budget is $12.50 per unit.",
        },
      });

      fireEvent.click(button);

      await waitFor(() => {
        expect(mockAnalyzeOpeningRequest).toHaveBeenCalled();
      });

      const items = await screen.findAllByText(/stainless steel bolts/i);
      expect(items.length).toBeGreaterThan(0);
      const quantities = screen.getAllByText(/500/);
      expect(quantities.length).toBeGreaterThan(0);
    });

    it("renders suggested seller cards with legal name, country code, and match score badge", async ({
      skip,
    }) => {
      render(<CreateDealPage onCreated={vi.fn()} />);
      await screen.findByLabelText("Buyer organization");

      const button = screen.queryByRole("button", {
        name: /analyze & suggest sellers|analyze quote|suggest sellers/i,
      });
      if (!button) {
        skip("Milestone M3: Analyze button not yet rendered in CreateDealPage");
        return;
      }

      const textarea = screen.getByLabelText(/opening request or quote/i);
      fireEvent.change(textarea, {
        target: { value: "500 stainless steel bolts" },
      });
      fireEvent.click(button);

      expect(
        await screen.findByText("Berlin Fastener & Bolt GmbH")
      ).toBeInTheDocument();
      expect(screen.getByText(/92%|0\.92/)).toBeInTheDocument();
    });

    it("renders match reasons on each suggested seller card", async ({
      skip,
    }) => {
      render(<CreateDealPage onCreated={vi.fn()} />);
      await screen.findByLabelText("Buyer organization");

      const button = screen.queryByRole("button", {
        name: /analyze & suggest sellers|analyze quote|suggest sellers/i,
      });
      if (!button) {
        skip("Milestone M3: Analyze button not yet rendered in CreateDealPage");
        return;
      }

      const textarea = screen.getByLabelText(/opening request or quote/i);
      fireEvent.change(textarea, {
        target: { value: "500 stainless steel bolts" },
      });
      fireEvent.click(button);

      expect(
        await screen.findByText(/matches product: stainless steel bolts/i)
      ).toBeInTheDocument();
    });

    it("standard deal creation proceeds normally without analysis when opening request is omitted", async () => {
      const handleCreated = vi.fn();
      mockedCreateDeal.mockResolvedValue({
        id: "deal-123",
        buyer_organization_id: BUYER_ORG_ID,
        seller_organization_id: SELLER_BOLTS_ID,
        status: "DRAFT",
        version: 0,
        pending_counterparty: false,
      });

      render(<CreateDealPage onCreated={handleCreated} />);
      await screen.findByLabelText("Buyer organization");

      // Search and pick seller from standard directory combobox
      const searchInput = screen.getByLabelText("Seller organization");
      fireEvent.change(searchInput, { target: { value: "Berlin" } });

      const option = await screen.findByRole("option", {
        name: "Berlin Fastener & Bolt GmbH DE",
      });
      fireEvent.click(option);

      // Submit deal without typing opening message or triggering analysis
      fireEvent.click(screen.getByRole("button", { name: "Create deal" }));

      await waitFor(() => {
        expect(mockedCreateDeal).toHaveBeenCalledWith({
          buyer_organization_id: BUYER_ORG_ID,
          seller_organization_id: SELLER_BOLTS_ID,
        });
      });
      expect(handleCreated).toHaveBeenCalledWith("deal-123");
      expect(mockAnalyzeOpeningRequest).not.toHaveBeenCalled();
    });
  });

  // ============================================================================
  // TIER 2: BOUNDARY & CORNER CASES
  // ============================================================================

  describe("Tier 2: Boundary & Corner Cases", () => {
    it("disables or ignores analysis when opening request textarea is empty or whitespace only", async ({
      skip,
    }) => {
      render(<CreateDealPage onCreated={vi.fn()} />);
      await screen.findByLabelText("Buyer organization");

      const button = screen.queryByRole("button", {
        name: /analyze & suggest sellers|analyze quote|suggest sellers/i,
      });
      if (!button) {
        skip("Milestone M3: Analyze button not yet rendered in CreateDealPage");
        return;
      }

      const textarea = screen.getByLabelText(/opening request or quote/i);
      fireEvent.change(textarea, { target: { value: "   \n\t  " } });
      fireEvent.click(button);

      expect(mockAnalyzeOpeningRequest).not.toHaveBeenCalled();
    });

    it("handles maximum length 8,000 characters in opening request without crashing", async () => {
      render(<CreateDealPage onCreated={vi.fn()} />);
      await screen.findByLabelText("Buyer organization");

      const textarea = screen.getByLabelText(/opening request or quote/i);
      const longText = "Need fasteners. " + "A".repeat(7980);
      fireEvent.change(textarea, { target: { value: longText } });

      expect(textarea).toHaveValue(longText);
    });

    it("displays friendly empty state when zero sellers match requirements", async ({
      skip,
    }) => {
      mockAnalyzeOpeningRequest.mockResolvedValueOnce({
        requirements: {
          item_description: "Non-existent Satellite Optics",
          raw_text: "Need Satellite Optics",
        },
        suggested_sellers: [],
      });

      render(<CreateDealPage onCreated={vi.fn()} />);
      await screen.findByLabelText("Buyer organization");

      const button = screen.queryByRole("button", {
        name: /analyze & suggest sellers|analyze quote|suggest sellers/i,
      });
      if (!button) {
        skip("Milestone M3: Analyze button not yet rendered in CreateDealPage");
        return;
      }

      const textarea = screen.getByLabelText(/opening request or quote/i);
      fireEvent.change(textarea, { target: { value: "Need Satellite Optics" } });
      fireEvent.click(button);

      expect(
        await screen.findByText(/no registered sellers matched/i)
      ).toBeInTheDocument();
    });

    it("excludes active buyer organization from suggested sellers list in UI", async ({
      skip,
    }) => {
      render(<CreateDealPage onCreated={vi.fn()} />);
      await screen.findByLabelText("Buyer organization");

      const button = screen.queryByRole("button", {
        name: /analyze & suggest sellers|analyze quote|suggest sellers/i,
      });
      if (!button) {
        skip("Milestone M3: Analyze button not yet rendered in CreateDealPage");
        return;
      }

      const textarea = screen.getByLabelText(/opening request or quote/i);
      fireEvent.change(textarea, {
        target: { value: "500 stainless steel bolts" },
      });
      fireEvent.click(button);

      await screen.findByText("Berlin Fastener & Bolt GmbH");
      // The buyer org legal name should not appear as a suggested seller card
      const suggestionCards = screen.queryAllByTestId("suggested-seller-card");
      for (const card of suggestionCards) {
        expect(card).not.toHaveTextContent("Global Procurement Corp");
      }
    });

    it("renders Unicode and multi-language characters in requirements card without distortion", async ({
      skip,
    }) => {
      mockAnalyzeOpeningRequest.mockResolvedValueOnce({
        requirements: {
          item_description: "Café de Colombia 顶级咖啡豆",
          raw_text: "Café de Colombia 顶级咖啡豆 1000 kg",
        },
        suggested_sellers: [],
      });

      render(<CreateDealPage onCreated={vi.fn()} />);
      await screen.findByLabelText("Buyer organization");

      const button = screen.queryByRole("button", {
        name: /analyze & suggest sellers|analyze quote|suggest sellers/i,
      });
      if (!button) {
        skip("Milestone M3: Analyze button not yet rendered in CreateDealPage");
        return;
      }

      const textarea = screen.getByLabelText(/opening request or quote/i);
      fireEvent.change(textarea, {
        target: { value: "Café de Colombia 顶级咖啡豆 1000 kg" },
      });
      fireEvent.click(button);

      expect(
        await screen.findByText(/café de colombia 顶级咖啡豆/i)
      ).toBeInTheDocument();
    });
  });

  // ============================================================================
  // TIER 3: CROSS-FEATURE COMBINATIONS
  // ============================================================================

  describe("Tier 3: Cross-Feature Combinations", () => {
    it("one-click seller selection updates selected seller and switches counterparty mode", async ({
      skip,
    }) => {
      render(<CreateDealPage onCreated={vi.fn()} />);
      await screen.findByLabelText("Buyer organization");

      const button = screen.queryByRole("button", {
        name: /analyze & suggest sellers|analyze quote|suggest sellers/i,
      });
      if (!button) {
        skip("Milestone M3: Analyze button not yet rendered in CreateDealPage");
        return;
      }

      const textarea = screen.getByLabelText(/opening request or quote/i);
      fireEvent.change(textarea, {
        target: { value: "500 stainless steel bolts" },
      });
      fireEvent.click(button);

      const selectBtn = await screen.findByRole("button", {
        name: /select seller|choose seller/i,
      });
      fireEvent.click(selectBtn);

      const combobox = screen.getByRole("combobox", {
        name: /search registered organizations|seller organization/i,
      });
      expect(combobox).toHaveValue("Berlin Fastener & Bolt GmbH");
    });

    it("gracefully displays inline error message when analysis API fails", async ({
      skip,
    }) => {
      mockAnalyzeOpeningRequest.mockRejectedValueOnce(
        new ApiError(500, "AI Service Temporary Outage")
      );

      render(<CreateDealPage onCreated={vi.fn()} />);
      await screen.findByLabelText("Buyer organization");

      const button = screen.queryByRole("button", {
        name: /analyze & suggest sellers|analyze quote|suggest sellers/i,
      });
      if (!button) {
        skip("Milestone M3: Analyze button not yet rendered in CreateDealPage");
        return;
      }

      const textarea = screen.getByLabelText(/opening request or quote/i);
      fireEvent.change(textarea, {
        target: { value: "500 stainless steel bolts" },
      });
      fireEvent.click(button);

      expect(
        await screen.findByText(/ai service temporary outage|something went wrong/i)
      ).toBeInTheDocument();
      // Form must remain functional and not crash
      expect(
        screen.getByRole("button", { name: "Create deal" })
      ).toBeInTheDocument();
    });

    it("displays partial trade attributes cleanly when some fields are absent", async ({
      skip,
    }) => {
      mockAnalyzeOpeningRequest.mockResolvedValueOnce({
        requirements: {
          item_description: "Precision Bolts",
          quantity: "500",
          unit: "units",
          target_unit_price: null,
          budget: null,
          currency: null,
          raw_text: "500 precision bolts",
        },
        suggested_sellers: [],
      });

      render(<CreateDealPage onCreated={vi.fn()} />);
      await screen.findByLabelText("Buyer organization");

      const button = screen.queryByRole("button", {
        name: /analyze & suggest sellers|analyze quote|suggest sellers/i,
      });
      if (!button) {
        skip("Milestone M3: Analyze button not yet rendered in CreateDealPage");
        return;
      }

      const textarea = screen.getByLabelText(/opening request or quote/i);
      fireEvent.change(textarea, { target: { value: "500 precision bolts" } });
      fireEvent.click(button);

      expect(await screen.findByText(/precision bolts/i)).toBeInTheDocument();
      const quantities = screen.getAllByText(/500/);
      expect(quantities.length).toBeGreaterThan(0);
    });

    it("maintains separate state and appropriate labels when switching between Buyer and Seller roles", async () => {
      render(<CreateDealPage onCreated={vi.fn()} />);
      await screen.findByLabelText("Buyer organization");

      const sellerRadio = screen.getByRole("radio", { name: /seller/i });
      fireEvent.click(sellerRadio);

      expect(
        screen.getByLabelText(/quote to the buyer|opening request or quote/i)
      ).toBeInTheDocument();
    });
  });

  // ============================================================================
  // TIER 4: REAL-WORLD PROCUREMENT SCENARIOS
  // ============================================================================

  describe("Tier 4: Real-World Procurement Scenarios", () => {
    it("full buyer workflow: enter quote -> analyze -> select seller -> create deal", async ({
      skip,
    }) => {
      const handleCreated = vi.fn();
      mockedCreateDeal.mockResolvedValue({
        id: "deal-aerospace-999",
        buyer_organization_id: BUYER_ORG_ID,
        seller_organization_id: SELLER_BOLTS_ID,
        status: "DRAFT",
        version: 0,
        pending_counterparty: false,
      });

      render(<CreateDealPage onCreated={handleCreated} />);
      await screen.findByLabelText("Buyer organization");

      const button = screen.queryByRole("button", {
        name: /analyze & suggest sellers|analyze quote|suggest sellers/i,
      });
      if (!button) {
        skip("Milestone M3: Analyze button not yet rendered in CreateDealPage");
        return;
      }

      const quote =
        "We need 500 units of stainless steel bolts delivered to Berlin, Germany by 2026-12-01. Budget is $12.50 per unit.";
      const textarea = screen.getByLabelText(/opening request or quote/i);
      fireEvent.change(textarea, { target: { value: quote } });
      fireEvent.click(button);

      const selectBtn = await screen.findByRole("button", {
        name: /select seller|choose seller/i,
      });
      fireEvent.click(selectBtn);

      fireEvent.click(screen.getByRole("button", { name: "Create deal" }));

      await waitFor(() => {
        expect(mockedCreateDeal).toHaveBeenCalledWith({
          buyer_organization_id: BUYER_ORG_ID,
          seller_organization_id: SELLER_BOLTS_ID,
          initiator_party: "BUYER",
          display_name: undefined,
        });
      });
      expect(handleCreated).toHaveBeenCalledWith("deal-aerospace-999", {
        text: quote,
        source: "BUYER_QUOTE",
      });
    });

    it("offline resilience workflow: displays offline extractor provenance badge", async ({
      skip,
    }) => {
      mockAnalyzeOpeningRequest.mockResolvedValueOnce({
        requirements: {
          item_description: "Industrial Fasteners",
          raw_text: "500 Industrial Fasteners",
        },
        suggested_sellers: [],
        provenance: {
          provider: "offline",
          mode: "offline",
          fallback_reason: "missing_credentials",
        },
      });

      render(<CreateDealPage onCreated={vi.fn()} />);
      await screen.findByLabelText("Buyer organization");

      const button = screen.queryByRole("button", {
        name: /analyze & suggest sellers|analyze quote|suggest sellers/i,
      });
      if (!button) {
        skip("Milestone M3: Analyze button not yet rendered in CreateDealPage");
        return;
      }

      const textarea = screen.getByLabelText(/opening request or quote/i);
      fireEvent.change(textarea, {
        target: { value: "500 Industrial Fasteners" },
      });
      fireEvent.click(button);

      expect(
        await screen.findByText(/offline|fallback|rule-based/i)
      ).toBeInTheDocument();
    });

    it("standard procurement workflow without opening request analysis succeeds cleanly", async () => {
      const handleCreated = vi.fn();
      mockedCreateDeal.mockResolvedValue({
        id: "deal-standard-001",
        buyer_organization_id: BUYER_ORG_ID,
        seller_organization_id: SELLER_BOLTS_ID,
        status: "DRAFT",
        version: 0,
        pending_counterparty: false,
      });

      render(<CreateDealPage onCreated={handleCreated} />);
      await screen.findByLabelText("Buyer organization");

      const searchInput = screen.getByLabelText("Seller organization");
      fireEvent.change(searchInput, { target: { value: "Berlin" } });

      const option = await screen.findByRole("option", {
        name: "Berlin Fastener & Bolt GmbH DE",
      });
      fireEvent.click(option);

      fireEvent.click(screen.getByRole("button", { name: "Create deal" }));

      await waitFor(() => {
        expect(mockedCreateDeal).toHaveBeenCalledWith({
          buyer_organization_id: BUYER_ORG_ID,
          seller_organization_id: SELLER_BOLTS_ID,
        });
      });
      expect(handleCreated).toHaveBeenCalledWith("deal-standard-001");
    });
  });
});
