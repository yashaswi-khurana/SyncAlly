# Execute All Remaining SyncAlly Steps

Execute this step now in SyncAlly workspace. This upload alone is the complete execution contract for 01-16. Do not stop after planning. Execute every ready step one at a time in numerical order; resume by verifying code and evidence, not by trusting a status label. No original prompt, external handoff, `C:\Proj\Prompts.txt.txt`, or sibling upload is required. Sibling repository Markdown may be read if available, but this inline contract controls if it is more complete.

## Workspace and Historical Context

Locate the repository from the current workspace by the simultaneous presence of `backend/pyproject.toml`, `backend/src/syncally/config.py`, and `frontend/package.json`. Verify `git rev-parse --show-toplevel`; check its exit code immediately. Prefer `C:\Proj\SyncAlly` only if those markers exist there; otherwise use the located root as `$Root`. Do not assume external Windows paths are accessible. Read applicable repository instructions and the senior-engineer and testing-qa skills if available; unavailable external skills do not replace this contract.

Historical baseline dated **2026-10-31**, not a current passed claim: F12 backend **713 run / 686 pass / 27 skip**, frontend **364 passes**, full static checks and build passed, with **3 payment warnings and a bundle warning**. Uncommitted migrations **0012-0017** must be reinspected. Historical code and independent review ACCEPTED: **B1-4, Q1, F1a, F2, F3, F4, F5, F6, F11a, F12**. This is neither live-gate completion nor production approval. Existing documentation statuses may be stale. Reuse the identity/onboarding, negotiation, agreement/hash/history, workflow/outbox, payment modes/intents/reconciliation, demo/reset and F12 export foundations; do not rebuild them.

Read [configuration](../../backend/src/syncally/config.py), [backend manifest](../../backend/pyproject.toml), [frontend manifest](../../frontend/package.json), [existing plan](../implementation-plan.md), [operations](../operations.md), and [F12 handoff](../f12-trade-pack-handoff.md) as evidence, not authoritative current results. During execution, change existing docs only when the relevant planned task authorizes truthful updates; do not retroactively overwrite historical evidence.

## Common Rules

Exactly three specialized role agents: **PLANNER read-only; DEVELOPER one planned task; REVIEWER independent; repair max 3; do not manually substitute if roles cannot be spawned.** Coordinate those roles only. PLANNER reads the owning code/tests, verifies dependencies and already-done behavior, states a falsifiable hypothesis and cheapest check, and delivers one bounded task. DEVELOPER implements that one task and runs focused checks immediately after its first substantive edit. REVIEWER independently inspects current changes and evidence. No self-approval. If independent subagent coordination is unavailable, record BLOCKED and ask the operator before any manual-role substitution; do not pretend agents ran. Continue unrelated ready steps where their required roles are available.

Routine conservative choices in this plan are authorized. Policy expansion, client-only roles, automatic privilege backfill, blanket new finance/fulfillment grants, refunds, legal/compliance claims, remote private-context egress and unapproved real-provider operations are not. Preserve existing rights until an explicit policy is approved; routing or trigger eligibility never grants authority. Server-side fresh tenant membership/capability checks control every mutation, read and private export. Test organization switching, revocation, forged identifiers and stale requests. Keep private evidence scoped to its organization and authorized deal participants; do not expose profile contacts, attachment bodies or secrets in public search, errors, logs, notifications or progress.

Committed terms, hash/schema/version and payment/fulfillment history are immutable. Approval must be human, bilateral, and for the identical version/hash; AI has no approval, legal, verification, fulfillment or financial authority. A provider redirect does not prove payment. Never convert real payment history to offline simulation. Durable outbox writes belong in the same database transaction as business state; perform no network I/O while holding database transactions/row locks. Validate finite bounded Decimal values, currency precision and allocations **before formatting**, quantizing or multiplying; reject NaN, infinity and oversized exponents/digits. No implicit currency or quantity-unit conversion.

Preserve all existing tracked/untracked/user changes. Snapshot current status; reread files before authorized edits; use apply_patch for manual edits. No destructive cleanup, branches, commits, push or resets. Compute migration head from actual current versions/Alembic, never assume `0018`; preserve fresh-install and upgrade data and block downgrades that would lose committed/paid history. Keep demo claim/lock, paid-history preservation, worker drain and migrations **0014/0017** safeguards. Tests normally use fakes; live checks require isolated explicitly approved environments. Never request secrets through model-visible questions or put credentials in docs/model output: the operator enters secrets privately in their terminal. Missing policy, tools, services or credentials means BLOCKED, not fabricated completion.

## Execution and Evidence

For each step, verify dependencies from code plus current evidence before editing. An ACCEPTED label alone is insufficient. Compare an already-implemented step against every acceptance criterion; rerun its scoped checks and obtain independent review instead of reimplementing it. Record PLANNER, DEVELOPER, REVIEWER and each repair result in repository `docs/remaining-tasks/progress.md` if present; if absent, create that ledger in this authorized folder using the format below. A sibling upload is never required.

Use statuses NOT_RUN, READY, IN_PROGRESS, REVIEW_PENDING, REPAIR, ACCEPTED, BLOCKED and NOT_ELECTED (only 14/15 after explicit operator election). Record UTC timestamp, step/dependencies, role identity, inspected file:line and version/diff evidence, command/cwd/exit code, run/pass/fail/skip counts and reasons, artifact paths, findings and repair count 0-3. Reviewer findings require severity (critical/high/medium/low), file:line, reproducible proof, impact and concrete fix. Repair the same task at most three times, rerunning the failed focused check and independent review; thereafter BLOCKED. Never erase findings or relabel skips as passes. Report implementation acceptance separately from live verification and production approval.

