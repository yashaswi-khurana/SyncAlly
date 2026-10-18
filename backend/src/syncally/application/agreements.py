"""Approval recording and bilateral agreement commit use cases.

This module owns the orchestration for CommitAgreement: it calls a
persistence port that atomically validates and commits an agreement version,
then derives obligations and writes the audit/outbox records that stage
exit depends on. It must stay free of HTTP parsing, request/response
schemas, and SQLAlchemy so the rules can be tested against a fake repository.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from syncally.domain.agreements.agreement import Agreement, Approval, ApprovalDecision
from syncally.domain.agreements.obligations import ObligationDraft, build_obligations
from syncally.domain.shared.errors import DomainError


class AgreementNotFound(DomainError):
    """The deal or the requested agreement version does not exist."""


class StaleAgreementVersion(DomainError):
    """The version is no longer the current, pending-approval candidate."""


class WrongTermsHash(DomainError):
    """The caller's hash does not match the stored agreement version's hash."""


class UnauthorizedApproval(DomainError):
    """The actor cannot approve on behalf of the requested organization."""


class DuplicateApproval(DomainError):
    """The organization already recorded a decision for this agreement version."""


class AgreementAlreadyCommitted(DomainError):
    """Another request already committed this agreement version."""


@dataclass(frozen=True)
class RecordApprovalCommand:
    """Input for recording one organization's decision on an agreement version."""

    deal_id: UUID
    version_number: int
    terms_hash: str
    organization_id: UUID
    user_id: UUID
    decision: ApprovalDecision


@dataclass(frozen=True)
class CommitAgreementCommand:
    """Input for committing an agreement once both parties have approved."""

    deal_id: UUID
    expected_version: int
    expected_terms_hash: str


@dataclass(frozen=True)
class AuditEventDraft:
    aggregate_type: str
    aggregate_id: UUID
    event_type: str
    actor_type: str
    actor_id: str
    occurred_at: datetime
    correlation_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OutboxEventDraft:
    aggregate_type: str
    aggregate_id: UUID
    event_type: str
    payload: dict[str, Any]


class AgreementRepository(Protocol):
    """Persistence port for approvals and the atomic agreement commit.

    The adapter owns the transaction's invariants: ``record_approval`` must
    reject an unauthorized organization, a stale version, a wrong hash, and a
    repeated/conflicting decision; ``commit`` must verify both authorized
    approvals match the current version/hash, commit at most once under
    concurrent callers, and update the deal in the same transaction.
    """

    def record_approval(self, command: RecordApprovalCommand, *, now: datetime) -> Approval:
        """Persist one organization's approval decision."""

    def commit(self, command: CommitAgreementCommand, *, now: datetime) -> Agreement:
        """Validate both approvals and commit the agreement version."""


class ObligationRepository(Protocol):
    def add_all(
        self, deal_id: UUID, agreement_version_id: UUID, drafts: list[ObligationDraft]
    ) -> None:
        """Persist the obligations derived from a committed agreement."""


class AuditRepository(Protocol):
    def add(self, draft: AuditEventDraft) -> None:
        """Persist one audit record."""


class OutboxRepository(Protocol):
    def add(self, draft: OutboxEventDraft) -> None:
        """Persist one outbox row for later relay. Never call Temporal here."""


def record_approval(
    command: RecordApprovalCommand,
    repository: AgreementRepository,
    *,
    now: datetime | None = None,
) -> Approval:
    """Record one organization's approval of an agreement version."""
    return repository.record_approval(command, now=now or datetime.now(UTC))


def commit_agreement(
    command: CommitAgreementCommand,
    agreement_repository: AgreementRepository,
    obligation_repository: ObligationRepository,
    audit_repository: AuditRepository,
    outbox_repository: OutboxRepository,
    *,
    now: datetime | None = None,
    correlation_id: str | None = None,
) -> Agreement:
    """Commit an agreement, then save its obligations, audit, and outbox rows.

    All four writes happen through ports bound to one transaction by the
    caller; this function only orchestrates the order and payloads.
    """
    now = now or datetime.now(UTC)
    agreement = agreement_repository.commit(command, now=now)

    obligations = build_obligations(agreement.terms)
    obligation_repository.add_all(command.deal_id, agreement.version_id, obligations)

    audit_repository.add(
        AuditEventDraft(
            aggregate_type="agreement",
            aggregate_id=agreement.version_id,
            event_type="AGREEMENT_COMMITTED",
            actor_type="SYSTEM",
            actor_id="commit_agreement",
            occurred_at=now,
            correlation_id=correlation_id,
            payload={
                "deal_id": str(command.deal_id),
                "version_number": agreement.version_number,
                "terms_hash": agreement.terms_hash,
            },
        )
    )
    outbox_repository.add(
        OutboxEventDraft(
            aggregate_type="agreement",
            aggregate_id=agreement.version_id,
            event_type="AGREEMENT_COMMITTED",
            payload={
                "deal_id": str(command.deal_id),
                "agreement_version_id": str(agreement.version_id),
            },
        )
    )
    return agreement
