import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("./api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api/client")>();
  return {
    ...actual,
    apiRequest: vi.fn(),
    login: vi.fn(),
    listOrganizations: vi.fn(),
    listPaymentStatuses: vi.fn(),
    getCommercialDocumentDraft: vi.fn(),
    listDeals: vi.fn(),
    createDeal: vi.fn(),
    getDeal: vi.fn(),
    getCurrentAgreement: vi.fn(),
    listDealFacts: vi.fn(),
    listDealMessages: vi.fn(),
  };
});

import {
  ApiError,
  apiRequest,
  getCommercialDocumentDraft,
  getCurrentAgreement,
  getDeal,
  listDealFacts,
  listDealMessages,
  listDeals,
  listOrganizations,
  listPaymentStatuses,
} from "./api/client";
import { clearAccessToken, setAccessToken } from "./api/tokenStore";

const mockedGetDeal = vi.mocked(getDeal);
const mockedApiRequest = vi.mocked(apiRequest);
const mockedGetCurrentAgreement = vi.mocked(getCurrentAgreement);
const mockedListDeals = vi.mocked(listDeals);
const mockedListOrganizations = vi.mocked(listOrganizations);
const mockedListDealFacts = vi.mocked(listDealFacts);
const mockedListDealMessages = vi.mocked(listDealMessages);
const mockedGetCommercialDocumentDraft = vi.mocked(getCommercialDocumentDraft);
const mockedListPaymentStatuses = vi.mocked(listPaymentStatuses);

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearAccessToken();
    window.location.hash = "";
    vi.stubGlobal("confirm", vi.fn(() => true));
    mockedListDeals.mockResolvedValue([]);
    mockedListPaymentStatuses.mockResolvedValue([]);
    mockedGetCommercialDocumentDraft.mockRejectedValue(
      new ApiError(409, "Agreement not committed"),
    );
    mockedListDealFacts.mockResolvedValue([]);
    mockedListDealMessages.mockResolvedValue([]);
    mockedListOrganizations.mockResolvedValue([
      {
        id: "11111111-1111-1111-1111-111111111111",
        legal_name: "Demo Buyer Co",
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
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));

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
    expect(mockedListOrganizations).toHaveBeenCalledTimes(1);
  });

  it("shows the create flow when the create route is requested", async () => {
    setAccessToken("access-token");
    window.location.hash = "#/deals/new";

    render(<App />);

    expect(await screen.findByLabelText("Buyer organization")).toBeInTheDocument();
    expect(mockedListOrganizations).toHaveBeenCalled();
  });

  it("navigates to the organizations settings page when clicking Organizations in the nav", async () => {
    setAccessToken("access-token");

    render(<App />);

    await screen.findByRole("heading", { name: "Deals shared with you" });
    const organizationsLink = screen.getByRole("button", { name: "Organizations" });
    fireEvent.click(organizationsLink);

    expect(window.location.hash).toBe("#/settings/organizations");
    expect(
      await screen.findByRole("heading", { name: "Organization IDs" }),
    ).toBeInTheDocument();
    expect(mockedListOrganizations).toHaveBeenCalledTimes(2);
    expect(organizationsLink).toHaveClass("is-active");
  });

  it("shows the organizations settings page when the settings route is requested directly", async () => {
    setAccessToken("access-token");
    window.location.hash = "#/settings/organizations";

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Organization IDs" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Demo Buyer Co (US)")).toBeInTheDocument();
    expect(mockedListOrganizations).toHaveBeenCalledTimes(2);
  });

  it("handles query parameters on the organizations route gracefully", async () => {
    setAccessToken("access-token");
    window.location.hash = "#/settings/organizations?invited=true";

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Organization IDs" }),
    ).toBeInTheDocument();
  });

  it("returns to the deals workspace after resetting from a deal route", async () => {
    setAccessToken("access-token");
    window.location.hash = "#/deals/deal-42";
    mockedGetDeal.mockResolvedValue({
      id: "deal-42",
      buyer_organization_id: "11111111-1111-1111-1111-111111111111",
      seller_organization_id: "22222222-2222-2222-2222-222222222222",
      status: "DRAFT",
      version: 0,
    });
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));
    mockedApiRequest.mockResolvedValue({ message: "Demo data cleared" });

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "Acting as Buyer" }));
    fireEvent.click(screen.getByRole("button", { name: "Reset Demo Data" }));

    expect(await screen.findByRole("heading", { name: "Deals shared with you" })).toBeInTheDocument();
    expect(window.location.hash).toBe("#/deals");
  });
});
