import { useEffect, useRef, useState } from "react";

import { ApiError, getNegotiation, negotiateDeal } from "../api/client";
import type {
  Deal,
  NegotiationAction,
  NegotiationInput,
  NegotiationProposal,
  NegotiationView,
  ReviewedProposalTerms,
} from "../api/types";

interface NegotiationReviewProps {
  deal: Deal;
  organizationId: string;
  reloadToken: number;
  onLoaded: (view: NegotiationView | null) => void;
  onChanged: () => void;
}

const ACTION_LABELS: Record<string, string> = {
  accept: "Accept proposal for agreement review",
  reject: "Reject proposal",
  supersede: "Withdraw proposal",
  expire: "Expire proposal",
};

function proposalStatusLabel(proposal: NegotiationProposal, viewerOrganizationId: string): string {
  switch (proposal.status) {
    case "SUBMITTED": return proposal.author_organization_id === viewerOrganizationId ? "Waiting for partner response" : "Your response is needed";
    case "ACCEPTED": return "Accepted · agreement review next";
    case "REJECTED": return "Rejected";
    case "SUPERSEDED": return "Replaced by a newer proposal";
    case "EXPIRED": return "Expired";
    default: return proposal.status.replaceAll("_", " ").toLowerCase();
  }
}

function historyActionLabel(action: NegotiationView["history"][number]["action"]): string {
  switch (action) {
    case "submit": return "Human proposal submitted";
    case "counter": return "Counterproposal submitted";
    case "accept": return "Proposal accepted for agreement review";
    case "reject": return "Proposal rejected";
    case "supersede": return "Proposal withdrawn or replaced";
    case "expire": return "Proposal expired";
    case "escalate": return "Escalation requested";
  }
}

interface ItemDraft {
  id: string;
  description: string;
  quantity: string;
  unit: string;
  unitPrice: string;
  currency: string;
  sku: string;
}

interface ShipmentAllocationDraft {
  line_item_id: string;
  quantity: string;
  unit: string;
}

interface ShipmentDraft {
  id: string;
  destination: string;
  targetDate: string;
  allocations: ShipmentAllocationDraft[];
}

interface PaymentAllocationDraft {
  obligation_id: string;
  amount: string;
  currency: string;
}

interface PaymentDraft {
  id: string;
  amount: string;
  currency: string;
  trigger: string;
  dueCondition: string;
  allocations: PaymentAllocationDraft[];
}

function defaultDraft() {
  return {
    items: [
      { id: "item-1", description: "Desk", quantity: "10", unit: "pieces", unitPrice: "25.00", currency: "USD", sku: "" },
    ],
    shipments: [
      { id: "ship-1", destination: "Toronto", targetDate: "2030-01-01", allocations: [{ line_item_id: "item-1", quantity: "10", unit: "pieces" }] },
    ],
    payments: [
      { id: "pay-1", amount: "250.00", currency: "USD", trigger: "seller_invoice", dueCondition: "when seller invoices", allocations: [{ obligation_id: "ship-1", amount: "250.00", currency: "USD" }] },
    ],
    deliveryLocation: "Toronto",
    incoterm: "",
    cancellationTerms: "",
  };
}

function isValidDecimal(value: string, { allowZero = false } = {}): boolean {
  if (!value || !value.trim()) return false;
  const trimmed = value.trim();
  if (!/^-?\d+(\.\d+)?$/.test(trimmed)) return false;
  const num = Number(trimmed);
  if (!Number.isFinite(num)) return false;
  if (!allowZero && num <= 0) return false;
  if (num < 0) return false;
  const parts = trimmed.split(".");
  const intPart = parts[0].replace(/^-/, "");
  const fracPart = parts[1] || "";
  if (intPart.length > 40) return false;
  if (fracPart.length > 18) return false;
  return true;
}

function parseScaled(val: string): bigint {
  const trimmed = val.trim();
  const [intPart, fracPart = ""] = trimmed.split(".");
  const paddedFrac = fracPart.padEnd(18, "0").slice(0, 18);
  return BigInt(intPart + paddedFrac);
}

