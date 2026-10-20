# 02 --- Temporal Deal Workflow Contract

**Status:** Proposed\
**Purpose:** Define how Temporal orchestrates long-running deal
processes without becoming the source of commercial truth.

## 1. Responsibility boundary

Temporal owns process progression, timers, retries, signals, and durable
waits. The SyncAlly domain owns commercial state and validates every
command. LangGraph may be invoked inside a bounded activity to extract
or propose terms.

Never place non-deterministic LLM calls, HTTP calls, or direct database
writes inside Temporal workflow code. Perform them in activities or
application services. Workflow code should orchestrate, not implement
the domain.

## 2. Workflow identity

Use a stable workflow ID, for example:

`deal/{deal_id}/lifecycle`

Start only one lifecycle workflow for a deal. Use a controlled
workflow-ID reuse/conflict policy and handle "already started" responses
idempotently.

Do not place private constraints, payment credentials, or large
transcripts in workflow arguments or event history. Pass stable record
IDs and minimal non-sensitive data. Retrieve role-authorized context
inside activities.

## 3. Workflow inputs

`DealWorkflowInput` - `deal_id` - `schema_version` -
`initiating_actor_id` (for audit/correlation only; not a continuing
authorization grant) - `created_at`

The workflow should load authoritative state from the domain service. It
must not trust an input snapshot as permanently current.

## 4. Signals and updates

Recommended external events: - `BuyerMessageReceived(message_id)` -
`SellerMessageReceived(message_id)` - `ProposalSubmitted(proposal_id)` -
`AgreementApprovalRecorded(approval_id)` -
`AgreementRejected(approval_id)` -
`PaymentIntentAuthorized(payment_intent_id)` -
`PaymentStateChanged(payment_intent_id, new_domain_version)` -
`FulfillmentEvidenceRecorded(event_id)` -
`CancelRequested(request_id, actor_id)`

Signals are notifications, not proof of authorization. The receiving
workflow or activity must load and validate the referenced domain
record. Where a synchronous response/validation is needed, use an
appropriate Temporal Update or an API command followed by a signal; the
API must still enforce the domain policy.

Signal handlers should be idempotent and tolerate duplicate/out-of-order
notifications. Prefer IDs over full payloads.

## 5. Activities

Suggested activity contracts:

### `ExtractConstraints`

Input: `deal_id`, `message_id`, `organization_id`, `schema_version`\
Output: extraction-run ID and candidate constraint IDs.

Requirements: - load only the caller organization's authorized
conversation/context; - return typed, schema-validated candidates with
provenance; - never auto-confirm high-impact constraints unless a
documented policy explicitly allows it; - apply model timeout, retry
budget and token budget.

### `GenerateProposal`

Input: `deal_id`, `proposal_context_id`, `acting_organization_id`,
`round_number`\
Output: `proposal_id`.

Requirements: - use role-specific private policy; - emit only shareable
proposal terms and an explanation suitable for the counterparty; - do
not include hidden budget, floor, internal prompts, or raw private
traces; - pass proposal to domain validation before it can be submitted.

### `ValidateProposal`

Input: `proposal_id`, `expected_deal_version`\
Output: `VALID | INVALID | NEEDS_CLARIFICATION` plus error codes.

The domain service remains authoritative. A model-produced validation
result is never sufficient.

### `RequestApproval`

Input: `agreement_version_id`, `terms_hash`, `organization_id`\
Output: notification/job reference.

This activity requests attention; it does not manufacture approval.
Approval is recorded by the authenticated API after the human acts.

### `CreateProviderInvoice`

Input: `payment_intent_id`\
Output: provider invoice ID and provider status.

Must use the payment-intent state machine and provider idempotency
controls described in document 03.

### `ReconcileProviderInvoice`

Input: `payment_intent_id`, optional `provider_event_id`\
Output: normalized provider snapshot and resulting domain state version.

Must fetch/reconcile provider state where applicable rather than
trusting webhook body alone.

## 6. Main lifecycle

1.  Start workflow for a persisted deal.
2.  Wait for requirements/messages or a deadline.
3.  Request bounded extraction/proposal activities.
4.  Validate proposals through the domain service.
5.  Enforce maximum rounds, wall-clock deadline, model-call budget and
    escalation.
6.  When an agreement candidate exists, wait for domain approval
    records.
7.  Ask the domain service to commit only after both valid approvals
    reference the same current version/hash.
8.  After commitment, coordinate document preparation and payment
    milestones.
9.  For each payment milestone, wait for an authorized payment intent
    and provider reconciliation.
10. Track fulfillment evidence and supported completion conditions.
11. Complete, expire, cancel or escalate according to domain policy.

Do not model every conversational message as a new Temporal workflow.
Use one deal lifecycle workflow plus bounded activities; use child
workflows only when there is a genuinely independent long-running
sub-process.

## 7. Waits, timeouts and escalation

Every wait must have a defined policy: - negotiation round deadline; -
user approval deadline; - payment due date/reminder schedule; - maximum
agent attempts; - maximum wall-clock duration; - manual escalation
destination.

Timeout must not imply acceptance. An expired approval request remains
unapproved. An expired payment deadline becomes overdue or escalated
under domain policy; it must not automatically mark a payment failed
without provider/domain evidence.

## 8. Retry and idempotency rules

-   Retry transient network errors with bounded exponential backoff and
    jitter.
-   Do not retry permanent validation/authentication failures blindly.
-   Use stable application operation IDs for external side effects.
-   Before retrying an ambiguous provider call, query/reconcile using
    the saved intent and provider reference where possible.
