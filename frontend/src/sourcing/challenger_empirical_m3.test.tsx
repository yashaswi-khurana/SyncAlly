/**
 * Empirical Challenger Verification Suite for Milestone M3 (Frontend Sourcing Hub)
 * Agent: challenger_sourcing_m3_2
 *
 * EMPIRICAL INVESTIGATION MATRIX:
 * 1. Local rendering of the disclosed demo catalogue
 * 2. Prompt Interpretation Regex Bug (copper -> ppe -> Medical Supplies)
 * 3. SourcingHubPage Natural Language Evaluation Disconnection
 * 4. Sector Dropdown Filtering across 5 Sectors (Missing Agricultural Commodities)
 * 5. Deal Creation Bridge URL Hash (`sellerOrganizationId` set to `listing_id`)
 * 6. Deal Creation Bridge Router Mismatch (`sellerId` vs `sellerOrganizationId`)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, render, screen, fireEvent, within } from "@testing-library/react";
import { ReferenceSourcingHub as SourcingHub } from "./SourcingHubPage";
import { MOCK_BUNDLED_LISTINGS } from "./bundledListings";
import { parseRoute } from "../router";
import { interpretPrompt } from "./sourcingEngine";
import { evaluateNaturalRequirements, installSourcingMocks, openServerInquiry } from "./sourcingTestFixtures";
import {
  draftSourcingInquiry,
  evaluateSourcing,
  interpretSourcingRequirements,
} from "../api/client";

const ReferenceSourcingHub = () => <SourcingHub initialListings={MOCK_BUNDLED_LISTINGS} />;

vi.mock("../api/client", () => ({
  draftSourcingInquiry: vi.fn(),
  evaluateSourcing: vi.fn(),
  interpretSourcingRequirements: vi.fn(),
}));

describe("Challenger Empirical Verification: Milestone M3", () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>;
  let xhrOpenSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.resetAllMocks();
    installSourcingMocks();
    window.location.hash = "";
    fetchSpy = vi.spyOn(window, "fetch");
    xhrOpenSpy = vi.spyOn(window.XMLHttpRequest.prototype, "open");
  });

  afterEach(() => {
    fetchSpy.mockRestore();
    xhrOpenSpy.mockRestore();
    vi.clearAllMocks();
  });

  // ============================================================================
  // REQUIREMENT 1: LOCAL DEMO CATALOGUE RENDERING
  // ============================================================================
  describe("1. Bundled Demo Catalogue Disclosure", () => {
    it("renders the bundled catalogue locally and labels it as unverified demo data", () => {
      render(<ReferenceSourcingHub />);

      expect(screen.getByText(/bundled sample suppliers and listing data are not verified marketplace offers/i))
        .toBeInTheDocument();
      expect(screen.getAllByRole("heading", { level: 3 }).length).toBeGreaterThan(0);
      expect(fetchSpy).not.toHaveBeenCalled();
      expect(xhrOpenSpy).not.toHaveBeenCalled();
    });

    it("verifies category detection in interpretPrompt: 'copper' correctly matches 'Electronics'", () => {
      const electronicsPrompt = "5000 units automotive spec copper wire harness 28AWG, max $8.00 CIF";
      const parsed = interpretPrompt(electronicsPrompt);

      console.log("Electronics prompt categorized as:", parsed.category);
      expect(parsed.category).toBe("Electronics");
    });

    it("interprets and evaluates through the backend sourcing endpoints", async () => {
      render(<ReferenceSourcingHub />);

      const initialCards = screen.getAllByRole("heading", { level: 3 });
      expect(initialCards[0].textContent).toContain("M8x30 Grade 316 Stainless Steel Hex Cap Bolts");

      const requirements = {
        title: "Nitrile examination gloves",
        category: "Medical Supplies & PPE",
        description: "Nitrile examination gloves",
        technical_specs: { materials: [], certifications: [], standards: [] },
        pricing: { currency: "USD" },
        quantity: { target_quantity: "10000", unit: "boxes" },
        delivery: { destination_country_code: "DE" },
        commercial_terms: {
          acceptable_incoterms: [],
          min_warranty_months: 12,
          inspection_requirement: "NONE",
        },
      };
      vi.mocked(interpretSourcingRequirements).mockResolvedValue({
        requirements,
        parsed_fields: ["quantity", "category"],
        ai_provider: "openai",
        ai_model: "test-model",
        fallback_reason: null,
      } as never);
      vi.mocked(evaluateSourcing).mockResolvedValue({
        requirements,
        comparisons: [{
          listing_id: "demo-medical-1",
          listing_title: "Nitrile Examination Gloves",
          seller_organization_id: "demo-supplier",
          seller_organization_name: "Demo Medical Supplier",
          country_code: "DE",
          unit_price: "10.00",
          currency: "USD",
          available_quantity: "20000",
          moq: "100",
          unit: "boxes",
          lead_time_days: 10,
          composite_score: 90,
          tier: "Tier A",
          match_tier: "A",
          score_breakdown: {
            specifications: 90,
            pricing: 90,
            quantity_and_moq: 90,
            lead_time: 90,
            commercial_terms: 90,
            composite: 90,
          },
          attribute_matrix: [],
          detected_gaps: [],
        }],
        inquiries: {},
        total_listings_evaluated: 1,
      } as never);
      vi.mocked(draftSourcingInquiry).mockResolvedValue({
        listing_id: "demo-medical-1",
        seller_organization_name: "Demo Medical Supplier",
        subject: "Demo RFQ",
        body: "Please confirm availability.",
        gaps_addressed: [],
      });

      const promptInput = screen.getByLabelText(/procurement requirement/i);
      fireEvent.change(promptInput, {
        target: { value: "Hospital urgently replenishing 10000 boxes sterile powder-free nitrile examination gloves" },
      });
      fireEvent.click(screen.getByRole("button", { name: /interpret requirements/i }));
      await screen.findByText(/review the interpreted requirements before ranking/i);
      expect(evaluateSourcing).not.toHaveBeenCalled();

      fireEvent.click(screen.getByRole("button", { name: /confirm requirements and evaluate/i }));

      expect(await screen.findByRole("heading", { name: "Nitrile Examination Gloves" })).toBeInTheDocument();
      expect(interpretSourcingRequirements).toHaveBeenCalledOnce();
      expect(evaluateSourcing).toHaveBeenCalledOnce();
      fireEvent.click(screen.getByRole("button", { name: /draft inquiry/i }));
      await screen.findByRole("dialog");
      expect(draftSourcingInquiry).toHaveBeenCalledWith({
        requirements,
        listing_id: "demo-medical-1",
      });
    });

    it("discards stale interpretation and inquiry responses after context changes", async () => {
      const deferred = <T,>() => {
        let resolve!: (value: T) => void;
        const promise = new Promise<T>((complete) => {
          resolve = complete;
        });
        return { promise, resolve };
      };
      const staleInterpretation =
        deferred<Awaited<ReturnType<typeof interpretSourcingRequirements>>>();
      const currentInterpretation =
        deferred<Awaited<ReturnType<typeof interpretSourcingRequirements>>>();
      const currentRequirements = {
        title: "Current item",
        category: "Industrial Fasteners",
        description: "Current item",
        technical_specs: { materials: [], certifications: [], standards: [] },
        pricing: { currency: "USD" },
        quantity: { target_quantity: "1000", unit: "boxes" },
        delivery: { destination_country_code: "DE" },
        commercial_terms: {
          acceptable_incoterms: [],
          min_warranty_months: 12,
          inspection_requirement: "NONE",
        },
      };
      const oldRequirements = { ...currentRequirements, title: "Stale item" };
      vi.mocked(interpretSourcingRequirements)
        .mockReturnValueOnce(staleInterpretation.promise)
        .mockReturnValueOnce(currentInterpretation.promise);
      vi.mocked(evaluateSourcing).mockResolvedValue({
        requirements: currentRequirements,
        comparisons: [
          {
            listing_id: "current-supplier-a",
            listing_title: "Current Listing A",
            seller_organization_id: "supplier-a",
            seller_organization_name: "Current Supplier A",
            country_code: "DE",
            unit_price: "10.00",
            currency: "USD",
            available_quantity: "2000",
            moq: "100",
            lead_time_days: 10,
            composite_score: 90,
            tier: "Tier A",
            match_tier: "A",
            attribute_matrix: [],
            detected_gaps: [],
          },
          {
            listing_id: "current-supplier-b",
            listing_title: "Current Listing B",
            seller_organization_id: "supplier-b",
            seller_organization_name: "Current Supplier B",
            country_code: "DE",
            unit_price: "11.00",
            currency: "USD",
            available_quantity: "2000",
            moq: "100",
            lead_time_days: 12,
            composite_score: 85,
            tier: "Tier B",
            match_tier: "B",
            attribute_matrix: [],
            detected_gaps: [],
          },
        ],
        inquiries: {},
        total_listings_evaluated: 2,
      } as never);
      const staleInquiry =
        deferred<Awaited<ReturnType<typeof draftSourcingInquiry>>>();
      vi.mocked(draftSourcingInquiry).mockReturnValueOnce(staleInquiry.promise);

      render(<ReferenceSourcingHub />);
      const promptInput = screen.getByLabelText(/procurement requirement/i);
      fireEvent.change(promptInput, { target: { value: "Old requirement" } });
      fireEvent.click(screen.getByRole("button", { name: /interpret requirements/i }));
      expect(screen.getByRole("button", { name: /working/i })).toBeDisabled();
      fireEvent.change(promptInput, { target: { value: "Current requirement" } });
      expect(screen.getByRole("button", { name: /interpret requirements/i })).toBeEnabled();
      fireEvent.click(screen.getByRole("button", { name: /interpret requirements/i }));

      await act(async () => {
        staleInterpretation.resolve({
          requirements: oldRequirements,
          parsed_fields: ["title"],
          ai_provider: "openai",
          ai_model: "stale-model",
          fallback_reason: null,
        } as never);
      });
      expect(screen.queryByText(/review the interpreted requirements before ranking/i)).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: /working/i })).toBeDisabled();

      await act(async () => {
        currentInterpretation.resolve({
          requirements: currentRequirements,
          parsed_fields: ["title", "quantity"],
          ai_provider: "openai",
          ai_model: "test-model",
          fallback_reason: null,
        } as never);
      });
      await screen.findByText(/review the interpreted requirements before ranking/i);
      expect(screen.getByText(/Current item/)).toBeInTheDocument();
      expect(screen.queryByText(/Stale item/)).not.toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: /confirm requirements and evaluate/i }));
      await screen.findByText("Candidate Listings (2)");

      fireEvent.click(
        within(screen.getByTestId("listing-card-current-supplier-a"))
          .getByRole("button", { name: /draft inquiry/i }),
      );
      fireEvent.click(screen.getByTestId("listing-card-current-supplier-b"));
      await act(async () => {
        staleInquiry.resolve({
          listing_id: "current-supplier-a",
          seller_organization_name: "Current Supplier A",
          subject: "Stale inquiry",
          body: "Stale inquiry body",
          gaps_addressed: [],
        });
      });

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      expect(
        screen.getByRole("heading", { name: /Attribute Comparison Matrix — Current Supplier B/i }),
      ).toBeInTheDocument();
    });
  });

  // ============================================================================
  // REQUIREMENT 2: SECTOR DROPDOWN FILTERING ACROSS ALL 5 SECTORS
  // ============================================================================
  describe("2. Sector Dropdown Filtering across 5 Sectors", () => {
    it("verifies sector dropdown includes the 5th commercial sector (Agricultural Commodities)", () => {
      render(<ReferenceSourcingHub />);
      const sectorSelect = screen.getByLabelText(/filter by sector:/i) as HTMLSelectElement;

      const optionTexts = Array.from(sectorSelect.options).map((opt) => opt.textContent?.trim());
      console.log("Available sector dropdown options in UI:", optionTexts);

      // Sourcing Hub is mandated to support 5 sectors:
      // Fasteners, Electronics, Agricultural Commodities, Textiles, Medical Supplies
      const hasAgriOption = Array.from(sectorSelect.options).some(
        (o) => /agri|commodity|coffee|grain|crop/i.test(o.text) || /agri/i.test(o.value)
      );

      expect(hasAgriOption).toBe(true);
      expect(optionTexts).toEqual([
        "All Sectors",
        "Industrial Fasteners",
        "Electronics",
        "Agricultural Commodities",
        "Textiles",
        "Medical Supplies",
      ]);
    });

    it("verifies MOCK_BUNDLED_LISTINGS includes candidates for Agricultural Commodities", () => {
      const agriCandidates = MOCK_BUNDLED_LISTINGS.filter(
        (c) => c.category.toLowerCase().includes("agri") || c.category.toLowerCase().includes("commodity")
      );
      console.log("Number of Agricultural Commodities candidates in MOCK_BUNDLED_LISTINGS:", agriCandidates.length);

      // BUNDLED_MARKETPLACE_LISTING_DETAILS has 3 agricultural listings (110, 111, 112)
      expect(agriCandidates.length).toBe(3);
    });

    it("verifies dynamic count updates for the 4 implemented sectors in UI", () => {
      render(<ReferenceSourcingHub />);
      const sectorSelect = screen.getByLabelText(/filter by sector:/i) as HTMLSelectElement;

      // Fasteners (4 candidates)
      fireEvent.change(sectorSelect, { target: { value: "Fasteners" } });
      expect(screen.getByText("Candidate Listings (4)")).toBeInTheDocument();

      // Electronics (2 candidates)
      fireEvent.change(sectorSelect, { target: { value: "Electronics" } });
      expect(screen.getByText("Candidate Listings (2)")).toBeInTheDocument();

      // Textiles (1 candidate)
      fireEvent.change(sectorSelect, { target: { value: "Textiles" } });
      expect(screen.getByText("Candidate Listings (1)")).toBeInTheDocument();

      // Medical (1 candidate)
      fireEvent.change(sectorSelect, { target: { value: "Medical" } });
      expect(screen.getByText("Candidate Listings (1)")).toBeInTheDocument();
    });
  });

  // ============================================================================
  // REQUIREMENT 3: DEAL CREATION BRIDGE & POPULATED TERMS
  // ============================================================================
  describe("3. Deal Creation Bridge URL Hash & Terms", () => {
    it("verifies handleInitiateDeal assigns sellerOrganizationId properly in URL hash", async () => {
      render(<ReferenceSourcingHub />);

      await evaluateNaturalRequirements();
      await openServerInquiry("00000000-0000-4000-8000-000000000101");

      // Click Initiate Deal Room
      fireEvent.click(screen.getByRole("button", { name: /initiate deal room/i }));

      const hash = window.location.hash;
      const params = new URLSearchParams(hash.slice(hash.indexOf("?")));

      console.log("Generated Deal Hash:", hash);
      console.log("listingId param:", params.get("listingId"));
      console.log("sellerOrganizationId param:", params.get("sellerOrganizationId"));

      // Listing ID is correctly 00000000-0000-4000-8000-000000000101
      expect(params.get("listingId")).toBe("00000000-0000-4000-8000-000000000101");

      // Verify sellerOrganizationId is the actual seller organization ID (11111111-0000-4000-8000-000000000001)
      expect(params.get("sellerOrganizationId")).toBe("11111111-0000-4000-8000-000000000001");
      expect(params.get("sellerId")).toBe("11111111-0000-4000-8000-000000000001");
    });

    it("verifies router parseRoute parses sellerOrganizationId correctly from bridge hash", () => {
      // Sourcing Hub initiates deal by navigating to:
      // #/deals/new?listingId=...&sellerOrganizationId=...
      const bridgeUrlHash =
        "#/deals/new?listingId=00000000-0000-4000-8000-000000000101&sellerOrganizationId=11111111-0000-4000-8000-000000000001&initiatorParty=BUYER&quantity=1000&unitPrice=11.50";

      const parsedRoute = parseRoute(bridgeUrlHash);
      console.log("Parsed Route from Bridge Hash:", parsedRoute);

      expect(parsedRoute.name).toBe("create");
      if (parsedRoute.name === "create") {
        expect(parsedRoute.listingId).toBe("00000000-0000-4000-8000-000000000101");
        expect(parsedRoute.initiatorParty).toBe("BUYER");
        expect(parsedRoute.sellerOrganizationId).toBe("11111111-0000-4000-8000-000000000001");
      }
    });

    it("verifies populated terms format in deal URL", async () => {
      render(<ReferenceSourcingHub />);

      await evaluateNaturalRequirements();
      await openServerInquiry("00000000-0000-4000-8000-000000000101");
      fireEvent.click(screen.getByRole("button", { name: /initiate deal room/i }));

      const params = new URLSearchParams(window.location.hash.slice(window.location.hash.indexOf("?")));
      expect(params.get("quantity")).toBe("1000");
      expect(params.get("unitPrice")).toBe("11.50");
      expect(params.get("initiatorParty")).toBe("BUYER");
    });
  });
});
