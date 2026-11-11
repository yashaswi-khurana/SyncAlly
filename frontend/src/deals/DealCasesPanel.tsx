import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import {
  ApiError,
  addCaseEvidence,
  getCurrentAgreement,
  listDealCases,
  raiseDealCase,
  respondToDealCase,
} from "../api/client";
import type {
  BilateralDecision,
  CaseStatus,
  CaseType,
  Deal,
  DealCase,
  EvidenceVisibility,
} from "../api/types";

interface DealCasesPanelProps {
  deal: Deal;
  selectedOrganizationId?: string;
  reloadToken?: number;
  onCaseChanged?: () => void;
}

function statusBadgeClass(status: CaseStatus): string {
  switch (status) {
    case "OPEN":
      return "badge badge--warning";
    case "UNDER_REVIEW":
      return "badge badge--info";
    case "RESOLVED":
      return "badge badge--success";
    case "REJECTED":
      return "badge badge--danger";
    case "WITHDRAWN":
      return "badge badge--neutral";
    default:
      return "badge";
  }
}

function typeBadgeClass(type: CaseType): string {
  return type === "DISPUTE" ? "badge badge--dispute" : "badge badge--cancellation";
}

export default function DealCasesPanel({
  deal,
  selectedOrganizationId,
  reloadToken = 0,
  onCaseChanged,
}: DealCasesPanelProps) {
  const [cases, setCases] = useState<DealCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state for raising a case
  const [showRaiseModal, setShowRaiseModal] = useState(false);
  const [caseType, setCaseType] = useState<CaseType>("DISPUTE");
  const [reason, setReason] = useState("");
  const [evidenceVisibility, setEvidenceVisibility] = useState<EvidenceVisibility>("MUTUAL_VISIBLE");
  const [evidenceNotes, setEvidenceNotes] = useState("");
  const [agreementVersionId, setAgreementVersionId] = useState("");
  const [agreementTermsHash, setAgreementTermsHash] = useState("");
  const [submittingCase, setSubmittingCase] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Action state for responding to a case
  const [activeRespondCase, setActiveRespondCase] = useState<{
    caseId: string;
    decision: BilateralDecision;
  } | null>(null);
  const [respondRationale, setRespondRationale] = useState("");
  const [submittingResponse, setSubmittingResponse] = useState(false);
  const [responseError, setResponseError] = useState<string | null>(null);

  // State for adding evidence
  const [activeEvidenceCaseId, setActiveEvidenceCaseId] = useState<string | null>(null);
  const [newEvidenceNotes, setNewEvidenceNotes] = useState("");
  const [newEvidenceVisibility, setNewEvidenceVisibility] = useState<EvidenceVisibility>("MUTUAL_VISIBLE");
  const [submittingEvidence, setSubmittingEvidence] = useState(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    void listDealCases(deal.id, selectedOrganizationId, { signal: controller.signal })
      .then((data) => {
        if (!cancelled) {
          setCases(data);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (cancelled || (err instanceof DOMException && err.name === "AbortError")) return;
        setError(err instanceof ApiError ? err.message : "Failed to load cases");
        setLoading(false);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [deal.id, selectedOrganizationId, reloadToken]);

  const refreshCases = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listDealCases(deal.id, selectedOrganizationId);
      setCases(data);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err instanceof ApiError ? err.message : "Failed to load cases");
    } finally {
      setLoading(false);
    }
  };

  // Load current agreement details when opening raise modal
  const handleOpenRaiseModal = async () => {
    setFormError(null);
    setReason("");
    setEvidenceNotes("");
    setShowRaiseModal(true);
    try {
      const agreement = await getCurrentAgreement(deal.id, {
        organizationId: selectedOrganizationId || undefined,
      });
      if (agreement && agreement.id) {
        setAgreementVersionId(agreement.id);
        setAgreementTermsHash(agreement.terms_hash);
      }
    } catch {
      setFormError("Could not load current agreement version. Please try again.");
    }
  };

  const handleRaiseCaseSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setFormError("Reason is required.");
      return;
    }
    if (!agreementVersionId || !agreementTermsHash) {
      setFormError("Agreement version and terms hash are required.");
      return;
    }

    try {
      setSubmittingCase(true);
      setFormError(null);
      await raiseDealCase(deal.id, {
        case_type: caseType,
        reason: reason.trim(),
        agreement_version_id: agreementVersionId,
        agreement_terms_hash: agreementTermsHash,
        evidence_visibility: evidenceVisibility,
        evidence_notes: evidenceNotes.trim() || null,
        acting_organization_id: selectedOrganizationId || null,
      });
      setShowRaiseModal(false);
      await refreshCases();
      onCaseChanged?.();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Failed to raise case");
    } finally {
      setSubmittingCase(false);
    }
  };

  const handleRespondSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!activeRespondCase) return;
    if (!respondRationale.trim()) {
      setResponseError("Rationale is required.");
      return;
    }

    try {
      setSubmittingResponse(true);
      setResponseError(null);
      await respondToDealCase(deal.id, activeRespondCase.caseId, {
        decision: activeRespondCase.decision,
        rationale: respondRationale.trim(),
        acting_organization_id: selectedOrganizationId || null,
      });
      setActiveRespondCase(null);
      setRespondRationale("");
      await refreshCases();
      onCaseChanged?.();
    } catch (err) {
      setResponseError(err instanceof ApiError ? err.message : "Failed to respond to case");
    } finally {
      setSubmittingResponse(false);
    }
  };

  const handleAddEvidenceSubmit = async (caseId: string, e: FormEvent) => {
    e.preventDefault();
    if (!newEvidenceNotes.trim()) {
      setEvidenceError("Evidence notes are required.");
      return;
    }

    try {
      setSubmittingEvidence(true);
      setEvidenceError(null);
      await addCaseEvidence(deal.id, caseId, {
        notes: newEvidenceNotes.trim(),
        visibility: newEvidenceVisibility,
        acting_organization_id: selectedOrganizationId || null,
      });
      setActiveEvidenceCaseId(null);
      setNewEvidenceNotes("");
      await refreshCases();
      onCaseChanged?.();
    } catch (err) {
      setEvidenceError(err instanceof ApiError ? err.message : "Failed to add evidence");
    } finally {
      setSubmittingEvidence(false);
    }
  };

  return (
    <section className="card deal-cases-panel" aria-labelledby="deal-cases-heading">
      <div className="panel-head panel-head--row">
        <div>
          <span className="eyebrow">Disputes & Cancellations</span>
          <h2 id="deal-cases-heading" className="display">
            Deal cases ({cases.length})
          </h2>
        </div>
        {deal.status !== "CANCELLED" && deal.status !== "COMPLETED" ? (
          <button
            type="button"
            className="button button--secondary"
            onClick={handleOpenRaiseModal}
          >
            Raise Case
          </button>
        ) : null}
      </div>

      {loading ? (
        <p className="muted">Loading cases...</p>
      ) : error ? (
        <div className="banner banner--error" role="alert">
          {error}
        </div>
      ) : cases.length === 0 ? (
        <p className="muted">
          No cancellation or dispute cases recorded for this deal.
        </p>
      ) : (
        <div className="deal-cases-list" style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
          {cases.map((c) => {
            const isInitiator = selectedOrganizationId === c.requested_by_organization_id;
            const canRespond = c.status === "OPEN" || c.status === "UNDER_REVIEW";

            return (
              <div
                key={c.id}
                className="deal-case-item card"
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                    <span className={typeBadgeClass(c.case_type)}>{c.case_type}</span>
                    <span className={statusBadgeClass(c.status)}>{c.status}</span>
                    <span className="badge badge--neutral">{c.evidence_visibility}</span>
                  </div>
                  <span className="mono muted deal-case-item__timestamp">
                    {new Date(c.created_at).toLocaleString()}
                  </span>
                </div>

                <p className="deal-case-item__reason">{c.reason}</p>

                {/* Blocker alert banner */}
                {c.operational_impact_blockers && c.operational_impact_blockers.length > 0 ? (
                  <div className="deal-cases-blocker-banner banner banner--warning" role="alert">
                    <strong>Operational Impact Blockers:</strong>
                    <ul>
                      {c.operational_impact_blockers.map((blocker, idx) => (
                        <li key={idx}>{blocker}</li>
                      ))}
                    </ul>
                    <small className="muted">
                      Automated closure is blocked until financial and delivery obligations are settled.
                    </small>
                  </div>
                ) : null}

                {c.resolution ? (
                  <p className="deal-case-item__resolution">
                    <strong>Resolution:</strong> {c.resolution}
                  </p>
                ) : null}

                {/* Evidence items */}
                <div className="deal-case-item__evidence">
                  <h4>Evidence items ({c.evidence_items.length})</h4>
                  {c.evidence_items.length === 0 ? (
                    <span className="muted" style={{ fontSize: "0.85rem" }}>No evidence submitted.</span>
                  ) : (
                    <ul className="deal-case-evidence">
                      {c.evidence_items.map((e) => (
                        <li key={e.evidence_id} className="deal-case-evidence__item">
                          <p>{e.notes}</p>
                          <span className="mono">{new Date(e.submitted_at).toLocaleString()}</span>
                          <span className="badge badge--neutral">{e.visibility}</span>
                        </li>
                      ))}
                    </ul>
                  )}

                  {canRespond ? (
                    <div style={{ marginTop: "0.5rem" }}>
                      {activeEvidenceCaseId === c.id ? (
                        <form onSubmit={(e) => handleAddEvidenceSubmit(c.id, e)} className="deal-case-form">
                          <div className="field">
                            <label htmlFor={`case-evidence-notes-${c.id}`}>Evidence notes</label>
                            <textarea
                              className="input input--textarea"
                              id={`case-evidence-notes-${c.id}`}
                              placeholder="Add evidence notes..."
                              value={newEvidenceNotes}
                              onChange={(e) => setNewEvidenceNotes(e.target.value)}
                              rows={2}
                              required
                            />
                          </div>
                          <div className="deal-case-form__row">
                            <select
                              className="input"
                              aria-label="Evidence visibility"
                              value={newEvidenceVisibility}
                              onChange={(e) => setNewEvidenceVisibility(e.target.value as EvidenceVisibility)}
                            >
                              <option value="MUTUAL_VISIBLE">Mutual Visible</option>
                              <option value="COUNTERPARTY_RESTRICTED">Counterparty Restricted</option>
                              <option value="PRIVATE_OPERATOR">Private Operator</option>
                            </select>
                            <button
                              type="submit"
                              className="button button--compact"
                              disabled={submittingEvidence}
                            >
                              {submittingEvidence ? "Saving..." : "Save Evidence"}
                            </button>
                            <button
                              type="button"
                              className="button button--secondary button--compact"
                              onClick={() => setActiveEvidenceCaseId(null)}
                            >
                              Cancel
                            </button>
                          </div>
                          {evidenceError ? <p className="banner banner--error">{evidenceError}</p> : null}
                        </form>
                      ) : (
                        <button
                          type="button"
                          className="button button--secondary button--compact"
                          onClick={() => {
                            setActiveEvidenceCaseId(c.id);
                            setNewEvidenceNotes("");
                            setEvidenceError(null);
                          }}
                        >
                          + Add Evidence
                        </button>
                      )}
                    </div>
                  ) : null}
                </div>

                {/* Bilateral decision controls */}
                {canRespond ? (
                  <div className="deal-case-item__actions">
                    <div style={{ display: "flex", gap: "0.5rem" }}>
                      {isInitiator ? (
                        <button
                          type="button"
                          className="button button--secondary button--compact"
                          onClick={() => {
                            setActiveRespondCase({ caseId: c.id, decision: "WITHDRAW" });
                            setRespondRationale("");
                            setResponseError(null);
                          }}
                        >
                          Withdraw Case
                        </button>
                      ) : (
                        <>
                          <button
                            type="button"
                            className="button button--compact"
                            onClick={() => {
                              setActiveRespondCase({ caseId: c.id, decision: "CONSENT" });
                              setRespondRationale("");
                              setResponseError(null);
                            }}
                          >
                            Consent
                          </button>
                          <button
                            type="button"
                            className="button button--danger button--compact"
                            onClick={() => {
                              setActiveRespondCase({ caseId: c.id, decision: "REJECT" });
                              setRespondRationale("");
                              setResponseError(null);
                            }}
                          >
                            Reject
                          </button>
                        </>
                      )}
                    </div>

                    {activeRespondCase && activeRespondCase.caseId === c.id ? (
                      <form onSubmit={handleRespondSubmit} className="deal-case-form">
                        <div className="field">
                          <label htmlFor={`case-rationale-${c.id}`}>
                            Rationale for {activeRespondCase.decision}
                          </label>
                          <textarea
                            className="input input--textarea"
                            id={`case-rationale-${c.id}`}
                            value={respondRationale}
                            onChange={(e) => setRespondRationale(e.target.value)}
                            placeholder="State rationale for your decision..."
                            rows={2}
                            required
                          />
                        </div>
                        <div style={{ display: "flex", gap: "0.5rem" }}>
                          <button
                            type="submit"
                            className="button button--compact"
                            disabled={submittingResponse}
                          >
                            {submittingResponse ? "Submitting..." : `Confirm ${activeRespondCase.decision}`}
                          </button>
                          <button
                            type="button"
                            className="button button--secondary button--compact"
                            onClick={() => setActiveRespondCase(null)}
                          >
                            Cancel
                          </button>
                        </div>
                        {responseError ? (
                          <p className="banner banner--error" style={{ marginTop: "0.5rem" }}>
                            {responseError}
                          </p>
                        ) : null}
                      </form>
                    ) : null}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      )}

      {/* Raise Case Modal */}
      {showRaiseModal ? (
        <div
          className="manual-fact-modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="raise-case-modal-title"
        >
          <div className="manual-fact-modal">
            <div className="panel-head">
              <div>
                <span className="eyebrow">Formal Commercial Action</span>
                <h3 id="raise-case-modal-title" className="display" style={{ fontSize: "1.25rem" }}>
                  Raise Dispute or Cancellation
                </h3>
              </div>
              <button
                type="button"
                className="deal-modal-close"
                onClick={() => setShowRaiseModal(false)}
                aria-label="Close modal"
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden="true">
                  <path d="M3 3 9 9 M9 3 3 9" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleRaiseCaseSubmit} className="form deal-case-form">
              <fieldset>
                <legend>Case type</legend>
                <label>
                  <input
                    type="radio"
                    name="caseType"
                    value="DISPUTE"
                    checked={caseType === "DISPUTE"}
                    onChange={() => setCaseType("DISPUTE")}
                  />
                  Dispute
                </label>
                <label>
                  <input
                    type="radio"
                    name="caseType"
                    value="CANCELLATION"
                    checked={caseType === "CANCELLATION"}
                    onChange={() => setCaseType("CANCELLATION")}
                  />
                  Mutual cancellation
                </label>
              </fieldset>

              <div className="field">
                <label htmlFor="case-reason">Reason</label>
                <textarea
                  className="input input--textarea"
                  id="case-reason"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Explain why this case is being raised..."
                  rows={3}
                  required
                />
              </div>

              <div className="field">
                <label htmlFor="case-evidence-visibility">Evidence visibility</label>
                <select
                  className="input"
                  id="case-evidence-visibility"
                  value={evidenceVisibility}
                  onChange={(e) => setEvidenceVisibility(e.target.value as EvidenceVisibility)}
                >
                  <option value="MUTUAL_VISIBLE">Mutual visible (both parties)</option>
                  <option value="COUNTERPARTY_RESTRICTED">Counterparty restricted (submitting organization only)</option>
                  <option value="PRIVATE_OPERATOR">Private operator (internal only)</option>
                </select>
              </div>

              <div className="field">
                <label htmlFor="case-evidence-notes">Initial evidence notes (optional)</label>
                <textarea
                  className="input input--textarea"
                  id="case-evidence-notes"
                  value={evidenceNotes}
                  onChange={(e) => setEvidenceNotes(e.target.value)}
                  placeholder="Add initial evidence, document references, or notes…"
                  rows={2}
                />
              </div>

              {formError ? (
                <div className="banner banner--error" role="alert">
                  {formError}
                </div>
              ) : null}

              <div className="deal-case-form__actions">
                <button
                  type="button"
                  className="button button--secondary"
                  onClick={() => setShowRaiseModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="button"
                  disabled={submittingCase}
                >
                  {submittingCase ? "Submitting..." : "Submit Case"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </section>
  );
}
