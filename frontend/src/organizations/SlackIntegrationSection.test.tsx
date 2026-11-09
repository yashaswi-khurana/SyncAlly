import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { disconnectSlack, getSlackConnection, redeemSlackLink, startSlackConnection } from "../api/client";
import type { Organization, SlackConnection } from "../api/types";
import SlackIntegrationSection from "./SlackIntegrationSection";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    disconnectSlack: vi.fn(),
    getSlackConnection: vi.fn(),
    redeemSlackLink: vi.fn(),
    startSlackConnection: vi.fn(),
  };
});

const mockedDisconnectSlack = vi.mocked(disconnectSlack);
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

describe("SlackIntegrationSection", () => {
  beforeEach(() => {
    mockedGetSlackConnection.mockResolvedValue(connection());
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
      await screen.findByText(/only an organization administrator can view or manage/i),
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
    expect(await screen.findByText(/connected to private workspace/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Disconnect Slack" }));
    expect(await screen.findByRole("dialog", { name: "Disconnect Slack?" })).toBeInTheDocument();

    view.rerender(<SlackIntegrationSection organization={organization("MEMBER")} />);

    expect(
      await screen.findByText(/only an organization administrator can view or manage/i),
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
    mockedDisconnectSlack.mockResolvedValue(connection());

    render(<SlackIntegrationSection organization={organization()} />);

    expect(await screen.findByText(/connected to acme slack/i)).toBeInTheDocument();
    expect(screen.getByText(/members can ask about a deal by exact id/i)).toBeInTheDocument();
    expect(screen.getByText(/app_mentions:read, chat:write/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Disconnect Slack" }));
    expect(await screen.findByRole("dialog", { name: "Disconnect Slack?" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Disconnect Slack" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm disconnect" }));

    await waitFor(() => expect(mockedDisconnectSlack).toHaveBeenCalledWith(ORG_ID));
    expect(await screen.findByText(/slack was disconnected/i)).toBeInTheDocument();
    expect(mockedGetSlackConnection).toHaveBeenCalledTimes(2);
  });

  it("redeems the private Slack code and confirms linking without granting permissions", async () => {
    mockedRedeemSlackLink.mockResolvedValue({ linked: true });

    render(<SlackIntegrationSection organization={organization("MEMBER")} />);
    fireEvent.change(screen.getByLabelText("Temporary link code"), {
      target: { value: "AbCdEfGh1234" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Link Slack account" }));

    await waitFor(() => expect(mockedRedeemSlackLink).toHaveBeenCalledWith("AbCdEfGh1234"));
    expect(await screen.findByText(/your slack account is linked. deal access still follows your syncally permissions/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Temporary link code")).toHaveValue("");
  });

  it("shows a safe error and preserves the code after a failed redemption", async () => {
    mockedRedeemSlackLink.mockRejectedValue(new Error("Slack link code is invalid or expired"));

    render(<SlackIntegrationSection organization={organization("MEMBER")} />);
    fireEvent.change(screen.getByLabelText("Temporary link code"), {
      target: { value: "AbCdEfGh1234" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Link Slack account" }));

    expect(await screen.findByText("Slack link code is invalid or expired")).toBeInTheDocument();
    expect(screen.getByLabelText("Temporary link code")).toHaveValue("AbCdEfGh1234");
  });

  it("explains deployment setup and prevents an unavailable connect action", async () => {
    mockedGetSlackConnection.mockResolvedValue(connection({ configured: false }));

    render(<SlackIntegrationSection organization={organization()} />);

    expect(
      await screen.findByText(/slack setup is not configured for this syncally deployment/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /connect slack/i })).toBeDisabled();
    expect(mockedStartSlackConnection).not.toHaveBeenCalled();
  });
});
