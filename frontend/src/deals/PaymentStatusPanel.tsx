import { useEffect, useRef, useState } from "react";

import {
  ApiError,
  authorizeDealPayment,
  getCurrentAgreement,
  getOrganization,
  listOrganizations,
  listPaymentStatuses,
} from "../api/client";
import type { OrganizationDirectoryItem, PaymentStatus } from "../api/types";

/**
 * PAY-01 extended the payment status record with recipient details, invoice link,
 * and retry diagnostics. Keep the extended schema local to prevent transport widening.
 */
export interface ExtendedPaymentStatus extends PaymentStatus {
  recipient_email?: string | null;
  recipient_name?: string | null;
  recipient_country_code?: string | null;
  recipient_legal_name?: string | null;
  invoice_url?: string | null;
  invoice_number?: string | null;
  retry_count?: number;
  next_retry_at?: string | null;
  failure_reason?: string | null;
}

type PaymentState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "ready";
      payments: ExtendedPaymentStatus[];
      agreementCommitted: boolean;
      sellerMember: boolean;
      buyerMember: boolean;
      buyerOrganization: OrganizationDirectoryItem | null;
      milestone: { amount: string; currency: string } | null;
    };

interface RecipientPreview {
  legalName: string;
  countryCode: string;
  billingEmail: string;
  amount: { amount: string; currency: string } | null;
}

function firstMilestoneAmount(
  payments: PaymentStatus[],
  agreement: { terms: { payment_terms: Array<{ amount: { amount: string; currency: string } }> } } | null,
): { amount: string; currency: string } | null {
  const payment = payments[0];
  if (payment) {
    return { amount: payment.amount, currency: payment.currency };
  }
  return agreement?.terms?.payment_terms?.[0]?.amount ?? null;
}

