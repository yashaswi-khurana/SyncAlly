"""Submitted proposal snapshots and negotiation round control."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from syncally.domain.agreements.trade_terms import TradeTerms
from syncally.domain.shared.errors import InvalidTransition, InvariantViolation
from syncally.domain.shared.identifiers import (
    DealId,
    NegotiationSessionId,
    OrganizationId,
    ProposalId,
)

DEFAULT_MAX_NEGOTIATION_ROUNDS = 5


class ProposalStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    ACCEPTED_AS_CANDIDATE = "ACCEPTED_AS_CANDIDATE"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
    EXPIRED = "EXPIRED"


class NegotiationSubmissionOutcome(StrEnum):
    SUBMITTED = "SUBMITTED"
    ESCALATION_REQUIRED = "ESCALATION_REQUIRED"


@dataclass(slots=True)
class Proposal:
    id: ProposalId
    deal_id: DealId
    author_organization_id: OrganizationId
    terms: TradeTerms
    created_at: datetime
    based_on_proposal_id: ProposalId | None = None
    expires_at: datetime | None = None
    status: ProposalStatus = ProposalStatus.SUBMITTED

    def __setattr__(self, name: str, value: object) -> None:
        if hasattr(self, name):
            raise InvalidTransition("Submitted proposal snapshots are immutable")
        object.__setattr__(self, name, value)

    def __post_init__(self) -> None:
        if self.author_organization_id not in (self.terms.buyer_id, self.terms.seller_id):
            raise InvariantViolation("Proposal author must be a party to its trade terms")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise InvariantViolation("Proposal creation time must be timezone-aware")
        if self.expires_at is not None:
            if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
                raise InvariantViolation("Proposal expiry must be timezone-aware")
            if not self.created_at < self.expires_at <= self.created_at + timedelta(days=30):
                raise InvariantViolation("Proposal expiry must be within 30 days of creation")

    @property
    def terms_hash(self) -> str:
        return self.terms.terms_hash

    def accept_as_candidate(self, *, now: datetime) -> None:
        self._ensure_not_expired(now)
        self._transition(ProposalStatus.ACCEPTED_AS_CANDIDATE)

    def reject(self) -> None:
        self._transition(ProposalStatus.REJECTED)

    def supersede(self) -> None:
        self._transition(ProposalStatus.SUPERSEDED)

    def expire(self, *, now: datetime) -> None:
        if self.expires_at is None or now < self.expires_at:
            raise InvalidTransition("Proposal deadline has not elapsed")
        self._transition(ProposalStatus.EXPIRED)

    def authorize_action(self, action: str, organization_id: OrganizationId) -> None:
        if organization_id not in (self.terms.buyer_id, self.terms.seller_id):
            raise InvariantViolation("Actor must be a deal party")
        if action in ("counter", "accept", "reject") and organization_id == self.author_organization_id:
            raise InvalidTransition("Only the other party may respond to a proposal")
        if action == "supersede" and organization_id != self.author_organization_id:
            raise InvalidTransition("Only the author may supersede a proposal")

    def _transition(self, target: ProposalStatus) -> None:
        if self.status is not ProposalStatus.SUBMITTED:
            raise InvalidTransition(f"Cannot move proposal from {self.status} to {target}")
        object.__setattr__(self, "status", target)

    def _ensure_not_expired(self, now: datetime) -> None:
        if self.expires_at is not None and self.expires_at <= now:
            raise InvalidTransition("Expired proposal cannot advance negotiation")


@dataclass(slots=True)
class NegotiationSession:
    id: NegotiationSessionId
    deal_id: DealId
    max_rounds: int
    round_count: int = 0
    current_proposal_id: ProposalId | None = None
    escalated: bool = False

    def __post_init__(self) -> None:
        if self.max_rounds < 1 or not 0 <= self.round_count <= self.max_rounds:
            raise InvariantViolation("Negotiation round counts must be within a positive limit")

    def submit(
        self,
        proposal: Proposal,
        *,
        now: datetime,
        current_proposal: Proposal | None = None,
    ) -> NegotiationSubmissionOutcome:
        if proposal.status is not ProposalStatus.SUBMITTED:
            raise InvalidTransition("Only a submitted proposal can advance negotiation")
        if proposal.deal_id != self.deal_id:
            raise InvariantViolation("Proposal belongs to a different deal")
        if proposal.based_on_proposal_id != self.current_proposal_id:
            raise InvariantViolation("Proposal predecessor is not the current proposal")
        if self.current_proposal_id is None:
            if current_proposal is not None:
                raise InvariantViolation("Negotiation has no current proposal to supersede")
        elif current_proposal is None or current_proposal.id != self.current_proposal_id:
            raise InvariantViolation("Current proposal is required to submit its successor")
        elif current_proposal.deal_id != self.deal_id:
            raise InvariantViolation("Current proposal belongs to a different deal")
        proposal._ensure_not_expired(now)
        if self.escalated:
            raise InvalidTransition("Negotiation is escalated for human review")
        if self.round_count >= self.max_rounds:
            self.escalated = True
            return NegotiationSubmissionOutcome.ESCALATION_REQUIRED
        if current_proposal is not None and current_proposal.status is ProposalStatus.SUBMITTED:
            current_proposal._ensure_not_expired(now)
            current_proposal.supersede()
        self.round_count += 1
        self.current_proposal_id = proposal.id
        return NegotiationSubmissionOutcome.SUBMITTED
