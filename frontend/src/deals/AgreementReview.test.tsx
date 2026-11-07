import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  commitAgreementVersion,
  getCurrentAgreement,
  getAgreementHistory,
  getAgreementVersion,
  compareAgreementVersions,
  getAmendmentImpact,
  listOrganizations,
  recordAgreementDecision,
  getTradePack,
  withdrawAmendment,
  proposeAmendment,
  previewAmendmentImpact,
} from "../api/client";
import type { AgreementVersion, Organization } from "../api/types";
import { clearAccessToken, setAccessToken } from "../api/tokenStore";
import AgreementReview from "./AgreementReview";

function fakeJwt(sub: string): string {
  const payload = btoa(JSON.stringify({ sub })).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
  return `header.${payload}.sig`;
}

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    commitAgreementVersion: vi.fn(),
    getCurrentAgreement: vi.fn(),
    getAgreementHistory: vi.fn(),
    getAgreementVersion: vi.fn(),
    compareAgreementVersions: vi.fn(),
    getAmendmentImpact: vi.fn(),
    listOrganizations: vi.fn(),
    recordAgreementDecision: vi.fn(),
    getTradePack: vi.fn(),
    withdrawAmendment: vi.fn(),
    proposeAmendment: vi.fn(),
    previewAmendmentImpact: vi.fn(),
  };
});

const DEAL_ID = "deal-1";
const BUYER_ID = "buyer-org";
const SELLER_ID = "seller-org";
const BUYER: Organization = {
  id: BUYER_ID,
  legal_name: "Buyer Co",
  country_code: "US",
  role: "ADMIN",
};
const SELLER: Organization = {
  id: SELLER_ID,
  legal_name: "Seller Co",
  country_code: "CA",
  role: "MEMBER",
};

const AGREEMENT: AgreementVersion = {
  deal_id: DEAL_ID,
  version_number: 3,
  terms_hash: "a".repeat(64),
  status: "PENDING_APPROVAL",
  terms: {
    schema_version: 1,
    buyer_id: BUYER_ID,
    seller_id: SELLER_ID,
    line_items: [
      {
        description: "Desk",
        sku: null,
        quantity: "10",
        unit: "pieces",
        unit_price: { amount: "25.00", currency: "USD" },
      },
    ],
    shipments: [{ quantity: "10", destination: "Toronto", target_date: "2026-12-01" }],
    payment_terms: [
      {
        amount: { amount: "250.00", currency: "USD" },
        trigger: "seller_invoice",
        due_condition: "when seller invoices",
      },
    ],
    delivery_location: "Toronto",
    incoterm: null,
    cancellation_terms: "",
  },
  created_at: "2026-10-19T10:00:00Z",
  committed_at: null,
  approvals: [],
};

const mockedGetCurrent = vi.mocked(getCurrentAgreement);
const mockedCommitAgreement = vi.mocked(commitAgreementVersion);
const mockedListOrganizations = vi.mocked(listOrganizations);
const mockedRecordDecision = vi.mocked(recordAgreementDecision);
const mockedWithdrawAmendment = vi.mocked(withdrawAmendment);
const mockedGetAmendmentImpact = vi.mocked(getAmendmentImpact);
const mockedProposeAmendment = vi.mocked(proposeAmendment);
const mockedPreviewAmendmentImpact = vi.mocked(previewAmendmentImpact);

function renderReview() {
  return render(
    <AgreementReview
      dealId={DEAL_ID}
      buyerOrganizationId={BUYER_ID}
      sellerOrganizationId={SELLER_ID}
    />,
  );
}

