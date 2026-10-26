import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiRequest, listOrganizations } from "../api/client";
import { clearAccessToken, getAccessToken, setAccessToken } from "../api/tokenStore";
import DevRoleSwitcher from "./DevRoleSwitcher";

vi.mock("../api/client", () => ({ apiRequest: vi.fn(), listOrganizations: vi.fn() }));

const mockedApiRequest = vi.mocked(apiRequest);
const mockedListOrganizations = vi.mocked(listOrganizations);

describe("DevRoleSwitcher", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearAccessToken();
    mockedListOrganizations.mockResolvedValue([
      { id: "buyer-org", legal_name: "Demo Buyer Co", country_code: "US", role: "ADMIN" },
    ]);
    vi.stubGlobal("confirm", vi.fn(() => true));
  });

  it("switches to Seller, stores both tokens, and refreshes the current view", async () => {
    mockedApiRequest.mockResolvedValue({
      access_token: "seller-access",
      refresh_token: "seller-refresh",
      token_type: "bearer",
    });
    const onSessionChanged = vi.fn();

    setAccessToken("buyer-access");
    render(<DevRoleSwitcher onSessionChanged={onSessionChanged} />);
    expect(await screen.findByRole("button", { name: "Acting as Buyer" })).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Acting as Buyer" }));
    fireEvent.click(screen.getByRole("button", { name: "Switch to Seller" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Switched to Seller.");
    expect(mockedApiRequest).toHaveBeenCalledWith("/dev/switch-role", {
      method: "POST",
      body: JSON.stringify({ target_role: "SELLER" }),
    });
    expect(getAccessToken()).toBe("seller-access");
    expect(onSessionChanged).toHaveBeenCalledOnce();
    expect(screen.getByRole("button", { name: "Acting as Seller" })).toBeInTheDocument();
  });

  it("does not restore tokens when the signed-in session changes during a switch", async () => {
    let resolveSwitch!: (tokens: {
      access_token: string;
      refresh_token: string;
      token_type: string;
    }) => void;
    mockedApiRequest.mockReturnValue(new Promise((resolve) => { resolveSwitch = resolve; }));
    setAccessToken("buyer-access");
    const onSessionChanged = vi.fn();
    render(<DevRoleSwitcher onSessionChanged={onSessionChanged} />);
    fireEvent.click(await screen.findByRole("button", { name: "Acting as Buyer" }));
    fireEvent.click(screen.getByRole("button", { name: "Switch to Seller" }));

    clearAccessToken();
    resolveSwitch({ access_token: "seller-access", refresh_token: "seller-refresh", token_type: "bearer" });

    await waitFor(() => expect(getAccessToken()).toBeNull());
    expect(onSessionChanged).not.toHaveBeenCalled();
  });

  it("derives the pill role from the signed-in organization", async () => {
    mockedListOrganizations.mockResolvedValue([
      { id: "seller-org", legal_name: "Demo Seller Co", country_code: "US", role: "ADMIN" },
    ]);
    setAccessToken("seller-access");

    render(<DevRoleSwitcher onSessionChanged={vi.fn()} />);

    expect(await screen.findByRole("button", { name: "Acting as Seller" })).toBeInTheDocument();
  });

  it("updates its role when another tab changes the active access token", async () => {
    setAccessToken("buyer-access");
    render(<DevRoleSwitcher onSessionChanged={vi.fn()} />);
    expect(await screen.findByRole("button", { name: "Acting as Buyer" })).toBeInTheDocument();

    mockedListOrganizations.mockResolvedValue([
      { id: "seller-org", legal_name: "Demo Seller Co", country_code: "US", role: "ADMIN" },
    ]);
    setAccessToken("seller-access");
    window.dispatchEvent(new StorageEvent("storage", { key: "syncally.accessToken" }));

    expect(await screen.findByRole("button", { name: "Acting as Seller" })).toBeInTheDocument();
  });

  it("confirms before resetting demo data and displays success feedback", async () => {
    mockedApiRequest.mockResolvedValue({ message: "Demo data cleared" });
    setAccessToken("buyer-access");

    render(<DevRoleSwitcher onSessionChanged={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Acting as Buyer" }));
    fireEvent.click(screen.getByRole("button", { name: "Reset Demo Data" }));

    await waitFor(() => expect(mockedApiRequest).toHaveBeenCalledWith("/dev/reset-demo", {
      method: "POST",
    }));
    expect(window.confirm).toHaveBeenCalledWith(
      "Reset demo data? This clears demo deals and related activity.",
    );
    expect(await screen.findByRole("status")).toHaveTextContent("Demo data reset.");
  });

  it("does not reset demo data when confirmation is cancelled", async () => {
    vi.mocked(window.confirm).mockReturnValue(false);
    setAccessToken("buyer-access");

    render(<DevRoleSwitcher onSessionChanged={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Acting as Buyer" }));
    fireEvent.click(screen.getByRole("button", { name: "Reset Demo Data" }));

    expect(window.confirm).toHaveBeenCalledOnce();
    expect(mockedApiRequest).not.toHaveBeenCalled();
  });
});
