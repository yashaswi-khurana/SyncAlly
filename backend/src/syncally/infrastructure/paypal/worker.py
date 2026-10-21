"""Durable issuance against the S7-02 outbox; no network in DB transactions.

One leased event per intent. Claim commits before HTTP. An expired claim
recovers by reconciliation, never by repeating a potentially completed create.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4, uuid5

from sqlalchemy import or_, select, update

from syncally.application.invoicing import InvoiceClient, InvoiceFailure
from syncally.application.payments import PAYMENT_INTENT_AUTHORIZED_EVENT_TYPE
from syncally.domain.agreements.trade_terms import TradeTerms
from syncally.domain.shared.errors import InvariantViolation
from syncally.infrastructure.models import (
    AgreementVersion,
    AuditEvent,
    Deal,
    Organization,
    OrganizationMember,
    OutboxEvent,
    PaymentIntent,
    PaymentMilestone,
    User,
)

LEASE_SECONDS = 300  # Recovery interval; correctness does not require HTTP to finish in it.
MAX_ATTEMPTS = 8
ACTION_REQUIRED = "FAILED_REQUIRES_ACTION"


@dataclass(frozen=True)
class SandboxMerchant:
    seller_id: UUID
    buyer_id: UUID
    seller_email: str
    buyer_email: str

    def __post_init__(self):
        if self.seller_id == self.buyer_id or any(
            "@" not in email or len(email) > 254 for email in (self.seller_email, self.buyer_email)
        ):
            raise ValueError("Invalid Sandbox merchant binding")


def _hash(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def operation_id(intent_id, phase):
    return str(uuid5(intent_id, f"paypal-sandbox-{phase}"))


def _payload(db, intent, merchant):
    agreement = db.get(AgreementVersion, intent.agreement_version_id)
    milestone = db.get(PaymentMilestone, intent.payment_milestone_id)
    deal = db.get(Deal, intent.deal_id)
    if not agreement or not milestone or not deal:
        raise InvoiceFailure("MISSING_COMMITMENT", permanent=True)
    terms = TradeTerms.from_canonical_json(agreement.canonical_terms_json)
    terms.validate_for_commit()
    if not (
        deal.status in {"AGREED", "EXECUTING"}
        and agreement.status == "COMMITTED"
        and agreement.terms_hash == terms.terms_hash
        and agreement.deal_id == deal.id
        and deal.current_agreement_version_id == agreement.id
        and milestone.agreement_version_id == agreement.id
        and milestone.deal_id == deal.id
        and milestone.status == "PENDING"
        and milestone.sequence_number == 1
        and milestone.amount == intent.amount == terms.total.amount
        and milestone.currency == intent.currency == terms.currency == "USD"
        and milestone.payer_organization_id == intent.payer_organization_id == terms.buyer_id
        and intent.seller_organization_id
        == deal.seller_organization_id
        == terms.seller_id
        == merchant.seller_id
        and intent.payer_organization_id == deal.buyer_organization_id == merchant.buyer_id
        and intent.provider == "PAYPAL"
    ):
        raise InvoiceFailure("COMMITMENT_MISMATCH", permanent=True)
    for org_id in (merchant.seller_id, merchant.buyer_id):
        org = db.get(Organization, org_id)
        if not org or org.status != "ACTIVE":
            raise InvoiceFailure("INACTIVE_PARTY", permanent=True)
    item = terms.line_items[0]
    # Never silently round the agreed obligation to fit PayPal USD precision.
    if any(
        value != value.quantize(Decimal("0.01"))
        for value in (intent.amount, item.unit_price.amount)
    ):
        raise InvoiceFailure("UNSUPPORTED_USD_PRECISION", permanent=True)
    return {
        "detail": {
            "invoice_number": "SA-" + intent.id.hex[:22],
            "reference": str(intent.id),
            "currency_code": intent.currency,
            "payment_term": {"term_type": "DUE_ON_RECEIPT"},
        },
        "invoicer": {"email_address": merchant.seller_email},
        "primary_recipients": [{"billing_info": {"email_address": merchant.buyer_email}}],
        "items": [
            {
                "name": item.description,
                "quantity": str(item.quantity),
                "unit_amount": {
                    "currency_code": intent.currency,
                    "value": format(item.unit_price.amount, ".2f"),
                },
            }
        ],
        "configuration": {"allow_tip": False, "partial_payment": {"allow_partial_payment": False}},
    }


def _require_seller(db, seller_id, user_id):
    active = db.scalar(
        select(OrganizationMember.id)
        .join(User)
        .where(
            OrganizationMember.organization_id == seller_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.status == "ACTIVE",
            User.status == "ACTIVE",
        )
    )
    if not active:
        raise InvoiceFailure("SELLER_AUTHORITY_REQUIRED", permanent=True)


def authorize_sandbox_issuance(session_factory, intent_id, seller_user_id, merchant):
    """Trusted operator seam pending #33's authenticated seller command/API.

    Verify the named seller actor's active membership, then freeze the exact
    server-derived request and record an audit. Never grants authority from
    browser IDs. Replays cannot alter the authorized request or operation IDs.
    """
    with session_factory() as db, db.begin():
        event = db.scalar(
            select(OutboxEvent)
            .where(
                OutboxEvent.aggregate_id == intent_id,
                OutboxEvent.event_type == PAYMENT_INTENT_AUTHORIZED_EVENT_TYPE,
            )
            .with_for_update()
        )
        intent = db.scalar(
            select(PaymentIntent).where(PaymentIntent.id == intent_id).with_for_update()
        )
        if not intent or intent.status != "AUTHORIZED":
            raise InvoiceFailure("INTENT_NOT_AUTHORIZABLE", permanent=True)
        _require_seller(db, merchant.seller_id, seller_user_id)
        payload = _payload(db, intent, merchant)
        if not event or event.status != "PENDING":
            raise InvoiceFailure("DISPATCH_NOT_AUTHORIZABLE", permanent=True)
        digest = _hash(payload)
        if "issuance" in event.payload:
            if intent.request_payload_hash != digest:
                raise InvoiceFailure("AUTHORIZATION_CHANGED", permanent=True)
            return
        event.payload = {
            **event.payload,
            "issuance": {
                "request": payload,
                "seller_user_id": str(seller_user_id),
                "create_operation_id": operation_id(intent.id, "create"),
                "send_operation_id": operation_id(intent.id, "send"),
            },
        }
        intent.request_payload_hash = digest
        intent.version += 1
        db.add(
            AuditEvent(
                aggregate_type="payment_intent",
                aggregate_id=intent.id,
                event_type="SANDBOX_INVOICE_ISSUANCE_AUTHORIZED",
                actor_type="USER",
                actor_id=str(seller_user_id),
                occurred_at=datetime.now(UTC),
                payload={"request_payload_hash": digest},
            )
        )


@dataclass(frozen=True)
class Work:
    event_id: UUID
    token: str
    intent_id: UUID
    version: int
    phase: str
    request: dict
    invoice_id: str | None


def _claim(session_factory, merchant, now):
    with session_factory() as db, db.begin():
        event = db.scalar(
            select(OutboxEvent)
            .where(
                OutboxEvent.event_type == PAYMENT_INTENT_AUTHORIZED_EVENT_TYPE,
                OutboxEvent.status.in_(["PENDING", "PROCESSING"]),
                or_(OutboxEvent.next_attempt_at.is_(None), OutboxEvent.next_attempt_at <= now),
            )
            .order_by(OutboxEvent.created_at, OutboxEvent.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if event is None:
            return None
        # CAS also guards SQLite tests, where SELECT FOR UPDATE is ignored.
        claimed = db.execute(
            update(OutboxEvent)
            .where(
                OutboxEvent.id == event.id,
                OutboxEvent.status == event.status,
                OutboxEvent.retry_count == event.retry_count,
            )
            .values(
                status="PROCESSING",
                retry_count=event.retry_count + 1,
                next_attempt_at=now + timedelta(seconds=LEASE_SECONDS),
            )
        )
        if claimed.rowcount != 1:
            return None
        intent = db.scalar(
            select(PaymentIntent).where(PaymentIntent.id == event.aggregate_id).with_for_update()
        )
        try:
            issuance = event.payload.get("issuance")
            if intent and intent.status in {"SENT", "PARTIALLY_PAID", "PAID", "CANCELLED"}:
                event.status = "DELIVERED"
                event.delivered_at = now
                event.next_attempt_at = None
                return True
            if not intent or not issuance:
                raise InvoiceFailure("SELLER_ISSUANCE_AUTHORIZATION_REQUIRED", permanent=True)
            if intent.status == ACTION_REQUIRED:
                raise InvoiceFailure("MANUAL_REVIEW_REQUIRED", permanent=True)
            _require_seller(db, merchant.seller_id, UUID(issuance["seller_user_id"]))
            request = _payload(db, intent, merchant)
            if _hash(request) != intent.request_payload_hash or request != issuance["request"]:
                raise InvoiceFailure("AUTHORIZED_REQUEST_CHANGED", permanent=True)
            if event.retry_count > MAX_ATTEMPTS:
                raise InvoiceFailure("RETRY_BUDGET_EXHAUSTED", permanent=True)
            if intent.status not in {
                "AUTHORIZED",
                "CREATE_PENDING",
                "CREATE_UNKNOWN",
                "PROVIDER_CREATED",
                "SEND_PENDING",
                "SEND_UNKNOWN",
            }:
                raise InvoiceFailure("INTENT_STATE_REQUIRES_REVIEW", permanent=True)
            phase = (
                "create"
                if intent.status == "AUTHORIZED" and not intent.provider_invoice_id
                else "reconcile"
            )
            # Persist unknown BEFORE entering HTTP. A hard crash is ambiguous
            # too, even if the worker never receives a timeout exception.
            if phase == "create" or not intent.provider_invoice_id:
                intent.status = "CREATE_UNKNOWN"
            else:
                intent.status = "SEND_UNKNOWN"
            token = str(uuid4())
            event.payload = {**event.payload, "claim_token": token}
            intent.version += 1
            return Work(
                event.id,
                token,
                intent.id,
                intent.version,
                phase,
                request,
                intent.provider_invoice_id,
            )
        except (
            InvoiceFailure,
            InvariantViolation,
            KeyError,
            TypeError,
            ValueError,
            AttributeError,
            ArithmeticError,
        ) as error:
            _manual(
                event,
                intent,
                error.code if isinstance(error, InvoiceFailure) else "INVALID_COMMITMENT",
            )
            return True


def _manual(event, intent, code):
    event.status = "FAILED"
    event.error_detail = code
    event.next_attempt_at = None
    if intent:
        intent.status = ACTION_REQUIRED
        intent.failure_code = code
        intent.failure_detail = "Operator review required; reconcile with PayPal before resuming."
        intent.version += 1


def _validate(evidence, work):
    request = work.request
    total = sum(
        Decimal(item["quantity"]) * Decimal(item["unit_amount"]["value"])
        for item in request["items"]
    )
    if not (
        evidence.id
        and (not work.invoice_id or evidence.id == work.invoice_id)
        and evidence.number == request["detail"]["invoice_number"]
        and evidence.reference == request["detail"]["reference"]
        and evidence.currency == request["detail"]["currency_code"]
        and evidence.amount == total
        and evidence.seller_email.casefold() == request["invoicer"]["email_address"].casefold()
        and evidence.recipient_email.casefold()
        == request["primary_recipients"][0]["billing_info"]["email_address"].casefold()
    ):
        raise InvoiceFailure("PROVIDER_INVOICE_MISMATCH", permanent=True)


def dispatch_one_payment(session_factory, client: InvoiceClient, merchant, *, now=None):
    now = now or datetime.now(UTC)
    work = _claim(session_factory, merchant, now)
    if not isinstance(work, Work):
        return bool(work)
    invoice_id = work.invoice_id
    status = "CREATE_UNKNOWN" if not invoice_id else "SEND_UNKNOWN"
    error = None
    try:
        if work.phase == "create":
            invoice_id = client.create(work.request, operation_id(work.intent_id, "create"))
            # Create acknowledgment alone does not validate the draft.
            status = "PROVIDER_CREATED"
        else:
            if invoice_id:
                evidence = client.get(invoice_id)
            else:
                matches = client.find(work.request["detail"]["invoice_number"])
                if len(matches) != 1:
                    raise InvoiceFailure("CREATE_OUTCOME_UNRESOLVED", permanent=len(matches) > 1)
                evidence = matches[0]
            _validate(evidence, work)
            invoice_id = evidence.id
            if evidence.status == "DRAFT" and not work.invoice_id:
                # Recover creation durably before beginning the separate send.
                status = "PROVIDER_CREATED"
            elif evidence.status == "DRAFT":
                # Draft was fetched/validated immediately before send. Send's
                # response only queues another GET, never marks SENT/PAID.
                client.send(invoice_id, operation_id(work.intent_id, "send"))
                status = "SEND_UNKNOWN"
            elif evidence.status in {
                "SENT",
                "SCHEDULED",
                "UNPAID",
                "PAYMENT_PENDING",
                "PARTIALLY_PAID",
                "PAID",
                "MARKED_AS_PAID",
            }:
                status = "SENT"  # Settlement belongs to #36; never set PAID here.
            else:
                raise InvoiceFailure("PROVIDER_STATUS_REQUIRES_REVIEW", permanent=True)
    except InvoiceFailure as failure:
        error = failure
        if work.phase == "create" and not failure.ambiguous and not failure.permanent:
            status = "AUTHORIZED"  # Explicit rejection before mutation (e.g. 429).
    # Unexpected exceptions deliberately leave the lease and unknown state in
    # place. Restart must reconcile; never assume a mutation did not happen.
    with session_factory() as db, db.begin():
        event = db.scalar(
            select(OutboxEvent).where(OutboxEvent.id == work.event_id).with_for_update()
        )
        intent = db.scalar(
            select(PaymentIntent).where(PaymentIntent.id == work.intent_id).with_for_update()
        )
        if event.payload.get("claim_token") != work.token or intent.version != work.version:
            return True  # Stale worker cannot overwrite a newer command/claim.
        intent.provider_invoice_id = invoice_id
        if work.phase == "reconcile":
            intent.last_checked_at = now
        if error and (error.permanent or event.retry_count >= MAX_ATTEMPTS):
            _manual(event, intent, error.code)
        else:
            intent.status = status
            intent.version += 1
            intent.failure_code = error.code if error else None
            event.error_detail = error.code if error else None
            event.status = "DELIVERED" if status == "SENT" else "PENDING"
            event.delivered_at = now if status == "SENT" else None
            event.next_attempt_at = (
                None
                if status == "SENT"
                else now + timedelta(seconds=min(300, 2**event.retry_count))
            )
        db.add(
            AuditEvent(
                aggregate_type="payment_intent",
                aggregate_id=intent.id,
                event_type="SANDBOX_INVOICE_WORK_CHECKED",
                actor_type="SYSTEM",
                actor_id="payment_worker",
                occurred_at=now,
                payload={"status": intent.status, "failure_code": intent.failure_code},
            )
        )
    return True
