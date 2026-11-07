import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import {
  ApiError,
  listOrganizationMembers,
  revokeOrganizationMember,
  updateMemberPermissions,
} from "../api/client";
import { getAccessToken } from "../api/tokenStore";
import type {
  Organization,
  OrganizationCapability,
  OrganizationMember,
} from "../api/types";
import ApprovalRoutingSection from "./ApprovalRoutingSection";

interface Props {
  organization: Organization;
}

const ALL_CAPABILITIES: { key: OrganizationCapability; label: string; description: string }[] = [
  {
    key: "ADMINISTRATION",
    label: "Administration",
    description: "Manage organization profile, settings, and team members",
  },
  {
    key: "DRAFTING",
    label: "Drafting",
    description: "Create and edit deal proposals and agreement drafts",
  },
  {
    key: "AGREEMENT_APPROVAL",
    label: "Agreement Approval",
    description: "Formally approve and bind bilateral trade agreements",
  },
  {
    key: "FINANCE",
    label: "Finance",
    description: "Authorize payment requests and handle settlement operations",
  },
  {
    key: "FULFILLMENT",
    label: "Fulfillment",
    description: "Verify delivery and handle trade execution milestones",
  },
];

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

function getCurrentUserId(): string | null {
  const token = getAccessToken();
  if (!token) return null;
  try {
    const parts = token.split(".");
    if (parts.length < 2) return null;
    const base64 = parts[1].replaceAll("-", "+").replaceAll("_", "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const payload = JSON.parse(atob(padded));
    return typeof payload.sub === "string" ? payload.sub : null;
  } catch {
    return null;
  }
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
  const [draftRole, setDraftRole] = useState<"ADMIN" | "MEMBER">("MEMBER");
  const [draftAssignedCaps, setDraftAssignedCaps] = useState<Set<OrganizationCapability>>(
    new Set()
  );
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
    (m) => m.role === "ADMIN" && m.status === "ACTIVE"
  ).length;

  function handleStartEdit(member: OrganizationMember) {
    setEditingUserId(member.user_id);
    setDraftRole(member.role === "ADMIN" ? "ADMIN" : "MEMBER");
    setDraftAssignedCaps(new Set(member.assigned_capabilities || member.capabilities || []));
    setDraftExpectedVersion(member.version);
    setActionError(null);
    setActionNotice(null);
  }

  function handleCancelEdit() {
    setEditingUserId(null);
    setActionError(null);
  }

  function handleToggleCapability(cap: OrganizationCapability) {
    setDraftAssignedCaps((prev) => {
      const next = new Set(prev);
      if (next.has(cap)) {
        next.delete(cap);
      } else {
        next.add(cap);
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

    if (targetMember.role === "ADMIN" && draftRole === "MEMBER" && activeAdminsCount <= 1) {
      setActionError("Cannot demote the last remaining admin of the organization.");
      return;
    }

    setSaving(true);
    setActionError(null);
    setActionNotice(null);
    try {
      const updated = await updateMemberPermissions(organization.id, editingUserId, {
        expected_version: draftExpectedVersion,
        role: draftRole,
        capabilities: Array.from(draftAssignedCaps),
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
            const isLastAdmin = member.role === "ADMIN" && activeAdminsCount <= 1;

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
                          className={`badge ${member.role === "ADMIN" ? "badge--status-confirmed" : ""}`}
                          style={{ fontSize: "0.75rem", fontWeight: 600 }}
                        >
                          {member.role}
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
                        {(member.capabilities || []).map((cap) => (
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
                        {isSelf ? (
                          <span className="hint" style={{ fontSize: "0.75rem" }}>
                            Cannot self-modify
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
                              disabled={isLastAdmin || saving || revokingUserId === member.user_id}
                              title={isLastAdmin ? "Cannot revoke the last admin" : "Revoke membership"}
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

                    <div className="field" style={{ marginBottom: 12 }}>
                      <label htmlFor={`edit-role-${member.user_id}`}>Role</label>
                      <select
                        id={`edit-role-${member.user_id}`}
                        value={draftRole}
                        onChange={(e) => setDraftRole(e.target.value as "ADMIN" | "MEMBER")}
                        disabled={saving || (isLastAdmin && draftRole === "ADMIN")}
                      >
                        <option value="MEMBER">MEMBER (Safe default: Drafting)</option>
                        <option value="ADMIN">ADMIN (Safe default: Administration, Drafting, Agreement Approval)</option>
                      </select>
                      {isLastAdmin && (
                        <p className="hint">This is the only admin of the organization. Demotion is disabled.</p>
                      )}
                    </div>

                    <div className="field">
                      <label>Additional Capabilities</label>
                      <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 4 }}>
                        {ALL_CAPABILITIES.map((cap) => {
                          const isAssigned = draftAssignedCaps.has(cap.key);
                          const isDefaultInRole =
                            draftRole === "ADMIN"
                              ? ["ADMINISTRATION", "DRAFTING", "AGREEMENT_APPROVAL"].includes(cap.key)
                              : cap.key === "DRAFTING";

                          return (
                            <label
                              key={cap.key}
                              style={{
                                display: "flex",
                                alignItems: "flex-start",
                                gap: 8,
                                fontSize: "0.85rem",
                                cursor: "pointer",
                              }}
                            >
                              <input
                                type="checkbox"
                                checked={isAssigned || isDefaultInRole}
                                disabled={saving || isDefaultInRole}
                                onChange={() => handleToggleCapability(cap.key)}
                              />
                              <div>
                                <span>
                                  <strong>{cap.label}</strong> ({cap.key})
                                  {isDefaultInRole ? (
                                    <span className="muted" style={{ marginLeft: 6, fontSize: "0.75rem" }}>
                                      [Role default]
                                    </span>
                                  ) : null}
                                </span>
                                <div className="muted" style={{ fontSize: "0.75rem" }}>
                                  {cap.description}
                                </div>
                              </div>
                            </label>
                          );
                        })}
                      </div>
                    </div>
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
