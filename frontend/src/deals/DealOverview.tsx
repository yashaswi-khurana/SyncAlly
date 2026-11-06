import type { AgreementVersion, Deal } from "../api/types";

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

export default function DealOverview({ deal, organizationId, reloadToken, snapshot }: Props) {
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
  return <section className="card" aria-labelledby="deal-overview-heading">
    <h2 id="deal-overview-heading">Deal overview</h2>
    <p>Current stage: {DEAL_STAGE_LABELS[deal.status] ?? "Stage unavailable"}</p>
    {organizationId && current?.partyVerified ? <p>Viewing as {organizationId === deal.buyer_organization_id ? "buyer" : "seller"}.</p> : null}
    {agreementLink && current?.agreement && Array.isArray(current.agreement.terms?.line_items)
      ? <ul aria-label="Items in current agreement">{current.agreement.terms.line_items.map((item, index) =>
        <li key={index}>{item.description}: {item.quantity} {item.unit}</li>)}</ul> : null}
    <p>{message}</p>
    {agreementLink ? <button type="button" className="button secondary" onClick={() => scrollTo("agreement-review-heading")}>Review agreement</button> : null}
    {executionLinks ? <div className="actions">
      <button type="button" className="button secondary" onClick={() => scrollTo("payment-status-heading")}>View payment</button>
      <button type="button" className="button secondary" onClick={() => scrollTo("fulfillment-heading")}>View delivery</button>
    </div> : null}
  </section>;
}
