import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  commitAgreementVersion,
  getCurrentAgreement,
  listOrganizations,
  recordAgreementDecision,
} from "../api/client";
import type { AgreementVersion, Organization } from "../api/types";
import AgreementReview from "./AgreementReview";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    commitAgreementVersion: vi.fn(),
    getCurrentAgreement: vi.fn(),
    listOrganizations: vi.fn(),
    recordAgreementDecision: vi.fn(),
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

  afterEach(() => vi.clearAllMocks());

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
    expect(await screen.findByText("APPROVE")).toBeInTheDocument();
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
      ),
    );
    expect(await screen.findByText(/committed\. its terms are read-only/i)).toBeInTheDocument();
    expect(onCommitted).toHaveBeenCalledTimes(1);
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
});
