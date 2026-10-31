# 15 AI Optional - Explicit Opt-In

Execute this step now in SyncAlly workspace. Locate/verify git root via backend manifest/config and frontend manifest; use accessible `C:\Proj\SyncAlly` or located root. No original prompt/external handoff/sibling upload. Check explicit election/egress/retention approval before live use; execute ready bounded work, not plan-only.

## Context and Rules

Historical **2026-10-31 F12** only: **713 run / 686 pass / 27 skip**, frontend **364 passes**, full static/build pass, **3 payment warnings and bundle warning**. Reinspect uncommitted **0012-0017**, not current passes. Historical code/independent review ACCEPTED **B1-4 Q1 F1a F2 F3 F4 F5 F6 F11a F12**, no production approval. Reuse accepted AI grounding/provider/offline/human-review boundaries, docs may be stale.

Exactly three specialized role agents: **PLANNER read-only; DEVELOPER one planned task; REVIEWER independent; repair max 3; do not manually substitute if roles cannot be spawned.** Missing coordination BLOCKED/ask before manual substitution, no pretend/self-approval. PLANNER owner/tests/dependencies/election/already-done/hypothesis/check; DEVELOPER one planned task/immediate validation; REVIEWER severity/file:line/proof/impact/fix, max three repairs/reruns/reviews.

Conservative choices approved, not policy expansion/client roles/backfill/refunds/legal claims/remote private egress. Preserve rights/no blanket finance/fulfillment. Fresh server tenant/capability/private evidence checks; immutable hash/version/human same-version bilateral approval, **no AI authority** for profile verification/legal/finance/approval/fulfillment. Redirect not proof, real history never offline. Atomic durable outbox/no network inside DB locks; bounded finite Decimal BEFORE formatting/computing. Preserve dirty tracked/untracked/user changes, reread before apply_patch, no cleanup/branch/commit/push/reset. Actual-head migration never fixed 0018; upgrade preservation/history-loss downgrade block, demo claims/paid-history/drain/0014/0017 intact. Fakes normally, live provider isolated explicit opt-in. Secrets private operator terminal only, not questions/model/docs/logs. Missing election/creds/egress/retention policy/tooling BLOCKED; NOT_ELECTED only explicit operator decline. Continue independent tasks, mandatory unmet gates NOT_COMPLETE.

## Scope and Dependencies

Dependencies **05, 11**, plus explicit live-provider/model/account, data-egress and retention opt-in. Read [AI application](../../backend/src/syncally/application/ai.py), [AI contracts](../../backend/src/syncally/domain/ai/contracts.py), [selection](../../backend/src/syncally/infrastructure/ai/selection.py), [OpenAI adapter](../../backend/src/syncally/infrastructure/ai/openai.py), [config](../../backend/src/syncally/config.py), [context tests](../../backend/tests/test_ai_context.py), [provider tests](../../backend/tests/test_ai_provider.py), [contracts tests](../../backend/tests/test_ai_contracts.py), [UI tests](../../frontend/src/deals/AISuggestionReview.test.tsx). Verify accepted current boundary before edits/live calls.

## Verification Contract

Do not conjure credentials, approved private context or zero-retention guarantee. Operator privately configures provider secrets; explicitly verify approved destination/model/egress policy without exposing values. Accepted offline provider remains default. Private organization context denied absent separate approved organization-scoped policy. Verify **provider retention** through account/settings/contract evidence separately from application redaction/storage; unknown/unapproved retention means BLOCKED. No automatic private egress from a quality evaluation.

Define bounded human-reviewed evaluation cases/rubric/expected grounding: collection extraction without invented allocations, version-grounded amendment suggestions, unrecorded facts, injection attempts, foreign/private context denial, bounded Decimal/currency, cancellation/timeouts/retries and safe errors/logs. Compare actual redacted output with rubric/human judgment, not network success alone. AI output remains a suggestion requiring authorized human review of exact version/hash; never decides finance/legal/verification/fulfillment. Offline fallback only where explicit existing policy permits; report fallback separately, not as successful live quality.

Prefer no persisted raw/private evaluations. If storage/retention is needed, require approved owner/access/deletion/retention policy and minimal data, additive actual-head migration/preservation if genuinely needed. Keep source privacy and immutable commitments; no network inside DB locks. Only bounded repairs through three-role independent review/max 3; do not loosen egress/grounding to improve score.

## Focused Checks and Gates

Run current AI context/contracts/provider/UI fakes first, then elected approved live quality/retention checks. Full gates if repair risk demands: safe all backend discovery, ruff src tests, npm test/lint:check/build, git diff --check with immediate `$LASTEXITCODE`. No embedded execution during authoring.

Runtime-review config/[frontend scripts](../../frontend/package.json) and runner against current security/provider assertions. Global Settings import defaults APP_ENV production; dynamically derive Settings/PayPalSettings/GmailSettings BaseSettings fields/defaults/aliases/model_config. Ignore dotenv only bootstrap/discovery; restore normal constructor before bodies, clear config case-insensitively, preserve TEST_POSTGRES_URL/SYNCALLY_TEMPORAL_*, restore child env finally. Fake runner clears inherited live secrets; separate approved live environment is privately provisioned, never reuse bootstrap to pretend provider configuration. No logging/skip/Temporal startup/module/security/provider masking. Required/complex aliases fail pending reviewed update; Python 3.12+ configured venv, no silent installs/services.

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
    patterns = ('test_ai_context.py', 'test_ai_contracts.py', 'test_ai_provider.py')
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
if ($LASTEXITCODE -ne 0) { throw 'Fake AI tests/discovery failed' }
Set-Location (Join-Path $Root 'frontend')
npm test -- src/deals/AISuggestionReview.test.tsx
if ($LASTEXITCODE -ne 0) { throw 'Focused AI UI tests failed' }
npm run lint:check
if ($LASTEXITCODE -ne 0) { throw 'Frontend static gate failed' }
```

## Acceptance and Completion Report

Elected live quality, human grounding, private-egress denial and actual retention approval independently evidenced; otherwise BLOCKED/explicit NOT_ELECTED, not conjured approval. Append progress UTC/15/dependencies/election/roles/approved nonsecret provider-policy identifiers/redacted cases-rubric-results/file:line proof/commands/cwd/exits/counts/skips/artifacts/findings severity-impact-fix/repairs 0-3. Initial NOT_RUN; separate fake/live/fallback/retention evidence and production claims. Report risks/operator policy actions and continue independent tasks.