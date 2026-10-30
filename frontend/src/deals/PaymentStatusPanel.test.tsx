import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  authorizeDealPayment,
  getCurrentAgreement,
  getDeal,
  getOrganization,
  listOrganizations,
  listPaymentStatuses,
} from "../api/client";
import type { AgreementVersion, Deal, OrganizationDirectoryItem, PaymentStatus } from "../api/types";
import PaymentStatusPanel from "./PaymentStatusPanel";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    authorizeDealPayment: vi.fn(),
    getCurrentAgreement: vi.fn(),
    getDeal: vi.fn(),
    getOrganization: vi.fn(),
    listOrganizations: vi.fn(),
    listPaymentStatuses: vi.fn(),
  };
});

const mockedAuthorizeDealPayment = vi.mocked(authorizeDealPayment);
const mockedGetCurrentAgreement = vi.mocked(getCurrentAgreement);
const mockedGetDeal = vi.mocked(getDeal);
const mockedGetOrganization = vi.mocked(getOrganization);
const mockedListOrganizations = vi.mocked(listOrganizations);
const mockedListPaymentStatuses = vi.mocked(listPaymentStatuses);

const PAYMENT: PaymentStatus = {
  id: "payment-1",
  milestone_sequence: 1,
  amount: "100",
  currency: "USD",
  status: "PENDING",
  reconciled_amount: null,
  last_checked_at: null,
  last_reconciled_at: null,
};

