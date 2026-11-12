import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, disconnectSlack, getSlackAccountLinkStatus, getSlackConnection, redeemSlackLink, startSlackConnection } from "../api/client";
import type { Organization, SlackConnection } from "../api/types";

type LoadState =
  | { status: "loading" }
  | { status: "restricted" }
  | { status: "error"; message: string }
  | { status: "ready"; connection: SlackConnection };

type LinkStatusState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; workspaceConnected: boolean; accountLinked: boolean };

type Notice = { kind: "success" | "info" | "error"; message: string };

function describeError(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error && error.message) return error.message;
  return "Slack connection status could not be loaded. Try again.";
}

function describeLinkError(error: unknown): string {
  if (error instanceof ApiError && error.status === 401) {
    return "Your SyncAlly session has expired. Sign in again, then submit a fresh Slack link code.";
  }
  const message = describeError(error);
  if (/invalid or expired/i.test(message)) {
    return "That code is invalid or expired. Mention @SyncAlly link in Slack to get a fresh code, then try again.";
  }
  if (/already linked/i.test(message)) {
    return "This Slack account or SyncAlly account is already linked. Sign in to the account you want to link, or ask an organization administrator for help.";
  }
  if (/organization membership required/i.test(message)) {
    return "Your signed-in account needs active membership in this organization to link Slack.";
  }
  return message;
}

function callbackMessage(): Notice | null {
  const rawPath = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : window.location.hash;
  const [, query] = rawPath.split("?");
  const result = new URLSearchParams(query || "").get("integration");
  switch (result) {
    case "connected": return { kind: "success", message: "Slack is connected. Members can now link their accounts and use the commands below." };
    case "cancelled": return { kind: "info", message: "Slack setup was cancelled. You can connect a workspace whenever you are ready." };
    case "workspace_in_use": return { kind: "error", message: "That Slack workspace is already connected to another SyncAlly organization." };
    case "already_connected": return { kind: "error", message: "A Slack workspace is already connected to this organization." };
    case "authorization_changed": return { kind: "error", message: "Your organization permissions changed during setup. Ask an administrator to connect Slack again." };
    case "failed": return { kind: "error", message: "Slack could not be connected. Check the Slack app setup, then try again." };
    default: return null;
  }
}

function noticeClass(kind: Notice["kind"]): string {
  if (kind === "success") return "success";
  if (kind === "error") return "form-error";
  return "muted";
}

