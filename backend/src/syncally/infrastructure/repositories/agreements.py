"""SQLAlchemy implementation of the agreement commit transaction.

Rows are translated to and from framework-independent domain types here so
the bilateral-approval invariants in ``domain.agreements.agreement`` stay the
single source of truth; this module only adds persistence, authorization
lookups, and the concurrency guards (row lock + compare-and-swap update)
needed to keep two simultaneous requests from double-committing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syncally.application.agreements import (
    AgreementAlreadyCommitted,
    AgreementNotFound,
    AuditEventDraft,
    CommitAgreementCommand,
    DuplicateApproval,
    OutboxEventDraft,
    RecordApprovalCommand,
    StaleAgreementVersion,
    UnauthorizedApproval,
    WrongTermsHash,
    commit_agreement,
)
from syncally.domain.agreements.agreement import Agreement as DomainAgreement
from syncally.domain.agreements.agreement import AgreementStatus, ApprovalDecision
from syncally.domain.agreements.agreement import Approval as DomainApproval
from syncally.domain.agreements.obligations import ObligationDraft
from syncally.domain.agreements.trade_terms import TradeTerms
from syncally.domain.deals.deal import Deal as DomainDeal
from syncally.domain.deals.deal import DealStatus
from syncally.domain.shared.identifiers import (
    AgreementId,
    AgreementVersionId,
    DealId,
    OrganizationId,
    UserId,
)
from syncally.infrastructure.models import (
    AgreementVersion,
    Approval,
    AuditEvent,
    Deal,
    Obligation,
    Organization,
    OrganizationMember,
    OutboxEvent,
    User,
)
from syncally.infrastructure.repositories._timestamps import as_utc


def _deal_to_domain(row: Deal) -> DomainDeal:
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
    )


def _agreement_to_domain(
    version_row: AgreementVersion, approval_rows: list[Approval]
) -> DomainAgreement:
    """Rebuild the PENDING_APPROVAL aggregate so domain invariants can run.

    ``Agreement`` always constructs as PENDING_APPROVAL (status is a private,
    init=False field since the terms-freezing change) - callers only use this
    for rows that are still PENDING_APPROVAL, checked before calling in.
    """
    terms = TradeTerms.from_canonical_json(version_row.canonical_terms_json)
    approvals = {
        OrganizationId(row.organization_id): DomainApproval(
            organization_id=OrganizationId(row.organization_id),
            user_id=UserId(row.user_id),
            decision=ApprovalDecision(row.decision),
            terms_hash=row.terms_hash,
            created_at=as_utc(row.created_at),
        )
        for row in approval_rows
    }
    return DomainAgreement(
        id=AgreementId(version_row.id),
        version_id=AgreementVersionId(version_row.id),
        deal_id=DealId(version_row.deal_id),
        version_number=version_row.version_number,
        terms=terms,
        created_at=as_utc(version_row.created_at),
        approvals=approvals,
    )


class SqlAlchemyAgreementRepository:
    """Agreement version and approval persistence backed by a SQLAlchemy session."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def record_approval(self, command: RecordApprovalCommand, *, now: datetime) -> DomainApproval:
        version_row = self._get_version(command.deal_id, command.version_number)
        if version_row is None:
            raise AgreementNotFound("Agreement version not found")
        if version_row.status != AgreementStatus.PENDING_APPROVAL.value:
            raise StaleAgreementVersion("Agreement version is no longer pending approval")
        if version_row.terms_hash != command.terms_hash:
            raise WrongTermsHash("Terms hash does not match the current agreement version")

        terms = TradeTerms.from_canonical_json(version_row.canonical_terms_json)
        if OrganizationId(command.organization_id) not in (terms.buyer_id, terms.seller_id):
            raise UnauthorizedApproval("Organization is not a party to this agreement")
        self._require_active_member(command.organization_id, command.user_id)

        approval = DomainApproval(
            organization_id=OrganizationId(command.organization_id),
            user_id=UserId(command.user_id),
            decision=command.decision,
            terms_hash=command.terms_hash,
            created_at=now,
        )
        # Defensive re-check through the domain aggregate before writing.
        _agreement_to_domain(version_row, []).record_approval(approval)

        try:
            with self._db.begin_nested():
                row = Approval(
                    deal_id=version_row.deal_id,
                    agreement_version_id=version_row.id,
                    organization_id=command.organization_id,
                    user_id=command.user_id,
                    decision=command.decision.value,
                    terms_hash=command.terms_hash,
                    created_at=now,
                )
                self._db.add(row)
                self._db.flush()
        except IntegrityError as error:
            raise DuplicateApproval(
                "Organization already recorded a decision for this agreement version"
            ) from error

        self._db.commit()
        return approval

    def commit(self, command: CommitAgreementCommand, *, now: datetime) -> DomainAgreement:
        deal_row = self._db.scalar(
            select(Deal).where(Deal.id == command.deal_id).with_for_update()
        )
        if deal_row is None:
            raise AgreementNotFound("Deal not found")

        version_row = self._get_version(command.deal_id, command.expected_version)
        if version_row is None:
            raise AgreementNotFound("Agreement version not found")
        if version_row.status != AgreementStatus.PENDING_APPROVAL.value:
            raise AgreementAlreadyCommitted(
                "Agreement version is no longer pending approval"
            )
        if version_row.terms_hash != command.expected_terms_hash:
            raise WrongTermsHash("Terms hash does not match the current agreement version")

        approval_rows = list(
            self._db.scalars(
                select(Approval).where(Approval.agreement_version_id == version_row.id)
            )
        )
        agreement = _agreement_to_domain(version_row, approval_rows)
        agreement.commit(command.expected_terms_hash, now)

        committed = self._db.execute(
            update(AgreementVersion)
            .where(
                AgreementVersion.id == version_row.id,
                AgreementVersion.status == AgreementStatus.PENDING_APPROVAL.value,
            )
            .values(status=AgreementStatus.COMMITTED.value, committed_at=now)
            .execution_options(synchronize_session=False)
        )
        if cast(CursorResult[Any], committed).rowcount != 1:
            raise AgreementAlreadyCommitted(
                "Another request already committed this agreement version"
            )

        domain_deal = _deal_to_domain(deal_row)
        domain_deal.mark_agreed(AgreementVersionId(version_row.id))
        deal_updated = self._db.execute(
            update(Deal)
            .where(Deal.id == deal_row.id, Deal.version == deal_row.version)
            .values(status=domain_deal.status.value, version=domain_deal.version)
            .execution_options(synchronize_session=False)
        )
        if cast(CursorResult[Any], deal_updated).rowcount != 1:
            raise AgreementAlreadyCommitted("Deal was concurrently modified")

        self._db.flush()
        return agreement

    def _get_version(self, deal_id: UUID, version_number: int) -> AgreementVersion | None:
        return self._db.scalar(
            select(AgreementVersion).where(
                AgreementVersion.deal_id == deal_id,
                AgreementVersion.version_number == version_number,
            )
        )

    def _require_active_member(self, organization_id: UUID, user_id: UUID) -> None:
        is_active_member = self._db.scalar(
            select(OrganizationMember.id)
            .join(Organization, Organization.id == OrganizationMember.organization_id)
            .join(User, User.id == OrganizationMember.user_id)
            .where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == "ACTIVE",
                Organization.status == "ACTIVE",
                User.status == "ACTIVE",
            )
        )
        if is_active_member is None:
            raise UnauthorizedApproval("User must be an active member of the owning organization")


class SqlAlchemyObligationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add_all(
        self, deal_id: UUID, agreement_version_id: UUID, drafts: list[ObligationDraft]
    ) -> None:
        for draft in drafts:
            self._db.add(
                Obligation(
                    deal_id=deal_id,
                    agreement_version_id=agreement_version_id,
                    obligation_type=draft.obligation_type,
                    owner_organization_id=draft.owner_organization_id,
                    counterparty_organization_id=draft.counterparty_organization_id,
                    due_condition=draft.due_condition,
                    due_date=draft.due_date,
                    source_terms_reference=draft.source_terms_reference,
                )
            )
        self._db.flush()


class SqlAlchemyAuditRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, draft: AuditEventDraft) -> None:
        self._db.add(
            AuditEvent(
                aggregate_type=draft.aggregate_type,
                aggregate_id=draft.aggregate_id,
                event_type=draft.event_type,
                actor_type=draft.actor_type,
                actor_id=draft.actor_id,
                occurred_at=draft.occurred_at,
                correlation_id=draft.correlation_id,
                payload=draft.payload,
            )
        )
        self._db.flush()


class SqlAlchemyOutboxRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, draft: OutboxEventDraft) -> None:
        self._db.add(
            OutboxEvent(
                aggregate_type=draft.aggregate_type,
                aggregate_id=draft.aggregate_id,
                event_type=draft.event_type,
                payload=draft.payload,
            )
        )
        self._db.flush()


def commit_agreement_in_transaction(
    db: Session,
    command: CommitAgreementCommand,
    *,
    now: datetime | None = None,
    correlation_id: str | None = None,
) -> DomainAgreement:
    """Run CommitAgreement as one transaction: commit, obligations, audit, outbox.

    Commits ``db`` once on success and rolls back on any failure, so approval,
    commit, and obligation rows are saved together or not at all. Never call
    Temporal or another external service from inside this function - the
    outbox row is the hand-off point for that, consumed later by a relay.
    """
    now = now or datetime.now(UTC)
    try:
        agreement = commit_agreement(
            command,
            SqlAlchemyAgreementRepository(db),
            SqlAlchemyObligationRepository(db),
            SqlAlchemyAuditRepository(db),
            SqlAlchemyOutboxRepository(db),
            now=now,
            correlation_id=correlation_id,
        )
        db.commit()
        return agreement
    except Exception:
        db.rollback()
        raise
