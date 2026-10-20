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
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syncally.application.agreements import (
    AgreementAccessDenied,
    AgreementAlreadyCommitted,
    AgreementNotFound,
    AgreementVersionConflict,
    AuditEventDraft,
    CommitAgreementCommand,
    CreateAgreementDraftCommand,
    DuplicateApproval,
    OutboxEventDraft,
    ProposalNotFound,
    RecordApprovalCommand,
    StaleAgreementVersion,
    UnauthorizedApproval,
    WrongTermsHash,
    commit_agreement,
    create_agreement_draft,
    record_approval,
)
from syncally.application.workflow_notifications import NotificationKind
from syncally.domain.agreements.agreement import Agreement as DomainAgreement
from syncally.domain.agreements.agreement import AgreementStatus, ApprovalDecision
from syncally.domain.agreements.agreement import Approval as DomainApproval
from syncally.domain.agreements.obligations import ObligationDraft, PaymentMilestoneDraft
from syncally.domain.agreements.trade_terms import TradeTerms
from syncally.domain.deals.deal import Deal as DomainDeal
from syncally.domain.deals.deal import DealStatus
from syncally.domain.shared.errors import InvalidTransition
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
    PaymentMilestone,
    Proposal,
    User,
)
from syncally.infrastructure.repositories._timestamps import as_utc
from syncally.infrastructure.workflow_notifications import queue_deal_workflow_notification

