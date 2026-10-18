import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, listOrganizations } from "../api/client";
import type { Organization } from "../api/types";
import OrganizationsPanel from "./OrganizationsPanel";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    listOrganizations: vi.fn(),
  };
});

const mockedListOrganizations = vi.mocked(listOrganizations);

const ORG_ID = "33333333-3333-3333-3333-333333333333";

function organization(overrides: Partial<Organization> = {}): Organization {
  return {
    id: ORG_ID,
    legal_name: "Demo Seller Co",
    country_code: "US",
    role: "ADMIN",
    ...overrides,
  };
}

describe("OrganizationsPanel", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it("lists each organization with the ID to share", async () => {
    mockedListOrganizations.mockResolvedValue([organization()]);

    render(<OrganizationsPanel />);

    expect(screen.getByRole("status")).toHaveTextContent(/loading your organizations/i);
    expect(await screen.findByText("Demo Seller Co (US)")).toBeInTheDocument();
    expect(screen.getByText(ORG_ID)).toBeInTheDocument();
  });

  it("shows an empty state when the account has no organizations", async () => {
    mockedListOrganizations.mockResolvedValue([]);

    render(<OrganizationsPanel />);

    expect(await screen.findByText(/not an active member of any organization/i)).toBeInTheDocument();
  });

  it("shows an error state that can be retried", async () => {
    mockedListOrganizations.mockRejectedValueOnce(new ApiError(500, "Server error"));

    render(<OrganizationsPanel />);

    expect(
      await screen.findByRole("heading", { name: /could not load your organizations/i }),
    ).toBeInTheDocument();

    mockedListOrganizations.mockResolvedValueOnce([organization()]);
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByText(ORG_ID)).toBeInTheDocument();
    expect(mockedListOrganizations).toHaveBeenCalledTimes(2);
  });

  it("copies the organization ID to the clipboard", async () => {
    mockedListOrganizations.mockResolvedValue([organization()]);
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });

    render(<OrganizationsPanel />);
    await screen.findByText(ORG_ID);

    fireEvent.click(screen.getByRole("button", { name: "Copy ID" }));

    expect(writeText).toHaveBeenCalledWith(ORG_ID);
    expect(await screen.findByRole("button", { name: "Copied" })).toBeInTheDocument();
  });
});
