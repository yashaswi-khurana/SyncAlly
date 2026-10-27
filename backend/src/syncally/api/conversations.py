"""Deal conversation and fact-review HTTP endpoints.

Routes validate request schemas, derive the actor from authentication, call the
application use cases, and translate their outcomes into a stable error contract.
The acting organization always comes from the verified actor, never from the
request as authority. Message bodies are never written to logs.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
from syncally.application.ai import (
    AISuggestionProvider,
    AITransientError,
    draft_proposal_from_context,
    extract_facts_from_context,
    persist_fact_candidates,
)
from syncally.application.conversations import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    AddMessageCommand,
    AmbiguousOrganization,
    CommunicationNotFound,
    CommunicationRepository,
    ConcurrentConstraintUpdate,
    ConstraintNotFound,
    ConstraintReviewAction,
    CreateManualConstraintCommand,
    OrganizationAccessDenied,
    add_message,
    correct_constraint,
    create_manual_constraint,
    list_visible_constraints,
    list_visible_messages,
    review_constraint,
    select_ai_context,
)
from syncally.application.identity import ActorContext
from syncally.application.workflow_notifications import NotificationKind
from syncally.config import settings
from syncally.domain.ai.contracts import (
    AI_SCHEMA_VERSION,
    AIContractError,
    ExtractedFact,
    FactField,
    SourceReference,
    ValidationResult,
)
from syncally.domain.conversations import (
    Constraint,
    ConstraintKind,
    ConstraintStatus,
    Message,
    Visibility,
)
from syncally.domain.shared.errors import InvalidTransition, InvariantViolation
from syncally.infrastructure.ai.demo import DemoAISuggestionProvider
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import (
    AuditEvent,
    Organization,
    OrganizationMember,
    User,
)
from syncally.infrastructure.models import (
    Constraint as ConstraintModel,
)
from syncally.infrastructure.models import (
    Message as MessageModel,
)
from syncally.infrastructure.repositories import (
    CommunicationScopeError,
    SqlAlchemyCommunicationRepository,
)
from syncally.infrastructure.workflow_notifications import queue_deal_workflow_notification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deals/{deal_id}", tags=["conversations"])


class AddMessageRequest(BaseModel):
    """A user-authored message to store on the actor's side of a deal."""

    body: str = Field(min_length=1, max_length=8000)
    visibility: Visibility
    source_reference: str | None = Field(default=None, max_length=500)
    organization_id: UUID | None = None

    @field_validator("body", mode="before")
    @classmethod
    def strip_body(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("source_reference", mode="before")
    @classmethod
    def strip_source_reference(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class MessageResponse(BaseModel):
    """Public representation of a stored message; never a serialized ORM entity."""

    id: UUID
    conversation_id: UUID
    author_user_id: UUID | None
    author_agent_id: str | None
    body: str
    visibility: str
    source_type: str
    source_reference: str | None
    created_at: datetime


class ConstraintResponse(BaseModel):
    """Public representation of a deal fact and its review state."""

    id: UUID
    deal_id: UUID
    owner_organization_id: UUID
    field: str
    typed_value: str
    currency_or_unit: str | None
    kind: str
    status: str
    visibility: str
    source_message_id: UUID | None
    source_span: str | None
    confirmed_by: UUID | None
    confirmed_at: datetime | None
    version: int
    created_at: datetime


class ValidationIssueResponse(BaseModel):
    schema_version: int
    code: str
    path: str
    message: str


class FactSuggestionResponse(BaseModel):
    status: str
    issues: list[ValidationIssueResponse]
    facts: list[ConstraintResponse]
    missing_fields: list[str]
    guidance_message: str


class ProposalSuggestionResponse(BaseModel):
    schema_version: int
    description: str
    quantity: str
    unit: str
    unit_price: str
    currency: str
    delivery_destination: str
    delivery_date: date | None
    status: str = "DRAFT"


class AISuggestionRequest(BaseModel):
    organization_id: UUID


class CorrectFactRequest(BaseModel):
    expected_version: int = Field(ge=0)
    field: str = Field(min_length=1, max_length=100)
    typed_value: str = Field(min_length=1, max_length=2000)
    currency_or_unit: str | None = Field(default=None, max_length=32)

    @field_validator("field", "typed_value", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class CreateFactRequest(BaseModel):
    """A user-entered fact; source attribution is created by the server."""

    organization_id: UUID | None = None
    field: str = Field(min_length=1, max_length=100)
    typed_value: str = Field(min_length=1, max_length=2000)
    currency_or_unit: str | None = Field(default=None, max_length=32)
    kind: ConstraintKind = ConstraintKind.INFORMATIONAL
    visibility: Visibility

    @field_validator("field", "typed_value", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("currency_or_unit", mode="before")
    @classmethod
    def strip_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class FactCorrectionResponse(BaseModel):
    replaced_fact: ConstraintResponse
    corrected_fact: ConstraintResponse


class UpdateFactVisibilityRequest(BaseModel):
    visibility: Visibility


def get_communication_repository(
    db: Session = Depends(get_db),
) -> CommunicationRepository:
    """Provide the conversation persistence port for the current request."""
    return SqlAlchemyCommunicationRepository(db)


def get_ai_suggestion_provider() -> AISuggestionProvider:
    """Use the deterministic demo provider locally; require a chosen provider elsewhere."""
    if settings.app_env.lower() not in {"development", "test"}:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI suggestions are not configured",
        )
    return DemoAISuggestionProvider()


def _validation_issue_responses(result: ValidationResult) -> list[ValidationIssueResponse]:
    return [
        ValidationIssueResponse(
            schema_version=issue.schema_version,
            code=issue.code,
            path=issue.path,
            message=issue.message,
        )
        for issue in result.issues
    ]


_REQUIRED_PROPOSAL_FIELDS = (
    ("description", frozenset({"description", "item_description"})),
    ("quantity", frozenset({"quantity"})),
    ("unit", frozenset({"unit"})),
    ("unit_price", frozenset({"unit_price"})),
    ("delivery_destination", frozenset({"delivery_destination"})),
    ("delivery_date", frozenset({"delivery_date"})),
)


def _missing_trade_fields(constraints: tuple[Constraint, ...] | list[Constraint]) -> list[str]:
    """List required draft fields that are not represented by known deal facts."""
    ignored_statuses = {
        ConstraintStatus.NEEDS_CLARIFICATION,
        ConstraintStatus.REJECTED,
        ConstraintStatus.SUPERSEDED,
    }
    present = {
        constraint.field.casefold().replace(" ", "_")
        for constraint in constraints
        if constraint.status not in ignored_statuses
    }
    return [
        proposal_field
        for proposal_field, aliases in _REQUIRED_PROPOSAL_FIELDS
        if not present.intersection(aliases)
    ]


def _fact_suggestion_guidance(missing_fields: list[str]) -> str:
    if not missing_fields:
        return "All required trade details were found. Review each fact before using a draft."
    labels = {
        "description": "item description",
        "quantity": "quantity",
        "unit": "unit",
        "unit_price": "unit price",
        "delivery_destination": "delivery destination",
        "delivery_date": "delivery date",
    }
    missing = ", ".join(labels[field] for field in missing_fields)
    return (
        f"Add the missing details: {missing}. Suggested format: "
        "‘Order of [item], [quantity] [unit] at USD [price] each, "
        "ship to [city or port] by YYYY-MM-DD.’"
    )


def _list_all_visible_constraints(
    actor: ActorContext,
    deal_id: UUID,
    organization_id: UUID,
    repository: CommunicationRepository,
) -> list[Constraint]:
    """Read every page after extraction so guidance reflects current visible facts."""
    constraints: list[Constraint] = []
    offset = 0
    while True:
        page = list_visible_constraints(
            actor,
            deal_id,
            repository,
            organization_id=organization_id,
            limit=MAX_PAGE_SIZE,
            offset=offset,
        )
        constraints.extend(page)
        if len(page) < MAX_PAGE_SIZE:
            return constraints
        offset += len(page)


@router.post("/ai/facts", response_model=FactSuggestionResponse)
def suggest_facts_route(
    deal_id: UUID,
    payload: AISuggestionRequest,
    actor: ActorContext = Depends(get_current_actor),
    repository: CommunicationRepository = Depends(get_communication_repository),
    provider: AISuggestionProvider = Depends(get_ai_suggestion_provider),
    db: Session = Depends(get_db),
) -> FactSuggestionResponse:
    """Run the scoped fake/provider on explicit request and save unreviewed candidates."""
    try:
        context = select_ai_context(actor, deal_id, payload.organization_id, repository)
        db.rollback()  # Do not hold a database transaction while the provider runs.
        result = extract_facts_from_context(context, provider)
        facts = persist_fact_candidates(actor, deal_id, result, repository)
        db.commit()
        current_constraints = _list_all_visible_constraints(
            actor, deal_id, context.organization_id, repository
        )
    except AITransientError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI provider is temporarily unavailable",
        ) from exc
    except (
        CommunicationNotFound,
        OrganizationAccessDenied,
        AmbiguousOrganization,
        CommunicationScopeError,
    ) as exc:
        db.rollback()
        _raise_review_error(exc)
    except Exception:
        db.rollback()
        raise

    missing_fields = _missing_trade_fields(current_constraints)
    return FactSuggestionResponse(
        status=result.result.status.value,
        issues=_validation_issue_responses(result.result),
        facts=[_to_constraint_response(fact) for fact in facts],
        missing_fields=missing_fields,
        guidance_message=_fact_suggestion_guidance(missing_fields),
    )


@router.post("/ai/proposal", response_model=ProposalSuggestionResponse)
def suggest_proposal_route(
    deal_id: UUID,
    payload: AISuggestionRequest,
    actor: ActorContext = Depends(get_current_actor),
    repository: CommunicationRepository = Depends(get_communication_repository),
    provider: AISuggestionProvider = Depends(get_ai_suggestion_provider),
    db: Session = Depends(get_db),
) -> ProposalSuggestionResponse:
    """Return validated draft terms; this route cannot save or approve an agreement."""
    try:
        context = select_ai_context(actor, deal_id, payload.organization_id, repository)
        db.rollback()
        result = draft_proposal_from_context(context, provider)
    except AITransientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI provider is temporarily unavailable",
        ) from exc
    except (
        CommunicationNotFound,
        OrganizationAccessDenied,
        AmbiguousOrganization,
        CommunicationScopeError,
    ) as exc:
        _raise_review_error(exc)

    if result.proposal is None:
        message = result.result.issues[0].message if result.result.issues else "Proposal could not be drafted"
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)
    proposal = result.proposal
    return ProposalSuggestionResponse(
        schema_version=proposal.schema_version,
        description=proposal.description,
        quantity=str(proposal.quantity),
        unit=proposal.unit,
        unit_price=str(proposal.unit_price),
        currency=proposal.currency,
        delivery_destination=proposal.delivery_destination,
        delivery_date=proposal.delivery_date,
    )


