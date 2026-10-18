"""Conversation visibility and constraint-confirmation use cases."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from syncally.application.identity import ActorContext
from syncally.domain.conversations import (
    Constraint,
    Conversation,
    Message,
    Visibility,
)
from syncally.domain.deals.deal import Deal
from syncally.domain.shared.errors import DomainError
from syncally.domain.shared.identifiers import UserId


class ConstraintRepository(Protocol):
    """Persistence boundary needed to confirm a deal-scoped constraint."""

    def get_deal_for_participant(self, deal_id: UUID, user_id: UUID) -> Deal | None:
        """Load a deal only when the user is an active member of a party."""

    def get_constraint_for_deal(
        self, deal_id: UUID, constraint_id: UUID
    ) -> Constraint | None:
        """Load a constraint within the requested deal scope."""

    def save_constraint(self, constraint: Constraint) -> Constraint:
        """Persist the constraint's new review state."""


class ConstraintNotFound(DomainError):
    """The constraint, its deal, or the actor's deal access is unavailable."""


def can_view_message(
    actor: ActorContext,
    deal: Deal,
    conversation: Conversation,
    message: Message,
) -> bool:
    """Apply deal membership and message visibility to a conversation message."""
    if (
        conversation.deal_id != deal.id
        or conversation.owner_organization_id
        not in (deal.buyer_organization_id, deal.seller_organization_id)
        or message.conversation_id != conversation.id
        or not actor.can_access_deal(deal)
    ):
        return False
    return message.visibility is Visibility.SHAREABLE or (
        conversation.owner_organization_id in actor.organization_ids
    )


def can_view_constraint(actor: ActorContext, deal: Deal, constraint: Constraint) -> bool:
    """Apply deal membership and organization ownership to a constraint read."""
    if (
        constraint.deal_id != deal.id
        or constraint.owner_organization_id
        not in (deal.buyer_organization_id, deal.seller_organization_id)
        or not actor.can_access_deal(deal)
    ):
        return False
    return constraint.visibility is Visibility.SHAREABLE or (
        constraint.owner_organization_id in actor.organization_ids
    )


def confirm_constraint(
    actor: ActorContext,
    deal_id: UUID,
    constraint_id: UUID,
    repository: ConstraintRepository,
    *,
    now: datetime | None = None,
) -> Constraint:
    """Confirm an extracted fact only for a member of its owning deal party."""
    deal = repository.get_deal_for_participant(deal_id, actor.user_id)
    if deal is None or deal.id != deal_id or not actor.can_access_deal(deal):
        raise ConstraintNotFound("Constraint not found")

    constraint = repository.get_constraint_for_deal(deal_id, constraint_id)
    if constraint is None or constraint.deal_id != deal.id:
        raise ConstraintNotFound("Constraint not found")
    if constraint.owner_organization_id not in (
        deal.buyer_organization_id,
        deal.seller_organization_id,
    ):
        raise ConstraintNotFound("Constraint not found")
    if constraint.owner_organization_id not in actor.organization_ids:
        raise ConstraintNotFound("Constraint not found")

    constraint.confirm(
        confirmed_by=UserId(actor.user_id),
        confirmed_at=now or datetime.now(UTC),
    )
    return repository.save_constraint(constraint)
