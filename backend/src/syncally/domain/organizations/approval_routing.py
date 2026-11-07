"""Organization-level approval routing policy and its pure evaluation rules.

A routing policy only constrains *which members of one organization* must
act, and in what order, before that organization's single bilateral
``Approval`` (see ``domain.agreements.agreement``) is recorded. It never
creates cross-organization authority: the counterparty's own approval is
untouched, and ``Agreement.commit`` still requires both organizations to
approve the identical terms hash exactly as it does when no policy exists.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from syncally.domain.agreements.agreement import ApprovalDecision
from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import OrganizationId, UserId

MAX_APPROVERS = 10


class ApprovalRoutingMode(StrEnum):
    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"


@dataclass(slots=True)
class ApprovalRoutingPolicy:
    """An organization's explicit, opt-in approval routing configuration.

    Absence of a policy (the default) means the organization's existing
    single-approver bilateral behavior is unchanged.
    """

    organization_id: OrganizationId
    mode: ApprovalRoutingMode
    approver_user_ids: tuple[UserId, ...]
    version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
    updated_by_user_id: UserId | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.mode, ApprovalRoutingMode):
            try:
                object.__setattr__(self, "mode", ApprovalRoutingMode(self.mode))
            except ValueError as exc:
                raise InvariantViolation(f"Invalid approval routing mode: {self.mode}") from exc
        self.approver_user_ids = tuple(self.approver_user_ids)
        if not self.approver_user_ids:
            raise InvariantViolation("An approval routing policy needs at least one eligible approver")
        if len(self.approver_user_ids) > MAX_APPROVERS:
            raise InvariantViolation(f"An approval routing policy cannot exceed {MAX_APPROVERS} approvers")
        if len(set(self.approver_user_ids)) != len(self.approver_user_ids):
            raise InvariantViolation("Approval routing approvers must be distinct")
        if self.version < 1:
            raise InvariantViolation("Approval routing policy version must be at least 1")


class RoutingSlotStatus(StrEnum):
    """The current actionability of one configured approver's seat."""

    REQUIRED = "REQUIRED"
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    REVOKED = "REVOKED"


class RoutingOutcomeStatus(StrEnum):
    """The aggregate state of one organization's routed decision."""

    REQUIRED = "REQUIRED"
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class RoutingDecisionRecord:
    """One eligible approver's latest recorded decision on an agreement version."""

    user_id: UserId
    decision: ApprovalDecision
    policy_version: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RoutingApproverSlot:
    user_id: UserId
    status: RoutingSlotStatus
    decision: ApprovalDecision | None
    stale: bool


@dataclass(frozen=True, slots=True)
class RoutingEvaluation:
    status: RoutingOutcomeStatus
    satisfied: bool
    rejected: bool
    finalize_decision: ApprovalDecision | None
    finalize_user_id: UserId | None
    slots: tuple[RoutingApproverSlot, ...] = field(default_factory=tuple)


def evaluate_routing(
    policy: ApprovalRoutingPolicy,
    decisions: Mapping[UserId, RoutingDecisionRecord],
    eligible_user_ids: frozenset[UserId],
) -> RoutingEvaluation:
    """Derive each approver's actionable status and whether the route is settled.

    ``eligible_user_ids`` must be a freshly checked set (active membership and
    current AGREEMENT_APPROVAL capability) - a configured approver outside
    this set is REVOKED and blocks completion until an authorized admin
    reassigns the policy; a stale decision from a prior policy version never
    counts toward satisfaction.
    """
    slots: list[RoutingApproverSlot] = []
    any_revoked = False
    any_reject = False
    reject_user: UserId | None = None
    next_required_claimed = False

    for user_id in policy.approver_user_ids:
        record = decisions.get(user_id)
        current = record is not None and record.policy_version == policy.version
        stale = record is not None and not current

        if user_id not in eligible_user_ids:
            status = RoutingSlotStatus.REVOKED
            any_revoked = True
        elif current and record.decision is ApprovalDecision.REJECT:
            status = RoutingSlotStatus.COMPLETED
            any_reject = True
            reject_user = user_id
        elif current and record.decision is ApprovalDecision.APPROVE:
            status = RoutingSlotStatus.COMPLETED
        elif policy.mode is ApprovalRoutingMode.PARALLEL or not next_required_claimed:
            status = RoutingSlotStatus.REQUIRED
            next_required_claimed = True
        else:
            status = RoutingSlotStatus.PENDING

        slots.append(
            RoutingApproverSlot(
                user_id=user_id,
                status=status,
                decision=record.decision if current else None,
                stale=stale,
            )
        )

    # A reject is always from an eligible, current slot (the REVOKED branch
    # above takes priority over it per-slot), so it finalizes as the veto it
    # is even if some other configured seat is separately revoked - a
    # revocation elsewhere must not suppress a vote that already landed.
    if any_reject:
        return RoutingEvaluation(
            status=RoutingOutcomeStatus.COMPLETED,
            satisfied=False,
            rejected=True,
            finalize_decision=ApprovalDecision.REJECT,
            finalize_user_id=reject_user,
            slots=tuple(slots),
        )

    if any_revoked:
        return RoutingEvaluation(
            status=RoutingOutcomeStatus.ERROR,
            satisfied=False,
            rejected=False,
            finalize_decision=None,
            finalize_user_id=None,
            slots=tuple(slots),
        )

    if all(slot.status is RoutingSlotStatus.COMPLETED for slot in slots):
        last_decider = max(
            (decisions[slot.user_id] for slot in slots),
            key=lambda record: record.created_at,
        )
        return RoutingEvaluation(
            status=RoutingOutcomeStatus.COMPLETED,
            satisfied=True,
            rejected=False,
            finalize_decision=ApprovalDecision.APPROVE,
            finalize_user_id=last_decider.user_id,
            slots=tuple(slots),
        )

    any_decided = any(slot.status is RoutingSlotStatus.COMPLETED for slot in slots)
    return RoutingEvaluation(
        status=RoutingOutcomeStatus.PENDING if any_decided else RoutingOutcomeStatus.REQUIRED,
        satisfied=False,
        rejected=False,
        finalize_decision=None,
        finalize_user_id=None,
        slots=tuple(slots),
    )


def can_act(
    evaluation: RoutingEvaluation,
    user_id: UserId,
    decision: ApprovalDecision,
) -> bool:
    """Whether ``user_id`` may record ``decision`` right now, given the current evaluation.

    REJECT is a veto: any eligible, non-revoked approver may cast or revise it
    at any time regardless of sequence order - the same "any single
    rejection blocks" behavior the unrouted default already has. APPROVE
    must come from a slot that is either REQUIRED (their turn - the only
    state possible in PARALLEL mode, or the next slot in SEQUENTIAL mode) or
    already COMPLETED (revising their own prior decision); a PENDING slot
    means a SEQUENTIAL predecessor has not acted yet.
    """
    slot = next((s for s in evaluation.slots if s.user_id == user_id), None)
    if slot is None or slot.status is RoutingSlotStatus.REVOKED:
        return False
    if decision is ApprovalDecision.REJECT:
        return True
    return slot.status is not RoutingSlotStatus.PENDING
