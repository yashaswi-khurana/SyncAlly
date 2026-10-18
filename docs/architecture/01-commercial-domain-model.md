# 01 --- Commercial Domain Model and State Transitions

**Status:** Proposed\
**Owner:** SyncAlly engineering\
**Last updated:** 2026-10-13

## 1. Purpose and boundaries

This document defines the business concepts and invariants that remain
authoritative regardless of whether SyncAlly uses LangGraph, Temporal,
FastAPI, or a particular LLM provider.

The domain owns: - parties and their authority to act; - private and
shareable commercial constraints; - proposals and counterproposals; -
immutable agreement versions and approvals; - committed obligations; -
payment milestones and payment intents; - fulfillment evidence and audit
events.

The domain does **not** own: - LLM reasoning internals; - Temporal
workflow history; - PayPal's authoritative provider-side records; - a
complete accounting, inventory, tax, or customs system.

## 2. Core aggregates and entities

### Organization and membership

`Organization` - `id` (UUID) - `legal_name` - `country_code` -
`status` - `created_at`

`OrganizationMember` - `organization_id` - `user_id` - `role` -
`status` - `created_at`

A user must be an active member of the relevant organization and hold
the required permission to approve terms or authorize a payment request.
Do not trust organization IDs or roles asserted by the client or an LLM.

### Deal

`Deal` - `id` - `buyer_organization_id` - `seller_organization_id` -
`status` - `current_proposal_id` (nullable) -
`current_agreement_version_id` (nullable) - `version` (optimistic
concurrency counter) - `created_at`, `updated_at`

Invariants: - buyer and seller are different organizations; - a deal has
exactly one buyer and one seller in the MVP; - all reads and writes are
authorized against deal participation; - state transitions occur through
domain commands, not direct status assignment.

### Conversation and message

`Conversation` - `id`, `deal_id`, `participant_organization_id`,
`created_at`

`Message` - `id`, `conversation_id`, `author_user_id` or
`author_agent_id` - `content_reference` or protected content -
`created_at` - `visibility` - `source_type`

Conversation data must be labeled by owner and visibility. Never build a
shared LLM prompt from all deal messages without an explicit
access-filtering step.

### Constraint and evidence

`Constraint` - `id`, `deal_id`, `owner_organization_id` - `field`,
`typed_value`, `currency_or_unit` where relevant - `kind`:
`HARD_LIMIT | PREFERENCE | FLEXIBLE_OPTION | INFORMATIONAL` - `status`:
`EXTRACTED | NEEDS_CLARIFICATION | CONFIRMED | REJECTED | SUPERSEDED` -
`visibility`: `PRIVATE | SHAREABLE` - `source_message_id` -
`source_span` or provenance reference - `confirmed_by`, `confirmed_at` -
`version`

Constraints extracted by a model remain `EXTRACTED` until reviewed or
confirmed under the applicable policy. Model-reported confidence is not
proof of correctness. Conflicting or ambiguous high-impact facts should
trigger clarification.

### Proposal

`Proposal` - `id`, `deal_id`, `proposal_number` -
`author_organization_id` - `based_on_proposal_id` (nullable) - `status`:
`DRAFT | SUBMITTED | ACCEPTED_AS_CANDIDATE | REJECTED | SUPERSEDED | EXPIRED` -
`terms_json` (validated canonical schema) - `terms_hash` - `created_at`,
`expires_at` (optional)

A proposal is a candidate, not a binding agreement. A proposal must
include a schema version. A canonicalizer must normalize decimal values,
units, dates, currency codes, shipment allocations, and optional fields
before calculating `terms_hash`.

### AgreementVersion

`AgreementVersion` - `id`, `deal_id`, `version_number` - `proposal_id` -
`canonical_terms_json` - `terms_hash` - `status`:
`PENDING_APPROVAL | COMMITTED | SUPERSEDED | VOIDED` - `created_at`,
`committed_at` - `created_by`

Committed versions are immutable. Corrections and changes create a new
version or a formally recorded amendment; they do not edit the committed
snapshot.

### Approval

`Approval` - `id`, `deal_id`, `agreement_version_id` -
`organization_id`, `user_id` - `decision`: `APPROVE | REJECT` -
`terms_hash` - `created_at` - `authentication_context` / audit reference

The server derives the user's organization and permissions from
authenticated identity. The request must reference the exact current
agreement version and hash. Approval of an older version is stale and
cannot satisfy the commit condition.

### Obligation and milestone

`Obligation` - `id`, `deal_id`, `agreement_version_id` -
`obligation_type`: `PAYMENT | DELIVERY | DOCUMENT | OTHER` -
`owner_organization_id` - `counterparty_organization_id` - `status` -
`due_condition` or due date - `source_terms_reference`

`PaymentMilestone` - `id`, `deal_id`, `agreement_version_id` -
`sequence_number` - `amount` as fixed-precision decimal - `currency` -
`trigger_type` - `status` - `created_at`

Milestones must reconcile to the payable total under the supported
commercial rules. Deposits, fees, taxes, refunds, credits, exchange-rate
effects, and partial payments must be explicitly modeled rather than
silently folded into amounts.

### PaymentIntent

See `03-paypal-payment-intent-lifecycle.md`. It represents one
authorized attempt to create/send a provider payment request and is not
itself proof of payment.

### AuditEvent

`AuditEvent` - `id` - `aggregate_type`, `aggregate_id` - `event_type` -
`actor_type`, `actor_id` - `occurred_at`, `recorded_at` -
`correlation_id` - `payload_reference` or minimized structured payload -
`previous_event_hash` only if a tamper-evident chain is intentionally
implemented

