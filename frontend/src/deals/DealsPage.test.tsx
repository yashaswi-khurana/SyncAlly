import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, listDeals, listOrganizations } from "../api/client";
import type { DealSummary, Organization } from "../api/types";
import DealsPage from "./DealsPage";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    listDeals: vi.fn(),
    listOrganizations: vi.fn(),
  };
});

const mockedListDeals = vi.mocked(listDeals);
const mockedListOrganizations = vi.mocked(listOrganizations);

function deal(overrides: Partial<DealSummary> = {}): DealSummary {
  return {
    id: "deal-1",
    buyer_organization_id: "11111111-1111-1111-1111-111111111111",
    seller_organization_id: "22222222-2222-2222-2222-222222222222",
    status: "DRAFT",
    version: 0,
    viewer_role: "BUYER",
    ...overrides,
  };
}

function organization(overrides: Partial<Organization> = {}): Organization {
  return {
    id: "33333333-3333-3333-3333-333333333333",
    legal_name: "Demo Seller Co",
    country_code: "US",
    role: "ADMIN",
    ...overrides,
  };
}

describe("DealsPage", () => {
  beforeEach(() => {
    mockedListOrganizations.mockResolvedValue([organization()]);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("loads and lists the deals shared with the actor", async () => {
    mockedListDeals.mockResolvedValue([deal()]);

    render(<DealsPage onOpenDeal={vi.fn()} onCreateDeal={vi.fn()} />);

    expect(screen.getByText(/loading deals/i)).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "Deals shared with you" }),
    ).toBeInTheDocument();
    expect(mockedListDeals).toHaveBeenCalledTimes(1);
    expect(screen.getByText("You are the buyer")).toBeInTheDocument();
  });

  it("shows the signed-in organization IDs to share", async () => {
    mockedListDeals.mockResolvedValue([]);

    render(<DealsPage onOpenDeal={vi.fn()} onCreateDeal={vi.fn()} />);

    expect(await screen.findByText("Demo Seller Co (US)")).toBeInTheDocument();
    expect(screen.getByText("33333333-3333-3333-3333-333333333333")).toBeInTheDocument();
  });

  it("labels the seller party on a shared deal", async () => {
    mockedListDeals.mockResolvedValue([deal({ viewer_role: "SELLER" })]);

    render(<DealsPage onOpenDeal={vi.fn()} onCreateDeal={vi.fn()} />);

    expect(await screen.findByText("You are the seller")).toBeInTheDocument();
  });

  it("shows an empty state when the actor has no deals", async () => {
    mockedListDeals.mockResolvedValue([]);

    render(<DealsPage onOpenDeal={vi.fn()} onCreateDeal={vi.fn()} />);

    expect(await screen.findByText(/no deals yet/i)).toBeInTheDocument();
  });

  it("shows an error state that can be retried", async () => {
    mockedListDeals.mockRejectedValueOnce(new ApiError(500, "Server error"));

    render(<DealsPage onOpenDeal={vi.fn()} onCreateDeal={vi.fn()} />);

    expect(
      await screen.findByRole("heading", { name: /could not load your deals/i }),
    ).toBeInTheDocument();

    mockedListDeals.mockResolvedValueOnce([deal()]);
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByText("You are the buyer")).toBeInTheDocument();
    expect(mockedListDeals).toHaveBeenCalledTimes(2);
  });

  it("opens a deal and starts a new deal when asked", async () => {
    mockedListDeals.mockResolvedValue([deal()]);
    const onOpenDeal = vi.fn();
    const onCreateDeal = vi.fn();

    render(<DealsPage onOpenDeal={onOpenDeal} onCreateDeal={onCreateDeal} />);
    await screen.findByText("You are the buyer");

    fireEvent.click(screen.getByRole("button", { name: "Open deal" }));
    fireEvent.click(screen.getByRole("button", { name: "New deal" }));

    expect(onOpenDeal).toHaveBeenCalledWith("deal-1");
    expect(onCreateDeal).toHaveBeenCalledTimes(1);
  });
});
