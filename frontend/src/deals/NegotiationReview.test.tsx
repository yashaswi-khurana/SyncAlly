import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, getNegotiation, negotiateDeal } from "../api/client";
import type { Deal, NegotiationView } from "../api/types";
import NegotiationReview from "./NegotiationReview";

vi.mock("../api/client", async (original) => ({ ...await original<typeof import("../api/client")>(), getNegotiation: vi.fn(), negotiateDeal: vi.fn() }));
const deal: Deal = { id: "deal", buyer_organization_id: "buyer", seller_organization_id: "seller", status: "NEGOTIATING", version: 1 };
const view: NegotiationView = {
  deal_id: "deal", organization_id: "seller", deal_revision: 1, round_count: 1, max_rounds: 5,
  escalated: false, history_ambiguous: false, eligible_actions: ["accept", "counter", "reject"],
  current_candidate: null, proposals: [], history: [],
  latest: { id: "proposal", status: "SUBMITTED", terms_hash: "a".repeat(64), proposal_number: 1,
    author_organization_id: "buyer", based_on_proposal_id: null, lifecycle_origin: "HUMAN_ROUNDS",
    created_at: "2026-10-31T12:00:00Z", expires_at: null, evidence_refs: [], metadata_schema_version: 1,
    terms: { schema_version: 1, buyer_id: "buyer", seller_id: "seller", line_items: [{ description: "Desk", sku: null, quantity: "1", unit: "each", unit_price: { amount: "10", currency: "USD" } }],
      shipments: [{ quantity: "1", destination: "Toronto", target_date: "2030-01-01" }], payment_terms: [{ amount: { amount: "10", currency: "USD" }, trigger: "seller_invoice", due_condition: "when seller invoices" }], delivery_location: "Toronto", incoterm: null, cancellation_terms: "" } },
};

describe("NegotiationReview", () => {
  beforeEach(() => { vi.clearAllMocks(); vi.mocked(getNegotiation).mockResolvedValue(view); });

  it("accepts the exact latest proposal without recording agreement approval", async () => {
    const changed = vi.fn();
    vi.mocked(negotiateDeal).mockResolvedValue({ outcome: "APPLIED", deal_revision: 2, proposal_id: "proposal", candidate_id: "candidate" });
    render(<NegotiationReview deal={deal} organizationId="seller" reloadToken={0} onLoaded={vi.fn()} onChanged={changed} />);
    fireEvent.click(await screen.findByRole("button", { name: "Accept as candidate" }));
    await waitFor(() => expect(changed).toHaveBeenCalledOnce());
    expect(negotiateDeal).toHaveBeenCalledWith("deal", "accept", expect.objectContaining({
      command_id: expect.any(String), expected_deal_revision: 1, organization_id: "seller",
      base: { id: "proposal", terms_hash: "a".repeat(64), status: "SUBMITTED" },
    }), expect.any(Object));
    expect(screen.queryByRole("button", { name: "Approve this version" })).not.toBeInTheDocument();
  });

  it("disables actions until reload after conflict", async () => {
    vi.mocked(negotiateDeal).mockRejectedValue(new ApiError(409, "stale"));
    render(<NegotiationReview deal={deal} organizationId="seller" reloadToken={0} onLoaded={vi.fn()} onChanged={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Accept as candidate" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Reload and review");
    expect(screen.getByRole("button", { name: "Reject proposal" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Reload rounds" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Reject proposal" })).toBeEnabled());
  });

  it("ignores a delayed private history response after organization switch", async () => {
    let resolve!: (value: NegotiationView) => void;
    vi.mocked(getNegotiation).mockImplementationOnce(() => new Promise((done) => { resolve = done; }));
    const { rerender } = render(<NegotiationReview deal={deal} organizationId="buyer" reloadToken={0} onLoaded={vi.fn()} onChanged={vi.fn()} />);
    rerender(<NegotiationReview deal={deal} organizationId="seller" reloadToken={0} onLoaded={vi.fn()} onChanged={vi.fn()} />);
    expect(await screen.findByText("Latest proposal: round 1")).toBeInTheDocument();
    await act(async () => resolve({ ...view, organization_id: "buyer", latest: { ...view.latest!, terms_hash: "PRIVATE-ONLY-HASH" } }));
    expect(screen.queryByText("PRIVATE-ONLY-HASH")).not.toBeInTheDocument();
  });

  it("blocks pending-counterparty commands and renders only projected history", async () => {
    render(<NegotiationReview deal={{ ...deal, pending_counterparty: true }} organizationId="seller" reloadToken={0} onLoaded={vi.fn()} onChanged={vi.fn()} />);
    expect(await screen.findByRole("button", { name: "Accept as candidate" })).toBeDisabled();
    expect(screen.queryByText(/Evidence/)).not.toBeInTheDocument();
    expect(negotiateDeal).not.toHaveBeenCalled();
  });
});