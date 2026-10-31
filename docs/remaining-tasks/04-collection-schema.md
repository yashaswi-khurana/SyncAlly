# 04 Collection Schema - F10a

Execute this step now in SyncAlly workspace. Locate/verify git root by backend manifest/config and frontend manifest; prefer accessible `C:\Proj\SyncAlly`, otherwise located root. No original prompt/external handoff/sibling upload required. Execute after current dependency verification, not plan only.

## Context and Rules

Historical **2026-10-31 F12** only: **713 run / 686 pass / 27 skip**, frontend **364 passes**, static/build pass, **3 payment warnings and bundle warning**. Reinspect uncommitted **0012-0017**, not current validation. Historical code/independent review ACCEPTED **B1-4 Q1 F1a F2 F3 F4 F5 F6 F11a F12**, no production approval. Reuse implemented commitment/history/payment/export foundations; existing docs stale until verified.

Exactly three specialized role agents: **PLANNER read-only; DEVELOPER one planned task; REVIEWER independent; repair max 3; do not manually substitute if roles cannot be spawned.** Missing agents BLOCKED, ask before manual substitution, no self-approval. PLANNER owning code/tests/dependencies/already-done/hypothesis/cheap check; DEVELOPER one task/immediate post-edit validation; REVIEWER severity/file:line/proof/impact/fix. Same-task repairs max three with rerun/review.

Conservative choices approved, not policy expansion/client roles/backfill/refunds/legal claims/private egress. Preserve existing rights, no blanket finance/fulfillment. Fresh tenant/capability/private evidence checks, immutable committed hash/version, human same-version bilateral approval/no AI authority. No redirect proof or real-to-offline conversion. Transactional outbox/no network inside DB locks; bounded finite Decimal BEFORE formatting/calculation. Preserve dirty tracked/untracked/user changes, reread before apply_patch, no cleanup/branches/commit/push/reset. Actual-head migration never fixed 0018; preserve upgrades/block history-loss downgrade; demo claims/paid-history/drain/0014/0017 intact. Fakes normally, isolated opt-in external gates; secrets operator private terminal only, no questions/model/docs/logs. Missing policy/tools BLOCKED, continue independent tasks, mandatory unmet gates NOT_COMPLETE.

## Scope and Dependencies

Dependency **03**: version-owned fulfillment facts/partial quantities and derived completion currently verified. Read [trade terms](../../backend/src/syncally/domain/agreements/trade_terms.py), [agreement](../../backend/src/syncally/domain/agreements/agreement.py), [money](../../backend/src/syncally/domain/shared/money.py), [agreement models](../../backend/src/syncally/infrastructure/models/agreements.py), [agreement tests](../../backend/tests/test_agreements.py), [negotiation tests](../../backend/tests/test_negotiation.py), [commercial document tests](../../backend/tests/test_commercial_documents.py) and [Alembic environment](../../backend/alembic/env.py). Verify existing support before editing.

## Implementation Contract

Version item/shipment/payment collections with stable explicit IDs, schema discriminator and deterministic canonical ordering/serialization. Define quantities/units, bounded prices/currencies/precision, shipment-item allocations, payment-obligation allocations and explicit trigger descriptions. Retain duplicate commercial lines as different IDs; reject duplicate IDs, foreign-version references, unsupported schema, overallocations, unit mismatch and mixed-currency totals. No implicit allocations/unit/currency conversion. State approved rounding/residual policy; ambiguous money policy blocks affected cases. Validate finite digit/exponent/range bounds before format/quantization/multiplication/totals.

Legacy singleton projections must preserve committed canonical bytes/hash and historical F12 exports exactly; do not silently rewrite or enrich old commitments. Add actual-head additive migration, fresh/representative upgrade checks, preservation/backfill tests and history-loss downgrade refusal. Persist schemas/projections only where needed and update compatibility contracts. API/UI follow at 05; do not prematurely build a second authoring surface.

## Focused Checks and Gates

Test deterministic hash roundtrip/order/identity, duplicate lines versus IDs, partial allocation/overallocations, giant decimals/NaN/infinity, exact totals/rounding, old schemas/exports and rollback. Run agreement/negotiation/document tests below; shared serialization requires expanded regressions/full gates when justified. Full gates are safe full discovery (`patterns = ('test_*.py',)`), backend ruff, frontend npm test/lint:check/build and git diff --check with immediate `$LASTEXITCODE`. No embedded execution now.

Runtime-reinspect [config](../../backend/src/syncally/config.py)/[npm scripts](../../frontend/package.json) and verify runner against security/provider assertions. Global Settings at import/production APP_ENV default require temporary bootstrap; derive all Settings/PayPalSettings/GmailSettings BaseSettings model_fields/defaults/aliases/model_config, ignore dotenv only for discovery and restore normal settings before bodies. Clear fields/aliases case-insensitively, preserve TEST_POSTGRES_URL/SYNCALLY_TEMPORAL_*, restore child env finally. No logging/skip/Temporal startup/module/provider/security masking. New required/complex aliases fail pending review; configured Python 3.12+ venv, no implicit dependency installs/services.

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
    patterns = ('test_agreements.py', 'test_negotiation.py', 'test_commercial_documents.py')
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
& $Python -m ruff check src tests
if ($LASTEXITCODE -ne 0) { throw 'Backend static gate failed' }
```

## Acceptance and Completion Report

All three versioned collections/allocation identities supported, numeric/schema validation and old immutable canonical/hash/export compatibility proven. Independent review required. Append progress UTC/04/dependency/roles/file:line/version evidence/commands/cwd/exits/counts/skips/artifacts/findings severity-proof-impact-fix/repairs 0-3. NOT_RUN to ACCEPTED only by current checks/review; otherwise BLOCKED, preserve historical evidence. Report implemented files/behavior/checks/risks and continue independent ready tasks.