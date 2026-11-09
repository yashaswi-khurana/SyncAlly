import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  getApprovalRoutingPolicy,
  listAssignableOrganizationDeals,
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
    getApprovalRoutingPolicy: vi.fn(),
    listAssignableOrganizationDeals: vi.fn(),
  };
});

const mockedListMembers = vi.mocked(listOrganizationMembers);
const mockedUpdatePermissions = vi.mocked(updateMemberPermissions);
const mockedRevokeMember = vi.mocked(revokeOrganizationMember);
const mockedGetApprovalRoutingPolicy = vi.mocked(getApprovalRoutingPolicy);
const mockedListAssignableDeals = vi.mocked(listAssignableOrganizationDeals);

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
    mockedGetApprovalRoutingPolicy.mockResolvedValue(null);
    mockedListAssignableDeals.mockResolvedValue([]);
  });

  afterEach(() => {
    vi.clearAllMocks();
    clearAccessToken();
  });

  it("renders member role bundles and grant version", async () => {
    const members: OrganizationMember[] = [
      {
        user_id: CURRENT_USER_ID,
        email: "admin@test.com",
        display_name: "Admin Self",
        role: "ADMIN",
        status: "ACTIVE",
        capabilities: [],
        role_bundles: ["ORG_ADMIN"],
        permissions: [],
        deal_ids: [],
        is_owner: false,
        version: 1,
      },
      {
        user_id: OTHER_USER_ID,
        email: "colleague@test.com",
        display_name: "Colleague",
        role: "MEMBER",
        status: "ACTIVE",
        capabilities: [],
        role_bundles: ["FINANCE"],
        permissions: [],
        deal_ids: [],
        is_owner: false,
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

  it("allows an admin to grant a bundle and an individual deal assignment", async () => {
    mockedListAssignableDeals.mockResolvedValue([
      { id: "deal-1", display_name: "Deal One", status: "OPEN" },
    ]);
    const member: OrganizationMember = {
      user_id: OTHER_USER_ID,
      email: "colleague@test.com",
      role: "MEMBER",
      status: "ACTIVE",
      capabilities: [],
      role_bundles: [],
      permissions: [],
      deal_ids: [],
      is_owner: false,
      version: 1,
    };
    mockedListMembers.mockResolvedValue([
      {
        user_id: CURRENT_USER_ID,
        email: "admin@test.com",
        role: "ADMIN",
        status: "ACTIVE",
        capabilities: [],
        role_bundles: ["ORG_ADMIN"],
        permissions: [],
        deal_ids: [],
        is_owner: false,
        version: 1,
      },
      member,
    ]);

    mockedUpdatePermissions.mockResolvedValue({
      ...member,
      role_bundles: ["FINANCE"],
      permissions: [],
      deal_ids: ["deal-1"],
      is_owner: false,
      version: 2,
    });

    render(<OrganizationMembersSection organization={testOrg()} />);

    expect(await screen.findByText("colleague@test.com")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Edit permissions"));

    expect(screen.getByText(/Editing permissions for colleague@test.com/)).toBeInTheDocument();

    fireEvent.click(await screen.findByLabelText("FINANCE"));
    fireEvent.click(screen.getByLabelText("Deal One (OPEN)"));

    // Save changes
    fireEvent.click(screen.getByText("Save changes"));

    await waitFor(() => {
      expect(mockedUpdatePermissions).toHaveBeenCalledWith(ORG_ID, OTHER_USER_ID, {
        expected_version: 1,
        role_bundles: ["FINANCE"],
        permissions: [],
        deal_ids: ["deal-1"],
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
      capabilities: [],
      role_bundles: [],
      permissions: [],
      deal_ids: [],
      version: 1,
    };
    mockedListMembers.mockResolvedValue([
      {
        user_id: CURRENT_USER_ID,
        email: "admin@test.com",
        role: "ADMIN",
        status: "ACTIVE",
        capabilities: [],
        role_bundles: ["ORG_ADMIN"],
        permissions: [],
        deal_ids: [],
        is_owner: false,
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

  it("decodes user ID from a base64url token payload containing '-' and '_' to disable self-modification", async () => {
    // Payload json: {"sub":"user-base64url-9999","a":"x>","b":" ?"}
    // Base64: eyJzdWIiOiJ1c2VyLWJhc2U2NHVybC05OTk5IiwiYSI6Ing+IiwiYiI6IiA/In0=
    // Base64url contains both '-' and '_':
    const b64urlPayload = "eyJzdWIiOiJ1c2VyLWJhc2U2NHVybC05OTk5IiwiYSI6Ing-IiwiYiI6IiA_In0";
    expect(b64urlPayload).toContain("-");
    expect(b64urlPayload).toContain("_");

    const base64urlUserId = "user-base64url-9999";
    setAccessToken(`header.${b64urlPayload}.sig`);

    const members: OrganizationMember[] = [
      {
        user_id: base64urlUserId,
        email: "base64url@test.com",
        display_name: "Self User",
        role: "ADMIN",
        status: "ACTIVE",
        capabilities: ["ADMINISTRATION", "DRAFTING", "AGREEMENT_APPROVAL"],
        version: 1,
      },
    ];
    mockedListMembers.mockResolvedValue(members);

    render(<OrganizationMembersSection organization={testOrg()} />);

    expect(await screen.findByText("Self User")).toBeInTheDocument();
    expect(screen.getByText("You")).toBeInTheDocument();
    expect(screen.getByText("Cannot self-modify")).toBeInTheDocument();
    expect(screen.queryByText("Edit permissions")).not.toBeInTheDocument();
  });

  it("handles missing or malformed token payloads without crashing", async () => {
    setAccessToken("header.malformed-base64-or-json@@@.sig");

    const members: OrganizationMember[] = [
      {
        user_id: OTHER_USER_ID,
        email: "other@test.com",
        display_name: "Other User",
        role: "MEMBER",
        status: "ACTIVE",
        capabilities: ["DRAFTING"],
        version: 1,
      },
    ];
    mockedListMembers.mockResolvedValue(members);

    render(<OrganizationMembersSection organization={testOrg()} />);

    expect(await screen.findByText("Other User")).toBeInTheDocument();
    expect(screen.queryByText("You")).not.toBeInTheDocument();
    expect(screen.getByText("Edit permissions")).toBeInTheDocument();
  });
});
