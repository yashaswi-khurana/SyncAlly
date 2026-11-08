import { describe, expect, it } from "vitest";
import {
  interpretPrompt,
  evaluateCandidateListing,
  rescoreCandidatesWithOverrides,
  draftSellerInquiry,
} from "./sourcingEngine";
import {
  BUNDLED_MARKETPLACE_LISTING_DETAILS,
  MOCK_BUNDLED_LISTINGS,
} from "./bundledListings";
import { parseRoute, sourcingPath, navigateToSourcing } from "../router";
import {
  interpretSourcingRequirements,
  getSourcingListings,
  compareSourcingListings,
  analyzeSourcingGaps,
  draftSourcingInquiry,
  evaluateSourcing,
} from "../api/client";

describe("Sourcing Routing & Engine Integration Tests", () => {
  describe("Router Integration", () => {
    it("parses #/sourcing route correctly", () => {
      expect(parseRoute("#/sourcing")).toEqual({ name: "sourcing", listingId: undefined });
      expect(parseRoute("#/sourcing/")).toEqual({ name: "sourcing", listingId: undefined });
    });

    it("parses #/sourcing with listingId query parameter", () => {
      const route = parseRoute("#/sourcing?listingId=listing-123");
      expect(route).toEqual({ name: "sourcing", listingId: "listing-123" });
    });

    it("generates correct sourcingPath and navigates to sourcing", () => {
      expect(sourcingPath()).toBe("#/sourcing");
      expect(sourcingPath("listing-456")).toBe("#/sourcing?listingId=listing-456");

      navigateToSourcing("listing-789");
      expect(window.location.hash).toBe("#/sourcing?listingId=listing-789");
    });
  });

  describe("Sourcing Engine Unit Verification", () => {
    it("interprets natural language requirement prompts accurately", () => {
      const parsed = interpretPrompt(
        "Need 5,000 meters of flame retardant nomex protective fabric delivered to London by Dec 15, max price $15.00/m CIF"
      );
      expect(parsed.category).toBe("Textiles");
      expect(parsed.quantity.target_quantity).toBe("5000");
      expect(parsed.quantity.unit).toBe("meters");
      expect(parsed.delivery.destination_country_code).toBe("GB");
      expect(parsed.commercial_terms.preferred_incoterm).toBe("CIF");
    });

    it("evaluates candidate listings producing scores and attribute comparisons", () => {
      const berlinListing = BUNDLED_MARKETPLACE_LISTING_DETAILS[0];
      const requirements = interpretPrompt("1000 boxes of M8 Grade 316 stainless steel bolts to Berlin, max $14.00 DDP");
      const result = evaluateCandidateListing(berlinListing, requirements);

      expect(result.listing_id).toBe(berlinListing.id);
      expect(result.match_tier).toBe("A");
      expect(result.composite_score).toBeGreaterThanOrEqual(90);
      expect(result.gaps).toHaveLength(0);
      expect(result.attribute_matrix.length).toBeGreaterThanOrEqual(4);
    });

    it("identifies commercial gaps for non-compliant listings", () => {
      const balticListing = BUNDLED_MARKETPLACE_LISTING_DETAILS[2]; // Baltic has 5000 MOQ
      const requirements = interpretPrompt("1000 boxes of M8 bolts, max $14.00");
      const result = evaluateCandidateListing(balticListing, requirements);

      expect(result.gaps.some((g) => g.field_name === "moq")).toBe(true);
      const moqGap = result.gaps.find((g) => g.field_name === "moq");
      expect(moqGap?.category).toBe("NON_COMPLIANT");
      expect(moqGap?.severity).toBe("CRITICAL");
    });

    it("rescores candidates when buyer changes budget ceiling", () => {
      const rescored = rescoreCandidatesWithOverrides(MOCK_BUNDLED_LISTINGS, 10.0);
      // Candidates priced > $10 should be downgraded to Tier D
      const berlin = rescored.find((c) => c.listing_id === "00000000-0000-4000-8000-000000000101");
      expect(berlin?.match_tier).toBe("D");
    });

    it("drafts seller inquiry letters addressing candidate and detected gaps", () => {
      const candidate = MOCK_BUNDLED_LISTINGS[3]; // Baltic with MOQ gap
      const inquiry = draftSellerInquiry(candidate, "1000", "boxes");

      expect(inquiry.subject).toContain("Industrial Marine-Grade A4-80 Bolts & Studs");
      expect(inquiry.body).toContain("Baltic Fastener Works");
      expect(inquiry.body).toContain("MOQ");
    });
  });

  describe("Sourcing API Client Endpoint Methods", () => {
    it("exports all 6 API client methods", () => {
      expect(typeof interpretSourcingRequirements).toBe("function");
      expect(typeof getSourcingListings).toBe("function");
      expect(typeof compareSourcingListings).toBe("function");
      expect(typeof analyzeSourcingGaps).toBe("function");
      expect(typeof draftSourcingInquiry).toBe("function");
      expect(typeof evaluateSourcing).toBe("function");
    });
  });
});
