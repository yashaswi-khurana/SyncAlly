import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  listOrganizationMembers,
  revokeOrganizationMember,
  updateMemberPermissions,
} from "../api/client";
import { clearAccessToken, setAccessToken } from "../api/tokenStore";
import type { Organization, OrganizationMember } from "../api/types";
import OrganizationMembersSection from "./OrganizationMembersSection";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    listOrganizationMembers: vi.fn(),
    updateMemberPermissions: vi.fn(),
    revokeOrganizationMember: vi.fn(),
  };
});

const mockedListMembers = vi.mocked(listOrganizationMembers);
const mockedUpdatePermissions = vi.mocked(updateMemberPermissions);
const mockedRevokeMember = vi.mocked(revokeOrganizationMember);

const ORG_ID = "org-1111-1111";
const CURRENT_USER_ID = "user-self-9999";
const OTHER_USER_ID = "user-other-8888";

function mockAuthToken(userId: string) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = btoa(JSON.stringify({ sub: userId, exp: 9999999999 }));
  setAccessToken(`${header}.${payload}.signature`);
}

function testOrg(role: "ADMIN" | "MEMBER" = "ADMIN"): Organization {
  return {
    id: ORG_ID,
    legal_name: "Test Corp",
    country_code: "US",
    role,
  };
}

describe("OrganizationMembersSection", () => {
  beforeEach(() => {
    mockAuthToken(CURRENT_USER_ID);
  });

  afterEach(() => {
    vi.clearAllMocks();
    clearAccessToken();
  });

  it("renders members list with capability badges and version", async () => {
    const members: OrganizationMember[] = [
      {
        user_id: CURRENT_USER_ID,
        email: "admin@test.com",
        display_name: "Admin Self",
        role: "ADMIN",
        status: "ACTIVE",
        capabilities: ["ADMINISTRATION", "DRAFTING", "AGREEMENT_APPROVAL"],
        version: 1,
      },
      {
        user_id: OTHER_USER_ID,
        email: "colleague@test.com",
        display_name: "Colleague",
        role: "MEMBER",
        status: "ACTIVE",
        capabilities: ["DRAFTING", "FINANCE"],
        assigned_capabilities: ["FINANCE"],
        version: 2,
      },
    ];
    mockedListMembers.mockResolvedValue(members);

    render(<OrganizationMembersSection organization={testOrg()} />);

    expect(await screen.findByText("Team Members & Permissions")).toBeInTheDocument();
    expect(screen.getByText("Admin Self")).toBeInTheDocument();
    expect(screen.getByText("You")).toBeInTheDocument();
    expect(screen.getByText("Cannot self-modify")).toBeInTheDocument();

    expect(screen.getByText("Colleague")).toBeInTheDocument();
    expect(screen.getByText("FINANCE")).toBeInTheDocument();
    expect(screen.getByText("v2")).toBeInTheDocument();
  });

  it("allows admin to edit other member permissions and submit updates", async () => {
    const member: OrganizationMember = {
      user_id: OTHER_USER_ID,
      email: "colleague@test.com",
      role: "MEMBER",
      status: "ACTIVE",
      capabilities: ["DRAFTING"],
      assigned_capabilities: [],
      version: 1,
    };
    mockedListMembers.mockResolvedValue([
      {
        user_id: CURRENT_USER_ID,
        email: "admin@test.com",
        role: "ADMIN",
        status: "ACTIVE",
        capabilities: ["ADMINISTRATION", "DRAFTING", "AGREEMENT_APPROVAL"],
        version: 1,
      },
      member,
    ]);

    mockedUpdatePermissions.mockResolvedValue({
      ...member,
      capabilities: ["DRAFTING", "FINANCE"],
      assigned_capabilities: ["FINANCE"],
      version: 2,
    });

    render(<OrganizationMembersSection organization={testOrg()} />);

    expect(await screen.findByText("colleague@test.com")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Edit permissions"));

    expect(screen.getByText(/Editing permissions for colleague@test.com/)).toBeInTheDocument();

    // Toggle Finance capability
    const financeCheckbox = screen.getByLabelText(/Finance/);
    fireEvent.click(financeCheckbox);

    // Save changes
    fireEvent.click(screen.getByText("Save changes"));

    await waitFor(() => {
      expect(mockedUpdatePermissions).toHaveBeenCalledWith(ORG_ID, OTHER_USER_ID, {
        expected_version: 1,
        role: "MEMBER",
        capabilities: ["FINANCE"],
      });
    });

    expect(await screen.findByText("Updated permissions for colleague@test.com.")).toBeInTheDocument();
  });

  it("displays actionable error state on 409 conflict", async () => {
    const member: OrganizationMember = {
      user_id: OTHER_USER_ID,
      email: "colleague@test.com",
      role: "MEMBER",
      status: "ACTIVE",
      capabilities: ["DRAFTING"],
      version: 1,
    };
    mockedListMembers.mockResolvedValue([
      {
        user_id: CURRENT_USER_ID,
        email: "admin@test.com",
        role: "ADMIN",
        status: "ACTIVE",
        capabilities: ["ADMINISTRATION", "DRAFTING", "AGREEMENT_APPROVAL"],
        version: 1,
      },
      member,
    ]);

    mockedUpdatePermissions.mockRejectedValue(
      new ApiError(409, "Member permissions conflict; please refresh")
    );

    render(<OrganizationMembersSection organization={testOrg()} />);

    expect(await screen.findByText("Edit permissions")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Edit permissions"));
    fireEvent.click(screen.getByText("Save changes"));

    expect(
      await screen.findByText("Member permissions conflict; please refresh")
    ).toBeInTheDocument();
  });

  it("displays actionable error state on 403 self-escalation attempt", async () => {
    const member: OrganizationMember = {
      user_id: OTHER_USER_ID,
      email: "colleague@test.com",
      role: "MEMBER",
      status: "ACTIVE",
      capabilities: ["DRAFTING"],
      version: 1,
    };
    mockedListMembers.mockResolvedValue([member]);

    mockedUpdatePermissions.mockRejectedValue(
      new ApiError(403, "Cannot modify your own membership role or capabilities")
    );

    render(<OrganizationMembersSection organization={testOrg()} />);

    expect(await screen.findByText("Edit permissions")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Edit permissions"));
    fireEvent.click(screen.getByText("Save changes"));

    expect(
      await screen.findByText("Cannot modify your own membership role or capabilities")
    ).toBeInTheDocument();
  });

  it("handles member revocation", async () => {
    const member: OrganizationMember = {
      user_id: OTHER_USER_ID,
      email: "colleague@test.com",
      role: "MEMBER",
      status: "ACTIVE",
      capabilities: ["DRAFTING"],
      version: 1,
    };
    mockedListMembers.mockResolvedValue([
      {
        user_id: CURRENT_USER_ID,
        email: "admin@test.com",
        role: "ADMIN",
        status: "ACTIVE",
        capabilities: ["ADMINISTRATION"],
        version: 1,
      },
      member,
    ]);
    mockedRevokeMember.mockResolvedValue(undefined);
    window.confirm = vi.fn().mockReturnValue(true);

    render(<OrganizationMembersSection organization={testOrg()} />);

    expect(await screen.findByText("Revoke")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Revoke"));

    await waitFor(() => {
      expect(mockedRevokeMember).toHaveBeenCalledWith(ORG_ID, OTHER_USER_ID);
    });

    expect(await screen.findByText("Revoked membership for colleague@test.com.")).toBeInTheDocument();
  });
});
