"""Application service for scheduling, evaluating, and safely dispatching obligation reminders."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from syncally.application.workflow_notifications import NotificationKind
from syncally.domain.agreements.agreement import AgreementStatus
from syncally.domain.deals.cases import CaseStatus
from syncally.domain.deals.deal import DealStatus
from syncally.domain.reminders.reminder import (
    DEFAULT_RECURRENCE_CAP,
    DealReminder,
    ReminderChannel,
    ReminderScope,
    ReminderStatus,
    SuppressionReason,
    build_deduplication_key,
    ensure_utc,
)
from syncally.domain.shared.errors import DomainError
from syncally.domain.shared.identifiers import DealId, OrganizationId, UserId
from syncally.infrastructure.models.agreements import (
    AgreementRoutingDecision,
    AgreementVersion,
    Obligation,
)
from syncally.infrastructure.models.deal_cases import DealCaseModel
from syncally.infrastructure.models.deals import Deal
from syncally.infrastructure.models.fulfillment import FulfillmentEvent
from syncally.infrastructure.models.identity import (
    Organization,
    OrganizationApprovalRoutingPolicy,
    OrganizationMember,
)
from syncally.infrastructure.models.operations import AuditEvent
from syncally.infrastructure.models.payments import PaymentIntent, PaymentMilestone
from syncally.infrastructure.models.reminders import DealReminderModel
from syncally.infrastructure.repositories.reminders import SqlAlchemyReminderRepository
from syncally.infrastructure.workflow_notifications import queue_deal_workflow_notification

logger = logging.getLogger(__name__)

TERMINAL_DEAL_STATUSES = frozenset(
    {
        DealStatus.COMPLETED.value,
        DealStatus.CANCELLED.value,
        DealStatus.EXPIRED.value,
    }
)

DEFAULT_REMINDER_INTERVAL = timedelta(days=2)


class ReminderAccessDenied(DomainError):
    """The requesting actor cannot access reminders for this organization."""


def _is_active_member(
    db: Session, organization_id: UUID, user_id: UUID | None = None
) -> bool:
    """Verify that an organization exists and, if specified, the user is an active member."""
    org = db.get(Organization, organization_id)
    if org is None or getattr(org, "status", "ACTIVE") != "ACTIVE":
        return False
    if user_id is None:
        return True
    member = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.status == "ACTIVE",
        )
    )
    return member is not None


def schedule_deal_reminders(
    db: Session,
    deal_id: UUID,
    now: datetime | None = None,
) -> list[DealReminder]:
    """Inspect all obligations on a deal and sync/schedule durable reminders.

    Covers the 4 required scopes:
    1. Outstanding fulfillment (unconfirmed delivery quantity on committed agreement).
    2. Eligible-but-unacted milestone payments (unpaid milestone without active intent).
    3. Unresolved cases (cancellation or dispute awaiting response).
    4. Approval routing (pending approver seat under configured policy).
    """
    now_utc = ensure_utc(now or datetime.now(UTC), "now")
    repo = SqlAlchemyReminderRepository(db)

    deal = db.get(Deal, deal_id)
    if deal is None:
        return []

    # If deal is terminal, suppress all existing active reminders and do not schedule new ones.
    if deal.status in TERMINAL_DEAL_STATUSES:
        repo.suppress_active_for_deal(deal_id, SuppressionReason.DEAL_TERMINAL, now_utc)
        return []

    scheduled_reminders: list[DealReminder] = []

    # 1. SCOPE: FULFILLMENT
    # Check current committed agreement
    current_committed = db.scalar(
        select(AgreementVersion)
        .where(
            AgreementVersion.deal_id == deal_id,
            AgreementVersion.status == AgreementStatus.COMMITTED.value,
        )
        .order_by(AgreementVersion.version_number.desc())
        .limit(1)
    )

    if current_committed is not None:
        obligations = db.scalars(
            select(Obligation).where(
                Obligation.deal_id == deal_id,
                Obligation.agreement_version_id == current_committed.id,
            )
        ).all()

        for ob in obligations:
            # Query fulfillment events for this obligation
            confirmed_events = db.scalars(
                select(FulfillmentEvent).where(
                    FulfillmentEvent.deal_id == deal_id,
                    FulfillmentEvent.agreement_version_id == current_committed.id,
                    FulfillmentEvent.obligation_id == ob.id,
                    FulfillmentEvent.event_type == "CONFIRMED",
                )
            ).all()
            confirmed_total = sum(
                (Decimal(e.quantity) for e in confirmed_events), Decimal("0")
            )

            shipped_events = db.scalars(
                select(FulfillmentEvent).where(
                    FulfillmentEvent.deal_id == deal_id,
                    FulfillmentEvent.agreement_version_id == current_committed.id,
                    FulfillmentEvent.obligation_id == ob.id,
                    FulfillmentEvent.event_type == "SHIPPED",
                )
            ).all()
            shipped_total = sum(
                (Decimal(e.quantity) for e in shipped_events), Decimal("0")
            )

            planned_qty = Decimal("0")
            terms_data = current_committed.canonical_terms_json
            if isinstance(terms_data, dict) and "shipments" in terms_data and terms_data["shipments"]:
                try:
                    planned_qty = Decimal(str(terms_data["shipments"][0].get("quantity", "0")))
                except Exception:
                    planned_qty = Decimal("0")

            if (ob.status == "FULFILLED") or (planned_qty > Decimal("0") and confirmed_total >= planned_qty):
                # Obligation is completely confirmed; suppress active reminders
                repo.suppress_active_for_reference(
                    deal_id, ReminderScope.FULFILLMENT, ob.id, SuppressionReason.RESOLVED, now_utc
                )
            else:
                seller_org = ob.owner_organization_id or deal.seller_organization_id
                buyer_org = ob.counterparty_organization_id or deal.buyer_organization_id

                if planned_qty > Decimal("0") and shipped_total >= planned_qty:
                    # Goods shipped! Seller obligation fulfilled; responsible party switched to buyer.
                    repo.suppress_active_for_reference(
                        deal_id,
                        ReminderScope.FULFILLMENT,
                        ob.id,
                        SuppressionReason.ORGANIZATION_SWITCHED,
                        now_utc,
                        recipient_organization_id=seller_org,
                    )
                    recipient_org = buyer_org
                else:
                    # Still awaiting shipment from seller. Suppress buyer reminders if switched back.
                    repo.suppress_active_for_reference(
                        deal_id,
                        ReminderScope.FULFILLMENT,
                        ob.id,
                        SuppressionReason.ORGANIZATION_SWITCHED,
                        now_utc,
                        recipient_organization_id=buyer_org,
                    )
                    recipient_org = seller_org

                due_at = now_utc + DEFAULT_REMINDER_INTERVAL
                dedup_key = build_deduplication_key(
                    deal_id,
                    ReminderScope.FULFILLMENT,
                    ob.id,
                    0,
                    recipient_organization_id=recipient_org,
                )
                existing = repo.get_by_deduplication_key(dedup_key)
                if existing is None:
                    rem = DealReminder(
                        id=uuid4(),
                        deal_id=DealId(deal_id),
                        scope=ReminderScope.FULFILLMENT,
                        reference_id=ob.id,
                        recipient_organization_id=OrganizationId(recipient_org),
                        recipient_user_id=None,
                        status=ReminderStatus.SCHEDULED,
                        scheduled_for=now_utc,
                        due_at=due_at,
                        recurrence_cap=DEFAULT_RECURRENCE_CAP,
                        recurrence_count=0,
                        deduplication_key=dedup_key,
                        channel=ReminderChannel.IN_APP,
                    )
                    scheduled_reminders.append(repo.save(rem))

    # 2. SCOPE: MILESTONE
    if current_committed is not None:
        milestones = db.scalars(
            select(PaymentMilestone).where(
                PaymentMilestone.deal_id == deal_id,
                PaymentMilestone.agreement_version_id == current_committed.id,
            )
        ).all()

        for m in milestones:
            if m.status == "PAID":
                repo.suppress_active_for_reference(
                    deal_id, ReminderScope.MILESTONE, m.id, SuppressionReason.RESOLVED, now_utc
                )
                continue

            # Check if there is an active payment intent in-flight
            active_intent = db.scalar(
                select(PaymentIntent).where(
                    PaymentIntent.deal_id == deal_id,
                    PaymentIntent.payment_milestone_id == m.id,
                    PaymentIntent.status.not_in(["FAILED", "CANCELLED"]),
                ).limit(1)
            )

            if active_intent is not None and active_intent.status == "PAID":
                repo.suppress_active_for_reference(
                    deal_id, ReminderScope.MILESTONE, m.id, SuppressionReason.RESOLVED, now_utc
                )
                continue

            # If payment is in flight (not PAID, not FAILED, not CANCELLED), do not schedule a reminder
            if active_intent is not None:
                continue

            # Eligible-but-unacted milestone
            due_at = now_utc + DEFAULT_REMINDER_INTERVAL
            dedup_key = build_deduplication_key(
                deal_id,
                ReminderScope.MILESTONE,
                m.id,
                0,
                recipient_organization_id=m.payer_organization_id,
            )
            existing = repo.get_by_deduplication_key(dedup_key)
            if existing is None:
                rem = DealReminder(
                    id=uuid4(),
                    deal_id=DealId(deal_id),
                    scope=ReminderScope.MILESTONE,
                    reference_id=m.id,
                    recipient_organization_id=OrganizationId(m.payer_organization_id),
                    recipient_user_id=None,
                    status=ReminderStatus.SCHEDULED,
                    scheduled_for=now_utc,
                    due_at=due_at,
                    recurrence_cap=DEFAULT_RECURRENCE_CAP,
                    recurrence_count=0,
                    deduplication_key=dedup_key,
                    channel=ReminderChannel.IN_APP,
                )
                scheduled_reminders.append(repo.save(rem))

    # 3. SCOPE: CASE (Unresolved Disputes and Cancellations)
    cases = db.scalars(select(DealCaseModel).where(DealCaseModel.deal_id == deal_id)).all()
    for case in cases:
        if case.status in (CaseStatus.RESOLVED.value, CaseStatus.REJECTED.value, CaseStatus.WITHDRAWN.value):
            repo.suppress_active_for_reference(
                deal_id, ReminderScope.CASE, case.id, SuppressionReason.RESOLVED, now_utc
            )
        elif case.status in (CaseStatus.OPEN.value, CaseStatus.UNDER_REVIEW.value):
            # Counterparty needs to act
            recipient_org = (
                deal.seller_organization_id
                if case.requested_by_organization_id == deal.buyer_organization_id
                else deal.buyer_organization_id
            )
            due_at = now_utc + DEFAULT_REMINDER_INTERVAL
            dedup_key = build_deduplication_key(
                deal_id,
                ReminderScope.CASE,
                case.id,
                0,
                recipient_organization_id=recipient_org,
            )
            existing = repo.get_by_deduplication_key(dedup_key)
            if existing is None:
                rem = DealReminder(
                    id=uuid4(),
                    deal_id=DealId(deal_id),
                    scope=ReminderScope.CASE,
                    reference_id=case.id,
                    recipient_organization_id=OrganizationId(recipient_org),
                    recipient_user_id=None,
                    status=ReminderStatus.SCHEDULED,
                    scheduled_for=now_utc,
                    due_at=due_at,
                    recurrence_cap=DEFAULT_RECURRENCE_CAP,
                    recurrence_count=0,
                    deduplication_key=dedup_key,
                    channel=ReminderChannel.IN_APP,
                )
                scheduled_reminders.append(repo.save(rem))

    # 4. SCOPE: ROUTING (Approval Routing Pending Decision)
    latest_draft = db.scalar(
        select(AgreementVersion)
        .where(
            AgreementVersion.deal_id == deal_id,
            AgreementVersion.status == AgreementStatus.PENDING_APPROVAL.value,
        )
        .order_by(AgreementVersion.version_number.desc())
        .limit(1)
    )

    # First, suppress any active routing reminders for superseded drafts or when no draft is pending
    active_routing_rems = db.scalars(
        select(DealReminderModel).where(
            DealReminderModel.deal_id == deal_id,
            DealReminderModel.scope == ReminderScope.ROUTING.value,
            DealReminderModel.status.in_([ReminderStatus.SCHEDULED.value, ReminderStatus.PENDING.value]),
        )
    ).all()
    for active_rem in active_routing_rems:
        if latest_draft is None or active_rem.reference_id != latest_draft.id:
            active_rem.status = ReminderStatus.SUPPRESSED.value
            active_rem.suppressed_at = now_utc
            active_rem.suppression_reason = SuppressionReason.SUPERSEDED.value
            active_rem.next_attempt_at = None
            active_rem.version += 1
            active_rem.updated_at = now_utc

    if latest_draft is not None:
        for org_id in (deal.buyer_organization_id, deal.seller_organization_id):
            policy_row = db.get(OrganizationApprovalRoutingPolicy, org_id)
            if policy_row is None:
                continue

            # Query existing decisions for this agreement version
            decisions = db.scalars(
                select(AgreementRoutingDecision).where(
                    AgreementRoutingDecision.agreement_version_id == latest_draft.id,
                    AgreementRoutingDecision.organization_id == org_id,
                )
            ).all()
            decided_user_ids = {d.user_id for d in decisions if d.policy_version == policy_row.version}

            # Query active members of the organization
            active_members = db.scalars(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.status == "ACTIVE",
                )
            ).all()
            eligible_user_ids = {m.user_id for m in active_members}

            # Check approver seats
            configured_approver_ids: set[UUID] = set()
            for raw_approver_id in policy_row.approver_user_ids:
                try:
                    approver_id = UUID(str(raw_approver_id))
                except (ValueError, TypeError):
                    continue
                configured_approver_ids.add(approver_id)

                if approver_id in decided_user_ids:
                    # User already decided; suppress active reminder
                    repo.suppress_active_for_reference(
                        deal_id,
                        ReminderScope.ROUTING,
                        latest_draft.id,
                        SuppressionReason.RESOLVED,
                        now_utc,
                        recipient_organization_id=org_id,
                        recipient_user_id=approver_id,
                    )
                    continue

                if approver_id not in eligible_user_ids:
                    # Approver revoked or no longer member
                    repo.suppress_active_for_reference(
                        deal_id,
                        ReminderScope.ROUTING,
                        latest_draft.id,
                        SuppressionReason.RECIPIENT_REVOKED,
                        now_utc,
                        recipient_organization_id=org_id,
                        recipient_user_id=approver_id,
                    )
                    continue

                due_at = now_utc + DEFAULT_REMINDER_INTERVAL
                dedup_key = build_deduplication_key(
                    deal_id,
                    ReminderScope.ROUTING,
                    latest_draft.id,
                    0,
                    recipient_organization_id=org_id,
                    recipient_user_id=approver_id,
                )
                existing = repo.get_by_deduplication_key(dedup_key)
                if existing is None:
                    rem = DealReminder(
                        id=uuid4(),
                        deal_id=DealId(deal_id),
                        scope=ReminderScope.ROUTING,
                        reference_id=latest_draft.id,
                        recipient_organization_id=OrganizationId(org_id),
                        recipient_user_id=UserId(approver_id),
                        status=ReminderStatus.SCHEDULED,
                        scheduled_for=now_utc,
                        due_at=due_at,
                        recurrence_cap=DEFAULT_RECURRENCE_CAP,
                        recurrence_count=0,
                        deduplication_key=dedup_key,
                        channel=ReminderChannel.IN_APP,
                    )
                    scheduled_reminders.append(repo.save(rem))

            # Suppress active reminders for any approvers removed from policy
            for active_rem in active_routing_rems:
                if (
                    active_rem.reference_id == latest_draft.id
                    and active_rem.recipient_organization_id == org_id
                    and active_rem.recipient_user_id is not None
                    and active_rem.recipient_user_id not in configured_approver_ids
                ):
                    repo.suppress_active_for_reference(
                        deal_id,
                        ReminderScope.ROUTING,
                        latest_draft.id,
                        SuppressionReason.RECIPIENT_REVOKED,
                        now_utc,
                        recipient_organization_id=org_id,
                        recipient_user_id=active_rem.recipient_user_id,
                    )

    db.flush()
    return scheduled_reminders


def dispatch_due_reminders(
    db: Session,
    now: datetime | None = None,
    batch_size: int = 20,
    deal_id: UUID | None = None,
) -> list[DealReminder]:
    """Claim and dispatch due reminders, strictly rechecking obligation truth.

    Reminders never automatically approve, pay, complete, or escalate.
    If the underlying obligation was resolved or superseded, the reminder is
    suppressed rather than delivered.
    """
    now_utc = ensure_utc(now or datetime.now(UTC), "now")
    repo = SqlAlchemyReminderRepository(db)
    due_reminders = repo.claim_due_reminders(now_utc, limit=batch_size, deal_id=deal_id)
    processed: list[DealReminder] = []

    for reminder in due_reminders:
        deal = db.get(Deal, reminder.deal_id)
        if deal is None or deal.status in TERMINAL_DEAL_STATUSES:
            reminder.mark_suppressed(SuppressionReason.DEAL_TERMINAL, now_utc)
            repo.save(reminder)
            processed.append(reminder)
            continue

        # Recheck recipient membership
        if not _is_active_member(db, reminder.recipient_organization_id, reminder.recipient_user_id):
            reminder.mark_suppressed(SuppressionReason.RECIPIENT_REVOKED, now_utc)
            repo.save(reminder)
            processed.append(reminder)
            continue

        # Recheck obligation by scope
        suppress_reason: SuppressionReason | None = None

        if reminder.scope is ReminderScope.FULFILLMENT:
            ob = db.get(Obligation, reminder.reference_id)
            if ob is None:
                suppress_reason = SuppressionReason.SUPERSEDED
            else:
                # Check current committed version
                current_committed = db.scalar(
                    select(AgreementVersion)
                    .where(
                        AgreementVersion.deal_id == reminder.deal_id,
                        AgreementVersion.status == AgreementStatus.COMMITTED.value,
                    )
                    .order_by(AgreementVersion.version_number.desc())
                    .limit(1)
                )
                if current_committed is None or current_committed.id != ob.agreement_version_id:
                    suppress_reason = SuppressionReason.SUPERSEDED
                else:
                    # Check confirmed quantity
                    confirmed_events = db.scalars(
                        select(FulfillmentEvent).where(
                            FulfillmentEvent.deal_id == reminder.deal_id,
                            FulfillmentEvent.obligation_id == ob.id,
                            FulfillmentEvent.event_type == "CONFIRMED",
                        )
                    ).all()
                    confirmed_total = sum(
                        (Decimal(e.quantity) for e in confirmed_events), Decimal("0")
                    )
                    shipped_events = db.scalars(
                        select(FulfillmentEvent).where(
                            FulfillmentEvent.deal_id == reminder.deal_id,
                            FulfillmentEvent.obligation_id == ob.id,
                            FulfillmentEvent.event_type == "SHIPPED",
                        )
                    ).all()
                    shipped_total = sum(
                        (Decimal(e.quantity) for e in shipped_events), Decimal("0")
                    )

                    planned_qty = Decimal("0")
                    terms_data = current_committed.canonical_terms_json
                    if isinstance(terms_data, dict) and "shipments" in terms_data and terms_data["shipments"]:
                        try:
                            planned_qty = Decimal(str(terms_data["shipments"][0].get("quantity", "0")))
                        except Exception:
                            planned_qty = Decimal("0")

                    if (ob.status == "FULFILLED") or (planned_qty > Decimal("0") and confirmed_total >= planned_qty):
                        suppress_reason = SuppressionReason.RESOLVED
                    else:
                        seller_org = ob.owner_organization_id or deal.seller_organization_id
                        buyer_org = ob.counterparty_organization_id or deal.buyer_organization_id
                        if planned_qty > Decimal("0") and shipped_total >= planned_qty:
                            # Goods shipped: if reminder was for seller, duty switched to buyer
                            if reminder.recipient_organization_id == seller_org:
                                suppress_reason = SuppressionReason.ORGANIZATION_SWITCHED
                        else:
                            # Not shipped: if reminder was for buyer, duty is with seller
                            if reminder.recipient_organization_id == buyer_org:
                                suppress_reason = SuppressionReason.ORGANIZATION_SWITCHED

        elif reminder.scope is ReminderScope.MILESTONE:
            m = db.get(PaymentMilestone, reminder.reference_id)
            if m is None or m.status == "PAID":
                suppress_reason = SuppressionReason.RESOLVED
            else:
                current_committed = db.scalar(
                    select(AgreementVersion)
                    .where(
                        AgreementVersion.deal_id == reminder.deal_id,
                        AgreementVersion.status == AgreementStatus.COMMITTED.value,
                    )
                    .order_by(AgreementVersion.version_number.desc())
                    .limit(1)
                )
                if current_committed is None or current_committed.id != m.agreement_version_id:
                    suppress_reason = SuppressionReason.SUPERSEDED
                else:
                    active_intent = db.scalar(
                        select(PaymentIntent).where(
                            PaymentIntent.deal_id == reminder.deal_id,
                            PaymentIntent.payment_milestone_id == m.id,
                            PaymentIntent.status.not_in(["FAILED", "CANCELLED"]),
                        ).limit(1)
                    )
                    if active_intent is not None:
                        if active_intent.status == "PAID":
                            suppress_reason = SuppressionReason.RESOLVED
                        else:
                            # Payment intent in flight: defer attempt
                            reminder.next_attempt_at = now_utc + timedelta(hours=6)
                            repo.save(reminder)
                            processed.append(reminder)
                            continue

        elif reminder.scope is ReminderScope.CASE:
            case = db.get(DealCaseModel, reminder.reference_id)
            if case is None or case.status in (
                CaseStatus.RESOLVED.value,
                CaseStatus.REJECTED.value,
                CaseStatus.WITHDRAWN.value,
            ):
                suppress_reason = SuppressionReason.RESOLVED

        elif reminder.scope is ReminderScope.ROUTING:
            version = db.get(AgreementVersion, reminder.reference_id)
            if version is None or version.status != AgreementStatus.PENDING_APPROVAL.value:
                suppress_reason = SuppressionReason.SUPERSEDED
            else:
                policy_row = db.get(OrganizationApprovalRoutingPolicy, reminder.recipient_organization_id)
                if policy_row is None:
                    suppress_reason = SuppressionReason.SUPERSEDED
                elif reminder.recipient_user_id is not None:
                    approver_user_ids = {str(u) for u in policy_row.approver_user_ids}
                    if str(reminder.recipient_user_id) not in approver_user_ids:
                        suppress_reason = SuppressionReason.RECIPIENT_REVOKED
                    else:
                        decision = db.scalar(
                            select(AgreementRoutingDecision).where(
                                AgreementRoutingDecision.agreement_version_id == version.id,
                                AgreementRoutingDecision.organization_id == reminder.recipient_organization_id,
                                AgreementRoutingDecision.user_id == reminder.recipient_user_id,
                                AgreementRoutingDecision.policy_version == policy_row.version,
                            ).limit(1)
                        )
                        if decision is not None:
                            suppress_reason = SuppressionReason.RESOLVED

        if suppress_reason is not None:
            reminder.mark_suppressed(suppress_reason, now_utc)
            db.add(
                AuditEvent(
                    id=uuid4(),
                    aggregate_type="deal",
                    aggregate_id=reminder.deal_id,
                    event_type="REMINDER_SUPPRESSED",
                    actor_type="system" if reminder.recipient_user_id is None else "user",
                    actor_id="system" if reminder.recipient_user_id is None else str(reminder.recipient_user_id),
                    occurred_at=now_utc,
                    correlation_id=None,
                    payload={
                        "reminder_id": str(reminder.id),
                        "scope": reminder.scope.value,
                        "suppression_reason": suppress_reason.value,
                        "recipient_organization_id": str(reminder.recipient_organization_id),
                    },
                )
            )
            repo.save(reminder)
            processed.append(reminder)
            continue

        # Deliver via authorized IN_APP channel
        reminder.mark_delivered(now_utc)
        db.add(
            AuditEvent(
                id=uuid4(),
                aggregate_type="deal",
                aggregate_id=reminder.deal_id,
                event_type="REMINDER_DELIVERED",
                actor_type="system" if reminder.recipient_user_id is None else "user",
                actor_id="system" if reminder.recipient_user_id is None else str(reminder.recipient_user_id),
                occurred_at=now_utc,
                correlation_id=None,
                payload={
                    "reminder_id": str(reminder.id),
                    "scope": reminder.scope.value,
                    "channel": reminder.channel.value,
                    "recurrence_count": reminder.recurrence_count,
                    "recipient_organization_id": str(reminder.recipient_organization_id),
                },
            )
        )
        queue_deal_workflow_notification(
            db,
            deal_id=reminder.deal_id,
            record_id=reminder.id,
            kind=NotificationKind.REMINDER_TRIGGERED,
        )
        repo.save(reminder)

        # Schedule next recurrence if recurrence cap is not reached
        if reminder.recurrence_count < reminder.recurrence_cap:
            next_due = now_utc + DEFAULT_REMINDER_INTERVAL
            next_dedup_key = build_deduplication_key(
                reminder.deal_id,
                reminder.scope,
                reminder.reference_id,
                reminder.recurrence_count,
                recipient_organization_id=reminder.recipient_organization_id,
                recipient_user_id=reminder.recipient_user_id,
            )
            if repo.get_by_deduplication_key(next_dedup_key) is None:
                next_reminder = DealReminder(
                    id=uuid4(),
                    deal_id=reminder.deal_id,
                    scope=reminder.scope,
                    reference_id=reminder.reference_id,
                    recipient_organization_id=reminder.recipient_organization_id,
                    recipient_user_id=reminder.recipient_user_id,
                    status=ReminderStatus.SCHEDULED,
                    scheduled_for=now_utc,
                    due_at=next_due,
                    recurrence_cap=reminder.recurrence_cap,
                    recurrence_count=reminder.recurrence_count,
                    deduplication_key=next_dedup_key,
                    channel=reminder.channel,
                )
                repo.save(next_reminder)

        processed.append(reminder)

    db.flush()
    return processed


def list_deal_reminders(
    db: Session,
    deal_id: UUID,
    viewer_organization_id: UUID,
) -> list[DealReminder]:
    """List reminders for a deal, strictly scoped to viewer organization."""
    deal = db.get(Deal, deal_id)
    if deal is None:
        return []
    if viewer_organization_id not in (deal.buyer_organization_id, deal.seller_organization_id):
        raise ReminderAccessDenied("Actor organization does not participate in this deal")

    repo = SqlAlchemyReminderRepository(db)
    return repo.list_for_deal(deal_id, organization_id=viewer_organization_id)
