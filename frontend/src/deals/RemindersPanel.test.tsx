import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  listDealReminders,
  suppressDealReminder,
  syncDealReminders,
} from "../api/client";
import type { Deal, DealReminder } from "../api/types";
import RemindersPanel from "./RemindersPanel";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    listDealReminders: vi.fn(),
    syncDealReminders: vi.fn(),
    suppressDealReminder: vi.fn(),
  };
});

const mockedListDealReminders = vi.mocked(listDealReminders);
const mockedSyncDealReminders = vi.mocked(syncDealReminders);
const mockedSuppressDealReminder = vi.mocked(suppressDealReminder);

const TEST_DEAL: Deal = {
  id: "deal-123",
  buyer_organization_id: "org-buyer",
  seller_organization_id: "org-seller",
  status: "AGREED",
  version: 1,
};

const SAMPLE_REMINDERS: DealReminder[] = [
  {
    id: "rem-1",
    deal_id: "deal-123",
    scope: "MILESTONE",
    reference_id: "ms-1",
    recipient_organization_id: "org-buyer",
    recipient_user_id: null,
    status: "SCHEDULED",
    scheduled_for: "2026-11-07T12:00:00Z",
    due_at: "2026-11-08T12:00:00Z",
    recurrence_cap: 3,
    recurrence_count: 0,
    deduplication_key: "dedup-1",
    channel: "IN_APP",
    suppression_reason: null,
    delivered_at: null,
    suppressed_at: null,
    last_error: null,
    created_at: "2026-11-07T12:00:00Z",
    updated_at: "2026-11-07T12:00:00Z",
  },
  {
    id: "rem-2",
    deal_id: "deal-123",
    scope: "FULFILLMENT",
    reference_id: "ob-1",
    recipient_organization_id: "org-buyer",
    recipient_user_id: null,
    status: "DELIVERED",
    scheduled_for: "2026-11-06T12:00:00Z",
    due_at: "2026-11-07T12:00:00Z",
    recurrence_cap: 3,
    recurrence_count: 1,
    deduplication_key: "dedup-2",
    channel: "IN_APP",
    suppression_reason: null,
    delivered_at: "2026-11-07T12:00:05Z",
    suppressed_at: null,
    last_error: null,
    created_at: "2026-11-06T12:00:00Z",
    updated_at: "2026-11-07T12:00:05Z",
  },
  {
    id: "rem-3",
    deal_id: "deal-123",
    scope: "CASE",
    reference_id: "case-1",
    recipient_organization_id: "org-buyer",
    recipient_user_id: null,
    status: "SUPPRESSED",
    scheduled_for: "2026-11-05T12:00:00Z",
    due_at: "2026-11-06T12:00:00Z",
    recurrence_cap: 3,
    recurrence_count: 1,
    deduplication_key: "dedup-3",
    channel: "IN_APP",
    suppression_reason: "RESOLVED",
    delivered_at: null,
    suppressed_at: "2026-11-06T12:00:01Z",
    last_error: null,
    created_at: "2026-11-05T12:00:00Z",
    updated_at: "2026-11-06T12:00:01Z",
  },
];

