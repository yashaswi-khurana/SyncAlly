# SyncAlly Implementation Plan

**Status:** Living plan. Foundations and core product workflows are fully implemented; remaining production hardening and enterprise milestones are detailed below.

This plan tracks the implementation of SyncAlly from the initial demo contract ([Issue #8](https://github.com/yashaswi-khurana/SyncAlly/issues/8)) through the major commercial execution capabilities and workflow extensions ([Issue #77](https://github.com/yashaswi-khurana/SyncAlly/issues/77)).

---

## Current Implementation Status

### Implemented Foundation & Core Vertical Slice

The following capabilities are complete, tested, and merged into the active application mainline:

1. **Authentication, Tenant Isolation & Onboarding:**
   - JWT access and refresh token rotation with cryptographic secrets and configurable TTLs.
   - Database-backed organization membership checks and actor context resolution (`ActorContext`).
   - Guided organization setup wizard (`OnboardingWizard`) for first-time signups with 0 organizations.
   - Cryptographically signed 7-day single-use counterparty invitation tokens (`POST /organizations/{org_id}/invitations` and `POST /invitations/accept`) with atomic replay protection.
   - Development demo account seeder (`python -m syncally.cli.seed_demo`) for local environments; public self-registration remains disabled.

2. **Organization Directory Discovery & Deal Creation:**
   - Case-insensitive legal entity directory search API (`GET /organizations/directory`) with prefix matching, pagination, and active organization exclusions.
   - Deal Creation Wizard (`CreateDealPage`) discovering trading counterparties directly via directory search, replacing manual UUID entry.

3. **Context-Scoped Negotiation & In-Deal Messaging:**
   - Dual-channel message timeline (`DealConversationReview`) with explicit privacy tagging (`SHAREABLE` vs. `PRIVATE`).
   - Client idempotency key transmission and message existence verification (`GET /deals/{deal_id}/messages/existence`).

4. **Commercial Facts Review & Manual Term Studio:**
   - On-demand AI fact extraction (`POST /deals/{deal_id}/ai/facts`) with provenance, confidence scores, and missing-field diagnostics.
   - Manual Term Studio (`POST /deals/{deal_id}/facts`, `PATCH /deals/{deal_id}/facts/{fact_id}`) enabling manual entry, editing, and fact visibility toggling (`PATCH .../visibility`).
   - Agreement readiness checklist dynamically tracking mandatory terms (item, quantity, price, delivery date, destination) before unblocking proposal drafting.

5. **Reactive Suggestion-to-Proposal Synchronization:**
   - Confirmed commercial facts automatically overlay candidate agreement proposals.
   - Revoking or modifying a confirmed fact automatically invalidates affected draft fields while preserving unrelated human edits.

6. **Bilateral Agreement Consensus & Atomic Commitment:**
   - Canonical JSON terms serialization and deterministic `SHA-256` terms hashing.
   - Payment timing terms validation (`UPFRONT`, `NET_30`, `UPON_DELIVERY`, `SPLIT_50_50`).
   - Dual approval verification: both buyer and seller organizations must approve the identical version and terms hash.
   - Atomic PostgreSQL commitment transaction: transitions deal to `COMMITTED`, generates immutable obligations and payment milestones, logs audit events, and writes outbox events.

7. **Durable Temporal Workflow Orchestration:**
   - Transactional outbox relay (`outbox_worker.py`) delivering committed events to Temporal via `signal_with_start`.
   - `DealWorkflow` (`deal/<deal_id>/lifecycle`) maintaining durable state across 30-day horizons.
   - `RefreshDealStateActivity` reloading authoritative commercial truth directly from PostgreSQL via SQLAlchemy repositories.

8. **PayPal Sandbox Invoicing & Reconciliation:**
   - Independent leased payment outbox worker (`payment_worker.py`) with PostgreSQL `FOR UPDATE SKIP LOCKED` claims (5-minute leases).
   - Seller pre-authorization confirmation dialog previewing the buyer organization's single active administrator contact.
   - Deterministic PayPal Sandbox invoice creation, send dispatch, and optional Gmail SMTP copies.
   - Robust recovery for ambiguous timeouts (`CREATE_PENDING` $\rightarrow$ `CREATE_UNKNOWN` with lookup before retry).
   - Cryptographically verified PayPal webhook intake (`POST /webhooks/paypal/invoicing`) with automated full-amount and currency reconciliation to `PAID`.

9. **Developer Tooling & Verification Automation:**
   - Floating Dev Role Switcher (`POST /dev/switch-role`) for 1-click toggling between Buyer, Seller, and Admin sessions in development mode.
   - Safe Demo Data Reset (`POST /dev/reset-demo`) purging test deals between demo organizations while preserving accounts and external records.
   - Standalone end-to-end simulation CLI (`simulate_deal_flow.py`) executing all 7 checkpoints in <0.5s in CI mode and against running live APIs.

---

### Still Planned / Production Rollout Scope

The following items are intentionally deferred for production scaling and enterprise compliance:

- **Live Production Payments:** Onboarding live PayPal merchant credentials, multi-seller payout routing, dispute webhooks, and alternative settlement rails / escrow.
- **Cloud Object Storage:** S3 / MinIO storage adapter for persisting commercial document drafts and compliance artifacts.
- **Automated PDF Generation:** Server-side document rendering (e.g. WeasyPrint) generating standardized, printable PDF sales contracts bearing the immutable agreement hash.
- **In-Flight Term Amendments:** Non-destructive amendment state machine (`deepdiff`) allowing post-commitment milestone adjustments without workflow resets.
- **Distributed Observability:** OpenTelemetry distributed tracing and Prometheus metrics exporters.
- **Enterprise Legal & Tax Compliance:** Automated calculation of regional VAT/GST, cross-border customs declarations, and multi-jurisdiction e-signature compliance.

See [README](../README.md), [system architecture](../ARCHITECTURE.md), [operations guide](operations.md), and the [architecture decision record](architecture/04-architecture-decision-record.md) for more detail.

---

## New Architecture Contracts (Issue #77 Extensions)

### 1. Organization Directory Search Contract
- **Endpoint:** `GET /organizations/directory?query={prefix}&limit={10}&offset={0}`
- **Ownership:** `backend/src/syncally/api/organizations.py`, `infrastructure/repositories/organizations.py`
- **Contract Guarantees:**
  - Performs case-insensitive prefix matching against active organizations (`status = 'ACTIVE'`).
  - Automatically filters out organizations where the authenticated caller holds active membership to prevent self-dealing.
  - Returns paginated list of `{ id, legal_name, country_code }`.
  - Enforced by frontend `CreateDealPage` to eliminate manual UUID copy-pasting.

### 2. Deal Message Composer & Privacy Selector Contract
- **Endpoint:** `POST /deals/{deal_id}/messages`
- **Ownership:** `backend/src/syncally/api/conversations.py`, `frontend/src/deals/DealConversationReview.tsx`
- **Contract Guarantees:**
  - Requires caller to be an active member of a participant organization in the deal.
  - Enforces explicit `visibility` parameter: `SHAREABLE` (delivered to counterparty) or `PRIVATE` (persisted strictly within authoring organization's context).
  - Accepts optional `idempotency_key` string from the client to prevent duplicate posts on network retries.
  - Component preserves unsubmitted text and selected privacy state upon network or server error.

### 3. Manual Term Studio & Readiness Checklist Contract
- **Endpoints:**
  - `POST /deals/{deal_id}/facts` (insert manual fact candidate)
  - `PATCH /deals/{deal_id}/facts/{fact_id}` (update fact value or unit)
  - `PATCH /deals/{deal_id}/facts/{fact_id}/visibility` (toggle between `PRIVATE` and `SHAREABLE`)
  - `POST /deals/{deal_id}/facts/{fact_id}/confirm` (mark fact authoritative)
- **Ownership:** `backend/src/syncally/api/conversations.py`, `frontend/src/deals/AISuggestionReview.tsx`
- **Contract Guarantees:**
  - Allows operators to bypass or supplement AI extraction by manually entering structured terms (item description, quantity, unit price, delivery destination, delivery date).
  - Readiness checklist dynamically inspects confirmed terms; disables proposal creation and highlights missing fields until all mandatory terms are confirmed.
  - Toggling visibility verifies that only the fact's owner organization can alter privacy boundaries.

### 4. Dev Role Switcher & Sandbox Recovery Contract
- **Endpoints:**
  - `POST /dev/switch-role` (issue fresh JWT tokens for `BUYER`, `SELLER`, or `ADMIN`)
  - `POST /dev/reset-demo` (transactional purge of demo deal records)
- **Ownership:** `backend/src/syncally/api/dev.py`, `frontend/src/ui/DevRoleSwitcher.tsx`
- **Contract Guarantees:**
  - Strictly blocked (HTTP 403) unless `APP_ENV` is `development` or `test` and caller holds a valid demo admin token.
  - Reset Demo Data locks reset operations, preserves user accounts, retains memberships, and deletes only deals between seeded demo organizations (`buyer@syncally.demo` and `seller@syncally.demo`). Deals involving other organizations remain untouched.

### 5. Invoice Observability & Pre-Authorization Recipient Contract
- **Endpoints:** `POST /deals/{deal_id}/payments`, `GET /deals/{deal_id}/payments`
- **Ownership:** `backend/src/syncally/api/payments.py`, `frontend/src/deals/PaymentStatusPanel.tsx`
- **Contract Guarantees:**
  - Before authorizing payment, the seller UI displays a confirmation dialog previewing the buyer organization's single active administrator contact (email, name, country).
  - Status panel exposes live status (`AUTHORIZED`, `PROVIDER_CREATED`, `SENT`, `PAID`, `ACTION_REQUIRED`), provider invoice URL, failure reason, and retry countdown timers.
  - Browser displays payment observations; actual settlement requires verified PayPal webhook reconciliation.

---

## Acceptance Criteria Verification Matrix (GitHub Issue #77)

The table below maps all 11 acceptance criteria from Issue #77 directly to their implemented code modules, automated test suites, and verified execution commands:

| AC ID | Acceptance Criteria & Requirement | Implemented Code Modules | Automated Test Suite & Coverage | Verification Command | Status |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **AC-1** | **Organization Directory Search API**<br>Expose `GET /organizations/directory` with case-insensitive prefix matching, pagination, and caller org exclusion. | `backend/src/syncally/api/organizations.py`<br>`backend/src/syncally/infrastructure/repositories/organizations.py` | `test_organization_directory.py`<br>(10 unit & integration tests) | `python -m unittest discover -s backend/tests -p "test_organization_directory.py"` | **PASS** |
| **AC-2** | **Directory Deal Creation Wizard**<br>Replace manual seller UUID entry with searchable directory picker; validate non-self-trading and display search errors. | `frontend/src/deals/CreateDealPage.tsx`<br>`frontend/src/api/client.ts` (`searchOrganizations`) | `CreateDealPage.test.tsx`<br>(14 component tests) | `cd frontend && npx vitest run src/deals/CreateDealPage.test.tsx` | **PASS** |
| **AC-3** | **In-Deal Message Composer & Privacy**<br>Allow posting messages with explicit `SHAREABLE` or `PRIVATE` visibility, idempotency keys, and error preservation. | `frontend/src/deals/DealConversationReview.tsx`<br>`backend/src/syncally/api/conversations.py` | `DealConversationReview.test.tsx`<br>`test_conversation_routes.py` (36 tests) | `cd frontend && npx vitest run src/deals/DealConversationReview.test.tsx` | **PASS** |
| **AC-4** | **Manual Term Studio & Readiness Checklist**<br>Allow manual fact entry and editing; enforce checklist requiring mandatory terms before proposal generation. | `frontend/src/deals/AISuggestionReview.tsx`<br>`frontend/src/deals/DealConversationReview.tsx` | `AISuggestionReview.test.tsx`<br>`DealConversationReview.test.tsx` | `cd frontend && npx vitest run src/deals/AISuggestionReview.test.tsx` | **PASS** |
| **AC-5** | **Fact Visibility Toggle API & UI**<br>Add `PATCH /deals/{id}/facts/{id}/visibility` allowing fact owners to toggle between `PRIVATE` and `SHAREABLE`. | `backend/src/syncally/api/conversations.py`<br>`frontend/src/deals/DealConversationReview.tsx` | `test_conversation_routes.py`<br>`DealConversationReview.test.tsx` | `python -m unittest discover -s backend/tests -p "test_conversation_routes.py"` | **PASS** |
| **AC-6** | **Colloquial AI Fact Extraction**<br>Extract commercial terms from informal messages with confidence scores, source citations, and missing-field diagnostics. | `backend/src/syncally/infrastructure/ai/demo.py`<br>`backend/src/syncally/application/ai.py` | `test_ai_provider.py`<br>`test_ai_context.py` (15 tests) | `python -m unittest discover -s backend/tests -p "test_ai_provider.py"` | **PASS** |
| **AC-7** | **Reactive Fact-to-Proposal Sync**<br>Synchronize confirmed facts into proposal drafts; revoking or editing facts invalidates affected proposal fields. | `frontend/src/deals/DealConversationReview.tsx`<br>`backend/src/syncally/api/agreements.py` | `DealConversationReview.test.tsx`<br>`test_agreement_routes.py` | `cd frontend && npx vitest run src/deals/DealConversationReview.test.tsx` | **PASS** |
| **AC-8** | **Payment Timing & Agreement Review**<br>Validate payment timing terms (`NET_30`, `UPFRONT`), compute SHA-256 canonical hash, and require bilateral approval. | `backend/src/syncally/domain/agreements/`<br>`frontend/src/deals/AgreementReview.tsx` | `AgreementReview.test.tsx`<br>`test_agreements.py` (30 tests) | `cd frontend && npx vitest run src/deals/AgreementReview.test.tsx` | **PASS** |
| **AC-9** | **Dev Role Switcher & Sandbox Recovery**<br>Floating widget to toggle `BUYER`, `SELLER`, `ADMIN` (`/dev/switch-role`) and reset demo data (`/dev/reset-demo`). | `backend/src/syncally/api/dev.py`<br>`frontend/src/ui/DevRoleSwitcher.tsx` | `DevRoleSwitcher.test.tsx`<br>`test_dev_routes.py` (22 tests) | `cd frontend && npx vitest run src/ui/DevRoleSwitcher.test.tsx` | **PASS** |
| **AC-10** | **Pre-Authorization Recipient & Observability**<br>Preview buyer admin contact before payment request; display provider invoice link, retry count, and countdown timers. | `frontend/src/deals/PaymentStatusPanel.tsx`<br>`backend/src/syncally/api/payments.py` | `PaymentStatusPanel.test.tsx`<br>`test_payment_processing.py` (28 tests) | `cd frontend && npx vitest run src/deals/PaymentStatusPanel.test.tsx` | **PASS** |
| **AC-11** | **Automated Dual-Role Simulation CLI**<br>Execute all 7 deal flow checkpoints end-to-end; support sub-second in-process CI mode and live network API execution. | `backend/src/syncally/cli/simulate_deal_flow.py` | Standalone CLI Test Harness<br>(7/7 checkpoints passing in 0.4s) | `python -m syncally.cli.simulate_deal_flow --ci --no-color` | **PASS** |

---

## Identity and Onboarding Status

Email/password login, verified-token identity, database-backed memberships, organization creation, and admin membership for existing users are fully implemented. Public self-registration is disabled to match the demo contract.

Product onboarding is implemented via two complementary mechanisms:
1. **Guided Setup Wizard (`OnboardingWizard`):** Authenticated users with 0 organizations are automatically presented with the setup wizard upon sign-in to configure their company legal name and country code, establishing them as `ADMIN`.
2. **Tokenized Counterparty Invitations:** Organization administrators generate signed 7-day single-use JWT invitation links (`POST /organizations/{org_id}/invitations`). Recipients opening `#/invite?token=...` are guided through account creation, company registration, and direct linking into the target deal via `POST /invitations/accept`.
3. **Local Demo Seeding:** Run `python -m syncally.cli.seed_demo` after migrations to provision fixed demo accounts (`buyer@syncally.demo` and `seller@syncally.demo`) with prompted passwords.

---

## Rules Every Stage Must Follow

- Keep business decisions in `backend/src/syncally/domain/` and `application/`. The domain must not depend on FastAPI, Temporal, AI libraries, or PayPal.
- The backend checks who the user is and which organization they belong to. Never trust a role or organization ID just because the browser sent it.
- Keep buyer-private and seller-private data separate. Only share data marked shareable.
- AI can suggest facts and terms. A person and the domain rules must check them before they affect an agreement.
- Both organizations must approve the same agreement version. A committed agreement is not edited in place.
- PostgreSQL stores the business truth. Temporal, AI history, a webhook, or a browser redirect cannot replace it.
- Save and authorize a `PaymentIntent` before calling PayPal. Mark it paid only after checking PayPal's current payment state.
- Do not hold a database transaction open while calling an AI service, Temporal, or PayPal.
- Use decimal money values and an explicit currency. Do not use floating-point numbers for money.

---

## Stage Summary & Historical Record

### Stage 1 - Set Up the Basics *(Status: Merged & Verified)*
- **S1-01 Organization and deal types:** Pure domain types in `backend/src/syncally/domain/`.
- **S1-02 Database setup:** SQLAlchemy 2.0 models, Alembic migrations, PostgreSQL connection.
- **S1-03 User identity boundary:** JWT token decode/issue, `ActorContext`, and dev login override.
- **S1-04 Test and check commands:** Verified unittest and Vitest configurations.

### Stage 2 - Create and View a Deal *(Status: Merged & Verified)*
- **S2-01 Deal use cases:** Application operations for deal creation and retrieval.
- **S2-02 Save and load deals:** SQLAlchemy deal repository with participant authorization.
- **S2-03 Deal API routes:** `POST /deals`, `GET /deals`, and `GET /deals/{deal_id}` endpoints.
- **S2-04 Connect deal UI:** `CreateDealPage` and `DealDetailPage` with directory search integration.

### Stage 3 - Messages and Facts *(Status: Merged & Verified)*
- **S3-01 Define messages and facts:** Domain models for `Conversation`, `Message`, and `Constraint`.
- **S3-02 Save messages and facts:** Tables and repositories with strict tenant visibility filtering.
- **S3-03 Message and fact API routes:** `POST/GET /deals/{id}/messages` and review actions.
- **S3-04 Message and fact review screens:** Dual-role chat timeline and fact review badges.

### Stage 4 - AI Suggestions *(Status: Merged & Verified)*
- **S4-01 AI input and output types:** Versioned Pydantic schemas for extracted terms.
- **S4-02 Filter AI context by organization:** Isolation service filtering private counterparty data.
- **S4-03 AI adapter and fake:** Deterministic demo AI provider with fallback diagnostics.
- **S4-04 AI review UI:** Suggestion review cards with explicit confirm/reject/clarify buttons.

### Stage 5 - Agreement and Approvals *(Status: Merged & Verified)*
- **S5-01 Stable agreement versions:** Canonical JSON serialization and SHA-256 terms hashing.
- **S5-02 Save approvals and commit in one transaction:** Atomic PostgreSQL commit transaction.
- **S5-03 Approval API routes:** `POST /agreements/{version}/approve` and `commit` endpoints.
- **S5-04 Agreement review screens:** Side-by-side proposal editor and bilateral approval buttons.

### Stage 6 - Background Deal Workflow *(Status: Merged & Verified)*
- **S6-01 Deliver outbox work to Temporal:** Transactional outbox table and `cli/outbox_worker.py`.
- **S6-02 Deal workflow:** `DealWorkflow` with 30-day wait deadline and replay safety.
- **S6-03 Workflow activities and worker process:** `RefreshDealStateActivity` reloading PostgreSQL state.
- **S6-04 Local services and restart test:** Docker Compose setup and integration smoke test.

### Stage 7 - PayPal Sandbox Payment *(Status: Merged & Verified)*
- **S7-01 PaymentIntent rules:** Domain state machine for payment milestones.
- **S7-02 Save payment intents and outbox:** Transactional payment outbox with lease claims.
- **S7-03 PayPal Sandbox adapter and worker:** Leased invoice creation with lookup recovery.
- **S7-04 Verify PayPal events and reconciliation:** HMAC webhook verification and full payment checks.

### Stage 8 - Finish the Demo and Handoff *(Status: Merged & Verified)*
- **S8-01 Generate draft commercial documents:** Read-only commercial draft generator.
- **S8-02 Payment and document screens:** `PaymentStatusPanel` and document draft viewer.
- **S8-03 Test the full flow and access boundaries:** `test_demo_lifecycle.py` and `simulate_deal_flow.py`.
- **S8-04 Safe logs and recovery guide:** Redacted JSON console logging and `docs/operations.md`.

---

## Design References

- [Deal, message, and approval rules](architecture/01-commercial-domain-model.md)
- [Temporal and outbox rules](architecture/02-temporal-deal-workflow-contract.md)
- [PayPal payment rules](architecture/03-paypal-payment-intent-lifecycle.md)
- [Architecture decisions](architecture/04-architecture-decision-record.md)
- [Domain layer specifications](architecture/05-domain-layer.md)
- [AI provider boundary](architecture/06-ai-provider-boundary.md)
- [Safe operations and recovery](operations.md)
- [Architecture overview](../ARCHITECTURE.md)
- [Project README](../README.md)
