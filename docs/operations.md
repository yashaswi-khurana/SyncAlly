# Safe operations and recovery

Use this guide for the local/demo API, Temporal workflow worker, Temporal outbox relay,
and PayPal Sandbox payment worker. PostgreSQL is the commercial source of truth.
A workflow outcome, browser redirect or webhook body does not prove payment.

## F11a explicit payment modes

Back up the intended database, stop/drain API payment writers and payment workers,
and prohibit demo resets during the upgrade. Apply 0017 after 0016, then restart
only updated writers/workers. Do not mix old writers with the immutable provider/mode
schema. The migration preserves payment history and both existing partial unique
indexes. Existing `PAYPAL` rows retain Sandbox routing and `LEGACY_UNVERIFIED`
evidence; every other historical provider remains unresolved, not retagged offline.
Unknown history requires explicit operator investigation, never ID-shape guessing.
Constraint/table operations take locks; plan a maintenance window.

Downgrade refuses if new routing/evidence or simulation observations would be lost.
Retain the schema and roll back compatible application code instead; never delete
payment history to force downgrade. The demo reset refusal remains unchanged even
for synthetic/offline payments. A SQLite ORM-initialized demo is not an Alembic
upgrade proof; older file-backed demo schemas are rejected, not silently migrated.

For a local persistent offline demo, configure both API and payment worker with:

```powershell
$env:APP_ENV = "development"
$env:PAYMENT_MODE = "OFFLINE_DEMO"
$env:DATABASE_URL = "sqlite:///C:/Proj/SyncAlly/backend/syncally-demo.db"
$env:PUBLIC_FRONTEND_URL = "http://localhost:5173"
```

Use the existing `seed_demo --offline` procedure privately to prepare missing local
credentials. Start the API with `python -m uvicorn syncally.api.main:app --host 127.0.0.1`
and the payment worker with `python -m syncally.cli.payment_worker` in separate
terminals with the same database path. Do not expose demo endpoints publicly.
Configuration/environment validation and current demo authorization enforce scope;
request Host/forwarded headers are not authorization. Neither process needs PayPal
or Gmail credentials for offline intents, and failures never activate fallback.

After bilateral approval/commit and seller authorization, inspect the returned
intent ID. Invoice dispatch only yields an unpaid offline reference. To simulate
progress, the active seeded demo admin must explicitly POST the protected
`/dev/payments/{intent_id}/simulate-reconciliation` command with:

```json
{"idempotency_key":"demo-paid-once","expected_version":4,"outcome":"PAID","paid_amount":"10"}
```

Replace the version and amount with freshly read saved values; the example grants
no authority. Pending requires zero, partial requires a strictly intermediate
amount, and paid requires the exact authorized total/currency. A `202` is queued
evidence only. Read status after worker completion and verify
`reconciliation_source=OFFLINE_DEMO`, `SIMULATION/OFFLINE_DEMO` audit, processed
observation and delivered outbox together. On stale/revoked/invalid evidence, the
worker records needs-action without changing payment truth. Replays retain exact
command identity; use a new key only for a genuinely new observation. No simulated
signature check or real webhook claim exists.

Sandbox setup is separate: choose `PAYMENT_MODE=PAYPAL_SANDBOX` for new intents and
provision Sandbox app/webhook credentials privately. Existing intents keep their
saved mode across configuration changes and restarts. The UI distinguishes simulated
payment, Sandbox (not production), and legacy/unknown evidence. Missing credentials
and uncertain provider outcomes require action/reconciliation, not offline conversion.

