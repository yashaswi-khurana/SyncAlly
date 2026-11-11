import { useEffect, useState } from "react";

import { ApiError, getOrganization, listDeals } from "../api/client";
import type { DealSummary, ViewerRole } from "../api/types";
import Reveal from "../ui/Reveal";
import SplitText from "../ui/SplitText";

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
  const [organizationNames, setOrganizationNames] = useState<Record<string, string>>({});
  const [failedOrganizationIds, setFailedOrganizationIds] = useState<Record<string, true>>({});

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

  useEffect(() => {
    if (state.status !== "ready") return;
    let cancelled = false;
    const controller = new AbortController();
    // An unaccepted counterparty is an inactive shell and must not be looked up.
    const ids = new Set(state.deals.flatMap((deal) => {
      if (deal.pending_counterparty) return [];
      if (deal.viewer_role === "BOTH") return [deal.buyer_organization_id, deal.seller_organization_id];
      return [deal.viewer_role === "BUYER" ? deal.seller_organization_id : deal.buyer_organization_id];
    }));
    const queue = [...ids];
    let next = 0;
    const loadNames = async () => {
      while (!cancelled && next < queue.length) {
        const id = queue[next++];
        try {
          const organization = await getOrganization(id, { signal: controller.signal });
          if (!cancelled) setOrganizationNames((names) => ({ ...names, [id]: organization.legal_name }));
        } catch {
          // A missing or inaccessible party name does not prevent opening the deal.
          if (!cancelled) setFailedOrganizationIds((failed) => ({ ...failed, [id]: true }));
        }
      }
    };
    for (let i = 0; i < Math.min(4, queue.length); i++) void loadNames();
    return () => { cancelled = true; controller.abort(); };
  }, [state]);

  function retryDeals() {
    setState({ status: "loading" });
    setReloadCount((count) => count + 1);
  }

  function renderDeals() {
    if (state.status === "loading") {
      return (
        <section className="card" aria-live="polite">
          <p role="status">Loading deals…</p>
          <div className="skeleton-stack" aria-hidden="true">
            <span className="skeleton-bar skeleton-bar--mid" />
            <span className="skeleton-bar" />
            <span className="skeleton-bar skeleton-bar--short" />
          </div>
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
          <button type="button" className="button secondary" onClick={onCreateDeal}>
            New deal
          </button>
        </div>
        <p className="muted">
          Each row is a separate deal with its own reference, terms, and approvals. The same trading partner can have more than one deal.
        </p>
        {state.deals.length === 0 ? (
          <p className="empty-state">
            No deals yet. Start one when you are ready to trade with another organization.
          </p>
        ) : (
          <ul className="deal-list">
            {state.deals.map((deal) => (
              <li key={deal.id}>
                <h3 className="deal-list__title">
                  {deal.display_name?.trim()
                    ? `${deal.display_name.trim()} · ${deal.id.slice(0, 8)}`
                    : (deal.pending_counterparty
                    ? `New counterparty deal · ${deal.id.slice(0, 8)}`
                    : deal.viewer_role === "BOTH"
                      ? `${organizationNames[deal.buyer_organization_id] ?? "Buyer"} ↔ ${organizationNames[deal.seller_organization_id] ?? "Seller"} · ${deal.id.slice(0, 8)}`
                      : `Trade with ${organizationNames[deal.viewer_role === "BUYER" ? deal.seller_organization_id : deal.buyer_organization_id] ?? "counterparty"} · ${deal.id.slice(0, 8)}`)}
                </h3>
                <div className="deal-meta">
                  <span className="badge">{deal.status}</span>
                  <span className="deal-role">{ROLE_LABELS[deal.viewer_role]}</span>
                  {deal.pending_counterparty ? <span>Waiting for trading partner to join</span> : (
                    deal.viewer_role === "BOTH"
                      ? <span>{organizationNames[deal.buyer_organization_id] ?? "Buyer"} ↔ {organizationNames[deal.seller_organization_id] ?? "Seller"}</span>
                      : organizationNames[deal.viewer_role === "BUYER" ? deal.seller_organization_id : deal.buyer_organization_id]
                        ? <span>Trading partner: {organizationNames[deal.viewer_role === "BUYER" ? deal.seller_organization_id : deal.buyer_organization_id]}</span>
                        : failedOrganizationIds[deal.viewer_role === "BUYER" ? deal.seller_organization_id : deal.buyer_organization_id]
                          ? <span>Trading partner: Name unavailable</span>
                          : null
                  )}
                  <span className="mono">Reference: {deal.id}</span>
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
        <h1 className="display"><SplitText text="Deals, on record." /></h1>
        <p className="hero__lede">
          Each deal has one shared reference. Open a record to read the conversation and review
          the facts connected to their source messages.
        </p>
      </Reveal>

      <Reveal delay={80}>{renderDeals()}</Reveal>
    </div>
  );
}