describe("PaymentStatusPanel", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/");
    mockedAuthorizeDealPayment.mockResolvedValue({
      id: "payment-1",
      status: "AUTHORIZED",
      already_existed: false,
    });
    mockedGetCurrentAgreement.mockRejectedValue(new ApiError(404, "Agreement not found"));
    mockedGetDeal.mockResolvedValue({
      id: "deal-1",
      buyer_organization_id: "buyer-org-1",
      seller_organization_id: "seller-org-1",
      status: "ACTIVE",
      version: 1,
    } as Deal);
    mockedGetOrganization.mockResolvedValue({
      id: "buyer-org-1",
      legal_name: "Buyer Co",
      country_code: "US",
    } as OrganizationDirectoryItem);
    mockedListOrganizations.mockResolvedValue([]);
  });

  afterEach(() => {
    vi.clearAllMocks();
    window.history.replaceState({}, "", "/");
  });

  it("shows a loading state", () => {
    mockedListPaymentStatuses.mockReturnValue(new Promise(() => {}));

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    expect(screen.getByRole("status")).toHaveTextContent(/loading payment status/i);
  });

  it("shows a pending status even when the return URL says paid", async () => {
    window.history.replaceState({}, "", "/?payment_status=paid&success=true");
    mockedListPaymentStatuses.mockResolvedValue([PAYMENT]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    expect(await screen.findByText("Waiting for payment")).toBeInTheDocument();
    expect(screen.queryByText(/^Paid$/)).not.toBeInTheDocument();
  });

  it("shows the confirmed partial amount", async () => {
    mockedListPaymentStatuses.mockResolvedValue([
      { ...PAYMENT, status: "PARTIALLY_PAID", reconciled_amount: "40" },
    ]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    expect(await screen.findByText("Partially paid")).toBeInTheDocument();
    expect(screen.getByText("Confirmed so far: USD 40 of USD 100")).toBeInTheDocument();
  });

  it("shows paid only when the backend reports paid", async () => {
    mockedListPaymentStatuses.mockResolvedValue([
      { ...PAYMENT, status: "PAID", reconciled_amount: "100" },
    ]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    expect(await screen.findByText("Paid")).toBeInTheDocument();
    expect(screen.getByText(/backend has confirmed the full milestone amount/i)).toBeInTheDocument();
  });

  it("shows a failed payment as needing attention", async () => {
    mockedListPaymentStatuses.mockResolvedValue([{ ...PAYMENT, status: "FAILED" }]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    expect(await screen.findByText("Needs attention")).toBeInTheDocument();
    expect(screen.getByText("The payment request did not complete.")).toBeInTheDocument();
  });

  it("handles a payment status the screen does not recognize", async () => {
    mockedListPaymentStatuses.mockResolvedValue([{ ...PAYMENT, status: "NEW_STATUS" }]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    expect(await screen.findByText("Status unavailable")).toBeInTheDocument();
  });

  it("shows an unavailable state when no request exists", async () => {
    mockedListPaymentStatuses.mockResolvedValue([]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    expect(await screen.findByText(/no payment request is available/i)).toBeInTheDocument();
  });

  it("reloads payment eligibility when the agreement reload token changes", async () => {
    mockedListPaymentStatuses.mockResolvedValue([]);
    mockedGetCurrentAgreement
      .mockRejectedValueOnce(new ApiError(404, "Agreement not found"))
      .mockResolvedValueOnce({ status: "COMMITTED" } as AgreementVersion);
    mockedListOrganizations.mockResolvedValue([
      { id: "seller-org-1", legal_name: "Seller Co", country_code: "CA", role: "ADMIN" },
    ]);

    const { rerender } = render(
      <PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" reloadToken={0} />,
    );

    expect(await screen.findByText(/no payment request is available/i)).toBeInTheDocument();
    expect(mockedGetCurrentAgreement).toHaveBeenCalledTimes(1);

    rerender(
      <PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" reloadToken={1} />,
    );

    expect(await screen.findByRole("button", { name: "Request Payment" })).toBeInTheDocument();
    expect(mockedGetCurrentAgreement).toHaveBeenCalledTimes(2);
  });

  it("lets a committed agreement's seller queue its payment request after confirmation", async () => {
    mockedListPaymentStatuses.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockResolvedValue({ status: "COMMITTED" } as AgreementVersion);
    mockedListOrganizations.mockResolvedValue([
      { id: "seller-org-1", legal_name: "Seller Co", country_code: "CA", role: "ADMIN" },
    ]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    fireEvent.click(await screen.findByRole("button", { name: "Request Payment" }));

    expect(await screen.findByRole("dialog", { name: "Confirm Invoice Recipient" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Confirm & Send Invoice" }));

    expect(mockedAuthorizeDealPayment).toHaveBeenCalledWith("deal-1", expect.any(String));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "The payment request is queued for the backend worker.",
    );
  });

  it("does not let a buyer queue the seller's payment request", async () => {
    mockedListPaymentStatuses.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockResolvedValue({ status: "COMMITTED" } as AgreementVersion);
    mockedListOrganizations.mockResolvedValue([
      { id: "buyer-org-1", legal_name: "Buyer Co", country_code: "US", role: "ADMIN" },
    ]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    expect(await screen.findByText(/no payment request is available/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Request Payment" })).not.toBeInTheDocument();
    expect(mockedAuthorizeDealPayment).not.toHaveBeenCalled();
  });

  it("prompts recipient confirmation dialog with buyer details and formatted milestone amount before authorizing", async () => {
    mockedListPaymentStatuses.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockResolvedValue({
      status: "COMMITTED",
      terms: {
        buyer_id: "buyer-org-1",
        seller_id: "seller-org-1",
        payment_terms: [
          {
            amount: { amount: "22500.00", currency: "USD" },
            trigger: "DELIVERY",
            due_condition: "NET_30",
          },
        ],
      },
    } as unknown as AgreementVersion);
    mockedListOrganizations.mockResolvedValue([
      { id: "seller-org-1", legal_name: "Seller Co", country_code: "CA", role: "ADMIN" },
    ]);
    mockedGetOrganization.mockResolvedValue({
      id: "buyer-org-1",
      legal_name: "Acme Industrial Corp",
      country_code: "US",
    } as OrganizationDirectoryItem);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    const requestButton = await screen.findByRole("button", { name: "Request Payment" });
    fireEvent.click(requestButton);

    const dialog = await screen.findByRole("dialog", { name: "Confirm Invoice Recipient" });
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute("aria-modal", "true");

    expect(screen.getByText("Acme Industrial Corp")).toBeInTheDocument();
    expect(screen.getByText("US")).toBeInTheDocument();
    expect(screen.getByText("Resolved by the backend at issuance")).toBeInTheDocument();
    expect(screen.getByText("USD 22,500.00")).toBeInTheDocument();
    expect(
      screen.getByText("This will create a formal PayPal invoice dispatched to the recipient above."),
    ).toBeInTheDocument();

    expect(mockedAuthorizeDealPayment).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Confirm & Send Invoice" }));

    expect(mockedAuthorizeDealPayment).toHaveBeenCalledWith("deal-1", expect.any(String));
  });

  it("displays recipient billing email from existing payment status when present", async () => {
    mockedListPaymentStatuses.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockResolvedValue({
      status: "COMMITTED",
      terms: {
        buyer_id: "buyer-org-1",
        seller_id: "seller-org-1",
        payment_terms: [
          {
            amount: { amount: "10000", currency: "EUR" },
            trigger: "DELIVERY",
            due_condition: "NET_15",
          },
        ],
      },
    } as unknown as AgreementVersion);
    mockedListOrganizations.mockResolvedValue([
      { id: "seller-org-1", legal_name: "Seller Co", country_code: "CA", role: "ADMIN" },
    ]);
    mockedGetOrganization.mockResolvedValue({
      id: "buyer-org-1",
      legal_name: "Global Import AG",
      country_code: "DE",
      billing_email: "ap@globalimport.example",
    } as unknown as OrganizationDirectoryItem);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    fireEvent.click(await screen.findByRole("button", { name: "Request Payment" }));

    expect(await screen.findByText("Global Import AG")).toBeInTheDocument();
    expect(screen.getByText("DE")).toBeInTheDocument();
    expect(screen.getByText("ap@globalimport.example")).toBeInTheDocument();
    expect(screen.getByText("EUR 10,000.00")).toBeInTheDocument();
  });

  it("closes the confirmation modal on Cancel without authorizing payment", async () => {
    mockedListPaymentStatuses.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockResolvedValue({ status: "COMMITTED" } as AgreementVersion);
    mockedListOrganizations.mockResolvedValue([
      { id: "seller-org-1", legal_name: "Seller Co", country_code: "CA", role: "ADMIN" },
    ]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    fireEvent.click(await screen.findByRole("button", { name: "Request Payment" }));

    expect(await screen.findByRole("dialog", { name: "Confirm Invoice Recipient" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("dialog", { name: "Confirm Invoice Recipient" })).not.toBeInTheDocument();
    expect(mockedAuthorizeDealPayment).not.toHaveBeenCalled();
  });

  it("closes the confirmation modal on Escape key without authorizing payment", async () => {
    mockedListPaymentStatuses.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockResolvedValue({ status: "COMMITTED" } as AgreementVersion);
    mockedListOrganizations.mockResolvedValue([
      { id: "seller-org-1", legal_name: "Seller Co", country_code: "CA", role: "ADMIN" },
    ]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    fireEvent.click(await screen.findByRole("button", { name: "Request Payment" }));

    expect(await screen.findByRole("dialog", { name: "Confirm Invoice Recipient" })).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });

    expect(screen.queryByRole("dialog", { name: "Confirm Invoice Recipient" })).not.toBeInTheDocument();
    expect(mockedAuthorizeDealPayment).not.toHaveBeenCalled();
  });

  it("closes the confirmation modal when clicking the close button", async () => {
    mockedListPaymentStatuses.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockResolvedValue({ status: "COMMITTED" } as AgreementVersion);
    mockedListOrganizations.mockResolvedValue([
      { id: "seller-org-1", legal_name: "Seller Co", country_code: "CA", role: "ADMIN" },
    ]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    fireEvent.click(await screen.findByRole("button", { name: "Request Payment" }));

    expect(await screen.findByRole("dialog", { name: "Confirm Invoice Recipient" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Close recipient confirmation" }));

    expect(screen.queryByRole("dialog", { name: "Confirm Invoice Recipient" })).not.toBeInTheDocument();
    expect(mockedAuthorizeDealPayment).not.toHaveBeenCalled();
  });

  it("shows an API error with a retry action", async () => {
    mockedListPaymentStatuses.mockRejectedValueOnce(new ApiError(503, "Service unavailable"));

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/payment status is unavailable/i);
    mockedListPaymentStatuses.mockResolvedValueOnce([PAYMENT]);
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Waiting for payment")).toBeInTheDocument();
  });

  it("does not render provider invoice links or payment secrets", async () => {
    mockedListPaymentStatuses.mockResolvedValue([
      {
        ...PAYMENT,
        provider_invoice_id: "secret-invoice-id",
        recipient_view_url: "https://paypal.example/private-invoice-token",
      } as PaymentStatus,
    ]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    await screen.findByText("Waiting for payment");
    expect(screen.queryByText(/secret-invoice|private-invoice-token/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
