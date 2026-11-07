import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

  it("starts and resets a blank draft when no proposal exists", async () => {
    vi.mocked(getNegotiation).mockResolvedValue({
      ...view,
      eligible_actions: ["submit"],
      round_count: 0,
      latest: null,
      current_candidate: null,
      proposals: [],
      history: [],
    });
    render(<NegotiationReview deal={deal} organizationId="seller" reloadToken={0} onLoaded={vi.fn()} onChanged={vi.fn()} />);

    const description = await screen.findByLabelText("Item description 1");
    expect(description).toHaveValue("");
    expect(screen.getByLabelText("Item quantity 1")).toHaveValue("");
    expect(screen.getByLabelText("Shipment destination 1")).toHaveValue("");
    expect(screen.getByLabelText("Payment term amount 1")).toHaveValue("");
    expect(screen.getByLabelText("Delivery location")).toHaveValue("");
    expect(screen.getByLabelText("Authoring draft status")).toHaveTextContent("draft");

    fireEvent.change(description, { target: { value: "Copper cable" } });
    fireEvent.click(screen.getByRole("button", { name: "Reset draft" }));
    expect(description).toHaveValue("");
    expect(screen.getByLabelText("Authoring draft status")).toHaveTextContent("draft");
  });

  it("compares the linked round and shows changed, added and removed terms without technical IDs", async () => {
    const base = view.latest!;
    const desk = { ...base.terms.line_items[0], id: "private-desk-id" };
    const lamp = { ...desk, id: "private-lamp-id", description: "Lamp" };
    const chair = { ...desk, id: "private-chair-id", description: "Chair" };
    const previous = {
      ...base,
      id: "linked-round",
      status: "SUPERSEDED",
      terms: {
        ...base.terms, schema_version: 2, line_items: [desk, lamp],
        shipments: [{ ...base.terms.shipments[0], id: "private-shipment-id", allocations: [
          { line_item_id: desk.id, quantity: "1", unit: "each" },
        ] }],
        payment_terms: [{ ...base.terms.payment_terms[0], id: "private-payment-id", allocations: [
          { obligation_id: desk.id, amount: { amount: "10", currency: "USD" } },
        ] }],
        incoterm: "FOB",
      },
    };
    const latest = {
      ...base,
      proposal_number: 3,
      based_on_proposal_id: previous.id,
      terms: {
        ...previous.terms,
        line_items: [chair, { ...desk, unit_price: { amount: "15", currency: "USD" } }],
        shipments: [{ ...previous.terms.shipments[0], allocations: [
          { line_item_id: chair.id, quantity: "1", unit: "each" },
        ] }],
        payment_terms: [{ ...previous.terms.payment_terms[0], due_condition: "Net 30", allocations: [
          { obligation_id: chair.id, amount: { amount: "15", currency: "USD" } },
        ] }],
        incoterm: "CIF",
      },
    };
    const unrelated = { ...base, id: "unrelated-round", proposal_number: 2 };
    vi.mocked(getNegotiation).mockResolvedValue({ ...view, latest, proposals: [latest, unrelated, previous] });

    render(<NegotiationReview deal={deal} organizationId="seller" reloadToken={0} onLoaded={vi.fn()} onChanged={vi.fn()} />);

    const comparison = within(await screen.findByRole("region", { name: "Changes from the previous proposal" }));
    const rows = comparison.getAllByRole("listitem");
    const deskChange = within(rows.find((row) => within(row).queryByRole("heading", { name: /Desk.*Changed/ }))!);
    expect(deskChange.getByText("Previous · Round 1")).toBeVisible();
    expect(deskChange.getByText("Current · Round 3")).toBeVisible();
    expect(deskChange.getByText("10 USD")).toBeVisible();
    expect(deskChange.getByText("15 USD")).toBeVisible();
    expect(deskChange.queryByText("Quantity")).not.toBeInTheDocument();
    expect(comparison.getByRole("heading", { name: /Chair.*Added/ })).toBeVisible();
    expect(comparison.getByRole("heading", { name: /Lamp.*Removed/ })).toBeVisible();
    expect(comparison.getAllByText("Not included")).toHaveLength(2);
    expect(comparison.getByText(/1 each for Item 1: Desk/)).toBeVisible();
    expect(comparison.getByText(/1 each for Item 1: Chair/)).toBeVisible();
    const paymentChange = within(rows.find((row) => within(row).queryByRole("heading", { name: /Payment 1.*Changed/ }))!);
    expect(paymentChange.getByText("10 USD for Item 1: Desk")).toBeVisible();
    expect(paymentChange.getByText("15 USD for Item 1: Chair")).toBeVisible();
    expect(comparison.getByText("Net 30")).toBeVisible();
    expect(comparison.getByText("FOB")).toBeVisible();
    expect(comparison.getByText("CIF")).toBeVisible();
    expect(comparison.queryByText(/private-|linked-round|unrelated-round/)).not.toBeInTheDocument();
  });

  it("shows no changes when the same terms are reordered", async () => {
    const base = view.latest!;
    const first = { ...base.terms.line_items[0], id: "first" };
    const second = { ...first, id: "second", description: "Chair" };
    const allocations = [{ line_item_id: first.id, quantity: "1", unit: "each" },
      { line_item_id: second.id, quantity: "1", unit: "each" }];
    const previous = { ...base, terms: {
      ...base.terms, schema_version: 2, line_items: [first, second],
      shipments: [{ ...base.terms.shipments[0], id: "shipment", allocations }],
      payment_terms: [{ ...base.terms.payment_terms[0], id: "payment" }],
    } };
    const latest = { ...previous, id: "counter", based_on_proposal_id: previous.id, proposal_number: 2, terms: {
      ...previous.terms, line_items: [second, first],
      shipments: [{ ...previous.terms.shipments[0], allocations: [...allocations].reverse() }],
    } };
    vi.mocked(getNegotiation).mockResolvedValue({ ...view, latest, proposals: [latest, previous] });

    render(<NegotiationReview deal={deal} organizationId="seller" reloadToken={0} onLoaded={vi.fn()} onChanged={vi.fn()} />);

    expect(await screen.findByText("No commercial terms changed since round 1.")).toBeVisible();
  });

  it("compares single legacy terms when collection IDs are absent", async () => {
    const previous = view.latest!;
    const latest = {
      ...previous, id: "legacy-counter", proposal_number: 2, based_on_proposal_id: previous.id,
      terms: { ...previous.terms, shipments: [{ ...previous.terms.shipments[0], target_date: "2030-02-01" }] },
    };
    vi.mocked(getNegotiation).mockResolvedValue({ ...view, latest, proposals: [previous, latest] });
    render(<NegotiationReview deal={deal} organizationId="seller" reloadToken={0} onLoaded={vi.fn()} onChanged={vi.fn()} />);

    const comparison = within(await screen.findByRole("region", { name: "Changes from the previous proposal" }));
    expect(comparison.getByRole("heading", { name: /Shipment 1 to Toronto.*Changed/ })).toBeVisible();
    expect(comparison.getByText("2030-01-01")).toBeVisible();
    expect(comparison.getByText("2030-02-01")).toBeVisible();
  });

  it.each([
    [null, "This proposal has no linked previous round to compare."],
    ["missing-round", "The previous proposal is unavailable for comparison."],
  ])("handles an absent or unavailable predecessor link (%s)", async (based_on_proposal_id, message) => {
    const latest = { ...view.latest!, based_on_proposal_id };
    const unrelated = { ...latest, id: "different-round" };
    vi.mocked(getNegotiation).mockResolvedValue({ ...view, latest, proposals: [unrelated] });
    render(<NegotiationReview deal={deal} organizationId="seller" reloadToken={0} onLoaded={vi.fn()} onChanged={vi.fn()} />);
    expect(await screen.findByText(message)).toBeVisible();
  });

  it("accepts the exact latest proposal without recording agreement approval", async () => {
    const changed = vi.fn();
    vi.mocked(negotiateDeal).mockResolvedValue({ outcome: "APPLIED", deal_revision: 2, proposal_id: "proposal", candidate_id: "candidate" });
    render(<NegotiationReview deal={deal} organizationId="seller" reloadToken={0} onLoaded={vi.fn()} onChanged={changed} />);
    fireEvent.click(await screen.findByRole("button", { name: "Accept proposal for agreement review" }));
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
    fireEvent.click(await screen.findByRole("button", { name: "Accept proposal for agreement review" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Reload and review");
    expect(screen.getByRole("button", { name: "Reject proposal" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Refresh proposals" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Reject proposal" })).toBeEnabled());
  });

  it("ignores a delayed private history response after organization switch", async () => {
    let resolve!: (value: NegotiationView) => void;
    vi.mocked(getNegotiation).mockImplementationOnce(() => new Promise((done) => { resolve = done; }));
    const { rerender } = render(<NegotiationReview deal={deal} organizationId="buyer" reloadToken={0} onLoaded={vi.fn()} onChanged={vi.fn()} />);
    rerender(<NegotiationReview deal={deal} organizationId="seller" reloadToken={0} onLoaded={vi.fn()} onChanged={vi.fn()} />);
    expect(await screen.findByText(/Latest human proposal/i)).toBeInTheDocument();
    await act(async () => resolve({ ...view, organization_id: "buyer", latest: { ...view.latest!, terms_hash: "PRIVATE-ONLY-HASH" } }));
    expect(screen.queryByText("PRIVATE-ONLY-HASH")).not.toBeInTheDocument();
  });

  it("blocks pending-counterparty commands and renders only projected history", async () => {
    render(<NegotiationReview deal={{ ...deal, pending_counterparty: true }} organizationId="seller" reloadToken={0} onLoaded={vi.fn()} onChanged={vi.fn()} />);
    expect(await screen.findByRole("button", { name: "Accept proposal for agreement review" })).toBeDisabled();
    expect(screen.queryByText(/Evidence/)).not.toBeInTheDocument();
    expect(negotiateDeal).not.toHaveBeenCalled();
  });

  it("separates a human proposal from the candidate agreement and hides technical hashes by default", async () => {
    const candidate = { id: "candidate", version_number: 3, terms_hash: "b".repeat(64), proposal_id: "proposal" };
    vi.mocked(getNegotiation).mockResolvedValue({ ...view, current_candidate: candidate });
    render(<NegotiationReview deal={deal} organizationId="seller" reloadToken={0} onLoaded={vi.fn()} onChanged={vi.fn()} />);

    expect(await screen.findByText("Your response is needed")).toBeInTheDocument();
    expect(screen.getByText(/accepting one moves its terms to agreement review as a candidate/i)).toBeInTheDocument();
    expect(screen.getByText(/each organization must review that version and record its own decision/i)).toBeInTheDocument();
    expect(screen.getByText("Replace agreement version 3. Its existing decisions will no longer apply.")).toBeInTheDocument();
    const hash = screen.getByText("a".repeat(64));
    expect(hash).not.toBeVisible();
    fireEvent.click(screen.getByText("Proposal verification details"));
    expect(hash).toBeVisible();
    expect(screen.getByRole("button", { name: "Accept proposal for agreement review" })).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox", { name: /replace agreement version 3/i }));
    expect(screen.getByRole("button", { name: "Accept proposal for agreement review" })).toBeEnabled();
  });

  it("renders schema 2 proposal terms with stable IDs and allocations", async () => {
    const schema2View: NegotiationView = {
      deal_id: "deal",
      organization_id: "seller",
      deal_revision: 1,
      round_count: 1,
      max_rounds: 5,
      escalated: false,
      history_ambiguous: false,
      eligible_actions: ["counter", "reject"],
      current_candidate: null,
      proposals: [],
      history: [],
      latest: {
        id: "proposal-2",
        status: "SUBMITTED",
        terms_hash: "c".repeat(64),
        proposal_number: 1,
        author_organization_id: "buyer",
        based_on_proposal_id: null,
        lifecycle_origin: "HUMAN_ROUNDS",
        created_at: "2026-10-31T12:00:00Z",
        expires_at: null,
        evidence_refs: [],
        metadata_schema_version: 1,
        terms: {
          schema_version: 2,
          buyer_id: "buyer",
          seller_id: "seller",
          line_items: [
            {
              id: "item-10",
              description: "Solar Inverters",
              sku: "INV-500",
              quantity: "20",
              unit: "units",
              unit_price: { amount: "500.00", currency: "USD" },
            },
          ],
          shipments: [
            {
              id: "ship-20",
              quantity: "20",
              destination: "Antwerp Port",
              target_date: "2026-12-15",
              allocations: [
                { line_item_id: "item-10", quantity: "20", unit: "units" },
              ],
            },
          ],
          payment_terms: [
            {
              id: "pay-30",
              amount: { amount: "10000.00", currency: "USD" },
              trigger: "bill_of_lading",
              due_condition: "Within 10 days of B/L",
              allocations: [
                { obligation_id: "ship-20", amount: { amount: "10000.00", currency: "USD" } },
              ],
            },
          ],
          delivery_location: "Antwerp Port",
          incoterm: "CIF",
          cancellation_terms: "30-day notice",
        },
      },
    };

    vi.mocked(getNegotiation).mockResolvedValue(schema2View);
    render(<NegotiationReview deal={deal} organizationId="seller" reloadToken={0} onLoaded={vi.fn()} onChanged={vi.fn()} />);

    expect(await screen.findByText("item-10")).toBeInTheDocument();
    expect(screen.getByText("INV-500")).toBeInTheDocument();
    expect(screen.getByText("ship-20")).toBeInTheDocument();
    expect(screen.getByText("20 units of item item-10")).toBeInTheDocument();
    expect(screen.getByText("pay-30")).toBeInTheDocument();
    expect(screen.getByText("10000.00 USD for obligation ship-20")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Create a trade proposal" })).toBeInTheDocument();
  });

  it("submits a schema 2 counter-proposal with collections", async () => {
    const schema2View: NegotiationView = {
      deal_id: "deal",
      organization_id: "seller",
      deal_revision: 1,
      round_count: 1,
      max_rounds: 5,
      escalated: false,
      history_ambiguous: false,
      eligible_actions: ["counter"],
      current_candidate: null,
      proposals: [],
      history: [],
      latest: {
        id: "proposal-base",
        status: "SUBMITTED",
        terms_hash: "d".repeat(64),
        proposal_number: 1,
        author_organization_id: "buyer",
        based_on_proposal_id: null,
        lifecycle_origin: "HUMAN_ROUNDS",
        created_at: "2026-10-31T12:00:00Z",
        expires_at: null,
        evidence_refs: [],
        metadata_schema_version: 1,
        terms: {
          schema_version: 2,
          buyer_id: "buyer",
          seller_id: "seller",
          line_items: [
            {
              id: "item-1",
              description: "Valves",
              sku: "V-1",
              quantity: "10",
              unit: "pieces",
              unit_price: { amount: "100.00", currency: "USD" },
            },
          ],
          shipments: [
            {
              id: "ship-1",
              quantity: "10",
              destination: "Rotterdam",
              target_date: "2026-12-01",
              allocations: [
                { line_item_id: "item-1", quantity: "10", unit: "pieces" },
              ],
            },
          ],
          payment_terms: [
            {
              id: "pay-1",
              amount: { amount: "1000.00", currency: "USD" },
              trigger: "delivery",
              due_condition: "immediate",
              allocations: [
                { obligation_id: "ship-1", amount: { amount: "1000.00", currency: "USD" } },
              ],
            },
          ],
          delivery_location: "Rotterdam",
          incoterm: "DAP",
          cancellation_terms: "None",
        },
      },
    };

    vi.mocked(getNegotiation).mockResolvedValue(schema2View);
    vi.mocked(negotiateDeal).mockResolvedValue({
      outcome: "APPLIED",
      deal_revision: 2,
      proposal_id: "proposal-new",
      candidate_id: null,
    });

    const onChanged = vi.fn();
    render(<NegotiationReview deal={deal} organizationId="seller" reloadToken={0} onLoaded={vi.fn()} onChanged={onChanged} />);

    expect(await screen.findByRole("button", { name: "Submit counter-proposal" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Submit counter-proposal" }));

    await waitFor(() => expect(negotiateDeal).toHaveBeenCalledOnce());
    expect(negotiateDeal).toHaveBeenCalledWith("deal", "counter", expect.objectContaining({
      command_id: expect.any(String),
      expected_deal_revision: 1,
      organization_id: "seller",
      base: { id: "proposal-base", terms_hash: "d".repeat(64), status: "SUBMITTED" },
      terms: expect.objectContaining({
        schema_version: 2,
        line_items: [
          expect.objectContaining({ id: "item-1", description: "Valves", quantity: "10" }),
        ],
        shipments: [
          expect.objectContaining({ id: "ship-1", destination: "Rotterdam" }),
        ],
        payment_terms: [
          expect.objectContaining({ id: "pay-1" }),
        ],
      }),
    }), expect.any(Object));
  });

  it("rejects invalid authoring draft with validation alert and does not submit", async () => {
    const schema2View: NegotiationView = {
      deal_id: "deal",
      organization_id: "seller",
      deal_revision: 1,
      round_count: 1,
      max_rounds: 5,
      escalated: false,
      history_ambiguous: false,
      eligible_actions: ["counter"],
      current_candidate: null,
      proposals: [],
      history: [],
      latest: {
        id: "proposal-base",
        status: "SUBMITTED",
        terms_hash: "e".repeat(64),
        proposal_number: 1,
        author_organization_id: "buyer",
        based_on_proposal_id: null,
        lifecycle_origin: "HUMAN_ROUNDS",
        created_at: "2026-10-31T12:00:00Z",
        expires_at: null,
        evidence_refs: [],
        metadata_schema_version: 1,
        terms: {
          schema_version: 2,
          buyer_id: "buyer",
          seller_id: "seller",
          line_items: [
            {
              id: "item-1",
              description: "Valves",
              sku: "V-1",
              quantity: "10",
              unit: "pieces",
              unit_price: { amount: "100.00", currency: "USD" },
            },
          ],
          shipments: [
            {
              id: "ship-1",
              quantity: "10",
              destination: "Rotterdam",
              target_date: "2026-12-01",
              allocations: [
                { line_item_id: "item-1", quantity: "10", unit: "pieces" },
              ],
            },
          ],
          payment_terms: [
            {
              id: "pay-1",
              amount: { amount: "1000.00", currency: "USD" },
              trigger: "delivery",
              due_condition: "immediate",
              allocations: [
                { obligation_id: "ship-1", amount: { amount: "1000.00", currency: "USD" } },
              ],
            },
          ],
          delivery_location: "Rotterdam",
          incoterm: "DAP",
          cancellation_terms: "None",
        },
      },
    };

    vi.mocked(getNegotiation).mockResolvedValue(schema2View);
    render(<NegotiationReview deal={deal} organizationId="seller" reloadToken={0} onLoaded={vi.fn()} onChanged={vi.fn()} />);

    expect(await screen.findByLabelText("Delivery location")).toBeInTheDocument();
    // Clear delivery location to make it invalid
    fireEvent.change(screen.getByLabelText("Delivery location"), { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: "Submit counter-proposal" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Delivery location is required.");
    expect(negotiateDeal).not.toHaveBeenCalled();
  });
});
