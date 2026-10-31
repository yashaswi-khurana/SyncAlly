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
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Refresh status" }));
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

    expect(await screen.findByText("Acme Industrial Corp")).toBeInTheDocument();
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

  it("sets panel ready state without waiting for slow or pending buyer organization lookup", async () => {
    mockedListPaymentStatuses.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockResolvedValue({
      status: "COMMITTED",
      terms: {
        buyer_id: "buyer-org-1",
        seller_id: "seller-org-1",
        payment_terms: [
          {
            amount: { amount: "5000", currency: "USD" },
            trigger: "DELIVERY",
            due_condition: "NET_30",
          },
        ],
      },
    } as unknown as AgreementVersion);
    mockedListOrganizations.mockResolvedValue([
      { id: "seller-org-1", legal_name: "Seller Co", country_code: "CA", role: "ADMIN" },
    ]);
    // Buyer lookup that stays pending indefinitely:
    mockedGetOrganization.mockReturnValue(new Promise(() => {}));

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    // The panel should become ready immediately without waiting for directory lookup
    expect(await screen.findByRole("button", { name: "Request Payment" })).toBeInTheDocument();
    expect(screen.queryByText(/loading payment status/i)).not.toBeInTheDocument();

    // Opening confirmation dialog shows graceful fallbacks
    fireEvent.click(screen.getByRole("button", { name: "Request Payment" }));
    expect(await screen.findByRole("dialog", { name: "Confirm Invoice Recipient" })).toBeInTheDocument();
    expect(screen.getAllByText("Not available")).toHaveLength(2); // legalName and countryCode
    expect(screen.getByText("USD 5,000.00")).toBeInTheDocument();
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

    const requestButton = await screen.findByRole("button", { name: "Request Payment" });
    fireEvent.click(requestButton);

    expect(await screen.findByRole("dialog", { name: "Confirm Invoice Recipient" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("dialog", { name: "Confirm Invoice Recipient" })).not.toBeInTheDocument();
    expect(document.activeElement).toBe(requestButton);
    expect(mockedAuthorizeDealPayment).not.toHaveBeenCalled();
  });

  it("closes the confirmation modal on Escape key without authorizing payment", async () => {
    mockedListPaymentStatuses.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockResolvedValue({ status: "COMMITTED" } as AgreementVersion);
    mockedListOrganizations.mockResolvedValue([
      { id: "seller-org-1", legal_name: "Seller Co", country_code: "CA", role: "ADMIN" },
    ]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    const requestButton = await screen.findByRole("button", { name: "Request Payment" });
    fireEvent.click(requestButton);

    expect(await screen.findByRole("dialog", { name: "Confirm Invoice Recipient" })).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });

    expect(screen.queryByRole("dialog", { name: "Confirm Invoice Recipient" })).not.toBeInTheDocument();
    expect(document.activeElement).toBe(requestButton);
    expect(mockedAuthorizeDealPayment).not.toHaveBeenCalled();
  });

  it("closes the confirmation modal when clicking the close button", async () => {
    mockedListPaymentStatuses.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockResolvedValue({ status: "COMMITTED" } as AgreementVersion);
    mockedListOrganizations.mockResolvedValue([
      { id: "seller-org-1", legal_name: "Seller Co", country_code: "CA", role: "ADMIN" },
    ]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    const requestButton = await screen.findByRole("button", { name: "Request Payment" });
    fireEvent.click(requestButton);

    expect(await screen.findByRole("dialog", { name: "Confirm Invoice Recipient" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Close recipient confirmation" }));

    expect(screen.queryByRole("dialog", { name: "Confirm Invoice Recipient" })).not.toBeInTheDocument();
    expect(document.activeElement).toBe(requestButton);
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

  it("displays prominent '💳 View & Pay PayPal Invoice' link opening in new tab for buyer", async () => {
    mockedListOrganizations.mockResolvedValue([
      { id: "buyer-org-1", legal_name: "Buyer Co", country_code: "US", role: "ADMIN" },
    ]);
    mockedListPaymentStatuses.mockResolvedValue([
      {
        ...PAYMENT,
        status: "SENT",
        invoice_url: "https://www.sandbox.paypal.com/invoice/p/#INV2-SIM-TEST1234",
      } as PaymentStatus,
    ]);

    render(
      <PaymentStatusPanel
        dealId="deal-1"
        sellerOrganizationId="seller-org-1"
        buyerOrganizationId="buyer-org-1"
      />,
    );

    const payLink = await screen.findByRole("link", { name: "💳 View & Pay PayPal Invoice" });
    expect(payLink).toBeInTheDocument();
    expect(payLink).toHaveAttribute(
      "href",
      "https://www.sandbox.paypal.com/invoice/p/#INV2-SIM-TEST1234",
    );
    expect(payLink).toHaveAttribute("target", "_blank");
    expect(payLink).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("displays invoice number and payment instructions when invoice_url is present", async () => {
    mockedListOrganizations.mockResolvedValue([
      { id: "buyer-org-1", legal_name: "Buyer Co", country_code: "US", role: "ADMIN" },
    ]);
    mockedListPaymentStatuses.mockResolvedValue([
      {
        ...PAYMENT,
        status: "SENT",
        invoice_url: "https://www.sandbox.paypal.com/invoice/p/#INV2-SIM-TEST1234",
      } as PaymentStatus,
    ]);

    render(
      <PaymentStatusPanel
        dealId="deal-1"
        sellerOrganizationId="seller-org-1"
        buyerOrganizationId="buyer-org-1"
      />,
    );

    expect(await screen.findByText("INV2-SIM-TEST1234")).toBeInTheDocument();
    expect(screen.getByText("Payment Instructions")).toBeInTheDocument();
    expect(
      screen.getByText(/Review your order details and milestone amount on PayPal/i),
    ).toBeInTheDocument();
  });

  it("clearly distinguishes RETRYING state with live countdown, retry count, last attempt, and cause", async () => {
    mockedListPaymentStatuses.mockResolvedValue([
      {
        ...PAYMENT,
        status: "RETRYING",
        retry_count: 2,
        last_checked_at: "10:42 AM",
        failure_reason: "PayPal sandbox rate limit",
        next_retry_at: "45",
      } as PaymentStatus,
    ]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    expect(await screen.findByText("Automatic Retry Scheduled")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Payment request retry #2 in ~45 seconds. Last attempt: 10:42 AM. Cause: PayPal sandbox rate limit.",
      ),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Retrying")).toHaveLength(1);
  });

  it("falls back to neutral 'Cause unavailable' in RETRYING state when failure_reason is not provided", async () => {
    mockedListPaymentStatuses.mockResolvedValue([
      {
        ...PAYMENT,
        status: "RETRYING",
        retry_count: 1,
        last_checked_at: null,
        failure_reason: null,
        next_retry_at: "30",
      } as PaymentStatus,
    ]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    expect(await screen.findByText("Automatic Retry Scheduled")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Payment request retry #1 in ~30 seconds. Last attempt: Just now. Cause: Cause unavailable.",
      ),
    ).toBeInTheDocument();
  });

  it("clearly distinguishes FAILED state, showing exact error cause and safe Retry Request button for eligible seller", async () => {
    mockedGetCurrentAgreement.mockResolvedValue({ status: "COMMITTED" } as AgreementVersion);
    mockedListOrganizations.mockResolvedValue([
      { id: "seller-org-1", legal_name: "Seller Co", country_code: "CA", role: "ADMIN" },
    ]);
    mockedListPaymentStatuses.mockResolvedValue([
      {
        ...PAYMENT,
        status: "FAILED",
        failure_reason: "PayPal sandbox rate limit exceeded",
      } as PaymentStatus,
    ]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    expect(await screen.findByText("Payment Request Failed")).toBeInTheDocument();
    expect(
      screen.getByText("PayPal sandbox rate limit exceeded", { exact: false }),
    ).toBeInTheDocument();

    const retryButton = screen.getByRole("button", { name: "Retry Request" });
    expect(retryButton).toBeInTheDocument();

    fireEvent.click(retryButton);

    expect(mockedAuthorizeDealPayment).toHaveBeenCalledWith("deal-1", expect.any(String));
  });

  it("does not render the Retry Request button for buyers on a failed payment", async () => {
    mockedGetCurrentAgreement.mockResolvedValue({ status: "COMMITTED" } as AgreementVersion);
    mockedListOrganizations.mockResolvedValue([
      { id: "buyer-org-1", legal_name: "Buyer Co", country_code: "US", role: "ADMIN" },
    ]);
    mockedListPaymentStatuses.mockResolvedValue([
      {
        ...PAYMENT,
        status: "FAILED",
        failure_reason: "PayPal sandbox rate limit exceeded",
      } as PaymentStatus,
    ]);

    render(
      <PaymentStatusPanel
        dealId="deal-1"
        sellerOrganizationId="seller-org-1"
        buyerOrganizationId="buyer-org-1"
      />,
    );

    expect(await screen.findByText("Payment Request Failed")).toBeInTheDocument();
    expect(
      screen.getByText("PayPal sandbox rate limit exceeded", { exact: false }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry Request" })).not.toBeInTheDocument();
    expect(mockedAuthorizeDealPayment).not.toHaveBeenCalled();
  });

  it("auto-polls payment status every 10 seconds while payment is in transitional state and cleans up on unmount", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockedListPaymentStatuses.mockResolvedValue([
      {
        ...PAYMENT,
        status: "CREATE_PENDING",
      },
    ]);

    const { unmount } = render(
      <PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />,
    );

    // Wait for initial load to complete
    expect(await screen.findByText("Preparing payment request")).toBeInTheDocument();
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(1);

    // Fast-forward 10 seconds
    await vi.advanceTimersByTimeAsync(10000);
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(2);

    // Fast-forward another 10 seconds
    await vi.advanceTimersByTimeAsync(10000);
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(3);

    // Unmount and verify polling stops
    unmount();
    await vi.advanceTimersByTimeAsync(20000);
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(3);

    vi.useRealTimers();
  });

  it("auto-polls payment status while in SENT or PENDING state awaiting backend reconciliation", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockedListPaymentStatuses.mockResolvedValue([
      {
        ...PAYMENT,
        status: "SENT",
      },
    ]);

    const { unmount } = render(
      <PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />,
    );

    expect(await screen.findByText("Waiting for payment")).toBeInTheDocument();
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(10000);
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(2);

    unmount();
    await vi.advanceTimersByTimeAsync(20000);
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(2);

    vi.useRealTimers();
  });

  it("preserves newer payments loaded by manual refresh when an older poll response arrives", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });

    // Initial load returns transitional PENDING payment
    mockedListPaymentStatuses.mockResolvedValueOnce([
      {
        ...PAYMENT,
        status: "PENDING",
      },
    ]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    expect(await screen.findByText("Waiting for payment")).toBeInTheDocument();

    // Prepare a deferred poll response
    let resolveSlowPoll!: (value: PaymentStatus[]) => void;
    const slowPollPromise = new Promise<PaymentStatus[]>((resolve) => {
      resolveSlowPoll = resolve;
    });

    mockedListPaymentStatuses.mockReturnValueOnce(slowPollPromise);

    // Advance 10s so the poll starts
    await vi.advanceTimersByTimeAsync(10000);
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(2);

    // Before slow poll resolves, user clicks "Refresh" (manual refresh)
    mockedListPaymentStatuses.mockResolvedValueOnce([
      {
        ...PAYMENT,
        status: "PAID",
        reconciled_amount: "100",
      },
    ]);

    const refreshButton = screen.getByRole("button", { name: "Refresh status" });
    fireEvent.click(refreshButton);

    // Wait for manual refresh to update UI to PAID
    expect(await screen.findByText("Paid")).toBeInTheDocument();
    expect(screen.queryByText("Waiting for payment")).not.toBeInTheDocument();

    // Now resolve the older poll that had PENDING status
    resolveSlowPoll([
      {
        ...PAYMENT,
        status: "PENDING",
      },
    ]);
    await vi.advanceTimersByTimeAsync(100);

    // Stale poll should be discarded; UI must remain Paid
    expect(screen.getByText("Paid")).toBeInTheDocument();
    expect(screen.queryByText("Waiting for payment")).not.toBeInTheDocument();

    vi.useRealTimers();
  });

  it("invalidates in-flight poll when the component unmounts", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });

    mockedListPaymentStatuses.mockResolvedValueOnce([
      {
        ...PAYMENT,
        status: "PENDING",
      },
    ]);

    const { unmount } = render(
      <PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />,
    );

    expect(await screen.findByText("Waiting for payment")).toBeInTheDocument();

    let resolveSlowPoll!: (value: PaymentStatus[]) => void;
    const slowPollPromise = new Promise<PaymentStatus[]>((resolve) => {
      resolveSlowPoll = resolve;
    });
    mockedListPaymentStatuses.mockReturnValueOnce(slowPollPromise);

    await vi.advanceTimersByTimeAsync(10000);
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(2);

    unmount();

    // Resolve after unmount - should safely no-op without updating state
    resolveSlowPoll([
      {
        ...PAYMENT,
        status: "PAID",
      },
    ]);
    await vi.advanceTimersByTimeAsync(100);

    vi.useRealTimers();
  });
});
