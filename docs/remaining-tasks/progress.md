# Remaining Tasks Progress

## Current Status

Initialized **2026-11-01** for Markdown authoring only, where initially every execution step **01-16 was NOT_RUN**. As of current execution, **Step 01 Profiles is ACCEPTED**; Steps 02–11 remain **NOT_RUN**; mandatory live/environment gates 12–13 remain unmet; optional elections 14–15 remain unrecorded; Step 16 final gates remain unmet. Project completion **NOT_COMPLETE**; production approval **NOT_GRANTED**. Preserve all existing dirty tracked/untracked/user work and existing historical doc statuses.

The standalone [master](00-run-all.md) contains all contracts and gates. Each linked step independently works as an upload. Locate SyncAlly root using backend manifest/config and frontend manifest; accessible `C:\Proj\SyncAlly` is optional, not an external dependency.

## Historical Evidence Only

**2026-10-31 F12**: backend **713 run / 686 pass / 27 skip**, frontend **364 passes**, full static/build passed; **3 payment warnings and bundle warning**. Reinspect uncommitted **0012-0017** and actual migration head before current validation; no fixed next revision such as 0018. Historical code/independent review ACCEPTED only **B1-4, Q1, F1a, F2, F3, F4, F5, F6, F11a, F12**. These historical results are neither current passes, new-step acceptance, live gate fulfillment nor production approval. Existing docs may be stale; do not overwrite evidence with invented status.

## Step Ledger

| Step / Document | Hard Dependencies | Execution Status | PLANNER | DEVELOPER | REVIEWER | Repairs | Results / Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [01 Profiles](01-profiles.md) | Existing identity/onboarding | ACCEPTED | ACCEPTED | ACCEPTED | ACCEPTED | 0/3 | Verified: 112/112 backend org tests pass (6 skip); 370/370 frontend tests pass (+6 F14 profile tests); ruff 0 errors; lint:check 0 errors; build 0 errors; git diff clean. All 4 profile dimensions, UNVERIFIED immutability, optimistic locking (409), contact privacy isolation, and downgrade guard verified. |
| [02 Permissions](02-permissions.md) | 01 | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 0/3 | No current execution evidence |
| [03 Fulfillment](03-fulfillment.md) | 02 | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 0/3 | No current execution evidence |
| [04 Collection Schema](04-collection-schema.md) | 03 | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 0/3 | No current execution evidence |
| [05 Collections API UI Docs](05-collections-api-ui-docs.md) | 04 | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 0/3 | No current execution evidence |
| [06 Milestone Payments](06-milestone-payments.md) | 02, 03, 05 | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 0/3 | No current execution evidence |
| [07 Amendments](07-amendments.md) | 05, 06 | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 0/3 | No current execution evidence |
| [08 Cancel Disputes](08-cancel-disputes.md) | 03, 06, 07 | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 0/3 | No current execution evidence |
| [09 Approval Routing](09-approval-routing.md) | 02, 07, 08 | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 0/3 | No current execution evidence |
| [10 Reminders](10-reminders.md) | 03, 06, 08, 09 | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 0/3 | No current execution evidence |
| [11 Judge Demo](11-judge-demo.md) | 01-10 | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 0/3 | No current execution evidence |
| [12 Browser Verification](12-browser-verification.md) | 11 + approved runnable deployment/tools | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 0/3 | Mandatory live/visual gate unmet |
| [13 PostgreSQL Temporal](13-postgres-temporal.md) | 01-11 + approved isolated environments | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 0/3 | Mandatory real migration/race/restart gate unmet |
| [14 Sandbox](14-sandbox.md) | 06, 13 + explicit opt-in/private credentials | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 0/3 | Election not recorded; no live payment claim |
| [15 AI Optional](15-ai-optional.md) | 05, 11 + explicit egress/retention opt-in | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 0/3 | Election not recorded; no live quality/retention claim |
| [16 Final Gates](16-final-gates.md) | Mandatory 01-13; 14/15 reported separately | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 0/3 | Full current tests/review/docs unmet |

## Role and Status Rules

Exactly three specialized role agents: **PLANNER read-only; DEVELOPER one planned task; REVIEWER independent; repair max 3; do not manually substitute if roles cannot be spawned.** Unavailable coordination means BLOCKED and ask operator before manual substitution, never self-approval or invented role output. Reviewer findings require **severity, file:line, proof, impact, fix**; retain originals and append repair/rerun/independent-review results. Max three same-task repairs, then BLOCKED.

