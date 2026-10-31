# Safe operations and recovery

Use this guide for the local/demo API, Temporal workflow worker, Temporal outbox relay,
and PayPal Sandbox payment worker. PostgreSQL is the commercial source of truth.
A workflow outcome, browser redirect or webhook body does not prove payment.

For ordered installation, migrations, interactive demo seeding and all process
terminals, start with the [root quickstart](../README.md#local-quickstart). The API,
workflow worker and relay support local conversation/agreement work; real Sandbox
invoice processing additionally requires the payment worker with configured
`PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET`. Empty credentials make that worker
exit; the API can still accept a durable payment request that awaits processing.

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

```powershell
python -m uvicorn syncally.api.main:app
python -m syncally.workflows.worker
python -m syncally.cli.outbox_worker
python -m syncally.cli.payment_worker
```

Run each in its own terminal. The API replaces Uvicorn's existing handlers and
disables its raw access logger; `http.completed` supplies safe request outcomes.
Workers catch fatal runtime exceptions, log `worker.failed`, then exit nonzero
without printing the exception. Supervise and restart failed processes after fixing
the cause. Startup/import failures before logging configuration, Python/native
stderr, reverse proxies, custom handlers installed later, external collectors and
Temporal server history are separate boundaries. Do not enable their raw body,
query, SQL-parameter, prompt or exception capture. Do not override the safe formatter
with a deployment logging configuration. Existing historical logs/error details
are not retroactively scrubbed; restrict access and apply your retention policy.

## Health and initial inspection

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/health/database
docker compose -f infra/compose.yaml ps
```

Run Compose commands from the repository root. `/health` proves only that the API
responds. `/health/database` acquires a connection and executes `SELECT 1`; a failure
returns an error, rather than claiming health. Neither checks Temporal, worker
pollers, queue progress, PayPal or Gmail. Check all four process supervisors and
Temporal UI at `http://localhost:8233`; the configured namespace and task queue must
match between relay and worker. PostgreSQL/Temporal startup and the optional restart
smoke test are documented in [infra/README.md](../infra/README.md).

Use an access-controlled PostgreSQL session against the intended database. Inspect
only IDs, state and timing first. Replace each angle-bracket placeholder with an
inspected local UUID. Avoid `SELECT *`, `payload`, `raw_payload`, `failure_detail`,
`error_detail`, credentials and provider references in exported diagnostics.

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

## Stuck outbox and workflows

| Work | Owner | Normal recovery |
| --- | --- | --- |
| `AGREEMENT_COMMITTED`, `DEAL_NOTIFICATION` | Temporal outbox relay | `PENDING` retries when due; bounded exponential jitter up to 300 seconds. PostgreSQL claim locks release on crash. |
| `PAYMENT_INTENT_AUTHORIZED`, `PAYPAL_WEBHOOK_RECONCILIATION` | Payment worker | A `PROCESSING` lease lasts five minutes. Expired leases are reclaimed. `PENDING` retries when due with the same bounded jitter. |
| `FAILED` | Operator/maintainer | Inspect and fix the permanent cause before any same-row replay. Do not mass requeue. |

If due work remains unchanged, verify its owning process is running and can connect.
Check `worker.connection_retry`, `worker.connection_failed`, `worker.failed` and the
row's retry timing. Do not reset a live payment lease. Restarting the worker lets it
reclaim expired work without inventing a new operation.

For a corrected **Temporal relay** failure, stop that relay, inspect exactly one
row and its current database state, and use a guarded transaction. Preserve its ID,
payload and retry history. This is an operator SQL procedure, not a public API.

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

Restart the relay and verify the same event becomes `DELIVERED`, then verify
workflow/activity progress and authoritative database state. Signal-with-start uses
`deal/<deal-uuid>/lifecycle`; duplicate delivery must retain that workflow identity.
A `DELIVERED` relay event means Temporal accepted it, not that the activity finished.
In Temporal UI inspect run status, pending/failed activities, retry attempts and
`processed_notification_count`. Correct the actual database/configuration problem
before retrying a failed activity or considering a history reset. Do not terminate,
reset or start a new workflow to force commercial state. `WAIT_EXPIRED` is an
operational outcome, not deal cancellation or payment rejection. Escalate an exhausted
activity, unexpected history or repeated expiry with the safe IDs and timeline.

## Failed request versus unknown PayPal outcome

A definitive rejection can require operator action. A lost response, timeout or
worker crash during a provider POST is **unknown**, even if the caller saw an error.
Never create a new payment intent, invoice number, idempotency key or PayPal request
ID to recover an unclear timeout. Never reset an unknown intent to `AUTHORIZED`,
delete audit/idempotency records, clear its payload hash or replace its original
`provider_create_started_at`.

1. Inspect the existing intent and authorization outbox ID. Resume its existing
   `PENDING`/expired `PROCESSING` work with the payment worker.
2. Recovery turns `CREATE_PENDING` into `CREATE_UNKNOWN` and searches PayPal by the
   same stable invoice number, validating identity. Lookup failure remains unresolved
   and cannot authorize a new create. A found invoice is attached and reused.
3. Only a verified no-match, unchanged request hash, known original create time and
   the existing 44-day safety window permit the **same intent/stable request ID** to
   retry creation. This is the application's guarded behavior, not permission for
   a manual provider POST.
4. Missing timestamp, elapsed window, changed terms/contact payload, multiple matches
   or conflicting provider identity require maintainer/provider-account inspection.
   Keep the unknown state and stop any manual retry until reconciliation establishes
   what happened. Do not guess absence from an empty browser screen.

If the authorization event is `FAILED`, a maintainer must classify the failure and
confirm that replaying that exact intent is safe after fixing the cause. There is no
packaged manual payment retry/reconciliation CLI or endpoint. Do not apply the
Temporal requeue SQL to payment events. A definitive failed intent may still need
provider inspection before a new business request is authorized.

`PROVIDER_CREATED` retains its provider invoice before send. A send timeout fetches
current provider status before another send; it never creates a second invoice.
Gmail copy failures may retry independently through the existing outbox and cannot
justify recreating or resending the PayPal invoice. Gmail delivery can duplicate
when SMTP accepted a message but its acknowledgement was lost. The one-off
`python -m syncally.cli.email_invoice INV2-...` command sends only a Gmail copy of
an existing invoice; it is not a payment recovery or status-reconciliation command.

## Webhooks, payment mismatches and escalation

Webhook intake is `POST /webhooks/paypal/invoicing`. Missing/invalid signatures or
malformed events return 400. Missing configuration or temporary verification/storage
failure returns 503; a permanent provider verification failure returns 502. Check
the Sandbox REST app, endpoint, secret-store configuration and `PAYPAL_WEBHOOK_ID`
privately. Never print signature headers, tokens or bodies, and never disable
verification to clear a backlog. Let PayPal redeliver eligible events after repair.

Each verified provider event ID is saved once. A known invoice schedules a fresh
provider read. The payment worker compares saved invoice identity, amount, currency
and current payment progress; partial/pending/unknown/mismatched responses cannot
prove full payment. A mismatch records manual action atomically and retains the last
trusted payment state. Escalate with local intent/event IDs, timestamps and approved
error categories. Never edit payment status to `PAID` or change the authorized amount
or currency to match an unexpected response.

Two existing limits require maintainer involvement:

- A webhook received before its invoice is attached is saved as processed without
  reconciliation work. Replaying that duplicate does not schedule a later check.
- Failed mismatch reconciliation marks its webhook processed. Merely resetting its
  outbox row cannot perform a fresh reconciliation. Use a new legitimately verified
  event or a separately reviewed maintainer repair that fetches current provider
  state; no general manual enqueue tool exists today.

Escalate when automatic retries make no progress, configuration cannot be verified,
a provider outcome remains unknown or history/state disagree. Record local UUIDs,
first/last observation time, status, retry count, next attempt time, process/version
and actions already taken. Keep customer/provider evidence in restricted systems.

## Demo and simulation boundaries

The role switcher requires a seeded demo administrator session and server
`APP_ENV=development` or `test`. Browser visibility (`VITE_ENABLE_DEV_SWITCHER` or
Vite development mode) never grants server authority. Reset Demo Data deletes only
deals whose two parties are seeded demo organizations and their related records;
it does not cancel PayPal invoices or clear Temporal history. Do not use reset as
payment recovery.

From activated `backend/` with a valid local configuration:

```powershell
$env:PYTHONUTF8 = "1"
python -m syncally.cli.simulate_deal_flow --ci --no-color
```

This uses an isolated in-memory SQLite/FastAPI harness. It exercises the seven-step
application lifecycle without launching PostgreSQL, Temporal, payment workers or
PayPal. It may print a simulated invoice URL; exit 0 does not establish delivery
or payment. Network mode targets `--base-url` (or `SYNCALLY_API_URL`) using
`BUYER_PASSWORD` and `SELLER_PASSWORD`; it falls back to the isolated harness if its
API health probe fails. Read the printed mode and verify the intended environment.
Network runs create real records in the target database and may queue work for an
already-running payment worker.

In the app, use payment status/last-check time and available retry diagnostics as
observations, not proof that a worker is progressing. An invoice link opens the
provider invoice; verify its current state through the worker's reconciled records.
The UI does not supply a manual retry API. Continue using the unknown-outcome and
webhook procedures above for stalled or ambiguous work.

## Verification and remaining deployment gates

From `backend/` run the documented suite and lint:

```powershell
python -m unittest discover -s tests -v
python -m ruff check src tests
```

`test_operations.py` captures configured output with secret/private/link canaries
through request, workflow dispatch, payment retry and fatal worker paths. Existing
payment tests cover unknown-create lookup before retry, stable identities, duplicate
webhooks and mismatches. Follow [the infrastructure guide](../infra/README.md) for
PostgreSQL locking and restart checks. Fake-provider tests do not establish the
Stage 7 live Sandbox authorize/create/send/reconcile gate. Verify that environment
gate and the full demo separately; no whole-project or zero-defect claim follows
from these checks.
