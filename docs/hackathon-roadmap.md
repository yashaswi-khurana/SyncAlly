# SyncAlly: Confirmed Bugs and Feature Roadmap

This document consolidates the confirmed bug findings and feature ideas discussed for the
hackathon and the next product milestones. It is a planning document, not a claim that the
repository is bug-free or that every feature below is absent.

The bug list contains issues confirmed during code review. The feature list distinguishes
existing foundations from the user-facing capabilities still worth completing. Priorities assume
a product/AI hackathon; reorder them if the judging rubric emphasizes different criteria.

## Confirmed bugs

These are confirmed findings, not an exhaustive audit. Live PostgreSQL, Temporal, PayPal, and
Gmail integrations were not exercised as part of the review.

| # | Severity | Bug | Evidence and impact | Recommended fix |
|---|---|---|---|---|
| 1 | Medium | Invitation acceptance allows passwords that login rejects. | Invitation acceptance permits passwords from 8 characters, while login requires at least 12. A user can accept an invitation and receive a token, then be unable to log in after it expires. See [organization invitation request](../backend/src/syncally/api/organizations.py), [login request validation](../backend/src/syncally/api/auth.py), and [sign-in UI](../frontend/src/auth/SignInPage.tsx). | Align password rules in invitation acceptance, login, and the frontend. Add a regression test covering acceptance followed by login. |
| 2 | Medium | Message retries can create duplicate messages. | The client sends an idempotency key, but the message endpoint does not enforce it. Repeating the same request with the same key created two messages with different IDs. The composer also generates a new key for each send attempt. See [message composer](../frontend/src/deals/DealConversationReview.tsx), [conversation API](../backend/src/syncally/api/conversations.py), and [API client](../frontend/src/api/client.ts). | Enforce idempotency server-side, scoped to the deal and actor, and reuse the same key when retrying the same draft. Add a database-backed regression test. |
| 3 | Medium | Payment status polling can stop while processing is still active. | The UI does not poll for some backend nonterminal states, including `AUTHORIZED`, `CREATE_UNKNOWN`, and `PROVIDER_CREATED`. A payment may therefore appear stale until manually refreshed. The UI also treats `RETRYING` as a payment status even though retry state is separate from the backend intent status. See [payment status panel](../frontend/src/deals/PaymentStatusPanel.tsx), [payment intent statuses](../backend/src/syncally/domain/payments/intent.py), and [payment repository](../backend/src/syncally/infrastructure/repositories/payments.py). | Derive polling behavior from backend-defined nonterminal states. Expose outbox retry state separately if the UI needs to display it. |
| 4 | Low | Locally generated invitation links point to the production app. | The invitation URL uses the production frontend origin, while a local invitation token is signed with the local backend secret. The production app cannot validate that token. See [invitation creation and verification](../backend/src/syncally/api/organizations.py). | Make the public frontend URL environment-configurable and test local and production settings. |

## Feature roadmap

### Hackathon-focused vertical slice

| Priority | Feature | Existing foundation | Recommended next work |
|---|---|---|---|
| P0 | **One-click judge demo** | A development role switcher and demo reset already exist in [DevRoleSwitcher](../frontend/src/ui/DevRoleSwitcher.tsx). | Seed one complete, realistic buyer/seller scenario with messages, reviewable facts, and an agreement draft. Provide one documented start/reset flow and a short judge-facing walkthrough. |
| P0 | **Conversation-to-terms AI copilot** | Typed AI contracts, privacy filtering, source grounding, and a deterministic rule-based provider exist. See [AI provider boundary](architecture/06-ai-provider-boundary.md) and [demo provider](../backend/src/syncally/infrastructure/ai/demo.py). | Add a real provider behind the existing boundary if credentials and time permit. Let users paste or import a conversation, extract candidate terms with exact source citations, highlight conflicts and missing information, and require human review. Keep an offline fallback. |
| P0 | **Complete two-party onboarding** | Organization directory and invitation API routes exist in [organizations.py](../backend/src/syncally/api/organizations.py); invitations should not be rebuilt from scratch. | Complete and verify the end-user invitation/acceptance flow, including password setup, local links, and a counterparty experience that does not depend on the development-only role switcher. |
| P0 | **PayPal Sandbox end-to-end** | Payment intents, outbox processing, status APIs, and a payment panel exist. External provider integration is identified as planned in the [README](../README.md). | Complete the opt-in Sandbox invoice creation, webhook verification, reconciliation, and visible status flow. Never treat a browser redirect as proof of payment. Clearly label any fallback simulation. |
| P1 | **Agreement change review and evidence trail** | Bilateral approval of the same version/hash is implemented. | Show a before/after terms diff, link changed terms to source messages, and make each party’s approval of the exact version clear. |
| P1 | **Shareable trade pack** | A committed-agreement trade summary can be downloaded as plain text through the [document panel](../frontend/src/deals/CommercialDocumentPanel.tsx). | Produce a polished downloadable draft pack from committed terms. Label it as a draft and do not claim legal, tax, or customs compliance. |

