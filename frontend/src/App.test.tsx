import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("./api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api/client")>();
  return {
    ...actual,
    apiRequest: vi.fn(),
    login: vi.fn(),
    listOrganizations: vi.fn(),
    createOrganization: vi.fn(),
    listPaymentStatuses: vi.fn(),
    getCommercialDocumentDraft: vi.fn(),
    getTradePack: vi.fn(),
    listDeals: vi.fn(),
    createDeal: vi.fn(),
    getDeal: vi.fn(),
    getNegotiation: vi.fn(async (dealId: string, organizationId: string) => ({ deal_id: dealId, organization_id: organizationId,
      deal_revision: 0, latest: null, current_candidate: null, eligible_actions: [], round_count: 0, max_rounds: 5,
      escalated: false, history_ambiguous: false, proposals: [], history: [] })),
    getOrganization: vi.fn(),
    getCurrentAgreement: vi.fn(),
    getAgreementHistory: vi.fn().mockResolvedValue({ versions: [] }),
    getAgreementVersion: vi.fn().mockRejectedValue(new actual.ApiError(404, "No version")),
    compareAgreementVersions: vi.fn().mockRejectedValue(new actual.ApiError(404, "No comparison")),
    getDealMessageExistence: vi.fn(),
    listDealFacts: vi.fn(),
    listDealMessages: vi.fn(),
  };
});

import {
  ApiError,
  apiRequest,
  createOrganization,
  getCommercialDocumentDraft,
  getCurrentAgreement,
  getAgreementVersion,
  getTradePack,
  getDeal,
  getDealMessageExistence,
  listDealFacts,
  listDealMessages,
  listDeals,
  listOrganizations,
  listPaymentStatuses,
  login,
} from "./api/client";
import { clearAccessToken, getAccessToken, setAccessToken } from "./api/tokenStore";
import type { AgreementVersion } from "./api/types";

const mockedGetDeal = vi.mocked(getDeal);
const mockedApiRequest = vi.mocked(apiRequest);
const mockedGetCurrentAgreement = vi.mocked(getCurrentAgreement);
const mockedGetDealMessageExistence = vi.mocked(getDealMessageExistence);
const mockedListDeals = vi.mocked(listDeals);
const mockedListOrganizations = vi.mocked(listOrganizations);
const mockedCreateOrganization = vi.mocked(createOrganization);
const mockedLogin = vi.mocked(login);
const mockedListDealFacts = vi.mocked(listDealFacts);
const mockedListDealMessages = vi.mocked(listDealMessages);
const mockedGetCommercialDocumentDraft = vi.mocked(getCommercialDocumentDraft);
const mockedListPaymentStatuses = vi.mocked(listPaymentStatuses);

