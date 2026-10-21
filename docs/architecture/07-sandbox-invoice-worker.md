# Sandbox invoice issuance (S7-03 / #35)

Implementation against the saved-intent/outbox contract in #34 and the USD,
one-item, full-payment demo defaults in #8. This is isolated contract code;
Stage 7 integration is **not verified**: #30, #31, and #32 were open on
2026-10-20. The Stage 6 exit check in `docs/implementation-plan.md` remains
required before enabling the Sandbox process. No automatic API/Temporal hookup
is added. Webhook verification and settlement reconciliation belong to #36.

## Boundary and focused contract extension

`application/invoicing.py` defines the invoice client/evidence/failure port.
`infrastructure/paypal/adapter.py` implements OAuth and Invoicing v2 HTTP against
only `https://api-m.sandbox.paypal.com`. `fake.py` implements the same port without
keys or network. `worker.py` consumes only `PAYMENT_INTENT_AUTHORIZED` events.

The existing #34 authorization records a **payer** member, not seller issuance
approval. It must not implicitly authorize sending an invoice. Pending #33's
authenticated seller command, `authorize_sandbox_issuance` is a trusted operator
seam: validate an active seller actor, committed terms, intent, milestone, and
server-configured merchant/recipient binding, then freeze the exact invoice
request and request hash in the existing outbox transaction and audit the actor.
The CLI is an operator tool, not a user authentication mechanism. Do not expose
its user ID argument directly through an HTTP request. The future API must derive
that actor from verified authentication and enforce issuance permission.

This story proposes the smallest contract extension: retain #34's payer fields,
add explicit seller issuance approval of the exact request, and use
`SEND_UNKNOWN` plus nonterminal `FAILED_REQUIRES_ACTION` for recoverable issuance
and manual review. The existing active-milestone index includes these states,
so an ambiguous/manual operation continues blocking a replacement invoice.
#33 should incorporate these states in its domain contract before integration.
No change to issue #8's product defaults is necessary.

The request snapshot contains only the invoice fields needed to reproduce the
approved obligation, including the Sandbox emails. It is server-side data and
is not forwarded to Temporal or AI. Tokens/client secrets are never persisted.
Existing #34 outbox columns provide the lease, attempt count and retry schedule;
no migration is necessary.

## Processing and recovery

1. Claim the event using PostgreSQL `FOR UPDATE SKIP LOCKED` plus a conditional
   update; persist a claim token, five-minute lease, attempt count, and an unknown
   create state **before** network I/O. Commit and close the session.
2. Create the draft from the frozen, revalidated committed terms. Derive separate
   stable UUID operation IDs for create and send from the saved intent ID. The
   create request includes `PayPal-Request-Id`. Never rely on its retention for
   recovery. Send's endpoint does not document that header; its application ID
   is saved locally and a GET precedes every send attempt.
3. On a later dispatch, GET the draft and compare ID, invoice number, full intent
   reference, total, currency, seller email and sole recipient before sending.
   Send acknowledgment queues another check; only a GET establishes `SENT`.
4. Timeout, 5xx, malformed create acknowledgment, or a crash after mutation leaves
   an unknown state. A known invoice is fetched; an unknown create is searched
   by stable invoice number, then an exact match is fetched and validated.
   **An empty search is not definitive absence. Never automatically recreate it.**
5. Explicit pre-mutation rejection (429 or failed token acquisition) may retry
   create with the same operation ID. Persist exponential backoff (2–256 seconds)
   and stop after eight claims. Permanent errors, mismatched evidence, unknown
   statuses and exhausted recovery move the event to `FAILED` and intent to
   `FAILED_REQUIRES_ACTION`, with fixed sanitized codes.
6. A claim token plus locked version check prevents a stale worker from applying
   its result over a newer command. An expired claim is reconciled. The HTTP
   client's individual timeouts are 15 seconds; searches fetch at most one exact
   invoice and reject multiple hits. No provider call holds a DB transaction.

