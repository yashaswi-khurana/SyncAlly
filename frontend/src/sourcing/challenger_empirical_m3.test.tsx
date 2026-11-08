/**
 * Empirical Challenger Verification Suite for Milestone M3 (Frontend Sourcing Hub)
 * Agent: challenger_sourcing_m3_2
 *
 * EMPIRICAL INVESTIGATION MATRIX:
 * 1. Air-Gapped Offline Execution (R4)
 * 2. Prompt Interpretation Regex Bug (copper -> ppe -> Medical Supplies)
 * 3. SourcingHubPage Natural Language Evaluation Disconnection
 * 4. Sector Dropdown Filtering across 5 Sectors (Missing Agricultural Commodities)
 * 5. Deal Creation Bridge URL Hash (`sellerOrganizationId` set to `listing_id`)
 * 6. Deal Creation Bridge Router Mismatch (`sellerId` vs `sellerOrganizationId`)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { ReferenceSourcingHub } from "./SourcingHubPage";
import { MOCK_BUNDLED_LISTINGS } from "./bundledListings";
import { parseRoute } from "../router";
import { interpretPrompt } from "./sourcingEngine";

describe("Challenger Empirical Verification: Milestone M3", () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>;
  let xhrOpenSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
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
  // REQUIREMENT 1: AIR-GAPPED OFFLINE EVALUATION (R4)
  // ============================================================================
  describe("1. Air-Gapped Offline Self-Containment (R4)", () => {
    it("proves client-side UI executes without any remote network calls (air-gapped)", () => {
      render(<ReferenceSourcingHub />);

      const promptInput = screen.getByLabelText(/procurement requirement/i);
      fireEvent.change(promptInput, {
        target: { value: "10,000 boxes nitrile examination gloves with FDA certs, max $9.00 USD" },
      });

      const evalButton = screen.getByRole("button", { name: /evaluate marketplace listings/i });
      fireEvent.click(evalButton);

      // Verify zero network calls were attempted
      expect(fetchSpy).not.toHaveBeenCalled();
      expect(xhrOpenSpy).not.toHaveBeenCalled();
    });

    it("verifies category detection in interpretPrompt: 'copper' correctly matches 'Electronics'", () => {
      const electronicsPrompt = "5000 units automotive spec copper wire harness 28AWG, max $8.00 CIF";
      const parsed = interpretPrompt(electronicsPrompt);

      console.log("Electronics prompt categorized as:", parsed.category);
      expect(parsed.category).toBe("Electronics");
    });

    it("verifies SourcingHubPage handleEvaluate invokes sourcing engine and updates candidate ranking based on prompt", () => {
      render(<ReferenceSourcingHub />);

      // Initial top candidate is Berlin Fastener (Industrial Fasteners, bolts)
      const initialCards = screen.getAllByRole("heading", { level: 3 });
      expect(initialCards[0].textContent).toContain("M8x30 Grade 316 Stainless Steel Hex Cap Bolts");

      // Enter a prompt exclusively requesting Medical Supplies (Nitrile Gloves)
      const promptInput = screen.getByLabelText(/procurement requirement/i);
      fireEvent.change(promptInput, {
        target: { value: "Hospital urgently replenishing 10000 boxes sterile powder-free nitrile examination gloves" },
      });
      fireEvent.click(screen.getByRole("button", { name: /evaluate marketplace listings/i }));

      // SourcingHubPage handleEvaluate genuinely evaluates BUNDLED_MARKETPLACE_LISTING_DETAILS
      const postEvalCards = screen.getAllByRole("heading", { level: 3 });
      console.log("Top candidate after evaluating medical gloves prompt:", postEvalCards[0].textContent);

      // Top candidate is now medical supplies (Nitrile Examination Gloves)
      expect(postEvalCards[0].textContent).toContain("Nitrile Examination Gloves");
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
    it("verifies handleInitiateDeal assigns sellerOrganizationId properly in URL hash", () => {
      render(<ReferenceSourcingHub />);

      // Select Berlin Fastener (Listing: ...101, Org: ...001)
      const berlinCard = screen.getByTestId("listing-card-00000000-0000-4000-8000-000000000101");
      fireEvent.click(within(berlinCard).getByRole("button", { name: /draft inquiry/i }));

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

    it("verifies populated terms format in deal URL", () => {
      render(<ReferenceSourcingHub />);

      const berlinCard = screen.getByTestId("listing-card-00000000-0000-4000-8000-000000000101");
      fireEvent.click(within(berlinCard).getByRole("button", { name: /draft inquiry/i }));
      fireEvent.click(screen.getByRole("button", { name: /initiate deal room/i }));

      const params = new URLSearchParams(window.location.hash.slice(window.location.hash.indexOf("?")));
      expect(params.get("quantity")).toBe("1000");
      expect(params.get("unitPrice")).toBe("11.50");
      expect(params.get("initiatorParty")).toBe("BUYER");
    });
  });
});
