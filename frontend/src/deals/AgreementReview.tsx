import { useEffect, useRef, useState } from "react";

import {
  ApiError,
  commitAgreementVersion,
  getCurrentAgreement,
  getAgreementHistory,
  getAgreementVersion,
  compareAgreementVersions,
  getAmendmentImpact,
  previewAmendmentImpact,
  proposeAmendment,
  listOrganizations,
  recordAgreementDecision,
  withdrawAmendment,
} from "../api/client";
import type {
  AgreementApproval,
  AgreementVersion,
  AgreementHistory,
  AgreementComparison,
  AmendmentImpact,
  Organization,
  PaymentTrigger,
  ProposeAmendmentRequest,
} from "../api/types";
import { paymentTimingLabel } from "../api/types";
import CommercialDocumentPanel from "./CommercialDocumentPanel";
import type { OverviewSnapshot } from "./DealOverview";

interface AgreementReviewProps {
  dealId: string;
  buyerOrganizationId: string;
  sellerOrganizationId: string;
  reloadToken?: number;
  onCommitted?: () => void;
  selectedOrganizationId?: string;
  onOrganizationChange?: (organizationId: string) => void;
  onOverviewChange?: (snapshot: OverviewSnapshot) => void;
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

function agreementStatusLabel(status: string): string {
  switch (status) {
    case "PENDING_APPROVAL": return "Awaiting party decisions";
    case "COMMITTED": return "Agreed and committed";
    case "SUPERSEDED": return "Replaced by a newer version";
    case "VOIDED": return "Withdrawn";
    default: return status.replaceAll("_", " ").toLowerCase();
  }
}

function decisionLabel(decision?: AgreementApproval["decision"]): string {
  if (decision === "APPROVE") return "Approved";
  if (decision === "REJECT") return "Rejected";
  return "Awaiting decision";
}

function approvalMatchesVersion(approval: AgreementApproval | undefined, agreement: AgreementVersion): boolean {
  return Boolean(approval && approval.version_number === agreement.version_number && approval.terms_hash === agreement.terms_hash);
}

function approvalFor(
  approvals: AgreementApproval[] | undefined,
  organizationId: string,
): AgreementApproval | undefined {
  return approvals?.find((approval) => approval.organization_id === organizationId);
}

function ComparedValue({ value }: { value: unknown }) {
  if (value === null || value === undefined) return <>Not specified</>;
  if (Array.isArray(value)) {
    if (value.length === 0) return <>None</>;
    return (
      <ul className="compared-list" style={{ listStyleType: "none", paddingLeft: 0 }}>
        {value.map((item, index) => (
          <li key={index}><ComparedValue value={item} /></li>
        ))}
      </ul>
    );
  }
  if (typeof value === "object") {
    return (
      <dl className="agreement-terms__item">
        {Object.entries(value).map(([field, entry]) => (
          <div key={field}>
            <dt>{field.replaceAll("_", " ")}</dt>
            <dd><ComparedValue value={entry} /></dd>
          </div>
        ))}
      </dl>
    );
  }
  return <>{String(value)}</>;
}

export default function AgreementReview({
  dealId,
  buyerOrganizationId,
  sellerOrganizationId,
  reloadToken = 0,
  onCommitted,
  selectedOrganizationId: sharedOrganizationId,
  onOrganizationChange,
  onOverviewChange,
}: AgreementReviewProps) {
  const [state, setState] = useState<AgreementState>({ status: "loading" });
  const [selectedOrganizationId, setSelectedOrganizationId] = useState("");
  const selectedPartyRef = useRef("");
  const [reloadCount, setReloadCount] = useState(0);
  const [pendingDecision, setPendingDecision] = useState<"approve" | "reject" | "commit" | "withdraw" | null>(null);
  const [decisionError, setDecisionError] = useState("");
  const [stale, setStale] = useState(false);
  const [viewedVersion, setViewedVersion] = useState(0);
  const [compareBefore, setCompareBefore] = useState(0);
  const [history, setHistory] = useState<{ key: string; data: AgreementHistory } | null>(null);
  const [versionView, setVersionView] = useState<{ key: string; agreement?: AgreementVersion; comparison?: AgreementComparison; error?: string } | null>(null);
  const [amendmentImpact, setAmendmentImpact] = useState<AmendmentImpact | null>(null);
  const [showProposeAmendment, setShowProposeAmendment] = useState(false);
  const [amendmentRationale, setAmendmentRationale] = useState("");
  const [submittingAmendment, setSubmittingAmendment] = useState(false);
  const [amendmentError, setAmendmentError] = useState("");
  const [previewingImpact, setPreviewingImpact] = useState(false);
  const [proposedImpact, setProposedImpact] = useState<AmendmentImpact | null>(null);
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
    setAmendmentImpact(null);
    setShowProposeAmendment(false);
    setAmendmentRationale("");
    setSubmittingAmendment(false);
    setAmendmentError("");
    setPreviewingImpact(false);
    setProposedImpact(null);
  }
  const active = useRef(true);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);

  const historyKey = JSON.stringify([dealId, actingOrganizationId, reloadToken, reloadCount]);
  useEffect(() => {
    if (!actingOrganizationId || state.status !== "ready") return;
    const controller = new AbortController();
    void getAgreementHistory(dealId, actingOrganizationId, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setHistory({ key: historyKey, data });
        }
      })
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
      if (!controller.signal.aborted) {
        setVersionView({ key: contextSignature, agreement, comparison });
        if (!viewedVersion && !compareBefore && (agreement.is_current === false || agreement.terms_hash !== state.agreement.terms_hash)) {
          onOverviewChange?.({ dealId, organizationId: actingOrganizationId || "", reloadToken, status: "error" });
        } else if (!viewedVersion && !compareBefore) {
          onOverviewChange?.({
            dealId,
            organizationId: actingOrganizationId || "",
            reloadToken,
            status: "ready",
            partyVerified: state.status === "ready" && state.organizations.some((party) => party.id === actingOrganizationId),
            agreement,
          });
        }
      }
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) {
        setVersionView({ key: contextSignature, error: apiMessage(error) });
        if (!viewedVersion && !compareBefore) onOverviewChange?.({ dealId, organizationId: actingOrganizationId || "", reloadToken, status: "error" });
      }
    });
    return () => controller.abort();
  }, [dealId, actingOrganizationId, viewedVersion, compareBefore, contextSignature, state, onOverviewChange, reloadToken, sharedOrganizationId]);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    const overviewContext = {
      dealId,
      organizationId: sharedOrganizationId || selectedPartyRef.current || "",
      reloadToken,
    };
    let errorOverviewContext = overviewContext;
    onOverviewChange?.({ ...overviewContext, status: "loading" });
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
        if (parties.length === 0) throw new Error("No active deal organization is available");

        const requestedParty = sharedOrganizationId || selectedPartyRef.current;
        const partyId = parties.some((party) => party.id === requestedParty)
          ? requestedParty
          : parties.length === 1
            ? parties[0].id
            : "";
        selectedPartyRef.current = partyId;
        setSelectedOrganizationId(partyId);
        if (partyId && !sharedOrganizationId && parties.length === 1) onOrganizationChange?.(partyId);

        const partyVerified = Boolean(partyId && parties.some((party) => party.id === partyId));
        const partyOverviewContext = { dealId, organizationId: partyId, reloadToken };
        errorOverviewContext = partyOverviewContext;

        if (agreement && (agreement.deal_id !== dealId || agreement.is_current === false)) {
          throw new Error("The current agreement response does not match this deal");
        }

        if (agreement) {
          onOverviewChange?.({ ...partyOverviewContext, status: partyVerified ? "loading" : "ready", partyVerified, agreement });
          setState({ status: "ready", agreement, organizations: parties });
          return;
        }

        if (!agreement) {
          if (partyId) {
            const saved = await getAgreementHistory(dealId, partyId, controller.signal);
            if (cancelled) return;
            if (saved.deal_id !== dealId || saved.organization_id !== partyId || saved.current_version_id !== null) {
              throw new Error("Agreement history does not confirm the current deal state");
            }
            if (saved.versions.length) {
              const latest = saved.versions[0];
              setHistory({ key: JSON.stringify([dealId, partyId, reloadToken, reloadCount]), data: saved });
              setViewedVersion(latest.version_number);
              onOverviewChange?.({ ...partyOverviewContext, status: "empty", partyVerified });
              setState({ status: "ready", agreement: latest, organizations: parties });
              return;
            }
          }
          onOverviewChange?.({ ...partyOverviewContext, status: "empty", partyVerified });
          setState({ status: "empty", organizations: parties });
        }
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        onOverviewChange?.({ ...errorOverviewContext, status: "error" });
        setState({ status: "error", message: apiMessage(error) });
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [dealId, buyerOrganizationId, sellerOrganizationId, sharedOrganizationId, reloadCount, reloadToken, onOverviewChange, onOrganizationChange]);

  function getActiveAgreement(): AgreementVersion | null {
    if (state.status !== "ready") return null;
    if (viewedVersion && versionView?.key === contextSignature && versionView.agreement) {
      return versionView.agreement;
    }
    return state.agreement;
  }

  async function decide(decision: "approve" | "reject") {
    const agreement = getActiveAgreement();
    if (!agreement || state.status !== "ready" || pendingDecision || !actingOrganizationId || stale || compareBefore) return;
    if (agreement.status !== "PENDING_APPROVAL") return;
    const atStart = context.current;
    setPendingDecision(decision);
    setDecisionError("");
    setStale(false);
    try {
      await recordAgreementDecision(
        dealId,
        agreement.version_number,
        agreement.terms_hash,
        decision,
        actingOrganizationId || undefined,
      );
      if (!active.current || atStart !== context.current) return;
      reloadAgreement();
    } catch (error) {
      if (!active.current || atStart !== context.current) return;
      if (error instanceof ApiError && error.status === 409) {
        setStale(true);
        onOverviewChange?.({ dealId, organizationId: actingOrganizationId || "", reloadToken, status: "error" });
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
    const agreement = getActiveAgreement();
    if (!agreement || state.status !== "ready" || pendingDecision || !actingOrganizationId || stale || compareBefore) return;
    if (agreement.status !== "PENDING_APPROVAL") return;
    const atStart = context.current;
    setPendingDecision("commit");
    setDecisionError("");
    setStale(false);
    try {
      await commitAgreementVersion(
        dealId,
        agreement.version_number,
        agreement.terms_hash,
        actingOrganizationId,
      );
      if (!active.current || atStart !== context.current) return;
      onCommitted?.();
      reloadAgreement();
    } catch (error) {
      if (!active.current || atStart !== context.current) return;
      if (error instanceof ApiError && error.status === 409) {
        setStale(true);
        onOverviewChange?.({ dealId, organizationId: actingOrganizationId || "", reloadToken, status: "error" });
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

  useEffect(() => {
    const controller = new AbortController();
    if (state.status !== "ready") {
      void Promise.resolve().then(() => {
        if (!controller.signal.aborted) setAmendmentImpact(null);
      });
      return () => controller.abort();
    }
    const currentAgreement = viewedVersion ? versionView?.agreement : state.agreement;
    if (currentAgreement && currentAgreement.version_number > 1 && currentAgreement.status === "PENDING_APPROVAL") {
      void getAmendmentImpact(dealId, { versionNumber: currentAgreement.version_number, signal: controller.signal })
        .then((impact) => {
          if (!controller.signal.aborted) setAmendmentImpact(impact);
        })
        .catch(() => {
          if (!controller.signal.aborted) setAmendmentImpact(null);
        });
      return () => controller.abort();
    } else {
      void Promise.resolve().then(() => {
        if (!controller.signal.aborted) setAmendmentImpact(null);
      });
      return () => controller.abort();
    }
  }, [dealId, state, viewedVersion, versionView]);

  async function withdrawCurrentAmendment() {
    const agreement = getActiveAgreement();
    if (!agreement || state.status !== "ready" || pendingDecision || !actingOrganizationId || stale || compareBefore) return;
    if (agreement.version_number <= 1 || agreement.status !== "PENDING_APPROVAL") return;
    const atStart = context.current;
    setPendingDecision("withdraw");
    setDecisionError("");
    try {
      await withdrawAmendment(
        dealId,
        agreement.version_number,
        agreement.terms_hash,
        actingOrganizationId || undefined,
      );
      if (!active.current || atStart !== context.current) return;
      reloadAgreement();
    } catch (error) {
      if (!active.current || atStart !== context.current) return;
      setDecisionError(apiMessage(error));
    } finally {
      if (active.current && atStart === context.current) setPendingDecision(null);
    }
  }

  async function handleSubmitAmendment(committedAgreement: AgreementVersion) {
    if (!actingOrganizationId || !amendmentRationale.trim()) return;
    setSubmittingAmendment(true);
    setAmendmentError("");
    try {
      const terms = committedAgreement.terms;
      const request: ProposeAmendmentRequest = {
        schema_version: terms.schema_version,
        prior_version_number: committedAgreement.version_number,
        prior_terms_hash: committedAgreement.terms_hash,
        rationale: amendmentRationale.trim(),
        organization_id: actingOrganizationId,
        line_items: terms.line_items,
        shipments: terms.shipments,
        payment_terms: terms.payment_terms,
        delivery_location: terms.delivery_location,
        incoterm: terms.incoterm,
        cancellation_terms: terms.cancellation_terms,
      };
      if (terms.schema_version === 1) {
        request.description = terms.line_items[0]?.description;
        request.quantity = terms.line_items[0]?.quantity;
        request.unit = terms.line_items[0]?.unit;
        request.unit_price = terms.line_items[0]?.unit_price.amount;
        request.currency = terms.line_items[0]?.unit_price.currency as "USD";
        request.delivery_destination = terms.shipments[0]?.destination;
        request.delivery_date = terms.shipments[0]?.target_date ?? null;
        request.payment_trigger = terms.payment_terms[0]?.trigger as PaymentTrigger;
      }
      await proposeAmendment(dealId, request);
      setShowProposeAmendment(false);
      setAmendmentRationale("");
      setProposedImpact(null);
      reloadAgreement();
    } catch (error) {
      setAmendmentError(apiMessage(error));
    } finally {
      setSubmittingAmendment(false);
    }
  }

  async function handlePreviewProposedImpact(committedAgreement: AgreementVersion) {
    if (!actingOrganizationId) return;
    setPreviewingImpact(true);
    setAmendmentError("");
    try {
      const terms = committedAgreement.terms;
      const impact = await previewAmendmentImpact(dealId, {
        schema_version: terms.schema_version,
        organization_id: actingOrganizationId,
        line_items: terms.line_items,
        shipments: terms.shipments,
        payment_terms: terms.payment_terms,
        delivery_location: terms.delivery_location,
        incoterm: terms.incoterm,
        cancellation_terms: terms.cancellation_terms,
      });
      setProposedImpact(impact);
    } catch (error) {
      setAmendmentError(apiMessage(error));
    } finally {
      setPreviewingImpact(false);
    }
  }

  function reloadAgreement() {
    onOverviewChange?.({ dealId, organizationId: actingOrganizationId || "", reloadToken, status: "loading" });
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
          <p className="muted">
            Review this saved version, then each organization records its own decision. AI suggestions,
            extracted facts, and accepted proposals do not approve it. Both organizations must approve
            this same version before an authorized member can commit it as the agreed deal.
          </p>
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
              Version {version.version_number} · {agreementStatusLabel(version.status)}
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
        const isPendingCandidate = agreement.status === "PENDING_APPROVAL";
        const readConflict = currentView && (Boolean(currentView.error) || (!viewedVersion && currentView.agreement?.is_current === false)
          || (Boolean(currentView.agreement) && currentView.agreement?.terms_hash !== agreement.terms_hash));
        const canDecide = isPendingCandidate && !compareBefore && !readConflict;
        const pendingCandidate = currentHistory?.versions.find(
          (v) => v.status === "PENDING_APPROVAL" && v.version_number > 1,
        );
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
            {viewedVersion && !isPendingCandidate ? <p role="status">Historical version · Read-only</p> : null}
            {agreement.status === "COMMITTED" && pendingCandidate ? (
              <div role="status" className="agreement-review__pending-notice" style={{ margin: "1rem 0", padding: "0.75rem", background: "#eff6ff", border: "1px solid #93c5fd", borderRadius: "4px" }}>
                <p style={{ margin: "0 0 0.5rem 0" }}>An amendment (Version {pendingCandidate.version_number}) is awaiting approval.</p>
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => setViewedVersion(pendingCandidate.version_number)}
                >
                  Review pending amendment (Version {pendingCandidate.version_number})
                </button>
              </div>
            ) : null}
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
            {agreement.version_number > 1 ? (
              <div className="agreement-review__lineage" role="region" aria-label="Amendment lineage" style={{ marginBottom: "1rem" }}>
                <span className="badge badge--kind">
                  Amends version {agreement.version_number - 1}
                </span>
                {agreement.prior_terms_hash ? (
                  <span className="muted" style={{ marginLeft: "0.5rem" }}>
                    Prior hash: <code>{agreement.prior_terms_hash.slice(0, 12)}…</code>
                  </span>
                ) : null}
                {agreement.amendment_rationale ? (
                  <p className="agreement-review__rationale" style={{ marginTop: "0.5rem" }}>
                    <strong>Rationale:</strong> {agreement.amendment_rationale}
                  </p>
                ) : null}
              </div>
            ) : null}
            <div className="agreement-review__summary">
              <div>
                <span className="fact-source__label">VERSION STATUS</span>
                <strong>{agreementStatusLabel(agreement.status)}</strong>
              </div>
              <div>
                <span className="fact-source__label">SAVED</span>
                <time dateTime={agreement.created_at}>
                  {new Date(agreement.created_at).toLocaleString()}
                </time>
              </div>
            </div>

            <details className="agreement-review__technical-details">
              <summary>Technical verification details</summary>
              <p>These values identify the exact saved terms and recorded decisions.</p>
              <p>Version {agreement.version_number} terms hash</p>
              <code className="agreement-review__hash">{agreement.terms_hash}</code>
              {agreement.approvals.length > 0 ? <ul>
                {agreement.approvals.map((approval) => <li key={`${approval.organization_id}:${approval.user_id}`}>
                  {partyName(state.organizations, approval.organization_id)} · version {approval.version_number} · actor {approval.user_id} · {approval.decision} · {approval.terms_hash}
                </li>)}
              </ul> : <p>No party decisions have been recorded for this version.</p>}
            </details>

            {amendmentImpact?.blockers && amendmentImpact.blockers.length > 0 ? (
              <div role="alert" className="agreement-review__impact-blocker" style={{ margin: "1rem 0", padding: "1rem", background: "#fef2f2", border: "1px solid #f87171", borderRadius: "4px" }}>
                <h4>Amendment Policy Blockers</h4>
                <ul>
                  {amendmentImpact.blockers.map((blocker, idx) => (
                    <li key={idx}>{blocker}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {amendmentImpact ? (
              <div className="agreement-review__impact" aria-label="Operational impact preview">
                <h3>Operational impact preview</h3>
                {amendmentImpact.fulfillment_impact.length > 0 ? (
                  <div className="impact-group">
                    <h4>Fulfillment impact</h4>
                    {amendmentImpact.fulfillment_impact.map((f, idx) => (
                      <p key={idx}>
                        {f.obligation_reference}: planned {f.planned_quantity} {f.unit} (shipped: {f.shipped_quantity}, confirmed: {f.confirmed_quantity}) · <strong>{f.status}</strong>
                      </p>
                    ))}
                  </div>
                ) : null}
                {amendmentImpact.payment_impact.length > 0 ? (
                  <div className="impact-group">
                    <h4>Payment milestone impact</h4>
                    {amendmentImpact.payment_impact.map((p, idx) => (
                      <p key={idx}>
                        {p.milestone_reference}: {p.amount} {p.currency} (status: {p.payment_status}) · <strong>{p.status}</strong>
                      </p>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}

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

            {agreement.status === "COMMITTED" && !pendingCandidate && actingOrganizationId ? (
              <div className="agreement-review__amendment-propose" style={{ margin: "1.5rem 0" }}>
                {!showProposeAmendment ? (
                  <button
                    type="button"
                    className="button secondary"
                    onClick={() => {
                      setShowProposeAmendment(true);
                      setProposedImpact(null);
                      setAmendmentError("");
                    }}
                  >
                    Propose amendment
                  </button>
                ) : (
                  <div className="card" style={{ padding: "1rem", background: "#f8fafc", border: "1px solid #e2e8f0" }}>
                    <h3>Propose terms amendment</h3>
                    <p className="hint">
                      Proposing an amendment creates a new version against this committed version. Both organizations must approve it before it can be committed.
                    </p>
                    <div className="field">
                      <label htmlFor={`amendment-rationale-${dealId}`}>Amendment rationale (required)</label>
                      <textarea
                        id={`amendment-rationale-${dealId}`}
                        rows={3}
                        value={amendmentRationale}
                        placeholder="Explain the operational or commercial rationale for this amendment..."
                        onChange={(e) => setAmendmentRationale(e.target.value)}
                      />
                    </div>

                    {amendmentError ? (
                      <p role="alert" className="form-error">{amendmentError}</p>
                    ) : null}

                    {proposedImpact ? (
                      <div className="agreement-review__impact" aria-label="Proposed operational impact preview" style={{ margin: "1rem 0" }}>
                        <h4>Operational impact preview</h4>
                        {proposedImpact.blockers.length > 0 ? (
                          <div role="alert" className="form-error">
                            <strong>Policy blockers:</strong>
                            <ul>
                              {proposedImpact.blockers.map((b, idx) => (
                                <li key={idx}>{b}</li>
                              ))}
                            </ul>
                          </div>
                        ) : null}
                        {proposedImpact.fulfillment_impact.map((f, idx) => (
                          <p key={idx}>
                            {f.obligation_reference}: planned {f.planned_quantity} {f.unit} · {f.status}
                          </p>
                        ))}
                        {proposedImpact.payment_impact.map((p, idx) => (
                          <p key={idx}>
                            {p.milestone_reference}: {p.amount} {p.currency} · {p.status}
                          </p>
                        ))}
                      </div>
                    ) : null}

                    <div className="fact-actions" style={{ marginTop: "1rem" }}>
                      <button
                        type="button"
                        className="button secondary"
                        disabled={previewingImpact || submittingAmendment}
                        onClick={() => void handlePreviewProposedImpact(agreement)}
                      >
                        {previewingImpact ? "Previewing impact…" : "Preview operational impact"}
                      </button>
                      <button
                        type="button"
                        className="button"
                        disabled={submittingAmendment || !amendmentRationale.trim()}
                        onClick={() => void handleSubmitAmendment(agreement)}
                      >
                        {submittingAmendment ? "Submitting amendment…" : "Submit amendment proposal"}
                      </button>
                      <button
                        type="button"
                        className="button secondary"
                        disabled={submittingAmendment}
                        onClick={() => {
                          setShowProposeAmendment(false);
                          setAmendmentError("");
                        }}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
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
                  Both organizations review and decide on these saved terms before the agreement can be committed.
                </p>
              </div>
            ) : null}

            <div className="agreement-terms" aria-label={`Agreement version ${agreement.version_number} terms`}>
              <h3>Trade terms</h3>
              {agreement.terms.line_items.map((item, index) => (
                <dl className="agreement-terms__item" key={item.id ?? `${item.description}-${index}`}>
                  {item.id ? <div><dt>Item ID</dt><dd>{item.id}</dd></div> : null}
                  <div><dt>Item</dt><dd>{item.description}</dd></div>
                  <div><dt>Quantity</dt><dd>{item.quantity} {item.unit}</dd></div>
                  {item.sku ? <div><dt>SKU</dt><dd>{item.sku}</dd></div> : null}
                  <div><dt>Unit price</dt><dd>{item.unit_price.amount} {item.unit_price.currency}</dd></div>
                </dl>
              ))}
              {agreement.terms.shipments.map((shipment, index) => (
                <dl className="agreement-terms__item" key={shipment.id ?? `${shipment.destination}-${index}`}>
                  {shipment.id ? <div><dt>Shipment ID</dt><dd>{shipment.id}</dd></div> : null}
                  <div><dt>Delivery location</dt><dd>{shipment.destination}</dd></div>
                  <div><dt>Delivery quantity</dt><dd>{shipment.quantity ?? "Not specified"}</dd></div>
                  <div><dt>Target date</dt><dd>{shipment.target_date ?? "Not specified"}</dd></div>
                  {shipment.allocations && shipment.allocations.length > 0 ? (
                    <div>
                      <dt>Allocations</dt>
                      <dd>
                        {shipment.allocations.map((alloc, aIdx) => (
                          <span key={`${alloc.line_item_id}-${aIdx}`} className="allocation-tag" style={{ display: "block" }}>
                            {alloc.quantity} {alloc.unit} of item {alloc.line_item_id}
                          </span>
                        ))}
                      </dd>
                    </div>
                  ) : null}
                </dl>
              ))}
              {agreement.terms.payment_terms.map((term, index) => (
                <dl className="agreement-terms__item" key={term.id ?? `${term.trigger}-${index}`}>
                  {term.id ? <div><dt>Payment Term ID</dt><dd>{term.id}</dd></div> : null}
                  <div><dt>Payment amount</dt><dd>{term.amount.amount} {term.amount.currency}</dd></div>
                  <div><dt>Payment Timing (contract text)</dt><dd>{term.trigger.replaceAll("_", " ")}</dd></div>
                  <div><dt>Due Condition (contract text)</dt><dd>{term.due_condition}</dd></div>
                  {term.allocations && term.allocations.length > 0 ? (
                    <div>
                      <dt>Allocations</dt>
                      <dd>
                        {term.allocations.map((alloc, aIdx) => (
                          <span key={`${alloc.obligation_id}-${aIdx}`} className="allocation-tag" style={{ display: "block" }}>
                            {alloc.amount.amount} {alloc.amount.currency} for obligation {alloc.obligation_id}
                          </span>
                        ))}
                      </dd>
                    </div>
                  ) : null}
                </dl>
              ))}
              <dl className="agreement-terms__item">
                <div><dt>Delivery location</dt><dd>{agreement.terms.delivery_location}</dd></div>
                {agreement.terms.incoterm ? <div><dt>Incoterm</dt><dd>{agreement.terms.incoterm}</dd></div> : null}
                {agreement.terms.cancellation_terms ? <div><dt>Cancellation terms</dt><dd>{agreement.terms.cancellation_terms}</dd></div> : null}
                <div><dt>Unrecorded fields</dt><dd>Taxes, freight, customs classification, and other fees: Not specified in committed terms</dd></div>
              </dl>
            </div>

            <div className="agreement-review__approvals" aria-label="Approval status by organization">
              <h3>Decisions for version {agreement.version_number}</h3>
              {[buyerOrganizationId, sellerOrganizationId].map((organizationId) => {
                const approval = organizationId === buyerOrganizationId ? buyerApproval : sellerApproval;
                const matchesVersion = approvalMatchesVersion(approval, agreement);
                const displayedDecision = matchesVersion ? approval?.decision : undefined;
                return (
                  <div className="agreement-review__approval" key={organizationId}>
                    <span>{partyName(state.organizations, organizationId)}</span>
                    <span className={`badge ${displayedDecision === "APPROVE" ? "badge--status-confirmed" : displayedDecision === "REJECT" ? "badge--status-rejected" : "badge--status-extracted"}`}>
                      {approval && !matchesVersion ? "Needs review" : decisionLabel(displayedDecision)}
                    </span>
                    {approval ? <div><span>{matchesVersion ? "Decision recorded " : "Recorded decision is for different terms "}</span><time dateTime={approval.created_at}>{new Date(approval.created_at).toLocaleString()}</time></div> : null}
                  </div>
                );
              })}
            </div>

            {canDecide ? (
              <>
                {myApproval ? (
                  <p className="hint">{approvalMatchesVersion(myApproval, agreement)
                    ? `Your organization recorded a decision for version ${agreement.version_number}: ${decisionLabel(myApproval.decision).toLowerCase()}.`
                    : "Your organization's recorded decision is for different terms. Reload this agreement to review the current version."}</p>
                ) : null}
                <p className="hint">Your decision applies to agreement version {agreement.version_number}.</p>
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
                  {agreement.version_number > 1 ? (
                    <button
                      type="button"
                      className="button secondary"
                      disabled={stale || !actingOrganizationId || pendingDecision !== null}
                      onClick={() => void withdrawCurrentAmendment()}
                    >
                      {pendingDecision === "withdraw" ? "Withdrawing…" : "Withdraw amendment"}
                    </button>
                  ) : null}
                </div>
                {bothApproved ? (
                  <div className="agreement-review__commit">
                    <p className="agreement-review__notice">
                      Both organizations approved this exact version. Commit it to mark the deal agreed.
                    </p>
                    {amendmentImpact && !amendmentImpact.can_commit ? (
                      <p className="form-error">
                        Cannot commit amendment: unresolved policy blockers must be addressed.
                      </p>
                    ) : null}
                    <button
                      type="button"
                      className="button"
                      disabled={stale || !actingOrganizationId || pendingDecision !== null || (amendmentImpact !== null && !amendmentImpact.can_commit)}
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
