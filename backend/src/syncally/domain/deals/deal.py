"""Deal aggregate coordinating references to other commercial contexts."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from syncally.domain.shared.errors import InvalidTransition, InvariantViolation
from syncally.domain.shared.identifiers import AgreementVersionId, DealId, OrganizationId


class DealStatus(StrEnum):
    DRAFT = "DRAFT"
    NEGOTIATING = "NEGOTIATING"
    PENDING_APPROVALS = "PENDING_APPROVALS"
    AGREED = "AGREED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    DISPUTED = "DISPUTED"


@dataclass(slots=True)
class Deal:
    id: DealId
    buyer_organization_id: OrganizationId
    seller_organization_id: OrganizationId
    created_at: datetime
    status: DealStatus = DealStatus.DRAFT
    current_agreement_version_id: AgreementVersionId | None = None
    version: int = 0

    def __post_init__(self) -> None:
        if self.buyer_organization_id == self.seller_organization_id:
            raise InvariantViolation("Buyer and seller must be different organizations")

    def start_negotiation(self) -> None:
        self._transition(DealStatus.DRAFT, DealStatus.NEGOTIATING)

    def request_approval(self, agreement_version_id: AgreementVersionId) -> None:
        self._transition(DealStatus.NEGOTIATING, DealStatus.PENDING_APPROVALS)
        self.current_agreement_version_id = agreement_version_id

    def mark_agreed(self, agreement_version_id: AgreementVersionId) -> None:
        if self.status is not DealStatus.PENDING_APPROVALS:
            raise InvalidTransition(f"Cannot mark deal agreed from {self.status}")
        if self.current_agreement_version_id != agreement_version_id:
            raise InvariantViolation("Agreement version is no longer current for this deal")
        self.status = DealStatus.AGREED
        self.version += 1

    def begin_execution(self) -> None:
        self._transition(DealStatus.AGREED, DealStatus.EXECUTING)

    def complete(self) -> None:
        self._transition(DealStatus.EXECUTING, DealStatus.COMPLETED)

    def _transition(self, expected: DealStatus, target: DealStatus) -> None:
        if self.status is not expected:
            raise InvalidTransition(f"Cannot move deal from {self.status} to {target}")
        self.status = target
        self.version += 1
