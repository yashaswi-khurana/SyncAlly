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
- A small LangGraph proposal flow checks required trade fields when no source
  messages are available. Partial saved facts must not block a draft grounded in
  messages; the provider and local validators own that decision. Missing facts
  without messages return deterministic clarification guidance without egress.
  The graph has no checkpointer: each
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
| `max_attempts` | 2 (OpenAI), 1 (Gemini) | Transient retry attempts |
| `timeout_seconds` | 25 seconds (OpenAI), 90 seconds (Gemini) | Elapsed deadline cancels transport and response streaming |
| `backoff_seconds` | 0.5 | Delay between retry attempts |
| Remote budget | 50.5 seconds (OpenAI), 90 seconds (Gemini) | Below the fact/proposal frontend's 180-second deadline |
| Request/response | 128 KiB each | Whole UTF-8 request; streamed response checked before buffering |
| Output tokens | 4096 (OpenAI), 8192 (Gemini) | No truncation accepted; completion must finish normally |
| Fact/citation count | 100 | Strict bounded wrapper |

Network timeouts/errors, 429, and 5xx are transient except `insufficient_quota`,
which is permanent. Authentication/authorization, refusal, unsupported response,
malformed/duplicate-key/nonfinite JSON, invalid schema/version/domain contract,
oversize output, bad citations, and insufficient proposal context do not trigger
transient retries or offline fallback. Gemini may repair a parsed but invalid
fact/proposal response once within the original elapsed deadline, applying the
same validators again. NVIDIA may re-evaluate a proposal once within its original
deadline after invalid output or an insufficient-context response; the repair
prompt distinguishes required terms from an optional delivery date, and the same
validators run on the result. A second insufficient-context response remains a
terminal failure. Explicit insufficient context does not trigger Gemini repair.
Clients/responses close on success, failure, and elapsed cancellation.
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
Invalid currency evidence produces no candidates or draft and no database writes;
it cannot trigger offline fallback. Gemini's bounded repair must provide new,
valid evidence before any result is accepted.
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
Candidate deduplication includes currency/unit as well as owner, message, field,
and value: equal numeric values in different currencies or count units must not
collapse into one fact. Explicit code-plus-symbol prices such as `CAD $12 each`
pass both the remote validator and the shared candidate binding contract.
Gemini thought parts are excluded from answer JSON; they are never facts or
logged reasoning.

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

The existing `httpx.MockTransport` coverage exercises both adapters, including
Gemini structured requests, bounded repair, token-limit rejection, and thought
separation, plus common privacy, grounding, parsing, size-limit, retry and
provenance behavior. These are mocked contract checks, not production certification.

## Production rollout decisions

Keep the modular monolith and current provider port. Deterministic validation,
ranking, authorization, money calculations, and commercial state transitions
must stay ordinary code, not model decisions. A general autonomous agent, vector
database, prompt framework, or another orchestration service is not required for
these bounded use cases.

Release in independently reviewable slices:

1. **Boundary correctness:** preserve typed provider output, exact citations,
   private egress policy, currency/unit identity, bounded calls, and explicit
   rejection. Exercise malformed output, outage, and duplicate extraction as
   well as the happy path.
2. **Genuine sourcing:** restore evaluation only over persisted offers with
   explicit unknown values, compatible units and currencies, and authorized
   buyer context. Label actual provider execution separately from deterministic
   ranking. Never promote missing requirements to inferred quantity, price,
   currency, destination, or payment commitments.
3. **Measured production gate:** evaluate the configured model against reviewed,
   consented examples before rollout. Require zero unauthorized-data disclosures
   and zero accepted unsupported commercial values in the release fixture set.
   Track extraction acceptance, empty/clarification outcomes, correction rate,
   p50/p95 latency, timeout/429 rates, and cost per successful reviewed result.
   Set product SLOs and spend limits from this baseline, not model advertising.
4. **Operational scale:** load-test API worker occupancy during provider outages;
   add bounded per-organization admission and explicit overload responses before
   broad rollout. Move calls to durable background jobs only if measured latency
   requires resumable progress. Keep manual fact entry available during outages.

