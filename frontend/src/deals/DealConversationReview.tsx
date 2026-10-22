import { useEffect, useState } from "react";

import {
  ApiError,
  listDealFacts,
  listDealMessages,
  listOrganizations,
  reviewDealFact,
} from "../api/client";
import type {
  Deal,
  DealFact,
  DealMessage,
  FactReviewAction,
  Organization,
} from "../api/types";
import AISuggestionReview from "./AISuggestionReview";

type OrganizationState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; organizations: Organization[] };

type ConversationState =
  | { status: "loading"; organizationId: string }
  | { status: "error"; organizationId: string; message: string }
  | {
      status: "ready";
      organizationId: string;
      messages: DealMessage[];
      facts: DealFact[];
    };

interface DealConversationReviewProps {
  deal: Deal;
  onAgreementCreated?: () => void;
}

type FactFilter = "all" | "needs-review" | "confirmed" | "private";

const REVIEWABLE_STATUSES = new Set<DealFact["status"]>([
  "EXTRACTED",
  "NEEDS_CLARIFICATION",
]);

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

export default function DealConversationReview({
  deal,
  onAgreementCreated = () => {},
}: DealConversationReviewProps) {
  const [organizationState, setOrganizationState] = useState<OrganizationState>({
    status: "loading",
  });
  const [selectedOrganizationId, setSelectedOrganizationId] = useState("");
  const [conversationState, setConversationState] = useState<ConversationState | null>(null);
  const [reloadCount, setReloadCount] = useState(0);
  const [pendingFactId, setPendingFactId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<{ factId: string; message: string } | null>(null);
  const [highlightedMessageId, setHighlightedMessageId] = useState<string | null>(null);
  const [factFilter, setFactFilter] = useState<FactFilter>("all");

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
        setSelectedOrganizationId(partyOrganizations.length === 1 ? partyOrganizations[0].id : "");
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setOrganizationState({ status: "error", message: describeError(caught) });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [deal.buyer_organization_id, deal.seller_organization_id]);

  const partyOrganizations = organizationState.status === "ready" ? organizationState.organizations : [];
  const selectedOrganization = partyOrganizations.find(
    (organization) => organization.id === selectedOrganizationId,
  );
  const activeOrganizationId = selectedOrganization?.id ?? "";
  const currentConversation =
    conversationState?.status === "ready" && conversationState.organizationId === activeOrganizationId
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
            message: describeError(caught),
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [activeOrganizationId, deal.id, reloadCount]);

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
        current?.status === "ready" && current.organizationId === activeOrganizationId
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

  function addSuggestedFact(fact: DealFact) {
    setConversationState((current) => current?.status === "ready" && current.organizationId === activeOrganizationId
      ? { ...current, facts: [...current.facts.filter((item) => item.id !== fact.id), fact] }
      : current);
  }

  function updateSuggestedFact(fact: DealFact) {
    setConversationState((current) => current?.status === "ready" && current.organizationId === activeOrganizationId
      ? { ...current, facts: current.facts.map((item) => item.id === fact.id ? fact : item) }
      : current);
  }

  function replaceSuggestedFact(replaced: DealFact, corrected: DealFact) {
    setConversationState((current) => current?.status === "ready" && current.organizationId === activeOrganizationId
      ? {
          ...current,
          facts: [...current.facts.map((item) => item.id === replaced.id ? replaced : item), corrected],
        }
      : current);
  }

  return (
    <section className="communication-grid" aria-label="Deal conversation and fact review">
      <section className="card communication-card" aria-labelledby="conversation-heading">
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
                    setActionError(null);
                    setHighlightedMessageId(null);
                    setFactFilter("all");
                    setSelectedOrganizationId(event.target.value);
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
            ) : conversationState?.organizationId !== activeOrganizationId ||
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
              <ol className="message-list" aria-label="Conversation messages">
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
            )}
          </>
        )}
      </section>

      <section className="card communication-card" aria-labelledby="fact-review-heading">
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
        ) : conversationState?.organizationId !== activeOrganizationId ||
          conversationState.status === "loading" ? (
          <p role="status">Loading conversation and facts…</p>
        ) : conversationState.status === "error" ? (
          <p className="muted">Facts could not be loaded. Use the retry button in Conversation.</p>
        ) : visibleFacts.length === 0 ? (
          <p className="empty-state">No facts are available for this organization yet.</p>
        ) : filteredFacts.length === 0 ? (
          <p className="empty-state">No facts match this view for the selected organization.</p>
        ) : (
          <ul className="fact-list" aria-label="Deal facts">
            {filteredFacts.map((fact) => {
              const canReview =
                fact.owner_organization_id === activeOrganizationId &&
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
                        {readable(fact.visibility)}
                      </span>
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
                          disabled={pendingFactId !== null}
                          onClick={() => void reviewFact(fact, "confirm")}
                        >
                          {pendingFactId === fact.id ? "Saving…" : "Confirm"}
                        </button>
                        <button
                          type="button"
                          className="button secondary button--compact"
                          disabled={pendingFactId !== null}
                          onClick={() => void reviewFact(fact, "reject")}
                        >
                          Reject
                        </button>
                        {fact.status === "EXTRACTED" ? (
                          <button
                            type="button"
                            className="button secondary button--compact"
                            disabled={pendingFactId !== null}
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
