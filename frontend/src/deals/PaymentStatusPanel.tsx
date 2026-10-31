import { useEffect, useRef, useState } from "react";

import {
  ApiError,
  authorizeDealPayment,
  getCurrentAgreement,
  getOrganization,
  listOrganizations,
  listPaymentStatuses,
  previewDealPayment,
} from "../api/client";
import type { OrganizationDirectoryItem, PaymentPreview, PaymentStatus } from "../api/types";

type PaymentState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "ready";
      payments: PaymentStatus[];
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

export function extractInvoiceNumber(payment: PaymentStatus): string {
  if (payment.invoice_reference) return payment.invoice_reference;
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

function parseTimestamp(timestamp: string | null | undefined): number | null {
  if (!timestamp || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(timestamp)) return null;
  const targetMs = Date.parse(timestamp);
  return Number.isFinite(targetMs) ? targetMs : null;
}

export function formatCountdown(timestamp: string | null | undefined, nowMs: number): number | null {
  const targetMs = parseTimestamp(timestamp);
  return targetMs === null ? null : Math.max(0, Math.round((targetMs - nowMs) / 1000));
}

function requiresPolling(payment: PaymentStatus): boolean {
  return payment.requires_polling ?? [
    "AUTHORIZED", "CREATE_PENDING", "CREATE_UNKNOWN", "PROVIDER_CREATED",
    "SENT", "PENDING", "PARTIALLY_PAID",
  ].includes(payment.status);
}

function hasScheduledRetry(payment: PaymentStatus): boolean {
  return payment.outbox_status === "RETRYING" ||
    (payment.outbox_status === "PENDING" && (payment.retry_count ?? 0) > 0);
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
  const [paymentPreview, setPaymentPreview] = useState<PaymentPreview | null>(null);
  const previewSequenceRef = useRef(0);
  const [now, setNow] = useState(() => Date.now());
  const idempotencyKey = useRef<string | null>(null);
  const requestButtonRef = useRef<HTMLButtonElement>(null);
  const refreshButtonRef = useRef<HTMLButtonElement>(null);
  const confirmationDialogRef = useRef<HTMLDivElement>(null);
  const requestGenerationRef = useRef(0);
  const committedGenerationRef = useRef(0);

  const recipientPreview: RecipientPreview | null =
    state.status === "ready"
      ? {
          legalName: textOrFallback(
              state.payments[0]?.recipient_name ??
              state.buyerOrganization?.legal_name,
            "Not available",
          ),
          countryCode: textOrFallback(
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
    const controller = new AbortController();
    const currentGeneration = ++requestGenerationRef.current;
    void Promise.all([
      listPaymentStatuses(dealId, { signal: controller.signal }),
      getCurrentAgreement(dealId).catch((caught: unknown) => {
        if (caught instanceof ApiError && caught.status === 404) return null;
        throw caught;
      }),
      listOrganizations(),
    ]).then(
      ([payments, agreement, organizations]) => {
        if (cancelled || currentGeneration !== requestGenerationRef.current) return;

        const buyerOrgId = buyerOrganizationId ?? agreement?.terms?.buyer_id;
        const isSellerMember = organizations.some((org) => org.id === sellerOrganizationId);
        const isBuyerMember = buyerOrgId ? organizations.some((org) => org.id === buyerOrgId) : false;

        committedGenerationRef.current = currentGeneration;
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
            if (cancelled || currentGeneration !== requestGenerationRef.current || !buyerOrganization) return;
            setState((prev) =>
              prev.status === "ready" ? { ...prev, buyerOrganization } : prev,
            );
          });
      },
      (caught: unknown) => {
        if (cancelled || currentGeneration !== requestGenerationRef.current) return;
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
      controller.abort();
    };
  }, [buyerOrganizationId, dealId, reloadCount, reloadToken, sellerOrganizationId]);

  const hasTransitionalPayment =
    state.status === "ready" &&
    state.payments.some(requiresPolling);

  useEffect(() => {
    if (!hasTransitionalPayment) return;

    let cancelled = false;
    let inFlight = false;
    const controller = new AbortController();

    const intervalId = window.setInterval(() => {
      if (inFlight || committedGenerationRef.current !== requestGenerationRef.current) return;
      inFlight = true;
      const pollGeneration = requestGenerationRef.current;

      void listPaymentStatuses(dealId, { signal: controller.signal })
        .then((payments) => {
          if (cancelled || pollGeneration !== requestGenerationRef.current) return;
          setState((prev) => (prev.status === "ready" ? { ...prev, payments } : prev));
        })
        .catch(() => undefined)
        .finally(() => {
          inFlight = false;
        });
    }, 10000);

    return () => {
      cancelled = true;
      controller.abort();
      window.clearInterval(intervalId);
    };
  }, [buyerOrganizationId, dealId, hasTransitionalPayment, reloadCount, reloadToken, sellerOrganizationId]);

  const hasRetryingPayment =
    state.status === "ready" &&
    state.payments.some((payment) => hasScheduledRetry(payment) &&
      formatCountdown(payment.retry_scheduled_at, now) !== null);

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
    requestGenerationRef.current += 1;
    setAuthorizationError("");
    setAuthorizationNotice("");
    setState({ status: "loading" });
    setReloadCount((count) => count + 1);
  }

  async function openRecipientConfirmation() {
    if (state.status !== "ready") return;
    const generation = requestGenerationRef.current;
    const sequence = ++previewSequenceRef.current;
    setPaymentPreview(null);
    setAuthorizationError("");
    setConfirmationOpen(true);
    try {
      const preview = await previewDealPayment(dealId);
      if (generation === requestGenerationRef.current && sequence === previewSequenceRef.current) {
        setPaymentPreview(preview);
      }
    } catch (caught) {
      if (generation === requestGenerationRef.current && sequence === previewSequenceRef.current) {
        setAuthorizationError(caught instanceof ApiError ? caught.message : "Payment mode preview unavailable.");
      }
    }
  }

  function cancelRecipientConfirmation() {
    setConfirmationOpen(false);
  }

  function confirmRecipientAndSend() {
    if (!paymentPreview) return;
    setConfirmationOpen(false);
    void authorizePayment();
  }

  async function authorizePayment() {
    if (!canRequestPayment) return;
    setAuthorizing(true);
    setAuthorizationError("");
    setAuthorizationNotice("");
    idempotencyKey.current ??= crypto.randomUUID();
    try {
      const result = await authorizeDealPayment(dealId, idempotencyKey.current, paymentPreview?.execution_mode);
      idempotencyKey.current = null;
      setAuthorizationNotice(`The payment request is queued for the backend worker. Mode: ${result.execution_mode ?? "Unknown"}.`);
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

  const canRequestPayment =
    state.status === "ready" && state.agreementCommitted && state.sellerMember;
  const isBuyer = state.status === "ready" && (state.buyerMember || !state.sellerMember);
  const isSeller = state.status === "ready" && state.sellerMember;

  return (
    <section className="card payment-status" aria-labelledby="payment-status-heading">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Persisted payment record</span>
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
          {canRequestPayment ? (
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
            const offline = payment.provider === "OFFLINE_DEMO" && payment.execution_mode === "OFFLINE_DEMO";
            const sandbox = payment.provider === "PAYPAL" && payment.execution_mode === "PAYPAL_SANDBOX";
            const trustedSource = (offline && payment.reconciliation_source === "OFFLINE_DEMO") ||
              (sandbox && payment.reconciliation_source === "PAYPAL_SANDBOX");
            const paymentProgress = payment.status === "PAID" || payment.status === "PARTIALLY_PAID";
            if (paymentProgress && !trustedSource) {
              presentation.label = "Recorded payment: evidence unknown";
              presentation.detail = "Legacy or missing provenance is not verified payment evidence.";
            } else if (offline && paymentProgress) {
              presentation.label = payment.status === "PAID" ? "Simulated paid" : "Simulated partial payment";
              presentation.detail = "Offline demo observation only. No money was transferred.";
            }
            const paidAmount = payment.reconciled_amount;
            const invoiceNum = extractInvoiceNumber(payment);
            const isFailed = payment.status === "FAILED" || payment.status === "CANCELLED";
            const isRetrying = hasScheduledRetry(payment);
            const countdown = formatCountdown(payment.retry_scheduled_at, now);
            const backendCheckedAt = parseTimestamp(payment.last_checked_at);

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
                <p>{offline ? "Offline demo" : sandbox ? "PayPal Sandbox: not production" : "Payment mode unknown"}</p>
                <p>Evidence: {trustedSource ? offline ? "Simulation / OFFLINE_DEMO" : "Provider / PAYPAL_SANDBOX" : payment.reconciliation_source === "NONE" ? "Not reconciled" : "Legacy or unknown, unverified"}</p>
                {offline && payment.invoice_reference ? <p>Invoice reference: {payment.invoice_reference}</p> : null}
                {payment.status === "PARTIALLY_PAID" && paidAmount !== null ? (
                  <p className="payment-status__amount">
                    {offline ? "Simulated so far" : trustedSource ? "Confirmed so far" : "Recorded so far"}: {displayAmount(paidAmount, payment.currency)} of{" "}
                    {displayAmount(payment.amount, payment.currency)}
                  </p>
                ) : null}
                <p className="payment-status__checked">
                  Last checked by backend: {backendCheckedAt !== null
                    ? new Date(backendCheckedAt).toLocaleString() : "Unavailable"}
                </p>

                {/* Retrying Observability Widget */}
                {isRetrying ? (
                  <div className="payment-status__retry-card" role="status">
                    <div className="payment-status__retry-header">
                      <span className="badge badge--retrying">Retrying</span>
                      <h4>Automatic Retry Scheduled</h4>
                    </div>
                    <p className="payment-status__retry-meta">
                      Payment request retry #{payment.retry_count ?? 0}{countdown === null
                        ? ": Retry time unavailable." : ` in ~${countdown} seconds.`}
                      {" "}Cause: {payment.failure_reason || "Cause unavailable"}.
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
                    {canRequestPayment ? (
                      <button
                        type="button"
                        className="button button--compact payment-status__retry-button"
                        disabled={authorizing}
                        onClick={openRecipientConfirmation}
                      >
                        {authorizing ? "Retrying…" : "Retry Request"}
                      </button>
                    ) : null}
                  </div>
                ) : null}

                {/* Buyer Invoice & Pay Action */}
                {sandbox && payment.invoice_url && isBuyer ? (
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
                {sandbox && payment.invoice_url && isSeller && !isBuyer ? (
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
              {paymentPreview?.execution_mode === "OFFLINE_DEMO" ? "Offline demo: simulated invoice, no money transfer or recipient email." : "Review the recipient and execution mode before authorization."}
            </p>

            <dl className="invoice-recipient-dialog__details">
              <div>
                <dt>Payment mode</dt>
                <dd>{paymentPreview ? paymentPreview.execution_mode === "OFFLINE_DEMO" ? "Offline demo: simulated payment" : "PayPal Sandbox: not production" : "Loading payment mode..."}</dd>
              </div>
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
              {paymentPreview?.execution_mode === "OFFLINE_DEMO" ? "This queues an offline simulated invoice only. It does not mark the payment paid." : paymentPreview ? "This will create a formal PayPal invoice dispatched to the recipient above." : "Payment mode must be available before confirmation."}
            </p>

            <div className="invoice-recipient-dialog__actions">
              <button type="button" className="button secondary" onClick={cancelRecipientConfirmation}>
                Cancel
              </button>
              <button type="button" className="button" disabled={!paymentPreview || authorizing} onClick={confirmRecipientAndSend}>
                Confirm &amp; Send Invoice
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
