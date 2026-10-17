import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App", () => {
  it("renders the SyncAlly placeholder page", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { name: "Commercial conversations, in sync." }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Deal creation, negotiation, approvals, and payments/)).toBeInTheDocument();
  });
});
