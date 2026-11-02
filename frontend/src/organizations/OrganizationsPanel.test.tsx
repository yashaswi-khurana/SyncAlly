import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, getOrganizationProfile, listOrganizations, updateOrganizationProfile } from "../api/client";
import type { Organization, OrganizationProfile } from "../api/types";
import OrganizationsPanel from "./OrganizationsPanel";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    listOrganizations: vi.fn(),
    getOrganizationProfile: vi.fn(),
    updateOrganizationProfile: vi.fn(),
  };
});

const mockedListOrganizations = vi.mocked(listOrganizations);
const mockedGetOrganizationProfile = vi.mocked(getOrganizationProfile);
const mockedUpdateOrganizationProfile = vi.mocked(updateOrganizationProfile);

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

function sampleProfile(overrides: Partial<OrganizationProfile> = {}): OrganizationProfile {
  return {
    organization_id: ORG_ID,
    capabilities: ["Freight Forwarding", "Logistics"],
    products: ["Bulk Grain", "Corn"],
    regions: ["US", "CA"],
    contacts: [
      {
        id: "c1",
        name: "Alice Lead",
        purpose: "Operations",
        visibility: "PRIVATE",
        email: "alice@demoseller.com",
        phone: "+1-555-0199",
      },
    ],
    verification_status: "UNVERIFIED",
    version: 1,
    ...overrides,
  };
}

describe("OrganizationsPanel", () => {
  beforeEach(() => {
    mockedGetOrganizationProfile.mockResolvedValue(sampleProfile());
  });

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

  it("renders organization profile with 4 dimensions and private contact badge", async () => {
    mockedListOrganizations.mockResolvedValue([organization()]);

    render(<OrganizationsPanel />);

    expect(await screen.findByText("Demo Seller Co (US)")).toBeInTheDocument();
    expect(await screen.findByText("Freight Forwarding")).toBeInTheDocument();
    expect(screen.getByText("Bulk Grain")).toBeInTheDocument();
    expect(screen.getByText("Alice Lead")).toBeInTheDocument();
    expect(screen.getByText("Private")).toBeInTheDocument();
    expect(screen.getByText("UNVERIFIED")).toBeInTheDocument();
    expect(screen.getByText("v1")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edit profile" })).toBeInTheDocument();
  });

  it("shows read-only badge and hides edit button for non-admin member", async () => {
    mockedListOrganizations.mockResolvedValue([organization({ role: "MEMBER" })]);

    render(<OrganizationsPanel />);

    expect(await screen.findByText("Demo Seller Co (US)")).toBeInTheDocument();
    expect(await screen.findByText("Read-only (Non-admin)")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit profile" })).not.toBeInTheDocument();
  });

  it("allows admin to edit and save organization profile", async () => {
    mockedListOrganizations.mockResolvedValue([organization()]);
    mockedUpdateOrganizationProfile.mockResolvedValue(
      sampleProfile({
        version: 2,
        capabilities: ["Freight Forwarding", "Logistics", "Cold Storage"],
      }),
    );

    render(<OrganizationsPanel />);

    expect(await screen.findByRole("button", { name: "Edit profile" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Edit profile" }));

    expect(screen.getByRole("button", { name: "Save profile" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();

    const capsInput = screen.getByLabelText(/capabilities/i);
    fireEvent.change(capsInput, {
      target: { value: "Freight Forwarding, Logistics, Cold Storage" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Save profile" }));

    await waitFor(() => {
      expect(mockedUpdateOrganizationProfile).toHaveBeenCalledWith(
        ORG_ID,
        expect.objectContaining({
          expected_version: 1,
          capabilities: ["Freight Forwarding", "Logistics", "Cold Storage"],
        }),
      );
    });

    expect(await screen.findByText("Cold Storage")).toBeInTheDocument();
    expect(screen.getByText("v2")).toBeInTheDocument();
  });

  it("allows admin to cancel editing without saving", async () => {
    mockedListOrganizations.mockResolvedValue([organization()]);

    render(<OrganizationsPanel />);

    expect(await screen.findByRole("button", { name: "Edit profile" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Edit profile" }));

    const capsInput = screen.getByLabelText(/capabilities/i);
    fireEvent.change(capsInput, { target: { value: "Something Else" } });

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(mockedUpdateOrganizationProfile).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Save profile" })).not.toBeInTheDocument();
    expect(screen.getByText("Freight Forwarding")).toBeInTheDocument();
  });

  it("shows stale error with refresh button when saving encounters a 409 conflict", async () => {
    mockedListOrganizations.mockResolvedValue([organization()]);
    mockedUpdateOrganizationProfile.mockRejectedValue(
      new ApiError(409, "Profile version conflict; please refresh"),
    );

    render(<OrganizationsPanel />);

    expect(await screen.findByRole("button", { name: "Edit profile" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Edit profile" }));
    fireEvent.click(screen.getByRole("button", { name: "Save profile" }));

    expect(
      await screen.findByText(/profile was updated by another session/i),
    ).toBeInTheDocument();

    const refreshButton = screen.getByRole("button", { name: "Refresh profile" });
    expect(refreshButton).toBeInTheDocument();

    mockedGetOrganizationProfile.mockResolvedValueOnce(
      sampleProfile({
        version: 3,
        capabilities: ["Updated Remotely"],
      }),
    );
    fireEvent.click(refreshButton);

    expect(await screen.findByText("Updated Remotely")).toBeInTheDocument();
    expect(screen.getByText("v3")).toBeInTheDocument();
  });

  it("displays empty states when profile dimensions are empty", async () => {
    mockedListOrganizations.mockResolvedValue([organization()]);
    mockedGetOrganizationProfile.mockResolvedValue(
      sampleProfile({
        capabilities: [],
        products: [],
        regions: [],
        contacts: [],
      }),
    );

    render(<OrganizationsPanel />);

    expect(await screen.findByText("No capabilities listed")).toBeInTheDocument();
    expect(screen.getByText("No products listed")).toBeInTheDocument();
    expect(screen.getByText("No regions listed")).toBeInTheDocument();
    expect(screen.getByText("No contacts listed.")).toBeInTheDocument();
  });
});
