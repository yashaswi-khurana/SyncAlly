import { type FormEvent, useEffect,useRef, useState } from "react";

import {
  ApiError,
  createDealMessage,
  listDealFacts,
  listDealMessages,
  listOrganizations,
  reviewDealFact,
  updateFactVisibility,
} from "../api/client";
import type {
  Deal,
  DealFact,
  DealMessage,
  FactReviewAction,
  Organization,
  Visibility,
} from "../api/types";
import AISuggestionReview from "./AISuggestionReview";

type OrganizationState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; organizations: Organization[] };

type ConversationState = { dealId: string } & (
  | { status: "loading"; organizationId: string }
  | { status: "error"; organizationId: string; message: string }
  | {
      status: "ready";
      organizationId: string;
      messages: DealMessage[];
      facts: DealFact[];
    });

interface DealConversationReviewProps {
  deal: Deal;
  onAgreementCreated?: () => void;
  onMessagesChanged?: (messages: DealMessage[]) => void;
  onMessageCreated?: () => void;
  selectedOrganizationId?: string;
  onOrganizationChange?: (organizationId: string) => void;
  revalidateIntervalMs?: number;
}

type FactFilter = "all" | "needs-review" | "confirmed" | "private";

const REVIEWABLE_STATUSES = new Set<DealFact["status"]>([
  "EXTRACTED",
  "NEEDS_CLARIFICATION",
]);

function areFactsEqual(a: DealFact[], b: DealFact[]): boolean {
  if (a.length !== b.length) {
    return false;
  }
  for (let i = 0; i < a.length; i++) {
    const factA = a[i];
    const factB = b[i];
    if (
      factA.id !== factB.id ||
      factA.version !== factB.version ||
      factA.visibility !== factB.visibility ||
      factA.status !== factB.status ||
      factA.typed_value !== factB.typed_value ||
      factA.currency_or_unit !== factB.currency_or_unit ||
      factA.kind !== factB.kind ||
      factA.field !== factB.field ||
      factA.source_span !== factB.source_span ||
      factA.source_message_id !== factB.source_message_id ||
      factA.confirmed_by !== factB.confirmed_by ||
      factA.confirmed_at !== factB.confirmed_at
    ) {
      return false;
    }
  }
  return true;
}

function describeError(caught: unknown): string {
  if (caught instanceof ApiError) {
    if (caught.status === 401) {
      return "Your session has expired. Sign in again.";
    }
    return caught.message;
  }
  return "Something went wrong. Please try again.";
}

function readable(value: string): string {
  return value.toLowerCase().replaceAll("_", " ");
}

function organizationRole(deal: Deal, organizationId: string): string {
  if (organizationId === deal.buyer_organization_id) {
    return "Buyer";
  }
  return "Seller";
}

function formatTimestamp(value: string): string {
  return new Date(value).toLocaleString();
}

