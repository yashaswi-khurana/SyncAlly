import { useEffect, useRef, useState } from "react";

import {
  ApiError,
  commitAgreementVersion,
  getCurrentAgreement,
  getAgreementHistory,
  getAgreementVersion,
  compareAgreementVersions,
  listOrganizations,
  recordAgreementDecision,
} from "../api/client";
import type { AgreementApproval, AgreementVersion, AgreementHistory, AgreementComparison, Organization } from "../api/types";
import { paymentTimingLabel } from "../api/types";
import CommercialDocumentPanel from "./CommercialDocumentPanel";

interface AgreementReviewProps {
  dealId: string;
  buyerOrganizationId: string;
  sellerOrganizationId: string;
  reloadToken?: number;
  onCommitted?: () => void;
  selectedOrganizationId?: string;
  onOrganizationChange?: (organizationId: string) => void;
}

type AgreementState =
  | { status: "loading" }
  | { status: "empty"; organizations?: Organization[] }
  | { status: "error"; message: string }
  | { status: "ready"; agreement: AgreementVersion; organizations: Organization[] };

function apiMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "Your session has expired. Sign in again.";
    if (error.status === 0) return error.message;
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

function ComparedValue({ value }: { value: unknown }) {
  if (value !== null && typeof value === "object") return <dl className="agreement-terms__item">
    {Object.entries(value).map(([field, entry]) => <div key={field}><dt>{field.replaceAll("_", " ")}</dt><dd><ComparedValue value={entry} /></dd></div>)}
  </dl>;
  return <>{value === null ? "Not specified" : String(value)}</>;
}

