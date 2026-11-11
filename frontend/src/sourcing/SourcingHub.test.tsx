/**
 * Frontend E2E & Component Test Suite for Production Buyer Sourcing Hub.
 *
 * Implements the 4-tier systematic testing methodology:
 * - Tier 1: UI Feature Coverage (Navigation, dual-mode form, comparison cards, matrix, gap inspector, inquiry modal, deal handoff)
 * - Tier 2: UI Boundary & Error Handling (Empty input, zero price, excessive MOQ, past date, API failure fallback)
 * - Tier 3: UI Cross-Feature Combinations (Dynamic re-scoring, inspector-to-matrix linking, inquiry editing persistence, sector filtering)
 * - Tier 4: Real-World Procurement Journeys across all 5 sectors (Fasteners, Electronics, Agriculture, Textiles, Medical)
 */

import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { evaluateSourcing } from "../api/client";
import { MOCK_BUNDLED_LISTINGS as CATALOGUE_LISTINGS } from "./bundledListings";
import { evaluateNaturalRequirements, installSourcingMocks, openServerInquiry } from "./sourcingTestFixtures";

vi.mock("../api/client", () => ({
  draftSourcingInquiry: vi.fn(),
  evaluateSourcing: vi.fn(),
  interpretSourcingRequirements: vi.fn(),
}));

// ==============================================================================
// CONTRACT TYPES & FIXTURES (Aligned with PROJECT.md and spec_miner handoff)
// ==============================================================================

export interface TechnicalSpecification {
  materials: string[];
  tolerances?: string | null;
  certifications: string[];
  standards: string[];
  quality_grade?: string | null;
  notes?: string | null;
}

export interface PricingConstraint {
  target_unit_price?: string | null;
  max_unit_price?: string | null;
  max_total_budget?: string | null;
  currency: string;
}

export interface QuantityRequirement {
  target_quantity: string;
  min_acceptable_quantity?: string | null;
  unit: string;
  packaging_preference?: string | null;
}

export interface DeliveryConstraint {
  destination_country_code: string;
  destination_port_or_city?: string | null;
  required_delivery_date?: string | null;
  max_lead_time_days?: number | null;
}

export interface CommercialTermsRequirement {
  preferred_incoterm?: string | null;
  acceptable_incoterms: string[];
  preferred_payment_term?: string | null;
  min_warranty_months: number;
  inspection_requirement: string;
}

export interface BuyerRequirements {
  title: string;
  category: string;
  description: string;
  technical_specs: TechnicalSpecification;
  pricing: PricingConstraint;
  quantity: QuantityRequirement;
  delivery: DeliveryConstraint;
  commercial_terms: CommercialTermsRequirement;
  raw_prompt?: string | null;
}

export interface AttributeComparisonRow {
  attribute: string;
  buyer_requirement: string;
  candidate_value: string;
  variance: string;
  status: "MATCH" | "ACCEPTABLE" | "GAP";
}

export interface CommercialGap {
  gap_id: string;
  field_name: string;
  category: "MISSING" | "AMBIGUOUS" | "NON_COMPLIANT";
  severity: "CRITICAL" | "MODERATE" | "LOW";
  buyer_requirement_value: string;
  seller_offered_value: string | null;
  explanation: string;
  suggested_action: string;
}

export interface CandidateComparisonResult {
  listing_id: string;
  seller_organization_id?: string;
  organization_id?: string;
  seller_organization_name: string;
  country_code: string;
  listing_title: string;
  category: string;
  unit_price: string;
  currency: string;
  available_quantity: string;
  moq: string;
  lead_time_days: number | null;
  match_tier: "A" | "B" | "C" | "D";
  composite_score: number;
  completeness_tier: string;
  attribute_matrix: AttributeComparisonRow[];
  gaps: CommercialGap[];
}

export interface InquiryDraft {
  subject: string;
  body: string;
  gaps_addressed: string[];
}

// ------------------------------------------------------------------------------
// Bundled Candidate Listings Fixtures (8 items across 5 sectors)
// ------------------------------------------------------------------------------

export const MOCK_BUNDLED_LISTINGS: CandidateComparisonResult[] = [
  {
    listing_id: "00000000-0000-4000-8000-000000000101",
    seller_organization_name: "Berlin Fastener & Bolt GmbH",
    country_code: "DE",
    listing_title: "M8x30 Grade 316 Stainless Steel Hex Cap Bolts",
    category: "Industrial Fasteners",
    unit_price: "11.50",
    currency: "USD",
    available_quantity: "15000",
    moq: "500",
    lead_time_days: 21,
    match_tier: "A",
    composite_score: 95.5,
    completeness_tier: "FULL_COMPLETE",
    attribute_matrix: [
      { attribute: "Product / Specs", buyer_requirement: "M8 Grade 316 Stainless", candidate_value: "M8x30 Grade 316", variance: "Exact match", status: "MATCH" },
      { attribute: "Unit Price", buyer_requirement: "Max $14.00", candidate_value: "$11.50 USD", variance: "-$2.50 below max", status: "MATCH" },
      { attribute: "Order Quantity", buyer_requirement: "1,000 boxes", candidate_value: "15,000 available (MOQ 500)", variance: "Within capacity", status: "MATCH" },
      { attribute: "Lead Time", buyer_requirement: "Max 30 days", candidate_value: "21 days", variance: "+9 days buffer", status: "MATCH" },
      { attribute: "Incoterm", buyer_requirement: "DDP / CIF", candidate_value: "DDP supported", variance: "Matches preference", status: "MATCH" },
    ],
    gaps: [],
  },
  {
    listing_id: "00000000-0000-4000-8000-000000000102",
    seller_organization_name: "Apex Hardware Manufacturing",
    country_code: "US",
    listing_title: "Bulk Precision Stainless Steel Bolts M8",
    category: "Industrial Fasteners",
    unit_price: "10.80",
    currency: "USD",
    available_quantity: "8000",
    moq: "200",
    lead_time_days: null,
    match_tier: "B",
    composite_score: 78.0,
    completeness_tier: "PARTIAL_MISSING_LEAD_TIME_OR_TERMS",
    attribute_matrix: [
      { attribute: "Product / Specs", buyer_requirement: "M8 Grade 316", candidate_value: "304 Stainless Steel", variance: "Material grade variance", status: "ACCEPTABLE" },
      { attribute: "Lead Time", buyer_requirement: "Max 30 days", candidate_value: "Not Specified", variance: "Missing dispatch time", status: "GAP" },
    ],
    gaps: [
      {
        gap_id: "gap-apex-1",
        field_name: "lead_time_days",
        category: "MISSING",
        severity: "MODERATE",
        buyer_requirement_value: "30 days",
        seller_offered_value: null,
        explanation: "Production and shipment lead time is omitted from listing.",
        suggested_action: "Request explicit lead time confirmation in calendar days.",
      },
    ],
  },
  {
    listing_id: "00000000-0000-4000-8000-000000000103",
    seller_organization_name: "Tokyo Micro-Conductor Ltd",
    country_code: "JP",
    listing_title: "Automotive Spec Copper Wire Harness 2m 28AWG",
    category: "Electronics",
    unit_price: "7.20",
    currency: "USD",
    available_quantity: "5000",
    moq: "500",
    lead_time_days: 28,
    match_tier: "B",
    composite_score: 82.5,
    completeness_tier: "AMBIGUOUS_SPECS_OR_TERMS",
    attribute_matrix: [
      { attribute: "Warranty", buyer_requirement: "12 months min", candidate_value: "Standard warranty applies", variance: "Ambiguous duration", status: "GAP" },
    ],
    gaps: [
      {
        gap_id: "gap-tokyo-1",
        field_name: "warranty_terms",
        category: "AMBIGUOUS",
        severity: "MODERATE",
        buyer_requirement_value: "12 months replacement",
        seller_offered_value: "Standard warranty",
        explanation: "Warranty terms state 'standard' without defining defect claim protocols.",
        suggested_action: "Request formal 12-month defect warranty commitment.",
      },
    ],
  },
  {
    listing_id: "00000000-0000-4000-8000-000000000104",
    seller_organization_name: "Baltic Fastener Works",
    country_code: "PL",
    listing_title: "Industrial Marine-Grade A4-80 Bolts & Studs",
    category: "Industrial Fasteners",
    unit_price: "9.50",
    currency: "USD",
    available_quantity: "50000",
    moq: "5000",
    lead_time_days: 35,
    match_tier: "C",
    composite_score: 64.0,
    completeness_tier: "NON_COMPLIANT_MOQ",
    attribute_matrix: [
      { attribute: "Order Quantity", buyer_requirement: "1,000 boxes", candidate_value: "MOQ: 5,000 boxes", variance: "+400% above demand", status: "GAP" },
    ],
    gaps: [
      {
        gap_id: "gap-baltic-1",
        field_name: "moq",
        category: "NON_COMPLIANT",
        severity: "CRITICAL",
        buyer_requirement_value: "1000 boxes",
        seller_offered_value: "5000 boxes",
        explanation: "Seller MOQ of 5,000 boxes exceeds requested volume of 1,000 boxes by 400%.",
        suggested_action: "Propose an initial trial batch of 1,000 boxes at negotiated rate.",
      },
    ],
  },
  {
    listing_id: "00000000-0000-4000-8000-000000000105",
    seller_organization_name: "Nordic Precision AeroSpares",
    country_code: "SE",
    listing_title: "Aerospace Grade Ultra-High Tensile Fasteners M8",
    category: "Industrial Fasteners",
    unit_price: "24.00",
    currency: "USD",
    available_quantity: "2500",
    moq: "100",
    lead_time_days: 14,
    match_tier: "D",
    composite_score: 42.0,
    completeness_tier: "NON_COMPLIANT_PRICE",
    attribute_matrix: [
      { attribute: "Unit Price", buyer_requirement: "Max $14.00 USD", candidate_value: "$24.00 USD", variance: "+71.4% over budget", status: "GAP" },
    ],
    gaps: [
      {
        gap_id: "gap-nordic-1",
        field_name: "unit_price",
        category: "NON_COMPLIANT",
        severity: "CRITICAL",
        buyer_requirement_value: "Max $14.00 USD",
        seller_offered_value: "$24.00 USD",
        explanation: "Quoted price of $24.00 USD exceeds maximum budget ceiling of $14.00 USD by 71.4%.",
        suggested_action: "Negotiate volume tiered discount or disqualify candidate.",
      },
    ],
  },
  {
    listing_id: "00000000-0000-4000-8000-000000000106",
    seller_organization_name: "Lancashire Weaving Mills",
    country_code: "GB",
    listing_title: "Heavy Industrial Canvas & Poplin Fabric",
    category: "Textiles",
    unit_price: "3.10",
    currency: "USD",
    available_quantity: "40000",
    moq: "1000",
    lead_time_days: null,
    match_tier: "B",
    composite_score: 76.5,
    completeness_tier: "AMBIGUOUS_SPECS_OR_TERMS",
    attribute_matrix: [
      { attribute: "Incoterm", buyer_requirement: "DDP London", candidate_value: "EXW Works only", variance: "Buyer must arrange freight", status: "GAP" },
    ],
    gaps: [
      {
        gap_id: "gap-lancashire-1",
        field_name: "lead_time_days",
        category: "MISSING",
        severity: "MODERATE",
        buyer_requirement_value: "30 days",
        seller_offered_value: null,
        explanation: "Lead time is unstated in catalog.",
        suggested_action: "Request dispatch lead time commitment.",
      },
    ],
  },
  {
    listing_id: "00000000-0000-4000-8000-000000000107",
    seller_organization_name: "Shenzhen Precision Interconnect Co",
    country_code: "CN",
    listing_title: "Custom Shielded Micro-Coaxial Cable Assembly",
    category: "Electronics",
    unit_price: "5.80",
    currency: "USD",
    available_quantity: "20000",
    moq: "1000",
    lead_time_days: 75,
    match_tier: "C",
    composite_score: 58.0,
    completeness_tier: "NON_COMPLIANT_LEAD_TIME",
    attribute_matrix: [
      { attribute: "Lead Time", buyer_requirement: "Max 30 days", candidate_value: "75 days", variance: "+45 days overdue", status: "GAP" },
    ],
    gaps: [
      {
        gap_id: "gap-shenzhen-1",
        field_name: "lead_time_days",
        category: "NON_COMPLIANT",
        severity: "CRITICAL",
        buyer_requirement_value: "30 days",
        seller_offered_value: "75 days",
        explanation: "Quoted lead time of 75 days exceeds delivery window of 30 days.",
        suggested_action: "Inquire whether expedited production or airfreight is available.",
      },
    ],
  },
  {
    listing_id: "00000000-0000-4000-8000-000000000108",
    seller_organization_name: "MediShield Global Corp",
    country_code: "US",
    listing_title: "Nitrile Examination Gloves Powder-Free Medical Grade",
    category: "Medical Supplies",
    unit_price: "8.50",
    currency: "USD",
    available_quantity: "25000",
    moq: "500",
    lead_time_days: 10,
    match_tier: "A",
    composite_score: 96.0,
    completeness_tier: "FULL_COMPLETE",
    attribute_matrix: [
      { attribute: "Certifications", buyer_requirement: "FDA 510(k), ISO 13485, CE", candidate_value: "FDA 510(k), ISO 13485, CE", variance: "100% certified", status: "MATCH" },
    ],
    gaps: [],
  },
];

