import { useCallback, useEffect, useState } from "react";

import { ApiError, listPlatformOrganizationMembers, listPlatformOrganizations, listPlatformUsers, setPlatformOrganizationOwner, updatePlatformOrganizationStatus, updatePlatformUserStatus } from "../api/client";
import type { PlatformOrganization, PlatformOrganizationMember, PlatformUser } from "../api/types";
import { getCurrentUserId } from "../api/tokenStore";

export default function PlatformOrganizationsPage() {
  const [organizations, setOrganizations] = useState<PlatformOrganization[]>([]);
  const [users, setUsers] = useState<PlatformUser[]>([]);
  const [view, setView] = useState<"organizations" | "users">("organizations");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const currentUserId = getCurrentUserId();
  const [ownerOrganization, setOwnerOrganization] = useState<PlatformOrganization | null>(null);
  const [ownerCandidates, setOwnerCandidates] = useState<PlatformOrganizationMember[]>([]);
  const [selectedOwnerId, setSelectedOwnerId] = useState("");
  const [ownerReason, setOwnerReason] = useState("");
  const [ownerError, setOwnerError] = useState<string | null>(null);
  const [savingOwner, setSavingOwner] = useState(false);

  const refresh = useCallback(async () => {
    try {
      if (view === "organizations") setOrganizations(await listPlatformOrganizations());
      else setUsers(await listPlatformUsers());
      setError(null);
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 403
        ? "This account does not have platform administrator access."
        : "Could not load organizations. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [view]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const result = view === "organizations" ? await listPlatformOrganizations() : await listPlatformUsers();
        if (!cancelled) {
          if (view === "organizations") setOrganizations(result as PlatformOrganization[]);
          else setUsers(result as PlatformUser[]);
          setError(null);
        }
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof ApiError && caught.status === 403
            ? "This account does not have platform administrator access."
            : "Could not load organizations. Please try again.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [view]);

  async function changeStatus(organization: PlatformOrganization) {
    const nextStatus = organization.status === "ACTIVE" ? "SUSPENDED" : "ACTIVE";
    if (nextStatus === "SUSPENDED" && !window.confirm(
      `Suspend ${organization.legal_name}? Its members will lose access to this organization until it is reactivated.`,
    )) return;
    setBusyId(organization.id);
    setError(null);
    try {
      const updated = await updatePlatformOrganizationStatus(organization.id, nextStatus);
      setOrganizations((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch {
      setError("The organization status could not be changed. Refresh and try again.");
    } finally {
      setBusyId(null);
    }
  }

  async function changeUserStatus(user: PlatformUser) {
    const nextStatus = user.status === "ACTIVE" ? "LOCKED" : "ACTIVE";
    const action = nextStatus === "LOCKED" ? "Lock" : "Unlock";
    const message = nextStatus === "LOCKED"
      ? `Lock ${user.email}? This immediately blocks access and revokes refresh sessions. The user must sign in again after unlock.`
      : `Unlock ${user.email}? This restores sign-in only; previous sessions stay revoked.`;
    if (!window.confirm(message)) return;
    setBusyId(user.id);
    setError(null);
    try {
      const updated = await updatePlatformUserStatus(user.id, nextStatus);
      setUsers((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 409
        ? `${action} was refused because this account needs a recovery or ownership transfer first.`
        : `Could not ${action.toLowerCase()} account. Refresh and try again.`);
    } finally {
      setBusyId(null);
    }
  }

  async function openOwnerDialog(organization: PlatformOrganization) {
    setOwnerOrganization(organization);
    setOwnerError(null);
    setOwnerReason("");
    try {
      const members = await listPlatformOrganizationMembers(organization.id);
      setOwnerCandidates(members);
      setSelectedOwnerId(members.find((member) => member.is_owner)?.user_id ?? members[0]?.user_id ?? "");
    } catch {
      setOwnerError("Could not load active organization members.");
    }
  }

  async function saveOwner() {
    if (!ownerOrganization || !selectedOwnerId || ownerReason.trim().length < 3) return;
    const nextOwner = ownerCandidates.find((member) => member.user_id === selectedOwnerId);
    if (!nextOwner) return;
    const current = ownerCandidates.find((member) => member.is_owner);
    const action = current ? "Transfer" : "Assign";
    if (!window.confirm(`${action} ownership of ${ownerOrganization.legal_name} to ${nextOwner.email}? The previous owner will become an organization administrator.`)) return;
    setSavingOwner(true);
    setOwnerError(null);
    try {
      const result = await setPlatformOrganizationOwner(ownerOrganization.id, selectedOwnerId, ownerReason.trim());
      setOrganizations((items) => items.map((item) => item.id === result.organization_id ? { ...item, owner_user_id: result.owner_user_id } : item));
      setOwnerOrganization(null);
    } catch (caught) {
      setOwnerError(caught instanceof ApiError ? caught.message : "Could not update organization owner.");
    } finally {
      setSavingOwner(false);
    }
  }

  return (
    <section className="card" aria-labelledby="platform-organizations-heading">
      <div className="page-header">
        <div>
          <p className="eyebrow">PLATFORM ADMINISTRATION</p>
          <h1 id="platform-organizations-heading">Organizations</h1>
          <p>Manage organization access. Private deals, agreements, and payment records remain organization-scoped.</p>
        </div>
        <button type="button" className="button secondary" onClick={() => void refresh()} disabled={loading}>
          Refresh
        </button>
      </div>

      <div role="tablist" aria-label="Platform administration">
        <button type="button" role="tab" aria-selected={view === "organizations"} onClick={() => { setLoading(true); setView("organizations"); }}>Organizations</button>
        <button type="button" role="tab" aria-selected={view === "users"} onClick={() => { setLoading(true); setView("users"); }}>Users</button>
      </div>

      {error ? <p role="alert" className="form-error">{error}</p> : null}
      {loading ? <p role="status">Loading {view}…</p> : null}
      {view === "organizations" && !loading && !error && organizations.length === 0 ? <p>No organizations have been created yet.</p> : null}
      {view === "organizations" && !loading && organizations.length > 0 ? (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", textAlign: "left", borderCollapse: "collapse" }}>
            <thead>
              <tr><th scope="col">Organization</th><th scope="col">Country</th><th scope="col">Owner</th><th scope="col">Status</th><th scope="col">Created</th><th scope="col">Action</th></tr>
            </thead>
            <tbody>
              {organizations.map((organization) => (
                <tr key={organization.id}>
                  <th scope="row">{organization.legal_name}</th>
                  <td>{organization.country_code}</td>
                  <td>{organization.owner_user_id || "Owner recovery needed"}</td>
                  <td>{organization.status}</td>
                  <td>{organization.created_at ? new Date(organization.created_at).toLocaleDateString() : "—"}</td>
                  <td>
                    {organization.status === "ACTIVE" || organization.status === "SUSPENDED" ? (
                      <button
                        type="button"
                        className="button ghost"
                        disabled={busyId === organization.id}
                        onClick={() => void changeStatus(organization)}
                      >
                        {busyId === organization.id
                          ? "Saving…"
                          : organization.status === "ACTIVE" ? "Suspend" : "Reactivate"}
                      </button>
                    ) : "—"}
                    <button type="button" className="button secondary" onClick={() => void openOwnerDialog(organization)} disabled={organization.status !== "ACTIVE"}>
                      {organization.owner_user_id ? "Manage owner" : "Recover owner"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {ownerOrganization ? <div className="manual-fact-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="platform-owner-title">
        <div className="manual-fact-modal">
          <div className="panel-head"><h2 id="platform-owner-title">Organization owner</h2><button type="button" className="button ghost" onClick={() => setOwnerOrganization(null)} aria-label="Close">×</button></div>
          <p>Choose an active organization member. Owner access includes all organization actions and deals.</p>
          <div className="field"><label htmlFor="platform-owner-select">New owner</label><select id="platform-owner-select" value={selectedOwnerId} disabled={savingOwner} onChange={(event) => setSelectedOwnerId(event.target.value)}>
            {ownerCandidates.map((member) => <option key={member.user_id} value={member.user_id}>{member.display_name} · {member.email}{member.is_owner ? " · current owner" : ""}</option>)}
          </select></div>
          <div className="field"><label htmlFor="platform-owner-reason">Reason</label><input id="platform-owner-reason" value={ownerReason} maxLength={500} disabled={savingOwner} onChange={(event) => setOwnerReason(event.target.value)} /></div>
          {ownerError ? <p role="alert" className="form-error">{ownerError}</p> : null}
          <button type="button" className="button" disabled={savingOwner || !selectedOwnerId || ownerReason.trim().length < 3} onClick={() => void saveOwner()}>{savingOwner ? "Saving…" : "Save owner"}</button>
        </div>
      </div> : null}
      {view === "users" && !loading && !error && users.length === 0 ? <p>No accounts have been created yet.</p> : null}
      {view === "users" && !loading && users.length > 0 ? (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", textAlign: "left", borderCollapse: "collapse" }}>
            <thead><tr><th scope="col">User</th><th scope="col">Account state</th><th scope="col">System role</th><th scope="col">Created</th><th scope="col">Action</th></tr></thead>
            <tbody>{users.map((user) => <tr key={user.id}>
              <th scope="row">{user.display_name}<br />{user.email}</th>
              <td>{user.status}</td><td>{user.system_role}</td>
              <td>{user.created_at ? new Date(user.created_at).toLocaleDateString() : "—"}</td>
              <td>{user.status === "ACTIVE" || user.status === "LOCKED" ? <button type="button" className="button ghost" disabled={busyId === user.id || user.id === currentUserId} title={user.id === currentUserId ? "You cannot lock or unlock your own account" : undefined} onClick={() => void changeUserStatus(user)}>{busyId === user.id ? "Saving…" : user.status === "ACTIVE" ? "Lock account" : "Unlock account"}</button> : "—"}</td>
            </tr>)}</tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
