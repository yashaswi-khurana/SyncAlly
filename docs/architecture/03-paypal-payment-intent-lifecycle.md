# 03 --- PayPal Payment Intent Lifecycle

**Status:** Proposed\
**Purpose:** Specify safe, recoverable creation and reconciliation of
PayPal invoices/payment requests.

## 1. Scope and assumptions

The MVP uses PayPal Sandbox and a designated seller-controlled merchant
account. Production multi-merchant support is conditional on PayPal
account eligibility, partner/onboarding requirements, permissions, and a
validated integration model.

This document describes an invoice/payment-request lifecycle, not
escrow, custody, a guarantee of settlement, or a universal marketplace
payment solution.

Keep three concepts separate: - **Commercial invoice:** a seller's
commercial/export document. - **Payment milestone:** the amount and
condition owed under the committed agreement. - **PayPal invoice:** the
provider's payment request.

## 2. Components

-   `PaymentService`: validates commands and domain permissions.
-   `PaymentIntent` repository: durable intent and lifecycle state.
-   `PayPalAdapter`: provider-specific HTTP calls, authentication and
    response normalization.
-   `PaymentWorker`: creates/sends invoices, retries and reconciles.
-   Webhook endpoint: verifies signature/authenticity, stores event
    idempotently, then schedules reconciliation.
-   Reconciliation job: fetches provider invoice/payment state and
    updates the domain through a validated command.
-   Audit/outbox: records authorized operations and reliable downstream
    work.

The LLM never receives PayPal credentials and cannot invoke unrestricted
payment operations.

## 3. PaymentIntent data model

Suggested fields: - `id` (UUID) - `deal_id` - `agreement_version_id` -
`payment_milestone_id` - `seller_organization_id` -
`merchant_connection_id` - `amount` (fixed-precision decimal) -
`currency` - `status` - `provider` (`PAYPAL`) - `provider_invoice_id`
(nullable until known) - `provider_request_id` / operation key -
`request_payload_hash` - `created_by`, `authorized_at` - `created_at`,
`updated_at` - `last_reconciled_at` - `failure_code` and sanitized
`failure_detail` - `version`

Uniqueness constraints should prevent multiple active intents for the
same milestone/operation unless an explicit replacement policy
authorizes a new attempt. A new invoice after cancellation must be a
new, auditable operation linked to the prior intent.

## 4. Authorization preconditions

Before creating a PaymentIntent, the domain service must verify: 1. The
deal has a committed agreement. 2. The milestone belongs to that
committed agreement version. 3. The requesting human is authenticated
and authorized to act for the seller organization. 4. The seller has
authorized issuance for the exact amount/currency and recipient context.
5. The merchant connection belongs to the seller organization and is
valid for the intended API operation. 6. The milestone is not already
fully paid, cancelled, disputed or superseded. 7. Amount/currency match
the canonical milestone after supported adjustments. 8. No duplicate
active intent exists for the same milestone. 9. Applicable
product/payment policy permits the requested operation.

Persist the authorized intent and an outbox event in the same database
transaction. Only then should a worker call PayPal.

## 5. State machine

Internal normalized states:

-   `AUTHORIZED`: seller/domain authorization recorded.
-   `CREATE_PENDING`: durable operation ready for provider call.
-   `CREATE_UNKNOWN`: request outcome ambiguous (for example, timeout
    after request may have reached PayPal).
-   `DRAFT`: provider invoice exists but is not sent.
-   `SEND_PENDING`: authorized send operation is queued.
-   `SENT`: provider confirms invoice was sent.
-   `PENDING`: provider reports payment processing or another non-final
    state.
-   `PARTIALLY_PAID`: reconciled received amount is below amount due.
-   `PAID`: provider reconciliation confirms the required amount is
    fully satisfied.
-   `CANCEL_PENDING`: cancellation requested but not yet confirmed.
-   `CANCELLED`: provider/domain confirms cancellation.
-   `FAILED_REQUIRES_ACTION`: permanent error or unresolved condition
    requiring human intervention.
-   `REFUNDED`, `PARTIALLY_REFUNDED`, `DISPUTED`: only when the provider
    evidence and supported product scope justify these states.

`CREATE_UNKNOWN` is essential. A timeout does not prove the provider
failed to create an invoice.

Do not map an unrecognized provider status to `PAID`. Unknown statuses
should be stored safely and routed to reconciliation/manual review.

## 6. Lifecycle

### A. Authorize and persist

1.  Validate committed agreement, milestone, seller authority and
    merchant connection.
2.  Create a PaymentIntent and unique operation key.
3.  Insert the corresponding outbox record in the same transaction.
4.  Return the intent ID and a non-final status to the UI.

### B. Create PayPal invoice

1.  Worker claims the outbox/job atomically.
2.  Build provider request from server-owned committed terms and
    seller/recipient data.
3.  Use a stable `PayPal-Request-Id` where the specific endpoint
    supports it.
4.  Persist the provider invoice ID and normalized status.
5.  If the response is ambiguous, mark `CREATE_UNKNOWN` and reconcile
    before issuing another create request.
6.  Do not generate a new operation key simply because an HTTP request
    timed out.

Provider idempotency is endpoint-specific and may have retention limits;
verify the actual endpoint contract before relying on it.
Application-side uniqueness and reconciliation remain required.

### C. Send invoice

Sending is a separate side effect. Persist a send operation with its own
stable application operation ID and state. Do not send until the invoice
draft has been validated against the PaymentIntent. If the send response
is ambiguous, reconcile provider state before retrying.

### D. Receive webhook

1.  Receive the raw event over HTTPS.
2.  Verify the webhook signature using PayPal's documented verification
    mechanism or a correctly implemented equivalent.
