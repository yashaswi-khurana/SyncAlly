import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiRequest, createCounterpartyInvitation, createDeal, listOrganizations } from "../api/client";
import type { Organization } from "../api/types";
import CreateDealPage from "./CreateDealPage";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    listOrganizations: vi.fn(),
    createDeal: vi.fn(),
    createCounterpartyInvitation: vi.fn(),
    apiRequest: vi.fn(),
  };
});

const mockedListOrganizations = vi.mocked(listOrganizations);
const mockedSearch = vi.mocked(apiRequest);
const mockedCreateDeal = vi.mocked(createDeal);

const BUYER_ID = "11111111-1111-1111-1111-111111111111";
const SELLER_ID = "22222222-2222-2222-2222-222222222222";

function organization(overrides: Partial<Organization> = {}): Organization {
  return {
    id: BUYER_ID,
    legal_name: "Buyer Co",
    country_code: "US",
    role: "ADMIN",
    ...overrides,
  };
}

describe("CreateDealPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mockedSearch.mockResolvedValue([organization({ id: SELLER_ID, legal_name: "Andean Coffee Exporters", country_code: "CO" })]);
    window.location.hash = "";
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("shows a loading state and then the create form", async () => {
    mockedListOrganizations.mockResolvedValue([organization()]);

    render(<CreateDealPage onCreated={vi.fn()} />);

    expect(screen.getByRole("status")).toHaveTextContent(/loading organizations/i);
    expect(await screen.findByLabelText("Buyer organization")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create deal" })).toBeInTheDocument();
  });

  it("creates a pending deal through invite mode and exposes a copyable link before navigation", async () => {
    mockedListOrganizations.mockResolvedValue([organization()]);
    vi.mocked(createCounterpartyInvitation).mockResolvedValue({ token: "bound-token", invite_url: "https://app.example/#/invite?token=bound-token", organization_id: BUYER_ID, organization_legal_name: "Buyer Co", deal_id: "pending-deal", role: "ADMIN", expires_at: "2026-11-07T12:00:00Z", kind: "COUNTERPARTY", pending_counterparty: true });
    const onCreated = vi.fn();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    render(<CreateDealPage onCreated={onCreated} />);
    await screen.findByLabelText("Buyer organization");
    fireEvent.click(screen.getByRole("radio", { name: "Invite counterparty" }));
    expect(screen.queryByRole("combobox", { name: "Seller organization" })).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Counterparty email"), { target: { value: " Seller@Example.com " } });
    fireEvent.change(screen.getByLabelText("Counterparty company legal name"), { target: { value: "Seller Ltd" } });
    fireEvent.change(screen.getByLabelText("Country code"), { target: { value: "JP" } });
    fireEvent.click(screen.getByRole("button", { name: "Create deal" }));
    expect(await screen.findByRole("heading", { name: "Awaiting counterparty" })).toBeInTheDocument();
    expect(createCounterpartyInvitation).toHaveBeenCalledWith({ buyer_organization_id: BUYER_ID, recipient_email: "seller@example.com", legal_name: "Seller Ltd", country_code: "JP" });
    expect(onCreated).not.toHaveBeenCalled();
    expect(mockedCreateDeal).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Copy Link" }));
    expect(await screen.findByRole("button", { name: "Copied!" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open pending deal" }));
    expect(onCreated).toHaveBeenCalledWith("pending-deal");
  });

  it("shows an empty state when the account has no organizations", async () => {
    mockedListOrganizations.mockResolvedValue([]);

    render(<CreateDealPage onCreated={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "No organizations yet" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create deal" })).not.toBeInTheDocument();
  });

  it("shows an error state and retries loading organizations", async () => {
    mockedListOrganizations.mockRejectedValueOnce(
      new ApiError(0, null, "Unable to reach the SyncAlly API. Check that it is running."),
    );

    render(<CreateDealPage onCreated={vi.fn()} />);

    expect(
      await screen.findByRole("heading", { name: /could not load your organizations/i }),
    ).toBeInTheDocument();

    mockedListOrganizations.mockResolvedValueOnce([organization()]);
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByLabelText("Buyer organization")).toBeInTheDocument();
    expect(mockedListOrganizations).toHaveBeenCalledTimes(2);
  });

  it("requires selection and rejects trading with the acting organization", async () => {
    mockedListOrganizations.mockResolvedValue([organization()]);
    mockedSearch.mockResolvedValue([organization()]);
    render(<CreateDealPage onCreated={vi.fn()} />);
    const input = await screen.findByLabelText("Seller organization");
    fireEvent.click(screen.getByRole("button", { name: "Create deal" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Choose a seller organization");
    fireEvent.change(input, { target: { value: "Buyer" } });
    fireEvent.click(screen.getByRole("button", { name: "Create deal" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Choose a seller organization");
    fireEvent.click(await screen.findByRole("option", { name: "Buyer Co US" }));
    fireEvent.click(screen.getByRole("button", { name: "Create deal" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Buyer and seller must be different organizations.");
    expect(mockedCreateDeal).not.toHaveBeenCalled();
  });

  it("creates a deal and hands the new deal id to the caller", async () => {
    mockedListOrganizations.mockResolvedValue([organization()]);
    mockedCreateDeal.mockResolvedValue({
      id: "deal-1",
      buyer_organization_id: BUYER_ID,
      seller_organization_id: SELLER_ID,
      status: "DRAFT",
      version: 0,
    });
    const onCreated = vi.fn();

    render(<CreateDealPage onCreated={onCreated} />);
    await screen.findByLabelText("Buyer organization");

    fireEvent.change(screen.getByLabelText("Seller organization"), {
      target: { value: "Andean" },
    });
    fireEvent.click(await screen.findByRole("option", { name: "Andean Coffee Exporters CO" }));
    fireEvent.click(screen.getByRole("button", { name: "Create deal" }));

    await waitFor(() => expect(onCreated).toHaveBeenCalledWith("deal-1"));
    expect(mockedCreateDeal).toHaveBeenCalledWith({
      buyer_organization_id: BUYER_ID,
      seller_organization_id: SELLER_ID,
    });
  });

  it("shows an API error instead of staying in the submitting state", async () => {
    mockedListOrganizations.mockResolvedValue([organization()]);
    mockedCreateDeal.mockRejectedValue(new ApiError(403, "Forbidden"));

    render(<CreateDealPage onCreated={vi.fn()} />);
    await screen.findByLabelText("Buyer organization");

    fireEvent.change(screen.getByLabelText("Seller organization"), {
      target: { value: "Andean" },
    });
    fireEvent.click(await screen.findByRole("option", { name: "Andean Coffee Exporters CO" }));
    fireEvent.click(screen.getByRole("button", { name: "Create deal" }));

    expect(
      await screen.findByText("You cannot create a deal for that buyer organization."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create deal" })).toBeEnabled();
  });
  it("debounces the latest query for 250 ms and encodes it", async () => {
    mockedListOrganizations.mockResolvedValue([organization()]);
    render(<CreateDealPage onCreated={vi.fn()} />);
    const input = await screen.findByRole("combobox", { name: "Seller organization" });
    vi.useFakeTimers();
    fireEvent.change(input, { target: { value: "And" } });
    await act(() => vi.advanceTimersByTimeAsync(200));
    fireEvent.change(input, { target: { value: "Andean & Co" } });
    await act(() => vi.advanceTimersByTimeAsync(249));
    expect(mockedSearch).not.toHaveBeenCalled();
    expect(screen.getByRole("status")).toHaveTextContent("Searching");
    await act(() => vi.advanceTimersByTimeAsync(1));
    expect(mockedSearch).toHaveBeenCalledExactlyOnceWith(
      "/organizations/directory?q=Andean%20%26%20Co", { signal: expect.any(AbortSignal) });
    expect(screen.getByRole("option", { name: "Andean Coffee Exporters CO" })).toBeInTheDocument();
    expect(screen.queryByText(SELLER_ID)).not.toBeInTheDocument();
  });

  it("supports keyboard selection, dismissal, and invalidates an edited selection", async () => {
    mockedListOrganizations.mockResolvedValue([organization()]);
    render(<CreateDealPage onCreated={vi.fn()} />);
    const input = await screen.findByRole("combobox", { name: "Seller organization" });
    fireEvent.change(input, { target: { value: "Andean" } });
    await screen.findByRole("listbox");
    expect(input).toHaveAttribute("aria-controls", "seller-results");
    fireEvent.keyDown(input, { key: "ArrowUp" });
    expect(input).toHaveAttribute("aria-activedescendant", "seller-option-0");
    fireEvent.keyDown(input, { key: "Escape" });
    expect(input).toHaveAttribute("aria-expanded", "false");
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(input).toHaveValue("Andean Coffee Exporters");
    expect(mockedCreateDeal).not.toHaveBeenCalled();
    fireEvent.change(input, { target: { value: "Andean Coffee" } });
    fireEvent.click(screen.getByRole("button", { name: "Create deal" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Choose a seller organization");
    expect(mockedCreateDeal).not.toHaveBeenCalled();
  });

  it("revalidates when the acting buyer changes to the selected seller", async () => {
    mockedListOrganizations.mockResolvedValue([organization(), organization({ id: SELLER_ID, legal_name: "Andean Coffee Exporters" })]);
    render(<CreateDealPage onCreated={vi.fn()} />);
    const input = await screen.findByLabelText("Seller organization");
    fireEvent.change(input, { target: { value: "Andean" } });
    fireEvent.click(await screen.findByRole("option", { name: "Andean Coffee Exporters CO" }));
    fireEvent.change(screen.getByLabelText("Buyer organization"), { target: { value: SELLER_ID } });
    expect(screen.getByRole("alert")).toHaveTextContent("different organizations");
    fireEvent.click(screen.getByRole("button", { name: "Create deal" }));
    expect(mockedCreateDeal).not.toHaveBeenCalled();
  });

  it("shows search errors, retries, and explains empty results", async () => {
    mockedListOrganizations.mockResolvedValue([organization()]);
    mockedSearch.mockRejectedValueOnce(new ApiError(503, "Directory unavailable"));
    render(<CreateDealPage onCreated={vi.fn()} />);
    fireEvent.change(await screen.findByLabelText("Seller organization"), { target: { value: "Andean" } });
    expect(await screen.findByRole("alert")).toHaveTextContent("Directory unavailable");
    mockedSearch.mockResolvedValueOnce([]);
    fireEvent.click(screen.getByRole("button", { name: "Retry search" }));
    expect(await screen.findByText(/No organizations found/)).toBeInTheDocument();
    expect(mockedSearch).toHaveBeenCalledTimes(2);
  });

  it.each([false, true])("ignores obsolete search completion (rejection: %s) and aborts on unmount", async (rejectOld) => {
    mockedListOrganizations.mockResolvedValue([organization()]);
    let resolveOld!: (value: Organization[]) => void;
    let reject!: (reason: Error) => void;
    mockedSearch.mockImplementationOnce(() => new Promise((resolve, rejectPromise) => {
      resolveOld = resolve;
      reject = rejectPromise;
    }));
    const { unmount } = render(<CreateDealPage onCreated={vi.fn()} />);
    const input = await screen.findByLabelText("Seller organization");
    vi.useFakeTimers();
    fireEvent.change(input, { target: { value: "Old" } });
    await act(() => vi.advanceTimersByTimeAsync(250));
    const oldSignal = mockedSearch.mock.calls[0][1]?.signal;
    fireEvent.change(input, { target: { value: "Andean" } });
    expect(oldSignal?.aborted).toBe(true);
    await act(() => vi.advanceTimersByTimeAsync(250));
    await act(async () => {
      if (rejectOld) reject(new Error("obsolete error"));
      else resolveOld([organization({ legal_name: "Obsolete" })]);
    });
    expect(screen.getByRole("option", { name: "Andean Coffee Exporters CO" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByText("Obsolete")).not.toBeInTheDocument();
    const latestSignal = mockedSearch.mock.calls[1][1]?.signal;
    unmount();
    expect(latestSignal?.aborted).toBe(true);
  });

  it("cancels pending debounce on unmount and blank input", async () => {
    mockedListOrganizations.mockResolvedValue([organization()]);
    const { unmount } = render(<CreateDealPage onCreated={vi.fn()} />);
    const input = await screen.findByLabelText("Seller organization");
    vi.useFakeTimers();
    fireEvent.change(input, { target: { value: "Andean" } });
    fireEvent.change(input, { target: { value: "  " } });
    await act(() => vi.advanceTimersByTimeAsync(250));
    expect(mockedSearch).not.toHaveBeenCalled();
    fireEvent.change(input, { target: { value: "Andean" } });
    unmount();
    await act(() => vi.advanceTimersByTimeAsync(250));
    expect(mockedSearch).not.toHaveBeenCalled();
  });

  it("selects the exact company among duplicate names and locks the pending submission", async () => {
    mockedListOrganizations.mockResolvedValue([organization()]);
    mockedSearch.mockResolvedValue([
      organization({ id: "other-seller", legal_name: "Andean Coffee Exporters", country_code: "PE" }),
      organization({ id: SELLER_ID, legal_name: "Andean Coffee Exporters", country_code: "CO" }),
    ]);
    let finish!: (deal: Awaited<ReturnType<typeof createDeal>>) => void;
    mockedCreateDeal.mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
    const onCreated = vi.fn();
    render(<CreateDealPage onCreated={onCreated} />);
    const input = await screen.findByLabelText("Seller organization");
    fireEvent.change(input, { target: { value: "Andean" } });
    fireEvent.click(await screen.findByRole("option", { name: "Andean Coffee Exporters CO" }));
    fireEvent.click(screen.getByRole("button", { name: "Create deal" }));
    expect(input).toBeDisabled();
    expect(screen.getByLabelText("Buyer organization")).toBeDisabled();
    fireEvent.submit(input.closest("form")!);
    expect(mockedCreateDeal).toHaveBeenCalledExactlyOnceWith({
      buyer_organization_id: BUYER_ID, seller_organization_id: SELLER_ID,
    });
    await act(async () => finish({ id: "deal-duplicate", buyer_organization_id: BUYER_ID,
      seller_organization_id: SELLER_ID, status: "DRAFT", version: 0 }));
    expect(onCreated).toHaveBeenCalledWith("deal-duplicate");
  });

});
