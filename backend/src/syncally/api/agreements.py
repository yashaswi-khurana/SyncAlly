"""Deal agreement draft, approval, and commit HTTP endpoints.

Approval is a verified backend command: the acting organization is derived
from the authenticated ``ActorContext`` and the request must name the exact
agreement version and terms hash the user reviewed. The caller can never send
an agreement status, so it cannot set ``COMMITTED`` directly. Routes only
validate transport schemas and translate application outcomes into the API
error contract.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
from syncally.application.agreements import (
    AgreementAccessDenied,
    AgreementAlreadyCommitted,
    AgreementNotFound,
    AgreementVersionConflict,
    AmbiguousAgreementOrganization,
    CommitAgreementCommand,
    CreateAgreementDraftCommand,
    CreateReviewedAgreementDraftCommand,
    DuplicateApproval,
    ProposalNotFound,
    RecordApprovalCommand,
    StaleAgreementVersion,
    UnauthorizedApproval,
    WrongTermsHash,
    compare_agreement_terms,
    get_current_agreement,
    resolve_party_organization,
)
from syncally.application.deals import (
    DealAccessDenied,
    DealNotFound,
    DealRepository,
    get_deal,
)
from syncally.application.identity import ActorContext
from syncally.domain.agreements.agreement import Agreement, Approval, ApprovalDecision
from syncally.domain.agreements.trade_terms import SUPPORTED_DEMO_PAYMENT_TRIGGER
from syncally.domain.ai.contracts import AIContractError, ProposedTerms
from syncally.domain.shared.errors import InvalidTransition, InvariantViolation
from syncally.domain.shared.identifiers import OrganizationId
from syncally.infrastructure.database import get_db
from syncally.infrastructure.repositories import (
    SqlAlchemyAgreementRepository,
    SqlAlchemyDealRepository,
    commit_agreement_in_transaction,
    create_agreement_draft_in_transaction,
    create_reviewed_agreement_draft_in_transaction,
    record_approval_in_transaction,
)

router = APIRouter(prefix="/deals/{deal_id}/agreements", tags=["agreements"])

_TERMS_HASH_FIELD = Field(pattern=r"^[0-9a-f]{64}$")


class CreateAgreementDraftRequest(BaseModel):
    """Name the saved proposal to snapshot as the deal's candidate agreement."""

    model_config = ConfigDict(extra="forbid")

    proposal_id: UUID


class CreateReviewedAgreementDraftRequest(BaseModel):
    """Explicitly submit the user's reviewed AI draft for bilateral approval."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    description: str = Field(min_length=1, max_length=2_000)
    quantity: Decimal
    unit: str = Field(min_length=1, max_length=100)
    unit_price: Decimal
    currency: str = Field(min_length=3, max_length=3)
    delivery_destination: str = Field(min_length=1, max_length=2_000)
    delivery_date: date | None
    # Rollout shim: clients deployed before this field existed omit it, and during
    # a backend-first rollout they still reach new instances. Omission is
    # unambiguous because the demo contract supports exactly one trigger, and
    # ``ProposedTerms.to_trade_terms()`` derives that same trigger regardless of
    # this acknowledgement. An explicit unsupported value is still rejected.
    # Make the field required once every client sends it.
    payment_trigger: str = Field(
        default=SUPPORTED_DEMO_PAYMENT_TRIGGER, min_length=1, max_length=100
    )
    organization_id: UUID | None = None

    @field_validator("payment_trigger")
    @classmethod
    def supported_payment_trigger(cls, value: str) -> str:
        """Reject a timing the demo contract cannot build, instead of silently ignoring it.

        The proposer explicitly picks the trigger; the due condition is derived
        from it by ``ProposedTerms.to_trade_terms()``, so it is not accepted here.
        """
        trigger = value.strip().casefold()
        if trigger != SUPPORTED_DEMO_PAYMENT_TRIGGER:
            # Never interpolate the submitted value: the 422 handler strips
            # Pydantic's ``input`` field but keeps ``msg``, so echoing it here
            # would reflect caller-supplied text despite the redaction contract.
            raise ValueError(
                f"Unsupported payment timing; supported: {SUPPORTED_DEMO_PAYMENT_TRIGGER}"
            )
        return trigger


class RecordApprovalRequest(BaseModel):
    """The exact agreement version and hash shown to the user, plus optional party choice.

    ``organization_id`` is only a disambiguator for a user who is an active
    member of both parties; it is never authorization on its own.
    """

    model_config = ConfigDict(extra="forbid")

    terms_hash: str = _TERMS_HASH_FIELD
    organization_id: UUID | None = None


class CommitAgreementRequest(BaseModel):
    """The exact agreement version and hash the user asked to commit."""

    model_config = ConfigDict(extra="forbid")

    terms_hash: str = _TERMS_HASH_FIELD
    organization_id: UUID | None = None


class ApprovalResponse(BaseModel):
    """Public representation of one organization's recorded decision."""

    deal_id: UUID
    version_number: int
    organization_id: UUID
    user_id: UUID
    decision: str
    terms_hash: str
    created_at: datetime
    id: UUID | None = None
    agreement_version_id: UUID | None = None