@router.patch("/facts/{fact_id}", response_model=FactCorrectionResponse)
def correct_fact_route(
    deal_id: UUID,
    fact_id: UUID,
    payload: CorrectFactRequest,
    actor: ActorContext = Depends(get_current_actor),
    repository: CommunicationRepository = Depends(get_communication_repository),
    db: Session = Depends(get_db),
) -> FactCorrectionResponse:
    """Record a user correction as a new private candidate with the same evidence."""
    try:
        fact_field = FactField(payload.field)
        ExtractedFact(
            schema_version=AI_SCHEMA_VERSION,
            field=fact_field,
            value=payload.typed_value,
            source=SourceReference(
                schema_version=AI_SCHEMA_VERSION,
                message_id=None,
                quote=None,
                unknown_reason="Human correction of a source-backed suggestion",
            ),
            currency_or_unit=payload.currency_or_unit,
        )
    except (ValueError, AIContractError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Corrected fact does not match a supported field format",
        ) from exc

    try:
        replaced, corrected = correct_constraint(
            actor,
            deal_id,
            fact_id,
            expected_version=payload.expected_version,
            field=fact_field.value,
            typed_value=payload.typed_value,
            currency_or_unit=payload.currency_or_unit,
            repository=repository,
        )
        db.commit()
    except (
        ConstraintNotFound,
        OrganizationAccessDenied,
        ConcurrentConstraintUpdate,
        InvalidTransition,
        InvariantViolation,
        CommunicationScopeError,
    ) as exc:
        db.rollback()
        _raise_review_error(exc)
    except Exception:
        db.rollback()
        raise

    return FactCorrectionResponse(
        replaced_fact=_to_constraint_response(replaced),
        corrected_fact=_to_constraint_response(corrected),
    )