F11b live acceptance remains separately approved and unexecuted: actual Sandbox
create/send, Sandbox buyer payment, signature-verified webhook, fresh authenticated
provider reconciliation and persisted provenance must all be verified. Redirects,
fake adapter fixtures, queued commands and webhook bodies alone do not qualify.
F11a automated gates use SQLite/mock transports and no real services or credentials;
PostgreSQL trigger/locking execution and desktop/mobile two-party browser exercises
remain unverified. See [recorded F11a results](implementation-plan.md#f11a---explicit-payment-modes-implemented-review-ready).

## Migration 0014 transition

For an existing database, use a stopped, drained upgrade, not a mixed-version
deployment:

1. Disable all demo reset entrypoints (API and CLI). Stop and drain every old
   generic outbox relay, allowing in-flight external calls to complete before
   migration. Then stop the old API and reset tooling. Keep resets prohibited
   throughout the migration and restart transition.
2. If an old relay is killed while a request outcome is unknown, conservatively
   keep the affected demo blocked from reset until external history (including
   Temporal history where applicable) is verified. A legacy null
   `dispatch_started_at` is not proof that no external call occurred: old relays
   could make that call without recording it. Migration `0014` backfill cannot
   infer old in-flight attempts; do not fabricate dispatch history to clear the
   block.
3. From `backend/`, apply migration `0014` with `alembic upgrade head`. Do not run
   old relays, APIs or reset tooling alongside updated versions.
4. After migration succeeds, restart only the updated API and reset tooling with
   resets still blocked, then restart updated generic outbox relays. Only after
   this transition is complete may resets be re-enabled; retain the reset block
   for any affected demo whose unknown external outcome is still unverified.

## F5 persisted human negotiation

Apply migration 0016 only after 0015. Back up the database and drain old API writers
before `alembic upgrade head`; do not run old writers against new human rounds.
The migration adds scoped foreign keys, positive count/version/state checks, command
history and unique pending-candidate/terminal-action indexes. Existing inconsistent
cross-deal references, counts or duplicate pending candidates can prevent installation;
inspect and reconcile them explicitly, never discard or invent historical records.
Constraint/index installation takes locks; schedule a deployment window.
Downgrade refuses once human proposals or action history exist. Roll back application
code only while retaining the schema and keep incompatible old draft writers disabled.

The UI's Accept as candidate is not agreement approval. To replace a pending candidate,
acknowledge its exact displayed version/hash/source proposal, submit the next proposal,
and have the other party accept it. Old approvals remain historical; both parties must
approve the new candidate separately. A commit winner prevents replacement. On 409,
reload current truth and review it; do not retry with invented base/version values.
Keep the same command UUID for an unchanged uncertain retry, and rotate it for a new
action or changed payload. Replays still require current membership and completed F4
onboarding. Deadlines require explicit expiry; there is no background expiry service.

Required two-party walkthrough, on an approved existing test deployment:

1. Buyer submits reviewed terms; seller checks identical canonical terms/hash/history.
2. Seller counters; buyer accepts as candidate. Verify no approval/payment was implied.
3. Approve one side, explicitly replace with equal terms, then accept the new candidate.
   Verify its ID/version changed and both approval slots are empty.
4. In two tabs, race counters/acceptance and replacement versus approval/commit. Reload
   losers and verify one latest proposal/current candidate and no partial mutation.
5. Reject, supersede and explicitly expire an elapsed round; submit from each terminal
   base. Verify preserved history, round cap/escalation, pending-onboarding blocking,
   revoked memberships and private evidence redaction after switching organizations.
6. Repeat on desktop/mobile. Old-version workflow notifications must reload the current
   persisted agreement, not restore a superseded candidate.

Automated F5 checks are in the existing negotiation/migration, domain, agreement and
frontend review/client tests. With an explicitly approved `TEST_POSTGRES_URL`, the five
race tests and fresh migration test create UUID-named temporary schemas and remove only
those schemas afterward; the account needs CREATE/DROP SCHEMA privileges. Do not use a
production URL. Without that variable they skip. File-backed SQLite races run locally
but do not establish PostgreSQL correctness. See [the recorded gate results](implementation-plan.md#f5---persisted-human-negotiation-implemented-environment-gates-outstanding).

## Invitation URL configuration

Set `PUBLIC_FRONTEND_URL` in the backend environment to the deployed frontend base,
not the API URL. Development/test default to `http://localhost:5173`; if Vite uses a
different port, configure that port explicitly. All other environments fail startup
unless an explicit HTTPS URL with a public host is configured, for example:

```text
PUBLIC_FRONTEND_URL=https://app.syncally.trade
```

A safe base path such as `https://app.syncally.trade/portal/` is supported; trailing
slashes are removed before appending `/#/invite?token=<signed-token>`. The frontend
must be served at that base path. Credentials, query strings, fragments, blank or
malformed URLs, control characters, backslashes, traversal and encoded separators
are not permitted. Local/private IP literals and local hostnames are rejected
outside development/test. Proxy `Host`, `Forwarded` and `X-Forwarded-*` headers are
ignored when generating links; configure the destination explicitly and restart
the API after changing it. Verify a newly generated link's origin, base path and
`#/invite` route privately; do not paste invitation tokens into logs or tickets.

## Logging contract

The documented API invocation and each worker entrypoint configure standard-library
JSON console logs. The application generates a fresh UUID `X-Correlation-ID` for
every HTTP response, including validation, oversized-body and unhandled-error
responses. Caller-supplied IDs are ignored. Find its `http.completed` record by
`correlation_id`, `http_status` and `duration_ms`. Raw paths, query strings, headers,
request/response bodies and exception text are omitted. Successful deal routes also
include their validated `deal_id` when available.

Search worker records by `deal_id`, `workflow_id`, `payment_intent_id` and
`outbox_event_id`. These stable identifiers bridge processes; the ephemeral HTTP
correlation ID is not persisted into outbox rows. `outbox.completed` and
`payment_outbox.completed` describe committed delivery status, retry count and the
next attempt time. `payment.state_changed` describes committed payment state;
`workflow.activity_completed` includes the activity attempt and whether the reloaded
deal is terminal. Lease losers never claim successful delivery.

Only approved event names, canonical UUIDs, known statuses/error categories,
nonnegative integer counters and timestamps are emitted. Unknown messages, provider
error names, arguments, extra fields and exception chains become `log.redacted` with
severity/component only. This deliberately sacrifices arbitrary diagnostic prose.
Private prompts/messages, credentials, tokens, amounts, recipient emails, provider
invoice IDs and recipient invoice links must not be added to general logs. Use local
UUIDs in tickets. Keep any necessary provider inspection inside the restricted
operator session.

Supported commands, from `backend/` after installation/configuration:
# Safe Operations and Recovery

Use this guide for the local/demo API, Temporal workflow worker, Temporal outbox relay, and PayPal Sandbox payment worker. PostgreSQL is the commercial source of truth. A workflow outcome, browser redirect, or webhook body does not prove payment.

For ordered installation, migrations, interactive demo seeding, and process startup, start with the [root quickstart](../README.md#local-quickstart). The API, workflow worker, and relay support local conversation/agreement work; real Sandbox invoice processing additionally requires the payment worker with configured `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET`. Empty credentials make that worker exit; the API can still accept a durable payment request that awaits processing.

---

## Logging Contract

The documented API invocation and each worker entrypoint configure standard-library JSON console logs. The application generates a fresh UUID `X-Correlation-ID` for every HTTP response, including validation, oversized-body, and unhandled-error responses. Caller-supplied IDs are ignored. Find its `http.completed` record by `correlation_id`, `http_status`, and `duration_ms`. Raw paths, query strings, headers, request/response bodies, and exception text are omitted. Successful deal routes also include their validated `deal_id` when available.

Search worker records by `deal_id`, `workflow_id`, `payment_intent_id`, and `outbox_event_id`. These stable identifiers bridge processes; the ephemeral HTTP correlation ID is not persisted into outbox rows. `outbox.completed` and `payment_outbox.completed` describe committed delivery status, retry count, and next attempt time. `payment.state_changed` describes committed payment state; `workflow.activity_completed` includes the activity attempt and whether the reloaded deal is terminal. Lease losers never claim successful delivery.

Only approved event names, canonical UUIDs, known statuses/error categories, nonnegative integer counters, and timestamps are emitted. Unknown messages, provider error names, arguments, extra fields, and exception chains become `log.redacted` with severity/component only. This deliberately sacrifices arbitrary diagnostic prose. Private prompts/messages, credentials, tokens, amounts, recipient emails, provider invoice IDs, and recipient invoice links must not be added to general logs. Use local UUIDs in tickets. Keep any necessary provider inspection inside the restricted operator session.

Supported worker commands, from `backend/` after installation and configuration:

```bash
python -m uvicorn syncally.api.main:app
python -m syncally.workflows.worker
python -m syncally.cli.outbox_worker
python -m syncally.cli.payment_worker
```

Run each in its own terminal. The API replaces Uvicorn's existing handlers and disables its raw access logger; `http.completed` supplies safe request outcomes. Workers catch fatal runtime exceptions, log `worker.failed`, then exit nonzero without printing the exception. Supervise and restart failed processes after fixing the cause. Startup/import failures before logging configuration, Python/native stderr, reverse proxies, custom handlers installed later, external collectors, and Temporal server history are separate boundaries. Do not enable their raw body, query, SQL-parameter, prompt, or exception capture. Do not override the safe formatter with a deployment logging configuration. Existing historical logs/error details are not retroactively scrubbed; restrict access and apply your retention policy.

---

## Health and Initial Inspection

Verify application and service health:

<!-- slide -->
**POSIX (Linux / macOS / WSL):**
```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/database
docker compose -f infra/compose.yaml ps
```

**Windows (PowerShell):**
```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/health/database
docker compose -f infra/compose.yaml ps
```

Run Compose commands from the repository root. `/health` proves only that the API responds. `/health/database` acquires a connection and executes `SELECT 1`; a failure returns an error rather than claiming health. Neither checks Temporal, worker pollers, queue progress, PayPal, or Gmail. Check all four process supervisors and Temporal UI at `http://localhost:8233`; the configured namespace and task queue must match between relay and worker. PostgreSQL/Temporal startup and the optional restart smoke test are documented in [infra/README.md](../infra/README.md).

Use an access-controlled PostgreSQL session against the intended database. Inspect only IDs, state, and timing first. Replace each angle-bracket placeholder with an inspected local UUID. Avoid `SELECT *`, `payload`, `raw_payload`, `failure_detail`, `error_detail`, credentials, and provider references in exported diagnostics.

```sql
BEGIN READ ONLY;
SELECT id, aggregate_type, aggregate_id, event_type, status, retry_count,
       created_at, delivered_at, next_attempt_at
FROM outbox_events
WHERE status IN ('PENDING', 'PROCESSING', 'FAILED')
ORDER BY created_at, id LIMIT 100;

SELECT id, deal_id, payment_milestone_id, status,
       provider_create_started_at, last_checked_at, last_reconciled_at, version
FROM payment_intents WHERE id = '<intent-uuid>';

SELECT id, payment_intent_id, processed, received_at
FROM webhook_events WHERE payment_intent_id = '<intent-uuid>'
ORDER BY received_at DESC LIMIT 20;

SELECT id, aggregate_type, aggregate_id, event_type, actor_type,
       occurred_at, recorded_at
FROM audit_events WHERE aggregate_id = '<intent-uuid>'
ORDER BY occurred_at DESC LIMIT 20;
COMMIT;
```

---

## Stuck Outbox and Workflows

| Work | Owner | Normal Recovery |
| --- | --- | --- |
| `AGREEMENT_COMMITTED`, `DEAL_NOTIFICATION` | Temporal outbox relay | `PENDING` retries when due; bounded exponential jitter up to 300 seconds. PostgreSQL claim locks release on crash. |
| `PAYMENT_INTENT_AUTHORIZED`, `PAYPAL_WEBHOOK_RECONCILIATION` | Payment worker | A `PROCESSING` lease lasts five minutes. Expired leases are reclaimed. `PENDING` retries when due with the same bounded jitter. |
| `FAILED` | Operator/maintainer | Inspect and fix the permanent cause before any same-row replay. Do not mass requeue. |

If due work remains unchanged, verify its owning process is running and can connect. Check `worker.connection_retry`, `worker.connection_failed`, `worker.failed`, and the row's retry timing. Do not reset a live payment lease. Restarting the worker lets it reclaim expired work without inventing a new operation.

For a corrected **Temporal relay** failure, stop that relay, inspect exactly one row and its current database state, and use a guarded transaction. Preserve its ID, payload, and retry history. This is an operator SQL procedure, not a public API.

```sql
BEGIN;
SELECT id, status, event_type FROM outbox_events
WHERE id = '<event-uuid>' FOR UPDATE;
UPDATE outbox_events
SET status = 'PENDING', next_attempt_at = NULL, error_detail = NULL
WHERE id = '<event-uuid>' AND status = 'FAILED'
  AND event_type IN ('AGREEMENT_COMMITTED', 'DEAL_NOTIFICATION');
-- Commit only after confirming exactly one inspected row was updated.
-- Otherwise ROLLBACK and investigate.
COMMIT;
```

Restart the relay and verify the same event becomes `DELIVERED`, then verify workflow/activity progress and authoritative database state. Signal-with-start uses `deal/<deal-uuid>/lifecycle`; duplicate delivery must retain that workflow identity. A `DELIVERED` relay event means Temporal accepted it, not that the activity finished. In Temporal UI inspect run status, pending/failed activities, retry attempts, and `processed_notification_count`. Correct the actual database/configuration problem before retrying a failed activity or considering a history reset. Do not terminate, reset, or start a new workflow to force commercial state. `WAIT_EXPIRED` is an operational outcome, not deal cancellation or payment rejection. Escalate an exhausted activity, unexpected history, or repeated expiry with safe IDs and timeline.

---

## Failed Request Versus Unknown PayPal Outcome

A definitive rejection can require operator action. A lost response, timeout, or worker crash during a provider POST is **unknown**, even if the caller saw an error. Never create a new payment intent, invoice number, idempotency key, or PayPal request ID to recover an unclear timeout. Never reset an unknown intent to `AUTHORIZED`, delete audit/idempotency records, clear its payload hash, or replace its original `provider_create_started_at`.

1. Inspect the existing intent and authorization outbox ID. Resume its existing `PENDING` / expired `PROCESSING` work with the payment worker.
2. Recovery turns `CREATE_PENDING` into `CREATE_UNKNOWN` and searches PayPal by the same stable invoice number, validating identity. Lookup failure remains unresolved and cannot authorize a new create. A found invoice is attached and reused.
3. Only a verified no-match, unchanged request hash, known original create time, and the existing 44-day safety window permit the **same intent/stable request ID** to retry creation. This is the application's guarded behavior, not permission for a manual provider POST.
4. Missing timestamp, elapsed window, changed terms/contact payload, multiple matches, or conflicting provider identity require maintainer/provider-account inspection. Keep the unknown state and stop any manual retry until reconciliation establishes what happened. Do not guess absence from an empty browser screen.

If the authorization event is `FAILED`, a maintainer must classify the failure and confirm that replaying that exact intent is safe after fixing the cause. There is no packaged manual payment retry/reconciliation CLI or endpoint. Do not apply the Temporal requeue SQL to payment events. A definitive failed intent may still need provider inspection before a new business request is authorized.

`PROVIDER_CREATED` retains its provider invoice before send. A send timeout fetches current provider status before another send; it never creates a second invoice. Gmail copy failures may retry independently through the existing outbox and cannot justify recreating or resending the PayPal invoice. Gmail delivery can duplicate when SMTP accepted a message but its acknowledgement was lost. The one-off `python -m syncally.cli.email_invoice INV2-...` command sends only a Gmail copy of an existing invoice; it is not a payment recovery or status-reconciliation command.

---

## Webhooks, Payment Mismatches, and Escalation

Webhook intake is `POST /webhooks/paypal/invoicing`. Missing/invalid signatures or malformed events return 400. Missing configuration or temporary verification/storage failure returns 503; a permanent provider verification failure returns 502. Check the Sandbox REST app, endpoint, secret-store configuration, and `PAYPAL_WEBHOOK_ID` privately. Never print signature headers, tokens, or bodies, and never disable verification to clear a backlog. Let PayPal redeliver eligible events after repair.

Each verified provider event ID is saved once. A known invoice schedules a fresh provider read. The payment worker compares saved invoice identity, amount, currency, and current payment progress; partial/pending/unknown/mismatched responses cannot prove full payment. A mismatch records manual action atomically and retains the last trusted payment state. Escalate with local intent/event IDs, timestamps, and approved error categories. Never edit payment status to `PAID` or change the authorized amount or currency to match an unexpected response.

Two existing limits require maintainer involvement:
- A webhook received before its invoice is attached is saved as processed without reconciliation work. Replaying that duplicate does not schedule a later check.
- Failed mismatch reconciliation marks its webhook processed. Merely resetting its outbox row cannot perform a fresh reconciliation. Use a new legitimately verified event or a separately reviewed maintainer repair that fetches current provider state; no general manual enqueue tool exists today.

Escalate when automatic retries make no progress, configuration cannot be verified, a provider outcome remains unknown, or history/state disagree. Record local UUIDs, first/last observation time, status, retry count, next attempt time, process/version, and actions already taken. Keep customer/provider evidence in restricted systems.

---

## F4 counterparty onboarding

Apply `0015_counterparty_onboarding` after `0014_outbox_dispatch_started_at`, before
deploying the updated API/UI. Stop old API writers for the transition; do not mix old and
new onboarding writers. If crossing 0014, follow the existing [0014 transition](#migration-0014-transition)
first, including draining relays and prohibiting resets for unknown external outcomes.
Run `alembic upgrade head` from `backend/` against the intended PostgreSQL database.
No existing organizations or deals are adopted as pending. Keep binding records and old
INACTIVE shells private; do not delete them to clear a used/stale invitation.

The 0015 downgrade refuses when any onboarding history exists, including consumed rows.
Retain the schema and use a compatible application rollback in that case; never bypass
the refusal. An empty onboarding table can downgrade to 0014. Legacy invitations retain
their established bearer semantics; the updated UI issues recipient-bound TEAM tokens,
and counterparty creation issues exact buyer/deal/shell bindings.

Two-person acceptance, using separate browser profiles and real accounts:

1. Buyer signs in as an ACTIVE ADMIN, opens New deal, selects Invite counterparty, and
   supplies the recipient email and company display details. Copy the generated URL;
   no email delivery is performed or implied.
2. Verify the DRAFT deal says Awaiting counterparty. Prepare human draft text/facts;
   sending, thread import, and proposal/agreement actions must remain unavailable.
   The shell must not appear in directory search, pagination, or public ID lookup.
3. Recipient opens the URL in their own profile. A matching existing account must sign
   in with valid credentials; a new account supplies the matching signup email/password
   and its own company legal name/country. A wrong signed-in account must fail.
4. After acceptance, verify refreshed membership, navigation to the same server-returned
   deal, SELLER access under the recipient's separate organization, and retained BUYER
   access. Send a seller response and use the existing human review flow. Do not use
   development role switching. Acceptance must not create approval/payment state.
5. Reopen the used link and confirm rejection. Change invitation links while a request
   is in flight and sign out during refresh; old results must not navigate or restore
   memberships. Team invitations instead join the inviting organization as MEMBER.

Recipient address matching and signed-token possession are capabilities, not verified
mailbox ownership. There is no `email_verified` claim or email service. Before production
team access, add separately reviewed mailbox/recipient verification. Do not log or publish
invitation URLs, tokens, or recipient metadata. Expired, used, wrong-account, revoked-inviter,
quota, or stale-party failures require correcting the account/state, not changing database
parties or forging a replacement binding; automated reissue/cancellation is not part of F4.

Set `TEST_POSTGRES_URL` privately to an isolated PostgreSQL test database with schema-create
permission, then run the existing invitation and counterparty-migration test modules. They
create/drop UUID-named schemas and prove simultaneous acceptance rollback, acceptance versus
message writer locking, and fresh upgrade/empty downgrade. Without that URL these three
tests skip; SQLite and 0014-to-0015 PostgreSQL SQL generation do not prove PostgreSQL locks.
The historical full migration chain cannot execute on SQLite or generate entirely offline
because earlier revisions use PostgreSQL/data reads. Run fresh upgrade on PostgreSQL.
The two-person browser walkthrough is an additional environment gate, not a unit-test claim.

### F4 validation record (2026-10-31)

- Focused backend: 138 tests, 0 failures, 0 errors, 9 skips. The initial 22-test
   failure-focused rerun also passed without skips.
- Full backend: 629 tests, 0 failures, 0 errors, 20 skips. Discovery imported with
   `APP_ENV=test`; all environment variables corresponding to `Settings.model_fields`
   were removed before executing tests. Logging remained enabled. Migration tests isolate
   Alembic's logging configuration so later application log assertions remain meaningful.
- Backend lint: `ruff check src tests` passed, as did explicit lint of migrations
   0012-0015. A broader `ruff check backend` still reports import ordering in untouched
   historical files `alembic/env.py` and `alembic/versions/0001_initial_schema.py`.
- Frontend: focused onboarding tests 212/212, full suite 328/328, `lint:check`, and
   production build passed. Three existing payment-panel lint warnings and the large
   Three.js chunk warning remain. `git diff --check` passed.
- Unexecuted: PostgreSQL simultaneous acceptance and acceptance/message races in
   `test_organization_invitations.py`, and fresh upgrade/empty downgrade in
   `test_counterparty_onboarding_migration.py`, because `TEST_POSTGRES_URL` is unset.
   Other skips comprise seven existing PostgreSQL cases, one PostgreSQL/Temporal smoke
   case, and nine Temporal cases whose test-server download returned HTTP 403.
- The real two-person browser walkthrough was not run; no services, live provider calls,
   email delivery, or development role switching were used. Independent review and those
   environment gates remain required before production sign-off.

## Verification and remaining deployment gates
## Demo and Simulation Boundaries

The role switcher requires a seeded demo administrator session and server `APP_ENV=development` or `test`. Browser visibility (`VITE_ENABLE_DEV_SWITCHER` or Vite development mode) never grants server authority. Reset Demo Data deletes only deals whose two parties are seeded demo organizations and their related records; it does not cancel PayPal invoices or clear Temporal history. Do not use reset as payment recovery.

From an activated terminal in `backend/` with a valid local configuration:

<!-- slide -->
**POSIX (Linux / macOS / WSL):**
```bash
python -m syncally.cli.simulate_deal_flow --ci --no-color
```

**Windows (PowerShell):**
```powershell
$env:PYTHONUTF8 = "1"
python -m syncally.cli.simulate_deal_flow --ci --no-color
```

This uses an isolated in-memory SQLite/FastAPI harness. It exercises the seven-step application lifecycle without launching PostgreSQL, Temporal, payment workers, or PayPal. It may print a simulated invoice URL; exit 0 does not establish delivery or payment. Network mode targets `--base-url` (or `SYNCALLY_API_URL`) using `BUYER_PASSWORD` and `SELLER_PASSWORD`; it falls back to the isolated harness if its API health probe fails. Read the printed mode and verify the intended environment. Network runs create real records in the target database and may queue work for an already-running payment worker.

In the app, use payment status/last-check time and available retry diagnostics as observations, not proof that a worker is progressing. An invoice link opens the provider invoice; verify its current state through the worker's reconciled records. The UI does not supply a manual retry API. Continue using the unknown-outcome and webhook procedures above for stalled or ambiguous work.

---

## Verification and Remaining Deployment Gates

From `backend/`, run the documented suite and linter:

```bash
python -m unittest discover -s tests -v
python -m ruff check src tests
```

`test_operations.py` captures configured output with secret/private/link canaries through request, workflow dispatch, payment retry, and fatal worker paths. Existing payment tests cover unknown-create lookup before retry, stable identities, duplicate webhooks, and mismatches. Follow [the infrastructure guide](../infra/README.md) for PostgreSQL locking and restart checks. Fake-provider tests do not establish the Stage 7 live Sandbox authorize/create/send/reconcile gate. Verify that environment gate and the full demo separately; no whole-project or zero-defect claim follows from these checks.
