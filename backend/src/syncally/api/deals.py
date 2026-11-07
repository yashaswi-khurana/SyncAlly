"""Deal HTTP endpoints.

Routes validate request schemas, derive the actor from authentication, call the
application use cases, and translate their outcomes into a stable error contract.
No deal policy or persistence happens here.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
from syncally.application.deal_cases import (
    AddCaseEvidenceCommand,
    CaseUnauthorizedError,
    DealCaseNotFound,
    RaiseDealCaseCommand,
    RespondToDealCaseCommand,
    StaleAgreementVersionError,
    add_case_evidence,
    list_deal_cases,
    raise_deal_case,
    respond_to_deal_case,
)
from syncally.application.deals import (
    CreateDealCommand,
    DealAccessDenied,
    DealNotFound,
    DealRepository,
    create_deal,
    get_deal,
    list_deals,
)
from syncally.application.identity import ActorContext
from syncally.domain.deals.cases import (
    BilateralDecision,
    CaseError,
    CaseEvidence,
    CaseType,
    DealCase,
    EvidenceVisibility,
)
from syncally.domain.deals.deal import Deal
from syncally.domain.shared.errors import InvalidTransition, InvariantViolation
from syncally.infrastructure.database import get_db
from syncally.infrastructure.demo_lifecycle import lock_demo_deal_creation
from syncally.infrastructure.repositories import SqlAlchemyDealRepository

router = APIRouter(prefix="/deals", tags=["deals"])
api_v1_router = APIRouter(prefix="/api/v1/deals", tags=["deals"])


class CreateDealRequest(BaseModel):
    """Fields required to start a draft deal and identify the initiating party."""

    buyer_organization_id: UUID
    seller_organization_id: UUID
    display_name: str | None = Field(default=None, max_length=160)
    initiator_party: Literal["BUYER", "SELLER"] = "BUYER"


class DealResponse(BaseModel):
    """Public representation of a deal; never a serialized ORM entity."""

    id: UUID
    buyer_organization_id: UUID
    seller_organization_id: UUID
    status: str
    version: int
    pending_counterparty: bool = False
    display_name: str | None = None


class DealSummaryResponse(DealResponse):
    """A deal plus the party the requesting actor acts for."""

    viewer_role: str


class CaseEvidenceResponse(BaseModel):
    evidence_id: UUID
    case_id: UUID
    submitted_by_user_id: UUID
    submitted_by_organization_id: UUID
    visibility: str
    notes: str
    submitted_at: datetime
    metadata: dict[str, Any] = {}


class CaseResponse(BaseModel):
    id: UUID
    deal_id: UUID
    agreement_version_id: UUID
    agreement_terms_hash: str
    case_type: str
    reason: str
    obligation_references: list[str]
    requested_by_user_id: UUID
    requested_by_organization_id: UUID
    created_at: datetime
    status: str
    resolution: str | None = None
    resolved_by_user_id: UUID | None = None
    resolved_at: datetime | None = None
    evidence_visibility: str
    evidence_items: list[CaseEvidenceResponse] = []
    bilateral_consent_counterparty_id: UUID | None = None
    bilateral_consent_at: datetime | None = None
    operational_impact_blockers: list[str] = []
    version: int


class RaiseCaseRequest(BaseModel):
    case_type: Literal["CANCELLATION", "DISPUTE"]
    reason: str
    agreement_version_id: UUID
    agreement_terms_hash: str
    obligation_references: list[str] = []
    evidence_visibility: Literal["PRIVATE_OPERATOR", "COUNTERPARTY_RESTRICTED", "MUTUAL_VISIBLE"] = "MUTUAL_VISIBLE"
    evidence_notes: str | None = None
    acting_organization_id: UUID | None = None


class RespondCaseRequest(BaseModel):
    decision: Literal["CONSENT", "REJECT", "WITHDRAW"]
    rationale: str
    acting_organization_id: UUID | None = None


class AddEvidenceRequest(BaseModel):
    notes: str
    visibility: Literal["PRIVATE_OPERATOR", "COUNTERPARTY_RESTRICTED", "MUTUAL_VISIBLE"] = "MUTUAL_VISIBLE"
    metadata: dict[str, Any] = {}
    acting_organization_id: UUID | None = None


def get_deal_repository(db: Session = Depends(get_db)) -> DealRepository:
    """Provide the deal persistence port for the current request."""
    return SqlAlchemyDealRepository(db)


def _to_response(deal: Deal) -> DealResponse:
    return DealResponse(
        id=deal.id,
        buyer_organization_id=deal.buyer_organization_id,
        seller_organization_id=deal.seller_organization_id,
        status=deal.status.value,
        version=deal.version,
        pending_counterparty=deal.pending_counterparty,
        display_name=deal.display_name,
    )


def _to_evidence_response(evidence: CaseEvidence) -> CaseEvidenceResponse:
    return CaseEvidenceResponse(
        evidence_id=evidence.evidence_id,
        case_id=evidence.case_id,
        submitted_by_user_id=evidence.submitted_by_user_id,
        submitted_by_organization_id=evidence.submitted_by_organization_id,
        visibility=evidence.visibility.value,
        notes=evidence.notes,
        submitted_at=evidence.submitted_at,
        metadata=evidence.metadata,
    )


def _to_case_response(case: DealCase) -> CaseResponse:
    return CaseResponse(
        id=case.id,
        deal_id=case.deal_id,
        agreement_version_id=case.agreement_version_id,
        agreement_terms_hash=case.agreement_terms_hash,
        case_type=case.case_type.value,
        reason=case.reason,
        obligation_references=case.obligation_references,
        requested_by_user_id=case.requested_by_user_id,
        requested_by_organization_id=case.requested_by_organization_id,
        created_at=case.created_at,
        status=case.status.value,
        resolution=case.resolution,
        resolved_by_user_id=case.resolved_by_user_id,
        resolved_at=case.resolved_at,
        evidence_visibility=case.evidence_visibility.value,
        evidence_items=[_to_evidence_response(e) for e in case.evidence_items],
        bilateral_consent_counterparty_id=case.bilateral_consent_counterparty_id,
        bilateral_consent_at=case.bilateral_consent_at,
        operational_impact_blockers=case.operational_impact_blockers,
        version=case.version,
    )


def _viewer_role(actor: ActorContext, deal: Deal) -> str:
    """Name the actor's side of a deal they participate in."""
    is_buyer = deal.buyer_organization_id in actor.organization_ids
    is_seller = deal.seller_organization_id in actor.organization_ids
    if is_buyer and is_seller:
        return "BOTH"
    return "BUYER" if is_buyer else "SELLER"


