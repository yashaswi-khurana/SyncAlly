"""SQLAlchemy model registry.

Import every model here so Alembic sees one complete metadata registry.
Keep model definitions in focused modules grouped by business capability.
"""

from syncally.infrastructure.models.agreements import (
    AgreementRoutingDecision,
    AgreementVersion,
    Approval,
    Obligation,
)
from syncally.infrastructure.models.base import Base
from syncally.infrastructure.models.deal_cases import DealCaseEvidenceModel, DealCaseModel
from syncally.infrastructure.models.deals import (
    Constraint,
    Conversation,
    CounterpartyOnboarding,
    Deal,
    Message,
)
from syncally.infrastructure.models.demo import DemoFixture
from syncally.infrastructure.models.fulfillment import FulfillmentEvent
from syncally.infrastructure.models.identity import (
    Organization,
    OrganizationApprovalRoutingPolicy,
    OrganizationMember,
    OrganizationProfile,
    RefreshToken,
    User,
)
from syncally.infrastructure.models.marketplace import MarketplaceListing, MarketplaceRFQ
from syncally.infrastructure.models.negotiation import (
    NegotiationAction,
    NegotiationSession,
    Proposal,
)
from syncally.infrastructure.models.operations import AuditEvent, OutboxEvent
from syncally.infrastructure.models.payments import PaymentIntent, PaymentMilestone, WebhookEvent

__all__ = [
    "AgreementRoutingDecision",
    "AgreementVersion",
    "Approval",
    "AuditEvent",
    "Base",
    "Constraint",
    "Conversation",
    "CounterpartyOnboarding",
    "Deal",
    "DealCaseEvidenceModel",
    "DealCaseModel",
    "DemoFixture",
    "FulfillmentEvent",
    "Message",
    "MarketplaceListing",
    "MarketplaceRFQ",
    "NegotiationAction",
    "NegotiationSession",
    "Obligation",
    "Organization",
    "OrganizationApprovalRoutingPolicy",
    "OrganizationMember",
    "OrganizationProfile",
    "OutboxEvent",
    "PaymentIntent",
    "PaymentMilestone",
    "Proposal",
    "RefreshToken",
    "User",
    "WebhookEvent",
]