function formatInvoiceAmount(amount: string, currency: string): string {
  const numericAmount = Number(amount);
  if (!Number.isFinite(numericAmount) || !/^[A-Z]{3}$/.test(currency)) {
    return `${currency} ${amount}`;
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    currencyDisplay: "code",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
    .format(numericAmount)
    .replace(/\u00a0/g, " ");
}

function textOrFallback(value: string | null | undefined, fallback: string): string {
  const trimmed = value?.trim();
  return trimmed ? trimmed : fallback;
}

export function extractInvoiceNumber(payment: ExtendedPaymentStatus): string {
  if (payment.invoice_number?.trim()) {
    return payment.invoice_number.trim();
  }
  if (payment.invoice_url) {
    const hashMatch = payment.invoice_url.match(/#([A-Za-z0-9._-]+)/);
    if (hashMatch) {
      return hashMatch[1];
    }
    const pathMatch = payment.invoice_url.match(/\/p\/#?([A-Za-z0-9._-]+)/);
    if (pathMatch) {
      return pathMatch[1];
    }
  }
  return `INV-${payment.id.slice(0, 8).toUpperCase()}`;
}

export function formatCountdown(nextRetryAt: string | null | undefined, nowMs: number): number {
  if (!nextRetryAt) return 45;
  const parsedInt = parseInt(nextRetryAt, 10);
  if (!isNaN(parsedInt) && !nextRetryAt.includes("-") && !nextRetryAt.includes(":")) {
    return Math.max(0, parsedInt);
  }
  try {
    const targetMs = new Date(nextRetryAt).getTime();
    if (isNaN(targetMs)) return 45;
    const diffSec = Math.round((targetMs - nowMs) / 1000);
    return Math.max(0, diffSec);
  } catch {
    return 45;
  }
}

export function formatLastAttempt(timestamp: string | null | undefined): string {
  if (!timestamp) return "Just now";
  const trimmed = timestamp.trim();
  if (/^\d{1,2}:\d{2}\s*(?:AM|PM)?$/i.test(trimmed)) {
    return trimmed;
  }
  try {
    const date = new Date(trimmed);
    if (isNaN(date.getTime())) return trimmed;
    return date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  } catch {
    return trimmed;
  }
}

function describeStatus(status: string): { label: string; detail: string } {
  switch (status) {
    case "AUTHORIZED":
    case "CREATE_PENDING":
    case "PROVIDER_CREATED":
      return {
        label: "Preparing payment request",
        detail: "The backend is processing the payment request.",
      };
    case "CREATE_UNKNOWN":
      return {
        label: "Payment request needs reconciliation",
        detail: "Wait for the backend to check the provider before retrying.",
      };
    case "RETRYING":
      return {
        label: "Retrying payment request",
        detail: "The backend is retrying the payment request with PayPal.",
      };
    case "SENT":
    case "PENDING":
      return { label: "Waiting for payment", detail: "The backend has not confirmed payment yet." };
    case "PARTIALLY_PAID":
      return { label: "Partially paid", detail: "The backend has confirmed a partial payment." };
    case "PAID":
      return { label: "Paid", detail: "The backend has confirmed the full milestone amount." };
    case "FAILED":
      return { label: "Needs attention", detail: "The payment request did not complete." };
    case "CANCELLED":
      return { label: "Needs attention", detail: "The payment request did not complete." };
    default:
      return {
        label: "Status unavailable",
        detail: "The backend returned a payment state this screen does not recognize.",
      };
  }
}

function displayAmount(amount: string, currency: string): string {
  return `${currency} ${amount}`;
}

interface PaymentStatusPanelProps {
  dealId: string;
  sellerOrganizationId: string;
  reloadToken?: number;
  buyerOrganizationId?: string;
}

export default function PaymentStatusPanel({
  dealId,
  sellerOrganizationId,
  reloadToken = 0,
  buyerOrganizationId,
}: PaymentStatusPanelProps) {
  const [state, setState] = useState<PaymentState>({ status: "loading" });
  const [reloadCount, setReloadCount] = useState(0);
  const [authorizing, setAuthorizing] = useState(false);
  const [authorizationError, setAuthorizationError] = useState("");
  const [authorizationNotice, setAuthorizationNotice] = useState("");
  const [confirmationOpen, setConfirmationOpen] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const idempotencyKey = useRef<string | null>(null);
  const requestButtonRef = useRef<HTMLButtonElement>(null);
  const refreshButtonRef = useRef<HTMLButtonElement>(null);
  const confirmationDialogRef = useRef<HTMLDivElement>(null);

  const recipientPreview: RecipientPreview | null =
    state.status === "ready"
      ? {
          legalName: textOrFallback(
            state.payments[0]?.recipient_legal_name ??
              state.payments[0]?.recipient_name ??
              state.buyerOrganization?.legal_name,
            "Not available",
          ),
          countryCode: textOrFallback(
            state.payments[0]?.recipient_country_code ??
              state.buyerOrganization?.country_code,
            "Not available",
          ),
          billingEmail: textOrFallback(
            state.payments[0]?.recipient_email ??
              (state.buyerOrganization as { billing_email?: string; email?: string } | null)?.billing_email ??
              (state.buyerOrganization as { billing_email?: string; email?: string } | null)?.email,
            "Resolved by the backend at issuance",
          ),
          amount: state.milestone,
        }
      : null;

  useEffect(() => {
    let cancelled = false;
    void Promise.all([
      listPaymentStatuses(dealId) as Promise<ExtendedPaymentStatus[]>,
      getCurrentAgreement(dealId).catch((caught: unknown) => {
        if (caught instanceof ApiError && caught.status === 404) return null;
        throw caught;
      }),
      listOrganizations(),
    ]).then(
      ([payments, agreement, organizations]) => {
        if (cancelled) return;

        const buyerOrgId = buyerOrganizationId ?? agreement?.terms?.buyer_id;
        const isSellerMember = organizations.some((org) => org.id === sellerOrganizationId);
        const isBuyerMember = buyerOrgId ? organizations.some((org) => org.id === buyerOrgId) : false;

        setState({
          status: "ready",
          payments,
          agreementCommitted: agreement?.status === "COMMITTED",
          sellerMember: isSellerMember,
          buyerMember: isBuyerMember,
          buyerOrganization: null,
          milestone: firstMilestoneAmount(payments, agreement),
        });

        if (!buyerOrgId) return;

        void getOrganization(buyerOrgId)
          .catch(() => null)
          .then((buyerOrganization) => {
            if (cancelled || !buyerOrganization) return;
            setState((prev) =>
              prev.status === "ready" ? { ...prev, buyerOrganization } : prev,
            );
          });
      },
      (caught: unknown) => {
        if (cancelled) return;
        setState({
          status: "error",
          message:
            caught instanceof ApiError
              ? caught.message
              : "Unable to load payment status and seller access. Please try again.",
        });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [buyerOrganizationId, dealId, reloadCount, reloadToken, sellerOrganizationId]);

  // Transitional state auto-polling (every 10 seconds)
  const hasTransitionalPayment =
    state.status === "ready" &&
    state.payments.some(
      (payment) =>
        payment.status === "CREATE_PENDING" ||
        payment.status === "RETRYING",
    );

  useEffect(() => {
    if (!hasTransitionalPayment) return;

    const intervalId = window.setInterval(() => {
      void (listPaymentStatuses(dealId) as Promise<ExtendedPaymentStatus[]>)
        .then((payments) => {
          setState((prev) => (prev.status === "ready" ? { ...prev, payments } : prev));
        })
        .catch(() => {
          // Do not overwrite ready state on transient network poll error
        });
    }, 10000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [dealId, hasTransitionalPayment]);

  // Live countdown ticker for RETRYING status
  const hasRetryingPayment =
    state.status === "ready" &&
    state.payments.some((payment) => payment.status === "RETRYING");

  useEffect(() => {
    if (!hasRetryingPayment) return;

    const intervalId = window.setInterval(() => {
      setNow(Date.now());
    }, 1000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [hasRetryingPayment]);

  useEffect(() => {
    if (!confirmationOpen) return;

    const focusReturnTarget = requestButtonRef.current;
    confirmationDialogRef.current?.focus();

    function handleDialogKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        setConfirmationOpen(false);
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = confirmationDialogRef.current?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable?.length) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || document.activeElement === confirmationDialogRef.current)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleDialogKeyDown);
    return () => {
      document.removeEventListener("keydown", handleDialogKeyDown);
      if (focusReturnTarget?.isConnected && !focusReturnTarget.disabled) {
        focusReturnTarget.focus();
      } else if (refreshButtonRef.current?.isConnected && !refreshButtonRef.current.disabled) {
        refreshButtonRef.current.focus();
      }
    };
  }, [confirmationOpen]);

  function retry() {
    setAuthorizationError("");
    setAuthorizationNotice("");
    setState({ status: "loading" });
    setReloadCount((count) => count + 1);
  }

  function openRecipientConfirmation() {
    if (state.status !== "ready") return;
    setConfirmationOpen(true);
  }

  function cancelRecipientConfirmation() {
    setConfirmationOpen(false);
  }

  function confirmRecipientAndSend() {
    setConfirmationOpen(false);
    void authorizePayment();
  }

  async function authorizePayment() {
    if (state.status !== "ready" || !state.agreementCommitted || !state.sellerMember) return;
    setAuthorizing(true);
    setAuthorizationError("");
    setAuthorizationNotice("");
    idempotencyKey.current ??= crypto.randomUUID();
    try {
      await authorizeDealPayment(dealId, idempotencyKey.current);
      idempotencyKey.current = null;
      setAuthorizationNotice("The payment request is queued for the backend worker.");
      setState({ status: "loading" });
      setReloadCount((count) => count + 1);
    } catch (caught) {
      setAuthorizationError(
        caught instanceof ApiError ? caught.message : "Unable to queue the payment request.",
      );
    } finally {
      setAuthorizing(false);
    }
  }

  async function handleRetryRequest() {
    setAuthorizing(true);
    setAuthorizationError("");
    setAuthorizationNotice("");
    const retryKey = crypto.randomUUID();
    try {
      await authorizeDealPayment(dealId, retryKey);
      setAuthorizationNotice("The payment request retry is queued for the backend worker.");
      setState({ status: "loading" });
      setReloadCount((count) => count + 1);
    } catch (caught) {
      setAuthorizationError(
        caught instanceof ApiError ? caught.message : "Unable to retry the payment request.",
      );
    } finally {
      setAuthorizing(false);
    }
  }

  const isBuyer = state.status === "ready" && (state.buyerMember || !state.sellerMember);
  const isSeller = state.status === "ready" && state.sellerMember;

  return (
    <section className="card payment-status" aria-labelledby="payment-status-heading">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Backend confirmed</span>
          <h2 id="payment-status-heading">Payment status</h2>
        </div>
        <button
          ref={refreshButtonRef}
          type="button"
          className="button secondary button--compact"
          onClick={retry}
        >
          Refresh status
        </button>
      </div>

      {state.status === "loading" ? <p role="status">Loading payment status…</p> : null}
      {state.status === "error" ? (
        <div className="payment-status__message" role="alert">
          <p>Payment status is unavailable. {state.message}</p>
          <button type="button" className="button secondary button--compact" onClick={retry}>
            Try again
          </button>
        </div>
      ) : null}
      {state.status === "ready" && state.payments.length === 0 ? (
        <>
          {state.agreementCommitted && state.sellerMember ? (
            <div className="payment-status__message">
              <p>The agreement is committed. The seller can authorize its payment milestone.</p>
              <button
                ref={requestButtonRef}
                type="button"
                className="button"
                disabled={authorizing}
                aria-haspopup="dialog"
                onClick={openRecipientConfirmation}
              >
                {authorizing ? "Queuing payment request…" : "Request Payment"}
              </button>
            </div>
          ) : (
            <p className="payment-status__message" role="status">
              No payment request is available yet. A seller can authorize one after both parties
              commit the agreement. A browser return does not change this status.
            </p>
          )}
        </>
      ) : null}
      {authorizationNotice ? <p className="payment-status__message" role="status">{authorizationNotice}</p> : null}
      {authorizationError ? <p className="payment-status__message" role="alert">{authorizationError}</p> : null}
      {state.status === "ready" && state.payments.length > 0 ? (
        <div className="payment-status__list">
          {state.payments.map((payment) => {
            const presentation = describeStatus(payment.status);
            const paidAmount = payment.reconciled_amount;
            const invoiceNum = extractInvoiceNumber(payment);
            const isFailed = payment.status === "FAILED" || payment.status === "CANCELLED";
            const isRetrying = payment.status === "RETRYING";

            return (
              <article className="payment-status__item" key={payment.id}>
                <div className="payment-status__summary">
                  <div>
                    <h3>Milestone {payment.milestone_sequence}</h3>
                    <p>{displayAmount(payment.amount, payment.currency)}</p>
                  </div>
                  <span className={`badge ${isRetrying ? "badge--retrying" : isFailed ? "badge--danger" : ""}`}>
                    {presentation.label}
                  </span>
                </div>
                <p className="muted">{presentation.detail}</p>
                {payment.status === "PARTIALLY_PAID" && paidAmount !== null ? (
                  <p className="payment-status__amount">
                    Confirmed so far: {displayAmount(paidAmount, payment.currency)} of{" "}
                    {displayAmount(payment.amount, payment.currency)}
                  </p>
                ) : null}
                {payment.last_checked_at ? (
                  <p className="payment-status__checked">
                    Last checked by backend: {new Date(payment.last_checked_at).toLocaleString()}
                  </p>
                ) : null}

                {/* Retrying Observability Widget */}
                {isRetrying ? (
                  <div className="payment-status__retry-card" role="status">
                    <div className="payment-status__retry-header">
                      <span className="badge badge--retrying">Retrying</span>
                      <h4>Automatic Retry Scheduled</h4>
                    </div>
                    <p className="payment-status__retry-meta">
                      Payment request retry #{payment.retry_count ?? 1} in ~{formatCountdown(payment.next_retry_at, now)} seconds.
                      {" "}Last attempt: {formatLastAttempt(payment.last_checked_at)}.
                      {" "}Cause: {payment.failure_reason || "PayPal sandbox rate limit"}.
                    </p>
                  </div>
                ) : null}

                {/* Failed State Observability Widget */}
                {isFailed ? (
                  <div className="payment-status__failure-card" role="alert">
                    <div className="payment-status__failure-header">
                      <span className="badge badge--danger">Failed</span>
                      <h4>Payment Request Failed</h4>
                    </div>
                    <p className="payment-status__failure-cause">
                      <strong>Cause:</strong> {payment.failure_reason || "Payment processing encountered an error."}
                    </p>
                    <button
                      type="button"
                      className="button button--compact payment-status__retry-button"
                      disabled={authorizing}
                      onClick={handleRetryRequest}
                    >
                      {authorizing ? "Retrying…" : "Retry Request"}
                    </button>
                  </div>
                ) : null}

                {/* Buyer Invoice & Pay Action */}
                {payment.invoice_url && isBuyer ? (
                  <div className="payment-status__invoice-card">
                    <div className="payment-status__invoice-card-header">
                      <span className="eyebrow">PayPal Sandbox invoice ready</span>
                      <p className="payment-status__invoice-number">
                        Invoice #: <strong>{invoiceNum}</strong>
                      </p>
                    </div>
                    <a
                      href={payment.invoice_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="button payment-status__pay-button"
                    >
                      💳 View &amp; Pay PayPal Invoice
                    </a>
                    <div className="payment-status__instructions">
                      <h4>Payment Instructions</h4>
                      <p>
                        Review your order details and milestone amount on PayPal. Click the button above to authorize
                        your payment in PayPal Sandbox. SyncAlly will automatically detect the payment confirmation
                        and mark this milestone as paid.
                      </p>
                    </div>
                  </div>
                ) : null}

                {/* Seller Invoice Reference */}
                {payment.invoice_url && isSeller && !isBuyer ? (
                  <div className="payment-status__seller-invoice">
                    <p>
                      Invoice #: <strong>{invoiceNum}</strong> issued to buyer.
                    </p>
                    <a
                      href={payment.invoice_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="button secondary button--compact"
                    >
                      View PayPal Invoice
                    </a>
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      ) : null}
      <p className="payment-status__footnote">
        This view uses saved backend status. PayPal return pages and browser redirects are not
        payment evidence.
      </p>

      {confirmationOpen && recipientPreview ? (
        <div
          className="manual-fact-modal-backdrop"
          role="presentation"
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              cancelRecipientConfirmation();
            }
          }}
        >
          <div
            ref={confirmationDialogRef}
            className="manual-fact-modal invoice-recipient-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="invoice-recipient-title"
            aria-describedby="invoice-recipient-notice"
            tabIndex={-1}
          >
            <div className="panel-head">
              <div>
                <span className="eyebrow">Payment authorization</span>
                <h3 id="invoice-recipient-title">Confirm Invoice Recipient</h3>
              </div>
              <button
                type="button"
                className="button ghost"
                onClick={cancelRecipientConfirmation}
                aria-label="Close recipient confirmation"
              >
                ✕
              </button>
            </div>

            <p className="muted">
              Read back the recipient details before authorizing PayPal to issue this invoice.
            </p>

            <dl className="invoice-recipient-dialog__details">
              <div>
                <dt>Buyer legal name</dt>
                <dd>{recipientPreview.legalName}</dd>
              </div>
              <div>
                <dt>Registered country code</dt>
                <dd>{recipientPreview.countryCode}</dd>
              </div>
              <div>
                <dt>Recipient billing email</dt>
                <dd>{recipientPreview.billingEmail}</dd>
              </div>
              <div>
                <dt>Milestone amount</dt>
                <dd className="invoice-recipient-dialog__amount">
                  {recipientPreview.amount
                    ? formatInvoiceAmount(recipientPreview.amount.amount, recipientPreview.amount.currency)
                    : "Amount unavailable"}
                </dd>
              </div>
            </dl>

            <p id="invoice-recipient-notice" className="invoice-recipient-dialog__notice">
              This will create a formal PayPal invoice dispatched to the recipient above.
            </p>

            <div className="invoice-recipient-dialog__actions">
              <button type="button" className="button secondary" onClick={cancelRecipientConfirmation}>
                Cancel
              </button>
              <button type="button" className="button" onClick={confirmRecipientAndSend}>
                Confirm &amp; Send Invoice
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
