import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { disconnectSlack, getSlackAccountLinkStatus, getSlackConnection, redeemSlackLink, startSlackConnection } from "../api/client";
import type { Organization, SlackConnection } from "../api/types";
import SlackIntegrationSection from "./SlackIntegrationSection";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    disconnectSlack: vi.fn(),
    getSlackAccountLinkStatus: vi.fn(),
    getSlackConnection: vi.fn(),
    redeemSlackLink: vi.fn(),
    startSlackConnection: vi.fn(),
  };
});

const mockedDisconnectSlack = vi.mocked(disconnectSlack);
const mockedGetSlackAccountLinkStatus = vi.mocked(getSlackAccountLinkStatus);
const mockedGetSlackConnection = vi.mocked(getSlackConnection);
const mockedRedeemSlackLink = vi.mocked(redeemSlackLink);
const mockedStartSlackConnection = vi.mocked(startSlackConnection);
const ORG_ID = "33333333-3333-3333-3333-333333333333";

function organization(role: Organization["role"] = "ADMIN"): Organization {
  return {
    id: ORG_ID,
    legal_name: "Demo Seller Co",
    country_code: "US",
    role,
  };
}

function connection(overrides: Partial<SlackConnection> = {}): SlackConnection {
  return {
    configured: true,
    connected: false,
    workspace_id: null,
    workspace_name: null,
    granted_scopes: [],
    connected_at: null,
    messaging_enabled: false,
    ...overrides,
  };
}

function linkStatus(overrides: Partial<{ workspace_connected: boolean; account_linked: boolean }> = {}) {
  return {
    workspace_connected: true,
    account_linked: false,
    ...overrides,
  };
}

