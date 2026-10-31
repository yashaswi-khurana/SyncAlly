# 13 PostgreSQL Temporal

Execute this step now in SyncAlly workspace. Locate/verify git root via backend manifest/config and frontend manifest; use accessible `C:\Proj\SyncAlly` or located root. No original prompt/external handoff/sibling upload. Execute genuine isolated verification after prerequisites; do not stop after a plan or fake live success.

## Context and Rules

Historical **2026-10-31 F12** only: **713 run / 686 pass / 27 skip**, frontend **364 passes**, full static/build pass, **3 payment warnings and bundle warning**. Reinspect uncommitted **0012-0017**, not current validation. Historical code/independent review ACCEPTED **B1-4 Q1 F1a F2 F3 F4 F5 F6 F11a F12**, no production approval. Reuse database/workflow/payment/outbox/demo foundations; doc statuses may be stale.

Exactly three specialized role agents: **PLANNER read-only; DEVELOPER one planned task; REVIEWER independent; repair max 3; do not manually substitute if roles cannot be spawned.** Missing coordination BLOCKED/ask before manual substitution, no self-approval/pretend review. PLANNER owner/tests/dependencies/already-done/hypothesis/check; DEVELOPER one verification/assigned repair/immediate validation; REVIEWER severity/file:line/proof/impact/fix; max three repairs/reruns/reviews.

Conservative choices approved, not policy expansion/client roles/backfill/refunds/legal claims/private egress. Preserve rights/no blanket finance/fulfillment. Fresh server tenant/capability/private evidence checks; immutable hash/version, human same-version bilateral approval/no AI authority. No redirect proof/real-to-offline history. Atomic outbox/no network inside DB locks; bounded finite Decimal BEFORE formatting/computing. Preserve all dirty tracked/untracked/user changes; reread before apply_patch, no cleanup/branches/commit/push/reset. Actual-head migrations never fixed 0018, upgrades preserve data/downgrades block history loss. Keep demo claims/paid-history/drain/0014/0017 safeguards. Fakes for external provider calls, real isolated PostgreSQL/Temporal only with explicit approval. Secrets private operator terminal, never questions/model/docs/logs. Missing tools/services/policy BLOCKED; continue independent tasks, mandatory unmet gates NOT_COMPLETE.

## Scope and Dependencies

Dependencies **01-11**, currently accepted from code/check/review evidence. Browser gate 12 independently mandatory for final completion, not prerequisite here. Require approved isolated PostgreSQL database/schema and Temporal environment/namespace, worker ownership and safe restart scope. Never production/customer/shared database or destructive teardown. Read [Alembic environment](../../backend/alembic/env.py), [database](../../backend/src/syncally/infrastructure/database.py), [worker](../../backend/src/syncally/workflows/worker.py), [operations](../operations.md), [database tests](../../backend/tests/test_database.py), [worker tests](../../backend/tests/test_workflow_worker.py), [migration config tests](../../backend/tests/test_migration_config.py), [demo locks](../../backend/tests/test_demo_lifecycle_lock.py) and inspect all actual migration versions including 0012-0017. Verify current test-specific TEST_POSTGRES_URL/SYNCALLY_TEMPORAL_* contracts privately without printing credentials.

## Verification Contract

Inspect actual Alembic heads/dependency chain and current deployed revisions before selecting new migration names; never assume 0018. Use separate isolated fresh-install and representative prechange-upgrade databases with committed hash/version, paid/in-flight intents/create-started provenance, demo claim/lock and legacy exports. Verify constraints/indexes/foreign keys/uniqueness, new capability defaults, collections/allocations and unchanged historical bytes. Exercise transactional rollback; history-loss downgrade must refuse, not delete records. Do not use downgrade/reset as cleanup.

Run actual PostgreSQL competing tenant/approval/fulfillment/milestone/amendment/case transitions, worker lease/outbox idempotency and create-started races. Assert one active milestone intent/no duplicate invoice using approved provider fakes, no network inside DB locks and private source/error/log safety. Restart approved isolated workers with pending timers/outbox: replay/durable notifications, safe drain/shutdown, lease recovery and demo reset claims/paid history under 0014/0017 remain correct. Record exact schemas/revisions, scenario timing/assertions and anonymized evidence; SQLite/mocks cannot satisfy database locking/Temporal replay.

Run current genuine integration/smoke contracts without changing skips, server availability, test modules, Temporal startup or downloads to manufacture a pass. Explicitly provision approved inputs privately; runner preserves them. Missing dependencies/native skips remain unmet mandatory gates. If a test's normal Temporal startup behavior is not authorized for this environment, BLOCKED rather than patching it. Repairs require one bounded PLANNER task, immediate focused rerun and independent review, max 3. No new persistence unless a real defect requires reviewed actual-head migration/preservation.

## Focused Checks and Gates

Review [config](../../backend/src/syncally/config.py)/[frontend scripts](../../frontend/package.json) and runner against current security/provider tests before runtime. Settings/PayPalSettings/GmailSettings BaseSettings fields/defaults/aliases/model_config are dynamic; global Settings import defaults APP_ENV production. Ignore dotenv only discovery, restore normal construction before bodies, clear inherited settings case-insensitively, preserve TEST_POSTGRES_URL/SYNCALLY_TEMPORAL_*, restore original child env finally. No logging/skip/Temporal startup/module/security/provider masking. New required/complex aliases fail pending reviewed runner update. Use configured Python 3.12+ venv, no silent installs/elevation/service teardown. Full gates when required: safe all backend discovery, ruff src tests, npm test/lint:check/build, git diff --check, immediate `$LASTEXITCODE`. No embedded execution during authoring.

Run migration commands below ONLY after the operator privately provisions the approved isolated destination and PLANNER verifies it without secret exposure. Run separately for fresh and upgrade environments; preserve current environment/worker ownership and historical data.

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
& $Python -m alembic heads
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect actual migration heads' }
& $Python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Isolated upgrade failed' }
& $Python -m alembic current
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify isolated current revision' }
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
    patterns = ('test_*migration.py', 'test_migration_config.py', 'test_database*.py', 'test_workflow*.py', 'test_demo_lifecycle_lock.py', 'test_payment_processing.py', 'test_outbox_dispatcher.py', 'test_local_workflow_smoke.py')
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
if ($LASTEXITCODE -ne 0) { throw 'Isolated backend tests/discovery failed' }
```

## Acceptance and Completion Report

Actual fresh/upgrade PostgreSQL constraints/history/locking and genuine Temporal race/restart/replay/drain evidence independently accepted, not SQLite/mock/native skip substitution. Append progress UTC/13/dependencies/roles/redacted destination/revisions/file:line and scenario proof/commands/cwd/exits/counts/skips/artifacts/findings severity-impact-fix/repairs 0-3. NOT_RUN to ACCEPTED only current real evidence/review; otherwise BLOCKED. Report failures/tooling/operator actions; mandatory unmet gate means NOT_COMPLETE.