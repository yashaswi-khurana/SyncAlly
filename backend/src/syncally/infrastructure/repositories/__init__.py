"""Database repository adapters implementing application persistence ports."""

from syncally.infrastructure.repositories.agreements import (
    SqlAlchemyAgreementRepository,
    SqlAlchemyAuditRepository,
    SqlAlchemyObligationRepository,
    SqlAlchemyOutboxRepository,
    SqlAlchemyPaymentMilestoneRepository,
    commit_agreement_in_transaction,
    create_agreement_draft_in_transaction,
    create_reviewed_agreement_draft_in_transaction,
    propose_amendment_in_transaction,
    record_approval_in_transaction,
    record_routing_decision_in_transaction,
    withdraw_amendment_in_transaction,
)
from syncally.infrastructure.repositories.approval_routing import (
    SqlAlchemyApprovalRoutingPolicyRepository,
)
from syncally.infrastructure.repositories.communications import (
    CommunicationScopeError,
    SqlAlchemyCommunicationRepository,
)
from syncally.infrastructure.repositories.deal_cases import SqlAlchemyDealCaseRepository
from syncally.infrastructure.repositories.deals import SqlAlchemyDealRepository
from syncally.infrastructure.repositories.organizations import (
    SqlAlchemyOrganizationMemberRepository,
    SqlAlchemyOrganizationRepository,
)
from syncally.infrastructure.repositories.payments import (
    SqlAlchemyPaymentIntentRepository,
    authorize_payment_intent_in_transaction,
)
from syncally.infrastructure.repositories.reminders import SqlAlchemyReminderRepository

__all__ = [
    "CommunicationScopeError",
    "SqlAlchemyAgreementRepository",
    "SqlAlchemyApprovalRoutingPolicyRepository",
    "SqlAlchemyAuditRepository",
    "SqlAlchemyCommunicationRepository",
    "SqlAlchemyDealCaseRepository",
    "SqlAlchemyDealRepository",
    "SqlAlchemyObligationRepository",
    "SqlAlchemyOrganizationMemberRepository",
    "SqlAlchemyOrganizationRepository",
    "SqlAlchemyOutboxRepository",
    "SqlAlchemyPaymentIntentRepository",
    "SqlAlchemyPaymentMilestoneRepository",
    "SqlAlchemyReminderRepository",
    "authorize_payment_intent_in_transaction",
    "commit_agreement_in_transaction",
    "create_agreement_draft_in_transaction",
    "create_reviewed_agreement_draft_in_transaction",
    "propose_amendment_in_transaction",
    "record_approval_in_transaction",
    "record_routing_decision_in_transaction",
    "withdraw_amendment_in_transaction",
]
