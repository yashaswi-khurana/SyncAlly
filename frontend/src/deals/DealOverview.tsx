import { useEffect, useRef } from "react";
import type { AgreementVersion, Deal, DealFact } from "../api/types";
import { initMotion } from "../ui/motion";
import { conversationTermMismatches, savedTermsFromTrade } from "./suggestionPreview";

export type OverviewSnapshot = {
  dealId: string;
  organizationId: string;
  reloadToken: number;
  status: "loading" | "empty" | "error" | "ready";
  partyVerified?: boolean;
  agreement?: AgreementVersion;
};

interface Props {
  deal: Deal;
  organizationId: string;
  reloadToken: number;
  snapshot: OverviewSnapshot | null;
  conversationFacts?: DealFact[];
  partyNames?: { buyer?: string; seller?: string };
  onRevealPanel?: (panel: "obligations" | "invoices") => void;
}

const PIPELINE_STAGES = [
  "Negotiation",
  "Term Verification",
  "Bilateral Approval",
  "Committed Trade",
  "Settlement",
] as const;

function stageIndex(status: string): number {
  if (["DRAFT", "NEGOTIATING"].includes(status)) return 0;
  if (status === "PENDING_APPROVALS") return 2;
  if (status === "AGREED") return 3;
  if (["EXECUTING", "COMPLETED"].includes(status)) return 4;
  return -1;
}

const DEAL_STAGE_LABELS: Record<string, string> = {
  DRAFT: "Draft",
  NEGOTIATING: "In discussion",
  PENDING_APPROVALS: "Waiting for agreement decisions",
  AGREED: "Agreement committed",
  EXECUTING: "Payment and delivery",
  COMPLETED: "Complete",
  CANCELLED: "Cancelled",
  EXPIRED: "Expired",
  DISPUTED: "Disputed",
};

function hasVerifiedCurrentAgreement(agreement: AgreementVersion, deal: Deal): boolean {
  if (agreement.deal_id !== deal.id || agreement.is_current === false || !/^[0-9a-f]{64}$/.test(agreement.terms_hash)) return false;
  if (!Array.isArray(agreement.terms?.line_items) || agreement.terms.line_items.some((item) =>
    !item || typeof item.description !== "string" || typeof item.quantity !== "string" || typeof item.unit !== "string"
  )) return false;
  if (!Array.isArray(agreement.approvals)) return false;
  const partyIds = new Set([deal.buyer_organization_id, deal.seller_organization_id]);
  const approvalOrganizations = new Set<string>();
  for (const approval of agreement.approvals) {
    if (
      approval.deal_id !== deal.id ||
      approval.version_number !== agreement.version_number ||
      approval.terms_hash !== agreement.terms_hash ||
      !partyIds.has(approval.organization_id) ||
      !["APPROVE", "REJECT"].includes(approval.decision) ||
      approvalOrganizations.has(approval.organization_id)
    ) return false;
    approvalOrganizations.add(approval.organization_id);
  }
  if (agreement.status === "COMMITTED") {
    return ["AGREED", "EXECUTING", "COMPLETED"].includes(deal.status) &&
      agreement.approvals.length === 2 && agreement.approvals.every((approval) => approval.decision === "APPROVE");
  }
  return agreement.status === "PENDING_APPROVAL" && deal.status === "PENDING_APPROVALS";
}

function nextRequiredAction(deal: Deal, organizationId: string): string {
  const refreshTip = " If the other party has acted since this page loaded, refresh before continuing.";
  if (["COMPLETED", "CANCELLED", "EXPIRED"].includes(deal.status)) return "No action is pending for this deal.";
  if (deal.pending_counterparty) return "Inviting party: share the invitation link manually and wait for the counterparty to join.";
  if (deal.status === "DISPUTED") return "Buyer and seller: review the open case and respond to any requested evidence.";
  if (!organizationId) return "Choose the buyer or seller organization above to see its next action.";
  const role = organizationId === deal.buyer_organization_id
    ? "Buyer"
    : organizationId === deal.seller_organization_id ? "Seller" : null;
  if (!role) return "Choose a buyer or seller organization that belongs to this deal.";
  if (["DRAFT", "NEGOTIATING"].includes(deal.status)) {
    return role === "Buyer"
      ? "Buyer: share your requirements, then review any incoming proposal and its available response actions in the conversation." + refreshTip
      : "Seller: share availability and pricing, then review any incoming proposal and its available response actions in the conversation." + refreshTip;
  }
  if (deal.status === "PENDING_APPROVALS") {
    return "Buyer and seller: refresh, then review the current agreement panel and use the approval or commit action it shows.";
  }
  if (["AGREED", "EXECUTING"].includes(deal.status)) {
    return role === "Seller"
      ? "Seller: review the agreement for amendments, check payment for outstanding invoice actions, and use delivery to report shipment when available." + refreshTip
      : "Buyer: review the agreement for amendments, follow the payment panel's current Sandbox or Offline Demo steps, and use delivery to record receipt when available." + refreshTip;
  }
  return "Refresh the deal to check its current stage and available actions.";
}