def _resolve_deal_party_organization(
    actor: ActorContext,
    deal: Deal,
    organization_id: UUID | None = None,
) -> UUID:
    party_organizations = {
        deal.buyer_organization_id,
        deal.seller_organization_id,
    } & actor.organization_ids
    if not party_organizations:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Actor is not an active member of a deal party",
        )
    if organization_id is not None:
        if organization_id not in party_organizations:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Named organization is not a valid deal party for this actor",
            )
        return organization_id
    if len(party_organizations) == 1:
        return next(iter(party_organizations))
    return deal.buyer_organization_id


@router.get("", response_model=list[DealSummaryResponse])
def list_deals_route(
    actor: ActorContext = Depends(get_current_actor),
    repository: DealRepository = Depends(get_deal_repository),
) -> list[DealSummaryResponse]:
    """List the deals the actor participates in, newest first."""
    return [
        DealSummaryResponse(
            **_to_response(deal).model_dump(),
            viewer_role=_viewer_role(actor, deal),
        )
        for deal in list_deals(actor, repository)
    ]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DealResponse)
def create_deal_route(
    payload: CreateDealRequest,
    actor: ActorContext = Depends(get_current_actor),
    repository: DealRepository = Depends(get_deal_repository),
    db: Session = Depends(get_db),
) -> DealResponse:
    """Create a draft deal when the actor belongs to the selected initiating party."""
    try:
        lock_demo_deal_creation(
            db, payload.buyer_organization_id, payload.seller_organization_id
        )
        deal = create_deal(
            actor,
            CreateDealCommand(
                buyer_organization_id=payload.buyer_organization_id,
                seller_organization_id=payload.seller_organization_id,
                display_name=payload.display_name,
                initiator_party=payload.initiator_party,
            ),
            repository,
        )
    except DealAccessDenied as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DealNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvariantViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_response(deal)


@router.get("/{deal_id}", response_model=DealResponse)
def read_deal_route(
    deal_id: UUID,
    actor: ActorContext = Depends(get_current_actor),
    repository: DealRepository = Depends(get_deal_repository),
) -> DealResponse:
    """Return a deal to an active member of either party."""
    try:
        deal = get_deal(actor, deal_id, repository)
    except DealNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_response(deal)


