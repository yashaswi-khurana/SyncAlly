# 06 Milestone Payments - F10c

Execute this step now in SyncAlly workspace. Locate/verify git root by backend manifest/config and frontend manifest; use accessible `C:\Proj\SyncAlly` or located root. No original prompt/external handoff/sibling upload. Execute after dependencies verified, not plan-only.

## Context and Rules

Historical **2026-10-31 F12** only: **713 run / 686 pass / 27 skip**, frontend **364 passes**, full static/build pass, **3 payment warnings and bundle warning**. Uncommitted **0012-0017** must be reinspected, not current passes. Historical code/independent review ACCEPTED **B1-4 Q1 F1a F2 F3 F4 F5 F6 F11a F12**, no production approval. Extend existing intents/outbox/modes/reconciliation, do not rebuild foundations; docs may be stale.

Exactly three specialized role agents: **PLANNER read-only; DEVELOPER one planned task; REVIEWER independent; repair max 3; do not manually substitute if roles cannot be spawned.** If unavailable BLOCKED/ask before manual substitution, no pretend/self-review. PLANNER current owner/tests/dependencies/already-done/hypothesis/check; DEVELOPER one planned task/immediate focused validation; REVIEWER severity/file:line/proof/impact/fix; max three same-task repairs/reruns/reviews.

Conservative choices approved, not policy expansion/client roles/backfill/refunds/legal claims/private egress. Preserve rights/no blanket finance/fulfillment grants. Fresh server tenant/capability/private evidence checks, immutable hash/version and human same-version bilateral approval/no AI authority. Redirects not proof; no real-to-offline conversion. Atomic durable outbox/no network inside DB locks. Bound finite Decimal BEFORE formatting/quantizing/totals. Preserve dirty tracked/untracked/user changes, reread before apply_patch; no cleanup/branches/commit/push/reset. Actual-head migration, never fixed 0018, upgrade preservation/history-loss downgrade block. Keep demo claims/paid-history/drain/0014/0017. Normal fakes; isolated explicit opt-in external gates. Secrets only private operator terminal, never questions/model/docs/logs. Policy/tools absent BLOCKED; continue independent tasks, mandatory unmet gates NOT_COMPLETE.

## Scope and Dependencies

Dependencies **02, 03, 05**: explicit capability policy, fulfillment facts and reviewed collection allocations/versioned exports currently verified. Read [intent](../../backend/src/syncally/domain/payments/intent.py), [processing](../../backend/src/syncally/application/payment_processing.py), [outbox](../../backend/src/syncally/infrastructure/payment_outbox.py), [repository](../../backend/src/syncally/infrastructure/repositories/payments.py), [processing tests](../../backend/tests/test_payment_processing.py), [outbox tests](../../backend/tests/test_payment_outbox.py), [reconciliation tests](../../backend/tests/test_payment_reconciliation.py), [intent tests](../../backend/tests/test_payment_intent_repository.py), [UI tests](../../frontend/src/deals/PaymentStatusPanel.test.tsx). Verify current implemented behavior first.

## Implementation Contract

Extend existing intents to explicit committed-version payment collection/milestone IDs, currency/amount/allocations and approved trigger conditions. Validate milestone sums, precision, bounded finite Decimal, currency balance and residual policy BEFORE formatting/quantization/calculation. No implicit conversion. Eligibility from delivery/time/approval is NOT issuance/payment authority: require fresh finance capability and explicitly approved trigger policy; block ambiguity rather than automatic privilege grants/payment.

Enforce one active intent per milestone/version with DB uniqueness, transaction/outbox idempotency and replay/concurrent trigger protection. Network calls outside DB locks; unknown create-started/send outcomes reconcile durable provider provenance before retries, never duplicate invoices. Keep paid/in-flight history/mode immutable, simulation explicit, redirects nonauthoritative. Completion derives from fulfilled obligations and reconciled required payments. Add actual-head additive migration/preservation/downgrade guards as needed. Typed API/UI distinguish ineligible/eligible/authorized/queued/unknown/sent/reconciled states and safe errors/source privacy.

## Focused Checks and Gates

Test exact sums, giant/nonfinite Decimal, currency mismatch, partial settlement, unauthorized/revoked eligibility, racing/duplicate triggers, worker crash/retry/create-started unknown outcomes, one active intent, completion requirements and real/offline provenance. Run processing/outbox/reconciliation/intent and UI tests below. Real DB races are mandatory later isolated gate, not satisfied by mocks. Full gates as required: safe all-test discovery, ruff src tests, npm test/lint:check/build, git diff --check with immediate `$LASTEXITCODE`; no embedded execution during authoring.

Runtime-review [config](../../backend/src/syncally/config.py)/[scripts](../../frontend/package.json) and runner against security/provider tests before use. Settings global import/production APP_ENV default require bootstrap. Dynamically derive Settings/PayPalSettings/GmailSettings BaseSettings fields/defaults/aliases/model_config; ignore dotenv only discovery, restore normal constructor before bodies, clear settings case-insensitively, preserve TEST_POSTGRES_URL/SYNCALLY_TEMPORAL_*, restore child env finally. No logging/skip/Temporal startup/module/security/provider changes. New required/complex aliases fail closed pending review; configured Python 3.12+ venv, no silent installs/services.

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
    patterns = ('test_payment_processing.py', 'test_payment_outbox.py', 'test_payment_reconciliation.py', 'test_payment_intent_repository.py')
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
npm test -- src/deals/PaymentStatusPanel.test.tsx
if ($LASTEXITCODE -ne 0) { throw 'Focused UI tests failed' }
npm run lint:check
if ($LASTEXITCODE -ne 0) { throw 'Frontend static gate failed' }
```

## Acceptance and Completion Report

Version-owned milestones, exact bounded totals/eligibility/authority, no duplicate invoices or fabricated paid state, immutable real/offline provenance verified independently. Append progress UTC/06/dependencies/roles/file:line/version evidence/commands/cwd/exits/counts/skips/artifacts/findings severity-proof-impact-fix/repairs 0-3. NOT_RUN to ACCEPTED only with current checks/review; otherwise BLOCKED. Report implemented files/behavior/checks and remaining real-race gate, continue independent tasks.