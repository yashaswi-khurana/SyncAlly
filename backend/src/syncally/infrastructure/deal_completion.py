"""Complete a deal only from its current committed, fulfilled, paid terms."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from syncally.application.workflow_notifications import NotificationKind
from syncally.domain.agreements.fulfillment import FulfillmentStage, bounded_quantity
from syncally.domain.agreements.trade_terms import TradeTerms
from syncally.domain.deals.deal import Deal as DomainDeal
from syncally.domain.deals.deal import DealStatus
from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import AgreementVersionId, DealId, OrganizationId
from syncally.infrastructure.models import (
    AgreementVersion,
    AuditEvent,
    Deal,
    FulfillmentEvent,
    Obligation,
    PaymentIntent,
    PaymentMilestone,
)
from syncally.infrastructure.repositories._timestamps import as_utc
from syncally.infrastructure.workflow_notifications import queue_deal_workflow_notification


def _scaled(value: Decimal) -> int:
    value = bounded_quantity(value)
    sign, digits, exponent = value.as_tuple()
    significant = list(digits)
    while significant and significant[-1] == 0:
        significant.pop()
        exponent += 1
    coefficient = int("".join(str(digit) for digit in significant) or "0")
    scale = exponent + 18
    if scale < 0:
        raise ValueError("Quantity has more than 18 fractional digits")
    return (-coefficient if sign else coefficient) * (10**scale)


def _event_total(events: list[FulfillmentEvent], stage: FulfillmentStage) -> int:
    return sum(_scaled(Decimal(event.quantity)) for event in events if event.event_type == stage.value)


def delivery_obligation_fulfilled(
    db: Session, deal_id: UUID, agreement: AgreementVersion, terms: TradeTerms
) -> bool:
    if not terms.shipments or not terms.line_items:
        return False

    if terms.schema_version == 1:
        if len(terms.line_items) != 1 or len(terms.shipments) != 1:
            return False
        obligations = list(
            db.scalars(
                select(Obligation).where(
                    Obligation.deal_id == deal_id,
                    Obligation.agreement_version_id == agreement.id,
                    Obligation.obligation_type == "DELIVERY",
                    Obligation.source_terms_reference == "shipments[0]",
                )
            )
        )
        if len(obligations) != 1:
            return False
        matching_obligation_ids = select(Obligation.id).where(
            Obligation.deal_id == deal_id,
            Obligation.source_terms_reference == "shipments[0]",
        )
        events = list(
            db.scalars(
                select(FulfillmentEvent).where(
                    FulfillmentEvent.deal_id == deal_id,
                    FulfillmentEvent.obligation_id.in_(matching_obligation_ids),
                )
            )
        )
        if any(event.unit != terms.line_items[0].unit for event in events):
            return False
        expected = _scaled(terms.shipments[0].quantity)
        return all(_event_total(events, stage) == expected for stage in FulfillmentStage)

    # Schema 2: verify every shipment's delivery obligation has reached 100% confirmation
    for index, shipment in enumerate(terms.shipments):
        ref = shipment.id if shipment.id else f"shipments[{index}]"
        matching_obligation_ids = select(Obligation.id).where(
            Obligation.deal_id == deal_id,
            Obligation.source_terms_reference == ref,
        )
        events = list(
            db.scalars(
                select(FulfillmentEvent).where(
                    FulfillmentEvent.deal_id == deal_id,
                    FulfillmentEvent.obligation_id.in_(matching_obligation_ids),
                )
            )
        )
        if shipment.allocations:
            allowed_units = {a.unit for a in shipment.allocations}
            if any(event.unit not in allowed_units for event in events):
                return False
        if shipment.quantity is not None:
            expected = _scaled(shipment.quantity)
        elif shipment.allocations:
            expected = sum(_scaled(a.quantity) for a in shipment.allocations)
        else:
            return False
        if not all(_event_total(events, stage) == expected for stage in FulfillmentStage):
            return False
    return True


def payments_reconciled(
    db: Session, deal_id: UUID, agreement_version_id: UUID, terms: TradeTerms
) -> bool:
    seller_organization_id = db.scalar(
        select(Deal.seller_organization_id).where(Deal.id == deal_id)
    )
    if seller_organization_id is None:
        return False
    milestones = list(
        db.scalars(
            select(PaymentMilestone)
            .where(
                PaymentMilestone.deal_id == deal_id,
                PaymentMilestone.agreement_version_id == agreement_version_id,
            )
            .order_by(PaymentMilestone.sequence_number)
        )
    )
    if len(milestones) != len(terms.payment_terms):
        return False
    for expected_sequence, (milestone, term) in enumerate(
        zip(milestones, terms.payment_terms, strict=True), start=1
    ):
        if (
            milestone.sequence_number != expected_sequence
            or milestone.amount != term.amount.amount
            or milestone.currency != term.amount.currency
            or milestone.payer_organization_id != terms.buyer_id
            or (term.id and milestone.source_terms_reference and milestone.source_terms_reference != term.id)
        ):
            return False
        matching_milestone_ids = (
            select(PaymentMilestone.id).where(
                PaymentMilestone.deal_id == deal_id,
                PaymentMilestone.source_terms_reference == milestone.source_terms_reference,
            )
            if milestone.source_terms_reference
            else [milestone.id]
        )
        paid = db.scalar(
            select(PaymentIntent.id).where(
                PaymentIntent.deal_id == deal_id,
                PaymentIntent.payment_milestone_id.in_(matching_milestone_ids),
                PaymentIntent.seller_organization_id == seller_organization_id,
                PaymentIntent.payer_organization_id == milestone.payer_organization_id,
                PaymentIntent.status == "PAID",
                PaymentIntent.reconciliation_source.in_(("PAYPAL_SANDBOX", "OFFLINE_DEMO")),
                PaymentIntent.reconciliation_source == PaymentIntent.execution_mode,
                PaymentIntent.amount == milestone.amount,
                PaymentIntent.reconciled_amount == milestone.amount,
                PaymentIntent.last_reconciled_at.is_not(None),
                PaymentIntent.currency == milestone.currency,
            ).limit(1)
        )
        if paid is None:
            return False
    return True


def maybe_complete_deal(db: Session, deal_id: UUID, trigger_record_id: UUID) -> bool:
    """Persist the terminal transition atomically when both ledgers prove completion."""
    deal = db.scalar(
        select(Deal)
        .where(Deal.id == deal_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if deal is None or deal.status not in (DealStatus.AGREED.value, DealStatus.EXECUTING.value):
        return False
    agreement = (
        db.get(AgreementVersion, deal.current_agreement_version_id)
        if deal.current_agreement_version_id is not None
        else None
    )
    if (
        agreement is None
        or agreement.deal_id != deal_id
        or agreement.status != "COMMITTED"
        or agreement.committed_at is None
    ):
        return False
    try:
        terms = TradeTerms.from_canonical_json(agreement.canonical_terms_json)
        terms.validate_for_commit()
    except (KeyError, TypeError, ValueError, InvariantViolation):
        return False
    if terms.terms_hash != agreement.terms_hash or not delivery_obligation_fulfilled(
        db, deal_id, agreement, terms
    ):
        return False
    if not payments_reconciled(db, deal_id, agreement.id, terms):
        return False

    aggregate = DomainDeal(
        id=DealId(deal.id),
        buyer_organization_id=OrganizationId(deal.buyer_organization_id),
        seller_organization_id=OrganizationId(deal.seller_organization_id),
        created_at=as_utc(deal.created_at),
        status=DealStatus(deal.status),
        current_agreement_version_id=AgreementVersionId(agreement.id),
        version=deal.version,
    )
    if aggregate.status is DealStatus.AGREED:
        aggregate.begin_execution()
    aggregate.complete(fulfillment_complete=True, payments_reconciled=True)
    result = db.execute(
        update(Deal)
        .where(
            Deal.id == deal_id,
            Deal.version == deal.version,
            Deal.status == deal.status,
            Deal.current_agreement_version_id == agreement.id,
        )
        .values(status=aggregate.status.value, version=aggregate.version)
    )
    if result.rowcount != 1:
        raise RuntimeError("Deal changed while fulfillment completion was being recorded")
    deal.status = aggregate.status.value
    deal.version = aggregate.version
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    db.add(
        AuditEvent(
            aggregate_type="deal",
            aggregate_id=deal_id,
            event_type="DEAL_COMPLETED",
            actor_type="SYSTEM",
            actor_id="fulfillment_and_reconciled_payments",
            occurred_at=now,
            payload={
                "agreement_version_id": str(agreement.id),
                "terms_hash": agreement.terms_hash,
            },
        )
    )
    queue_deal_workflow_notification(
        db,
        deal_id=deal_id,
        record_id=trigger_record_id,
        kind=NotificationKind.DEAL_COMPLETED,
    )
    return True
