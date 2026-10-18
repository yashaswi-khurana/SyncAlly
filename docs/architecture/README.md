# SyncAlly Architecture Documents

**Status:** Proposed reference design\
**Date:** 2026-10-13\
**Purpose:** Define the production-evolvable contracts for SyncAlly's
commercial domain, Temporal orchestration, and PayPal payment execution.

## Documents

1.  `01-commercial-domain-model.md` --- domain entities, invariants,
    state transitions, and approval semantics.
2.  `02-temporal-deal-workflow-contract.md` --- workflow boundaries,
    signals, activities, retries, idempotency, and failure recovery.
3.  `03-paypal-payment-intent-lifecycle.md` --- payment intent states,
    provider integration, webhook verification, reconciliation, and
    operational controls.
4.  `04-architecture-decision-record.md` --- the architecture decision
    tying the documents together.
5.  `05-domain-layer.md` --- implemented domain model boundaries, rules,
    and the remaining application and persistence work.
6.  `06-ai-provider-boundary.md` --- the provider-independent AI suggestion
    port, offline fake, bounded retries, and the deferred provider choice.

## Architecture at a glance

-   **Frontend:** React + TypeScript.
-   **API:** Python + FastAPI.
-   **Domain:** framework-independent Python services and domain models.
-   **AI:** LangGraph + Pydantic, used for bounded extraction and
    negotiation proposals.
-   **Durable orchestration:** Temporal.
-   **Source of truth:** PostgreSQL.
-   **Payments:** PayPal Invoicing API through a merchant-aware adapter.
-   **Storage:** S3-compatible object storage for files and generated
    documents.
-   **Observability:** OpenTelemetry plus redacted application/agent
    traces.

## Core rule

> AI can propose. Temporal can orchestrate. Only authenticated,
> authorized domain commands can commit commercial or financial actions.

Temporal workflow history is not the commercial ledger. LangGraph
checkpoints are not approvals. A provider webhook is not accepted as
final payment truth until it has been verified, deduplicated, and
reconciled against the provider.

## Scope assumptions

The first release is a constrained vertical slice: one buyer, one
seller, one supported currency/trade scenario, bilateral approval,
generated draft commercial records, and a PayPal Sandbox payment.
Production rollout requires a separate merchant eligibility, legal,
tax/export, security, and operational readiness review.

These documents are implementation contracts and recommendations, not
legal, tax, or payment-provider certification.
