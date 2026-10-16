"""Versioned agreement aggregate with same-version bilateral approval."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from syncally.domain.agreements.trade_terms import TradeTerms
from syncally.domain.shared.errors import InvalidTransition, InvariantViolation
from syncally.domain.shared.identifiers import (
    AgreementId,
    AgreementVersionId,
    DealId,
    OrganizationId,
    UserId,
)


class AgreementStatus(StrEnum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    COMMITTED = "COMMITTED"
    SUPERSEDED = "SUPERSEDED"
    VOIDED = "VOIDED"


class ApprovalDecision(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


@dataclass(frozen=True, slots=True)
class Approval:
    organization_id: OrganizationId
    user_id: UserId
    decision: ApprovalDecision
    terms_hash: str
    created_at: datetime


@dataclass(slots=True)
class Agreement:
    id: AgreementId
    version_id: AgreementVersionId
    deal_id: DealId
    version_number: int
    terms: TradeTerms
    created_at: datetime
    status: AgreementStatus = AgreementStatus.PENDING_APPROVAL
    approvals: dict[OrganizationId, Approval] = field(default_factory=dict)
    committed_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.version_number < 1:
            raise InvariantViolation("Agreement version number must be positive")

    @property
    def terms_hash(self) -> str:
        return self.terms.terms_hash

    def record_approval(self, approval: Approval) -> None:
        self._ensure_pending()
        if approval.organization_id not in (self.terms.buyer_id, self.terms.seller_id):
            raise InvariantViolation("Only a deal party can approve its agreement")
        if approval.terms_hash != self.terms_hash:
            raise InvariantViolation("Approval must reference this exact terms hash")
        self.approvals[approval.organization_id] = approval

    def commit(self, expected_terms_hash: str, committed_at: datetime) -> None:
        self._ensure_pending()
        if expected_terms_hash != self.terms_hash:
            raise InvariantViolation("Agreement terms changed before commitment")
        for organization_id in (self.terms.buyer_id, self.terms.seller_id):
            approval = self.approvals.get(organization_id)
            if approval is None or approval.decision is not ApprovalDecision.APPROVE:
                raise InvalidTransition(
                    "Both organizations must approve the same agreement version"
                )
            if approval.terms_hash != expected_terms_hash:
                raise InvariantViolation("A stale approval cannot commit this agreement")
        self.status = AgreementStatus.COMMITTED
        self.committed_at = committed_at

    def supersede(self) -> None:
        self._ensure_pending()
        self.status = AgreementStatus.SUPERSEDED

    def _ensure_pending(self) -> None:
        if self.status is not AgreementStatus.PENDING_APPROVAL:
            raise InvalidTransition(f"Agreement is {self.status}, not pending approval")
