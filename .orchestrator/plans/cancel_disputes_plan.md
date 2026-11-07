# Architectural & Implementation Plan: Step 08 Cancel Disputes (F8)

**Target Agent:** DEVELOPER (coordinated via Orchestrator/Parent `ab818dbc-79f2-4302-a819-05c92dc85c9d`)  
**Contract Reference:** `.orchestrator/contracts/cancel-disputes-contract.md` (FROZEN v1)  
**Status:** READY FOR IMPLEMENTATION

---

## 1. Executive Summary & Existing vs. Required Behavior

### Existing Codebase Behavior
- **DealStatus enum** already contains `CANCELLED` and `DISPUTED` in `backend/src/syncally/domain/deals/deal.py`.
- **Pre-commit cancellation**: `deal.cancel()` calls `_close_before_commit(DealStatus.CANCELLED)` which strictly requires `DRAFT` or `NEGOTIATING`. Any attempt to cancel from `PENDING_APPROVALS`, `AGREED`, or `EXECUTING` raises `InvalidTransition`.
- **Terminal statuses**: `TERMINAL_DEAL_STATUSES` in `workflow_state.py` includes `COMPLETED`, `CANCELLED`, `EXPIRED`. `DISPUTED` is non-terminal because it requires operational resolution.
- **Amendment assessment**: In `syncally/domain/agreements/amendment.py`, `assess_amendment_impact()` already anticipates `active_cases: list[dict[str, Any]] | None` and emits blockers: `"Deal has an active case {case_id}; resolution required before amending terms."`
- **Missing functionality**: No domain entities, persistence models, migration, application use cases, API routes, or UI components exist for raising, tracking, or resolving cancellation or dispute cases. Post-commit deals cannot be mutually cancelled, and disputes cannot be formally lodged or resolved.

### What F8 Requires
1. **Preserve pre-commit cancellation**: Unilateral cancellation for uncommitted deals (`DRAFT`, `NEGOTIATING`) continues to work without modification or regression.
2. **Post-commit cancellation & dispute cases**: Structured `DealCase` entities scoped to an exact `agreement_version_id` and `terms_hash`.
3. **Case creation is NOT automated settlement**: Raising a case does not trigger money movement, refund, payment reversal, or liability waiver. Paid milestones and active shipments remain intact. Operational consequences are surfaced as `operational_impact_blockers`.
4. **Bilateral counterparty authorization**: Mutual cancellation requires consent from the counterparty on the matching `agreement_version_id` and `terms_hash`. Self-consent and forged tenant actions are strictly rejected with HTTP 403 Forbidden.
5. **Private & scoped evidence**: Tenant-based filtering of evidence according to `EvidenceVisibility` (`PRIVATE_OPERATOR`, `COUNTERPARTY_RESTRICTED`, `MUTUAL_VISIBLE`).
6. **Concurrency & serialization**: Optimistic version checking (`409 Conflict`), atomic DB transactions covering case state + deal state + outbox + audit events, and absolutely no external network calls inside DB transactions.
7. **Additive migration 0025**: `0025_cancel_disputes` on top of `0024_amendments` with an explicit history-loss downgrade guard.
8. **DealDetailPage UI**: Cases section/tab, Raise Case form, Evidence listing with visibility tags, Bilateral decision controls (Consent / Reject / Withdraw), and Blocker warning banners.
9. **Import safety fix in `graph.py`**: Safe guard around `langgraph` import and compilation so the BaseSettings discovery test runner passes without error.

---

## 2. Domain Entities & Value Objects

### File: `backend/src/syncally/domain/deals/cases.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from syncally.domain.shared.errors import DomainError, InvalidTransition, InvariantViolation
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
                # Operational blockers prevent automated resolution
                self.status = CaseStatus.UNDER_REVIEW
                self.resolution = f"Bilateral consent recorded. Automated closure blocked: {'; '.join(self.operational_impact_blockers)}"
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
```

---

## 3. Deal Aggregate Coordination

### File: `backend/src/syncally/domain/deals/deal.py`
Add explicit methods to coordinate case outcomes while preserving pre-commit cancellation:

```python
    def mark_disputed(self) -> None:
        """Mark deal disputed upon a formal dispute case being raised."""
        if self.status in {DealStatus.COMPLETED, DealStatus.CANCELLED, DealStatus.EXPIRED}:
            raise InvalidTransition(f"Cannot dispute terminal deal in status {self.status}")
        if self.status != DealStatus.DISPUTED:
            self._status = DealStatus.DISPUTED
            self.version += 1

    def resolve_dispute(self, has_active_disputes: bool, resume_status: DealStatus = DealStatus.EXECUTING) -> None:
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
```

---

## 4. Persistence Models & Alembic Migration 0025

### File: `backend/src/syncally/infrastructure/models/deal_cases.py`
Create SQLAlchemy models: `DealCaseModel`, `DealCaseEvidenceModel`.

### Migration: `backend/alembic/versions/0025_cancel_disputes.py`
- `revision = "0025_cancel_disputes"`
- `down_revision = "0024_amendments"`
- `upgrade()` creates `deal_cases` and `deal_case_evidence`.
- `downgrade()` includes mandatory history-loss check.

---

## 5. Application Layer: Use Cases & Operational Impact Assessment

### File: `backend/src/syncally/application/deal_cases.py`
- Protocol `DealCaseRepository`
- Impact assessment `assess_deal_case_blockers`
- Use Cases:
  - `raise_deal_case`
  - `respond_to_deal_case`
  - `add_case_evidence`
  - `list_deal_cases`
- Outbox events: `deal.case.raised`, `deal.case.responded`, `deal.case.evidence_added`
- Audit events: `DEAL_CASE_RAISED`, `DEAL_CASE_RESPONDED`, `DEAL_CASE_EVIDENCE_ADDED`

---

## 6. HTTP API Layer

### File: `backend/src/syncally/api/deals.py`
- `POST /deals/{deal_id}/cases`
- `GET /deals/{deal_id}/cases`
- `POST /deals/{deal_id}/cases/{case_id}/respond`
- `POST /deals/{deal_id}/cases/{case_id}/evidence`

---

## 7. Frontend Integration

### File: `frontend/src/api/types.ts`
### File: `frontend/src/api/client.ts`
### File: `frontend/src/deals/DealCasesPanel.tsx`
### File: `frontend/src/deals/DealDetailPage.tsx`

---

## 8. Import Safety Fix for `backend/src/syncally/infrastructure/ai/graph.py`
Safe optional import for `langgraph` and deterministic fallback to `_check_readiness` and `draft_proposal_from_context`.

---

## 9. Verification & Test Plan
- `backend/tests/test_deal_cases.py`
- `frontend/src/deals/DealDetailPage.test.tsx`
- Focused runner script
- Static gates (ruff, npm run lint:check, npm run build, git diff --check)
