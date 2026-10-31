"""SQLAlchemy implementation of the agreement commit transaction.

Rows are translated to and from framework-independent domain types here so
the bilateral-approval invariants in ``domain.agreements.agreement`` stay the
single source of truth; this module only adds persistence, authorization
lookups, and the concurrency guards (row lock + compare-and-swap update)
needed to keep two simultaneous requests from double-committing.
"""

from __future__ import annotations

from copy import deepcopy
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
    AmbiguousAgreementOrganization,
    AuditEventDraft,
    CommitAgreementCommand,
    CreateAgreementDraftCommand,
    CreateReviewedAgreementDraftCommand,
    DuplicateApproval,
    OutboxEventDraft,
    ProposalNotFound,
    RecordApprovalCommand,
    StaleAgreementVersion,
    UnauthorizedApproval,
    WrongTermsHash,
    commit_agreement,
    create_agreement_draft,
    create_reviewed_agreement_draft,
    record_approval,
)
from syncally.application.documents import export_display_terms
from syncally.application.workflow_notifications import NotificationKind
from syncally.domain.agreements.agreement import Agreement as DomainAgreement
from syncally.domain.agreements.agreement import AgreementStatus, ApprovalDecision
from syncally.domain.agreements.agreement import Approval as DomainApproval
from syncally.domain.agreements.obligations import ObligationDraft, PaymentMilestoneDraft
from syncally.domain.agreements.trade_terms import TradeTerms
from syncally.domain.deals.deal import Deal as DomainDeal
from syncally.domain.deals.deal import DealStatus
from syncally.domain.negotiation.proposal import (
    DEFAULT_MAX_NEGOTIATION_ROUNDS,
    NegotiationSubmissionOutcome,
    ProposalStatus,
)
from syncally.domain.negotiation.proposal import (
    NegotiationSession as DomainNegotiationSession,
)
from syncally.domain.negotiation.proposal import (
    Proposal as DomainProposal,
)
from syncally.domain.shared.errors import InvalidTransition
from syncally.domain.shared.identifiers import (
    AgreementId,
    AgreementVersionId,
    DealId,
    NegotiationSessionId,
    OrganizationId,
    ProposalId,
    UserId,
)
from syncally.infrastructure.counterparty_onboarding import is_pending, lock_deal
from syncally.infrastructure.models import (
    AgreementVersion,
    Approval,
    AuditEvent,
    Constraint,
    Conversation,
    Deal,
    Message,
    NegotiationSession,
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

    def read_versions(self, deal_id: UUID, user_id: UUID, organization_id: UUID | None,
                      numbers: tuple[int, ...] | None = None, *,
                      commitment_only: bool = False) -> dict[str, Any]:
        deal = self._db.get(Deal, deal_id, populate_existing=True)
        if deal is None:
            raise AgreementNotFound("Deal not found")
        parties = set(self._db.scalars(select(OrganizationMember.organization_id)
            .join(Organization, Organization.id == OrganizationMember.organization_id)
            .join(User, User.id == OrganizationMember.user_id)
            .where(OrganizationMember.user_id == user_id, OrganizationMember.status == "ACTIVE",
                   Organization.status == "ACTIVE", User.status == "ACTIVE",
                   OrganizationMember.organization_id.in_([deal.buyer_organization_id, deal.seller_organization_id]))))
        if not parties or (organization_id is not None and organization_id not in parties):
            raise AgreementNotFound("Deal not found")
        if organization_id is None and len(parties) != 1:
            raise AmbiguousAgreementOrganization("Choose the acting organization")
        party = organization_id or next(iter(parties))
        query = select(AgreementVersion).where(AgreementVersion.deal_id == deal_id)
        if numbers is not None:
            query = query.where(AgreementVersion.version_number.in_(numbers))
        rows = list(self._db.scalars(query.order_by(AgreementVersion.version_number.desc())
                                    .execution_options(populate_existing=True)))
        if numbers is not None and {row.version_number for row in rows} != set(numbers):
            raise AgreementNotFound("Agreement version not found")
        return {"deal_id": str(deal_id), "organization_id": str(party),
                "current_version_id": str(deal.current_agreement_version_id) if deal.current_agreement_version_id else None,
                "versions": [self._read_projection(row, party, deal, commitment_only=commitment_only) for row in rows]}

    def _read_projection(self, row: AgreementVersion, party: UUID, deal: Deal, *,
                         commitment_only: bool = False) -> dict[str, Any]:
        display = export_display_terms(row.canonical_terms_json) if commitment_only else row.canonical_terms_json
        terms = TradeTerms.from_canonical_json(display)
        if (terms.terms_hash != row.terms_hash or terms.buyer_id != deal.buyer_organization_id
                or terms.seller_id != deal.seller_organization_id):
            raise AgreementVersionConflict("Stored agreement is inconsistent")
        approvals = list(self._db.scalars(select(Approval).where(
            Approval.agreement_version_id == row.id, Approval.deal_id == row.deal_id)
            .order_by(Approval.organization_id).execution_options(populate_existing=True)))
        if commitment_only:
            return {"id": str(row.id), "deal_id": str(row.deal_id), "version_number": row.version_number,
                    "terms_hash": row.terms_hash, "status": row.status, "terms": display,
                    "created_at": as_utc(row.created_at),
                    "committed_at": as_utc(row.committed_at) if row.committed_at else None,
                    "approvals": [{"agreement_version_id": str(approval.agreement_version_id),
                        "deal_id": str(approval.deal_id), "version_number": row.version_number,
                        "organization_id": str(approval.organization_id),
                        "decision": approval.decision, "terms_hash": approval.terms_hash}
                        for approval in approvals]}
        proposal = self._db.scalar(select(Proposal).where(Proposal.id == row.proposal_id,
            Proposal.deal_id == row.deal_id).execution_options(populate_existing=True))
        refs = row.canonical_terms_json.get("_f6_evidence")
        if refs is None:
            refs = proposal.evidence_refs if proposal is not None and proposal.terms_hash == row.terms_hash else []
        evidence = [self._read_evidence(ref, row, party) for ref in (refs or [])]
        payment = terms.payment_terms[0] if len(terms.payment_terms) == 1 else None
        return {"id": str(row.id), "deal_id": str(row.deal_id), "version_number": row.version_number,
                "proposal_id": str(row.proposal_id), "terms_hash": row.terms_hash, "status": row.status,
                "terms": terms.to_storage_dict(), "created_at": as_utc(row.created_at),
                "committed_at": as_utc(row.committed_at) if row.committed_at else None,
                "is_current": deal.current_agreement_version_id == row.id,
                "payment_trigger": payment.trigger if payment else None,
                "payment_due_condition": payment.due_condition if payment else None,
                "approvals": [{"id": str(approval.id), "agreement_version_id": str(row.id),
                    "deal_id": str(row.deal_id), "version_number": row.version_number,
                    "organization_id": str(approval.organization_id), "user_id": str(approval.user_id),
                    "decision": approval.decision, "terms_hash": approval.terms_hash,
                    "created_at": as_utc(approval.created_at)} for approval in approvals],
                "evidence": evidence, "grounding": "UNMAPPED"}

    def _read_evidence(self, ref: Any, row: AgreementVersion, party: UUID) -> dict[str, Any]:
        import hashlib

        disabled: dict[str, Any] = {"trace_enabled": False, "state": "UNAVAILABLE", "grounding": "UNMAPPED"}
        if not isinstance(ref, dict):
            return disabled
        try:
            if (type(ref.get("metadata_schema_version")) is not int
                    or ref["metadata_schema_version"] != 1
                    or type(ref.get("version")) is not int or ref["version"] < 1):
                return disabled
            identifiers = {}
            for key in ("fact_id", "owner_organization_id", "source_message_id"):
                value = ref.get(key)
                if not isinstance(value, str) or len(value) != 36:
                    return disabled
                identifiers[key] = UUID(value)
                if str(identifiers[key]) != value.lower():
                    return disabled
            for key in ("visibility", "source_visibility"):
                if not isinstance(ref.get(key), str) or ref[key] not in (
                    "PRIVATE", "INTERNAL", "SHAREABLE"
                ):
                    return disabled
            span = ref.get("source_span")
            body_hash = ref.get("source_body_hash")
            if (not isinstance(span, str) or not span.strip() or len(span) > 8_000
                    or not isinstance(body_hash, str) or len(body_hash) != 64
                    or any(character not in "0123456789abcdef" for character in body_hash)):
                return disabled
            owner = identifiers["owner_organization_id"]
            if owner != party and ref.get("visibility") != "SHAREABLE":
                return disabled
            fact = self._db.get(Constraint, identifiers["fact_id"], populate_existing=True)
            if (fact is None or fact.deal_id != row.deal_id or fact.owner_organization_id != owner
                    or (owner != party and fact.visibility != "SHAREABLE")):
                return disabled
            source = None
            if ref.get("source_message_id"):
                source = self._db.execute(select(Message, Conversation).join(Conversation,
                    Conversation.id == Message.conversation_id).where(Message.id == identifiers["source_message_id"],
                    Conversation.deal_id == row.deal_id).execution_options(populate_existing=True)).one_or_none()
            if source is None:
                return disabled
            message, conversation = source
            if conversation.participant_organization_id != owner:
                return disabled
            if owner != party and (ref.get("source_visibility") != "SHAREABLE" or message.visibility != "SHAREABLE"):
                return disabled
            public = {**disabled, "fact_id": ref["fact_id"], "version": ref["version"],
                      "agreement_version_id": str(row.id), "terms_hash": row.terms_hash,
                      "organization_id": str(party)}
            if (fact.version != ref["version"] or fact.status != "CONFIRMED"
                    or str(fact.source_message_id) != ref.get("source_message_id")
                    or fact.source_span != ref.get("source_span")):
                return {**public, "state": "CHANGED"}
            if not ref.get("source_message_id") or not ref.get("source_body_hash"):
                return {**public, "state": "UNKNOWN"}
            span = ref.get("source_span")
            if (hashlib.sha256(message.body.encode("utf-8")).hexdigest() != ref["source_body_hash"]
                    or not isinstance(span, str) or message.body.count(span) != 1):
                return {**public, "state": "CHANGED"}
            return {**public, "state": "AVAILABLE", "trace_enabled": True,
                    "source_message_id": str(message.id), "source_span": span}
        except (KeyError, ValueError, TypeError):
            return disabled

    def create_draft(
        self, command: CreateAgreementDraftCommand, *, now: datetime
    ) -> DomainAgreement:
        # Locking the deal serializes draft creation against a concurrent
        # approval or commit, so only one version can become current.
        deal_row = lock_deal(self._db, command.deal_id)
        if deal_row is None:
            raise AgreementNotFound("Deal not found")
        if not self._is_active_participant(deal_row, command.user_id):
            raise AgreementAccessDenied("User must be an active member of a deal party")
        if is_pending(self._db, command.deal_id):
            raise AgreementVersionConflict("Awaiting counterparty acceptance")

        proposal_row = self._db.scalar(
            select(Proposal).where(
                Proposal.id == command.proposal_id,
                Proposal.deal_id == command.deal_id,
            )
        )
        if proposal_row is None:
            raise ProposalNotFound("Proposal not found for this deal")
        if self._db.scalar(
            select(Proposal.id)
            .where(
                Proposal.deal_id == command.deal_id,
                Proposal.lifecycle_origin == "HUMAN_ROUNDS",
            )
            .limit(1)
        ) is not None:
            raise AgreementVersionConflict(
                "Human rounds require explicit negotiation and candidate replacement"
            )
        if proposal_row.lifecycle_origin == "HUMAN_ROUNDS":
            raise AgreementVersionConflict("Human proposals require explicit negotiation acceptance")
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

        pending_version = self._pending_version(command.deal_id)
        if pending_version is not None:
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
        version_row.canonical_terms_json = {**version_row.canonical_terms_json,
                            "_f6_evidence": deepcopy(proposal_row.evidence_refs or [])}
        self._db.add(version_row)
        deal_row.status = domain_deal.status.value
        deal_row.current_agreement_version_id = version_id
        deal_row.version = domain_deal.version
        self._db.flush()
        return _agreement_to_domain(version_row, [])

    def create_draft_from_reviewed_terms(
        self, command: CreateReviewedAgreementDraftCommand, *, now: datetime
    ) -> DomainAgreement:
        """Persist the reviewed proposal and agreement snapshot atomically."""
        deal_row = lock_deal(self._db, command.deal_id)
        if deal_row is None:
            raise AgreementNotFound("Deal not found")
        if not self._is_active_participant(deal_row, command.user_id):
            raise AgreementAccessDenied("User must be an active member of a deal party")
        if is_pending(self._db, command.deal_id):
            raise AgreementVersionConflict("Awaiting counterparty acceptance")
        if command.author_organization_id not in (
            deal_row.buyer_organization_id,
            deal_row.seller_organization_id,
        ):
            raise UnauthorizedApproval("Proposal author must be a party to this deal")
        self._require_active_member(command.author_organization_id, command.user_id)
        if self._db.scalar(select(Proposal.id).where(Proposal.deal_id == command.deal_id,
                                                     Proposal.lifecycle_origin == "HUMAN_ROUNDS").limit(1)) is not None:
            raise AgreementVersionConflict("Human rounds require explicit negotiation and candidate replacement")
        if (
            command.terms.buyer_id != OrganizationId(deal_row.buyer_organization_id)
            or command.terms.seller_id != OrganizationId(deal_row.seller_organization_id)
        ):
            raise AgreementVersionConflict("Proposal terms parties do not match the deal")

        pending_version = self._pending_version(command.deal_id)
        if (
            pending_version is not None
            and pending_version.terms_hash == command.terms.terms_hash
        ):
            # Idempotent replay: an identical submission after a lost response
            # (or a concurrent identical submit) already saved exactly these
            # terms. Return that version instead of creating a duplicate
            # proposal or reporting a conflict. Genuinely different terms still
            # fall through to the pending-version conflict.
            approval_rows = list(
                self._db.scalars(
                    select(Approval).where(
                        Approval.agreement_version_id == pending_version.id
                    )
                )
            )
            return _agreement_to_domain(pending_version, approval_rows)

        session_row = self._db.scalar(
            select(NegotiationSession)
            .where(NegotiationSession.deal_id == command.deal_id)
            .with_for_update()
        )
        if session_row is None:
            session_row = NegotiationSession(
                deal_id=command.deal_id,
                max_rounds=DEFAULT_MAX_NEGOTIATION_ROUNDS,
                round_count=0,
            )
            self._db.add(session_row)
            self._db.flush()

        current_row = (
            self._db.get(Proposal, session_row.current_proposal_id)
            if session_row.current_proposal_id is not None
            else None
        )
        current_proposal = None
        if session_row.current_proposal_id is not None:
            if current_row is None or current_row.deal_id != command.deal_id:
                raise AgreementVersionConflict("Current negotiation proposal is unavailable")
            try:
                current_proposal = DomainProposal(
                    id=ProposalId(current_row.id),
                    deal_id=DealId(current_row.deal_id),
                    author_organization_id=OrganizationId(
                        current_row.author_organization_id
                    ),
                    terms=TradeTerms.from_canonical_json(current_row.terms_json),
                    created_at=as_utc(current_row.created_at),
                    based_on_proposal_id=(
                        ProposalId(current_row.based_on_proposal_id)
                        if current_row.based_on_proposal_id is not None
                        else None
                    ),
                    expires_at=(
                        as_utc(current_row.expires_at)
                        if current_row.expires_at is not None
                        else None
                    ),
                    status=ProposalStatus(current_row.status),
                )
            except (TypeError, ValueError) as error:
                raise AgreementVersionConflict(
                    "Current negotiation proposal has an unsupported state"
                ) from error

        proposal_id = uuid4()
        domain_session = DomainNegotiationSession(
            id=NegotiationSessionId(session_row.id),
            deal_id=DealId(command.deal_id),
            max_rounds=session_row.max_rounds,
            round_count=session_row.round_count,
            current_proposal_id=(
                ProposalId(session_row.current_proposal_id)
                if session_row.current_proposal_id is not None
                else None
            ),
            escalated=session_row.escalated,
        )
        proposal = DomainProposal(
            id=ProposalId(proposal_id),
            deal_id=DealId(command.deal_id),
            author_organization_id=OrganizationId(command.author_organization_id),
            terms=command.terms,
            created_at=now,
            based_on_proposal_id=domain_session.current_proposal_id,
        )
        outcome = domain_session.submit(
            proposal,
            now=now,
            current_proposal=current_proposal,
        )
        if outcome is NegotiationSubmissionOutcome.ESCALATION_REQUIRED:
            raise AgreementVersionConflict("Negotiation requires human review")

        if current_row is not None and current_proposal is not None:
            current_row.status = current_proposal.status.value
        proposal_number = self._next_proposal_number(command.deal_id)
        self._db.add(
            Proposal(
                id=proposal_id,
                deal_id=command.deal_id,
                negotiation_session_id=session_row.id,
                proposal_number=proposal_number,
                author_organization_id=command.author_organization_id,
                based_on_proposal_id=(
                    proposal.based_on_proposal_id
                    if proposal.based_on_proposal_id is not None
                    else None
                ),
                terms_json=command.terms.to_storage_dict(),
                terms_hash=command.terms.terms_hash,
                status=proposal.status.value,
                created_at=now,
            )
        )
        session_row.round_count = domain_session.round_count
        session_row.current_proposal_id = proposal_id
        self._db.flush()

        return self.create_draft(
            CreateAgreementDraftCommand(
                deal_id=command.deal_id,
                proposal_id=proposal_id,
                user_id=command.user_id,
            ),
            now=now,
        )

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
        deal_row = lock_deal(self._db, command.deal_id)
        if deal_row is None:
            raise AgreementNotFound("Deal not found")
        if is_pending(self._db, command.deal_id):
            raise AgreementVersionConflict("Awaiting counterparty acceptance")

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
        deal_row = lock_deal(self._db, command.deal_id)
        if deal_row is None:
            raise AgreementNotFound("Deal not found")
        if is_pending(self._db, command.deal_id):
            raise AgreementVersionConflict("Awaiting counterparty acceptance")

        version_row = self._get_version(command.deal_id, command.expected_version)
        if version_row is None:
            raise AgreementNotFound("Agreement version not found")
        proposal = self._db.get(Proposal, version_row.proposal_id)
        if proposal is not None and proposal.lifecycle_origin == "HUMAN_ROUNDS" and command.user_id is None:
            raise UnauthorizedApproval("Human candidate commitment requires a verified actor")
        if command.user_id is not None:
            if command.organization_id not in (deal_row.buyer_organization_id, deal_row.seller_organization_id):
                raise UnauthorizedApproval("Commit actor must select a deal party")
            self._require_active_member(command.organization_id, command.user_id)
        if version_row.status == AgreementStatus.SUPERSEDED.value:
            raise StaleAgreementVersion("Agreement version was superseded; reload before continuing")
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

    def _pending_version(self, deal_id: UUID) -> AgreementVersion | None:
        """Return the deal's pending agreement version, if one exists.

        Draft creation allows at most one pending version per deal; both the
        conflict check and the reviewed-terms replay rely on that invariant.
        """
        return self._db.scalar(
            select(AgreementVersion).where(
                AgreementVersion.deal_id == deal_id,
                AgreementVersion.status == AgreementStatus.PENDING_APPROVAL.value,
            )
        )

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

    def _next_proposal_number(self, deal_id: UUID) -> int:
        highest = self._db.scalar(
            select(func.max(Proposal.proposal_number)).where(Proposal.deal_id == deal_id)
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


def create_reviewed_agreement_draft_in_transaction(
    db: Session,
    command: CreateReviewedAgreementDraftCommand,
    *,
    now: datetime | None = None,
) -> DomainAgreement:
    """Persist the party's reviewed proposal and agreement as one transaction."""
    now = now or datetime.now(UTC)
    try:
        agreement = create_reviewed_agreement_draft(
            command, SqlAlchemyAgreementRepository(db), now=now
        )
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