# Case endpoints implementation
def _raise_case_impl(
    deal_id: UUID,
    payload: RaiseCaseRequest,
    actor: ActorContext,
    db: Session,
) -> CaseResponse:
    deal_repo = SqlAlchemyDealRepository(db)
    deal = deal_repo.get(deal_id)
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    acting_org = _resolve_deal_party_organization(actor, deal, payload.acting_organization_id)

    try:
        case = raise_deal_case(
            db,
            RaiseDealCaseCommand(
                deal_id=deal_id,
                case_type=CaseType(payload.case_type),
                reason=payload.reason,
                agreement_version_id=payload.agreement_version_id,
                agreement_terms_hash=payload.agreement_terms_hash,
                obligation_references=payload.obligation_references,
                evidence_visibility=EvidenceVisibility(payload.evidence_visibility),
                evidence_notes=payload.evidence_notes,
                actor_user_id=actor.user_id,
                actor_organization_id=acting_org,
            ),
        )
        db.commit()
    except StaleAgreementVersionError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CaseUnauthorizedError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (DealNotFound, DealCaseNotFound) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (InvalidTransition, CaseError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return _to_case_response(case)


def _list_cases_impl(
    deal_id: UUID,
    actor: ActorContext,
    db: Session,
    organization_id: UUID | None,
) -> list[CaseResponse]:
    deal_repo = SqlAlchemyDealRepository(db)
    deal = deal_repo.get(deal_id)
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    acting_org = _resolve_deal_party_organization(actor, deal, organization_id)

    try:
        cases = list_deal_cases(
            db,
            deal_id,
            acting_org,
            is_operator=actor.is_system_admin,
        )
    except CaseUnauthorizedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DealNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [_to_case_response(c) for c in cases]


def _respond_case_impl(
    deal_id: UUID,
    case_id: UUID,
    payload: RespondCaseRequest,
    actor: ActorContext,
    db: Session,
) -> CaseResponse:
    deal_repo = SqlAlchemyDealRepository(db)
    deal = deal_repo.get(deal_id)
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    acting_org = _resolve_deal_party_organization(actor, deal, payload.acting_organization_id)

    try:
        case = respond_to_deal_case(
            db,
            RespondToDealCaseCommand(
                case_id=case_id,
                decision=BilateralDecision(payload.decision),
                rationale=payload.rationale,
                actor_user_id=actor.user_id,
                actor_organization_id=acting_org,
            ),
        )
        db.commit()
    except StaleAgreementVersionError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CaseUnauthorizedError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (DealNotFound, DealCaseNotFound) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (InvalidTransition, CaseError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return _to_case_response(case)


def _add_evidence_impl(
    deal_id: UUID,
    case_id: UUID,
    payload: AddEvidenceRequest,
    actor: ActorContext,
    db: Session,
) -> CaseEvidenceResponse:
    deal_repo = SqlAlchemyDealRepository(db)
    deal = deal_repo.get(deal_id)
    if deal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    acting_org = _resolve_deal_party_organization(actor, deal, payload.acting_organization_id)

    try:
        evidence = add_case_evidence(
            db,
            AddCaseEvidenceCommand(
                case_id=case_id,
                notes=payload.notes,
                visibility=EvidenceVisibility(payload.visibility),
                actor_user_id=actor.user_id,
                actor_organization_id=acting_org,
                metadata=payload.metadata,
            ),
        )
        db.commit()
    except CaseUnauthorizedError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (DealNotFound, DealCaseNotFound) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (InvalidTransition, CaseError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return _to_evidence_response(evidence)


# Mount on router (/deals)
@router.post("/{deal_id}/cases", status_code=status.HTTP_201_CREATED, response_model=CaseResponse)
def raise_case_deals_route(
    deal_id: UUID,
    payload: RaiseCaseRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> CaseResponse:
    return _raise_case_impl(deal_id, payload, actor, db)


@router.get("/{deal_id}/cases", response_model=list[CaseResponse])
def list_cases_deals_route(
    deal_id: UUID,
    organization_id: UUID | None = Query(default=None),
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[CaseResponse]:
    return _list_cases_impl(deal_id, actor, db, organization_id)


@router.post("/{deal_id}/cases/{case_id}/respond", response_model=CaseResponse)
def respond_case_deals_route(
    deal_id: UUID,
    case_id: UUID,
    payload: RespondCaseRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> CaseResponse:
    return _respond_case_impl(deal_id, case_id, payload, actor, db)


@router.post("/{deal_id}/cases/{case_id}/evidence", status_code=status.HTTP_201_CREATED, response_model=CaseEvidenceResponse)
def add_evidence_deals_route(
    deal_id: UUID,
    case_id: UUID,
    payload: AddEvidenceRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> CaseEvidenceResponse:
    return _add_evidence_impl(deal_id, case_id, payload, actor, db)


# Mount on api_v1_router (/api/v1/deals)
@api_v1_router.post("/{deal_id}/cases", status_code=status.HTTP_201_CREATED, response_model=CaseResponse)
def raise_case_v1_route(
    deal_id: UUID,
    payload: RaiseCaseRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> CaseResponse:
    return _raise_case_impl(deal_id, payload, actor, db)


@api_v1_router.get("/{deal_id}/cases", response_model=list[CaseResponse])
def list_cases_v1_route(
    deal_id: UUID,
    organization_id: UUID | None = Query(default=None),
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[CaseResponse]:
    return _list_cases_impl(deal_id, actor, db, organization_id)


@api_v1_router.post("/{deal_id}/cases/{case_id}/respond", response_model=CaseResponse)
def respond_case_v1_route(
    deal_id: UUID,
    case_id: UUID,
    payload: RespondCaseRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> CaseResponse:
    return _respond_case_impl(deal_id, case_id, payload, actor, db)


@api_v1_router.post("/{deal_id}/cases/{case_id}/evidence", status_code=status.HTTP_201_CREATED, response_model=CaseEvidenceResponse)
def add_evidence_v1_route(
    deal_id: UUID,
    case_id: UUID,
    payload: AddEvidenceRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> CaseEvidenceResponse:
    return _add_evidence_impl(deal_id, case_id, payload, actor, db)
