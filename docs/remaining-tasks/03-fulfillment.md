# 03 Fulfillment - F9

Execute this step now in SyncAlly workspace. Locate/verify repository root from backend manifest/config and frontend manifest; use accessible `C:\Proj\SyncAlly` or located root, never assume external paths. No original prompt or sibling upload needed. Execute the bounded task now after dependency verification.

## Context and Rules

Historical **2026-10-31 F12**: backend **713 run / 686 pass / 27 skip**, frontend **364 passes**, full static/build pass, **3 payment warnings and bundle warning**; not current validation. Uncommitted **0012-0017** need reinspection. Historical code/independent review ACCEPTED **B1-4 Q1 F1a F2 F3 F4 F5 F6 F11a F12**, not production approval. Reuse identity/agreement/payment/workflow/demo/export foundations; doc statuses may be stale.

Exactly three specialized role agents: **PLANNER read-only; DEVELOPER one planned task; REVIEWER independent; repair max 3; do not manually substitute if roles cannot be spawned.** Missing coordination BLOCKED; ask before manual substitution, never self-approve. PLANNER reads owner/tests, verifies done/dependencies and hypothesis/cheap check. DEVELOPER one task, immediate post-edit scoped validation. REVIEWER independent severity/file:line/proof/impact/fix; max three repairs with rerun/review.

Conservative choices approved, not policy expansion/client roles/backfills/refunds/legal claims/private egress. Preserve existing rights; no blanket finance/fulfillment grants. Fresh server tenant/capability and private evidence/export checks, immutable committed hash/version, human same-version bilateral approval, no AI authority. Redirects not proof, no real-to-offline history. Atomic outbox, no network inside DB locks; finite bounded Decimal BEFORE formatting/calculation. Preserve dirty tracked/untracked/user changes; reread before apply_patch edits; no cleanup/branch/commit/push/reset. Actual-head migration, never fixed 0018, upgrade preservation/history-loss downgrade block. Keep demo claims/paid history/drain/0014/0017. Fakes normally, isolated opt-in external checks; secrets private operator terminal only, not model/questions/docs/logs. Missing policy/tools BLOCKED, continue independent tasks; unmet mandatory gates NOT_COMPLETE.

## Scope and Dependencies

Dependency **02**: fresh explicit capabilities/approval continuity, no new blanket grants, independently verified. Read [obligations](../../backend/src/syncally/domain/agreements/obligations.py), [deal domain](../../backend/src/syncally/domain/deals/deal.py), [deal application](../../backend/src/syncally/application/deals.py), [workflow](../../backend/src/syncally/workflows/deal.py), [deal models](../../backend/src/syncally/infrastructure/models/deals.py), [deal tests](../../backend/tests/test_deal_use_cases.py), [workflow tests](../../backend/tests/test_deal_workflow.py) and [detail UI/tests](../../frontend/src/deals/DealDetailPage.test.tsx). Check already-implemented behavior before editing.

## Implementation Contract

Persist append-only shipment/delivery observations and authorized confirmations linked to immutable committed version/hash and obligation IDs. Begin with supported legacy single-item terms. Distinguish planned/shipped/observed/confirmed facts, actor/time/source and bounded quantities/units. Missing evidence remains unrecorded; AI/carrier URL alone not confirmation. Define fresh existing fulfillment authority, no new implicit privilege. Private evidence references require tenant/deal entitlement on every access; sanitize external references and keep bodies/contacts out of errors/logs.

Support partial deliveries, explicit idempotency keys, optimistic version conflicts and audit rollback. Derive fulfillment from obligation quantities/facts, not a status click. Deal completion requires actual fulfilled obligations AND reconciled required payments, not delivery alone or paid alone. No title transfer/legal acceptance/compliance assertions. Persist state/audit/outbox atomically; notify after commit without network inside locks. Add typed API/UI commands/history with pending/empty/stale/error/revoked states. Needed additive migration follows actual head, preserves historical data and blocks lossy downgrade.

## Focused Checks and Gates

Test partial/duplicate/overdelivery, units and numeric bounds, foreign/revoked actors, observation-versus-confirmation, competing updates, transaction rollback, canceled/superseded references and paid/unfulfilled versus delivered/unpaid completion. Run deal/workflow/detail UI tests below; touched lint/typecheck and shared-contract gates when required. Full gates: backend runner with all test_*.py, ruff check src tests, npm test/lint:check/build, git diff --check, immediate `$LASTEXITCODE`. Never run embedded gates during authoring.

At runtime review [config](../../backend/src/syncally/config.py)/[frontend scripts](../../frontend/package.json) and runner against current security/provider tests. Global Settings import defaults APP_ENV production; all Settings/PayPalSettings/GmailSettings BaseSettings fields/defaults/aliases/model_config must remain dynamically handled. Bootstrap ignores dotenv only during import/discovery; restore normal construction before bodies, clear configuration case-insensitively, preserve TEST_POSTGRES_URL/SYNCALLY_TEMPORAL_* and original child env finally. No logging/skip/Temporal startup/module/security masking. New required/complex alias fields fail closed pending reviewed runner update; configured Python 3.12+ venv required, no silent installs/services.

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
    patterns = ('test_deal_use_cases.py', 'test_deal_workflow.py')
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
npm test -- src/deals/DealDetailPage.test.tsx
if ($LASTEXITCODE -ne 0) { throw 'Focused UI tests failed' }
npm run lint:check
if ($LASTEXITCODE -ne 0) { throw 'Frontend static gate failed' }
```

## Acceptance and Completion Report

Authorized version-owned fulfillment facts, partial delivery and derived paid-plus-fulfilled completion proven without invented authority/payment/legal facts. Independent review required. Append progress UTC/03/dependencies/roles/file:line/version evidence/commands/cwd/exits/counts/skips/artifacts/findings severity-proof-impact-fix/repairs 0-3. NOT_RUN to ACCEPTED only from current checks/review; otherwise BLOCKED. Report scope/files/checks/risks and continue independent ready tasks without declaring unmet gates complete.