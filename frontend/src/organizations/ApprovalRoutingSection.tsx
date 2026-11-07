import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import {
  ApiError,
  deleteApprovalRoutingPolicy,
  getApprovalRoutingPolicy,
  putApprovalRoutingPolicy,
} from "../api/client";
import type { ApprovalRoutingPolicy, Organization, OrganizationMember } from "../api/types";

interface Props {
  organization: Organization;
  members: OrganizationMember[];
}

function describeError(caught: unknown): string {
  if (caught instanceof ApiError) {
    if (caught.status === 409) {
      return caught.message || "Approval routing policy conflict; please refresh.";
    }
    if (caught.status === 422) {
      return caught.message || "Every approver must be an active member with Agreement Approval capability.";
    }
    return caught.message;
  }
  return "Something went wrong. Please try again.";
}

export default function ApprovalRoutingSection({ organization, members }: Props) {
  const isAdmin = organization.role === "ADMIN";
  const eligibleApprovers = members.filter((m) => m.capabilities.includes("AGREEMENT_APPROVAL"));

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [policy, setPolicy] = useState<ApprovalRoutingPolicy | null>(null);

  const [editing, setEditing] = useState(false);
  const [draftMode, setDraftMode] = useState<"SEQUENTIAL" | "PARALLEL">("PARALLEL");
  const [draftOrder, setDraftOrder] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const current = await getApprovalRoutingPolicy(organization.id);
        if (!cancelled) {
          setPolicy(current);
          setLoadError(null);
          setLoading(false);
        }
      } catch (caught) {
        if (!cancelled) {
          setLoadError(describeError(caught));
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [organization.id]);

  function startEdit() {
    setDraftMode(policy?.mode ?? "PARALLEL");
    setDraftOrder(policy?.approver_user_ids ?? []);
    setActionError(null);
    setActionNotice(null);
    setEditing(true);
  }

  function toggleApprover(userId: string) {
    setDraftOrder((prev) =>
      prev.includes(userId) ? prev.filter((id) => id !== userId) : [...prev, userId],
    );
  }

  function moveApprover(userId: string, delta: -1 | 1) {
    setDraftOrder((prev) => {
      const index = prev.indexOf(userId);
      const target = index + delta;
      if (index < 0 || target < 0 || target >= prev.length) return prev;
      const next = [...prev];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (draftOrder.length === 0) {
      setActionError("Select at least one eligible approver.");
      return;
    }
    setSaving(true);
    setActionError(null);
    try {
      const saved = await putApprovalRoutingPolicy(organization.id, {
        mode: draftMode,
        approver_user_ids: draftOrder,
        expected_version: policy?.version ?? null,
      });
      setPolicy(saved);
      setEditing(false);
      setActionNotice("Approval routing policy saved.");
    } catch (caught) {
      setActionError(describeError(caught));
    } finally {
      setSaving(false);
    }
  }

  async function handleRemove() {
    if (!policy) return;
    if (!window.confirm("Remove approval routing? This organization will revert to its default single-approver behavior.")) {
      return;
    }
    setSaving(true);
    setActionError(null);
    try {
      await deleteApprovalRoutingPolicy(organization.id, policy.version);
      setPolicy(null);
      setEditing(false);
      setActionNotice("Approval routing policy removed; default bilateral approval restored.");
    } catch (caught) {
      setActionError(describeError(caught));
    } finally {
      setSaving(false);
    }
  }

  function labelFor(userId: string): string {
    const member = members.find((m) => m.user_id === userId);
    return member ? member.display_name || member.email : userId;
  }

  if (loading) {
    return <p role="status" className="muted">Loading approval routing…</p>;
  }
  if (loadError) {
    return <p className="form-error" role="alert">{loadError}</p>;
  }

  return (
    <div
      className="approval-routing-section"
      data-testid="approval-routing-section"
      style={{ marginTop: 24, borderTop: "1px solid var(--border)", paddingTop: 16 }}
    >
      <div className="panel-head" style={{ marginBottom: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <span className="eyebrow">Organization Access</span>
          <h4 style={{ margin: "4px 0" }}>Approval Routing</h4>
          <p className="muted" style={{ fontSize: "0.85rem", margin: 0 }}>
            Optional: require specific members to approve, in sequence or in parallel, before this
            organization&apos;s approval is recorded. Leaving this unset keeps the default: any one
            member with Agreement Approval capability can approve alone.
          </p>
        </div>
      </div>

      {actionError && <p className="form-error" role="alert" style={{ marginBottom: 12 }}>{actionError}</p>}
      {actionNotice && <p className="success" role="status" style={{ marginBottom: 12 }}>{actionNotice}</p>}

      {!editing ? (
        <div>
          {policy ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <span className="badge">{policy.mode}</span>
                <span className="mono muted" style={{ fontSize: "0.75rem" }}>v{policy.version}</span>
              </div>
              <ol style={{ margin: 0, paddingLeft: 20 }}>
                {policy.approver_user_ids.map((userId) => (
                  <li key={userId}>{labelFor(userId)}</li>
                ))}
              </ol>
            </div>
          ) : (
            <p className="muted">No approval routing configured; default bilateral approval applies.</p>
          )}
          {isAdmin && (
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button type="button" className="button secondary" onClick={startEdit} disabled={saving}>
                {policy ? "Edit routing" : "Configure routing"}
              </button>
              {policy && (
                <button type="button" className="button danger" onClick={() => void handleRemove()} disabled={saving}>
                  Remove routing
                </button>
              )}
            </div>
          )}
        </div>
      ) : (
        <form onSubmit={handleSave} noValidate>
          <div className="field" style={{ marginBottom: 12 }}>
            <label htmlFor="routing-mode">Mode</label>
            <select
              id="routing-mode"
              value={draftMode}
              onChange={(e) => setDraftMode(e.target.value as "SEQUENTIAL" | "PARALLEL")}
              disabled={saving}
            >
              <option value="PARALLEL">Parallel (any order, all must approve)</option>
              <option value="SEQUENTIAL">Sequential (must approve in listed order)</option>
            </select>
          </div>

          <div className="field" style={{ marginBottom: 12 }}>
            <label>Eligible approvers</label>
            {eligibleApprovers.length === 0 ? (
              <p className="hint">
                No members currently have Agreement Approval capability. Grant it under Team
                Members &amp; Permissions first.
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 4 }}>
                {eligibleApprovers.map((member) => (
                  <label key={member.user_id} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.85rem" }}>
                    <input
                      type="checkbox"
                      checked={draftOrder.includes(member.user_id)}
                      disabled={saving}
                      onChange={() => toggleApprover(member.user_id)}
                    />
                    <span>{member.display_name || member.email}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {draftOrder.length > 0 && (
            <div className="field" style={{ marginBottom: 12 }}>
              <label>Order{draftMode === "SEQUENTIAL" ? " (turn order)" : ""}</label>
              <ol style={{ margin: 0, paddingLeft: 20 }}>
                {draftOrder.map((userId, index) => (
                  <li key={userId} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                    <span>{labelFor(userId)}</span>
                    {draftMode === "SEQUENTIAL" && (
                      <span style={{ display: "flex", gap: 4 }}>
                        <button
                          type="button"
                          className="button ghost"
                          style={{ fontSize: "0.7rem", padding: "2px 6px" }}
                          onClick={() => moveApprover(userId, -1)}
                          disabled={saving || index === 0}
                        >
                          ↑
                        </button>
                        <button
                          type="button"
                          className="button ghost"
                          style={{ fontSize: "0.7rem", padding: "2px 6px" }}
                          onClick={() => moveApprover(userId, 1)}
                          disabled={saving || index === draftOrder.length - 1}
                        >
                          ↓
                        </button>
                      </span>
                    )}
                  </li>
                ))}
              </ol>
            </div>
          )}

          <div style={{ display: "flex", gap: 8 }}>
            <button type="submit" className="button" disabled={saving}>
              {saving ? "Saving…" : "Save routing"}
            </button>
            <button type="button" className="button ghost" onClick={() => setEditing(false)} disabled={saving}>
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
