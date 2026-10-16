"""Strongly named identifiers keep unrelated UUIDs distinct to type checkers."""

from typing import NewType
from uuid import UUID

OrganizationId = NewType("OrganizationId", UUID)
UserId = NewType("UserId", UUID)
DealId = NewType("DealId", UUID)
ProposalId = NewType("ProposalId", UUID)
NegotiationSessionId = NewType("NegotiationSessionId", UUID)
AgreementId = NewType("AgreementId", UUID)
AgreementVersionId = NewType("AgreementVersionId", UUID)
PaymentMilestoneId = NewType("PaymentMilestoneId", UUID)
PaymentIntentId = NewType("PaymentIntentId", UUID)

