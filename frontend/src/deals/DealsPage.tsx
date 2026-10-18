import { useEffect, useState } from "react";

import { ApiError, listDeals } from "../api/client";
import type { DealSummary, ViewerRole } from "../api/types";
import OrganizationsPanel from "../organizations/OrganizationsPanel";
import Reveal from "../ui/Reveal";

type DealsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; deals: DealSummary[] };

interface DealsPageProps {
  onOpenDeal: (dealId: string) => void;
  onCreateDeal: () => void;
}

const ROLE_LABELS: Record<ViewerRole, string> = {
  BUYER: "You are the buyer",
  SELLER: "You are the seller",
  BOTH: "You are both parties",
};

function describeError(caught: unknown): string {
  if (caught instanceof ApiError) {
    if (caught.status === 401) {
      return "Your session has expired. Sign in again.";
    }
    return caught.message;
  }
  return "Something went wrong. Please try again.";
}

export default function DealsPage({ onOpenDeal, onCreateDeal }: DealsPageProps) {
  const [state, setState] = useState<DealsState>({ status: "loading" });
  const [reloadCount, setReloadCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const deals = await listDeals();
        if (!cancelled) {
          setState({ status: "ready", deals });
        }
      } catch (caught) {
        if (!cancelled) {
          setState({ status: "error", message: describeError(caught) });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reloadCount]);

  function retryDeals() {
    setState({ status: "loading" });
    setReloadCount((count) => count + 1);
  }

  function renderDeals() {
    if (state.status === "loading") {
      return (
        <section className="card" aria-live="polite">
          <p role="status">Loading deals…</p>
        </section>
      );
    }

    if (state.status === "error") {
      return (
        <section className="card" role="alert">
          <h2>We could not load your deals</h2>
          <p className="muted" style={{ marginTop: 10 }}>
            {state.message}
          </p>
          <div className="actions">
            <button type="button" className="button" onClick={retryDeals}>
              Try again
            </button>
          </div>
        </section>
      );
    }

    return (
      <section className="card" aria-labelledby="deals-heading">
        <div className="page-header">
          <div className="panel-head">
            <span className="eyebrow">Workspace</span>
            <h2 id="deals-heading">Deals shared with you</h2>
          </div>
          <button type="button" className="button" onClick={onCreateDeal}>
            New deal
          </button>
        </div>
        <p className="muted">
          Deals where your organization is the buyer or the seller. Select one to review it.
        </p>
        {state.deals.length === 0 ? (
          <p className="empty-state">
            No deals yet. Start one when you are ready to trade with another organization.
          </p>
        ) : (
          <ul className="deal-list">
            {state.deals.map((deal) => (
              <li key={deal.id}>
                <div className="deal-meta">
                  <span className="badge">{deal.status}</span>
                  <span className="deal-role">{ROLE_LABELS[deal.viewer_role]}</span>
                  <span className="mono">{deal.id}</span>
                </div>
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => onOpenDeal(deal.id)}
                >
                  Open deal
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    );
  }

  return (
    <div className="workspace">
      <Reveal className="hero">
        <div className="workspace-intro__meta">
          <span className="eyebrow">01 / Deal register</span>
          <span className="workspace-intro__caption">Shared between your organizations</span>
        </div>
        <h1 className="display">Deals, on record.</h1>
        <p className="hero__lede">
          Each deal has one shared reference. Open a record to read the conversation and review
          the facts connected to their source messages.
        </p>
      </Reveal>

      <Reveal delay={80}>{renderDeals()}</Reveal>

      <Reveal delay={120}>
        <OrganizationsPanel />
      </Reveal>
    </div>
  );
}
