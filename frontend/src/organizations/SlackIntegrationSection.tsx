import { useCallback, useEffect, useState } from "react";

import { ApiError, disconnectSlack, getSlackConnection, startSlackConnection } from "../api/client";
import type { Organization, SlackConnection } from "../api/types";

type LoadState =
  | { status: "loading" }
  | { status: "restricted" }
  | { status: "error"; message: string }
  | { status: "ready"; connection: SlackConnection };

function describeError(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error && error.message) return error.message;
  return "Slack connection status could not be loaded. Try again.";
}

function callbackMessage(): string | null {
  const rawPath = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : window.location.hash;
  const [, query] = rawPath.split("?");
  const result = new URLSearchParams(query || "").get("integration");
  switch (result) {
    case "connected": return "Slack workspace connected. Messaging is not enabled yet.";
    case "cancelled": return "Slack authorization was cancelled.";
    case "workspace_in_use": return "That Slack workspace is already connected to another SyncAlly organization.";
    case "already_connected": return "A Slack workspace is already connected to this organization.";
    case "authorization_changed": return "Your organization permissions changed during authorization. Ask an administrator to connect Slack again.";
    case "failed": return "Slack could not be connected. Check the setup and try again.";
    default: return null;
  }
}

export default function SlackIntegrationSection({ organization }: { organization: Organization }) {
  const canManage = organization.role === "ADMIN";
  const [state, setState] = useState<LoadState>(() =>
    canManage ? { status: "loading" } : { status: "restricted" },
  );
  const [notice, setNotice] = useState<string | null>(() => callbackMessage());
  const [busy, setBusy] = useState(false);
  const [confirmingDisconnect, setConfirmingDisconnect] = useState(false);

  const loadConnection = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const connection = await getSlackConnection(organization.id);
      setState({ status: "ready", connection });
    } catch (error) {
      setState({ status: "error", message: describeError(error) });
    }
  }, [organization.id]);

  useEffect(() => {
    if (!canManage) return;
    let active = true;
    void getSlackConnection(organization.id)
      .then((connection) => {
        if (active) setState({ status: "ready", connection });
      })
      .catch((error: unknown) => {
        if (active) setState({ status: "error", message: describeError(error) });
      });
    return () => { active = false; };
  }, [canManage, organization.id]);

  async function connect() {
    setBusy(true);
    setNotice(null);
    try {
      const result = await startSlackConnection(organization.id);
      window.location.assign(result.authorization_url);
    } catch (error) {
      setNotice(describeError(error));
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true);
    setNotice(null);
    try {
      await disconnectSlack(organization.id);
      setConfirmingDisconnect(false);
      setNotice("Slack was disconnected and its SyncAlly access token was revoked.");
      await loadConnection();
    } catch (error) {
      setNotice(describeError(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="org-tab-panel" id="org-integrations-panel" role="tabpanel" aria-labelledby="org-integrations-tab">
      <div className="org-section-heading">
        <div>
          <span className="eyebrow">Connected apps</span>
          <h4>Integrations</h4>
          <p className="muted">Connect collaboration tools to this organization. Each provider installation is scoped to one SyncAlly organization.</p>
        </div>
      </div>

      <article className="card" aria-labelledby="slack-integration-heading">
        <div className="org-team-actions">
          <div>
            <span className="eyebrow">Collaboration</span>
            <h4 id="slack-integration-heading">Slack</h4>
            <p className="muted">Use a Slack workspace to ask about SyncAlly deals and receive selected updates in a later release.</p>
          </div>
          {state.status === "ready" && !state.connection.connected && canManage ? (
            <button type="button" className="button" onClick={() => void connect()} disabled={busy || !state.connection.configured}>
              {busy ? "Opening Slack…" : "Connect Slack"}
            </button>
          ) : null}
        </div>

        {canManage && state.status === "loading" ? <p role="status">Loading Slack connection…</p> : null}
        {state.status === "restricted" || !canManage ? <p className="muted" role="status">Only an organization administrator can view or manage Slack connection details.</p> : null}
        {canManage && state.status === "error" ? <div role="alert"><p className="form-error">{state.message}</p><button type="button" className="button secondary" onClick={() => void loadConnection()}>Try again</button></div> : null}
        {canManage && state.status === "ready" && !state.connection.configured ? (
          <p className="muted" role="status">Slack setup is not configured for this SyncAlly deployment yet.</p>
        ) : null}
        {canManage && state.status === "ready" && state.connection.connected ? (
          <div>
            <p role="status"><strong>Connected to {state.connection.workspace_name}</strong></p>
            <p className="muted">Workspace ID: <code>{state.connection.workspace_id}</code></p>
            <p className="muted">Granted access: {state.connection.granted_scopes.join(", ") || "No scopes reported"}</p>
            <p className="muted">Connected {state.connection.connected_at ? new Date(state.connection.connected_at).toLocaleString() : "recently"}</p>
            <p className="hint">Connected; messaging is not enabled yet. Slack will not read messages or send deal updates in this slice.</p>
            {canManage ? <button type="button" className="button danger" onClick={() => setConfirmingDisconnect(true)} disabled={busy}>Disconnect Slack</button> : null}
          </div>
        ) : null}
        {notice ? <p className="form-error" role="status">{notice}</p> : null}
      </article>

      {confirmingDisconnect && canManage ? (
        <div className="manual-fact-modal-backdrop" role="presentation">
          <section className="manual-fact-modal" role="dialog" aria-modal="true" aria-labelledby="disconnect-slack-title">
            <span className="eyebrow">Confirm disconnection</span>
            <h3 id="disconnect-slack-title">Disconnect Slack?</h3>
            <p className="muted">SyncAlly will revoke its Slack token and remove access for this organization. You can connect the workspace again later.</p>
            {notice ? <p className="form-error" role="alert">{notice}</p> : null}
            <div className="org-team-actions">
              <button type="button" className="button ghost" onClick={() => setConfirmingDisconnect(false)} disabled={busy}>Cancel</button>
              <button type="button" className="button danger" onClick={() => void disconnect()} disabled={busy}>{busy ? "Disconnecting…" : "Confirm disconnect"}</button>
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}
