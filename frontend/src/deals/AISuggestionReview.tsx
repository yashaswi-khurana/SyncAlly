import { useEffect, useRef, useState } from "react";

import { ApiError, correctDealFact, createAgreementFromReviewedTerms, createDealFact, draftDealProposal, reviewDealFact, suggestDealFacts } from "../api/client";
import type { DealFact, FactReviewAction, PaymentTrigger, ReviewedProposalTerms, Visibility } from "../api/types";
import { isPaymentTrigger, SUPPORTED_PAYMENT_TIMING } from "../api/types";
import {
  REQUIRED_TRADE_FIELDS,
  guidanceForMissingTradeFields,
  missingRequiredTradeFields,
  requiredTradeField,
  toFactSuggestionDraft,
  toProposalDraft,
  type FactSuggestionDraft,
  type ProposalSuggestionDraft,
  type RequiredTradeField,
} from "./suggestionPreview";

interface AISuggestionReviewProps {
  dealId: string;
  organizationId: string;
  facts: DealFact[];
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
  facts,
  onTraceSource,
  onFactAdded,
  onFactUpdated,
  onFactCorrected,
  onAgreementCreated = () => {},
}: AISuggestionReviewProps) {
  const [factDrafts, setFactDrafts] = useState<FactSuggestionDraft[]>([]);
  const [factOverrides, setFactOverrides] = useState<Record<string, DealFact>>({});
  const [factSuggestionGuidance, setFactSuggestionGuidance] = useState("");
  const [serverMissingFields, setServerMissingFields] = useState<RequiredTradeField[] | null>(null);
  const [hasFactSuggestionRun, setHasFactSuggestionRun] = useState(false);
  const [manualEntryOpen, setManualEntryOpen] = useState(false);
  const [manualField, setManualField] = useState<RequiredTradeField>("item_description");
  const [manualValue, setManualValue] = useState("");
  const [manualCurrencyOrUnit, setManualCurrencyOrUnit] = useState("");
  const [manualVisibility, setManualVisibility] = useState<Visibility>("PRIVATE");
  const [manualError, setManualError] = useState("");
  const [proposalState, setProposalState] = useState<{
    draft: ProposalSuggestionDraft;
    signatures: Partial<Record<keyof ProposalSuggestionDraft, string>>;
    invalidated: boolean;
    observedSignatures: Partial<Record<keyof ProposalSuggestionDraft, string>>;
  } | null>(null);
  const proposalEditRevisionRef = useRef(0);
  const activeRef = useRef(false);
  useEffect(() => {
    activeRef.current = true;
    return () => { activeRef.current = false; };
  }, []);
  const [observedFacts, setObservedFacts] = useState({ facts, ids: new Set(facts.map((fact) => fact.id)) });
  if (observedFacts.facts !== facts) {
    setObservedFacts({ facts, ids: new Set([...observedFacts.ids, ...facts.map((fact) => fact.id)]) });
  }
  const [serverFactsSignature, setServerFactsSignature] = useState("");
  // The AI draft never picks the payment timing for a human; the proposer confirms it here.
  const [paymentTrigger, setPaymentTrigger] = useState<PaymentTrigger>(
    SUPPORTED_PAYMENT_TIMING[0].trigger,
  );
  const [suggestionError, setSuggestionError] = useState("");
  const [agreementNotice, setAgreementNotice] = useState("");
  const [pendingAction, setPendingAction] = useState<"facts" | "proposal" | "agreement" | "manual" | null>(null);
  const factStateRevisionRef = useRef(0);
  const manualTriggerRef = useRef<HTMLButtonElement>(null);
  const factSuggestionButtonRef = useRef<HTMLButtonElement>(null);
  const manualDialogRef = useRef<HTMLElement>(null);
  const manualFieldRef = useRef<HTMLSelectElement>(null);

  useEffect(() => {
    if (!manualEntryOpen) return;

    const fallbackFocus = factSuggestionButtonRef.current;
    const focusReturnTarget = manualTriggerRef.current ?? fallbackFocus;
    manualFieldRef.current?.focus();
    function keepDialogKeyboardFocus(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        setManualEntryOpen(false);
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = manualDialogRef.current?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable?.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", keepDialogKeyboardFocus);
    return () => {
      document.removeEventListener("keydown", keepDialogKeyboardFocus);
      if (focusReturnTarget?.isConnected) focusReturnTarget.focus();
      else fallbackFocus?.focus();
    };
  }, [manualEntryOpen]);

  const selectedPaymentTiming = SUPPORTED_PAYMENT_TIMING.find(
    (option) => option.trigger === paymentTrigger,
  ) ?? SUPPORTED_PAYMENT_TIMING[0];
  const authorized = (fact: DealFact) => fact.deal_id === dealId
    && (fact.visibility === "SHAREABLE" || fact.owner_organization_id === organizationId);
  const knownFactsById = new Map(facts.filter(authorized).map((fact) => [fact.id, fact]));
  for (const fact of [...factDrafts.map((draft) => draft.fact), ...Object.values(factOverrides)]) {
    const current = knownFactsById.get(fact.id);
    // Local saves bridge callback batching. A missing, previously observed ID was revoked.
    if (authorized(fact) && ((!current && !observedFacts.ids.has(fact.id))
      || (current && fact.version > current.version))) knownFactsById.set(fact.id, fact);
  }
  const synchronizedDrafts = factDrafts.flatMap((draft) => {
    const fact = knownFactsById.get(draft.fact.id);
    if (!fact) return [];
    const editable = fact.status === "EXTRACTED" || fact.status === "NEEDS_CLARIFICATION";
    return [{ ...draft, fact,
      field: editable && draft.field !== draft.fact.field ? draft.field : fact.field,
      value: editable && draft.value !== draft.fact.typed_value ? draft.value : fact.typed_value,
      currencyOrUnit: editable && draft.currencyOrUnit !== draft.fact.currency_or_unit
        ? draft.currencyOrUnit : fact.currency_or_unit,
    }];
  });
  const factsSignature = JSON.stringify([...knownFactsById.values()]);
  const missingFields = missingRequiredTradeFields([...knownFactsById.values()],
    serverFactsSignature === factsSignature ? serverMissingFields : null);
  const confirmedValues: Partial<Record<keyof ProposalSuggestionDraft, string>> = {};
  const confirmedSignatures: Partial<Record<keyof ProposalSuggestionDraft, string>> = {};
  const conflictingFields = new Set<keyof ProposalSuggestionDraft>();
  const fieldNames: Record<RequiredTradeField, keyof ProposalSuggestionDraft> = {
    item_description: "description", quantity: "quantity", unit: "unit", unit_price: "unitPrice",
    delivery_destination: "deliveryDestination", delivery_date: "deliveryDate",
  };
  const confirmed = [...knownFactsById.values()].filter((fact) => fact.status === "CONFIRMED");
  for (const { key } of REQUIRED_TRADE_FIELDS) {
    const matching = confirmed.filter((fact) => requiredTradeField(fact.field) === key);
    const field = fieldNames[key];
    if (!matching.length) continue;
    confirmedSignatures[field] = JSON.stringify(matching.map((fact) => [fact.id, fact.version, fact.typed_value, fact.currency_or_unit]).sort());
    if (new Set(matching.map((fact) => fact.typed_value)).size > 1) conflictingFields.add(field);
    else confirmedValues[field] = matching[0].typed_value;
  }
  if (!confirmedSignatures.unit && confirmedSignatures.quantity) {
    const quantities = confirmed.filter((fact) => requiredTradeField(fact.field) === "quantity");
    const units = new Set(quantities.map((fact) => fact.currency_or_unit).filter(Boolean));
    if (units.size > 1) conflictingFields.add("unit");
    else if (units.size === 1) {
      confirmedValues.unit = [...units][0]!;
      confirmedSignatures.unit = confirmedSignatures.quantity;
    }
  }
  let proposal = proposalState?.draft ?? null;
  let proposalInvalidated = proposalState?.invalidated ?? false;
  if (proposal && proposalState) {
    proposal = { ...proposal };
    for (const [field] of PROPOSAL_FIELDS) {
      const previous = proposalState.signatures[field];
      const previouslyDerived = proposalState.observedSignatures[field];
      const signature = confirmedSignatures[field];
      if (conflictingFields.has(field) || ((previous || previouslyDerived) && !signature)) {
        proposal = { ...proposal, [field]: "" };
        proposalInvalidated = true;
      } else if (signature && previous !== signature) {
        proposal = { ...proposal, [field]: confirmedValues[field] ?? "" };
      }
    }
    const observedSignatures = { ...proposalState.observedSignatures, ...confirmedSignatures };
    if (JSON.stringify(observedSignatures) !== JSON.stringify(proposalState.observedSignatures)
      || proposalInvalidated !== proposalState.invalidated) {
      setProposalState({ ...proposalState, observedSignatures, invalidated: proposalInvalidated });
    }
  }

  const currentFactGuidance = hasFactSuggestionRun
    ? guidanceForMissingTradeFields(missingFields)
    : factSuggestionGuidance;

  async function runFactSuggestion() {
    const revisionAtStart = factStateRevisionRef.current;
    setSuggestionError("");
    setFactSuggestionGuidance("");
    setPendingAction("facts");
    try {
      const result = await suggestDealFacts(dealId, organizationId);
      if (!activeRef.current) return;
      if (revisionAtStart !== factStateRevisionRef.current) return;
      const drafts = result.facts.filter(authorized).map(toFactSuggestionDraft);
      setServerFactsSignature(JSON.stringify([...new Map([...facts, ...result.facts].filter(authorized).map((fact) => [fact.id, fact])).values()]));
      setFactDrafts(drafts);
      setFactSuggestionGuidance(result.guidance_message);
      setHasFactSuggestionRun(true);
      const serverMissing = new Set(result.missing_fields.map(requiredTradeField).filter(
        (field): field is RequiredTradeField => field !== null,
      ));
      setServerMissingFields(REQUIRED_TRADE_FIELDS
        .filter(({ key }) => serverMissing.has(key))
        .map(({ key }) => key));
      result.facts.filter(authorized).forEach(onFactAdded);
      if (result.status !== "VALID") {
        setSuggestionError(result.issues.map((issue) => issue.message).join("; "));
      } else if (drafts.length === 0) {
        setSuggestionError("No supported facts were found in this organization's authorized conversation.");
      }
    } catch (caught) {
      if (!activeRef.current) return;
      setSuggestionError(describeError(caught));
    } finally {
      if (activeRef.current) setPendingAction(null);
    }
  }

  async function runProposalDraft() {
    const editRevision = proposalEditRevisionRef.current;
    // Preserve the authorization/status context even before the first draft is visible.
    const requestFactSignatures = { ...confirmedSignatures };
    setSuggestionError("");
    setAgreementNotice("");
    setPendingAction("proposal");
    try {
      const result = await draftDealProposal(dealId, organizationId);
      if (!activeRef.current) return;
      if (editRevision !== proposalEditRevisionRef.current) return;
      setProposalState({ draft: toProposalDraft(result), signatures: {}, invalidated: false, observedSignatures: requestFactSignatures });
      setPaymentTrigger(SUPPORTED_PAYMENT_TIMING[0].trigger);
    } catch (caught) {
      if (!activeRef.current) return;
      setSuggestionError(describeError(caught));
    } finally {
      if (activeRef.current) setPendingAction(null);
    }
  }

  async function createReviewedAgreement() {
    if (!proposal || proposalInvalidated || conflictingFields.size > 0) return;
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
      if (!activeRef.current) return;
      setProposalState(null);
      setAgreementNotice(`Agreement version ${agreement.version_number} is ready for both parties to review.`);
      onAgreementCreated();
    } catch (caught) {
      if (!activeRef.current) return;
      setSuggestionError(describeError(caught));
    } finally {
      if (activeRef.current) setPendingAction(null);
    }
  }

  function updateFact(id: string, update: Partial<Pick<FactSuggestionDraft, "field" | "value" | "currencyOrUnit">>) {
    const displayed = synchronizedDrafts.find((draft) => draft.fact.id === id);
    setFactDrafts((current) => current.map((draft) => draft.fact.id === id
      ? { ...(displayed ?? draft), ...update, error: "" } : draft));
  }

  async function reviewFact(draft: FactSuggestionDraft, action: FactReviewAction) {
    factStateRevisionRef.current += 1;
    updateFact(draft.fact.id, {});
    setFactDrafts((current) => current.map((item) => item.fact.id === draft.fact.id ? { ...item, pending: true } : item));
    try {
      const updated = await reviewDealFact(dealId, draft.fact.id, action);
      if (!activeRef.current) return;
      setServerMissingFields(null);
      setFactDrafts((current) => current.map((item) => item.fact.id === updated.id ? toFactSuggestionDraft(updated) : item));
      setFactOverrides((current) => ({ ...current, [updated.id]: updated }));
      onFactUpdated(updated);
    } catch (caught) {
      if (!activeRef.current) return;
      const error = describeError(caught);
      setFactDrafts((current) => current.map((item) => item.fact.id === draft.fact.id ? { ...item, pending: false, error } : item));
    } finally {
      if (activeRef.current) factStateRevisionRef.current += 1;
    }
  }

  async function saveCorrection(draft: FactSuggestionDraft) {
    factStateRevisionRef.current += 1;
    setFactDrafts((current) => current.map((item) => item.fact.id === draft.fact.id ? { ...item, pending: true, error: "" } : item));
    try {
      const result = await correctDealFact(dealId, draft.fact.id, {
        expected_version: draft.fact.version,
        field: draft.field,
        typed_value: draft.value,
        currency_or_unit: draft.currencyOrUnit,
      });
      if (!activeRef.current) return;
      setServerMissingFields(null);
      setFactDrafts((current) => current.map((item) => item.fact.id === draft.fact.id
        ? toFactSuggestionDraft(result.corrected_fact)
        : item));
      setFactOverrides((current) => ({
        ...current,
        [result.replaced_fact.id]: result.replaced_fact,
        [result.corrected_fact.id]: result.corrected_fact,
      }));
      onFactCorrected(result.replaced_fact, result.corrected_fact);
    } catch (caught) {
      if (!activeRef.current) return;
      const error = describeError(caught);
      setFactDrafts((current) => current.map((item) => item.fact.id === draft.fact.id ? { ...item, pending: false, error } : item));
    } finally {
      if (activeRef.current) factStateRevisionRef.current += 1;
    }
  }

  function isCorrectionChanged(draft: FactSuggestionDraft): boolean {
    return draft.field !== draft.fact.field
      || draft.value !== draft.fact.typed_value
      || draft.currencyOrUnit !== draft.fact.currency_or_unit;
  }

  async function addManualFact(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = manualValue.trim();
    if (!value) {
      setManualError("Enter a value for this term.");
      return;
    }

    setManualError("");
    factStateRevisionRef.current += 1;
    setPendingAction("manual");
    try {
      const fact = await createDealFact(dealId, {
        organization_id: organizationId,
        field: manualField,
        typed_value: value,
        currency_or_unit: manualCurrencyOrUnit.trim() || null,
        kind: "INFORMATIONAL",
        visibility: manualVisibility,
      });
      if (!activeRef.current) return;
      setServerMissingFields(null);
      setFactDrafts((current) => [...current.filter((item) => item.fact.id !== fact.id), toFactSuggestionDraft(fact)]);
      setFactOverrides((current) => ({ ...current, [fact.id]: fact }));
      setHasFactSuggestionRun(true);
      onFactAdded(fact);
      setManualEntryOpen(false);
      setManualValue("");
      setManualCurrencyOrUnit("");
      setManualVisibility("PRIVATE");
    } catch (caught) {
      if (!activeRef.current) return;
      setManualError(describeError(caught));
    } finally {
      if (activeRef.current) {
        factStateRevisionRef.current += 1;
        setPendingAction(null);
      }
    }
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
      <section className="terms-readiness" aria-labelledby={`terms-readiness-heading-${dealId}`}>
        <h3 id={`terms-readiness-heading-${dealId}`}>Terms Readiness Checklist</h3>
        <ul className="terms-readiness__list">
          {REQUIRED_TRADE_FIELDS.map(({ key, label }) => {
            const missing = missingFields.includes(key);
            return (
              <li className={missing ? "terms-readiness__item terms-readiness__item--missing" : "terms-readiness__item terms-readiness__item--ready"} key={key}>
                <span className="terms-readiness__icon" aria-hidden="true">{missing ? "●" : "✓"}</span>
                <span>{label}</span>
                <span className="visually-hidden">{missing ? "Missing" : "Detected"}</span>
              </li>
            );
          })}
        </ul>
        {synchronizedDrafts.length === 0 || missingFields.length > 0 ? (
          <div className="terms-readiness__manual">
            <p>Don't see your terms? Add them manually.</p>
            <button
              ref={manualTriggerRef}
              type="button"
              className="button secondary button--compact"
              disabled={pendingAction !== null}
              onClick={() => {
                setManualError("");
                setManualEntryOpen(true);
              }}
            >
              + Add Term Manually
            </button>
          </div>
        ) : null}
      </section>
      <div className="ai-review-actions">
        <button ref={factSuggestionButtonRef} type="button" className="button" disabled={pendingAction !== null} onClick={() => void runFactSuggestion()}>
          {pendingAction === "facts" ? "Extracting facts..." : "Suggest facts from this side's messages"}
        </button>
        <button type="button" className="button secondary" disabled={pendingAction !== null} onClick={() => void runProposalDraft()}>
          {pendingAction === "proposal" ? "Drafting terms..." : "Draft proposed terms"}
        </button>
      </div>
      {suggestionError ? <p className="form-error" role="alert">{suggestionError}</p> : null}
      {currentFactGuidance ? <p className="hint" role="status">{currentFactGuidance}</p> : null}
      {agreementNotice ? <p className="hint" role="status">{agreementNotice}</p> : null}
      {manualEntryOpen ? (
        <div className="manual-fact-modal-backdrop">
          <section
            className="manual-fact-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby={`manual-fact-heading-${dealId}`}
            aria-describedby={`manual-fact-description-${dealId}`}
            ref={manualDialogRef}
            tabIndex={-1}
          >
            <div className="panel-head">
              <h3 id={`manual-fact-heading-${dealId}`}>Add a term manually</h3>
              <button type="button" className="button secondary button--compact" onClick={() => setManualEntryOpen(false)}>Close</button>
            </div>
            <p id={`manual-fact-description-${dealId}`} className="muted">Add one trade detail for this organization. You can review it with the other fact suggestions.</p>
            <form className="manual-fact-form" onSubmit={(event) => void addManualFact(event)}>
              <div className="field">
                <label htmlFor={`manual-fact-field-${dealId}`}>Term type</label>
                <select id={`manual-fact-field-${dealId}`} ref={manualFieldRef} value={manualField} onChange={(event) => setManualField(event.target.value as RequiredTradeField)}>
                  {REQUIRED_TRADE_FIELDS.map(({ key, label }) => <option key={key} value={key}>{label}</option>)}
                </select>
              </div>
              <div className="field">
                <label htmlFor={`manual-fact-value-${dealId}`}>Value</label>
                <textarea id={`manual-fact-value-${dealId}`} value={manualValue} maxLength={2000} rows={3} required onChange={(event) => setManualValue(event.target.value)} />
              </div>
              <div className="field">
                <label htmlFor={`manual-fact-unit-${dealId}`}>Currency or unit (optional)</label>
                <input id={`manual-fact-unit-${dealId}`} value={manualCurrencyOrUnit} maxLength={32} onChange={(event) => setManualCurrencyOrUnit(event.target.value)} placeholder="For example, USD or bags" />
              </div>
              <div className="field">
                <label htmlFor={`manual-fact-visibility-${dealId}`}>Visibility</label>
                <select id={`manual-fact-visibility-${dealId}`} value={manualVisibility} onChange={(event) => setManualVisibility(event.target.value as Visibility)}>
                  <option value="PRIVATE">Private to this organization</option>
                  <option value="SHAREABLE">Share with both parties</option>
                </select>
              </div>
              {manualError ? <p className="form-error" role="alert">{manualError}</p> : null}
              <div className="fact-actions">
                <button type="button" className="button secondary button--compact" disabled={pendingAction === "manual"} onClick={() => setManualEntryOpen(false)}>Cancel</button>
                <button type="submit" className="button button--compact" disabled={pendingAction !== null}>
                  {pendingAction === "manual" ? "Adding term..." : "Add term"}
                </button>
              </div>
            </form>
          </section>
        </div>
      ) : null}

      {synchronizedDrafts.length > 0 ? (
        <div className="ai-suggestion-list" aria-label="Fact suggestions for review">
          <h3>Extracted fact suggestions</h3>
          {synchronizedDrafts.map((draft) => {
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
          {proposalInvalidated || conflictingFields.size > 0 ? <p role="alert" className="form-error">Confirmed terms changed or conflict. Review the facts and request a fresh draft before sending.</p> : null}
          {PROPOSAL_FIELDS.map(([field, label]) => (
            <div className="field" key={field}>
              <label htmlFor={`proposal-${dealId}-${field}`}>{label}</label>
              <input id={`proposal-${dealId}-${field}`} value={proposal[field]} onChange={(event) => {
                proposalEditRevisionRef.current += 1;
                setProposalState({
                  draft: { ...proposal, [field]: event.target.value },
                  signatures: confirmedSignatures,
                  invalidated: proposalInvalidated,
                  observedSignatures: proposalState?.observedSignatures ?? {},
                });
              }} />
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
                  proposalEditRevisionRef.current += 1;
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
            disabled={pendingAction !== null || proposalInvalidated || conflictingFields.size > 0}
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
