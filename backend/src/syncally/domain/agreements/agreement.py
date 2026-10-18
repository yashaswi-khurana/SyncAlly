"""Versioned agreement aggregate with same-version bilateral approval."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType

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
    approvals: Mapping[OrganizationId, Approval] = field(default_factory=dict)
    committed_at: datetime | None = None
    _status: AgreementStatus = field(default=AgreementStatus.PENDING_APPROVAL, init=False, repr=False)

    def __setattr__(self, name: str, value: object) -> None:
        status = getattr(self, "_status", None)
        if status is not None and status is not AgreementStatus.PENDING_APPROVAL:
            raise InvalidTransition("Finalized agreement versions are immutable; create a new version")
        if name == "_status" and hasattr(self, "_status"):
            raise InvalidTransition("Agreement status changes must use domain methods")
        if name in {"id", "version_id", "deal_id", "version_number", "created_at"} and hasattr(self, name):
            raise InvalidTransition("Agreement version identity is immutable")
        object.__setattr__(self, name, value)

    def __post_init__(self) -> None:
        if type(self.version_number) is not int or self.version_number < 1:
            raise InvariantViolation("Agreement version number must be positive")
        object.__setattr__(self, "_status", AgreementStatus.PENDING_APPROVAL)
        object.__setattr__(self, "approvals", MappingProxyType(dict(self.approvals)))

    @property
    def status(self) -> AgreementStatus:
        return self._status

    @property
    def terms_hash(self) -> str:
        return self.terms.terms_hash

    def record_approval(self, approval: Approval) -> None:
        self._ensure_pending()
        if approval.organization_id not in (self.terms.buyer_id, self.terms.seller_id):
            raise InvariantViolation("Only a deal party can approve its agreement")
        if approval.terms_hash != self.terms_hash:
            raise InvariantViolation("Approval must reference this exact terms hash")
        approvals = dict(self.approvals)
        approvals[approval.organization_id] = approval
        self.approvals = MappingProxyType(approvals)

    def commit(self, expected_terms_hash: str, committed_at: datetime) -> None:
        self._ensure_pending()
        self.terms.validate_for_commit()
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
        object.__setattr__(self, "committed_at", committed_at)
        object.__setattr__(self, "_status", AgreementStatus.COMMITTED)

    def supersede(self) -> None:
        self._ensure_pending()
        object.__setattr__(self, "_status", AgreementStatus.SUPERSEDED)

    def create_next_version(
        self,
        *,
        version_id: AgreementVersionId,
        terms: TradeTerms,
        created_at: datetime,
    ) -> Agreement:
        if self.status is not AgreementStatus.COMMITTED:
            raise InvalidTransition("Only a committed agreement can create a new version")
        if version_id == self.version_id:
            raise InvariantViolation("A new agreement version needs a new version ID")
        if terms.buyer_id != self.terms.buyer_id or terms.seller_id != self.terms.seller_id:
            raise InvariantViolation("A new agreement version must keep the same deal parties")
        if terms.terms_hash == self.terms_hash:
            raise InvariantViolation("A new agreement version must change the terms")
        return Agreement(
            id=self.id,
            version_id=version_id,
            deal_id=self.deal_id,
            version_number=self.version_number + 1,
            terms=terms,
            created_at=created_at,
        )

    def _ensure_pending(self) -> None:
        if self.status is not AgreementStatus.PENDING_APPROVAL:
            raise InvalidTransition(f"Agreement is {self.status}, not pending approval")