_TERMINAL_PROPOSAL_STATUSES = frozenset({"REJECTED", "EXPIRED", "SUPERSEDED"})
_APPROVABLE_DEAL_STATUSES = frozenset({DealStatus.DRAFT, DealStatus.NEGOTIATING})


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
    """Rebuild a pending agreement aggregate from persisted values."""
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
        id=AgreementId(version_row.deal_id),
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

    def create_draft(
        self, command: CreateAgreementDraftCommand, *, now: datetime
    ) -> DomainAgreement:
        # Locking the deal serializes draft creation against a concurrent
        # approval or commit, so only one version can become current.
        deal_row = self._db.scalar(
            select(Deal).where(Deal.id == command.deal_id).with_for_update()
        )
        if deal_row is None:
            raise AgreementNotFound("Deal not found")
        if not self._is_active_participant(deal_row, command.user_id):
            raise AgreementAccessDenied("User must be an active member of a deal party")

        proposal_row = self._db.scalar(
            select(Proposal).where(
                Proposal.id == command.proposal_id,
                Proposal.deal_id == command.deal_id,
            )
        )
        if proposal_row is None:
            raise ProposalNotFound("Proposal not found for this deal")
        if proposal_row.status in _TERMINAL_PROPOSAL_STATUSES:
            raise AgreementVersionConflict(
                f"Proposal is {proposal_row.status} and cannot become an agreement"
            )

        terms = TradeTerms.from_canonical_json(proposal_row.terms_json)
        if terms.buyer_id != OrganizationId(
            deal_row.buyer_organization_id
        ) or terms.seller_id != OrganizationId(deal_row.seller_organization_id):
            raise AgreementVersionConflict("Proposal terms parties do not match the deal")
        if terms.terms_hash != proposal_row.terms_hash:
            raise AgreementVersionConflict("Proposal terms do not match their recorded hash")

        pending_version_id = self._db.scalar(
            select(AgreementVersion.id).where(
                AgreementVersion.deal_id == command.deal_id,
                AgreementVersion.status == AgreementStatus.PENDING_APPROVAL.value,
            )
        )
        if pending_version_id is not None:
            raise AgreementVersionConflict(
                "A pending agreement version already exists for this deal"
            )

        domain_deal = _deal_to_domain(deal_row)
        if domain_deal.status not in _APPROVABLE_DEAL_STATUSES:
            raise AgreementVersionConflict(
                f"Deal is {domain_deal.status} and cannot start approval"
            )

        version_number = self._next_version_number(command.deal_id)
        version_id = uuid4()
        try:
            if domain_deal.status is DealStatus.DRAFT:
                domain_deal.start_negotiation()
            domain_deal.request_approval(AgreementVersionId(version_id))
        except InvalidTransition as error:
            raise AgreementVersionConflict(str(error)) from error

        version_row = AgreementVersion(
            id=version_id,
            deal_id=deal_row.id,
            proposal_id=proposal_row.id,
            version_number=version_number,
            canonical_terms_json=terms.to_storage_dict(),
            terms_hash=terms.terms_hash,
            status=AgreementStatus.PENDING_APPROVAL.value,
            created_by=command.user_id,
            created_at=now,
        )
        self._db.add(version_row)
        deal_row.status = domain_deal.status.value
        deal_row.current_agreement_version_id = version_id
        deal_row.version = domain_deal.version
        self._db.flush()
        return _agreement_to_domain(version_row, [])

    def get_current(self, deal_id: UUID) -> DomainAgreement | None:
        """Load the deal's current immutable version and its recorded decisions."""
        deal_row = self._db.get(Deal, deal_id)
        if deal_row is None or deal_row.current_agreement_version_id is None:
            return None
        version_row = self._db.scalar(
            select(AgreementVersion).where(
                AgreementVersion.id == deal_row.current_agreement_version_id,
                AgreementVersion.deal_id == deal_id,
            )
        )
        if version_row is None:
            return None
        approval_rows = list(
            self._db.scalars(
                select(Approval)
                .where(Approval.agreement_version_id == version_row.id)
                .order_by(Approval.organization_id)
            )
        )
        agreement = _agreement_to_domain(version_row, approval_rows)
        if agreement.terms_hash != version_row.terms_hash:
            raise AgreementVersionConflict("Stored agreement terms do not match their hash")
        if version_row.status == AgreementStatus.COMMITTED.value:
            if version_row.committed_at is None:
                raise AgreementVersionConflict("Committed agreement is missing its commit time")
            agreement.commit(version_row.terms_hash, as_utc(version_row.committed_at))
        elif version_row.status != AgreementStatus.PENDING_APPROVAL.value:
            raise AgreementVersionConflict("Current agreement has an unsupported status")
        return agreement

    def record_approval(self, command: RecordApprovalCommand, *, now: datetime) -> DomainApproval:
        # Locking the deal row serializes this against a concurrent commit()
        # (which locks the same row), so the staleness/party checks below see
        # a consistent snapshot of which version is current.
        deal_row = self._db.scalar(
            select(Deal).where(Deal.id == command.deal_id).with_for_update()
        )
        if deal_row is None:
            raise AgreementNotFound("Deal not found")

        version_row = self._get_version(command.deal_id, command.version_number)
        if version_row is None:
            raise AgreementNotFound("Agreement version not found")
        if (
            version_row.status != AgreementStatus.PENDING_APPROVAL.value
            or deal_row.current_agreement_version_id != version_row.id
        ):
            raise StaleAgreementVersion("Agreement version is no longer pending approval")
        if version_row.terms_hash != command.terms_hash:
            raise WrongTermsHash("Terms hash does not match the current agreement version")

        terms = TradeTerms.from_canonical_json(version_row.canonical_terms_json)
        if terms.buyer_id != OrganizationId(deal_row.buyer_organization_id) or terms.seller_id != OrganizationId(
            deal_row.seller_organization_id
        ):
            raise UnauthorizedApproval("Agreement version parties do not match the deal")
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

        existing_row = self._db.scalar(
            select(Approval).where(
                Approval.agreement_version_id == version_row.id,
                Approval.organization_id == command.organization_id,
            )
        )
        if existing_row is not None:
            if existing_row.decision == command.decision.value:
                raise DuplicateApproval(
                    "Organization already recorded this decision for this agreement version"
                )
            # A party is revising a prior REJECT/APPROVE while still pending.
            existing_row.decision = command.decision.value
            existing_row.user_id = command.user_id
            existing_row.terms_hash = command.terms_hash
            existing_row.created_at = now
            self._db.flush()
        else:
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

        queue_deal_workflow_notification(
            self._db,
            deal_id=version_row.deal_id,
            record_id=version_row.id,
            kind=NotificationKind.AGREEMENT_APPROVAL_RECORDED,
        )
        return approval

    def commit(
        self, command: CommitAgreementCommand, *, now: datetime
    ) -> tuple[DomainAgreement, bool]:
        deal_row = self._db.scalar(
            select(Deal).where(Deal.id == command.deal_id).with_for_update()
        )
        if deal_row is None:
            raise AgreementNotFound("Deal not found")

        version_row = self._get_version(command.deal_id, command.expected_version)
        if version_row is None:
            raise AgreementNotFound("Agreement version not found")
        if (
            version_row.status == AgreementStatus.PENDING_APPROVAL.value
            and deal_row.current_agreement_version_id != version_row.id
        ):
            raise StaleAgreementVersion(
                "Agreement version is no longer current for this deal"
            )
        if version_row.status != AgreementStatus.PENDING_APPROVAL.value:
            if (
                version_row.status == AgreementStatus.COMMITTED.value
                and version_row.terms_hash == command.expected_terms_hash
            ):
                # Idempotent replay: the caller already committed this exact
                # version (e.g. a retry after losing the first response).
                approval_rows = list(
                    self._db.scalars(
                        select(Approval).where(Approval.agreement_version_id == version_row.id)
                    )
                )
                agreement = _agreement_to_domain(version_row, approval_rows)
                agreement.commit(command.expected_terms_hash, as_utc(version_row.committed_at))
                return agreement, False
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
        if agreement.terms.buyer_id != OrganizationId(
            deal_row.buyer_organization_id
        ) or agreement.terms.seller_id != OrganizationId(deal_row.seller_organization_id):
            raise UnauthorizedApproval("Agreement version parties do not match the deal")
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
        version_row.status = AgreementStatus.COMMITTED.value
        version_row.committed_at = now

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
        deal_row.status = domain_deal.status.value
        deal_row.version = domain_deal.version

        self._db.flush()
        return agreement, True

    def _get_version(self, deal_id: UUID, version_number: int) -> AgreementVersion | None:
        return self._db.scalar(
            select(AgreementVersion).where(
                AgreementVersion.deal_id == deal_id,
                AgreementVersion.version_number == version_number,
            )
        )

    def _next_version_number(self, deal_id: UUID) -> int:
        highest = self._db.scalar(
            select(func.max(AgreementVersion.version_number)).where(
                AgreementVersion.deal_id == deal_id
            )
        )
        return (highest or 0) + 1

    def _is_active_participant(self, deal_row: Deal, user_id: UUID) -> bool:
        is_member = self._db.scalar(
            select(OrganizationMember.id)
            .join(Organization, Organization.id == OrganizationMember.organization_id)
            .join(User, User.id == OrganizationMember.user_id)
            .where(
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == "ACTIVE",
                Organization.status == "ACTIVE",
                User.status == "ACTIVE",
                OrganizationMember.organization_id.in_(
                    [deal_row.buyer_organization_id, deal_row.seller_organization_id]
                ),
            )
        )
        return is_member is not None

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
    ) -> dict[str, UUID]:
        rows = [
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
            for draft in drafts
        ]
        self._db.add_all(rows)
        self._db.flush()
        return {
            row.source_terms_reference: row.id for row in rows if row.source_terms_reference
        }


class SqlAlchemyPaymentMilestoneRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add_all(
        self,
        deal_id: UUID,
        agreement_version_id: UUID,
        drafts: list[PaymentMilestoneDraft],
        obligation_ids_by_reference: dict[str, UUID],
    ) -> None:
        for draft in drafts:
            self._db.add(
                PaymentMilestone(
                    deal_id=deal_id,
                    agreement_version_id=agreement_version_id,
                    obligation_id=obligation_ids_by_reference.get(draft.source_terms_reference),
                    sequence_number=draft.sequence_number,
                    payer_organization_id=draft.payer_organization_id,
                    amount=draft.amount.amount,
                    currency=draft.amount.currency,
                    trigger_type=draft.trigger_type,
                    due_condition=draft.due_condition,
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


def create_agreement_draft_in_transaction(
    db: Session,
    command: CreateAgreementDraftCommand,
    *,
    now: datetime | None = None,
) -> DomainAgreement:
    """Run CreateAgreementDraft as its own transaction: commits on success, rolls back on failure."""
    now = now or datetime.now(UTC)
    try:
        agreement = create_agreement_draft(command, SqlAlchemyAgreementRepository(db), now=now)
        db.commit()
        return agreement
    except Exception:
        db.rollback()
        raise


def record_approval_in_transaction(
    db: Session,
    command: RecordApprovalCommand,
    *,
    now: datetime | None = None,
) -> DomainApproval:
    """Run RecordApproval as its own transaction: commits on success, rolls back on failure.

    Owns the commit so the repository itself never commits the shared
    session - unrelated pending writes on ``db`` are left untouched either way.
    """
    now = now or datetime.now(UTC)
    try:
        approval = record_approval(command, SqlAlchemyAgreementRepository(db), now=now)
        db.commit()
        return approval
    except Exception:
        db.rollback()
        raise


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
            SqlAlchemyPaymentMilestoneRepository(db),
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