### Core product capabilities

| Priority | Feature | Existing foundation | Recommended next work |
|---|---|---|---|
| P1 | **Persisted negotiation rounds and counteroffers** | The domain defines proposals, proposal status, and negotiation round control in [proposal.py](../backend/src/syncally/domain/negotiation/proposal.py). | Connect these concepts to persistence, API routes, and UI so parties can submit, counter, accept, reject, supersede, and expire proposals with a visible history. |
| P1 | **Fulfillment tracking and evidence** | Committing terms creates delivery obligations in [obligations.py](../backend/src/syncally/domain/agreements/obligations.py); deal lifecycle states include execution and completion in [deal.py](../backend/src/syncally/domain/deals/deal.py). | Add participant-facing fulfillment tasks with due dates, shipment references, delivery confirmation, and supporting evidence. Keep fulfillment state separate from payment state. |
| P1 | **Post-agreement amendments and change orders** | Committed agreement versions are treated as immutable. | Let parties request changes to quantity, delivery, or payment terms as a new version, show the impact, and require the appropriate re-approvals. Never edit a committed snapshot in place. |
| P1 | **Exception, cancellation, and dispute handling** | The domain has lifecycle states such as `CANCELLED` and `DISPUTED`, but those states alone do not provide a complete user workflow. | Add authorized requests, evidence collection, status tracking, and resolution history for late delivery, short shipment, damage, payment mismatch, or cancellation. Avoid automatically deciding disputes. |
| P2 | **Multiple shipments and staged payments** | Trade terms represent collections of line items, shipments, and payment terms; payment milestones are derived from payment terms. | Make APIs, UI, payment processing, and document generation handle every line, shipment, and milestone consistently. Confirm that no path silently handles only the first entry before expanding scope. |
| P2 | **Business roles and approval policies** | Organization membership currently distinguishes broad `ADMIN` and `MEMBER` roles in [organization.py](../backend/src/syncally/domain/organizations/organization.py). | Add permission boundaries for procurement, finance, and fulfillment, plus configurable approval routing and separation of duties for higher-risk actions. Enforce all permissions server-side. |
| P2 | **Supplier qualification and richer profiles** | An authenticated organization directory exists in [organizations.py](../backend/src/syncally/api/organizations.py). | Enrich profiles with relevant capabilities, products, regions, contacts, and explicitly defined verification status; support buyer shortlisting without treating unverified claims as facts. |
| P2 | **Deadline reminders and notifications** | Temporal workflows and a transactional outbox provide durable orchestration foundations. | Notify the appropriate users about pending approvals, upcoming delivery dates, and payment actions through in-app notifications and optional email. Keep retries bounded and avoid exposing private deal data. |

## Suggested sequencing

1. Fix the four confirmed bugs and add regression tests.
2. Make the seeded demo repeatable and finish the real two-party experience.
3. Implement proposal rounds and source-grounded conversation review.
4. Complete and test the Sandbox payment path, if the required credentials are available.
5. Add fulfillment tracking, then amendments and exception handling.
6. Expand to staged payments, additional organization roles, supplier qualification, and reminders when the core lifecycle is reliable.

## Scope and safeguards

- Treat every AI result as a suggestion. Humans and domain rules remain responsible for approval and payment authorization.
- Keep buyer-private and seller-private context isolated.
- Use fakes for ordinary tests; external Sandbox tests must be opt-in.
- Do not imply production payment readiness or universal legal, tax, customs, export, or accounting compliance.
- Recheck implementation status before starting a feature; this roadmap records review observations and proposals, not a substitute for inspecting the current code.
