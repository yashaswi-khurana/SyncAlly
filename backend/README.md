# SyncAlly backend

Python package for the HTTP API, application use cases, domain rules, adapters, and durable workflow processes.

The API exposes public health endpoints and protected deal reads. Protected requests use
HS256 bearer JWTs: the `sub` claim identifies the user, while active organization
memberships are loaded from the database for authorization. Organization or role claims
supplied by the browser are not trusted. Set `JWT_SECRET` (at least 32 characters outside
development/test), and optionally `JWT_ISSUER` and `JWT_AUDIENCE`.
Access tokens expire after `ACCESS_TOKEN_TTL_MINUTES` (default 15 minutes).
Refresh tokens expire after `REFRESH_TOKEN_TTL_DAYS` (default 30 days).

`POST /auth/refresh` accepts a refresh token, rotates it, and returns a new access
token and refresh token. Refresh tokens are opaque, stored only as hashes, and are
revoked as a family if a previously rotated token is reused.

For local development/test only, `DEV_AUTH_USER_ID` may be configured and sent as
`X-Dev-User-Id`; this shortcut is rejected by configuration outside those environments.

The domain package contains framework-independent foundations for deals, negotiation,
canonical trade terms, bilateral agreement approval, and payment intent state.

Install from the repository root with `python -m pip install -e ./backend`.

See [the domain architecture](../docs/architecture/05-domain-layer.md) for implemented invariants, package boundaries, and remaining work. The domain types do not perform persistence, authenticated authorization, or external provider calls.
