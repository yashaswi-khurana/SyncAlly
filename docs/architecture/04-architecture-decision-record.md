# 04 --- Architecture Decision Record: SyncAlly Production Foundation

**ADR:** 001\
**Status:** Accepted as the proposed implementation baseline\
**Date:** 2026-10-13

## Context

SyncAlly turns unstructured buyer/seller conversations into negotiated
trade terms, bilateral approvals, operational documents, and payment
requests. It combines probabilistic AI with commercial and financial
side effects. The architecture must support a hackathon vertical slice
and evolve into a secure, supportable production service.

Key requirements: - AI experimentation without coupling the business
domain to a framework; - long-running deals that wait hours or days; -
reliable retries and recovery after crashes; - multi-tenant isolation
and private negotiation context; - immutable agreement versions and
authorized approvals; - safe payment creation and provider
reconciliation; - future ERP and payment-provider adapters; - low
operational overhead during initial delivery.

## Decision

Adopt a **Python modular monolith with a durable workflow engine**.

-   React + TypeScript frontend.
-   FastAPI API.
-   Framework-independent Python domain and application services.
-   Pydantic schemas for validated inputs/outputs.
-   LangGraph for bounded, role-isolated agent reasoning when justified.
-   Temporal for durable deal lifecycle orchestration and long-running
    activities.
-   PostgreSQL as the authoritative business database.
-   SQLAlchemy + Alembic for persistence and migrations.
-   PayPal adapter for Invoicing API operations, beginning with Sandbox.
-   Object storage for document artifacts.
-   OpenTelemetry and redacted agent/application traces.

Run the API and Temporal workers as separate processes from the same
repository. Use managed PostgreSQL and managed Temporal when feasible
for production. For local development, use Docker Compose.

## Why not microservices immediately?

The initial domain is cohesive and needs frequent atomic operations
across deals, proposals, approvals, obligations and payment intents. A
modular monolith provides clear boundaries without introducing network
hops and distributed consistency problems. Extract services only when
independent scaling, availability, ownership or deployment needs are
demonstrated.

## Why Temporal plus LangGraph?

Temporal handles durable business process progression, retries, timers
and waiting for external events. LangGraph handles bounded AI reasoning
and branching. They must not compete to own the authoritative commercial
lifecycle.

If the initial negotiation workflow does not justify a graph, start with
typed Python functions behind an agent interface and introduce LangGraph
only when needed. The business domain must remain independent of either
choice.

## Why PostgreSQL is the source of truth

PostgreSQL transactions and constraints enforce bilateral approval,
immutable agreement versions, unique operation IDs and durable outbox
records. Temporal history and LangGraph checkpoints describe execution
state; neither replaces the business ledger.

## Required architecture rules

1.  AI proposes; domain commands validate and commit.
2.  Every approval is authenticated, authorized, and bound to an exact
    agreement version/hash.
3.  A proposal is not a commitment.
4.  A committed agreement version is immutable; amendments are new
    versions.
5.  PaymentIntent must exist before any provider-side invoice side
    effect.
6.  External side effects use stable operation IDs, bounded retries and
    reconciliation.
7.  Webhooks are verified and deduplicated; payment state is reconciled
    with the provider.
8.  Buyer and seller private context are isolated before prompt
    construction.
9.  The domain layer imports no FastAPI, Temporal, LangGraph or
    PayPal-specific code.
10. The first release supports a constrained trade scenario and does not
    claim universal tax, customs or legal compliance.

## Alternatives considered

### FastAPI + LangGraph + PostgreSQL only

Pros: simpler operations, fewer components, quick prototype.\
Cons: application team must implement and operate more of the durable
long-running workflow mechanics, including waits, timers, retries and
recovery.

This remains an acceptable hackathon fallback if managed Temporal setup
threatens delivery. Preserve the same domain and idempotency contracts.

### Python AI service + TypeScript business service

Pros: clear language/service split and independent scaling.\
Cons: duplicate deployment, network failure modes, distributed
transactions, and more operational complexity before the product has
validated demand.

Rejected for initial delivery.

### Full TypeScript stack

Pros: one language across frontend/backend, good product-development
velocity.\
Cons: Python is a strong fit for experimentation across AI workflows and
evaluation. Still a valid alternative if team expertise strongly favors
TypeScript.

Not selected for this implementation baseline.

### Immediate microservices/Kubernetes/Kafka

Rejected due to premature operational complexity. Revisit only when
scale or team boundaries justify them.

## Consequences

Positive: - Domain contracts survive changes in AI frameworks and
payment providers. - Long-running workflows can wait for humans and
recover from worker failures. - Payment operations are explicit,
auditable and reconcilable. - Initial development remains one codebase
with clear module boundaries.

Negative: - Temporal adds infrastructure and workflow-versioning
responsibilities. - Developers must understand deterministic workflow
constraints and activity retry semantics. - Production payment
onboarding depends on external provider eligibility and permissions. -
The architecture alone does not establish market demand, legal
compliance or production readiness.

## Rollout gates

### Gate 1 --- Prototype

-   Structured constraints and bounded agent proposals.
-   Bilateral exact-version approval.
-   One PayPal Sandbox invoice/payment.
-   Worker restart and duplicate webhook tests.

### Gate 2 --- Private beta

-   Tenant isolation review and adversarial tests.
-   Recovery, monitoring, backup/restore and incident procedures.
-   Agent evaluation suite and human escalation.
-   Documented supported trade scenario and limitations.

### Gate 3 --- Production

-   Approved merchant onboarding/payment integration.
-   Security and compliance review for target corridors/products.
-   Production SLOs, alerting, support, audit and retention policies.
-   Customer validation and operational readiness sign-off.

## Revisit this decision if

-   Temporal operational cost is disproportionate to the workflow needs;
-   team expertise or delivery constraints strongly favor another stack;
-   real traffic requires independently scalable AI or payment services;
-   provider access rules require a different marketplace/payment
    architecture;
-   customer discovery shows that the core workflow should integrate
    into an existing ERP rather than own transaction orchestration.
