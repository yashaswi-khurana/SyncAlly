"""Authorized payment intent with explicit ambiguous-outcome reconciliation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from syncally.domain.shared.errors import InvalidTransition, InvariantViolation
from syncally.domain.shared.identifiers import (
    AgreementVersionId,
    DealId,
    OrganizationId,
    PaymentIntentId,
    PaymentMilestoneId,
    UserId,
)
from syncally.domain.shared.money import Money


class PaymentExecutionMode(StrEnum):
    PAYPAL_SANDBOX = "PAYPAL_SANDBOX"
    OFFLINE_DEMO = "OFFLINE_DEMO"
    LEGACY_UNRESOLVED = "LEGACY_UNRESOLVED"

    @property
    def provider(self) -> str:
        if self is PaymentExecutionMode.LEGACY_UNRESOLVED:
            raise InvariantViolation("Unresolved payment provenance cannot authorize payments")
        return "PAYPAL" if self is PaymentExecutionMode.PAYPAL_SANDBOX else "OFFLINE_DEMO"


class PaymentIntentStatus(StrEnum):
    AUTHORIZED = "AUTHORIZED"
    CREATE_PENDING = "CREATE_PENDING"
    CREATE_UNKNOWN = "CREATE_UNKNOWN"
    PROVIDER_CREATED = "PROVIDER_CREATED"
    SENT = "SENT"
    PENDING = "PENDING"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    @property
    def is_terminal(self) -> bool:
        return self in {
            PaymentIntentStatus.PAID,
            PaymentIntentStatus.FAILED,
            PaymentIntentStatus.CANCELLED,
        }


class VerifiedProviderPaymentStatus(StrEnum):
    """Normalized result of an authenticated provider status lookup."""

    UNKNOWN = "UNKNOWN"
    NOT_FOUND = "NOT_FOUND"
    PENDING = "PENDING"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"


@dataclass(frozen=True, slots=True)
class PaymentMilestone:
    id: PaymentMilestoneId
    deal_id: DealId
    agreement_version_id: AgreementVersionId
    sequence_number: int
    payer_organization_id: OrganizationId
    amount: Money
    trigger: str
    due_condition: str

    def __post_init__(self) -> None:
        if self.sequence_number < 1 or self.amount.amount <= 0:
            raise InvariantViolation("Payment milestone must have a positive sequence and amount")
        if not self.trigger.strip() or not self.due_condition.strip():
            raise InvariantViolation("Payment milestone needs a trigger and due condition")


@dataclass(frozen=True, slots=True)
class VerifiedProviderPaymentState:
    """Provider status and amount returned by an authenticated status check.

    Provider adapters should construct this value only after checking the
    provider's current invoice/payment state. Webhook payloads and browser
    redirects alone are not this evidence.
    """

    status: VerifiedProviderPaymentStatus
    paid_amount: Money
    provider_reference: str | None = None
    source: str = "PAYPAL_SANDBOX"

    def __post_init__(self) -> None:
        if not isinstance(self.status, VerifiedProviderPaymentStatus):
            raise InvariantViolation("Provider payment state must use a normalized status")
        if self.source not in {"PAYPAL_SANDBOX", "OFFLINE_DEMO"}:
            raise InvariantViolation("Payment evidence needs an explicit source")
        if not isinstance(self.paid_amount, Money):
            raise InvariantViolation("Provider payment state must use a Money amount")
        if self.provider_reference is not None and not isinstance(self.provider_reference, str):
            raise InvariantViolation("Provider reference must be text")


@dataclass(slots=True)
class PaymentIntent:
    id: PaymentIntentId
    milestone: PaymentMilestone
    seller_organization_id: OrganizationId
    payer_organization_id: OrganizationId
    authorized_by: UserId
    idempotency_key: str
    created_at: datetime
    provider_reference: str | None = None
    reconciled_amount: Money | None = None
    _status: PaymentIntentStatus = field(
        default=PaymentIntentStatus.AUTHORIZED, init=False, repr=False
    )

    @property
    def status(self) -> PaymentIntentStatus:
        """Read-only state; transitions must pass through domain methods."""
        return self._status

    def __post_init__(self) -> None:
        if not self.idempotency_key.strip():
            raise InvariantViolation("Payment intent requires an idempotency key")
        if self.payer_organization_id != self.milestone.payer_organization_id:
            raise InvariantViolation("Payment intent payer differs from the milestone payer")
        if self.seller_organization_id == self.payer_organization_id:
            raise InvariantViolation("Payment intent seller and payer must differ")

    @classmethod
    def restore(
        cls,
        *,
        id: PaymentIntentId,
        milestone: PaymentMilestone,
        seller_organization_id: OrganizationId,
        payer_organization_id: OrganizationId,
        authorized_by: UserId,
        idempotency_key: str,
        created_at: datetime,
        status: PaymentIntentStatus,
        provider_reference: str | None = None,
        reconciled_amount: Money | None = None,
    ) -> PaymentIntent:
        """Rehydrate a persisted intent before applying a state transition."""
        intent = cls(
            id=id,
            milestone=milestone,
            seller_organization_id=seller_organization_id,
            payer_organization_id=payer_organization_id,
            authorized_by=authorized_by,
            idempotency_key=idempotency_key,
            created_at=created_at,
            provider_reference=provider_reference,
            reconciled_amount=reconciled_amount,
        )
        intent._status = PaymentIntentStatus(status)
        return intent

    def begin_create(self) -> None:
        if self.status is PaymentIntentStatus.CREATE_UNKNOWN:
            raise InvalidTransition("Reconcile the unknown provider outcome before retrying")
        if self.status is not PaymentIntentStatus.AUTHORIZED:
            raise InvalidTransition(f"Cannot create provider request from {self.status}")
        self._status = PaymentIntentStatus.CREATE_PENDING

    def record_create_unknown(self) -> None:
        if self.status is not PaymentIntentStatus.CREATE_PENDING:
            raise InvalidTransition("Only a pending provider create can become unknown")
        self._status = PaymentIntentStatus.CREATE_UNKNOWN

    def record_provider_created(self, provider_reference: str) -> None:
        if self.status not in {
            PaymentIntentStatus.CREATE_PENDING,
            PaymentIntentStatus.CREATE_UNKNOWN,
        }:
            raise InvalidTransition("Provider creation requires a pending or reconciled create")
        if not provider_reference.strip():
            raise InvariantViolation("Provider reference is required")
        self.provider_reference = provider_reference
        self._status = PaymentIntentStatus.PROVIDER_CREATED

    def mark_failed(self) -> None:
        if self.status not in {
            PaymentIntentStatus.AUTHORIZED,
            PaymentIntentStatus.CREATE_PENDING,
        }:
            raise InvalidTransition(f"Cannot mark a payment failed from {self.status}")
        self._status = PaymentIntentStatus.FAILED

    def mark_sent(self) -> None:
        if self.status is not PaymentIntentStatus.PROVIDER_CREATED:
            raise InvalidTransition("Only a provider-created request can be sent")
        self._status = PaymentIntentStatus.SENT

    def reconcile_provider_state(
        self,
        state: VerifiedProviderPaymentState,
    ) -> None:
        allowed = {
            PaymentIntentStatus.CREATE_UNKNOWN,
            PaymentIntentStatus.PROVIDER_CREATED,
            PaymentIntentStatus.SENT,
            PaymentIntentStatus.PENDING,
            PaymentIntentStatus.PARTIALLY_PAID,
        }
        if self.status not in allowed:
            raise InvalidTransition(f"Cannot reconcile provider state from {self.status}")
        paid_amount = state.paid_amount
        if paid_amount.currency != self.milestone.amount.currency:
            raise InvariantViolation("Reconciled payment currency differs from the milestone")
        if paid_amount.amount < 0 or paid_amount.amount > self.milestone.amount.amount:
            raise InvariantViolation("Reconciled payment amount is outside the milestone amount")
        if (
            self.reconciled_amount is not None
            and paid_amount.amount < self.reconciled_amount.amount
        ):
            raise InvalidTransition("Reconciliation cannot reduce recorded payment progress")

        if (
            self.provider_reference is not None
            and state.provider_reference is not None
            and state.provider_reference != self.provider_reference
        ):
            raise InvalidTransition("Reconciliation references a different provider request")

        if state.status is VerifiedProviderPaymentStatus.UNKNOWN:
            return
        if state.status is VerifiedProviderPaymentStatus.NOT_FOUND:
            if (
                self.status is not PaymentIntentStatus.CREATE_UNKNOWN
                or state.provider_reference is not None
                or paid_amount.amount != 0
            ):
                raise InvalidTransition(
                    "Only an unknown create with a verified not-found result can be retried"
                )
            self.reconciled_amount = paid_amount
            self._status = PaymentIntentStatus.AUTHORIZED
            return

        if not state.provider_reference or not state.provider_reference.strip():
            raise InvariantViolation("Verified provider state requires a provider reference")
        if state.status is VerifiedProviderPaymentStatus.PAID:
            if paid_amount.amount != self.milestone.amount.amount:
                raise InvariantViolation("Provider-paid amount must equal the milestone amount")
        elif state.status is VerifiedProviderPaymentStatus.PARTIALLY_PAID:
            if paid_amount.amount <= 0 or paid_amount.amount >= self.milestone.amount.amount:
                raise InvariantViolation("Partial payment must be greater than zero and below the milestone")
        self.provider_reference = state.provider_reference
        self.reconciled_amount = paid_amount
        if state.status is VerifiedProviderPaymentStatus.PAID:
            self._status = PaymentIntentStatus.PAID
        elif state.status is VerifiedProviderPaymentStatus.PARTIALLY_PAID:
            self._status = PaymentIntentStatus.PARTIALLY_PAID
        elif state.status is VerifiedProviderPaymentStatus.PENDING:
            self._status = PaymentIntentStatus.PENDING
        else:
            raise InvariantViolation(f"Unsupported verified provider status: {state.status}")