Continue numerically through all ready independent tasks when one is blocked; mark dependent tasks BLOCKED with the dependency proof. Steps 14/15 require explicit opt-in and private operator provisioning. They may be BLOCKED or explicitly NOT_ELECTED without inventing credentials/retention approval. The project is not complete while any mandatory 01-13 or 16 gate is unmet. Finish with executed/accepted/blocked/not-elected summary, changes, exact checks, evidence, open risks and next operator actions, not a future-only plan.

## Gates and Safe Windows Runner

Use Windows PowerShell **5.1** commands without shell `&&`; the existing npm scripts may internally contain `&&`. Check `$LASTEXITCODE` immediately after each native command, before another native command. Locate a configured backend virtualenv Python first (`backend/.venv/Scripts/python.exe`, then root `.venv/Scripts/python.exe`, then the active `python` command). Require Python 3.12+ and installed project dependencies; report a missing environment rather than silently installing or fetching services. Reinspect current manifests/config before runtime use of this runner: `Settings`, `PayPalSettings`, `GmailSettings` derive from BaseSettings; `settings = Settings()` happens at import; APP_ENV defaults to production. New settings classes/required fields/aliases require a reviewed runner update before use. Verify the bootstrap against current security/provider tests before relying on full-suite counts.

The following complete runner isolates only import/discovery, not test bodies. It derives names/defaults/aliases from model metadata; restores normal BaseSettings construction/dotenv handling before execution, clears inherited configuration case-insensitively, preserves explicit TEST_POSTGRES_URL and SYNCALLY_TEMPORAL_* inputs and logging, and never patches skips, Temporal startup, test modules or security assertions. The child finally restores its original environment; it does not mutate the parent. Required new fields without defaults fail discovery rather than inventing provider configuration. The current `backend/tests` directory has no package initializer: discover with top-level directory `tests`. For focused checks set `$TestModules` to existing `test_*` module names (for example `test_agreements`) after verifying importability; an empty list discovers all tests. Never execute this full suite during Markdown authoring.

```powershell
$Root = (Get-Location).Path
while (-not ((Test-Path (Join-Path $Root 'backend/pyproject.toml')) -and (Test-Path (Join-Path $Root 'frontend/package.json')))) {
    $Parent = Split-Path $Root -Parent
    if (-not $Parent -or $Parent -eq $Root) { throw 'Locate SyncAlly workspace root first' }
    $Root = $Parent
}
$Python = @((Join-Path $Root 'backend/.venv/Scripts/python.exe'), (Join-Path $Root '.venv/Scripts/python.exe')) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Python) { $Python = (Get-Command python -ErrorAction Stop).Source }
Set-Location (Join-Path $Root 'backend')
& $Python -c "import sys; assert sys.version_info >= (3,12); import pydantic_settings, syncally"
if ($LASTEXITCODE -ne 0) { throw 'Backend interpreter/dependencies unavailable' }
$TestModules = @()
$HadSelector = Test-Path Env:SYNCALLY_HANDOFF_TEST_MODULES
$OldSelector = $env:SYNCALLY_HANDOFF_TEST_MODULES
$env:SYNCALLY_HANDOFF_TEST_MODULES = ($TestModules -join ',')
try {
@'
import os
import sys
import unittest
from pydantic_core import PydanticUndefined
from pydantic_settings import BaseSettings

original_environment = dict(os.environ)
original_init = BaseSettings.__init__
classes = ()
def alias_names(value):
    if isinstance(value, str):
        return {value}
    choices = getattr(value, "choices", ())
    if choices:
        return set().union(*(alias_names(choice) for choice in choices))
    path = getattr(value, "path", ())
    return {path[0]} if path and isinstance(path[0], str) else set()
def environment_names(models):
    names = set()
    for model in models:
        prefix = model.model_config.get("env_prefix", "")
        for name, field in model.model_fields.items():
            names.update({name.casefold(), (prefix + name).casefold()})
            names.update(item.casefold() for item in alias_names(field.alias) | alias_names(field.validation_alias))
    return names
def clear_configuration(names):
    for name in tuple(os.environ):
        folded = name.casefold()
        if folded == "test_postgres_url" or folded.startswith("syncally_temporal_"):
            continue
        if folded in names:
            del os.environ[name]
def bootstrap_init(self, **kwargs):
    values = {}
    for name, field in type(self).model_fields.items():
        value = field.get_default(call_default_factory=True)
        if value is PydanticUndefined:
            raise RuntimeError("Required settings field needs reviewed test bootstrap: " + name)
        aliases = alias_names(field.validation_alias) or alias_names(field.alias)
        key = next(iter(sorted(aliases)), name)
        if getattr(field.validation_alias, "path", None):
            raise RuntimeError("AliasPath needs reviewed bootstrap: " + name)
        values[key] = value
    if type(self).__name__ == "Settings":
        for name, value in {"app_env": "test", "database_url": "sqlite+pysqlite:///:memory:", "ai_provider": "offline", "payment_mode": "OFFLINE_DEMO"}.items():
            field = type(self).model_fields[name]
            key = next(iter(sorted(alias_names(field.validation_alias) or alias_names(field.alias))), name)
            values[key] = value
    for name, value in kwargs.items():
        matched = next(((field_name, field) for field_name, field in type(self).model_fields.items() if name == field_name or name in alias_names(field.validation_alias) | alias_names(field.alias)), None)
        if matched is not None:
            field_name, field = matched
            for old_key in {field_name} | alias_names(field.validation_alias) | alias_names(field.alias):
                values.pop(old_key, None)
            key = next(iter(sorted(alias_names(field.validation_alias) or alias_names(field.alias))), field_name)
            values[key] = value
        else:
            values[name] = value
    values["_env_file"] = None
    original_init(self, **values)
try:
    BaseSettings.__init__ = bootstrap_init
    os.environ.update(APP_ENV="test", DATABASE_URL="sqlite+pysqlite:///:memory:", AI_PROVIDER="offline", PAYMENT_MODE="OFFLINE_DEMO")
    import syncally.config as config
    classes = (config.Settings, config.PayPalSettings, config.GmailSettings)
    names = environment_names(classes)
    clear_configuration(names)
    os.environ.update(APP_ENV="test", DATABASE_URL="sqlite+pysqlite:///:memory:", AI_PROVIDER="offline", PAYMENT_MODE="OFFLINE_DEMO")
    modules = [item for item in os.environ.get("SYNCALLY_HANDOFF_TEST_MODULES", "").split(",") if item]
    sys.path.insert(0, os.path.abspath("tests"))
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromNames(modules) if modules else loader.discover("tests", pattern="test_*.py", top_level_dir="tests")
    BaseSettings.__init__ = original_init
    clear_configuration(environment_names(classes))
    if BaseSettings.__init__ is not original_init or any(key.casefold() == "app_env" for key in os.environ):
        raise RuntimeError("Test body isolation failed")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    code = 0 if result.wasSuccessful() and not loader.errors else 1
finally:
    BaseSettings.__init__ = original_init
    os.environ.clear()
    os.environ.update(original_environment)
sys.exit(code)
'@ | & $Python -
if ($LASTEXITCODE -ne 0) { throw 'Backend tests/discovery failed' }
} finally {
    if ($HadSelector) { $env:SYNCALLY_HANDOFF_TEST_MODULES = $OldSelector }
    else { Remove-Item Env:SYNCALLY_HANDOFF_TEST_MODULES -ErrorAction SilentlyContinue }
}
```