export default function NegotiationReview({ deal, organizationId, reloadToken, onLoaded, onChanged }: NegotiationReviewProps) {
  const [loadedView, setView] = useState<NegotiationView | null>(null);
  const view = loadedView?.deal_id === deal.id && loadedView.organization_id === organizationId ? loadedView : null;
  const [error, setError] = useState("");
  const [authorError, setAuthorError] = useState("");
  const [stale, setStale] = useState(false);
  const [pending, setPending] = useState(false);
  const [reload, setReload] = useState(0);
  const [replacementConfirmed, setReplacementConfirmed] = useState(false);

  // Authoring draft state
  const [items, setItems] = useState<ItemDraft[]>(defaultDraft().items);
  const [shipments, setShipments] = useState<ShipmentDraft[]>(defaultDraft().shipments);
  const [payments, setPayments] = useState<PaymentDraft[]>(defaultDraft().payments);
  const [deliveryLocation, setDeliveryLocation] = useState("Toronto");
  const [incoterm, setIncoterm] = useState("");
  const [cancellationTerms, setCancellationTerms] = useState("");
  const [isDirty, setIsDirty] = useState(false);

  const loadContext = JSON.stringify([deal.id, deal.version, organizationId, reloadToken, reload]);
  const [observedContext, setObservedContext] = useState(loadContext);
  if (loadContext !== observedContext) {
    setObservedContext(loadContext);
    setView(null);
    setPending(false);
    setError("");
    setAuthorError("");
    setStale(false);
    setReplacementConfirmed(false);
    setIsDirty(false);
  }

  function populateEditorFromTerms(terms: ReviewedProposalTerms) {
    if (terms.schema_version === 2) {
      if (terms.line_items && terms.line_items.length > 0) {
        setItems(terms.line_items.map((it, idx) => ({
          id: it.id || `item-${idx + 1}`,
          description: it.description,
          quantity: it.quantity,
          unit: it.unit,
          unitPrice: it.unit_price.amount,
          currency: it.unit_price.currency,
          sku: it.sku || "",
        })));
      }
      if (terms.shipments && terms.shipments.length > 0) {
        setShipments(terms.shipments.map((s, idx) => ({
          id: s.id || `ship-${idx + 1}`,
          destination: s.destination,
          targetDate: s.target_date || "",
          allocations: (s.allocations || []).map(a => ({
            line_item_id: a.line_item_id,
            quantity: a.quantity,
            unit: a.unit,
          })),
        })));
      }
      if (terms.payment_terms && terms.payment_terms.length > 0) {
        setPayments(terms.payment_terms.map((p, idx) => ({
          id: p.id || `pay-${idx + 1}`,
          amount: p.amount.amount,
          currency: p.amount.currency,
          trigger: p.trigger,
          dueCondition: p.due_condition,
          allocations: (p.allocations || []).map(a => ({
            obligation_id: a.obligation_id,
            amount: a.amount.amount,
            currency: a.amount.currency,
          })),
        })));
      }
      if (terms.delivery_location) setDeliveryLocation(terms.delivery_location);
      if (terms.incoterm) setIncoterm(terms.incoterm);
      if (terms.cancellation_terms) setCancellationTerms(terms.cancellation_terms);
    }
  }

  function resetEditor() {
    if (view?.latest?.terms && view.latest.terms.schema_version === 2) {
      populateEditorFromTerms(view.latest.terms);
    } else {
      setItems([{ id: "item-1", description: "Industrial Valves", quantity: "100", unit: "pieces", unitPrice: "250.00", currency: "USD", sku: "VALVE-100" }]);
      setShipments([{ id: "ship-1", destination: "Warehouse 4A, Hamburg Port", targetDate: "2026-12-01", allocations: [{ line_item_id: "item-1", quantity: "100", unit: "pieces" }] }]);
      setPayments([{ id: "pay-1", amount: "25000.00", currency: "USD", trigger: "customs_clearance", dueCondition: "Net 30 days after arrival", allocations: [{ obligation_id: "ship-1", amount: "25000.00", currency: "USD" }] }]);
      setDeliveryLocation("Warehouse 4A, Hamburg Port");
      setIncoterm("DAP");
      setCancellationTerms("Standard bilateral 14-day notice with forfeiture of accrued logistics deposits.");
    }
    setError("");
    setAuthorError("");
    setStale(false);
    setReplacementConfirmed(false);
    setIsDirty(false);
  }
  const request = useRef<AbortController | null>(null);
  const command = useRef<{ signature: string; id: string } | null>(null);
  const loadedCallback = useRef(onLoaded);
  useEffect(() => { loadedCallback.current = onLoaded; }, [onLoaded]);

  useEffect(() => {
    const controller = new AbortController();
    request.current?.abort();
    request.current = null;
    loadedCallback.current(null);
    void getNegotiation(deal.id, organizationId, { signal: controller.signal }).then((next) => {
      if (controller.signal.aborted || next.deal_id !== deal.id || next.organization_id !== organizationId) return;
      setView(next);
      loadedCallback.current(next);
      if (next?.latest?.terms && next.latest.terms.schema_version === 2) {
        populateEditorFromTerms(next.latest.terms);
      }
    }).catch((caught: unknown) => {
      if (!controller.signal.aborted) setError(caught instanceof ApiError ? caught.message : "Unable to load negotiation rounds.");
    });
    return () => { controller.abort(); request.current?.abort(); };
  }, [deal.id, deal.version, organizationId, reloadToken, reload]);

  function validateCollections(): string | null {
    if (items.length === 0) return "At least one line item is required.";
    if (shipments.length === 0) return "At least one shipment is required.";
    if (payments.length === 0) return "At least one payment term is required.";
    if (!deliveryLocation.trim()) return "Delivery location is required.";

    const allIds = new Set<string>();
    const currencies = new Set<string>();

    for (let i = 0; i < items.length; i++) {
      const it = items[i];
      if (!it.id.trim()) return `Line item ${i + 1} requires an ID.`;
      if (allIds.has(it.id)) return `Duplicate ID '${it.id}' across items, shipments, and payment terms.`;
      allIds.add(it.id);
      if (!it.description.trim()) return `Line item '${it.id}' requires a description.`;
      if (!isValidDecimal(it.quantity)) return `Line item '${it.id}' quantity must be a positive decimal within limits.`;
      if (!it.unit.trim()) return `Line item '${it.id}' requires a unit.`;
      if (!isValidDecimal(it.unitPrice)) return `Line item '${it.id}' unit price must be a positive decimal within limits.`;
      if (!it.currency || it.currency.length !== 3) return `Line item '${it.id}' requires a 3-letter currency code.`;
      currencies.add(it.currency);
    }

    for (let i = 0; i < shipments.length; i++) {
      const s = shipments[i];
      if (!s.id.trim()) return `Shipment ${i + 1} requires an ID.`;
      if (allIds.has(s.id)) return `Duplicate ID '${s.id}' across items, shipments, and payment terms.`;
      allIds.add(s.id);
      if (!s.destination.trim()) return `Shipment '${s.id}' requires a destination.`;
      if (!s.targetDate.trim()) return `Shipment '${s.id}' requires a target delivery date.`;
      if (s.allocations.length === 0) return `Shipment '${s.id}' requires at least one allocation.`;
      for (const a of s.allocations) {
        if (!a.line_item_id.trim()) return `Shipment '${s.id}' allocation requires a line item ID.`;
        const targetItem = items.find(it => it.id === a.line_item_id);
        if (!targetItem) return `Shipment '${s.id}' allocation references unknown line item '${a.line_item_id}'.`;
        if (a.unit !== targetItem.unit) return `Shipment '${s.id}' allocation unit '${a.unit}' does not match line item unit '${targetItem.unit}'.`;
        if (!isValidDecimal(a.quantity)) return `Shipment '${s.id}' allocation quantity must be a positive decimal within limits.`;
      }
    }

    for (let i = 0; i < payments.length; i++) {
      const p = payments[i];
      if (!p.id.trim()) return `Payment term ${i + 1} requires an ID.`;
      if (allIds.has(p.id)) return `Duplicate ID '${p.id}' across items, shipments, and payment terms.`;
      allIds.add(p.id);
      if (!isValidDecimal(p.amount)) return `Payment term '${p.id}' amount must be a positive decimal within limits.`;
      if (!p.currency || p.currency.length !== 3) return `Payment term '${p.id}' requires a 3-letter currency code.`;
      currencies.add(p.currency);
      if (!p.trigger.trim()) return `Payment term '${p.id}' requires a trigger.`;
      if (!p.dueCondition.trim()) return `Payment term '${p.id}' requires a due condition.`;
      if (p.allocations.length === 0) return `Payment term '${p.id}' requires at least one allocation.`;
      for (const a of p.allocations) {
        if (!a.obligation_id.trim()) return `Payment term '${p.id}' allocation requires an obligation ID.`;
        const obligationExists = shipments.some(s => s.id === a.obligation_id) || items.some(it => it.id === a.obligation_id);
        if (!obligationExists) return `Payment term '${p.id}' allocation references unknown obligation '${a.obligation_id}'.`;
        if (!isValidDecimal(a.amount)) return `Payment term '${p.id}' allocation amount must be a positive decimal within limits.`;
        if (a.currency !== p.currency) return `Payment term '${p.id}' allocation currency '${a.currency}' does not match payment term currency '${p.currency}'.`;
      }
    }

    if (currencies.size > 1) return "All line items, payment terms, and allocations must use the same single currency.";

    for (const it of items) {
      let totalAlloc = BigInt(0);
      for (const s of shipments) {
        for (const a of s.allocations) {
          if (a.line_item_id === it.id) {
            totalAlloc += parseScaled(a.quantity);
          }
        }
      }
      const itemQty = parseScaled(it.quantity);
      if (totalAlloc !== itemQty) {
        return `Line item '${it.id}' total allocated quantity must match line item quantity.`;
      }
    }

    for (const p of payments) {
      let termAlloc = BigInt(0);
      for (const a of p.allocations) {
        termAlloc += parseScaled(a.amount);
      }
      if (termAlloc !== parseScaled(p.amount)) {
        return `Payment term '${p.id}' allocations must sum to payment term amount.`;
      }
    }

    let totalItemsAmount = BigInt(0);
    for (const it of items) {
      const q = parseScaled(it.quantity);
      const p = parseScaled(it.unitPrice);
      totalItemsAmount += (q * p) / BigInt("1000000000000000000");
    }
    let totalPaymentsAmount = BigInt(0);
    for (const p of payments) {
      totalPaymentsAmount += parseScaled(p.amount);
    }
    if (totalItemsAmount !== totalPaymentsAmount) {
      return "Total payment terms must equal total line items (zero-residual balance).";
    }

    return null;
  }

  async function submitAuthoring(action: "submit" | "counter") {
    if (request.current || !view || stale || deal.pending_counterparty || !view.eligible_actions.includes(action)) return;
    if (view.current_candidate && !replacementConfirmed) return;

    const validationErr = validateCollections();
    if (validationErr) {
      setAuthorError(validationErr);
      return;
    }
    setAuthorError("");

    const termsPayload: ReviewedProposalTerms = {
      schema_version: 2,
      line_items: items.map(it => ({
        id: it.id,
        description: it.description,
        quantity: it.quantity,
        unit: it.unit,
        unit_price: { amount: it.unitPrice, currency: it.currency },
        sku: it.sku ? it.sku : null,
      })),
      shipments: shipments.map(s => ({
        id: s.id,
        destination: s.destination,
        target_date: s.targetDate || null,
        quantity: s.allocations.reduce((acc, a) => acc + Number(a.quantity || 0), 0).toString(),
        allocations: s.allocations.map(a => ({
          line_item_id: a.line_item_id,
          quantity: a.quantity,
          unit: a.unit,
        })),
      })),
      payment_terms: payments.map(p => ({
        id: p.id,
        amount: { amount: p.amount, currency: p.currency },
        trigger: p.trigger,
        due_condition: p.dueCondition,
        allocations: p.allocations.map(a => ({
          obligation_id: a.obligation_id,
          amount: { amount: a.amount, currency: a.currency },
        })),
      })),
      delivery_location: deliveryLocation,
      incoterm: incoterm ? incoterm : null,
      cancellation_terms: cancellationTerms,
    };

    const latest = view.latest;
    const input: Omit<NegotiationInput, "command_id"> = {
      expected_deal_revision: view.deal_revision,
      organization_id: organizationId,
      base: latest ? { id: latest.id, terms_hash: latest.terms_hash, status: latest.status } : null,
      supersede_current_candidate: view.current_candidate,
      terms: termsPayload,
    };
    const signature = JSON.stringify([deal.id, action, input]);
    if (command.current?.signature !== signature) command.current = { signature, id: crypto.randomUUID() };
    const controller = new AbortController();
    request.current = controller;
    setPending(true);
    setError("");

    try {
      await negotiateDeal(deal.id, action, { ...input, command_id: command.current.id }, { signal: controller.signal });
      if (controller.signal.aborted) return;
      command.current = null;
      setIsDirty(false);
      setView(null);
      loadedCallback.current(null);
      onChanged();
      setReload((value) => value + 1);
    } catch (caught) {
      if (controller.signal.aborted) return;
      if (caught instanceof ApiError && caught.status === 409) {
        setStale(true);
        loadedCallback.current(null);
        setError("Negotiation changed. Reload and review the latest round before continuing.");
      } else setError(caught instanceof ApiError ? caught.message : "Unable to save this proposal.");
    } finally {
      if (!controller.signal.aborted) { request.current = null; setPending(false); }
    }
  }

  async function act(action: NegotiationAction) {
    if (request.current || !view || stale || deal.pending_counterparty || !view.eligible_actions.includes(action)) return;
    if (view.current_candidate && !replacementConfirmed) return;
    const latest = view.latest;
    const input: Omit<NegotiationInput, "command_id"> = {
      expected_deal_revision: view.deal_revision, organization_id: organizationId,
      base: latest ? { id: latest.id, terms_hash: latest.terms_hash, status: latest.status } : null,
      supersede_current_candidate: view.current_candidate,
    };
    const signature = JSON.stringify([deal.id, action, input]);
    if (command.current?.signature !== signature) command.current = { signature, id: crypto.randomUUID() };
    const controller = new AbortController();
    request.current = controller;
    setPending(true);
    setError("");
    try {
      await negotiateDeal(deal.id, action, { ...input, command_id: command.current.id }, { signal: controller.signal });
      if (controller.signal.aborted) return;
      command.current = null;
      setView(null);
      loadedCallback.current(null);
      onChanged();
      setReload((value) => value + 1);
    } catch (caught) {
      if (controller.signal.aborted) return;
      if (caught instanceof ApiError && caught.status === 409) {
        setStale(true);
        loadedCallback.current(null);
        setError("Negotiation changed. Reload and review the latest round before continuing.");
      } else setError(caught instanceof ApiError ? caught.message : "Unable to save this action.");
    } finally {
      if (!controller.signal.aborted) { request.current = null; setPending(false); }
    }
  }

  // Reorder helpers
  function moveItem(from: number, to: number) {
    if (to < 0 || to >= items.length) return;
    const updated = [...items];
    const [moved] = updated.splice(from, 1);
    updated.splice(to, 0, moved);
    setItems(updated);
    setIsDirty(true);
  }

  function moveShipment(from: number, to: number) {
    if (to < 0 || to >= shipments.length) return;
    const updated = [...shipments];
    const [moved] = updated.splice(from, 1);
    updated.splice(to, 0, moved);
    setShipments(updated);
    setIsDirty(true);
  }

  function movePayment(from: number, to: number) {
    if (to < 0 || to >= payments.length) return;
    const updated = [...payments];
    const [moved] = updated.splice(from, 1);
    updated.splice(to, 0, moved);
    setPayments(updated);
    setIsDirty(true);
  }

  const authoringStatus = stale
    ? "stale"
    : pending
    ? "pending"
    : authorError || error
    ? "error"
    : items.length === 0
    ? "empty"
    : isDirty
    ? "unsaved"
    : "ready";

  return (
    <section className="negotiation-review" aria-labelledby={`negotiation-heading-${deal.id}`}>
      <div className="panel-head">
        <h2 id={`negotiation-heading-${deal.id}`}>Review proposals</h2>
        <button type="button" className="button secondary" disabled={pending} onClick={() => setReload((value) => value + 1)}>Refresh proposals</button>
      </div>
      <p className="muted">
        A person submits each proposal. Accepting one moves its terms to Agreement review as a candidate;
        it does not approve or finalize the agreement.
      </p>
      {!view && !error ? <p role="status">Loading proposals…</p> : null}
      {error ? <p className="form-error" role="alert">{error}</p> : null}
      {view ? <>
        <p>{view.round_count} / {view.max_rounds} rounds</p>
        {view.escalated ? <p role="status">Escalation required</p> : null}
        {view.history_ambiguous ? <p role="alert">Legacy history requires review.</p> : null}
        {view.latest ? <>
          <h3>Latest human proposal · round {view.latest.proposal_number}</h3>
          <p>{proposalStatusLabel(view.latest, organizationId)}</p>
          <details>
            <summary>Proposal verification details</summary>
            <code className="agreement-review__hash">{view.latest.terms_hash}</code>
          </details>
          {view.latest.expires_at ? <p>Respond by: <time dateTime={view.latest.expires_at}>{new Date(view.latest.expires_at).toLocaleString()}</time></p> : null}
          <div className="agreement-terms" aria-label="Latest proposal terms">
            {view.latest.terms.line_items.map((item, index) => <dl className="agreement-terms__item" key={item.id ?? index}>
              {item.id ? <div><dt>Item ID</dt><dd>{item.id}</dd></div> : null}
              <div><dt>Item</dt><dd>{item.description}</dd></div>
              <div><dt>Quantity</dt><dd>{item.quantity} {item.unit}</dd></div>
              {item.sku ? <div><dt>SKU</dt><dd>{item.sku}</dd></div> : null}
              <div><dt>Unit price</dt><dd>{item.unit_price.amount} {item.unit_price.currency}</dd></div>
            </dl>)}
            {view.latest.terms.shipments.map((item, index) => <dl className="agreement-terms__item" key={item.id ?? index}>
              {item.id ? <div><dt>Shipment ID</dt><dd>{item.id}</dd></div> : null}
              <div><dt>Delivery</dt><dd>{item.quantity ?? "Not specified"} to {item.destination}</dd></div>
              <div><dt>Date</dt><dd>{item.target_date ?? "Not specified"}</dd></div>
              {item.allocations && item.allocations.length > 0 ? (
                <div><dt>Allocations</dt><dd>{item.allocations.map(a => `${a.quantity} ${a.unit} of item ${a.line_item_id}`).join(", ")}</dd></div>
              ) : null}
            </dl>)}
            {view.latest.terms.payment_terms.map((item, index) => <dl className="agreement-terms__item" key={item.id ?? index}>
              {item.id ? <div><dt>Payment Term ID</dt><dd>{item.id}</dd></div> : null}
              <div><dt>Payment</dt><dd>{item.amount.amount} {item.amount.currency}</dd></div>
              <div><dt>Due condition</dt><dd>{item.due_condition}</dd></div>
              {item.allocations && item.allocations.length > 0 ? (
                <div><dt>Allocations</dt><dd>{item.allocations.map(a => `${a.amount.amount} ${a.amount.currency} for obligation ${a.obligation_id}`).join(", ")}</dd></div>
              ) : null}
            </dl>)}
          </div>
          {view.current_candidate ? <label>
            <input type="checkbox" checked={replacementConfirmed} disabled={pending} onChange={(event) => setReplacementConfirmed(event.target.checked)} />
            Replace agreement version {view.current_candidate.version_number}. Its existing decisions will no longer apply.
          </label> : null}
          {view.current_candidate ? <p className="hint">
            This proposal created candidate agreement version {view.current_candidate.version_number}. Each organization must review that version and record its own decision. Both must approve the same version before an authorized member can commit it.
          </p> : null}
          <div className="fact-actions">
            {(["accept", "reject", "supersede", "expire"] as const).filter((action) => view.eligible_actions.includes(action)).map((action) =>
              <button type="button" className="button secondary" key={action}
                disabled={pending || stale || deal.pending_counterparty || Boolean(view.current_candidate && !replacementConfirmed)}
                onClick={() => void act(action)}>{ACTION_LABELS[action]}</button>)}
          </div>
        </> : <p>No human proposal has been submitted. Extracted facts and AI suggestions still need review by a person before they can become a proposal.</p>}

        {view.eligible_actions.includes("submit") || view.eligible_actions.includes("counter") ? (
          <div className="collection-authoring" aria-label="Create a trade proposal">
            <h3>Create a trade proposal</h3>
            <p className="hint" aria-label="Authoring draft status">Draft status: <strong>{authoringStatus}</strong></p>
            <button type="button" className="button secondary" onClick={resetEditor} style={{ marginBottom: "8px" }}>Reset draft</button>
            {authorError ? <p role="alert" className="form-error">{authorError}</p> : null}

            <div className="authoring-items" aria-label="Authoring line items">
              <h4>Line items</h4>
              <button type="button" className="button secondary" onClick={() => {
                const nextNum = items.length + 1;
                setItems([...items, { id: `item-${nextNum}`, description: "", quantity: "1", unit: "pieces", unitPrice: "0.00", currency: "USD", sku: "" }]);
                setIsDirty(true);
              }}>Add Line Item</button>

              {items.map((it, idx) => (
                <div key={idx} className="collection-item-row">
                  <div>
                    <label>ID: <input type="text" aria-label={`Item ID ${idx + 1}`} value={it.id} onChange={(e) => {
                      const updated = [...items];
                      updated[idx].id = e.target.value;
                      setItems(updated);
                      setIsDirty(true);
                    }} /></label>
                    <label>Description: <input type="text" aria-label={`Item description ${idx + 1}`} value={it.description} onChange={(e) => {
                      const updated = [...items];
                      updated[idx].description = e.target.value;
                      setItems(updated);
                      setIsDirty(true);
                    }} /></label>
                    <label>Quantity: <input type="text" aria-label={`Item quantity ${idx + 1}`} value={it.quantity} onChange={(e) => {
                      const updated = [...items];
                      updated[idx].quantity = e.target.value;
                      setItems(updated);
                      setIsDirty(true);
                    }} /></label>
                    <label>Unit: <input type="text" aria-label={`Item unit ${idx + 1}`} value={it.unit} onChange={(e) => {
                      const updated = [...items];
                      updated[idx].unit = e.target.value;
                      setItems(updated);
                      setIsDirty(true);
                    }} /></label>
                    <label>Unit Price: <input type="text" aria-label={`Item unit price ${idx + 1}`} value={it.unitPrice} onChange={(e) => {
                      const updated = [...items];
                      updated[idx].unitPrice = e.target.value;
                      setItems(updated);
                      setIsDirty(true);
                    }} /></label>
                    <label>Currency: <input type="text" aria-label={`Item currency ${idx + 1}`} value={it.currency} onChange={(e) => {
                      const updated = [...items];
                      updated[idx].currency = e.target.value;
                      setItems(updated);
                      setIsDirty(true);
                    }} /></label>
                    <label>SKU: <input type="text" aria-label={`Item SKU ${idx + 1}`} value={it.sku} onChange={(e) => {
                      const updated = [...items];
                      updated[idx].sku = e.target.value;
                      setItems(updated);
                      setIsDirty(true);
                    }} /></label>
                  </div>
                  <div>
                    <button type="button" aria-label={`Move item ${idx + 1} up`} disabled={idx === 0} onClick={() => moveItem(idx, idx - 1)}>↑</button>
                    <button type="button" aria-label={`Move item ${idx + 1} down`} disabled={idx === items.length - 1} onClick={() => moveItem(idx, idx + 1)}>↓↓</button>
                    <button type="button" aria-label={`Remove item ${idx + 1}`} onClick={() => {
                      const updated = items.filter((_, i) => i !== idx);
                      setItems(updated);
                      setIsDirty(true);
                    }}>Remove</button>
                  </div>
                </div>
              ))}
            </div>

            <div className="authoring-shipments" aria-label="Authoring shipments">
              <h4>Shipments</h4>
              <button type="button" className="button secondary" onClick={() => {
                const nextNum = shipments.length + 1;
                setShipments([...shipments, { id: `ship-${nextNum}`, destination: deliveryLocation, targetDate: "2030-01-01", allocations: [] }]);
                setIsDirty(true);
              }}>Add Shipment</button>

              {shipments.map((s, idx) => (
                <div key={idx} className="collection-shipment-row">
                  <div>
                    <label>ID: <input type="text" aria-label={`Shipment ID ${idx + 1}`} value={s.id} onChange={(e) => {
                      const updated = [...shipments];
                      updated[idx].id = e.target.value;
                      setShipments(updated);
                      setIsDirty(true);
                    }} /></label>
                    <label>Destination: <input type="text" aria-label={`Shipment destination ${idx + 1}`} value={s.destination} onChange={(e) => {
                      const updated = [...shipments];
                      updated[idx].destination = e.target.value;
                      setShipments(updated);
                      setIsDirty(true);
                    }} /></label>
                    <label>Target Date: <input type="text" aria-label={`Shipment target date ${idx + 1}`} value={s.targetDate} onChange={(e) => {
                      const updated = [...shipments];
                      updated[idx].targetDate = e.target.value;
                      setShipments(updated);
                      setIsDirty(true);
                    }} /></label>
                  </div>
                  <div>
                    <h5>Allocations</h5>
                    <button type="button" aria-label={`Add allocation to shipment ${idx + 1}`} onClick={() => {
                      const updated = [...shipments];
                      const firstItemId = items[0]?.id || "";
                      const firstItemUnit = items[0]?.unit || "pieces";
                      updated[idx].allocations.push({ line_item_id: firstItemId, quantity: "1", unit: firstItemUnit });
                      setShipments(updated);
                      setIsDirty(true);
                    }}>Add Allocation</button>
                    {s.allocations.map((a, aIdx) => (
                      <div key={aIdx} className="collection-allocation-row">
                        <label>Item: <input type="text" aria-label={`Shipment ${idx + 1} allocation line item ${aIdx + 1}`} value={a.line_item_id} onChange={(e) => {
                          const updated = [...shipments];
                          updated[idx].allocations[aIdx].line_item_id = e.target.value;
                          setShipments(updated);
                          setIsDirty(true);
                        }} /></label>
                        <label>Quantity: <input type="text" aria-label={`Shipment ${idx + 1} allocation quantity ${aIdx + 1}`} value={a.quantity} onChange={(e) => {
                          const updated = [...shipments];
                          updated[idx].allocations[aIdx].quantity = e.target.value;
                          setShipments(updated);
                          setIsDirty(true);
                        }} /></label>
                        <label>Unit: <input type="text" aria-label={`Shipment ${idx + 1} allocation unit ${aIdx + 1}`} value={a.unit} onChange={(e) => {
                          const updated = [...shipments];
                          updated[idx].allocations[aIdx].unit = e.target.value;
                          setShipments(updated);
                          setIsDirty(true);
                        }} /></label>
                        <button type="button" aria-label={`Remove allocation ${aIdx + 1} from shipment ${idx + 1}`} onClick={() => {
                          const updated = [...shipments];
                          updated[idx].allocations = updated[idx].allocations.filter((_, i) => i !== aIdx);
                          setShipments(updated);
                          setIsDirty(true);
                        }}>Remove Allocation</button>
                      </div>
                    ))}
                  </div>
                  <div>
                    <button type="button" aria-label={`Move shipment ${idx + 1} up`} disabled={idx === 0} onClick={() => moveShipment(idx, idx - 1)}>↑</button>
                    <button type="button" aria-label={`Move shipment ${idx + 1} down`} disabled={idx === shipments.length - 1} onClick={() => moveShipment(idx, idx + 1)}>↓</button>
                    <button type="button" aria-label={`Remove shipment ${idx + 1}`} onClick={() => {
                      const updated = shipments.filter((_, i) => i !== idx);
                      setShipments(updated);
                      setIsDirty(true);
                    }}>Remove</button>
                  </div>
                </div>
              ))}
            </div>

            <div className="authoring-payments" aria-label="Authoring payment terms">
              <h4>Payment terms</h4>
              <button type="button" className="button secondary" onClick={() => {
                const nextNum = payments.length + 1;
                setPayments([...payments, { id: `pay-${nextNum}`, amount: "0.00", currency: "USD", trigger: "seller_invoice", dueCondition: "when seller invoices", allocations: [] }]);
                setIsDirty(true);
              }}>Add Payment Term</button>

              {payments.map((p, idx) => (
                <div key={idx} className="collection-payment-row">
                  <div>
                    <label>ID: <input type="text" aria-label={`Payment term ID ${idx + 1}`} value={p.id} onChange={(e) => {
                      const updated = [...payments];
                      updated[idx].id = e.target.value;
                      setPayments(updated);
                      setIsDirty(true);
                    }} /></label>
                    <label>Amount: <input type="text" aria-label={`Payment term amount ${idx + 1}`} value={p.amount} onChange={(e) => {
                      const updated = [...payments];
                      updated[idx].amount = e.target.value;
                      setPayments(updated);
                      setIsDirty(true);
                    }} /></label>
                    <label>Currency: <input type="text" aria-label={`Payment term currency ${idx + 1}`} value={p.currency} onChange={(e) => {
                      const updated = [...payments];
                      updated[idx].currency = e.target.value;
                      setPayments(updated);
                      setIsDirty(true);
                    }} /></label>
                    <label>Trigger: <input type="text" aria-label={`Payment term trigger ${idx + 1}`} value={p.trigger} onChange={(e) => {
                      const updated = [...payments];
                      updated[idx].trigger = e.target.value;
                      setPayments(updated);
                      setIsDirty(true);
                    }} /></label>
                    <label>Due condition: <input type="text" aria-label={`Payment term due condition ${idx + 1}`} value={p.dueCondition} onChange={(e) => {
                      const updated = [...payments];
                      updated[idx].dueCondition = e.target.value;
                      setPayments(updated);
                      setIsDirty(true);
                    }} /></label>
                  </div>
                  <div>
                    <h5>Allocations</h5>
                    <button type="button" aria-label={`Add allocation to payment term ${idx + 1}`} onClick={() => {
                      const updated = [...payments];
                      const firstObligationId = shipments[0]?.id || items[0]?.id || "";
                      updated[idx].allocations.push({ obligation_id: firstObligationId, amount: "0.00", currency: p.currency });
                      setPayments(updated);
                      setIsDirty(true);
                    }}>Add Allocation</button>
                    {p.allocations.map((a, aIdx) => (
                      <div key={aIdx} className="collection-allocation-row">
                        <label>Obligation: <input type="text" aria-label={`Payment term ${idx + 1} allocation obligation ${aIdx + 1}`} value={a.obligation_id} onChange={(e) => {
                          const updated = [...payments];
                          updated[idx].allocations[aIdx].obligation_id = e.target.value;
                          setPayments(updated);
                          setIsDirty(true);
                        }} /></label>
                        <label>Amount: <input type="text" aria-label={`Payment term ${idx + 1} allocation amount ${aIdx + 1}`} value={a.amount} onChange={(e) => {
                          const updated = [...payments];
                          updated[idx].allocations[aIdx].amount = e.target.value;
                          setPayments(updated);
                          setIsDirty(true);
                        }} /></label>
                        <label>Currency: <input type="text" aria-label={`Payment term ${idx + 1} allocation currency ${aIdx + 1}`} value={a.currency} onChange={(e) => {
                          const updated = [...payments];
                          updated[idx].allocations[aIdx].currency = e.target.value;
                          setPayments(updated);
                          setIsDirty(true);
                        }} /></label>
                        <button type="button" aria-label={`Remove allocation ${aIdx + 1} from payment term ${idx + 1}`} onClick={() => {
                          const updated = [...payments];
                          updated[idx].allocations = updated[idx].allocations.filter((_, i) => i !== aIdx);
                          setPayments(updated);
                          setIsDirty(true);
                        }}>Remove Allocation</button>
                      </div>
                    ))}
                  </div>
                  <div>
                    <button type="button" aria-label={`Move payment term ${idx + 1} up`} disabled={idx === 0} onClick={() => movePayment(idx, idx - 1)}>↑</button>
                    <button type="button" aria-label={`Move payment term ${idx + 1} down`} disabled={idx === payments.length - 1} onClick={() => movePayment(idx, idx + 1)}>↓</button>
                    <button type="button" aria-label={`Remove payment term ${idx + 1}`} onClick={() => {
                      const updated = payments.filter((_, i) => i !== idx);
                      setPayments(updated);
                      setIsDirty(true);
                    }}>Remove</button>
                  </div>
                </div>
              ))}
            </div>

            <div className="authoring-conditions">
              <h4>Trade conditions</h4>
              <label>Delivery location: <input type="text" aria-label="Delivery location" value={deliveryLocation} onChange={(e) => { setDeliveryLocation(e.target.value); setIsDirty(true); }} /></label>
              <label>Incoterm: <input type="text" aria-label="Incoterm" value={incoterm} onChange={(e) => { setIncoterm(e.target.value); setIsDirty(true); }} /></label>
              <label>Cancellation terms: <input type="text" aria-label="Cancellation terms" value={cancellationTerms} onChange={(e) => { setCancellationTerms(e.target.value); setIsDirty(true); }} /></label>
              <p className="hint">Taxes, freight, customs classification, and other fees: Not recorded in committed terms</p>
            </div>

            <div className="fact-actions" style={{ marginTop: "12px" }}>
              {view.eligible_actions.includes("counter") ? (
                <button
                  type="button"
                  className="button"
                  disabled={pending || stale || deal.pending_counterparty || Boolean(view.current_candidate && !replacementConfirmed)}
                  onClick={() => void submitAuthoring("counter")}
                >
                  {pending ? "Submitting counter-proposal…" : "Submit counter-proposal"}
                </button>
              ) : view.eligible_actions.includes("submit") ? (
                <button
                  type="button"
                  className="button"
                  disabled={pending || stale || deal.pending_counterparty || Boolean(view.current_candidate && !replacementConfirmed)}
                  onClick={() => void submitAuthoring("submit")}
                >
                  {pending ? "Submitting proposal…" : "Submit proposal"}
                </button>
              ) : null}
            </div>
          </div>
        ) : null}

        <h3>Proposal history</h3>
        <ol>{view.proposals.map((proposal) => <li key={proposal.id}>
          <details><summary>Round {proposal.proposal_number}: {proposalStatusLabel(proposal, organizationId)}{proposal.lifecycle_origin === "LEGACY" ? " (legacy record)" : ""}</summary>
            <code className="agreement-review__hash">{proposal.terms_hash}</code>
            {proposal.terms.line_items.map((item, index) => <p key={index}>{item.id ? `[${item.id}] ` : ""}{item.description}: {item.quantity} {item.unit} at {item.unit_price.amount} {item.unit_price.currency}</p>)}
            {proposal.evidence_refs.map((ref) => <p key={ref.fact_id}>Evidence {ref.fact_id}, version {ref.version}</p>)}
          </details>
        </li>)}</ol>
        <h3>Proposal activity</h3>
        <ol>{view.history.map((event) => <li key={event.id}>
          <time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time>: {historyActionLabel(event.action)}
          {event.invalidated_candidate_id ? " - prior candidate invalidated" : ""}
        </li>)}</ol>
      </> : null}
    </section>
  );
}
