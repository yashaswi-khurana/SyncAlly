# 02 Permissions - F15a

Execute this step now in SyncAlly workspace. Locate/verify the git root with `backend/pyproject.toml`, `backend/src/syncally/config.py`, `frontend/package.json`; `C:\Proj\SyncAlly` is a preference only when accessible, otherwise use located root. No original prompt/external handoff/sibling upload required. Execute the ready task, not just a plan.

## Context and Rules

Historical **2026-10-31 F12** only: **713 run / 686 pass / 27 skip**, frontend **364 passes**, full static/build pass, **3 payment warnings and bundle warning**. Uncommitted **0012-0017** require reinspection; not current passed claims. Historical code/independent review ACCEPTED **B1-4 Q1 F1a F2 F3 F4 F5 F6 F11a F12**, no production approval. Reuse accepted foundations; existing doc statuses may be stale.

Exactly three specialized role agents: **PLANNER read-only; DEVELOPER one planned task; REVIEWER independent; repair max 3; do not manually substitute if roles cannot be spawned.** Unavailable coordination: BLOCKED, ask before manual substitution; no self-approval/pretend review. PLANNER reads owning code/tests and dependencies, checks already-done behavior and states hypothesis/cheap check; DEVELOPER edits one task then immediately validates; independent REVIEWER reports severity/file:line/proof/impact/fix. Max three same-task repairs with reruns/review.

Routine conservative decisions approved, policy expansion/client roles/backfills/refunds/legal claims/private egress not approved. Preserve existing rights and no blanket finance/fulfillment grants. Fresh server tenant/capability checks protect private reads/evidence/exports and writes. Immutable committed hash/version; human same-version bilateral approvals, no AI authority. Redirects not payment proof, real history never offline. Atomic durable outbox, no network inside DB locks; bound finite Decimal BEFORE formatting/calculation. Preserve dirty tracked/untracked/user changes, reread before apply_patch edits, no cleanup/branch/commit/push/reset. Actual-head migrations, never fixed 0018, preserve upgrades/block history-loss downgrade. Keep demo claims/paid-history/drain/0014/0017 safeguards. Fakes normally; external environments isolated opt-in. Secrets only operator private terminal, not questions/model/docs/logs. Block affected tasks for policy/tools, continue independent steps; mandatory unmet gates mean NOT_COMPLETE.

## Scope and Dependencies

Dependency **01**: verify profiles' four dimensions, UNVERIFIED authority/private contact semantics and independent current evidence. Read [organization domain](../../backend/src/syncally/domain/organizations/organization.py), [identity application](../../backend/src/syncally/application/identity.py), [organization repository](../../backend/src/syncally/infrastructure/repositories/organizations.py), [deal application](../../backend/src/syncally/application/deals.py), [agreement application](../../backend/src/syncally/application/agreements.py), [payments](../../backend/src/syncally/application/payments.py), [authorization tests](../../backend/tests/test_deal_authorization.py), [identity tests](../../backend/tests/test_identity_boundary.py), [session](../../frontend/src/auth/useSession.ts) and [settings UI](../../frontend/src/organizations/OrganizationsSettingsPage.tsx). Verify current implementation before editing.

## Implementation Contract

Define explicit server capability matrix: administration/profile editing, drafting/negotiation, agreement approval, finance and fulfillment. Preserve existing legitimate approval continuity and rights until explicit replacement policy. Profile capabilities are descriptions, never authorization. Do not grant new finance/fulfillment to all ADMIN/MEMBER, silently migrate privileges, create client-only roles or invent a grant authority. Require explicit scoped assignment by an existing authorized authority under approved policy; if absent block new grants and report policy need while preserving existing legitimate behavior. Protect self-escalation and last-administrator using established rules; new policy requires approval.

Add scoped versioned assignments/audit with additive actual-head migration only as needed; safe defaults must not authorize new actions. Enforce membership/capability freshness at API/application commit and worker dispatch, not only JWT/UI snapshot. Cover private exports/read projections and tenant membership changes. UI shows actionable permission/pending/revocation/error states and prevents stale requests without being authority.

## Focused Checks and Gates

Test matrix allow/deny, forged cross-tenant assignment/IDs, self-escalation, stale roles/tokens, revocation between read/commit, rollback, default no-new-grants, old approval continuity and UI parity. Run identity boundary/deal authorization and client/settings tests; broaden shared authorization regressions when needed. Full gates when required: safe backend discovery below with all `test_*.py`, backend ruff, frontend npm test/lint:check/build and git diff --check; immediate `$LASTEXITCODE` checks. No embedded execution during authoring.

Before runtime, reinspect [config](../../backend/src/syncally/config.py) and [npm scripts](../../frontend/package.json), then review the runner against current security/provider tests. BaseSettings Settings/PayPalSettings/GmailSettings metadata controls field/default/alias isolation; global Settings import and production APP_ENV default require temporary local bootstrap. Normal dotenv/settings construction is restored BEFORE test bodies; all inherited settings fields/aliases cleared case-insensitively, TEST_POSTGRES_URL/SYNCALLY_TEMPORAL_* preserved, environment restored finally. No logging/skip/Temporal startup/test-module/security patches. New required fields/complex aliases require reviewed runner changes. Use Python 3.12+ configured venv; missing dependencies BLOCKED, not silently installed.

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
    patterns = ('test_identity_boundary.py', 'test_deal_authorization.py')
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
npm test -- src/api/client.test.ts src/organizations/OrganizationsSettingsPage.test.tsx
if ($LASTEXITCODE -ne 0) { throw 'Focused UI tests failed' }
npm run lint:check
if ($LASTEXITCODE -ne 0) { throw 'Frontend static gate failed' }
```

## Acceptance and Completion Report

Matrix enforced on server/UI with explicit authority, no backfill or blanket new finance/fulfillment grants, fresh revocation/tenant checks and approval continuity demonstrated. Independent review required. Append progress UTC/step 02/dependencies/role identities/file:line and version evidence/commands/cwd/exits/counts/skips/findings severity-proof-impact-fix/repair count 0-3. Start NOT_RUN; ACCEPTED only from current checks/review, otherwise BLOCKED. Report files/behavior/checks/risks/operator policy needs, preserve historical evidence and continue independent ready tasks.