# 05 Collections API UI Docs - F10b

Execute this step now in SyncAlly workspace. Locate/verify git root using backend manifest/config and frontend manifest; use `C:\Proj\SyncAlly` only if accessible, otherwise located root. No original prompt/external handoff/sibling upload required. Execute, validate and report after dependency verification.

## Context and Rules

Historical **2026-10-31 F12** only: **713 run / 686 pass / 27 skip**, frontend **364 passes**, full static/build pass, **3 payment warnings and bundle warning**. Reinspect uncommitted **0012-0017**; not current passes. Historical code/independent review ACCEPTED **B1-4 Q1 F1a F2 F3 F4 F5 F6 F11a F12**, not production approval. Reuse implemented foundations; doc statuses may be stale.

Exactly three specialized role agents: **PLANNER read-only; DEVELOPER one planned task; REVIEWER independent; repair max 3; do not manually substitute if roles cannot be spawned.** Missing coordination BLOCKED, ask before manual substitution; no self-approval/pretend review. PLANNER owns read-only dependency/already-done/hypothesis/cheap-check evidence; DEVELOPER one task and immediate validation; REVIEWER severity/file:line/proof/impact/fix. Max three same-task repairs/reruns/reviews.

Conservative choices approved, not policy expansion/client roles/backfill/refunds/legal claims/private egress. Preserve existing rights/no blanket finance/fulfillment grants. Fresh server tenant/capability/private evidence authorization; immutable hash/version and human same-version bilateral approval; no AI authority, redirect proof or real-to-offline history. Atomic outbox/no network inside DB locks. Bound finite Decimal BEFORE formatting/computing. Preserve dirty tracked/untracked/user changes; reread before apply_patch edits, no cleanup/branches/commit/push/reset. Actual-head migrations never fixed 0018; upgrade preservation/history-loss downgrade block. Demo claims/paid-history/drain/0014/0017 stay intact. Fakes normally; external checks isolated opt-in. Secrets only private operator terminal, never questions/model/docs/logs. Missing policy/tools BLOCKED, continue independent tasks; mandatory unmet gates NOT_COMPLETE.

## Scope and Dependencies

Dependency **04**: all three versioned collections, explicit allocations/IDs, Decimal policy and legacy immutable bytes verified currently. Read [agreement API](../../backend/src/syncally/api/agreements.py), [negotiation application](../../backend/src/syncally/application/negotiation.py), [documents](../../backend/src/syncally/application/documents.py), [document API](../../backend/src/syncally/api/documents.py), [API client](../../frontend/src/api/client.ts), [AgreementReview](../../frontend/src/deals/AgreementReview.tsx), [NegotiationReview](../../frontend/src/deals/NegotiationReview.tsx), [document UI tests](../../frontend/src/deals/CommercialDocumentPanel.test.tsx), [route tests](../../backend/tests/test_agreement_routes.py) and [document tests](../../backend/tests/test_commercial_documents.py). Verify whether done before editing.

## Implementation Contract

Expose typed schema-versioned authoring/read/update contracts for items/shipments/payments and explicit allocations. Add/edit/remove/reorder with stable IDs, bounded validation, unsaved/pending/empty/error/stale states and visibly unrecorded fields. Connect fulfillment references without inferring allocation or financial authority. Enforce fresh server capabilities; UI does not grant rights. Review exact proposed/committed version/hash bilaterally, show meaningful collection/history diffs, invalidate stale approvals and cancel late requests on session/deal/organization change.

Extend existing F12 ZIP/HTML/print/downloads with version-aware collection/allocation tables, immutable commitment and fulfillment evidence provenance. Preserve historical legacy canonical/export bytes. Escape content/filenames, bound rendering and freshly authorize private exports. Never invent compliance, verification or missing details. Prefer projections; needed persistence follows actual-head additive migration/preservation guards. Update relevant API/user/export documentation truthfully without overwriting unrelated/historical evidence.

## Focused Checks and Gates

Test route schema/limits, duplicates/allocations, cross-tenant private exports, same-version approvals, revoked/stale UI and canceled late requests, escaping, deterministic ZIP members/download bytes and print data. Run routes/documents and AgreementReview/NegotiationReview/CommercialDocumentPanel/client tests. Shared UI contracts require lint:check/build; full gates when required: all backend test_*.py with safe runner, ruff src tests, npm test/lint:check/build, git diff --check and immediate `$LASTEXITCODE`. Never execute embedded commands during authoring.

Runtime-review [config](../../backend/src/syncally/config.py)/[frontend scripts](../../frontend/package.json) and runner against current security/provider tests. Settings/PayPalSettings/GmailSettings BaseSettings metadata/defaults/aliases/model_config dynamically control isolation; Settings global imports with production APP_ENV default. Ignore dotenv ONLY for bootstrap/discovery; restore normal constructor before bodies, clear all settings names case-insensitively, preserve TEST_POSTGRES_URL/SYNCALLY_TEMPORAL_*, finally restore original child environment. No skip/logging/Temporal startup/module/security/provider patches. New required/complex aliases require review. Configured Python 3.12+ venv required, no silent installations/services.

