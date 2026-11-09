"""Deal agreement draft, approval, and commit HTTP endpoints.

Approval is a verified backend command: the acting organization is derived
from the authenticated ``ActorContext`` and the request must name the exact
agreement version and terms hash the user reviewed. The caller can never send
an agreement status, so it cannot set ``COMMITTED`` directly. Routes only
validate transport schemas and translate application outcomes into the API
error contract.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
from syncally.api.authorization import require_deal_action
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
    NotEligibleApprover,
    OutOfSequenceApproval,
    ProposalNotFound,
    ProposeAmendmentCommand,
    RecordApprovalCommand,
    RecordRoutingDecisionCommand,
    StaleAgreementVersion,
    UnauthorizedApproval,
    WithdrawAmendmentCommand,
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
from syncally.domain.agreements.amendment import (
    AmendmentAlreadyCommitted as DomainAmendmentAlreadyCommitted,
)
from syncally.domain.agreements.amendment import (
    AmendmentConflict,
    AmendmentImpactBlocked,
    StalePriorVersion,
    WrongPriorHash,
)
from syncally.domain.agreements.trade_terms import (
    SUPPORTED_DEMO_PAYMENT_TRIGGER,
    PaymentObligationAllocation,
    PaymentTerm,
    ShipmentItemAllocation,
    ShipmentTerm,
    TradeLineItem,
    TradeTerms,
)
from syncally.domain.ai.contracts import AIContractError, ProposedTerms
from syncally.domain.shared.errors import InvalidTransition, InvariantViolation
from syncally.domain.shared.identifiers import OrganizationId
from syncally.domain.shared.money import Money
from syncally.infrastructure.database import get_db
from syncally.infrastructure.repositories import (
    SqlAlchemyAgreementRepository,
    SqlAlchemyApprovalRoutingPolicyRepository,
    SqlAlchemyDealRepository,
    commit_agreement_in_transaction,
    create_agreement_draft_in_transaction,
    create_reviewed_agreement_draft_in_transaction,
    propose_amendment_in_transaction,
    record_approval_in_transaction,
    record_routing_decision_in_transaction,
    withdraw_amendment_in_transaction,
)

router = APIRouter(prefix="/deals/{deal_id}/agreements", tags=["agreements"])

_TERMS_HASH_FIELD = Field(pattern=r"^[0-9a-f]{64}$")


class CreateAgreementDraftRequest(BaseModel):
    """Name the saved proposal to snapshot as the deal's candidate agreement."""

    model_config = ConfigDict(extra="forbid")

    proposal_id: UUID
    organization_id: UUID | None = None


class MoneyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal
    currency: str = Field(min_length=3, max_length=3)


class ShipmentItemAllocationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_item_id: str = Field(min_length=1, max_length=64)
    quantity: Decimal
    unit: str = Field(min_length=1, max_length=100)


class PaymentObligationAllocationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    obligation_id: str = Field(min_length=1, max_length=64)
    amount: MoneyRequest


class TradeLineItemDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1, max_length=2_000)
    quantity: Decimal
    unit: str = Field(min_length=1, max_length=100)
    unit_price: MoneyRequest
    sku: str | None = Field(default=None, max_length=100)


class ShipmentTermDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    destination: str = Field(min_length=1, max_length=2_000)
    target_date: date | None = None
    allocations: list[ShipmentItemAllocationRequest] = Field(default_factory=list)
    quantity: Decimal | None = None


class PaymentTermDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    amount: MoneyRequest
    trigger: str = Field(min_length=1, max_length=100)
    due_condition: str = Field(min_length=1, max_length=200)
    allocations: list[PaymentObligationAllocationRequest] = Field(default_factory=list)


