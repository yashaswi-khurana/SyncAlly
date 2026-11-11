import { act, fireEvent, screen, within } from "@testing-library/react";
import { expect, vi } from "vitest";
import {
  draftSourcingInquiry,
  evaluateSourcing,
  interpretSourcingRequirements,
} from "../api/client";
import { MOCK_BUNDLED_LISTINGS } from "./bundledListings";

export const testRequirements = {
  title: "M8 fasteners",
  category: "Industrial Fasteners",
  description: "M8 fasteners",
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

export function installSourcingMocks() {
  vi.mocked(interpretSourcingRequirements).mockImplementation(async (request) => {
    let requirements = testRequirements;
    const prompt = request.prompt?.toLowerCase() || "";
    if (prompt.includes("coffee")) {
      requirements = {
        ...requirements,
        title: "Certified Organic Arabica Green Coffee Beans",
        category: "Agricultural Commodities",
        quantity: { target_quantity: "500", unit: "bags" },
      };
    } else if (prompt.includes("nitrile")) {
      requirements = {
        ...requirements,
        title: "Nitrile examination gloves",
        category: "Medical Supplies & PPE",
        quantity: { target_quantity: "10000", unit: "boxes" },
      };
    } else if (prompt.includes("wire harness")) {
      requirements = {
        ...requirements,
        title: "Wire harness",
        category: "Electronics & Electrical",
        quantity: { target_quantity: "1000", unit: "units" },
      };
    } else if (prompt.includes("cotton canvas")) {
      requirements = {
        ...requirements,
        title: "Cotton canvas",
        category: "Textiles & Fabrics",
        quantity: { target_quantity: "1000", unit: "yards" },
      };
    }
    return {
      requirements: request.prompt ? requirements : request.structured_overrides,
      parsed_fields: ["title", "quantity"],
      ai_provider: request.prompt ? "openai" : "structured",
      ai_model: request.prompt ? "test-model" : null,
      fallback_reason: null,
    } as never;
  });
  vi.mocked(evaluateSourcing).mockImplementation(async (request) => ({
    requirements: request.requirements,
    comparisons: MOCK_BUNDLED_LISTINGS.map((candidate) => ({
      ...candidate,
      tier: `Tier ${candidate.match_tier}`,
    })),
    inquiries: {},
    total_listings_evaluated: MOCK_BUNDLED_LISTINGS.length,
  }) as never);
  vi.mocked(draftSourcingInquiry).mockImplementation(async (request) => {
    const candidate = MOCK_BUNDLED_LISTINGS.find((item) => item.listing_id === request.listing_id);
    if (!candidate) throw new Error("Listing not found");
    return {
      listing_id: candidate.listing_id,
      seller_organization_name: candidate.seller_organization_name,
      subject: `Commercial Sourcing Inquiry: ${candidate.listing_title} — RFQ`,
      body: [
        `Dear ${candidate.seller_organization_name},`,
        ...candidate.gaps.flatMap((gap) => [gap.explanation, gap.suggested_action]),
      ].join("\n"),
      gaps_addressed: candidate.gaps.map((gap) => gap.field_name),
    };
  });
}

export async function evaluateNaturalRequirements(prompt = "Need 1000 boxes of M8 fasteners") {
  fireEvent.change(screen.getByLabelText(/procurement requirement/i), { target: { value: prompt } });
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /interpret requirements/i }));
  });
  expect(screen.getByText(/review the interpreted requirements before ranking/i)).toBeInTheDocument();
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /confirm requirements and evaluate/i }));
  });
}

export async function openServerInquiry(listingId: string) {
  await act(async () => {
    fireEvent.click(within(screen.getByTestId(`listing-card-${listingId}`)).getByRole("button", {
      name: /draft inquiry/i,
    }));
  });
  expect(screen.getByTestId("inquiry-modal")).toBeInTheDocument();
}
