# SyncAlly web app

React and TypeScript client built with Vite. It provides a sign-in form, a deals workspace, and a
deal create/detail flow that reads and writes through the SyncAlly API. Requires Node.js 22.13 or
newer on the 22.x line, or Node.js 24 or newer.

From this directory, install the locked dependencies and run the app:

```powershell
npm ci
npm run dev
```

Run the frontend tests, lint/type checks, and production build with:

```powershell
npm test
npm run lint:check
npm run build
```

## API connection

The API client lives in `src/api/` and is the only module that talks to the backend. It uses
the documented contract: `POST /auth/login`, `GET /organizations`, `POST /organizations`,
`POST /organizations/{id}/members`, `GET /deals`, `POST /deals`, and `GET /deals/{deal_id}`.
API data is authoritative; the UI refetches deals from the API when a page loads, including
after a browser reload.

The deal review screen loads `GET /deals/{deal_id}/agreements/current` to show the exact saved
terms, version, hash, and party decisions. Approve and reject requests send that displayed version
and hash to the corresponding agreement endpoint. Once both parties approve that exact hash, a
separate commit action requests the backend to mark the deal agreed. A `409` response leaves the
old terms visible, disables further decisions, and asks the user to reload and review the current
version.

After signing in, the app opens the deals workspace (`#/deals`), which lists every deal where the
signed-in account's organization is the buyer or the seller and labels which side the account is
on. A seller reaches shared deals here instead of the create form. The workspace also lists the
account's own organization IDs with a copy button, so a seller can share its ID for the buyer to
name in a new deal, and includes forms to create a new organization and to add an existing
account as a member of an organization the signed-in user administers. The draft-deal form is at
`#/deals/new` and a single deal is at `#/deals/{deal_id}`.

The interface uses a dark editorial theme adapted from the reference portfolio `huyml.co`:
near-black canvas, electric-blue accent, oversized display type, marquees, an animated aurora
background, film grain, a pointer-follower cursor, and scroll-reveal motion. Motion is disabled
for users who prefer reduced motion.

During local development the Vite dev server proxies `/auth`, `/organizations`, and `/deals`
to the backend so the browser stays same-origin. Point the proxy at a non-default backend with
`VITE_API_PROXY_TARGET` (default `http://127.0.0.1:8000`). To call the API from a different
origin, set `VITE_API_BASE_URL`; that environment needs CORS configured on the backend.

The seller must be a different active organization. Because there is no organization search
endpoint yet, the create form asks for the seller organization ID directly. Set
`VITE_DEMO_SELLER_ORGANIZATION_ID` to prefill it for the local demo.

Sign in with a provisioned demo account (for example `buyer@syncally.demo`). The access token
is kept in browser storage and sent as a bearer token; there is no public self-registration.

Use feature-oriented folders under `src/` as product flows are implemented. Keep API access in
the shared `src/api/client.ts` module and keep server-side authorization and business rules in
the backend.