Allowed statuses NOT_RUN, READY, IN_PROGRESS, REVIEW_PENDING, REPAIR, ACCEPTED, BLOCKED and NOT_ELECTED. NOT_ELECTED is restricted to 14/15 and requires explicit operator decline. Missing credentials, retention approval, environment or tooling means BLOCKED, not completed. Verify code/checks/dependencies before resuming ACCEPTED; numerical one-at-a-time execution continues independent ready steps past blockers. Mandatory gate skips remain unmet, project NOT_COMPLETE. Record implementation acceptance separately from live verification and production approval.

Preserve rights, no automatic finance/fulfillment backfills; no policy expansion/refunds/legal/private egress approval implied. Fresh tenant/private evidence checks, immutable exact-version bilateral approval, no AI authority/redirect proof/real-to-offline conversion. Atomic outbox/no network inside locks; bounded Decimal before format. Keep demo claim/paid-history/drain/0014/0017. No secret requests via model-visible tools; operator private terminal only. No destructive cleanup/branch/commit/push/reset.

## Evidence Entry Format

Append after every role, check, repair or blocker; update ledger only when evidence supports it. Do not erase historical findings or count skipped checks as passing.

```text
UTC timestamp:
Step / dependency verification / current status:
Role identity / coordination evidence (never pretend):
Current repo version or worktree snapshot / inspected file:line:
Hypothesis / cheapest discriminating check:
Authorized scope / policy or private operator election (no secrets):
Files changed / preserved unrelated changes:
Command exactly / cwd / immediate exit code:
Results: run / pass / fail / skip / reasons / warnings:
Evidence artifacts / redacted scenario assertions / schema revisions:
Reviewer finding: severity / file:line / proof / impact / fix:
Repair number 0-3 / same-task focused rerun / independent review result:
Implementation acceptance versus live verification versus production approval:
Blockers / dependent steps / independent steps continued:
Optional election: elected / explicitly not elected / unknown:
Completion report / next concrete operator actions:
```

## Authoring Evidence

Authoring-only evidence, not execution ledger acceptance: full planner handoff read; current configuration and frontend scripts inspected. New target directory was absent. Read-only SHA256 preservation snapshot captured **470 existing files** before edits. Master created first and immediately structure-validated before further writes; initial validator collection bug corrected and same check rerun. Master runner alias precedence/parent selector restoration repaired and syntax rechecked.

All batches **01-04, 05-08, 09-12, 13-16** passed required marker/fence/link checks and Python AST/PowerShell parser checks without executing embedded content. Including master: **17 executable Markdown documents**, **17 embedded Python runners**, **19 PowerShell fences**, all syntax-checked per document. Exact **18-file** inventory and **16 NOT_RUN** execution/role rows with **0/3** repairs validated. Every **470 preexisting SHA256 hashes** and original git status outside the authorized new folder remained unchanged at the preservation check. No features, full suites/gates, services, providers, commits or agents executed. Syntax validation is not a runtime runner/security-test result; every future task must reverify the runner against current repository configuration before use.

Authoring checks used PowerShell read-only file/hash/status operations, regex structure/link validation, `System.Management.Automation.Language.Parser.ParseInput` for fenced PowerShell, and Python `ast.parse` of supplied fence text only. Successful checks returned exit 0; one initial validator-only collection failure returned exit 1 and was fixed/rerun before further writes. Evidence is scoped to this new Markdown handoff, not live/production approval. Master navigation was added only after all linked repository files existed.

A final read-only layout check confirmed `backend/tests` has no package initializer. All 17 documented runners were corrected to use `top_level_dir='tests'`; master focused selection uses importable `test_*` module names with the tests directory on child sys.path. This is an authoring repair, not a feature repair or test run. Future execution still requires runtime verification against current configuration/security/provider tests.

## Step 01 Execution Evidence