describe("RemindersPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  it("renders empty state truthfully when no reminders exist", async () => {
    mockedListDealReminders.mockResolvedValue([]);

    render(
      <RemindersPanel
        deal={TEST_DEAL}
        selectedOrganizationId="org-buyer"
      />
    );

    expect(screen.getByTestId("reminders-loading")).toBeInTheDocument();

    const empty = await screen.findByTestId("reminders-empty");
    expect(empty).toHaveTextContent("No obligation reminders scheduled for your organization.");
    expect(mockedListDealReminders).toHaveBeenCalledWith("deal-123", "org-buyer", expect.anything());
  });

  it("truthfully displays reminder items with status, channel, and due dates", async () => {
    mockedListDealReminders.mockResolvedValue(SAMPLE_REMINDERS);

    render(
      <RemindersPanel
        deal={TEST_DEAL}
        selectedOrganizationId="org-buyer"
      />
    );

    const list = await screen.findByTestId("reminders-list");
    expect(list).toBeInTheDocument();

    // Check scope labels
    expect(screen.getByTestId("reminder-scope-rem-1")).toHaveTextContent("Payment Milestone");
    expect(screen.getByTestId("reminder-scope-rem-2")).toHaveTextContent("Fulfillment");
    expect(screen.getByTestId("reminder-scope-rem-3")).toHaveTextContent("Deal Case / Dispute");

    // Check status badges
    expect(screen.getByTestId("reminder-status-rem-1")).toHaveTextContent("SCHEDULED");
    expect(screen.getByTestId("reminder-status-rem-2")).toHaveTextContent("DELIVERED");
    expect(screen.getByTestId("reminder-status-rem-3")).toHaveTextContent("SUPPRESSED");

    // Check suppression reason is displayed
    expect(screen.getByText(/Suppressed \(RESOLVED\)/)).toBeInTheDocument();

    // Check channels and recurrence
    expect(screen.getAllByText(/Channel: IN_APP/)).toHaveLength(3);
    expect(screen.getByText("0 / 3")).toBeInTheDocument();
  });

  it("handles sync reminders action", async () => {
    mockedListDealReminders.mockResolvedValue([]);
    mockedSyncDealReminders.mockResolvedValue(SAMPLE_REMINDERS);

    render(
      <RemindersPanel
        deal={TEST_DEAL}
        selectedOrganizationId="org-buyer"
      />
    );

    await screen.findByTestId("reminders-empty");

    const syncBtn = screen.getByTestId("sync-reminders-button");
    await act(async () => {
      fireEvent.click(syncBtn);
    });

    expect(mockedSyncDealReminders).toHaveBeenCalledWith("deal-123", "org-buyer");
    expect(await screen.findByTestId("reminders-list")).toBeInTheDocument();
  });

  it("allows dismissing an active reminder", async () => {
    mockedListDealReminders.mockResolvedValue([SAMPLE_REMINDERS[0]]);
    const suppressedItem: DealReminder = {
      ...SAMPLE_REMINDERS[0],
      status: "SUPPRESSED",
      suppression_reason: "RESOLVED",
      suppressed_at: "2026-11-07T13:00:00Z",
    };
    mockedSuppressDealReminder.mockResolvedValue(suppressedItem);

    render(
      <RemindersPanel
        deal={TEST_DEAL}
        selectedOrganizationId="org-buyer"
      />
    );

    await screen.findByTestId("reminder-item-rem-1");

    const dismissBtn = screen.getByTestId("dismiss-reminder-rem-1");
    await act(async () => {
      fireEvent.click(dismissBtn);
    });

    expect(mockedSuppressDealReminder).toHaveBeenCalledWith("deal-123", "rem-1", "org-buyer");
    expect(await screen.findByTestId("reminder-status-rem-1")).toHaveTextContent("SUPPRESSED");
  });

  it("displays error message if listing reminders fails", async () => {
    mockedListDealReminders.mockRejectedValue(new ApiError(500, "Database error loading reminders"));

    render(
      <RemindersPanel
        deal={TEST_DEAL}
        selectedOrganizationId="org-buyer"
      />
    );

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Database error loading reminders");
  });

  it("renders error_detail badge when present and allows dismissing pending reminders", async () => {
    const errorReminder: DealReminder = {
      ...SAMPLE_REMINDERS[0],
      status: "PENDING",
      error_detail: "Connection refused to dispatch worker",
    };
    mockedListDealReminders.mockResolvedValue([errorReminder]);

    render(
      <RemindersPanel
        deal={TEST_DEAL}
        selectedOrganizationId="org-buyer"
      />
    );

    await screen.findByTestId("reminder-item-rem-1");
    expect(screen.getByText(/Error: Connection refused to dispatch worker/)).toBeInTheDocument();

    const dismissBtn = screen.getByTestId("dismiss-reminder-rem-1");
    expect(dismissBtn).toBeInTheDocument();
  });
});