describe("SlackIntegrationSection", () => {
  beforeEach(() => {
    mockedGetSlackConnection.mockResolvedValue(connection());
    mockedGetSlackAccountLinkStatus.mockResolvedValue(linkStatus());
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it("does not fetch or reveal connection details to a non-admin member", async () => {
    mockedGetSlackConnection.mockResolvedValue(connection({
      connected: true,
      workspace_id: "T-private",
      workspace_name: "Private workspace",
    }));

    render(<SlackIntegrationSection organization={organization("MEMBER")} />);

    expect(
      await screen.findByText(/an organization administrator manages the slack workspace connection/i),
    ).toBeInTheDocument();
    expect(mockedGetSlackConnection).not.toHaveBeenCalled();
    expect(screen.queryByText("Private workspace")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /connect slack/i })).not.toBeInTheDocument();
  });

  it("hides loaded workspace details if the organization role changes to member", async () => {
    mockedGetSlackConnection.mockResolvedValue(connection({
      connected: true,
      workspace_id: "T-private",
      workspace_name: "Private workspace",
      granted_scopes: ["app_mentions:read", "chat:write"],
    }));

    const view = render(<SlackIntegrationSection organization={organization("ADMIN")} />);
    expect(await screen.findByText("Private workspace")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Disconnect Slack" }));
    expect(await screen.findByRole("dialog", { name: "Disconnect Slack?" })).toBeInTheDocument();

    view.rerender(<SlackIntegrationSection organization={organization("MEMBER")} />);

    expect(
      await screen.findByText(/an organization administrator manages the slack workspace connection/i),
    ).toBeInTheDocument();
    expect(screen.queryByText("Private workspace")).not.toBeInTheDocument();
    expect(screen.queryByText("T-private")).not.toBeInTheDocument();
    expect(screen.queryByText(/app_mentions:read, chat:write/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirm disconnect" })).not.toBeInTheDocument();
    expect(mockedGetSlackConnection).toHaveBeenCalledTimes(1);
  });

  it("shows connected workspace details and requires confirmation to disconnect", async () => {
    mockedGetSlackConnection
      .mockResolvedValueOnce(connection({
        connected: true,
        workspace_id: "T-acme",
        workspace_name: "Acme Slack",
        granted_scopes: ["app_mentions:read", "chat:write"],
        connected_at: "2026-11-09T10:00:00Z",
      }))
      .mockResolvedValueOnce(connection());
    mockedGetSlackAccountLinkStatus
      .mockResolvedValueOnce(linkStatus())
      .mockResolvedValueOnce(linkStatus({ workspace_connected: false }));
    mockedDisconnectSlack.mockResolvedValue(connection());

    render(<SlackIntegrationSection organization={organization()} />);

    expect(await screen.findByText("Acme Slack")).toBeInTheDocument();
    expect(screen.getByText(/syncally handles messages that mention @syncally/i)).toBeInTheDocument();
    expect(screen.getByText(/@syncally status <deal-id>/i)).toBeInTheDocument();
    expect(screen.queryByText("T-acme")).not.toBeInTheDocument();
    expect(screen.queryByText(/app_mentions:read, chat:write/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Disconnect Slack" }));
    expect(await screen.findByRole("dialog", { name: "Disconnect Slack?" })).toBeInTheDocument();
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Cancel" }));
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Disconnect Slack" }));
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Disconnect Slack" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm disconnect" }));

    await waitFor(() => expect(mockedDisconnectSlack).toHaveBeenCalledWith(ORG_ID));
    expect(await screen.findByText(/slack was disconnected/i)).toBeInTheDocument();
    expect(mockedGetSlackConnection).toHaveBeenCalledTimes(2);
    expect(document.activeElement).toHaveTextContent(/slack was disconnected/i);
  });

  it("redeems the private Slack code and confirms linking without granting permissions", async () => {
    mockedRedeemSlackLink.mockResolvedValue({ linked: true });

    render(<SlackIntegrationSection organization={organization("MEMBER")} />);
    fireEvent.change(await screen.findByLabelText("Temporary link code"), {
      target: { value: "AbCdEfGh1234" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Link Slack account" }));

    await waitFor(() => expect(mockedRedeemSlackLink).toHaveBeenCalledWith("AbCdEfGh1234"));
    const linkedMessage = await screen.findByText(/your slack account is linked. deal and payment access still follow your syncally permissions/i);
    const linkCard = screen.getByRole("heading", { name: "Link your Slack account" }).closest("article") as HTMLElement;
    expect(linkCard).toContainElement(linkedMessage);
    expect(screen.queryByLabelText("Temporary link code")).not.toBeInTheDocument();
    expect(mockedGetSlackAccountLinkStatus).toHaveBeenCalledWith(ORG_ID);
  });

  it("shows a safe error and preserves the code after a failed redemption", async () => {
    mockedRedeemSlackLink.mockRejectedValue(new Error("Slack link code is invalid or expired"));

    render(<SlackIntegrationSection organization={organization("MEMBER")} />);
    fireEvent.change(await screen.findByLabelText("Temporary link code"), {
      target: { value: "AbCdEfGh1234" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Link Slack account" }));

    const linkError = "That code is invalid or expired. Mention @SyncAlly link in Slack to get a fresh code, then try again.";
    expect(await screen.findByText(linkError)).toBeInTheDocument();
    const linkCard = screen.getByLabelText("Temporary link code").closest("article") as HTMLElement;
    expect(linkCard).toContainElement(screen.getByText(linkError));
    expect(screen.getByLabelText("Temporary link code")).toHaveValue("AbCdEfGh1234");
  });

  it("does not offer account linking to an admin until a workspace is connected", async () => {
    mockedGetSlackAccountLinkStatus.mockResolvedValue(linkStatus({ workspace_connected: false }));
    render(<SlackIntegrationSection organization={organization()} />);

    expect(await screen.findByText(/no slack workspace is connected/i)).toBeInTheDocument();
    expect(screen.getByText(/an organization administrator must connect a slack workspace/i)).toBeInTheDocument();
    expect(screen.queryByLabelText("Temporary link code")).not.toBeInTheDocument();
  });

  it("explains deployment setup and prevents an unavailable connect action", async () => {
    mockedGetSlackConnection.mockResolvedValue(connection({ configured: false }));
    mockedGetSlackAccountLinkStatus.mockResolvedValue(linkStatus({ workspace_connected: false }));

    render(<SlackIntegrationSection organization={organization()} />);

    expect(
      await screen.findByText(/slack is not configured for this syncally deployment yet/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /connect slack/i })).toBeDisabled();
    expect(mockedStartSlackConnection).not.toHaveBeenCalled();
  });

  it("shows an existing account link when the integration panel is reopened", async () => {
    mockedGetSlackAccountLinkStatus.mockResolvedValue(linkStatus({ account_linked: true }));

    render(<SlackIntegrationSection organization={organization("MEMBER")} />);

    expect(await screen.findByText(/your slack account is linked/i)).toBeInTheDocument();
    expect(screen.queryByLabelText("Temporary link code")).not.toBeInTheDocument();
  });
});
