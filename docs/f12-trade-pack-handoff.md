# F12 Trade Pack Handoff

Status: implemented and ready for independent code review, not production sign-off.
Validation date: 2026-10-31. Scope is the supplied F12 requirements, not an assumed
external handoff file. Prior Q1/demo/AI/onboarding/negotiation/F6/payment-mode work
and migrations 0012-0017 were preserved. No agents, commits, services, migrations,
document persistence or retained server copies were introduced.

## Delivered Contract

`GET /deals/{deal_id}/documents/versions/{number}/trade-pack` requires
`agreement_version_id`, `terms_hash`, and `organization_id`. `format=zip` defaults
to a ZIP; `format=html` returns its identical self-contained HTML attachment.

Authorization rechecks database ACTIVE user, organization and membership state.
Only the exact COMMITTED historical version with matching UUID/number/hash/deal
parties and both version-specific approval hashes can export. No current/latest
substitution or current demo commitment validation is used. Missing/forbidden
resources return 404; inconsistent/unapproved commitments return 409; malformed
or missing parameters return 422; resource-limit violations return 413.

The evidence-free projection excludes `_f6_evidence` without resolving sources or
reading organization profiles. Unknown commitment fields and schemas fail closed.
Canonical UTF-8 JSON uses the established TradeTerms implementation and is verified
against the stored SHA-256 hash. Copied display terms retain recorded case; no live
legal names, download actor or current-time values are added.

ZIP files have fixed order, timestamps, permissions and compression settings:
`trade-pack.html`, `canonical-terms.json`, `manifest.json`. The manifest records
schema versions, exact source identities, created/committed times, party IDs,
entry counts and display terms. Both parties receive deterministic identical bytes.

All persisted line items, shipments and payment terms, including duplicates, are
rendered. Each section is DRAFT / FOR REVIEW ONLY. Missing legal names, addresses,
weight, packaging, banking, tax/customs details and allocations are explicitly not
recorded. The artifact is not an invoice, signed proof, payment proof or compliance
certificate. Fixed inline print CSS, quote-aware escaping, restrictive CSP and no
remote assets, scripts, handlers, links or user CSS prevent executable markup.

Limits: 2 MiB display JSON; a conservative cumulative decimal-expansion envelope
of 2 MiB checked before domain formatting; 2 MiB canonical JSON; 16 MiB total
uncompressed artifact bytes for either format. Rendering growth is bounded and
compression occurs only after the aggregate size check. No output is truncated.
Attachments use validated ASCII filenames, correct MIME, no-store and nosniff.

The panel lives in F6 AgreementReview and uses its exact viewed snapshot and acting
organization. History remains read-only. Changes of party, deal, version, hash,
comparison, reload or session abort/discard stale work. Binary client requests share
authentication, timeout and JSON error handling. Object URLs are cleaned up and
downloaded HTML is never injected into React. The legacy commercial-draft endpoint
and client helper remain unchanged. F10 collection authoring and PDF generation
remain out of scope.

## Files Touched By F12

16 files, including this handoff. This is the F12 list, not the dirty-worktree total.

- [backend document application](../backend/src/syncally/application/documents.py)
- [backend document API](../backend/src/syncally/api/documents.py)
- [agreement repository](../backend/src/syncally/infrastructure/repositories/agreements.py)
- [document application tests](../backend/tests/test_commercial_documents.py)
- [agreement and document route tests](../backend/tests/test_agreement_routes.py)
- [backend README](../backend/README.md)
- [API client](../frontend/src/api/client.ts)
- [API client tests](../frontend/src/api/client.test.ts)
- [document panel](../frontend/src/deals/CommercialDocumentPanel.tsx)
- [document panel tests](../frontend/src/deals/CommercialDocumentPanel.test.tsx)
- [agreement review](../frontend/src/deals/AgreementReview.tsx)
- [agreement review tests](../frontend/src/deals/AgreementReview.test.tsx)
- [deal detail](../frontend/src/deals/DealDetailPage.tsx)
- [deal detail tests](../frontend/src/deals/DealDetailPage.test.tsx)
- [App tests](../frontend/src/App.test.tsx)
- [this handoff](f12-trade-pack-handoff.md)

## Verification

- Focused first edit: 7 document tests passed, including legacy behavior.
- Final document slice: 9 tests passed. Final agreement/API slice: 43 passed.
- Full backend: 713 run, 686 passed, 27 skipped, zero failures/errors.
- Full frontend: 17 files, 364 tests passed, no skips or failures.
- `ruff check src tests`, frontend `lint:check`, production `build`, and
  `git diff --check` passed. Three existing PaymentStatusPanel lint warnings and
  the existing large Three.js bundle warning remain outside F12.

Backend validation used the existing virtual environment, cleared inherited app,
provider and database settings, and bootstrapped APP_ENV=test only for discovery.
That variable was removed before tests so the missing-environment security test
remained meaningful. Logging was not disabled. Temporal integration modules were
explicitly marked unavailable in the runner; PostgreSQL URLs were unset.

The 27 skips cover PostgreSQL message idempotency/locking, F4/F5 concurrency and
migration execution, combined local-service smoke tests, and Temporal test-server
integration. No PostgreSQL/Temporal or provider service was started or live-verified.
Initial harness attempts were corrected and the final complete run passed.

Live PostgreSQL races, real two-party browser downloads and manual print-layout
inspection remain environment verification tasks. There is no production compliance,
signature, payment-proof, provider-retention or F10 authoring claim.