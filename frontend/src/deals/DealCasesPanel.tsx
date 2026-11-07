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
      <div className="panel-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <span className="eyebrow">Disputes & Cancellations</span>
          <h2 id="deal-cases-heading" className="display" style={{ margin: 0, fontSize: "1.25rem" }}>
            Deal Cases ({cases.length})
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
        <p className="muted" style={{ padding: "1rem" }}>Loading cases...</p>
      ) : error ? (
        <div className="banner banner--error" role="alert" style={{ margin: "1rem 0" }}>
          {error}
        </div>
      ) : cases.length === 0 ? (
        <p className="muted" style={{ padding: "1rem 0" }}>
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
                style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.1)", padding: "1rem" }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                  <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                    <span className={typeBadgeClass(c.case_type)}>{c.case_type}</span>
                    <span className={statusBadgeClass(c.status)}>{c.status}</span>
                    <span className="badge badge--neutral">{c.evidence_visibility}</span>
                  </div>
                  <span className="muted mono" style={{ fontSize: "0.8rem" }}>
                    {new Date(c.created_at).toLocaleString()}
                  </span>
                </div>

                <p style={{ margin: "0.5rem 0", fontWeight: 500 }}>{c.reason}</p>

                {/* Blocker alert banner */}
                {c.operational_impact_blockers && c.operational_impact_blockers.length > 0 ? (
                  <div
                    className="deal-cases-blocker-banner banner banner--warning"
                    role="alert"
                    style={{ margin: "0.75rem 0", padding: "0.75rem", background: "rgba(255,170,0,0.1)", border: "1px solid #fa0" }}
                  >
                    <strong>Operational Impact Blockers:</strong>
                    <ul style={{ margin: "0.25rem 0 0 1.25rem", padding: 0 }}>
                      {c.operational_impact_blockers.map((blocker, idx) => (
                        <li key={idx}>{blocker}</li>
                      ))}
                    </ul>
                    <small className="muted" style={{ display: "block", marginTop: "0.25rem" }}>
                      Automated closure is blocked until financial and delivery obligations are settled.
                    </small>
                  </div>
                ) : null}

                {c.resolution ? (
                  <div style={{ margin: "0.5rem 0", padding: "0.5rem", background: "rgba(255,255,255,0.02)", borderRadius: "4px" }}>
                    <strong>Resolution:</strong> {c.resolution}
                  </div>
                ) : null}

                {/* Evidence items */}
                <div style={{ marginTop: "0.75rem" }}>
                  <h4 style={{ margin: "0.25rem 0", fontSize: "0.9rem" }}>
                    Evidence Items ({c.evidence_items.length})
                  </h4>
                  {c.evidence_items.length === 0 ? (
                    <span className="muted" style={{ fontSize: "0.85rem" }}>No evidence submitted.</span>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginTop: "0.25rem" }}>
                      {c.evidence_items.map((e) => (
                        <div
                          key={e.evidence_id}
                          style={{
                            padding: "0.5rem",
                            background: "rgba(0,0,0,0.2)",
                            borderRadius: "4px",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                          }}
                        >
                          <div>
                            <p style={{ margin: 0, fontSize: "0.9rem" }}>{e.notes}</p>
                            <span className="muted mono" style={{ fontSize: "0.75rem" }}>
                              {new Date(e.submitted_at).toLocaleString()}
                            </span>
                          </div>
                          <span className="badge badge--neutral" style={{ fontSize: "0.75rem" }}>
                            {e.visibility}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {canRespond ? (
                    <div style={{ marginTop: "0.5rem" }}>
                      {activeEvidenceCaseId === c.id ? (
                        <form onSubmit={(e) => handleAddEvidenceSubmit(c.id, e)} style={{ marginTop: "0.5rem" }}>
                          <textarea
                            className="input"
                            placeholder="Add evidence notes..."
                            value={newEvidenceNotes}
                            onChange={(e) => setNewEvidenceNotes(e.target.value)}
                            rows={2}
                            style={{ width: "100%", marginBottom: "0.5rem" }}
                            required
                          />
                          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                            <select
                              className="input"
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
                  <div style={{ marginTop: "1rem", paddingTop: "0.75rem", borderTop: "1px solid rgba(255,255,255,0.1)" }}>
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
                      <form onSubmit={handleRespondSubmit} style={{ marginTop: "0.75rem" }}>
                        <div style={{ marginBottom: "0.5rem" }}>
                          <label style={{ display: "block", fontSize: "0.85rem", marginBottom: "0.25rem" }}>
                            Rationale for {activeRespondCase.decision}:
                          </label>
                          <textarea
                            className="input"
                            value={respondRationale}
                            onChange={(e) => setRespondRationale(e.target.value)}
                            placeholder="State rationale for your decision..."
                            rows={2}
                            style={{ width: "100%" }}
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
                ✕
              </button>
            </div>

            <form onSubmit={handleRaiseCaseSubmit} style={{ marginTop: "1rem" }}>
              <div style={{ marginBottom: "1rem" }}>
                <label style={{ display: "block", marginBottom: "0.25rem", fontWeight: 500 }}>
                  Case Type
                </label>
                <div style={{ display: "flex", gap: "1rem" }}>
                  <label>
                    <input
                      type="radio"
                      name="caseType"
                      value="DISPUTE"
                      checked={caseType === "DISPUTE"}
                      onChange={() => setCaseType("DISPUTE")}
                    />{" "}
                    Dispute
                  </label>
                  <label>
                    <input
                      type="radio"
                      name="caseType"
                      value="CANCELLATION"
                      checked={caseType === "CANCELLATION"}
                      onChange={() => setCaseType("CANCELLATION")}
                    />{" "}
                    Mutual Cancellation
                  </label>
                </div>
              </div>

              <div style={{ marginBottom: "1rem" }}>
                <label style={{ display: "block", marginBottom: "0.25rem", fontWeight: 500 }}>
                  Reason
                </label>
                <textarea
                  className="input"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Explain why this case is being raised..."
                  rows={3}
                  style={{ width: "100%" }}
                  required
                />
              </div>

              <div style={{ marginBottom: "1rem" }}>
                <label style={{ display: "block", marginBottom: "0.25rem", fontWeight: 500 }}>
                  Evidence Visibility
                </label>
                <select
                  className="input"
                  value={evidenceVisibility}
                  onChange={(e) => setEvidenceVisibility(e.target.value as EvidenceVisibility)}
                  style={{ width: "100%" }}
                >
                  <option value="MUTUAL_VISIBLE">Mutual Visible (Both parties)</option>
                  <option value="COUNTERPARTY_RESTRICTED">Counterparty Restricted (Submitting org only)</option>
                  <option value="PRIVATE_OPERATOR">Private Operator (Internal only)</option>
                </select>
              </div>

              <div style={{ marginBottom: "1rem" }}>
                <label style={{ display: "block", marginBottom: "0.25rem", fontWeight: 500 }}>
                  Initial Evidence Notes (Optional)
                </label>
                <textarea
                  className="input"
                  value={evidenceNotes}
                  onChange={(e) => setEvidenceNotes(e.target.value)}
                  placeholder="Add initial evidence, document references, or notes..."
                  rows={2}
                  style={{ width: "100%" }}
                />
              </div>

              {formError ? (
                <div className="banner banner--error" role="alert" style={{ marginBottom: "1rem" }}>
                  {formError}
                </div>
              ) : null}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
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
