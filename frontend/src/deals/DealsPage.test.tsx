import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, getOrganization, listDeals, listOrganizations } from "../api/client";
import type { DealSummary } from "../api/types";
import DealsPage from "./DealsPage";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    listDeals: vi.fn(),
    listOrganizations: vi.fn(),
    getOrganization: vi.fn().mockRejectedValue(new Error("Unavailable")),
  };
});

const mockedListDeals = vi.mocked(listDeals);
const mockedListOrganizations = vi.mocked(listOrganizations);
const mockedGetOrganization = vi.mocked(getOrganization);

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

describe("DealsPage", () => {
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

  it("does not render organization management panels on the deals workspace", async () => {
    mockedListDeals.mockResolvedValue([]);

    render(<DealsPage onOpenDeal={vi.fn()} onCreateDeal={vi.fn()} />);

    expect(
      await screen.findByRole("heading", { name: "Deals shared with you" }),
    ).toBeInTheDocument();
    expect(mockedListOrganizations).not.toHaveBeenCalled();
    expect(screen.queryByText(/loading your organizations/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Organization IDs" })).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Create an organization" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: /could not load your organizations/i }),
    ).not.toBeInTheDocument();
  });

  it("labels the seller party on a shared deal", async () => {
    mockedListDeals.mockResolvedValue([deal({ viewer_role: "SELLER" })]);

    render(<DealsPage onOpenDeal={vi.fn()} onCreateDeal={vi.fn()} />);

    expect(await screen.findByText("You are the seller")).toBeInTheDocument();
  });

  it("shows the other party to buyers and sellers and keeps both parties identifiable", async () => {
    mockedListDeals.mockResolvedValue([
      deal(), deal({ id: "deal-2", viewer_role: "SELLER" }),
      deal({ id: "deal-3", viewer_role: "BOTH" }),
    ]);
    mockedGetOrganization.mockImplementation(async (id) => ({
      id, legal_name: id.startsWith("111") ? "Buyer Co" : "Seller Co", country_code: "US",
    }));
    render(<DealsPage onOpenDeal={vi.fn()} onCreateDeal={vi.fn()} />);
    expect(await screen.findByText("Trading partner: Seller Co")).toBeInTheDocument();
    expect(screen.getByText("Trading partner: Buyer Co")).toBeInTheDocument();
    expect(screen.getByText("Buyer Co ↔ Seller Co")).toBeInTheDocument();
    expect(mockedGetOrganization).toHaveBeenCalledTimes(2);
  });

  it("does not look up an unclaimed counterparty and still lists deals when lookups fail", async () => {
    mockedListDeals.mockResolvedValue([
      deal({ pending_counterparty: true, seller_organization_id: "unclaimed-shell" }),
      deal({ id: "deal-2" }),
    ]);
    mockedGetOrganization.mockRejectedValue(new ApiError(404, "Organization not found"));
    render(<DealsPage onOpenDeal={vi.fn()} onCreateDeal={vi.fn()} />);
    expect(await screen.findByText("Waiting for trading partner to join")).toBeInTheDocument();
    expect(screen.getByText("Trading partner: Name unavailable")).toBeInTheDocument();
    expect(screen.getByText("Reference: deal-1")).toBeInTheDocument();
    expect(screen.getByText("Reference: deal-2")).toBeInTheDocument();
    expect(mockedGetOrganization).not.toHaveBeenCalledWith("unclaimed-shell");
  });

  it("shows available partner names without waiting for another lookup", async () => {
    mockedListDeals.mockResolvedValue([
      deal(), deal({ id: "deal-2", seller_organization_id: "other-seller" }),
    ]);
    mockedGetOrganization.mockImplementation((id) => id === "other-seller"
      ? new Promise(() => {})
      : Promise.resolve({ id, legal_name: "Seller Co", country_code: "US" }));
    render(<DealsPage onOpenDeal={vi.fn()} onCreateDeal={vi.fn()} />);
    expect(await screen.findByText("Trading partner: Seller Co")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Open deal" })).toHaveLength(2);
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
