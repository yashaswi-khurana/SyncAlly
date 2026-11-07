"""Persistence for organization approval routing policies.

Shared by the organizations settings API (create/update/remove the policy)
and the agreements repository (reading it, with a row lock, while recording
a routed decision). Keeping both call sites on one converter and one set of
validation rules avoids the two ever disagreeing about what a valid policy
is.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syncally.domain.organizations.approval_routing import ApprovalRoutingPolicy
from syncally.domain.organizations.organization import (
    OrganizationCapability,
    resolve_effective_capabilities,
)
from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import OrganizationId, UserId
from syncally.infrastructure.models import (
    AgreementRoutingDecision,
    Organization,
    OrganizationApprovalRoutingPolicy,
    OrganizationMember,
    User,
)
from syncally.infrastructure.repositories._timestamps import as_utc


def routing_policy_to_domain(row: OrganizationApprovalRoutingPolicy) -> ApprovalRoutingPolicy:
    return ApprovalRoutingPolicy(
        organization_id=OrganizationId(row.organization_id),
        mode=row.mode,
        approver_user_ids=tuple(UserId(UUID(uid)) for uid in row.approver_user_ids),
        version=row.version,
        created_at=as_utc(row.created_at),
        updated_at=as_utc(row.updated_at),
        updated_by_user_id=UserId(row.updated_by_user_id) if row.updated_by_user_id else None,
    )


class SqlAlchemyApprovalRoutingPolicyRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, organization_id: UUID, *, for_update: bool = False) -> ApprovalRoutingPolicy | None:
        stmt = select(OrganizationApprovalRoutingPolicy).where(
            OrganizationApprovalRoutingPolicy.organization_id == organization_id
        )
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        row = self._db.scalar(stmt)
        return routing_policy_to_domain(row) if row is not None else None

    def eligible_approver_ids(
        self, organization_id: UUID, user_ids: tuple[UserId, ...], *, for_update: bool = False
    ) -> frozenset[UserId]:
        """Fresh check: still an active member of this organization with AGREEMENT_APPROVAL.

        ``for_update`` takes a FOR SHARE lock on the matching membership rows,
        held for the rest of this transaction - use it right before a decision
        that must not be undercut by a revocation racing the read (an admin's
        revoke issues an UPDATE on that same row, which then blocks until this
        transaction commits or rolls back).
        """
        if not user_ids:
            return frozenset()
        stmt = (
            select(OrganizationMember.user_id, OrganizationMember.role, OrganizationMember.capabilities)
            .join(Organization, Organization.id == OrganizationMember.organization_id)
            .join(User, User.id == OrganizationMember.user_id)
            .where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id.in_(user_ids),
                OrganizationMember.status == "ACTIVE",
                Organization.status == "ACTIVE",
                User.status == "ACTIVE",
            )
        )
        if for_update:
            stmt = stmt.with_for_update(read=True, of=OrganizationMember)
        rows = self._db.execute(stmt).all()
        eligible: set[UserId] = set()
        for user_id, role, capabilities in rows:
            if OrganizationCapability.AGREEMENT_APPROVAL in resolve_effective_capabilities(role, capabilities):
                eligible.add(UserId(user_id))
        return frozenset(eligible)

    def save(
        self,
        policy: ApprovalRoutingPolicy,
        *,
        expected_version: int | None,
        updated_by_user_id: UUID,
    ) -> ApprovalRoutingPolicy:
        """Create or update the policy with optimistic concurrency.

        Every configured approver must currently be an eligible (active,
        AGREEMENT_APPROVAL-capable) member of this organization - a policy
        can never name someone who could not actually act on it.
        """
        eligible = self.eligible_approver_ids(policy.organization_id, policy.approver_user_ids)
        ineligible = [uid for uid in policy.approver_user_ids if uid not in eligible]
        if ineligible:
            raise InvariantViolation(
                "All approval routing approvers must be active organization members "
                f"with AGREEMENT_APPROVAL capability; ineligible: {', '.join(str(u) for u in ineligible)}"
            )

        row = self._db.scalar(
            select(OrganizationApprovalRoutingPolicy)
            .where(OrganizationApprovalRoutingPolicy.organization_id == policy.organization_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        now = datetime.now(UTC)
        if row is None:
            if expected_version not in (None, 0):
                raise InvariantViolation("Approval routing policy version conflict; stale write rejected")
            row = OrganizationApprovalRoutingPolicy(
                organization_id=policy.organization_id,
                mode=policy.mode.value,
                approver_user_ids=[str(uid) for uid in policy.approver_user_ids],
                version=1,
                updated_by_user_id=updated_by_user_id,
                created_at=now,
                updated_at=now,
            )
            self._db.add(row)
            try:
                self._db.flush()
            except IntegrityError as error:
                # SELECT ... FOR UPDATE can't lock a row that doesn't exist yet,
                # so two concurrent first-time creates both reach this insert;
                # the loser hits the primary key and must be told to retry,
                # not blow up as a server error.
                raise InvariantViolation(
                    "Approval routing policy version conflict; stale write rejected"
                ) from error
            return routing_policy_to_domain(row)

        # Updating an existing policy always requires the caller's last-seen
        # version - unlike the create-without-version path above, skipping
        # this check here would let a stale edit silently clobber a newer one.
        if expected_version is None or row.version != expected_version:
            raise InvariantViolation("Approval routing policy version conflict; stale write rejected")

        row.mode = policy.mode.value
        row.approver_user_ids = [str(uid) for uid in policy.approver_user_ids]
        row.version = row.version + 1
        row.updated_by_user_id = updated_by_user_id
        row.updated_at = now
        self._db.flush()
        return routing_policy_to_domain(row)

    def delete(self, organization_id: UUID, *, expected_version: int | None) -> bool:
        """Remove the policy, reverting the organization to default bilateral approval.

        Also wipes this org's recorded per-approver routing decisions: a
        recreated policy starts back at version 1, so leaving old decisions
        in place would let them satisfy the new policy as "current" without
        anyone actually voting under it.
        """
        row = self._db.scalar(
            select(OrganizationApprovalRoutingPolicy)
            .where(OrganizationApprovalRoutingPolicy.organization_id == organization_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if row is None:
            return False
        if expected_version is not None and row.version != expected_version:
            raise InvariantViolation("Approval routing policy version conflict; stale write rejected")
        self._db.delete(row)
        self._db.execute(
            delete(AgreementRoutingDecision).where(
                AgreementRoutingDecision.organization_id == organization_id
            )
        )
        self._db.flush()
        return True
