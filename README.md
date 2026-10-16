# SyncAlly

SyncAlly is a proposed platform for helping buyers and sellers turn commercial conversations into reviewed trade terms, mutually approved agreements, operational documents, and payment requests.

> **Project status:** Early implementation. The repository contains a minimal FastAPI health endpoint, a React/TypeScript frontend shell, and framework-independent domain foundations for deal negotiation, agreements, and payment intents. Application workflows, persistence, infrastructure, and external integrations are not implemented yet.

## Architecture

The proposed first release is a constrained vertical slice built as a Python modular monolith with a React and TypeScript frontend. FastAPI exposes the application API, PostgreSQL stores authoritative business state, and Temporal coordinates long-running deal workflows. AI may help extract requirements and draft proposals, while domain services remain responsible for validation, authorization, and commercial decisions.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the system overview and [docs/architecture/](docs/architecture/README.md) for the detailed domain, workflow, payment, and decision records.

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
├── infra/                       # Local and deployment infrastructure (future)
├── docs/architecture/           # Domain, workflow, payment, and ADR documents
├── ARCHITECTURE.md
├── LICENSE
└── README.md
```

## Development

### Backend

Requires Python 3.12 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .\backend
python -m uvicorn syncally.api.main:app --reload --app-dir backend\src
```

The API currently exposes `GET /health`. It does not yet check database, workflow-worker, or provider availability.

### Frontend

Requires Node.js 22.12 or newer and npm.

```powershell
cd frontend
npm install
npm run dev
```

The frontend is a placeholder shell and is not connected to the API yet.

### Implementation boundaries

- Keep business rules in `backend/src/syncally/domain`; this package must not depend on FastAPI, Temporal, LangGraph, or provider SDKs.
- Keep use cases in `application` and external system integrations in `infrastructure`.
- Keep the API and workflow worker as separate process entry points over shared application and domain code.
- Add infrastructure definitions only alongside verified local setup instructions.

## License

SyncAlly is licensed under the [MIT License](LICENSE).
