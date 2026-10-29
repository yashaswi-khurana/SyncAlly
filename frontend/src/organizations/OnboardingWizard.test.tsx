import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, createOrganization, listOrganizations } from "../api/client";
import OnboardingWizard, { SUPPORTED_COUNTRIES } from "./OnboardingWizard";

vi.mock("../api/client", () => ({
  createOrganization: vi.fn(),
  listOrganizations: vi.fn(),
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
const mockedListOrganizations = vi.mocked(listOrganizations);

const createdOrg = {
  id: "org-uuid-1234",
  legal_name: "Global Grain Importers Ltd",
  country_code: "DE",
  role: "ADMIN",
};

const timeoutError = new ApiError(
  0,
  null,
  "The SyncAlly API took too long to respond. Please try again.",
);

describe("OnboardingWizard", () => {
  const mockOnComplete = vi.fn();
  const mockOnSignOut = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  function submitOrganization(
    name = "Global Grain Importers Ltd",
    country = "DE",
  ) {
    fireEvent.change(screen.getByLabelText(/company legal name/i), {
      target: { value: name },
    });
    fireEvent.change(screen.getByLabelText(/country code/i), {
      target: { value: country },
    });
    fireEvent.click(screen.getByRole("button", { name: /create/i }));
  }

  it("renders the wizard dialog with Company Legal Name and Country Code inputs with suggestions", () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSignOut={mockOnSignOut} />);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /set up your trading organization/i }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/company legal name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/country code/i)).toBeInTheDocument();

    const countryInput = screen.getByLabelText(/country code/i);
    expect(countryInput).toHaveAttribute("list", "wizard-country-suggestions");
    expect(document.querySelector("#wizard-country-suggestions")).toBeInTheDocument();
  });

  it("populates country suggestions datalist from the JSON country mapping", () => {
    render(<OnboardingWizard onComplete={mockOnComplete} />);

    const datalist = document.querySelector("#wizard-country-suggestions");
    expect(datalist).toBeInTheDocument();
    const options = datalist?.querySelectorAll("option");
    expect(options?.length).toBe(SUPPORTED_COUNTRIES.length);
    expect(SUPPORTED_COUNTRIES.some((c) => c.code === "DE" && c.label === "Germany (DE)")).toBe(true);
    expect(SUPPORTED_COUNTRIES.some((c) => c.code === "US" && c.label === "United States (US)")).toBe(true);
    expect(options?.[0]).toHaveAttribute("value", SUPPORTED_COUNTRIES[0].code);
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

  it("validates that country code is required and must be a two-letter code", async () => {
    render(<OnboardingWizard onComplete={mockOnComplete} />);

    fireEvent.change(screen.getByLabelText(/company legal name/i), {
      target: { value: "Global Grain Importers Ltd" },
    });

    const submitBtn = screen.getByRole("button", { name: /create/i });
    fireEvent.click(submitBtn);

    expect(
      await screen.findByText(/enter a two-letter country code/i),
    ).toBeInTheDocument();
    expect(mockedCreateOrganization).not.toHaveBeenCalled();
  });

  it("allows users to enter any valid two-letter country code outside the common suggestions (e.g. ES)", async () => {
    const spanishOrg = {
      id: "org-spain-1234",
      legal_name: "Aceite de Oliva SL",
      country_code: "ES",
      role: "ADMIN",
    };
    mockedCreateOrganization.mockResolvedValue(spanishOrg);

    render(<OnboardingWizard onComplete={mockOnComplete} />);

    fireEvent.change(screen.getByLabelText(/company legal name/i), {
      target: { value: "Aceite de Oliva SL" },
    });
    fireEvent.change(screen.getByLabelText(/country code/i), {
      target: { value: "es" },
    });

    fireEvent.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(mockedCreateOrganization).toHaveBeenCalledWith({
        legal_name: "Aceite de Oliva SL",
        country_code: "ES",
      });
    });

    expect(mockOnComplete).toHaveBeenCalledWith(spanishOrg);
  });

  it("submits the organization creation and invokes onComplete with created admin organization", async () => {
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
    // A rejected request is not ambiguous, so no reconciliation is needed.
    expect(mockedListOrganizations).not.toHaveBeenCalled();
  });

  it("uses the organization created by an ambiguous attempt instead of creating a duplicate", async () => {
    mockedCreateOrganization.mockRejectedValue(timeoutError);
    mockedListOrganizations.mockResolvedValue([createdOrg]);

    render(<OnboardingWizard onComplete={mockOnComplete} />);
    submitOrganization();

    await waitFor(() => {
      expect(mockOnComplete).toHaveBeenCalledWith(createdOrg);
    });
    expect(mockedCreateOrganization).toHaveBeenCalledTimes(1);
    expect(mockedListOrganizations).toHaveBeenCalledTimes(1);
  });

  it("reconciles before retrying an ambiguous create and retries only when no organization exists", async () => {
    mockedCreateOrganization
      .mockRejectedValueOnce(timeoutError)
      .mockResolvedValueOnce(createdOrg);
    mockedListOrganizations.mockResolvedValue([]);

    render(<OnboardingWizard onComplete={mockOnComplete} />);
    submitOrganization();

    expect(await screen.findByText(timeoutError.message)).toBeInTheDocument();
    expect(mockedCreateOrganization).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(mockOnComplete).toHaveBeenCalledWith(createdOrg);
    });
    expect(mockedListOrganizations).toHaveBeenCalledTimes(2);
    expect(mockedCreateOrganization).toHaveBeenCalledTimes(2);
  });

  it("does not create another organization while an ambiguous result is unconfirmed", async () => {
    mockedCreateOrganization.mockRejectedValue(timeoutError);
    mockedListOrganizations.mockRejectedValue(
      new ApiError(0, null, "Unable to reach the SyncAlly API."),
    );

    render(<OnboardingWizard onComplete={mockOnComplete} />);
    submitOrganization();

    expect(await screen.findByText(/could not confirm/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(mockedListOrganizations).toHaveBeenCalledTimes(2);
    });
    expect(mockedCreateOrganization).toHaveBeenCalledTimes(1);
    expect(mockOnComplete).not.toHaveBeenCalled();
  });

  it("does not display creation failure if onComplete throws after successful createOrganization", async () => {
    mockedCreateOrganization.mockResolvedValue(createdOrg);
    const crashingOnComplete = vi.fn().mockImplementation(() => {
      throw new Error("Consumer callback crashed");
    });
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(<OnboardingWizard onComplete={crashingOnComplete} />);
    submitOrganization();

    await waitFor(() => {
      expect(mockedCreateOrganization).toHaveBeenCalledTimes(1);
    });
    expect(crashingOnComplete).toHaveBeenCalledWith(createdOrg);

    // Error alert must NOT be displayed
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByText(/Something went wrong/i)).not.toBeInTheDocument();
    consoleErrorSpy.mockRestore();
  });

  it("does not display creation failure if onComplete throws during ambiguous reconciliation", async () => {
    mockedCreateOrganization.mockRejectedValue(timeoutError);
    mockedListOrganizations.mockResolvedValue([createdOrg]);
    const crashingOnComplete = vi.fn().mockImplementation(() => {
      throw new Error("Consumer callback crashed during reconciliation");
    });
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(<OnboardingWizard onComplete={crashingOnComplete} />);
    submitOrganization();

    await waitFor(() => {
      expect(mockedListOrganizations).toHaveBeenCalled();
    });
    expect(crashingOnComplete).toHaveBeenCalledWith(createdOrg);

    // Form must NOT show UNCONFIRMED_CREATE_MESSAGE or creation failure alert
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByText(/could not confirm/i)).not.toBeInTheDocument();
    consoleErrorSpy.mockRestore();
  });

  it("allows user to sign out from the wizard", () => {
    render(<OnboardingWizard onComplete={mockOnComplete} onSignOut={mockOnSignOut} />);

    const signOutBtn = screen.getByRole("button", { name: /sign out/i });
    fireEvent.click(signOutBtn);

    expect(mockOnSignOut).toHaveBeenCalledTimes(1);
  });
});

