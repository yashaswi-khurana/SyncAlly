import { useEffect, useRef, useState } from "react";

import { ApiError, getNegotiation, negotiateDeal } from "../api/client";
import type { Deal, NegotiationAction, NegotiationInput, NegotiationProposal, NegotiationView } from "../api/types";

interface NegotiationReviewProps {
  deal: Deal;
  organizationId: string;
  reloadToken: number;
  onLoaded: (view: NegotiationView | null) => void;
  onChanged: () => void;
}

const ACTION_LABELS = {
  accept: "Accept proposal for agreement review", reject: "Reject proposal", supersede: "Withdraw proposal", expire: "Expire proposal",
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
        <div>
          <span className="eyebrow">Human proposals</span>
          <h2 id={`negotiation-heading-${deal.id}`}>Negotiation rounds</h2>
        </div>
        <button type="button" className="button secondary" disabled={pending} onClick={() => setReload((value) => value + 1)}>Reload rounds</button>
      </div>
      <p className="muted">
        A person submits each proposal. Accepting one moves its terms to Agreement review as a candidate;
        it does not approve or finalize the agreement.
      </p>
      {!view && !error ? <p role="status">Loading negotiation rounds...</p> : null}
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
        <h3>Round history</h3>
        <ol>{view.proposals.map((proposal) => <li key={proposal.id}>
          <details><summary>Round {proposal.proposal_number}: {proposalStatusLabel(proposal, organizationId)}{proposal.lifecycle_origin === "LEGACY" ? " (legacy record)" : ""}</summary>
            <code className="agreement-review__hash">{proposal.terms_hash}</code>
            {proposal.terms.line_items.map((item, index) => <p key={index}>{item.description}: {item.quantity} {item.unit} at {item.unit_price.amount} {item.unit_price.currency}</p>)}
            {proposal.evidence_refs.map((ref) => <p key={ref.fact_id}>Evidence {ref.fact_id}, version {ref.version}</p>)}
          </details>
        </li>)}</ol>
        <h3>Negotiation activity</h3>
        <ol>{view.history.map((event) => <li key={event.id}>
          <time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time>: {historyActionLabel(event.action)}
          {event.invalidated_candidate_id ? " - prior candidate invalidated" : ""}
        </li>)}</ol>
      </> : null}
    </section>
  );
}
