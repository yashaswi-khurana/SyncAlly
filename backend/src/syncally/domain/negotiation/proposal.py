"""Submitted proposal snapshots and negotiation round control."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from syncally.domain.agreements.trade_terms import TradeTerms
from syncally.domain.shared.errors import InvalidTransition, InvariantViolation
from syncally.domain.shared.identifiers import (
    DealId,
    NegotiationSessionId,
    OrganizationId,
    ProposalId,
)


class ProposalStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    ACCEPTED_AS_CANDIDATE = "ACCEPTED_AS_CANDIDATE"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
    EXPIRED = "EXPIRED"


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

    def __post_init__(self) -> None:
        if self.author_organization_id not in (self.terms.buyer_id, self.terms.seller_id):
            raise InvariantViolation("Proposal author must be a party to its trade terms")
        if self.expires_at is not None and self.expires_at <= self.created_at:
            raise InvariantViolation("Proposal expiry must be later than its creation time")

    @property
    def terms_hash(self) -> str:
        return self.terms.terms_hash

    def accept_as_candidate(self) -> None:
        self._transition(ProposalStatus.ACCEPTED_AS_CANDIDATE)

    def reject(self) -> None:
        self._transition(ProposalStatus.REJECTED)

    def supersede(self) -> None:
        self._transition(ProposalStatus.SUPERSEDED)

    def _transition(self, target: ProposalStatus) -> None:
        if self.status is not ProposalStatus.SUBMITTED:
            raise InvalidTransition(f"Cannot move proposal from {self.status} to {target}")
        self.status = target


@dataclass(slots=True)
class NegotiationSession:
    id: NegotiationSessionId
    deal_id: DealId
    max_rounds: int
    round_count: int = 0
    current_proposal_id: ProposalId | None = None
    escalated: bool = False

    def __post_init__(self) -> None:
        if self.max_rounds < 1:
            raise InvariantViolation("Negotiation max_rounds must be positive")

    def submit(self, proposal: Proposal) -> None:
        if proposal.status is not ProposalStatus.SUBMITTED:
            raise InvalidTransition("Only a submitted proposal can advance negotiation")
        if proposal.deal_id != self.deal_id:
            raise InvariantViolation("Proposal belongs to a different deal")
        if proposal.based_on_proposal_id != self.current_proposal_id:
            raise InvariantViolation("Proposal predecessor is not the current proposal")
        if self.escalated:
            raise InvalidTransition("Negotiation is escalated for human review")
        if self.round_count >= self.max_rounds:
            self.escalated = True
            raise InvalidTransition("Maximum negotiation rounds reached")
        self.round_count += 1
        self.current_proposal_id = proposal.id