export default function AgreementReview({
  dealId,
  buyerOrganizationId,
  sellerOrganizationId,
  reloadToken = 0,
  onCommitted,
  selectedOrganizationId: sharedOrganizationId,
  onOrganizationChange,
}: AgreementReviewProps) {
  const [state, setState] = useState<AgreementState>({ status: "loading" });
  const [selectedOrganizationId, setSelectedOrganizationId] = useState("");
  const selectedPartyRef = useRef("");
  const [reloadCount, setReloadCount] = useState(0);
  const [pendingDecision, setPendingDecision] = useState<"approve" | "reject" | "commit" | null>(null);
  const [decisionError, setDecisionError] = useState("");
  const [stale, setStale] = useState(false);
  const [viewedVersion, setViewedVersion] = useState(0);
  const [compareBefore, setCompareBefore] = useState(0);
  const [history, setHistory] = useState<{ key: string; data: AgreementHistory } | null>(null);
  const [versionView, setVersionView] = useState<{ key: string; agreement?: AgreementVersion; comparison?: AgreementComparison; error?: string } | null>(null);
  const actingOrganizationId = sharedOrganizationId ?? selectedOrganizationId;
  const context = useRef("");
  const contextSignature = JSON.stringify([dealId, actingOrganizationId, reloadToken, reloadCount, viewedVersion, compareBefore]);
  useEffect(() => { context.current = contextSignature; }, [contextSignature]);
  const loadContext = JSON.stringify([dealId, sharedOrganizationId, reloadToken, reloadCount]);
  const [observedContext, setObservedContext] = useState(loadContext);
  if (observedContext !== loadContext) {
    setObservedContext(loadContext);
    setState({ status: "loading" });
    setPendingDecision(null);
    setStale(false);
    setDecisionError("");
    setViewedVersion(0);
    setCompareBefore(0);
    setHistory(null);
    setVersionView(null);
  }
  const active = useRef(true);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);

  const historyKey = JSON.stringify([dealId, actingOrganizationId, reloadToken, reloadCount]);
  useEffect(() => {
    if (!actingOrganizationId || state.status !== "ready") return;
    const controller = new AbortController();
    void getAgreementHistory(dealId, actingOrganizationId, controller.signal)
      .then((data) => { if (!controller.signal.aborted) setHistory({ key: historyKey, data }); })
      .catch(() => { if (!controller.signal.aborted) setHistory(null); });
    return () => controller.abort();
  }, [dealId, actingOrganizationId, reloadToken, reloadCount, historyKey, state.status]);

  useEffect(() => {
    if (!actingOrganizationId || state.status !== "ready") return;
    const controller = new AbortController();
    const number = viewedVersion || state.agreement.version_number;
    void Promise.all([
      getAgreementVersion(dealId, number, actingOrganizationId, controller.signal),
      compareBefore ? compareAgreementVersions(dealId, compareBefore, number, actingOrganizationId, controller.signal) : Promise.resolve(undefined),
    ]).then(([agreement, comparison]) => {
      if (agreement.deal_id !== dealId || agreement.version_number !== number
        || (comparison && (comparison.before.deal_id !== dealId || comparison.after.deal_id !== dealId
          || comparison.before.version_number !== compareBefore || comparison.after.version_number !== number
          || comparison.after.terms_hash !== agreement.terms_hash))) throw new Error("Version response mismatch");
      if (!controller.signal.aborted) setVersionView({ key: contextSignature, agreement, comparison });
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setVersionView({ key: contextSignature, error: apiMessage(error) });
    });
    return () => controller.abort();
  }, [dealId, actingOrganizationId, viewedVersion, compareBefore, contextSignature, state]);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    void Promise.all([getCurrentAgreement(dealId, { organizationId: sharedOrganizationId, signal: controller.signal }).catch((error: unknown) => {
      if (error instanceof ApiError && error.status === 404) return null;
      throw error;
    }), listOrganizations()])
      .then(async ([agreement, organizations]) => {
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
        if (!agreement) {
          const party = sharedOrganizationId || selectedPartyRef.current || (parties.length === 1 ? parties[0].id : "");
          if (party) {
            const saved = await getAgreementHistory(dealId, party, controller.signal);
            if (cancelled) return;
            if (saved.versions.length) {
              const latest = saved.versions[0];
              setHistory({ key: JSON.stringify([dealId, party, reloadToken, reloadCount]), data: saved });
              setViewedVersion(latest.version_number);
              setState({ status: "ready", agreement: latest, organizations: parties });
              return;
            }
          }
          setState({ status: "empty", organizations: parties });
          return;
        }
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
      controller.abort();
    };
  }, [dealId, buyerOrganizationId, sellerOrganizationId, sharedOrganizationId, reloadCount, reloadToken]);

  async function decide(decision: "approve" | "reject") {
    if (state.status !== "ready" || pendingDecision || !actingOrganizationId || stale || viewedVersion || compareBefore) return;
    if (state.agreement.is_current === false) return;
    if (versionView?.key === contextSignature && (versionView.error || versionView.agreement?.is_current === false
      || versionView.agreement?.terms_hash !== state.agreement.terms_hash)) return;
    const atStart = context.current;
    setPendingDecision(decision);
    setDecisionError("");
    setStale(false);
    try {
      await recordAgreementDecision(
        dealId,
        state.agreement.version_number,
        state.agreement.terms_hash,
        decision,
        actingOrganizationId || undefined,
      );
      if (!active.current || atStart !== context.current) return;
      reloadAgreement();
    } catch (error) {
      if (!active.current || atStart !== context.current) return;
      if (error instanceof ApiError && error.status === 409) {
        setStale(true);
        setDecisionError(
          "This agreement changed or this decision conflicts with one already recorded. Reload and review the current version before continuing.",
        );
      } else {
        setDecisionError(apiMessage(error));
      }
    } finally {
      if (active.current && atStart === context.current) setPendingDecision(null);
    }
  }

  async function commitCurrentAgreement() {
    if (state.status !== "ready" || pendingDecision || !actingOrganizationId || stale || viewedVersion || compareBefore) return;
    if (state.agreement.is_current === false) return;
    if (versionView?.key === contextSignature && (versionView.error || versionView.agreement?.is_current === false
      || versionView.agreement?.terms_hash !== state.agreement.terms_hash)) return;
    const atStart = context.current;
    setPendingDecision("commit");
    setDecisionError("");
    setStale(false);
    try {
      await commitAgreementVersion(
        dealId,
        state.agreement.version_number,
        state.agreement.terms_hash,
        actingOrganizationId,
      );
      if (!active.current || atStart !== context.current) return;
      onCommitted?.();
      reloadAgreement();
    } catch (error) {
      if (!active.current || atStart !== context.current) return;
      if (error instanceof ApiError && error.status === 409) {
        setStale(true);
        setDecisionError(
          "This agreement changed or is no longer ready to commit. Reload and review the current version before continuing.",
        );
      } else {
        setDecisionError(apiMessage(error));
      }
    } finally {
      if (active.current && atStart === context.current) setPendingDecision(null);
    }
  }

  function reloadAgreement() {
    setState({ status: "loading" });
    setStale(false);
    setDecisionError("");
    setReloadCount((count) => count + 1);
  }

  function changeParty(organizationId: string) {
    selectedPartyRef.current = organizationId;
    setSelectedOrganizationId(organizationId);
    onOrganizationChange?.(organizationId);
  }

  return (
    <section className="card agreement-review" aria-labelledby="agreement-review-heading">
      <div className="panel-head">
        <div>
          <span className="eyebrow">Saved terms</span>
          <h2 id="agreement-review-heading">Agreement review</h2>
        </div>
        {state.status === "ready" ? (
          <span className="badge badge--kind">VERSION {viewedVersion || state.agreement.version_number}</span>
        ) : null}
      </div>

      {state.status === "loading" ? <p role="status">Loading saved agreement…</p> : null}
      {state.status === "empty" ? (
        <div className="empty-state">
          {state.organizations && state.organizations.length > 1 ? <div className="field">
            <label htmlFor={`agreement-empty-party-${dealId}`}>Review as organization</label>
            <select id={`agreement-empty-party-${dealId}`} value={actingOrganizationId} onChange={(event) => {
              changeParty(event.target.value); setReloadCount((count) => count + 1);
            }}><option value="">Choose an organization</option>{state.organizations.map((party) => <option key={party.id} value={party.id}>{party.legal_name}</option>)}</select>
          </div> : null}
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
        const currentView = versionView?.key === contextSignature ? versionView : null;
        const currentHistory = history?.key === historyKey ? history.data : null;
        const partySelector = state.organizations.length > 1 ? <div className="field agreement-review__party-choice">
          <label htmlFor={`agreement-party-${dealId}`}>{viewedVersion ? "Review as organization" : "Approve as organization"}</label>
          <select id={`agreement-party-${dealId}`} value={actingOrganizationId} disabled={pendingDecision !== null}
            onChange={(event) => changeParty(event.target.value)}>
            <option value="">Choose an organization</option>
            {state.organizations.map((organization) => <option key={organization.id} value={organization.id}>{organization.legal_name}</option>)}
          </select>
        </div> : null;
        const selectors = currentHistory ? <div className="field">
          <label htmlFor={`agreement-version-${dealId}`}>Agreement version</label>
          <select id={`agreement-version-${dealId}`} value={viewedVersion} disabled={pendingDecision !== null}
            onChange={(event) => setViewedVersion(Number(event.target.value))}>
            <option value={0}>Current version</option>
            {currentHistory.versions.map((version) => <option key={version.id ?? version.version_number} value={version.version_number}>
              Version {version.version_number} · {version.status.replaceAll("_", " ")}
            </option>)}
          </select>
          <label htmlFor={`agreement-compare-${dealId}`}>Compare before</label>
          <select id={`agreement-compare-${dealId}`} value={compareBefore} disabled={pendingDecision !== null}
            onChange={(event) => setCompareBefore(Number(event.target.value))}>
            <option value={0}>No comparison</option>
            {currentHistory.versions.map((version) => <option key={version.id ?? version.version_number} value={version.version_number}>Version {version.version_number}</option>)}
          </select>
        </div> : null;
        if ((viewedVersion || compareBefore) && !currentView?.agreement) return <>{partySelector}{selectors}<p role={currentView?.error ? "alert" : "status"}>{currentView?.error ?? "Loading saved version…"}</p></>;
        const agreement = viewedVersion ? currentView!.agreement! : state.agreement;
        const buyerApproval = approvalFor(agreement.approvals, buyerOrganizationId);
        const sellerApproval = approvalFor(agreement.approvals, sellerOrganizationId);
        const myApproval = actingOrganizationId
          ? approvalFor(agreement.approvals, actingOrganizationId)
          : undefined;
        const readConflict = !viewedVersion && currentView && (currentView.error || currentView.agreement?.is_current === false
          || currentView.agreement?.terms_hash !== agreement.terms_hash);
        const canDecide = agreement.status === "PENDING_APPROVAL" && agreement.is_current !== false && !viewedVersion && !compareBefore && !readConflict;
        // Prefer the explicit, hashed projection; fall back to the nested terms
        // so a cached payload from before that field existed still renders.
        const paymentTiming = agreement.payment_trigger && agreement.payment_due_condition
          ? [{
              trigger: agreement.payment_trigger,
              dueCondition: agreement.payment_due_condition,
            }]
          : agreement.terms.payment_terms.map((term) => ({
              trigger: term.trigger,
              dueCondition: term.due_condition,
            }));
        const bothApproved = buyerApproval?.decision === "APPROVE"
          && sellerApproval?.decision === "APPROVE"
          && buyerApproval.terms_hash === agreement.terms_hash
          && sellerApproval.terms_hash === agreement.terms_hash;
        return (
          <>
            {partySelector}
            {selectors}
            {viewedVersion ? <p role="status">Historical version · Read-only</p> : null}
            {readConflict ? <div role="alert"><p>The agreement changed or is unavailable.</p><button type="button" className="button secondary" onClick={reloadAgreement}>Reload agreement</button></div> : null}
            {currentView?.comparison ? <div aria-label="Structured agreement comparison">
              <h3>Version {currentView.comparison.before.version_number} to {currentView.comparison.after.version_number}</h3>
              {currentView.comparison.changes.fields.map((change) => <dl key={change.field}>
                <dt>{change.field.replaceAll("_", " ")}</dt><dd><ComparedValue value={change.before} /> → <ComparedValue value={change.after} /></dd>
              </dl>)}
              {Object.entries(currentView.comparison.changes.collections).map(([name, changes]) => <div key={name}>
                <h4>{name.replaceAll("_", " ")}</h4>
                {changes.added.map((entry, index) => <div key={`added-${index}`}><strong>Added</strong><ComparedValue value={entry} /></div>)}
                {changes.removed.map((entry, index) => <div key={`removed-${index}`}><strong>Removed</strong><ComparedValue value={entry} /></div>)}
                {changes.modified.map((entry, index) => <div key={`modified-${index}`}><strong>Modified · Before</strong><ComparedValue value={entry.before} /><strong>After</strong><ComparedValue value={entry.after} /></div>)}
              </div>)}
            </div> : null}
            {currentView?.agreement?.evidence?.length ? <div aria-label="Agreement evidence trace">
              <h3>Referenced evidence · Unmapped to terms</h3>
              {currentView.agreement.evidence.map((ref, index) => <div key={index}>
                <p>{ref.state}{ref.fact_id ? ` · Fact ${ref.fact_id} version ${ref.version}` : ""}</p>
                {ref.trace_enabled && ref.organization_id === actingOrganizationId && ref.agreement_version_id === currentView.agreement?.id
                  && ref.terms_hash === agreement.terms_hash && !stale && !readConflict ? <blockquote>{ref.source_span}</blockquote> : null}
              </div>)}
            </div> : null}
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

            {agreement.status === "COMMITTED" && agreement.id && actingOrganizationId
              && currentView?.agreement?.id === agreement.id
              && currentView.agreement.terms_hash === agreement.terms_hash
              && currentView.agreement.status === "COMMITTED" && !stale && !readConflict ? (
              <CommercialDocumentPanel key={contextSignature} dealId={dealId} agreement={agreement}
                organizationId={actingOrganizationId} contextKey={contextSignature} />
            ) : null}

            {paymentTiming.length > 0 ? (
              <div className="agreement-terms" aria-label="Payment timing summary">
                <h3>Payment timing</h3>
                {paymentTiming.map((term, index) => (
                  <dl
                    className="agreement-terms__item"
                    key={`${term.trigger}-${term.dueCondition}-${index}`}
                  >
                    <div>
                      <dt>Payment Timing</dt>
                      <dd>{paymentTimingLabel(term.trigger)}</dd>
                    </div>
                    <div>
                      <dt>Due Condition</dt>
                      <dd>{term.dueCondition}</dd>
                    </div>
                  </dl>
                ))}
                <p className="hint">
                  Both parties review these exact terms before signing. The terms hash above
                  covers them.
                </p>
              </div>
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
                  <div><dt>Payment Timing (contract text)</dt><dd>{term.trigger.replaceAll("_", " ")}</dd></div>
                  <div><dt>Due Condition (contract text)</dt><dd>{term.due_condition}</dd></div>
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
                    {approval ? <div><span>Actor {approval.user_id}</span> <time dateTime={approval.created_at}>{new Date(approval.created_at).toLocaleString()}</time><code className="agreement-review__hash">{approval.terms_hash}</code></div> : null}
                  </div>
                );
              })}
            </div>

            {canDecide ? (
              <>
                {myApproval ? (
                  <p className="hint">Your organization recorded {myApproval.decision.toLowerCase()} for this exact version.</p>
                ) : null}
                <p className="hint">Your decision will include version {agreement.version_number} and the hash shown above.</p>
                <div className="fact-actions">
                  <button
                    type="button"
                    className="button"
                    disabled={stale || !actingOrganizationId || pendingDecision !== null || myApproval?.decision === "APPROVE"}
                    onClick={() => void decide("approve")}
                  >
                    {pendingDecision === "approve" ? "Submitting approval…" : "Approve this version"}
                  </button>
                  <button
                    type="button"
                    className="button secondary"
                    disabled={stale || !actingOrganizationId || pendingDecision !== null || myApproval?.decision === "REJECT"}
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
                      disabled={stale || !actingOrganizationId || pendingDecision !== null}
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
