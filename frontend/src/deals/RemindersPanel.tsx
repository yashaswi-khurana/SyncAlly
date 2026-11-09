import { useEffect, useState } from "react";

import { ApiError, listDealReminders, suppressDealReminder, syncDealReminders } from "../api/client";
import type { Deal, DealReminder, ReminderScope, ReminderStatus } from "../api/types";

interface RemindersPanelProps {
  deal: Deal;
  selectedOrganizationId?: string;
  reloadToken?: number;
}

function statusBadgeClass(status: ReminderStatus): string {
  switch (status) {
    case "SCHEDULED":
      return "badge badge--neutral";
    case "PENDING":
      return "badge badge--warning";
    case "DELIVERED":
      return "badge badge--success";
    case "SUPPRESSED":
      return "badge badge--secondary";
    case "FAILED":
      return "badge badge--danger";
    default:
      return "badge";
  }
}

function scopeBadgeLabel(scope: ReminderScope): string {
  switch (scope) {
    case "FULFILLMENT":
      return "Fulfillment";
    case "MILESTONE":
      return "Payment Milestone";
    case "CASE":
      return "Deal Case / Dispute";
    case "ROUTING":
      return "Approval Routing";
    default:
      return scope;
  }
}

function formatUtc(isoString: string): string {
  try {
    const d = new Date(isoString);
    return isNaN(d.getTime()) ? isoString : d.toISOString().replace("T", " ").substring(0, 19) + " UTC";
  } catch {
    return isoString;
  }
}

export default function RemindersPanel({
  deal,
  selectedOrganizationId,
  reloadToken = 0,
}: RemindersPanelProps) {
  const [reminders, setReminders] = useState<DealReminder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [suppressingId, setSuppressingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    void listDealReminders(deal.id, selectedOrganizationId, { signal: controller.signal })
      .then((data) => {
        if (!cancelled) {
          setReminders(data);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (cancelled || (err instanceof DOMException && err.name === "AbortError")) return;
        setError(err instanceof ApiError ? err.message : "Failed to load reminders");
        setLoading(false);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [deal.id, selectedOrganizationId, reloadToken]);

  const handleSync = async () => {
    setSyncing(true);
    setActionError(null);
    try {
      const updated = await syncDealReminders(deal.id, selectedOrganizationId);
      setReminders(updated);
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : "Failed to sync reminders";
      setActionError(msg);
    } finally {
      setSyncing(false);
    }
  };

  const handleSuppress = async (reminderId: string) => {
    setSuppressingId(reminderId);
    setActionError(null);
    try {
      const updated = await suppressDealReminder(deal.id, reminderId, selectedOrganizationId);
      setReminders((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : "Failed to suppress reminder";
      setActionError(msg);
    } finally {
      setSuppressingId(null);
    }
  };

  return (
    <section className="panel" aria-labelledby="reminders-panel-title" data-testid="reminders-panel">
      <div className="panel-head panel-head--row">
        <div>
          <span className="eyebrow">Durable Schedules</span>
          <h3 id="reminders-panel-title" className="display">
            Obligation reminders
          </h3>
        </div>
        <div>
          <button
            type="button"
            className="button button--secondary"
            onClick={handleSync}
            disabled={syncing || loading}
            aria-busy={syncing}
            data-testid="sync-reminders-button"
          >
            {syncing ? "Syncing..." : "Sync Reminders"}
          </button>
        </div>
      </div>

      {actionError && (
        <div className="banner banner--error" role="alert" style={{ marginBottom: "1rem" }}>
          {actionError}
        </div>
      )}

      {loading ? (
        <div className="panel-body" data-testid="reminders-loading">
          <p className="muted">Loading scheduled reminders...</p>
        </div>
      ) : error ? (
        <div className="panel-body">
          <div className="banner banner--error" role="alert">
            {error}
          </div>
        </div>
      ) : reminders.length === 0 ? (
        <div className="panel-body" data-testid="reminders-empty">
          <p className="muted">No obligation reminders scheduled for your organization.</p>
        </div>
      ) : (
        <div className="panel-body">
          <ul className="reminders-list" style={{ listStyle: "none", padding: 0, margin: 0 }} data-testid="reminders-list">
            {reminders.map((reminder) => {
              const isDismissible = reminder.status !== "SUPPRESSED";
              const isBusy = suppressingId === reminder.id;

              return (
                <li
                  key={reminder.id}
                  data-testid={`reminder-item-${reminder.id}`}
                  className="reminders-panel__item"
                >
                  <div className="reminders-panel__body">
                    <div className="reminders-panel__badges">
                      <span className="badge badge--outline" data-testid={`reminder-scope-${reminder.id}`}>
                        {scopeBadgeLabel(reminder.scope)}
                      </span>
                      <span
                        className={statusBadgeClass(reminder.status)}
                        data-testid={`reminder-status-${reminder.id}`}
                      >
                        {reminder.status}
                      </span>
                      <span className="badge badge--ghost" title="Recurrence count / cap">
                        {reminder.recurrence_count} / {reminder.recurrence_cap}
                      </span>
                      <span className="badge badge--ghost">Channel: {reminder.channel}</span>
                    </div>

                    <div className="reminders-panel__meta">
                      <span>Due: {formatUtc(reminder.due_at)}</span>
                      {reminder.delivered_at && (
                        <span>Delivered: {formatUtc(reminder.delivered_at)}</span>
                      )}
                      {reminder.suppression_reason && (
                        <span className="reminders-panel__meta--warning">
                          Suppressed ({reminder.suppression_reason})
                        </span>
                      )}
                      {(reminder.error_detail || reminder.last_error) && (
                        <span className="reminders-panel__meta--danger">
                          Error: {reminder.error_detail || reminder.last_error}
                        </span>
                      )}
                    </div>
                  </div>

                  {isDismissible && (
                    <div>
                      <button
                        type="button"
                        className="button button--ghost"
                        onClick={() => handleSuppress(reminder.id)}
                        disabled={isBusy}
                        aria-busy={isBusy}
                        data-testid={`dismiss-reminder-${reminder.id}`}
                      >
                        {isBusy ? "Dismissing..." : "Dismiss"}
                      </button>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </section>
  );
}
