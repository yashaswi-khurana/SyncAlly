import { useState } from "react";

import { ApiError, correctDealFact, createAgreementFromReviewedTerms, draftDealProposal, reviewDealFact, suggestDealFacts } from "../api/client";
import type { DealFact, FactReviewAction, PaymentTrigger, ReviewedProposalTerms } from "../api/types";
import { isPaymentTrigger, SUPPORTED_PAYMENT_TIMING } from "../api/types";
import {
  toFactSuggestionDraft,
  toProposalDraft,
  type FactSuggestionDraft,
  type ProposalSuggestionDraft,
} from "./suggestionPreview";

interface AISuggestionReviewProps {
  dealId: string;
  organizationId: string;
  onTraceSource: (messageId: string) => void;
  onFactAdded: (fact: DealFact) => void;
  onFactUpdated: (fact: DealFact) => void;
  onFactCorrected: (replaced: DealFact, corrected: DealFact) => void;
  onAgreementCreated?: () => void;
}

const PROPOSAL_FIELDS: Array<[keyof ProposalSuggestionDraft, string]> = [
  ["description", "Item description"],
  ["quantity", "Quantity"],
  ["unit", "Unit"],
  ["unitPrice", "Unit price"],
  ["deliveryDestination", "Delivery destination"],
  ["deliveryDate", "Delivery date"],
];

function describeError(caught: unknown): string {
  if (caught instanceof ApiError) {
    return caught.status === 401 ? "Your session has expired. Sign in again." : caught.message;
  }
  return "Something went wrong. Please try again.";
}

