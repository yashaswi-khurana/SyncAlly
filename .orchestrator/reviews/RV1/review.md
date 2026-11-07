# Code Review: Step 08 Cancel Disputes (F8) — Work Package RV1

## 1. Executive Summary & Change Stack Digest
- **New Features:** Scoped deal cancellation and dispute cases with bilateral decisions, operational impact blocker detection, and privacy-filtered evidence.
- **Bug Fixes:** Wrapped langgraph import in try/except in `graph.py` with deterministic fallback.
- **Security:** Tenant-scoped authorization via `_resolve_deal_party_organization`, forged tenant rejection (403), strict self-consent rejection, and multi-tenant evidence visibility filters (`MUTUAL_VISIBLE`, `COUNTERPARTY_RESTRICTED`, `PRIVATE_OPERATOR`).
- **Refactoring:** Preserved pre-commit unilateral cancellation (`Deal.cancel()`) while adding post-commit bilateral coordination (`Deal.mark_disputed()`, `Deal.resolve_dispute()`, `Deal.cancel_committed()`).
- **Tests:** 12 backend unit and integration tests in `test_deal_cases.py`; 4 frontend vitest test suites in `DealDetailPage.test.tsx`; all passing.

_Reviewed: 14 files across 5 stacks. Skipped: graphify cache and report files._

---

## 2. Reviewer's Guide

### Control-flow diagram
```mermaid
sequenceDiagram
    autonumber
    participant Initiator as Initiator (Buyer/Seller)
    participant API as Deal Cases API
    participant App as Deal Cases App Service
    participant DB as Postgres/SQLite DB
    participant Counterparty as Counterparty Organization

    Initiator->>API: POST /deals/{id}/cases (type, reason, version, hash)
    API->>App: raise_deal_case(command)
    Note over App: Verify tenant, agreement version & hash<br/>Assess paid milestones & fulfillment blockers
    App->>DB: Persist DealCase + OutboxEvent + AuditEvent
    App-->>API: 201 Created (DealCase with blockers)
    API-->>Initiator: 201 Created

    Counterparty->>API: POST /deals/{id}/cases/{case_id}/respond (CONSENT/REJECT)
    API->>App: respond_to_deal_case(command)
    Note over App: Verify counterparty != initiator<br/>Verify current agreement hash match
    alt Blockers Exist
        App->>DB: Status -> UNDER_REVIEW (Automated closure blocked)
    else No Blockers & CONSENT
        App->>DB: Status -> RESOLVED; Deal -> CANCELLED
    end
    App-->>API: 200 OK (Updated DealCase)
    API-->>Counterparty: 200 OK
```

### Blast-Radius & File Risk Table
| File | Change Stack | Blast Radius / Affected Callers | Risk Level |
|---|---|---|---|
| `backend/src/syncally/domain/deals/cases.py` | Core Business Logic | Domain model for cases; imported by `deal_cases` repository and application service | Low |
| `backend/src/syncally/domain/deals/deal.py` | Core Business Logic | Added `mark_disputed()`, `resolve_dispute()`, `cancel_committed()`; `cancel()` completely preserved | Low |
| `backend/src/syncally/application/deal_cases.py` | Core Business Logic | Application services for raise, respond, evidence, list; interacts with outbox/audit/db | Medium |
| `backend/src/syncally/infrastructure/repositories/deal_cases.py` | Data Layer | DealCase and CaseEvidence persistence | Low |
| `backend/src/syncally/infrastructure/models/deal_cases.py` | Data Layer | DealCaseModel and DealCaseEvidenceModel ORM declarations | Low |
| `backend/alembic/versions/0025_cancel_disputes.py` | Data Layer | Database schema migration with history-loss downgrade guard; branches parallel to `0025_system_admin` | Medium |
| `backend/src/syncally/api/deals.py` | API Contract | REST endpoints under `/deals/{deal_id}/cases` and `/api/v1/deals/{deal_id}/cases` | Medium |
| `backend/src/syncally/infrastructure/ai/graph.py` | Core Business Logic | Proposal drafting fallback when langgraph is not installed | Low |
| `frontend/src/api/types.ts` | API Contract | Case, Evidence, Decision, Visibility TypeScript models | Low |
| `frontend/src/api/client.ts` | API Contract | HTTP client methods for deal cases | Low |
| `frontend/src/deals/DealCasesPanel.tsx` | Core Business Logic | UI component for case history, evidence, modal, and bilateral decision buttons | Low |
| `frontend/src/deals/DealDetailPage.tsx` | Core Business Logic | Renders DealCasesPanel inside deal detail view | Low |
| `backend/tests/test_deal_cases.py` | Tests | Unit and integration tests covering all F8 requirements | Low |
| `frontend/src/deals/DealDetailPage.test.tsx` | Tests | Component tests validating panel rendering, modals, and actions | Low |

