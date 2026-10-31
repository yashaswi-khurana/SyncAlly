# SyncAlly

SyncAlly helps buyers and sellers turn trade conversations into reviewed terms, a bilateral agreement, draft commercial records, and a PayPal Sandbox invoice. The current app includes organization setup and invitations, counterparty search, private/shareable messages, fact review, proposed terms, agreement approval, payment authorization and status, and development demo tools.

The supported slice uses one buyer, one seller, USD terms and seller-invoice payment timing. AI suggestions are non-binding: people review terms, both organizations approve the same agreement version, and the seller separately requests payment. Production rollout remains subject to the [architecture gates](ARCHITECTURE.md#scope-and-deployment).

## Trade lifecycle

1. Sign in with a seeded demo account, or accept an invitation to create an account. Users without an organization complete the setup wizard; organization settings support team invitations.
2. Create a deal by searching the organization directory by legal name. The deal page also supports counterparty invitations. No manual copying of organization IDs is needed for the normal create flow.
3. Post messages as your organization, choosing private or shareable visibility. First-deal guidance explains the conversation flow.
4. Request fact suggestions, review or correct them, or add terms manually. Saved confirmations synchronize fact badges and affected proposal fields. Private context stays scoped to its organization; draft generation does not share or approve it.
5. Request a proposal, edit its terms, then send the reviewed version for bilateral approval. Buyer and seller approve the same version and terms hash; commitment creates payment milestones and obligations atomically.
6. The seller reviews the invoice recipient and chooses **Request Payment**. A configured payment worker creates and sends the Sandbox invoice. The buyer can open its invoice link and see reconciled payment status. A committed agreement also supplies a read-only commercial document draft.

## Architecture and repository

| Component | Current implementation |
| --- | --- |
| Web | React 19, TypeScript, Vite |
| API and business rules | FastAPI; framework-independent domain and application services |
| Commercial ledger | PostgreSQL, SQLAlchemy, Alembic migrations |
| Durable workflow | Temporal lifecycle worker plus a separate database outbox relay |
| Suggestions | Explicit API requests to the bounded demo AI provider |
| Payments | Separate payment outbox worker, PayPal Sandbox adapter, verified webhooks and reconciliation |

`backend/src/syncally/` contains `api/`, `application/`, `domain/`, `infrastructure/`, `workflows/`, and `cli/`. `frontend/src/` contains the app; `infra/` supplies local PostgreSQL and Temporal. See [ARCHITECTURE.md](ARCHITECTURE.md) for current routes and data flow, [the architecture records](docs/architecture/README.md) for design decisions, and [operations](docs/operations.md) for recovery. LangGraph, S3 storage and OpenTelemetry are design directions rather than integrations in this slice.

## Local quickstart

Use PowerShell from the repository root. Install Python **3.12+**, Docker with Compose v2, and Node **22.13+ on 22.x or 24+**, with npm. Docker must be running. Plan for dependency/image downloads on a fresh machine; a five-minute startup target assumes prerequisites and downloads are already available, and is not a measured cold-install guarantee.

### 1. Install, configure and start dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e "./backend[dev]"
if (!(Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
docker compose -f infra/compose.yaml up -d
docker compose -f infra/compose.yaml ps
docker compose -f infra/compose.yaml exec -T postgres pg_isready -U syncally -d syncally
```

Wait for PostgreSQL to report healthy/accepting connections and for Temporal UI at <http://localhost:8233> to respond. PostgreSQL listens on `localhost:5432`, Temporal on `localhost:7233`; Compose persists both services in named volumes. Existing data/configuration is retained. See [infra/README.md](infra/README.md) for service troubleshooting and the workflow restart smoke test.

The example `backend/.env` opts into `APP_ENV=development`, supplies a local JWT key and a `DATABASE_URL` matching Compose. Review it before connecting to another database. Settings load this file relative to the backend package, regardless of terminal directory; environment variables override it. Do not use the example credentials outside local development.

### 2. Migrate and provision the demo accounts

In the same activated terminal:

```powershell
Set-Location backend
alembic upgrade head
python -m syncally.cli.seed_demo
```

Set and confirm passwords of 12 to 128 characters when prompted. The command creates `buyer@syncally.demo` / **Demo Buyer Co** and `seller@syncally.demo` / **Demo Seller Co**, with administrator memberships. It is repeatable and retains an existing password; it is not a password reset. Seeding is restricted to development/test. Invitation acceptance supports new account creation; there is no standalone public registration endpoint.

### 3. Run the API and workers

Open a separate terminal for each process below. In **every backend terminal**, start from the repository root, activate `.\.venv\Scripts\Activate.ps1`, then `Set-Location backend`. Each process uses the same configuration.

| Terminal | Command | Purpose |
| --- | --- | --- |
| API | `python -m uvicorn syncally.api.main:app --reload` | HTTP API at <http://localhost:8000> |
| Workflow worker | `python -m syncally.workflows.worker` | Executes durable deal lifecycle activities |
| Temporal relay | `python -m syncally.cli.outbox_worker` | Delivers committed database events to Temporal |
| Payment worker | `python -m syncally.cli.payment_worker` | Creates/sends/reconciles Sandbox invoices; requires the credentials below |

For conversation/agreement development, run the first three processes. The payment worker exits without PayPal credentials; queued payment requests cannot create invoices until it is configured and running. The API's interactive route reference is <http://localhost:8000/docs>.

### 4. Run the frontend

In a new terminal from the repository root:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open the URL Vite prints, usually <http://localhost:5173>, and sign in using a demo email and the password you set. During development Vite proxies `/auth`, `/dev`, `/organizations` and `/deals` to `http://127.0.0.1:8000`. Optional `VITE_API_PROXY_TARGET` changes that target; `VITE_API_BASE_URL` changes the client's API base. The invitation acceptance path is `/invitations/accept`, outside the default Vite proxy prefixes: invitation testing needs that path routed to the API by your local proxy or a suitable API base and same-origin deployment. See [frontend/README.md](frontend/README.md) for additional client details.

From any terminal, check API readiness:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/health/database
```

These check process/database access only; verify the workers separately in their terminals and Temporal UI.

## Real PayPal Sandbox invoices

Configure `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` in `backend/.env` using a **Sandbox** REST app, then start/restart the payment worker. The adapter is fixed to `https://api-m.sandbox.paypal.com`. For verified invoice events, configure the app's invoicing webhook at a reachable `POST /webhooks/paypal/invoicing` endpoint and set its `PAYPAL_WEBHOOK_ID`; localhost requires an externally reachable forwarding setup.

The invoice contact comes from the buyer organization's **single active administrator** and their email, with the organization legal name/country. Seeded `.demo` addresses are local identities, not real mailboxes; use appropriate controlled Sandbox identities/contact data when verifying actual delivery. The recipient modal previews available data; it does not edit the backend's invoice contact. An optional Gmail copy uses `GMAIL_SMTP_USERNAME`, `GMAIL_APP_PASSWORD` and optional `GMAIL_FROM_EMAIL` (a verified alias). Supply both username and App Password if enabling Gmail.

A queued intent or displayed link does not prove invoice dispatch or payment. Verify provider create/send and reconciled status separately. [Operations](docs/operations.md) explains unknown outcomes, webhook verification and safe recovery; never create a second intent to recover an ambiguous provider response.

## Development role switcher and simulation

After demo sign-in, the development switcher changes between the seeded Buyer and Seller sessions without signing in again. It appears in Vite development builds, or with `VITE_ENABLE_DEV_SWITCHER=true`. The server independently restricts these endpoints to `APP_ENV=development` or `test` and an authenticated seeded demo administrator. The neutral **Admin** label is not a separate account; the API's ADMIN target resolves to the buyer.

**Reset Demo Data** asks for confirmation and deletes deals whose two parties are the seeded demo organizations, with their related activity. It preserves deals involving other organizations and restores the demo identities/memberships. It does not reset Temporal history or cancel provider invoices; do not use it to recover a payment.

For an isolated lifecycle smoke run, from an activated `backend/` terminal with the example `.env` in place:

```powershell
$env:PYTHONUTF8 = "1"
python -m syncally.cli.simulate_deal_flow --help
python -m syncally.cli.simulate_deal_flow --ci --no-color
```

`PYTHONUTF8=1` keeps the CLI's Unicode output readable in Windows terminals. `--ci` and `--in-process` use an in-memory SQLite/FastAPI harness with seeded test identities. They do not start PostgreSQL, Temporal, the browser or PayPal. A passing run returns 0; failure returns 1 and reports the failing step and elapsed time. The CLI prints a **simulated** Sandbox invoice URL when no actual `invoice_url` is available; this is not invoice delivery/payment evidence.

To target the running local API, supply passwords matching your seeded accounts through `BUYER_PASSWORD` and `SELLER_PASSWORD` in your shell environment, then run:

```powershell
python -m syncally.cli.simulate_deal_flow --base-url http://127.0.0.1:8000 --no-color
```

The CLI also accepts `SYNCALLY_API_URL`, `--buyer-email`, `--seller-email`, `--buyer-password` and `--seller-password`. Its built-in test passwords are not the seed command's chosen passwords. A network-mode run creates deal/payment-intent records; if the health probe cannot reach the API it automatically falls back to the isolated harness. Read the printed mode before interpreting success as live-API verification.

## Verification and contribution boundaries

From an activated `backend/` terminal:

```powershell
python -m unittest discover -s tests -v
python -m ruff check src tests
```

From `frontend/`:

```powershell
npm test
npm run lint:check
npm run build
```

Business rules stay in `domain/`, use cases in `application/`, and external integrations in `infrastructure/`. HTTP, workflow relay, workflow execution and payment processing remain separate process boundaries over shared services. PostgreSQL is the commercial source of truth; neither AI output, workflow history nor a browser redirect authorizes a commitment or proves payment.

## License

[MIT](LICENSE).
