import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, apiRequest, listOrganizations } from "../api/client";
import type { Invitation as CreateInvitationResponse, InvitationAcceptance as AcceptInvitationResponse, Organization } from "../api/types";
import { invitationPresentation } from "../auth/invitationPresentation";
import { navigateToDeal, navigateToDeals, navigateToOrganizations, parseRoute } from "../router";
import OrganizationsPanel from "./OrganizationsPanel";
import Reveal from "../ui/Reveal";

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

export default function OrganizationsSettingsPage({ onAccepted }: {
  onAccepted?: (result: AcceptInvitationResponse, isCurrentInvitation: () => boolean) => Promise<void>;
}) {
  // Invite Generator Modal State
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [adminOrganizations, setAdminOrganizations] = useState<Organization[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [recipientEmail, setRecipientEmail] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [generatedInvite, setGeneratedInvite] = useState<CreateInvitationResponse | null>(null);
  const [copied, setCopied] = useState(false);

  // Accept Invitation Flow State
  const [inviteToken, setInviteToken] = useState<string | null>(null);
  const [acceptOrgName, setAcceptOrgName] = useState("");
  const [acceptCountryCode, setAcceptCountryCode] = useState("US");
  const [accepting, setAccepting] = useState(false);
  const [acceptError, setAcceptError] = useState<string | null>(null);
  const [acceptedResult, setAcceptedResult] = useState<AcceptInvitationResponse | null>(null);
  // Tracks which token the accept outcome above belongs to, so a new invite starts clean.
  const lastInviteTokenRef = useRef<string | null>(null);
  const invitationGenerationRef = useRef(0);
  const intent = invitationPresentation(inviteToken);

  // Extract invite token from hash on mount and hashchange
  useEffect(() => {
    function checkHashForInvite() {
      const hash = window.location.hash;
      const rawPath = hash.startsWith("#") ? hash.slice(1) : hash;
      const [, queryString] = rawPath.split("?");
      const token = (queryString ? new URLSearchParams(queryString).get("token") : null) ?? null;
      if (token !== lastInviteTokenRef.current) {
        invitationGenerationRef.current += 1;
        // A different invitation is being opened: discard the previous invitation's outcome
        // so its result or error cannot leak into the new accept flow.
        lastInviteTokenRef.current = token;
        setAcceptedResult(null);
        setAcceptError(null);
        setAcceptOrgName("");
        setAcceptCountryCode("US");
        setAccepting(false);
      }
      setInviteToken(token);
    }

    checkHashForInvite();
    window.addEventListener("hashchange", checkHashForInvite);
    return () => {
      invitationGenerationRef.current += 1;
      window.removeEventListener("hashchange", checkHashForInvite);
    };
  }, []);

  // Fetch admin organizations when opening the invite modal
  async function handleOpenInviteModal() {
    setShowInviteModal(true);
    setGenerateError(null);
    setGeneratedInvite(null);
    setCopied(false);
    try {
      const orgs = await listOrganizations();
      const admins = orgs.filter((org) => org.role === "ADMIN");
      setAdminOrganizations(admins);
      if (admins.length > 0 && !selectedOrgId) {
        setSelectedOrgId(admins[0].id);
      }
    } catch (caught) {
      setGenerateError(describeError(caught));
    }
  }

  async function handleGenerateInvite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedOrgId && adminOrganizations.length > 0) {
      setSelectedOrgId(adminOrganizations[0].id);
    }
    const targetOrgId = selectedOrgId || (adminOrganizations[0] ? adminOrganizations[0].id : "");
    if (!targetOrgId) {
      setGenerateError("Please select an organization where you are an admin.");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(recipientEmail.trim())) {
      setGenerateError("Enter the team member's email address.");
      return;
    }

    setGenerating(true);
    setGenerateError(null);
    try {
      const res = await apiRequest<CreateInvitationResponse>(
        `/organizations/${encodeURIComponent(targetOrgId)}/invitations`,
        {
          method: "POST",
          body: JSON.stringify({
            recipient_email: recipientEmail.trim().toLowerCase(),
          }),
        },
      );
      setGeneratedInvite(res);
    } catch (caught) {
      setGenerateError(describeError(caught));
    } finally {
      setGenerating(false);
    }
  }

  async function handleCopyLink() {
    if (!generatedInvite) return;
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(generatedInvite.invite_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      setCopied(false);
    }
  }

  async function handleAcceptInvite() {
    if (!inviteToken || accepting || intent.kind === "INVALID") return;
    if (intent.kind === "COUNTERPARTY" && !acceptOrgName.trim()) {
      setAcceptError("Your company legal name is required.");
      return;
    }
    const acceptingToken = inviteToken;
    const acceptingGeneration = invitationGenerationRef.current;
    const isCurrentInvitation = () => {
      const currentRoute = parseRoute(window.location.hash);
      return invitationGenerationRef.current === acceptingGeneration &&
        lastInviteTokenRef.current === acceptingToken &&
        currentRoute.name === "organizations" && currentRoute.inviteToken === acceptingToken;
    };
    setAccepting(true);
    setAcceptError(null);
    try {
      const payload: {
        token: string;
        organization_legal_name?: string;
        country_code?: string;
      } = { token: inviteToken };
      if (intent.kind !== "TEAM" && acceptOrgName.trim()) {
        payload.organization_legal_name = acceptOrgName.trim();
        payload.country_code = acceptCountryCode.trim().toUpperCase() || "US";
      }

      const res = await apiRequest<AcceptInvitationResponse>("/invitations/accept", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (!isCurrentInvitation()) return;
      setAcceptedResult(res);
      await onAccepted?.(res, isCurrentInvitation);
    } catch (caught) {
      if (isCurrentInvitation()) setAcceptError(describeError(caught));
    } finally {
      if (isCurrentInvitation()) setAccepting(false);
    }
  }

  function handleDismissAcceptModal() {
    setInviteToken(null);
    navigateToOrganizations();
  }

  return (
    <div className="workspace">
      <Reveal className="hero">
        <div className="workspace-intro__meta">
          <span className="eyebrow">Settings / Organizations</span>
          <span className="workspace-intro__caption">Counterparty directory &amp; members</span>
        </div>
        <h1 className="display">Organizations.</h1>
        <p className="hero__lede">
          Share your organization IDs with counterparties to create deals, manage registered trading
          entities, and invite team members.
        </p>
        <div style={{ marginTop: 24, display: "flex", gap: 12 }}>
          <button
            type="button"
            className="button"
            onClick={handleOpenInviteModal}
          >
            Invite team member
          </button>
        </div>
      </Reveal>

      <Reveal delay={80}>
        <OrganizationsPanel />
      </Reveal>

      {/* Shareable Invitation Modal */}
      {showInviteModal && (
        <div
          className="manual-fact-modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="invite-modal-title"
        >
          <div className="manual-fact-modal">
            <div className="panel-head">
              <div>
                <span className="eyebrow">Onboarding</span>
                <h3 id="invite-modal-title" className="display" style={{ fontSize: "1.25rem" }}>
                  Invite team member
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

            <p className="muted" style={{ fontSize: "0.9rem", marginBottom: 16 }}>
              Team membership invitation
            </p>

            <form className="form" onSubmit={handleGenerateInvite} noValidate>
              <div className="field">
                <label htmlFor="invite-modal-org">Inviting organization</label>
                <select
                  id="invite-modal-org"
                  value={selectedOrgId}
                  onChange={(e) => setSelectedOrgId(e.target.value)}
                  disabled={generating || adminOrganizations.length === 0}
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

              <div className="field">
                <label htmlFor="invite-modal-email">Team member email</label>
                <input
                  id="invite-modal-email"
                  type="email"
                  maxLength={320}
                  value={recipientEmail}
                  onChange={(e) => setRecipientEmail(e.target.value)}
                  disabled={generating}
                />
              </div>

              {generateError && (
                <p className="form-error" role="alert">
                  {generateError}
                </p>
              )}

              <div style={{ marginTop: 12 }}>
                <button
                  type="submit"
                  className="button"
                  disabled={generating || adminOrganizations.length === 0}
                >
                  {generating ? "Generating link…" : "Generate Invite Link"}
                </button>
              </div>
            </form>

            {generatedInvite && (
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
                    onClick={handleCopyLink}
                  >
                    {copied ? "Copied!" : "Copy Link"}
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
                    Expires in 7 days · Single use
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Accept Invitation Modal (Opens when navigating with ?token=...) */}
      {inviteToken && (
        <div
          className="manual-fact-modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="accept-modal-title"
        >
          <div className="manual-fact-modal">
            <div className="panel-head">
              <div>
                <span className="eyebrow">Invitation</span>
                <h3 id="accept-modal-title" className="display" style={{ fontSize: "1.25rem" }}>
                  {intent.kind === "TEAM" ? "Accept team invitation" : intent.kind === "COUNTERPARTY" ? "Accept counterparty invitation" : "Accept Invitation"}
                </h3>
              </div>
              <button
                type="button"
                className="button ghost"
                onClick={handleDismissAcceptModal}
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            {!acceptedResult ? (
              <>
                <p className="muted" style={{ marginBottom: 16 }}>
                  You have received an invitation to collaborate with a counterparty on SyncAlly.
                  Accepting will grant your account access to trade documents and bilateral deals.
                </p>

                {intent.recipientEmail ? <p className="muted">Addressed to {intent.recipientEmail}</p> : null}
                {intent.kind === "INVALID" ? <p role="alert">Invalid invitation token</p> : null}
                {intent.kind !== "TEAM" ? <div className="field" style={{ marginBottom: 12 }}>
                  <label htmlFor="accept-org-name">{intent.kind === "COUNTERPARTY" ? "Your Company Legal Name" : "Your Company Legal Name (Optional)"}</label>
                  <input
                    id="accept-org-name"
                    type="text"
                    maxLength={200}
                    value={acceptOrgName}
                    onChange={(e) => setAcceptOrgName(e.target.value)}
                  />
                </div> : null}

                {intent.kind !== "TEAM" && acceptOrgName.trim() ? (
                  <div className="field" style={{ marginBottom: 12 }}>
                    <label htmlFor="accept-country-code">Country Code (2 letters)</label>
                    <input
                      id="accept-country-code"
                      type="text"
                      maxLength={2}
                      placeholder="US"
                      value={acceptCountryCode}
                      onChange={(e) => setAcceptCountryCode(e.target.value.toUpperCase())}
                    />
                  </div>
                ) : null}

                {acceptError && (
                  <p className="form-error" role="alert" style={{ marginBottom: 16 }}>
                    {acceptError}
                  </p>
                )}

                <div style={{ display: "flex", gap: 12 }}>
                  <button
                    type="button"
                    className="button"
                    disabled={accepting || intent.kind === "INVALID"}
                    onClick={handleAcceptInvite}
                  >
                    {accepting ? "Accepting…" : "Accept & Join"}
                  </button>
                  <button
                    type="button"
                    className="button ghost"
                    onClick={handleDismissAcceptModal}
                  >
                    Decline
                  </button>
                </div>
              </>
            ) : (
              <div style={{ marginTop: 12 }}>
                <p className="success" role="status" style={{ marginBottom: 20 }}>
                  ✓ Successfully joined {acceptedResult.organization_legal_name}! You are now an active member.
                </p>
                <div style={{ display: "flex", gap: 12 }}>
                  {acceptedResult.deal_id ? (
                    <button
                      type="button"
                      className="button"
                      onClick={() => navigateToDeal(acceptedResult.deal_id!)}
                    >
                      Go to Linked Deal
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="button secondary"
                    onClick={navigateToDeals}
                  >
                    Go to Workspace
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