-   Every activity that writes domain state must use an idempotent
    command with an expected version or unique operation key.
-   Do not assume a Temporal activity executes exactly once. A worker
    can crash after the provider succeeds but before Temporal records
    the result.
-   Do not perform direct email, PayPal, ERP or storage side effects in
    workflow code.

## 9. Outbox and workflow start consistency

Creating a deal and starting a Temporal workflow are two different
systems; a crash between them can leave an orphaned deal or a missing
workflow.

Recommended pattern: 1. Persist the deal and `WorkflowStartRequested`
outbox event in one PostgreSQL transaction. 2. An outbox dispatcher
starts the workflow using the stable workflow ID. 3. Mark the outbox
event dispatched only after handling the start result. 4. If the
dispatcher crashes and retries, treat "workflow already started" as a
successful idempotent outcome after verifying the workflow identity.

Use the same approach for important domain events that must be delivered
to a workflow. Temporal is not a substitute for a transactional outbox
between PostgreSQL and an external orchestration service.

## 10. Temporal workflow determinism and versioning

-   Keep workflow code deterministic; no direct current-time calls
    outside Temporal's workflow-safe APIs, random IDs, HTTP or database
    I/O in workflow code.
-   Use activities for external interactions.
-   Version workflow behavior when deployments may encounter histories
    created by earlier code.
-   Avoid incompatible workflow changes without a migration/versioning
    strategy.
-   Keep payloads small and redact secrets.
-   Test replay against representative histories before production
    releases.

### Deal workflow signal and wait contract

`DealWorkflow` uses the stable `deal/{deal_id}/lifecycle` ID. The
transactional outbox sends deal creation, agreement commits, approvals,
messages, and constraint changes as signals containing only an outbox
notification ID, record ID, and notification kind;
message bodies, approval decisions, payment states, credentials, and
other private content do not enter workflow history. The workflow ignores
repeated notification IDs and asks the `RefreshDealState` activity to
reload and validate current domain state. The start request uses
signal-with-start, so the first committed event is processed immediately
without waiting for a later signal. The first notification immediately
triggers an activity to refresh persisted deal state; every later
notification does the same. The activity must not treat the
initiating agreement-version ID as current authority.
That activity must make decisions from persisted records, so delayed or
out-of-order notifications cannot authorize a business action by
themselves.

The workflow waits at most 30 days in total, carrying its absolute deadline
through Continue-As-New. Each state-refresh activity has a 30-second
start-to-close timeout, a schedule-to-close timeout no later than that
deadline, and at most three attempts. Validation, business rejection,
authorization, and security activity errors are non-retryable by their
Temporal error type names. A timeout returns `WAIT_EXPIRED` and emits an
operational warning without changing deal, approval, or payment state.
The operations worker must alert on that warning and on failed workflow
executions.

The signal queue is capped at 256 entries; overflow coalesces wake-up
hints, because the activity always reloads the full authoritative deal
state. Duplicate IDs are remembered in a rolling 1,024-ID window. The
workflow continues as new after at most 100 processed notifications (the
internal input may lower this cap), carrying its absolute deadline, pending
notifications, deduplication window, and
processed count forward. Activity refresh is therefore required to be
idempotent and complete enough to recover state when hints are coalesced.
This rollout guards the new Continue-As-New command with the patch ID
`deal-workflow-history-rollover-v1`. Keep the old branch available until
all runs created before the marker have closed; then retire it with
`workflow.deprecate_patch` in a later deployment.

When a timed-out or failed execution closes, the next outbox event uses
signal-with-start with `ALLOW_DUPLICATE` reuse and `USE_EXISTING` conflict
policies. An active execution receives the signal; a closed one is
restarted and receives the signal atomically.

Activities and their worker registration are added in S6-03.

For incompatible workflow behavior changes, add a `workflow.patched`
marker at the command-sequence change and keep both branches until every
execution that could replay the old branch has passed that marker. Only
then may the old branch be retired with `workflow.deprecate_patch`. For
incompatible input changes, increment `schema_version` and keep a decoder
for in-flight old inputs or introduce a new workflow type. Before release,
replay representative histories for every supported version. Never reuse
an existing patch ID for a different change.

## 11. Workflow failure policy

Distinguish: - **Business rejection:** normal domain result; do not
retry. - **Clarification required:** pause and wait for user input. -
**Transient provider failure:** retry/reconcile. - **Permanent
provider/configuration failure:** mark operation requiring
intervention. - **Security/authorization failure:** reject and audit; do
not retry automatically. - **Workflow code failure:** alert, inspect
history, and recover using a documented operational procedure.

A workflow failure must not silently reverse an already committed
agreement or provider-side payment. Recovery proceeds through explicit
domain actions and compensating business operations.

## 12. Testing contract

Required tests: - workflow pauses for approval and resumes after worker
restart; - duplicate signals do not duplicate proposals or payment
operations; - out-of-order signals are reconciled against domain
state; - stale approval cannot commit a newer version; - LLM timeout
causes bounded retry/escalation; - Temporal worker crashes after an
external side effect and recovers without duplicate execution; - a deal
created while Temporal is unavailable eventually starts from the
outbox; - workflow replay remains compatible with supported deployed
histories.

## 13. Definition of done

-   No provider side effect occurs directly in workflow code.
-   All financial actions refer to a persisted PaymentIntent.
-   All approvals are independently verified by the domain layer.
-   Every wait, retry and loop has a limit or explicit operational
    policy.
-   Outbox dispatch is recoverable and idempotent.
-   Workflow history contains no unnecessary secrets or private
    commercial context.
