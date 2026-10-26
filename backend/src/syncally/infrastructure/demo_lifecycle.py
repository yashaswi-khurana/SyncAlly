"""Database coordination for destructive demo resets and in-flight work."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from syncally.infrastructure.models import Deal, Organization, PaymentIntent

_DEMO_LOCK_ID = 0x53594E43414C4C59
_DEMO_ORGANIZATIONS = ("Demo Buyer Co", "Demo Seller Co")


def _is_demo_deal(
    db: Session, buyer_organization_id: UUID, seller_organization_id: UUID
) -> bool:
    organization_ids = set(
        db.scalars(
            select(Organization.id).where(
                Organization.id.in_(
                    (buyer_organization_id, seller_organization_id)
                ),
                Organization.legal_name.in_(_DEMO_ORGANIZATIONS),
                Organization.country_code == "US",
            )
        )
    )
    return organization_ids == {
        buyer_organization_id,
        seller_organization_id,
    }


def _acquire_lock(db: Session) -> None:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        # Transaction-scoped so closing/committing the owner session releases it.
        db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": _DEMO_LOCK_ID})


def lock_demo_deal_creation(
    db: Session, buyer_organization_id: UUID, seller_organization_id: UUID
) -> None:
    """Serialize creation of in-scope demo deals with reset_demo."""
    if _is_demo_deal(db, buyer_organization_id, seller_organization_id):
        _acquire_lock(db)


def lock_demo_payment_processing(db: Session, payment_intent_id: UUID) -> None:
    """Keep reset_demo from deleting an intent during its provider operation."""
    deal = db.scalar(
        select(Deal)
        .join(PaymentIntent, PaymentIntent.deal_id == Deal.id)
        .where(PaymentIntent.id == payment_intent_id)
    )
    if deal is not None and _is_demo_deal(
        db, deal.buyer_organization_id, deal.seller_organization_id
    ):
        _acquire_lock(db)


def lock_demo_reset(db: Session) -> None:
    """Serialize a reset against demo deal creation and payment processing."""
    _acquire_lock(db)