class CreateReviewedAgreementDraftRequest(BaseModel):
    """Explicitly submit the user's reviewed AI draft or schema 2 collections for bilateral approval."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    # Schema 1 flat fields
    description: str | None = Field(default=None, max_length=2_000)
    quantity: Decimal | None = None
    unit: str | None = Field(default=None, max_length=100)
    unit_price: Decimal | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    delivery_destination: str | None = Field(default=None, max_length=2_000)
    delivery_date: date | None = None
    payment_trigger: str | None = Field(default=None, max_length=100)
    organization_id: UUID | None = None

    # Schema 2 collection fields
    line_items: list[TradeLineItemDraftRequest] | None = None
    shipments: list[ShipmentTermDraftRequest] | None = None
    payment_terms: list[PaymentTermDraftRequest] | None = None
    delivery_location: str | None = Field(default=None, max_length=2_000)
    incoterm: str | None = Field(default=None, max_length=10)
    cancellation_terms: str = Field(default="", max_length=2_000)

    @field_validator("payment_trigger")
    @classmethod
    def supported_payment_trigger(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trigger = value.strip().casefold()
        if trigger != SUPPORTED_DEMO_PAYMENT_TRIGGER:
            raise ValueError(
                f"Unsupported payment timing; supported: {SUPPORTED_DEMO_PAYMENT_TRIGGER}"
            )
        return trigger

    @model_validator(mode="after")
    def validate_schema_fields(self) -> CreateReviewedAgreementDraftRequest:
        if self.schema_version == 1:
            missing = []
            if not self.description:
                missing.append("description")
            if self.quantity is None:
                missing.append("quantity")
            if not self.unit:
                missing.append("unit")
            if self.unit_price is None:
                missing.append("unit_price")
            if not self.currency:
                missing.append("currency")
            if not self.delivery_destination:
                missing.append("delivery_destination")
            if missing:
                raise ValueError(f"Schema 1 requires flat fields: {', '.join(missing)}")
            if self.payment_trigger is None:
                self.payment_trigger = SUPPORTED_DEMO_PAYMENT_TRIGGER
        elif self.schema_version == 2:
            missing = []
            if not self.line_items:
                missing.append("line_items")
            if not self.shipments:
                missing.append("shipments")
            if not self.payment_terms:
                missing.append("payment_terms")
            if not self.delivery_location:
                missing.append("delivery_location")
            if missing:
                raise ValueError(f"Schema 2 requires collection fields: {', '.join(missing)}")
        else:
            raise ValueError(f"Unsupported schema_version: {self.schema_version}")
        return self


def build_trade_terms_from_request(
    payload: CreateReviewedAgreementDraftRequest,
    buyer_id: OrganizationId,
    seller_id: OrganizationId,
) -> TradeTerms:
    if payload.schema_version == 1:
        assert payload.description is not None
        assert payload.quantity is not None
        assert payload.unit is not None
        assert payload.unit_price is not None
        assert payload.currency is not None
        assert payload.delivery_destination is not None
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
        return proposed_terms.to_trade_terms(buyer_id=buyer_id, seller_id=seller_id)
    if payload.schema_version == 2:
        assert payload.line_items is not None
        assert payload.shipments is not None
        assert payload.payment_terms is not None
        assert payload.delivery_location is not None

        domain_items = tuple(
            TradeLineItem(
                id=item.id,
                description=item.description,
                quantity=item.quantity,
                unit=item.unit,
                unit_price=Money(item.unit_price.amount, item.unit_price.currency),
                sku=item.sku,
            )
            for item in payload.line_items
        )
        domain_shipments = tuple(
            ShipmentTerm(
                id=shipment.id,
                destination=shipment.destination,
                target_date=shipment.target_date,
                quantity=shipment.quantity,
                allocations=tuple(
                    ShipmentItemAllocation(
                        line_item_id=alloc.line_item_id,
                        quantity=alloc.quantity,
                        unit=alloc.unit,
                    )
                    for alloc in shipment.allocations
                ),
            )
            for shipment in payload.shipments
        )
        domain_payment_terms = tuple(
            PaymentTerm(
                id=term.id,
                amount=Money(term.amount.amount, term.amount.currency),
                trigger=term.trigger,
                due_condition=term.due_condition,
                allocations=tuple(
                    PaymentObligationAllocation(
                        obligation_id=alloc.obligation_id,
                        amount=Money(alloc.amount.amount, alloc.amount.currency),
                    )
                    for alloc in term.allocations
                ),
            )
            for term in payload.payment_terms
        )
        return TradeTerms(
            buyer_id=buyer_id,
            seller_id=seller_id,
            line_items=domain_items,
            shipments=domain_shipments,
            payment_terms=domain_payment_terms,
            delivery_location=payload.delivery_location,
            incoterm=payload.incoterm,
            cancellation_terms=payload.cancellation_terms,
            schema_version=payload.schema_version,
        )
    raise InvariantViolation(f"Unsupported trade terms schema version: {payload.schema_version}")


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


class ProposeAmendmentRequest(CreateReviewedAgreementDraftRequest):
    """Propose an amendment against an exact committed agreement version and hash."""

    prior_version_number: int = Field(ge=1)
    prior_terms_hash: str = _TERMS_HASH_FIELD
    rationale: str | None = Field(default=None, max_length=2_000)
    replace_pending_draft: bool = False


class WithdrawAmendmentRequest(BaseModel):
    """Withdraw a pending amendment candidate."""

    model_config = ConfigDict(extra="forbid")

    terms_hash: str = _TERMS_HASH_FIELD
    organization_id: UUID | None = None


class PreviewAmendmentImpactRequest(CreateReviewedAgreementDraftRequest):
    """Preview impacts of proposed terms against the current committed agreement."""

    pass


class FulfillmentObligationImpactResponse(BaseModel):
    obligation_reference: str
    item_id: str | None = None
    planned_quantity: str
    unit: str
    shipped_quantity: str
    confirmed_quantity: str
    preserved: bool
    status: str
    details: str | None = None


class PaymentMilestoneImpactResponse(BaseModel):
    milestone_reference: str
    amount: str
    currency: str
    payment_status: str
    has_active_intent: bool
    preserved: bool
    status: str
    details: str | None = None


class AmendmentImpactResponse(BaseModel):
    prior_version_number: int
    prior_terms_hash: str
    proposed_version_number: int
    proposed_terms_hash: str
    diff: dict[str, Any]
    fulfillment_impact: list[FulfillmentObligationImpactResponse]
    payment_impact: list[PaymentMilestoneImpactResponse]
    active_cases: list[dict[str, Any]]
    blockers: list[str]
    can_commit: bool


class RoutingSlotResponse(BaseModel):
    """One configured approver's current actionability. Omits the user id
    for a viewer outside this organization - see ``RoutingStatusResponse``.
    """

    user_id: UUID | None
    status: str
    decision: str | None
    stale: bool


class RoutingStatusResponse(BaseModel):
    """An organization's approval routing state for one agreement version.

    ``slots`` carries full per-approver detail only for a viewer who belongs
    to this organization; a counterparty sees aggregate counts only, never
    who the configured approvers are.
    """

    organization_id: UUID
    mode: str
    policy_version: int
    status: str
    required_approvers: int
    completed_approvers: int
    slots: list[RoutingSlotResponse] | None = None


class ApprovalResponse(BaseModel):
    """Public representation of one organization's recorded decision."""

    deal_id: UUID
    version_number: int
    organization_id: UUID
    user_id: UUID | None
    decision: str
    terms_hash: str
    created_at: datetime
    id: UUID | None = None
    agreement_version_id: UUID | None = None
    routing: RoutingStatusResponse | None = None


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
    prior_agreement_version_id: UUID | None = None
    prior_terms_hash: str | None = None
    amendment_rationale: str | None = None
    approvals: list[ApprovalResponse] = Field(default_factory=list)
    id: UUID | None = None
    proposal_id: UUID | None = None
    is_current: bool | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    grounding: str = "UNMAPPED"
    # Keyed by organization_id (string); only present for organizations that
    # have an approval routing policy configured - absent entirely otherwise.
    routing_status: dict[str, RoutingStatusResponse] = Field(default_factory=dict)


