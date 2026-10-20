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


class PaymentMilestoneNotFound(DomainError):
    """The command's ``payment_milestone_id`` does not reference a real milestone."""


class PaymentIntentCommandMismatch(DomainError):
    """The command's deal/agreement/org/amount fields disagree with the milestone on record."""


class UnauthorizedPaymentAuthorization(DomainError):
    """``authorized_by`` is not an active member of the payer organization."""


class IdempotencyKeyReused(DomainError):
    """The idempotency key already belongs to a different payment authorization."""


PAYMENT_INTENT_AUTHORIZED_EVENT_TYPE = "PAYMENT_INTENT_AUTHORIZED"


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


@dataclass(frozen=True, slots=True)
class PaymentIntentAuthorizationOutcome:
    """What ended up on record for this command.

    ``already_existed`` is true only for a lost-acknowledgement retry: the
    exact same authorization (matched by idempotency key) was already
    committed by an earlier call, and ``intent_id`` is *that* row's id -
    which may differ from ``command.id`` when the caller generates a fresh
    id per attempt but keeps the idempotency key stable.
    """

    intent_id: UUID
    already_existed: bool


class PaymentIntentRepository(Protocol):
    """Persistence port for authorizing one payment intent.

    The adapter owns the one-active-intent-per-milestone invariant: it must
    raise ``DuplicateActivePaymentIntent`` rather than persist a second
    non-terminal intent for the same ``payment_milestone_id``. It also owns
    idempotent replay: a retry with the same idempotency key as an already-
    committed authorization must return that row's outcome rather than raise.
    """

    def add(
        self, command: AuthorizePaymentIntentCommand, *, now: datetime
    ) -> PaymentIntentAuthorizationOutcome:
        """Persist one newly authorized payment intent."""


def authorize_payment_intent(
    command: AuthorizePaymentIntentCommand,
    repository: PaymentIntentRepository,
    outbox_repository: OutboxRepository,
    *,
    now: datetime | None = None,
) -> PaymentIntentAuthorizationOutcome:
    """Save the intent and its outbox dispatch event through one caller-owned transaction.

    A replay (``already_existed``) skips the outbox write: the original call
    already queued that dispatch, and this one has nothing new to report.
    """
    now = now or datetime.now(UTC)
    outcome = repository.add(command, now=now)
    if outcome.already_existed:
        return outcome
    outbox_repository.add(
        OutboxEventDraft(
            aggregate_type="payment_intent",
            aggregate_id=outcome.intent_id,
            event_type=PAYMENT_INTENT_AUTHORIZED_EVENT_TYPE,
            payload={
                "payment_intent_id": str(outcome.intent_id),
                "deal_id": str(command.deal_id),
                "agreement_version_id": str(command.agreement_version_id),
                "payment_milestone_id": str(command.payment_milestone_id),
            },
        )
    )
    return outcome