Do not log raw prompts, responses, quotes, credentials, or chain-of-thought.
Use existing correlation IDs and allowlisted failure stages for diagnostics.
Persist durable per-result model/prompt-version provenance only with a defined
retention and privacy policy; current invocation provenance is not an audit trail.
Pin and evaluate a model change before promoting it. Roll back through operator
provider configuration; never silently replace remote AI with a demo result.
Database-backed supplier catalogue ownership and supplier verification remain
separate release requirements: an AI-generated ranking cannot certify a supplier.

### Sourcing implementation boundary

The backend `/sourcing/interpret` endpoint supports natural-language
interpretation using the configured remote transport; strict field
contracts and quoted source evidence are validated locally. Unknown required
fields cause clarification, not speculative commercial defaults. Structured
user input is explicitly labeled separately. Provider failures are surfaced
without offline substitution for sourcing.

Scored sourcing comparison, gap analysis, evaluation and inquiry drafting remain
unavailable because persisted offers lack the data and unknown-value semantics
needed for reliable scoring. The sourcing page can interpret requirements for
human review, search active marketplace listings, compare up to three offers'
stated details without scores, and start a deal from a selected offer. Search
remains usable when AI is unavailable. Unstructured seller terms require
confirmation; marketplace offers are not supplier verification. Bundled data is
restricted to direct development/test service callers and test fixtures.

Sourcing transmits the prompt and controls the user submits for this purpose; it
does not retrieve organization-private deal data. Operator remote-egress and
provider-retention approval remain required. Deal-context private allowlisting
does not authorize or prohibit text explicitly submitted in this separate flow.
The `/deals` opening-request analyzer remains a distinct consumer of the provider
port and now reuses grounded remote fact extraction from main.

## Verification receipt

- Focused backend checks: **136 passed**, including **103 subtests** covering
  scoped evidence, both mocked provider transports, commercial claim roles,
  negation/cropped quotes, missing fields, failures, and inquiry authority.
- Frontend checks: **135 passed** in the combined sourcing/deal-AI/client run;
  the remaining inquiry case passed separately after correcting unsupported
  test matchers. Its single-case rerun deselected the other 22 cases in that
  file. This is cumulative focused coverage, not a fresh full-suite pass.
- Changed-file Ruff and ESLint checks, TypeScript checking, the production Vite
  build, and whitespace validation passed for the checked snapshot. Backend
  checks retain four framework deprecation warnings; the build retains a
  large-chunk warning.
- A final sourcing lifecycle fix releases the authentication read transaction
  before provider HTTP, following the existing deal-AI route pattern. Its
  isolated SQLite/MockTransport regression passed separately for both
  interpretation and evaluation after those checks; evaluation is now disabled.
- Subsequent sourcing checks passed 148 backend tests and 62 frontend tests.
  Some legacy backend tests explicitly override the availability gate to exercise
  isolated demo logic; they do not prove the public sourcing workflow is available.
- Opening analysis hardening passed 77 focused backend tests and two subtests.
  The separate opening end-to-end suite still has 13 pre-existing failures at deal
  creation authorization.
- No live provider calls, production deployment, private-data egress, migrations,
  or payment execution were used for verification. Model quality, account
  retention, operational load, and supplier verification remain release gates.

## Production readiness: open gates

The checked-in deployment layouts are not production-ready: the Hostless layout
stores Temporal state in ephemeral `/tmp`, uses expiring free PostgreSQL, and
runs one small replica; the OCI layout has a single VM as a failure point. Before
customer rollout, operators must provision durable database and Temporal storage,
test backup and restore, establish a recovery plan, and validate capacity and
availability for the intended workload.

The deployment health check uses `/health` rather than database readiness, and
the checked-in Compose workers have no health checks. Add dependency readiness,
worker monitoring and alerts, and a deployment pipeline with automated checks
before relying on these layouts. No checked-in CI workflow was found during this
review.

The marketplace RFQ search currently filters to organizations the actor can
manage. Confirm the intended counterparty discovery and authorization policy
before changing that behavior or promising cross-organization discovery.
PayPal Sandbox is an explicitly accepted exception for this rollout, not evidence
of live-payment readiness.