def get_agreement_repository(db: Session = Depends(get_db)) -> SqlAlchemyAgreementRepository:
    return SqlAlchemyAgreementRepository(db)


def get_deal_repository(db: Session = Depends(get_db)) -> DealRepository:
    return SqlAlchemyDealRepository(db)


@router.get("/history")
def read_agreement_history_route(
    deal_id: UUID, organization_id: UUID | None = None,
    actor: ActorContext = Depends(get_current_actor),
    repository: SqlAlchemyAgreementRepository = Depends(get_agreement_repository),
    deal_repository: DealRepository = Depends(get_deal_repository),
) -> dict[str, Any]:
    try:
        deal = get_deal(actor, deal_id, deal_repository)
        selected_org = resolve_party_organization(actor, deal, organization_id)
        require_deal_action(actor, deal, selected_org, "deal.read_assigned")
        return repository.read_versions(deal_id, actor.user_id, selected_org)
    except Exception as exc:
        _raise_agreement_error(exc)


@router.get("/versions/{number}", response_model=AgreementVersionResponse)
def read_exact_agreement_route(
    deal_id: UUID, number: int = Path(ge=1), organization_id: UUID | None = None,
    actor: ActorContext = Depends(get_current_actor),
    repository: SqlAlchemyAgreementRepository = Depends(get_agreement_repository),
    deal_repository: DealRepository = Depends(get_deal_repository),
) -> AgreementVersionResponse:
    try:
        deal = get_deal(actor, deal_id, deal_repository)
        selected_org = resolve_party_organization(actor, deal, organization_id)
        require_deal_action(actor, deal, selected_org, "deal.read_assigned")
        result = repository.read_versions(deal_id, actor.user_id, selected_org, (number,))
        return AgreementVersionResponse.model_validate(result["versions"][0])
    except Exception as exc:
        _raise_agreement_error(exc)


