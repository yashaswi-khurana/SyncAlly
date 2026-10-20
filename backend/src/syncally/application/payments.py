"""Persist an authorized payment intent and its outbox hand-off atomically.

This is the persistence boundary only: no PayPal call happens here or in the
transaction that wraps it (see ``infrastructure/repositories/payments.py``).
A later worker (S7-03) reads the outbox row this writes and talks to PayPal;
reconciling its response back onto the intent is a separate concern too.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from syncally.application.agreements import OutboxEventDraft, OutboxRepository
from syncally.domain.shared.errors import DomainError
from syncally.domain.shared.money import Money


class DuplicateActivePaymentIntent(DomainError):
    """Another non-terminal payment intent already exists for this milestone."""


@dataclass(frozen=True)
class AuthorizePaymentIntentCommand:
    """Input for persisting one newly authorized payment intent."""

    id: UUID
    deal_id: UUID
    agreement_version_id: UUID
    payment_milestone_id: UUID
    seller_organization_id: UUID
    payer_organization_id: UUID
    authorized_by: UUID
    amount: Money
    idempotency_key: str


class PaymentIntentRepository(Protocol):
    """Persistence port for authorizing one payment intent.

    The adapter owns the one-active-intent-per-milestone invariant: it must
    raise ``DuplicateActivePaymentIntent`` rather than persist a second
    non-terminal intent for the same ``payment_milestone_id``.
    """

    def add(self, command: AuthorizePaymentIntentCommand, *, now: datetime) -> None:
        """Persist one newly authorized payment intent."""


def authorize_payment_intent(
    command: AuthorizePaymentIntentCommand,
    repository: PaymentIntentRepository,
    outbox_repository: OutboxRepository,
    *,
    now: datetime | None = None,
) -> None:
    """Save the intent and its outbox dispatch event through one caller-owned transaction."""
    now = now or datetime.now(UTC)
    repository.add(command, now=now)
    outbox_repository.add(
        OutboxEventDraft(
            aggregate_type="payment_intent",
            aggregate_id=command.id,
            event_type="PAYMENT_INTENT_AUTHORIZED",
            payload={
                "payment_intent_id": str(command.id),
                "deal_id": str(command.deal_id),
                "agreement_version_id": str(command.agreement_version_id),
                "payment_milestone_id": str(command.payment_milestone_id),
            },
        )
    )