function MessageComposer({ deal, organization, onSent }: {
  deal: Deal;
  organization: Organization;
  onSent: (message: DealMessage) => void;
}) {
  const [body, setBody] = useState("");
  const [visibility, setVisibility] = useState<Visibility>("SHAREABLE");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => { request.current?.abort(); }, []);

  async function send() {
    if (request.current) return;
    const text = body.trim();
    setSent(false);
    if (!text || text.length > 8000) {
      setError(!text ? "Enter a message before sending." : "Keep your message within 8,000 characters.");
      return;
    }
    const controller = new AbortController();
    request.current = controller;
    setSubmitting(true);
    setError(null);
    try {
      const message = await createDealMessage(deal.id, {
        body: text, visibility, organization_id: organization.id,
        idempotency_key: crypto.randomUUID(),
      }, { signal: controller.signal });
      if (controller.signal.aborted) return;
      onSent(message);
      setBody("");
      setSent(true);
    } catch (caught) {
      if (!controller.signal.aborted) setError(describeError(caught));
    } finally {
      if (!controller.signal.aborted) {
        request.current = null;
        setSubmitting(false);
      }
    }
  }

  return (
    <form className="message-composer" noValidate onSubmit={(event) => { event.preventDefault(); void send(); }}>
      <p className="hint">Sending as {organization.legal_name} ({organizationRole(deal, organization.id)})</p>
      <div className="field">
        <label htmlFor={`deal-message-composer-${deal.id}`}>Message</label>
        <textarea id={`deal-message-composer-${deal.id}`} rows={4} maxLength={8000}
          placeholder="Discuss trade terms (e.g. quantity, unit price, delivery port, timeline)..."
          value={body} disabled={submitting}
          aria-describedby={`message-help-${deal.id}${error ? ` message-error-${deal.id}` : ""}`}
          aria-invalid={error ? true : undefined}
          onChange={(event) => { setBody(event.target.value); setSent(false); setError(null); }}
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.metaKey || event.ctrlKey) && !event.nativeEvent.isComposing) {
              event.preventDefault(); void send();
            }
          }} />
      </div>
      <fieldset className="message-composer__visibility" disabled={submitting}>
        <legend>Message visibility</legend>
        <label><input type="radio" name="message-visibility" value="SHAREABLE"
          checked={visibility === "SHAREABLE"} onChange={() => setVisibility("SHAREABLE")} />
          <span><span aria-hidden="true">{"\u{1F310}"} </span>Shareable <small>Visible to both buyer and seller</small></span>
        </label>
        <label><input type="radio" name="message-visibility" value="PRIVATE"
          checked={visibility === "PRIVATE"} onChange={() => setVisibility("PRIVATE")} />
          <span><span aria-hidden="true">{"\u{1F512}"} </span>Private <small>Visible only to members of your organization</small></span>
        </label>
      </fieldset>
      <div className="message-composer__actions">
        <button type="submit" className="button" disabled={submitting}>{submitting ? "Sending..." : "Send Message"}</button>
        <p id={`message-help-${deal.id}`} className="hint">Cmd/Ctrl + Enter to send</p>
      </div>
      {error ? <p id={`message-error-${deal.id}`} className="form-error" role="alert">{error} Your draft is saved here; you can try sending again.</p> : null}
      {sent ? <p role="status">Message sent.</p> : null}
    </form>
  );
function generateIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

