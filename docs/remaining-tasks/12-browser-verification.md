# 12 Browser Verification

Execute this step now in SyncAlly workspace. Locate/verify git root via backend manifest/config and frontend manifest; use accessible `C:\Proj\SyncAlly` or located root. No original prompt/external handoff/sibling upload. Execute the verification, not merely a plan.

## Context and Rules

Historical **2026-10-31 F12** only: **713 run / 686 pass / 27 skip**, frontend **364 passes**, full static/build pass, **3 payment warnings and bundle warning**. Reinspect uncommitted **0012-0017**, not current passes. Historical code/independent review ACCEPTED **B1-4 Q1 F1a F2 F3 F4 F5 F6 F11a F12**, no production approval. Reuse current UI/demo/Three.js/F12 foundations; docs may be stale.

Exactly three specialized role agents: **PLANNER read-only; DEVELOPER one planned task; REVIEWER independent; repair max 3; do not manually substitute if roles cannot be spawned.** Missing coordination BLOCKED/ask before manual substitution, no pretend/self-review. PLANNER reads current owner/tests/dependencies/already-done/hypothesis/check; DEVELOPER performs one verification/assigned repair and immediately reruns focused validation after edits; REVIEWER independently assesses severity/file:line/proof/impact/fix; max three repair cycles.

Conservative choices approved, not policy expansion/client roles/backfill/refunds/legal claims/private egress. Preserve rights/no blanket finance/fulfillment grants. Fresh tenant/capability/private evidence checks, immutable committed hash/version and human same-version bilateral approvals/no AI authority. Redirect not proof, real history never offline. Atomic outbox/no network inside DB locks; bounded finite Decimal BEFORE formatting/computing. Preserve dirty tracked/untracked/user changes, reread before apply_patch, no cleanup/branch/commit/push/reset. Actual-head migration never fixed 0018; preserve upgrades/block history-loss downgrade; demo claims/paid-history/drain/0014/0017 intact. Fakes normally; browser/live check only authorized isolated environment. Secrets private operator terminal only, not questions/model/docs/logs/screenshots. Missing tools/deployment BLOCKED, continue independent tasks; mandatory unmet gate NOT_COMPLETE.

## Scope and Dependencies

Dependency **11**, plus authorized runnable deployment/URL and Playwright/browser tools. Verify readiness/mode/session setup; never substitute mounted mocked UI for an actual deployment. No implicit service startup/install. Read [App](../../frontend/src/App.tsx), [TradeFlowScene](../../frontend/src/deals/TradeFlowScene.tsx), [DealConstellation](../../frontend/src/deals/DealConstellation.tsx), [document panel](../../frontend/src/deals/CommercialDocumentPanel.tsx), [styles](../../frontend/src/styles.css), [frontend scripts](../../frontend/package.json), [document tests](../../backend/tests/test_commercial_documents.py) and [detail UI tests](../../frontend/src/deals/DealDetailPage.test.tsx). Inspect current selectors/asset paths and run support; do not invent URLs. Verify done from current visual/artifact evidence before repeating.

## Verification Contract

Use Playwright **desktop and mobile**, at least desktop 1440x900 and mobile 390x844 plus a narrow supported width, with **two isolated authenticated party contexts** and an unrelated tenant denial case. Operator performs private authentication if needed. Execute the full judge journey: profile capabilities/products/regions/contacts/UNVERIFIED authority, explicit permissions, collection authoring, bilateral version/hash commitment, partial fulfillment, milestones, amendments/cases/routing/reminders and exports. Check organization switches, revocation, back/forward, stale/late canceled requests, keyboard/forms, empty/loading/error/disabled states and responsive layout. Assert absence of cross-tenant/private evidence leakage; redacted artifacts only.

Capture screenshots and DOM bounding/overflow assertions on both viewports; inspect console/network failures. For **Three.js** require screenshots plus **canvas-pixel checks**, not merely canvas presence: capture the canvas screenshot, decode PNG through an available image parser or a browser Image/2D canvas using its screenshot data URL, count nontransparent/nonuniform/nonbackground pixels and record thresholds/dimensions. Compare two actual rendered frames over time to prove motion when allowed; exercise supported pointer/touch interaction and show scene change. Verify correct framing, visible objects, asset load success, resize, reduced-motion preference and no overlapping canvas/text/controls. Do not alter application rendering/preserveDrawingBuffer merely to manufacture evidence. If pixel tooling is unavailable BLOCKED, not visually guessed pass.

Actually download authorized ZIP and individual HTML/documents in both entitled contexts. Inspect archive members, safe names/escaping, version/hash/allocation/fulfillment provenance and deterministic content; deny unrelated/revoked contexts and compare legacy historical bytes where applicable. Test print media, preview/PDF where supported: page breaks, full tables, no clipping/overlap/missing records, mobile-to-print transitions and correct provenance. Record any PDF/browser limitations as unmet criteria, not fake completion.

No feature changes unless PLANNER assigns a bounded repair, then DEVELOPER/focused tests and independent REVIEWER, max 3. Prefer no persistence/migration; if repair needs persistence, actual-head preservation rules apply. Full gates only where repair risk requires them; final whole-worktree gates remain mandatory later.

## Focused Checks and Gates

The complete runner below is for document regression alongside current frontend tests; it does NOT satisfy Playwright/3D/download/print evidence. Reinspect [config](../../backend/src/syncally/config.py) and current security/provider tests before runtime. Dynamically derive all Settings/PayPalSettings/GmailSettings BaseSettings fields/defaults/aliases/model_config; Settings imports globally with production APP_ENV default. Ignore dotenv ONLY bootstrap/discovery; restore normal construction before bodies, clear config case-insensitively, preserve TEST_POSTGRES_URL/SYNCALLY_TEMPORAL_*, restore child env finally. No logging/skip/Temporal startup/module/security/provider masking; required/complex aliases fail pending reviewed runner update. Python 3.12+ configured venv, no silent installs/services. Full gates when required: all backend discovery, ruff src tests, npm test/lint:check/build and git diff --check with immediate `$LASTEXITCODE`. Never run embedded checks during authoring.

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
    patterns = ('test_commercial_documents.py',)
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
npm test -- src/deals/CommercialDocumentPanel.test.tsx src/deals/DealDetailPage.test.tsx
if ($LASTEXITCODE -ne 0) { throw 'Focused UI tests failed' }
npm run lint:check
if ($LASTEXITCODE -ne 0) { throw 'Frontend static gate failed' }
```

## Acceptance and Completion Report

Genuine desktop/mobile two-party security/layout, Three.js nonblank pixel/framing/asset/motion/interaction and download/ZIP/HTML/print evidence independently accepted. Otherwise mandatory BLOCKED. Append progress UTC/12/dependency/roles/URL-mode-browser-viewports/redacted screenshots and pixel metrics/file:line proof/commands/cwd/exits/counts/skips/download/print artifacts/findings severity-impact-fix/repairs 0-3. Initial NOT_RUN; no mocked pass or production approval. Report verified/failed scope/tools/risks and continue independent tasks.