# 07 Amendments - F7

Execute this step now in SyncAlly workspace. Locate/verify git root by backend manifest/config and frontend manifest; use `C:\Proj\SyncAlly` if accessible, otherwise located root. No original prompt/external handoff/sibling upload. Execute after dependency checks, not plan-only.

## Context and Rules

Historical **2026-10-31 F12** only: **713 run / 686 pass / 27 skip**, frontend **364 passes**, static/build pass, **3 payment warnings and bundle warning**. Reinspect uncommitted **0012-0017**, not current passes. Historical code/independent review ACCEPTED **B1-4 Q1 F1a F2 F3 F4 F5 F6 F11a F12**, no production approval. Reuse proposal/version/history/payment foundations; doc statuses may be stale.

Exactly three specialized role agents: **PLANNER read-only; DEVELOPER one planned task; REVIEWER independent; repair max 3; do not manually substitute if roles cannot be spawned.** Missing coordination BLOCKED, ask before manual substitution; no self-approval/pretend review. PLANNER owner/tests/dependencies/already-done/hypothesis/check; DEVELOPER one task/immediate validation; REVIEWER severity/file:line/proof/impact/fix; max three repairs/reruns/reviews.

Conservative choices approved, not policy expansion/client roles/backfills/refunds/legal claims/private egress. Preserve rights/no blanket finance/fulfillment. Fresh server tenant/capability/private evidence checks; immutable committed hash/version and human same-version bilateral approval/no AI authority. Redirects not proof; real history never offline. Atomic outbox/no network inside DB locks; finite bounded Decimal BEFORE formatting/computation. Preserve dirty tracked/untracked/user changes, reread before apply_patch; no cleanup/branch/commit/push/reset. Actual-head migration never fixed 0018; upgrade preservation/history-loss downgrade block. Keep demo claims/paid-history/drain/0014/0017. Fakes normally; isolated opt-in external gates. Secrets private operator terminal only, not questions/model/docs/logs. Missing policy/tools BLOCKED, continue independent tasks, unmet mandatory gates NOT_COMPLETE.

## Scope and Dependencies

Dependencies **05, 06**: reviewed collection authoring/exports and milestone authority/provenance verified currently. Read [agreement](../../backend/src/syncally/domain/agreements/agreement.py), [proposal](../../backend/src/syncally/domain/negotiation/proposal.py), [negotiation](../../backend/src/syncally/application/negotiation.py), [agreement application](../../backend/src/syncally/application/agreements.py), [repository](../../backend/src/syncally/infrastructure/repositories/agreements.py), [agreement tests](../../backend/tests/test_agreements.py), [negotiation tests](../../backend/tests/test_negotiation.py) and [review UI tests](../../frontend/src/deals/NegotiationReview.test.tsx). Verify existing support before editing.

## Implementation Contract

Human propose/review/withdraw/reject/commit amendments against explicit previous committed version/hash, with immutable lineage/diff and fresh bilateral approvals of identical new version/hash. Replaced drafts invalidate stale approvals. Assess impacts on fulfillment allocations, unpaid/paid/in-flight milestones and active cases. Preserve all original commitments, paid/in-flight evidence and history/export bytes. Block ambiguous settlement/replacement/refund policy rather than silently adjusting obligations or claiming legal effects. AI suggests only, never approval/finance/legal resolution.

Persist proposal/version/decisions/audit/outbox atomically with actual-head additive migration if needed; current-version optimistic/locking checks without network inside locks. API/UI expose lineage, exact-version impact preview, private history and pending/conflict/revoked/error states. Ensure accepted amendment does not orphan existing payment or evidence records. Update affected contracts/docs truthfully.

## Focused Checks and Gates

Test concurrent proposals/approvals/payments, wrong prior hash, stale version/approval, revoked/foreign actors, rollback, paid/in-flight preservation, unresolved impact blocker, private lineage and historical export bytes. Run negotiation/agreement/payment and review UI tests below; shared serialization/full gates when needed: safe all backend discovery, ruff src tests, npm test/lint:check/build, git diff --check, immediate `$LASTEXITCODE`. No embedded execution during authoring.

Before runtime review [config](../../backend/src/syncally/config.py)/[scripts](../../frontend/package.json) and runner against current security/provider tests. Settings/PayPalSettings/GmailSettings BaseSettings fields/defaults/aliases/model_config dynamically isolated, global Settings import defaults APP_ENV production. Ignore dotenv only during bootstrap/discovery; restore normal construction before bodies, clear names case-insensitively, preserve TEST_POSTGRES_URL/SYNCALLY_TEMPORAL_*, restore child env finally. No logging/skip/Temporal startup/module/security/provider patches. Required/complex aliases fail pending review; configured Python 3.12+ venv, no silent installs/services.

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
    patterns = ('test_negotiation.py', 'test_agreements.py', 'test_payment_processing.py')
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
npm test -- src/deals/NegotiationReview.test.tsx src/deals/AgreementReview.test.tsx
if ($LASTEXITCODE -ne 0) { throw 'Focused UI tests failed' }
npm run lint:check
if ($LASTEXITCODE -ne 0) { throw 'Frontend static gate failed' }
```

## Acceptance and Completion Report

Fresh exact-version bilateral amendments with immutable lineage/payment history and explicit approved financial effects or visible policy blockers, independently verified. Append UTC/07/dependencies/roles/file:line/version evidence/commands/cwd/exits/counts/skips/artifacts/findings severity-proof-impact-fix/repairs 0-3 in progress. NOT_RUN to ACCEPTED only with current checks/review, otherwise BLOCKED. Report implementation/files/checks/risks/policy needs; continue independent ready tasks.