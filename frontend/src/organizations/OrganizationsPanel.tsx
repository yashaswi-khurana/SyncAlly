import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { addOrganizationMember, ApiError, listOrganizations } from "../api/client";
import type { Organization } from "../api/types";
import OrganizationMembersSection from "./OrganizationMembersSection";
import OrganizationProfileSection from "./OrganizationProfileSection";

type OrganizationsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; organizations: Organization[] };

type OrganizationTab = "overview" | "team";

function describeError(caught: unknown): string {
  if (caught instanceof ApiError) {
    if (caught.status === 401) return "Your session has expired. Sign in again.";
    return caught.message;
  }
  return "Something went wrong. Please try again.";
}

export default function OrganizationsPanel({
  onInviteTeamMember,
}: {
  onInviteTeamMember?: (organizationId: string) => void;
}) {
  const [state, setState] = useState<OrganizationsState>({ status: "loading" });
  const [reloadCount, setReloadCount] = useState(0);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [activeTab, setActiveTab] = useState<OrganizationTab>("overview");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteNotice, setInviteNotice] = useState<string | null>(null);
  const [inviting, setInviting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const organizations = await listOrganizations();
        if (!cancelled) {
          setState({ status: "ready", organizations });
          setSelectedOrgId((current) =>
            organizations.some((organization) => organization.id === current)
              ? current
              : organizations[0]?.id ?? "",
          );
        }
      } catch (caught) {
        if (!cancelled) setState({ status: "error", message: describeError(caught) });
      }
    })();
    return () => { cancelled = true; };
  }, [reloadCount]);

  const organizations = state.status === "ready" ? state.organizations : [];
  const selectedOrganization = organizations.find((organization) => organization.id === selectedOrgId);

  function retryOrganizations() {
    setState({ status: "loading" });
    setReloadCount((count) => count + 1);
  }

  async function copyOrganizationId(organizationId: string) {
    try {
      await navigator.clipboard.writeText(organizationId);
      setCopiedId(organizationId);
    } catch {
      setCopiedId(null);
    }
  }

  async function handleAddExistingMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const email = inviteEmail.trim();
    setInviteNotice(null);
    if (!selectedOrganization) {
      setInviteError("Choose an organization first.");
      return;
    }
    if (!email) {
      setInviteError("Enter the email address for an existing account.");
      return;
    }
    setInviteError(null);
    setInviting(true);
    try {
      const member = await addOrganizationMember(selectedOrganization.id, email);
      setInviteNotice(member.email_sent
        ? `Added ${member.email} as ${member.role}. A sign-in email was sent.`
        : `Added ${member.email} as ${member.role}.`);
      setInviteError(member.email_sent ? null : member.email_error || "The account was added, but its notification email could not be sent.");
      setInviteEmail("");
    } catch (caught) {
      setInviteError(describeError(caught));
    } finally {
      setInviting(false);
    }
  }

  if (state.status === "loading") {
    return (
      <section className="card">
        <p role="status">Loading your organizations…</p>
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
      <section className="card org-console" role="alert">
        <div className="org-empty-state">
          <span className="eyebrow">Organization workspace</span>
          <h2>We could not load your organizations</h2>
          <p className="muted">{state.message}</p>
          <button type="button" className="button" onClick={retryOrganizations}>Try again</button>
        </div>
      </section>
    );
  }

  return (
    <section className="card org-console" aria-labelledby="organizations-heading">
      <header className="org-console__header">
        <div>
          <span className="eyebrow">Company workspace · {organizations.length} {organizations.length === 1 ? "organization" : "organizations"}</span>
          <h2 id="organizations-heading">Manage organizations</h2>
          <p className="muted">Company details, team access, and invitations live together here.</p>
        </div>
      </header>

      {organizations.length === 0 ? (
        <div className="org-empty-state">
          <span className="eyebrow">Organization access</span>
          <h3>You are not an active member of any organization</h3>
          <p className="muted">Ask an organization administrator for an invitation. New organizations are set up during owner account onboarding.</p>
        </div>
      ) : (
        <div className="org-console__layout">
          <aside className="org-switcher" aria-label="Your organizations">
            <div className="org-switcher__heading">
              <span className="eyebrow">Your organizations</span>
              <span className="org-count">{organizations.length}</span>
            </div>
            <div className="org-switcher__list">
              {organizations.map((organization) => (
                <button
                  type="button"
                  key={organization.id}
                  className={`org-switcher__item${organization.id === selectedOrgId ? " is-selected" : ""}`}
                  onClick={() => { setSelectedOrgId(organization.id); setActiveTab("overview"); }}
                  aria-current={organization.id === selectedOrgId ? "true" : undefined}
                >
                  <span className="org-switcher__avatar" aria-hidden="true">{organization.legal_name.trim().charAt(0).toUpperCase()}</span>
                  <span className="org-switcher__copy">
                    <strong>{organization.legal_name} ({organization.country_code})</strong>
                    <small>{organization.role === "ADMIN" ? "Administrator" : "Member"}</small>
                  </span>
                  <span className="org-switcher__arrow" aria-hidden="true">›</span>
                </button>
              ))}
            </div>
          </aside>

          {selectedOrganization ? (
            <div className="org-detail">
              <header className="org-detail__header">
                <div className="org-detail__title">
                  <span className="org-detail__avatar" aria-hidden="true">{selectedOrganization.legal_name.trim().charAt(0).toUpperCase()}</span>
                  <div>
                    <span className="eyebrow">Organization profile</span>
                    <h3>{selectedOrganization.legal_name}</h3>
                    <p>{selectedOrganization.country_code} · {selectedOrganization.role === "ADMIN" ? "Administrator access" : "Member access"}</p>
                  </div>
                </div>
                <div className="org-detail__reference">
                  <span>Organization ID</span>
                  <code title={selectedOrganization.id}>{selectedOrganization.id}</code>
                  <button type="button" className="button secondary" onClick={() => void copyOrganizationId(selectedOrganization.id)}>
                    {copiedId === selectedOrganization.id ? "Copied" : "Copy ID"}
                  </button>
                </div>
              </header>

              <div className="org-tabs" role="tablist" aria-label="Organization sections">
                <button type="button" id="org-overview-tab" role="tab" aria-selected={activeTab === "overview"} aria-controls="org-overview-panel" onClick={() => setActiveTab("overview")}>
                  Overview
                </button>
                <button type="button" id="org-team-tab" role="tab" aria-selected={activeTab === "team"} aria-controls="org-team-panel" onClick={() => setActiveTab("team")}>
                  Team &amp; access
                </button>
              </div>

              {activeTab === "overview" ? (
                <section className="org-tab-panel" id="org-overview-panel" role="tabpanel" aria-labelledby="org-overview-tab">
                  <div className="org-section-heading">
                    <div>
                      <span className="eyebrow">Company details</span>
                      <h4>Business profile</h4>
                      <p className="muted">Help trading partners understand what your organization offers.</p>
                    </div>
                  </div>
                  <OrganizationProfileSection organization={selectedOrganization} />
                </section>
              ) : (
                <section className="org-tab-panel" id="org-team-panel" role="tabpanel" aria-labelledby="org-team-tab">
                  <div className="org-team-actions">
                    <div>
                      <span className="eyebrow">People &amp; permissions</span>
                      <h4>Team access</h4>
                      <p className="muted">Invite a new teammate with a sign-up link, or add an account that already exists.</p>
                    </div>
                    {selectedOrganization.role === "ADMIN" && onInviteTeamMember ? (
                      <button type="button" className="button" onClick={() => onInviteTeamMember(selectedOrganization.id)}>Invite a new teammate</button>
                    ) : null}
                  </div>

                  {selectedOrganization.role === "ADMIN" ? (
                    <form className="org-add-member" onSubmit={handleAddExistingMember} noValidate>
                      <div className="org-add-member__intro">
                        <span className="org-add-member__icon" aria-hidden="true">＋</span>
                        <div>
                          <h5>Add an existing account</h5>
                          <p className="muted">Use this for someone who already has a SyncAlly account.</p>
                        </div>
                      </div>
                      <div className="org-add-member__controls">
                        <div className="field">
                          <label htmlFor="invite-email">Account email</label>
                          <input
                            id="invite-email"
                            name="invite-email"
                            type="email"
                            placeholder="colleague@example.com"
                            value={inviteEmail}
                            onChange={(event) => setInviteEmail(event.target.value)}
                            disabled={inviting}
                          />
                        </div>
                        <button type="submit" className="button secondary" disabled={inviting}>
                          {inviting ? "Adding…" : "Add account"}
                        </button>
                      </div>
                      {inviteError ? <p className="form-error" role="alert">{inviteError}</p> : null}
                      {inviteNotice ? <p className="success" role="status">{inviteNotice}</p> : null}
                    </form>
                  ) : null}
                  <OrganizationMembersSection organization={selectedOrganization} />
                </section>
              )}
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}
