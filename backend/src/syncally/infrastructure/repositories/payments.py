"""SQLAlchemy persistence for authorized payment intents.

Mirrors the crash-safety shape of ``repositories.agreements``: the intent row
and its outbox row are written in one caller-owned transaction, and the
one-active-intent-per-milestone invariant is enforced by a database
constraint (``ix_payment_intents_one_active_per_milestone``) rather than a
check-then-insert race. No PayPal call happens anywhere in this module.

``add`` flushes directly rather than inside ``begin_nested()``: every error
path here rolls back the whole caller-owned transaction (see
``authorize_payment_intent_in_transaction``) rather than continuing it, so no
savepoint is needed to isolate the failed insert.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syncally.application.payments import (
    AuthorizePaymentIntentCommand,
    DuplicateActivePaymentIntent,
    authorize_payment_intent,
)
from syncally.infrastructure.models import PaymentIntent
from syncally.infrastructure.repositories.agreements import SqlAlchemyOutboxRepository

_PAYMENT_INTENT_AUTHORIZED_STATUS = "AUTHORIZED"


class SqlAlchemyPaymentIntentRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, command: AuthorizePaymentIntentCommand, *, now: datetime) -> None:
        try:
            self._db.add(
                PaymentIntent(
                    id=command.id,
                    deal_id=command.deal_id,
                    agreement_version_id=command.agreement_version_id,
                    payment_milestone_id=command.payment_milestone_id,
                    seller_organization_id=command.seller_organization_id,
                    payer_organization_id=command.payer_organization_id,
                    authorized_by=command.authorized_by,
                    amount=command.amount.amount,
                    currency=command.amount.currency,
                    status=_PAYMENT_INTENT_AUTHORIZED_STATUS,
                    idempotency_key=command.idempotency_key,
                    version=0,
                    created_at=now,
                )
            )
            self._db.flush()
        except IntegrityError as error:
            raise DuplicateActivePaymentIntent(
                "An active payment intent already exists for this milestone"
            ) from error


def authorize_payment_intent_in_transaction(
    db: Session,
    command: AuthorizePaymentIntentCommand,
    *,
    now: datetime | None = None,
) -> None:
    """Run AuthorizePaymentIntent as one transaction: commits on success, rolls back on failure.

    The intent row and its ``PAYMENT_INTENT_AUTHORIZED`` outbox row are saved
    together or not at all, so a crash between them cannot happen.
    """
    now = now or datetime.now(UTC)
    try:
        authorize_payment_intent(
            command,
            SqlAlchemyPaymentIntentRepository(db),
            SqlAlchemyOutboxRepository(db),
            now=now,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
