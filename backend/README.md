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

Demo accounts are provisioned by an operator; public self-registration is not part of this
slice. `POST /auth/login` accepts `{ "email": "...", "password": "..." }` and returns
an access token and refresh token for an active account. Passwords are stored as scrypt
hashes. Invalid credentials and inactive or missing accounts receive the same `401`
response. `POST /auth/dev-login` is an optional shortcut for the configured local
development identity when `DEV_AUTH_USER_ID` and the matching `X-Dev-User-Id` header are
supplied.
After signing in, `POST /organizations` creates an organization and makes the caller its
first active admin. `GET /organizations` lists only the caller's active memberships.
An organization admin can use
`POST /organizations/{organization_id}/members` with an existing active user's email to
add that account as a regular member. Accounts must be provisioned by an operator first;
the endpoint does not create accounts or allow callers to choose another user's role.
`POST /auth/refresh` accepts a refresh token, rotates it, and returns a new access
token and refresh token. Refresh tokens are opaque and stored only as hashes.
Each refresh token can be used once. Replaying any rotated token, including a concurrent
or delayed retry, is treated as reuse of a leaked credential: the whole token family is
revoked and the request receives `401`. Clients should serialize refresh requests and
sign in again if a refresh response is lost. Rotation state is committed together, so a
failed rotation does not leave a replacement token partially saved.

For local development/test only, `DEV_AUTH_USER_ID` may be configured and sent as
`X-Dev-User-Id`; this shortcut is rejected by configuration outside those environments.

The domain package contains framework-independent foundations for deals, negotiation,
canonical trade terms, bilateral agreement approval, and payment intent state.

Install from the repository root with `python -m pip install -e ./backend`.

For a local PostgreSQL database, copy `.env.example` to `.env`, set `DATABASE_URL`, and
apply the schema from this directory:

```text
alembic upgrade head
```

See [the domain architecture](../docs/architecture/05-domain-layer.md) for implemented invariants, package boundaries, and remaining work. The domain types do not perform persistence, authenticated authorization, or external provider calls.
