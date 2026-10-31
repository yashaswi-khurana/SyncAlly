# SyncAlly Implementation Plan

**Status:** Living plan. Completed foundations and remaining product work are listed separately below.

This plan tracks the constrained first demo from the shared [demo contract in issue #8](https://github.com/yashaswi-khurana/SyncAlly/issues/8). The contract's working defaults are ready to implement. Update implementation status when work merges, and use the relevant issue/PR to propose a focused contract change when code reveals a concrete mismatch.

## Current Implementation Status

### Implemented foundation

- Backend API health endpoints, JWT authentication, refresh-token storage/rotation, and deal reads authorized through database-backed organization membership.
- PostgreSQL models, Alembic migrations, database configuration, persistence/rollback coverage, and migration instructions (PRs [#41](https://github.com/yashaswi-khurana/SyncAlly/pull/41) and [#42](https://github.com/yashaswi-khurana/SyncAlly/pull/42)).
- Framework-independent domain foundations for deals, trade terms, negotiation, bilateral agreements, and payment intents.
- Framework-independent conversation, message, and constraint contracts with visibility checks and owner-authorized fact confirmation.
- React/TypeScript Vite shell.
- Backend test/lint commands, a health-route test, and frontend test/build/lint checks are defined in the project READMEs and verified by this story.
- Development/test demo seeding creates buyer/seller accounts, organizations, and admin memberships; public self-registration is disabled.

### Still planned

- Persisted deal creation and complete browser-to-API deal workflows.
- Message/fact review, proposal creation and negotiation workflows, bilateral approval, and committed agreement persistence.
- PayPal Sandbox invoice creation and reconciliation.
- Frontend connection to the API and user-facing product flows.
- Independent production-readiness review and live PostgreSQL/browser verification of F4 onboarding.

See [README](../README.md), [system architecture](../ARCHITECTURE.md), and the [architecture decision record](architecture/04-architecture-decision-record.md) for more detail. Architecture documents describe intended behavior where the implementation status above says work is still planned.

## What We Are Building

Build one simple buyer/seller flow for one agreed trade type and currency:

1. Create a deal and save it.
2. Add messages and review extracted facts.
3. Draft a proposal and let people review it.
4. Get both sides to approve the exact same agreement.
5. Track long-running work with Temporal.
6. Create and reconcile one PayPal Sandbox invoice.

This does not include production payments, multiple payment providers, escrow, or general legal/tax/customs compliance.

## Words Used in This Plan

- **Migration:** a versioned change to the database structure.
- **Outbox:** a database row saved with a business change, then picked up and delivered later. It prevents work from being lost if a process stops.
- **Idempotent:** safe to retry without doing the same work twice.
- **Reconcile:** ask PayPal for its current status and compare it with our saved status.
- **Immutable:** cannot be edited after commit; make a new version to change it.
- **Private context:** information visible only to the organization that supplied it.

## Identity and Onboarding Status

Email/password login, verified-token identity, database-backed memberships, organization
creation, and admin membership for existing users are implemented. Public self-registration
is disabled to match the demo contract. From `backend/`, run
`python -m syncally.cli.seed_demo` after migrations to provision the demo buyer and seller;
the command prompts for passwords and hashes them in the app.

### F4 - Counterparty onboarding (implemented, awaiting independent review)

An ACTIVE buyer ADMIN can use New deal / Invite counterparty or
`POST /deals/counterparty-invitations` to atomically create an INACTIVE private seller
shell, human DRAFT deal, durable recipient binding, audit, and identifier-only outbox
wakeup. Ordinary active-organization deal creation and directory selection remain available.
Migration `0015_counterparty_onboarding` descends from `0014`; it never infers pending
state from legacy names or missing memberships. Pending human preparation is allowed,
but messages, thread import, and persisted proposals/negotiation are blocked.

Versioned TEAM invitations bind a normalized recipient and grant MEMBER. COUNTERPARTY
invitations bind the exact buyer/deal/shell and create the recipient's separate organization
with ADMIN membership. Acceptance rechecks current database identity and inviter authority,
locks and validates the unused binding and pristine DRAFT deal, replaces only its seller,
increments version, creates the recipient conversation, consumes the invitation, and issues
tokens in one transaction. It never approves an agreement or authorizes a payment.
Both acceptance screens reset on token changes; App refreshes memberships and uses the
server-returned deal ID, ignoring stale-session refreshes.

Genuinely legacy invitations retain their bearer-capability contract. Unknown or malformed
typed claims cannot fall back to it. Token possession and matching signup email are not
verified mailbox ownership; stronger recipient verification, especially for team access,
is a separate security recommendation. No email is sent. F5 is not included.
See [the operations walkthrough](operations.md#f4-counterparty-onboarding) for rollout,
rollback, two-person acceptance, and the required PostgreSQL/browser environment gates.

F4 validation on 2026-10-31: the focused backend slice ran 138 tests with no failures
or errors and 9 PostgreSQL-dependent skips; the full backend suite ran 629 tests with
no failures or errors and 20 environment skips. Focused frontend tests passed 212/212;
the full frontend suite passed 328/328. The documented backend Ruff gate, frontend
`lint:check`, production build, and `git diff --check` passed. Existing payment-panel
lint warnings and the large Three.js bundle warning remain outside F4.
PostgreSQL concurrency/fresh migration and the real two-person browser walkthrough
remain unexecuted. F4 is ready for independent code review, not production sign-off.

### F5 - Persisted human negotiation (implemented, environment gates outstanding)

F5 adds explicit human submit/counter/accept-as-candidate/reject/supersede/expire commands,
immutable canonical terms snapshots and persisted actor-organization/user action history.
Latest-base and revision checks, fresh database authorization, F4 pending-state rejection,
durable round-limit escalation and atomic candidate replacement are enforced under the
deal lock. New acceptance creates a fresh empty-approval candidate even for equal hashes;
legacy drafting contracts remain available without bypassing human rounds. Private evidence
is reauthorized/redacted at projection. Migration 0016 is additive after the preserved 0015.
The AI/detail UI uses these commands; agreement approval and execution stay separate.
F6 is not included.

Validation on 2026-10-31: focused negotiation/migration 33 tests (27 pass, six PostgreSQL
skips), domain 20/20, agreement routes/domain/repository 46/46; isolated full backend
668 tests (642 pass, 26 database/service skips). Five file-backed SQLite race scenarios
pass, including candidate replacement versus decisions and injected lock-winner rollback;
SQLite does not prove PostgreSQL locking. Backend Ruff `src tests` passes. Focused
frontend negotiation/AI/detail/client 92/92 and full frontend 336/336 pass; lint/typecheck
and production build pass with three existing payment-panel warnings and a large Three.js
chunk warning. The full backend runner bootstraps local SQLite/offline configuration,
removes application environment variables before tests, and disables Temporal test-server
startup for this invocation only under the no-services constraint.

Live PostgreSQL fresh migration/races require `TEST_POSTGRES_URL`, which is not configured.
Desktop/mobile two-party browser verification remains unexecuted under the no-services
constraint. F5 is ready for independent review, not production sign-off.
See [F5 operations](operations.md#f5-persisted-human-negotiation).

### F6 - Agreement history and comparison (implemented, environment gates outstanding)

F6 adds fresh database-authorized history, exact-version and structured comparison GETs,
version-owned recorded approvals, and read-only historical review in AgreementReview.
Equal-hash versions remain distinct. Comparison normalizes copies without changing stored
terms/hashes and preserves duplicate counts; ambiguous entry matching stays added/removed.
Exact-proposal evidence references are frozen in existing version JSON metadata for new
snapshots. Current source authorization, frozen privacy and source integrity are rechecked
on each read. Legacy/changed/ambiguous/missing sources do not enable tracing or fabricate
term grounding. F7 amendments and F10 structured authoring remain excluded; migrations
0012-0016 and prior accepted work are preserved.

Validation on 2026-10-31: focused backend agreement/negotiation/domain 107 tests,
101 pass and six PostgreSQL skips; full isolated backend 679 tests, 652 pass and 27
database/service skips, zero failures/errors and Python exit 0. Focused frontend
AgreementReview/client/detail 88/88 and full frontend 342/342 pass. Backend Ruff,
frontend lint/typecheck, production build and whitespace checks pass. Three existing
payment-panel lint warnings and the large Three.js chunk warning remain unchanged.
The backend runner uses SQLite/offline bootstrap, removes service configuration and
disables Temporal test-server startup for this invocation. Real PostgreSQL/service
validation and desktop/mobile two-party browser verification remain unexecuted under
the no-services constraint. F6 is ready for independent review, not production sign-off.
See [F6 API contract](../backend/README.md#f6-agreement-history-and-comparison).

### F11a - Explicit payment modes (implemented, review ready)

F11a extends the existing single-milestone payment path, not F10/multi-milestone
authoring. New intent mode is selected exclusively by server configuration, persisted
atomically with provider/outbox identity, and immutable thereafter. Matching replays
retain their original mode across configuration changes. Per-intent worker dispatch
has no fake fallback, fabricated offline URLs, remote construction for offline work,
or automatic paid transition. The protected demo-scoped command queues explicit
simulated observations; worker commit rechecks scope/version/lease and records
`OFFLINE_DEMO` source plus `SIMULATION/OFFLINE_DEMO` success audit. Rejected evidence
receives atomic needs-action completion without changing payment truth. Real PayPal
webhooks remain separate. Typed UI labels distinguish offline, Sandbox and unknown
evidence, including the seller's preview confirmation.

Additive 0017 preserves migrations 0012-0016 and historical payment values/indexes.
Legacy PayPal routing remains Sandbox with unverified historical evidence; other
legacy providers remain unresolved, never converted to demo history. Downgrade
refuses provenance loss, and payment-history reset protections remain unchanged.
The CLI's explicit offline harness shares the adapter and prints stored unpaid
truth; unavailable backends never silently switch databases. Importing the CLI
no longer mutates process logger levels (regression-tested).

Validation on 2026-10-31: focused payment 83 tests, dev routes 20, webhook 3 and
demo 41 passed before repairs; focused repository 24 and CLI/operations 12 passed
after repairs; explicit CLI CI wiring also passes. Full isolated backend: 699 tests,
672 pass, 27 skips, zero failures
or errors. Skips comprise 17 PostgreSQL-dependent tests, nine Temporal test-server
tests and one local PostgreSQL/Temporal smoke test. The invocation bootstraps
SQLite/offline configuration, removes service environment variables and disables
Temporal server startup without altering test code. Frontend: 17 files, 346 tests
passed. Ruff `src tests`, frontend lint/typecheck and production build pass, with
three pre-existing payment-panel warnings and the existing Three.js chunk warning.

No agents, commits, real services or credentials were used. Live PostgreSQL
migration/locking execution, desktop/mobile two-party browser verification and
F11b Sandbox create/pay/webhook verification remain unexecuted. F11a is ready for
independent code review, not production sign-off. See
[F11a operating contract](operations.md#f11a-explicit-payment-modes).

## Team Rules

- Each story gets one branch and one PR. Put tests with the code they test.
- Use issue #8 as the working product and API contract; work can proceed asynchronously against those defaults.
- Agree on shared types and API shapes before building dependent pieces in parallel.
- Do not edit the same file at the same time. If two stories need the same file, merge the shared change first or do those stories one after another.
- Merge all stories in a stage before starting a later stage that changes the same interfaces.
- Update this plan when work merges so completed foundations remain distinct from planned flows.

## Rules Every Stage Must Follow

- Keep business decisions in `backend/src/syncally/domain/` and `application/`. The domain must not depend on FastAPI, Temporal, AI libraries, or PayPal.
- The backend checks who the user is and which organization they belong to. Never trust a role or organization ID just because the browser sent it.
- Keep buyer-private and seller-private data separate. Only share data marked shareable.
- AI can suggest facts and terms. A person and the domain rules must check them before they affect an agreement.
- Both organizations must approve the same agreement version. A committed agreement is not edited in place.
- PostgreSQL stores the business truth. Temporal, AI history, a webhook, or a browser redirect cannot replace it.
- Save and authorize a PaymentIntent before calling PayPal. Mark it paid only after checking PayPal's current payment state.
- Do not hold a database transaction open while calling an AI service, Temporal, or PayPal.
- Use decimal money values and an explicit currency. Do not use floating-point numbers for money.

## Stage 1 - Set Up the Basics

**Goal:** Add the first domain types, database setup, user identity boundary, and test commands.

### S1-01 - Add organization and deal types

**Code area:** `backend/src/syncally/domain/`

**Why:** Other features need a common definition of a deal and its participants.

**What to build:** Add Organization, membership, and Deal types. A deal has one buyer, one seller, a status, and a version. Put allowed status changes in domain methods, not in the API or database code.

**Done when:**
- Tests reject a deal where buyer and seller are the same organization.
- Tests reject an invalid status change.
- Importing the domain package does not load FastAPI, the database, Temporal, or PayPal code.

### S1-02 - Set up the database

**Code area:** `backend/src/syncally/infrastructure/` and the chosen migrations folder.

**Why:** Deals and user memberships must survive app restarts.

**What to build:** Add SQLAlchemy setup, Alembic migrations, database configuration from environment variables, and tables for organizations, memberships, and deals. Add the basic outbox table, but not its worker yet.

**Done when:**
- A clean local database can be created with the documented migration command.
- Tests cover saving and loading the first records and rolling back after an error.
- A deal and its outbox row can be saved in one transaction; if the transaction fails, neither is saved.
- No database password is committed to the repo.

### S1-03 - Add the user identity boundary

**Code area:** `backend/src/syncally/api/` and `application/`.

**Why:** Later API calls must know which user is making a request and which organizations they can act for.

**What to build:** Implement the sign-in/authentication choice agreed by the team. Add a backend ActorContext that gives application code the verified user and organization memberships. Any shortcut for local development must be disabled outside development/test settings.

For the first demo, operator provisioning is performed by the development/test-only
`python -m syncally.cli.seed_demo` command. Do not expose public self-registration. The
separate product onboarding flow (invite by email, accept invite, set password, activate
membership) remains planned.

**Done when:**
- Protected requests fail when the user is not signed in.
- A user without active membership cannot access that organization's deal.
- Tests prove browser-supplied roles or organization IDs cannot grant access.
- Secrets come from configuration and are not written to logs.

### S1-04 - Add test and check commands

**Code area:** backend/frontend test configuration and READMEs.

**Why:** Everyone needs the same quick way to check their changes.

**What to build:** Add a backend test/lint setup and a frontend test setup that fit the existing projects. Add a health-route test and a basic frontend render test. Document the commands.

**Done when:**
- The documented backend and frontend checks run after installing dependencies.
- A broken test makes its command fail.
- The health route and basic frontend render are tested.

**Stage check:** The foundational stories are merged. A clean checkout can run the documented checks and database migration.

## Stage 2 - Create and View a Deal

**Goal:** A signed-in user can create a deal, save it, and view it again.

### S2-01 - Add deal use cases

**Code area:** `backend/src/syncally/application/`

**Why:** The API and UI need one tested place to ask for deal creation and retrieval.

**What to build:** Add create-deal and get-deal operations. They take the verified user context, check participation, and use a repository interface. Do not put SQLAlchemy code here.

**Done when:**
- Unit tests cover create, get, missing deal, same buyer/seller, and user without membership.
- The use case does not trust a role supplied by the caller.
- Tests run without starting FastAPI or PostgreSQL.

### S2-02 - Save and load deals

**Code area:** `backend/src/syncally/infrastructure/`.

**Why:** The use cases need a database implementation of their repository interface.

**What to build:** Add create/get database operations for organizations, memberships, and deals. Convert database rows to domain types at this boundary.

**Done when:**
- Database tests save and load a deal with the right buyer, seller, and version.
- Missing or duplicate references return clear errors.
- A failed create leaves no partial deal behind.

### S2-03 - Add deal API routes

**Code area:** `backend/src/syncally/api/`.

**Why:** The UI needs HTTP endpoints to create and view deals.

**What to build:** Add create and detail routes, input/output schemas, and error mapping. Get the user context from S1-03. Call application use cases; do not implement deal rules inside the route.

**Done when:**
- API tests cover success, bad input, not signed in, forbidden access, and missing deal.
- Responses use API schemas, not raw database objects.
- A user cannot see another organization's membership details.

### S2-04 - Connect the deal UI

**Code area:** `frontend/src/`.

**Why:** This proves the backend and browser work together.

**What to build:** Replace the placeholder screen with a basic create and detail flow. Load data from the API. Show loading, empty, validation, and error states.

**Done when:**
- A user can create a deal and see it in the UI.
- Refreshing the page loads the saved deal from the API.
- API errors do not leave the screen stuck loading.
- Frontend tests and build pass.

**Stage check:** Create a deal in the browser, refresh, and see it again. A different organization cannot read it.

## Stage 3 - Messages and Facts

**Goal:** Store deal messages and facts while keeping each side's private information private.

### S3-01 - Define messages and facts

**Code area:** `backend/src/syncally/domain/` and `application/`.

**Why:** Later proposal work needs to know who said something and whether it can be shared.

**What to build:** Add Conversation, Message, and Constraint types. A conversation uses `participant_organization_id`; messages and facts have explicit private/shareable visibility. Facts retain units and provenance, start unconfirmed, and advance by versioned review transitions.

**Contract code:** Domain types and fake-backed authorization/confirmation checks are implemented. A message inherits deal/owner scope through its required conversation reference; a constraint stores its deal and owner directly. The repository port requires current owner membership, same-deal provenance, and an expected-version check in the save transaction. Persistence, API routes, and UI remain in S3-02 through S3-04.

**Done when:**
- Tests reject messages or facts without a deal owner and visibility.
- Extracted facts cannot become confirmed without an authorized confirm operation.

### S3-02 - Save messages and facts

**Code area:** database migrations and `backend/src/syncally/infrastructure/`.

**Why:** Messages and their source information must persist and remain correctly scoped.

**What to build:** Add tables and repository operations for conversations, messages, and constraints. Save owner, visibility, source reference, and status. Require a deal/organization scope when reading records.

**Done when:**
- Database tests save and load messages/facts with ownership and visibility intact.
- A buyer-scoped query cannot return seller-private data, and vice versa.
- Migration and rollback are covered by tests.

### S3-03 - Add message and fact API routes

**Code area:** `backend/src/syncally/api/` and `application/`.

**Why:** The backend, not the browser, must decide which side can read or change a message or fact.

**What to build:** Add routes to add/list messages and to confirm, reject, or request clarification for a fact. Get the organization from the verified user context.

**Done when:**
- API tests cover allowed access, cross-organization denial, and unauthorized confirmation.
- A participant gets only the messages/facts allowed by the visibility rules.
- Message contents are not written to general logs.

### S3-04 - Build the message and fact review screens

**Code area:** `frontend/src/`.

**Why:** People need to check extracted facts before the app uses them.

**What to build:** Add a deal conversation screen and a fact review screen. Label private/shareable and extracted/confirmed information. Let the user confirm, reject, or ask for clarification.

**Done when:**
- Users can only see data returned by their authorized API calls.
- Unconfirmed facts look different from confirmed facts.
- The UI does not present an extracted fact as agreed truth.

**Stage check:** Tests with two organizations prove private messages/facts do not cross between them.

## Stage 4 - AI Suggestions

**Goal:** AI can suggest facts and terms, but a person reviews them before they are used.

### S4-01 - Define AI input and output types

**Code area:** `backend/src/syncally/domain/` or shared application schemas.

**Why:** The app must reject malformed AI output instead of trusting free-form text.

**What to build:** Define versioned schemas for extracted facts, their source references, proposal terms, and validation errors. Check required fields and supported values in normal Python code.

**Done when:**
- Tests reject missing, malformed, or unsupported values.
- Each extracted fact has a source reference or says that its source is unknown.
- AI output cannot directly approve an agreement or start a payment.

### S4-02 - Filter AI context by organization

**Code area:** `backend/src/syncally/application/`.

**Why:** A prompt must not include the other side's private information.

**What to build:** Add a service that selects only the current organization's private data and explicitly shareable data. Keep filtering separate from prompt-building so it can be tested without an AI service.

**Done when:**
- Tests prove buyer prompts cannot include seller-private facts and seller prompts cannot include buyer-private facts.
- Missing or conflicting ownership/visibility causes the request to fail closed.
- Raw private context is not put in logs or Temporal workflow inputs.

### S4-03 - Add an AI adapter and fake

**Code area:** `backend/src/syncally/infrastructure/` and `application/`.

**Why:** The app needs to call an AI service without making business rules depend on its SDK.

**What to build:** Add a small interface for fact extraction and proposal drafting. Add a fake implementation for tests. Add one real provider only after the team chooses it. Set time and retry limits; parse output with S4-01 schemas. Use LangGraph only if a simple typed function is not enough.

**Contract code:** F2 implements one OpenAI Chat Completions HTTP adapter behind the existing `AISuggestionProvider` port, promoting the existing httpx version constraint to runtime. Offline remains the default; remote mode requires explicit egress permission, operator-configured model and masked environment credentials. Private message/constraint egress requires the private flag plus the selected organization's trusted UUID allowlist entry and normal database authorization. Two 10-second attempts and 0.5-second backoff, 128 KiB request/streamed response limits, 4096 output tokens, strict domain JSON and locally grounded proposal citations bound the integration. Only explicit missing-credential or exhausted-transient fallback is allowed. API/UI provenance is additive and invocation-only, never reviewed terms or fabricated per-fact history. HTTP is transaction-free with selected membership reauthorization before persistence. `store=false` does not promise zero retention. Mocked transport/context/route/frontend evaluation makes no real-provider, account or model availability claim; `gpt-4.1-mini` is an operator example only. No migrations, onboarding, negotiation, or changes to B1-B4/Q1/F1a/F3 are included. See [the AI provider boundary](architecture/06-ai-provider-boundary.md).

**Done when:**
- Tests run with the fake and need no network or API key.
- Invalid AI output is rejected or sent for clarification; it is never auto-confirmed.
- Timeouts/retries have a fixed limit.
- AI credentials never reach the browser, Temporal history, or logs.

### S4-04 - Add the AI review UI

**Code area:** `frontend/src/`.

**Why:** Users need to review suggestions before sharing or using them.

**What to build:** Show extracted facts with their source. Let users correct, confirm, or ask for clarification. Show proposals as drafts, not agreements. Hide private facts from the other party's view.

**Done when:**
- Review actions go through the API and require an explicit user click.
- A private fact never appears in the other party's proposal screen.
- AI drafts are clearly different from approved agreements.

**Stage check:** Verified on the current mainline: deterministic AI suggestions are requested explicitly, facts are saved unconfirmed with source evidence, the user can review them, and private context remains organization-scoped. Backend coverage is in `test_ai_context.py`, `test_ai_provider.py`, and `test_conversation_routes.py`; frontend coverage is in `DealConversationReview.test.tsx`.

## Stage 5 - Agreement and Approvals

**Goal:** The deal becomes agreed only after both sides approve the same saved version.

### S5-01 - Make stable agreement versions

**Code area:** `backend/src/syncally/domain/` and `application/`.

**Why:** Both approvals must refer to exactly the same terms.

**What to build:** Define the agreement fields and how to normalize them before saving. Create a stable hash (fingerprint) from the normalized terms. A change after commit creates a new version.

**Done when:**
- Tests show the same terms produce the same hash even if fields arrive in a different order.
- Amounts use decimal values and always include a currency.
- Unsupported/unclear terms cannot be committed.
- A committed agreement cannot be edited in place.

### S5-02 - Save approvals and commit in one transaction

**Code area:** `backend/src/syncally/infrastructure/` and `application/`.

**Why:** Two simultaneous approval requests must not create two agreements or commit different terms.

**What to build:** Save agreement versions and approvals. Add `CommitAgreement`: check both authorized approvals match the current version and hash, then save the commit, obligations, audit record, and outbox row in one database transaction.

**Done when:**
- Tests reject one approval, unauthorized approval, old version, and wrong hash.
- Two simultaneous commit attempts create only one commit and one set of obligations.
- If any check fails, none of the commit-related rows are saved.

### S5-03 - Add approval API routes

**Code area:** `backend/src/syncally/api/`.

**Why:** Approval must be a verified backend command, not a browser status change.

**What to build:** Add routes to create an agreement draft, approve/reject a version, and request commit. Get the user's organization from sign-in state. Require the version and hash the user saw.

**Done when:**
- API tests cover unauthorized users, stale versions, wrong hashes, repeat requests, and successful commit.
- A client cannot send `COMMITTED` status or pretend to be the other organization.
- Stale approvals return a clear conflict response.

### S5-04 - Add agreement review and approval screens

**Code area:** `frontend/src/`.

**Why:** Both sides must review the same saved terms before approving.

**What to build:** Show agreement terms, version, and status. Approve/reject the version currently on screen. If it changed, show the conflict and reload. Make committed terms read-only.

**Done when:**
- The UI sends the version/hash it displayed.
- A stale approval asks the user to reload; it does not approve a newer version automatically.
- Committed terms cannot be edited on the screen.

**Stage check:** Only two authorized approvals for the same version/hash can create one committed agreement and its obligations.

## Stage 6 - Background Deal Workflow

**Goal:** Let a deal wait for people and recover if a worker stops.

### S6-01 - Deliver outbox work to Temporal

**Code area:** `backend/src/syncally/infrastructure/` and worker entry point.

**Why:** Saving a deal and starting Temporal are two separate operations. The outbox lets the app retry if Temporal is down.

**What to build:** Add a process that reads pending outbox rows and starts one workflow per deal with a stable ID. Mark a row delivered only after handling the start result. Make retries safe.

**Done when:**
- Tests cover a stopped dispatcher, Temporal being unavailable, two dispatchers, and a workflow that already started.
- A pending row starts one workflow after Temporal comes back.
- Outbox data contains IDs, not private messages or secrets.

### S6-02 - Write the deal workflow

**Code area:** `backend/src/syncally/workflows/`.

**Why:** Deals can wait hours or days; a normal API request cannot stay open that long.

**What to build:** Add one workflow per deal. It may wait, set timers, and receive signals. It must call activities for database, AI, or provider work; do not call those systems directly from workflow code. Put a limit on waits, retries, and proposal rounds.

**Contract code:** `workflows/deal.py` accepts the ID-only start payload from the S6-01 outbox, deduplicates notification IDs, and refreshes persisted state through the `RefreshDealState` activity contract. The workflow has a 30-day wait deadline and a three-attempt activity retry limit. Timeout returns `WAIT_EXPIRED` and does not mutate business state. The activity implementation and worker registration are in S6-03. The workflow patch marker and input schema migration strategy is documented in [the Temporal contract](architecture/02-temporal-deal-workflow-contract.md#10-temporal-workflow-determinism-and-versioning).

**Done when:**
- Tests show the workflow waits for approval and continues after a signal or worker restart.
- Repeated/out-of-order signals do not repeat business actions.
- A timeout never means approval or payment.
- There is a test/release plan for changing workflow code while old workflows exist.

### S6-03 - Add workflow activities and worker process

**Code area:** `backend/src/syncally/workflows/` and `application/`.

**Why:** Activities do external work; the API and workflow worker should be startable separately.

**What to build:** Add activities that call application services using saved record IDs. Add a worker entry point separate from the FastAPI app. Reload current state before taking an action; do not treat old workflow input as current authorization.

**Contract code:** `application/workflow_state.py` reloads the deal and current agreement by saved ID; the agreement version carried in older workflow input is not treated as current. `workflows/activities.py` implements `RefreshDealState`, converts validation and business rejections to non-retryable errors, and leaves transient database failures to the workflow's bounded retry policy. `workflows/worker.py` registers the workflow and activity as a process independent of FastAPI.

**Done when:**
- Tests show activities reload current state and use safe/repeatable commands.
- Temporary errors retry a limited number of times; permission/validation errors do not retry forever.
- Starting the API does not start a worker, and starting the worker does not start API routes.

### S6-04 - Add local services and restart test

**Code area:** `infra/` and local development docs.

**Why:** All developers need a repeatable way to run PostgreSQL, Temporal, the API, and the worker.

**What to build:** Add only the local service setup that has been tested. Document how to run migrations, API, outbox relay, and workflow worker. Add a smoke test that starts a workflow from the outbox and continues it after approval signals and a worker restart.

**Local implementation:** `infra/compose.yaml` runs PostgreSQL and a Temporal CLI development server with persistent local workflow history. The API, outbox relay, and workflow worker run as separate backend processes. `backend/tests/test_local_workflow_smoke.py` is an opt-in PostgreSQL/Temporal integration test that verifies outbox start, approval notification delivery, worker restart recovery, and idempotent commit replay.

**Done when:**
- A new developer can follow the instructions and start all local processes.
- The smoke test starts a workflow from an outbox row and resumes it after approval.
- Restarting the worker does not lose deal state or repeat a commit.

**Stage check:** A saved deal starts a workflow through the outbox, and the workflow can recover after a worker restart.

## Stage 7 - PayPal Sandbox Payment

**Goal:** Create one authorized Sandbox invoice and update its status only after checking PayPal.

### S7-01 - Add PaymentIntent rules

**Code area:** `backend/src/syncally/domain/` and `application/`.

**Why:** The app needs a saved, authorized payment operation before it contacts PayPal.

**What to build:** Add PaymentIntent and its states. Check there is a committed agreement, a valid seller, the right milestone amount/currency, and no duplicate active request. Include an unknown state for timeouts where PayPal may have received the request.

**Done when:**
- Tests reject missing agreement, unauthorized seller, wrong amount/currency, and duplicate request.
- A timeout can be marked unknown, not falsely marked failed.
- Only a PayPal status check can mark the intent fully paid.

### S7-02 - Save payment intents and payment outbox rows

**Code area:** database migrations and `backend/src/syncally/infrastructure/`.

**Why:** The worker needs to resume a payment operation after a crash without creating another invoice.

**What to build:** Save intent ID, deal/agreement/milestone IDs, amount/currency, status, version, operation key, provider invoice ID, and last check time. Save its outbox row in the same transaction. Never save credentials as ordinary database data.

**Done when:**
- Database tests reject duplicate active requests for one milestone.
- Tests prove the intent and outbox row save or roll back together.
- Logs and stored fields do not expose credentials or unnecessary provider data.

### S7-03 - Add PayPal Sandbox adapter and worker

**Code area:** `backend/src/syncally/infrastructure/` and payment worker.

**Why:** PayPal-specific requests should be separate from deal rules and safe to retry.

**What to build:** Add an adapter to create and send an invoice using the saved PaymentIntent and committed agreement data. Create and send are separate operations. Use stable request IDs when PayPal supports them. Do not call PayPal while a database transaction is open.

**Done when:**
- Automated tests use a fake PayPal client and need no credentials.
- A timeout records an unknown result and checks PayPal before retrying invoice creation.
- Permanent errors are shown as needing action, not retried forever.
- Credentials never reach the browser or AI code.

### S7-04 - Verify PayPal events and check payment status

**Code area:** `backend/src/syncally/api/` and payment reconciliation worker.

**Why:** A webhook or browser redirect alone does not prove that the full amount was paid.

**What to build:** Verify webhook signatures, save each event ID once, then schedule a PayPal status check. Compare PayPal's current amount/currency/status with the saved intent before updating it.

**Done when:**
- Tests reject invalid signatures and ignore duplicate events safely.
- Partial, pending, unknown, or mismatched payments never become paid.
- Old events cannot overwrite a newer checked status.
- Status, audit, and outbox updates commit together.

**Implementation:** `POST /webhooks/paypal/invoicing` verifies the transmission
with PayPal's Sandbox webhook-verification API, persists verified event IDs once,
and writes reconciliation work to the payment outbox in the same transaction.
The payment worker fetches the current invoice, checks its saved identity, amount,
currency and payment progress, then commits the guarded intent update, audit row,
webhook completion, and outbox completion together. Automated coverage uses fake
PayPal responses. Mismatches are audited and moved to manual action atomically
without changing the last trusted payment state. Stored webhook metadata omits
payer details. The live Sandbox webhook round trip remains an environment check.

**Stage check:** The Sandbox flow authorizes, creates, sends, and checks one invoice. Tests cover timeouts, duplicate webhooks, and partial payments.

## Stage 8 - Finish the Demo and Handoff

**Goal:** Show the saved agreement/payment status, test the full flow, and explain how to recover from failures.

### S8-01 - Generate draft commercial documents

**Code area:** `backend/src/syncally/application/` and document adapter if needed.

**Why:** Users need a useful document based on the agreed terms, without creating another editable source of truth.

**What to build:** Generate a clearly marked draft from the committed agreement. Include the agreement version. Do not claim legal/tax/customs compliance or guess missing terms. Add object storage only if the team has chosen how files should be saved.

**Done when:**
- Tests show the draft uses the committed terms and version.
- Editing a draft cannot change the agreement.
- Missing/unsupported terms are shown as missing, not guessed.

### S8-02 - Finish payment and document screens

**Code area:** `frontend/src/`.

**Why:** Users need to know whether a payment is waiting, partial, paid, or needs help.

**What to build:** Show the backend's payment status and safe document links. Do not use a browser redirect to decide payment status. Do not show invoice secrets or payment credentials.

**Done when:**
- UI tests cover loading, pending, partial, paid, error, and unavailable API states.
- A redirect/query string cannot mark a payment paid.
- Secret invoice links and credentials are not displayed in logs or page source.

### S8-03 - Test the full flow and access boundaries

**Code area:** backend integration tests and frontend end-to-end tests.

**Why:** Bugs often happen between components, especially around privacy, approval, retries, and payment.

**What to build:** Add one automated flow from deal creation through agreement and payment status. Use fake AI/PayPal services in normal tests. Keep the live Sandbox test optional.

**Done when:**
- Tests cover private data isolation for both organizations.
- Simultaneous approvals cannot create duplicate agreements or obligations.
- Repeated signals, outbox rows, webhooks, and worker restarts cannot create duplicate payment actions.
- The normal test suite needs no external account or API key.

**Implementation (issue #39):** `backend/tests/test_demo_lifecycle.py` drives the API,
agreement commit, payment outbox worker, and webhook reconciliation with in-memory SQLite and
fake AI, PayPal, and webhook adapters. It checks buyer/seller private-message isolation,
outsider access, exact bilateral approval, idempotent agreement/payment retries, provider
timeout recovery across worker instances, duplicate webhook handling, and payment status that
omits invoice IDs and payer details. `backend/tests/test_local_workflow_smoke.py` adds two
simultaneous commit requests against PostgreSQL and verifies one set of obligations, audit, and
outbox effects, plus Temporal recovery after a worker restart. The PostgreSQL/Temporal check is
opt-in; the normal suite needs no external services or credentials.

### S8-04 - Add safe logs and a recovery guide

**Code area:** logging/metrics setup and operations docs.

**Why:** Developers need to find stuck work and recover it without exposing customer data or making duplicate payments.

**What to build:** Add correlation IDs and useful status/retry information. Redact secrets, private prompts, and sensitive invoice links. Document how to inspect stuck outbox items, failed workflows, unknown PayPal results, bad webhooks, and payment mismatches.

**Done when:**
- Tests or captured logs prove sensitive values are hidden.
- The guide explains how to check state, retry safely, and escalate unresolved cases.
- The guide warns not to create a new PayPal request ID after an unclear timeout until the old request is checked.
- Health checks do not claim a dependency is healthy unless they actually check it.

**Implementation:** Standard-library allowlisted operational output is configured on
API and worker entrypoints. HTTP responses carry generated correlation UUIDs;
committed outbox/payment outcomes expose safe identifiers, status and retry timing.
Captured-output tests exercise privacy canaries and recovery-related boundaries.
The [operations guide](operations.md) documents health scope, guarded inspection and
recovery, unknown PayPal outcomes and webhook reconciliation limitations. Live
Sandbox and full-demo stage gates require separate environment verification.

**Final demo check:** A new developer can run the app locally with fake AI/PayPal services and complete the flow. The optional Sandbox test can complete one invoice. All privacy, approval, restart, and payment tests pass.

## Do Not Add to This First Build

These need a separate team decision:

- Live PayPal, multiple seller accounts, escrow, or other payment providers.
- General legal, tax, customs, or export compliance.
- Full accounting, ERP, inventory, shipping, refunds, and disputes.
- AI automatically approving agreements or starting payments.
- Microservices or Kubernetes.

## Design References

- [Deal, message, and approval rules](architecture/01-commercial-domain-model.md)
- [Temporal and outbox rules](architecture/02-temporal-deal-workflow-contract.md)
- [PayPal payment rules](architecture/03-paypal-payment-intent-lifecycle.md)
- [Architecture decisions](architecture/04-architecture-decision-record.md)
- [Architecture overview](../ARCHITECTURE.md)
