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
import type { Deal, NegotiationView, Organization } from "../api/types";
import Reveal from "../ui/Reveal";
import SplitText from "../ui/SplitText";
import { setSceneConsensus } from "../ui/motion";
import DealConstellation from "./DealConstellation";
import DealConversationReview from "./DealConversationReview";
import AgreementReview from "./AgreementReview";
import PaymentStatusPanel from "./PaymentStatusPanel";
import DealCasesPanel from "./DealCasesPanel";
import RemindersPanel from "./RemindersPanel";
import NegotiationReview from "./NegotiationReview";
import FulfillmentPanel from "./FulfillmentPanel";
import DealOverview from "./DealOverview";
import type { OverviewSnapshot } from "./DealOverview";
import type { OpeningMessageDraft } from "./openingMessageDraft";
import MemberGrantFields, { type MemberGrants } from "../organizations/MemberGrantFields";

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
  openingMessageDraft?: OpeningMessageDraft;
  onOpeningMessageDraftChange?: (draft: OpeningMessageDraft) => void;
  onOpeningMessageDraftComplete?: (dealId: string, organizationId: string) => void;
}

export default function DealDetailPage({
  dealId,
  onBackToDeals,
  freshnessIntervalMs = 2500,
  openingMessageDraft,
  onOpeningMessageDraftChange,
  onOpeningMessageDraftComplete,
}: DealDetailPageProps) {
  const [state, setState] = useState<DealState>({ status: "loading" });
  const [reloadCount, setReloadCount] = useState(0);
  const [agreementReloadToken, setAgreementReloadToken] = useState(0);
  const [freshness, setFreshness] = useState<FreshnessStatus>("unknown");
  const [freshnessError, setFreshnessError] = useState<string | null>(null);
  const [freshnessReloadToken, setFreshnessReloadToken] = useState(0);
  const [freshnessChecked, setFreshnessChecked] = useState(false);
  const [selectedOrganizationId, setSelectedOrganizationId] = useState(openingMessageDraft?.organizationId ?? "");
  const [counterpartyName, setCounterpartyName] = useState("Counterparty");
  const [partyNames, setPartyNames] = useState<{ buyer: string; seller: string }>({ buyer: "", seller: "" });
  const [deskTab, setDeskTab] = useState<"trade" | "obligations" | "invoices" | "audit">("trade");
  const [negotiation, setNegotiation] = useState<NegotiationView | null>(null);
  const [overview, setOverview] = useState<OverviewSnapshot | null>(null);
  function commercialChanged() {
    setNegotiation(null);
    setAgreementReloadToken((token) => token + 1);
    setReloadCount((count) => count + 1);
  }

  // Shareable Counterparty Invitation Modal State
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [adminOrganizations, setAdminOrganizations] = useState<Organization[]>([]);
  const [selectedInviteOrgId, setSelectedInviteOrgId] = useState("");
  const [teamRecipientEmail, setTeamRecipientEmail] = useState("");
  const [generatingInvite, setGeneratingInvite] = useState(false);
  const [cancelingInvite, setCancelingInvite] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [generatedInvite, setGeneratedInvite] = useState<{
    invitation_id: string;
    token: string;
    invite_url: string;
    organization_id: string;
    deal_id: string | null;
  } | null>(null);
  const [copiedInvite, setCopiedInvite] = useState(false);
  const [inviteGrants, setInviteGrants] = useState<MemberGrants>({ role_bundles: [], permissions: [], deal_ids: [] });
  const updateInviteGrants = useCallback((grants: MemberGrants) => setInviteGrants(grants), []);

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
    if (state.status !== "ready") return;
    let cancelled = false;
    const { deal } = state;
    void Promise.allSettled([
      getOrganization(deal.buyer_organization_id),
      getOrganization(deal.seller_organization_id),
    ]).then(([buyerResult, sellerResult]) => {
      if (cancelled) return;
      setPartyNames({
        buyer: buyerResult.status === "fulfilled" ? buyerResult.value?.legal_name || "" : "",
        seller: sellerResult.status === "fulfilled" ? sellerResult.value?.legal_name || "" : "",
      });
    });
    return () => { cancelled = true; };
  }, [state]);

  const pendingCounterparty = state.status === "ready" && state.deal.pending_counterparty;
  useEffect(() => {
    if (!pendingCounterparty || freshnessIntervalMs <= 0) return;
    let cancelled = false;
    let inFlight = false;
    const timer = setInterval(() => {
      if (document.hidden || inFlight) return;
      inFlight = true;
      void getDeal(dealId).then((deal) => {
        if (!cancelled && !deal.pending_counterparty) setState({ status: "ready", deal });
      }).catch(() => {}).finally(() => { inFlight = false; });
    }, freshnessIntervalMs);
    return () => { cancelled = true; clearInterval(timer); };
  }, [dealId, pendingCounterparty, freshnessIntervalMs]);

  useEffect(() => {
    if (state.status !== "ready" || agreementReloadToken > 0) {
      return;
    }

    const { deal } = state;
    let cancelled = false;

    void (async () => {
      try {
        const [agreementResult, organizationsResult] = await Promise.allSettled([
          getCurrentAgreement(deal.id, { organizationId: selectedOrganizationId || undefined }),
          listOrganizations(),
        ]);

        if (cancelled) return;

        // Resolve the active organization even when an agreement already exists. Otherwise
        // returning users with membership in exactly one party would see agreement details
        // but no role context or next step until they changed the selector manually.
        if (organizationsResult.status === "fulfilled") {
          const organizations = organizationsResult.value;
          const partyOrganizations = organizations.filter(
            (org) => org.id === deal.buyer_organization_id || org.id === deal.seller_organization_id,
          );
          const selectedPartyIsActive = partyOrganizations.some((org) => org.id === selectedOrganizationId);
          const draftOrganization = openingMessageDraft?.dealId === deal.id
            ? partyOrganizations.find((org) => org.id === openingMessageDraft.organizationId)
            : undefined;
          if (!selectedPartyIsActive) {
            if (draftOrganization) setSelectedOrganizationId(draftOrganization.id);
            else if (partyOrganizations.length === 1) setSelectedOrganizationId(partyOrganizations[0].id);
            else if (selectedOrganizationId) setSelectedOrganizationId("");
          }
        }

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

        let effectivePartyId = partyOrganizations.some((org) => org.id === selectedOrganizationId)
          ? selectedOrganizationId
          : "";
        if (partyOrganizations.length === 1 && !effectivePartyId) {
          effectivePartyId = partyOrganizations[0].id;
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
  }, [state, agreementReloadToken, reloadCount, freshnessReloadToken, selectedOrganizationId,
    openingMessageDraft?.dealId, openingMessageDraft?.organizationId]);

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
    setOverview(null);
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
    setNegotiation(null);
    setSelectedOrganizationId(orgId);
    setFreshness("unknown");
    setFreshnessError(null);
  }, []);

  // direction §2: approval progress in the DOM tweens the shared scene state
  useEffect(() => {
    if (state.status !== "ready") return;
    const status = state.deal.status;
    const target = ["AGREED", "EXECUTING", "COMPLETED"].includes(status)
      ? 1
      : status === "PENDING_APPROVALS"
        ? 0.5
        : 0;
    setSceneConsensus(target);
  }, [state]);

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
    setInviteGrants({ role_bundles: [], permissions: [], deal_ids: [] });
    setTeamRecipientEmail("");
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
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(teamRecipientEmail.trim())) {
      setInviteError("Enter the team member's email address.");
      return;
    }
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
        invitation_id: string;
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
          recipient_email: teamRecipientEmail.trim().toLowerCase(),
          ...(inviteGrants.role_bundles.length > 0 ? { role_bundles: inviteGrants.role_bundles } : {}),
          ...(inviteGrants.permissions.length > 0 ? { permissions: inviteGrants.permissions } : {}),
          ...(inviteGrants.deal_ids.length > 0 ? { deal_ids: inviteGrants.deal_ids } : {}),
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

  async function handleCancelInvite() {
    if (!generatedInvite || cancelingInvite) return;
    setCancelingInvite(true);
    setInviteError(null);
    try {
      await apiRequest<void>(`/organizations/${encodeURIComponent(generatedInvite.organization_id)}/invitations/${encodeURIComponent(generatedInvite.invitation_id)}`, { method: "DELETE" });
      setGeneratedInvite(null);
      setInviteError("Invitation revoked. Its link can no longer be accepted.");
    } catch (caught) {
      setInviteError(describeError(caught));
    } finally {
      setCancelingInvite(false);
    }
  }

  if (state.status === "loading") {
    return (
      <section className="card" aria-live="polite">
        <p role="status">Loading deal…</p>
        <div className="skeleton-stack" aria-hidden="true">
          <span className="skeleton-bar skeleton-bar--mid" />
          <span className="skeleton-bar" />
          <span className="skeleton-bar skeleton-bar--short" />
        </div>
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
  const showBanner = !deal.pending_counterparty && freshness === "fresh" && agreementReloadToken === 0;
  const viewingRole = selectedOrganizationId === deal.buyer_organization_id
    ? "BUYER"
    : selectedOrganizationId === deal.seller_organization_id ? "SELLER" : null;

  return (
    <Reveal>
      <div className="workspace deal-workspace">
        {deal.pending_counterparty ? (
          <aside className="deal-onboarding-banner" role="status">
            <h2>Awaiting counterparty</h2>
          </aside>
        ) : null}
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
                Use this guide to move from the first request or quote to agreed terms, payment, and delivery.
              </p>
            </div>

            <section className="deal-onboarding-prep" aria-labelledby="deal-onboarding-prep-heading">
              <div className="deal-onboarding-prep__header">
                <h3 id="deal-onboarding-prep-heading">Information to agree</h3>
                <span className="badge">{viewingRole ? `${viewingRole === "BUYER" ? "Buyer" : "Seller"} checklist` : "Shared checklist"}</span>
              </div>
              <ul className="deal-onboarding-prep__list">
                {viewingRole === "BUYER" ? <>
                  <li>Product or specification, quantity and unit, plus any acceptable alternatives.</li>
                  <li>Your target price and currency, or the price quote you need from the seller.</li>
                  <li>Delivery destination and required date, plus preferred payment amount and timing.</li>
                </> : viewingRole === "SELLER" ? <>
                  <li>Product or specification offered, available quantity and unit, and any limits.</li>
                  <li>Your quoted unit price and currency, plus minimum quantities or other limits.</li>
                  <li>Delivery timing and destination, plus payment amounts and triggers you accept.</li>
                </> : <>
                  <li>The product or specification, quantity, and unit.</li>
                  <li>Price and currency, delivery destination and date.</li>
                  <li>Payment amount, trigger, and due condition.</li>
                </>}
              </ul>
              <p className="deal-onboarding-prep__note">
                Clarify open points in the conversation before proposing terms. The proposal does not
                record taxes, freight, customs classification, or other fees, so agree those separately.
              </p>
            </section>

            <h3 className="deal-onboarding-guide-heading">How the trade moves through SyncAlly</h3>
            <ol className="deal-onboarding-steps" aria-label="How to complete the trade">
              <li className="deal-onboarding-step deal-onboarding-step--active" aria-current="step">
                <div className="deal-onboarding-step__indicator">
                  <span className="deal-onboarding-step__number">1</span>
                  <span className="deal-onboarding-step__line" aria-hidden="true" />
                </div>
                <div className="deal-onboarding-step__content">
                  <strong className="deal-onboarding-step__label">
                    Step 1 · Start with a request or quote
                  </strong>
                  <p className="deal-onboarding-step__text">
                    The buyer describes what they need or asks for a quote. The seller replies with
                    availability and pricing. Keep internal notes private; mark only agreed details
                    shareable with both organizations.
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
                    Step 2 · Confirm the trade details
                  </strong>
                  <p className="deal-onboarding-step__text">
                    Review, correct, or reject suggested facts. Fill gaps manually, then submit a
                    structured proposal with the item, quantities, price, delivery, and payment terms.
                    The other party can accept it for agreement review or send a counterproposal.
                  </p>
                </div>
              </li>

              <li className="deal-onboarding-step">
                <div className="deal-onboarding-step__indicator">
                  <span className="deal-onboarding-step__number">3</span>
                </div>
                <div className="deal-onboarding-step__content">
                  <strong className="deal-onboarding-step__label">
                    Step 3 · Approve and commit
                  </strong>
                  <p className="deal-onboarding-step__text">
                    Both organizations review and approve the same agreement version. If anyone
                    changes the terms, review and approve the new version. An authorized member then
                    commits it; proposals and approvals alone do not finalize the agreement.
                  </p>
                </div>
              </li>

              <li className="deal-onboarding-step">
                <div className="deal-onboarding-step__indicator">
                  <span className="deal-onboarding-step__number">4</span>
                </div>
                <div className="deal-onboarding-step__content">
                  <strong className="deal-onboarding-step__label">
                    Step 4 · Record payment and delivery
                  </strong>
                  <p className="deal-onboarding-step__text">
                    After commitment, the seller requests payment and confirms the invoice recipient.
                    The seller reports shipped quantity; the buyer records and confirms received
                    quantity. SyncAlly marks the deal complete only after all required payments are
                    reconciled and the full quantity is confirmed.
                  </p>
                </div>
              </li>
            </ol>
            <p className="deal-onboarding-prep__note">
              Payment mode matters: PayPal Sandbox is for testing; Offline Demo payment is simulated
              and transfers no money. Check the payment panel before acting.
            </p>

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
                Invite team member
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
                <SplitText text={deal.display_name?.trim() || `Trade with ${counterpartyName}`} />
              </h1>
              <p className="deal-room__lede">
                Discuss the deal, review the details and agree on the terms together. Reviewing a
                detail does not approve the agreement.
              </p>
              <div className="deal-room__state">
                <span className="deal-room__state-dot" aria-hidden="true" />
                <span>{deal.status}</span>
                <span className="deal-room__state-divider" aria-hidden="true" />
                <span>Deal version {deal.version}</span>
              </div>
              <div className="deal-room__actions">
                {!deal.pending_counterparty ? <button
                  type="button"
                  className="button"
                  onClick={handleOpenInviteModal}
                >
                  Invite team member
                </button> : null}
                <button type="button" className="button deal-room__refresh" onClick={retryDeal}>
                  Refresh room <span aria-hidden="true">↻</span>
                </button>
              </div>
            </div>

            <DealConstellation
              buyerOrganizationId={deal.buyer_organization_id}
              sellerOrganizationId={deal.seller_organization_id}
              buyerName={partyNames.buyer || undefined}
              sellerName={partyNames.seller || undefined}
            />
          </div>

          <dl className="deal-room__ledger">
            <div className="deal-room__ledger-item">
              <dt>Deal reference</dt>
              <dd className="mono" title={deal.id}>{deal.id}</dd>
            </div>
            <div className="deal-room__ledger-item">
              <dt>Buyer organization</dt>
              <dd className="mono" title={deal.buyer_organization_id}>
                {partyNames.buyer || deal.buyer_organization_id.slice(0, 8)}
                <span className="visually-hidden">{deal.buyer_organization_id}</span>
              </dd>
            </div>
            <div className="deal-room__ledger-item">
              <dt>Seller organization</dt>
              <dd className="mono" title={deal.seller_organization_id}>
                {partyNames.seller || deal.seller_organization_id.slice(0, 8)}
                <span className="visually-hidden">{deal.seller_organization_id}</span>
              </dd>
            </div>
            <div className="deal-room__ledger-item deal-room__ledger-item--version">
              <dt>Deal version</dt>
              <dd>{deal.version}</dd>
            </div>
          </dl>
        </section>

        <DealOverview
          deal={deal}
          organizationId={selectedOrganizationId}
          reloadToken={agreementReloadToken}
          snapshot={overview}
          partyNames={partyNames}
          onRevealPanel={setDeskTab}
        />
        <div className="deal-desk" data-active-tab={deskTab}>
          <div className="deal-desk__tabs" role="tablist" aria-label="Deal workspace views">
            <button
              type="button"
              role="tab"
              id="deal-desk-tab-trade"
              aria-selected={deskTab === "trade"}
              aria-controls="deal-desk-panel-trade"
              className={deskTab === "trade" ? "deal-desk__tab deal-desk__tab--active" : "deal-desk__tab"}
              onClick={() => setDeskTab("trade")}
            >
              Trade Desk
            </button>
            <button
              type="button"
              role="tab"
              id="deal-desk-tab-obligations"
              aria-selected={deskTab === "obligations"}
              aria-controls="deal-desk-panel-obligations"
              className={deskTab === "obligations" ? "deal-desk__tab deal-desk__tab--active" : "deal-desk__tab"}
              onClick={() => setDeskTab("obligations")}
            >
              Obligations &amp; Delivery
            </button>
            <button
              type="button"
              role="tab"
              id="deal-desk-tab-invoices"
              aria-selected={deskTab === "invoices"}
              aria-controls="deal-desk-panel-invoices"
              className={deskTab === "invoices" ? "deal-desk__tab deal-desk__tab--active" : "deal-desk__tab"}
              onClick={() => setDeskTab("invoices")}
            >
              Invoices &amp; Payments
            </button>
            <button
              type="button"
              role="tab"
              id="deal-desk-tab-audit"
              aria-selected={deskTab === "audit"}
              aria-controls="deal-desk-panel-audit"
              className={deskTab === "audit" ? "deal-desk__tab deal-desk__tab--active" : "deal-desk__tab"}
              onClick={() => setDeskTab("audit")}
            >
              Audit &amp; Legal
            </button>
          </div>
          <div className="deal-desk__panel deal-desk__panel--trade" role="tabpanel" id="deal-desk-panel-trade" aria-labelledby="deal-desk-tab-trade">
            <div className="deal-desk__stream">
        <DealConversationReview
          negotiation={negotiation?.organization_id === selectedOrganizationId && negotiation.deal_id === deal.id ? negotiation : null}
          deal={deal}
          openingMessageDraft={openingMessageDraft?.dealId === deal.id ? openingMessageDraft : undefined}
          onOpeningMessageDraftChange={onOpeningMessageDraftChange}
          onOpeningMessageDraftComplete={onOpeningMessageDraftComplete}
          composerId="deal-message-input"
          buttonLabel="Send message"
          selectedOrganizationId={selectedOrganizationId}
          onOrganizationChange={handleOrganizationChange}
          onAgreementCreated={commercialChanged}
          onMessageCreated={() => {
            setFreshness("not-fresh");
            setFreshnessError(null);
          }}
        />
        {selectedOrganizationId ? <NegotiationReview
          deal={deal} organizationId={selectedOrganizationId} reloadToken={agreementReloadToken}
          onLoaded={setNegotiation} onChanged={commercialChanged}
        /> : null}
            </div>
            <div className="deal-desk__ledger">
        {!deal.pending_counterparty ? <AgreementReview
          key={`agreement:${deal.id}:${selectedOrganizationId}`}
          dealId={deal.id}
          buyerOrganizationId={deal.buyer_organization_id}
          sellerOrganizationId={deal.seller_organization_id}
          buyerOrganizationName={partyNames.buyer}
          sellerOrganizationName={partyNames.seller}
          reloadToken={agreementReloadToken}
          selectedOrganizationId={selectedOrganizationId}
          onOrganizationChange={handleOrganizationChange}
          onCommitted={commercialChanged}
          onOverviewChange={setOverview}
        /> : null}
            </div>
          </div>
          <div className="deal-desk__panel deal-desk__panel--obligations" role="tabpanel" id="deal-desk-panel-obligations" aria-labelledby="deal-desk-tab-obligations">
        <FulfillmentPanel
          dealId={deal.id}
          buyerOrganizationId={deal.buyer_organization_id}
          sellerOrganizationId={deal.seller_organization_id}
          selectedOrganizationId={selectedOrganizationId}
          reloadToken={agreementReloadToken}
          onChanged={commercialChanged}
        />
        <RemindersPanel
          key={`reminders:${deal.id}:${selectedOrganizationId}`}
          deal={deal}
          selectedOrganizationId={selectedOrganizationId}
          reloadToken={agreementReloadToken}
        />
          </div>
          <div className="deal-desk__panel deal-desk__panel--invoices" role="tabpanel" id="deal-desk-panel-invoices" aria-labelledby="deal-desk-tab-invoices">
        <PaymentStatusPanel
          key={`payment:${deal.id}:${selectedOrganizationId}`}
          dealId={deal.id}
          buyerOrganizationId={deal.buyer_organization_id}
          sellerOrganizationId={deal.seller_organization_id}
          selectedOrganizationId={selectedOrganizationId}
          reloadToken={agreementReloadToken}
        />
          </div>
          <div className="deal-desk__panel deal-desk__panel--audit" role="tabpanel" id="deal-desk-panel-audit" aria-labelledby="deal-desk-tab-audit">
        <DealCasesPanel
          key={`cases:${deal.id}`}
          deal={deal}
          selectedOrganizationId={selectedOrganizationId}
          reloadToken={agreementReloadToken}
          onCaseChanged={commercialChanged}
        />
          </div>
        </div>

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
                    Invite team member
                  </h3>
                </div>
                <button
                  type="button"
                  className="button ghost"
                  onClick={() => setShowInviteModal(false)}
                  aria-label="Close"
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden="true">
                    <path d="M3 3 9 9 M9 3 3 9" />
                  </svg>
                </button>
              </div>

              <p className="muted invite-modal__intro">
                Team membership invitation
              </p>

              <form onSubmit={handleGenerateInvite} className="form invite-modal__form">
                <div className="field">
                  <label htmlFor="deal-team-email">Team member email</label>
                  <input
                    id="deal-team-email"
                    type="email"
                    maxLength={320}
                    placeholder="colleague@company.com"
                    value={teamRecipientEmail}
                    disabled={generatingInvite}
                    onChange={(event) => setTeamRecipientEmail(event.target.value)}
                  />
                </div>
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

                {selectedInviteOrgId && state.status === "ready" ? <MemberGrantFields
                  key={selectedInviteOrgId}
                  organizationId={selectedInviteOrgId}
                  isOwner={Boolean(adminOrganizations.find((org) => org.id === selectedInviteOrgId)?.is_owner)}
                  disabled={generatingInvite}
                  onChange={updateInviteGrants}
                /> : null}

                {inviteError ? (
                  <p className="form-error" role="alert">
                    {inviteError}
                  </p>
                ) : null}

                <div className="invite-modal__actions">
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
                <div className="invite-modal__link">
                  <span className="eyebrow">Shareable invitation link</span>
                  <div className="invite-modal__link-row">
                    <input
                      type="text"
                      readOnly
                      aria-label="Shareable invitation link"
                      value={generatedInvite.invite_url}
                      className="mono"
                    />
                    <button
                      type="button"
                      className="button secondary"
                      onClick={handleCopyInviteLink}
                    >
                      {copiedInvite ? "Copied!" : "Copy Link"}
                    </button>
                    <button type="button" className="button danger" disabled={cancelingInvite} onClick={() => void handleCancelInvite()}>
                      {cancelingInvite ? "Revoking…" : "Revoke invitation"}
                    </button>
                  </div>
                  <span className="badge badge--status-confirmed">Expires in 7 days · Single use</span>
                </div>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>
    </Reveal>
  );
}
