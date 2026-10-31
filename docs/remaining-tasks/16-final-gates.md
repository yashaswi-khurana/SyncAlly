# 16 Final Gates and Truthful Completion

Execute this step now in SyncAlly workspace. Locate/verify git root via backend manifest/config and frontend manifest; use accessible `C:\Proj\SyncAlly` or located root. No original prompt/external handoff/sibling upload. Execute every ready validation/review/doc task and report actual outcome, not plan-only or fake project completion.

## Context and Rules

Historical **2026-10-31 F12** only: backend **713 run / 686 pass / 27 skip**, frontend **364 passes**, full static/build pass, **3 payment warnings and bundle warning**. Reinspect uncommitted **0012-0017**, not current passed claims. Historical code/independent review ACCEPTED **B1-4 Q1 F1a F2 F3 F4 F5 F6 F11a F12**, neither current full gates nor production approval. Reuse implemented foundations, existing documentation statuses may be stale.

Exactly three specialized role agents: **PLANNER read-only; DEVELOPER one planned task; REVIEWER independent; repair max 3; do not manually substitute if roles cannot be spawned.** Missing coordination BLOCKED/ask before manual substitution, never self-approve/pretend agents. PLANNER current owner/tests/dependencies/already-done/hypothesis/cheap check; DEVELOPER one planned validation/doc/repair task and immediate focused post-edit check; REVIEWER independent severity/file:line/proof/impact/fix, max three same-task repairs/reruns/reviews. Final review includes entire current worktree, not just authored steps.

Conservative choices approved, not policy expansion/client roles/backfills/refunds/legal claims/private egress. Preserve rights/no blanket finance/fulfillment. Fresh server tenant/capability/private evidence/source/privacy/export checks; immutable committed hash/version, human same-version bilateral approval/no AI authority. Redirect not proof, real history never offline. Atomic durable outbox/no network inside DB locks; bounded finite Decimal BEFORE formatting/computing. Preserve all dirty tracked/untracked/user changes, reread before apply_patch; no cleanup/branches/commit/push/reset. Actual-head migration never fixed 0018; fresh/upgrade preservation/history-loss downgrade block. Keep demo claim/paid-history/drain/0014/0017 safeguards. Fakes normally; actual browser/DB/Temporal and elected provider checks isolated approved environments. Secrets private operator terminal only, never questions/model/docs/logs. Missing dependencies/tooling/policy BLOCKED, continue independent tasks; mandatory unmet gate means NOT_COMPLETE.

## Scope and Dependencies

Mandatory **01-13** accepted from current code/evidence/independent review, including real desktop/mobile two-party Three.js pixel/assets/motion/layout/download/print and isolated PostgreSQL/Temporal migration/race/restart gates. Optional **14/15** separately ACCEPTED, BLOCKED or explicitly NOT_ELECTED; neither absent credentials nor guessed retention means completion. Reverify status/current dirty tracked/untracked paths and actual migration heads; do not trust old labels. Read [config](../../backend/src/syncally/config.py), [backend manifest](../../backend/pyproject.toml), [frontend manifest](../../frontend/package.json), [operations](../operations.md), [architecture](../../ARCHITECTURE.md), [plan](../implementation-plan.md), [F12 handoff](../f12-trade-pack-handoff.md) and owning tests touched by all tasks. This document provides its own full gates without sibling upload dependency.

## Implementation and Review Contract

Runtime-verify the embedded runner against current Settings/PayPalSettings/GmailSettings `.model_fields`, defaults/factories/aliases, `model_config`, dotenv sources and global import-time `settings = Settings()`. APP_ENV defaults production; preserve fail-closed tests. Reinspect growth/new settings fields before use, review unsupported required fields/complex aliases instead of hiding provider/security failures. Normal dotenv/settings construction must be restored before test bodies. Do not mask security/provider config, disable logging/assertLogs, alter skips/Temporal startup/server test modules or make integration selection disappear. Explicit TEST_POSTGRES_URL/SYNCALLY_TEMPORAL_* are preserved. Every native exit must be checked immediately in Windows PowerShell 5.1; no shell && (existing npm scripts internally && are fine).

Run focused regressions first after any bounded repair. Run current full backend discovery, backend ruff, frontend npm test/lint:check/build and git diff --check below. Report counts/warnings/skips and discovery errors; historical counts/warnings are not current output. Unexpected failures remain failures, unrelated defects separately reported not repaired without scope approval. Native skips are unfulfilled required live gates; a green unittest result with mandatory skipped integration is NOT_COMPLETE. Do not install/start services implicitly; current dependency/service provisioning needs its appropriate approved isolated step.

Independent REVIEWER verifies fresh authority/tenant isolation/private exports/contacts/profile UNVERIFIED authority, exact-version bilateral approvals/history, money-before-format bounds, trigger eligibility versus finance authority, payment provenance/unknown outcomes/idempotency, durable outbox/no-network-locks, migration upgrade/downgrade/reset/drain/paid-history, browser artifacts and actual live evidence. Report severity/file:line/proof/impact/fix and repair count. DEVELOPER repairs one planned slice max 3, reruns affected focused tests and required full gates; no self-approval.

Update relevant existing API/user/architecture/operations/plan/F12 docs only as authorized truthful final documentation, preserving historical evidence and unrelated user edits. State which features and gates truly exist, what remains blocked/not elected and current runbook/migration constraints. Do not relabel old accepted code as current production approval, optional integrations as completed, or mandatory skipped checks as passed.

## Complete Full Gate Runner

Use configured backend/root venv Python, fallback active Python 3.12+ with installed dependencies; no silent installs. Child runner snapshots environment privately, temporarily wraps BaseSettings init during import/discovery using metadata defaults plus explicit local constructor inputs and `_env_file=None`. It never bypasses validators. Dynamically clear all inherited field/prefix/alias names case-insensitively across the three settings classes; preserve explicit integration inputs; restore normal init/dotenv before test bodies and original env finally. Missing required/complex aliases fail closed pending review. No embedded full-suite execution during Markdown authoring.

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
    suite = loader.discover('tests', pattern='test_*.py', top_level_dir='tests')
    BaseSettings.__init__ = normal
    clear(models)
    if BaseSettings.__init__ is not normal or any(name.casefold() == 'app_env' for name in os.environ): raise RuntimeError('Body isolation failed')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    code = 0 if result.wasSuccessful() and not loader.errors else 1
finally:
    BaseSettings.__init__ = normal
    os.environ.clear()
    os.environ.update(saved)
sys.exit(code)
'@ | & $Python -
if ($LASTEXITCODE -ne 0) { throw 'Full backend tests/discovery failed' }
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

## Acceptance and Completion Report

All mandatory features and real 12/13 gates accepted, current full tests/static/build successful with every required skip resolved, independent whole-worktree review accepted, docs/progress truthful. Otherwise **NOT_COMPLETE**, exact blockers/operator actions while continuing independent ready work. Append progress UTC/16/dependencies/roles/current versions-diff/file:line proof/commands/cwd/exits/run-pass-fail-skip and reasons/current warnings/artifacts/findings severity-proof-impact-fix/repairs 0-3. Initial NOT_RUN; separate implementation/live/optional/historical/production status. Final report implemented/verified scope/files/checks/results/review repairs/optional election/open risks; no commits/branches/push/cleanup/secrets/production approval.