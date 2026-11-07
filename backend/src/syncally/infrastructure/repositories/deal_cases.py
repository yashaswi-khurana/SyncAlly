"""SQLAlchemy implementation of the deal case repository port."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from syncally.domain.deals.cases import (
    CaseEvidence,
    CaseStatus,
    CaseType,
    DealCase,
    EvidenceVisibility,
)
from syncally.domain.shared.identifiers import AgreementVersionId, DealId, OrganizationId, UserId
from syncally.infrastructure.models.deal_cases import DealCaseEvidenceModel, DealCaseModel
from syncally.infrastructure.repositories._timestamps import as_utc


def _evidence_to_domain(row: DealCaseEvidenceModel) -> CaseEvidence:
    return CaseEvidence(
        evidence_id=row.id,
        case_id=row.case_id,
        submitted_by_user_id=UserId(row.submitted_by_user_id),
        submitted_by_organization_id=OrganizationId(row.submitted_by_organization_id),
        visibility=EvidenceVisibility(row.visibility),
        notes=row.notes,
        submitted_at=as_utc(row.submitted_at),
        metadata=dict(row.metadata_payload or {}),
    )


def _to_domain(row: DealCaseModel) -> DealCase:
    return DealCase(
        id=row.id,
        deal_id=DealId(row.deal_id),
        agreement_version_id=AgreementVersionId(row.agreement_version_id),
        agreement_terms_hash=row.agreement_terms_hash,
        case_type=CaseType(row.case_type),
        reason=row.reason,
        obligation_references=list(row.obligation_references or []),
        requested_by_user_id=UserId(row.requested_by_user_id),
        requested_by_organization_id=OrganizationId(row.requested_by_organization_id),
        created_at=as_utc(row.created_at),
        status=CaseStatus(row.status),
        resolution=row.resolution,
        resolved_by_user_id=UserId(row.resolved_by_user_id) if row.resolved_by_user_id else None,
        resolved_at=as_utc(row.resolved_at) if row.resolved_at else None,
        evidence_visibility=EvidenceVisibility(row.evidence_visibility),
        evidence_items=[_evidence_to_domain(e) for e in row.evidence_items],
        bilateral_consent_counterparty_id=(
            OrganizationId(row.bilateral_consent_counterparty_id)
            if row.bilateral_consent_counterparty_id
            else None
        ),
        bilateral_consent_at=as_utc(row.bilateral_consent_at) if row.bilateral_consent_at else None,
        operational_impact_blockers=list(row.operational_impact_blockers or []),
        version=row.version,
    )


class SqlAlchemyDealCaseRepository:
    """DealCase repository backed by a SQLAlchemy session."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, case_id: UUID) -> DealCase | None:
        row = self._db.get(DealCaseModel, case_id)
        return _to_domain(row) if row is not None else None

    def list_for_deal(self, deal_id: UUID) -> list[DealCase]:
        rows = list(
            self._db.scalars(
                select(DealCaseModel)
                .where(DealCaseModel.deal_id == deal_id)
                .order_by(DealCaseModel.created_at.asc())
            )
        )
        return [_to_domain(row) for row in rows]

    def has_active_disputes(self, deal_id: UUID) -> bool:
        stmt = (
            select(DealCaseModel.id)
            .where(
                DealCaseModel.deal_id == deal_id,
                DealCaseModel.case_type == CaseType.DISPUTE.value,
                DealCaseModel.status.in_([CaseStatus.OPEN.value, CaseStatus.UNDER_REVIEW.value]),
            )
            .limit(1)
        )
        return self._db.scalar(stmt) is not None

    def save(self, case: DealCase) -> DealCase:
        row = self._db.get(DealCaseModel, case.id)
        if row is None:
            row = DealCaseModel(
                id=case.id,
                deal_id=case.deal_id,
                agreement_version_id=case.agreement_version_id,
                agreement_terms_hash=case.agreement_terms_hash,
                case_type=case.case_type.value,
                reason=case.reason,
                obligation_references=case.obligation_references,
                requested_by_user_id=case.requested_by_user_id,
                requested_by_organization_id=case.requested_by_organization_id,
                status=case.status.value,
                resolution=case.resolution,
                resolved_by_user_id=case.resolved_by_user_id,
                resolved_at=case.resolved_at,
                evidence_visibility=case.evidence_visibility.value,
                bilateral_consent_counterparty_id=case.bilateral_consent_counterparty_id,
                bilateral_consent_at=case.bilateral_consent_at,
                operational_impact_blockers=case.operational_impact_blockers,
                version=case.version,
            )
            self._db.add(row)
        else:
            row.status = case.status.value
            row.resolution = case.resolution
            row.resolved_by_user_id = case.resolved_by_user_id
            row.resolved_at = case.resolved_at
            row.bilateral_consent_counterparty_id = case.bilateral_consent_counterparty_id
            row.bilateral_consent_at = case.bilateral_consent_at
            row.operational_impact_blockers = case.operational_impact_blockers
            row.version = case.version

        # Sync evidence items
        existing_evidence_ids = {e.id for e in row.evidence_items}
        for item in case.evidence_items:
            if item.evidence_id not in existing_evidence_ids:
                row.evidence_items.append(
                    DealCaseEvidenceModel(
                        id=item.evidence_id,
                        case_id=case.id,
                        submitted_by_user_id=item.submitted_by_user_id,
                        submitted_by_organization_id=item.submitted_by_organization_id,
                        visibility=item.visibility.value,
                        notes=item.notes,
                        metadata_payload=item.metadata,
                        submitted_at=item.submitted_at,
                    )
                )

        self._db.flush()
        return _to_domain(row)

    def add_evidence(self, case_id: UUID, evidence: CaseEvidence) -> None:
        row = DealCaseEvidenceModel(
            id=evidence.evidence_id,
            case_id=case_id,
            submitted_by_user_id=evidence.submitted_by_user_id,
            submitted_by_organization_id=evidence.submitted_by_organization_id,
            visibility=evidence.visibility.value,
            notes=evidence.notes,
            metadata_payload=evidence.metadata,
            submitted_at=evidence.submitted_at,
        )
        self._db.add(row)
        self._db.flush()