def _to_message_response(message: Message) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        author_user_id=message.author_user_id,
        author_agent_id=message.author_agent_id,
        body=message.body,
        visibility=message.visibility.value,
        source_type=message.source_type.value,
        source_reference=message.source_reference,
        created_at=message.created_at,
    )


def _to_constraint_response(constraint: Constraint | ConstraintModel) -> ConstraintResponse:
    kind = constraint.kind if isinstance(constraint.kind, str) else constraint.kind.value
    status_str = constraint.status if isinstance(constraint.status, str) else constraint.status.value
    visibility = (
        constraint.visibility
        if isinstance(constraint.visibility, str)
        else constraint.visibility.value
    )
    return ConstraintResponse(
        id=constraint.id,
        deal_id=constraint.deal_id,
        owner_organization_id=constraint.owner_organization_id,
        field=constraint.field,
        typed_value=constraint.typed_value,
        currency_or_unit=constraint.currency_or_unit,
        kind=kind,
        status=status_str,
        visibility=visibility,
        source_message_id=constraint.source_message_id,
        source_span=constraint.source_span,
        confirmed_by=constraint.confirmed_by,
        confirmed_at=constraint.confirmed_at,
        version=constraint.version,
        created_at=constraint.created_at,
    )


def _raise_review_error(error: Exception) -> NoReturn:
    """Translate application review outcomes into the HTTP error contract."""
    if isinstance(error, (ConstraintNotFound, CommunicationNotFound)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, OrganizationAccessDenied):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    if isinstance(error, (ConcurrentConstraintUpdate, InvalidTransition)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if isinstance(error, (AmbiguousOrganization, InvariantViolation)):
        raise HTTPException(status_code=422, detail=str(error)) from error
    if isinstance(error, CommunicationScopeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found"
        ) from error
    raise error


@router.post(
    "/messages",
    status_code=status.HTTP_201_CREATED,
    response_model=MessageResponse,
)
def add_message_route(
    deal_id: UUID,
    payload: AddMessageRequest,
    actor: ActorContext = Depends(get_current_actor),
    repository: CommunicationRepository = Depends(get_communication_repository),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Store a message attributed to the verified actor for its deal party."""
    try:
        message = add_message(
            actor,
            deal_id,
            AddMessageCommand(
                body=payload.body,
                visibility=payload.visibility,
                source_reference=payload.source_reference,
                organization_id=payload.organization_id,
            ),
            repository,
        )
    except (
        CommunicationNotFound,
        OrganizationAccessDenied,
        AmbiguousOrganization,
        InvariantViolation,
        CommunicationScopeError,
    ) as exc:
        _raise_review_error(exc)
    db.commit()
    return _to_message_response(message)


@router.get("/messages", response_model=list[MessageResponse])
def list_messages_route(
    deal_id: UUID,
    organization_id: UUID | None = Query(default=None),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    actor: ActorContext = Depends(get_current_actor),
    repository: CommunicationRepository = Depends(get_communication_repository),
) -> list[MessageResponse]:
    """List the messages the actor's deal party may read."""
    try:
        messages = list_visible_messages(
            actor,
            deal_id,
            repository,
            organization_id=organization_id,
            limit=limit,
            offset=offset,
        )
    except (
        CommunicationNotFound,
        OrganizationAccessDenied,
        AmbiguousOrganization,
        CommunicationScopeError,
    ) as exc:
        _raise_review_error(exc)
    return [_to_message_response(message) for message in messages]


@router.get("/facts", response_model=list[ConstraintResponse])
def list_facts_route(
    deal_id: UUID,
    organization_id: UUID | None = Query(default=None),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    actor: ActorContext = Depends(get_current_actor),
    repository: CommunicationRepository = Depends(get_communication_repository),
) -> list[ConstraintResponse]:
    """List the extracted facts the actor's deal party may read."""
    try:
        constraints = list_visible_constraints(
            actor,
            deal_id,
            repository,
            organization_id=organization_id,
            limit=limit,
            offset=offset,
        )
    except (
        CommunicationNotFound,
        OrganizationAccessDenied,
        AmbiguousOrganization,
        CommunicationScopeError,
    ) as exc:
        _raise_review_error(exc)
    return [_to_constraint_response(constraint) for constraint in constraints]


@router.post(
    "/facts",
    status_code=status.HTTP_201_CREATED,
    response_model=ConstraintResponse,
)
def create_fact_route(
    deal_id: UUID,
    payload: CreateFactRequest,
    actor: ActorContext = Depends(get_current_actor),
    repository: CommunicationRepository = Depends(get_communication_repository),
    db: Session = Depends(get_db),
) -> ConstraintResponse:
    """Create a user-entered fact for an organization the actor may represent."""
    try:
        constraint = create_manual_constraint(
            actor,
            deal_id,
            CreateManualConstraintCommand(
                field=payload.field,
                typed_value=payload.typed_value,
                currency_or_unit=payload.currency_or_unit,
                kind=payload.kind,
                visibility=payload.visibility,
                organization_id=payload.organization_id,
            ),
            repository,
        )
    except (
        CommunicationNotFound,
        OrganizationAccessDenied,
        AmbiguousOrganization,
        InvariantViolation,
        CommunicationScopeError,
    ) as exc:
        db.rollback()
        _raise_review_error(exc)
    db.commit()
    return _to_constraint_response(constraint)


def _review_fact(
    *,
    deal_id: UUID,
    fact_id: UUID,
    action: ConstraintReviewAction,
    actor: ActorContext,
    repository: CommunicationRepository,
    db: Session,
) -> ConstraintResponse:
    try:
        constraint = review_constraint(actor, deal_id, fact_id, action, repository)
    except (
        ConstraintNotFound,
        OrganizationAccessDenied,
        ConcurrentConstraintUpdate,
        InvalidTransition,
        InvariantViolation,
        CommunicationScopeError,
    ) as exc:
        _raise_review_error(exc)
    db.commit()
    return _to_constraint_response(constraint)


@router.post("/facts/{fact_id}/confirm", response_model=ConstraintResponse)
def confirm_fact_route(
    deal_id: UUID,
    fact_id: UUID,
    actor: ActorContext = Depends(get_current_actor),
    repository: CommunicationRepository = Depends(get_communication_repository),
    db: Session = Depends(get_db),
) -> ConstraintResponse:
    """Confirm an extracted fact for a member of its owning party."""
    return _review_fact(
        deal_id=deal_id,
        fact_id=fact_id,
        action=ConstraintReviewAction.CONFIRM,
        actor=actor,
        repository=repository,
        db=db,
    )


@router.post("/facts/{fact_id}/reject", response_model=ConstraintResponse)
def reject_fact_route(
    deal_id: UUID,
    fact_id: UUID,
    actor: ActorContext = Depends(get_current_actor),
    repository: CommunicationRepository = Depends(get_communication_repository),
    db: Session = Depends(get_db),
) -> ConstraintResponse:
    """Reject an extracted or clarification-needed fact for its owning party."""
    return _review_fact(
        deal_id=deal_id,
        fact_id=fact_id,
        action=ConstraintReviewAction.REJECT,
        actor=actor,
        repository=repository,
        db=db,
    )


@router.post("/facts/{fact_id}/clarify", response_model=ConstraintResponse)
def clarify_fact_route(
    deal_id: UUID,
    fact_id: UUID,
    actor: ActorContext = Depends(get_current_actor),
    repository: CommunicationRepository = Depends(get_communication_repository),
    db: Session = Depends(get_db),
) -> ConstraintResponse:
    """Request clarification for an extracted fact for its owning party."""
    return _review_fact(
        deal_id=deal_id,
        fact_id=fact_id,
        action=ConstraintReviewAction.REQUEST_CLARIFICATION,
        actor=actor,
        repository=repository,
        db=db,
    )


@router.patch("/facts/{fact_id}/visibility", response_model=ConstraintResponse)
def update_fact_visibility_route(
    deal_id: UUID,
    fact_id: UUID,
    payload: UpdateFactVisibilityRequest,
    actor: ActorContext = Depends(get_current_actor),
    repository: CommunicationRepository = Depends(get_communication_repository),
    db: Session = Depends(get_db),
) -> ConstraintResponse:
    """Update visibility of an extracted fact only for an authorized owner organization member."""
    deal = repository.get_deal_for_participant(deal_id, actor.user_id)
    if deal is None or deal.id != deal_id or not actor.can_access_deal(deal):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    row = db.scalar(
        select(ConstraintModel)
        .where(
            ConstraintModel.id == fact_id,
            ConstraintModel.deal_id == deal_id,
        )
        .with_for_update()
    )
    if row is None or row.owner_organization_id not in (
        deal.buyer_organization_id,
        deal.seller_organization_id,
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fact not found")

    if row.owner_organization_id not in actor.organization_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an authorized member of the owner organization can modify fact visibility",
        )

    membership_id = db.scalar(
        select(OrganizationMember.id)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .join(User, User.id == OrganizationMember.user_id)
        .where(
            OrganizationMember.organization_id == row.owner_organization_id,
            OrganizationMember.user_id == actor.user_id,
            OrganizationMember.status == "ACTIVE",
            Organization.status == "ACTIVE",
            User.status == "ACTIVE",
        )
        .with_for_update(of=OrganizationMember)
    )
    if membership_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an authorized member of the owner organization can modify fact visibility",
        )

    try:
        previous_visibility = row.visibility
        if previous_visibility != payload.visibility.value:
            if payload.visibility == Visibility.SHAREABLE and row.source_message_id is not None:
                source_visibility = db.scalar(
                    select(MessageModel.visibility).where(MessageModel.id == row.source_message_id)
                )
                if source_visibility != Visibility.SHAREABLE.value:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="A shareable fact cannot cite a private message",
                    )
            row.visibility = payload.visibility.value
            row.version += 1
            audit_event = AuditEvent(
                aggregate_type="deal_fact",
                aggregate_id=row.id,
                event_type="FACT_VISIBILITY_UPDATED",
                actor_type="USER",
                actor_id=str(actor.user_id),
                occurred_at=datetime.now(UTC),
                payload={
                    "deal_id": str(deal_id),
                    "fact_id": str(row.id),
                    "previous_visibility": previous_visibility,
                    "new_visibility": row.visibility,
                    "owner_organization_id": str(row.owner_organization_id),
                },
            )
            db.add(audit_event)
            queue_deal_workflow_notification(
                db,
                deal_id=deal_id,
                record_id=row.id,
                kind=NotificationKind.CONSTRAINT_CHANGED,
            )
            logger.info(
                "Fact %s visibility updated from %s to %s for deal %s by user %s",
                row.id,
                previous_visibility,
                row.visibility,
                deal_id,
                actor.user_id,
            )

        db.commit()
        db.refresh(row)
    except Exception:
        db.rollback()
        raise

    return _to_constraint_response(row)
