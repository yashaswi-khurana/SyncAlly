"""Authorized payment intent with explicit ambiguous-outcome reconciliation."""

from dataclasses import dataclass
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


class PaymentIntentStatus(StrEnum):
    AUTHORIZED = "AUTHORIZED"
    CREATE_PENDING = "CREATE_PENDING"
    CREATE_UNKNOWN = "CREATE_UNKNOWN"
    PROVIDER_CREATED = "PROVIDER_CREATED"
    SENT = "SENT"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


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


@dataclass(slots=True)
class PaymentIntent:
    id: PaymentIntentId
    milestone: PaymentMilestone
    payer_organization_id: OrganizationId
    authorized_by: UserId
    idempotency_key: str
    created_at: datetime
    status: PaymentIntentStatus = PaymentIntentStatus.AUTHORIZED
    provider_reference: str | None = None
    reconciled_amount: Money | None = None

    def __post_init__(self) -> None:
        if not self.idempotency_key.strip():
            raise InvariantViolation("Payment intent requires an idempotency key")
        if self.payer_organization_id != self.milestone.payer_organization_id:
            raise InvariantViolation("Payment intent payer differs from the milestone payer")

    def begin_create(self) -> None:
        if self.status is PaymentIntentStatus.CREATE_UNKNOWN:
            raise InvalidTransition("Reconcile the unknown provider outcome before retrying")
        if self.status is not PaymentIntentStatus.AUTHORIZED:
            raise InvalidTransition(f"Cannot create provider request from {self.status}")
        self.status = PaymentIntentStatus.CREATE_PENDING

    def record_create_unknown(self) -> None:
        if self.status is not PaymentIntentStatus.CREATE_PENDING:
            raise InvalidTransition("Only a pending provider create can become unknown")
        self.status = PaymentIntentStatus.CREATE_UNKNOWN

    def record_provider_created(self, provider_reference: str) -> None:
        if self.status is not PaymentIntentStatus.CREATE_PENDING:
            raise InvalidTransition("Provider creation requires a pending create")
        if not provider_reference.strip():
            raise InvariantViolation("Provider reference is required")
        self.provider_reference = provider_reference
        self.status = PaymentIntentStatus.PROVIDER_CREATED

    def mark_sent(self) -> None:
        if self.status is not PaymentIntentStatus.PROVIDER_CREATED:
            raise InvalidTransition("Only a provider-created request can be sent")
        self.status = PaymentIntentStatus.SENT

    def reconcile_provider_state(
        self,
        *,
        provider_reference: str | None,
        paid_amount: Money,
    ) -> None:
        allowed = {
            PaymentIntentStatus.CREATE_UNKNOWN,
            PaymentIntentStatus.PROVIDER_CREATED,
            PaymentIntentStatus.SENT,
            PaymentIntentStatus.PARTIALLY_PAID,
        }
        if self.status not in allowed:
            raise InvalidTransition(f"Cannot reconcile provider state from {self.status}")
        if paid_amount.currency != self.milestone.amount.currency:
            raise InvariantViolation("Reconciled payment currency differs from the milestone")
        if paid_amount.amount < 0 or paid_amount.amount > self.milestone.amount.amount:
            raise InvariantViolation("Reconciled payment amount is outside the milestone amount")
        if (
            self.reconciled_amount is not None
            and paid_amount.amount < self.reconciled_amount.amount
        ):
            raise InvalidTransition("Reconciliation cannot reduce recorded payment progress")
        self.provider_reference = provider_reference or self.provider_reference
        self.reconciled_amount = paid_amount
        if paid_amount.amount == self.milestone.amount.amount:
            self.status = PaymentIntentStatus.PAID
        elif paid_amount.amount > 0:
            self.status = PaymentIntentStatus.PARTIALLY_PAID
        elif self.provider_reference:
            self.status = PaymentIntentStatus.PROVIDER_CREATED
        else:
            # A definitive provider lookup established that the request was not created.
            self.status = PaymentIntentStatus.AUTHORIZED
