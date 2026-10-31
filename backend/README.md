# SyncAlly backend

Python package for the HTTP API, application use cases, domain rules, adapters, and durable workflow processes.

## F11a explicit payment modes

`PAYMENT_MODE` defaults to `PAYPAL_SANDBOX`. `OFFLINE_DEMO` is accepted only with
`APP_ENV=development` or `test`. Configuration chooses new intents, never rewrites
payment history. The authorization transaction persists `provider`, immutable
`execution_mode`, and initial `reconciliation_source=NONE` with its outbox event.
The worker resolves each saved intent separately, including mixed-mode batches.
Missing Sandbox credentials, remote timeouts and unresolved legacy identity never
fall back to offline execution.

`GET /deals/{deal_id}/payments/preview` requires current seller access and a committed
agreement. Authorization accepts optional `expected_mode` as a stale-preview guard,
not a provider selector. A matching idempotent replay returns the original intent
and mode even after configuration changes; changed commands still conflict. Status
reads expose saved mode/source/version and an offline invoice reference, with no
offline or unresolved invoice URL. Browser redirects never prove payment.

For the persistent local demo, use the existing file-backed SQLite setup below and
set `PAYMENT_MODE=OFFLINE_DEMO` in the API and worker environments. Run both against
the exact same `DATABASE_URL`; bind the API to `127.0.0.1`. Setup/reset does not
dispatch payment. After human approval, commit and seller authorization, run the
payment worker to issue a deterministic `OFFLINE-<intent UUID>` reference. It reaches
unpaid `SENT`, with no HTTP, PayPal, SMTP or automatic paid transition.

The protected `POST /dev/payments/{intent_id}/simulate-reconciliation` requires an
active seeded demo administrator, the matching marked demo agreement and offline
intent, an idempotency key, `expected_version`, explicit `PENDING`, `PARTIALLY_PAID`
or `PAID` outcome, and decimal-string `paid_amount`. It returns `202` with queued
event identity, not paid truth. The worker rechecks scope, version, event identity
and lease before atomically saving simulation evidence, audit and completion.
Successful evidence is `OFFLINE_DEMO` with `SIMULATION/OFFLINE_DEMO` audit identity;
rejected observations retain payment truth and receive a needs-action audit.
PayPal webhook verification remains separate and cannot associate offline intents.

`python -m syncally.cli.simulate_deal_flow --offline --no-color` explicitly uses an
isolated SQLite harness and the shared offline adapter; it does not replace an
unreachable API automatically or report invented invoice links. This isolated
exercise is not persistent same-database verification and is not PayPal evidence.
The explicit `--ci` command and Python CI hook select this same offline harness.

