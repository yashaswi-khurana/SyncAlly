"""Typed transport for explicit human negotiation, distinct from agreement approval."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from syncally.api.agreements import CreateReviewedAgreementDraftRequest
from syncally.api.auth import get_current_actor
from syncally.application.identity import ActorContext
from syncally.application.negotiation import (
    CandidateAcknowledgement,
    EvidenceReference,
    NegotiationActionKind,
    NegotiationCommand,
    NegotiationConflict,
    NegotiationNotFound,
    NegotiationOrganizationRequired,
    ProposalBase,
)
from syncally.domain.ai.contracts import AIContractError, ProposedTerms
from syncally.domain.shared.errors import InvalidTransition, InvariantViolation
from syncally.domain.shared.identifiers import OrganizationId
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import Deal
from syncally.infrastructure.repositories.negotiation import (
    SqlAlchemyNegotiationRepository,
    negotiate_in_transaction,
)

router = APIRouter(prefix="/deals/{deal_id}/negotiation", tags=["negotiation"])


class BaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    terms_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: str = Field(min_length=1, max_length=32)


class CandidateRequest(BaseRequest):
    status: str = "PENDING_APPROVAL"
    version_number: int = Field(ge=1)
    proposal_id: UUID


class EvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_id: UUID
    version: int = Field(ge=0)


class NegotiationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_id: UUID
    expected_deal_revision: int = Field(ge=0)
    base: BaseRequest | None
    organization_id: UUID | None = None
    terms: CreateReviewedAgreementDraftRequest | None = None
    expires_at: datetime | None = None
    supersede_current_candidate: CandidateRequest | None = None
    evidence: list[EvidenceRequest] = Field(default_factory=list, max_length=100)

    @field_validator("expires_at")
    @classmethod
    def aware_expiry(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Expiry must be timezone-aware")
        return value


class NegotiationResult(BaseModel):
    outcome: str
    deal_revision: int
    proposal_id: UUID | None
    candidate_id: UUID | None


class ProposalResponse(BaseModel):
    id: UUID
    proposal_number: int
    author_organization_id: UUID
    based_on_proposal_id: UUID | None
    terms: dict[str, Any]
    terms_hash: str
    status: str
    lifecycle_origin: str
    created_at: datetime
    expires_at: datetime | None
    evidence_refs: list[dict[str, Any]]
    metadata_schema_version: int


class HistoryResponse(BaseModel):
    id: UUID
    action: str
    proposal_id: UUID | None
    predecessor_id: UUID | None
    candidate_id: UUID | None
    invalidated_candidate_id: UUID | None
    actor_organization_id: UUID
    from_status: str | None
    to_status: str | None
    created_at: datetime


class NegotiationResponse(BaseModel):
    deal_id: UUID
    deal_revision: int
    organization_id: UUID
    max_rounds: int
    round_count: int
    escalated: bool
    history_ambiguous: bool
    eligible_actions: list[NegotiationActionKind]
    latest: ProposalResponse | None
    proposals: list[ProposalResponse]
    current_candidate: CandidateRequest | None
    history: list[HistoryResponse]


def _raise_error(error: Exception) -> None:
    if isinstance(error, NegotiationNotFound):
        raise HTTPException(404, "Deal not found") from error
    if isinstance(error, (NegotiationConflict, InvalidTransition)):
        raise HTTPException(409, str(error)) from error
    if isinstance(error, (NegotiationOrganizationRequired, InvariantViolation, AIContractError)):
        raise HTTPException(422, str(error)) from error
    raise error


@router.get("", response_model=NegotiationResponse)
def read_negotiation(deal_id: UUID, organization_id: UUID | None = None,
                     limit: int = Query(default=100, ge=1, le=100), offset: int = Query(default=0, ge=0, le=10_000),
                     actor: ActorContext = Depends(get_current_actor), db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        return SqlAlchemyNegotiationRepository(db).read(deal_id, actor.user_id, organization_id, limit=limit, offset=offset)
    except Exception as error:
        _raise_error(error)


@router.post("/{action}", response_model=NegotiationResult)
def write_negotiation(deal_id: UUID, action: NegotiationActionKind, payload: NegotiationRequest,
                      actor: ActorContext = Depends(get_current_actor), db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        repository = SqlAlchemyNegotiationRepository(db)
        deal = db.get(Deal, deal_id)
        repository._authorize(deal, actor.user_id, payload.organization_id)
        terms = None
        if payload.terms is not None:
            if payload.terms.organization_id is not None and payload.terms.organization_id != payload.organization_id:
                raise InvariantViolation("Terms organization must match the selected party")
            terms = ProposedTerms(
                schema_version=payload.terms.schema_version, description=payload.terms.description,
                quantity=payload.terms.quantity, unit=payload.terms.unit, unit_price=payload.terms.unit_price,
                currency=payload.terms.currency, delivery_destination=payload.terms.delivery_destination,
                delivery_date=payload.terms.delivery_date,
            ).to_trade_terms(buyer_id=OrganizationId(deal.buyer_organization_id), seller_id=OrganizationId(deal.seller_organization_id))
        ack = payload.supersede_current_candidate
        return negotiate_in_transaction(db, NegotiationCommand(
            deal_id=deal_id, user_id=actor.user_id, organization_id=payload.organization_id,
            command_id=payload.command_id, action=action, expected_deal_revision=payload.expected_deal_revision,
            base=ProposalBase(payload.base.id, payload.base.terms_hash, payload.base.status) if payload.base else None,
            terms=terms, expires_at=payload.expires_at,
            supersede_current_candidate=CandidateAcknowledgement(ack.id, ack.version_number, ack.terms_hash, ack.proposal_id) if ack else None,
            evidence=tuple(EvidenceReference(ref.fact_id, ref.version) for ref in payload.evidence),
        ))
    except Exception as error:
        db.rollback()
        _raise_error(error)