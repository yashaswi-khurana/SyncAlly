import { useEffect, useState } from "react";

import { ApiError, listPaymentStatuses } from "../api/client";
import type { PaymentStatus } from "../api/types";

type PaymentState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; payments: PaymentStatus[] };

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
}

export default function PaymentStatusPanel({ dealId }: PaymentStatusPanelProps) {
  const [state, setState] = useState<PaymentState>({ status: "loading" });
  const [reloadCount, setReloadCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    void listPaymentStatuses(dealId).then(
      (payments) => {
        if (!cancelled) setState({ status: "ready", payments });
      },
      (caught: unknown) => {
        if (cancelled) return;
        setState({
          status: "error",
          message:
            caught instanceof ApiError
              ? caught.message
              : "Unable to load payment status. Please try again.",
        });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [dealId, reloadCount]);

  function retry() {
    setState({ status: "loading" });
    setReloadCount((count) => count + 1);
  }

  return (
    <section className="card payment-status" aria-labelledby="payment-status-heading">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Backend confirmed</span>
          <h2 id="payment-status-heading">Payment status</h2>
        </div>
        <button type="button" className="button secondary button--compact" onClick={retry}>
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
        <p className="payment-status__message" role="status">
          No payment request is available yet. The backend will show one after it creates a request
          for a committed agreement. A browser return does not change this status.
        </p>
      ) : null}
      {state.status === "ready" && state.payments.length > 0 ? (
        <div className="payment-status__list">
          {state.payments.map((payment) => {
            const presentation = describeStatus(payment.status);
            const paidAmount = payment.reconciled_amount;
            return (
              <article className="payment-status__item" key={payment.id}>
                <div className="payment-status__summary">
                  <div>
                    <h3>Milestone {payment.milestone_sequence}</h3>
                    <p>{displayAmount(payment.amount, payment.currency)}</p>
                  </div>
                  <span className="badge">{presentation.label}</span>
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
              </article>
            );
          })}
        </div>
      ) : null}
      <p className="payment-status__footnote">
        This view uses saved backend status. PayPal return pages and browser redirects are not
        payment evidence.
      </p>
    </section>
  );
}