class AgreementVersionResponse(BaseModel):
    """Public representation of one immutable agreement version."""

    deal_id: UUID
    version_number: int
    terms_hash: str
    status: str
    terms: dict[str, Any]
    # Read projection of the single demo payment obligation. Both parties read
    # the same version row, so they always see the same timing. ``None`` when a
    # version carries zero or several payment terms - then ``terms`` is the
    # authoritative list and the review screens render every entry.
    payment_trigger: str | None = None
    payment_due_condition: str | None = None
    created_at: datetime
    committed_at: datetime | None = None
    approvals: list[ApprovalResponse] = Field(default_factory=list)
    id: UUID | None = None
    proposal_id: UUID | None = None
    is_current: bool | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    grounding: str = "UNMAPPED"


def get_agreement_repository(db: Session = Depends(get_db)) -> SqlAlchemyAgreementRepository:
    return SqlAlchemyAgreementRepository(db)


@router.get("/history")
def read_agreement_history_route(
    deal_id: UUID, organization_id: UUID | None = None,
    actor: ActorContext = Depends(get_current_actor),
    repository: SqlAlchemyAgreementRepository = Depends(get_agreement_repository),
) -> dict[str, Any]:
    try:
        return repository.read_versions(deal_id, actor.user_id, organization_id)
    except Exception as exc:
        _raise_agreement_error(exc)


@router.get("/versions/{number}", response_model=AgreementVersionResponse)
def read_exact_agreement_route(
    deal_id: UUID, number: int = Path(ge=1), organization_id: UUID | None = None,
    actor: ActorContext = Depends(get_current_actor),
    repository: SqlAlchemyAgreementRepository = Depends(get_agreement_repository),
) -> AgreementVersionResponse:
    try:
        result = repository.read_versions(deal_id, actor.user_id, organization_id, (number,))
        return AgreementVersionResponse.model_validate(result["versions"][0])
    except Exception as exc:
        _raise_agreement_error(exc)


@router.get("/compare")
def compare_agreements_route(
    deal_id: UUID, before: int = Query(ge=1), after: int = Query(ge=1), organization_id: UUID | None = None,
    actor: ActorContext = Depends(get_current_actor),
    repository: SqlAlchemyAgreementRepository = Depends(get_agreement_repository),
) -> dict[str, Any]:
    try:
        result = repository.read_versions(deal_id, actor.user_id, organization_id, (before, after))
        versions = {version["version_number"]: version for version in result["versions"]}
        return {"before": versions[before], "after": versions[after],
                "changes": compare_agreement_terms(versions[before]["terms"], versions[after]["terms"])}
    except Exception as exc:
        _raise_agreement_error(exc)


def get_deal_repository(db: Session = Depends(get_db)) -> DealRepository:
    """Provide the deal persistence port so routes can authorize the actor."""
    return SqlAlchemyDealRepository(db)


