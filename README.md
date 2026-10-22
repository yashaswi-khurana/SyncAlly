# SyncAlly

SyncAlly is a proposed platform for helping buyers and sellers turn commercial conversations into reviewed trade terms, mutually approved agreements, operational documents, and payment requests.

> **Project status:** The foundation includes a FastAPI API with health checks, JWT authentication and refresh rotation, protected deal reads, PostgreSQL persistence and migrations, framework-independent domain foundations, and a React/TypeScript frontend shell. Local demo accounts can be provisioned with a development/test-only seed command. Public self-registration and product invitation/acceptance are not implemented; product invitations remain planned. Deal creation, the create/detail browser flow, bilateral agreement approval, and the durable Temporal deal workflow with its separate worker process are implemented. Local PostgreSQL and Temporal development services and an opt-in worker restart smoke test are provided in `infra/`; external payment integration remains planned.

## Architecture

The proposed first release is a constrained vertical slice built as a Python modular monolith with a React and TypeScript frontend. FastAPI exposes the application API, PostgreSQL stores authoritative business state, and Temporal coordinates long-running deal workflows. AI may help extract requirements and draft proposals, while domain services remain responsible for validation, authorization, and commercial decisions.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the system overview, [docs/architecture/](docs/architecture/README.md) for the detailed domain, workflow, payment, and decision records, and [docs/implementation-plan.md](docs/implementation-plan.md) for the living plan separating implemented foundations from planned product flows.

The current domain code and its exact implementation boundary are described in [the domain layer architecture](docs/architecture/05-domain-layer.md).

## Core rules

- AI output is a proposal and must pass domain validation.
- Only authenticated, authorized commands can approve agreements or request payments.
- A proposal is not a commitment; both parties must approve the same immutable agreement version.
- PostgreSQL is the source of truth for commercial state. Workflow history and AI checkpoints are not the business ledger.
- Payment requests and provider events require durable intent, idempotency, verification, and reconciliation.
- Private buyer and seller context must be isolated before it is used in prompts or shared proposals.

## Planned stack

| Area | Proposed technology |
| --- | --- |
| Web app | React + TypeScript |
| API | Python + FastAPI |
| Domain models and schemas | Framework-independent Python + Pydantic |
| Durable deal workflows | Temporal |
| AI orchestration | LangGraph, introduced only where useful |
| Database and migrations | PostgreSQL + SQLAlchemy + Alembic |
| Payment requests | PayPal Invoicing API, starting with Sandbox |
| Document storage | S3-compatible object storage |
| Observability | OpenTelemetry with redacted application and agent traces |

The API and React client now have starter shells. The other components in this table remain planned and are not yet integrated. The architecture records explain the alternatives and conditions for revisiting these choices.

## MVP boundary

The reference design proposes one buyer, one seller, one supported currency and trade scenario, bilateral approval, generated draft commercial records, and a PayPal Sandbox payment flow. It does not claim universal legal, tax, customs, export, accounting, or payment-provider compliance. Production use needs separate product, security, operational, and provider-readiness reviews.

## Repository map

```text
.
├── backend/
│   ├── pyproject.toml
│   └── src/syncally/
│       ├── api/                 # HTTP boundary and route registration
│       ├── application/         # Use cases and command orchestration
│       ├── domain/              # Framework-independent business rules
│       ├── infrastructure/      # Persistence and provider adapters
│       └── workflows/           # Durable workflow definitions and activities
├── frontend/
│   ├── package.json
│   └── src/                     # React application
├── infra/                       # Local PostgreSQL and Temporal development services
├── docs/architecture/           # Domain, workflow, payment, and ADR documents
├── ARCHITECTURE.md
├── LICENSE
└── README.md
```

## Development

Start PostgreSQL and the persistent Temporal development service from the repository
root by following [the local infrastructure guide](infra/README.md). Then use the
backend and frontend commands below in separate terminals.

### Backend

Requires Python 3.12 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
cd backend
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
python -m ruff check src tests
cd ..
python -m uvicorn syncally.api.main:app --reload --app-dir backend\src
```

To create or update the local PostgreSQL schema, copy
`backend/.env.example` to `backend/.env`, set `DATABASE_URL`, then run the migration
command from the backend directory:

```powershell
cd backend
alembic upgrade head
```

In development/test, create the local demo buyer and seller accounts after migrating:

```powershell
python -m syncally.cli.seed_demo
```

The command asks for each password without displaying it. Use `buyer@syncally.demo` or
`seller@syncally.demo` to sign in. It is disabled outside development/test; public
self-registration and organization invitations are not available yet.

The API exposes `GET /health` for process health and `GET /health/database` to verify
that it can acquire and use a database connection. It does not yet check workflow-worker
or provider availability.

### Frontend

Requires Node.js 22.13 or newer on the 22.x line, or Node.js 24 or newer, and npm.

```powershell
cd frontend
npm ci
npm test
npm run lint:check
npm run build
npm run dev
```

The frontend provides a sign-in form and a deal create/detail flow connected to the API. It
proxies API paths to the backend during local development; see [frontend/README.md](frontend/README.md)
for the contract, configuration, and commands.

### Implementation boundaries

- Keep business rules in `backend/src/syncally/domain`; this package must not depend on FastAPI, Temporal, LangGraph, or provider SDKs.
- Keep use cases in `application` and external system integrations in `infrastructure`.
- Keep the API and workflow worker as separate process entry points over shared application and domain code.
- Add infrastructure definitions only alongside verified local setup instructions.

See [the operations and recovery guide](docs/operations.md) for safe logs, health
checks, stuck work and ambiguous PayPal outcomes.

## License

SyncAlly is licensed under the [MIT License](LICENSE).
