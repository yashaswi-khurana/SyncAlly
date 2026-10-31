"""Shared locking and pending-state guard for onboarding and commercial writers."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from syncally.infrastructure.models import CounterpartyOnboarding, Deal


def lock_deal(db: Session, deal_id: UUID, *, shared: bool = False) -> Deal | None:
    if db.get_bind().dialect.name == "sqlite":
        db.execute(update(Deal).where(Deal.id == deal_id).values(version=Deal.version))
    return db.scalar(
        select(Deal).where(Deal.id == deal_id).with_for_update(read=shared)
        .execution_options(populate_existing=True)
    )


def is_pending(db: Session, deal_id: UUID) -> bool:
    return db.scalar(
        select(CounterpartyOnboarding.invitation_jti).where(
            CounterpartyOnboarding.deal_id == deal_id,
            CounterpartyOnboarding.consumed_at.is_(None),
        )
    ) is not None