export default function SlackIntegrationSection({ organization }: { organization: Organization }) {
  const canManage = organization.role === "ADMIN";
  const [state, setState] = useState<LoadState>(() =>
    canManage ? { status: "loading" } : { status: "restricted" },
  );
  const [linkStatus, setLinkStatus] = useState<LinkStatusState>({ status: "loading" });
  const [integrationNotice, setIntegrationNotice] = useState<Notice | null>(() => callbackMessage());
  const [linkNotice, setLinkNotice] = useState<Notice | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmingDisconnect, setConfirmingDisconnect] = useState(false);
  const [linkCode, setLinkCode] = useState("");
  const [linking, setLinking] = useState(false);
  const disconnectTriggerRef = useRef<HTMLButtonElement>(null);
  const cancelDisconnectRef = useRef<HTMLButtonElement>(null);
  const disconnectDialogRef = useRef<HTMLElement>(null);
  const integrationNoticeRef = useRef<HTMLParagraphElement>(null);

  const loadConnection = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const connection = await getSlackConnection(organization.id);
      setState({ status: "ready", connection });
    } catch (error) {
      setState({ status: "error", message: describeError(error) });
    }
  }, [organization.id]);

  const loadLinkStatus = useCallback(async () => {
    setLinkStatus({ status: "loading" });
    try {
      const result = await getSlackAccountLinkStatus(organization.id);
      setLinkStatus({
        status: "ready",
        workspaceConnected: result.workspace_connected,
        accountLinked: result.account_linked,
      });
    } catch (error) {
      setLinkStatus({ status: "error", message: describeError(error) });
    }
  }, [organization.id]);

  useEffect(() => {
    let active = true;
    void getSlackAccountLinkStatus(organization.id)
      .then((result) => {
        if (active) {
          setLinkStatus({
            status: "ready",
            workspaceConnected: result.workspace_connected,
            accountLinked: result.account_linked,
          });
        }
      })
      .catch((error: unknown) => {
        if (active) setLinkStatus({ status: "error", message: describeError(error) });
      });
    return () => { active = false; };
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

  useEffect(() => {
    if (!confirmingDisconnect) return;
    const returnFocus = disconnectTriggerRef.current;
    cancelDisconnectRef.current?.focus();

    function handleDialogKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && !busy) {
        event.preventDefault();
        setConfirmingDisconnect(false);
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = disconnectDialogRef.current?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable?.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!disconnectDialogRef.current?.contains(document.activeElement)) {
        event.preventDefault();
        first.focus();
      } else if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleDialogKeyDown);
    return () => {
      document.removeEventListener("keydown", handleDialogKeyDown);
      returnFocus?.focus();
    };
  }, [busy, confirmingDisconnect]);

  async function connect() {
    setBusy(true);
    setIntegrationNotice(null);
    try {
      const result = await startSlackConnection(organization.id);
      window.location.assign(result.authorization_url);
    } catch (error) {
      setIntegrationNotice({ kind: "error", message: describeError(error) });
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true);
    setIntegrationNotice(null);
    try {
      await disconnectSlack(organization.id);
      setConfirmingDisconnect(false);
      setIntegrationNotice({ kind: "success", message: "Slack was disconnected and its access token was revoked." });
      await loadConnection();
      await loadLinkStatus();
      integrationNoticeRef.current?.focus();
    } catch (error) {
      setIntegrationNotice({ kind: "error", message: describeError(error) });
    } finally {
      setBusy(false);
    }
  }

  async function linkAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLinkNotice(null);
    setLinking(true);
    try {
      await redeemSlackLink(linkCode.trim());
      setLinkCode("");
      setLinkStatus({ status: "ready", workspaceConnected: true, accountLinked: true });
    } catch (error) {
      setLinkNotice({ kind: "error", message: describeLinkError(error) });
    } finally {
      setLinking(false);
    }
  }

  const connected = state.status === "ready" && state.connection.connected;

  return (
    <section className="org-tab-panel" id="org-integrations-panel" role="tabpanel" aria-labelledby="org-integrations-tab">
      <div className="org-section-heading">
        <div>
          <span className="eyebrow">Connected apps</span>
          <h4>Integrations</h4>
          <p className="muted">Connect collaboration tools to this organization. Each provider installation is scoped to one SyncAlly organization.</p>
        </div>
      </div>

      <article className="card slack-integration-card" aria-labelledby="slack-integration-heading">
        <div className="org-team-actions">
          <div>
            <span className="eyebrow">Collaboration</span>
            <h4 id="slack-integration-heading">Slack</h4>
            <p className="muted">Let members use SyncAlly in Slack to check deal status, review permitted payment status, start eligible draft deals, and follow updates.</p>
          </div>
          {state.status === "ready" && !connected && canManage ? (
            <button type="button" className="button" onClick={() => void connect()} disabled={busy || !state.connection.configured}>
              {busy ? "Opening Slack..." : "Connect Slack"}
            </button>
          ) : null}
        </div>

        {canManage && state.status === "loading" ? <p className="muted" role="status">Checking the Slack connection...</p> : null}
        {!canManage ? <p className="muted" role="status">An organization administrator manages the Slack workspace connection. Contact them if SyncAlly is not responding in Slack.</p> : null}
        {canManage && state.status === "error" ? (
          <div role="alert" className="slack-integration-card__alert">
            <p className="form-error">{state.message}</p>
            <button type="button" className="button secondary" onClick={() => void loadConnection()}>Try again</button>
          </div>
        ) : null}
        {canManage && state.status === "ready" && !state.connection.configured ? (
          <p className="muted" role="status">Slack is not configured for this SyncAlly deployment yet. Ask your deployment administrator to finish the Slack app setup.</p>
        ) : null}
        {canManage && state.status === "ready" && !state.connection.connected && state.connection.configured ? (
          <p className="muted" role="status">No Slack workspace is connected to {organization.legal_name} yet. Connect one to make the commands available to members.</p>
        ) : null}
        {canManage && connected ? (
          <div className="slack-integration-card__connected">
            <p className="slack-integration-card__connected-label" role="status">
              <span className="badge badge--status-confirmed">Connected</span>
              <strong>{state.connection.workspace_name || "Slack workspace"}</strong>
            </p>
            <p className="muted">Connected {state.connection.connected_at ? new Date(state.connection.connected_at).toLocaleString() : "recently"}.</p>
            <p className="hint">SyncAlly handles messages that mention @SyncAlly; it does not read channel history. Deal access comes from each member's SyncAlly permissions.</p>
            <button ref={disconnectTriggerRef} type="button" className="button danger" onClick={() => setConfirmingDisconnect(true)} disabled={busy}>Disconnect Slack</button>
          </div>
        ) : null}
        {integrationNotice && (!confirmingDisconnect || integrationNotice.kind !== "error") ? <p ref={integrationNoticeRef} tabIndex={-1} className={noticeClass(integrationNotice.kind)} role={integrationNotice.kind === "error" ? "alert" : "status"}>{integrationNotice.message}</p> : null}
      </article>

      <article className="card slack-integration-card" aria-labelledby="slack-account-link-heading">
        <h4 id="slack-account-link-heading">Link your Slack account</h4>
        {linkStatus.status === "loading" ? (
          <p className="muted" role="status">Checking the Slack connection and your account link...</p>
        ) : linkStatus.status === "error" ? (
          <div className="slack-integration-card__alert" role="alert">
            <p className="form-error">{linkStatus.message}</p>
            <button type="button" className="button secondary" onClick={() => void loadLinkStatus()}>Try again</button>
          </div>
        ) : linkStatus.accountLinked ? (
          <p className="success" role="status">Your Slack account is linked. Deal and payment access still follow your SyncAlly permissions.</p>
        ) : !linkStatus.workspaceConnected ? (
          <p className="muted" role="status">An organization administrator must connect a Slack workspace before you can link your account.</p>
        ) : (
          <>
            <ol className="slack-link-steps">
              <li>In the connected Slack workspace, mention <code>@SyncAlly link</code>.</li>
              <li>Copy the private code the bot sends you. It expires after 10 minutes.</li>
              <li>Paste the code below while signed in to the SyncAlly account you want to link.</li>
            </ol>
            <p className="muted">Linking confirms your identity. It does not grant access to deals or payments.</p>
            <form className="org-add-member slack-link-form" onSubmit={(event) => void linkAccount(event)} noValidate>
              <div className="org-add-member__controls">
                <div className="field">
                  <label htmlFor="slack-link-code">Temporary link code</label>
                  <input
                    id="slack-link-code"
                    name="slack-link-code"
                    type="text"
                    autoComplete="off"
                    autoCapitalize="characters"
                    autoCorrect="off"
                    spellCheck={false}
                    placeholder="Paste the code from Slack"
                    maxLength={64}
                    aria-describedby="slack-link-code-help"
                    value={linkCode}
                    onChange={(event) => { setLinkCode(event.target.value); setLinkNotice(null); }}
                    disabled={linking}
                  />
                  <span className="hint" id="slack-link-code-help">Paste the private code from @SyncAlly link. It must have 8 or more characters; this button enables when the code is ready. Codes expire after 10 minutes and can only be used once.</span>
                </div>
                <button type="submit" className="button secondary" disabled={linking || linkCode.trim().length < 8}>
                  {linking ? "Linking..." : "Link Slack account"}
                </button>
              </div>
            </form>
            {linkNotice ? <p className={noticeClass(linkNotice.kind)} role={linkNotice.kind === "error" ? "alert" : "status"}>{linkNotice.message}</p> : null}
          </>
        )}
      </article>

      <article className="card slack-integration-card" aria-labelledby="slack-commands-heading">
        <h4 id="slack-commands-heading">What members can do in Slack</h4>
        <p className="muted">Mention @SyncAlly in a message or thread. Deal replies are visible only to you. Use the commands below with deals your SyncAlly account can access.</p>
        <ul className="slack-command-list">
          <li><code>@SyncAlly status &lt;deal-name&gt;</code><span>Check a uniquely named deal's current status, for example <code>status Acme renewal</code>.</span></li>
          <li><code>@SyncAlly payments &lt;deal-name&gt;</code><span>View payment status when you have payment access.</span></li>
          <li><code>@SyncAlly follow &lt;deal-name&gt;</code><span>Get eligible deal updates in that thread. Use <code>@SyncAlly unfollow &lt;deal-name&gt;</code> to stop.</span></li>
          <li><code>@SyncAlly share &lt;message&gt;</code><span>Post a shareable deal message from this thread; the other party's followed thread receives it privately.</span></li>
          <li><code>@SyncAlly start buyer &lt;organization-id&gt;</code><span>Create a draft deal with an organization you can work with. If your organization is the seller, use <code>@SyncAlly start seller &lt;organization-id&gt;</code>.</span></li>
        </ul>
        <p className="hint">Use the exact deal name; matching ignores letter case. If multiple deals share the name, use the exact deal ID instead. Unnamed drafts still need their ID.</p>
        <p className="hint">Replies use your SyncAlly permissions. Linking Slack confirms your identity; it does not grant access to deals or payments.</p>
      </article>

      {confirmingDisconnect && canManage ? (
        <div className="manual-fact-modal-backdrop" role="presentation">
          <section ref={disconnectDialogRef} className="manual-fact-modal" role="dialog" aria-modal="true" aria-labelledby="disconnect-slack-title" aria-describedby="disconnect-slack-description" tabIndex={-1}>
            <span className="eyebrow">Confirm disconnection</span>
            <h3 id="disconnect-slack-title">Disconnect Slack?</h3>
            <p className="muted" id="disconnect-slack-description">SyncAlly will revoke its Slack token and remove this workspace connection, account links, and update subscriptions. Members will need to link again after the workspace is reconnected.</p>
            {integrationNotice?.kind === "error" ? <p className="form-error" role="alert">{integrationNotice.message}</p> : null}
            <div className="org-team-actions">
              <button ref={cancelDisconnectRef} type="button" className="button ghost" onClick={() => setConfirmingDisconnect(false)} disabled={busy}>Cancel</button>
              <button type="button" className="button danger" onClick={() => void disconnect()} disabled={busy}>{busy ? "Disconnecting..." : "Confirm disconnect"}</button>
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}