Treat the audit log as append-only at the application level. Avoid
storing secrets, full payment credentials, or unnecessary private
negotiation traces in audit payloads.

## 3. Canonical agreement contents

The MVP agreement schema should explicitly represent: - buyer and seller
legal/business identities; - line items, descriptions/SKUs where
available, units, quantities; - unit price, currency, discounts, and the
supported tax representation; - total payable amount and calculation
inputs; - shipment allocations, delivery locations and target dates; -
named delivery/trade terms where agreed; - payment milestones, triggers
and due conditions; - cancellation, change and exception process; -
source evidence references; - schema version and canonical terms hash.

Do not infer taxes, customs classification, Incoterms, legal authority,
or export eligibility from an LLM guess. If a required term is
unsupported or ambiguous, block commitment or route it to human review.

## 4. Deal lifecycle

Suggested high-level state machine:

`DRAFT -> GATHERING_REQUIREMENTS -> NEGOTIATING -> PENDING_APPROVALS -> AGREED -> EXECUTING -> COMPLETED`

Additional terminal/exception states: - `CANCELLED` (only under
authorized cancellation rules); - `EXPIRED`; - `DISPUTED` (if defined by
the product's dispute model).

Rules: 1. `DRAFT` can enter gathering only after the deal participants
are established. 2. `GATHERING_REQUIREMENTS` advances when required
facts are confirmed or explicitly waived by an authorized user. 3.
`NEGOTIATING` stores proposals; it does not create obligations. 4.
`PENDING_APPROVALS` points to one immutable agreement candidate version.
5. `AGREED` is entered only by a transactional domain command that
verifies both organizations approved the same current version/hash and
that required approvals remain valid. 6. `EXECUTING` means operational
obligations are underway; it does not imply payment or delivery is
complete. 7. `COMPLETED` requires all completion conditions defined by
the supported deal type. 8. A material change after commitment creates
an amendment/new version with the required approvals. 9. Payment and
fulfillment have separate state machines; deal status must not be used
as a substitute for them.

## 5. Atomic bilateral approval

Recommended command:
`CommitAgreement(deal_id, expected_version, expected_terms_hash)`.

Within one database transaction: 1. Lock or version-check the deal and
current agreement candidate. 2. Confirm candidate is still current and
`PENDING_APPROVAL`. 3. Confirm an authorized, active buyer approval
exists for this exact version/hash. 4. Confirm an authorized, active
seller approval exists for this exact version/hash. 5. Confirm neither
approval was invalidated by a changed version or policy. 6. Mark
agreement `COMMITTED`, set `committed_at`, update deal state and
version. 7. Create required obligations and payment milestones from the
committed snapshot. 8. Insert audit and outbox events in the same
transaction. 9. Commit.

If any check fails, roll back. Never rely on two browser callbacks or
two Temporal signals alone to commit.

## 6. Core invariants

-   No proposal is a commitment.
-   No agreement commits without bilateral, authorized approval of the
    same canonical version/hash.
-   No committed agreement version is edited in place.
-   No payment request is created/sent without a committed agreement, a
    valid payment milestone, and required seller authorization.
-   Money uses `Decimal` in application code and fixed-precision
    database columns; never binary floating point.
-   Currency is explicit on every amount.
-   Shipment allocations equal the agreed total quantity when they
    represent the complete shipment plan.
-   Payment allocations equal the modeled payable total when the
    schedule represents the complete payable amount.
-   All external side effects have durable intent records and
    idempotency/reconciliation logic.
-   Every state transition records actor/system identity, correlation
    ID, timestamp and reason.
-   Private constraints and prompts are never exposed to the
    counterparty through proposal payloads or shared traces.

## 7. Concurrency and database guidance

Use optimistic concurrency (`version` or expected version IDs) for deals
and proposals. Use database constraints for uniqueness and foreign-key
integrity. Use transactions for approval/commit and payment-intent
creation. If row-level security is used, set tenant context safely per
transaction and test pooled-connection behavior.

Do not keep database transactions open while calling an LLM or PayPal.
External calls belong outside short database transactions, coordinated
with durable state and outbox records.

## 8. Commands and events

Initial commands: - `CreateDeal` - `AddConversationMessage` -
`ConfirmConstraint` - `SubmitProposal` - `CreateAgreementCandidate` -
`ApproveAgreementVersion` - `RejectAgreementVersion` -
`CommitAgreement` - `ProposeAmendment` - `AuthorizePaymentIntent` -
`RecordProviderWebhook` - `ReconcilePayment` - `RecordFulfillmentEvent`

Initial domain events: - `DealCreated` - `ConstraintConfirmed` -
`ProposalSubmitted` - `AgreementCandidateCreated` -
`AgreementApproved` - `AgreementCommitted` - `AmendmentProposed` -
`PaymentIntentAuthorized` - `ProviderInvoiceCreated` -
`ProviderInvoiceSent` - `PaymentStateReconciled` -
`FulfillmentEventRecorded`

Events are facts that have already happened. Commands request an action
and can be rejected. Do not name an unverified provider callback
`PaymentCompleted`.

## 9. Definition of done

-   State transitions are unit-tested.
-   Bilateral approval tests include stale/mismatched versions and
    unauthorized users.
-   Concurrent commits cannot create duplicate commitments.
-   Monetary calculations are deterministic.
-   Tenant-isolation tests cover every deal, message, constraint,
    approval and payment endpoint.
-   Every committed agreement can be reconstructed from immutable stored
    terms and approval evidence.
