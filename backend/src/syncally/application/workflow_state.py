"""Authoritative deal-state refresh for workflow activities.

Workflow inputs carry identifiers, not continuing authorization. This module
reloads the deal and its current agreement through ports so an activity can
decide what to do from persisted business state. Callers must never use an old
workflow input snapshot - such as the agreement version that started the
workflow - as proof that a version is still current.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from syncally.domain.agreements.agreement import Agreement
from syncally.domain.deals.deal import Deal, DealStatus
from syncally.domain.shared.errors import DomainError, InvariantViolation

# A deal that needs no further lifecycle work. AGREED and EXECUTING are still
# active because payment and fulfillment work may follow.
TERMINAL_DEAL_STATUSES = frozenset(
    {
        DealStatus.COMPLETED,
        DealStatus.CANCELLED,
        DealStatus.EXPIRED,
    }
)


class WorkflowDealNotFound(DomainError):
    """The persisted deal referenced by a workflow no longer exists."""


class WorkflowDealRepository(Protocol):
    """Read-only deal lookup used by workflow activities."""

    def get(self, deal_id: UUID) -> Deal | None:
        """Load a deal by its saved identifier, independent of any actor."""


class WorkflowAgreementRepository(Protocol):
    """Read-only current-agreement lookup used by workflow activities."""

    def get_current(self, deal_id: UUID) -> Agreement | None:
        """Load the deal's current agreement version, if one exists."""


@dataclass(frozen=True, slots=True)
class DealWorkflowState:
    """The authoritative state a workflow activity may act on."""

    deal: Deal
    current_agreement: Agreement | None

    @property
    def is_terminal(self) -> bool:
        """Return whether the deal has reached a lifecycle terminal status."""
        return self.deal.status in TERMINAL_DEAL_STATUSES


def parse_workflow_uuid(value: object, field_name: str) -> UUID:
    """Parse an identifier from workflow input without echoing its value."""
    if isinstance(value, UUID):
        return value
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a UUID string")
    try:
        return UUID(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must be a UUID string") from error


def load_deal_workflow_state(
    deal_id: UUID,
    deal_repository: WorkflowDealRepository,
    agreement_repository: WorkflowAgreementRepository,
) -> DealWorkflowState:
    """Reload the deal and current agreement from persistence.

    The lookup uses the saved deal identifier. Any agreement version supplied
    by an earlier workflow input is deliberately not trusted as current
    authorization; ``get_current`` resolves the version that is current now.
    """
    deal = deal_repository.get(deal_id)
    if deal is None:
        raise WorkflowDealNotFound("Deal not found")
    if deal.id != deal_id:
        raise InvariantViolation("Deal repository returned a different deal")

    current_agreement = agreement_repository.get_current(deal_id)
    if current_agreement is not None and current_agreement.deal_id != deal_id:
        raise InvariantViolation("Current agreement does not belong to the deal")
    return DealWorkflowState(deal=deal, current_agreement=current_agreement)
