import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { AgreementApproval, AgreementVersion, Deal } from "../api/types";
import DealOverview from "./DealOverview";
import type { OverviewSnapshot } from "./DealOverview";

const deal: Deal = { id: "deal", buyer_organization_id: "buyer", seller_organization_id: "seller", status: "PENDING_APPROVALS", version: 1 };
const agreement = {
  deal_id: "deal", version_number: 2, terms_hash: "a".repeat(64), status: "PENDING_APPROVAL", is_current: true,
  approvals: [], terms: { line_items: [{ description: "Bolts", quantity: "5", unit: "boxes" }] },
} as unknown as AgreementVersion;
const approval = (organization_id: string, decision: "APPROVE" | "REJECT" = "APPROVE"): AgreementApproval => ({
  deal_id: "deal", version_number: 2, organization_id, user_id: "user", decision, terms_hash: "a".repeat(64), created_at: "2026-01-01",
});
const snapshot = (value: AgreementVersion): OverviewSnapshot => ({
  dealId: "deal", organizationId: "buyer", reloadToken: 0, status: "ready", partyVerified: true, agreement: value,
});

describe("DealOverview", () => {
  it("explains the manual invitation handoff without claiming an email was sent", () => {
    render(<DealOverview deal={{ ...deal, pending_counterparty: true }} organizationId="buyer" reloadToken={0} snapshot={null} />);
    expect(screen.getByText(/creating a link does not send an email/i)).toBeInTheDocument();
  });

  it("shows the current terms and decisions for the verified party", () => {
    const { rerender } = render(<DealOverview deal={deal} organizationId="buyer" reloadToken={0} snapshot={snapshot(agreement)} />);
    expect(screen.getByText("Current stage: Waiting for agreement decisions")).toBeInTheDocument();
    expect(screen.getByText("Bolts: 5 boxes")).toBeInTheDocument();
    expect(screen.getByText(/has not recorded a decision/i)).toBeInTheDocument();
    rerender(<DealOverview deal={deal} organizationId="buyer" reloadToken={0} snapshot={snapshot({ ...agreement, approvals: [approval("buyer")] })} />);
    expect(screen.getByText(/waiting for the other party's decision/i)).toBeInTheDocument();
    rerender(<DealOverview deal={deal} organizationId="buyer" reloadToken={0} snapshot={snapshot({ ...agreement, approvals: [approval("buyer"), approval("seller")] })} />);
    expect(screen.getByText(/still needs to be committed/i)).toBeInTheDocument();
    rerender(<DealOverview deal={deal} organizationId="buyer" reloadToken={0} snapshot={snapshot({ ...agreement, approvals: [approval("seller", "REJECT")] })} />);
    expect(screen.getByText(/has a rejection/i)).toBeInTheDocument();
  });

  it("does not treat mismatched decisions or stale snapshots as current", () => {
    const bad = { ...approval("buyer"), terms_hash: "b".repeat(64) };
    const { rerender } = render(<DealOverview deal={deal} organizationId="buyer" reloadToken={0} snapshot={snapshot({ ...agreement, approvals: [bad] })} />);
    expect(screen.getByText(/decisions could not be verified/i)).toBeInTheDocument();
    rerender(<DealOverview deal={deal} organizationId="seller" reloadToken={0} snapshot={snapshot(agreement)} />);
    expect(screen.getByText(/checking agreement status/i)).toBeInTheDocument();
    rerender(<DealOverview deal={deal} organizationId="buyer" reloadToken={1} snapshot={snapshot(agreement)} />);
    expect(screen.getByText(/checking agreement status/i)).toBeInTheDocument();
  });

  it("requires two exact approvals before describing a committed agreement", () => {
    render(<DealOverview deal={{ ...deal, status: "AGREED" }} organizationId="buyer" reloadToken={0} snapshot={snapshot({ ...agreement, status: "COMMITTED" })} />);
    expect(screen.getByText(/decisions could not be verified/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "View payment" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "View delivery" })).not.toBeInTheDocument();
  });

  it("does not show terms or agreement actions before a dual member chooses a party", () => {
    render(<DealOverview deal={deal} organizationId="" reloadToken={0} snapshot={{ ...snapshot(agreement), organizationId: "", partyVerified: false }} />);
    expect(screen.getByText(/choose a deal organization/i)).toBeInTheDocument();
    expect(screen.queryByText("Bolts: 5 boxes")).not.toBeInTheDocument();
    expect(screen.queryByText(/viewing as/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Review agreement" })).not.toBeInTheDocument();
  });

  it("keeps payment and delivery separate after commitment", () => {
    render(<DealOverview deal={{ ...deal, status: "AGREED" }} organizationId="buyer" reloadToken={0} snapshot={snapshot({
      ...agreement,
      status: "COMMITTED",
      approvals: [approval("buyer"), approval("seller")],
    })} />);
    expect(screen.getByText(/payment and delivery are tracked separately/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "View payment" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "View delivery" })).toBeInTheDocument();
  });

  it("does not invite term discussion when the deal stage says agreement should already exist", () => {
    render(<DealOverview deal={{ ...deal, status: "EXECUTING" }} organizationId="buyer" reloadToken={0}
      snapshot={{ ...snapshot(agreement), status: "empty" }} />);
    expect(screen.getByText(/current agreement could not be confirmed/i)).toBeInTheDocument();
  });
});
