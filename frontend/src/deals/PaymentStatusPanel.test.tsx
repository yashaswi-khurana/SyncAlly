import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  authorizeDealPayment,
  getCurrentAgreement,
  getDeal,
  getOrganization,
  listOrganizations,
  listPaymentStatuses,
  previewDealPayment,
} from "../api/client";
import type { AgreementVersion, Deal, OrganizationDirectoryItem, PaymentIntentStatus, PaymentStatus } from "../api/types";
import PaymentStatusPanel, { formatCountdown } from "./PaymentStatusPanel";

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
    previewDealPayment: vi.fn(),
  };
});

const mockedAuthorizeDealPayment = vi.mocked(authorizeDealPayment);
const mockedGetCurrentAgreement = vi.mocked(getCurrentAgreement);
const mockedGetDeal = vi.mocked(getDeal);
const mockedGetOrganization = vi.mocked(getOrganization);
const mockedListOrganizations = vi.mocked(listOrganizations);
const mockedListPaymentStatuses = vi.mocked(listPaymentStatuses);
const mockedPreviewDealPayment = vi.mocked(previewDealPayment);

const PAYMENT: PaymentStatus = {
  id: "payment-1",
  milestone_sequence: 1,
  amount: "100",
  currency: "USD",
  status: "PENDING",
  reconciled_amount: null,
  last_checked_at: null,
  last_reconciled_at: null,
  provider: "PAYPAL",
  execution_mode: "PAYPAL_SANDBOX",
  reconciliation_source: "PAYPAL_SANDBOX",
};

