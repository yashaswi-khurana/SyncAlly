"""Explicit human negotiation commands; no approval or execution authority."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol
from uuid import UUID

from syncally.domain.agreements.trade_terms import TradeTerms
from syncally.domain.shared.errors import DomainError, InvariantViolation

NegotiationActionKind = Literal["submit", "counter", "accept", "reject", "supersede", "expire"]


class NegotiationNotFound(DomainError):
    pass


class NegotiationConflict(DomainError):
    pass


class NegotiationOrganizationRequired(DomainError):
    pass


@dataclass(frozen=True)
class ProposalBase:
    id: UUID
    terms_hash: str
    status: str


@dataclass(frozen=True)
class CandidateAcknowledgement:
    id: UUID
    version_number: int
    terms_hash: str
    proposal_id: UUID


@dataclass(frozen=True)
class EvidenceReference:
    fact_id: UUID
    version: int


@dataclass(frozen=True)
class NegotiationCommand:
    deal_id: UUID
    user_id: UUID
    organization_id: UUID | None
    command_id: UUID
    action: NegotiationActionKind
    expected_deal_revision: int
    base: ProposalBase | None
    terms: TradeTerms | None = None
    expires_at: datetime | None = None
    supersede_current_candidate: CandidateAcknowledgement | None = None
    evidence: tuple[EvidenceReference, ...] = ()


class NegotiationRepository(Protocol):
    def execute(self, command: NegotiationCommand, *, now: datetime) -> dict[str, Any]: ...


def negotiate(command: NegotiationCommand, repository: NegotiationRepository, *, now: datetime) -> dict[str, Any]:
    if command.action not in ("submit", "counter", "accept", "reject", "supersede", "expire"):
        raise InvariantViolation("Unknown negotiation action")
    if command.expected_deal_revision < 0:
        raise InvariantViolation("Expected deal revision must be nonnegative")
    if command.action in ("submit", "counter"):
        if command.terms is None:
            raise InvariantViolation("Submission requires reviewed terms")
        command.terms.validate_for_commit()
    elif command.terms is not None or command.expires_at is not None or command.evidence:
        raise InvariantViolation("Only submission and counter may supply terms or evidence")
    if len(command.evidence) > 100 or len({ref.fact_id for ref in command.evidence}) != len(command.evidence):
        raise InvariantViolation("Evidence references must be bounded and distinct")
    return repository.execute(command, now=now)