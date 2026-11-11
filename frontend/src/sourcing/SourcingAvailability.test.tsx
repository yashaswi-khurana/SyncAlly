import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getMarketplaceListing, interpretSourcingRequirements, searchMarketplaceListings } from "../api/client";
import type { InterpretSourcingResponse, MarketplaceListing } from "../api/types";
import { SourcingHubPage } from "./SourcingHubPage";

vi.mock("../api/client", () => ({
  getMarketplaceListing: vi.fn(),
  interpretSourcingRequirements: vi.fn(),
  searchMarketplaceListings: vi.fn(),
  draftSourcingInquiry: vi.fn(),
  evaluateSourcing: vi.fn(),
}));

const offer: MarketplaceListing = {
  id: "listing-1", organization_id: "seller-1", organization_name: "Real Supplier",
  country_code: "DE", title: "Steel bolts", description: "Seller's offer", category: "Hardware",
  available_quantity: "300", unit: "boxes", unit_price: "12.5", currency: "EUR",
};

const interpretation: InterpretSourcingResponse = {
  ai_provider: "openai", ai_model: "test-model", parsed_fields: ["title"],
  requirements: {
    title: "Steel bolts", category: "Hardware", description: "",
    technical_specs: { materials: ["steel"], certifications: [], standards: [] },
    pricing: { currency: "EUR", target_unit_price: "12" },
    quantity: { target_quantity: "100", unit: "boxes" },
    delivery: { destination_country_code: "DE" },
    commercial_terms: { acceptable_incoterms: [], min_warranty_months: 12, inspection_requirement: "NONE" },
  },
};

