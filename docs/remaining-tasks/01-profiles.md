# 01 Profiles - F14

Execute this step now in SyncAlly workspace. This document is self-contained; do not require an original prompt, external handoff or sibling upload. Locate the repository using `backend/pyproject.toml`, `backend/src/syncally/config.py` and `frontend/package.json`; verify its git root. Use `C:\Proj\SyncAlly` only if present, otherwise the located root. Execute, verify and report, not just plan.

## Context and Rules

Historical **2026-10-31 F12** baseline only: backend **713 run / 686 pass / 27 skip**, frontend **364 passes**, full static/build passed; **3 payment warnings and bundle warning**. Uncommitted **0012-0017** must be reinspected; none is current validation. Historical code/independent review ACCEPTED **B1-4 Q1 F1a F2 F3 F4 F5 F6 F11a F12**, not production approval. Reuse implemented foundations; existing docs/statuses can be stale.

Exactly three specialized role agents: **PLANNER read-only; DEVELOPER one planned task; REVIEWER independent; repair max 3; do not manually substitute if roles cannot be spawned.** If coordination is unavailable record BLOCKED and ask before manual substitution; never self-approve or pretend review. PLANNER verifies current code/dependencies, identifies owning files, a falsifiable hypothesis and cheapest check. DEVELOPER makes one scoped change and immediately validates; REVIEWER reports severity/file:line/proof/impact/fix. Repair the same slice at most three times with rerun and independent review.

Routine conservative choices are approved, not policy expansion/client roles/automatic privilege backfill/refunds/legal claims/private egress. Preserve existing rights; do not blanket-grant finance/fulfillment. Enforce fresh server-side tenant/capability authorization, private evidence/source privacy, immutable committed hash/version, human same-version bilateral approvals and no AI authority. Redirects are not payment proof; real history never becomes offline. Use transactional durable outbox; no network inside DB locks. Bound finite Decimal BEFORE formatting/computing/quantizing. Preserve all dirty tracked/untracked/user work; reread before apply_patch edits, no destructive cleanup/branches/commit/push. New migration follows actual head, never fixed 0018; preserve upgrades and block history-loss downgrade. Preserve demo claim/paid-history/drain and 0014/0017 safeguards. Fakes normally; isolated external checks only with opt-in. Operator enters secrets privately in terminal, never model/question tools/docs/logs. Missing policy/tooling means BLOCKED; continue independent steps, never call mandatory unmet gates complete.

## Scope and Dependencies

No dependency among 01-16. Verify accepted identity/onboarding first. Before editing, read [organization domain](../../backend/src/syncally/domain/organizations/organization.py), [repository](../../backend/src/syncally/infrastructure/repositories/organizations.py), [organization API](../../backend/src/syncally/api/organizations.py), [identity models](../../backend/src/syncally/infrastructure/models/identity.py), [settings UI](../../frontend/src/organizations/OrganizationsSettingsPage.tsx), [domain tests](../../backend/tests/test_organization_domain.py), [directory tests](../../backend/tests/test_organization_directory.py), [repository tests](../../backend/tests/test_organization_repositories.py) and [UI tests](../../frontend/src/organizations/OrganizationsSettingsPage.test.tsx). Verify already-done behavior against this entire contract; do not redo it.

## Implementation Contract

Extend bounded profile collections for **capabilities, products, regions and contacts**. Capabilities are self-described commercial activities, not permissions. Products describe offerings, not verified inventory. Regions declare operating coverage using current country data, not licenses/legal eligibility. Contacts require owner/editor, purpose/consent and visibility; default contact channels private and disclose only to explicitly authorized participants, never public directory enumeration. Allow incomplete profiles and distinguish absent/unrecorded information.

Persist provenance, revision/update metadata and **UNVERIFIED** status. Defined authority is the existing authorized organization profile editor for self-described information; neither self-edit nor AI establishes VERIFIED. Do not invent a verifier/attestation authority. Any verified transition needs separately approved authority/policy; leave it unavailable. Preserve existing edit rights and historical snapshots; profile changes must not rewrite committed trade terms, hashes or F12 bytes.

Implement typed API projections/update commands with field/collection/Unicode bounds, region normalization, duplicate policy, version conflict and fresh auth checks. UI supports all four dimensions with edit/save/cancel/empty/pending/error/stale/unauthorized states and private-field visibility parity. Persist only needed fields with additive migration after computed actual head; preserve legacy data and block lossy downgrade where needed.

## Focused Checks and Gates

Test null/missing/oversized/Unicode fields, duplicate values, private/public projection, cross-tenant IDs, stale writes, revoked actors, rollback and immutable export/hash regression. Run focused organization tests and settings UI test, then touched lint/typecheck. Current full gates when a shared contract demands them: backend `python -m ruff check src tests`; frontend `npm test`, `npm run lint:check`, `npm run build`; `git -C $Root diff --check`, checking `$LASTEXITCODE` immediately after each. Full backend requires the safe runner below with `patterns = ('test_*.py',)` only at an authorized full gate. Never execute embedded checks during handoff authoring.

Reinspect [current config](../../backend/src/syncally/config.py) and [frontend scripts](../../frontend/package.json) before runtime use. Settings/PayPalSettings/GmailSettings are BaseSettings; global Settings is instantiated at import, APP_ENV defaults production. Review runner against current field/default/alias/model_config and security/provider tests before relying on it. It ignores dotenv only during import/discovery, restores normal construction before test bodies, dynamically clears all settings names/aliases case-insensitively, preserves TEST_POSTGRES_URL/SYNCALLY_TEMPORAL_* and finally restores child environment. No logging disable, skip changes, Temporal startup/module changes or security/provider masking. Missing defaults/complex aliases fail closed; update runner through review, not by hiding assertions.

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
    patterns = ('test_organization*.py',)
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
npm test -- src/organizations/OrganizationsSettingsPage.test.tsx
if ($LASTEXITCODE -ne 0) { throw 'Focused UI tests failed' }
npm run lint:check
if ($LASTEXITCODE -ne 0) { throw 'Frontend static gate failed' }
```

## Acceptance and Completion Report

All four profile dimensions, UNVERIFIED authority and private contact rules work server-side/UI; fresh tenant authorization, stale conflicts and immutable commitments proven. Require independent review acceptance, not self-certification. In repository progress ledger (create under authorized folder if absent), append UTC timestamp, step 01/dependencies, role identities, current file:line/version evidence, commands/cwd/exits/counts/skips, findings severity/file:line/proof/impact/fix and repair count 0-3. Initial NOT_RUN becomes ACCEPTED only after checks/review; missing evidence BLOCKED. Preserve historical results separately. Report implemented scope/files/checks/risks/blockers; do not stop after a plan.