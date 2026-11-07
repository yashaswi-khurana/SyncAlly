"""Domain models and value objects for Deal cancellation and dispute cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from syncally.domain.shared.errors import DomainError, InvalidTransition
from syncally.domain.shared.identifiers import AgreementVersionId, DealId, OrganizationId, UserId


class CaseType(StrEnum):
    CANCELLATION = "CANCELLATION"
    DISPUTE = "DISPUTE"


class CaseStatus(StrEnum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class EvidenceVisibility(StrEnum):
    PRIVATE_OPERATOR = "PRIVATE_OPERATOR"
    COUNTERPARTY_RESTRICTED = "COUNTERPARTY_RESTRICTED"
    MUTUAL_VISIBLE = "MUTUAL_VISIBLE"


class BilateralDecision(StrEnum):
    CONSENT = "CONSENT"
    REJECT = "REJECT"
    WITHDRAW = "WITHDRAW"


class CaseError(DomainError):
    """Base error for deal cases."""


class StaleAgreementVersionError(CaseError):
    """Case references an agreement version or hash that is no longer current."""


class CaseUnauthorizedError(CaseError):
    """Actor does not have authority to raise or decide this case."""


@dataclass(frozen=True, slots=True)
class CaseEvidence:
    evidence_id: UUID
    case_id: UUID
    submitted_by_user_id: UserId
    submitted_by_organization_id: OrganizationId
    visibility: EvidenceVisibility
    notes: str
    submitted_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DealCase:
    id: UUID
    deal_id: DealId
    agreement_version_id: AgreementVersionId
    agreement_terms_hash: str
    case_type: CaseType
    reason: str
    obligation_references: list[str]
    requested_by_user_id: UserId
    requested_by_organization_id: OrganizationId
    created_at: datetime
    status: CaseStatus = CaseStatus.OPEN
    resolution: str | None = None
    resolved_by_user_id: UserId | None = None
    resolved_at: datetime | None = None
    evidence_visibility: EvidenceVisibility = EvidenceVisibility.MUTUAL_VISIBLE
    evidence_items: list[CaseEvidence] = field(default_factory=list)
    bilateral_consent_counterparty_id: OrganizationId | None = None
    bilateral_consent_at: datetime | None = None
    operational_impact_blockers: list[str] = field(default_factory=list)
    version: int = 0

    def respond(
        self,
        *,
        decision: BilateralDecision,
        actor_organization_id: OrganizationId,
        actor_user_id: UserId,
        rationale: str,
        current_agreement_terms_hash: str,
        now: datetime,
    ) -> None:
        if self.status not in {CaseStatus.OPEN, CaseStatus.UNDER_REVIEW}:
            raise InvalidTransition(f"Cannot respond to case in status {self.status}")

        if decision == BilateralDecision.WITHDRAW:
            if actor_organization_id != self.requested_by_organization_id:
                raise CaseUnauthorizedError("Only the requesting organization may withdraw a case")
            self.status = CaseStatus.WITHDRAWN
            self.resolution = rationale
            self.resolved_by_user_id = actor_user_id
            self.resolved_at = now
            self.version += 1
            return

        # Bilateral decisions (CONSENT, REJECT) must come from the counterparty
        if actor_organization_id == self.requested_by_organization_id:
            raise CaseUnauthorizedError("Counterparty decision required; initiating organization cannot self-decide")

        if current_agreement_terms_hash != self.agreement_terms_hash:
            raise StaleAgreementVersionError("Agreement terms hash has changed since this case was raised")

        if decision == BilateralDecision.REJECT:
            self.status = CaseStatus.REJECTED
            self.resolution = rationale
            self.resolved_by_user_id = actor_user_id
            self.resolved_at = now
            self.version += 1
            return

        if decision == BilateralDecision.CONSENT:
            self.bilateral_consent_counterparty_id = actor_organization_id
            self.bilateral_consent_at = now
            if self.operational_impact_blockers:
                # Operational blockers prevent automated closure
                self.status = CaseStatus.UNDER_REVIEW
                self.resolution = (
                    f"Bilateral consent recorded. Automated closure blocked: "
                    f"{'; '.join(self.operational_impact_blockers)}"
                )
            else:
                self.status = CaseStatus.RESOLVED
                self.resolution = rationale
                self.resolved_by_user_id = actor_user_id
                self.resolved_at = now
            self.version += 1

    def add_evidence(self, evidence: CaseEvidence) -> None:
        if self.status not in {CaseStatus.OPEN, CaseStatus.UNDER_REVIEW}:
            raise InvalidTransition(f"Cannot add evidence to case in status {self.status}")
        self.evidence_items.append(evidence)
        self.version += 1
