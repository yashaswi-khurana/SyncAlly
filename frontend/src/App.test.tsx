import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("./api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api/client")>();
  return {
    ...actual,
    login: vi.fn(),
    listOrganizations: vi.fn(),
    listDeals: vi.fn(),
    createDeal: vi.fn(),
    getDeal: vi.fn(),
    listDealFacts: vi.fn(),
    listDealMessages: vi.fn(),
  };
});

import { getDeal, listDealFacts, listDealMessages, listDeals, listOrganizations } from "./api/client";
import { clearAccessToken, setAccessToken } from "./api/tokenStore";

const mockedGetDeal = vi.mocked(getDeal);
const mockedListDeals = vi.mocked(listDeals);
const mockedListOrganizations = vi.mocked(listOrganizations);
const mockedListDealFacts = vi.mocked(listDealFacts);
const mockedListDealMessages = vi.mocked(listDealMessages);

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearAccessToken();
    window.location.hash = "";
    mockedListDeals.mockResolvedValue([]);
    mockedListDealFacts.mockResolvedValue([]);
    mockedListDealMessages.mockResolvedValue([]);
    mockedListOrganizations.mockResolvedValue([
      {
        id: "11111111-1111-1111-1111-111111111111",
        legal_name: "Buyer Co",
        country_code: "US",
        role: "ADMIN",
      },
    ]);
  });

  it("asks an unauthenticated visitor to sign in", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { name: "Open your trade desk." }),
    ).toBeInTheDocument();
  });

  it("fetches the deal from the API for the current URL on reload", async () => {
    setAccessToken("access-token");
    window.location.hash = "#/deals/deal-42";
    mockedGetDeal.mockResolvedValue({
      id: "deal-42",
      buyer_organization_id: "11111111-1111-1111-1111-111111111111",
      seller_organization_id: "22222222-2222-2222-2222-222222222222",
      status: "DRAFT",
      version: 0,
    });

    render(<App />);

    expect(await screen.findByText("DRAFT")).toBeInTheDocument();
    expect(mockedGetDeal).toHaveBeenCalledWith("deal-42");
  });

  it("lands a signed-in user on the deals workspace by default", async () => {
    setAccessToken("access-token");

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Deals shared with you" }),
    ).toBeInTheDocument();
    expect(mockedListDeals).toHaveBeenCalledTimes(1);
    expect(mockedListOrganizations).toHaveBeenCalled();
  });

  it("shows the create flow when the create route is requested", async () => {
    setAccessToken("access-token");
    window.location.hash = "#/deals/new";

    render(<App />);

    expect(await screen.findByLabelText("Buyer organization")).toBeInTheDocument();
    expect(mockedListOrganizations).toHaveBeenCalledTimes(1);
  });
});
