import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, getApprovalRoutingPolicy, putApprovalRoutingPolicy } from "../api/client";
import type { ApprovalRoutingPolicy, Organization, OrganizationMember } from "../api/types";
import ApprovalRoutingSection from "./ApprovalRoutingSection";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    getApprovalRoutingPolicy: vi.fn(),
    putApprovalRoutingPolicy: vi.fn(),
    deleteApprovalRoutingPolicy: vi.fn(),
  };
});

const mockedGet = vi.mocked(getApprovalRoutingPolicy);
const mockedPut = vi.mocked(putApprovalRoutingPolicy);

const ORG: Organization = { id: "org-1", legal_name: "Test Corp", country_code: "US", role: "ADMIN" };

const APPROVER: OrganizationMember = {
  user_id: "user-approver",
  email: "approver@test.com",
  display_name: "Approver One",
  role: "MEMBER",
  status: "ACTIVE",
  capabilities: ["AGREEMENT_APPROVAL"],
  version: 1,
};

const NON_APPROVER: OrganizationMember = {
  user_id: "user-plain",
  email: "plain@test.com",
  display_name: "No Approval Rights",
  role: "MEMBER",
  status: "ACTIVE",
  capabilities: ["DRAFTING"],
  version: 1,
};

describe("ApprovalRoutingSection", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("shows the default-bilateral message when no policy is configured, and hides ineligible members from the approver picker", async () => {
    mockedGet.mockResolvedValue(null);
    render(<ApprovalRoutingSection organization={ORG} members={[APPROVER, NON_APPROVER]} />);

    await screen.findByText(/no approval routing configured/i);
    fireEvent.click(screen.getByRole("button", { name: /configure routing/i }));

    expect(screen.getByText("Approver One")).toBeInTheDocument();
    expect(screen.queryByText("No Approval Rights")).not.toBeInTheDocument();
  });

  it("hides edit controls for non-admin viewers", async () => {
    mockedGet.mockResolvedValue(null);
    render(<ApprovalRoutingSection organization={{ ...ORG, role: "MEMBER" }} members={[APPROVER]} />);

    await screen.findByText(/no approval routing configured/i);
    expect(screen.queryByRole("button", { name: /configure routing/i })).not.toBeInTheDocument();
  });

  it("saves a routing policy and surfaces a 409 conflict as an actionable error", async () => {
    mockedGet.mockResolvedValue(null);
    mockedPut.mockRejectedValueOnce(new ApiError(409, "Approval routing policy conflict; please refresh."));
    render(<ApprovalRoutingSection organization={ORG} members={[APPROVER]} />);

    await screen.findByText(/no approval routing configured/i);
    fireEvent.click(screen.getByRole("button", { name: /configure routing/i }));
    fireEvent.click(screen.getByLabelText("Approver One"));
    fireEvent.click(screen.getByRole("button", { name: /save routing/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/conflict/i);
    expect(mockedPut).toHaveBeenCalledWith("org-1", {
      mode: "PARALLEL",
      approver_user_ids: ["user-approver"],
      expected_version: null,
    });
  });

  it("lets admins remove a configured approver who is no longer eligible", async () => {
    const policy: ApprovalRoutingPolicy = {
      organization_id: "org-1",
      mode: "PARALLEL",
      approver_user_ids: ["user-approver", "user-revoked"],
      version: 3,
    };
    mockedGet.mockResolvedValue(policy);
    mockedPut.mockResolvedValue({ ...policy, approver_user_ids: ["user-approver"], version: 4 });
    render(<ApprovalRoutingSection organization={ORG} members={[APPROVER]} />);

    await screen.findByText("PARALLEL");
    fireEvent.click(screen.getByRole("button", { name: /edit routing/i }));

    expect(screen.getByText(/no longer eligible/i)).toBeInTheDocument();
    const removeButtons = screen.getAllByRole("button", { name: /remove/i });
    fireEvent.click(removeButtons[removeButtons.length - 1]);

    expect(screen.queryByText(/no longer eligible/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /save routing/i }));

    expect(mockedPut).toHaveBeenCalledWith("org-1", {
      mode: "PARALLEL",
      approver_user_ids: ["user-approver"],
      expected_version: 3,
    });
  });
});