export default function DealConversationReview({
  deal,
  onAgreementCreated = () => {},
  onMessagesChanged,
  onMessageCreated,
  selectedOrganizationId: controlledOrgId,
  onOrganizationChange,
  revalidateIntervalMs = 4000,
}: DealConversationReviewProps) {
  const [organizationState, setOrganizationState] = useState<OrganizationState>({
    status: "loading",
  });
  const [internalSelectedOrgId, setInternalSelectedOrgId] = useState("");
  const selectedOrganizationId =
    controlledOrgId !== undefined ? controlledOrgId : internalSelectedOrgId;
  const [conversationState, setConversationState] = useState<ConversationState | null>(null);
  const [reloadCount, setReloadCount] = useState(0);
  const [pendingFactId, setPendingFactId] = useState<string | null>(null);
  const [pendingVisibilityFactId, setPendingVisibilityFactId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<{ factId: string; message: string } | null>(null);
  const [highlightedMessageId, setHighlightedMessageId] = useState<string | null>(null);
  const [factFilter, setFactFilter] = useState<FactFilter>("all");
  const [messageBody, setMessageBody] = useState("");
  const [messageVisibility, setMessageVisibility] = useState<Visibility>("SHAREABLE");
  const [submittingMessage, setSubmittingMessage] = useState(false);
  const [messageError, setMessageError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void listOrganizations()
      .then((organizations) => {
        if (cancelled) {
          return;
        }
        const partyOrganizations = organizations.filter(
          (organization) =>
            organization.id === deal.buyer_organization_id ||
            organization.id === deal.seller_organization_id,
        );
        setOrganizationState({ status: "ready", organizations: partyOrganizations });
        const defaultOrgId = partyOrganizations.length === 1 ? partyOrganizations[0].id : "";
        setInternalSelectedOrgId(defaultOrgId);
        if (defaultOrgId) {
          onOrganizationChange?.(defaultOrgId);
        }
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setOrganizationState({ status: "error", message: describeError(caught) });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [deal.buyer_organization_id, deal.seller_organization_id, onOrganizationChange]);

  const partyOrganizations = organizationState.status === "ready" ? organizationState.organizations : [];
  const selectedOrganization = partyOrganizations.find(
    (organization) => organization.id === selectedOrganizationId,
  );
  const activeOrganizationId = selectedOrganization?.id ?? "";
  const currentConversation =
    conversationState?.status === "ready" && conversationState.organizationId === activeOrganizationId && conversationState.dealId === deal.id
      ? conversationState
      : null;
  const visibleFacts =
    currentConversation
      ? currentConversation.facts.filter(
          (fact) =>
            fact.visibility === "SHAREABLE" || fact.owner_organization_id === activeOrganizationId,
        )
      : [];
  const visibleMessages = currentConversation?.messages ?? [];
  const factsAwaitingReview = visibleFacts.filter((fact) => REVIEWABLE_STATUSES.has(fact.status)).length;
  const confirmedFacts = visibleFacts.filter((fact) => fact.status === "CONFIRMED").length;
  const privateFacts = visibleFacts.filter((fact) => fact.visibility === "PRIVATE").length;
  const filteredFacts = visibleFacts.filter((fact) => {
    if (factFilter === "needs-review") {
      return REVIEWABLE_STATUSES.has(fact.status);
    }
    if (factFilter === "confirmed") {
      return fact.status === "CONFIRMED";
    }
    if (factFilter === "private") {
      return fact.visibility === "PRIVATE";
    }
    return true;
  });

  function traceSourceMessage(messageId: string) {
    setHighlightedMessageId(messageId);
    document.getElementById(`deal-message-${messageId}`)?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  }

  useEffect(() => {
    if (!activeOrganizationId) {
      return;
    }
    let cancelled = false;
    void Promise.all([
      listDealMessages(deal.id, activeOrganizationId),
      listDealFacts(deal.id, activeOrganizationId),
    ])
      .then(([messages, facts]) => {
        if (!cancelled) {
          setConversationState({
            status: "ready",
            organizationId: activeOrganizationId,
            dealId: deal.id,
            messages,
            facts,
          });
        }
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setConversationState({
            status: "error",
            organizationId: activeOrganizationId,
            dealId: deal.id,
            message: describeError(caught),
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [activeOrganizationId, deal.id, reloadCount]);

  const conversationReady = currentConversation !== null;
  const observedMessages = currentConversation?.messages;
  useEffect(() => {
    if (observedMessages) onMessagesChanged?.(observedMessages);
  }, [observedMessages, onMessagesChanged]);

  function appendMessage(message: DealMessage) {
    setConversationState((current) =>
      current?.status === "ready" && current.organizationId === activeOrganizationId && current.dealId === deal.id
        ? { ...current, messages: [...current.messages.filter((item) => item.id !== message.id), message] }
        : current);
  }

  useEffect(() => {
    if (!activeOrganizationId || !conversationReady) {
      return;
    }

    let cancelled = false;
    let inFlight = false;

    const revalidate = async () => {
      if (cancelled || inFlight || pendingFactId !== null || pendingVisibilityFactId !== null) {
        return;
      }
      if (typeof document !== "undefined" && document.hidden) {
        return;
      }

      inFlight = true;
      try {
        const freshFacts = await listDealFacts(deal.id, activeOrganizationId);
        if (!cancelled) {
          setConversationState((current) => {
            if (current?.status !== "ready" || current.organizationId !== activeOrganizationId || current.dealId !== deal.id) {
              return current;
            }
            if (areFactsEqual(current.facts, freshFacts)) {
              return current;
            }
            return { ...current, facts: freshFacts };
          });
        }
      } catch {
        // Silently tolerate background revalidation errors so active review UI is not disrupted
      } finally {
        inFlight = false;
      }
    };

    const intervalId =
      revalidateIntervalMs > 0 && typeof window !== "undefined"
        ? window.setInterval(revalidate, revalidateIntervalMs)
        : null;

    const onWindowFocus = () => {
      void revalidate();
    };

    const onVisibilityChange = () => {
      if (typeof document !== "undefined" && !document.hidden) {
        void revalidate();
      }
    };

    if (typeof window !== "undefined") {
      window.addEventListener("focus", onWindowFocus);
    }
    if (typeof document !== "undefined") {
      document.addEventListener("visibilitychange", onVisibilityChange);
    }

    return () => {
      cancelled = true;
      if (intervalId !== null && typeof window !== "undefined") {
        window.clearInterval(intervalId);
      }
      if (typeof window !== "undefined") {
        window.removeEventListener("focus", onWindowFocus);
      }
      if (typeof document !== "undefined") {
        document.removeEventListener("visibilitychange", onVisibilityChange);
      }
    };
  }, [
    activeOrganizationId,
    conversationReady,
    deal.id,
    pendingFactId,
    pendingVisibilityFactId,
    revalidateIntervalMs,
  ]);

  function retryConversation() {
    setConversationState(null);
    setReloadCount((count) => count + 1);
  }

  async function reviewFact(fact: DealFact, action: FactReviewAction) {
    setPendingFactId(fact.id);
    setActionError(null);
    try {
      const updatedFact = await reviewDealFact(deal.id, fact.id, action);
      setConversationState((current) =>
        current?.status === "ready" && current.organizationId === activeOrganizationId && current.dealId === deal.id
          ? {
              ...current,
              facts: current.facts.map((item) => (item.id === updatedFact.id ? updatedFact : item)),
            }
          : current,
      );
    } catch (caught) {
      setActionError({ factId: fact.id, message: describeError(caught) });
    } finally {
      setPendingFactId(null);
    }
  }

  async function toggleFactVisibility(fact: DealFact) {
    const nextVisibility = fact.visibility === "PRIVATE" ? "SHAREABLE" : "PRIVATE";
    setPendingVisibilityFactId(fact.id);
    setActionError(null);
    try {
      const updatedFact = await updateFactVisibility(deal.id, fact.id, nextVisibility);
      setConversationState((current) =>
        current?.status === "ready" && current.organizationId === activeOrganizationId && current.dealId === deal.id
          ? {
              ...current,
              facts: current.facts.map((item) => (item.id === updatedFact.id ? updatedFact : item)),
            }
          : current,
      );
    } catch (caught) {
      setActionError({ factId: fact.id, message: describeError(caught) });
    } finally {
      setPendingVisibilityFactId(null);
    }
  }

  function addSuggestedFact(fact: DealFact) {
    setConversationState((current) => current?.status === "ready" && current.organizationId === activeOrganizationId && current.dealId === deal.id
      ? { ...current, facts: [...current.facts.filter((item) => item.id !== fact.id), fact] }
      : current);
    if (
      fact.source_message_id
      && currentConversation
      && !currentConversation.messages.some((message) => message.id === fact.source_message_id)
    ) {
      const initialMessageIds = new Set(currentConversation.messages.map((message) => message.id));
      void listDealMessages(deal.id, activeOrganizationId).then((messages) => {
        setConversationState((current) => {
          if (current?.status !== "ready" || current.organizationId !== activeOrganizationId || current.dealId !== deal.id) return current;
          // A confirmed send may arrive while this older transcript snapshot is in flight.
          const fetchedIds = new Set(messages.map((message) => message.id));
          const addedWhileLoading = current.messages.filter((message) =>
            !initialMessageIds.has(message.id) && !fetchedIds.has(message.id));
          return { ...current, messages: [...messages, ...addedWhileLoading] };
        });
      }).catch(() => {
        // The fact remains saved; message refresh can be retried by reloading the conversation.
      });
    }
  }

  function updateSuggestedFact(fact: DealFact) {
    setConversationState((current) => current?.status === "ready" && current.organizationId === activeOrganizationId && current.dealId === deal.id
      ? { ...current, facts: current.facts.map((item) => item.id === fact.id ? fact : item) }
      : current);
  }

  function replaceSuggestedFact(replaced: DealFact, corrected: DealFact) {
    setConversationState((current) => current?.status === "ready" && current.organizationId === activeOrganizationId && current.dealId === deal.id
      ? {
          ...current,
          facts: [...current.facts.map((item) => item.id === replaced.id ? replaced : item), corrected],
        }
      : current);
  }

  async function handleSendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = messageBody.trim();
    if (!trimmed || !activeOrganizationId) {
      return;
    }

    setSubmittingMessage(true);
    setMessageError(null);
    try {
      const createdMessage = await createDealMessage(deal.id, {
        body: trimmed,
        visibility: messageVisibility,
        organization_id: activeOrganizationId,
        idempotency_key: generateIdempotencyKey(),
      });
      setMessageBody("");
      setConversationState((current) =>
        current?.status === "ready" && current.organizationId === activeOrganizationId
          ? { ...current, messages: [...current.messages, createdMessage] }
          : current,
      );
      onMessageCreated?.();
    } catch (caught) {
      setMessageError(describeError(caught));
    } finally {
      setSubmittingMessage(false);
    }
  }

  return (
    <section className="communication-grid" aria-label="Deal conversation and fact review">
      <section className="card communication-card communication-card--transcript" aria-labelledby="conversation-heading">
        <div className="panel-head">
          <div>
            <span className="eyebrow">Deal messages</span>
            <h2 id="conversation-heading">Conversation</h2>
          </div>
          <span className="communication-index" aria-hidden="true">01 / LOG</span>
        </div>
        <p className="muted">Messages shown here are the ones your organization is allowed to read.</p>
        {organizationState.status === "loading" ? (
          <p role="status">Loading your organization access…</p>
        ) : organizationState.status === "error" ? (
          <p className="form-error" role="alert">{organizationState.message}</p>
        ) : partyOrganizations.length === 0 ? (
          <p className="empty-state">Your account has no active membership in either deal organization.</p>
        ) : (
          <>
            {partyOrganizations.length > 1 ? (
              <div className="field communication-context">
                <label htmlFor={`conversation-organization-${deal.id}`}>Viewing as</label>
                <select
                  id={`conversation-organization-${deal.id}`}
                  value={selectedOrganizationId}
                  onChange={(event) => {
                    const nextOrgId = event.target.value;
                    setActionError(null);
                    setHighlightedMessageId(null);
                    setFactFilter("all");
                    setInternalSelectedOrgId(nextOrgId);
                    onOrganizationChange?.(nextOrgId);
                  }}
                >
                  <option value="">Choose an organization</option>
                  {partyOrganizations.map((organization) => (
                    <option key={organization.id} value={organization.id}>
                      {organization.legal_name} ({organizationRole(deal, organization.id)})
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <p className="hint communication-context">
                Viewing as {selectedOrganization?.legal_name} ({organizationRole(deal, activeOrganizationId)}).
              </p>
            )}
            {!activeOrganizationId ? (
              <p className="empty-state">Choose which organization you are acting for to load its conversation.</p>
            ) : conversationState?.organizationId !== activeOrganizationId || conversationState.dealId !== deal.id ||
              conversationState.status === "loading" ? (
              <p role="status">Loading conversation and facts…</p>
            ) : conversationState.status === "error" ? (
              <div role="alert">
                <p className="form-error">{conversationState.message}</p>
                <button type="button" className="button secondary communication-retry" onClick={retryConversation}>
                  Try again
                </button>
              </div>
            ) : (
              <>
                <ol className="message-list" aria-label="Conversation messages" tabIndex={0}>
                  {visibleMessages.length === 0 ? (
                    <li className="empty-state">No messages yet.</li>
                  ) : (
                    visibleMessages.map((message) => (
                      <li
                        key={message.id}
                        id={`deal-message-${message.id}`}
                        className={`message-entry message-entry--${message.source_type.toLowerCase()}${highlightedMessageId === message.id ? " message-entry--source-linked" : ""}`}
                      >
                        <div className="communication-meta">
                          <span>
                            {message.source_type === "AGENT"
                              ? `SyncAlly agent${message.author_agent_id ? ` · ${message.author_agent_id}` : ""}`
                              : `Deal participant${message.author_user_id ? ` · ${message.author_user_id.slice(0, 8)}` : ""}`}
                          </span>
                          <time dateTime={message.created_at}>{formatTimestamp(message.created_at)}</time>
                        </div>
                        <p className="message-body">{message.body}</p>
                        <div className="communication-badges">
                          <span className={`badge badge--${message.visibility.toLowerCase()}`}>
                            {readable(message.visibility)}
                          </span>
                        </div>
                      </li>
                    ))
                  )}
                </ol>

                <form
                  className="message-composer"
                  aria-label="Post a deal message"
                  onSubmit={(event) => void handleSendMessage(event)}
                >
                  <div className="field">
                    <label htmlFor="deal-message-input">Post a message</label>
                    <textarea
                      id="deal-message-input"
                      name="message"
                      value={messageBody}
                      onChange={(event) => setMessageBody(event.target.value)}
                      placeholder="Introduce trade terms (e.g. 500 units at USD 45, deliver to Toronto)..."
                      rows={3}
                      maxLength={8000}
                      disabled={submittingMessage}
                      required
                    />
                  </div>
                  <div className="message-composer__controls">
                    <div
                      className="message-composer__visibility"
                      role="radiogroup"
                      aria-label="Message visibility"
                    >
                      <div className="communication-meta">
                        <span>
                          {message.source_type === "AGENT"
                            ? `SyncAlly agent${message.author_agent_id ? ` · ${message.author_agent_id}` : ""}`
                            : `Deal participant${message.author_user_id ? ` · ${message.author_user_id.slice(0, 8)}` : ""}`}
                        </span>
                        <time dateTime={message.created_at}>{formatTimestamp(message.created_at)}</time>
                      </div>
                      <p className="message-body">{message.body}</p>
                      <div className="communication-badges">
                        <span className={`badge badge--${message.visibility.toLowerCase()}`}>
                          <span aria-hidden="true">{message.visibility === "PRIVATE" ? "\u{1F512}" : "\u{1F310}"} </span>
                          {message.visibility === "PRIVATE" ? "Private" : "Shareable"}
                        </span>
                      </div>
                    </li>
                  ))
                )}
              </ol>
                      <label className="radio-label">
                        <input
                          type="radio"
                          name={`message-visibility-${deal.id}`}
                          value="SHAREABLE"
                          checked={messageVisibility === "SHAREABLE"}
                          onChange={() => setMessageVisibility("SHAREABLE")}
                          disabled={submittingMessage}
                        />
                        <span>Shareable</span>
                      </label>
                      <label className="radio-label">
                        <input
                          type="radio"
                          name={`message-visibility-${deal.id}`}
                          value="PRIVATE"
                          checked={messageVisibility === "PRIVATE"}
                          onChange={() => setMessageVisibility("PRIVATE")}
                          disabled={submittingMessage}
                        />
                        <span>Private</span>
                      </label>
                    </div>
                    <button
                      type="submit"
                      className="button button--compact"
                      disabled={submittingMessage || !messageBody.trim()}
                    >
                      {submittingMessage ? "Sending…" : "Send message"}
                    </button>
                  </div>
                  {messageError ? (
                    <p className="form-error" role="alert">
                      {messageError}
                    </p>
                  ) : null}
                </form>
              </>
            )}
            {currentConversation && selectedOrganization ? (
              <MessageComposer key={`${deal.id}:${activeOrganizationId}`}
                deal={deal} organization={selectedOrganization} onSent={appendMessage} />
            ) : null}
          </>
        )}
      </section>

      <section className="card communication-card communication-card--facts" aria-labelledby="fact-review-heading">
        <div className="panel-head">
          <div>
            <span className="eyebrow">Extracted details</span>
            <h2 id="fact-review-heading">Fact review</h2>
          </div>
          <span className="communication-index" aria-hidden="true">02 / LEDGER</span>
        </div>
        <p className="muted">
          Extracted facts are suggestions. Confirming one records your review; it does not approve the deal.
        </p>
        {currentConversation ? (
          <div className="review-metrics" role="group" aria-label="Filter facts for this organization">
            <button
              type="button"
              className="review-metric"
              aria-pressed={factFilter === "all"}
              onClick={() => setFactFilter("all")}
            >
              <strong className="review-metric__number">{String(visibleFacts.length).padStart(2, "0")}</strong>
              <span className="review-metric__label">all facts</span>
            </button>
            <button
              type="button"
              className="review-metric review-metric--open"
              aria-pressed={factFilter === "needs-review"}
              onClick={() => setFactFilter("needs-review")}
            >
              <strong className="review-metric__number">{String(factsAwaitingReview).padStart(2, "0")}</strong>
              <span className="review-metric__label">needs review</span>
            </button>
            <button
              type="button"
              className="review-metric"
              aria-pressed={factFilter === "confirmed"}
              onClick={() => setFactFilter("confirmed")}
            >
              <strong className="review-metric__number">{String(confirmedFacts).padStart(2, "0")}</strong>
              <span className="review-metric__label">confirmed</span>
            </button>
            <button
              type="button"
              className="review-metric"
              aria-pressed={factFilter === "private"}
              onClick={() => setFactFilter("private")}
            >
              <strong className="review-metric__number">{String(privateFacts).padStart(2, "0")}</strong>
              <span className="review-metric__label">private here</span>
            </button>
          </div>
        ) : null}
        {organizationState.status === "loading" ? (
          <p role="status">Loading your organization access…</p>
        ) : organizationState.status === "error" ? null : partyOrganizations.length === 0 ? (
          <p className="empty-state">No deal organization is available for your account.</p>
        ) : !activeOrganizationId ? (
          <p className="empty-state">Choose an organization above to load its facts.</p>
        ) : conversationState?.organizationId !== activeOrganizationId || conversationState.dealId !== deal.id ||
          conversationState.status === "loading" ? (
          <p role="status">Loading conversation and facts…</p>
        ) : conversationState.status === "error" ? (
          <p className="muted">Facts could not be loaded. Use the retry button in Conversation.</p>
        ) : visibleFacts.length === 0 ? (
          <p className="empty-state">No facts are available for this organization yet.</p>
        ) : filteredFacts.length === 0 ? (
          <p className="empty-state">No facts match this view for the selected organization.</p>
        ) : (
          <ul className="fact-list" aria-label="Deal facts" tabIndex={0}>
            {filteredFacts.map((fact) => {
              const isOwner = fact.owner_organization_id === activeOrganizationId;
              const canReview =
                isOwner &&
                REVIEWABLE_STATUSES.has(fact.status);
              const sourceMessageId = fact.source_message_id;
              const sourceMessageIndex = visibleMessages.findIndex(
                (message) => message.id === sourceMessageId,
              );
              const sourceMessage = sourceMessageIndex >= 0 ? visibleMessages[sourceMessageIndex] : null;
              return (
                <li key={fact.id}>
                  <article className="fact-ticket" aria-label={`${fact.field}: ${fact.typed_value}`}>
                    <div className="communication-meta">
                      <strong>{fact.field}</strong>
                      <span>{organizationRole(deal, fact.owner_organization_id)}-owned</span>
                    </div>
                    <p className="fact-value">
                      {fact.typed_value}{fact.currency_or_unit ? ` ${fact.currency_or_unit}` : ""}
                    </p>
                    <div className="communication-badges">
                      <span className={`badge badge--${fact.visibility.toLowerCase()}`}>
                        {fact.visibility === "PRIVATE"
                          ? "🔒 Private to your org"
                          : "🌐 Shared with counterparty"}
                      </span>
                      {isOwner ? (
                        <button
                          type="button"
                          className="button secondary button--compact"
                          disabled={pendingFactId !== null || pendingVisibilityFactId !== null}
                          onClick={() => void toggleFactVisibility(fact)}
                        >
                          {pendingVisibilityFactId === fact.id
                            ? "Updating…"
                            : fact.visibility === "PRIVATE"
                              ? "Make Shareable"
                              : "Make Private"}
                        </button>
                      ) : null}
                      <span className={`badge badge--status-${fact.status.toLowerCase()}`}>
                        {readable(fact.status)}
                        {fact.status === "EXTRACTED" ? " · unconfirmed" : ""}
                      </span>
                      <span className="badge badge--kind">{readable(fact.kind)}</span>
                    </div>
                    {fact.source_span ? (
                      <div className="fact-source">
                        <span className="fact-source__label">SOURCE EXCERPT</span>
                        {sourceMessage ? (
                          <button
                            type="button"
                            className="fact-source__trace"
                            aria-pressed={highlightedMessageId === sourceMessage.id}
                            onClick={() => traceSourceMessage(sourceMessage.id)}
                          >
                            Trace to message {String(sourceMessageIndex + 1).padStart(2, "0")}
                            <span aria-hidden="true"> ↗</span>
                          </button>
                        ) : null}
                        <blockquote className="fact-source__quote">“{fact.source_span}”</blockquote>
                      </div>
                    ) : null}
                    {canReview ? (
                      <div className="fact-actions" aria-label={`Review ${fact.field}`}>
                        <button
                          type="button"
                          className="button button--compact"
                          disabled={pendingFactId !== null || pendingVisibilityFactId !== null}
                          onClick={() => void reviewFact(fact, "confirm")}
                        >
                          {pendingFactId === fact.id ? "Saving…" : "Confirm"}
                        </button>
                        <button
                          type="button"
                          className="button secondary button--compact"
                          disabled={pendingFactId !== null || pendingVisibilityFactId !== null}
                          onClick={() => void reviewFact(fact, "reject")}
                        >
                          Reject
                        </button>
                        {fact.status === "EXTRACTED" ? (
                          <button
                            type="button"
                            className="button secondary button--compact"
                            disabled={pendingFactId !== null || pendingVisibilityFactId !== null}
                            onClick={() => void reviewFact(fact, "clarify")}
                          >
                            Ask for clarification
                          </button>
                        ) : null}
                      </div>
                    ) : null}
                    {actionError?.factId === fact.id ? (
                      <p className="form-error fact-error" role="alert">{actionError.message}</p>
                    ) : null}
                  </article>
                </li>
              );
            })}
          </ul>
        )}
      </section>
      {currentConversation ? (
        <AISuggestionReview
          key={`${deal.id}:${activeOrganizationId}`}
          dealId={deal.id}
          organizationId={activeOrganizationId}
          facts={currentConversation.facts}
          onTraceSource={traceSourceMessage}
          onFactAdded={addSuggestedFact}
          onFactUpdated={updateSuggestedFact}
          onFactCorrected={replaceSuggestedFact}
          onAgreementCreated={onAgreementCreated}
        />
      ) : null}
    </section>
  );
}
