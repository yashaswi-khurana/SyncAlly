import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { addOrganizationMember, ApiError, createOrganization, listOrganizations } from "../api/client";
import type { Organization } from "../api/types";
import Reveal from "../ui/Reveal";

type OrganizationsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; organizations: Organization[] };

const COUNTRY_PATTERN = /^[A-Z]{2}$/;

function describeError(caught: unknown): string {
  if (caught instanceof ApiError) {
    if (caught.status === 401) {
      return "Your session has expired. Sign in again.";
    }
    return caught.message;
  }
  return "Something went wrong. Please try again.";
}

export default function OrganizationsPanel() {
  const [state, setState] = useState<OrganizationsState>({ status: "loading" });
  const [reloadCount, setReloadCount] = useState(0);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const [legalName, setLegalName] = useState("");
  const [countryCode, setCountryCode] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [createNotice, setCreateNotice] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const [inviteOrgId, setInviteOrgId] = useState("");
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
          setInviteOrgId((current) => current || organizations[0]?.id || "");
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

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = legalName.trim();
    const country = countryCode.trim().toUpperCase();
    setCreateNotice(null);
    if (name === "") {
      setCreateError("Enter the legal name of the organization.");
      return;
    }
    if (!COUNTRY_PATTERN.test(country)) {
      setCreateError("Enter a two-letter country code, for example US.");
      return;
    }
    setCreateError(null);
    setCreating(true);
    try {
      const created = await createOrganization({ legal_name: name, country_code: country });
      setCreateNotice(`Created ${created.legal_name} (${created.country_code}).`);
      setLegalName("");
      setCountryCode("");
      setReloadCount((count) => count + 1);
    } catch (caught) {
      setCreateError(describeError(caught));
    } finally {
      setCreating(false);
    }
  }

  async function handleInvite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const email = inviteEmail.trim();
    setInviteNotice(null);
    if (inviteOrgId === "") {
      setInviteError("Choose an organization to invite the member to.");
      return;
    }
    if (email === "") {
      setInviteError("Enter the email of an existing account.");
      return;
    }
    setInviteError(null);
    setInviting(true);
    try {
      const member = await addOrganizationMember(inviteOrgId, email);
      setInviteNotice(`Added ${member.email} as ${member.role}.`);
      setInviteEmail("");
    } catch (caught) {
      setInviteError(describeError(caught));
    } finally {
      setInviting(false);
    }
  }

  if (state.status === "loading") {
    return (
      <section className="card" aria-live="polite">
        <p role="status">Loading your organizations…</p>
      </section>
    );
  }

  if (state.status === "error") {
    return (
      <section className="card" role="alert">
        <h2>We could not load your organizations</h2>
        <p className="muted" style={{ marginTop: 10 }}>
          {state.message}
        </p>
        <div className="actions">
          <button type="button" className="button" onClick={retryOrganizations}>
            Try again
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="card" aria-labelledby="organizations-heading">
      <div className="panel-head">
        <span className="eyebrow">Your organizations</span>
        <h2 id="organizations-heading">Organization IDs</h2>
      </div>
      <p className="muted">
        Share an organization ID so the other party can name your organization as the buyer or
        seller of a deal.
      </p>
      {state.organizations.length === 0 ? (
        <p className="empty-state">
          Your account is not an active member of any organization yet.
        </p>
      ) : (
        <ul className="org-list">
          {state.organizations.map((organization) => (
            <li key={organization.id}>
              <div className="deal-meta">
                <span>
                  {organization.legal_name} ({organization.country_code})
                </span>
                <span className="mono">{organization.id}</span>
              </div>
              <button
                type="button"
                className="button secondary"
                onClick={() => void copyOrganizationId(organization.id)}
              >
                {copiedId === organization.id ? "Copied" : "Copy ID"}
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="grid-2" style={{ marginTop: 34 }}>
        <Reveal>
          <form className="form" onSubmit={handleCreate} noValidate>
            <div className="panel-head" style={{ marginBottom: 0 }}>
              <span className="eyebrow">New organization</span>
              <h3 className="display" style={{ fontSize: "1.25rem" }}>
                Create an organization
              </h3>
            </div>
            <div className="field">
              <label htmlFor="organization-legal-name">Legal name</label>
              <input
                id="organization-legal-name"
                name="organization-legal-name"
                type="text"
                placeholder="Northwind Trading Ltd."
                value={legalName}
                onChange={(event) => setLegalName(event.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="organization-country">Country code</label>
              <input
                id="organization-country"
                name="organization-country"
                type="text"
                placeholder="US"
                maxLength={2}
                value={countryCode}
                onChange={(event) => setCountryCode(event.target.value.toUpperCase())}
              />
              <p className="hint">Two-letter ISO country code.</p>
            </div>
            {createError ? (
              <p className="form-error" role="alert">
                {createError}
              </p>
            ) : null}
            {createNotice ? (
              <p className="success" role="status">
                {createNotice}
              </p>
            ) : null}
            <button type="submit" className="button" disabled={creating}>
              {creating ? "Creating…" : "Create organization"}
            </button>
          </form>
        </Reveal>

        <Reveal delay={80}>
          <form className="form" onSubmit={handleInvite} noValidate>
            <div className="panel-head" style={{ marginBottom: 0 }}>
              <span className="eyebrow">Members</span>
              <h3 className="display" style={{ fontSize: "1.25rem" }}>
                Invite a member
              </h3>
            </div>
            <div className="field">
              <label htmlFor="invite-organization">Organization</label>
              <select
                id="invite-organization"
                name="invite-organization"
                value={inviteOrgId}
                onChange={(event) => setInviteOrgId(event.target.value)}
                disabled={state.organizations.length === 0}
              >
                {state.organizations.map((organization) => (
                  <option key={organization.id} value={organization.id}>
                    {organization.legal_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="invite-email">Member email</label>
              <input
                id="invite-email"
                name="invite-email"
                type="email"
                placeholder="colleague@example.com"
                value={inviteEmail}
                onChange={(event) => setInviteEmail(event.target.value)}
              />
              <p className="hint">The account must already exist. You must be an admin.</p>
            </div>
            {inviteError ? (
              <p className="form-error" role="alert">
                {inviteError}
              </p>
            ) : null}
            {inviteNotice ? (
              <p className="success" role="status">
                {inviteNotice}
              </p>
            ) : null}
            <button
              type="submit"
              className="button"
              disabled={inviting || state.organizations.length === 0}
            >
              {inviting ? "Adding…" : "Add member"}
            </button>
          </form>
        </Reveal>
      </div>
    </section>
  );
}