describe("PaymentStatusPanel", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/");
    mockedPreviewDealPayment.mockResolvedValue({ provider: "PAYPAL", execution_mode: "PAYPAL_SANDBOX" });
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
    vi.useRealTimers();
    window.history.replaceState({}, "", "/");
  });

  it("shows a loading state", () => {
    mockedListPaymentStatuses.mockReturnValue(new Promise(() => {}));

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    expect(screen.getByRole("status")).toHaveTextContent(/loading payment status/i);
  });

  it("shows offline simulation evidence and never a PayPal action", async () => {
    mockedListPaymentStatuses.mockResolvedValue([{ ...PAYMENT, status: "PAID", reconciled_amount: "100",
      provider: "OFFLINE_DEMO", execution_mode: "OFFLINE_DEMO", reconciliation_source: "OFFLINE_DEMO",
      invoice_reference: "OFFLINE-intent-1", invoice_url: "https://www.sandbox.paypal.com/invoice/p/#malformed" }]);
    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);
    expect(await screen.findByText("Simulated paid")).toBeInTheDocument();
    expect(screen.getByText("Evidence: Simulation / OFFLINE_DEMO")).toBeInTheDocument();
    expect(screen.getByText("Invoice reference: OFFLINE-intent-1")).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("does not turn missing legacy provenance into verified payment", async () => {
    mockedListPaymentStatuses.mockResolvedValue([{ ...PAYMENT, status: "PAID", provider: undefined,
      execution_mode: undefined, reconciliation_source: undefined }]);
    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);
    expect(await screen.findByText("Recorded payment: evidence unknown")).toBeInTheDocument();
    expect(screen.queryByText(/confirmed the full/i)).not.toBeInTheDocument();
  });

  it("requires a loaded offline mode preview before confirmation", async () => {
    mockedListPaymentStatuses.mockResolvedValue([]);
    mockedGetCurrentAgreement.mockResolvedValue({ status: "COMMITTED" } as AgreementVersion);
    mockedListOrganizations.mockResolvedValue([{ id: "seller-org-1", legal_name: "Seller", country_code: "US", role: "ADMIN" }]);
    let resolvePreview!: (value: { provider: "OFFLINE_DEMO"; execution_mode: "OFFLINE_DEMO" }) => void;
    mockedPreviewDealPayment.mockReturnValue(new Promise((resolve) => { resolvePreview = resolve; }));
    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);
    fireEvent.click(await screen.findByRole("button", { name: "Request Payment" }));
    expect(screen.getByRole("button", { name: "Confirm & Send Invoice" })).toBeDisabled();
    await act(async () => resolvePreview({ provider: "OFFLINE_DEMO", execution_mode: "OFFLINE_DEMO" }));
    expect(screen.getByText("Offline demo: simulated payment")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Confirm & Send Invoice" }));
    expect(mockedAuthorizeDealPayment).toHaveBeenCalledWith("deal-1", expect.any(String), "OFFLINE_DEMO");
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

  it("shows cancelled payments as needing attention", async () => {
    mockedListPaymentStatuses.mockResolvedValue([{ ...PAYMENT, status: "CANCELLED" }]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    expect(await screen.findByText("Needs attention")).toBeInTheDocument();
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

    expect(mockedAuthorizeDealPayment).toHaveBeenCalledWith("deal-1", expect.any(String), "PAYPAL_SANDBOX");
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

    expect(mockedAuthorizeDealPayment).toHaveBeenCalledWith("deal-1", expect.any(String), "PAYPAL_SANDBOX");
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

  it("distinguishes scheduled outbox retries from the payment state", async () => {
    vi.setSystemTime(new Date("2026-10-31T10:42:00Z"));
    mockedListPaymentStatuses.mockResolvedValue([
      {
        ...PAYMENT,
        status: "CREATE_UNKNOWN",
        outbox_status: "PENDING",
        retry_count: 2,
        last_checked_at: "2026-10-31T10:40:00Z",
        failure_reason: "PayPal sandbox rate limit",
        retry_scheduled_at: "2026-10-31T10:42:45Z",
      } as PaymentStatus,
    ]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    expect(await screen.findByText("Automatic Retry Scheduled")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Payment request retry #2 in ~45 seconds. Cause: PayPal sandbox rate limit.",
      ),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Retrying")).toHaveLength(1);
  });

  it("shows unavailable retry timing and backend check without fabricating diagnostics", async () => {
    mockedListPaymentStatuses.mockResolvedValue([
      {
        ...PAYMENT,
        status: "CREATE_PENDING",
        outbox_status: "RETRYING",
        retry_count: 1,
        last_checked_at: null,
        failure_reason: null,
        next_retry_at: "2026-10-31T10:42:30Z",
      } as PaymentStatus,
    ]);

    render(<PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />);

    expect(await screen.findByText("Automatic Retry Scheduled")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Payment request retry #1: Retry time unavailable. Cause: Cause unavailable.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Last checked by backend: Unavailable")).toBeInTheDocument();
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
    await act(async () => {});
    fireEvent.click(screen.getByRole("button", { name: "Confirm & Send Invoice" }));
    expect(mockedAuthorizeDealPayment).toHaveBeenCalledWith("deal-1", expect.any(String), "PAYPAL_SANDBOX");
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

  it.each<PaymentIntentStatus>([
    "AUTHORIZED", "CREATE_PENDING", "CREATE_UNKNOWN", "PROVIDER_CREATED", "SENT",
    "PENDING", "PARTIALLY_PAID", "PAID", "FAILED", "CANCELLED",
  ])("uses the exact legacy polling classification for %s", async (status) => {
    vi.useFakeTimers();
    mockedListPaymentStatuses.mockResolvedValue([{ ...PAYMENT, status }]);
    const { unmount } = render(
      <PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />,
    );
    await act(async () => {});
    const terminal = ["PAID", "FAILED", "CANCELLED"].includes(status);
    expect(vi.getTimerCount()).toBe(terminal ? 0 : 1);
    await act(() => vi.advanceTimersByTimeAsync(9999));
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(1);
    await act(() => vi.advanceTimersByTimeAsync(1));
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(terminal ? 1 : 2);
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });

  it.each([
    { status: "AUTHORIZED", requires_polling: false, polls: false },
    { status: "PAID", requires_polling: true, polls: true },
  ] as const)("honors explicit requires_polling=$requires_polling over $status", async ({ status, requires_polling, polls }) => {
    vi.useFakeTimers();
    mockedListPaymentStatuses.mockResolvedValue([{ ...PAYMENT, status, requires_polling }]);
    const { unmount } = render(
      <PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />,
    );
    await act(async () => {});
    await act(() => vi.advanceTimersByTimeAsync(10000));
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(polls ? 2 : 1);
    unmount();
  });

  it.each(["empty", "terminal"])("stops polling on a %s result and resumes after refresh", async (result) => {
    vi.useFakeTimers();
    const stopped: PaymentStatus[] = result === "empty" ? [] : [
      { ...PAYMENT, id: "paid", status: "PAID", requires_polling: false },
      { ...PAYMENT, id: "failed", status: "FAILED", requires_polling: false },
      { ...PAYMENT, id: "cancelled", status: "CANCELLED", requires_polling: false },
    ];
    const mixed: PaymentStatus[] = [
      { ...PAYMENT, id: "paid", status: "PAID", requires_polling: false },
      { ...PAYMENT, status: "PARTIALLY_PAID", requires_polling: true },
    ];
    mockedListPaymentStatuses.mockResolvedValueOnce(mixed).mockResolvedValueOnce(stopped);
    const { unmount } = render(
      <PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />,
    );
    await act(async () => {});
    await act(() => vi.advanceTimersByTimeAsync(10000));
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(2);
    expect(vi.getTimerCount()).toBe(0);
    await act(() => vi.advanceTimersByTimeAsync(20000));
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(2);
    mockedListPaymentStatuses.mockResolvedValue(mixed);
    fireEvent.click(screen.getByRole("button", { name: "Refresh status" }));
    await act(async () => {});
    await act(() => vi.advanceTimersByTimeAsync(10000));
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(4);
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("does not overlap slow background polls and releases the guard after rejection", async () => {
    vi.useFakeTimers();
    let rejectPoll!: (reason: Error) => void;
    const slowPoll = new Promise<PaymentStatus[]>((_resolve, reject) => { rejectPoll = reject; });
    mockedListPaymentStatuses.mockResolvedValueOnce([PAYMENT]).mockReturnValueOnce(slowPoll);
    const { unmount } = render(
      <PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />,
    );
    await act(async () => {});
    await act(() => vi.advanceTimersByTimeAsync(40000));
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(2);
    expect(screen.getByText("Waiting for payment")).toBeInTheDocument();
    await act(async () => rejectPoll(new ApiError(503, "Try later")));
    expect(screen.getByText("Waiting for payment")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    mockedListPaymentStatuses.mockResolvedValueOnce([{ ...PAYMENT, status: "PAID", requires_polling: false }]);
    await act(() => vi.advanceTimersByTimeAsync(10000));
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(3);
    expect(screen.getByText("Paid")).toBeInTheDocument();
    expect(vi.getTimerCount()).toBe(0);
    unmount();
  });

  it.each(["reloadToken", "dealId", "sellerOrganizationId", "buyerOrganizationId"])("gates polling until the delayed prop initial snapshot commits after %s changes", async (changedProp) => {
    vi.useFakeTimers();
    let resolveInitial!: (payments: PaymentStatus[]) => void;
    mockedListPaymentStatuses
      .mockResolvedValueOnce([PAYMENT])
      .mockReturnValueOnce(new Promise((resolve) => { resolveInitial = resolve; }))
      .mockResolvedValue([{ ...PAYMENT, status: "PAID", requires_polling: false }]);
    const props = { dealId: "deal-1", sellerOrganizationId: "seller-org-1", buyerOrganizationId: "buyer-org-1", reloadToken: 0 };
    const { rerender, unmount } = render(<PaymentStatusPanel {...props} />);
    await act(async () => {});
    expect(screen.getByText("Waiting for payment")).toBeInTheDocument();

    rerender(<PaymentStatusPanel {...props} {...{ [changedProp]: changedProp === "reloadToken" ? 1 : "changed-id" }} />);
    await act(() => vi.advanceTimersByTimeAsync(20000));
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(2);
    expect(screen.getByText("Waiting for payment")).toBeInTheDocument();

    await act(async () => resolveInitial([PAYMENT]));
    await act(() => vi.advanceTimersByTimeAsync(10000));
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(3);
    expect(screen.getByText("Paid")).toBeInTheDocument();
    expect(vi.getTimerCount()).toBe(0);
    await act(() => vi.advanceTimersByTimeAsync(20000));
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(3);
    expect(screen.queryByText("Waiting for payment")).not.toBeInTheDocument();
    unmount();
  });

  it.each(["reloadToken", "dealId", "sellerOrganizationId", "buyerOrganizationId"])("discards and aborts old polls after %s changes", async (changedProp) => {
    vi.useFakeTimers();
    let resolvePoll!: (payments: PaymentStatus[]) => void;
    const slowPoll = new Promise<PaymentStatus[]>((resolve) => { resolvePoll = resolve; });
    mockedListPaymentStatuses.mockResolvedValueOnce([PAYMENT]).mockReturnValueOnce(slowPoll);
    const props = { dealId: "deal-1", sellerOrganizationId: "seller-org-1", buyerOrganizationId: "buyer-org-1", reloadToken: 0 };
    const { rerender, unmount } = render(<PaymentStatusPanel {...props} />);
    await act(async () => {});
    await act(() => vi.advanceTimersByTimeAsync(10000));
    const oldSignal = mockedListPaymentStatuses.mock.calls[1][1]?.signal;
    expect(oldSignal?.aborted).toBe(false);
    mockedListPaymentStatuses.mockResolvedValueOnce([{ ...PAYMENT, status: "PAID", requires_polling: false }]);
    rerender(<PaymentStatusPanel {...props} {...{ [changedProp]: changedProp === "reloadToken" ? 1 : "changed-id" }} />);
    await act(async () => {});
    expect(oldSignal?.aborted).toBe(true);
    await act(async () => resolvePoll([PAYMENT]));
    expect(screen.getByText("Paid")).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(20000));
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(3);
    unmount();
  });

  it.each([null, undefined, "invalid", "45", "10:42 AM", "2026-10-31T10:42:00"])("does not fabricate countdowns from %s", (timestamp) => {
    expect(formatCountdown(timestamp, Date.parse("2026-10-31T10:42:00Z"))).toBeNull();
  });

  it("uses a live valid retry schedule, not the legacy timestamp or backend check", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-31T10:42:00Z"));
    mockedListPaymentStatuses.mockResolvedValue([{
      ...PAYMENT, status: "CREATE_UNKNOWN", requires_polling: false,
      outbox_status: "PENDING", retry_count: 2,
      retry_scheduled_at: "2026-10-31T10:42:05Z",
      next_retry_at: "2026-10-31T10:43:00Z",
      last_checked_at: "2026-10-31T10:40:00Z",
    }]);
    const { unmount } = render(
      <PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />,
    );
    await act(async () => {});
    expect(screen.getByText(/retry #2 in ~5 seconds/)).toBeInTheDocument();
    expect(screen.getByText(/Last checked by backend:/)).not.toHaveTextContent("Unavailable");
    expect(screen.queryByText(/Last attempt:/)).not.toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(2000));
    expect(screen.getByText(/retry #2 in ~3 seconds/)).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(5000));
    expect(screen.getByText(/retry #2 in ~0 seconds/)).toBeInTheDocument();
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });

  it.each([null, "invalid", "45"])("renders unavailable retry timing for %s with no countdown timer", async (retry_scheduled_at) => {
    vi.useFakeTimers();
    mockedListPaymentStatuses.mockResolvedValue([{
      ...PAYMENT, status: "CREATE_UNKNOWN", requires_polling: false,
      outbox_status: "PENDING", retry_count: 2, retry_scheduled_at,
      last_checked_at: retry_scheduled_at,
      next_retry_at: "2026-10-31T10:42:45Z",
    }]);
    const { unmount } = render(
      <PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />,
    );
    await act(async () => {});
    expect(screen.getByText(/Retry time unavailable/)).toBeInTheDocument();
    expect(screen.getByText("Last checked by backend: Unavailable")).toBeInTheDocument();
    expect(screen.queryByText(/~45 seconds|Just now|Last attempt/)).not.toBeInTheDocument();
    expect(vi.getTimerCount()).toBe(0);
    unmount();
  });

  it.each(["refresh", "reloadToken", "dealId"])("discards an initial snapshot after %s starts a new generation", async (action) => {
    vi.useFakeTimers();
    let resolveInitial!: (payments: PaymentStatus[]) => void;
    mockedListPaymentStatuses.mockReturnValueOnce(new Promise((resolve) => { resolveInitial = resolve; }));
    const { rerender, unmount } = render(
      <PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />,
    );
    const oldSignal = mockedListPaymentStatuses.mock.calls[0][1]?.signal;
    mockedListPaymentStatuses.mockResolvedValueOnce([{ ...PAYMENT, status: "PAID", requires_polling: false }]);
    if (action === "refresh") {
      fireEvent.click(screen.getByRole("button", { name: "Refresh status" }));
    } else {
      rerender(<PaymentStatusPanel dealId={action === "dealId" ? "deal-2" : "deal-1"}
        sellerOrganizationId="seller-org-1" reloadToken={action === "reloadToken" ? 1 : 0} />);
    }
    await act(async () => {});
    expect(oldSignal?.aborted).toBe(true);
    await act(async () => resolveInitial([PAYMENT]));
    expect(screen.getByText("Paid")).toBeInTheDocument();
    expect(vi.getTimerCount()).toBe(0);
    unmount();
  });

  it("aborts a pending initial request on unmount", () => {
    mockedListPaymentStatuses.mockReturnValueOnce(new Promise(() => {}));
    const { unmount } = render(
      <PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />,
    );
    const signal = mockedListPaymentStatuses.mock.calls[0][1]?.signal;
    expect(signal?.aborted).toBe(false);
    unmount();
    expect(signal?.aborted).toBe(true);
  });

  it("discards a pending poll after payment authorization reloads the snapshot", async () => {
    vi.useFakeTimers();
    mockedGetCurrentAgreement.mockResolvedValue({ status: "COMMITTED" } as AgreementVersion);
    mockedListOrganizations.mockResolvedValue([
      { id: "seller-org-1", legal_name: "Seller Co", country_code: "CA", role: "ADMIN" },
    ]);
    let resolvePoll!: (payments: PaymentStatus[]) => void;
    mockedListPaymentStatuses.mockResolvedValueOnce([
      PAYMENT, { ...PAYMENT, id: "failed-payment", status: "FAILED", requires_polling: false },
    ]).mockReturnValueOnce(new Promise((resolve) => { resolvePoll = resolve; }));
    const { unmount } = render(
      <PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />,
    );
    await act(async () => {});
    await act(() => vi.advanceTimersByTimeAsync(10000));
    const oldSignal = mockedListPaymentStatuses.mock.calls[1][1]?.signal;
    mockedListPaymentStatuses.mockResolvedValueOnce([{ ...PAYMENT, status: "PAID", requires_polling: false }]);
    fireEvent.click(screen.getByRole("button", { name: "Retry Request" }));
    await act(async () => {});
    fireEvent.click(screen.getByRole("button", { name: "Confirm & Send Invoice" }));
    await act(async () => {});
    expect(mockedAuthorizeDealPayment).toHaveBeenCalledTimes(1);
    expect(oldSignal?.aborted).toBe(true);
    await act(async () => resolvePoll([PAYMENT]));
    expect(screen.getByText("Paid")).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(20000));
    expect(mockedListPaymentStatuses).toHaveBeenCalledTimes(3);
    unmount();
  });

  it.each(["PROCESSING", "PENDING", "DELIVERED", "FAILED"] as const)("never shows a retry countdown for $status without a scheduled retry", async (outbox_status) => {
    vi.useFakeTimers();
    mockedListPaymentStatuses.mockResolvedValue([{
      ...PAYMENT, status: "AUTHORIZED", requires_polling: false, outbox_status,
      retry_count: outbox_status === "PENDING" ? 0 : 2,
      lease_expires_at: "2026-10-31T10:42:45Z",
      next_retry_at: "2026-10-31T10:42:45Z",
      last_checked_at: "invalid",
    }]);
    const { unmount } = render(
      <PaymentStatusPanel dealId="deal-1" sellerOrganizationId="seller-org-1" />,
    );
    await act(async () => {});
    expect(screen.queryByText("Automatic Retry Scheduled")).not.toBeInTheDocument();
    expect(screen.getByText("Last checked by backend: Unavailable")).toBeInTheDocument();
    expect(vi.getTimerCount()).toBe(0);
    unmount();
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

    const pollSignal = mockedListPaymentStatuses.mock.calls[1][1]?.signal;
    expect(pollSignal?.aborted).toBe(false);
    unmount();
    expect(pollSignal?.aborted).toBe(true);

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
