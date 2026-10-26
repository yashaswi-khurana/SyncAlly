import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiRequest } from "../api/client";
import { clearAccessToken, getAccessToken } from "../api/tokenStore";
import DevRoleSwitcher from "./DevRoleSwitcher";

vi.mock("../api/client", () => ({ apiRequest: vi.fn() }));

const mockedApiRequest = vi.mocked(apiRequest);

describe("DevRoleSwitcher", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearAccessToken();
    window.localStorage.removeItem("syncally.devRole");
    vi.stubGlobal("confirm", vi.fn(() => true));
  });

  it("switches to Seller, stores both tokens, and refreshes the current view", async () => {
    mockedApiRequest.mockResolvedValue({
      access_token: "seller-access",
      refresh_token: "seller-refresh",
      token_type: "bearer",
    });
    const onSessionChanged = vi.fn();

    render(<DevRoleSwitcher onSessionChanged={onSessionChanged} />);
    fireEvent.click(screen.getByRole("button", { name: "Acting as Buyer" }));
    fireEvent.click(screen.getByRole("button", { name: "Switch to Seller" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Switched to Seller.");
    expect(mockedApiRequest).toHaveBeenCalledWith("/dev/switch-role", {
      method: "POST",
      body: JSON.stringify({ target_role: "SELLER" }),
    });
    expect(getAccessToken()).toBe("seller-access");
    expect(window.localStorage.getItem("syncally.refreshToken")).toBeNull();
    expect(onSessionChanged).toHaveBeenCalledOnce();
    expect(screen.getByRole("button", { name: "Acting as Seller" })).toBeInTheDocument();
  });

  it("confirms before resetting demo data and displays success feedback", async () => {
    mockedApiRequest.mockResolvedValue({ message: "Demo data cleared" });

    render(<DevRoleSwitcher onSessionChanged={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Acting as Buyer" }));
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

    render(<DevRoleSwitcher onSessionChanged={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Acting as Buyer" }));
    fireEvent.click(screen.getByRole("button", { name: "Reset Demo Data" }));

    expect(window.confirm).toHaveBeenCalledOnce();
    expect(mockedApiRequest).not.toHaveBeenCalled();
  });
});
