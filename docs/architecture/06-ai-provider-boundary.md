# AI Provider Boundary

**Status:** Provider boundary implemented; real provider selection deliberately deferred
**Scope:** `backend/src/syncally/application/ai.py` and `backend/src/syncally/infrastructure/ai/`

This document records the S4-03 boundary that lets SyncAlly call an AI service
without coupling business rules to a provider SDK. It also records the current
decision to **not** select a real provider until the team makes and documents
that choice.

## Decision

- Define one small provider port now, and ship a deterministic offline fake so
  the normal test suite runs with no network and no API key.
- Do **not** add a provider SDK or credentials until the team records a provider
  choice (see below). The application depends only on the port.
- Business and domain code never import a provider SDK. Adapters translate
  provider output into the versioned S4-01 contracts.
- Do **not** add LangGraph yet. The selected flow is a single bounded, typed
  call per request; a graph is introduced only when a flow needs multi-step
  branching or state that typed functions cannot express.

## Contract

`AISuggestionProvider` (`application/ai.py`) has two methods:

- `extract_facts(FactExtractionRequest, *, timeout_seconds) -> tuple[ExtractedFact, ...]`
- `draft_proposal(ProposalDraftRequest, *, timeout_seconds) -> ProposedTerms`

Both requests carry only the `AiContext` selected by S4-02, so a provider only
ever sees the acting organization's own private data plus explicitly shareable
data. Adapters parse raw provider output with the S4-01 schemas using
`parse_extracted_facts` and `parse_proposed_terms`; malformed output raises
`AIPermanentError` rather than being partially trusted.

The `extract_facts` use case grounds every suggested fact against the same
authorized messages that were sent to the provider. A fact that cites an
unknown, unauthorized, or fabricated source is rejected, so a provider cannot
smuggle in the counterparty's private context or invent a value. Invalid or
ungrounded output produces an `INVALID` `FactExtractionResult` with no
candidates; it is never auto-confirmed.

## Resilience bounds

`AIRetryPolicy` fixes the limits for every call:

| Limit | Default | Meaning |
| --- | --- | --- |
| `max_attempts` | 3 | Maximum calls for one request |
| `timeout_seconds` | 30 | Per-call deadline forwarded to the adapter |
| `backoff_seconds` | 0.5 | Delay between retry attempts |

Only `AITransientError` (timeout or temporary outage) is retried. Permanent
errors and unexpected exceptions propagate immediately. Exhausted transient
retries surface a single `AITransientError` so a caller or worker can apply its
own later, still-bounded retry.

## Credentials

- Credentials belong to a concrete adapter's own configuration. They are never
  placed on a request, on `AiContext`, on a result, in Temporal workflow input,
  or in logs.
- Adapters raise errors with generic messages; parse and validation issues omit
  provider output, which may echo private context.
- The fake provider needs no credential and makes no network call.

## Authority

Everything this boundary produces is an unreviewed suggestion. Nothing here
confirms a fact, approves terms, commits an agreement, or starts a payment.

## Provider selection (deferred)

No real provider is chosen in this story. When the team records the choice,
that decision must name the provider, the pinned SDK, where credentials come
from, the timeout/retry tuning, the data-retention and redaction policy, and the
evaluation approach. Exactly one adapter is added at that point, behind the
existing port, and the fake remains available for offline tests.