export default function AISuggestionReview({
  dealId,
  organizationId,
  onTraceSource,
  onFactAdded,
  onFactUpdated,
  onFactCorrected,
  onAgreementCreated = () => {},
}: AISuggestionReviewProps) {
  const [factDrafts, setFactDrafts] = useState<FactSuggestionDraft[]>([]);
  const [proposal, setProposal] = useState<ProposalSuggestionDraft | null>(null);
  // The AI draft never picks the payment timing for a human; the proposer confirms it here.
  const [paymentTrigger, setPaymentTrigger] = useState<PaymentTrigger>(
    SUPPORTED_PAYMENT_TIMING[0].trigger,
  );
  const [suggestionError, setSuggestionError] = useState("");
  const [agreementNotice, setAgreementNotice] = useState("");
  const [pendingAction, setPendingAction] = useState<"facts" | "proposal" | "agreement" | null>(null);

  const selectedPaymentTiming = SUPPORTED_PAYMENT_TIMING.find(
    (option) => option.trigger === paymentTrigger,
  ) ?? SUPPORTED_PAYMENT_TIMING[0];

  async function runFactSuggestion() {
    setSuggestionError("");
    setPendingAction("facts");
    try {
      const result = await suggestDealFacts(dealId, organizationId);
      const drafts = result.facts.map(toFactSuggestionDraft);
      setFactDrafts(drafts);
      result.facts.forEach(onFactAdded);
      if (result.status !== "VALID") {
        setSuggestionError(result.issues.map((issue) => issue.message).join("; "));
      } else if (drafts.length === 0) {
        setSuggestionError("No supported facts were found in this organization's authorized conversation.");
      }
    } catch (caught) {
      setSuggestionError(describeError(caught));
    } finally {
      setPendingAction(null);
    }
  }

  async function runProposalDraft() {
    setSuggestionError("");
    setAgreementNotice("");
    setPendingAction("proposal");
    try {
      const result = await draftDealProposal(dealId, organizationId);
      setProposal(toProposalDraft(result));
      setPaymentTrigger(SUPPORTED_PAYMENT_TIMING[0].trigger);
    } catch (caught) {
      setSuggestionError(describeError(caught));
    } finally {
      setPendingAction(null);
    }
  }

  async function createReviewedAgreement() {
    if (!proposal) return;
    setSuggestionError("");
    setAgreementNotice("");
    setPendingAction("agreement");
    try {
      const terms: ReviewedProposalTerms = {
        schema_version: proposal.schemaVersion,
        description: proposal.description,
        quantity: proposal.quantity,
        unit: proposal.unit,
        unit_price: proposal.unitPrice,
        currency: proposal.currency,
        delivery_destination: proposal.deliveryDestination,
        delivery_date: proposal.deliveryDate || null,
        payment_trigger: paymentTrigger,
      };
      const agreement = await createAgreementFromReviewedTerms(dealId, organizationId, terms);
      setProposal(null);
      setAgreementNotice(`Agreement version ${agreement.version_number} is ready for both parties to review.`);
      onAgreementCreated();
    } catch (caught) {
      setSuggestionError(describeError(caught));
    } finally {
      setPendingAction(null);
    }
  }

  function updateFact(id: string, update: Partial<Pick<FactSuggestionDraft, "field" | "value" | "currencyOrUnit">>) {
    setFactDrafts((current) => current.map((draft) => draft.fact.id === id ? { ...draft, ...update, error: "" } : draft));
  }

  async function reviewFact(draft: FactSuggestionDraft, action: FactReviewAction) {
    updateFact(draft.fact.id, {});
    setFactDrafts((current) => current.map((item) => item.fact.id === draft.fact.id ? { ...item, pending: true } : item));
    try {
      const updated = await reviewDealFact(dealId, draft.fact.id, action);
      setFactDrafts((current) => current.map((item) => item.fact.id === updated.id ? toFactSuggestionDraft(updated) : item));
      onFactUpdated(updated);
    } catch (caught) {
      const error = describeError(caught);
      setFactDrafts((current) => current.map((item) => item.fact.id === draft.fact.id ? { ...item, pending: false, error } : item));
    }
  }

  async function saveCorrection(draft: FactSuggestionDraft) {
    setFactDrafts((current) => current.map((item) => item.fact.id === draft.fact.id ? { ...item, pending: true, error: "" } : item));
    try {
      const result = await correctDealFact(dealId, draft.fact.id, {
        expected_version: draft.fact.version,
        field: draft.field,
        typed_value: draft.value,
        currency_or_unit: draft.currencyOrUnit,
      });
      setFactDrafts((current) => current.map((item) => item.fact.id === draft.fact.id
        ? toFactSuggestionDraft(result.corrected_fact)
        : item));
      onFactCorrected(result.replaced_fact, result.corrected_fact);
    } catch (caught) {
      const error = describeError(caught);
      setFactDrafts((current) => current.map((item) => item.fact.id === draft.fact.id ? { ...item, pending: false, error } : item));
    }
  }

  function isCorrectionChanged(draft: FactSuggestionDraft): boolean {
    return draft.field !== draft.fact.field
      || draft.value !== draft.fact.typed_value
      || draft.currencyOrUnit !== draft.fact.currency_or_unit;
  }

  return (
    <section className="card communication-card ai-review-card" aria-labelledby="ai-review-heading">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Human review required</span>
          <h2 id="ai-review-heading">Suggestion review</h2>
        </div>
        <span className="communication-index" aria-hidden="true">03 / REVIEW</span>
      </div>
      <p className="muted">
        Demo AI suggestions run only after you request them. Extracted facts are saved as private, unconfirmed candidates for this organization. Draft edits never approve an agreement or start a payment.
      </p>
      <div className="ai-review-actions">
        <button type="button" className="button" disabled={pendingAction !== null} onClick={() => void runFactSuggestion()}>
          {pendingAction === "facts" ? "Extracting facts..." : "Suggest facts from this side's messages"}
        </button>
        <button type="button" className="button secondary" disabled={pendingAction !== null} onClick={() => void runProposalDraft()}>
          {pendingAction === "proposal" ? "Drafting terms..." : "Draft proposed terms"}
        </button>
      </div>
      {suggestionError ? <p className="form-error" role="alert">{suggestionError}</p> : null}
      {agreementNotice ? <p className="hint" role="status">{agreementNotice}</p> : null}

      {factDrafts.length > 0 ? (
        <div className="ai-suggestion-list" aria-label="Fact suggestions for review">
          <h3>Extracted fact suggestions</h3>
          {factDrafts.map((draft) => {
            const canReview = draft.fact.status === "EXTRACTED" || draft.fact.status === "NEEDS_CLARIFICATION";
            const sourceId = draft.fact.source_message_id;
            return (
              <article className="fact-ticket ai-suggestion" key={draft.fact.id} aria-label={`Fact suggestion: ${draft.field}`}>
                <div className="communication-meta">
                  <strong>{draft.field}</strong>
                  <span className="badge badge--status-extracted">{draft.fact.status.toLowerCase().replaceAll("_", " ")}</span>
                </div>
                <div className="field">
                  <label htmlFor={`${draft.fact.id}-field`}>Fact label</label>
                  <input id={`${draft.fact.id}-field`} value={draft.field} maxLength={100} disabled={draft.pending || !canReview} onChange={(event) => updateFact(draft.fact.id, { field: event.target.value })} />
                </div>
                <div className="field">
                  <label htmlFor={`${draft.fact.id}-value`}>Suggested value</label>
                  <textarea id={`${draft.fact.id}-value`} value={draft.value} maxLength={2000} rows={2} disabled={draft.pending || !canReview} onChange={(event) => updateFact(draft.fact.id, { value: event.target.value })} />
                </div>
                <div className="field">
                  <label htmlFor={`${draft.fact.id}-unit`}>Currency or unit</label>
                  <input id={`${draft.fact.id}-unit`} value={draft.currencyOrUnit ?? ""} maxLength={32} disabled={draft.pending || !canReview} onChange={(event) => updateFact(draft.fact.id, { currencyOrUnit: event.target.value || null })} />
                </div>
                {draft.fact.source_span ? (
                  <div className="fact-source">
                    <span className="fact-source__label">SOURCE MESSAGE</span>
                    {sourceId ? <button type="button" className="fact-source__trace" onClick={() => onTraceSource(sourceId)}>Trace to message</button> : null}
                    <blockquote className="fact-source__quote">"{draft.fact.source_span}"</blockquote>
                  </div>
                ) : null}
                {canReview ? (
                  <div className="fact-actions" aria-label={`Review suggestion ${draft.field}`}>
                    <button type="button" className="button button--compact" disabled={draft.pending || !isCorrectionChanged(draft)} onClick={() => void saveCorrection(draft)}>
                      {draft.pending ? "Saving..." : "Save correction"}
                    </button>
                    <button type="button" className="button secondary button--compact" disabled={draft.pending} onClick={() => void reviewFact(draft, "confirm")}>Confirm</button>
                    <button type="button" className="button secondary button--compact" disabled={draft.pending} onClick={() => void reviewFact(draft, "reject")}>Reject</button>
                    {draft.fact.status === "EXTRACTED" ? <button type="button" className="button secondary button--compact" disabled={draft.pending} onClick={() => void reviewFact(draft, "clarify")}>Ask for clarification</button> : null}
                  </div>
                ) : (
                  <p className="hint" role="status">Reviewed and saved as {draft.fact.status.toLowerCase().replaceAll("_", " ")}.</p>
                )}
                {draft.error ? <p className="form-error" role="alert">{draft.error}</p> : null}
              </article>
            );
          })}
        </div>
      ) : null}

      {proposal ? (
        <div className="proposal-draft" aria-label="Proposed terms draft">
          <div className="communication-meta">
            <h3>Proposed terms</h3>
            <span className="badge badge--status-extracted">DRAFT - NOT AN AGREEMENT</span>
          </div>
          <p className="hint">Review and edit the AI-generated draft. It is not shared or approved from this screen.</p>
          {PROPOSAL_FIELDS.map(([field, label]) => (
            <div className="field" key={field}>
              <label htmlFor={`proposal-${dealId}-${field}`}>{label}</label>
              <input id={`proposal-${dealId}-${field}`} value={proposal[field]} onChange={(event) => setProposal((current) => current ? { ...current, [field]: event.target.value } : current)} />
            </div>
          ))}
          <p className="proposal-currency">Currency: {proposal.currency}</p>
          <div className="field">
            <label htmlFor={`proposal-${dealId}-payment-trigger`}>Payment timing</label>
            <select
              id={`proposal-${dealId}-payment-trigger`}
              value={paymentTrigger}
              onChange={(event) => {
                if (isPaymentTrigger(event.target.value)) {
                  setPaymentTrigger(event.target.value);
                }
              }}
            >
              {SUPPORTED_PAYMENT_TIMING.map((option) => (
                <option key={option.trigger} value={option.trigger}>{option.label}</option>
              ))}
            </select>
          </div>
          <p className="hint">
            Due condition: {selectedPaymentTiming.dueCondition}
          </p>
          <p className="hint">Editing this draft does not create or approve an agreement and cannot start a payment.</p>
          <button
            type="button"
            className="button"
            disabled={pendingAction !== null}
            onClick={() => void createReviewedAgreement()}
          >
            {pendingAction === "agreement" ? "Saving agreement…" : "Send reviewed terms for bilateral approval"}
          </button>
          <p className="hint">Both parties must approve and commit this saved version before payment can begin.</p>
        </div>
      ) : null}
    </section>
  );
}
