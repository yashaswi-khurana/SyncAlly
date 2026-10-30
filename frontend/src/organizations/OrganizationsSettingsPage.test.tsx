import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as apiClient from "../api/client";
import OrganizationsSettingsPage from "./OrganizationsSettingsPage";

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof apiClient>("../api/client");
  return {
    ...actual,
    listOrganizations: vi.fn(),
    apiRequest: vi.fn(),
  };
});

const mockedListOrganizations = vi.mocked(apiClient.listOrganizations);
const mockedApiRequest = vi.mocked(apiClient.apiRequest);

describe("OrganizationsSettingsPage", () => {
  beforeEach(() => {
    window.location.hash = "#/settings/organizations";
    mockedListOrganizations.mockResolvedValue([
      {
        id: "11111111-1111-1111-1111-111111111111",
        legal_name: "Demo Seller Co",
        country_code: "US",
        role: "ADMIN",
      },
      {
        id: "22222222-2222-2222-2222-222222222222",
        legal_name: "Buyer Member Co",
        country_code: "DE",
        role: "MEMBER",
      },
    ]);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    window.location.hash = "";
  });

  it("renders page header and Invite Counterparty button", async () => {
    render(<OrganizationsSettingsPage />);

    expect(screen.getByRole("heading", { name: "Organizations." })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Invite Counterparty" })).toBeInTheDocument();
  });

  it("opens the invite modal and generates a shareable link with one click", async () => {
    mockedApiRequest.mockResolvedValueOnce({
      token: "signed-token-123",
      invite_url: "https://app.syncally.trade/#/invite?token=signed-token-123",
      organization_id: "11111111-1111-1111-1111-111111111111",
      organization_legal_name: "Demo Seller Co",
      deal_id: null,
      role: "MEMBER",
      expires_at: "2026-11-06T18:00:00Z",
    });

    // Mock navigator.clipboard
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: writeTextMock },
      configurable: true,
      writable: true,
    });

    render(<OrganizationsSettingsPage />);

    const inviteBtn = screen.getByRole("button", { name: "Invite Counterparty" });
    fireEvent.click(inviteBtn);

    expect(screen.getByRole("heading", { name: "Invite Counterparty" })).toBeInTheDocument();
    await screen.findByRole("option", { name: "Demo Seller Co (US)" });

    const generateBtn = screen.getByRole("button", { name: "Generate Invite Link" });
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(mockedApiRequest).toHaveBeenCalledWith(
        "/organizations/11111111-1111-1111-1111-111111111111/invitations",
        expect.objectContaining({
          method: "POST",
        }),
      );
    });

    expect(
      screen.getByDisplayValue("https://app.syncally.trade/#/invite?token=signed-token-123"),
    ).toBeInTheDocument();

    const copyBtn = screen.getByRole("button", { name: "Copy Link" });
    fireEvent.click(copyBtn);

    expect(writeTextMock).toHaveBeenCalledWith(
      "https://app.syncally.trade/#/invite?token=signed-token-123",
    );
    expect(await screen.findByRole("button", { name: "Copied!" })).toBeInTheDocument();
  });

  it("shows the accept invitation flow when opened with invite token in hash", async () => {
    window.location.hash = "#/invite?token=invited-token-456";

    mockedApiRequest.mockResolvedValueOnce({
      status: "ACCEPTED",
      organization_id: "11111111-1111-1111-1111-111111111111",
      organization_legal_name: "Demo Seller Co",
      user_id: "99999999-9999-9999-9999-999999999999",
      role: "MEMBER",
      deal_id: "deal-123",
    });

    render(<OrganizationsSettingsPage />);

    expect(screen.getByRole("heading", { name: "Accept Invitation" })).toBeInTheDocument();

    const acceptBtn = screen.getByRole("button", { name: "Accept & Join" });
    fireEvent.click(acceptBtn);

    await waitFor(() => {
      expect(mockedApiRequest).toHaveBeenCalledWith(
        "/invitations/accept",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ token: "invited-token-456" }),
        }),
      );
    });

    expect(
      await screen.findByText(/Successfully joined Demo Seller Co!/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Go to Linked Deal" })).toBeInTheDocument();
  });

  it("displays an error message when accepting an invalid or expired invitation", async () => {
    window.location.hash = "#/invite?token=expired-token";

    mockedApiRequest.mockRejectedValueOnce(
      new apiClient.ApiError(400, "Invitation token has expired"),
    );

    render(<OrganizationsSettingsPage />);

    const acceptBtn = screen.getByRole("button", { name: "Accept & Join" });
    fireEvent.click(acceptBtn);

    expect(
      await screen.findByText("Invitation token has expired"),
    ).toBeInTheDocument();
  });
});
