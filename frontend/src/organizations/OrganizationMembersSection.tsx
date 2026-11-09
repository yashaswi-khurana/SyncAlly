import { useEffect, useState } from "react";
import type { Dispatch, FormEvent, SetStateAction } from "react";

import {
  ApiError,
  listAssignableOrganizationDeals,
  listOrganizationMembers,
  revokeOrganizationMember,
  updateMemberPermissions,
} from "../api/client";
import { getCurrentUserId } from "../api/tokenStore";
import type {
  Organization,
  OrganizationMember,
  AssignableDeal,
} from "../api/types";
import ApprovalRoutingSection from "./ApprovalRoutingSection";

interface Props {
  organization: Organization;
}

const BUNDLES = ["DEAL_MANAGER", "DEAL_MEMBER", "APPROVER", "FINANCE", "FULFILLMENT"];

function describeError(caught: unknown): string {
  if (caught instanceof ApiError) {
    if (caught.status === 401) {
      return "Your session has expired. Sign in again.";
    }
    if (caught.status === 403) {
      return caught.message || "Permission denied or self-modification blocked.";
    }
    if (caught.status === 409) {
      return (
        caught.message ||
        "Permissions conflict or cannot modify the last remaining admin. Please refresh."
      );
    }
    return caught.message;
  }
  if (caught instanceof Error && caught.message) {
    return caught.message;
  }
  return "Something went wrong. Please try again.";
}

