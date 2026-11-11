import { expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SourcingHubPage } from "./SourcingHubPage";
import { MOCK_BUNDLED_LISTINGS } from "./bundledListings";

vi.mock("../api/client", () => ({
  draftSourcingInquiry: vi.fn(),
  evaluateSourcing: vi.fn(),
  interpretSourcingRequirements: vi.fn(),
}));

it("shows an actionable unavailable state instead of sample suppliers", () => {
  render(<SourcingHubPage />);
  expect(screen.getByText(/comparison unavailable/i)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /browse marketplace/i })).toHaveAttribute("href", "#/marketplace");
  expect(screen.queryByText(MOCK_BUNDLED_LISTINGS[0].seller_organization_name)).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /draft inquiry/i })).not.toBeInTheDocument();
});

it("labels explicitly injected test fixtures as unverified", () => {
  render(<SourcingHubPage initialListings={MOCK_BUNDLED_LISTINGS} />);
  expect(screen.getByText(/bundled sample suppliers and listing data are not verified/i)).toBeInTheDocument();
});
