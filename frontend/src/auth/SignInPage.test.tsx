import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, login } from "../api/client";
import SignInPage from "./SignInPage";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    login: vi.fn(),
  };
});

const mockedLogin = vi.mocked(login);

describe("SignInPage", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("validates required fields before calling the API", async () => {
    render(<SignInPage onSignIn={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Enter workspace" }));

    expect(await screen.findByText("Email is required.")).toBeInTheDocument();
    expect(screen.getByText("Password is required.")).toBeInTheDocument();
    expect(mockedLogin).not.toHaveBeenCalled();
  });

  it("explains the trade flow and quick-fills either local demo account", () => {
    render(<SignInPage onSignIn={vi.fn()} />);

    expect(screen.getByRole("heading", { name: "Cross-Border Trade on Autopilot." })).toBeInTheDocument();
    expect(screen.getByText("Cryptographic Bilateral Approval")).toBeInTheDocument();
    expect(screen.getByText("Automated PayPal Invoicing")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Why SyncAlly" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Demo Buyer" }));
    expect(screen.getByLabelText("Email")).toHaveValue("buyer@syncally.demo");
    expect(screen.getByLabelText("Password")).toHaveValue("correct-horse-battery");

    fireEvent.click(screen.getByRole("button", { name: "Demo Seller" }));
    expect(screen.getByLabelText("Email")).toHaveValue("seller@syncally.demo");
    expect(screen.getByLabelText("Password")).toHaveValue("correct-horse-battery");
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
});
