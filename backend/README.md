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

See [the domain architecture](../docs/architecture/05-domain-layer.md) for implemented invariants, package boundaries, and remaining work. The domain types do not perform persistence, authenticated authorization, or external provider calls.
