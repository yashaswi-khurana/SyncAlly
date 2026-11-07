# CONTRACT: cancel-disputes-contract v1   status: FROZEN
- producer: developer   consumers: frontend, backend, test-suite
- shared paths: backend/src/syncally/domain/deals/**, backend/src/syncally/api/deals.py, frontend/src/api/**, frontend/src/deals/**

## Interface
### Domain / Models
1. CaseType: CANCELLATION | DISPUTE
2. CaseStatus: OPEN | UNDER_REVIEW | RESOLVED | REJECTED | WITHDRAWN
3. EvidenceVisibility: PRIVATE_OPERATOR | COUNTERPARTY_RESTRICTED | MUTUAL_VISIBLE
4. Scoped Case Request attributes:
   - case_id: CaseId (UUID)
   - deal_id: DealId
   - agreement_version_id: AgreementVersionId
   - agreement_terms_hash: str
   - case_type: CaseType
   - reason: str (bounded length)
   - obligation_references: list[str] (e.g. specific payment milestone or fulfillment obligation)
   - requested_by_user_id: UserId
   - requested_by_organization_id: OrganizationId
   - created_at: datetime
   - status: CaseStatus
   - resolution: str | None
   - resolved_by_user_id: UserId | None
   - resolved_at: datetime | None
   - evidence_visibility: EvidenceVisibility
   - evidence_items: list[dict]
   - bilateral_consent_counterparty_id: OrganizationId | None
   - bilateral_consent_at: datetime | None
   - operational_impact_blockers: list[str] (e.g., paid milestone or in-flight fulfillment prevents automated closure)

### Endpoints (under /api/v1/deals/{deal_id}/cases)
- POST `/api/v1/deals/{deal_id}/cases`: Propose/raise scoped dispute or cancellation request.
  - Body: case_type, reason, agreement_version_id, agreement_terms_hash, obligation_references, evidence_visibility, evidence_notes.
  - Response: 201 Created with CaseResponse.
- GET `/api/v1/deals/{deal_id}/cases`: List cases for deal, filtered by actor's organization/tenant visibility.
- POST `/api/v1/deals/{deal_id}/cases/{case_id}/respond`: Bilateral counterparty decision (CONSENT, REJECT, WITHDRAW).
  - Body: decision: CONSENT | REJECT | WITHDRAW, rationale: str.
- POST `/api/v1/deals/{deal_id}/cases/{case_id}/evidence`: Add evidence item with visibility restriction.

## Errors and edge cases
- Stale version or mismatched terms hash -> HTTP 409 Conflict (StaleAgreementVersionError)
- Forged tenant / cross-organization access -> HTTP 403 Forbidden
- Case creation does NOT trigger automated money movement, payment reversal, or liability waiver.
- Paid milestones or active fulfillment remain unchanged; unresolved policy blocks affected transitions and surfaces `operational_impact_blockers`.
- Pre-commit cancellation (DRAFT, NEGOTIATING) continues to work via existing `cancel` use-case.
- Post-commit mutual cancellation requires bilateral consent on the same agreement version/hash.

## Change rule
Only the Orchestrator edits this file. A change bumps the version and issues a CHANGE directive to consumers.
