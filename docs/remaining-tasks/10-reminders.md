# 10 Reminders - F13

Execute this step now in SyncAlly workspace. Locate/verify git root via backend manifest/config and frontend manifest; use accessible `C:\Proj\SyncAlly` or located root. No original prompt/external handoff/sibling upload. Execute the ready bounded task, not plan-only.

## Context and Rules

Historical **2026-10-31 F12** only: **713 run / 686 pass / 27 skip**, frontend **364 passes**, static/build pass, **3 payment warnings and bundle warning**. Uncommitted **0012-0017** require reinspection; not current validation. Historical code/independent review ACCEPTED **B1-4 Q1 F1a F2 F3 F4 F5 F6 F11a F12**, no production approval. Reuse workflow/outbox/notification foundation; docs may be stale.

Exactly three specialized role agents: **PLANNER read-only; DEVELOPER one planned task; REVIEWER independent; repair max 3; do not manually substitute if roles cannot be spawned.** Unavailable coordination BLOCKED/ask before manual substitution, no self/pretend approval. PLANNER owner/tests/dependencies/already-done/hypothesis/check; DEVELOPER one task/immediate focused validation; REVIEWER severity/file:line/proof/impact/fix, max three repairs/reruns/reviews.

Conservative choices approved, not policy expansion/client roles/backfill/refunds/legal claims/private egress. Preserve rights/no blanket finance/fulfillment. Fresh tenant/capability/private evidence checks; immutable hash/version, human same-version bilateral approval/no AI authority. Redirect not proof, real history never offline. Atomic durable outbox/no network inside DB locks; finite bounded Decimal BEFORE formatting/computing. Preserve dirty tracked/untracked/user changes, reread before apply_patch, no cleanup/branch/commit/push/reset. Actual-head migration never fixed 0018; upgrade preservation/history-loss downgrade block, demo claims/paid-history/drain/0014/0017 intact. Fakes normally, external isolated opt-in. Secrets private operator terminal only, not questions/model/docs/logs. Policy/tools absent BLOCKED, continue independent steps, mandatory unmet gates NOT_COMPLETE.

## Scope and Dependencies

Dependencies **03, 06, 08, 09**: current fulfillment, milestones, cases and routing verified. Read [workflow](../../backend/src/syncally/workflows/deal.py), [notifications](../../backend/src/syncally/application/workflow_notifications.py), [outbox application](../../backend/src/syncally/application/outbox.py), [outbox infrastructure](../../backend/src/syncally/infrastructure/outbox.py), [dispatcher tests](../../backend/tests/test_outbox_dispatcher.py), [worker tests](../../backend/tests/test_workflow_worker.py), [operations tests](../../backend/tests/test_operations.py) and [detail UI](../../frontend/src/deals/DealDetailPage.tsx). Verify whether already implemented before editing.

## Implementation Contract

Durable scoped reminder schedules for outstanding fulfillment, eligible-but-unacted milestones, unresolved cases and routing. Explicitly define UTC/timezone semantics, due times, recurrence cap, deduplication key, channel, retry/backoff and resolved/superseded suppression. Default existing authorized in-app delivery, no unapproved automatic email or remote private egress. Reminder never automatically approves, expires, pays or escalates obligations. Dispatch rechecks version/current state, recipient membership/capability and resolved/superseded facts.

Replay-safe workflow timers and transactional schedule/state/audit/outbox, identifier-only payloads, network outside DB locks, safe logs without private bodies/contacts. Persist only needed durable state with actual-head additive migration/upgrade/downgrade guards. UI truthfully shows scheduled/pending/delivered/failed/suppressed, not invented delivery. Define cancellation/suppression on organization switching and state supersession.

## Focused Checks and Gates

Test mocked exact clocks and tolerant Windows elapsed budgets separately, timezone/daylight boundaries, duplicate/retry/worker restart, resolved/superseded suppression, recipient revocation and source privacy. Run workflow/outbox/operations/detail UI checks below; real replay/restart gate later requires isolated Temporal, not mocks. Full gates when needed: safe all backend discovery, ruff src tests, npm test/lint:check/build, git diff --check, immediate `$LASTEXITCODE`. No embedded execution during authoring.

Runtime-review [config](../../backend/src/syncally/config.py)/[scripts](../../frontend/package.json) and runner against security/provider tests. Global Settings import defaults APP_ENV production; derive all Settings/PayPalSettings/GmailSettings BaseSettings fields/defaults/aliases/model_config. Ignore dotenv only bootstrap/discovery, restore normal construction before bodies, clear settings case-insensitively, preserve TEST_POSTGRES_URL/SYNCALLY_TEMPORAL_*, restore child env finally. No logging/skip/Temporal startup/module/security/provider patches. Required/complex aliases fail pending review; Python 3.12+ configured venv, no silent installs/services.

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
    patterns = ('test_outbox_dispatcher.py', 'test_workflow_worker.py', 'test_operations.py')
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

Scoped durable reminders retry/replay/suppress safely without authority or privacy leakage; independent focused review accepted, live restart separately pending until genuine evidence. Append progress UTC/10/dependencies/roles/file:line/version evidence/commands/cwd/exits/counts/skips/artifacts/findings severity-proof-impact-fix/repairs 0-3. NOT_RUN to ACCEPTED only current checks/review, otherwise BLOCKED. Report files/behavior/checks/risks, continue independent tasks.