export default function DealOverview({ deal, organizationId, reloadToken, snapshot, conversationFacts = [], partyNames, onRevealPanel }: Props) {
  const rootRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const handle = initMotion(rootRef.current);
    return () => handle.destroy();
  }, []);
  const current = snapshot?.dealId === deal.id && snapshot.organizationId === organizationId &&
    snapshot.reloadToken === reloadToken ? snapshot : null;
  let message = "Checking agreement status…";
  let agreementLink = false;
  let executionLinks = false;

  if (deal.pending_counterparty) {
    message = "Waiting for your trading partner to join. Invitation links must be sent manually; creating a link does not send an email.";
  } else if (!current || current.status === "loading") {
    message = "Checking agreement status…";
  } else if (current.status === "error") {
    message = "Agreement status is unavailable. Refresh the deal to try again.";
  } else if (!organizationId || !current.partyVerified) {
    message = "Choose a deal organization to see its agreement decisions.";
  } else if (current.status === "empty") {
    if (["DRAFT", "NEGOTIATING"].includes(deal.status)) {
      message = "There is no current agreement. Discuss the terms and review the details before preparing one.";
    } else if (["CANCELLED", "EXPIRED", "COMPLETED"].includes(deal.status)) {
      message = `This deal is ${DEAL_STAGE_LABELS[deal.status]?.toLowerCase() ?? "closed"}. No current agreement is available.`;
    } else {
      message = "The deal stage suggests an agreement should be available, but the current agreement could not be confirmed. Refresh to check again.";
    }
  } else if (current.agreement) {
    const agreement = current.agreement;
    const approvals = agreement.approvals;
    const valid = hasVerifiedCurrentAgreement(agreement, deal);
    if (!valid) {
      message = "Agreement decisions could not be verified. Refresh and review the current agreement.";
    } else if (agreement.status === "COMMITTED") {
      message = `Agreement version ${agreement.version_number} is committed. Payment and delivery are tracked separately.`;
      agreementLink = true;
      executionLinks = true;
    } else if (agreement.status === "PENDING_APPROVAL") {
      agreementLink = true;
      const mine = approvals.find((approval) => approval.organization_id === organizationId);
      const otherId = organizationId === deal.buyer_organization_id ? deal.seller_organization_id : deal.buyer_organization_id;
      const other = approvals.find((approval) => approval.organization_id === otherId);
      if (approvals.some((approval) => approval.decision === "REJECT")) {
        message = `Agreement version ${agreement.version_number} has a rejection. Review the recorded decisions.`;
      } else if (mine?.decision === "APPROVE" && other?.decision === "APPROVE") {
        message = `Both parties approved agreement version ${agreement.version_number}. The agreement still needs to be committed.`;
      } else if (mine?.decision === "APPROVE") {
        message = `Your organization approved agreement version ${agreement.version_number}. Waiting for the other party's decision.`;
      } else {
        message = `Agreement version ${agreement.version_number} is ready to review. Your organization has not recorded a decision.`;
      }
    } else {
      message = "Review the agreement for its current status.";
    }
  }

  const scrollTo = (id: string) => document.getElementById(id)?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  const revealAndScroll = (panel: "obligations" | "invoices", id: string) => {
    onRevealPanel?.(panel);
    window.requestAnimationFrame(() => scrollTo(id));
  };

  let waiting: { text: string; side: "buyer" | "seller" | "neutral" } | null = null;
  if (
    current?.agreement && current.agreement.status === "PENDING_APPROVAL" &&
    deal.status === "PENDING_APPROVALS" && organizationId && current.partyVerified &&
    hasVerifiedCurrentAgreement(current.agreement, deal)
  ) {
    const approvals = current.agreement.approvals;
    const mine = approvals.find((approval) => approval.organization_id === organizationId);
    const otherId = organizationId === deal.buyer_organization_id ? deal.seller_organization_id : deal.buyer_organization_id;
    const other = approvals.find((approval) => approval.organization_id === otherId);
    const otherSide = otherId === deal.buyer_organization_id ? "buyer" : "seller";
    const otherLabel = otherSide === "buyer"
      ? partyNames?.buyer || "Buyer"
      : partyNames?.seller || "Seller";
    if (approvals.some((approval) => approval.decision === "REJECT")) {
      waiting = null;
    } else if (mine?.decision !== "APPROVE") {
      waiting = {
        text: "your approval",
        side: organizationId === deal.buyer_organization_id ? "buyer" : "seller",
      };
    } else if (other?.decision !== "APPROVE") {
      waiting = { text: `${otherLabel} approval`, side: otherSide };
    } else {
      waiting = { text: "commitment by either authorized member", side: "neutral" };
    }
  }

  const activeStage = stageIndex(deal.status);
  const termMismatches = current?.agreement
    ? conversationTermMismatches(conversationFacts, savedTermsFromTrade(current.agreement.terms ?? {}))
    : [];
  return <section ref={rootRef} className="card" aria-labelledby="deal-overview-heading">
    <h2 id="deal-overview-heading">Deal overview</h2>
    <ol className="stage-stepper" aria-label="Trade pipeline stages">
      {PIPELINE_STAGES.map((stage, index) => {
        const state = activeStage < 0 ? "halted" : index < activeStage ? "done" : index === activeStage ? "active" : "todo";
        return (
          <li
            key={stage}
            className={`stage-stepper__item stage-stepper__item--${state}`}
            aria-current={state === "active" ? "step" : undefined}
          >
            <span className="stage-stepper__marker" aria-hidden="true" />
            <span className="stage-stepper__label">{stage}</span>
          </li>
        );
      })}
    </ol>
    <p>Current stage: {DEAL_STAGE_LABELS[deal.status] ?? "Stage unavailable"}</p>
    {waiting ? (
      <p className={`stage-waiting stage-waiting--${waiting.side}`}>
        <strong>Waiting on:</strong> {waiting.text}
      </p>
    ) : null}
    <p><strong>Next action:</strong> {nextRequiredAction(deal, organizationId)}</p>
    {organizationId && current?.partyVerified ? <p>Viewing as {organizationId === deal.buyer_organization_id ? "buyer" : "seller"}.</p> : null}
    {agreementLink && current?.agreement && Array.isArray(current.agreement.terms?.line_items)
      ? <ul aria-label="Items in current agreement">{current.agreement.terms.line_items.map((item, index) =>
        <li key={index}>{item.description}: {item.quantity} {item.unit}</li>)}</ul> : null}
    {termMismatches.length > 0 ? (
      <aside className="term-mismatch" role="alert">
        <strong>Conversation does not match this agreement</strong>
        <p>
          Chat and extracted facts discuss {termMismatches[0].conversation}.
          The saved terms are {termMismatches[0].saved}. Review the messages before treating this as one deal.
        </p>
        <ul>
          {termMismatches.map((mismatch) => (
            <li key={mismatch.field}>
              {mismatch.label}: {mismatch.conversation} vs {mismatch.saved}
            </li>
          ))}
        </ul>
      </aside>
    ) : null}
    <p>{message}</p>
    {message === "Checking agreement status…" ? (
      <div className="skeleton-stack" aria-hidden="true">
        <span className="skeleton-bar skeleton-bar--mid" />
        <span className="skeleton-bar skeleton-bar--short" />
      </div>
    ) : null}
    {agreementLink ? <button type="button" className="button secondary" onClick={() => scrollTo("agreement-review-heading")}>Review agreement</button> : null}
    {executionLinks ? <div className="actions">
      <button type="button" className="button secondary" onClick={() => revealAndScroll("invoices", "payment-status-heading")}>View payment</button>
      <button type="button" className="button secondary" onClick={() => revealAndScroll("obligations", "fulfillment-heading")}>View delivery</button>
    </div> : null}
  </section>;
}