def _to_agreement_response(agreement: Agreement) -> AgreementVersionResponse:
    payment_terms = agreement.terms.payment_terms
    single_payment = payment_terms[0] if len(payment_terms) == 1 else None
    return AgreementVersionResponse(
        id=agreement.version_id,
        is_current=True,
        deal_id=agreement.deal_id,
        version_number=agreement.version_number,
        terms_hash=agreement.terms_hash,
        status=agreement.status.value,
        terms=agreement.terms.to_storage_dict(),
        payment_trigger=single_payment.trigger if single_payment else None,
        payment_due_condition=single_payment.due_condition if single_payment else None,
        created_at=agreement.created_at,
        committed_at=agreement.committed_at,
        approvals=[
            _to_approval_response(agreement.deal_id, agreement.version_number, approval)
            for approval in agreement.approvals.values()
        ],
    )


def _to_approval_response(
    deal_id: UUID, version_number: int, approval: Approval
) -> ApprovalResponse:
    return ApprovalResponse(
        deal_id=deal_id,
        version_number=version_number,
        organization_id=approval.organization_id,
        user_id=approval.user_id,
        decision=approval.decision.value,
        terms_hash=approval.terms_hash,
        created_at=approval.created_at,
    )


@router.get("/current", response_model=AgreementVersionResponse)
def read_current_agreement_route(
    deal_id: UUID,
    organization_id: UUID | None = None,
    actor: ActorContext = Depends(get_current_actor),
    deal_repository: DealRepository = Depends(get_deal_repository),
    agreement_repository: SqlAlchemyAgreementRepository = Depends(get_agreement_repository),
) -> AgreementVersionResponse:
    """Return the current saved agreement only to an active deal participant."""
    try:
        agreement = get_current_agreement(
            actor,
            deal_id,
            deal_repository,
            agreement_repository,
        )
        if organization_id is not None:
            result = agreement_repository.read_versions(deal_id, actor.user_id, organization_id,
                                                         (agreement.version_number,))
            return AgreementVersionResponse.model_validate(result["versions"][0])
    except Exception as exc:
        _raise_agreement_error(exc)
    return _to_agreement_response(agreement)


def _raise_agreement_error(error: Exception) -> NoReturn:
    """Translate agreement application outcomes into the stable HTTP contract."""
    if isinstance(error, DealNotFound):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, (AgreementNotFound, ProposalNotFound)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, (UnauthorizedApproval, AgreementAccessDenied, DealAccessDenied)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    if isinstance(error, StaleAgreementVersion):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The agreement changed; reload it before continuing",
        ) from error
    if isinstance(error, WrongTermsHash):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The displayed agreement terms are no longer current; reload before continuing",
        ) from error
    if isinstance(
        error,
        (
            DuplicateApproval,
            AgreementAlreadyCommitted,
            AgreementVersionConflict,
            InvalidTransition,
        ),
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if isinstance(error, AmbiguousAgreementOrganization):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    if isinstance(error, InvariantViolation):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    raise error


@router.post("", status_code=status.HTTP_201_CREATED, response_model=AgreementVersionResponse)
def create_agreement_draft_route(
    deal_id: UUID,
    payload: CreateAgreementDraftRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
    deal_repository: DealRepository = Depends(get_deal_repository),
) -> AgreementVersionResponse:
    """Snapshot a saved proposal into the deal's next pending agreement version."""
    try:
        get_deal(actor, deal_id, deal_repository)
        agreement = create_agreement_draft_in_transaction(
            db,
            CreateAgreementDraftCommand(
                deal_id=deal_id,
                proposal_id=payload.proposal_id,
                user_id=actor.user_id,
            ),
        )
    except Exception as exc:
        _raise_agreement_error(exc)
    return _to_agreement_response(agreement)


@router.post(
    "/from-reviewed-terms",
    status_code=status.HTTP_201_CREATED,
    response_model=AgreementVersionResponse,
)
def create_reviewed_agreement_draft_route(
    deal_id: UUID,
    payload: CreateReviewedAgreementDraftRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
    deal_repository: DealRepository = Depends(get_deal_repository),
) -> AgreementVersionResponse:
    """Save a reviewed proposal and create its agreement version atomically."""
    try:
        deal = get_deal(actor, deal_id, deal_repository)
        author_organization_id = resolve_party_organization(
            actor, deal, payload.organization_id
        )
        # payment_trigger is already pinned to the supported demo trigger by the
        # request validator; the domain contract derives the due condition from it.
        proposed_terms = ProposedTerms(
            schema_version=payload.schema_version,
            description=payload.description,
            quantity=payload.quantity,
            unit=payload.unit,
            unit_price=payload.unit_price,
            currency=payload.currency,
            delivery_destination=payload.delivery_destination,
            delivery_date=payload.delivery_date,
        )
        terms = proposed_terms.to_trade_terms(
            buyer_id=OrganizationId(deal.buyer_organization_id),
            seller_id=OrganizationId(deal.seller_organization_id),
        )
        agreement = create_reviewed_agreement_draft_in_transaction(
            db,
            CreateReviewedAgreementDraftCommand(
                deal_id=deal_id,
                author_organization_id=author_organization_id,
                user_id=actor.user_id,
                terms=terms,
            ),
        )
    except (AIContractError, InvariantViolation) as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Reviewed terms do not match the supported demo agreement: {error}",
        ) from error
    except Exception as error:
        db.rollback()
        _raise_agreement_error(error)
    return _to_agreement_response(agreement)


