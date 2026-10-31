import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  it("typed team invitation hides company fields and calls membership refresh", async () => {
    const token = `header.${btoa(JSON.stringify({ version: 1, kind: "TEAM", recipient_email: "recipient@example.com" }))}.signature`;
    window.location.hash = `#/invite?token=${token}`;
    const result = { status: "ACCEPTED", organization_id: "inviting-org", organization_legal_name: "Team Ltd", user_id: "recipient", role: "MEMBER", deal_id: null };
    mockedApiRequest.mockResolvedValueOnce(result);
    const onAccepted = vi.fn().mockResolvedValue(undefined);
    const { unmount } = render(<OrganizationsSettingsPage onAccepted={onAccepted} />);
    expect(await screen.findByRole("heading", { name: "Accept team invitation" })).toBeInTheDocument();
    expect(screen.queryByLabelText(/Company Legal Name/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Accept & Join" }));
    await waitFor(() => expect(onAccepted).toHaveBeenCalledWith(result, expect.any(Function)));
    const isCurrentInvitation = onAccepted.mock.calls[0][1] as () => boolean;
    expect(isCurrentInvitation()).toBe(true);
    unmount();
    expect(isCurrentInvitation()).toBe(false);
  });
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

  it("renders page header and Invite team member button", async () => {
    render(<OrganizationsSettingsPage />);

    expect(screen.getByRole("heading", { name: "Organizations." })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Invite team member" })).toBeInTheDocument();
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

    const inviteBtn = screen.getByRole("button", { name: "Invite team member" });
    fireEvent.click(inviteBtn);

    expect(screen.getByRole("heading", { name: "Invite team member" })).toBeInTheDocument();
    await screen.findByRole("option", { name: "Demo Seller Co (US)" });
    expect(screen.queryByLabelText(/Deal ID/)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Team member email"), { target: { value: " Teammate@Example.com " } });

    const generateBtn = screen.getByRole("button", { name: "Generate Invite Link" });
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(mockedApiRequest).toHaveBeenCalledWith(
        "/organizations/11111111-1111-1111-1111-111111111111/invitations",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ recipient_email: "teammate@example.com" }),
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

  it("resets the accept outcome when a different invite token is opened", async () => {
    window.location.hash = "#/invite?token=first-token";

    mockedApiRequest.mockResolvedValueOnce({
      status: "ACCEPTED",
      organization_id: "11111111-1111-1111-1111-111111111111",
      organization_legal_name: "Demo Seller Co",
      user_id: "99999999-9999-9999-9999-999999999999",
      role: "MEMBER",
      deal_id: null,
    });

    render(<OrganizationsSettingsPage />);

    fireEvent.click(screen.getByRole("button", { name: "Accept & Join" }));
    expect(await screen.findByText(/Successfully joined Demo Seller Co!/i)).toBeInTheDocument();

    window.location.hash = "#/invite?token=second-token";
    fireEvent(window, new Event("hashchange"));

    await waitFor(() => {
      expect(screen.queryByText(/Successfully joined/i)).not.toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Accept & Join" })).toBeInTheDocument();
  });

  it("does not refresh membership from a late response for a previous invitation", async () => {
    window.location.hash = "#/invite?token=first-token";
    let resolveAcceptance!: (result: unknown) => void;
    mockedApiRequest.mockImplementationOnce(() => new Promise((resolve) => {
      resolveAcceptance = resolve;
    }));
    const onAccepted = vi.fn();
    render(<OrganizationsSettingsPage onAccepted={onAccepted} />);
    fireEvent.click(screen.getByRole("button", { name: "Accept & Join" }));
    window.location.hash = "#/invite?token=second-token";
    fireEvent(window, new Event("hashchange"));
    await act(async () => resolveAcceptance({
      status: "ACCEPTED", organization_legal_name: "Previous Ltd", deal_id: "stale-deal",
    }));
    expect(onAccepted).not.toHaveBeenCalled();
    expect(screen.queryByText(/Successfully joined/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Accept & Join" })).toBeEnabled();
    expect(window.location.hash).toBe("#/invite?token=second-token");
  });

  it("keeps the accept outcome when the hash changes but the token is unchanged", async () => {
    window.location.hash = "#/invite?token=stable-token";

    mockedApiRequest.mockResolvedValueOnce({
      status: "ACCEPTED",
      organization_id: "11111111-1111-1111-1111-111111111111",
      organization_legal_name: "Demo Seller Co",
      user_id: "99999999-9999-9999-9999-999999999999",
      role: "MEMBER",
      deal_id: null,
    });

    render(<OrganizationsSettingsPage />);

    fireEvent.click(screen.getByRole("button", { name: "Accept & Join" }));
    expect(await screen.findByText(/Successfully joined Demo Seller Co!/i)).toBeInTheDocument();

    window.location.hash = "#/invite?token=stable-token&dealId=deal-999";
    fireEvent(window, new Event("hashchange"));

    await waitFor(() => {
      expect(screen.getByText(/Successfully joined Demo Seller Co!/i)).toBeInTheDocument();
    });
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

  it("allows entering counterparty company details and submits to accept endpoint", async () => {
    window.location.hash = "#/invite?token=invited-token-counterparty";

    mockedApiRequest.mockResolvedValueOnce({
      status: "ACCEPTED",
      organization_id: "org-new-counterparty",
      organization_legal_name: "Tokyo Maritime Ltd",
      user_id: "user-tokyo-789",
      role: "ADMIN",
      deal_id: "deal-123",
    });

    render(<OrganizationsSettingsPage />);

    expect(screen.getByRole("heading", { name: "Accept Invitation" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Your Company Legal Name (Optional)"), {
      target: { value: "Tokyo Maritime Ltd" },
    });
    fireEvent.change(screen.getByLabelText("Country Code (2 letters)"), {
      target: { value: "JP" },
    });

    const acceptBtn = screen.getByRole("button", { name: "Accept & Join" });
    fireEvent.click(acceptBtn);

    await waitFor(() => {
      expect(mockedApiRequest).toHaveBeenCalledWith(
        "/invitations/accept",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            token: "invited-token-counterparty",
            organization_legal_name: "Tokyo Maritime Ltd",
            country_code: "JP",
          }),
        }),
      );
    });

    expect(
      await screen.findByText(/Successfully joined Tokyo Maritime Ltd!/i),
    ).toBeInTheDocument();
  });
});