Migration `0017_explicit_payment_modes` follows preserved migrations 0012-0016.
Existing PayPal routing becomes Sandbox, but historical evidence remains
`LEGACY_UNVERIFIED`; unknown providers remain `LEGACY_UNRESOLVED`. No historical
IDs, statuses, amounts or indexes are converted into demo history. See
[F11a rollout and verification limits](../docs/operations.md#f11a-explicit-payment-modes).

## F12 committed trade packs

`GET /deals/{deal_id}/documents/versions/{number}/trade-pack` requires query
`agreement_version_id` (UUID), `terms_hash` (64 lowercase hex characters), and
`organization_id` (selected deal party). `format=zip` is the default; `format=html`
returns the same self-contained print-ready HTML. Active database user, organization,
and membership are rechecked. The exact historical version must remain COMMITTED,
match the supplied identity/hash and deal parties, and have both party approvals
for that exact version and hash. There is no latest-version substitution.

ZIP entries, in fixed order, are `trade-pack.html`, `canonical-terms.json`, and
`manifest.json`. Canonical bytes are verified with SHA-256 against the stored hash;
the manifest records schema, immutable IDs, created/committed timestamps, counts,
and copied display-case terms. Fixed ZIP timestamps/permissions and no actor or
download timestamp make bytes identical for both parties. `_f6_evidence` is excluded
without resolving facts, messages or organization profiles. Unknown commitment
fields/schemas fail closed. All persisted items, shipments and payments are rendered,
including duplicates; current demo commitment/authoring restrictions are unchanged.

Every section is DRAFT / FOR REVIEW ONLY, not an invoice, signature, payment proof,
or compliance claim. Missing legal names, addresses, weight, packaging, banking,
tax/customs details and allocations are explicitly not recorded. User content is
HTML-escaped; no remote assets, scripts, links or user CSS are included. Attachments
use validated ASCII filenames, correct MIME, `no-store`, `nosniff` and restrictive CSP.
Display/canonical JSON is bounded to 2 MiB, decimal expansion is guarded, and total
uncompressed output is limited to 16 MiB before compression for either format. Oversize
returns 413 without truncation; inconsistent/unapproved versions return 409, missing
or forbidden versions return 404, and malformed/missing parameters return 422.

Exports are generated on demand with no database write, migration, audit, retained
copy or new retention policy. The legacy `/documents/commercial-draft` JSON/text
contract is unchanged. F6 owns the browser's viewed snapshot; the download panel
uses that same version UUID/number/hash and selected party, including read-only
history. Context changes abort and discard stale downloads and revoke object URLs.
Downloaded HTML is never injected into the app. No PDF/template framework, F10
collection authoring, service startup or external provider verification is included.
See the [F12 handoff and verification results](../docs/f12-trade-pack-handoff.md).

## F6 agreement history and comparison

`GET /deals/{deal_id}/agreements/history`, `/versions/{number}`, and
`/compare?before={number}&after={number}` read saved agreement snapshots. Each read
reauthorizes active database user/organization membership before exposing data;
`organization_id` selects a deal party and is required for dual-party members.
Missing and forbidden deals share a 404. The existing `/current` contract remains
compatible and accepts an optional party selector.

Snapshots include their distinct version ID/number, stored hash/status/timestamps,
and only that version's recorded approval rows. Approval rows are latest recorded
decisions, not an invented decision timeline. Historical reads never transition
state or create audits, outbox records, obligations or amendments. Comparisons
normalize copies through the existing canonical terms implementation, preserve
duplicate counts, consume exact matches first and leave ambiguous pairing as
additions/removals. No stable collection-entry identity is claimed.

Evidence uses the exact snapshot proposal, never latest facts. New snapshots freeze
references in existing JSON metadata, excluded from terms hashes. Tracing rechecks
current fact/source authorization and frozen visibility on every read; it returns
only a unique exact span from an unchanged source. Changed, missing, ambiguous and
legacy sources disable tracing without reconstructing provenance. References remain
unmapped to terms: they do not prove term grounding, manual entry or current fact
confirmation. Frozen-private references cannot be shared retroactively through history.
The UI keeps historical/comparison views read-only and clears stale source displays
on version, party, deal, comparison and reload changes. No migration or backfill is needed.

## F5 persisted human negotiation

`GET /deals/{deal_id}/negotiation` returns the latest proposal, bounded proposal/action
history, round limit, eligible actions and current candidate acknowledgement. `limit`
defaults to 100 (maximum 100); `offset` is bounded to 10,000. A dual-party member must
select `organization_id`; the selection never grants membership.

`POST /deals/{deal_id}/negotiation/{action}` supports `submit`, `counter`, `accept`,
`reject`, `supersede` and `expire`. Each command includes a UUID `command_id`,
`expected_deal_revision`, and `base` containing the exact latest proposal ID/hash/status
(null only before the first proposal). Submit/counter include reviewed `terms` and may
include a timezone-aware `expires_at` within 30 days and up to 100 distinct confirmed
fact ID/version references. There is no automatic expiry or scheduler.

The non-author counters, accepts as candidate or rejects; the author explicitly
supersedes; either party may expire an elapsed proposal. Terminal proposals stay in
history and later submissions name that exact base. Successful submissions/counters
count toward the persisted limit (five for new sessions, legacy limits unchanged).
Over-limit attempts durably escalate without partially superseding proposals/candidates.

Deal locking serializes negotiation with approval/commit. Pending candidate replacement
requires `supersede_current_candidate` with its exact ID/version number/hash/source proposal
ID. Replacement preserves old approvals as history, clears the current candidate and
returns to negotiating. Acceptance creates a new pending agreement with empty approvals,
even for equal terms hashes. It never approves, commits, creates obligations or pays.
Exact command replay returns its saved result only after fresh database authorization
and the F4 pending-state guard. Changed replay payloads and stale bases return 409;
missing/forbidden deals return the same 404; invalid/ambiguous party input returns 422.
Committed/closed deals cannot be changed through F5.

Migration `0016_persisted_negotiation_rounds` follows 0015 without rewriting 0012-0015.
Legacy snapshots, statuses, counts and limits remain legacy; missing evidence/history is
not fabricated. Ambiguous legacy chains are preserved and negotiation fails closed.
The legacy agreement-draft endpoints retain their schemas/replay behavior, but cannot
bypass human acceptance or candidate replacement. Evidence metadata is excluded from
terms hashes, stored as a snapshot, and reauthorized/redacted on reads.
See [F5 rollout and verification](../docs/operations.md#f5-persisted-human-negotiation).

## F2 AI configuration

`AI_PROVIDER` defaults to `offline`: deterministic suggestions in development/test,
and the existing generic unconfigured 503 elsewhere. An environment API key alone
never enables HTTP. To opt into the single OpenAI Chat Completions adapter, set:

```text
AI_PROVIDER=openai
AI_REMOTE_EGRESS_ENABLED=true
OPENAI_MODEL=gpt-4.1-mini
AI_REMOTE_ALLOW_PRIVATE=false
AI_REMOTE_PRIVATE_ORGANIZATION_IDS=[]
```

`OPENAI_MODEL` is required with no default; the example is not live-verified and
operators must verify their account's model support. Supply `OPENAI_API_KEY` through
the environment or secret store; it is loaded as `SecretStr`, never sent to the UI
or put into prompts. No real provider was called during implementation/evaluation.

`openai_with_offline_fallback` is an explicit alternative mode: missing credentials
can produce offline suggestions with a credential fallback reason; only exhausted
transient network/429/5xx failures allow transient fallback. Quota exhaustion,
authentication/refusal, invalid output, grounding failure and incomplete terms do
not fall back. Disabled egress or missing model gives generic configuration 503,
with zero HTTP calls even in fallback mode.

Private egress defaults off for both messages and constraints. It requires
`AI_REMOTE_ALLOW_PRIVATE=true` **and** the selected organization's UUID in the
operator-controlled JSON allowlist `AI_REMOTE_PRIVATE_ORGANIZATION_IDS`. Database
authorization still applies; the allowlist grants no membership. Otherwise only
shareable message IDs/text and permitted trade terms are transmitted. Offline
behavior retains the existing authorized private context.

The fixed HTTPS endpoint verifies TLS and disables redirects/proxies/tools/URL
fetching. `store=false` is not zero retention: approve OpenAI contractual retention
and abuse-monitoring policy before egress. Requests/responses are bounded to
128 KiB, output to 4096 tokens and 100 facts/citations. Two 10-second elapsed
attempts plus 0.5-second backoff fit below the frontend's 30-second timeout.
Oversized, truncated, duplicate-key, unsupported or ungrounded results are rejected,
never persisted. HTTP holds no DB transaction; selected membership is rechecked
afterward. The UI exposes invocation provider/mode/model/scope/fallback reason,
not fabricated per-fact history, and human review remains mandatory. See
[the boundary and mocked evaluation](../docs/architecture/06-ai-provider-boundary.md).
No migration is required for this additive, non-durable provenance.

The API exposes public health endpoints and protected deal reads. Protected requests use
HS256 bearer JWTs: the `sub` claim identifies the user, while active organization
memberships are loaded from the database for authorization. Organization or role claims
supplied by the browser are not trusted. Set `JWT_SECRET` to a cryptographically generated
secret containing at least 32 random bytes outside development/test, and optionally
`JWT_ISSUER` and `JWT_AUDIENCE`.
Access tokens expire after `ACCESS_TOKEN_TTL_MINUTES` (default 15 minutes).
Refresh tokens expire after `REFRESH_TOKEN_TTL_DAYS` (default 30 days).

Public self-registration is disabled. The local seed command prepares the buyer/seller
accounts, organizations, admin memberships, and the curated unapproved deal described below.
It is limited to development/test and preserves existing password hashes on setup and reset.
Missing passwords come from `BUYER_PASSWORD` / `SELLER_PASSWORD` environment variables or
secure, non-echoing `getpass` prompts, never generated default passwords.
The fixed demo emails are `buyer@syncally.demo` and `seller@syncally.demo`.
`POST /auth/login` accepts `{ "email": "...", "password": "..." }` and returns an access
token and refresh token for an active account. Invalid credentials and inactive or missing
accounts receive the same `401` response. `POST /auth/dev-login` is an optional shortcut for
the configured local development identity when `DEV_AUTH_USER_ID` and the matching
`X-Dev-User-Id` header are supplied.
After signing in, `POST /organizations` creates an organization and makes the caller its
first active admin. `GET /organizations` lists only the caller's active memberships.
For existing accounts, an organization admin can use
`POST /organizations/{organization_id}/members` with an existing active user's email to
add that account as a regular member. The endpoint does not create accounts or allow callers
to choose another user's role. The only in-app account provisioning currently available is
the trusted operator's seed command for the two fixed demo identities; users cannot claim an
email through public registration. A future invitation flow must verify the invited address
before granting membership.
Organization admins generate invitation links through
`POST /organizations/{organization_id}/invitations`. Set `PUBLIC_FRONTEND_URL` to the
frontend base URL; it defaults to `http://localhost:5173` only in development/test.
Every other environment requires an explicit HTTPS URL with a public host, for example
`https://app.syncally.trade` or `https://app.syncally.trade/portal` for a base-path deployment.
Trailing slashes are normalized; links append `/#/invite?token=<signed-token>` without
changing the token. Credentials, query strings, fragments, malformed URLs, controls,
backslashes, traversal and encoded path separators are rejected at startup. Nonlocal
environments also reject local/private IP literals and local hostnames. Request `Host`
and forwarded headers never determine the invitation destination.
Organization creation is limited to five active organizations per user by default. Set
`MAX_ORGANIZATIONS_PER_USER` to a positive integer to change the limit.
After signing in, `POST /deals` creates a draft deal. The request body names the
`buyer_organization_id` and `seller_organization_id`; the caller must have an active
membership in the buyer organization, while the seller may be any active organization.
Success returns `201` with the deal ID, both organization IDs, `DRAFT` status, and version.
`GET /deals` lists every deal the caller participates in, newest first, each with a
`viewer_role` of `BUYER`, `SELLER`, or `BOTH` naming the caller's side. `GET /deals/{deal_id}`
returns the same representation to an active member of either party.
Routes call the application use cases and return explicit response schemas, never database
rows. Requests without valid credentials return `401`; an actor acting for an organization
it does not belong to returns `403`; identical buyer and seller organizations or invalid
fields return `422`; and missing, non-participating, or revoked-membership reads return the
same `404` so the API does not reveal another organization's deal or membership details.
`POST /deals/{deal_id}/messages` stores a user-authored message and
`GET /deals/{deal_id}/messages` lists the messages a deal party may read. The author is
always the verified actor, and the acting organization is derived from the actor's active
memberships, never trusted from the body. When the caller belongs to both deal parties, the
optional `organization_id` body field (or `organization_id` query parameter on reads) only
selects among organizations the actor already belongs to. Each message has `PRIVATE` or
`SHAREABLE` visibility; a party always sees its own messages and every `SHAREABLE` message
from the other side, while a counterparty's `PRIVATE` message and its source reference stay
hidden. A unique `(deal_id, participant_organization_id)` constraint guarantees one
conversation per deal party, so concurrent first messages converge on a single conversation.
Message creation accepts an optional nullable `idempotency_key`: a nonblank opaque string
of at most 128 characters, compared exactly (not trimmed). Omitted/null keys retain legacy
behavior and create a new message on each POST. A key is scoped to the deal, acting
organization, and authenticated user. Reusing it with the same normalized body, visibility,
and source reference returns the original message with `201`; changing those fields returns
`409`. Body and reference outer whitespace is stripped, and blank references equal null.
The versioned canonical fingerprint includes server-derived `USER` source, not client author
or source claims, IDs, or timestamps. Access is revalidated before replay, including race
recovery; retry metadata is not exposed. Message and notification are saved atomically.
Clients retain a key after a failed unchanged draft and rotate it on effective body,
visibility, deal/organization changes, or successful send.
Migration `0012_message_idempotency` installs nullable retry columns and the named unique
constraint without backfilling keys or modifying legacy messages. PostgreSQL installs these
additions transactionally: unlike the earlier index-only concurrent migrations, concurrent
index creation here would commit the columns before uniqueness is installed. Plan for the
table/index lock during deployment; downgrade removes only these additions.
`GET /deals/{deal_id}/facts` lists the reviewer's own facts plus shareable
counterparty facts. `POST /deals/{deal_id}/facts/{fact_id}/confirm`, `/reject`, and `/clarify`
advance a fact's review state, and only a member of the fact's owning organization may do so.
Review conflicts (a stale version or an invalid state change) return `409`. Message bodies are
never written to logs, and `422` validation errors are redacted so they do not echo submitted
request values back to the caller.
`POST /deals/{deal_id}/agreements` with `{ "proposal_id": "..." }` snapshots a saved proposal
into the deal's next `PENDING_APPROVAL` agreement version and returns its version number and
`terms_hash`. `GET /deals/{deal_id}/agreements/current` returns the current immutable terms,
version, hash, status, and both parties' recorded decisions to an active deal participant; it
returns `404` before a version exists. `POST /deals/{deal_id}/agreements/{version_number}/approve`
and `/reject` record
the authenticated party's decision for that exact version and the `terms_hash` the user saw.
`POST /deals/{deal_id}/agreements/{version_number}/commit` commits the version once both
parties approved it and derives the obligations, payment milestone, audit, and outbox rows in
one transaction. The acting organization always comes from the verified memberships: a caller
that belongs to both parties may pass `organization_id` only to select between them, and a
caller that names an organization it does not belong to or that is not a deal party receives
`403`. Requests cannot set an agreement status, so a browser cannot mark a deal `COMMITTED`.
A stale version, a mismatch between the displayed `terms_hash` and the stored terms, a repeated
decision, or a commit without both approvals returns `409` with a reload message. Non-participants
receive the same `404` as a missing deal, and a leaked or missing credential receives `401`.
Committing the same version and hash again is an idempotent success.
The proposal review screen saves the person's final edits through
`POST /deals/{deal_id}/agreements/from-reviewed-terms`. The server derives both parties from the
deal, validates the reviewed terms, then saves the proposal and pending agreement in one
transaction. An explicit `payment_trigger` must name a supported timing; an unsupported value is
rejected with `422`. For rollout compatibility the field may be omitted, in which case the server
uses the sole supported demo timing; remove that default once every client sends the field.
Retrying the same reviewed terms while a matching version is pending returns that version instead
of creating a duplicate or returning `409`; terms that differ from the pending version still
return `409`. Saving terms does not record either party's approval.
When rolling out payment timing in reviewed terms, deploy the API before the frontend: older API
instances forbid the unknown `payment_trigger` field, so a new frontend that reaches one receives
`422` until every instance is updated.
`POST /auth/refresh` accepts a refresh token, rotates it, and returns a new access
token and refresh token. Refresh tokens are opaque and stored only as hashes.
Each refresh token can be used once. Replaying any rotated token, including a concurrent
or delayed retry, is treated as reuse of a leaked credential: the whole token family is
revoked and the request receives `401`. Clients should serialize refresh requests and
sign in again if a refresh response is lost. Rotation state is committed together, so a
failed rotation does not leave a replacement token partially saved.
When rolling out the random refresh-token replacement behavior, drain older API instances
before enabling new instances: older versions may return a deterministically derived
refresh token after a retry, which cannot match replacements created by this version.

For local development/test only, `DEV_AUTH_USER_ID` may be configured and sent as
`X-Dev-User-Id`; this shortcut is rejected by configuration outside those environments.

The domain package contains framework-independent organization and membership records,
deal lifecycle rules, negotiation, canonical trade terms, bilateral agreement approval,
and payment intent state.

## Curated repeatable demo (F1a)

Prerequisites: Python 3.12+, the existing backend dependencies installed in `.venv`
(`python -m pip install -e ".[dev]"` when preparing a new environment), and Node.js
22.13+ on the 22.x line or 24+ with the frontend dependencies installed. Run backend
commands from `C:\Proj\SyncAlly\backend`. Configure a locally generated random
`JWT_SECRET` in the local environment or `.env` before starting the API. Do not use
production database URLs or production credentials.

For a persistent, provider-free demo, set these variables in the backend terminal:

```powershell
$env:APP_ENV = "development"
$env:DATABASE_URL = "sqlite:///C:/Proj/SyncAlly/backend/syncally-demo.db"
$env:PUBLIC_FRONTEND_URL = "http://localhost:5173"
```

One command sets up a fresh demo or restores the existing marked demo:

```powershell
.\.venv\Scripts\python.exe -m syncally.cli.seed_demo --offline --reset
```

On a fresh database, type each password and its confirmation directly into the terminal's
secure prompts (12-128 characters). A trusted script can provision missing passwords via
`BUYER_PASSWORD` and `SELLER_PASSWORD`; do not put passwords in command arguments, source
control, reports, or chat. Existing passwords are retained even when these variables change.
No prompt occurs on repeat setup/reset when both hashes already exist. Omit `--reset` for
idempotent setup that leaves an existing marked deal's subsequent human edits intact.

`--offline` requires file-backed SQLite, not an in-memory database. Only an empty database
is initialized from current ORM metadata, with foreign keys enabled. This does not execute
the historical PostgreSQL-only JSONB migrations or stamp a revision. Existing databases
must match current tables, columns, constraints, and both payment partial unique indexes
(uniqueness, ordered columns, and dialect-normalized predicates); unknown/older schemas are refused,
never silently upgraded. PostgreSQL operators instead apply `alembic upgrade head` through
the additive `0013_curated_demo_fixture` migration (after `0012_message_idempotency`) and
use the same command without `--offline`. That migration creates an empty marker table;
it neither adopts nor changes legacy deals.

The fixture contains one stainless-steel-bolts deal, one conversation per party, four
shared messages, a private note per party, eight exactly cited `EXTRACTED` candidates,
and one `PENDING_APPROVAL` agreement draft from explicit synthetic human choices. The
domain computes its canonical terms hash. No fact is confirmed, no approval is recorded,
and no obligation, payment, invoice, outbox dispatch, AI call, or other network operation
is created by setup/reset. Private sources and candidates stay party-scoped through the
existing API authorization rules.

Setup and API reset share one transaction-owning runner. PostgreSQL retains the advisory
transaction lock; SQLite setup/reset uses `BEGIN IMMEDIATE` before fixture reads/writes.
Failures roll back the entire seed/reset. The unique versioned marker records exact party
and deal IDs. Under that lock, reset refuses before deletion if the deal is no longer in
a pre-commit state, an agreement is approved/committed, or any approval, obligation,
payment milestone, or payment intent exists. Payment status and synthetic versus real
provider references do not bypass refusal: paid and uncertain-create reconciliation
history, webhooks, audit/outbox rows, and passwords are retained. No payment is cancelled
automatically and no fake/real provider conversion is attempted.

Only untouched `PENDING` `DEAL_NOTIFICATION` wakeups for deal creation, messages,
constraints, or proposals may be discarded. Payment/approval/commit notifications,
unknown event types/kinds (including Gmail work), and any processing, delivered, retried,
or otherwise attempted scoped dispatch refuse reset. API refusal returns `409`; CLI
refusal exits without a success message. Retain the history for reconciliation and use
a separately configured fresh database for another demo, rather than deleting history.

For an eligible unapproved draft, reset removes only that marked deal's children and
scoped audit/outbox rows, then recreates the same fixture IDs/content. It preserves identities/passwords, unmarked
same-party deals, mixed-party deals, and all unrelated audit data. Reserved-ID, version,
or party collisions refuse before cleanup; unmarked legacy deals are never auto-adopted.
Do not resolve collisions by deleting unrelated data or inventing a marker.

Start the API in that same configured backend terminal, using the same `DATABASE_URL`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn syncally.api.main:app --host 127.0.0.1 --port 8000
```

In a separate terminal from `frontend/`, run `npm run dev` (the existing proxy defaults
to `http://127.0.0.1:8000`; set `VITE_API_PROXY_TARGET` if using another API port).
Sign in as `buyer@syncally.demo` or `seller@syncally.demo` with the password you provisioned.
The existing workspace is `http://localhost:5173/#/deals`; the stable fixture route is
`http://localhost:5173/#/deals/d28a5d45-6f83-5001-93ec-43e28dbc712d`.
Authenticated demo admins can also use `POST /dev/reset-demo`, which invokes the same runner
and never prompts for passwords; missing identity hashes or collisions return `409`.
No Temporal, PayPal, Gmail, or AI service is required for F1a. The transient
`simulate_deal_flow` tool is a separate fake lifecycle exercise, not this persistent browser
seed. The judge walkthrough and later features are deferred beyond F1a.

From the backend directory, install the application and its test/lint tools with:

```powershell
python -m pip install -e ".[dev]"
```

## F4 invitations and private pending deals

`POST /deals/counterparty-invitations` accepts `buyer_organization_id`, normalized
`recipient_email`, bounded `legal_name`, and `country_code`. Current ACTIVE buyer ADMIN
authority is read from the database, not supplied roles. A single transaction creates a
private INACTIVE shell, DRAFT deal, durable 0015 binding, audit and identifier-only outbox
wakeup. The result contains the deal ID, copyable invitation URL, expiry and pending flag;
no email is sent. Public directory/ID and ordinary membership/deal creation reject shells.

Recipient-bound TEAM issuance uses `POST /organizations/{id}/invitations` with
`recipient_email` and server-selected MEMBER. Counterparty acceptance creates a separate
recipient organization with ADMIN, never membership in the buyer. Authenticated stored
email is authoritative; signup email must match and existing accounts need valid credentials.
Version/kind/binding tampering is rejected, while genuine legacy bearer invitations retain
their prior API shapes. Matching email is not verified mailbox ownership.

Acceptance locks/revalidates the exact pristine DRAFT deal and original unclaimed shell,
inviter authority, expiry and unused binding, then atomically swaps only the seller,
increments version, creates its conversation, consumes JTI/history, audits and issues
tokens. Pending messages/import/proposals are blocked without writes; human draft facts
use literal human-entry provenance without creating messages. Agreement approval/payment
rules are unchanged. See [operations](../docs/operations.md#f4-counterparty-onboarding)
for migration 0015, safe rollback, privacy, legacy compatibility, two-person testing and
the opt-in `TEST_POSTGRES_URL` gates. Preserve the 0014 relay/reset safeguards below.

Run the backend tests and lint checks from the backend directory:

```powershell
python -m unittest discover -s tests -v
python -m ruff check src tests
```

For a local PostgreSQL database, copy `.env.example` to `.env`, set `DATABASE_URL`, and
apply the schema from this directory:

For an existing database crossing migration `0014`, first disable demo resets and
stop and drain all old generic outbox relays: let in-flight external calls complete
before migrating, then stop the old API and reset tooling. Keep resets prohibited
through the transition; do not run mixed old/new versions. If a relay is killed
with an unknown request outcome, do not reset the affected demo until external
history is verified. A legacy null `dispatch_started_at` can mean an old relay made
an unrecorded external call; the migration backfill cannot infer old in-flight
attempts. Do not fabricate dispatch history. After `alembic upgrade head` applies
`0014`, restart the updated API and reset tooling with resets still blocked, then
start updated relays; only then re-enable resets, retaining the block for any
unverified outcome. See [the transition procedure](../docs/operations.md#migration-0014-transition).

```text
alembic upgrade head
```

This applies all migrations to the PostgreSQL database configured by `DATABASE_URL`.
The same command upgrades an existing database as well as creating a fresh schema.

Run the outbox relay separately after applying migrations:

```text
python -m syncally.cli.outbox_worker
```

Run the API and Temporal workflow worker as separate processes as well:

```text
python -m uvicorn syncally.api.main:app --reload
python -m syncally.workflows.worker
```

To process authorized payment intents, set `PAYPAL_CLIENT_ID` and
`PAYPAL_CLIENT_SECRET` to the PayPal **Sandbox** app credentials in the local
environment, then run this separate process:

```text
python -m syncally.cli.payment_worker
```

After an agreement is committed, an active seller member can authorize its first payment
milestone with `POST /deals/{deal_id}/payments` and an `idempotency_key`. The API saves the
PaymentIntent and outbox event together; the separate payment worker performs the PayPal calls.

For payment status updates, register an HTTPS webhook URL ending in
`/webhooks/paypal/invoicing` on that same Sandbox REST app and subscribe it to
the invoice events. Set `PAYPAL_WEBHOOK_ID` to the webhook ID shown by PayPal.
The API uses the Sandbox app credentials and webhook ID to ask PayPal to verify
each signature. It stores each verified event once and queues work only when
the invoice belongs to a saved SyncAlly payment intent. The payment worker then
fetches the current invoice and reconciles its amount, currency, and status;
webhook payload status alone never marks a payment paid. Stored event metadata is
limited to the event ID, event type, and invoice ID; payer details are discarded.

The worker creates a draft invoice and sends it as a separate PayPal request.
It uses the buyer organization's sole active admin as the invoice contact; if
that contact is missing or ambiguous, the intent is marked for manual action.
PayPal Sandbox notifications do not reach real inboxes. To send a separate
email copy with the PayPal invoice link, configure `GMAIL_SMTP_USERNAME` and
`GMAIL_APP_PASSWORD` in the local `.env` before processing the payment. Create
an App Password on a Google account with 2-Step Verification enabled; do not
use the account's regular password. `GMAIL_FROM_EMAIL` is optional and defaults
to the SMTP username. Gmail delivery is disabled when these settings are empty.

The Gmail copy runs after PayPal accepts the invoice. If SMTP delivery needs a
retry, the durable payment outbox retries it without creating or sending a
second PayPal invoice. Keep PayPal and Gmail credentials in the local `.env` or
deployment secret store. Do not put them in source control, database rows, or
frontend/AI configuration. Automated tests use fake providers and do not
require PayPal or Gmail credentials.

To email an invoice that was already sent before Gmail was configured, run this
one-time command with its PayPal Sandbox invoice ID:

```text
python -m syncally.cli.email_invoice INV2-...
```

It reads the recipient and invoice link from PayPal, then sends only the Gmail
copy; it does not send or recreate the PayPal invoice.

Configure `TEMPORAL_ADDRESS`, `TEMPORAL_NAMESPACE`, and `TEMPORAL_TASK_QUEUE` in
the environment. The relay sends only deal/agreement IDs. Failed deliveries use
a persisted exponential retry delay with jitter (up to five minutes); malformed
events become `FAILED` for inspection. Use the [operations and recovery guide](../docs/operations.md) to inspect and
recover work. Its guarded Temporal-only retry procedure does not apply to payment
events or processed reconciliation webhooks.

To include the PostgreSQL concurrency test, set `TEST_POSTGRES_URL` to a test
database URL and run the test suite. The test creates and removes its own isolated
schema; the database user needs permission to create schemas. Message idempotency tests in
`tests/test_communication_repositories.py` cover existing/lazy conversations, identical and
changed concurrent payloads, and rollback of the initial winner. They are skipped when
`TEST_POSTGRES_URL` is absent; normal tests need no database credentials. Temporal adapter
unit tests use a mocked client.

For the end-to-end local restart smoke test, start PostgreSQL and Temporal as described
in [the infrastructure guide](../infra/README.md), then set `TEST_POSTGRES_URL` and
`SYNCALLY_TEMPORAL_ADDRESS` and run `python -m unittest discover -s tests -p test_local_workflow_smoke.py -v`.
The test creates an isolated schema and verifies outbox delivery, two simultaneous agreement
commit requests, workflow recovery after worker restart, and idempotent replay of the agreement
commit. The ordinary test suite also runs `python -m unittest tests.test_demo_lifecycle -v` with
in-memory SQLite and fake AI, PayPal, and webhook adapters. It covers the browser-facing API
lifecycle, both parties' private messages, seller-only payment authorization, provider timeout
recovery, duplicate webhook handling, and safe reconciled payment status without external keys.

See [the domain architecture](../docs/architecture/05-domain-layer.md) for implemented invariants, package boundaries, and remaining work. The domain types do not perform persistence, authenticated authorization, or external provider calls.

Operational logging, correlation IDs, privacy limits, health checks and payment-safe
recovery procedures are documented in [the operations guide](../docs/operations.md).
