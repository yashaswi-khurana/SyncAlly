# AI Provider Boundary

**Status:** OpenAI and Gemini HTTP boundaries implemented; provider transports require live evaluation
**Scope:** `backend/src/syncally/application/ai.py` and `backend/src/syncally/infrastructure/ai/`

This document records the S4-03/F2 boundary. OpenAI Chat Completions and Google
Gemini GenerateContent use HTTP adapters behind the existing port, without provider
SDKs. Gemini support has not been live-evaluated. Account/model availability, live
output quality, and provider retention configuration must be verified by operators.

## Decision

- Keep the existing provider port and deterministic offline behavior; tests need
  neither network nor credentials. `AI_PROVIDER=offline` is the default.
- Promote the existing `httpx>=0.27,<1.0` dependency from dev to runtime. Fixed
  OpenAI and Gemini HTTPS endpoints have TLS verification enabled; redirects,
  environment proxies, tools, URL fetching, and arbitrary endpoint configuration
  are disabled.
- Business and domain code never import a provider SDK. Adapters translate
  provider output into the versioned S4-01 contracts.
- A small LangGraph proposal flow checks required trade fields before routing
  to the existing bounded provider call. Incomplete context returns deterministic
  clarification guidance without egress. The graph has no checkpointer: each
  request reloads authorized context from PostgreSQL, which remains the source
  of truth.

## Contract

`AISuggestionProvider` (`application/ai.py`) has two methods:

- `extract_facts(FactExtractionRequest, *, timeout_seconds) -> tuple[ExtractedFact, ...]`
- `draft_proposal(ProposalDraftRequest, *, timeout_seconds) -> ProposedTerms`

Both requests carry the `AiContext` selected after database-backed authorization.
Remote mode further filters both messages and constraints before HTTP. By default
only SHAREABLE data leaves the process. Private egress requires both
`AI_REMOTE_ALLOW_PRIVATE=true` and the selected organization's UUID in the trusted
`AI_REMOTE_PRIVATE_ORGANIZATION_IDS` allowlist (JSON array, default `[]`). This
allowlist is operator policy, not membership authority. A different organization's
allowlisting cannot enable private egress for the selected side. Counterparty
private data never enters the authorized context. Offline privacy behavior is unchanged.

Remote bodies contain only message IDs/text and permitted trade-field values and
currency/unit, not actor/org IDs, author metadata, timestamps, constraint IDs,
source URLs, rejected/superseded/clarification terms, or unrelated private limits.
Adapters parse raw provider output with the S4-01 schemas using
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
| `max_attempts` | 2 | Maximum HTTP calls for one request; one per attempt |
| `timeout_seconds` | 10 | Elapsed deadline cancels transport and response streaming |
| `backoff_seconds` | 0.5 | Delay between retry attempts |
| Remote budget | 20.5 seconds | Outer elapsed retry budget; below frontend's 30 seconds |
| Request/response | 128 KiB each | Whole UTF-8 request; streamed response checked before buffering |
| Output tokens | 4096 | No truncation accepted; finish reason must be `stop` |
| Fact/citation count | 100 | Strict bounded wrapper |

Network timeouts/errors, 429, and 5xx are transient except `insufficient_quota`,
which is permanent. Authentication/authorization, refusal, unsupported response,
malformed/duplicate-key/nonfinite JSON, invalid schema/version/domain contract,
oversize output, bad citations, and insufficient proposal context never retry or
fall back. Clients/responses close on success, failure, and elapsed cancellation.
No request, response, prompt, credential, or transport exception text is logged.

Strict JSON schemas require every key, including nullable optional values, with
`additionalProperties=false` at every object. Ordinary code validates again:
facts must ground against exact transmitted messages; each populated proposal
field requires a locally grounded citation or an exact transmitted term citation.
Three-letter currency codes, decimal bounds, canonical dates, and plain decimal
strings are enforced.
Missing required terms must return an insufficient-context failure, not invented defaults.

Remote monetary facts and message-backed proposal price citations require an
explicit three-letter currency code adjacent to the exact amount in the exact
authorized, transmitted quote. A symbol, currency name, or currency evidence
elsewhere in context cannot establish a code. The accepted strict policy requires
one monetary amount in the quote and its original message clause, associated
with `unit price`, `per unit`, `/unit`, `each`, or a quantity-at-price form such
as `12 boxes at INR 2.50`. Budget, payment, total, deposit, balance, and subtotal
clauses cannot authorize a unit price. Compound monetary quotes are rejected
rather than interpreted: `Budget INR 2.50; actual unit price $2.50.` is invalid.
Cropping that quote to `INR 2.50` or `2.50` cannot hide its original budget role;
repeated quote occurrences must all satisfy the policy. An unambiguous `actual
unit price INR 2.50` or `INR 2.50 per unit` citation remains valid and is
preserved verbatim. These are conservative accepted forms, not a universal
natural-language grounding guarantee. Recognized conflicting currency codes,
names, or symbols anywhere in the cited source message conservatively invalidate
that monetary evidence, even when the quote omits the contradictory qualifier.
No currency conversion is allowed. An exact authorized transmitted price term
with the same explicit currency code remains valid evidence for a proposal.
Invalid currency evidence is permanent: one HTTP
attempt, no offline fallback, no candidates or draft, and no database writes.
This stricter remote policy does not change the permissive offline demo helpers.

## Credentials

- Credentials belong to a concrete adapter's own configuration. They are never
  placed on a request, on `AiContext`, on a result, in Temporal workflow input,
  or in logs.
- Adapters raise errors with generic messages; parse and validation issues omit
  provider output, which may echo private context.
- The fake provider needs no credential and makes no network call.

## Operator selection

- `AI_PROVIDER=offline`: preserves local development/test behavior and the generic
  unconfigured 503 outside those environments. A stray key cannot enable remote mode.
- `AI_PROVIDER=openai`: requires `AI_REMOTE_EGRESS_ENABLED=true`, a nonblank
  `OPENAI_MODEL`, and `OPENAI_API_KEY` loaded as `SecretStr` from environment/secret store.
- `AI_PROVIDER=gemini`: requires `AI_REMOTE_EGRESS_ENABLED=true`, a nonblank
  `GEMINI_MODEL`, and `GOOGLE_API_KEY` loaded as `SecretStr` from environment/secret store.
- `AI_PROVIDER=openai_with_offline_fallback`: same egress/model requirements;
  missing credentials may fall back with `missing_credentials`. Only exhausted
  transient attempts may fall back with `transient_exhausted`. Transient fallback
  uses the same filtered context, not newly restored private context.
- `AI_PROVIDER=gemini_with_offline_fallback`: applies the same explicit fallback
  rules to the Gemini adapter.
- Disabled egress or missing model always gives generic configuration 503 and
  zero HTTP calls, even when fallback is selected.
- `OPENAI_MODEL` has no default. `gpt-4.1-mini` is a documentation example only;
  operators must verify support and availability for their account.

`store=false` opts out of completion storage; it does **not** promise zero retention
or disable provider abuse monitoring. Operators must approve provider contractual
retention/data handling before enabling any egress, especially private egress.
Google's Gemini free tier may use submitted prompts and responses to improve Google
products. Use paid Gemini service for deal data and verify the project billing tier
before configuring its key.

## Authority

Everything this boundary produces is an unreviewed suggestion. Nothing here
confirms a fact, approves terms, commits an agreement, or starts a payment.

HTTP runs after rollback, without a database transaction. The selected organization's
database membership is rechecked before HTTP and afterward before candidate
persistence or returning draft terms. Invalid output is never persisted.

## Provenance and evaluation

Facts/proposal responses add typed invocation-level `provenance`: actual provider,
selected mode, model (completion-envelope model when received), context scope,
and a safe fallback reason. The UI labels Offline, OpenAI, Offline fallback, or
Unknown (legacy). This is not per-fact history: deduplicated or old facts are not
backfilled. Provenance never enters reviewed terms or approval payloads. No
migration or durable provenance was added; B1-B4, Q1, F1a/F3 and migrations 0012-0014
are outside F2 and preserved.

The LangGraph graph only controls readiness and routing; grounding, retries,
provider selection, and validation remain in the existing application/provider
boundary. It cannot confirm facts, approve terms, or create agreements.

The existing `httpx.MockTransport` coverage exercises the OpenAI boundary and
common privacy, grounding, parsing, size-limit, retry and provenance behavior.
It does not exercise the new Gemini HTTP adapter. Gemini compiles but still needs
transport-level contract coverage and a live request using a paid Google AI project.
