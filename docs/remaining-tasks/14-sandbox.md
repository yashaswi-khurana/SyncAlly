# 14 Sandbox - F11b Explicit Opt-In

Execute this step now in SyncAlly workspace. Locate/verify git root via backend manifest/config and frontend manifest; use accessible `C:\Proj\SyncAlly` or located root. No original prompt/external handoff/sibling upload. Check election and prerequisites first; never conjure credentials or provider approval.

## Context and Rules

Historical **2026-10-31 F12** only: **713 run / 686 pass / 27 skip**, frontend **364 passes**, static/build pass, **3 payment warnings and bundle warning**. Reinspect uncommitted **0012-0017**; not current validation. Historical code/independent review ACCEPTED **B1-4 Q1 F1a F2 F3 F4 F5 F6 F11a F12**, not production approval. Reuse Sandbox adapter/intents/outbox/reconciliation, doc statuses may be stale.

Exactly three specialized role agents: **PLANNER read-only; DEVELOPER one planned task; REVIEWER independent; repair max 3; do not manually substitute if roles cannot be spawned.** Missing coordination BLOCKED/ask before manual substitution, no self/pretend approval. PLANNER read-only owner/tests/dependency/election/already-done/hypothesis/check; DEVELOPER one elected task/immediate focused validation; REVIEWER severity/file:line/proof/impact/fix, max three repair/rerun/review cycles.

Conservative choices approved, not policy expansion/client roles/backfill/refunds/legal claims/private egress/production provider actions. Preserve rights/no blanket finance/fulfillment. Fresh server tenant/capability/private evidence authorization; immutable hash/version, human same-version bilateral approval/no AI authority. Redirects not proof, never real-to-offline history. Atomic durable outbox/no network inside DB locks; bounded finite Decimal BEFORE formatting/calculation. Preserve dirty tracked/untracked/user changes, reread before apply_patch; no cleanup/branch/commit/push/reset. Actual-head migrations never fixed 0018; upgrade preservation/history-loss downgrade block, demo claims/paid-history/drain/0014/0017 intact. Normal fakes first; real Sandbox isolated explicit opt-in only. Secrets private operator terminal, never questions/model/docs/logs. Missing election/creds/policy/tooling BLOCKED; NOT_ELECTED only explicit operator decline, neither implies completed integration. Continue independent steps, mandatory unmet gates NOT_COMPLETE.

## Scope and Dependencies

Dependencies **06, 13**, plus explicit Sandbox opt-in, Sandbox-only seller/buyer accounts, privately provisioned client secret/webhook ID and approved webhook deployment. Verify no production account/destination/mode; do not print private values. Read [PayPal](../../backend/src/syncally/infrastructure/paypal.py), [webhooks](../../backend/src/syncally/api/paypal_webhooks.py), [payment worker](../../backend/src/syncally/cli/payment_worker.py), [config](../../backend/src/syncally/config.py), [webhook tests](../../backend/tests/test_paypal_webhooks.py), [reconciliation tests](../../backend/tests/test_payment_reconciliation.py) and [processing tests](../../backend/tests/test_payment_processing.py). Verify done from genuine provenance/evidence, not historical label.

## Verification Contract

Operator enters secrets privately in their terminal; model-visible questions must never request credentials. Verify explicitly authorized finance actor and committed eligible milestone. Execute actual unique persisted intent/outbox invoice create, send, buyer payment, signature-verified webhook and fresh authenticated provider reconciliation. All must agree on invoice ID, amount/currency, recipient/payee and status/provenance. Redirects, mocks, fixtures/offline simulated state do not qualify. Preserve immutable committed/payment history and mode. Unknown create/send outcomes reconcile existing persisted provider provenance before retry; never issue duplicate invoices. No refunds, real-money production actions or unapproved email/private payload egress.

Network outside DB locks; safe logs/errors/redacted evidence only, no payer/contact/token bodies in docs. Existing persistence preferred; if PLANNER proves a gap, one bounded repair with actual-head additive migration/preservation guards and independent review max 3. Do not weaken webhook signature/authenticated reconciliation or finance capability to make test pass.

## Focused Checks and Gates

Run fake tests for wrong signature/invoice/amount/currency/payee, duplicates/reordered events, stale/revoked finance authority, unknown-create retry and no duplicate invoice first; then only elected Sandbox real lifecycle. Evidence must separate fake from actual provider behavior. Full gates as repair risk requires: safe full backend discovery, ruff src tests, npm test/lint:check/build, git diff --check with immediate `$LASTEXITCODE`. No embedded execution during authoring.

Runtime-review config/metadata and [frontend scripts](../../frontend/package.json), verify runner against current security/provider tests. Settings/PayPalSettings/GmailSettings BaseSettings fields/defaults/aliases/model_config derive dynamically; global Settings import defaults APP_ENV production. Ignore dotenv only bootstrap/discovery, restore normal constructor before bodies, clear config case-insensitively, preserve TEST_POSTGRES_URL/SYNCALLY_TEMPORAL_*, restore child env finally. This fake test runner intentionally clears provider credentials from test environment; never use it as the Sandbox worker configuration. Privately configured live environment is separate. No logging/skip/Temporal startup/module/security/provider masking; required/complex aliases fail pending review. Python 3.12+ configured venv, no silent installs/services.

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
    patterns = ('test_paypal_webhooks.py', 'test_payment_reconciliation.py', 'test_payment_processing.py')
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
if ($LASTEXITCODE -ne 0) { throw 'Fake provider tests/discovery failed' }
```

## Acceptance and Completion Report

Actual elected Sandbox invoice/send/buyer payment/verified webhook/fresh reconciliation has matching durable provenance and independent review. Otherwise BLOCKED or explicitly NOT_ELECTED, never fake completed/production approved. Append progress UTC/14/dependencies/election/roles/redacted invoice/version/digests and file:line proof/commands/cwd/exits/counts/skips/artifacts/findings severity-impact-fix/repairs 0-3. Initial NOT_RUN; report real versus fake evidence, policy/credential blockers and continue independent tasks without requesting secrets.