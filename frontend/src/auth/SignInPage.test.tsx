import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiRequest, login } from "../api/client";
import SignInPage from "./SignInPage";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    apiRequest: vi.fn(),
    login: vi.fn(),
  };
});

const mockedApiRequest = vi.mocked(apiRequest);
const mockedLogin = vi.mocked(login);

describe("SignInPage", () => {
  function typedToken(kind: "TEAM" | "COUNTERPARTY") {
    return `header.${btoa(JSON.stringify({ version: 1, kind, recipient_email: "recipient@example.com" }))}.signature`;
  }

  it("typed TEAM acceptance never submits own-organization details and resets on a new token", async () => {
    const token = typedToken("TEAM");
    window.location.hash = `#/invite?token=${token}`;
    mockedApiRequest.mockRejectedValueOnce(new ApiError(403, "Invitation is addressed to a different account"));
    render(<SignInPage onSignIn={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "Join your team." })).toBeInTheDocument();
    expect(screen.queryByLabelText(/Company Legal Name/)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "wrong@example.com" } });
    fireEvent.change(screen.getByLabelText(/Password \(12/), { target: { value: "SecurePassword123!" } });
    fireEvent.click(screen.getByRole("button", { name: "Accept team invitation" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("different account");
    expect(mockedApiRequest).toHaveBeenCalledWith("/invitations/accept", expect.objectContaining({ body: JSON.stringify({ token, email: "wrong@example.com", password: "SecurePassword123!" }) }));
    window.location.hash = `#/invite?token=${typedToken("COUNTERPARTY")}`;
    fireEvent(window, new Event("hashchange"));
    expect(await screen.findByLabelText("Company Legal Name")).toHaveValue("");
    expect(screen.getByLabelText("Email")).toHaveValue("");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("requires own-company details for typed COUNTERPARTY before acceptance", async () => {
    window.location.hash = `#/invite?token=${typedToken("COUNTERPARTY")}`;
    render(<SignInPage onSignIn={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "recipient@example.com" } });
    fireEvent.change(screen.getByLabelText(/Password \(12/), { target: { value: "SecurePassword123!" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Account & Join Deal" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("company legal name is required");
    expect(mockedApiRequest).not.toHaveBeenCalled();
  });

  it("ignores late acceptance tokens and navigation after the invitation changes", async () => {
    window.location.hash = `#/invite?token=${typedToken("TEAM")}`;
    let resolveAcceptance!: (result: unknown) => void;
    mockedApiRequest.mockImplementationOnce(() => new Promise((resolve) => {
      resolveAcceptance = resolve;
    }));
    const onSignIn = vi.fn();
    render(<SignInPage onSignIn={onSignIn} />);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "recipient@example.com" } });
    fireEvent.change(screen.getByLabelText(/Password \(12/), { target: { value: "SecurePassword123!" } });
    fireEvent.click(screen.getByRole("button", { name: "Accept team invitation" }));
    const nextHash = `#/invite?token=${typedToken("COUNTERPARTY")}`;
    window.location.hash = nextHash;
    fireEvent(window, new Event("hashchange"));
    await act(async () => resolveAcceptance({
      access_token: "stale-token", refresh_token: "stale-refresh", deal_id: "stale-deal",
    }));
    expect(onSignIn).not.toHaveBeenCalled();
    expect(window.location.hash).toBe(nextHash);
    expect(screen.getByLabelText("Company Legal Name")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Create Account & Join Deal" })).toBeEnabled();
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllEnvs();
    window.location.hash = "";
  });

  it("validates required fields before calling the API", async () => {
    render(<SignInPage onSignIn={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Enter workspace" }));

    expect(await screen.findByText("Email is required.")).toBeInTheDocument();
    expect(screen.getByText("Password is required.")).toBeInTheDocument();
    expect(mockedLogin).not.toHaveBeenCalled();
  });

  it("explains the trade flow and hides demo quick-fill unless enabled", () => {
    render(<SignInPage onSignIn={vi.fn()} />);

    expect(screen.getByRole("heading", { name: "Cross-Border Trade on Autopilot." })).toBeInTheDocument();
    expect(screen.getByText("Cryptographic Bilateral Approval")).toBeInTheDocument();
    expect(screen.getByText("Automated PayPal Invoicing")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Why SyncAlly" })).toBeInTheDocument();

    expect(screen.queryByRole("button", { name: "Demo Buyer" })).not.toBeInTheDocument();
  });

  it("quick-fills the demo email without assuming the provisioned password", () => {
    vi.stubEnv("VITE_ENABLE_DEMO_QUICK_FILL", "true");
    vi.stubEnv("VITE_APP_ENV", "development");
    render(<SignInPage onSignIn={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Demo Buyer" }));
    expect(screen.getByLabelText("Email")).toHaveValue("buyer@syncally.demo");
    expect(screen.getByLabelText("Password")).toHaveValue("");

    fireEvent.click(screen.getByRole("button", { name: "Demo Seller" }));
    expect(screen.getByLabelText("Email")).toHaveValue("seller@syncally.demo");
    expect(screen.getByLabelText("Password")).toHaveValue("");
  });

  it("only shows demo quick-fill in development or test environments", () => {
    vi.stubEnv("VITE_ENABLE_DEMO_QUICK_FILL", "true");
    vi.stubEnv("VITE_APP_ENV", "production");
    const { rerender } = render(<SignInPage onSignIn={vi.fn()} />);
    expect(screen.queryByRole("button", { name: "Demo Buyer" })).not.toBeInTheDocument();

    vi.stubEnv("VITE_APP_ENV", "test");
    rerender(<SignInPage onSignIn={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Demo Buyer" })).toBeInTheDocument();
  });

  it("signs in and passes the tokens to the caller", async () => {
    const tokens = {
      access_token: "access-token",
      refresh_token: "refresh-token",
      token_type: "bearer",
    };
    mockedLogin.mockResolvedValue(tokens);
    const onSignIn = vi.fn();

    render(<SignInPage onSignIn={onSignIn} />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "buyer@syncally.demo" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "correct-horse-battery" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Enter workspace" }));

    await waitFor(() => expect(onSignIn).toHaveBeenCalledWith(tokens));
    expect(mockedLogin).toHaveBeenCalledWith("buyer@syncally.demo", "correct-horse-battery");
  });

  it("shows a message when the credentials are rejected", async () => {
    mockedLogin.mockRejectedValue(new ApiError(401, "Invalid email or password"));

    render(<SignInPage onSignIn={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "buyer@syncally.demo" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "wrong-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Enter workspace" }));

    expect(await screen.findByText("Invalid email or password.")).toBeInTheDocument();
  });

  it("renders counterparty onboarding card when invite token is present in hash", async () => {
    window.location.hash = "#/invite?token=valid-counterparty-token";

    render(<SignInPage onSignIn={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "Join via counterparty invite." })).toBeInTheDocument();
    expect(screen.getByLabelText("Company Legal Name (Optional)")).toBeInTheDocument();
    expect(screen.getByLabelText("Country Code (2 letters)")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create Account & Join Deal" })).toBeInTheDocument();
  });

  it.each([0, 6, 7, 8, 9, 10, 11, 129].flatMap((length) =>
    ["p", "\u{1F600}"].map((character) => ({ length, character })),
  ))(
    "rejects an invitation password of $length code points ($character) without submitting",
    async ({ length, character }) => {
      window.location.hash = "#/invite?token=valid-team-token";
      const onSignIn = vi.fn();
      render(<SignInPage onSignIn={onSignIn} />);

      fireEvent.change(screen.getByLabelText("Email"), {
        target: { value: "teammate@example.com" },
      });
      fireEvent.change(screen.getByLabelText("Password (12–128 characters)"), {
        target: { value: character.repeat(length) },
      });
      fireEvent.click(screen.getByRole("button", { name: "Create Account & Join Deal" }));

      const message = length === 0
        ? "Password is required."
        : length < 12
          ? "Password must be at least 12 characters."
          : "Password must be at most 128 characters.";
      expect(await screen.findByText(message)).toBeInTheDocument();
      expect(screen.getByLabelText("Password (12–128 characters)")).toHaveAttribute("aria-invalid", "true");
      expect(mockedApiRequest).not.toHaveBeenCalled();
      expect(mockedLogin).not.toHaveBeenCalled();
      expect(onSignIn).not.toHaveBeenCalled();
    },
  );

  it.each([12, 65, 128].flatMap((length) =>
    ["p", "\u{1F600}"].map((character) => ({ length, character })),
  ))("accepts an invitation password of $length code points ($character) unchanged", async ({ length, character }) => {
    window.location.hash = "#/invite?token=valid-team-token";
    const onSignIn = vi.fn();
    const tokens = {
      access_token: "new-access-token",
      refresh_token: "new-refresh-token",
      token_type: "bearer",
    };
    mockedApiRequest.mockResolvedValueOnce({ status: "ACCEPTED", deal_id: null, ...tokens });
    render(<SignInPage onSignIn={onSignIn} />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "teammate@example.com" },
    });
    const passwordInput = screen.getByLabelText("Password (12–128 characters)");
    expect(passwordInput).not.toHaveAttribute("minlength");
    expect(passwordInput).not.toHaveAttribute("maxlength");
    fireEvent.change(passwordInput, { target: { value: character.repeat(length) } });
    fireEvent.click(screen.getByRole("button", { name: "Create Account & Join Deal" }));

    await waitFor(() => expect(onSignIn).toHaveBeenCalledWith(tokens));
    expect(mockedApiRequest).toHaveBeenCalledWith("/invitations/accept", {
      method: "POST",
      body: JSON.stringify({
        token: "valid-team-token",
        email: "teammate@example.com",
        password: character.repeat(length),
      }),
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("submits counterparty onboarding form and triggers onSignIn with tokens", async () => {
    window.location.hash = "#/invite?token=valid-counterparty-token";
    const onSignIn = vi.fn();

    mockedApiRequest.mockResolvedValueOnce({
      status: "ACCEPTED",
      organization_id: "org-tokyo-123",
      organization_legal_name: "Tokyo Trade Co",
      user_id: "user-kenji-123",
      role: "ADMIN",
      deal_id: "deal-tokyo-456",
      access_token: "new-access-token",
      refresh_token: "new-refresh-token",
      token_type: "bearer",
    });

    render(<SignInPage onSignIn={onSignIn} />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "kenji@tokyo.jp" },
    });
    fireEvent.change(screen.getByLabelText("Password (12–128 characters)"), {
      target: { value: "password123!" },
    });
    fireEvent.change(screen.getByLabelText("Company Legal Name (Optional)"), {
      target: { value: "Tokyo Trade Co" },
    });
    fireEvent.change(screen.getByLabelText("Country Code (2 letters)"), {
      target: { value: "JP" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Create Account & Join Deal" }));

    await waitFor(() => {
      expect(mockedApiRequest).toHaveBeenCalledWith(
        "/invitations/accept",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            token: "valid-counterparty-token",
            email: "kenji@tokyo.jp",
            password: "password123!",
            organization_legal_name: "Tokyo Trade Co",
            country_code: "JP",
          }),
        }),
      );
    });

    expect(onSignIn).toHaveBeenCalledWith({
      access_token: "new-access-token",
      refresh_token: "new-refresh-token",
      token_type: "bearer",
    });
    expect(window.location.hash).toBe("#/deals/deal-tokyo-456");
  });

  it("lets a team invitee join without providing an organization legal name", async () => {
    window.location.hash = "#/invite?token=valid-team-token";

    mockedApiRequest.mockResolvedValueOnce({
      status: "ACCEPTED",
      organization_id: "org-inviting-123",
      organization_legal_name: "Inviting Co",
      user_id: "user-team-123",
      role: "MEMBER",
      deal_id: null,
    });

    render(<SignInPage onSignIn={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "teammate@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password (12–128 characters)"), {
      target: { value: "password123!" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Create Account & Join Deal" }));

    await waitFor(() => {
      expect(mockedApiRequest).toHaveBeenCalledWith(
        "/invitations/accept",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            token: "valid-team-token",
            email: "teammate@example.com",
            password: "password123!",
          }),
        }),
      );
    });
  });
});