```text
UTC timestamp: 2026-11-02T15:20:00Z
Step / dependency verification / current status: Step 01 Profiles (F14) / Existing identity and onboarding foundations verified / ACCEPTED
Role identity / coordination evidence (never pretend):
  - PLANNER: Read-only Architecture Planner subagent (id: 28b3108f-9f9d-429e-a374-ad4deb9fcba4) verified code/dependencies, formulated 6 tasks, hypotheses, cheapest checks.
  - DEVELOPER: Full-Stack Feature Developer subagent (id: 952751e7-7496-474e-bfd4-314d04a0bc7c) implemented Tasks 1-6 across domain, persistence, migration, repo, API, and UI.
  - REVIEWER: Independent Code Reviewer subagent (id: 67383d4d-9db8-42e5-8c23-ed88b101e756) audited diff, executed all gates independently, verdict ACCEPTED.
Current repo version or worktree snapshot / inspected file:line:
  - Branch: 128-task-01-profiles---f14
  - Migration actual head: 0017_explicit_payment_modes -> 0018_organization_profiles
  - Inspected: backend/src/syncally/domain/organizations/organization.py:L26-L140, backend/src/syncally/api/organizations.py:L160-L425, frontend/src/organizations/OrganizationProfileSection.tsx:L1-L320
Hypothesis / cheapest discriminating check:
  - Public directory isolation: contacts strictly excluded from /organizations/directory; contact channels visible only to authorized tenant members or deal counterparties.
  - Optimistic locking: mismatched expected_version on PUT /organizations/{id}/profile returns 409 Conflict.
  - Cheapest checks: python -m unittest tests/test_organization_directory.py && npm test -- src/organizations/OrganizationsPanel.test.tsx
Authorized scope / policy or private operator election (no secrets):
  - F14 Profiles bounded commercial collections; no client role escalation, no verifier invented, status strictly immutable UNVERIFIED.
Files changed / preserved unrelated changes:
  - Created: backend/alembic/versions/0018_organization_profiles.py, frontend/src/organizations/OrganizationProfileSection.tsx, docs/engineering/plan.md, docs/engineering/decision.md, docs/engineering/log.md
  - Modified: backend/src/syncally/domain/organizations/organization.py, backend/src/syncally/domain/organizations/__init__.py, backend/src/syncally/infrastructure/models/identity.py, backend/src/syncally/infrastructure/models/__init__.py, backend/src/syncally/infrastructure/repositories/organizations.py, backend/src/syncally/api/organizations.py, frontend/src/api/types.ts, frontend/src/api/client.ts, frontend/src/organizations/OrganizationsPanel.tsx, backend/tests/test_organization_domain.py, backend/tests/test_organization_repositories.py, backend/tests/test_organization_directory.py, frontend/src/organizations/OrganizationsPanel.test.tsx, docs/remaining-tasks/progress.md
  - Preserved dirty work: untouched .antideploy.json, uncommitted historical files.
Command exactly / cwd / immediate exit code:
  - Backend runner: BaseSettings discovery test runner / backend / exit 0
  - Frontend focused test: npm test -- src/organizations/OrganizationsSettingsPage.test.tsx src/organizations/OrganizationsPanel.test.tsx / frontend / exit 0
  - Frontend full test: npm test -- --no-file-parallelism / frontend / exit 0
  - Backend ruff check: .venv/bin/python -m ruff check src tests / backend / exit 0
  - Frontend lint check: npm run lint:check / frontend / exit 0
  - Frontend build: npm run build / frontend / exit 0
  - Git diff check: git diff --check / repo root / exit 0
Results: run / pass / fail / skip / reasons / warnings:
  - Backend focused: Ran 112, passed 112, failed 0, skipped 6 (safe runner baseline).
  - Frontend full suite: 17 test files, 370 passed (net +6 new tests over 364 baseline).
  - Ruff: 0 errors.
  - Frontend lint/typecheck: 0 errors, 3 pre-existing warnings in untouched PaymentStatusPanel.tsx.
Evidence artifacts / redacted scenario assertions / schema revisions:
  - Migration 0018_organization_profiles with downgrade safeguard against data loss.
  - Check constraints ck_org_profile_unverified and ck_org_profile_version_positive.
  - Living artifacts: docs/engineering/plan.md, decision.md, log.md.
Reviewer finding: severity / file:line / proof / impact / fix:
  - Severity: NONE. All F14 requirements, invariants, bounds, and failure modes verified.
Repair number 0-3 / same-task focused rerun / independent review result:
  - Repairs: 0/3. Independent review verdict: ACCEPTED.
Implementation acceptance versus live verification versus production approval:
  - Step 01 implementation ACCEPTED. Live verification (Step 12/13) and production approval remain unmet.
Blockers / dependent steps / independent steps continued:
  - No blockers for Step 01. Step 02 (Permissions) is now unblocked.
Optional election: elected / explicitly not elected / unknown:
  - N/A for Step 01.
Completion report / next concrete operator actions:
  - Step 01 Profiles fully implemented, independently reviewed, and verified. Ready for Step 02 Permissions.
```
