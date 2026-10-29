import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, createOrganization } from "../api/client";
import OnboardingWizard from "./OnboardingWizard";

vi.mock("../api/client", () => ({
  createOrganization: vi.fn(),
  ApiError: class ApiError extends Error {
    constructor(
      public status: number,
      public detail: unknown = null,
      message?: string,
    ) {
      super(message || "API Error");
      this.name = "ApiError";
    }
  },
}));

const mockedCreateOrganization = vi.mocked(createOrganization);

describe("OnboardingWizard", () => {
  const mockOnComplete = vi.fn();
  const mockOnSignOut = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the wizard dialog with Company Legal Name input and Country Code dropdown", () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSignOut={mockOnSignOut} />);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /set up your trading organization/i }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/company legal name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/country code/i)).toBeInTheDocument();

    const countrySelect = screen.getByLabelText(/country code/i) as HTMLSelectElement;
    expect(countrySelect).toBeInTheDocument();
    // Verify dropdown includes DE, US, GB
    expect(screen.getByRole("option", { name: /germany \(de\)/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /united states \(us\)/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /united kingdom \(gb\)/i })).toBeInTheDocument();
  });

  it("validates that company legal name is required", async () => {
    render(<OnboardingWizard onComplete={mockOnComplete} />);

    const submitBtn = screen.getByRole("button", { name: /create/i });
    fireEvent.click(submitBtn);

    expect(
      await screen.findByText(/enter your company legal name/i),
    ).toBeInTheDocument();
    expect(mockedCreateOrganization).not.toHaveBeenCalled();
    expect(mockOnComplete).not.toHaveBeenCalled();
  });

  it("validates that country code selection is required", async () => {
    render(<OnboardingWizard onComplete={mockOnComplete} />);

    fireEvent.change(screen.getByLabelText(/company legal name/i), {
      target: { value: "Global Grain Importers Ltd" },
    });

    const submitBtn = screen.getByRole("button", { name: /create/i });
    fireEvent.click(submitBtn);

    expect(
      await screen.findByText(/select a two-letter country code/i),
    ).toBeInTheDocument();
    expect(mockedCreateOrganization).not.toHaveBeenCalled();
  });

  it("submits the organization creation and invokes onComplete with created admin organization", async () => {
    const createdOrg = {
      id: "org-uuid-1234",
      legal_name: "Global Grain Importers Ltd",
      country_code: "DE",
      role: "ADMIN",
    };
    mockedCreateOrganization.mockResolvedValue(createdOrg);

    render(<OnboardingWizard onComplete={mockOnComplete} onSignOut={mockOnSignOut} />);

    fireEvent.change(screen.getByLabelText(/company legal name/i), {
      target: { value: "  Global Grain Importers Ltd  " },
    });
    fireEvent.change(screen.getByLabelText(/country code/i), {
      target: { value: "DE" },
    });

    fireEvent.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(mockedCreateOrganization).toHaveBeenCalledWith({
        legal_name: "Global Grain Importers Ltd",
        country_code: "DE",
      });
    });

    expect(mockOnComplete).toHaveBeenCalledWith(createdOrg);
  });

  it("displays server error when organization creation fails", async () => {
    mockedCreateOrganization.mockRejectedValue(
      new ApiError(409, null, "Organization limit reached for this account"),
    );

    render(<OnboardingWizard onComplete={mockOnComplete} />);

    fireEvent.change(screen.getByLabelText(/company legal name/i), {
      target: { value: "Global Grain Importers Ltd" },
    });
    fireEvent.change(screen.getByLabelText(/country code/i), {
      target: { value: "US" },
    });

    fireEvent.click(screen.getByRole("button", { name: /create/i }));

    expect(
      await screen.findByText("Organization limit reached for this account"),
    ).toBeInTheDocument();
    expect(mockOnComplete).not.toHaveBeenCalled();
  });

  it("allows user to sign out from the wizard", () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSignOut={mockOnSignOut} />);

    const signOutBtn = screen.getByRole("button", { name: /sign out/i });
    fireEvent.click(signOutBtn);

    expect(mockOnSignOut).toHaveBeenCalledTimes(1);
  });
});

