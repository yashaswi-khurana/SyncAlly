import { useEffect, useRef, useState } from "react";

import { ApiError, getNegotiation, negotiateDeal } from "../api/client";
import type { Deal, NegotiationAction, NegotiationInput, NegotiationView } from "../api/types";

interface NegotiationReviewProps {
  deal: Deal;
  organizationId: string;
  reloadToken: number;
  onLoaded: (view: NegotiationView | null) => void;
  onChanged: () => void;
}

const ACTION_LABELS = {
  accept: "Accept as candidate", reject: "Reject proposal", supersede: "Supersede proposal", expire: "Expire proposal",
};

export default function NegotiationReview({ deal, organizationId, reloadToken, onLoaded, onChanged }: NegotiationReviewProps) {
  const [loadedView, setView] = useState<NegotiationView | null>(null);
  const view = loadedView?.deal_id === deal.id && loadedView.organization_id === organizationId ? loadedView : null;
  const [error, setError] = useState("");
  const [stale, setStale] = useState(false);
  const [pending, setPending] = useState(false);
  const [reload, setReload] = useState(0);
  const [replacementConfirmed, setReplacementConfirmed] = useState(false);
  const loadContext = JSON.stringify([deal.id, deal.version, organizationId, reloadToken, reload]);
  const [observedContext, setObservedContext] = useState(loadContext);
  if (loadContext !== observedContext) {
    setObservedContext(loadContext);
    setView(null);
    setPending(false);
    setError("");
    setStale(false);
    setReplacementConfirmed(false);
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
    }).catch((caught: unknown) => {
      if (!controller.signal.aborted) setError(caught instanceof ApiError ? caught.message : "Unable to load negotiation rounds.");
    });
    return () => { controller.abort(); request.current?.abort(); };
  }, [deal.id, deal.version, organizationId, reloadToken, reload]);

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
        <h2 id={`negotiation-heading-${deal.id}`}>Negotiation rounds</h2>
        <button type="button" className="button secondary" disabled={pending} onClick={() => setReload((value) => value + 1)}>Reload rounds</button>
      </div>
      {!view && !error ? <p role="status">Loading negotiation rounds...</p> : null}
      {error ? <p className="form-error" role="alert">{error}</p> : null}
      {view ? <>
        <p>{view.round_count} / {view.max_rounds} rounds</p>
        {view.escalated ? <p role="status">Escalation required</p> : null}
        {view.history_ambiguous ? <p role="alert">Legacy history requires review.</p> : null}
        {view.latest ? <>
          <h3>Latest proposal: round {view.latest.proposal_number}</h3>
          <p>{view.latest.status.replaceAll("_", " ")}</p>
          <code className="agreement-review__hash">{view.latest.terms_hash}</code>
          {view.latest.expires_at ? <p>Deadline: <time dateTime={view.latest.expires_at}>{new Date(view.latest.expires_at).toLocaleString()}</time></p> : null}
          <div className="agreement-terms" aria-label="Latest proposal terms">
            {view.latest.terms.line_items.map((item, index) => <dl className="agreement-terms__item" key={index}>
              <div><dt>Item</dt><dd>{item.description}</dd></div>
              <div><dt>Quantity</dt><dd>{item.quantity} {item.unit}</dd></div>
              <div><dt>Unit price</dt><dd>{item.unit_price.amount} {item.unit_price.currency}</dd></div>
            </dl>)}
            {view.latest.terms.shipments.map((item, index) => <dl className="agreement-terms__item" key={index}>
              <div><dt>Delivery</dt><dd>{item.quantity} to {item.destination}</dd></div>
              <div><dt>Date</dt><dd>{item.target_date ?? "Not specified"}</dd></div>
            </dl>)}
            {view.latest.terms.payment_terms.map((item, index) => <dl className="agreement-terms__item" key={index}>
              <div><dt>Payment</dt><dd>{item.amount.amount} {item.amount.currency}</dd></div>
              <div><dt>Due condition</dt><dd>{item.due_condition}</dd></div>
            </dl>)}
          </div>
          {view.current_candidate ? <label>
            <input type="checkbox" checked={replacementConfirmed} disabled={pending} onChange={(event) => setReplacementConfirmed(event.target.checked)} />
            Replace candidate version {view.current_candidate.version_number} and invalidate its approvals
          </label> : null}
          <div className="fact-actions">
            {(["accept", "reject", "supersede", "expire"] as const).filter((action) => view.eligible_actions.includes(action)).map((action) =>
              <button type="button" className="button secondary" key={action}
                disabled={pending || stale || deal.pending_counterparty || Boolean(view.current_candidate && !replacementConfirmed)}
                onClick={() => void act(action)}>{ACTION_LABELS[action]}</button>)}
          </div>
        </> : <p>No submitted human proposal.</p>}
        <h3>Round history</h3>
        <ol>{view.proposals.map((proposal) => <li key={proposal.id}>
          <details><summary>Round {proposal.proposal_number}: {proposal.status.replaceAll("_", " ")}{proposal.lifecycle_origin === "LEGACY" ? " (legacy)" : ""}</summary>
            <code className="agreement-review__hash">{proposal.terms_hash}</code>
            {proposal.terms.line_items.map((item, index) => <p key={index}>{item.description}: {item.quantity} {item.unit} at {item.unit_price.amount} {item.unit_price.currency}</p>)}
            {proposal.evidence_refs.map((ref) => <p key={ref.fact_id}>Evidence {ref.fact_id}, version {ref.version}</p>)}
          </details>
        </li>)}</ol>
        <h3>Actions</h3>
        <ol>{view.history.map((event) => <li key={event.id}>
          <time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time>: {event.action.replaceAll("_", " ")}
          {event.invalidated_candidate_id ? " - prior candidate invalidated" : ""}
        </li>)}</ol>
      </> : null}
    </section>
  );
}