def _record_decision(
    *,
    deal_id: UUID,
    version_number: int,
    payload: RecordApprovalRequest,
    decision: ApprovalDecision,
    actor: ActorContext,
    db: Session,
    deal_repository: DealRepository,
) -> ApprovalResponse:
    try:
        deal = get_deal(actor, deal_id, deal_repository)
        organization_id = resolve_party_organization(actor, deal, payload.organization_id)
        approval = record_approval_in_transaction(
            db,
            RecordApprovalCommand(
                deal_id=deal_id,
                version_number=version_number,
                terms_hash=payload.terms_hash,
                organization_id=organization_id,
                user_id=actor.user_id,
                decision=decision,
            ),
        )
    except Exception as exc:
        _raise_agreement_error(exc)
    return _to_approval_response(deal_id, version_number, approval)


@router.post("/{version_number}/approve", response_model=ApprovalResponse)
def approve_agreement_route(
    deal_id: UUID,
    payload: RecordApprovalRequest,
    version_number: int = Path(ge=1),
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
    deal_repository: DealRepository = Depends(get_deal_repository),
) -> ApprovalResponse:
    """Record the authenticated party's approval of the exact displayed version."""
    return _record_decision(
        deal_id=deal_id,
        version_number=version_number,
        payload=payload,
        decision=ApprovalDecision.APPROVE,
        actor=actor,
        db=db,
        deal_repository=deal_repository,
    )


@router.post("/{version_number}/reject", response_model=ApprovalResponse)
def reject_agreement_route(
    deal_id: UUID,
    payload: RecordApprovalRequest,
    version_number: int = Path(ge=1),
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
    deal_repository: DealRepository = Depends(get_deal_repository),
) -> ApprovalResponse:
    """Record the authenticated party's rejection of the exact displayed version."""
    return _record_decision(
        deal_id=deal_id,
        version_number=version_number,
        payload=payload,
        decision=ApprovalDecision.REJECT,
        actor=actor,
        db=db,
        deal_repository=deal_repository,
    )


@router.post("/{version_number}/commit", response_model=AgreementVersionResponse)
def commit_agreement_route(
    deal_id: UUID,
    payload: CommitAgreementRequest,
    version_number: int = Path(ge=1),
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
    deal_repository: DealRepository = Depends(get_deal_repository),
) -> AgreementVersionResponse:
    """Commit the exact version once both verified parties approved it."""
    try:
        deal = get_deal(actor, deal_id, deal_repository)
        organization_id = resolve_party_organization(actor, deal, payload.organization_id)
        agreement = commit_agreement_in_transaction(
            db,
            CommitAgreementCommand(
                deal_id=deal_id,
                expected_version=version_number,
                expected_terms_hash=payload.terms_hash,
                user_id=actor.user_id,
                organization_id=organization_id,
            ),
        )
    except Exception as exc:
        _raise_agreement_error(exc)
    return _to_agreement_response(agreement)