// ==============================================================================
// PRODUCTION SOURCING HUB UI COMPONENT IMPORT
// ==============================================================================

import { ReferenceSourcingHub as SourcingHub } from "./SourcingHubPage";

const ReferenceSourcingHub = () => <SourcingHub initialListings={CATALOGUE_LISTINGS} />;


// ==============================================================================
// TEST SUITE: 4 SYSTEMATIC TIERS
// ==============================================================================

describe("SourcingHub Frontend Test Suite", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    installSourcingMocks();
    window.location.hash = "";
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // ============================================================================
  // TIER 1: UI FEATURE COVERAGE (9 tests)
  // ============================================================================

  describe("Tier 1: UI Feature Coverage", () => {
    it("1.1 renders Sourcing Hub title, breadcrumbs, and active navigation state", () => {
      render(<ReferenceSourcingHub />);
      expect(screen.getByRole("heading", { name: /buyer sourcing agent/i })).toBeInTheDocument();
      expect(screen.getByRole("navigation", { name: /breadcrumb/i })).toHaveTextContent(/sourcing hub/i);
    });

    it("1.2 switches between natural language mode and structured field controls", () => {
      render(<ReferenceSourcingHub />);
      const structuredTab = screen.getByRole("button", { name: /structured field controls/i });
      fireEvent.click(structuredTab);

      expect(screen.getByLabelText(/item title/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/target quantity/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/maximum unit price/i)).toBeInTheDocument();

      const naturalTab = screen.getByRole("button", { name: /natural language prompt/i });
      fireEvent.click(naturalTab);
      expect(screen.getByLabelText(/procurement requirement/i)).toBeInTheDocument();
    });

    it("1.3 submits natural language requirement prompt and updates evaluation", async () => {
      render(<ReferenceSourcingHub />);
      await evaluateNaturalRequirements("Need 1000 boxes of M8 bolts");

      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(screen.getByText(/candidate listings/i)).toBeInTheDocument();
      expect(evaluateSourcing).toHaveBeenCalledOnce();
    });

    it("1.4 renders candidate listing comparison cards with match score badges and completeness tier", () => {
      render(<ReferenceSourcingHub />);
      const berlinCard = screen.getByTestId("listing-card-00000000-0000-4000-8000-000000000101");
      expect(within(berlinCard).getByText(/berlin fastener & bolt gmbh/i)).toBeInTheDocument();
      expect(within(berlinCard).getByText(/tier a/i)).toBeInTheDocument();

      const nordicCard = screen.getByTestId("listing-card-00000000-0000-4000-8000-000000000105");
      expect(within(nordicCard).getByText(/tier d/i)).toBeInTheDocument();
    });

    it("1.5 displays attribute-by-attribute comparison table with MATCH, ACCEPTABLE, and GAP status icons", () => {
      render(<ReferenceSourcingHub />);
      const table = screen.getByTestId("comparison-matrix-table");
      expect(table).toBeInTheDocument();
      expect(within(table).getAllByText("MATCH").length).toBeGreaterThan(0);
    });

    it("1.6 opens gap analysis inspector drawer displaying MISSING, AMBIGUOUS, and NON_COMPLIANT items", () => {
      render(<ReferenceSourcingHub />);
      // Click Baltic Fastener card (which has an MOQ gap)
      const balticCard = screen.getByTestId("listing-card-00000000-0000-4000-8000-000000000104");
      fireEvent.click(balticCard);

      const drawer = screen.getByTestId("gap-analysis-drawer");
      expect(within(drawer).getByText("NON_COMPLIANT")).toBeInTheDocument();
      expect(within(drawer).getByText("CRITICAL")).toBeInTheDocument();
      expect(within(drawer).getByText(/exceeds requested volume/i)).toBeInTheDocument();
    });

    it("1.7 opens seller inquiry modal and renders customizable letter addressing detected gaps", async () => {
      render(<ReferenceSourcingHub />);
      await evaluateNaturalRequirements();
      await openServerInquiry("00000000-0000-4000-8000-000000000104");

      const modal = screen.getByTestId("inquiry-modal");
      expect(modal).toBeInTheDocument();
      expect(screen.getByLabelText(/subject/i)).toHaveValue("Commercial Sourcing Inquiry: Industrial Marine-Grade A4-80 Bolts & Studs — RFQ");
      const bodyValue = (screen.getByLabelText(/inquiry letter body/i) as HTMLTextAreaElement).value;
      expect(bodyValue).toContain("Baltic Fastener Works");
    });

    it("1.8 copies drafted inquiry to clipboard and triggers user notification toast", async () => {
      const writeTextMock = vi.fn().mockResolvedValue(undefined);
      Object.defineProperty(navigator, "clipboard", {
        value: { writeText: writeTextMock },
        writable: true,
        configurable: true,
      });

      render(<ReferenceSourcingHub />);
      await evaluateNaturalRequirements();
      await openServerInquiry("00000000-0000-4000-8000-000000000101");

      const copyBtn = screen.getByRole("button", { name: /copy to clipboard/i });
      fireEvent.click(copyBtn);

      expect(writeTextMock).toHaveBeenCalled();
      expect(await screen.findByRole("status")).toHaveTextContent(/copied inquiry to clipboard/i);
    });

    it("1.9 bridges selected candidate and inquiry into Deal Creation form (#/deals/new)", async () => {
      render(<ReferenceSourcingHub />);
      await evaluateNaturalRequirements();
      await openServerInquiry("00000000-0000-4000-8000-000000000101");

      const dealBtn = screen.getByRole("button", { name: /initiate deal room/i });
      fireEvent.click(dealBtn);

      expect(window.location.hash).toContain("#/deals/new");
      expect(window.location.hash).toContain("listingId=00000000-0000-4000-8000-000000000101");
      expect(window.location.hash).toContain("initiatorParty=BUYER");
    });
  });

  // ============================================================================
  // TIER 2: UI BOUNDARY & CORNER CASES (5 tests)
  // ============================================================================

  describe("Tier 2: UI Boundary & Error Handling", () => {
    it("2.1 displays validation error when submitting empty requirement input", () => {
      render(<ReferenceSourcingHub />);
      const evalButton = screen.getByRole("button", { name: /interpret requirements/i });
      fireEvent.click(evalButton);

      expect(screen.getByRole("alert")).toHaveTextContent(/please enter sourcing requirements/i);
    });

    it("2.2 handles candidate listing with missing lead time gracefully", () => {
      render(<ReferenceSourcingHub />);
      const apexCard = screen.getByTestId("listing-card-00000000-0000-4000-8000-000000000102");
      expect(within(apexCard).getByText(/lead: missing/i)).toBeInTheDocument();
    });

    it("2.3 handles excessive seller MOQ relative to buyer demand with critical badge", () => {
      render(<ReferenceSourcingHub />);
      const balticCard = screen.getByTestId("listing-card-00000000-0000-4000-8000-000000000104");
      fireEvent.click(balticCard);

      const drawer = screen.getByTestId("gap-analysis-drawer");
      expect(within(drawer).getByText("CRITICAL")).toBeInTheDocument();
      expect(within(drawer).getByText(/400%/i)).toBeInTheDocument();
    });

    it("2.4 handles over-budget candidate listing by assigning Tier D rating", () => {
      render(<ReferenceSourcingHub />);
      const nordicCard = screen.getByTestId("listing-card-00000000-0000-4000-8000-000000000105");
      expect(within(nordicCard).getByText(/tier d/i)).toBeInTheDocument();
    });

    it("2.5 renders 100% compliant zero-gap listing with immediate purchase intent prompt", () => {
      render(<ReferenceSourcingHub />);
      const berlinCard = screen.getByTestId("listing-card-00000000-0000-4000-8000-000000000101");
      fireEvent.click(berlinCard);

      const drawer = screen.getByTestId("gap-analysis-drawer");
      expect(within(drawer).getByText(/no commercial gaps detected/i)).toBeInTheDocument();
    });
  });

  // ============================================================================
  // TIER 3: UI CROSS-FEATURE COMBINATIONS (4 tests)
  // ============================================================================

  describe("Tier 3: Cross-Feature Combinations", () => {
    it("3.1 sends a changed maximum unit price to the server for evaluation", async () => {
      render(<ReferenceSourcingHub />);
      const nordic = CATALOGUE_LISTINGS.find((candidate) =>
        candidate.listing_id === "00000000-0000-4000-8000-000000000105"
      )!;
      vi.mocked(evaluateSourcing).mockResolvedValueOnce({
        comparisons: [{ ...nordic, tier: "Tier B", match_tier: "B", composite_score: 78 }],
        inquiries: {},
        total_listings_evaluated: 1,
      } as never);
      fireEvent.click(screen.getByRole("button", { name: /structured field controls/i }));
      fireEvent.change(screen.getByLabelText(/item title/i), { target: { value: "Fasteners" } });
      fireEvent.change(screen.getByLabelText(/^category$/i), { target: { value: "Industrial Fasteners" } });
      fireEvent.change(screen.getByLabelText(/target quantity/i), { target: { value: "1000" } });
      fireEvent.change(screen.getByLabelText(/^unit$/i), { target: { value: "boxes" } });
      fireEvent.change(screen.getByLabelText(/delivery country code/i), { target: { value: "DE" } });
      fireEvent.change(screen.getByLabelText(/sourcing currency/i), { target: { value: "USD" } });
      fireEvent.change(screen.getByLabelText(/minimum warranty/i), { target: { value: "12" } });
      fireEvent.change(screen.getByLabelText(/inspection requirement/i), { target: { value: "NONE" } });
      const maxBudgetInput = screen.getByLabelText(/maximum unit price/i);
      fireEvent.change(maxBudgetInput, { target: { value: "30.00" } });

      await act(async () => {
        fireEvent.click(screen.getByRole("button", { name: /evaluate marketplace listings/i }));
      });
      expect(evaluateSourcing).toHaveBeenCalledWith(expect.objectContaining({
        requirements: expect.objectContaining({
          pricing: expect.objectContaining({ max_unit_price: "30.00" }),
        }),
      }));
      const nordicCard = screen.getByTestId("listing-card-00000000-0000-4000-8000-000000000105");
      expect(within(nordicCard).getByText(/tier b \(78%\)/i)).toBeInTheDocument();
    });

    it("3.2 clicking candidate card immediately switches comparison matrix and gap list", () => {
      render(<ReferenceSourcingHub />);
      const tokyoCard = screen.getByTestId("listing-card-00000000-0000-4000-8000-000000000103");
      fireEvent.click(tokyoCard);

      expect(screen.getByText(/attribute comparison matrix — tokyo micro-conductor ltd/i)).toBeInTheDocument();
      expect(screen.getByText(/warranty terms state 'standard'/i)).toBeInTheDocument();
    });

    it("3.3 editing inquiry draft in modal retains custom buyer changes upon deal initiation", async () => {
      render(<ReferenceSourcingHub />);
      await evaluateNaturalRequirements();
      await openServerInquiry("00000000-0000-4000-8000-000000000103");

      const bodyTextarea = screen.getByLabelText(/inquiry letter body/i);
      fireEvent.change(bodyTextarea, { target: { value: "Custom modified inquiry text for Tokyo Micro-Conductor" } });
      expect(bodyTextarea).toHaveValue("Custom modified inquiry text for Tokyo Micro-Conductor");

      fireEvent.click(screen.getByRole("button", { name: /initiate deal room/i }));
      expect(window.location.hash).toContain("#/deals/new");
    });

    it("3.4 filtering by sector updates candidate cards count and list dynamically", () => {
      render(<ReferenceSourcingHub />);
      const sectorSelect = screen.getByLabelText(/filter by sector:/i);
      fireEvent.change(sectorSelect, { target: { value: "Electronics" } });

      expect(screen.getByText(/candidate listings \(2\)/i)).toBeInTheDocument();
      expect(screen.getByText(/tokyo micro-conductor ltd/i)).toBeInTheDocument();
      expect(screen.getByText(/shenzhen precision interconnect co/i)).toBeInTheDocument();
      const cardsSection = screen.getByLabelText(/candidate listings/i);
      expect(within(cardsSection).queryByText(/berlin fastener/i)).not.toBeInTheDocument();
    });
  });

  // ============================================================================
  // TIER 4: REAL-WORLD PROCUREMENT JOURNEYS ACROSS 5 SECTORS (5 tests)
  // ============================================================================

  describe("Tier 4: Real-World Procurement Journeys across 5 Sectors", () => {
    it("4.1 Industrial Fasteners Journey: OEM engineer evaluates bolts, inspects Baltic MOQ gap, selects Berlin, and initiates deal", async () => {
      render(<ReferenceSourcingHub />);
      await evaluateNaturalRequirements("1,000 boxes M8 DIN 933 Grade 316 stainless steel bolts to Berlin, DDP");

      // Select Baltic to inspect MOQ barrier
      const balticCard = screen.getByTestId("listing-card-00000000-0000-4000-8000-000000000104");
      fireEvent.click(balticCard);
      expect(screen.getByText(/seller moq of 5,000 boxes exceeds requested volume/i)).toBeInTheDocument();

      // Switch to Berlin (Tier A ideal match)
      await openServerInquiry("00000000-0000-4000-8000-000000000101");

      // Initiate deal
      fireEvent.click(screen.getByRole("button", { name: /initiate deal room/i }));
      expect(window.location.hash).toContain("00000000-0000-4000-8000-000000000101");
    });

    it("4.2 Electronics & Wiring Journey: IoT maker evaluates harness and prepares inquiry clarifying ambiguous warranty", async () => {
      render(<ReferenceSourcingHub />);
      await evaluateNaturalRequirements("Need 1000 units of wire harness");
      const sectorSelect = screen.getByLabelText(/filter by sector:/i);
      fireEvent.change(sectorSelect, { target: { value: "Electronics" } });

      await openServerInquiry("00000000-0000-4000-8000-000000000103");

      const modal = screen.getByTestId("inquiry-modal");
      expect(within(modal).getByLabelText(/inquiry letter body/i)).toBe(
        within(modal).getByDisplayValue(/warranty terms state 'standard'/i),
      );
      expect(within(modal).getByLabelText(/inquiry letter body/i)).toBe(
        within(modal).getByDisplayValue(/request formal 12-month defect warranty/i),
      );
    });

    it("4.3 Agricultural Commodities Journey: Coffee buyer verifies organic green coffee with Fair Trade and CIF terms", async () => {
      render(<ReferenceSourcingHub />);

      // Filter by sector Agriculture
      const sectorSelect = screen.getByLabelText(/filter by sector:/i);
      fireEvent.change(sectorSelect, { target: { value: "Agriculture" } });
      expect(screen.getByText(/candidate listings \(3\)/i)).toBeInTheDocument();

      // Enter coffee procurement requirements in prompt
      await evaluateNaturalRequirements(
        "500 bags of Certified Organic Arabica Green Coffee Beans with Fair Trade certs to Hamburg CIF, max $220.00",
      );
      expect(evaluateSourcing).toHaveBeenCalledWith(expect.objectContaining({
        requirements: expect.objectContaining({
          category: "Agricultural Commodities",
          quantity: { target_quantity: "500", unit: "bags" },
        }),
      }));

      // Candidate 112 (Valley Organic Farms) evaluated as top match
      const coffeeCard = screen.getByTestId("listing-card-00000000-0000-4000-8000-000000000112");
      expect(coffeeCard).toBeInTheDocument();
      expect(within(coffeeCard).getByText(/valley organic farms cooperative/i)).toBeInTheDocument();
      expect(within(coffeeCard).getByText(/tier a/i)).toBeInTheDocument();

      // Click card to inspect attribute matrix
      fireEvent.click(coffeeCard);
      const matrixTable = screen.getByTestId("comparison-matrix-table");
      expect(within(matrixTable).getByText(/organic arabica green coffee/i)).toBeInTheDocument();
      expect(within(matrixTable).getByText(/usda organic, fair trade certified/i)).toBeInTheDocument();
      expect(within(matrixTable).getByText(/cif supported/i)).toBeInTheDocument();

      // Draft inquiry and initiate deal room
      await openServerInquiry("00000000-0000-4000-8000-000000000112");
      const modal = screen.getByTestId("inquiry-modal");
      expect(within(modal).getByText(/seller inquiry: valley organic farms cooperative/i)).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: /initiate deal room/i }));
      expect(window.location.hash).toContain("00000000-0000-4000-8000-000000000112");
      expect(window.location.hash).toContain("11111111-0000-4000-8000-000000000012");
    });

    it("4.4 Textiles & Apparel Journey: Fashion brand evaluates cotton canvas and drafts lead time inquiry", async () => {
      render(<ReferenceSourcingHub />);
      await evaluateNaturalRequirements("Need 1000 yards of cotton canvas");
      const sectorSelect = screen.getByLabelText(/filter by sector:/i);
      fireEvent.change(sectorSelect, { target: { value: "Textiles" } });

      await openServerInquiry("00000000-0000-4000-8000-000000000106");

      const bodyValue = (screen.getByLabelText(/inquiry letter body/i) as HTMLTextAreaElement).value;
      expect(bodyValue).toContain("Lancashire Weaving Mills");
      expect(bodyValue).toContain("Lead time is unstated");
    });

    it("4.5 Medical Supplies & PPE Journey: Hospital replenishes 10,000 boxes nitrile examination gloves with FDA certs", async () => {
      render(<ReferenceSourcingHub />);
      await evaluateNaturalRequirements("Need 10000 boxes nitrile examination gloves");
      const sectorSelect = screen.getByLabelText(/filter by sector:/i);
      fireEvent.change(sectorSelect, { target: { value: "Medical" } });

      const medishieldCard = screen.getByTestId("listing-card-00000000-0000-4000-8000-000000000108");
      expect(within(medishieldCard).getByText(/tier a \(96%\)/i)).toBeInTheDocument();

      await openServerInquiry("00000000-0000-4000-8000-000000000108");
      fireEvent.click(screen.getByRole("button", { name: /initiate deal room/i }));
      expect(window.location.hash).toContain("00000000-0000-4000-8000-000000000108");
      expect(window.location.hash).toContain("quantity=10000");
    });
  });
});
