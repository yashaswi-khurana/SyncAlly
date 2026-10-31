# 08 Cancel Disputes - F8

Execute this step now in SyncAlly workspace. Locate/verify git root using backend manifest/config and frontend manifest; use accessible `C:\Proj\SyncAlly` or located root. No original prompt/external handoff/sibling upload required. Execute after dependency verification.

## Context and Rules

Historical **2026-10-31 F12** only: **713 run / 686 pass / 27 skip**, frontend **364 passes**, full static/build pass, **3 payment warnings and bundle warning**. Uncommitted **0012-0017** need reinspection; not current passes. Historical code/independent review ACCEPTED **B1-4 Q1 F1a F2 F3 F4 F5 F6 F11a F12**, not production approval. Reuse lifecycle/agreement/payment/outbox/history, existing doc statuses may be stale.

Exactly three specialized role agents: **PLANNER read-only; DEVELOPER one planned task; REVIEWER independent; repair max 3; do not manually substitute if roles cannot be spawned.** Missing coordination BLOCKED; ask before manual substitution, never self-approve/pretend review. PLANNER reads owning files/tests/dependencies/already-done/hypothesis/check; DEVELOPER one task/immediate validation; REVIEWER severity/file:line/proof/impact/fix, max three same-task repairs/reruns/reviews.

Conservative choices approved, not policy expansion/client roles/backfills/refunds/legal claims/private egress. Preserve rights/no blanket finance/fulfillment. Fresh tenant/capability/private evidence checks; immutable committed hash/version, human same-version bilateral approval/no AI authority. Redirect not proof, no real-to-offline history. Atomic durable outbox/no network inside DB locks; finite bounded Decimal BEFORE formatting/calculation. Preserve all dirty tracked/untracked/user changes, reread before apply_patch; no cleanup/branch/commit/push/reset. Actual-head migration never fixed 0018; upgrade preservation/history-loss downgrade block, demo claims/paid-history/drain/0014/0017 intact. Fakes normally; isolated opt-in external gates. Secrets private operator terminal only, not questions/model/docs/logs. Missing policy/tools BLOCKED, continue independent tasks; mandatory unmet gates NOT_COMPLETE.

## Scope and Dependencies

Dependencies **03, 06, 07**: fulfillment/finance/immutable amendment impact verified currently. Read [deal domain](../../backend/src/syncally/domain/deals/deal.py), [deal application](../../backend/src/syncally/application/deals.py), [deal API](../../backend/src/syncally/api/deals.py), [activities](../../backend/src/syncally/workflows/activities.py), [payments](../../backend/src/syncally/application/payment_processing.py), [deal tests](../../backend/tests/test_deal_use_cases.py), [workflow tests](../../backend/tests/test_deal_workflow.py) and [detail UI tests](../../frontend/src/deals/DealDetailPage.test.tsx). Verify done before editing.

## Implementation Contract

Persist scoped cancellation/dispute case requests with type/reason, agreement version/hash/obligation references, actor/time, authorized bilateral decisions, evidence visibility, resolution and audit transitions. Preserve current pre-commit cancellation. Request/case creation is NOT effective cancellation, liability, refund, payment reversal or legal resolution. Define existing decision authority; new adjudication/refund policy requires explicit approval. Do not auto-suspend unrelated obligations or settle paid/in-flight consequences; unresolved policy blocks affected transitions and remains visible.

Add state machine/API/UI case history with pending/error/stale/permission and private evidence states. Serialize conflicts with payment/amendment/fulfillment using optimistic/current-state checks and atomic case/audit/outbox; no network inside locks. Add actual-head additive migration/preservation/history-loss downgrade guard if needed. Keep original paid/history/export provenance immutable; safe error/log/source projections.

## Focused Checks and Gates

Test forged tenants/revocation, competing cases/payment/amendment/fulfillment, duplicate decisions, stale version, rollback, precommit regression, unresolved consequences and case-versus-effective-decision. Run deal/workflow/payment/detail UI tests below. Full shared-risk gates when needed: safe full backend test_*.py discovery, ruff src tests, npm test/lint:check/build, git diff --check, immediate `$LASTEXITCODE`. No embedded execution now.

Runtime-review [config](../../backend/src/syncally/config.py)/[scripts](../../frontend/package.json) and runner against security/provider tests. BaseSettings Settings/PayPalSettings/GmailSettings fields/defaults/aliases/model_config handled dynamically; global Settings import defaults APP_ENV production. Ignore dotenv only during discovery; normal constructor restored before bodies, inherited fields/aliases cleared case-insensitively, TEST_POSTGRES_URL/SYNCALLY_TEMPORAL_* preserved, original child env restored finally. No logging/skip/Temporal startup/module/security/provider masking. New required/complex aliases fail pending reviewed changes; Python 3.12+ configured venv, no implicit installs/services.

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
    patterns = ('test_deal_use_cases.py', 'test_deal_workflow.py', 'test_payment_processing.py')
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

Authorized auditable case workflow distinguishes requests/decisions and preserves finance/legal/history boundaries; concurrent and privacy behavior independently verified. Append progress UTC/08/dependencies/roles/file:line/version evidence/commands/cwd/exits/counts/skips/artifacts/findings severity-proof-impact-fix/repairs 0-3. NOT_RUN to ACCEPTED only by current checks/review; otherwise BLOCKED. Report scope/files/checks/policy blockers/risks, continue independent ready tasks.