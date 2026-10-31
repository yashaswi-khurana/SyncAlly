"""Deal-serialized human rounds and candidate replacement in one transaction."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from syncally.application.negotiation import (
    NegotiationCommand,
    NegotiationConflict,
    NegotiationNotFound,
    NegotiationOrganizationRequired,
    negotiate,
)
from syncally.domain.agreements.trade_terms import TradeTerms
from syncally.domain.deals.deal import DealStatus
from syncally.domain.negotiation.proposal import (
    DEFAULT_MAX_NEGOTIATION_ROUNDS,
    NegotiationSubmissionOutcome,
    ProposalStatus,
)
from syncally.domain.negotiation.proposal import (
    NegotiationSession as DomainSession,
)
from syncally.domain.negotiation.proposal import (
    Proposal as DomainProposal,
)
from syncally.domain.shared.errors import InvalidTransition, InvariantViolation
from syncally.domain.shared.identifiers import (
    AgreementVersionId,
    DealId,
    NegotiationSessionId,
    OrganizationId,
    ProposalId,
)
from syncally.infrastructure.counterparty_onboarding import is_pending, lock_deal
from syncally.infrastructure.models import (
    AgreementVersion,
    Constraint,
    Conversation,
    Deal,
    Message,
    NegotiationAction,
    NegotiationSession,
    Organization,
    OrganizationMember,
    Proposal,
    User,
)
from syncally.infrastructure.repositories._timestamps import as_utc
from syncally.infrastructure.repositories.agreements import _deal_to_domain


class SqlAlchemyNegotiationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _authorize(self, deal: Deal | None, user_id: UUID, organization_id: UUID | None) -> UUID:
        if deal is None:
            raise NegotiationNotFound("Deal not found")
        parties = set(self._db.scalars(
            select(OrganizationMember.organization_id)
            .join(Organization, Organization.id == OrganizationMember.organization_id)
            .join(User, User.id == OrganizationMember.user_id)
            .where(OrganizationMember.user_id == user_id, OrganizationMember.status == "ACTIVE",
                   Organization.status == "ACTIVE", User.status == "ACTIVE",
                   OrganizationMember.organization_id.in_([deal.buyer_organization_id, deal.seller_organization_id]))
        ))
        if not parties or (organization_id is not None and organization_id not in parties):
            raise NegotiationNotFound("Deal not found")
        if organization_id is None:
            if len(parties) != 1:
                raise NegotiationOrganizationRequired("Choose the acting organization")
            return next(iter(parties))
        return organization_id

    def _latest(self, deal_id: UUID, session: NegotiationSession | None) -> Proposal | None:
        latest = self._db.scalar(select(Proposal).where(Proposal.deal_id == deal_id)
                                 .order_by(Proposal.proposal_number.desc()).limit(1)
                                 .execution_options(populate_existing=True))
        if latest is not None:
            if session is None or latest.negotiation_session_id != session.id or session.current_proposal_id != latest.id:
                raise NegotiationConflict("Legacy negotiation history is ambiguous; review is required")
            chain = select(Proposal.negotiation_session_id, Proposal.based_on_proposal_id,
                           func.lag(Proposal.id).over(order_by=Proposal.proposal_number).label("previous"))\
                .where(Proposal.deal_id == deal_id).subquery()
            invalid = self._db.scalar(select(chain.c.negotiation_session_id).where(or_(
                chain.c.negotiation_session_id != session.id,
                chain.c.based_on_proposal_id != chain.c.previous,
                chain.c.based_on_proposal_id.is_(None) & chain.c.previous.is_not(None),
                chain.c.based_on_proposal_id.is_not(None) & chain.c.previous.is_(None),
            )).limit(1))
            if invalid is not None:
                raise NegotiationConflict("Negotiation predecessor chain is ambiguous; review is required")
        elif session is not None and session.current_proposal_id is not None:
            raise NegotiationConflict("Negotiation latest proposal is unavailable")
        return latest

    def _proposal(self, row: Proposal, *, legacy: bool = False) -> DomainProposal:
        terms = TradeTerms.from_canonical_json(row.terms_json)
        if terms.terms_hash != row.terms_hash:
            raise NegotiationConflict("Stored proposal hash is inconsistent")
        return DomainProposal(
            id=ProposalId(row.id), deal_id=DealId(row.deal_id),
            author_organization_id=OrganizationId(row.author_organization_id), terms=terms,
            created_at=as_utc(row.created_at),
            based_on_proposal_id=ProposalId(row.based_on_proposal_id) if row.based_on_proposal_id else None,
            expires_at=as_utc(row.expires_at) if row.expires_at and not legacy else None,
            status=ProposalStatus.SUPERSEDED if legacy else ProposalStatus(row.status),
        )

    def _fingerprint(self, command: NegotiationCommand, organization_id: UUID) -> str:
        payload = {
            "schema_version": 1, "deal_id": str(command.deal_id), "user_id": str(command.user_id),
            "organization_id": str(organization_id), "action": command.action,
            "expected_deal_revision": command.expected_deal_revision,
            "base": None if command.base is None else [str(command.base.id), command.base.terms_hash, command.base.status],
            "terms": command.terms.canonical_json() if command.terms else None,
            "expires_at": as_utc(command.expires_at).isoformat() if command.expires_at else None,
            "candidate": None if command.supersede_current_candidate is None else [
                str(command.supersede_current_candidate.id), command.supersede_current_candidate.version_number,
                command.supersede_current_candidate.terms_hash, str(command.supersede_current_candidate.proposal_id)],
            "evidence": sorted((str(ref.fact_id), ref.version) for ref in command.evidence),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def _source_visible(self, ref: dict[str, Any], deal_id: UUID, organization_id: UUID) -> bool:
        fact = self._db.get(Constraint, UUID(ref["fact_id"]), populate_existing=True)
        if fact is None or fact.deal_id != deal_id or fact.owner_organization_id != UUID(ref["owner_organization_id"]):
            return False
        if fact.owner_organization_id != organization_id and (
            ref["visibility"] != "SHAREABLE" or fact.visibility != "SHAREABLE"
        ):
            return False
        if ref["source_message_id"] is not None:
            source = self._db.execute(select(Message, Conversation).join(Conversation, Conversation.id == Message.conversation_id)
                                      .where(Message.id == UUID(ref["source_message_id"]), Conversation.deal_id == deal_id)
                                      .execution_options(populate_existing=True)).one_or_none()
            if source is None:
                return False
            message, conversation = source
            if conversation.participant_organization_id != organization_id and message.visibility != "SHAREABLE":
                return False
            if ref["visibility"] == "SHAREABLE" and message.visibility != "SHAREABLE":
                return False
        elif ref["visibility"] == "SHAREABLE" and ref["source_span"]:
            return False
        return True

    def _evidence(self, command: NegotiationCommand, organization_id: UUID) -> list[dict[str, Any]]:
        refs = []
        for requested in command.evidence:
            fact = self._db.get(Constraint, requested.fact_id, populate_existing=True)
            if (fact is None or fact.deal_id != command.deal_id or fact.version != requested.version
                    or fact.status != "CONFIRMED" or (fact.owner_organization_id != organization_id and fact.visibility != "SHAREABLE")):
                raise NegotiationConflict("Evidence is no longer authorized and confirmed")
            ref = {"metadata_schema_version": 1, "fact_id": str(fact.id), "version": fact.version,
                   "owner_organization_id": str(fact.owner_organization_id), "visibility": fact.visibility,
                   "source_message_id": str(fact.source_message_id) if fact.source_message_id else None,
                   "source_span": fact.source_span}
            if not self._source_visible(ref, command.deal_id, organization_id):
                raise NegotiationConflict("Evidence source is no longer authorized")
            if fact.source_message_id is not None:
                message = self._db.get(Message, fact.source_message_id, populate_existing=True)
                if message is not None:
                    ref["source_body_hash"] = hashlib.sha256(message.body.encode("utf-8")).hexdigest()
                    ref["source_visibility"] = message.visibility
            refs.append(ref)
        return refs

    def execute(self, command: NegotiationCommand, *, now: datetime) -> dict[str, Any]:
        deal = lock_deal(self._db, command.deal_id)
        organization_id = self._authorize(deal, command.user_id, command.organization_id)
        if is_pending(self._db, command.deal_id):
            raise NegotiationConflict("Awaiting counterparty acceptance")
        fingerprint = self._fingerprint(command, organization_id)
        replay = self._db.scalar(select(NegotiationAction).where(NegotiationAction.deal_id == command.deal_id,
                                                                NegotiationAction.command_id == command.command_id))
        if replay is not None:
            if replay.fingerprint != fingerprint:
                raise NegotiationConflict("Command ID was used for a different action")
            return dict(replay.result)
        if deal.status not in ("DRAFT", "NEGOTIATING", "PENDING_APPROVALS"):
            raise NegotiationConflict("Committed or closed deals cannot negotiate")
        if deal.version != command.expected_deal_revision:
            raise NegotiationConflict("Deal changed; reload before continuing")
        session = self._db.scalar(select(NegotiationSession).where(NegotiationSession.deal_id == deal.id)
                                  .with_for_update().execution_options(populate_existing=True))
        latest = self._latest(deal.id, session)
        if ((latest is None and command.base is not None) or (latest is not None and (
            command.base is None or (command.base.id, command.base.terms_hash, command.base.status)
            != (latest.id, latest.terms_hash, latest.status)
        ))):
            raise NegotiationConflict("Latest proposal changed; reload before continuing")
        if session is None:
            if command.action != "submit":
                raise NegotiationConflict("Submit a proposal first")
            session = NegotiationSession(deal_id=deal.id, max_rounds=DEFAULT_MAX_NEGOTIATION_ROUNDS)
            self._db.add(session)
            self._db.flush()
        if session.escalated:
            raise NegotiationConflict("Negotiation is escalated for human review")
        pending = self._db.scalar(select(AgreementVersion).where(AgreementVersion.deal_id == deal.id,
                                      AgreementVersion.status == "PENDING_APPROVAL").with_for_update()
                                  .execution_options(populate_existing=True))
        if pending is not None:
            ack = command.supersede_current_candidate
            if (ack is None or (ack.id, ack.version_number, ack.terms_hash, ack.proposal_id)
                    != (pending.id, pending.version_number, pending.terms_hash, pending.proposal_id)
                    or deal.current_agreement_version_id != pending.id):
                raise NegotiationConflict("Explicit acknowledgement of the current candidate is required")
        elif command.supersede_current_candidate is not None or deal.current_agreement_version_id is not None:
            raise NegotiationConflict("Candidate changed; reload before continuing")
        domain_deal = _deal_to_domain(deal)
        current = self._proposal(latest, legacy=latest.lifecycle_origin == "LEGACY") if latest else None
        if current and (current.terms.buyer_id != OrganizationId(deal.buyer_organization_id)
                        or current.terms.seller_id != OrganizationId(deal.seller_organization_id)):
            raise NegotiationConflict("Proposal parties do not match the deal")
        before = latest.status if latest else None
        new = None
        candidate = None
        action = command.action
        if command.action in ("submit", "counter"):
            if command.terms.buyer_id != OrganizationId(deal.buyer_organization_id) or command.terms.seller_id != OrganizationId(deal.seller_organization_id):
                raise NegotiationConflict("Reviewed terms parties do not match the deal")
            if command.action == "counter":
                if latest is None or latest.lifecycle_origin != "HUMAN_ROUNDS" or latest.status != "SUBMITTED":
                    raise NegotiationConflict("Only the latest live human proposal can be countered")
                current.authorize_action("counter", OrganizationId(organization_id))
                current._ensure_not_expired(now)
            elif latest and latest.lifecycle_origin == "HUMAN_ROUNDS" and latest.status == "SUBMITTED":
                raise NegotiationConflict("Counter or explicitly supersede the live proposal first")
            proposal = DomainProposal(id=ProposalId(uuid4()), deal_id=DealId(deal.id),
                                      author_organization_id=OrganizationId(organization_id), terms=command.terms,
                                      created_at=now, based_on_proposal_id=ProposalId(latest.id) if latest else None,
                                      expires_at=command.expires_at)
            evidence = self._evidence(command, organization_id)
            domain_session = DomainSession(NegotiationSessionId(session.id), DealId(deal.id), session.max_rounds,
                                           session.round_count, ProposalId(latest.id) if latest else None, session.escalated)
            outcome = domain_session.submit(proposal, now=now, current_proposal=current)
            if outcome is NegotiationSubmissionOutcome.ESCALATION_REQUIRED:
                session.escalated = True
                deal.version += 1
                result = {"outcome": "ESCALATION_REQUIRED", "deal_revision": deal.version,
                          "proposal_id": str(latest.id) if latest else None, "candidate_id": None}
                self._record(command, session, organization_id, fingerprint, "escalate", latest, before, before, None, None, result, now)
                return result
            if latest and latest.lifecycle_origin == "HUMAN_ROUNDS":
                latest.status = current.status.value
            number = self._db.scalar(select(func.max(Proposal.proposal_number)).where(Proposal.deal_id == deal.id)) or 0
            new = Proposal(id=proposal.id, deal_id=deal.id, negotiation_session_id=session.id,
                           proposal_number=number + 1, author_organization_id=organization_id, created_by=command.user_id,
                           based_on_proposal_id=latest.id if latest else None, terms_json=command.terms.to_storage_dict(),
                           terms_hash=command.terms.terms_hash, status="SUBMITTED", lifecycle_origin="HUMAN_ROUNDS",
                           evidence_refs=evidence, expires_at=command.expires_at, created_at=now)
            self._db.add(new)
            session.round_count = domain_session.round_count
            session.current_proposal_id = new.id
            deal.current_proposal_id = new.id
        else:
            if latest is None or latest.lifecycle_origin != "HUMAN_ROUNDS":
                raise NegotiationConflict("Action requires the latest human proposal")
            current.authorize_action(command.action, OrganizationId(organization_id))
            if command.action == "accept":
                current.accept_as_candidate(now=now)
            elif command.action == "reject":
                current.reject()
            elif command.action == "supersede":
                current.supersede()
            else:
                current.expire(now=now)
            latest.status = current.status.value
        invalidated = pending.id if pending else None
        if pending is not None:
            domain_deal.replace_pending_candidate(AgreementVersionId(pending.id))
            from syncally.infrastructure.repositories.agreements import _agreement_to_domain
            pending_domain = _agreement_to_domain(pending, [])
            if pending_domain.terms_hash != pending.terms_hash:
                raise NegotiationConflict("Candidate hash is inconsistent")
            pending_domain.supersede()
            pending.status = pending_domain.status.value
            self._db.flush()
        if domain_deal.status is DealStatus.DRAFT:
            domain_deal.start_negotiation()
        if command.action == "accept":
            candidate_id = uuid4()
            number = self._db.scalar(select(func.max(AgreementVersion.version_number)).where(AgreementVersion.deal_id == deal.id)) or 0
            candidate = AgreementVersion(id=candidate_id, deal_id=deal.id, proposal_id=latest.id,
                                         version_number=number + 1, canonical_terms_json=current.terms.to_storage_dict(),
                                         terms_hash=current.terms_hash, status="PENDING_APPROVAL", created_by=command.user_id, created_at=now)
            from copy import deepcopy
            candidate.canonical_terms_json = {**candidate.canonical_terms_json,
                                              "_f6_evidence": deepcopy(latest.evidence_refs or [])}
            self._db.add(candidate)
            domain_deal.request_approval(AgreementVersionId(candidate_id))
        deal.status = domain_deal.status.value
        deal.current_agreement_version_id = domain_deal.current_agreement_version_id
        deal.version = max(domain_deal.version, command.expected_deal_revision + 1)
        target = new or latest
        self._db.flush()
        result = {"outcome": "APPLIED", "deal_revision": deal.version, "proposal_id": str(target.id),
                  "candidate_id": str(candidate.id) if candidate else None}
        self._record(command, session, organization_id, fingerprint, action, target, before, target.status,
                     candidate, invalidated, result, now)
        return result

    def _record(self, command: NegotiationCommand, session: NegotiationSession, organization_id: UUID,
                fingerprint: str, action: str, proposal: Proposal | None, before: str | None, after: str | None,
                candidate: AgreementVersion | None, invalidated: UUID | None, result: dict[str, Any], now: datetime) -> None:
        self._db.add(NegotiationAction(deal_id=command.deal_id, session_id=session.id, command_id=command.command_id,
                                      fingerprint=fingerprint, actor_organization_id=organization_id, actor_user_id=command.user_id,
                                      action=action, expected_deal_revision=command.expected_deal_revision,
                                      proposal_id=proposal.id if proposal else None,
                                      predecessor_id=command.base.id if command.base else None,
                                      candidate_id=candidate.id if candidate else None, invalidated_candidate_id=invalidated,
                                      from_status=before, to_status=after, result=result, created_at=now))
        self._db.flush()

    def read(self, deal_id: UUID, user_id: UUID, organization_id: UUID | None, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        deal = lock_deal(self._db, deal_id, shared=True)
        party = self._authorize(deal, user_id, organization_id)
        session = self._db.scalar(select(NegotiationSession).where(NegotiationSession.deal_id == deal_id))
        pending = self._db.scalar(select(AgreementVersion).where(AgreementVersion.deal_id == deal_id,
                                                                AgreementVersion.status == "PENDING_APPROVAL"))
        latest = self._db.scalar(select(Proposal).where(Proposal.deal_id == deal_id).order_by(Proposal.proposal_number.desc()).limit(1))
        ambiguous = False
        try:
            self._latest(deal_id, session)
        except NegotiationConflict:
            ambiguous = True
        proposals = list(self._db.scalars(select(Proposal).where(Proposal.deal_id == deal_id)
                                         .order_by(Proposal.proposal_number.desc()).limit(limit).offset(offset)))
        history = list(self._db.scalars(select(NegotiationAction).where(NegotiationAction.deal_id == deal_id)
                                       .order_by(NegotiationAction.created_at.desc(), NegotiationAction.id).limit(limit).offset(offset)))
        writable = (not ambiguous and not is_pending(self._db, deal_id) and deal.status in ("DRAFT", "NEGOTIATING", "PENDING_APPROVALS")
                    and not (session and session.escalated))
        eligible = []
        if writable:
            if latest is None or latest.lifecycle_origin == "LEGACY" or latest.status != "SUBMITTED":
                eligible = ["submit"]
            else:
                elapsed = latest.expires_at is not None and as_utc(latest.expires_at) <= datetime.now(UTC)
                if latest.author_organization_id == party:
                    eligible = ["supersede"]
                else:
                    eligible = ["reject"] + ([] if elapsed else ["counter", "accept"])
                if elapsed:
                    eligible.append("expire")
        def projection(row: Proposal) -> dict[str, Any]:
            refs = [ref for ref in (row.evidence_refs or []) if self._source_visible(ref, deal_id, party)]
            return {"id": str(row.id), "proposal_number": row.proposal_number, "author_organization_id": str(row.author_organization_id),
                    "based_on_proposal_id": str(row.based_on_proposal_id) if row.based_on_proposal_id else None,
                    "terms": row.terms_json, "terms_hash": row.terms_hash, "status": row.status,
                    "lifecycle_origin": row.lifecycle_origin, "created_at": as_utc(row.created_at).isoformat(),
                    "expires_at": as_utc(row.expires_at).isoformat() if row.expires_at else None,
                    "evidence_refs": refs, "metadata_schema_version": 1}
        return {"deal_id": str(deal.id), "deal_revision": deal.version, "organization_id": str(party),
                "max_rounds": session.max_rounds if session else DEFAULT_MAX_NEGOTIATION_ROUNDS,
                "round_count": session.round_count if session else 0, "escalated": session.escalated if session else False,
                "history_ambiguous": ambiguous, "eligible_actions": eligible,
                "latest": projection(latest) if latest else None, "proposals": [projection(row) for row in proposals],
                "current_candidate": None if pending is None else {"id": str(pending.id), "version_number": pending.version_number,
                    "terms_hash": pending.terms_hash, "proposal_id": str(pending.proposal_id)},
                "history": [{"id": str(row.id), "action": row.action, "proposal_id": str(row.proposal_id) if row.proposal_id else None,
                             "predecessor_id": str(row.predecessor_id) if row.predecessor_id else None,
                             "candidate_id": str(row.candidate_id) if row.candidate_id else None,
                             "invalidated_candidate_id": str(row.invalidated_candidate_id) if row.invalidated_candidate_id else None,
                             "actor_organization_id": str(row.actor_organization_id), "from_status": row.from_status,
                             "to_status": row.to_status, "created_at": as_utc(row.created_at).isoformat()} for row in history]}


def negotiate_in_transaction(db: Session, command: NegotiationCommand, *, now: datetime | None = None) -> dict[str, Any]:
    try:
        result = negotiate(command, SqlAlchemyNegotiationRepository(db), now=now or datetime.now(UTC))
        db.commit()
        return result
    except (InvalidTransition, InvariantViolation):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise