import { useEffect, useState } from "react";

import {
  ApiError,
  commitAgreementVersion,
  getCurrentAgreement,
  listOrganizations,
  recordAgreementDecision,
} from "../api/client";
import type { AgreementApproval, AgreementVersion, Organization } from "../api/types";

interface AgreementReviewProps {
  dealId: string;
  buyerOrganizationId: string;
  sellerOrganizationId: string;
}

type AgreementState =
  | { status: "loading" }
  | { status: "empty" }
  | { status: "error"; message: string }
  | { status: "ready"; agreement: AgreementVersion; organizations: Organization[] };

function apiMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "Your session has expired. Sign in again.";
    return error.message;
  }
  return "Unable to load this agreement. Please try again.";
}

function partyName(organizations: Organization[], id: string): string {
  return organizations.find((organization) => organization.id === id)?.legal_name ?? id;
}

function approvalFor(
  approvals: AgreementApproval[],
  organizationId: string,
): AgreementApproval | undefined {
  return approvals.find((approval) => approval.organization_id === organizationId);
}

export default function AgreementReview({
  dealId,
  buyerOrganizationId,
  sellerOrganizationId,
}: AgreementReviewProps) {
  const [state, setState] = useState<AgreementState>({ status: "loading" });
  const [selectedOrganizationId, setSelectedOrganizationId] = useState("");
  const [reloadCount, setReloadCount] = useState(0);
  const [pendingDecision, setPendingDecision] = useState<"approve" | "reject" | "commit" | null>(null);
  const [decisionError, setDecisionError] = useState("");
  const [stale, setStale] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([getCurrentAgreement(dealId), listOrganizations()])
      .then(([agreement, organizations]) => {
        if (cancelled) return;
        const parties = organizations.filter(
          (organization) =>
            organization.id === buyerOrganizationId ||
            organization.id === sellerOrganizationId,
        );
        setSelectedOrganizationId((current) =>
          parties.some((party) => party.id === current)
            ? current
            : parties.length === 1
              ? parties[0].id
              : "",
        );
        setState({ status: "ready", agreement, organizations: parties });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 404) {
          setState({ status: "empty" });
        } else {
          setState({ status: "error", message: apiMessage(error) });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [dealId, buyerOrganizationId, sellerOrganizationId, reloadCount]);

  async function decide(decision: "approve" | "reject") {
    if (state.status !== "ready") return;
    setPendingDecision(decision);
    setDecisionError("");
    setStale(false);
    try {
      await recordAgreementDecision(
        dealId,
        state.agreement.version_number,
        state.agreement.terms_hash,
        decision,
        selectedOrganizationId || undefined,
      );
      reloadAgreement();
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setStale(true);
        setDecisionError(
          "This agreement changed or this decision conflicts with one already recorded. Reload and review the current version before continuing.",
        );
      } else {
        setDecisionError(apiMessage(error));
      }
    } finally {
      setPendingDecision(null);
    }
  }

  async function commitCurrentAgreement() {
    if (state.status !== "ready") return;
    setPendingDecision("commit");
    setDecisionError("");
    setStale(false);
    try {
      await commitAgreementVersion(
        dealId,
        state.agreement.version_number,
        state.agreement.terms_hash,
      );
      reloadAgreement();
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setStale(true);
        setDecisionError(
          "This agreement changed or is no longer ready to commit. Reload and review the current version before continuing.",
        );
      } else {
        setDecisionError(apiMessage(error));
      }
    } finally {
      setPendingDecision(null);
    }
  }

  function reloadAgreement() {
    setState({ status: "loading" });
    setStale(false);
    setDecisionError("");
    setReloadCount((count) => count + 1);
  }

  return (
    <section className="card agreement-review" aria-labelledby="agreement-review-heading">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Saved terms</span>
          <h2 id="agreement-review-heading">Agreement review</h2>
        </div>
        {state.status === "ready" ? (
          <span className="badge badge--kind">VERSION {state.agreement.version_number}</span>
        ) : null}
      </div>

      {state.status === "loading" ? <p role="status">Loading saved agreement…</p> : null}
      {state.status === "empty" ? (
        <div className="empty-state">
          <p>No saved agreement version is ready for review yet.</p>
          <button type="button" className="button secondary" onClick={reloadAgreement}>
            Reload agreement
          </button>
        </div>
      ) : null}
      {state.status === "error" ? (
        <div role="alert">
          <p className="form-error">{state.message}</p>
          <button type="button" className="button secondary" onClick={reloadAgreement}>
            Try again
          </button>
        </div>
      ) : null}

      {state.status === "ready" ? (() => {
        const agreement = state.agreement;
        const buyerApproval = approvalFor(agreement.approvals, buyerOrganizationId);
        const sellerApproval = approvalFor(agreement.approvals, sellerOrganizationId);
        const myApproval = selectedOrganizationId
          ? approvalFor(agreement.approvals, selectedOrganizationId)
          : undefined;
        const canDecide = agreement.status === "PENDING_APPROVAL";
        const bothApproved = buyerApproval?.decision === "APPROVE"
          && sellerApproval?.decision === "APPROVE"
          && buyerApproval.terms_hash === agreement.terms_hash
          && sellerApproval.terms_hash === agreement.terms_hash;
        return (
          <>
            <div className="agreement-review__summary">
              <div>
                <span className="fact-source__label">VERSION STATUS</span>
                <strong>{agreement.status.replaceAll("_", " ")}</strong>
              </div>
              <div>
                <span className="fact-source__label">EXACT TERMS HASH</span>
                <code className="agreement-review__hash">{agreement.terms_hash}</code>
              </div>
              <div>
                <span className="fact-source__label">SAVED</span>
                <time dateTime={agreement.created_at}>
                  {new Date(agreement.created_at).toLocaleString()}
                </time>
              </div>
            </div>

            {agreement.status === "COMMITTED" ? (
              <p className="agreement-review__notice" role="status">
                This agreement is committed. Its terms are read-only and cannot be changed in place.
              </p>
            ) : null}

            <div className="agreement-terms" aria-label={`Agreement version ${agreement.version_number} terms`}>
              <h3>Trade terms</h3>
              {agreement.terms.line_items.map((item, index) => (
                <dl className="agreement-terms__item" key={`${item.description}-${index}`}>
                  <div><dt>Item</dt><dd>{item.description}</dd></div>
                  <div><dt>Quantity</dt><dd>{item.quantity} {item.unit}</dd></div>
                  {item.sku ? <div><dt>SKU</dt><dd>{item.sku}</dd></div> : null}
                  <div><dt>Unit price</dt><dd>{item.unit_price.amount} {item.unit_price.currency}</dd></div>
                </dl>
              ))}
              {agreement.terms.shipments.map((shipment, index) => (
                <dl className="agreement-terms__item" key={`${shipment.destination}-${index}`}>
                  <div><dt>Delivery location</dt><dd>{shipment.destination}</dd></div>
                  <div><dt>Delivery quantity</dt><dd>{shipment.quantity}</dd></div>
                  <div><dt>Target date</dt><dd>{shipment.target_date ?? "Not specified"}</dd></div>
                </dl>
              ))}
              {agreement.terms.payment_terms.map((term, index) => (
                <dl className="agreement-terms__item" key={`${term.trigger}-${index}`}>
                  <div><dt>Payment amount</dt><dd>{term.amount.amount} {term.amount.currency}</dd></div>
                  <div><dt>Payment trigger</dt><dd>{term.trigger.replaceAll("_", " ")}</dd></div>
                  <div><dt>Due condition</dt><dd>{term.due_condition}</dd></div>
                </dl>
              ))}
              <dl className="agreement-terms__item">
                <div><dt>Delivery location</dt><dd>{agreement.terms.delivery_location}</dd></div>
                {agreement.terms.incoterm ? <div><dt>Incoterm</dt><dd>{agreement.terms.incoterm}</dd></div> : null}
                {agreement.terms.cancellation_terms ? <div><dt>Cancellation terms</dt><dd>{agreement.terms.cancellation_terms}</dd></div> : null}
              </dl>
            </div>

            <div className="agreement-review__approvals" aria-label="Approval status by organization">
              <h3>Decisions for version {agreement.version_number}</h3>
              {[buyerOrganizationId, sellerOrganizationId].map((organizationId) => {
                const approval = organizationId === buyerOrganizationId ? buyerApproval : sellerApproval;
                return (
                  <div className="agreement-review__approval" key={organizationId}>
                    <span>{partyName(state.organizations, organizationId)}</span>
                    <span className={`badge ${approval?.decision === "APPROVE" ? "badge--status-confirmed" : approval?.decision === "REJECT" ? "badge--status-rejected" : "badge--status-extracted"}`}>
                      {approval?.decision ?? "AWAITING DECISION"}
                    </span>
                  </div>
                );
              })}
            </div>

            {canDecide ? (
              <>
                {state.organizations.length > 1 ? (
                  <div className="field agreement-review__party-choice">
                    <label htmlFor={`agreement-party-${dealId}`}>Approve as organization</label>
                    <select
                      id={`agreement-party-${dealId}`}
                      value={selectedOrganizationId}
                      onChange={(event) => setSelectedOrganizationId(event.target.value)}
                    >
                      <option value="">Choose an organization</option>
                      {state.organizations.map((organization) => (
                        <option key={organization.id} value={organization.id}>{organization.legal_name}</option>
                      ))}
                    </select>
                  </div>
                ) : null}
                {myApproval ? (
                  <p className="hint">Your organization recorded {myApproval.decision.toLowerCase()} for this exact version.</p>
                ) : null}
                <p className="hint">Your decision will include version {agreement.version_number} and the hash shown above.</p>
                <div className="fact-actions">
                  <button
                    type="button"
                    className="button"
                    disabled={stale || !selectedOrganizationId || pendingDecision !== null || myApproval?.decision === "APPROVE"}
                    onClick={() => void decide("approve")}
                  >
                    {pendingDecision === "approve" ? "Submitting approval…" : "Approve this version"}
                  </button>
                  <button
                    type="button"
                    className="button secondary"
                    disabled={stale || !selectedOrganizationId || pendingDecision !== null || myApproval?.decision === "REJECT"}
                    onClick={() => void decide("reject")}
                  >
                    {pendingDecision === "reject" ? "Submitting rejection…" : "Reject this version"}
                  </button>
                </div>
                {bothApproved ? (
                  <div className="agreement-review__commit">
                    <p className="agreement-review__notice">
                      Both organizations approved this exact version. Commit it to mark the deal agreed.
                    </p>
                    <button
                      type="button"
                      className="button"
                      disabled={stale || pendingDecision !== null}
                      onClick={() => void commitCurrentAgreement()}
                    >
                      {pendingDecision === "commit" ? "Committing agreement…" : "Commit approved agreement"}
                    </button>
                  </div>
                ) : null}
              </>
            ) : null}

            {decisionError ? (
              <div role="alert" className="agreement-review__error">
                <p className="form-error">{decisionError}</p>
                {stale ? (
                  <button type="button" className="button" onClick={reloadAgreement}>
                    Reload and review current version
                  </button>
                ) : null}
              </div>
            ) : null}
            {!canDecide && agreement.status !== "COMMITTED" ? (
              <p className="hint">This version is not open for decisions.</p>
            ) : null}
          </>
        );
      })() : null}
    </section>
  );
}