vi.mock("./ui/DevRoleSwitcher", () => ({
  default: ({ onSessionChanged }: { onSessionChanged: () => void }) => {
    return (
      <aside className="dev-role-switcher" aria-label="Development role switcher">
        <button
          type="button"
          className="dev-role-switcher__pill"
          onClick={() => {}}
        >
          Acting as Buyer
        </button>
        <button
          type="button"
          onClick={async () => {
            if (!window.confirm("Reset demo data? This clears demo deals and related activity.")) return;
            await apiRequest<{ message: string }>("/dev/reset-demo", { method: "POST" });
            onSessionChanged();
          }}
        >
          Reset Demo Data
        </button>
      </aside>
    );
  },
}));

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearAccessToken();
    window.location.hash = "";
    vi.stubGlobal("confirm", vi.fn(() => true));
    mockedListDeals.mockResolvedValue([]);
    vi.mocked(getAgreementVersion).mockReset().mockRejectedValue(new ApiError(404, "No version"));
    mockedListPaymentStatuses.mockResolvedValue([]);
    mockedGetCommercialDocumentDraft.mockRejectedValue(
      new ApiError(409, "Agreement not committed"),
    );
    mockedListDealFacts.mockResolvedValue([]);
    mockedListDealMessages.mockResolvedValue([]);
    mockedGetDealMessageExistence.mockResolvedValue(false);
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

  it("aborts a committed download when signing out of the deal room", async () => {
    setAccessToken("access-token");
    window.location.hash = "#/deals/deal-42";
    mockedGetDeal.mockResolvedValue({ id: "deal-42", buyer_organization_id: "11111111-1111-1111-1111-111111111111",
      seller_organization_id: "22222222-2222-2222-2222-222222222222", status: "AGREED", version: 1 });
    const agreement = { id: "version-42", deal_id: "deal-42", version_number: 1, status: "COMMITTED",
      terms_hash: "a".repeat(64), created_at: "2026-10-31T10:00:00Z", approvals: [],
      terms: { line_items: [], shipments: [], payment_terms: [] } } as unknown as AgreementVersion;
    mockedGetCurrentAgreement.mockResolvedValue(agreement);
    vi.mocked(getAgreementVersion).mockResolvedValue(agreement);
    let resolve!: (blob: Blob) => void;
    vi.mocked(getTradePack).mockReturnValueOnce(new Promise((done) => { resolve = done; }));
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Download trade pack" }));
    const signal = vi.mocked(getTradePack).mock.calls[0][4]!;
    fireEvent.click(screen.getByRole("button", { name: /sign out/i }));
    expect(signal.aborted).toBe(true);
    await act(async () => { resolve(new Blob(["late document"])); });
    expect(screen.queryByRole("button", { name: "Download trade pack" })).not.toBeInTheDocument();
    expect(getAccessToken()).toBeNull();
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

  it("lets an authenticated user accept a pending invitation before onboarding", async () => {
    setAccessToken("access-token");
    window.location.hash = "#/invite?token=pending-team-token";
    mockedListOrganizations.mockResolvedValue([]);

    render(<App />);

    // Let the organization lookup settle so a zero-org user would otherwise
    // trigger the first-run onboarding wizard.
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(
      await screen.findByRole("heading", { name: "Accept Invitation" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Set up your trading organization" }),
    ).not.toBeInTheDocument();
  });

  it("refreshes accepted membership and navigates to the server-returned deal", async () => {
    setAccessToken("access-token");
    window.location.hash = "#/invite?token=pending-team-token";
    mockedGetDeal.mockResolvedValue({
      id: "accepted-deal", buyer_organization_id: "buyer", seller_organization_id: "seller",
      status: "DRAFT", version: 1,
    });
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "No current agreement"));
    mockedApiRequest.mockResolvedValueOnce({
      organization_id: "seller", role: "ADMIN", deal_id: "accepted-deal",
      access_token: "accepted-token", refresh_token: "accepted-refresh", token_type: "bearer",
    });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Accept & Join" }));
    expect(await screen.findByText("DRAFT")).toBeInTheDocument();
    expect(window.location.hash).toBe("#/deals/accepted-deal");
    expect(mockedListOrganizations.mock.calls.length).toBeGreaterThanOrEqual(3);
    expect(screen.queryByRole("heading", { name: "Set up your trading organization" })).not.toBeInTheDocument();
  });

  it("ignores an acceptance membership refresh that finishes after sign out", async () => {
    setAccessToken("access-token");
    window.location.hash = "#/invite?token=pending-team-token";
    let resolveRefresh!: (organizations: []) => void;
    mockedApiRequest.mockImplementationOnce(async () => {
      mockedListOrganizations.mockImplementation(() => new Promise((resolve) => {
        resolveRefresh = resolve;
      }));
      return { organization_id: "seller", role: "ADMIN", deal_id: "stale-deal" };
    });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Accept & Join" }));
    await act(async () => {});
    fireEvent.click(within(screen.getByRole("banner")).getByRole("button", { name: "Sign out" }));
    await act(async () => resolveRefresh([]));
    expect(screen.getByRole("heading", { name: "Join via counterparty invite." })).toBeInTheDocument();
    expect(mockedGetDeal).not.toHaveBeenCalledWith("stale-deal");
    expect(window.location.hash).not.toBe("#/deals/stale-deal");
  });

  it.each([false, true])("ignores invitation A's refresh after opening B (reopen A: %s)", async (reopenA) => {
    setAccessToken("access-token");
    window.location.hash = "#/invite?token=invitation-a";
    let resolveRefresh!: (organizations: []) => void;
    mockedApiRequest.mockImplementationOnce(async () => {
      mockedListOrganizations.mockImplementationOnce(() => new Promise((resolve) => {
        resolveRefresh = resolve;
      }));
      return {
        organization_id: "seller", role: "ADMIN", deal_id: "deal-a",
        access_token: "accepted-token", refresh_token: "accepted-refresh",
      };
    });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Accept & Join" }));
    await act(async () => {});
    expect(resolveRefresh).toBeDefined();
    await act(async () => {
      window.location.hash = "#/invite?token=invitation-b";
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    if (reopenA) {
      await act(async () => {
        window.location.hash = "#/invite?token=invitation-a";
        window.dispatchEvent(new HashChangeEvent("hashchange"));
      });
    }
    const currentHash = window.location.hash;
    await act(async () => resolveRefresh([]));
    expect(window.location.hash).toBe(currentHash);
    expect(mockedGetDeal).not.toHaveBeenCalledWith("deal-a");
    expect(screen.getByRole("button", { name: "Accept & Join" })).toBeEnabled();
    expect(screen.queryByRole("heading", { name: "Set up your trading organization" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Workspace" }));
    await screen.findByRole("heading", { name: "Deals shared with you" });
    expect(screen.queryByRole("heading", { name: "Set up your trading organization" })).not.toBeInTheDocument();
  });

  it.each(["sign out", "session change"])("ignores late acceptance after %s before applying returned tokens", async (change) => {
    setAccessToken("access-token");
    window.location.hash = "#/invite?token=invitation-a";
    let resolveAcceptance!: (result: {
      organization_id: string; role: string; deal_id: string;
      access_token: string; refresh_token: string;
    }) => void;
    mockedApiRequest.mockImplementationOnce(() => new Promise((resolve) => {
      resolveAcceptance = resolve;
    }));
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Accept & Join" }));
    if (change === "sign out") {
      fireEvent.click(within(screen.getByRole("banner")).getByRole("button", { name: "Sign out" }));
    } else {
      mockedApiRequest.mockResolvedValueOnce({ message: "Reset" });
      fireEvent.click(screen.getByRole("button", { name: "Reset Demo Data" }));
      await screen.findByRole("heading", { name: "Deals shared with you" });
      await act(async () => {
        window.location.hash = "#/invite?token=invitation-a";
        window.dispatchEvent(new HashChangeEvent("hashchange"));
      });
    }
    const currentHash = window.location.hash;
    const refreshCalls = mockedListOrganizations.mock.calls.length;
    await act(async () => resolveAcceptance({
      organization_id: "seller", role: "ADMIN", deal_id: "stale-deal",
      access_token: "stale-token", refresh_token: "stale-refresh",
    }));
    expect(window.location.hash).toBe(currentHash);
    expect(mockedListOrganizations).toHaveBeenCalledTimes(refreshCalls);
    expect(mockedGetDeal).not.toHaveBeenCalledWith("stale-deal");
    expect(getAccessToken()).toBe(change === "sign out" ? null : "access-token");
  });

  it("guides a new user with 0 organizations through the setup wizard to create an organization and routes to deal register with toast", async () => {
    setAccessToken("access-token");
    mockedListOrganizations.mockResolvedValueOnce([]);
    mockedCreateOrganization.mockResolvedValue({
      id: "org-grain-1",
      legal_name: "Global Grain Importers Ltd",
      country_code: "DE",
      role: "ADMIN",
    });

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Set up your trading organization" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Company Legal Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Country Code")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Company Legal Name"), {
      target: { value: "Global Grain Importers Ltd" },
    });
    fireEvent.change(screen.getByLabelText("Country Code"), {
      target: { value: "DE" },
    });

    fireEvent.click(screen.getByRole("button", { name: /create & continue/i }));

    expect(mockedCreateOrganization).toHaveBeenCalledWith({
      legal_name: "Global Grain Importers Ltd",
      country_code: "DE",
    });

    expect(
      await screen.findByRole("heading", { name: "Deals shared with you" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText(/Created Global Grain Importers Ltd \(DE\)/i),
    ).toBeInTheDocument();
    expect(window.location.hash).toBe("#/deals");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("does not trap existing users with organizations in the setup wizard", async () => {
    setAccessToken("access-token");
    mockedListOrganizations.mockResolvedValue([
      {
        id: "11111111-1111-1111-1111-111111111111",
        legal_name: "Existing Trading Co",
        country_code: "GB",
        role: "ADMIN",
      },
    ]);

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Deals shared with you" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Set up your trading organization" }),
    ).not.toBeInTheDocument();
  });

  it("does not lock out users if listing organizations fails", async () => {
    setAccessToken("access-token");
    mockedListOrganizations.mockRejectedValue(new Error("Network failure"));

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Deals shared with you" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("ignores late organization creation completion from a previous session after sign out", async () => {
    setAccessToken("token-user-a");
    mockedListOrganizations.mockResolvedValueOnce([]);

    let resolveCreate!: (org: {
      id: string;
      legal_name: string;
      country_code: string;
      role: string;
    }) => void;
    mockedCreateOrganization.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveCreate = resolve;
        }),
    );

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Set up your trading organization" }),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Company Legal Name"), {
      target: { value: "User A Corp" },
    });
    fireEvent.change(screen.getByLabelText("Country Code"), {
      target: { value: "US" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create & continue/i }));

    const globalSignOut = within(screen.getByRole("banner")).getByRole("button", {
      name: "Sign out",
    });
    fireEvent.click(globalSignOut);

    expect(
      await screen.findByRole("heading", { name: "Open your trade desk." }),
    ).toBeInTheDocument();

    mockedLogin.mockResolvedValueOnce({
      access_token: "token-user-b",
      refresh_token: "refresh-b",
      token_type: "Bearer",
    });
    mockedListOrganizations.mockResolvedValueOnce([]);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "user-b@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Enter workspace" }));

    expect(
      await screen.findByRole("heading", { name: "Set up your trading organization" }),
    ).toBeInTheDocument();

    resolveCreate({
      id: "org-a-123",
      legal_name: "User A Corp",
      country_code: "US",
      role: "ADMIN",
    });

    await new Promise((r) => setTimeout(r, 50));

    expect(
      screen.getByRole("heading", { name: "Set up your trading organization" }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Created User A Corp/i)).not.toBeInTheDocument();
  });

  it("clears the previous user's toast on sign out so it does not carry over to the next user", async () => {
    setAccessToken("token-user-a");
    mockedListOrganizations.mockResolvedValueOnce([]);
    mockedCreateOrganization.mockResolvedValueOnce({
      id: "org-a-1",
      legal_name: "Alpha Corp",
      country_code: "US",
      role: "ADMIN",
    });

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Set up your trading organization" }),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Company Legal Name"), {
      target: { value: "Alpha Corp" },
    });
    fireEvent.change(screen.getByLabelText("Country Code"), {
      target: { value: "US" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create & continue/i }));

    expect(await screen.findByText(/Created Alpha Corp \(US\)/i)).toBeInTheDocument();

    const globalSignOut = within(screen.getByRole("banner")).getByRole("button", {
      name: "Sign out",
    });
    fireEvent.click(globalSignOut);

    expect(screen.queryByText(/Created Alpha Corp \(US\)/i)).not.toBeInTheDocument();

    mockedLogin.mockResolvedValueOnce({
      access_token: "token-user-b",
      refresh_token: "refresh-b",
      token_type: "Bearer",
    });
    mockedListOrganizations.mockResolvedValueOnce([
      {
        id: "org-b-1",
        legal_name: "Beta Ltd",
        country_code: "GB",
        role: "ADMIN",
      },
    ]);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "user-b@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Enter workspace" }));

    expect(
      await screen.findByRole("heading", { name: "Deals shared with you" }),
    ).toBeInTheDocument();

    expect(screen.queryByText(/Created Alpha Corp \(US\)/i)).not.toBeInTheDocument();
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
