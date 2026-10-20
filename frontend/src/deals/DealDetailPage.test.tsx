import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, getCurrentAgreement, getDeal, listDealFacts, listDealMessages, listOrganizations } from "../api/client";
import type { Deal } from "../api/types";
import DealDetailPage from "./DealDetailPage";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    getDeal: vi.fn(),
    getCurrentAgreement: vi.fn(),
    listDealFacts: vi.fn(),
    listDealMessages: vi.fn(),
    listOrganizations: vi.fn(),
  };
});

const mockedGetDeal = vi.mocked(getDeal);
const mockedGetCurrentAgreement = vi.mocked(getCurrentAgreement);
const mockedListDealFacts = vi.mocked(listDealFacts);
const mockedListDealMessages = vi.mocked(listDealMessages);
const mockedListOrganizations = vi.mocked(listOrganizations);

const DEAL: Deal = {
  id: "deal-1",
  buyer_organization_id: "11111111-1111-1111-1111-111111111111",
  seller_organization_id: "22222222-2222-2222-2222-222222222222",
  status: "DRAFT",
  version: 0,
};

describe("DealDetailPage", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  beforeEach(() => {
    mockedListDealFacts.mockResolvedValue([]);
    mockedListDealMessages.mockResolvedValue([]);
    mockedListOrganizations.mockResolvedValue([
      {
        id: DEAL.buyer_organization_id,
        legal_name: "Buyer Co",
        country_code: "US",
        role: "ADMIN",
      },
    ]);
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));
  });

  it("fetches the deal on mount and renders its details", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);

    render(<DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} />);

    expect(screen.getByRole("status")).toHaveTextContent(/loading deal/i);
    expect(await screen.findByText("DRAFT")).toBeInTheDocument();
    expect(mockedGetDeal).toHaveBeenCalledWith("deal-1");
    expect(screen.getByText("deal-1")).toBeInTheDocument();
    expect(screen.getByText(DEAL.buyer_organization_id)).toBeInTheDocument();
    expect(screen.getByText(DEAL.seller_organization_id)).toBeInTheDocument();
  });

  it("shows a not found state for a missing or forbidden deal", async () => {
    mockedGetDeal.mockRejectedValue(new ApiError(404, "Deal not found"));

    render(<DealDetailPage dealId="missing" onBackToDeals={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "Deal not found" })).toBeInTheDocument();
  });

  it("shows an error state that can be retried", async () => {
    mockedGetDeal.mockRejectedValueOnce(new ApiError(500, "Server error"));

    render(<DealDetailPage dealId="deal-1" onBackToDeals={vi.fn()} />);

    expect(
      await screen.findByRole("heading", { name: /could not load this deal/i }),
    ).toBeInTheDocument();

    mockedGetDeal.mockResolvedValueOnce(DEAL);
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByText("DRAFT")).toBeInTheDocument();
    expect(mockedGetDeal).toHaveBeenCalledTimes(2);
  });

  it("navigates back to the deals workspace when asked", async () => {
    mockedGetDeal.mockResolvedValue(DEAL);
    const onBackToDeals = vi.fn();

    render(<DealDetailPage dealId="deal-1" onBackToDeals={onBackToDeals} />);
    await screen.findByText("DRAFT");

    fireEvent.click(screen.getByRole("button", { name: "Back to deals" }));

    expect(onBackToDeals).toHaveBeenCalledTimes(1);
  });
});