describe("live sourcing", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    window.location.hash = "";
    vi.mocked(searchMarketplaceListings).mockResolvedValue([offer]);
  });

  it("browses and compares real offers and starts a deal with the selected seller", async () => {
    render(<SourcingHubPage organizations={[{ id: "buyer-1" }]} />);
    expect(await screen.findByRole("heading", { name: "Steel bolts" })).toBeInTheDocument();
    expect(searchMarketplaceListings).toHaveBeenCalledWith(
      { q: undefined }, expect.objectContaining({ limit: 25, offset: 0 }),
    );
    fireEvent.click(screen.getByRole("checkbox", { name: /compare steel bolts from real supplier/i }));
    const comparison = screen.getByRole("region", { name: "Offer comparison" });
    expect(within(comparison).getByText(/12.5 EUR \/ boxes/)).toBeInTheDocument();
    expect(within(comparison).getByText(/not structured listing fields/i)).toBeInTheDocument();
    expect(within(comparison).queryByText(/match score:|% match/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Start a deal" }));
    expect(window.location.hash).toContain("sellerId=seller-1");
    expect(window.location.hash).toContain("listingId=listing-1");
  });

  it("reviews AI interpretation before searching with an editable keyword", async () => {
    vi.mocked(interpretSourcingRequirements).mockResolvedValue(interpretation);
    render(<SourcingHubPage />);
    await screen.findByRole("heading", { name: "Steel bolts" });
    fireEvent.change(screen.getByLabelText("What are you looking for?"), { target: { value: "Find steel bolts" } });
    fireEvent.click(screen.getByRole("button", { name: "Interpret requirements" }));
    expect(await screen.findByRole("region", { name: "Review interpreted requirements" })).toHaveTextContent("openai");
    expect(screen.getByLabelText("Product or keyword")).toHaveValue("Steel bolts");
    expect(searchMarketplaceListings).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("checkbox", { name: /compare steel bolts from real supplier/i }));
    expect(screen.getByRole("region", { name: "Offer comparison" })).toHaveTextContent("100 boxes");
    expect(screen.getByRole("region", { name: "Offer comparison" })).toHaveTextContent("12 EUR / boxes");
    fireEvent.change(screen.getByLabelText("Product or keyword"), { target: { value: "bolts" } });
    fireEvent.click(screen.getByRole("button", { name: "Search offers" }));
    await waitFor(() => expect(searchMarketplaceListings).toHaveBeenLastCalledWith(
      { q: "bolts" }, expect.objectContaining({ offset: 0 }),
    ));
    expect(interpretSourcingRequirements).toHaveBeenCalledWith(
      { prompt: "Find steel bolts" }, expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it("discards AI results when the prompt changes during a request", async () => {
    let resolve!: (value: InterpretSourcingResponse) => void;
    vi.mocked(interpretSourcingRequirements).mockReturnValue(new Promise((done) => { resolve = done; }));
    render(<SourcingHubPage />);
    await screen.findByRole("heading", { name: "Steel bolts" });
    const input = screen.getByLabelText("What are you looking for?");
    fireEvent.change(input, { target: { value: "First request" } });
    fireEvent.click(screen.getByRole("button", { name: "Interpret requirements" }));
    fireEvent.change(input, { target: { value: "Changed request" } });
    await act(async () => resolve(interpretation));
    expect(screen.queryByRole("region", { name: "Review interpreted requirements" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Product or keyword")).toHaveValue("");
  });

  it("surfaces provider and listing failures while allowing manual search and retry", async () => {
    vi.mocked(searchMarketplaceListings).mockRejectedValueOnce(new Error("Marketplace unavailable"));
    vi.mocked(interpretSourcingRequirements).mockRejectedValueOnce(new Error("AI is not configured"));
    render(<SourcingHubPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Marketplace unavailable");
    fireEvent.change(screen.getByLabelText("What are you looking for?"), { target: { value: "Need bolts" } });
    fireEvent.click(screen.getByRole("button", { name: "Interpret requirements" }));
    expect(await screen.findByText("AI is not configured")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Search offers" }));
    expect(await screen.findByRole("heading", { name: "Steel bolts" })).toBeInTheDocument();
  });

  it("paginates offers and supports links to listings outside the current page", async () => {
    vi.mocked(searchMarketplaceListings).mockResolvedValueOnce(
      Array.from({ length: 25 }, (_, index) => ({ ...offer, id: `page-${index}` })),
    ).mockResolvedValueOnce([]);
    vi.mocked(getMarketplaceListing).mockResolvedValue({ ...offer, id: "linked", title: "Linked bolts" });
    render(<SourcingHubPage initialListingId="linked" />);
    expect(await screen.findByRole("region", { name: "Linked offer" })).toHaveTextContent("Linked bolts");
    await waitFor(() => expect(screen.getByRole("button", { name: "Next" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(searchMarketplaceListings).toHaveBeenLastCalledWith(
      { q: undefined }, expect.objectContaining({ offset: 25 }),
    ));
    expect(await screen.findByText(/no offers found/i)).toBeInTheDocument();
  });

  it("does not start deals with the user's own organization", async () => {
    render(<SourcingHubPage organizations={[{ id: "seller-1" }]} />);
    await screen.findByRole("heading", { name: "Steel bolts" });
    expect(screen.queryByRole("button", { name: "Start a deal" })).not.toBeInTheDocument();
  });

  it("limits comparison to three offers and allows removing them", async () => {
    vi.mocked(searchMarketplaceListings).mockResolvedValue(
      Array.from({ length: 4 }, (_, index) => ({ ...offer, id: `id-${index}`, title: `Offer ${index}` })),
    );
    render(<SourcingHubPage />);
    await screen.findByRole("heading", { name: "Offer 0" });
    for (let index = 0; index < 3; index += 1) {
      fireEvent.click(screen.getByRole("checkbox", { name: `Compare Offer ${index} from Real Supplier` }));
    }
    const fourth = screen.getByRole("checkbox", { name: "Compare Offer 3 from Real Supplier" });
    expect(fourth).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Remove Offer 0 from Real Supplier from comparison" }));
    expect(fourth).toBeEnabled();
  });
});