3.  Persist the event ID under a unique constraint before scheduling
    processing.
4.  Acknowledge promptly after durable acceptance.
5.  Process asynchronously; duplicate event delivery must be safe.
6.  Treat webhook data as a signal to reconcile, not as the only source
    of financial truth.

Do not accept an unsigned browser redirect or client-side "success" page
as payment proof.

### E. Reconcile

1.  Resolve the local intent and its provider invoice ID.
2.  Retrieve authoritative provider invoice/payment details using the
    correct seller merchant context.
3.  Normalize provider status and monetary amounts.
4.  Compare paid amount, remaining balance, currency and relevant
    adjustments with the intended obligation.
5.  Update state through an idempotent domain command using optimistic
    concurrency.
6.  Record provider event/reference, reconciliation timestamp and audit
    event.
7.  Emit `PaymentStateReconciled` through the outbox.

The `INVOICING.INVOICE.PAID` webhook event can represent partial or
pending cases; therefore, do not directly transition to internal `PAID`
based only on the event type.

### F. Recovery and reconciliation sweep

Run a periodic worker for intents stuck in `CREATE_UNKNOWN`,
`SEND_PENDING`, `PENDING`, or otherwise stale states. It should query
provider state, apply bounded retries, and escalate unresolved cases.
The job must be safe to run repeatedly.

## 7. Idempotency and concurrency

Use multiple layers: - Unique local PaymentIntent/operation IDs. -
Unique outbox operation key. - Stable provider request ID when
supported. - Unique provider invoice ID per merchant/provider
namespace. - Unique webhook event ID. - Optimistic concurrency on
PaymentIntent. - Provider reconciliation after ambiguous outcomes. - No
provider calls inside a database transaction.

Do not promise mathematically "exactly once" execution across PostgreSQL
and PayPal. Aim for at-least-once delivery with idempotent commands and
reconciliation so duplicate execution does not create duplicate
financial effects.

## 8. Failure matrix

  -----------------------------------------------------------------------
  Failure                             Required response
  ----------------------------------- -----------------------------------
  LLM proposes wrong amount           Ignore model total; calculate from
                                      committed terms

  Seller approval missing             Reject intent creation

  Merchant connection invalid         Permanent actionable error; do not
                                      loop retries

  PayPal returns validation error     Mark actionable failure and
                                      preserve sanitized details

  Network timeout during create       `CREATE_UNKNOWN`; reconcile before
                                      retry

  Worker crashes after provider       Recover from stored intent/provider
  success                             lookup; do not mint a new operation
                                      key

  Duplicate webhook                   Unique event constraint; no
                                      duplicate state transition

  Webhook signature invalid           Reject/quarantine and alert per
                                      policy

  Webhook arrives out of order        Reconcile current provider state;
                                      don't blindly reverse a newer state

  Invoice is partially paid           `PARTIALLY_PAID` after
                                      reconciliation

  Provider reports pending            Keep pending; don't mark paid

  Amount/currency mismatch            Quarantine for review; no paid
                                      transition

  Refund/dispute                      Separate audited transition; do not
                                      erase original payment history

  PayPal unavailable for prolonged    Backoff, alert, manual recovery
  period                              queue
  -----------------------------------------------------------------------

## 9. Merchant connection model

`MerchantConnection` should include: - seller organization; -
provider; - provider merchant/account reference; - authorization status
and granted scopes/permissions; - encrypted credential/token reference
in a secrets manager; - connection health and last verification time; -
onboarding/eligibility state.

Do not store plaintext long-lived secrets in ordinary application tables
or agent context. Do not let a client select another seller's merchant
connection by ID without server-side ownership validation.

For a platform supporting many independent sellers, confirm PayPal
partner approval, onboarding and invoice permissions before designing
the final live-account flow. The Sandbox demo with one seller is not
proof that multi-merchant production access is approved.

## 10. Payment reconciliation invariants

-   `PAID` only follows verified provider reconciliation satisfying the
    full modeled amount due.
-   Amount and currency must match the intended obligation after
    explicit, supported adjustments.
-   A duplicate webhook cannot duplicate a payment or milestone
    transition.
-   A late event cannot downgrade a more current reconciled state
    without an explicit correction workflow.
-   A refund does not delete the original receipt; it adds a new
    financial event and recalculated state.
-   A payment does not imply shipment, delivery, or deal completion.
-   A cancelled local intent is not proof the provider invoice was
    cancelled.
-   Every provider call is correlated to a local intent, merchant
    connection and committed agreement version.

## 11. Observability and alerts

Capture: - PaymentIntent ID, deal ID, agreement version, merchant
connection ID; - provider request/response correlation IDs when
available; - operation duration and retry count; - normalized status
changes; - webhook verification and deduplication outcome; -
reconciliation differences; - stuck-state age and manual-intervention
reason.

Redact access tokens, bank data, personal details, invoice URLs with
sensitive tokens, and unnecessary request/response payloads. Establish
alerts for stale `CREATE_UNKNOWN`, repeated reconciliation mismatches,
webhook verification failures and unusually high duplicate-operation
rates.

## 12. Definition of done

-   One Sandbox invoice can be authorized, created, sent and paid
    end-to-end.
-   Duplicate webhook delivery is safe.
-   Create/send timeouts do not automatically cause duplicate invoices.
-   Partial/pending payment cannot become fully paid without
    reconciliation.
-   The seller merchant context is resolved and validated server-side.
-   A worker restart recovers in-progress intents.
-   Tests cover stale/mismatched amounts, invalid signatures,
    out-of-order events and provider outages.
