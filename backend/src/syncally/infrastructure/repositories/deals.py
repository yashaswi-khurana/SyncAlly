"""SQLAlchemy implementation of the deal repository port.

Rows are translated to and from the framework-independent domain aggregate here so
business rules and the API never depend on ORM entities.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from syncally.application.workflow_notifications import NotificationKind
from syncally.domain.deals.deal import Deal as DomainDeal
from syncally.domain.deals.deal import DealStatus
from syncally.domain.shared.identifiers import AgreementVersionId, DealId, OrganizationId
from syncally.infrastructure.models import Deal, Organization, OrganizationMember, User
from syncally.infrastructure.repositories._timestamps import as_utc
from syncally.infrastructure.workflow_notifications import queue_deal_workflow_notification


def _to_domain(row: Deal) -> DomainDeal:
    return DomainDeal(
        id=DealId(row.id),
        buyer_organization_id=OrganizationId(row.buyer_organization_id),
        seller_organization_id=OrganizationId(row.seller_organization_id),
        created_at=as_utc(row.created_at),
        status=DealStatus(row.status),
        current_agreement_version_id=(
            AgreementVersionId(row.current_agreement_version_id)
            if row.current_agreement_version_id is not None
            else None
        ),
        version=row.version,
        pending_counterparty=row.onboarding is not None and row.onboarding.consumed_at is None,
    )


def _active_participation(user_id: UUID):
    """Correlate a deal with an active membership the user holds in either party."""
    return exists(
        select(OrganizationMember.id)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .join(User, User.id == OrganizationMember.user_id)
        .where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.status == "ACTIVE",
            Organization.status == "ACTIVE",
            User.status == "ACTIVE",
            or_(
                OrganizationMember.organization_id == Deal.buyer_organization_id,
                OrganizationMember.organization_id == Deal.seller_organization_id,
            ),
        )
    )


class SqlAlchemyDealRepository:
    """Deal repository backed by a SQLAlchemy session."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def active_organization_exists(self, organization_id: UUID) -> bool:
        return (
            self._db.scalar(
                select(Organization.id).where(
                    Organization.id == organization_id,
                    Organization.status == "ACTIVE",
                )
            )
            is not None
        )

    def add(self, deal: DomainDeal) -> DomainDeal:
        row = self.stage(deal)
        self._db.commit()
        self._db.refresh(row)
        return _to_domain(row)

    def stage(self, deal: DomainDeal) -> Deal:
        row = Deal(
            id=deal.id,
            buyer_organization_id=deal.buyer_organization_id,
            seller_organization_id=deal.seller_organization_id,
            created_at=as_utc(deal.created_at),
            status=deal.status.value,
            current_agreement_version_id=deal.current_agreement_version_id,
            version=deal.version,
        )
        self._db.add(row)
        queue_deal_workflow_notification(
            self._db,
            deal_id=deal.id,
            record_id=deal.id,
            kind=NotificationKind.DEAL_CREATED,
        )
        return row

    def get(self, deal_id: UUID) -> DomainDeal | None:
        """Load a deal by saved identifier for trusted workflow work."""
        row = self._db.get(Deal, deal_id)
        return _to_domain(row) if row is not None else None

    def get_for_participant(
        self, deal_id: UUID, user_id: UUID, *, for_update: bool = False
    ) -> DomainDeal | None:
        statement = select(Deal).where(
            Deal.id == deal_id, _active_participation(user_id)
        )
        if for_update:
            statement = statement.with_for_update()
        row = self._db.scalar(statement)
        return _to_domain(row) if row is not None else None

    def list_for_participant(self, user_id: UUID) -> list[DomainDeal]:
        rows = self._db.scalars(
            select(Deal)
            .where(_active_participation(user_id))
            .order_by(Deal.created_at.desc(), Deal.id)
        ).all()
        return [_to_domain(row) for row in rows]