The worker never sets `PAID` or trusts a webhook/browser redirect. A provider
paid/partial/pending status establishes that issuance has happened; receipt
amount and settlement remain the responsibility of #36. Unrecognized statuses
require review. There is no production payment support.

## Operator procedure (after the stage gate)

Use Sandbox credentials from the seller-controlled demo business account.
Inject these environment variables through your local secret environment:

- `PAYPAL_SANDBOX_CLIENT_ID`, `PAYPAL_SANDBOX_CLIENT_SECRET`
- `PAYPAL_SANDBOX_SELLER_ORGANIZATION_ID`, `PAYPAL_SANDBOX_BUYER_ORGANIZATION_ID`
- `PAYPAL_SANDBOX_SELLER_EMAIL`, `PAYPAL_SANDBOX_BUYER_EMAIL`

Emails must identify the corresponding Sandbox merchant and personal recipient.
Credentials have secret-value representations, are not CLI arguments, and have
no configurable live API origin. HTTP redirects/environment proxies are disabled.
The adapter cannot determine whether a supplied secret was provisioned in live
or Sandbox, so operators must supply Sandbox keys; live keys will not authorize
the fixed Sandbox host. Do not enable HTTP wire logging.

From `backend/`, apply `alembic upgrade head`, save an intent through #34's
application contract, and authorize its exact issuance **before starting the
poller**:

```sh
python -m syncally.cli.payment_worker --stage-gate-verified \
  --authorize-intent <saved-intent-uuid> --seller-user-id <active-seller-user-uuid>
python -m syncally.cli.payment_worker --stage-gate-verified
```

The flag attests that the operator verified #29–#32 and Stage 6's exit check;
it is not proof generated by this implementation. The process refuses to start
without it. It is never started by importing or running the API.

For manual review, stop the poller and inspect the fixed `failure_code` and
PayPal's current invoice in the designated Sandbox merchant account. Search using
the saved invoice number and full intent reference; validate recipient, currency
and amount. Never change operation IDs or insert a replacement intent to escape
an unknown result. If a matching invoice exists, preserve its ID and resume at
`PROVIDER_CREATED` / reconciliation. Only after establishing that no invoice was
created may an operator resume `AUTHORIZED` with the original request and IDs.
After resolving the reason, reset the same event to `PENDING`, clear
`next_attempt_at`, and reset `retry_count` to zero under a controlled database
transaction; increment the intent version and add an operator audit record.
There is deliberately no blind automatic reset command. If evidence cannot
resolve the result, keep the operation blocked for manual investigation.

## Verification

Run `python -m unittest discover -s tests -v` and `python -m ruff check src tests`
from `backend/`. `test_paypal_worker.py` uses real committed-agreement persistence
and a stateful fake provider. It checks normal issuance, duplicate delivery,
create/send timeout, crash recovery, stable retries, bounded unresolved recovery,
manual failures, unauthorized/revoked seller, changed commitments/bindings,
provider mismatches, stale writes and the no-network-in-transaction invariant.
`test_paypal_adapter.py` exercises HTTP/OAuth, endpoint/header behavior, timeout
classification, malformed evidence, redaction, fixed origin and search using
`httpx.MockTransport`. No automated test needs PayPal keys or internet.

Passing tests provide evidence for these cases, not proof of zero possible
errors. A real Sandbox smoke run and the prior-stage exit gate remain release
checks; they have not been claimed as completed here.

## Provider references

- [Create draft invoice](https://developer.paypal.com/api/invoicing/v2/invoices-create/)
- [Send invoice](https://developer.paypal.com/api/invoicing/v2/invoices-send/)
- [PayPal request IDs](https://developer.paypal.com/api/make-api-requests/)
- [Invoicing v2, including search and invoice details](https://developer.paypal.com/api/invoicing/v2/)

The generic PayPal request guide recommends request IDs for POST; the endpoint
schema does not promise idempotency retention for these operations. Local
uniqueness and conservative reconciliation are therefore required regardless
of the header.
