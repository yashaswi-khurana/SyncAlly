import { useEffect, useState } from "react";

import {
  ApiError,
  getCurrentAgreement,
  getDeal,
  listDealMessages,
  listOrganizations,
} from "../api/client";
import type { Deal, Organization } from "../api/types";
import Reveal from "../ui/Reveal";
import DealConstellation from "./DealConstellation";
import DealConversationReview from "./DealConversationReview";
import AgreementReview from "./AgreementReview";
import CommercialDocumentPanel from "./CommercialDocumentPanel";
import PaymentStatusPanel from "./PaymentStatusPanel";

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
  const [agreementReloadToken, setAgreementReloadToken] = useState(0);
  const [isFresh, setIsFresh] = useState(false);
  const [activeOrgId, setActiveOrgId] = useState("");
  const [counterpartyName, setCounterpartyName] = useState("Counterparty");

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

  useEffect(() => {
    if (state.status !== "ready" || agreementReloadToken > 0) {
      return;
    }

    const { deal } = state;
    let cancelled = false;

    void (async () => {
      try {
        const [agreementResult, organizationsResult] = await Promise.allSettled([
          getCurrentAgreement(deal.id),
          listOrganizations(),
        ]);

        if (cancelled) return;

        const hasAgreement =
          agreementResult.status === "fulfilled" && agreementResult.value !== null;

        if (hasAgreement) {
          setIsFresh(false);
          return;
        }

        const organizations: Organization[] =
          organizationsResult.status === "fulfilled" ? organizationsResult.value : [];

        const userOrg = organizations.find(
          (org) =>
            org.id === deal.buyer_organization_id || org.id === deal.seller_organization_id,
        );

        const resolvedActiveOrgId = userOrg?.id || deal.buyer_organization_id;
        setActiveOrgId(resolvedActiveOrgId);
        const counterpartyId =
          userOrg?.id === deal.seller_organization_id
            ? deal.buyer_organization_id
            : deal.seller_organization_id;

        const counterpartyOrg = organizations.find((org) => org.id === counterpartyId);
        const resolvedCounterparty =
          counterpartyOrg?.legal_name ||
          organizations.find((org) => org.id !== userOrg?.id)?.legal_name ||
          "Counterparty";

        setCounterpartyName(resolvedCounterparty);

        const messages = await listDealMessages(deal.id, resolvedActiveOrgId);
        if (cancelled) return;

        const fresh = messages.length === 0;
        setIsFresh(fresh);
      } catch {
        // Defensive: if checks fail, don't break page rendering
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [state, agreementReloadToken, reloadCount]);

  // Periodic check to dismiss the banner automatically when the first message is posted
  useEffect(() => {
    if (!isFresh || state.status !== "ready" || agreementReloadToken > 0 || !activeOrgId) {
      return;
    }

    const { deal } = state;
    let cancelled = false;

    const intervalId = setInterval(() => {
      void (async () => {
        try {
          const messages = await listDealMessages(deal.id, activeOrgId);
          if (!cancelled && messages.length > 0) {
            setIsFresh(false);
          }
        } catch {
          // Keep background polling silent
        }
      })();
    }, 2500);

    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, [isFresh, state, agreementReloadToken, activeOrgId]);

  function retryDeal() {
    setState({ status: "loading" });
    setReloadCount((count) => count + 1);
  }

  function handleStartConversation() {
    const composer =
      document.querySelector<HTMLTextAreaElement>(
        "#deal-message-input, textarea[name='message'], .message-composer textarea, textarea",
      ) ||
      document.querySelector<HTMLElement>(
        "#conversation-heading, .communication-card--transcript",
      );
    if (composer) {
      composer.focus();
      composer.scrollIntoView({ behavior: "smooth", block: "center" });
    }
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
  const showBanner = isFresh && agreementReloadToken === 0;

  return (
    <Reveal>
      <div className="workspace deal-workspace">
        {showBanner ? (
          <section
            className="deal-onboarding-banner"
            aria-label="New deal next steps"
            role="region"
          >
            <div className="deal-onboarding-banner__header">
              <div className="deal-onboarding-banner__badge">
                <span className="deal-onboarding-banner__dot" aria-hidden="true" />
                <span>Next Steps</span>
              </div>
              <h2 className="deal-onboarding-banner__title">
                Deal created with {counterpartyName}!
              </h2>
              <p className="deal-onboarding-banner__desc">
                Follow this 3-step roadmap to propose terms, review AI facts, and approve your
                agreement.
              </p>
            </div>

            <ol className="deal-onboarding-steps" aria-label="Deal progression steps">
              <li className="deal-onboarding-step deal-onboarding-step--active" aria-current="step">
                <div className="deal-onboarding-step__indicator">
                  <span className="deal-onboarding-step__number">1</span>
                  <span className="deal-onboarding-step__line" aria-hidden="true" />
                </div>
                <div className="deal-onboarding-step__content">
                  <strong className="deal-onboarding-step__label">
                    Step 1 · Introduce terms
                  </strong>
                  <p className="deal-onboarding-step__text">
                    Introduce trade terms in the conversation below (e.g. quantity, price, delivery port).
                  </p>
                </div>
              </li>

              <li className="deal-onboarding-step">
                <div className="deal-onboarding-step__indicator">
                  <span className="deal-onboarding-step__number">2</span>
                  <span className="deal-onboarding-step__line" aria-hidden="true" />
                </div>
                <div className="deal-onboarding-step__content">
                  <strong className="deal-onboarding-step__label">
                    Step 2 · Review facts
                  </strong>
                  <p className="deal-onboarding-step__text">
                    Review AI-extracted terms and toggle them to Shareable.
                  </p>
                </div>
              </li>

              <li className="deal-onboarding-step">
                <div className="deal-onboarding-step__indicator">
                  <span className="deal-onboarding-step__number">3</span>
                </div>
                <div className="deal-onboarding-step__content">
                  <strong className="deal-onboarding-step__label">
                    Step 3 · Bilateral agreement
                  </strong>
                  <p className="deal-onboarding-step__text">
                    Approve the bilateral agreement to generate your invoice.
                  </p>
                </div>
              </li>
            </ol>

            <div className="deal-onboarding-banner__actions">
              <button
                type="button"
                className="button deal-onboarding-banner__button"
                onClick={handleStartConversation}
              >
                Start Conversation <span aria-hidden="true">↓</span>
              </button>
            </div>
          </section>
        ) : null}

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

        <AgreementReview
          dealId={deal.id}
          buyerOrganizationId={deal.buyer_organization_id}
          sellerOrganizationId={deal.seller_organization_id}
          reloadToken={agreementReloadToken}
          onCommitted={() => setAgreementReloadToken((token) => token + 1)}
        />
        <PaymentStatusPanel
          dealId={deal.id}
          sellerOrganizationId={deal.seller_organization_id}
          reloadToken={agreementReloadToken}
        />
        <CommercialDocumentPanel dealId={deal.id} />
        <DealConversationReview
          deal={deal}
          onAgreementCreated={() => setAgreementReloadToken((token) => token + 1)}
        />
      </div>
    </Reveal>
  );
}
