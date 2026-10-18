import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, createDeal, listOrganizations } from "../api/client";
import type { Organization } from "../api/types";
import CreateDealPage from "./CreateDealPage";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    listOrganizations: vi.fn(),
    createDeal: vi.fn(),
  };
});

const mockedListOrganizations = vi.mocked(listOrganizations);
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
    vi.clearAllMocks();
    window.location.hash = "";
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("shows a loading state and then the create form", async () => {
    mockedListOrganizations.mockResolvedValue([organization()]);

    render(<CreateDealPage onCreated={vi.fn()} />);

    expect(screen.getByRole("status")).toHaveTextContent(/loading organizations/i);
    expect(await screen.findByLabelText("Buyer organization")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create deal" })).toBeInTheDocument();
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

  it("validates required and malformed seller input before submitting", async () => {
    mockedListOrganizations.mockResolvedValue([organization()]);
    const onCreated = vi.fn();

    render(<CreateDealPage onCreated={onCreated} />);
    await screen.findByLabelText("Buyer organization");

    fireEvent.click(screen.getByRole("button", { name: "Create deal" }));
    expect(await screen.findByText("Enter the seller organization ID.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Seller organization ID"), {
      target: { value: "not-a-uuid" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create deal" }));
    expect(await screen.findByText("Enter a valid organization ID (UUID).")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Seller organization ID"), {
      target: { value: BUYER_ID },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create deal" }));
    expect(
      await screen.findByText("Buyer and seller must be different organizations."),
    ).toBeInTheDocument();

    expect(mockedCreateDeal).not.toHaveBeenCalled();
    expect(onCreated).not.toHaveBeenCalled();
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

    fireEvent.change(screen.getByLabelText("Seller organization ID"), {
      target: { value: SELLER_ID },
    });
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

    fireEvent.change(screen.getByLabelText("Seller organization ID"), {
      target: { value: SELLER_ID },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create deal" }));

    expect(
      await screen.findByText("You cannot create a deal for that buyer organization."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create deal" })).toBeEnabled();
  });
});
