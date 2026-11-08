import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, apiRequest, analyzeOpeningRequest, createCounterpartyInvitation, createDeal, getMarketplaceListing, getMarketplaceRFQ, getOrganization, listOrganizations } from "../api/client";
import type { Invitation, OpeningRequestAnalysisResult, Organization, SuggestedSeller } from "../api/types";
import { compactDecimal } from "../formatting";
import Reveal from "../ui/Reveal";
import type { OpeningMessageDraftInput } from "./openingMessageDraft";

type DirectoryItem = Pick<Organization, "id" | "legal_name" | "country_code">;
type SearchState =
  | { status: "idle" | "loading" }
  | { status: "ready"; items: DirectoryItem[] }
  | { status: "error"; message: string };

type OrganizationsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "empty" }
  | { status: "ready"; organizations: Organization[] };

interface FieldErrors {
  buyer?: string;
  seller?: string;
}

interface CreateDealPageProps {
  onCreated: (dealId: string, openingMessageDraft?: OpeningMessageDraftInput | { text: string; source: string }) => void;
  onOpeningMessageDraftReady?: (dealId: string, draft: OpeningMessageDraftInput) => void;
  initialCounterpartyId?: string;
  initialInitiatorParty?: "BUYER" | "SELLER";
  initialRfqId?: string;
  initialListingId?: string;
}

function describeError(caught: unknown): string {
  if (caught instanceof ApiError) {
    return caught.message;
  }
  return "Something went wrong. Please try again.";
}

function describeCreateError(caught: unknown, initiatorParty: "BUYER" | "SELLER"): string {
  if (caught instanceof ApiError) {
    if (caught.status === 401) {
      return "Your session has expired. Sign in again.";
    }
    if (caught.status === 403) {
      return `You cannot create a deal for that ${initiatorParty.toLowerCase()} organization.`;
    }
    if (caught.status === 404) {
      return "The buyer or seller organization was not found.";
    }
    return caught.message;
  }
  return "Unable to create the deal. Please try again.";
}

function counterpartyInviteUrl(invitation: Invitation): string {
  if (import.meta.env.DEV) {
    try {
      const configuredUrl = new URL(invitation.invite_url);
      const localHosts = new Set(["localhost", "127.0.0.1"]);
      if (localHosts.has(configuredUrl.hostname) && localHosts.has(window.location.hostname)) {
        const appPath = window.location.pathname.endsWith("/")
          ? window.location.pathname
          : `${window.location.pathname}/`;
        return `${window.location.origin}${appPath}#/invite?token=${encodeURIComponent(invitation.token)}`;
      }
    } catch {
      // Preserve the trusted server URL when it cannot be parsed locally.
    }
  }
  return invitation.invite_url;
}

function counterpartyInvitePreview(inviteUrl: string): string {
  try {
    const url = new URL(inviteUrl);
    const route = url.hash.split("?")[0] || "#/invite";
    return `${url.origin}${url.pathname}${route}?token=••••••••`;
  } catch {
    return "Single-use invitation link";
  }
}

