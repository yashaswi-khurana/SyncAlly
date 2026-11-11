import { useEffect, useLayoutEffect, useRef, useState } from "react";

import { ApiError, getNegotiation, negotiateDeal } from "../api/client";
import type {
  Deal,
  NegotiationAction,
  NegotiationInput,
  NegotiationProposal,
  NegotiationView,
  PaymentTrigger,
  ReviewedProposalTerms,
} from "../api/types";
import { isPaymentTrigger, SUPPORTED_PAYMENT_TIMING } from "../api/types";
import ProposalComparison from "./ProposalComparison";

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
  const paymentTiming = SUPPORTED_PAYMENT_TIMING[0];
  return {
    items: [
      { id: "item-1", description: "", quantity: "", unit: "", unitPrice: "", currency: "", sku: "" },
    ],
    shipments: [
      { id: "ship-1", destination: "", targetDate: "", allocations: [{ line_item_id: "item-1", quantity: "", unit: "" }] },
    ],
    payments: [
      { id: "pay-1", amount: "", currency: "", trigger: paymentTiming.trigger, dueCondition: paymentTiming.dueCondition, allocations: [{ obligation_id: "ship-1", amount: "", currency: "" }] },
    ],
    deliveryLocation: "",
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

const DECIMAL_SCALE = BigInt("1000000000000000000");

function formatScaled(value: bigint): string {
  const whole = value / DECIMAL_SCALE;
  const fraction = (value % DECIMAL_SCALE).toString().padStart(18, "0").replace(/0+$/, "");
  return fraction ? `${whole}.${fraction}` : whole.toString();
}

function calculateOrderTotal(items: ItemDraft[]): string | null {
  if (items.length === 0 || items.some((item) => !isValidDecimal(item.quantity) || !isValidDecimal(item.unitPrice))) return null;
  const total = items.reduce((sum, item) => sum + (parseScaled(item.quantity) * parseScaled(item.unitPrice)) / DECIMAL_SCALE, BigInt(0));
  return formatScaled(total);
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
  const [deliveryLocation, setDeliveryLocation] = useState("");
  const [incoterm, setIncoterm] = useState("");
  const [cancellationTerms, setCancellationTerms] = useState("");
  const [isDirty, setIsDirty] = useState(false);

  const loadContext = JSON.stringify([deal.id, deal.version, organizationId, reloadToken, reload]);
  const loadContextRef = useRef(loadContext);
  const [observedContext, setObservedContext] = useState(loadContext);
  if (loadContext !== observedContext) {
    const draft = defaultDraft();
    setObservedContext(loadContext);
    setView(null);
    setPending(false);
    setError("");
    setAuthorError("");
    setStale(false);
    setReplacementConfirmed(false);
    setItems(draft.items);
    setShipments(draft.shipments);
    setPayments(draft.payments);
    setDeliveryLocation(draft.deliveryLocation);
    setIncoterm(draft.incoterm);
    setCancellationTerms(draft.cancellationTerms);
    setIsDirty(false);
  }

  function populateEditorFromTerms(terms: ReviewedProposalTerms) {
    if (terms.schema_version === 2) {
      setItems((terms.line_items ?? []).map((it, idx) => ({
        id: it.id || `item-${idx + 1}`,
        description: it.description,
        quantity: it.quantity,
        unit: it.unit,
        unitPrice: it.unit_price.amount,
        currency: it.unit_price.currency,
        sku: it.sku || "",
      })));
      setShipments((terms.shipments ?? []).map((s, idx) => ({
        id: s.id || `ship-${idx + 1}`,
        destination: s.destination || (idx === 0 ? terms.delivery_location ?? "" : ""),
        targetDate: s.target_date || "",
        allocations: (s.allocations || []).map(a => ({
          line_item_id: a.line_item_id,
          quantity: a.quantity,
          unit: a.unit,
        })),
      })));
      setPayments((terms.payment_terms ?? []).map((p, idx) => ({
        id: p.id || `pay-${idx + 1}`,
        amount: p.amount.amount,
        currency: p.amount.currency,
        trigger: isPaymentTrigger(p.trigger) ? p.trigger : SUPPORTED_PAYMENT_TIMING[0].trigger,
        dueCondition: isPaymentTrigger(p.trigger) ? p.due_condition : SUPPORTED_PAYMENT_TIMING[0].dueCondition,
        allocations: (p.allocations || []).map(a => ({
          obligation_id: a.obligation_id,
          amount: a.amount.amount,
          currency: a.amount.currency,
        })),
      })));
      setIncoterm(terms.incoterm ?? "");
      setCancellationTerms(terms.cancellation_terms ?? "");
      setDeliveryLocation(terms.delivery_location ?? "");
    }
  }

  function resetEditor() {
    if (view?.latest?.terms && view.latest.terms.schema_version === 2) {
      populateEditorFromTerms(view.latest.terms);
    } else {
      const draft = defaultDraft();
      setItems(draft.items);
      setShipments(draft.shipments);
      setPayments(draft.payments);
      setDeliveryLocation(draft.deliveryLocation);
      setIncoterm(draft.incoterm);
      setCancellationTerms(draft.cancellationTerms);
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
  useLayoutEffect(() => { loadContextRef.current = loadContext; }, [loadContext]);

  useEffect(() => {
    const requestContext = loadContext;
    const controller = new AbortController();
    request.current?.abort();
    request.current = null;
    loadedCallback.current(null);
    void getNegotiation(deal.id, organizationId, { signal: controller.signal }).then((next) => {
      if (controller.signal.aborted || loadContextRef.current !== requestContext
        || next.deal_id !== deal.id || next.organization_id !== organizationId) return;
      setView(next);
      loadedCallback.current(next);
      if (next?.latest?.terms && next.latest.terms.schema_version === 2) {
        populateEditorFromTerms(next.latest.terms);
      }
    }).catch((caught: unknown) => {
      if (!controller.signal.aborted && loadContextRef.current === requestContext) {
        setError(caught instanceof ApiError ? caught.message : "Unable to load negotiation rounds.");
      }
    });
    return () => { controller.abort(); request.current?.abort(); };
  }, [deal.id, deal.version, organizationId, reloadToken, reload, loadContext]);

  function validateCollections(shipmentDrafts = shipments, paymentDrafts = payments): string | null {
    if (items.length === 0) return "At least one line item is required.";
    if (shipmentDrafts.length === 0) return "Add at least one delivery.";
    if (paymentDrafts.length === 0) return "Add at least one payment term.";

    const allIds = new Set<string>();
    const currencies = new Set<string>();

    for (let i = 0; i < items.length; i++) {
      const it = items[i];
      if (!it.id.trim()) return `Product ${i + 1} is missing an internal reference. Reset the draft and try again.`;
      if (allIds.has(it.id)) return `There is a duplicate product reference. Reset the draft and try again.`;
      allIds.add(it.id);
      if (!it.description.trim()) return `Enter a name or description for product ${i + 1}.`;
      if (!isValidDecimal(it.quantity)) return `Enter a valid quantity for ${it.description}.`;
      if (!it.unit.trim()) return `Choose a unit for ${it.description}, such as boxes or kilograms.`;
      if (!isValidDecimal(it.unitPrice)) return `Enter a valid price per unit for ${it.description}.`;
      if (!it.currency || it.currency.length !== 3) return `Enter a 3-letter currency code for ${it.description}, such as INR or USD.`;
      currencies.add(it.currency);
    }

    if (!deliveryLocation.trim()) return "Delivery location is required.";

    for (let i = 0; i < shipmentDrafts.length; i++) {
      const s = shipmentDrafts[i];
      if (!s.id.trim()) return `Delivery ${i + 1} is missing an internal reference. Reset the draft and try again.`;
      if (allIds.has(s.id)) return `There is a duplicate delivery reference. Reset the draft and try again.`;
      allIds.add(s.id);
      if (!s.destination.trim()) return `Enter a destination for delivery ${i + 1}.`;
      if (!s.targetDate.trim()) return `Choose a requested arrival date for delivery ${i + 1}.`;
      if (s.allocations.length === 0) return `Add at least one product to delivery ${i + 1}.`;
      for (const a of s.allocations) {
        if (!a.line_item_id.trim()) return `Choose a product for delivery ${i + 1}.`;
        const targetItem = items.find(it => it.id === a.line_item_id);
        if (!targetItem) return `Choose a listed product for delivery ${i + 1}.`;
        if (a.unit !== targetItem.unit) return `The unit for ${targetItem.description} must match the order details.`;
        if (!isValidDecimal(a.quantity)) return `Enter a valid quantity of ${targetItem.description} for delivery ${i + 1}.`;
      }
    }

    for (let i = 0; i < paymentDrafts.length; i++) {
      const p = paymentDrafts[i];
      if (!p.id.trim()) return `Payment stage ${i + 1} is missing an internal reference. Reset the draft and try again.`;
      if (allIds.has(p.id)) return `There is a duplicate payment reference. Reset the draft and try again.`;
      allIds.add(p.id);
      if (!isValidDecimal(p.amount)) return `Enter a valid amount for payment stage ${i + 1}.`;
      if (!p.currency || p.currency.length !== 3) return `Enter a 3-letter currency code for payment stage ${i + 1}.`;
      currencies.add(p.currency);
      if (!isPaymentTrigger(p.trigger)) return `Choose when payment stage ${i + 1} is due.`;
      if (!p.dueCondition.trim()) return `Choose when payment stage ${i + 1} is due.`;
      if (p.allocations.length === 0) return `Link payment stage ${i + 1} to a delivery.`;
      for (const a of p.allocations) {
        if (!a.obligation_id.trim()) return `Link payment stage ${i + 1} to a delivery.`;
        const obligationExists = shipmentDrafts.some(s => s.id === a.obligation_id) || items.some(item => item.id === a.obligation_id);
        if (!obligationExists) return `Choose one of the listed products or deliveries for payment stage ${i + 1}.`;
        if (!isValidDecimal(a.amount)) return `Enter a valid amount for each delivery share in payment stage ${i + 1}.`;
        if (a.currency !== p.currency) return `Use the same currency for payment stage ${i + 1} and its delivery shares.`;
      }
    }

    if (currencies.size > 1) return "Use one currency throughout this proposal.";

    for (const it of items) {
      let totalAlloc = BigInt(0);
      for (const s of shipmentDrafts) {
        for (const a of s.allocations) {
          if (a.line_item_id === it.id) {
            totalAlloc += parseScaled(a.quantity);
          }
        }
      }
      const itemQty = parseScaled(it.quantity);
      if (totalAlloc !== itemQty) {
        return `The quantities assigned across deliveries for ${it.description} must add up to the order quantity.`;
      }
    }

    for (const p of paymentDrafts) {
      let termAlloc = BigInt(0);
      for (const a of p.allocations) {
        termAlloc += parseScaled(a.amount);
      }
      if (termAlloc !== parseScaled(p.amount)) {
        return `Delivery shares for a payment stage must add up to that stage's amount.`;
      }
    }

    let totalItemsAmount = BigInt(0);
    for (const it of items) {
      const q = parseScaled(it.quantity);
      const p = parseScaled(it.unitPrice);
      totalItemsAmount += (q * p) / BigInt("1000000000000000000");
    }
    let totalPaymentsAmount = BigInt(0);
    for (const p of paymentDrafts) {
      totalPaymentsAmount += parseScaled(p.amount);
    }
    if (totalItemsAmount !== totalPaymentsAmount) {
      return "Payment stages must add up to the full order total.";
    }

    return null;
  }

  async function submitAuthoring(action: "submit" | "counter") {
    if (request.current || !view || stale || deal.pending_counterparty || !view.eligible_actions.includes(action)) return;
    if (view.current_candidate && !replacementConfirmed) return;

    const orderTotal = calculateOrderTotal(items);
    const proposalShipments = shipments.map((shipment) => ({
      ...shipment,
      allocations: shipments.length === 1
        ? items.map((item) => ({ line_item_id: item.id, quantity: item.quantity, unit: item.unit }))
        : shipment.allocations,
    }));
    const proposalPayments = payments.map((payment) => {
      const amount = payments.length === 1 && orderTotal !== null ? orderTotal : payment.amount;
      const currency = payments.length === 1 ? payment.currency || items[0]?.currency || "" : payment.currency;
      return {
        ...payment,
        amount,
        currency,
        allocations: payment.allocations.length > 1
          ? payment.allocations
          : [{ obligation_id: payment.allocations[0]?.obligation_id || proposalShipments[0]?.id || "", amount, currency }],
      };
    });
    const validationErr = validateCollections(proposalShipments, proposalPayments);
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
      shipments: proposalShipments.map(s => ({
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
      payment_terms: proposalPayments.map(p => ({
        id: p.id,
        amount: { amount: p.amount, currency: p.currency },
        trigger: p.trigger,
        due_condition: p.dueCondition,
        allocations: p.allocations.map(a => ({
          obligation_id: a.obligation_id,
          amount: { amount: a.amount, currency: a.currency },
        })),
      })),
      delivery_location: deliveryLocation.trim(),
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
          <ProposalComparison latest={view.latest} proposals={view.proposals} />
          <div className="agreement-terms" aria-label="Latest proposal terms">
            {(view.latest.terms.line_items ?? []).map((item, index) => <dl className="agreement-terms__item" key={item.id ?? index}>
              {item.id ? <div><dt>Item ID</dt><dd>{item.id}</dd></div> : null}
              <div><dt>Item</dt><dd>{item.description}</dd></div>
              <div><dt>Quantity</dt><dd>{item.quantity} {item.unit}</dd></div>
              {item.sku ? <div><dt>SKU</dt><dd>{item.sku}</dd></div> : null}
              <div><dt>Unit price</dt><dd>{item.unit_price.amount} {item.unit_price.currency}</dd></div>
            </dl>)}
            {(view.latest.terms.shipments ?? []).map((item, index) => <dl className="agreement-terms__item" key={item.id ?? index}>
              {item.id ? <div><dt>Shipment ID</dt><dd>{item.id}</dd></div> : null}
              <div><dt>Delivery</dt><dd>{item.quantity ?? "Not specified"} to {item.destination}</dd></div>
              <div><dt>Date</dt><dd>{item.target_date ?? "Not specified"}</dd></div>
              {item.allocations && item.allocations.length > 0 ? (
                <div><dt>Allocations</dt><dd>{item.allocations.map(a => `${a.quantity} ${a.unit} of item ${a.line_item_id}`).join(", ")}</dd></div>
              ) : null}
            </dl>)}
            {(view.latest.terms.payment_terms ?? []).map((item, index) => <dl className="agreement-terms__item" key={item.id ?? index}>
              {item.id ? <div><dt>Payment Term ID</dt><dd>{item.id}</dd></div> : null}
              <div><dt>Payment</dt><dd>{item.amount.amount} {item.amount.currency}</dd></div>
              <div><dt>Due condition</dt><dd>{item.due_condition}</dd></div>
              {item.allocations && item.allocations.length > 0 ? (
                <div><dt>Allocations</dt><dd>{item.allocations.map(a => `${a.amount.amount} ${a.amount.currency} for obligation ${a.obligation_id}`).join(", ")}</dd></div>
              ) : null}
            </dl>)}
          </div>
          {view.current_candidate ? <label className="check-row">
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
          <details className="collection-authoring" aria-label="Create a trade proposal">
            <summary><h3>Create a trade proposal</h3><span className="badge">Manual proposal</span></summary>
            <p className="proposal-editor__intro">Review your conversation and any AI suggestions above. Use this proposal to put the agreed product, delivery, and payment terms in one place for both businesses.</p>
            <ol className="proposal-workflow" aria-label="What happens after you send this proposal">
              <li><span>1</span>Partner reviews or counters</li><li><span>2</span>Both sides approve the same agreement</li><li><span>3</span>Agreement is committed, then invoice, payment, and delivery are recorded</li>
            </ol>
            <p className="hint">Sending shares the proposal with your partner. It does not approve or commit the agreement, request payment, or arrange delivery.</p>
            {authorError ? <p role="alert" className="form-error">{authorError}</p> : null}
            <p className="proposal-editor__draft-note" aria-label="Authoring draft status" aria-live="polite">{stale ? "This deal has changed. Reload the draft before sending." : pending ? "Sending draft…" : isDirty ? "Unsaved draft changes" : "This is a draft · nothing has been sent"}</p>
            <button type="button" className="button secondary proposal-editor__reset" onClick={resetEditor}>Reset draft</button>

            <div className="authoring-items" aria-label="Authoring line items">
              <div className="proposal-section__heading"><div><span className="proposal-section__step">01 / ORDER</span><h4>What is being traded?</h4></div><p>Add each product or service with its quantity and agreed unit price.</p></div>
              <button type="button" className="button secondary" onClick={() => {
                const nextNum = items.length + 1;
                setItems([...items, { id: `item-${nextNum}`, description: "", quantity: "", unit: "", unitPrice: "", currency: "", sku: "" }]);
                setIsDirty(true);
              }}>Add product</button>

              {items.map((it, idx) => (
                <div key={idx} className="collection-item-row">
                  <div>
                    <label>Item description <input type="text" aria-label={`Item description ${idx + 1}`} placeholder="e.g. Stainless steel bolts" value={it.description} onChange={(e) => {
                      const updated = [...items];
                      updated[idx].description = e.target.value;
                      setItems(updated);
                      setIsDirty(true);
                    }} /></label>
                    <label>Item quantity <input type="text" inputMode="decimal" aria-label={`Item quantity ${idx + 1}`} placeholder="e.g. 120" value={it.quantity} onChange={(e) => {
                      const updated = [...items];
                      updated[idx].quantity = e.target.value;
                      setItems(updated);
                      setIsDirty(true);
                    }} /></label>
                    <label>Unit <input type="text" aria-label={`Unit ${idx + 1}`} placeholder="boxes, kg, units…" value={it.unit} onChange={(e) => {
                      const updated = [...items];
                      updated[idx].unit = e.target.value;
                      setItems(updated);
                      setIsDirty(true);
                    }} /></label>
                    <label>Price per unit <input type="text" inputMode="decimal" aria-label={`Price per unit ${idx + 1}`} placeholder="e.g. 25" value={it.unitPrice} onChange={(e) => {
                      const updated = [...items];
                      updated[idx].unitPrice = e.target.value;
                      setItems(updated);
                      setIsDirty(true);
                    }} /></label>
                    <label>Currency code <input type="text" aria-label={`Currency code ${idx + 1}`} placeholder="INR" maxLength={3} value={it.currency} onChange={(e) => {
                      const updated = [...items];
                      updated[idx].currency = e.target.value.toUpperCase();
                      setItems(updated);
                      setIsDirty(true);
                    }} /></label>
                  </div>
                  {items.length > 1 ? <div>
                    <button type="button" className="button secondary" aria-label={`Remove product ${idx + 1}`} onClick={() => {
                      const updated = items.filter((_, i) => i !== idx);
                      setItems(updated);
                      setIsDirty(true);
                    }}>Remove product</button>
                  </div> : null}
                  <details className="proposal-editor__optional"><summary>Optional product reference</summary><label>SKU or seller reference <input type="text" aria-label={`SKU or seller reference ${idx + 1}`} placeholder="Optional" value={it.sku} onChange={(e) => {
                    const updated = [...items];
                    updated[idx].sku = e.target.value;
                    setItems(updated);
                    setIsDirty(true);
                  }} /></label></details>
                </div>
              ))}
              <div className="proposal-order-total" aria-live="polite">
                <span>Order total</span><strong>{calculateOrderTotal(items) !== null && items[0]?.currency ? `${calculateOrderTotal(items)} ${items[0].currency.toUpperCase()}` : "Add quantity and price to calculate"}</strong>
              </div>
            </div>

            <div className="authoring-shipments" aria-label="Authoring shipments">
              <div className="proposal-section__heading"><div><span className="proposal-section__step">02 / DELIVERY</span><h4>Where and when will it arrive?</h4></div><p>Use the destination and requested arrival date both sides can plan around.</p></div>
              <label>Delivery location<input type="text" aria-label="Delivery location" placeholder="City, port, or region for the overall delivery" value={deliveryLocation} onChange={(e) => { setDeliveryLocation(e.target.value); setIsDirty(true); }} /></label>
              <button type="button" className="button secondary" onClick={() => {
                const nextNum = shipments.length + 1;
                setShipments([...shipments, { id: `ship-${nextNum}`, destination: "", targetDate: "", allocations: items.map((item) => ({ line_item_id: item.id, quantity: "", unit: item.unit })) }]);
                setIsDirty(true);
              }}>Add delivery</button>

              {shipments.map((s, idx) => (
                <div key={idx} className="collection-shipment-row">
                  <div>
                    <label>{shipments.length > 1 ? `Shipment destination ${idx + 1}` : "Shipment destination"}<input type="text" aria-label={`Shipment destination ${idx + 1}`} placeholder="City, region, country" value={s.destination} onChange={(e) => {
                      const updated = [...shipments];
                      updated[idx].destination = e.target.value;
                      setShipments(updated);
                      setIsDirty(true);
                    }} /></label>
                    <label>Requested arrival date<input type="date" aria-label={`Requested arrival date ${idx + 1}`} value={s.targetDate} onChange={(e) => {
                      const updated = [...shipments];
                      updated[idx].targetDate = e.target.value;
                      setShipments(updated);
                      setIsDirty(true);
                    }} /></label>
                  </div>
                  {shipments.length > 1 ? <div className="proposal-editor__allocations">
                    <h5>Products in this delivery</h5>
                    <button type="button" className="button secondary" aria-label={`Add product to delivery ${idx + 1}`} onClick={() => {
                      const updated = [...shipments];
                      const firstItemId = items[0]?.id || "";
                      const firstItemUnit = items[0]?.unit || "pieces";
                      updated[idx].allocations.push({ line_item_id: firstItemId, quantity: "", unit: firstItemUnit });
                      setShipments(updated);
                      setIsDirty(true);
                    }}>Add product to delivery</button>
                    {s.allocations.map((a, aIdx) => (
                      <div key={aIdx} className="collection-allocation-row">
                        <label>Product<select aria-label={`Product in delivery ${idx + 1}, row ${aIdx + 1}`} value={a.line_item_id} onChange={(e) => {
                          const updated = [...shipments];
                          updated[idx].allocations[aIdx].line_item_id = e.target.value;
                          updated[idx].allocations[aIdx].unit = items.find((item) => item.id === e.target.value)?.unit ?? "";
                          setShipments(updated);
                          setIsDirty(true);
                        }}>{items.map((item, itemIdx) => <option key={item.id} value={item.id}>{item.description || `Product ${itemIdx + 1}`}</option>)}</select></label>
                        <label>Quantity ({items.find((item) => item.id === a.line_item_id)?.unit || "unit"})<input type="text" inputMode="decimal" aria-label={`Quantity in delivery ${idx + 1}, row ${aIdx + 1}`} value={a.quantity} onChange={(e) => {
                          const updated = [...shipments];
                          updated[idx].allocations[aIdx].quantity = e.target.value;
                          setShipments(updated);
                          setIsDirty(true);
                        }} /></label>
                        <button type="button" aria-label={`Remove allocation ${aIdx + 1} from shipment ${idx + 1}`} onClick={() => {
                          const updated = [...shipments];
                          updated[idx].allocations = updated[idx].allocations.filter((_, i) => i !== aIdx);
                          setShipments(updated);
                          setIsDirty(true);
                        }}>Remove product</button>
                      </div>
                    ))}
                  </div> : <p className="proposal-editor__auto-note">All listed products and quantities are assigned to this delivery automatically.</p>}
                  {shipments.length > 1 ? <div>
                    <button type="button" className="button secondary" aria-label={`Remove delivery ${idx + 1}`} onClick={() => {
                      const updated = shipments.filter((_, i) => i !== idx);
                      setShipments(updated);
                      setIsDirty(true);
                    }}>Remove delivery</button>
                  </div> : null}
                </div>
              ))}
            </div>

            <div className="authoring-payments" aria-label="Authoring payment terms">
              <div className="proposal-section__heading"><div><span className="proposal-section__step">03 / PAYMENT</span><h4>When should payment be made?</h4></div><p>A single payment defaults to the full order total. Add stages to split it into separate amounts.</p></div>
              <button type="button" className="button secondary" onClick={() => {
                const nextNum = payments.length + 1;
                const timing = SUPPORTED_PAYMENT_TIMING[0];
                const orderTotal = calculateOrderTotal(items);
                const existing = payments.length === 1 && orderTotal !== null
                  ? [{ ...payments[0], amount: orderTotal, currency: payments[0].currency || items[0]?.currency || "" }]
                  : payments;
                setPayments([...existing, { id: `pay-${nextNum}`, amount: "", currency: items[0]?.currency ?? "", trigger: timing.trigger, dueCondition: timing.dueCondition, allocations: [{ obligation_id: shipments[0]?.id ?? items[0]?.id ?? "", amount: "", currency: items[0]?.currency ?? "" }] }]);
                setIsDirty(true);
              }}>Add payment stage</button>

              {payments.map((p, idx) => (
                <div key={idx} className="collection-payment-row">
                  <div>
                    <label>Payment term amount<input type="text" inputMode="decimal" aria-label={`Payment term amount ${idx + 1}`} placeholder="e.g. 1500" value={p.amount} onChange={(e) => {
                      const updated = [...payments];
                      updated[idx].amount = e.target.value;
                      setPayments(updated);
                      setIsDirty(true);
                    }} /></label>
                    {payments.length === 1 ? <p className="proposal-editor__auto-note">{calculateOrderTotal(items) !== null && items[0]?.currency ? `A single payment defaults to the full order total of ${calculateOrderTotal(items)} ${items[0].currency.toUpperCase()} when left blank.` : "A single payment defaults to the full order total. Complete the order details first."}</p> : null}
                    {payments.length > 1 ? <label>Currency code<input type="text" aria-label={`Payment currency code ${idx + 1}`} placeholder={items[0]?.currency || "INR"} maxLength={3} value={p.currency} onChange={(e) => {
                      const updated = [...payments];
                      const currency = e.target.value.toUpperCase();
                      updated[idx].currency = currency;
                      updated[idx].allocations = updated[idx].allocations.map((allocation) => ({ ...allocation, currency }));
                      setPayments(updated);
                      setIsDirty(true);
                    }} /></label> : null}
                    {SUPPORTED_PAYMENT_TIMING.length === 1 ? <div className="proposal-payment-timing"><span>Payment timing</span><strong>{SUPPORTED_PAYMENT_TIMING[0].label}</strong><small>{SUPPORTED_PAYMENT_TIMING[0].dueCondition}</small></div> : <label>Payment timing<select aria-label={`Payment timing ${idx + 1}`} value={isPaymentTrigger(p.trigger) ? p.trigger : ""} onChange={(e) => {
                      if (!isPaymentTrigger(e.target.value)) return;
                      const updated = [...payments];
                      const timing = SUPPORTED_PAYMENT_TIMING.find((option) => option.trigger === e.target.value);
                      updated[idx].trigger = e.target.value as PaymentTrigger;
                      updated[idx].dueCondition = timing?.dueCondition ?? "";
                      setPayments(updated);
                      setIsDirty(true);
                    }}>
                      <option value="">Choose when payment is due</option>
                      {SUPPORTED_PAYMENT_TIMING.map((timing) => <option key={timing.trigger} value={timing.trigger}>{timing.label}</option>)}
                    </select></label>}
                  </div>
                  {shipments.length > 1 ? <div className="proposal-editor__allocations">
                    {p.allocations.length <= 1 ? <>
                      <label>Applies to<select aria-label={`Product or delivery for payment stage ${idx + 1}`} value={p.allocations[0]?.obligation_id ?? shipments[0].id} onChange={(e) => {
                        const updated = [...payments];
                        updated[idx].allocations = [{ obligation_id: e.target.value, amount: updated[idx].amount, currency: updated[idx].currency }];
                        setPayments(updated);
                        setIsDirty(true);
                      }}>{shipments.map((shipment, shipmentIdx) => <option key={shipment.id} value={shipment.id}>{shipment.destination || `Delivery ${shipmentIdx + 1}`}</option>)}{items.map((item, itemIdx) => <option key={item.id} value={item.id}>{item.description || `Product ${itemIdx + 1}`}</option>)}</select></label>
                      <button type="button" className="button secondary" aria-label={`Split payment ${idx + 1} across deliveries`} onClick={() => {
                        const updated = [...payments];
                        const first = updated[idx].allocations[0]?.obligation_id ?? shipments[0].id;
                        const second = shipments.find((shipment) => shipment.id !== first)?.id ?? first;
                        const currency = p.currency || items[0]?.currency || "";
                        updated[idx].allocations = [
                          { obligation_id: first, amount: "", currency },
                          { obligation_id: second, amount: "", currency },
                        ];
                        setPayments(updated);
                        setIsDirty(true);
                      }}>Split across deliveries</button>
                    </> : <>
                      <h5>Payment share for each delivery</h5>
                      {p.allocations.map((a, aIdx) => (
                        <div key={aIdx} className="collection-allocation-row">
                          <label>Product or delivery<select aria-label={`Payment ${idx + 1}, product or delivery share ${aIdx + 1}`} value={a.obligation_id} onChange={(e) => {
                            const updated = [...payments];
                            updated[idx].allocations[aIdx].obligation_id = e.target.value;
                            setPayments(updated);
                            setIsDirty(true);
                          }}>{shipments.map((shipment, shipmentIdx) => <option key={shipment.id} value={shipment.id}>{shipment.destination || `Delivery ${shipmentIdx + 1}`}</option>)}{items.map((item, itemIdx) => <option key={item.id} value={item.id}>{item.description || `Product ${itemIdx + 1}`}</option>)}</select></label>
                          <label>Amount<input type="text" inputMode="decimal" aria-label={`Payment ${idx + 1}, delivery amount ${aIdx + 1}`} value={a.amount} onChange={(e) => {
                            const updated = [...payments];
                            updated[idx].allocations[aIdx].amount = e.target.value;
                            setPayments(updated);
                            setIsDirty(true);
                          }} /></label>
                          <button type="button" className="button secondary" onClick={() => {
                            const updated = [...payments];
                            updated[idx].allocations = updated[idx].allocations.filter((_, i) => i !== aIdx);
                            setPayments(updated);
                            setIsDirty(true);
                          }}>Remove share</button>
                        </div>
                      ))}
                    </>}
                  </div> : <p className="proposal-editor__auto-note">Payment is linked to the delivery automatically.</p>}
                  {payments.length > 1 ? <div>
                    <button type="button" className="button secondary" aria-label={`Remove payment stage ${idx + 1}`} onClick={() => {
                      const updated = payments.filter((_, i) => i !== idx);
                      setPayments(updated);
                      setIsDirty(true);
                    }}>Remove payment stage</button>
                  </div> : null}
                </div>
              ))}
            </div>

            <details className="proposal-editor__optional">
              <summary>Optional trade terms</summary>
              <p className="hint">Only add terms both businesses have discussed and agreed on.</p>
              <label>Delivery responsibility (Incoterm) <input type="text" aria-label="Delivery responsibility Incoterm" placeholder="e.g. FOB, CIF, EXW" value={incoterm} onChange={(e) => { setIncoterm(e.target.value); setIsDirty(true); }} /></label>
              <label>Cancellation terms <input type="text" aria-label="Cancellation terms" placeholder="Optional; enter agreed terms" value={cancellationTerms} onChange={(e) => { setCancellationTerms(e.target.value); setIsDirty(true); }} /></label>
              <p className="hint">Taxes, freight, and customs fees are not captured here.</p>
            </details>

            <div className="fact-actions proposal-editor__actions">
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
          </details>
        ) : null}

        {view.proposals.length > 0 ? <>
          <h3>Proposal history</h3>
          <ol>{view.proposals.map((proposal) => <li key={proposal.id}>
            <details><summary>Round {proposal.proposal_number}: {proposalStatusLabel(proposal, organizationId)}{proposal.lifecycle_origin === "LEGACY" ? " (legacy record)" : ""}</summary>
              <code className="agreement-review__hash">{proposal.terms_hash}</code>
              {(proposal.terms.line_items ?? []).map((item, index) => <p key={index}>{item.id ? `[${item.id}] ` : ""}{item.description}: {item.quantity} {item.unit} at {item.unit_price.amount} {item.unit_price.currency}</p>)}
              {(proposal.evidence_refs ?? []).map((ref) => <p key={ref.fact_id}>Evidence {ref.fact_id}, version {ref.version}</p>)}
            </details>
          </li>)}</ol>
        </> : null}
        {view.history.length > 0 ? <>
          <h3>Proposal activity</h3>
          <ol>{view.history.map((event) => <li key={event.id}>
            <time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time>: {historyActionLabel(event.action)}
            {event.invalidated_candidate_id ? " - prior candidate invalidated" : ""}
          </li>)}</ol>
        </> : null}
      </> : null}
    </section>
  );
}
