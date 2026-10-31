import { useCallback, useEffect, useState } from "react";

import {
  ApiError,
  apiRequest,
  getCurrentAgreement,
  getDeal,
  getOrganization,
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

type FreshnessStatus = "unknown" | "fresh" | "not-fresh";

function nextFreshness(current: FreshnessStatus, next: FreshnessStatus): FreshnessStatus {
  // Messages are never deleted, so an older in-flight check must not downgrade
  // a deal that is already known to have activity.
  return current === "not-fresh" ? current : next;
}

function describeError(caught: unknown): string {
  if (caught instanceof ApiError) {
    if (caught.status === 401) {
      return "Your session has expired. Sign in again.";
    }
    return caught.message;
  }
  if (caught instanceof Error && caught.message) {
    return caught.message;
  }
  return "Something went wrong. Please try again.";
}

interface DealDetailPageProps {
  dealId: string;
  onBackToDeals: () => void;
  freshnessIntervalMs?: number;
}

export default function DealDetailPage({
  dealId,
  onBackToDeals,
  freshnessIntervalMs = 2500,
}: DealDetailPageProps) {
  const [state, setState] = useState<DealState>({ status: "loading" });
  const [reloadCount, setReloadCount] = useState(0);
  const [agreementReloadToken, setAgreementReloadToken] = useState(0);
  const [freshness, setFreshness] = useState<FreshnessStatus>("unknown");
  const [freshnessError, setFreshnessError] = useState<string | null>(null);
  const [freshnessReloadToken, setFreshnessReloadToken] = useState(0);
  const [freshnessChecked, setFreshnessChecked] = useState(false);
  const [selectedOrganizationId, setSelectedOrganizationId] = useState("");
  const [counterpartyName, setCounterpartyName] = useState("Counterparty");

  // Shareable Counterparty Invitation Modal State
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [adminOrganizations, setAdminOrganizations] = useState<Organization[]>([]);
  const [selectedInviteOrgId, setSelectedInviteOrgId] = useState("");
  const [generatingInvite, setGeneratingInvite] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [generatedInvite, setGeneratedInvite] = useState<{
    token: string;
    invite_url: string;
    organization_id: string;
    deal_id: string | null;
  } | null>(null);
  const [copiedInvite, setCopiedInvite] = useState(false);

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

        // 1. Inspect agreement check result
        if (agreementResult.status === "fulfilled" && agreementResult.value !== null) {
          setFreshness("not-fresh");
          setFreshnessError(null);
          return;
        }

        if (agreementResult.status === "rejected") {
          const reason = agreementResult.reason;
          const isNotFound = reason instanceof ApiError && reason.status === 404;
          if (!isNotFound) {
            // An agreement lookup failure cannot be assumed as "no agreement".
            // Treat as unknown and report failure.
            setFreshness("unknown");
            setFreshnessError(describeError(reason));
            return;
          }
          // If 404, we have verified that no agreement exists yet.
        }

        // 2. Resolve organizations
        if (organizationsResult.status === "rejected") {
          setFreshness("unknown");
          setFreshnessError(describeError(organizationsResult.reason));
          return;
        }

        const organizations: Organization[] = organizationsResult.value;

        const partyOrganizations = organizations.filter(
          (org) =>
            org.id === deal.buyer_organization_id || org.id === deal.seller_organization_id,
        );

        let effectivePartyId = selectedOrganizationId;
        if (partyOrganizations.length === 1 && !selectedOrganizationId) {
          effectivePartyId = partyOrganizations[0].id;
          setSelectedOrganizationId(partyOrganizations[0].id);
        }

        if (!effectivePartyId) {
          // Dual member who has not chosen a party yet: keep banner hidden
          setFreshness("unknown");
          setFreshnessError(null);
          setCounterpartyName("Counterparty");
          return;
        }

        const counterpartyId =
          effectivePartyId === deal.seller_organization_id
            ? deal.buyer_organization_id
            : deal.seller_organization_id;

        let resolvedCounterparty =
          organizations.find((org) => org.id === counterpartyId)?.legal_name;

        if (!resolvedCounterparty) {
          try {
            const fetchedCounterparty = await getOrganization(counterpartyId);
            if (!cancelled && fetchedCounterparty?.legal_name) {
              resolvedCounterparty = fetchedCounterparty.legal_name;
            }
          } catch {
            // Graceful fallback if counterparty organization details cannot be resolved
          }
        }

        if (cancelled) return;
        setCounterpartyName(resolvedCounterparty || "Counterparty");

        // 3. Inspect visible messages for the chosen party
        const messages = await listDealMessages(deal.id, effectivePartyId);
        if (cancelled) return;

        setFreshnessError(null);
        setFreshness((current) =>
          nextFreshness(current, messages.length > 0 ? "not-fresh" : "fresh"),
        );
      } catch (caught) {
        if (!cancelled) {
          setFreshness((current) => nextFreshness(current, "unknown"));
          setFreshnessError(describeError(caught));
        }
      } finally {
        if (!cancelled) {
          setFreshnessChecked(true);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [state, agreementReloadToken, reloadCount, freshnessReloadToken, selectedOrganizationId]);

  // Retry failed freshness checks periodically so onboarding recovers automatically
  // once network requests or services are restored.
  useEffect(() => {
    if (
      freshness !== "unknown" ||
      !freshnessError ||
      state.status !== "ready" ||
      agreementReloadToken > 0 ||
      freshnessIntervalMs <= 0
    ) {
      return;
    }

    const timerId = setTimeout(() => {
      retryFreshness();
    }, freshnessIntervalMs);

    return () => {
      clearTimeout(timerId);
    };
  }, [freshness, freshnessError, state.status, agreementReloadToken, freshnessIntervalMs]);

  // Periodic check to dismiss the banner automatically when the first message is posted,
  // or update freshness when an agreement is created or checks fail.
  useEffect(() => {
    if (
      freshness !== "fresh" ||
      state.status !== "ready" ||
      agreementReloadToken > 0 ||
      !selectedOrganizationId ||
      !freshnessChecked ||
      freshnessIntervalMs <= 0
    ) {
      return;
    }

    const { deal } = state;
    let cancelled = false;
    let inFlight = false;

    const pollFreshness = async () => {
      // A slow poll must finish before the next one starts, and hidden tabs
      // must not generate background traffic.
      if (cancelled || inFlight || document.hidden) {
        return;
      }

      inFlight = true;
      try {
        const [messagesResult, agreementResult] = await Promise.allSettled([
          listDealMessages(deal.id, selectedOrganizationId),
          getCurrentAgreement(deal.id),
        ]);
        if (cancelled) return;

        // 1. If an agreement is found, dismiss onboarding immediately
        if (agreementResult.status === "fulfilled" && agreementResult.value !== null) {
          setFreshness("not-fresh");
          setFreshnessError(null);
          setAgreementReloadToken((token) => token + 1);
          return;
        }

        // 2. If agreement check failed with non-404 error, treat as unknown
        if (agreementResult.status === "rejected") {
          const reason = agreementResult.reason;
          const isNotFound = reason instanceof ApiError && reason.status === 404;
          if (!isNotFound) {
            setFreshness((current) => nextFreshness(current, "unknown"));
            setFreshnessError(describeError(reason));
            return;
          }
        }

        // 3. If messages check failed, treat as unknown instead of silently retaining fresh
        if (messagesResult.status === "rejected") {
          setFreshness((current) => nextFreshness(current, "unknown"));
          setFreshnessError(describeError(messagesResult.reason));
          return;
        }

        // 4. Both checks succeeded and agreement is confirmed absent (404)
        const messages = messagesResult.value;
        setFreshness((current) =>
          nextFreshness(current, messages.length > 0 ? "not-fresh" : "fresh"),
        );
        setFreshnessError(null);
      } catch (caught) {
        if (!cancelled) {
          // Failed check: treat as unknown instead of silently retaining fresh
          setFreshness((current) => nextFreshness(current, "unknown"));
          setFreshnessError(describeError(caught));
        }
      } finally {
        inFlight = false;
      }
    };

    const intervalId = setInterval(() => {
      void pollFreshness();
    }, freshnessIntervalMs);

    // Resume promptly when the tab becomes visible instead of waiting a full interval.
    const onVisibilityChange = () => {
      if (!document.hidden) {
        void pollFreshness();
      }
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      cancelled = true;
      clearInterval(intervalId);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [freshness, state, agreementReloadToken, selectedOrganizationId, freshnessChecked, freshnessIntervalMs]);

  function retryDeal() {
    setState({ status: "loading" });
    setReloadCount((count) => count + 1);
    setFreshnessChecked(false);
    setFreshness("unknown");
    setFreshnessError(null);
  }

  function retryFreshness() {
    setFreshnessChecked(false);
    setFreshness("unknown");
    setFreshnessError(null);
    setFreshnessReloadToken((token) => token + 1);
  }

  const handleOrganizationChange = useCallback((orgId: string) => {
    setSelectedOrganizationId(orgId);
    setFreshness("unknown");
    setFreshnessError(null);
  }, []);

  function handleStartConversation() {
    const composer = document.querySelector<HTMLTextAreaElement>("#deal-message-input");
    if (composer) {
      composer.focus();
      composer.scrollIntoView?.({ behavior: "smooth", block: "center" });
      return;
    }

    const orgSelector =
      document.querySelector<HTMLSelectElement>(`#conversation-organization-${dealId}`) ||
      document.querySelector<HTMLSelectElement>("[id^='conversation-organization-']");
    if (orgSelector) {
      orgSelector.focus();
      orgSelector.scrollIntoView?.({ behavior: "smooth", block: "center" });
    }
  }

  async function handleOpenInviteModal() {
    if (state.status !== "ready") return;
    setShowInviteModal(true);
    setInviteError(null);
    setGeneratedInvite(null);
    setCopiedInvite(false);
    try {
      const orgs = await listOrganizations();
      const currentDeal = state.deal;
      const admins = orgs.filter(
        (org) =>
          org.role === "ADMIN" &&
          (org.id === currentDeal.buyer_organization_id ||
            org.id === currentDeal.seller_organization_id),
      );
      setAdminOrganizations(admins);
      setSelectedInviteOrgId(admins[0]?.id ?? "");
    } catch (caught) {
      setInviteError(describeError(caught));
    }
  }

  async function handleGenerateInvite(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (state.status !== "ready") return;
    const targetOrgId =
      selectedInviteOrgId || (adminOrganizations[0] ? adminOrganizations[0].id : "");
    if (!targetOrgId) {
      setInviteError("Please select an organization where you are an admin.");
      return;
    }

    setGeneratingInvite(true);
    setInviteError(null);
    try {
      const res = await apiRequest<{
        token: string;
        invite_url: string;
        organization_id: string;
        organization_legal_name: string;
        deal_id: string | null;
        role: string;
        expires_at: string;
      }>(`/organizations/${encodeURIComponent(targetOrgId)}/invitations`, {
        method: "POST",
        body: JSON.stringify({
          deal_id: state.deal.id,
        }),
      });
      setGeneratedInvite(res);
    } catch (caught) {
      setInviteError(describeError(caught));
    } finally {
      setGeneratingInvite(false);
    }
  }

  async function handleCopyInviteLink() {
    if (!generatedInvite) return;
    try {
      if (!navigator.clipboard || !navigator.clipboard.writeText) {
        throw new Error("Clipboard API is unavailable");
      }
      await navigator.clipboard.writeText(generatedInvite.invite_url);
      setCopiedInvite(true);
      setTimeout(() => setCopiedInvite(false), 2500);
    } catch {
      setCopiedInvite(false);
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
  const showBanner = freshness === "fresh" && agreementReloadToken === 0;

  return (
    <Reveal>
      <div className="workspace deal-workspace">
        {freshnessError && freshness === "unknown" ? (
          <aside className="deal-onboarding-error" role="status" aria-live="polite">
            <span>Unable to verify deal onboarding status: {freshnessError}</span>
            <button
              type="button"
              className="button button--secondary button--compact"
              onClick={retryFreshness}
            >
              Retry check
            </button>
          </aside>
        ) : null}

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
              <button
                type="button"
                className="button button--secondary"
                onClick={handleOpenInviteModal}
              >
                Invite Counterparty
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
                <button
                  type="button"
                  className="button"
                  onClick={handleOpenInviteModal}
                >
                  Invite Counterparty
                </button>
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
          composerId="deal-message-input"
          buttonLabel="Send message"
          selectedOrganizationId={selectedOrganizationId}
          onOrganizationChange={handleOrganizationChange}
          onAgreementCreated={() => setAgreementReloadToken((token) => token + 1)}
          onMessageCreated={() => {
            setFreshness("not-fresh");
            setFreshnessError(null);
          }}
        />

        {showInviteModal ? (
          <div
            className="manual-fact-modal-backdrop"
            role="dialog"
            aria-modal="true"
            aria-labelledby="deal-invite-modal-title"
          >
            <div className="manual-fact-modal">
              <div className="panel-head">
                <div>
                  <span className="eyebrow">Onboarding Link</span>
                  <h3 id="deal-invite-modal-title" className="display" style={{ fontSize: "1.25rem" }}>
                    Invite Counterparty
                  </h3>
                </div>
                <button
                  type="button"
                  className="button ghost"
                  onClick={() => setShowInviteModal(false)}
                  aria-label="Close"
                >
                  ✕
                </button>
              </div>

              <p className="muted" style={{ marginBottom: 16 }}>
                Generate a signed, single-use onboarding link for your counterparty. When opened,
                they will be guided to sign up, register their entity, and link directly into this deal.
              </p>

              <form onSubmit={handleGenerateInvite} className="form" style={{ gap: 14 }}>
                <div className="field">
                  <label htmlFor="deal-invite-org-select">Inviting Organization</label>
                  <select
                    id="deal-invite-org-select"
                    value={selectedInviteOrgId}
                    onChange={(e) => setSelectedInviteOrgId(e.target.value)}
                    disabled={generatingInvite || adminOrganizations.length === 0}
                  >
                    {adminOrganizations.length === 0 ? (
                      <option value="">No admin organizations available</option>
                    ) : (
                      adminOrganizations.map((org) => (
                        <option key={org.id} value={org.id}>
                          {org.legal_name} ({org.country_code})
                        </option>
                      ))
                    )}
                  </select>
                </div>

                {inviteError ? (
                  <p className="form-error" role="alert">
                    {inviteError}
                  </p>
                ) : null}

                <div style={{ marginTop: 8 }}>
                  <button
                    type="submit"
                    className="button"
                    disabled={generatingInvite || adminOrganizations.length === 0}
                  >
                    {generatingInvite ? "Generating link…" : "Generate Shareable Link"}
                  </button>
                </div>
              </form>

              {generatedInvite ? (
                <div style={{ marginTop: 24, paddingTop: 20, borderTop: "1px solid var(--line)" }}>
                  <span className="eyebrow">Shareable Invitation Link</span>
                  <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                    <input
                      type="text"
                      readOnly
                      value={generatedInvite.invite_url}
                      className="mono"
                      style={{ flex: 1, fontSize: "0.85rem" }}
                    />
                    <button
                      type="button"
                      className="button secondary"
                      onClick={handleCopyInviteLink}
                    >
                      {copiedInvite ? "Copied!" : "Copy Link"}
                    </button>
                  </div>
                  <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 8 }}>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        background: "rgba(56, 211, 159, 0.15)",
                        color: "#38d39f",
                        fontSize: "0.75rem",
                        fontWeight: 600,
                      }}
                    >
                      Expires in 7 days · Single use · Pre-linked to this deal
                    </span>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>
    </Reveal>
  );
}
