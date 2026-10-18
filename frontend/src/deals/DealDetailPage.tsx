import { useEffect, useState } from "react";

import { ApiError, getDeal } from "../api/client";
import type { Deal } from "../api/types";
import Reveal from "../ui/Reveal";
import DealConstellation from "./DealConstellation";
import DealConversationReview from "./DealConversationReview";

type DealState =
  | { status: "loading" }
  | { status: "not-found" }
  | { status: "error"; message: string }
  | { status: "ready"; deal: Deal };

interface DealDetailPageProps {
  dealId: string;
  onBackToDeals: () => void;
}

export default function DealDetailPage({ dealId, onBackToDeals }: DealDetailPageProps) {
  const [state, setState] = useState<DealState>({ status: "loading" });
  const [reloadCount, setReloadCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const deal = await getDeal(dealId);
        if (!cancelled) {
          setState({ status: "ready", deal });
        }
      } catch (caught) {
        if (cancelled) {
          return;
        }
        if (caught instanceof ApiError && caught.status === 404) {
          setState({ status: "not-found" });
        } else if (caught instanceof ApiError) {
          setState({ status: "error", message: caught.message });
        } else {
          setState({ status: "error", message: "Unable to load this deal. Please try again." });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [dealId, reloadCount]);

  function retryDeal() {
    setState({ status: "loading" });
    setReloadCount((count) => count + 1);
  }

  if (state.status === "loading") {
    return (
      <section className="card" aria-live="polite">
        <p role="status">Loading deal…</p>
      </section>
    );
  }

  if (state.status === "not-found") {
    return (
      <section className="card" role="alert">
        <h2>Deal not found</h2>
        <p className="muted" style={{ marginTop: 10 }}>
          This deal does not exist, or your organization is not a participant.
        </p>
        <div className="actions">
          <button type="button" className="button" onClick={onBackToDeals}>
            Back to deals
          </button>
        </div>
      </section>
    );
  }

  if (state.status === "error") {
    return (
      <section className="card" role="alert">
        <h2>We could not load this deal</h2>
        <p className="muted" style={{ marginTop: 10 }}>
          {state.message}
        </p>
        <div className="actions">
          <button type="button" className="button" onClick={retryDeal}>
            Try again
          </button>
        </div>
      </section>
    );
  }

  const { deal } = state;
  return (
    <Reveal>
      <div className="workspace deal-workspace">
        <section className="deal-room" aria-labelledby="deal-detail-heading">
          <div className="deal-room__topline">
            <button type="button" className="deal-room__back" onClick={onBackToDeals}>
              <span aria-hidden="true">←</span> Back to deals
            </button>
            <span className="deal-room__index">TRANSACTION ROOM / {deal.id.slice(0, 8)}</span>
          </div>

          <div className="deal-room__main">
            <div className="deal-room__copy">
              <div className="deal-room__kicker">
                <span className="eyebrow">The shared record</span>
                <span className="deal-room__version">DEAL VERSION {String(deal.version).padStart(2, "0")}</span>
              </div>
              <h1 id="deal-detail-heading">
                One deal.<br />
                <span>Two perspectives.</span>
              </h1>
              <p className="deal-room__lede">
                Read the conversation and review source-linked facts here. A fact review records a
                decision; it does not approve or commit an agreement.
              </p>
              <div className="deal-room__state">
                <span className="deal-room__state-dot" aria-hidden="true" />
                <span>{deal.status}</span>
                <span className="deal-room__state-divider" aria-hidden="true" />
                <span>Deal version {deal.version}</span>
              </div>
              <div className="deal-room__actions">
                <button type="button" className="button deal-room__refresh" onClick={retryDeal}>
                  Refresh room <span aria-hidden="true">↗</span>
                </button>
              </div>
            </div>

            <DealConstellation
              buyerOrganizationId={deal.buyer_organization_id}
              sellerOrganizationId={deal.seller_organization_id}
            />
          </div>

          <dl className="deal-room__ledger">
            <div className="deal-room__ledger-item">
              <dt>Deal reference</dt>
              <dd className="mono">{deal.id}</dd>
            </div>
            <div className="deal-room__ledger-item">
              <dt>Buyer organization</dt>
              <dd className="mono">{deal.buyer_organization_id}</dd>
            </div>
            <div className="deal-room__ledger-item">
              <dt>Seller organization</dt>
              <dd className="mono">{deal.seller_organization_id}</dd>
            </div>
            <div className="deal-room__ledger-item deal-room__ledger-item--version">
              <dt>Deal version</dt>
              <dd>{deal.version}</dd>
            </div>
          </dl>
        </section>

        <DealConversationReview deal={deal} />
      </div>
    </Reveal>
  );
}