@router.get("/compare")
def compare_agreements_route(
    deal_id: UUID, before: int = Query(ge=1), after: int = Query(ge=1), organization_id: UUID | None = None,
    actor: ActorContext = Depends(get_current_actor),
    repository: SqlAlchemyAgreementRepository = Depends(get_agreement_repository),
    deal_repository: DealRepository = Depends(get_deal_repository),
) -> dict[str, Any]:
    try:
        deal = get_deal(actor, deal_id, deal_repository)
        selected_org = resolve_party_organization(actor, deal, organization_id)
        require_deal_action(actor, deal, selected_org, "deal.read_assigned")
        result = repository.read_versions(deal_id, actor.user_id, selected_org, (before, after))
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
        prior_agreement_version_id=agreement.prior_agreement_version_id,
        prior_terms_hash=agreement.prior_terms_hash,
        amendment_rationale=agreement.amendment_rationale,
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
        deal = get_deal(actor, deal_id, deal_repository)
        selected_org = resolve_party_organization(actor, deal, organization_id)
        require_deal_action(actor, deal, selected_org, "deal.read_assigned")
        agreement = get_current_agreement(
            actor,
            deal_id,
            deal_repository,
            agreement_repository,
        )
        result = agreement_repository.read_versions(deal_id, actor.user_id, selected_org,
                                                     (agreement.version_number,))
        return AgreementVersionResponse.model_validate(result["versions"][0])
    except Exception as exc:
        _raise_agreement_error(exc)


