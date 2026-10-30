import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, apiRequest, listOrganizations } from "../api/client";
import type { Organization } from "../api/types";
import { navigateToDeal, navigateToDeals, navigateToOrganizations } from "../router";
import OrganizationsPanel from "./OrganizationsPanel";
import Reveal from "../ui/Reveal";

interface CreateInvitationResponse {
  token: string;
  invite_url: string;
  organization_id: string;
  organization_legal_name: string;
  deal_id: string | null;
  role: string;
  expires_at: string;
}

interface AcceptInvitationResponse {
  status: string;
  organization_id: string;
  organization_legal_name: string;
  user_id: string;
  role: string;
  deal_id: string | null;
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

export default function OrganizationsSettingsPage() {
  // Invite Generator Modal State
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [adminOrganizations, setAdminOrganizations] = useState<Organization[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [dealIdInput, setDealIdInput] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [generatedInvite, setGeneratedInvite] = useState<CreateInvitationResponse | null>(null);
  const [copied, setCopied] = useState(false);

  // Accept Invitation Flow State
  const [inviteToken, setInviteToken] = useState<string | null>(null);
  const [accepting, setAccepting] = useState(false);
  const [acceptError, setAcceptError] = useState<string | null>(null);
  const [acceptedResult, setAcceptedResult] = useState<AcceptInvitationResponse | null>(null);

  // Extract invite token from hash on mount and hashchange
  useEffect(() => {
    function checkHashForInvite() {
      const hash = window.location.hash;
      const rawPath = hash.startsWith("#") ? hash.slice(1) : hash;
      const [, queryString] = rawPath.split("?");
      if (queryString) {
        const params = new URLSearchParams(queryString);
        const token = params.get("token");
        if (token) {
          setInviteToken(token);
          return;
        }
      }
      setInviteToken(null);
    }

    checkHashForInvite();
    window.addEventListener("hashchange", checkHashForInvite);
    return () => window.removeEventListener("hashchange", checkHashForInvite);
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

    setGenerating(true);
    setGenerateError(null);
    try {
      const res = await apiRequest<CreateInvitationResponse>(
        `/organizations/${encodeURIComponent(targetOrgId)}/invitations`,
        {
          method: "POST",
          body: JSON.stringify({
            deal_id: dealIdInput.trim() || null,
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
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(generatedInvite.invite_url);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      setCopied(false);
    }
  }

  async function handleAcceptInvite() {
    if (!inviteToken) return;
    setAccepting(true);
    setAcceptError(null);
    try {
      const res = await apiRequest<AcceptInvitationResponse>("/invitations/accept", {
        method: "POST",
        body: JSON.stringify({ token: inviteToken }),
      });
      setAcceptedResult(res);
    } catch (caught) {
      setAcceptError(describeError(caught));
    } finally {
      setAccepting(false);
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
            Invite Counterparty
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

            <p className="muted" style={{ fontSize: "0.9rem", marginBottom: 16 }}>
              Generate a shareable link that allows a counterparty to sign up, join your organization,
              and immediately link into bilateral deals.
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
                <label htmlFor="invite-modal-deal">Link to Deal ID (Optional)</label>
                <input
                  id="invite-modal-deal"
                  type="text"
                  placeholder="e.g. 12345678-1234-1234-1234-123456789abc"
                  value={dealIdInput}
                  onChange={(e) => setDealIdInput(e.target.value)}
                  disabled={generating}
                />
                <p className="hint">If provided, the counterparty is immediately associated with this deal.</p>
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
                  Accept Invitation
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

                {acceptError && (
                  <p className="form-error" role="alert" style={{ marginBottom: 16 }}>
                    {acceptError}
                  </p>
                )}

                <div style={{ display: "flex", gap: 12 }}>
                  <button
                    type="button"
                    className="button"
                    disabled={accepting}
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
