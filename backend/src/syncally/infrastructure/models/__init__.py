"""SQLAlchemy model registry.

Import every model here so Alembic sees one complete metadata registry.
Keep model definitions in focused modules grouped by business capability.
"""

from syncally.infrastructure.models.agreements import AgreementVersion, Approval, Obligation
from syncally.infrastructure.models.base import Base
from syncally.infrastructure.models.deals import Constraint, Conversation, Deal, Message
from syncally.infrastructure.models.identity import (
    Organization,
    OrganizationMember,
    RefreshToken,
    User,
)
from syncally.infrastructure.models.negotiation import NegotiationSession, Proposal
from syncally.infrastructure.models.operations import AuditEvent, OutboxEvent
from syncally.infrastructure.models.payments import PaymentIntent, PaymentMilestone, WebhookEvent

__all__ = [
    "AgreementVersion",
    "Approval",
    "AuditEvent",
    "Base",
    "Constraint",
    "Conversation",
    "Deal",
    "Message",
    "NegotiationSession",
    "Obligation",
    "Organization",
    "OrganizationMember",
    "OutboxEvent",
    "PaymentIntent",
    "PaymentMilestone",
    "Proposal",
    "RefreshToken",
    "User",
    "WebhookEvent",
]