The parent temporary test-selector variable preserves any preexisting value. This selector is not a provider setting. Do not print environment snapshots or secrets. Do not disable unittest logging (assertLogs must work). Native dependency skips remain unmet live gates. Do not supply a nonexistent Temporal executable or change test selection to hide integration failures. Authorize service-dependent test bodies only in their isolated live step; do not start services implicitly during a fake-only task.

Run the following full static/frontend gates at 16 and whenever a planned shared-contract change requires them; run focused tests first. Do not assume historical counts remain valid.

```powershell
Set-Location (Join-Path $Root 'backend')
& $Python -m ruff check src tests
if ($LASTEXITCODE -ne 0) { throw 'Backend lint failed' }
Set-Location (Join-Path $Root 'frontend')
npm test
if ($LASTEXITCODE -ne 0) { throw 'Frontend tests failed' }
npm run lint:check
if ($LASTEXITCODE -ne 0) { throw 'Frontend lint/typecheck failed' }
npm run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
git -C $Root diff --check
if ($LASTEXITCODE -ne 0) { throw 'Whitespace gate failed' }
```

## Inventory and Navigation

Exactly 18 Markdown artifacts: this master `00-run-all.md`, the sixteen contracts below and `progress.md`. Navigate inline without sibling files: [01](#step-01-profiles), [02](#step-02-permissions), [03](#step-03-fulfillment), [04](#step-04-collection-schema), [05](#step-05-collections-api-ui-docs), [06](#step-06-milestone-payments), [07](#step-07-amendments), [08](#step-08-cancel-disputes), [09](#step-09-approval-routing), [10](#step-10-reminders), [11](#step-11-judge-demo), [12](#step-12-browser-verification), [13](#step-13-postgres-temporal), [14](#step-14-sandbox), [15](#step-15-ai-optional), [16](#step-16-final-gates). The progress format is inline under Execution and Evidence; create it only if absent, otherwise preserve and append current evidence.

All repository copies now exist. These relative links are optional navigation, never required uploads:

| Artifact | Contract / Hard Dependencies |
| --- | --- |
| [00-run-all.md](00-run-all.md) | Complete standalone master |
| [01-profiles.md](01-profiles.md) | F14 / existing identity and onboarding |
| [02-permissions.md](02-permissions.md) | F15a / 01 |
| [03-fulfillment.md](03-fulfillment.md) | F9 / 02 |
| [04-collection-schema.md](04-collection-schema.md) | F10a / 03 |
| [05-collections-api-ui-docs.md](05-collections-api-ui-docs.md) | F10b / 04 |
| [06-milestone-payments.md](06-milestone-payments.md) | F10c / 02, 03, 05 |
| [07-amendments.md](07-amendments.md) | F7 / 05, 06 |
| [08-cancel-disputes.md](08-cancel-disputes.md) | F8 / 03, 06, 07 |
| [09-approval-routing.md](09-approval-routing.md) | F15b / 02, 07, 08 |
| [10-reminders.md](10-reminders.md) | F13 / 03, 06, 08, 09 |
| [11-judge-demo.md](11-judge-demo.md) | F1b / 01-10 |
| [12-browser-verification.md](12-browser-verification.md) | 11 plus approved deployment/browser tools |
| [13-postgres-temporal.md](13-postgres-temporal.md) | 01-11 plus approved isolated environments |
| [14-sandbox.md](14-sandbox.md) | F11b / 06, 13 plus explicit opt-in/private credentials |
| [15-ai-optional.md](15-ai-optional.md) | 05, 11 plus explicit egress/retention opt-in |
| [16-final-gates.md](16-final-gates.md) | Mandatory 01-13; optional 14/15 separately reported |
| [progress.md](progress.md) | All 01-16 initially NOT_RUN; evidence ledger |

## Step 01 Profiles

Artifact: `01-profiles.md`. F14. Dependencies: none of 01-16; verify accepted identity/onboarding foundations in code first.

Read [organization domain](../../backend/src/syncally/domain/organizations/organization.py), [repository](../../backend/src/syncally/infrastructure/repositories/organizations.py), [API](../../backend/src/syncally/api/organizations.py), [identity persistence](../../backend/src/syncally/infrastructure/models/identity.py), [settings UI](../../frontend/src/organizations/OrganizationsSettingsPage.tsx), [domain tests](../../backend/tests/test_organization_domain.py), [directory tests](../../backend/tests/test_organization_directory.py), [repository tests](../../backend/tests/test_organization_repositories.py), and [UI tests](../../frontend/src/organizations/OrganizationsSettingsPage.test.tsx).

Implement bounded capabilities/products/regions/contacts profile collections, preserving existing identifiers, membership and onboarding. Define capabilities as self-described commercial activities, not permissions; products as descriptive offerings, regions as declared operating coverage using current country data; none imply licenses, vetted availability or legal eligibility. Contacts need explicit owner/editor, purpose, consent and visibility; use private-by-default contact channels with authorized participant disclosure only, not public directory enumeration. A profile may be incomplete. Persist provenance, updated/version metadata and **UNVERIFIED** status: defined authority is the existing authorized organization profile editor; self-edit or AI never makes it VERIFIED. Do not invent a verification authority, attestation program or grant. Any future verified status requires explicit approved verifier/policy. Keep existing rights, no privilege backfill.

Add typed API read/update projections, field and collection limits, duplicate policy, normalized region values, stale-write conflicts and frontend edit/save/error/empty/unauthorized states. Add additive persistence migration only if needed after actual head; preserve historical snapshots/hashes/F12 bytes. Test missing/null/Unicode/oversized contacts/products, forged tenant IDs, stale versions, role revocation, public/private projection and rollback. Run focused organization and settings UI tests plus touched lint/typecheck; full gates only for shared contracts. Acceptance: all four profile dimensions and UNVERIFIED authority/visibility rules work server-side and in UI; profile changes never mutate commitments. Independent reviewer must accept evidence before step 02.

## Step 02 Permissions

Artifact: `02-permissions.md`. F15a. Dependencies: 01.

Read [identity application](../../backend/src/syncally/application/identity.py), [organization domain](../../backend/src/syncally/domain/organizations/organization.py), [deal application](../../backend/src/syncally/application/deals.py), [agreement application](../../backend/src/syncally/application/agreements.py), [payment application](../../backend/src/syncally/application/payments.py), [authorization tests](../../backend/tests/test_deal_authorization.py), [identity boundary tests](../../backend/tests/test_identity_boundary.py), and [session client](../../frontend/src/auth/useSession.ts). Inspect organization API/repository and profile UI from 01.

Define an explicit server-enforced capability matrix for organization administration/profile editing, deal drafting/negotiation, bilateral agreement approval, finance actions and fulfillment confirmations. Preserve existing authorized approval continuity; do not infer finance/fulfillment grants from ADMIN/MEMBER or profile capabilities. New privileges require explicit assignment by an already-authorized authority under approved policy; if no grant authority exists, block grants, not existing legitimate reads/drafts/approvals. Do not silently remove existing rights or invent client roles. Store scoped assignments/version/audit only as needed with an additive actual-head migration. Protect last-administrator and self-escalation boundaries using existing semantics; clarify any genuinely new policy before implementing it.

Enforce fresh membership and capability at each API/application mutation, private read/export and worker trigger; token/UI state alone is not authority. Mirror allowed actions and stale/revoked failure handling in UI. Test full matrix allow/deny, cross-tenant grants, forged IDs, stale token/role, revocation between request/commit, rollback and existing approval regression. Run identity/deal authorization tests and relevant client/settings tests. Acceptance: no blanket backfill or unauthorized finance/fulfillment path, explicit policy ownership and old approval continuity proven; independent review required.

## Step 03 Fulfillment

Artifact: `03-fulfillment.md`. F9. Dependencies: 02.

Read [obligations](../../backend/src/syncally/domain/agreements/obligations.py), [deal domain](../../backend/src/syncally/domain/deals/deal.py), [deal application](../../backend/src/syncally/application/deals.py), [workflow](../../backend/src/syncally/workflows/deal.py), [deal persistence](../../backend/src/syncally/infrastructure/models/deals.py), [deal tests](../../backend/tests/test_deal_use_cases.py), [workflow tests](../../backend/tests/test_deal_workflow.py), and [detail UI/tests](../../frontend/src/deals/DealDetailPage.test.tsx).

Persist append-only shipment/delivery observations and authorized confirmations tied to committed agreement version/hash and obligation IDs. Start with supported legacy single-item terms, distinguishing planned, shipped, observed and confirmed facts with actor/timestamp/source; missing evidence remains unrecorded. Private evidence references have fresh tenant access; sanitize external references, do not treat a carrier URL or AI extraction as proof. Model partial deliveries, bounded quantities/units, idempotency keys and optimistic version conflicts. Derive fulfillment from actual obligations, not arbitrary status buttons; completion requires fulfilled obligations and independently reconciled required payments. Do not claim title transfer, legal acceptance or compliance.

Add typed API/UI commands and history with pending/error/stale/permission states; persist state/audit/outbox atomically, notify only after commit and outside DB locks. Add actual-head migration if needed, upgrade preservation and history-loss downgrade block. Test partial/duplicate/overdelivery, revoked/foreign actor, observation versus confirmation, competing updates, transaction rollback, canceled/superseded obligations and paid-but-unfulfilled/nonpaid-but-delivered completion. Run scoped deal/workflow tests and detail UI tests. Acceptance: version-owned authorized facts and derived completion, no fabricated payment or authority; independent review required.

## Step 04 Collection Schema

Artifact: `04-collection-schema.md`. F10a. Dependencies: 03.

Read [trade terms](../../backend/src/syncally/domain/agreements/trade_terms.py), [agreement domain](../../backend/src/syncally/domain/agreements/agreement.py), [money](../../backend/src/syncally/domain/shared/money.py), [agreement persistence](../../backend/src/syncally/infrastructure/models/agreements.py), [agreement tests](../../backend/tests/test_agreements.py), [negotiation tests](../../backend/tests/test_negotiation.py), and [commercial document tests](../../backend/tests/test_commercial_documents.py).

Extend supported term schemas to versioned item/shipment/payment collections with stable explicit IDs, deterministic ordering/serialization and version discriminator. Specify item quantity/unit/currency/price precision, shipment-to-item allocations and payment-to-obligation allocation/trigger descriptions. Preserve duplicate commercial lines as distinct identities; reject duplicate IDs, unsupported schema, references to other versions, overallocations, unit mismatch, unbounded/nonfinite Decimal and mixed-currency totals. Do not invent allocations for legacy data or auto-convert units/currency. State rounding and residual policy explicitly before implementing; ambiguous financial policy blocks affected cases. Validate numeric bounds before formatting/quantizing/computing totals.

Keep legacy committed canonical bytes/hash and historical exports unchanged; project legacy singleton data without rewriting history. Add actual-head additive migration, fresh/upgrade/backfill tests that verify unchanged commitments, and downgrade refusal where history loss is possible. Test deterministic hashes, order/identity sensitivity, duplicates, partial allocations, exact totals/rounding boundaries, giant exponents, old-schema round trips and rollback. Run agreements/negotiation/document tests and touched static checks; shared serialization requires expanded regression gates. Acceptance: schema supports all three collections without breaking old immutable commitments; independent review required.

## Step 05 Collections API UI Docs

Artifact: `05-collections-api-ui-docs.md`. F10b. Dependencies: 04.

Read [agreement API](../../backend/src/syncally/api/agreements.py), [negotiation application](../../backend/src/syncally/application/negotiation.py), [document application](../../backend/src/syncally/application/documents.py), [document API](../../backend/src/syncally/api/documents.py), [agreement UI](../../frontend/src/deals/AgreementReview.tsx), [negotiation UI](../../frontend/src/deals/NegotiationReview.tsx), [document UI/tests](../../frontend/src/deals/CommercialDocumentPanel.test.tsx), [API client](../../frontend/src/api/client.ts), and [agreement route tests](../../backend/tests/test_agreement_routes.py).

Expose schema-versioned structured authoring/read/update contracts for all collection fields/allocations from 04. Implement add/edit/remove/reorder controls with stable IDs, validation, unsaved/stale/error states and explicit partial/unrecorded data. Review exact committed/proposed version/hash bilaterally, display meaningful collection/history diffs, invalidate stale approvals, cancel late requests on deal/organization/session change and enforce capability server-side. Connect fulfillment references to explicit allocations; do not infer financial authority from editing.

Extend existing F12 deterministic ZIP/HTML/print/downloads with version-aware collection tables, allocation and fulfillment evidence provenance; preserve historical legacy bytes. Escape user content/filenames, enforce private export authorization and bounded rendering. Missing details are unrecorded, not compliance/verification claims. Prefer projections over migrations; any persistence change follows actual-head preservation rules. Test route contracts/limits, cross-tenant private exports, exact-version review, revoked/stale UI, escaping, duplicates and deterministic downloads/ZIP/print data. Run scoped routes/documents plus AgreementReview/NegotiationReview/CommercialDocumentPanel/client tests and lint/typecheck/build for shared UI contracts. Update relevant API/user docs truthfully. Acceptance: authoring through reviewed commitment and safe version-aware exports works end to end; independent review required.

## Step 06 Milestone Payments

Artifact: `06-milestone-payments.md`. F10c. Dependencies: 02, 03, 05.

Read [payment intent](../../backend/src/syncally/domain/payments/intent.py), [payment processing](../../backend/src/syncally/application/payment_processing.py), [payment outbox](../../backend/src/syncally/infrastructure/payment_outbox.py), [payment repository](../../backend/src/syncally/infrastructure/repositories/payments.py), [payment processing tests](../../backend/tests/test_payment_processing.py), [outbox tests](../../backend/tests/test_payment_outbox.py), [reconciliation tests](../../backend/tests/test_payment_reconciliation.py), and [payment UI/tests](../../frontend/src/deals/PaymentStatusPanel.test.tsx).

Extend existing milestone intents to explicit committed version-owned payment collection IDs, currencies, bounded Decimal amounts, allocations and approved trigger conditions. Check milestone sum/currency balance and residual/rounding before formatting. Eligibility from delivery/approval/time is not authority to issue/pay: require fresh finance capability and approved policy; no automatic grants or inferred trigger approval. Enforce one active intent per milestone/version with DB uniqueness, idempotent transaction/outbox and concurrent trigger/replay protection. Network calls stay outside locks; uncertain creates reconcile existing provenance without duplicate invoices.

Keep provider mode/provenance immutable, offline clearly simulated, paid/in-flight history protected, redirects nonauthoritative. Add additive actual-head migration and upgrade/downgrade protections. API/UI distinguish ineligible, eligible, authorized, queued, unknown, sent and reconciled state, protecting source privacy/errors. Test duplicate/racing triggers, revoked actors, mixed currency, giant decimals, exact totals, partial settlement, worker crash/retry, create-started unknown results and completion prerequisites. Run payment processing/outbox/reconciliation/intent tests and payment UI tests; integration races later in 13. Acceptance: no duplicate invoice, fabricated paid state, real-to-offline conversion or trigger-based privilege escalation; independent review required.

## Step 07 Amendments

Artifact: `07-amendments.md`. F7. Dependencies: 05, 06.

Read [agreement domain](../../backend/src/syncally/domain/agreements/agreement.py), [proposal](../../backend/src/syncally/domain/negotiation/proposal.py), [negotiation application](../../backend/src/syncally/application/negotiation.py), [agreement application](../../backend/src/syncally/application/agreements.py), [agreement repository](../../backend/src/syncally/infrastructure/repositories/agreements.py), [negotiation use-case tests](../../backend/tests/test_negotiation.py), [agreement tests](../../backend/tests/test_agreements.py), and [NegotiationReview tests](../../frontend/src/deals/NegotiationReview.test.tsx).

Implement human amendment propose/review/withdraw/reject/commit against explicit prior committed version/hash with immutable lineage and diff. Require fresh same-version bilateral approvals; invalidate stale decisions on replacement. Assess impacted fulfillment allocations, unpaid/paid/in-flight milestones and active cases; preserve all original commitment, payment and evidence history. Block ambiguous settlement/replacement/refund effects pending explicit policy, rather than auto-adjusting paid or queued obligations. AI may suggest text only and cannot approve or resolve financial/legal effects.

Persist proposed and committed versions/audit/outbox atomically using actual-head additive migration when needed; lock/check current version without network inside locks. Provide typed API/UI lineage, impact preview and pending/conflict/permission states, exact-version exports. Test concurrent proposals/approvals/payments, stale hashes, revocation, rollback, paid/in-flight preservation, private lineage and old export bytes. Run negotiation/agreement/payment regression and review UI tests. Acceptance: amendments can commit only with fresh bilateral exact-version approval and explicit permitted financial impact; immutable history and policy blockers visible; independent review required.

## Step 08 Cancel Disputes

Artifact: `08-cancel-disputes.md`. F8. Dependencies: 03, 06, 07.

Read [deal domain](../../backend/src/syncally/domain/deals/deal.py), [deal application/API](../../backend/src/syncally/api/deals.py), [workflow activities](../../backend/src/syncally/workflows/activities.py), [payment processing](../../backend/src/syncally/application/payment_processing.py), [deal use-case tests](../../backend/tests/test_deal_use_cases.py), [deal workflow tests](../../backend/tests/test_deal_workflow.py), and [detail UI tests](../../frontend/src/deals/DealDetailPage.test.tsx).

Add scoped cancellation/dispute cases: request type/reason, exact agreement version/obligation references, requesting actor, bilateral decisions, evidence visibility, resolution and auditable transitions. Preserve existing authorized pre-commit cancellation. Case creation/request is not proof of canceled obligations, liability, refund, payment reversal or legal resolution. Define which existing authority may decide; new adjudication/refund policies need explicit approval. Preserve paid/in-flight records and ambiguous downstream effects as BLOCKED, not silently settled. Never suspend unrelated obligations automatically without approved policy.

Implement persistence/state machine, optimistic concurrency and atomic case/audit/outbox with actual-head migration and history-loss downgrade block; serialize conflicting cancellation/payment/amendment decisions. Provide API/UI case history, reasons, private evidence and pending/conflict/unauthorized states. Test forged tenants, revoked actors, concurrent cases/payment/amendment, duplicate decisions, rollback, precommit regression and unresolved consequences. Run deal/workflow/payment scoped checks and detail UI tests. Acceptance: authorized case workflow distinguishes request from effective decision and preserves financial/legal boundaries; independent review required.

## Step 09 Approval Routing

Artifact: `09-approval-routing.md`. F15b. Dependencies: 02, 07, 08.

Read [organization repository](../../backend/src/syncally/infrastructure/repositories/organizations.py), [agreement application](../../backend/src/syncally/application/agreements.py), [negotiation application](../../backend/src/syncally/application/negotiation.py), [agreement route tests](../../backend/tests/test_agreement_routes.py), [identity boundary tests](../../backend/tests/test_identity_boundary.py), and [AgreementReview tests](../../frontend/src/deals/AgreementReview.test.tsx).

Add explicit organization-scoped routing requirements using established capabilities: eligible approvers, ordered/parallel review policy only where explicitly configured, version/hash and membership revision snapshot, reassignment and decision audit. Default must retain existing bilateral approval behavior until explicit policy configuration. Routing cannot create authority or count unilateral/internal approval as the other organization's consent; require same committed/proposed version/hash at final bilateral approval. Clarify quorum/delegation/escalation policy before expanding it. Revoked/reassigned/stale decisions cannot satisfy current routing.

Persist scoped config and decisions with actual-head additive migration when needed, atomic audit/outbox and fresh checks. API/UI present required/pending/completed/stale/unauthorized states without leaking contacts/private membership beyond entitlement. Test default continuity, multi-review approved cases, forged routes, revocation, reassignment, duplicate decisions, version changes and races with amendment/case actions. Run agreement/identity/negotiation tests and AgreementReview/settings UI tests. Acceptance: explicit routing requirements are enforced server-side without privilege creation or weakened bilateral version matching; independent review required.

## Step 10 Reminders

Artifact: `10-reminders.md`. F13. Dependencies: 03, 06, 08, 09.

Read [workflow](../../backend/src/syncally/workflows/deal.py), [workflow notifications](../../backend/src/syncally/application/workflow_notifications.py), [outbox](../../backend/src/syncally/application/outbox.py), [outbox dispatcher tests](../../backend/tests/test_outbox_dispatcher.py), [worker tests](../../backend/tests/test_workflow_worker.py), and [operations tests](../../backend/tests/test_operations.py).

Implement durable scoped reminder schedules for outstanding fulfillment, eligible-but-unacted milestones, unresolved cases and approval routing. Define UTC/timezone interpretation, due time, recurrence cap, deduplication key, delivery channel, retry/backoff and suppression rules explicitly; default to existing authorized in-app delivery, not automatic email/provider egress. No automatic approval, expiry, payment or unilateral escalation. Recheck current obligation/version, recipient membership/capability and resolved/superseded state at dispatch.

Use replay-safe workflow timers and transactional outbox schedule/state/audit; network outside DB locks, identifier-only payloads, safe logs, no private bodies/contacts in notifications. Add actual-head migration only for needed durable state; upgrade/downgrade safeguards. UI shows true pending/delivered/failed/suppressed state, not invented delivery. Test exact mocked clocks plus tolerant Windows timing, duplicates/retries, crash/restart, revocation, timezone boundaries and suppression after resolution/supersession. Run workflow/outbox/operations tests and relevant detail UI checks. Acceptance: reminders survive replay/restart and never grant authority or leak evidence; independent review required.

## Step 11 Judge Demo

Artifact: `11-judge-demo.md`. F1b. Dependencies: 01-10.

Read [seed demo](../../backend/src/syncally/cli/seed_demo.py), [demo lifecycle](../../backend/src/syncally/infrastructure/demo_lifecycle.py), [offline payments](../../backend/src/syncally/infrastructure/offline_payments.py), [demo seed tests](../../backend/tests/test_demo_seed.py), [demo lock tests](../../backend/tests/test_demo_lifecycle_lock.py), [demo lifecycle tests](../../backend/tests/test_demo_lifecycle.py), [local smoke tests](../../backend/tests/test_local_workflow_smoke.py), and [App tests](../../frontend/src/App.test.tsx).

Extend accepted demo foundations into reproducible two-party judge preparation and journey: profile UNVERIFIED/private contacts, explicit capabilities, collection draft/negotiation, bilateral commitment, partial fulfillment, authorized milestones, amendment, cancellation/dispute request/decision, routing/reminder and safe F12 downloads. Use clearly labeled offline simulation and controlled fixtures, never claim real payment/verified profiles/AI authority. Preserve claim locks, drain workers before reset, migrations 0014/0017 and paid-history protection; never turn real provenance offline or erase paid/in-flight evidence for a clean demo. No destructive cleanup.

Persist fixtures through existing supported commands and current schema only; actual-head migration only if genuinely needed for fixtures. Document exact preparation/runbook and stop points, error/retry/empty states and realistic two-session transitions. Test deterministic reseed/idempotency, reset refusal/claims, history preservation and full local journey with fakes. Run demo/lifecycle/smoke and App/deal UI tests. Acceptance: repeatable reviewed journey covers 01-10, preserves safeguards, and distinguishes simulation; independent review required. Browser/live infrastructure are separate 12/13 gates, not satisfied by fixtures.

## Step 12 Browser Verification

Artifact: `12-browser-verification.md`. Dependencies: 11. Verify an authorized runnable deployment and browser coordination. If unavailable record BLOCKED; unit/mock UI evidence is insufficient. Do not silently install/start services outside the approved environment.

Read [App](../../frontend/src/App.tsx), [TradeFlowScene](../../frontend/src/deals/TradeFlowScene.tsx), [DealConstellation](../../frontend/src/deals/DealConstellation.tsx), [document panel](../../frontend/src/deals/CommercialDocumentPanel.tsx), [styles](../../frontend/src/styles.css), [frontend manifest](../../frontend/package.json), and [commercial document tests](../../backend/tests/test_commercial_documents.py). Inspect current run scripts and target URL, browser support and deployment mode before use.

Use Playwright desktop and mobile viewports with two isolated authenticated party contexts. Run the 11 journey, organization switching, revocation and stale/late request cancellation, permissions, validation/empty/pending/error states, partial fulfillment/milestones/amendments/cases/routing/reminders. Assert no private cross-party/tenant evidence leaks. Capture screenshots, console/network failures and DOM assertions. Verify Three.js via screenshots **and canvas-pixel checks**: nonblank nonuniform rendered pixels, correct framing, loaded assets, visible motion over time and interaction, resize/mobile/reduced-motion behavior, no canvas/text/control overlap. Do not accept a mounted blank canvas as evidence.

Actually download ZIP and individual HTML/documents in both permitted contexts, inspect archive members/canonical version/allocation contents and safe filenames/escaping, compare historical legacy bytes where applicable. Inspect print media and generated print/PDF layout where supported for page breaks, clipping, tables and no missing data. Use isolated local evidence artifacts with no secrets; record tooling limitations honestly. No feature changes unless PLANNER assigns a bounded repair to DEVELOPER followed by independent REVIEWER, max 3. Run affected focused tests after repairs. Acceptance: desktop/mobile two-party visual, security, download/print and 3D pixel/asset/motion evidence genuinely passes; otherwise mandatory gate BLOCKED.

## Step 13 Postgres Temporal

Artifact: `13-postgres-temporal.md`. Dependencies: 01-11; 12 is independently required for final completion. Require explicit approved isolated PostgreSQL database/schema and Temporal namespace/environment; never use production or destructive teardown. Read [Alembic environment](../../backend/alembic/env.py), [database](../../backend/src/syncally/infrastructure/database.py), [workflow worker](../../backend/src/syncally/workflows/worker.py), [operations](../operations.md), [database tests](../../backend/tests/test_database.py), [worker tests](../../backend/tests/test_workflow_worker.py), [migration config tests](../../backend/tests/test_migration_config.py), and current migration versions including uncommitted 0012-0017.

Inspect actual Alembic head(s), dependency chain and downgrade guards before selecting a new revision; never hardcode 0018. Use isolated databases for fresh install and representative prechange upgrade with committed/paid/in-flight/claims data. Verify constraints, collections/hash preservation, indexes, foreign keys, uniqueness, new capability defaults and rollback. History-losing downgrade must block. Privately provision TEST_POSTGRES_URL and SYNCALLY_TEMPORAL_* per current test contracts; the runner must preserve them. Do not patch skips/startup/server test modules; missing environment means unmet gate.

Run real concurrent tenant/approval/fulfillment/milestone/case/amendment and outbox lease/create-started races; prove one active intent and no duplicate provider operation using approved fakes for external provider calls. Restart workers during outstanding timers/outbox and verify replay, durable notifications, safe shutdown/drain and demo claim/reset safeguards 0014/0017. No network inside DB locks. Capture exact commands, schema revisions, anonymized evidence, counts and restart/race results. Commands below are only for the operator-approved isolated environment; each native exit is checked immediately.

```powershell
Set-Location (Join-Path $Root 'backend')
& $Python -m alembic heads
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect actual heads' }
& $Python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Isolated migration upgrade failed' }
& $Python -m alembic current
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify isolated revision' }
```

Use the complete safe runner above for current migration/database/workflow test contracts, then genuine isolated smoke/restart/race runs. Repairs use three-role workflow/max 3. Acceptance: real PostgreSQL migrations/locking and Temporal restart/replay evidence accepted independently; SQLite/mocks/skips cannot satisfy this mandatory gate.

## Step 14 Sandbox

Artifact: `14-sandbox.md`. F11b optional. Dependencies: 06, 13 plus explicit Sandbox opt-in, Sandbox-only accounts/credentials and approved webhook deployment. Without election record NOT_ELECTED only if operator explicitly declines; otherwise BLOCKED. Read [PayPal adapter](../../backend/src/syncally/infrastructure/paypal.py), [webhooks](../../backend/src/syncally/api/paypal_webhooks.py), [payment worker](../../backend/src/syncally/cli/payment_worker.py), [config](../../backend/src/syncally/config.py), [webhook tests](../../backend/tests/test_paypal_webhooks.py), and [reconciliation tests](../../backend/tests/test_payment_reconciliation.py).

Operator privately enters Sandbox credentials/webhook IDs in their own terminal; never ask via model/question tools or print environment/provider tokens/payer details. Verify mode, accounts, destination and fresh finance authority without disclosing secrets. Use explicit committed eligible milestone and unique persisted intent/outbox: actual invoice create, send, buyer payment, signature-verified webhook and fresh authenticated provider reconciliation must agree on invoice ID, amount/currency, recipient, status and provenance. Redirect alone, mocks/fixtures or offline simulation do not qualify. Unknown create/send outcomes reconcile before retry, never issue duplicate invoice. Network outside DB locks; no refunds, production credentials or real-to-offline conversion.

Test invalid signatures, duplicate/reordered events, wrong invoice/amount/currency/payee and stale/revoked authority with normal fakes first; then approved Sandbox happy/unknown/retry lifecycle. Capture redacted persisted IDs/digests and evidence, not private payloads. No migration unless PLANNER proves a gap; actual-head preservation then applies. Repairs require independent reviewer/max 3. Acceptance: real Sandbox lifecycle and durable matching provenance independently accepted; absent credentials/policy/tooling remains BLOCKED and never implies production approval.

## Step 15 AI Optional

Artifact: `15-ai-optional.md`. Dependencies: 05, 11 plus explicit live-provider, data-egress and retention-policy opt-in. Read [AI application](../../backend/src/syncally/application/ai.py), [AI contracts](../../backend/src/syncally/domain/ai/contracts.py), [provider selection](../../backend/src/syncally/infrastructure/ai/selection.py), [OpenAI adapter](../../backend/src/syncally/infrastructure/ai/openai.py), [AI context tests](../../backend/tests/test_ai_context.py), [provider tests](../../backend/tests/test_ai_provider.py), and [AI UI tests](../../frontend/src/deals/AISuggestionReview.test.tsx).

Do not conjure live credentials, zero-retention approval or private-data permission. Operator privately provisions secrets and confirms approved provider/model/account/egress controls. Default accepted offline provider remains; private context remains denied absent explicit approved organization-scoped policy. Verify provider retention through actual account/settings/contract evidence, separately from application redaction; unknown retention is BLOCKED. No legal, finance, profile verification, approval, fulfillment or autonomous authority.

Evaluate bounded human-reviewed cases: collection extraction without invented allocations, version-grounded amendment suggestions, unrecorded facts, adversarial prompt injection, foreign/private context denial, numeric/currency bounds, timeout/retry/cancellation and safe errors/logs. Record expected output, rubric, actual redacted result and human judgment; judge quality rather than network success alone. Preserve accepted grounding/human review boundary and offline fallback only where explicit policy allows; do not silently leak or claim a successful live result after fallback. Prefer no persistence; if storing evaluations, minimize retention and require approved ownership/deletion policy and actual-head migration if necessary. Run AI context/contracts/provider/UI fakes first, then elected live evaluation. Acceptance: live quality and retention/egress evidence independently accepted or explicit BLOCKED/NOT_ELECTED; no assumed private egress or provider retention guarantee.

## Step 16 Final Gates

Artifact: `16-final-gates.md`. Dependencies: mandatory 01-13 accepted with current evidence; 14/15 separately ACCEPTED, BLOCKED or explicitly NOT_ELECTED. Reverify current status, all dependency evidence and actual dirty worktree; never rerun historical counts as claims. Read current config/manifests, [operations](../operations.md), [architecture](../../ARCHITECTURE.md), [plan](../implementation-plan.md), [F12 handoff](../f12-trade-pack-handoff.md), and the owning tests touched by 01-15.

Runtime-review the complete embedded runner against current Settings/PayPalSettings/GmailSettings field/default/alias/model_config/import behavior and current security assertions before executing. Run full backend discovery with logging preserved and all database/Temporal test bodies untouched, backend ruff, frontend npm test, lint:check and build, then git diff --check with the exact exit handling above. Count skips/reasons as unmet required live gates, preserve 3 historical payment warnings and bundle warning only as historical until current output confirms/classifies them. Missing dependencies or unrelated failures are reported separately, not suppressed. Run focused regressions first for any repair and full gates again where shared risk requires them.

Independent REVIEWER must review whole current changes for fresh tenant/capability checks, private evidence/source privacy, immutable same-version bilateral approval, monetary bounds before formatting, outbox/no-network-locks, payment provenance and unknown outcomes, migration/upgrade/downgrade/reset/drain safeguards, browser/download/print/3D and live gate proof. Report severity/file:line/proof/impact/fix; DEVELOPER repairs one bounded task, max 3, never self-approves. Update relevant existing docs only now as planned truthful current-state documentation, preserving historical distinctions and unrelated user edits. Claims must match actual implementation and evidence; optional failures/non-election do not become completed integrations.

Acceptance: mandatory features and real 12/13 gates accepted, full current tests/static/build gates successful with all required skips resolved, independent review accepted, docs/progress truthful. Otherwise report project NOT_COMPLETE with blockers and exact operator actions while still finishing independent ready work. No production approval, commits, push, branches, cleanup or secret exposure. Final report: implemented/verified scope, files, commands/cwd/exits/counts/warnings/skips, reviewer findings/repairs, live versus historical evidence, optional election and remaining risks.