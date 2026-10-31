# 11 Judge Demo - F1b

Execute this step now in SyncAlly workspace. Locate/verify git root via backend manifest/config and frontend manifest; prefer accessible `C:\Proj\SyncAlly`, otherwise located root. No original prompt/external handoff/sibling upload. Execute after verified dependencies, not plan-only.

## Context and Rules

Historical **2026-10-31 F12** only: **713 run / 686 pass / 27 skip**, frontend **364 passes**, full static/build pass, **3 payment warnings and bundle warning**. Reinspect uncommitted **0012-0017**, not current passes. Historical code/independent review ACCEPTED **B1-4 Q1 F1a F2 F3 F4 F5 F6 F11a F12**, no production approval. Extend accepted demo/reset/offline foundations; doc statuses may be stale.

Exactly three specialized role agents: **PLANNER read-only; DEVELOPER one planned task; REVIEWER independent; repair max 3; do not manually substitute if roles cannot be spawned.** Missing coordination BLOCKED/ask before manual substitution, no self/pretend approval. PLANNER owner/tests/dependencies/already-done/hypothesis/check; DEVELOPER one task/immediate validation; REVIEWER severity/file:line/proof/impact/fix, max three repairs/reruns/reviews.

Conservative choices approved, not policy expansion/client roles/backfill/refunds/legal claims/private egress. Preserve rights/no blanket finance/fulfillment grants; fresh tenant/capability/private evidence checks. Immutable committed hash/version, human same-version bilateral approvals/no AI authority. No redirect proof/real-to-offline conversion. Transactional durable outbox/no network inside DB locks; finite bounded Decimal BEFORE formatting/calculation. Preserve dirty tracked/untracked/user changes, reread before apply_patch; no cleanup/branch/commit/push/reset. Actual-head migration never fixed 0018; upgrade preservation/history-loss downgrade block. Keep demo claims/paid-history/drain/0014/0017 safeguards. Fakes normally; external isolated opt-in. Secrets private operator terminal only, not questions/model/docs/logs. Missing policy/tools BLOCKED; continue independent steps, mandatory unmet gates NOT_COMPLETE.

## Scope and Dependencies

Dependencies **01-10** verified individually from current code/evidence, not labels. Read [seed](../../backend/src/syncally/cli/seed_demo.py), [lifecycle](../../backend/src/syncally/infrastructure/demo_lifecycle.py), [offline payments](../../backend/src/syncally/infrastructure/offline_payments.py), [seed tests](../../backend/tests/test_demo_seed.py), [lifecycle tests](../../backend/tests/test_demo_lifecycle.py), [lock tests](../../backend/tests/test_demo_lifecycle_lock.py), [local smoke](../../backend/tests/test_local_workflow_smoke.py), [App tests](../../frontend/src/App.test.tsx) and [operations](../operations.md). Verify done before editing.

## Implementation Contract

Reproducible preparation and two-party judge journey covering profile capabilities/products/regions/private contacts/UNVERIFIED authority, explicit authorization, collection draft/negotiation, exact-version bilateral commitment, partial fulfillment, authorized milestones, amendment impact, cancellation/dispute request versus decision, routing/reminders and F12 downloads. Use controlled fixtures and clearly marked OFFLINE_DEMO; no real payment/verified organization/legal/AI-authority claims. Handle realistic empty/pending/error/retry transitions and two isolated sessions with no leakage.

Preserve accepted claim locks, worker drain before supported reset, 0014/0017 safeguards, paid/in-flight history and real provenance. Never erase protected history or convert real payments offline for a clean demo. Use existing supported seed/reset commands after inspecting current CLI/help/contracts; no invented destructive command or service startup. Fixture persistence follows current actual head; add migration only if genuinely required, preserving history/downgrade guards. Update authorized runbook/demo docs truthfully with preparation/stop/recovery conditions and simulation boundaries.

## Focused Checks and Gates

Test deterministic reseed/idempotency, claims/lock races, reset refusal, paid-history preservation, current collection fixtures and complete local two-party journey using fakes. Run demo/lifecycle/local smoke/App/detail tests below. Real browser/3D/download/print and PostgreSQL/Temporal evidence remain separate mandatory gates. Full gates when needed: safe full backend discovery, ruff src tests, npm test/lint:check/build, git diff --check with immediate `$LASTEXITCODE`; no embedded execution now.

Runtime-review [config](../../backend/src/syncally/config.py)/[scripts](../../frontend/package.json) and runner against current security/provider tests. Global Settings at import defaults APP_ENV production. Dynamically handle all Settings/PayPalSettings/GmailSettings BaseSettings fields/defaults/aliases/model_config; ignore dotenv only bootstrap/discovery; restore normal construction before bodies, clear settings case-insensitively, preserve TEST_POSTGRES_URL/SYNCALLY_TEMPORAL_*, restore child env finally. No logging/skip/Temporal startup/module/security/provider patches. Required/complex aliases fail pending review; Python 3.12+ configured venv, no silent installs/services.

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
    patterns = ('test_demo*.py', 'test_local_workflow_smoke.py')
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
npm test -- src/App.test.tsx src/deals/DealDetailPage.test.tsx
if ($LASTEXITCODE -ne 0) { throw 'Focused UI tests failed' }
npm run lint:check
if ($LASTEXITCODE -ne 0) { throw 'Frontend static gate failed' }
```

## Acceptance and Completion Report

Repeatable two-party reviewed judge journey covers 01-10 while preserving claims/paid history/drain and simulation truth. Independent review required. Append progress UTC/11/dependencies/roles/file:line/version evidence/commands/cwd/exits/counts/skips/artifacts/findings severity-proof-impact-fix/repairs 0-3. NOT_RUN to ACCEPTED only with current focused review/checks, otherwise BLOCKED. Report implementation/files/runbook/checks/risks; do not call browser/live gates completed by fixtures.