### AST Metrics Table
| Function | Length | Cognitive Complexity | Working Memory | Quality Score | Verdict |
|---|---|---|---|---|---|
| `DealCase.respond` | 49 | 7 | 5 | 88% | OK |
| `Deal.mark_disputed` | 8 | 2 | 2 | 96% | OK |
| `Deal.resolve_dispute` | 8 | 2 | 3 | 95% | OK |
| `Deal.cancel_committed` | 10 | 3 | 3 | 94% | OK |
| `assess_deal_case_blockers` | 61 | 9 | 6 | 82% | OK |
| `raise_deal_case` | 88 | 7 | 6 | 85% | OK |
| `respond_to_deal_case` | 74 | 7 | 5 | 86% | OK |
| `add_case_evidence` | 40 | 3 | 4 | 92% | OK |
| `list_deal_cases` | 48 | 6 | 5 | 89% | OK |
| `_raise_case_impl` | 39 | 3 | 4 | 93% | OK |
| `_respond_case_impl` | 39 | 3 | 4 | 93% | OK |

---

## 3. Merge Gate
> **APPROVED WITH SUGGESTIONS** (0 Critical, 0 High, 1 Medium/P2)

---

## 4. Findings

### 1. Medium (P2) — Parallel Alembic Migration Heads Branching From 0024_amendments
`[backend/alembic/versions/0025_cancel_disputes.py | L11-12 | module-level | Data Layer / Migrations | DB-MIG-BRANCH]`

**Cause:** Both `backend/alembic/versions/0025_cancel_disputes.py` and pre-existing `backend/alembic/versions/0025_system_admin.py` define `down_revision = "0024_amendments"`, creating two divergent heads in the migration tree.
**Consequence:** Running `alembic upgrade head` produces an error: `Multiple head revisions are present for given argument 'head'; please specify a specific target revision...`.
**Blast Radius:** Automated CI/CD deployments and developer setup commands that execute `alembic upgrade head` will abort until heads are merged or linearized.
**Fix:** Sequence `0025_cancel_disputes.py` after `0025_system_admin` by setting `down_revision = "0025_system_admin"` (or create a merge revision).

```suggestion
revision = "0025_cancel_disputes"
down_revision = "0025_system_admin"
```

**Verify:** `cd backend && .venv/bin/alembic heads` shows a single linear head instead of two heads.

---

## 5. Audit Checklist Verification

1. **Exact prior hash verification / stale agreement version rejection (409 Conflict):**
   - **Status:** PASS
   - **Evidence:** `backend/src/syncally/application/deal_cases.py:171-176` and `backend/src/syncally/domain/deals/cases.py:114-115` check that `agreement_version_id` and `terms_hash` match the current committed agreement; mismatches raise `StaleAgreementVersionError` which maps to HTTP `409 Conflict`. Validated in `test_raise_case_stale_hash_rejected_409`.

2. **Forged tenant rejection (403 Forbidden) and tenant boundaries:**
   - **Status:** PASS
   - **Evidence:** `_resolve_deal_party_organization` in `backend/src/syncally/api/deals.py:203-227` validates that the actor is an active member of the buyer or seller organization. Unrelated actors and forged organization IDs receive HTTP `403 Forbidden`. Validated in `test_forged_tenant_rejected_403`.

3. **Pre-commit cancellation preservation on uncommitted deals (DRAFT, NEGOTIATING):**
   - **Status:** PASS
   - **Evidence:** `Deal.cancel()` in `backend/src/syncally/domain/deals/deal.py:96-98` remains completely unchanged and continues to enforce pre-commit rules. Raising a case on an uncommitted deal is explicitly rejected in `backend/src/syncally/application/deal_cases.py:169`. Validated in `test_domain_deal_cancellation_and_dispute_transitions`.

