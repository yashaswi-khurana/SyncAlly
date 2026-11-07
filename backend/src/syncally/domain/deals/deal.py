"""Deal aggregate coordinating references to other commercial contexts."""

from dataclasses import dataclass, field
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


@dataclass(slots=True, init=False)
class Deal:
    id: DealId
    buyer_organization_id: OrganizationId
    seller_organization_id: OrganizationId
    created_at: datetime
    _status: DealStatus = field(default=DealStatus.DRAFT, init=False, repr=False)
    current_agreement_version_id: AgreementVersionId | None = None
    version: int = 0
    pending_counterparty: bool = False

    def __init__(
        self,
        id: DealId,
        buyer_organization_id: OrganizationId,
        seller_organization_id: OrganizationId,
        created_at: datetime,
        status: DealStatus = DealStatus.DRAFT,
        current_agreement_version_id: AgreementVersionId | None = None,
        version: int = 0,
        pending_counterparty: bool = False,
    ) -> None:
        self.id = id
        self.buyer_organization_id = buyer_organization_id
        self.seller_organization_id = seller_organization_id
        self.created_at = created_at
        self._status = status
        self.current_agreement_version_id = current_agreement_version_id
        self.version = version
        self.pending_counterparty = pending_counterparty
        self.__post_init__()

    def __post_init__(self) -> None:
        if self.buyer_organization_id == self.seller_organization_id:
            raise InvariantViolation("Buyer and seller must be different organizations")

    @property
    def status(self) -> DealStatus:
        return self._status

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
        self._transition(DealStatus.PENDING_APPROVALS, DealStatus.AGREED)

    def replace_pending_candidate(self, agreement_version_id: AgreementVersionId) -> None:
        if self.current_agreement_version_id != agreement_version_id:
            raise InvariantViolation("Candidate is no longer current")
        self._transition(DealStatus.PENDING_APPROVALS, DealStatus.NEGOTIATING)
        self.current_agreement_version_id = None

    def begin_execution(self) -> None:
        self._transition(DealStatus.AGREED, DealStatus.EXECUTING)

    def complete(
        self, *, fulfillment_complete: bool, payments_reconciled: bool
    ) -> None:
        """Complete only after committed delivery and payment obligations are met."""
        if not fulfillment_complete or not payments_reconciled:
            raise InvalidTransition(
                "Deal completion requires fulfilled delivery and reconciled payments"
            )
        self._transition(DealStatus.EXECUTING, DealStatus.COMPLETED)

    def cancel(self) -> None:
        """Cancel an uncommitted deal after the application authorizes the request."""
        self._close_before_commit(DealStatus.CANCELLED)

    def mark_disputed(self) -> None:
        """Mark deal disputed upon a formal dispute case being raised."""
        if self.status in {DealStatus.COMPLETED, DealStatus.CANCELLED, DealStatus.EXPIRED}:
            raise InvalidTransition(f"Cannot dispute terminal deal in status {self.status}")
        if self.status != DealStatus.DISPUTED:
            self._status = DealStatus.DISPUTED
            self.version += 1

    def resolve_dispute(
        self, has_active_disputes: bool, resume_status: DealStatus = DealStatus.EXECUTING
    ) -> None:
        """Restore deal status when all dispute cases are resolved/withdrawn."""
        if self.status != DealStatus.DISPUTED:
            return
        if not has_active_disputes:
            self._status = resume_status
            self.version += 1

    def cancel_committed(self, *, bilateral_consent: bool, blockers: list[str]) -> None:
        """Cancel an agreed or executing deal following verified bilateral consent."""
        if not bilateral_consent:
            raise InvalidTransition("Mutual cancellation requires verified bilateral consent")
        if blockers:
            raise InvalidTransition("Cannot cancel deal with unresolved operational blockers")
        if self.status not in {DealStatus.AGREED, DealStatus.EXECUTING, DealStatus.DISPUTED}:
            raise InvalidTransition(f"Cannot mutually cancel deal in status {self.status}")
        self._status = DealStatus.CANCELLED
        self.version += 1

    def expire(self) -> None:
        """Expire an uncommitted deal after the caller confirms its deadline elapsed."""
        self._close_before_commit(DealStatus.EXPIRED)

    def _close_before_commit(self, target: DealStatus) -> None:
        if self.status not in {
            DealStatus.DRAFT,
            DealStatus.NEGOTIATING,
        }:
            raise InvalidTransition(f"Cannot move deal from {self.status} to {target}")
        self._transition(self.status, target)

    def _transition(self, expected: DealStatus, target: DealStatus) -> None:
        if self.status is not expected:
            raise InvalidTransition(f"Cannot move deal from {self.status} to {target}")
        self._status = target
        self.version += 1