export default function CreateDealPage({ onCreated, onOpeningMessageDraftReady, initialCounterpartyId, initialInitiatorParty = "BUYER", initialRfqId, initialListingId }: CreateDealPageProps) {
  const [organizationsState, setOrganizationsState] = useState<OrganizationsState>({
    status: "loading",
  });
  const [buyerOrganizationId, setBuyerOrganizationId] = useState("");
  const [initiatorParty, setInitiatorParty] = useState<"BUYER" | "SELLER">(initialInitiatorParty);
  const [query, setQuery] = useState("");
  const [seller, setSeller] = useState<DirectoryItem | null>(null);
  const [searchState, setSearchState] = useState<SearchState>({ status: "idle" });
  const [searchRetry, setSearchRetry] = useState(0);
  const [searchOpen, setSearchOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loadingListingContext, setLoadingListingContext] = useState(Boolean(initialListingId));
  const [reloadCount, setReloadCount] = useState(0);
  const [mode, setMode] = useState<"directory" | "invite">("directory");
  const [recipientEmail, setRecipientEmail] = useState("");
  const [counterpartyName, setCounterpartyName] = useState("");
  const [countryCode, setCountryCode] = useState("US");
  const [invitation, setInvitation] = useState<Invitation | null>(null);
  const [invitationOpeningDraft, setInvitationOpeningDraft] = useState<OpeningMessageDraftInput | null>(null);
  const [copied, setCopied] = useState(false);
  const [showFullInvitationLink, setShowFullInvitationLink] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [openingMessage, setOpeningMessage] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<OpeningRequestAnalysisResult | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const organizations = await listOrganizations();
        if (cancelled) {
          return;
        }
        if (organizations.length === 0) {
          setOrganizationsState({ status: "empty" });
          return;
        }
        setOrganizationsState({ status: "ready", organizations });
        setBuyerOrganizationId((current) => current || organizations[0].id);
      } catch (caught) {
        if (!cancelled) {
          setOrganizationsState({ status: "error", message: describeError(caught) });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reloadCount]);

  useEffect(() => {
    if (mode !== "directory" || !query.trim() || seller) return;
    let cancelled = false;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      void apiRequest<DirectoryItem[]>(
        `/organizations/directory?q=${encodeURIComponent(query.trim())}`,
        { signal: controller.signal },
      ).then(
        (items) => {
          if (!cancelled) setSearchState({ status: "ready", items });
        },
        (caught: unknown) => {
          if (!cancelled) setSearchState({ status: "error", message: describeError(caught) });
        },
      );
    }, 250);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [query, seller, searchRetry, mode]);

  useEffect(() => {
    if (!initialCounterpartyId) return;
    let cancelled = false;
    void getOrganization(initialCounterpartyId).then(
      (item) => {
        if (cancelled) return;
        setSeller(item);
        setQuery(item.legal_name);
        setMode("directory");
      },
      (caught: unknown) => {
        if (!cancelled) setSubmitError(describeError(caught));
      },
    );
    return () => { cancelled = true; };
  }, [initialCounterpartyId]);

  useEffect(() => {
    if (!initialRfqId) return;
    let cancelled = false;
    void getMarketplaceRFQ(initialRfqId).then(
      (rfq) => {
        if (cancelled) return;
        const requestedTerms = [
          `We're responding to your request for ${rfq.title} (${rfq.category}).`,
          `Requested quantity: ${compactDecimal(rfq.quantity)} ${rfq.unit}.`,
          `Delivery destination: ${rfq.destination_country_code}${rfq.target_delivery_date ? ` by ${rfq.target_delivery_date}` : ""}.`,
          rfq.target_unit_price && rfq.currency ? `Target price: ${compactDecimal(rfq.target_unit_price)} ${rfq.currency} per ${rfq.unit}.` : "",
          rfq.description ? `Requirements: ${rfq.description}` : "",
          "Please review our quote and proposed trade terms.",
        ].filter(Boolean);
        setOpeningMessage(`Hello ${rfq.organization_name},\n\n${requestedTerms.join("\n")}`);
      },
      (caught: unknown) => {
        if (!cancelled) setSubmitError(describeError(caught));
      },
    );
    return () => { cancelled = true; };
  }, [initialRfqId]);

  useEffect(() => {
    if (!initialListingId) return;
    let cancelled = false;
    void getMarketplaceListing(initialListingId).then(
      (listing) => {
        if (cancelled) return;
        if (initialCounterpartyId && listing.organization_id !== initialCounterpartyId) {
          setSubmitError("This listing belongs to a different seller. Reopen the deal from the marketplace.");
          return;
        }
        const openingLines = [
          `Hello ${listing.organization_name},`,
          "",
          `I'm interested in your ${listing.title} listing (${listing.category}).`,
          `Listed availability: ${compactDecimal(listing.available_quantity)} ${listing.unit}.`,
          `Listed price: ${compactDecimal(listing.unit_price)} ${listing.currency} / ${listing.unit}.`,
          listing.description ? `Listing details: ${listing.description}` : null,
          "",
          "Please confirm current availability and share delivery options and payment terms.",
        ].filter((line) => line !== null);
        setOpeningMessage(openingLines.join("\n"));
      },
      (caught: unknown) => {
        if (!cancelled) setSubmitError(describeError(caught));
      },
    ).finally(() => {
      if (!cancelled) setLoadingListingContext(false);
    });
    return () => { cancelled = true; };
  }, [initialCounterpartyId, initialListingId]);

  const results = searchState.status === "ready" ? searchState.items : [];
  const listOpen = searchOpen && results.length > 0;
  const marketplaceContext = Boolean(initialListingId || initialRfqId);

  function selectSeller(item: DirectoryItem) {
    setSeller(item);
    setQuery(item.legal_name);
    setSearchState({ status: "idle" });
    setSearchOpen(false);
    setActiveIndex(-1);
    setFieldErrors({});
  }

  async function handleAnalyzeOpeningRequest() {
    const textToAnalyze = openingMessage.trim();
    if (!textToAnalyze || analyzing || submitting) return;
    setAnalyzing(true);
    setAnalysisError(null);
    try {
      const result = await analyzeOpeningRequest({
        text: textToAnalyze,
        buyer_organization_id: buyerOrganizationId || undefined,
      });
      setAnalysisResult(result);
    } catch (caught) {
      setAnalysisError(describeError(caught));
    } finally {
      setAnalyzing(false);
    }
  }

  function handleSelectSuggestedSeller(suggested: SuggestedSeller) {
    setMode("directory");
    selectSeller({
      id: suggested.id,
      legal_name: suggested.legal_name,
      country_code: suggested.country_code,
    });
  }

  function retryOrganizations() {
    setOrganizationsState({ status: "loading" });
    setReloadCount((count) => count + 1);
  }

  function copyInvitationLink(url: string) {
    setCopied(false);
    setSubmitError(null);
    if (!navigator.clipboard?.writeText) {
      setShowFullInvitationLink(true);
      setSubmitError("Could not copy the link. Open the full link below and copy it manually.");
      return;
    }
    void navigator.clipboard.writeText(url).then(
      () => setCopied(true),
      () => {
        setShowFullInvitationLink(true);
        setSubmitError("Could not copy the link. Open the full link below and copy it manually.");
      },
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (submitting) return;
    const nextErrors: FieldErrors = {};
    if (buyerOrganizationId === "") {
      nextErrors.buyer = "Choose your organization.";
    }
    if (mode === "invite") {
      const buyer = organizationsState.status === "ready" ? organizationsState.organizations.find((org) => org.id === buyerOrganizationId) : null;
      if (buyer?.role !== "ADMIN") nextErrors.buyer = "An organization admin is required to invite a counterparty.";
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(recipientEmail.trim()) || !counterpartyName.trim() || !/^[A-Z]{2}$/.test(countryCode.trim().toUpperCase())) {
        nextErrors.seller = "Enter the counterparty email, company legal name, and two-letter country code.";
      }
    } else if (!seller) {
      nextErrors.seller = `Choose a ${initiatorParty === "BUYER" ? "seller" : "buyer"} organization from the search results.`;
    } else if (seller.id === buyerOrganizationId) {
      nextErrors.seller = "Buyer and seller must be different organizations.";
    }
    setFieldErrors(nextErrors);
    setSubmitError(null);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setSubmitting(true);
    try {
      const openingMessageText = openingMessage.trim();
      const openingMessageDraft = openingMessageText
        ? {
            organizationId: buyerOrganizationId,
            body: openingMessageText,
            visibility: "SHAREABLE" as const,
            idempotencyKey: null,
          }
        : undefined;
      if (mode === "invite") {
        const result = await createCounterpartyInvitation({ ...(initiatorParty === "BUYER"
          ? { buyer_organization_id: buyerOrganizationId }
          : { inviting_organization_id: buyerOrganizationId, inviter_party: "SELLER" as const }),
          recipient_email: recipientEmail.trim().toLowerCase(), legal_name: counterpartyName.trim(),
          country_code: countryCode.trim().toUpperCase(),
          ...(displayName.trim() ? { display_name: displayName.trim() } : {}) });
        setCopied(false);
        setShowFullInvitationLink(false);
        setInvitationOpeningDraft(result.deal_id && openingMessageDraft ? openingMessageDraft : null);
        if (result.deal_id && openingMessageDraft) {
          onOpeningMessageDraftReady?.(result.deal_id, openingMessageDraft);
        }
        setInvitation(result);
        return;
      }
      if (!seller) return;
      const dealPayload = analysisResult ? {
        buyer_organization_id: initiatorParty === "BUYER" ? buyerOrganizationId : seller.id,
        seller_organization_id: initiatorParty === "SELLER" ? buyerOrganizationId : seller.id,
        initiator_party: initiatorParty,
        display_name: displayName.trim() || undefined,
      } : {
        buyer_organization_id: initiatorParty === "BUYER" ? buyerOrganizationId : seller.id,
        seller_organization_id: initiatorParty === "SELLER" ? buyerOrganizationId : seller.id,
        ...(displayName.trim() ? { display_name: displayName.trim() } : {}),
        ...(initiatorParty === "SELLER" ? { initiator_party: "SELLER" as const } : {}),
      };
      const deal = await createDeal(dealPayload);
      if (analysisResult && openingMessageText) {
        onCreated(deal.id, { text: openingMessageText, source: "BUYER_QUOTE" });
      } else if (openingMessageDraft) {
        onCreated(deal.id, openingMessageDraft);
      } else {
        onCreated(deal.id);
      }
    } catch (caught) {
      setSubmitError(describeCreateError(caught, initiatorParty));
    } finally {
      setSubmitting(false);
    }
  }

  const header = (
    <Reveal className="hero">
      <span className="eyebrow">New deal</span>
      <h1 className="display">
        Open a <span className="gradient-text">draft.</span>
      </h1>
      <p className="hero__lede">
        Start with a buyer and a seller organization. Review shareable conversation facts before
        negotiating terms; fact review does not commit an agreement.
      </p>
    </Reveal>
  );

  if (organizationsState.status === "loading") {
    return (
      <div className="workspace">
        {header}
        <section className="card" aria-live="polite">
          <p role="status">Loading organizations…</p>
        </section>
      </div>
    );
  }

  if (organizationsState.status === "error") {
    return (
      <div className="workspace">
        {header}
        <section className="card" role="alert">
          <h2>We could not load your organizations</h2>
          <p className="muted" style={{ marginTop: 10 }}>
            {organizationsState.message}
          </p>
          <div className="actions">
            <button type="button" className="button" onClick={retryOrganizations}>
              Try again
            </button>
          </div>
        </section>
      </div>
    );
  }

  if (organizationsState.status === "empty") {
    return (
      <div className="workspace">
        {header}
        <section className="card">
          <h2>No organizations yet</h2>
          <p className="muted" style={{ marginTop: 10 }}>
            Your account is not an active member of any organization, so you cannot create a deal
            yet.
          </p>
        </section>
      </div>
    );
  }

  if (invitation) {
    const invitationUrl = counterpartyInviteUrl(invitation);
    return (
      <div className="workspace counterparty-invitation-page">
        <Reveal>
          <section className="card counterparty-invitation" aria-labelledby="counterparty-invitation-heading">
            <div className="counterparty-invitation__eyebrow-row">
              <span className="eyebrow">Counterparty invitation</span>
              <span className="badge">Single use</span>
            </div>
            <h1 id="counterparty-invitation-heading" className="display">Awaiting counterparty</h1>
            <p className="counterparty-invitation__summary" role="status">
              Your deal is ready, but the invitation has not been sent. Copy the link and send it securely to {recipientEmail.trim().toLowerCase()}.
            </p>
            {invitationOpeningDraft ? <p className="hint">
              Your opening request is carried into the pending deal. You can review and send it after the counterparty joins.
            </p> : null}

            <div className="counterparty-invitation__recipient">
              <span className="counterparty-invitation__label">INVITED EMAIL</span>
              <strong>{recipientEmail.trim().toLowerCase()}</strong>
            </div>

            <div className="counterparty-invitation__link-card">
              <div>
                <span className="counterparty-invitation__label">INVITATION LINK</span>
                <code className="counterparty-invitation__preview">
                  {counterpartyInvitePreview(invitationUrl)}
                </code>
                <p className="hint">Only share this single-use link with the intended recipient.</p>
              </div>
              <button type="button" className="button" onClick={() => copyInvitationLink(invitationUrl)}>
                {copied ? "Copied!" : "Copy Link"}
              </button>
            </div>

            <details
              className="counterparty-invitation__full-link"
              open={showFullInvitationLink}
              onToggle={(event) => setShowFullInvitationLink(event.currentTarget.open)}
            >
              <summary>Show full link for manual copy</summary>
              <label htmlFor="counterparty-link">Counterparty invitation link</label>
              <textarea id="counterparty-link" readOnly rows={3} value={invitationUrl} />
            </details>

            <div className="counterparty-invitation__expiry">
              <span>Expires</span>
              <time dateTime={invitation.expires_at}>
                {new Date(invitation.expires_at).toLocaleString()}
              </time>
            </div>

            {submitError ? <p className="form-error" role="alert">{submitError}</p> : null}

            <div className="actions counterparty-invitation__actions">
              <button
                type="button"
                className="button secondary"
                disabled={!invitation.deal_id}
                onClick={() => invitation.deal_id && onCreated(invitation.deal_id)}
              >
                Open pending deal
              </button>
            </div>
          </section>
        </Reveal>
      </div>
    );
  }

  return (
    <div className="workspace">
      {header}
      <Reveal delay={80}>
        <section className="card" aria-labelledby="create-deal-heading">
          <div className="panel-head">
            <span className="eyebrow">Draft deal</span>
            <h2 id="create-deal-heading">{initialListingId ? "Start a deal from this listing" : initialRfqId ? "Respond to a buyer request" : "Create a draft deal"}</h2>
          </div>
          <p className="muted">
            {marketplaceContext
              ? initialListingId
                ? "You’re the buyer. The seller and product are from the listing you chose."
                : "You’re responding as the seller. The buyer and requirements are from their request."
              : "Choose your role and the other company for this deal."}
          </p>
          <form className="form" onSubmit={handleSubmit} noValidate style={{ marginTop: 22 }}>
            {!marketplaceContext ? (
              <fieldset disabled={submitting}>
                <legend>Your role</legend>
                <label><input type="radio" name="initiator-party" checked={initiatorParty === "BUYER"} onChange={() => { setInitiatorParty("BUYER"); setFieldErrors({}); }} /> Buyer</label>
                <label><input type="radio" name="initiator-party" checked={initiatorParty === "SELLER"} onChange={() => { setInitiatorParty("SELLER"); setFieldErrors({}); }} /> Seller</label>
              </fieldset>
            ) : null}
            <div className="field">
              <label htmlFor="deal-display-name">Deal name (optional)</label>
              <input id="deal-display-name" type="text" maxLength={160} value={displayName}
                placeholder="e.g. Toronto office furniture order" disabled={submitting}
                onChange={(event) => setDisplayName(event.target.value)} />
              <p className="hint">A short name helps both sides find this deal later.</p>
            </div>
            <div className="field">
              <label htmlFor="deal-opening-message">{initialListingId ? "Message to the seller (optional)" : initialRfqId ? "Quote to the buyer (optional)" : "Opening request or quote (optional)"}</label>
              <textarea
                id="deal-opening-message"
                value={openingMessage}
                maxLength={8000}
                rows={initialListingId ? 8 : 4}
                disabled={submitting || analyzing}
                placeholder={initiatorParty === "BUYER"
                  ? "We need [product/specification], [quantity and unit], delivered to [destination] by [date]. Please quote in [currency] and include your payment terms."
                  : "We can offer [product/specification], [available quantity and unit] at [price and currency], delivered to [destination] by [date]. Our payment terms are [terms]."}
                onChange={(event) => {
                  setOpeningMessage(event.target.value);
                  if (analysisResult) setAnalysisResult(null);
                  if (analysisError) setAnalysisError(null);
                }}
              />
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8, flexWrap: "wrap", gap: 8 }}>
                <p className="hint" style={{ margin: 0 }}>
                  {marketplaceContext ? "The deal stays a draft until you send this message." : "The deal stays a draft until you send this message. If you invite a company, it will be ready after they join."}
                </p>
                {initiatorParty === "BUYER" && !marketplaceContext ? (
                  <button
                    type="button"
                    className="button secondary"
                    disabled={submitting || analyzing || !openingMessage.trim()}
                    onClick={handleAnalyzeOpeningRequest}
                  >
                    {analyzing ? "Analyzing request…" : "Analyze & suggest sellers"}
                  </button>
                ) : null}
              </div>
            </div>

            {analysisError ? (
              <div className="form-error" role="alert" style={{ marginBottom: 16 }}>
                {analysisError}
              </div>
            ) : null}

            {analysisResult ? (
              <div className="card normalized-requirements-card" style={{ marginBottom: 20, padding: 16, border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface-sunken)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
                  <h3 style={{ margin: 0, fontSize: "1rem" }}>Structured Requirements</h3>
                  {analysisResult.provenance ? (
                    <span className="badge" style={{ fontSize: "0.75rem" }}>
                      {analysisResult.provenance.provider === "openai" || analysisResult.provenance.mode === "openai"
                        ? "AI Extracted (OpenAI)"
                        : "Offline Normalization"}
                    </span>
                  ) : null}
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12, marginBottom: 16 }}>
                  {analysisResult.requirements.category ? (
                    <div><small className="muted">Category</small><div><strong>{analysisResult.requirements.category}</strong></div></div>
                  ) : null}
                  {analysisResult.requirements.item_description ? (
                    <div><small className="muted">Item / Specification</small><div><strong>{analysisResult.requirements.item_description}</strong></div></div>
                  ) : null}
                  {analysisResult.requirements.quantity ? (
                    <div><small className="muted">Quantity</small><div><strong>{analysisResult.requirements.quantity} {analysisResult.requirements.unit || ""}</strong></div></div>
                  ) : null}
                  {analysisResult.requirements.target_unit_price || analysisResult.requirements.budget ? (
                    <div><small className="muted">Target Price / Budget</small><div><strong>{analysisResult.requirements.target_unit_price || analysisResult.requirements.budget} {analysisResult.requirements.currency || ""}</strong></div></div>
                  ) : null}
                  {analysisResult.requirements.destination_name || analysisResult.requirements.destination_country_code || analysisResult.requirements.delivery_destination ? (
                    <div><small className="muted">Destination</small><div><strong>{analysisResult.requirements.destination_name || analysisResult.requirements.destination_country_code || analysisResult.requirements.delivery_destination}</strong></div></div>
                  ) : null}
                  {analysisResult.requirements.target_delivery_date || analysisResult.requirements.delivery_date ? (
                    <div><small className="muted">Timeline</small><div><strong>{analysisResult.requirements.target_delivery_date || analysisResult.requirements.delivery_date}</strong></div></div>
                  ) : null}
                  {analysisResult.requirements.capabilities_required && analysisResult.requirements.capabilities_required.length > 0 ? (
                    <div><small className="muted">Required Capabilities</small><div><strong>{analysisResult.requirements.capabilities_required.join(", ")}</strong></div></div>
                  ) : null}
                </div>

                {(() => {
                  const buyerOrg = organizationsState.status === "ready"
                    ? organizationsState.organizations.find((org) => org.id === buyerOrganizationId)
                    : null;
                  const candidateSellers = (analysisResult.suggested_sellers || []).filter(
                    (s) => s.id !== buyerOrganizationId && (!buyerOrg || s.legal_name !== buyerOrg.legal_name)
                  );

                  if (candidateSellers.length > 0) {
                    return (
                      <div className="suggested-sellers-list">
                        <h4 style={{ margin: "12px 0 8px 0", fontSize: "0.9rem" }}>
                          Suggested Matching Sellers ({candidateSellers.length})
                        </h4>
                        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                          {candidateSellers.map((suggested) => {
                            const isSelected = seller?.id === suggested.id;
                            return (
                              <div
                                key={suggested.id}
                                data-testid="suggested-seller-card"
                                style={{
                                  display: "flex",
                                  justifyContent: "space-between",
                                  alignItems: "center",
                                  padding: "10px 14px",
                                  borderRadius: 6,
                                  border: isSelected ? "1px solid var(--accent)" : "1px solid var(--border)",
                                  background: isSelected ? "var(--accent-soft)" : "var(--surface)",
                                }}
                              >
                                <div>
                                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                    <strong>{suggested.legal_name}</strong>
                                    <span className="badge">{suggested.country_code}</span>
                                    {suggested.match_score != null ? (
                                      <span className="badge">{Math.round(suggested.match_score * 100)}%</span>
                                    ) : null}
                                    {isSelected ? <span className="badge badge--shareable">Selected</span> : null}
                                  </div>
                                  {suggested.match_reasons && suggested.match_reasons.length > 0 ? (
                                    <small className="muted" style={{ display: "block", marginTop: 4 }}>
                                      {suggested.match_reasons.join(" • ")}
                                    </small>
                                  ) : null}
                                </div>
                                <button
                                  type="button"
                                  className={`button ${isSelected ? "primary" : "secondary"}`}
                                  style={{ fontSize: "0.85rem", padding: "6px 12px" }}
                                  onClick={() => handleSelectSuggestedSeller(suggested)}
                                >
                                  {isSelected ? "Selected" : "Select Seller"}
                                </button>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  }

                  return (
                    <p className="muted" role="status" style={{ margin: "12px 0 0", fontSize: "0.9rem" }}>
                      No registered sellers matched your requirements. You can search manually below or invite a counterparty.
                    </p>
                  );
                })()}
              </div>
            ) : null}
            {!marketplaceContext ? (
              <fieldset disabled={submitting}>
                <legend>Counterparty</legend>
                <label><input type="radio" name="counterparty-mode" checked={mode === "directory"} onChange={() => { setMode("directory"); setFieldErrors({}); }} /> Existing organization</label>
                <label><input type="radio" name="counterparty-mode" checked={mode === "invite"} onChange={() => { setMode("invite"); setFieldErrors({}); }} /> Invite counterparty</label>
              </fieldset>
            ) : null}
            <div className="field">
              <label htmlFor="buyer-organization">{marketplaceContext ? "Your organization" : initiatorParty === "BUYER" ? "Buyer organization" : "Seller organization"}</label>
              <select
                id="buyer-organization"
                name="buyer-organization"
                value={buyerOrganizationId}
                aria-invalid={fieldErrors.buyer ? true : undefined}
                disabled={submitting}
                onChange={(event) => {
                  setBuyerOrganizationId(event.target.value);
                  setFieldErrors(seller?.id === event.target.value
                    ? { seller: "Buyer and seller must be different organizations." }
                    : {});
                }}
              >
                {organizationsState.organizations.map((organization) => (
                  <option key={organization.id} value={organization.id}>
                    {organization.legal_name} ({organization.country_code})
                  </option>
                ))}
              </select>
              {fieldErrors.buyer ? (
                <p className="field-error" role="alert">
                  {fieldErrors.buyer}
                </p>
              ) : null}
            </div>
            {marketplaceContext ? (
              <div className="field">
                <label htmlFor="marketplace-other-company">{initiatorParty === "BUYER" ? "Seller" : "Buyer"}</label>
                <input id="marketplace-other-company" value={seller?.legal_name ?? "Loading company…"} readOnly />
                <p className="hint">Selected from the marketplace {initialListingId ? "listing" : "request"}.</p>
              </div>
            ) : mode === "invite" ? <>
              <div className="field"><label htmlFor="counterparty-email">Counterparty email</label><input id="counterparty-email" type="email" maxLength={320} disabled={submitting} value={recipientEmail} onChange={(event) => setRecipientEmail(event.target.value)} /></div>
              <div className="field"><label htmlFor="counterparty-name">Counterparty company legal name</label><input id="counterparty-name" maxLength={200} disabled={submitting} value={counterpartyName} onChange={(event) => setCounterpartyName(event.target.value)} /></div>
              <div className="field"><label htmlFor="counterparty-country">Country code</label><input id="counterparty-country" maxLength={2} disabled={submitting} value={countryCode} onChange={(event) => setCountryCode(event.target.value.toUpperCase())} /></div>
              {fieldErrors.seller ? <p role="alert">{fieldErrors.seller}</p> : null}
            </> : <div className="field">
              <label htmlFor="seller-organization">{initiatorParty === "BUYER" ? "Seller organization" : "Buyer organization"}</label>
              <input
                id="seller-organization"
                name="seller-organization"
                type="text"
                role="combobox"
                autoComplete="off"
                maxLength={100}
                placeholder="Search by company name"
                value={query}
                disabled={submitting}
                aria-autocomplete="list"
                aria-expanded={listOpen}
                aria-controls={listOpen ? "seller-results" : undefined}
                aria-activedescendant={listOpen && activeIndex >= 0
                  ? `seller-option-${activeIndex}` : undefined}
                aria-invalid={fieldErrors.seller ? true : undefined}
                aria-describedby={fieldErrors.seller ? "seller-error" : "seller-organization-hint"}
                onFocus={() => setSearchOpen(true)}
                onBlur={() => setSearchOpen(false)}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setSeller(null);
                  setSearchState({ status: event.target.value.trim() ? "loading" : "idle" });
                  setSearchOpen(true);
                  setActiveIndex(-1);
                  setFieldErrors({});
                }}
                onKeyDown={(event) => {
                  if (event.key === "Escape") {
                    setSearchOpen(false);
                    setActiveIndex(-1);
                  } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                    event.preventDefault();
                    setSearchOpen(true);
                    if (results.length) setActiveIndex((current) =>
                      event.key === "ArrowDown"
                        ? (current + 1) % results.length
                        : (current <= 0 ? results.length - 1 : current - 1));
                  } else if (event.key === "Enter" && listOpen) {
                    event.preventDefault();
                    if (activeIndex >= 0) selectSeller(results[activeIndex]);
                  }
                }}
              />
              <p id="seller-organization-hint" className="hint">
                Search for a company, then select the {initiatorParty === "BUYER" ? "seller" : "buyer"} from the results.
              </p>
              {listOpen ? (
                <ul id="seller-results" role="listbox" aria-label={initiatorParty === "BUYER" ? "Seller organizations" : "Buyer organizations"}
                  style={{ listStyle: "none", padding: 0 }}>
                  {results.map((item, index) => (
                    <li key={item.id} id={`seller-option-${index}`} role="option"
                      aria-selected={activeIndex === index}
                      style={{ padding: 10, cursor: "pointer",
                        background: activeIndex === index ? "var(--accent-soft)" : undefined }}
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => selectSeller(item)}>
                      {item.legal_name} <span className="badge">{item.country_code}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
              {searchState.status === "loading" ? <p role="status">Searching organizations...</p> : null}
              {searchState.status === "ready" && results.length === 0 ? (
                <p role="status">No organizations found. Try another company name.</p>
              ) : null}
              {searchState.status === "error" ? (
                <div role="alert">
                  <p>{searchState.message}</p>
                  <button type="button" className="button" disabled={submitting} onClick={() => {
                    setSearchState({ status: "loading" });
                    setSearchRetry((count) => count + 1);
                    setSearchOpen(true);
                  }}>Retry search</button>
                </div>
              ) : null}
              {fieldErrors.seller ? (
                <p id="seller-error" className="field-error" role="alert">
                  {fieldErrors.seller}
                </p>
              ) : null}
            </div>}
            {submitError ? (
              <p className="form-error" role="alert">
                {submitError}
              </p>
            ) : null}
            <button type="submit" className="button" disabled={submitting || loadingListingContext}>
              {loadingListingContext ? "Loading listing…" : submitting ? "Creating deal…" : "Create deal"}
            </button>
          </form>
        </section>
      </Reveal>
    </div>
  );
}