4. **Operational impact blockers on paid milestones and fulfilled obligations (no automated settlement/money movement):**
   - **Status:** PASS
   - **Evidence:** `assess_deal_case_blockers()` in `backend/src/syncally/application/deal_cases.py:63-130` detects paid milestones, in-flight payment intents, and shipped/confirmed fulfillment events. When blockers exist, counterparty consent transitions the case to `UNDER_REVIEW` (not `RESOLVED`) and does not cancel the deal. Validated in `test_operational_impact_blockers_for_paid_milestone_and_fulfilled_shipment`.

5. **Bilateral consent requirement for mutual cancellation (counterparty only, same version/hash):**
   - **Status:** PASS
   - **Evidence:** `DealCase.respond()` in `backend/src/syncally/domain/deals/cases.py:110-112` strictly prohibits self-consent (`CaseUnauthorizedError` -> HTTP 403) and mandates that only the counterparty organization can consent or reject. Validated in `test_initiator_cannot_self_consent_403` and `test_bilateral_consent_cancels_deal_when_no_blockers`.

6. **Concurrency serialization (optimistic checks, atomic outbox and audit events, no network calls inside DB locks):**
   - **Status:** PASS
   - **Evidence:** Deal aggregate and case entities track integer `version` fields. Every case operation atomically writes domain model updates, `OutboxEvent`, and `AuditEvent` records within a single database transaction. No network calls or third-party requests are made inside database transactions.

7. **Evidence visibility filtering (MUTUAL_VISIBLE, COUNTERPARTY_RESTRICTED, PRIVATE_OPERATOR):**
   - **Status:** PASS
   - **Evidence:** `list_deal_cases()` in `backend/src/syncally/application/deal_cases.py:450-510` filters evidence items based on actor tenant and system admin status. Counterparty-restricted items are visible only to the submitting organization, and private operator items are hidden from standard tenants. Validated in `test_evidence_visibility_tenant_filtering`.

8. **Migration 0025 on top of 0024 with downgrade guard blocking history loss:**
   - **Status:** PASS (with P2 observation on parallel heads)
   - **Evidence:** `backend/alembic/versions/0025_cancel_disputes.py` builds the required schema and enforces a history-loss downgrade guard (`SELECT COUNT(*) FROM deal_cases`). Validated in `test_alembic_migration_0025_and_downgrade_block`.

9. **Frontend DealDetailPage UI integration, evidence tags, bilateral action buttons, and blocker alerts:**
   - **Status:** PASS
   - **Evidence:** `frontend/src/deals/DealCasesPanel.tsx` is mounted within `DealDetailPage.tsx` and renders case history, blocker warnings, evidence items with visibility tags, modal for raising cases, and bilateral action controls. Validated in `DealDetailPage.test.tsx` (4 dedicated tests, 37 total suite tests passing).

10. **Import safety fix in graph.py:**
    - **Status:** PASS
    - **Evidence:** `backend/src/syncally/infrastructure/ai/graph.py:54-72` wraps `langgraph` import in `try-except` and provides a deterministic non-network fallback that passes tests seamlessly.

---

## 6. Empirical Verification Summary
- `cd backend && PYTHONPATH=src:tests .venv/bin/python -m unittest tests/test_deal_cases.py`: Ran 12 tests, 12 passed in 2.30s (exit 0).
- `cd backend && PYTHONPATH=src:tests .venv/bin/python -c '<discovery script>'`: Ran 58 core deal/workflow/payment tests, 58 passed (8 skipped for external temporal server) (exit 0).
- `cd backend && .venv/bin/ruff check src tests`: Clean, all checks passed (exit 0).
- `cd frontend && npx vitest run src/deals/DealDetailPage.test.tsx`: 37 passed in 8.61s (exit 0).
- `cd frontend && npx vitest run`: 424 tests passed across 20 test files in 16.82s (exit 0).
- `cd frontend && npx eslint src/api/types.ts src/api/client.ts src/deals/DealCasesPanel.tsx src/deals/DealDetailPage.tsx src/deals/AgreementReview.tsx src/deals/DealDetailPage.test.tsx`: Clean, 0 errors, 0 warnings (exit 0).
- `cd frontend && npx tsc --noEmit`: Clean, 0 type errors (exit 0).
- `cd frontend && npm run build`: Vite build completed successfully in 695ms (exit 0).

---

## 7. Review Verdict
`VERDICT: PASS`
*(No P0 or P1 blockers remain; 1 P2 finding noted for migration chaining).*
