"""Deal conversation and fact-review HTTP endpoints.

Routes validate request schemas, derive the actor from authentication, call the
application use cases, and translate their outcomes into a stable error contract.
The acting organization always comes from the verified actor, never from the
request as authority. Message bodies are never written to logs.
"""

from __future__ import annotations

from datetime import datetime
from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
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
    OrganizationAccessDenied,
    add_message,
    list_visible_constraints,
    list_visible_messages,
    review_constraint,
)
from syncally.application.identity import ActorContext
from syncally.domain.conversations import Constraint, Message, Visibility
from syncally.domain.shared.errors import InvalidTransition, InvariantViolation
from syncally.infrastructure.database import get_db
from syncally.infrastructure.repositories import (
    CommunicationScopeError,
    SqlAlchemyCommunicationRepository,
)

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


def get_communication_repository(
    db: Session = Depends(get_db),
) -> CommunicationRepository:
    """Provide the conversation persistence port for the current request."""
    return SqlAlchemyCommunicationRepository(db)


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


def _to_constraint_response(constraint: Constraint) -> ConstraintResponse:
    return ConstraintResponse(
        id=constraint.id,
        deal_id=constraint.deal_id,
        owner_organization_id=constraint.owner_organization_id,
        field=constraint.field,
        typed_value=constraint.typed_value,
        currency_or_unit=constraint.currency_or_unit,
        kind=constraint.kind.value,
        status=constraint.status.value,
        visibility=constraint.visibility.value,
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
