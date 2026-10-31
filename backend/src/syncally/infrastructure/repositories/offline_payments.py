"""Explicit demo-scoped simulated observations, never provider webhook evidence."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syncally.application.payment_processing import PaymentNeedsAction
from syncally.application.payments import OFFLINE_RECONCILIATION_EVENT_TYPE
from syncally.domain.payments.intent import (
    VerifiedProviderPaymentState,
    VerifiedProviderPaymentStatus,
)
from syncally.domain.shared.errors import DomainError
from syncally.domain.shared.money import Money, canonical_decimal
from syncally.infrastructure.demo_lifecycle import lock_demo_payment_processing
from syncally.infrastructure.models import (
    AgreementVersion,
    DemoFixture,
    Organization,
    OrganizationMember,
    OutboxEvent,
    PaymentIntent,
    User,
    WebhookEvent,
)
from syncally.infrastructure.repositories.payment_processing import _restore_domain_intent


def require_simulation_scope(db: Session, row: PaymentIntent, user_id: UUID) -> None:
    from syncally.cli.seed_demo import DEMO_IDENTITIES
    from syncally.config import settings

    if settings.app_env.lower() not in {"development", "test"} or (row.provider, row.execution_mode) != ("OFFLINE_DEMO", "OFFLINE_DEMO"):
        raise PaymentNeedsAction("PAYMENT_SIMULATION_FORBIDDEN", "Simulation requires a local offline intent.")
    marker = db.scalar(select(DemoFixture).where(
        DemoFixture.deal_id == row.deal_id,
        DemoFixture.buyer_organization_id == row.payer_organization_id,
        DemoFixture.seller_organization_id == row.seller_organization_id,
    ))
    member = db.scalar(select(User.id).join(OrganizationMember, OrganizationMember.user_id == User.id)
        .join(Organization, Organization.id == OrganizationMember.organization_id).where(
            User.id == user_id, User.email.in_([identity.email for identity in DEMO_IDENTITIES]),
            User.status == "ACTIVE", OrganizationMember.status == "ACTIVE", OrganizationMember.role == "ADMIN",
            Organization.status == "ACTIVE", Organization.id.in_((row.seller_organization_id, row.payer_organization_id))))
    agreement = db.get(AgreementVersion, row.agreement_version_id)
    if marker is None or member is None or agreement is None or agreement.deal_id != row.deal_id or agreement.status != "COMMITTED":
        raise PaymentNeedsAction("PAYMENT_SIMULATION_FORBIDDEN", "Simulation requires a marked demo agreement and current demo administrator authority.")
    if row.provider_invoice_id != f"OFFLINE-{row.id}":
        raise PaymentNeedsAction("PAYMENT_PROVIDER_REFERENCE_CONFLICT", "Simulation requires the persisted offline invoice reference.")


def simulation_state(row: PaymentIntent, payload: dict) -> VerifiedProviderPaymentState:
    try:
        state = VerifiedProviderPaymentState(
            status=VerifiedProviderPaymentStatus(payload["outcome"]),
            paid_amount=Money(Decimal(payload["paid_amount"]), payload["currency"]),
            provider_reference=row.provider_invoice_id, source="OFFLINE_DEMO",
        )
        if state.status not in {VerifiedProviderPaymentStatus.PENDING, VerifiedProviderPaymentStatus.PARTIALLY_PAID, VerifiedProviderPaymentStatus.PAID} or (state.status is VerifiedProviderPaymentStatus.PENDING and state.paid_amount.amount != 0):
            raise ValueError("Invalid simulated outcome")
        return state
    except (DomainError, ArithmeticError, ValueError, TypeError, KeyError) as error:
        raise PaymentNeedsAction("PAYMENT_RECONCILIATION_REJECTED", "Invalid simulated payment observation.") from error


def queue_simulated_reconciliation(db: Session, intent_id: UUID, *, user_id: UUID, idempotency_key: str,
                                   expected_version: int, outcome: str, paid_amount: str) -> OutboxEvent:
    try:
        lock_demo_payment_processing(db, intent_id)
        statement = select(PaymentIntent).where(PaymentIntent.id == intent_id)
        if db.get_bind().dialect.name == "postgresql":
            statement = statement.with_for_update()
        row = db.scalar(statement)
        if row is None:
            raise PaymentNeedsAction("PAYMENT_INTENT_NOT_FOUND", "Payment intent not found.")
        require_simulation_scope(db, row, user_id)
        try:
            if not isinstance(paid_amount, str) or not 1 <= len(paid_amount) <= 64:
                raise ValueError("Invalid amount representation")
            amount = Decimal(paid_amount)
            if not amount.is_finite():
                raise ValueError("Invalid amount")
            parts = amount.as_tuple()
            exponent = parts.exponent
            integer_digits = max(amount.adjusted() + 1, 1)
            representation_length = parts.sign + integer_digits + (1 - exponent if exponent < 0 else 0)
            if not -6 <= exponent <= 13 or integer_digits > 14 or representation_length > 64:
                raise ValueError("Invalid amount")
            payload = {"actor_user_id": str(user_id), "expected_version": expected_version, "outcome": outcome,
                       "paid_amount": canonical_decimal(amount), "currency": row.currency}
        except (ArithmeticError, ValueError, TypeError) as error:
            raise PaymentNeedsAction("PAYMENT_RECONCILIATION_REJECTED", "Invalid simulated payment amount.") from error
        key = f"offline:{intent_id}:{idempotency_key}"
        existing = db.scalar(select(WebhookEvent).where(WebhookEvent.provider == "OFFLINE_DEMO", WebhookEvent.provider_event_id == key))
        if existing is not None:
            if existing.payment_intent_id != intent_id or existing.raw_payload != payload:
                raise PaymentNeedsAction("PAYMENT_STATE_CHANGED", "Simulation idempotency key belongs to different evidence.")
            events = db.scalars(select(OutboxEvent).where(OutboxEvent.event_type == OFFLINE_RECONCILIATION_EVENT_TYPE, OutboxEvent.aggregate_id == intent_id))
            event = next((event for event in events if event.payload.get("webhook_event_id") == str(existing.id)), None)
            if event is None:
                raise PaymentNeedsAction("PAYMENT_RECONCILIATION_RECORD_MISSING", "Simulation command record is missing.")
            db.commit()
            return event
        if row.version != expected_version:
            raise PaymentNeedsAction("PAYMENT_STATE_CHANGED", "Payment version changed; refresh before simulation.")
        state = simulation_state(row, payload)
        if state.status not in {VerifiedProviderPaymentStatus.PENDING, VerifiedProviderPaymentStatus.PARTIALLY_PAID, VerifiedProviderPaymentStatus.PAID}:
            raise PaymentNeedsAction("PAYMENT_RECONCILIATION_REJECTED", "Simulation requires an explicit pending, partial, or paid outcome.")
        if state.status is VerifiedProviderPaymentStatus.PENDING and amount != 0:
            raise PaymentNeedsAction("PAYMENT_RECONCILIATION_REJECTED", "Pending simulation must have zero paid amount.")
        try:
            _restore_domain_intent(db, row).reconcile_provider_state(state)
        except DomainError as error:
            raise PaymentNeedsAction("PAYMENT_RECONCILIATION_REJECTED", "Simulated state conflicts with payment progress.") from error
        observation = WebhookEvent(provider="OFFLINE_DEMO", provider_event_id=key, event_type=OFFLINE_RECONCILIATION_EVENT_TYPE,
                                   payment_intent_id=intent_id, raw_payload=payload, processed=False)
        db.add(observation)
        db.flush()
        event = OutboxEvent(aggregate_type="payment_intent", aggregate_id=intent_id, event_type=OFFLINE_RECONCILIATION_EVENT_TYPE,
                            payload={"payment_intent_id": str(intent_id), "webhook_event_id": str(observation.id)}, status="PENDING", retry_count=0)
        db.add(event)
        db.commit()
        return event
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(WebhookEvent).where(WebhookEvent.provider == "OFFLINE_DEMO", WebhookEvent.provider_event_id == key))
        if existing is not None:
            return queue_simulated_reconciliation(db, intent_id, user_id=user_id, idempotency_key=idempotency_key,
                expected_version=expected_version, outcome=outcome, paid_amount=paid_amount)
        raise
    except Exception:
        db.rollback()
        raise