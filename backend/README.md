# SyncAlly backend

Python package for the HTTP API, application use cases, domain rules, adapters, and durable workflow processes.

The API exposes public health endpoints and protected deal reads. Protected requests use
HS256 bearer JWTs: the `sub` claim identifies the user, while active organization
memberships are loaded from the database for authorization. Organization or role claims
supplied by the browser are not trusted. Set `JWT_SECRET` to a cryptographically generated
secret containing at least 32 random bytes outside development/test, and optionally
`JWT_ISSUER` and `JWT_AUDIENCE`.
Access tokens expire after `ACCESS_TOKEN_TTL_MINUTES` (default 15 minutes).
Refresh tokens expire after `REFRESH_TOKEN_TTL_DAYS` (default 30 days).

Public self-registration is disabled. For the local demo, run
`python -m syncally.cli.seed_demo` from `backend/` after applying migrations. It creates the
buyer and seller demo accounts, their organizations, and active admin memberships. The
command prompts for passwords without echoing them, hashes them in the application, and is
limited to development/test environments. Running it again preserves existing passwords.
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
Product onboarding for new counterparties through an organization invitation and acceptance
flow is not implemented yet; the demo seed command is a separate local provisioning path.
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
`GET /deals/{deal_id}/facts` lists the reviewer's own facts plus shareable
counterparty facts. `POST /deals/{deal_id}/facts/{fact_id}/confirm`, `/reject`, and `/clarify`
advance a fact's review state, and only a member of the fact's owning organization may do so.
Review conflicts (a stale version or an invalid state change) return `409`. Message bodies are
never written to logs, and `422` validation errors are redacted so they do not echo submitted
request values back to the caller.
`POST /deals/{deal_id}/agreements` with `{ "proposal_id": "..." }` snapshots a saved proposal
into the deal's next `PENDING_APPROVAL` agreement version and returns its version number and
`terms_hash`. `POST /deals/{deal_id}/agreements/{version_number}/approve` and `/reject` record
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

From the backend directory, install the application and its test/lint tools with:

```powershell
python -m pip install -e ".[dev]"
```

Run the backend tests and lint checks from the backend directory:

```powershell
python -m unittest discover -s tests -v
python -m ruff check src tests
```

For a local PostgreSQL database, copy `.env.example` to `.env`, set `DATABASE_URL`, and
apply the schema from this directory:

```text
alembic upgrade head
```

This applies all migrations to the PostgreSQL database configured by `DATABASE_URL`.
The same command upgrades an existing database as well as creating a fresh schema.

Run the outbox relay separately after applying migrations:

```text
python -m syncally.cli.outbox_worker
```

Configure `TEMPORAL_ADDRESS`, `TEMPORAL_NAMESPACE`, and `TEMPORAL_TASK_QUEUE` in
the environment. The relay sends only deal/agreement IDs. Failed deliveries use
a persisted exponential retry delay with jitter (up to five minutes); malformed
events become `FAILED` for inspection. After correcting a failed event, reset its
status to `PENDING` and clear `next_attempt_at` to retry immediately.

To include the PostgreSQL concurrency test, set `TEST_POSTGRES_URL` to a test
database URL and run the test suite. The test creates and removes its own isolated
schema; the database user needs permission to create schemas. Temporal adapter
tests use a mocked client; live Temporal smoke testing remains part of S6-04.

See [the domain architecture](../docs/architecture/05-domain-layer.md) for implemented invariants, package boundaries, and remaining work. The domain types do not perform persistence, authenticated authorization, or external provider calls.

The S7-03 Sandbox invoice adapter and separate payment worker are implemented
against #34's saved-intent/outbox contract. They remain isolated until the Stage 6
integration gate is verified. See [the Sandbox worker contract and recovery guide](../docs/architecture/07-sandbox-invoice-worker.md)
for seller issuance authorization, environment configuration, startup commands,
retry behavior, test coverage, and manual recovery. Automated tests use a fake
provider or HTTP mock transport and require no PayPal credentials.