export default function OrganizationMembersSection({ organization }: Props) {
  const isAdmin = organization.role === "ADMIN";
  const currentUserId = getCurrentUserId();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [reloadCount, setReloadCount] = useState(0);

  // Edit permissions state
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [draftBundles, setDraftBundles] = useState<Set<string>>(new Set());
  const [draftPermissions, setDraftPermissions] = useState<Set<string>>(new Set());
  const [draftDealIds, setDraftDealIds] = useState<Set<string>>(new Set());
  const [availableDeals, setAvailableDeals] = useState<AssignableDeal[]>([]);
  const [draftExpectedVersion, setDraftExpectedVersion] = useState<number>(1);
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [revokingUserId, setRevokingUserId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await listOrganizationMembers(organization.id);
        if (!cancelled) {
          setMembers(data);
          setError(null);
          setLoading(false);
        }
      } catch (caught) {
        if (!cancelled) {
          setError(describeError(caught));
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [organization.id, reloadCount]);

  function refreshMembers() {
    setLoading(true);
    setEditingUserId(null);
    setActionError(null);
    setReloadCount((c) => c + 1);
  }

  const activeAdminsCount = members.filter(
    (m) => (m.role_bundles || []).includes("ORG_ADMIN") || m.is_owner
  ).length;

  function handleStartEdit(member: OrganizationMember) {
    setEditingUserId(member.user_id);
    setDraftBundles(new Set(member.role_bundles || []));
    setDraftPermissions(new Set(member.permissions || []));
    setDraftDealIds(new Set(member.deal_ids || []));
    void listAssignableOrganizationDeals(organization.id).then(setAvailableDeals).catch(() => setAvailableDeals([]));
    setDraftExpectedVersion(member.version);
    setActionError(null);
    setActionNotice(null);
  }

  function handleCancelEdit() {
    setEditingUserId(null);
    setActionError(null);
  }

  function handleToggle(setter: Dispatch<SetStateAction<Set<string>>>, key: string) {
    setter((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  async function handleSavePermissions(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingUserId) return;

    if (editingUserId === currentUserId) {
      setActionError("Cannot modify your own membership role or capabilities (Self-escalation guard).");
      return;
    }

    const targetMember = members.find((m) => m.user_id === editingUserId);
    if (!targetMember) return;

    setSaving(true);
    setActionError(null);
    setActionNotice(null);
    try {
      const updated = await updateMemberPermissions(organization.id, editingUserId, {
        expected_version: draftExpectedVersion,
        role_bundles: Array.from(draftBundles),
        permissions: Array.from(draftPermissions),
        deal_ids: Array.from(draftDealIds),
      });
      setMembers((prev) =>
        prev.map((m) => (m.user_id === updated.user_id ? updated : m))
      );
      setActionNotice(`Updated permissions for ${updated.email}.`);
      setEditingUserId(null);
    } catch (caught) {
      setActionError(describeError(caught));
    } finally {
      setSaving(false);
    }
  }

  async function handleRevoke(member: OrganizationMember) {
    if (member.user_id === currentUserId) {
      setActionError("Cannot revoke your own membership.");
      return;
    }
    if (member.role === "ADMIN" && activeAdminsCount <= 1) {
      setActionError("Cannot revoke the last remaining admin of the organization.");
      return;
    }
    if (!window.confirm(`Are you sure you want to revoke membership for ${member.email}?`)) {
      return;
    }

    setRevokingUserId(member.user_id);
    setActionError(null);
    setActionNotice(null);
    try {
      await revokeOrganizationMember(organization.id, member.user_id);
      setMembers((prev) => prev.filter((m) => m.user_id !== member.user_id));
      setActionNotice(`Revoked membership for ${member.email}.`);
    } catch (caught) {
      setActionError(describeError(caught));
    } finally {
      setRevokingUserId(null);
    }
  }

  if (loading) {
    return (
      <div className="members-section" aria-live="polite" style={{ marginTop: 24, borderTop: "1px solid var(--border)", paddingTop: 16 }}>
        <p role="status" className="muted">Loading members…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="members-section" role="alert" style={{ marginTop: 24, borderTop: "1px solid var(--border)", paddingTop: 16 }}>
        <p className="form-error">{error}</p>
        <button type="button" className="button secondary" onClick={refreshMembers}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div
      className="members-section"
      data-testid="members-section"
      style={{ marginTop: 24, borderTop: "1px solid var(--border)", paddingTop: 16 }}
    >
      <div
        className="panel-head"
        style={{ marginBottom: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}
      >
        <div>
          <span className="eyebrow">Organization Access</span>
          <h4 style={{ margin: "4px 0" }}>Team Members &amp; Permissions</h4>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span className="badge">{members.length} {members.length === 1 ? "Member" : "Members"}</span>
          <button type="button" className="button secondary" onClick={refreshMembers} title="Refresh members list">
            Refresh
          </button>
        </div>
      </div>

      {actionError && (
        <p className="form-error" role="alert" style={{ marginBottom: 12 }}>
          {actionError}
        </p>
      )}

      {actionNotice && (
        <p className="success" role="status" style={{ marginBottom: 12 }}>
          {actionNotice}
        </p>
      )}

      {members.length === 0 ? (
        <p className="muted">No active members found.</p>
      ) : (
        <ul className="member-list" style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {members.map((member) => {
            const isSelf = member.user_id === currentUserId;
            const isEditing = editingUserId === member.user_id;
            const isLastAdmin = ((member.role_bundles || []).includes("ORG_ADMIN") || member.is_owner) && activeAdminsCount <= 1;

            return (
              <li
                key={member.user_id}
                data-testid={`member-row-${member.user_id}`}
                style={{
                  padding: "12px 16px",
                  borderRadius: 6,
                  border: "1px solid var(--line)",
                  marginBottom: 8,
                  background: isEditing ? "var(--bg-card-hover, rgba(255,255,255,0.03))" : "transparent",
                }}
              >
                {!isEditing ? (
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8 }}>
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                        <strong>{member.display_name || member.email}</strong>
                        {member.display_name && (
                          <span className="muted" style={{ fontSize: "0.85rem" }}>({member.email})</span>
                        )}
                        <span
                          className={`badge ${(member.is_owner || (member.role_bundles || []).includes("ORG_ADMIN")) ? "badge--status-confirmed" : ""}`}
                          style={{ fontSize: "0.75rem", fontWeight: 600 }}
                        >
                          {member.is_owner ? "ORG OWNER · FULL ACCESS" : (member.role_bundles || []).join(" + ") || "No access"}
                        </span>
                        {isSelf && (
                          <span
                            className="badge"
                            style={{ fontSize: "0.75rem", background: "rgba(56, 189, 248, 0.15)", color: "#38bdf8" }}
                          >
                            You
                          </span>
                        )}
                        <span className="mono muted" style={{ fontSize: "0.75rem" }}>
                          v{member.version}
                        </span>
                      </div>

                      <div style={{ marginTop: 8, display: "flex", gap: 6, flexWrap: "wrap" }}>
                        {[...(member.permissions || []), ...(member.deal_ids?.length ? [`${member.deal_ids.length} assigned deals`] : [])].map((cap) => (
                          <span
                            key={cap}
                            style={{
                              display: "inline-block",
                              padding: "2px 8px",
                              borderRadius: 4,
                              fontSize: "0.75rem",
                              background: "rgba(255, 255, 255, 0.08)",
                              border: "1px solid var(--line)",
                            }}
                          >
                            {cap}
                          </span>
                        ))}
                      </div>
                    </div>

                    {isAdmin && (
                      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        {isSelf || member.is_owner ? (
                          <span className="hint" style={{ fontSize: "0.75rem" }}>
                            {member.is_owner ? "Ownership must be transferred first" : "Cannot self-modify"}
                          </span>
                        ) : (
                          <>
                            <button
                              type="button"
                              className="button secondary"
                              style={{ fontSize: "0.8rem", padding: "4px 10px" }}
                              onClick={() => handleStartEdit(member)}
                              disabled={saving || revokingUserId === member.user_id}
                            >
                              Edit permissions
                            </button>
                            <button
                              type="button"
                              className="button danger"
                              style={{ fontSize: "0.8rem", padding: "4px 10px" }}
                              onClick={() => void handleRevoke(member)}
                              disabled={member.is_owner || isLastAdmin || saving || revokingUserId === member.user_id}
                              title={member.is_owner ? "Transfer ownership before revoking" : isLastAdmin ? "Cannot revoke the last admin" : "Revoke membership"}
                            >
                              {revokingUserId === member.user_id ? "Revoking…" : "Revoke"}
                            </button>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <form onSubmit={handleSavePermissions} noValidate style={{ marginTop: 4 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                      <div>
                        <strong>Editing permissions for {member.email}</strong>
                        <span className="mono muted" style={{ marginLeft: 8, fontSize: "0.8rem" }}>
                          (expected v{draftExpectedVersion})
                        </span>
                      </div>
                      <div style={{ display: "flex", gap: 8 }}>
                        <button
                          type="submit"
                          className="button"
                          style={{ fontSize: "0.8rem", padding: "4px 12px" }}
                          disabled={saving}
                        >
                          {saving ? "Saving…" : "Save changes"}
                        </button>
                        <button
                          type="button"
                          className="button ghost"
                          style={{ fontSize: "0.8rem", padding: "4px 12px" }}
                          onClick={handleCancelEdit}
                          disabled={saving}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>

                    <fieldset className="field" style={{ marginBottom: 12 }}>
                      <legend>Access bundles</legend>
                      <p className="muted">Bundles can be combined. Each bundle grants the actions listed in its description.</p>
                      {BUNDLES.map((bundle) => <label key={bundle} style={{ display: "block", margin: "6px 0" }}>
                        <input type="checkbox" checked={draftBundles.has(bundle)} disabled={saving}
                          onChange={() => handleToggle(setDraftBundles, bundle)} /> {bundle.replaceAll("_", " ")}
                      </label>)}
                      {organization.is_owner ? <label style={{ display: "block", margin: "6px 0" }}>
                        <input type="checkbox" checked={draftBundles.has("ORG_ADMIN")} disabled={saving}
                          onChange={() => handleToggle(setDraftBundles, "ORG_ADMIN")} /> Organization administrator
                      </label> : null}
                    </fieldset>

                    <fieldset className="field" style={{ marginBottom: 12 }}>
                      <legend>Additional permissions</legend>
                      {["deal.create", "deal.read_all", "deal.edit_assigned", "agreement.approve", "payments.read", "payments.authorize", "fulfillment.read", "fulfillment.record", "marketplace.manage", "approval_routing.manage"].map((permission) => {
                        const ownerOnly = permission === "deal.read_all";
                        return <label key={permission} style={{ display: "block", margin: "6px 0" }}>
                          <input type="checkbox" checked={draftPermissions.has(permission)} disabled={saving || (ownerOnly && !organization.is_owner)}
                            onChange={() => handleToggle(setDraftPermissions, permission)} /> {permission}{ownerOnly ? " (owner delegated)" : ""}
                        </label>;
                      })}
                    </fieldset>

                    <fieldset className="field">
                      <legend>Deal access</legend>
                      {availableDeals.length === 0 ? <p className="muted">No assignable deals are available.</p> : availableDeals.map((deal) => <label key={deal.id} style={{ display: "block", margin: "6px 0" }}>
                        <input type="checkbox" checked={draftDealIds.has(deal.id)} disabled={saving}
                          onChange={() => handleToggle(setDraftDealIds, deal.id)} /> {deal.display_name} ({deal.status})
                      </label>)}
                    </fieldset>
                  </form>
                )}
              </li>
            );
          })}
        </ul>
      )}

      <ApprovalRoutingSection organization={organization} members={members} />
    </div>
  );
}
