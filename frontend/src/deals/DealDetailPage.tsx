import { useEffect, useState } from "react";

import { ApiError, getDeal } from "../api/client";
import type { Deal } from "../api/types";
import Reveal from "../ui/Reveal";

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
      <section className="card" aria-labelledby="deal-detail-heading">
        <div className="page-header">
          <div className="panel-head">
            <span className="eyebrow">Deal</span>
            <h2 id="deal-detail-heading">Deal details</h2>
          </div>
        </div>
        <p className="muted">
          A draft becomes a committed agreement only after both organizations approve the same
          immutable version.
        </p>
        <dl className="details">
          <div>
            <dt>Status</dt>
            <dd>
              <span className="badge">{deal.status}</span>
            </dd>
          </div>
          <div>
            <dt>Version</dt>
            <dd className="stat">{deal.version}</dd>
          </div>
          <div>
            <dt>Deal ID</dt>
            <dd className="mono">{deal.id}</dd>
          </div>
          <div>
            <dt>Buyer organization</dt>
            <dd className="mono">{deal.buyer_organization_id}</dd>
          </div>
          <div>
            <dt>Seller organization</dt>
            <dd className="mono">{deal.seller_organization_id}</dd>
          </div>
        </dl>
        <div className="actions">
          <button type="button" className="button" onClick={retryDeal}>
            Refresh
          </button>
          <button type="button" className="button secondary" onClick={onBackToDeals}>
            Back to deals
          </button>
        </div>
      </section>
    </Reveal>
  );
}