def _raise_agreement_error(error: Exception) -> NoReturn:
    """Translate agreement application outcomes into the stable HTTP contract."""
    if isinstance(error, HTTPException):
        raise error
    if isinstance(error, DealNotFound):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, (AgreementNotFound, ProposalNotFound)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(
        error,
        (UnauthorizedApproval, AgreementAccessDenied, DealAccessDenied, NotEligibleApprover),
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    if isinstance(error, OutOfSequenceApproval):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
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
            AmendmentConflict,
            AmendmentImpactBlocked,
            StalePriorVersion,
            WrongPriorHash,
            DomainAmendmentAlreadyCommitted,
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
        deal = get_deal(actor, deal_id, deal_repository)
        organization_id = resolve_party_organization(actor, deal, payload.organization_id)
        require_deal_action(actor, deal, organization_id, "deal.edit_assigned")
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
        require_deal_action(actor, deal, author_organization_id, "deal.edit_assigned")
        terms = build_trade_terms_from_request(
            payload,
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


def _to_routing_status_response(
    organization_id: UUID, policy: Any, evaluation: Any, *, reveal_detail: bool
) -> RoutingStatusResponse:
    completed = sum(1 for slot in evaluation.slots if slot.status.value == "COMPLETED")
    slots = None
    if reveal_detail:
        slots = [
            RoutingSlotResponse(
                user_id=slot.user_id,
                status=slot.status.value,
                decision=slot.decision.value if slot.decision else None,
                stale=slot.stale,
            )
            for slot in evaluation.slots
        ]
    return RoutingStatusResponse(
        organization_id=organization_id,
        mode=policy.mode.value,
        policy_version=policy.version,
        status=evaluation.status.value,
        required_approvers=len(evaluation.slots),
        completed_approvers=completed,
        slots=slots,
    )


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
        require_deal_action(actor, deal, organization_id, "agreement.approve")
        # Locked so an admin can't create/update/remove this org's policy
        # between this branch decision and the write below; record_routing_decision
        # re-reads under the same lock, so the response built from `policy`
        # further down always matches what it actually evaluated against.
        policy = SqlAlchemyApprovalRoutingPolicyRepository(db).get(organization_id, for_update=True)
        if policy is None:
            # Default: unchanged single-approver bilateral behavior.
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
            return _to_approval_response(deal_id, version_number, approval)

        outcome = record_routing_decision_in_transaction(
            db,
            RecordRoutingDecisionCommand(
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

    reveal_detail = organization_id in actor.organization_ids
    routing = _to_routing_status_response(
        organization_id, policy, outcome.evaluation, reveal_detail=reveal_detail
    )
    if outcome.finalized_approval is not None:
        response = _to_approval_response(deal_id, version_number, outcome.finalized_approval)
        response.routing = routing
        return response
    return ApprovalResponse(
        deal_id=deal_id,
        version_number=version_number,
        organization_id=organization_id,
        user_id=actor.user_id,
        decision=decision.value,
        terms_hash=payload.terms_hash,
        created_at=datetime.now(UTC),
        routing=routing,
    )


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
        require_deal_action(actor, deal, organization_id, "agreement.approve")
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


@router.post(
    "/amendments/propose",
    status_code=status.HTTP_201_CREATED,
    response_model=AgreementVersionResponse,
)
def propose_amendment_route(
    deal_id: UUID,
    payload: ProposeAmendmentRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
    deal_repository: DealRepository = Depends(get_deal_repository),
) -> AgreementVersionResponse:
    """Propose an amendment against the current committed agreement version."""
    try:
        deal = get_deal(actor, deal_id, deal_repository)
        author_organization_id = resolve_party_organization(
            actor, deal, payload.organization_id
        )
        require_deal_action(actor, deal, author_organization_id, "deal.edit_assigned")
        terms = build_trade_terms_from_request(
            payload,
            buyer_id=OrganizationId(deal.buyer_organization_id),
            seller_id=OrganizationId(deal.seller_organization_id),
        )
        agreement = propose_amendment_in_transaction(
            db,
            ProposeAmendmentCommand(
                deal_id=deal_id,
                author_organization_id=author_organization_id,
                user_id=actor.user_id,
                prior_version_number=payload.prior_version_number,
                prior_terms_hash=payload.prior_terms_hash,
                terms=terms,
                rationale=payload.rationale,
                replace_pending_draft=payload.replace_pending_draft,
            ),
        )
    except (AIContractError, InvariantViolation) as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Proposed amendment terms do not match supported agreement format: {error}",
        ) from error
    except Exception as error:
        db.rollback()
        _raise_agreement_error(error)
    return _to_agreement_response(agreement)


@router.get(
    "/amendments/impact",
    response_model=AmendmentImpactResponse,
)
def read_amendment_impact_route(
    deal_id: UUID,
    organization_id: UUID | None = Query(default=None),
    version_number: int | None = Query(default=None, ge=1),
    actor: ActorContext = Depends(get_current_actor),
    repository: SqlAlchemyAgreementRepository = Depends(get_agreement_repository),
    deal_repository: DealRepository = Depends(get_deal_repository),
) -> AmendmentImpactResponse:
    """Assess operational fulfillment, payment, and policy impact of a pending amendment."""
    try:
        deal = get_deal(actor, deal_id, deal_repository)
        selected_org = resolve_party_organization(actor, deal, organization_id)
        require_deal_action(actor, deal, selected_org, "deal.read_assigned")
        impact = repository.assess_amendment_impact(
            deal_id,
            pending_version_number=version_number,
        )
        return AmendmentImpactResponse.model_validate(impact.to_dict())
    except Exception as exc:
        _raise_agreement_error(exc)


@router.post(
    "/amendments/preview-impact",
    response_model=AmendmentImpactResponse,
)
def preview_amendment_impact_route(
    deal_id: UUID,
    payload: PreviewAmendmentImpactRequest,
    actor: ActorContext = Depends(get_current_actor),
    repository: SqlAlchemyAgreementRepository = Depends(get_agreement_repository),
    deal_repository: DealRepository = Depends(get_deal_repository),
) -> AmendmentImpactResponse:
    """Preview operational impact of proposed terms before submitting an amendment candidate."""
    try:
        deal = get_deal(actor, deal_id, deal_repository)
        require_deal_action(actor, deal, payload.organization_id, "deal.edit_assigned")
        terms = build_trade_terms_from_request(
            payload,
            buyer_id=OrganizationId(deal.buyer_organization_id),
            seller_id=OrganizationId(deal.seller_organization_id),
        )
        impact = repository.assess_amendment_impact(
            deal_id,
            proposed_terms=terms,
        )
        return AmendmentImpactResponse.model_validate(impact.to_dict())
    except (AIContractError, InvariantViolation) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Proposed terms do not match supported agreement format: {error}",
        ) from error
    except Exception as exc:
        _raise_agreement_error(exc)


@router.post(
    "/amendments/{version_number}/withdraw",
    response_model=AgreementVersionResponse,
)
def withdraw_amendment_route(
    deal_id: UUID,
    payload: WithdrawAmendmentRequest,
    version_number: int = Path(ge=1),
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
    deal_repository: DealRepository = Depends(get_deal_repository),
) -> AgreementVersionResponse:
    """Withdraw/void a pending amendment candidate."""
    try:
        deal = get_deal(actor, deal_id, deal_repository)
        organization_id = resolve_party_organization(
            actor, deal, payload.organization_id
        )
        require_deal_action(actor, deal, organization_id, "deal.edit_assigned")
        agreement = withdraw_amendment_in_transaction(
            db,
            WithdrawAmendmentCommand(
                deal_id=deal_id,
                version_number=version_number,
                terms_hash=payload.terms_hash,
                user_id=actor.user_id,
                organization_id=organization_id,
            ),
        )
    except Exception as exc:
        _raise_agreement_error(exc)
    return _to_agreement_response(agreement)