```powershell
$Root = (Get-Location).Path
while (-not ((Test-Path (Join-Path $Root 'backend/pyproject.toml')) -and (Test-Path (Join-Path $Root 'frontend/package.json')))) {
    $Parent = Split-Path $Root -Parent
    if (-not $Parent -or $Parent -eq $Root) { throw 'Locate SyncAlly root' }
    $Root = $Parent
}
$Python = @((Join-Path $Root 'backend/.venv/Scripts/python.exe'), (Join-Path $Root '.venv/Scripts/python.exe')) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Python) { $Python = (Get-Command python -ErrorAction Stop).Source }
Set-Location (Join-Path $Root 'backend')
@'
import os, sys, unittest
from pydantic_core import PydanticUndefined
from pydantic_settings import BaseSettings
assert sys.version_info >= (3, 12)
saved = dict(os.environ)
normal = BaseSettings.__init__
def aliases(value):
    if isinstance(value, str): return {value}
    if getattr(value, "choices", None): return set().union(*(aliases(choice) for choice in value.choices))
    return {value.path[0]} if getattr(value, "path", None) else set()
def key(name, field):
    if getattr(field.validation_alias, "path", None): raise RuntimeError("Review AliasPath bootstrap")
    return next(iter(sorted(aliases(field.validation_alias) or aliases(field.alias))), name)
def bootstrap(self, **kwargs):
    fields = type(self).model_fields
    values = {}
    for name, field in fields.items():
        value = field.get_default(call_default_factory=True)
        if value is PydanticUndefined: raise RuntimeError("Review required settings field: " + name)
        values[key(name, field)] = value
    if type(self).__name__ == "Settings":
        for name, value in dict(app_env="test", database_url="sqlite+pysqlite:///:memory:", ai_provider="offline", payment_mode="OFFLINE_DEMO").items(): values[key(name, fields[name])] = value
    for name, value in kwargs.items():
        match = next(((field_name, field) for field_name, field in fields.items() if name == field_name or name in aliases(field.alias) | aliases(field.validation_alias)), None)
        if match:
            field_name, field = match
            for old_key in {field_name} | aliases(field.alias) | aliases(field.validation_alias): values.pop(old_key, None)
            values[key(field_name, field)] = value
        else: values[name] = value
    values["_env_file"] = None
    normal(self, **values)
def clear(models):
    names = set()
    for model in models:
        for name, field in model.model_fields.items(): names.update(value.casefold() for value in {name, model.model_config.get("env_prefix", "") + name} | aliases(field.alias) | aliases(field.validation_alias))
    for name in tuple(os.environ):
        folded = name.casefold()
        if folded in names and folded != "test_postgres_url" and not folded.startswith("syncally_temporal_"): del os.environ[name]
try:
    BaseSettings.__init__ = bootstrap
    os.environ.update(APP_ENV="test", DATABASE_URL="sqlite+pysqlite:///:memory:", AI_PROVIDER="offline", PAYMENT_MODE="OFFLINE_DEMO")
    import syncally.config as config
    models = (config.Settings, config.PayPalSettings, config.GmailSettings)
    clear(models)
    os.environ.update(APP_ENV="test", DATABASE_URL="sqlite+pysqlite:///:memory:", AI_PROVIDER="offline", PAYMENT_MODE="OFFLINE_DEMO")
    loader = unittest.TestLoader()
    patterns = ('test_agreement_routes.py', 'test_commercial_documents.py')
    suite = unittest.TestSuite(loader.discover('tests', pattern=pattern, top_level_dir='tests') for pattern in patterns)
    BaseSettings.__init__ = normal
    clear(models)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    code = 0 if result.wasSuccessful() and not loader.errors else 1
finally:
    BaseSettings.__init__ = normal
    os.environ.clear()
    os.environ.update(saved)
sys.exit(code)
'@ | & $Python -
if ($LASTEXITCODE -ne 0) { throw 'Focused backend tests/discovery failed' }
Set-Location (Join-Path $Root 'frontend')
npm test -- src/deals/AgreementReview.test.tsx src/deals/NegotiationReview.test.tsx src/deals/CommercialDocumentPanel.test.tsx src/api/client.test.ts
if ($LASTEXITCODE -ne 0) { throw 'Focused UI tests failed' }
npm run lint:check
if ($LASTEXITCODE -ne 0) { throw 'Frontend static gate failed' }
npm run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
```

## Acceptance and Completion Report

Collection authoring through bilateral reviewed commitment and authorized deterministic version-aware exports works, immutable legacy data and private evidence preserved. Independent review required. Append progress UTC/05/dependency/roles/file:line/version evidence/commands/cwd/exits/counts/skips/artifacts/findings severity-proof-impact-fix/repairs 0-3. NOT_RUN to ACCEPTED only with current review/checks, otherwise BLOCKED. Report implemented files/behavior/docs/checks/risks, continue independent tasks.