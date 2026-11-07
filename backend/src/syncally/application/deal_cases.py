"""Deal cancellation and dispute case application use cases and blocker assessment."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from syncally.domain.deals.cases import (
    BilateralDecision,
    CaseEvidence,
    CaseStatus,
    CaseType,
    CaseUnauthorizedError,
    DealCase,
    EvidenceVisibility,
    StaleAgreementVersionError,
)
from syncally.domain.deals.deal import DealStatus
from syncally.domain.shared.errors import DomainError, InvalidTransition
from syncally.domain.shared.identifiers import AgreementVersionId, DealId, OrganizationId, UserId
from syncally.infrastructure.models.agreements import AgreementVersion, Obligation
from syncally.infrastructure.models.deal_cases import DealCaseModel
from syncally.infrastructure.models.deals import Deal as DealModel
from syncally.infrastructure.models.fulfillment import FulfillmentEvent
from syncally.infrastructure.models.operations import AuditEvent, OutboxEvent
from syncally.infrastructure.models.payments import PaymentIntent, PaymentMilestone
from syncally.infrastructure.repositories.deal_cases import SqlAlchemyDealCaseRepository
from syncally.infrastructure.repositories.deals import SqlAlchemyDealRepository


class DealNotFound(DomainError):
    """The requested deal does not exist or the actor is not a participant."""


class DealCaseNotFound(DomainError):
    """The requested case does not exist."""


class DealCaseRepository(Protocol):
    """Persistence port for DealCase."""

    def get(self, case_id: UUID) -> DealCase | None:
        ...

    def list_for_deal(self, deal_id: UUID) -> list[DealCase]:
        ...

    def has_active_disputes(self, deal_id: UUID) -> bool:
        ...

    def save(self, case: DealCase) -> DealCase:
        ...

    def add_evidence(self, case_id: UUID, evidence: CaseEvidence) -> None:
        ...


def assess_deal_case_blockers(
    db: Session,
    deal_id: UUID,
    agreement_version_id: UUID | None = None,
    obligation_references: list[str] | None = None,
) -> list[str]:
    """Detect operational facts (paid milestones, fulfilled obligations) that block closure."""
    blockers: list[str] = []

    # 1. Payment operational facts
    milestone_stmt = select(PaymentMilestone).where(PaymentMilestone.deal_id == deal_id)
    if agreement_version_id:
        milestone_stmt = milestone_stmt.where(PaymentMilestone.agreement_version_id == agreement_version_id)
    milestones = list(db.scalars(milestone_stmt))

    for m in milestones:
        has_paid = m.status == "PAID"
        if not has_paid:
            paid_intent = db.scalar(
                select(PaymentIntent.id).where(
                    PaymentIntent.deal_id == deal_id,
                    PaymentIntent.payment_milestone_id == m.id,
                    PaymentIntent.status == "PAID",
                ).limit(1)
            )
            has_paid = paid_intent is not None

        ref = m.source_terms_reference or f"payment_terms[{m.sequence_number - 1}]"
        if has_paid:
            blockers.append(
                f"Payment milestone {ref} ({m.amount} {m.currency}) is PAID; requires operational settlement"
            )

        active_intent = db.scalar(
            select(PaymentIntent.id).where(
                PaymentIntent.deal_id == deal_id,
                PaymentIntent.payment_milestone_id == m.id,
                PaymentIntent.status.not_in(["PAID", "FAILED", "CANCELLED"]),
            ).limit(1)
        )
        if active_intent:
            blockers.append(
                f"Payment milestone {ref} has an active in-flight payment intent"
            )

    # 2. Fulfillment operational facts
    obl_stmt = select(Obligation).where(Obligation.deal_id == deal_id)
    if agreement_version_id:
        obl_stmt = obl_stmt.where(Obligation.agreement_version_id == agreement_version_id)
    obligations = list(db.scalars(obl_stmt))

    for obl in obligations:
        events = list(db.scalars(select(FulfillmentEvent).where(FulfillmentEvent.obligation_id == obl.id)))
        shipped = sum(
            (Decimal(str(e.quantity)) for e in events if e.event_type == "SHIPPED"),
            Decimal(0),
        )
        confirmed = sum(
            (Decimal(str(e.quantity)) for e in events if e.event_type == "CONFIRMED"),
            Decimal(0),
        )
        if shipped > 0 or confirmed > 0 or obl.status in {"SHIPPED", "CONFIRMED", "DELIVERED"}:
            ref = obl.source_terms_reference or str(obl.id)
            blockers.append(
                f"Shipment obligation {ref} has fulfilled quantity (shipped: {shipped}, confirmed: {confirmed}); requires physical return or operational settlement"
            )

    return blockers


@dataclass(frozen=True)
class RaiseDealCaseCommand:
    deal_id: UUID
    case_type: CaseType
    reason: str
    agreement_version_id: UUID
    agreement_terms_hash: str
    case_id: UUID | None = None
    obligation_references: list[str] = field(default_factory=list)
    evidence_visibility: EvidenceVisibility = EvidenceVisibility.MUTUAL_VISIBLE
    evidence_notes: str | None = None
    evidence_metadata: dict[str, Any] = field(default_factory=dict)
    actor_user_id: UUID = field(default_factory=uuid4)
    actor_organization_id: UUID = field(default_factory=uuid4)
    now: datetime | None = None


def raise_deal_case(
    db: Session,
    command: RaiseDealCaseCommand,
) -> DealCase:
    """Raise a scoped cancellation or dispute case with atomic audit and outbox events."""
    now = command.now or datetime.now(UTC)

    # Serialize case creation and resolution on the deal row. Amendment writes also
    # update this row, so the committed terms are re-read after acquiring the lock.
    deal_repo = SqlAlchemyDealRepository(db)
    deal_row = db.scalar(
        select(DealModel)
        .where(DealModel.id == command.deal_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if deal_row is None:
        raise DealNotFound(f"Deal {command.deal_id} not found")
    deal = deal_repo.get(command.deal_id)
    if deal is None:
        raise DealNotFound(f"Deal {command.deal_id} not found")

    deal_parties = {deal.buyer_organization_id, deal.seller_organization_id}
    if command.actor_organization_id not in deal_parties:
        raise CaseUnauthorizedError("Actor organization is not a party to this deal")

    case_id = command.case_id or uuid4()
    case_repo = SqlAlchemyDealCaseRepository(db)
    existing_case = case_repo.get(case_id)
    if existing_case is not None:
        initial_evidence = existing_case.evidence_items[0] if existing_case.evidence_items else None
        same_request = (
            existing_case.deal_id == deal.id
            and existing_case.case_type == command.case_type
            and existing_case.reason == command.reason
            and existing_case.agreement_version_id == command.agreement_version_id
            and existing_case.agreement_terms_hash == command.agreement_terms_hash
            and existing_case.obligation_references == command.obligation_references
            and existing_case.requested_by_user_id == command.actor_user_id
            and existing_case.requested_by_organization_id == command.actor_organization_id
            and existing_case.evidence_visibility == command.evidence_visibility
        )
        if command.evidence_notes:
            same_request = same_request and any(
                item is initial_evidence
                and item.submitted_by_user_id == command.actor_user_id
                and item.submitted_by_organization_id == command.actor_organization_id
                and item.visibility == command.evidence_visibility
                and item.notes == command.evidence_notes
                and item.metadata == command.evidence_metadata
                for item in existing_case.evidence_items
            )
        else:
            same_request = same_request and initial_evidence is None
        if same_request:
            return existing_case
        raise InvalidTransition("Case ID is already used by a different request")

    if deal.status in {DealStatus.CANCELLED, DealStatus.EXPIRED} or (
        deal.status == DealStatus.COMPLETED and command.case_type != CaseType.DISPUTE
    ):
        raise InvalidTransition(f"Cannot raise a case on terminal deal in status {deal.status}")

    if deal.current_agreement_version_id is None:
        raise InvalidTransition("Cannot raise cancellation/dispute case on uncommitted deal; use direct cancel")

    if deal.current_agreement_version_id != command.agreement_version_id:
        raise StaleAgreementVersionError("Agreement version does not match current committed agreement")

    version_row = db.get(AgreementVersion, command.agreement_version_id)
    if version_row is None or version_row.terms_hash != command.agreement_terms_hash:
        raise StaleAgreementVersionError("Agreement terms hash does not match current committed agreement")

    if command.evidence_metadata and not command.evidence_notes:
        raise InvalidTransition("Delivery exception evidence requires a description")
    if command.evidence_metadata:
        if (
            command.case_type != CaseType.DISPUTE
            or command.actor_organization_id != deal.buyer_organization_id
            or command.evidence_metadata.get("kind") != "DELIVERY_EXCEPTION"
        ):
            raise InvalidTransition("Delivery exception evidence must be submitted by the buyer as a dispute")
        try:
            fulfillment_event_id = UUID(str(command.evidence_metadata["fulfillment_event_id"]))
            affected_value = command.evidence_metadata.get("affected_quantity")
            affected_quantity = Decimal(str(affected_value)) if affected_value is not None else None
            unit = str(command.evidence_metadata["unit"])
        except (KeyError, ValueError, ArithmeticError) as error:
            raise InvalidTransition("Delivery exception evidence is incomplete") from error
        shipment = db.get(FulfillmentEvent, fulfillment_event_id)
        obligation = db.get(Obligation, shipment.obligation_id) if shipment else None
        if (
            shipment is None
            or obligation is None
            or shipment.deal_id != deal.id
            or obligation.deal_id != deal.id
            or obligation.agreement_version_id != command.agreement_version_id
            or shipment.agreement_version_id != command.agreement_version_id
            or shipment.terms_hash != command.agreement_terms_hash
            or shipment.event_type != "SHIPPED"
            or (obligation.source_terms_reference or str(obligation.id)) not in command.obligation_references
            or shipment.unit != unit
            or (
                affected_quantity is not None
                and (
                    not affected_quantity.is_finite()
                    or affected_quantity <= 0
                    or affected_quantity > Decimal(shipment.quantity)
                )
            )
        ):
            raise InvalidTransition("Delivery exception must reference a current shipment and valid affected quantity")

    # 2. Blockers calculation
    blockers = assess_deal_case_blockers(
        db,
        deal.id,
        command.agreement_version_id,
        command.obligation_references,
    )

    # 3. Create case
    evidence_items: list[CaseEvidence] = []
    if command.evidence_notes:
        evidence_items.append(
            CaseEvidence(
                evidence_id=uuid4(),
                case_id=case_id,
                submitted_by_user_id=UserId(command.actor_user_id),
                submitted_by_organization_id=OrganizationId(command.actor_organization_id),
                visibility=command.evidence_visibility,
                notes=command.evidence_notes,
                submitted_at=now,
                metadata=dict(command.evidence_metadata),
            )
        )

    case = DealCase(
        id=case_id,
        deal_id=DealId(deal.id),
        agreement_version_id=AgreementVersionId(command.agreement_version_id),
        agreement_terms_hash=command.agreement_terms_hash,
        case_type=command.case_type,
        reason=command.reason,
        obligation_references=list(command.obligation_references),
        requested_by_user_id=UserId(command.actor_user_id),
        requested_by_organization_id=OrganizationId(command.actor_organization_id),
        created_at=now,
        status=CaseStatus.OPEN,
        evidence_visibility=command.evidence_visibility,
        evidence_items=evidence_items,
        operational_impact_blockers=blockers,
        version=0,
    )

    # 4. If dispute, mark deal disputed
    if case.case_type == CaseType.DISPUTE and deal.status != DealStatus.COMPLETED:
        deal.mark_disputed()
        deal_row.status = deal.status.value
        deal_row.version = deal.version

    saved_case = case_repo.save(case)

    # 5. Outbox & Audit events
    db.add(
        OutboxEvent(
            aggregate_type="deal",
            aggregate_id=deal.id,
            event_type="deal.case.raised",
            payload={
                "deal_id": str(deal.id),
                "case_id": str(saved_case.id),
                "case_type": saved_case.case_type.value,
                "requested_by_organization_id": str(saved_case.requested_by_organization_id),
                "status": saved_case.status.value,
                "blockers": saved_case.operational_impact_blockers,
            },
        )
    )
    db.add(
        AuditEvent(
            aggregate_type="deal_case",
            aggregate_id=saved_case.id,
            event_type="DEAL_CASE_RAISED",
            actor_type="user",
            actor_id=str(command.actor_user_id),
            occurred_at=now,
            correlation_id=None,
            payload={
                "deal_id": str(deal.id),
                "case_type": saved_case.case_type.value,
                "reason": saved_case.reason,
                "status": saved_case.status.value,
                "blockers_count": len(saved_case.operational_impact_blockers),
            },
        )
    )
    db.flush()
    return saved_case


@dataclass(frozen=True)
class RespondToDealCaseCommand:
    case_id: UUID
    decision: BilateralDecision
    rationale: str
    actor_user_id: UUID
    actor_organization_id: UUID
    now: datetime | None = None


def respond_to_deal_case(
    db: Session,
    command: RespondToDealCaseCommand,
) -> DealCase:
    """Respond to a deal case (CONSENT, REJECT, WITHDRAW) with bilateral verification."""
    now = command.now or datetime.now(UTC)

    case_repo = SqlAlchemyDealCaseRepository(db)
    case = case_repo.get(command.case_id)
    if case is None:
        raise DealCaseNotFound(f"Case {command.case_id} not found")

    # Use the same lock as case creation so resolving the last active dispute
    # cannot race with another dispute being inserted.
    deal_row = db.scalar(
        select(DealModel)
        .where(DealModel.id == case.deal_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if deal_row is None:
        raise DealNotFound(f"Deal {case.deal_id} not found")
    case_row = db.get(DealCaseModel, command.case_id)
    if case_row is None:
        raise DealCaseNotFound(f"Case {command.case_id} not found")
    db.refresh(case_row)
    db.expire(case_row, ["evidence_items"])
    case = case_repo.get(command.case_id)
    if case is None:
        raise DealCaseNotFound(f"Case {command.case_id} not found")

    deal_repo = SqlAlchemyDealRepository(db)
    deal = deal_repo.get(case.deal_id)
    if deal is None:
        raise DealNotFound(f"Deal {case.deal_id} not found")

    deal_parties = {deal.buyer_organization_id, deal.seller_organization_id}
    if command.actor_organization_id not in deal_parties:
        raise CaseUnauthorizedError("Actor organization is not a party to this deal")

    # Current terms hash check
    version_row = db.get(AgreementVersion, case.agreement_version_id)
    current_terms_hash = version_row.terms_hash if version_row else ""

    # Call domain respond method (validates bilateral permissions and hash match)
    case.respond(
        decision=command.decision,
        actor_organization_id=OrganizationId(command.actor_organization_id),
        actor_user_id=UserId(command.actor_user_id),
        rationale=command.rationale,
        current_agreement_terms_hash=current_terms_hash,
        now=now,
    )

    saved_case = case_repo.save(case)

    # Status coordination
    if case.status == CaseStatus.RESOLVED and case.case_type == CaseType.CANCELLATION:
        # Bilateral consent recorded with no operational blockers -> cancel committed deal
        deal.cancel_committed(bilateral_consent=True, blockers=case.operational_impact_blockers)
        deal_row = db.get(DealModel, deal.id)
        if deal_row:
            deal_row.status = deal.status.value
            deal_row.version = deal.version
    elif case.case_type == CaseType.DISPUTE and case.status in {
        CaseStatus.RESOLVED,
        CaseStatus.REJECTED,
        CaseStatus.WITHDRAWN,
    }:
        # Check if deal still has active disputes
        active_disputes = case_repo.has_active_disputes(deal.id)
        if not active_disputes:
            deal.resolve_dispute(has_active_disputes=False)
            deal_row.status = deal.status.value
            deal_row.version = deal.version

    # Outbox & Audit events
    db.add(
        OutboxEvent(
            aggregate_type="deal",
            aggregate_id=deal.id,
            event_type="deal.case.responded",
            payload={
                "deal_id": str(deal.id),
                "case_id": str(saved_case.id),
                "decision": command.decision.value,
                "status": saved_case.status.value,
                "deal_status": deal.status.value,
            },
        )
    )
    db.add(
        AuditEvent(
            aggregate_type="deal_case",
            aggregate_id=saved_case.id,
            event_type="DEAL_CASE_RESPONDED",
            actor_type="user",
            actor_id=str(command.actor_user_id),
            occurred_at=now,
            correlation_id=None,
            payload={
                "deal_id": str(deal.id),
                "decision": command.decision.value,
                "rationale": command.rationale,
                "status": saved_case.status.value,
            },
        )
    )
    db.flush()
    return saved_case


@dataclass(frozen=True)
class AddCaseEvidenceCommand:
    case_id: UUID
    notes: str
    visibility: EvidenceVisibility
    actor_user_id: UUID
    actor_organization_id: UUID
    metadata: dict[str, Any] = field(default_factory=dict)
    now: datetime | None = None


def add_case_evidence(
    db: Session,
    command: AddCaseEvidenceCommand,
) -> CaseEvidence:
    """Add evidence to an open or under-review case with visibility restriction."""
    now = command.now or datetime.now(UTC)

    case_repo = SqlAlchemyDealCaseRepository(db)
    case = case_repo.get(command.case_id)
    if case is None:
        raise DealCaseNotFound(f"Case {command.case_id} not found")

    deal_repo = SqlAlchemyDealRepository(db)
    deal = deal_repo.get(case.deal_id)
    if deal is None:
        raise DealNotFound(f"Deal {case.deal_id} not found")

    deal_parties = {deal.buyer_organization_id, deal.seller_organization_id}
    if command.actor_organization_id not in deal_parties:
        raise CaseUnauthorizedError("Actor organization is not a party to this deal")

    evidence = CaseEvidence(
        evidence_id=uuid4(),
        case_id=case.id,
        submitted_by_user_id=UserId(command.actor_user_id),
        submitted_by_organization_id=OrganizationId(command.actor_organization_id),
        visibility=command.visibility,
        notes=command.notes,
        submitted_at=now,
        metadata=dict(command.metadata),
    )

    case.add_evidence(evidence)
    case_repo.save(case)

    # Outbox & Audit
    db.add(
        OutboxEvent(
            aggregate_type="deal",
            aggregate_id=deal.id,
            event_type="deal.case.evidence_added",
            payload={
                "deal_id": str(deal.id),
                "case_id": str(case.id),
                "evidence_id": str(evidence.evidence_id),
                "visibility": evidence.visibility.value,
            },
        )
    )
    db.add(
        AuditEvent(
            aggregate_type="deal_case",
            aggregate_id=case.id,
            event_type="DEAL_CASE_EVIDENCE_ADDED",
            actor_type="user",
            actor_id=str(command.actor_user_id),
            occurred_at=now,
            correlation_id=None,
            payload={
                "evidence_id": str(evidence.evidence_id),
                "visibility": evidence.visibility.value,
            },
        )
    )
    db.flush()
    return evidence


def list_deal_cases(
    db: Session,
    deal_id: UUID,
    actor_organization_id: UUID,
    *,
    is_operator: bool = False,
) -> list[DealCase]:
    """List deal cases, filtering evidence according to actor's tenant visibility."""
    deal_repo = SqlAlchemyDealRepository(db)
    deal = deal_repo.get(deal_id)
    if deal is None:
        raise DealNotFound(f"Deal {deal_id} not found")

    deal_parties = {deal.buyer_organization_id, deal.seller_organization_id}
    if not is_operator and actor_organization_id not in deal_parties:
        raise CaseUnauthorizedError("Actor organization is not a party to this deal")

    case_repo = SqlAlchemyDealCaseRepository(db)
    cases = case_repo.list_for_deal(deal_id)

    filtered_cases: list[DealCase] = []
    for c in cases:
        filtered_evidence: list[CaseEvidence] = []
        for e in c.evidence_items:
            if is_operator:
                filtered_evidence.append(e)
            elif e.visibility == EvidenceVisibility.MUTUAL_VISIBLE:
                filtered_evidence.append(e)
            elif (
                e.visibility == EvidenceVisibility.COUNTERPARTY_RESTRICTED
                and e.submitted_by_organization_id == actor_organization_id
            ):
                filtered_evidence.append(e)
            # PRIVATE_OPERATOR excluded for non-operator tenants

        filtered_cases.append(
            DealCase(
                id=c.id,
                deal_id=c.deal_id,
                agreement_version_id=c.agreement_version_id,
                agreement_terms_hash=c.agreement_terms_hash,
                case_type=c.case_type,
                reason=c.reason,
                obligation_references=c.obligation_references,
                requested_by_user_id=c.requested_by_user_id,
                requested_by_organization_id=c.requested_by_organization_id,
                created_at=c.created_at,
                status=c.status,
                resolution=c.resolution,
                resolved_by_user_id=c.resolved_by_user_id,
                resolved_at=c.resolved_at,
                evidence_visibility=c.evidence_visibility,
                evidence_items=filtered_evidence,
                bilateral_consent_counterparty_id=c.bilateral_consent_counterparty_id,
                bilateral_consent_at=c.bilateral_consent_at,
                operational_impact_blockers=c.operational_impact_blockers,
                version=c.version,
            )
        )

    return filtered_cases
