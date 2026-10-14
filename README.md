# SyncAlly

SyncAlly is a proposed platform for helping buyers and sellers turn commercial conversations into reviewed trade terms, mutually approved agreements, operational documents, and payment requests.

> **Project status:** Architecture baseline. This repository currently contains design documents only; the application, infrastructure, and local run commands have not been implemented yet.

## Architecture

The proposed first release is a constrained vertical slice built as a Python modular monolith with a React and TypeScript frontend. FastAPI exposes the application API, PostgreSQL stores authoritative business state, and Temporal coordinates long-running deal workflows. AI may help extract requirements and draft proposals, while domain services remain responsible for validation, authorization, and commercial decisions.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the system overview and [docs/architecture/](docs/architecture/README.md) for the detailed domain, workflow, payment, and decision records.

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

This is a proposed baseline, not evidence that these components have been installed or integrated. The architecture records explain the alternatives and conditions for revisiting these choices.

## MVP boundary

The reference design proposes one buyer, one seller, one supported currency and trade scenario, bilateral approval, generated draft commercial records, and a PayPal Sandbox payment flow. It does not claim universal legal, tax, customs, export, accounting, or payment-provider compliance. Production use needs separate product, security, operational, and provider-readiness reviews.

## Repository map

```text
.
├── README.md
├── ARCHITECTURE.md
├── LICENSE
├── .gitignore
└── docs/
    └── architecture/
        ├── README.md
        ├── 01-commercial-domain-model.md
        ├── 02-temporal-deal-workflow-contract.md
        ├── 03-paypal-payment-intent-lifecycle.md
        └── 04-architecture-decision-record.md
```

## Development

There is no runnable application or development environment in the repository yet. Setup instructions will be added with the first implementation so that documented commands can be verified against working code.

## License

SyncAlly is licensed under the [MIT License](LICENSE).
