# 09 Approval Routing - F15b

Execute this step now in SyncAlly workspace. Locate/verify git root using backend manifest/config and frontend manifest; use accessible `C:\Proj\SyncAlly` or located root. No original prompt/external handoff/sibling upload required. Execute after current dependency verification.

## Context and Rules

Historical **2026-10-31 F12** only: **713 run / 686 pass / 27 skip**, frontend **364 passes**, full static/build pass, **3 payment warnings and bundle warning**. Reinspect uncommitted **0012-0017**, not current passes. Historical code/independent review ACCEPTED **B1-4 Q1 F1a F2 F3 F4 F5 F6 F11a F12**, no production approval. Reuse approval/identity/version/outbox foundations; docs may be stale.

Exactly three specialized role agents: **PLANNER read-only; DEVELOPER one planned task; REVIEWER independent; repair max 3; do not manually substitute if roles cannot be spawned.** Missing coordination BLOCKED, ask before manual substitution, no self-approval/pretend review. PLANNER owner/tests/dependency/already-done/hypothesis/check; DEVELOPER one task/immediate validation; REVIEWER severity/file:line/proof/impact/fix, max three same-task repairs/reruns/reviews.

Conservative choices approved, not policy expansion/client roles/backfill/refunds/legal claims/private egress. Preserve rights/no blanket finance/fulfillment grants. Fresh server tenant/capability/private evidence checks, immutable hash/version and human same-version bilateral approvals/no AI authority. No redirect proof/real-to-offline history. Atomic durable outbox/no network inside DB locks; finite bounded Decimal BEFORE formatting/computing. Preserve dirty tracked/untracked/user changes, reread before apply_patch, no cleanup/branch/commit/push/reset. Actual-head migration never fixed 0018; upgrade preservation/history-loss downgrade block; demo claims/paid-history/drain/0014/0017 intact. Fakes normally, isolated opt-in external checks. Secrets private operator terminal only, not questions/model/docs/logs. Missing policy/tools BLOCKED, continue independent steps, mandatory unmet gates NOT_COMPLETE.

## Scope and Dependencies

Dependencies **02, 07, 08**: capabilities/default continuity, amendment and case decisions currently verified. Read [organization repository](../../backend/src/syncally/infrastructure/repositories/organizations.py), [agreement application](../../backend/src/syncally/application/agreements.py), [negotiation](../../backend/src/syncally/application/negotiation.py), [agreement routes/tests](../../backend/tests/test_agreement_routes.py), [identity tests](../../backend/tests/test_identity_boundary.py), [review UI tests](../../frontend/src/deals/AgreementReview.test.tsx) and [settings UI](../../frontend/src/organizations/OrganizationsSettingsPage.tsx). Check whether done before editing.

## Implementation Contract

Persist explicitly configured organization routing requirements using existing capabilities: eligible approvers, required sequence/parallel conditions only under approved policy, version/hash/membership revision, reassignment and decision audit. Default retains existing bilateral approval behavior until configuration is explicitly authorized. Routing does not create authority; internal/unilateral approvals cannot count as the other organization's consent. Final bilateral approval must match identical current version/hash.

Clarify quorum/delegation/escalation before expanding policy. Recheck revoked/reassigned actors and stale decisions/config revision; none satisfy current route. Add typed API/UI required/pending/completed/stale/revoked/error states and limited participant projections without private contacts/membership leakage. Needed scoped persistence uses actual-head additive migration, atomic decision/audit/outbox and history-preserving rollback/downgrade safeguards; no network inside locks.

## Focused Checks and Gates

Test default continuity, approved multiple-review configurations, forged routes/tenant IDs, capability revocation/reassignment, duplicate/stale decisions, version/config change and races with amendments/cases. Run agreement/identity/negotiation and review/settings UI tests below; shared auth gates when needed. Full gates: safe all backend test_*.py discovery, ruff src tests, npm test/lint:check/build, git diff --check, immediate `$LASTEXITCODE`; no embedded execution now.

Runtime-review [config](../../backend/src/syncally/config.py)/[scripts](../../frontend/package.json) and runner against current security/provider tests. Settings/PayPalSettings/GmailSettings BaseSettings fields/defaults/aliases/model_config dynamically handled; global Settings import defaults APP_ENV production. Ignore dotenv only bootstrap/discovery; restore normal constructor before bodies, clear settings case-insensitively, preserve TEST_POSTGRES_URL/SYNCALLY_TEMPORAL_*, finally restore child env. No logging/skip/Temporal startup/module/security/provider patches. Required/complex aliases fail pending reviewed update; configured Python 3.12+ venv, no silent installs/services.

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
    patterns = ('test_agreement_routes.py', 'test_identity_boundary.py', 'test_negotiation.py')
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
npm test -- src/deals/AgreementReview.test.tsx src/organizations/OrganizationsSettingsPage.test.tsx
if ($LASTEXITCODE -ne 0) { throw 'Focused UI tests failed' }
npm run lint:check
if ($LASTEXITCODE -ne 0) { throw 'Frontend static gate failed' }
```

## Acceptance and Completion Report

Explicit routing enforced without privilege creation, default approval continuity and fresh bilateral exact-version matching proven independently. Append progress UTC/09/dependencies/roles/file:line/version evidence/commands/cwd/exits/counts/skips/artifacts/findings severity-proof-impact-fix/repairs 0-3. NOT_RUN to ACCEPTED only by current checks/review; otherwise BLOCKED. Report files/behavior/checks/risks/policy needs; continue independent ready tasks.