describe("AgreementReview", () => {
  beforeEach(() => {
    vi.mocked(getAgreementHistory).mockResolvedValue({ deal_id: DEAL_ID, organization_id: BUYER_ID, current_version_id: "current", versions: [AGREEMENT, { ...AGREEMENT, id: "old", version_number: 2, status: "SUPERSEDED" }] });
    vi.mocked(getAgreementVersion).mockImplementation(async (_deal, number) => ({
      ...AGREEMENT,
      id: number === 2 ? "old" : "current",
      version_number: number,
      terms_hash: number === 4 ? "b".repeat(64) : AGREEMENT.terms_hash,
      status: number === 2 ? "SUPERSEDED" : "PENDING_APPROVAL",
    }));
    vi.mocked(compareAgreementVersions).mockResolvedValue({ before: { ...AGREEMENT, version_number: 2 }, after: AGREEMENT, changes: { fields: [], collections: {} } });
    mockedGetAmendmentImpact.mockResolvedValue({
      prior_version_number: 1,
      prior_terms_hash: "0".repeat(64),
      proposed_version_number: 3,
      proposed_terms_hash: AGREEMENT.terms_hash,
      diff: { fields: [], collections: {} },
      fulfillment_impact: [],
      payment_impact: [],
      active_cases: [],
      blockers: [],
      can_commit: true,
    });
    mockedWithdrawAmendment.mockResolvedValue({
      ...AGREEMENT,
      status: "VOIDED",
    });
    mockedGetCurrent.mockResolvedValue(AGREEMENT);
    mockedListOrganizations.mockResolvedValue([BUYER]);
    mockedRecordDecision.mockResolvedValue({
      deal_id: DEAL_ID,
      version_number: AGREEMENT.version_number,
      organization_id: BUYER_ID,
      user_id: "buyer-user",
      decision: "APPROVE",
      terms_hash: AGREEMENT.terms_hash,
      created_at: "2026-10-19T10:01:00Z",
    });
    mockedCommitAgreement.mockResolvedValue({
      ...AGREEMENT,
      status: "COMMITTED",
      committed_at: "2026-10-19T10:02:00Z",
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
    clearAccessToken();
  });

  it("downloads the displayed historical committed snapshot and returns to the exact current one", async () => {
    const current = { ...AGREEMENT, id: "current", status: "COMMITTED" as const };
    const old = { ...current, id: "old", version_number: 2, terms_hash: "b".repeat(64) };
    mockedGetCurrent.mockResolvedValue(current);
    vi.mocked(getAgreementHistory).mockResolvedValue({ deal_id: DEAL_ID, organization_id: BUYER_ID,
      current_version_id: "current", versions: [current, old] });
    vi.mocked(getAgreementVersion).mockImplementation(async (_deal, number) => number === 2 ? old : current);
    vi.mocked(getTradePack).mockRejectedValue(new ApiError(413, "Test export too large"));
    renderReview();
    fireEvent.click(await screen.findByRole("button", { name: "Download trade pack" }));
    await screen.findByText("Test export too large");
    expect(getTradePack).toHaveBeenLastCalledWith(DEAL_ID, current, BUYER_ID, "zip", expect.any(AbortSignal));
    fireEvent.change(screen.getByLabelText("Agreement version"), { target: { value: "2" } });
    expect(screen.queryByRole("button", { name: "Download trade pack" })).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Download trade pack" }));
    expect(getTradePack).toHaveBeenLastCalledWith(DEAL_ID, old, BUYER_ID, "zip", expect.any(AbortSignal));
    expect(screen.queryByRole("button", { name: "Approve this version" })).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Agreement version"), { target: { value: "0" } });
    fireEvent.click(await screen.findByRole("button", { name: "Download trade pack" }));
    expect(getTradePack).toHaveBeenLastCalledWith(DEAL_ID, current, BUYER_ID, "zip", expect.any(AbortSignal));
  });

  it("hides exports when exact current identity disagrees or remains unavailable", async () => {
    mockedGetCurrent.mockResolvedValue({ ...AGREEMENT, id: "current", status: "COMMITTED" });
    vi.mocked(getAgreementVersion).mockResolvedValue({ ...AGREEMENT, id: "other", status: "COMMITTED" });
    renderReview();
    await waitFor(() => expect(getAgreementVersion).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: "Download trade pack" })).not.toBeInTheDocument();
  });

  it("loads exact historical versions read-only and clears evidence immediately on selection", async () => {
    vi.mocked(getAgreementVersion).mockResolvedValueOnce({ ...AGREEMENT, id: "current", evidence: [{ state: "AVAILABLE", grounding: "UNMAPPED", trace_enabled: true, agreement_version_id: "current", terms_hash: AGREEMENT.terms_hash, organization_id: BUYER_ID, source_span: "Frozen quote" }] });
    renderReview();
    expect(await screen.findByText("Frozen quote")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Agreement version"), { target: { value: "2" } });
    expect(screen.queryByText("Frozen quote")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve this version" })).not.toBeInTheDocument();
    expect(await screen.findByText(/Historical version/)).toBeInTheDocument();
    expect(getAgreementVersion).toHaveBeenCalledWith(DEAL_ID, 2, BUYER_ID, expect.any(AbortSignal));
    expect(recordAgreementDecision).not.toHaveBeenCalled();
  });

  it("compares selected versions without enabling approval commands", async () => {
    renderReview();
    await screen.findByLabelText("Compare before");
    fireEvent.change(screen.getByLabelText("Compare before"), { target: { value: "2" } });
    expect(await screen.findByLabelText("Structured agreement comparison")).toBeInTheDocument();
    expect(compareAgreementVersions).toHaveBeenCalledWith(DEAL_ID, 2, 3, BUYER_ID, expect.any(AbortSignal));
    expect(screen.queryByRole("button", { name: "Approve this version" })).not.toBeInTheDocument();
  });

  it("retains historical access after the current candidate has been removed", async () => {
    mockedGetCurrent.mockRejectedValue(new ApiError(404, "No current agreement"));
    vi.mocked(getAgreementHistory).mockResolvedValue({ deal_id: DEAL_ID, organization_id: BUYER_ID, current_version_id: null,
      versions: [{ ...AGREEMENT, id: "old", version_number: 2, status: "VOIDED" }] });
    renderReview();
    expect(await screen.findByText(/Historical version/)).toBeInTheDocument();
    expect(screen.getByLabelText("Agreement version")).toHaveValue("2");
    expect(screen.queryByRole("button", { name: "Approve this version" })).not.toBeInTheDocument();
  });

  it("blocks commands and old source quotes when the exact read hash changed", async () => {
    vi.mocked(getAgreementVersion).mockResolvedValue({ ...AGREEMENT, terms_hash: "b".repeat(64) });
    renderReview();
    expect(await screen.findByText("The agreement changed or is unavailable.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve this version" })).not.toBeInTheDocument();
    expect(mockedRecordDecision).not.toHaveBeenCalled();
  });

  it("aborts old version reads and ignores late evidence on party change", async () => {
    let resolveOld!: (agreement: AgreementVersion) => void;
    vi.mocked(getAgreementVersion).mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve; }));
    const props = { dealId: DEAL_ID, buyerOrganizationId: BUYER_ID, sellerOrganizationId: SELLER_ID };
    const view = render(<AgreementReview {...props} selectedOrganizationId={BUYER_ID} />);
    await waitFor(() => expect(getAgreementVersion).toHaveBeenCalled());
    const signal = vi.mocked(getAgreementVersion).mock.calls[0][3]!;
    view.rerender(<AgreementReview {...props} selectedOrganizationId={SELLER_ID} />);
    expect(signal.aborted).toBe(true);
    resolveOld({ ...AGREEMENT, id: "current", evidence: [{ trace_enabled: true, state: "AVAILABLE", grounding: "UNMAPPED",
      organization_id: BUYER_ID, agreement_version_id: "current", terms_hash: AGREEMENT.terms_hash, source_span: "Late private quote" }] });
    await screen.findByText("VERSION 3");
    expect(screen.queryByText("Late private quote")).not.toBeInTheDocument();
  });

  it("shows saved terms and submits the exact displayed version and hash", async () => {
    const approvedAgreement: AgreementVersion = {
      ...AGREEMENT,
      approvals: [
        {
          deal_id: DEAL_ID,
          version_number: AGREEMENT.version_number,
          organization_id: BUYER_ID,
          user_id: "buyer-user",
          decision: "APPROVE",
          terms_hash: AGREEMENT.terms_hash,
          created_at: "2026-10-19T10:01:00Z",
        },
      ],
    };
    mockedGetCurrent.mockResolvedValueOnce(AGREEMENT).mockResolvedValueOnce(approvedAgreement);

    renderReview();

    expect(await screen.findByText("VERSION 3")).toBeInTheDocument();
    expect(screen.getByText("Desk")).toBeInTheDocument();
    expect(screen.getAllByText("Toronto")).toHaveLength(2);
    expect(screen.getByText(AGREEMENT.terms_hash)).toBeInTheDocument();
    // Reviewers must read the exact condition the agreement stores and hashes,
    // never a stronger paraphrase of it.
    const paymentTiming = screen.getByLabelText("Payment timing summary");
    expect(paymentTiming).toHaveTextContent("Upon Seller Invoice");
    expect(paymentTiming).toHaveTextContent("when seller invoices");
    expect(paymentTiming).not.toHaveTextContent(/immediately/i);
    expect(screen.queryByRole("button", { name: "Commit approved agreement" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Approve this version" }));

    await waitFor(() =>
      expect(mockedRecordDecision).toHaveBeenCalledWith(
        DEAL_ID,
        3,
        AGREEMENT.terms_hash,
        "approve",
        BUYER_ID,
      ),
    );
    expect(await screen.findByText("Approved")).toBeInTheDocument();
    expect(mockedGetCurrent).toHaveBeenCalledTimes(2);
  });

  it("asks the user to reload after a stale decision and then shows the new version", async () => {
    mockedGetCurrent
      .mockResolvedValueOnce(AGREEMENT)
      .mockResolvedValueOnce({ ...AGREEMENT, version_number: 4, terms_hash: "b".repeat(64) });
    mockedRecordDecision.mockRejectedValue(
      new ApiError(409, "The displayed agreement terms are no longer current; reload before continuing"),
    );

    renderReview();
    await screen.findByText("VERSION 3");
    fireEvent.click(screen.getByRole("button", { name: "Approve this version" }));

    expect(await screen.findByText(/agreement changed|decision conflicts/i)).toBeInTheDocument();
    expect(mockedGetCurrent).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Approve this version" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Reject this version" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Reload and review current version" }));
    expect(await screen.findByText("VERSION 4")).toBeInTheDocument();
    expect(mockedGetCurrent).toHaveBeenCalledTimes(2);
  });

  it("keeps committed terms read-only and hides decision controls", async () => {
    mockedGetCurrent.mockResolvedValue({
      ...AGREEMENT,
      status: "COMMITTED",
      committed_at: "2026-10-19T10:02:00Z",
    });

    renderReview();

    expect(await screen.findByText(/committed. its terms are read-only/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve this version" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reject this version" })).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("offers commit only after both parties approve the exact saved version", async () => {
    const onCommitted = vi.fn();
    const approvals = [BUYER_ID, SELLER_ID].map((organizationId) => ({
      deal_id: DEAL_ID,
      version_number: AGREEMENT.version_number,
      organization_id: organizationId,
      user_id: `${organizationId}-user`,
      decision: "APPROVE" as const,
      terms_hash: AGREEMENT.terms_hash,
      created_at: "2026-10-19T10:01:00Z",
    }));
    mockedGetCurrent
      .mockResolvedValueOnce({ ...AGREEMENT, approvals })
      .mockResolvedValueOnce({
        ...AGREEMENT,
        approvals,
        status: "COMMITTED",
        committed_at: "2026-10-19T10:02:00Z",
      });

    render(
      <AgreementReview
        dealId={DEAL_ID}
        buyerOrganizationId={BUYER_ID}
        sellerOrganizationId={SELLER_ID}
        onCommitted={onCommitted}
      />,
    );
    await screen.findByText("VERSION 3");
    fireEvent.click(screen.getByRole("button", { name: "Commit approved agreement" }));

    await waitFor(() =>
      expect(mockedCommitAgreement).toHaveBeenCalledWith(
        DEAL_ID,
        AGREEMENT.version_number,
        AGREEMENT.terms_hash,
        BUYER_ID,
      ),
    );
    expect(await screen.findByText(/committed\. its terms are read-only/i)).toBeInTheDocument();
    expect(onCommitted).toHaveBeenCalledTimes(1);
  });

  it("lets a routed approver cast a fresh vote even when the org's aggregate decision is already recorded", async () => {
    setAccessToken(fakeJwt("me-1"));
    const routedAgreement: AgreementVersion = {
      ...AGREEMENT,
      approvals: [
        {
          deal_id: DEAL_ID,
          version_number: AGREEMENT.version_number,
          organization_id: BUYER_ID,
          user_id: "other-buyer-admin",
          decision: "APPROVE",
          terms_hash: AGREEMENT.terms_hash,
          created_at: "2026-10-19T10:01:00Z",
        },
      ],
      routing_status: {
        [BUYER_ID]: {
          organization_id: BUYER_ID,
          mode: "PARALLEL",
          policy_version: 1,
          status: "REQUIRED",
          required_approvers: 2,
          completed_approvers: 0,
          slots: [
            { user_id: "me-1", status: "REQUIRED", decision: null, stale: false },
            { user_id: "other-buyer-admin", status: "REQUIRED", decision: null, stale: false },
          ],
        },
      },
    };
    mockedGetCurrent.mockResolvedValue(routedAgreement);

    render(
      <AgreementReview
        dealId={DEAL_ID}
        buyerOrganizationId={BUYER_ID}
        sellerOrganizationId={SELLER_ID}
        selectedOrganizationId={BUYER_ID}
      />,
    );

    await screen.findByText("VERSION 3");
    expect(screen.getByRole("button", { name: "Approve this version" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Reject this version" })).toBeEnabled();
  });

  it("shows an actionable error when approval cannot be saved", async () => {
    mockedRecordDecision.mockRejectedValue(new ApiError(500, "Server unavailable"));

    renderReview();
    await screen.findByText("VERSION 3");
    fireEvent.click(screen.getByRole("button", { name: "Approve this version" }));

    expect(await screen.findByText("Server unavailable")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve this version" })).toBeEnabled();
  });

  it("asks a user with access to both parties to choose one side", async () => {
    mockedListOrganizations.mockResolvedValue([BUYER, SELLER]);

    renderReview();

    await screen.findByText("VERSION 3");
    expect(screen.getByLabelText("Approve as organization")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve this version" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Approve as organization"), {
      target: { value: SELLER_ID },
    });
    fireEvent.click(screen.getByRole("button", { name: "Reject this version" }));

    await waitFor(() =>
      expect(mockedRecordDecision).toHaveBeenCalledWith(
        DEAL_ID,
        3,
        AGREEMENT.terms_hash,
        "reject",
        SELLER_ID,
      ),
    );
  });

  it("renders schema 2 collection terms with stable IDs, allocations, and unrecorded disclaimer", async () => {
    const schema2Agreement: AgreementVersion = {
      deal_id: DEAL_ID,
      version_number: 4,
      terms_hash: "b".repeat(64),
      status: "COMMITTED",
      terms: {
        schema_version: 2,
        buyer_id: BUYER_ID,
        seller_id: SELLER_ID,
        line_items: [
          {
            id: "item-valves-1",
            description: "Industrial Valves",
            sku: "VALVE-100",
            quantity: "100",
            unit: "pieces",
            unit_price: { amount: "250.00", currency: "USD" },
          },
        ],
        shipments: [
          {
            id: "ship-alpha",
            quantity: "100",
            destination: "Warehouse 4A, Hamburg Port",
            target_date: "2026-12-01",
            allocations: [
              { line_item_id: "item-valves-1", quantity: "100", unit: "pieces" },
            ],
          },
        ],
        payment_terms: [
          {
            id: "pay-deposit",
            amount: { amount: "25000.00", currency: "USD" },
            trigger: "customs_clearance",
            due_condition: "Net 30 days after arrival",
            allocations: [
              {
                obligation_id: "ship-alpha",
                amount: { amount: "25000.00", currency: "USD" },
              },
            ],
          },
        ],
        delivery_location: "Warehouse 4A, Hamburg Port",
        incoterm: "DAP",
        cancellation_terms: "14-day notice",
      },
      created_at: "2026-10-19T10:00:00Z",
      committed_at: "2026-10-19T11:00:00Z",
      approvals: [],
    };

    mockedGetCurrent.mockResolvedValue(schema2Agreement);
    renderReview();

    await screen.findByText("VERSION 4");
    expect(screen.getByText("item-valves-1")).toBeInTheDocument();
    expect(screen.getByText("VALVE-100")).toBeInTheDocument();
    expect(screen.getByText("ship-alpha")).toBeInTheDocument();
    expect(screen.getByText("100 pieces of item item-valves-1")).toBeInTheDocument();
    expect(screen.getByText("pay-deposit")).toBeInTheDocument();
    expect(screen.getByText("25000.00 USD for obligation ship-alpha")).toBeInTheDocument();
    expect(screen.getByText(/Taxes, freight, customs classification, and other fees: Not specified in committed terms/)).toBeInTheDocument();
  });

  it("sends a verified single-party choice and current agreement to the overview", async () => {
    const onOverviewChange = vi.fn();
    const onOrganizationChange = vi.fn();
    render(
      <AgreementReview
        dealId={DEAL_ID}
        buyerOrganizationId={BUYER_ID}
        sellerOrganizationId={SELLER_ID}
        onOrganizationChange={onOrganizationChange}
        onOverviewChange={onOverviewChange}
      />,
    );

    await screen.findByText("VERSION 3");
    expect(onOrganizationChange).toHaveBeenCalledWith(BUYER_ID);
    await waitFor(() => expect(onOverviewChange).toHaveBeenLastCalledWith(expect.objectContaining({
      dealId: DEAL_ID,
      organizationId: BUYER_ID,
      status: "ready",
      partyVerified: true,
      agreement: expect.objectContaining({ deal_id: DEAL_ID, version_number: 3, terms_hash: AGREEMENT.terms_hash }),
    })));
  });

  it("waits for the exact current version read before publishing agreement status", async () => {
    let resolveExact!: (agreement: AgreementVersion) => void;
    vi.mocked(getAgreementVersion).mockImplementationOnce(() => new Promise((resolve) => { resolveExact = resolve; }));
    const onOverviewChange = vi.fn();
    render(
      <AgreementReview
        dealId={DEAL_ID}
        buyerOrganizationId={BUYER_ID}
        sellerOrganizationId={SELLER_ID}
        selectedOrganizationId={BUYER_ID}
        onOverviewChange={onOverviewChange}
      />,
    );

    await screen.findByText("VERSION 3");
    await waitFor(() => expect(getAgreementVersion).toHaveBeenCalled());
    expect(onOverviewChange).toHaveBeenLastCalledWith(expect.objectContaining({ status: "loading" }));
    resolveExact(AGREEMENT);
    await waitFor(() => expect(onOverviewChange).toHaveBeenLastCalledWith(expect.objectContaining({
      organizationId: BUYER_ID,
      status: "ready",
      partyVerified: true,
      agreement: AGREEMENT,
    })));
  });

  it("keeps the overview neutral until a dual member chooses a deal party", async () => {
    mockedListOrganizations.mockResolvedValue([BUYER, SELLER]);
    const onOverviewChange = vi.fn();
    const onOrganizationChange = vi.fn();
    render(
      <AgreementReview
        dealId={DEAL_ID}
        buyerOrganizationId={BUYER_ID}
        sellerOrganizationId={SELLER_ID}
        selectedOrganizationId=""
        onOrganizationChange={onOrganizationChange}
        onOverviewChange={onOverviewChange}
      />,
    );

    await screen.findByText("VERSION 3");
    expect(onOrganizationChange).not.toHaveBeenCalled();
    expect(onOverviewChange).toHaveBeenLastCalledWith(expect.objectContaining({
      organizationId: "",
      status: "ready",
      partyVerified: false,
    }));
    fireEvent.change(screen.getByLabelText("Approve as organization"), { target: { value: SELLER_ID } });
    expect(onOrganizationChange).toHaveBeenCalledWith(SELLER_ID);
  });

  it("does not publish an empty agreement state when the history check fails", async () => {
    mockedGetCurrent.mockRejectedValue(new ApiError(404, "No current agreement"));
    vi.mocked(getAgreementHistory).mockRejectedValue(new ApiError(500, "History unavailable"));
    const onOverviewChange = vi.fn();
    render(
      <AgreementReview
        dealId={DEAL_ID}
        buyerOrganizationId={BUYER_ID}
        sellerOrganizationId={SELLER_ID}
        selectedOrganizationId={BUYER_ID}
        onOverviewChange={onOverviewChange}
      />,
    );

    expect(await screen.findByText("History unavailable")).toBeInTheDocument();
    expect(onOverviewChange).not.toHaveBeenCalledWith(expect.objectContaining({ status: "empty" }));
    expect(onOverviewChange).toHaveBeenLastCalledWith(expect.objectContaining({ status: "error" }));
  });

  it("renders amendment lineage badge, prior hash and rationale when version_number > 1", async () => {
    const amendmentVersion: AgreementVersion = {
      ...AGREEMENT,
      version_number: 2,
      prior_terms_hash: "f".repeat(64),
      amendment_rationale: "Price adjustment agreed by both parties",
    };
    mockedGetCurrent.mockResolvedValue(amendmentVersion);
    vi.mocked(getAgreementVersion).mockResolvedValue(amendmentVersion);

    render(
      <AgreementReview
        dealId={DEAL_ID}
        buyerOrganizationId={BUYER_ID}
        sellerOrganizationId={SELLER_ID}
        selectedOrganizationId={BUYER_ID}
      />,
    );

    expect(await screen.findByText("Amends version 1")).toBeInTheDocument();
    expect(screen.getByText(/Price adjustment agreed by both parties/)).toBeInTheDocument();
    expect(screen.getByText(/Prior hash:/)).toBeInTheDocument();
  });

  it("renders withdraw amendment button for pending amendment version > 1 and calls withdrawAmendment", async () => {
    const amendmentVersion: AgreementVersion = {
      ...AGREEMENT,
      version_number: 2,
      prior_terms_hash: "f".repeat(64),
      status: "PENDING_APPROVAL",
    };
    mockedGetCurrent.mockResolvedValue(amendmentVersion);
    vi.mocked(getAgreementVersion).mockResolvedValue(amendmentVersion);

    render(
      <AgreementReview
        dealId={DEAL_ID}
        buyerOrganizationId={BUYER_ID}
        sellerOrganizationId={SELLER_ID}
        selectedOrganizationId={BUYER_ID}
      />,
    );

    const withdrawBtn = await screen.findByRole("button", { name: "Withdraw amendment" });
    expect(withdrawBtn).toBeInTheDocument();
    fireEvent.click(withdrawBtn);

    await waitFor(() => {
      expect(mockedWithdrawAmendment).toHaveBeenCalledWith(
        DEAL_ID,
        2,
        amendmentVersion.terms_hash,
        BUYER_ID,
      );
    });
  });

  it("disables commit button and displays blocker warning when amendment impact has can_commit === false", async () => {
    const bothApprovedAmendment: AgreementVersion = {
      ...AGREEMENT,
      version_number: 2,
      prior_terms_hash: "f".repeat(64),
      status: "PENDING_APPROVAL",
      approvals: [
        {
          deal_id: DEAL_ID,
          version_number: 2,
          organization_id: BUYER_ID,
          user_id: "buyer-user",
          decision: "APPROVE",
          terms_hash: AGREEMENT.terms_hash,
          created_at: "2026-10-19T10:01:00Z",
        },
        {
          deal_id: DEAL_ID,
          version_number: 2,
          organization_id: SELLER_ID,
          user_id: "seller-user",
          decision: "APPROVE",
          terms_hash: AGREEMENT.terms_hash,
          created_at: "2026-10-19T10:01:00Z",
        },
      ],
    };
    mockedGetCurrent.mockResolvedValue(bothApprovedAmendment);
    vi.mocked(getAgreementVersion).mockResolvedValue(bothApprovedAmendment);
    mockedGetAmendmentImpact.mockResolvedValue({
      prior_version_number: 1,
      prior_terms_hash: "f".repeat(64),
      proposed_version_number: 2,
      proposed_terms_hash: AGREEMENT.terms_hash,
      diff: { fields: [], collections: {} },
      fulfillment_impact: [],
      payment_impact: [],
      active_cases: [],
      blockers: ["Fulfilled obligations cannot be reduced"],
      can_commit: false,
    });

    render(
      <AgreementReview
        dealId={DEAL_ID}
        buyerOrganizationId={BUYER_ID}
        sellerOrganizationId={SELLER_ID}
        selectedOrganizationId={BUYER_ID}
      />,
    );

    expect(
      await screen.findByText("Cannot commit amendment: unresolved policy blockers must be addressed."),
    ).toBeInTheDocument();
    const commitBtn = screen.getByRole("button", { name: "Commit approved agreement" });
    expect(commitBtn).toBeDisabled();
  });

  it("allows reviewing and approving a pending amendment candidate selected from version dropdown", async () => {
    const committedV1: AgreementVersion = {
      ...AGREEMENT,
      id: "v1",
      version_number: 1,
      status: "COMMITTED",
      committed_at: "2026-10-19T09:00:00Z",
    };
    const pendingV2: AgreementVersion = {
      ...AGREEMENT,
      id: "v2",
      version_number: 2,
      status: "PENDING_APPROVAL",
      prior_terms_hash: committedV1.terms_hash,
      amendment_rationale: "Increase quantity for demand spike",
      approvals: [],
    };

    mockedGetCurrent.mockResolvedValue(committedV1);
    vi.mocked(getAgreementHistory).mockResolvedValue({
      deal_id: DEAL_ID,
      organization_id: BUYER_ID,
      current_version_id: "v1",
      versions: [pendingV2, committedV1],
    });
    vi.mocked(getAgreementVersion).mockImplementation(async (_deal, number) => {
      if (number === 2) return pendingV2;
      return committedV1;
    });

    render(
      <AgreementReview
        dealId={DEAL_ID}
        buyerOrganizationId={BUYER_ID}
        sellerOrganizationId={SELLER_ID}
        selectedOrganizationId={BUYER_ID}
      />,
    );

    // Initial view shows committed V1 and the pending notice banner
    expect(await screen.findByText("This agreement is committed. Its terms are read-only and cannot be changed in place.")).toBeInTheDocument();
    expect(await screen.findByText("An amendment (Version 2) is awaiting approval.")).toBeInTheDocument();

    // Click banner button to switch to Version 2
    fireEvent.click(await screen.findByRole("button", { name: "Review pending amendment (Version 2)" }));

    // Now viewing Version 2
    expect(await screen.findByText("Amends version 1")).toBeInTheDocument();
    expect(screen.getByText(/Increase quantity for demand spike/)).toBeInTheDocument();
    expect(screen.queryByText("Historical version · Read-only")).not.toBeInTheDocument();

    // Decision buttons are available
    const approveBtn = screen.getByRole("button", { name: "Approve this version" });
    expect(approveBtn).toBeEnabled();
    const withdrawBtn = screen.getByRole("button", { name: "Withdraw amendment" });
    expect(withdrawBtn).toBeEnabled();

    // Approve Version 2
    fireEvent.click(approveBtn);
    await waitFor(() => {
      expect(mockedRecordDecision).toHaveBeenCalledWith(
        DEAL_ID,
        2,
        pendingV2.terms_hash,
        "approve",
        BUYER_ID,
      );
    });
  });

  it("allows proposing an amendment from a committed agreement when no pending candidate exists", async () => {
    const committedV1: AgreementVersion = {
      ...AGREEMENT,
      id: "v1",
      version_number: 1,
      status: "COMMITTED",
      committed_at: "2026-10-19T09:00:00Z",
    };

    mockedGetCurrent.mockResolvedValue(committedV1);
    vi.mocked(getAgreementHistory).mockResolvedValue({
      deal_id: DEAL_ID,
      organization_id: BUYER_ID,
      current_version_id: "v1",
      versions: [committedV1],
    });
    vi.mocked(getAgreementVersion).mockResolvedValue(committedV1);
    mockedPreviewAmendmentImpact.mockResolvedValue({
      prior_version_number: 1,
      prior_terms_hash: committedV1.terms_hash,
      proposed_version_number: 2,
      proposed_terms_hash: "new-hash",
      diff: { fields: [], collections: {} },
      fulfillment_impact: [],
      payment_impact: [],
      active_cases: [],
      blockers: [],
      can_commit: true,
    });
    mockedProposeAmendment.mockResolvedValue({
      ...committedV1,
      id: "v2",
      version_number: 2,
      status: "PENDING_APPROVAL",
    });

    render(
      <AgreementReview
        dealId={DEAL_ID}
        buyerOrganizationId={BUYER_ID}
        sellerOrganizationId={SELLER_ID}
        selectedOrganizationId={BUYER_ID}
      />,
    );

    // Initial committed view without pending candidate has "Propose amendment"
    const proposeBtn = await screen.findByRole("button", { name: "Propose amendment" });
    expect(proposeBtn).toBeInTheDocument();
    fireEvent.click(proposeBtn);

    // Form is displayed
    const rationaleInput = screen.getByLabelText("Amendment rationale (required)");
    const submitBtn = screen.getByRole("button", { name: "Submit amendment proposal" });
    expect(submitBtn).toBeDisabled();

    // Enter rationale
    fireEvent.change(rationaleInput, { target: { value: "Expanding delivery scope" } });
    expect(submitBtn).toBeEnabled();

    // Preview impact
    const previewBtn = screen.getByRole("button", { name: "Preview operational impact" });
    fireEvent.click(previewBtn);
    await waitFor(() => {
      expect(mockedPreviewAmendmentImpact).toHaveBeenCalledWith(DEAL_ID, expect.objectContaining({
        organization_id: BUYER_ID,
      }));
    });

    // Submit amendment
    fireEvent.click(submitBtn);
    await waitFor(() => {
      expect(mockedProposeAmendment).toHaveBeenCalledWith(DEAL_ID, expect.objectContaining({
        prior_version_number: 1,
        prior_terms_hash: committedV1.terms_hash,
        rationale: "Expanding delivery scope",
        organization_id: BUYER_ID,
      }));
    });
  });
});
