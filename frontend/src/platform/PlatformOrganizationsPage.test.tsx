import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  listPlatformOrganizationMembers,
  listPlatformOrganizations,
  listPlatformUsers,
  setPlatformOrganizationOwner,
} from "../api/client";
import PlatformOrganizationsPage from "./PlatformOrganizationsPage";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    listPlatformOrganizationMembers: vi.fn(),
    listPlatformOrganizations: vi.fn(),
    listPlatformUsers: vi.fn(),
    setPlatformOrganizationOwner: vi.fn(),
  };
});

const mockedOrganizations = vi.mocked(listPlatformOrganizations);
const mockedMembers = vi.mocked(listPlatformOrganizationMembers);
const mockedUsers = vi.mocked(listPlatformUsers);
const mockedSetOwner = vi.mocked(setPlatformOrganizationOwner);

describe("PlatformOrganizationsPage owner recovery", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it("assigns an active member as owner when the organization has none", async () => {
    mockedOrganizations.mockResolvedValue([{
      id: "org-no-owner",
      legal_name: "Recovered Co",
      country_code: "US",
      status: "ACTIVE",
      created_at: "2026-01-01T00:00:00Z",
      owner_user_id: null,
    }]);
    mockedUsers.mockResolvedValue([]);
    mockedMembers.mockResolvedValue([{
      user_id: "user-active",
      email: "owner@example.com",
      display_name: "New Owner",
      is_owner: false,
    }]);
    mockedSetOwner.mockResolvedValue({
      organization_id: "org-no-owner",
      owner_user_id: "user-active",
      status: "transferred",
    });
    window.confirm = vi.fn().mockReturnValue(true);

    render(<PlatformOrganizationsPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Recover owner" }));

    expect(await screen.findByRole("heading", { name: "Organization owner" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Reason"), { target: { value: "Owner account was removed" } });
    fireEvent.click(screen.getByRole("button", { name: "Save owner" }));

    await waitFor(() => {
      expect(mockedSetOwner).toHaveBeenCalledWith("org-no-owner", "user-active", "Owner account was removed");
    });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByText("user-active")).toBeInTheDocument();
  });
});
