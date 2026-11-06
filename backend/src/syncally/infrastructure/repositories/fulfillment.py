"""Transactional persistence for fulfillment facts and their audit trail."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syncally.application.fulfillment import (
    FulfillmentConflict,
    FulfillmentEventRecord,
    FulfillmentSnapshot,
    FulfillmentUnavailable,
    RecordFulfillmentCommand,
)
from syncally.application.identity import ActorContext
from syncally.application.workflow_notifications import NotificationKind
from syncally.domain.agreements.fulfillment import FulfillmentStage, bounded_quantity, quantity_text
from syncally.domain.agreements.trade_terms import TradeTerms
from syncally.domain.deals.deal import Deal as DomainDeal
from syncally.domain.deals.deal import DealStatus
from syncally.domain.shared.errors import InvariantViolation
from syncally.infrastructure.deal_completion import (
    _scaled,
    maybe_complete_deal,
    payments_reconciled,
)
from syncally.infrastructure.models import (
    AgreementVersion,
    AuditEvent,
    Deal,
    FulfillmentEvent,
    Obligation,
)
from syncally.infrastructure.repositories._timestamps import as_utc
from syncally.infrastructure.workflow_notifications import queue_deal_workflow_notification


def _record(row: FulfillmentEvent) -> FulfillmentEventRecord:
    return FulfillmentEventRecord(
        id=row.id,
        deal_id=row.deal_id,
        agreement_version_id=row.agreement_version_id,
        terms_hash=row.terms_hash,
        obligation_id=row.obligation_id,
        organization_id=row.actor_organization_id,
        user_id=row.actor_user_id,
        stage=FulfillmentStage(row.event_type),
        quantity=bounded_quantity(Decimal(row.quantity)),
        unit=row.unit,
        source_type=row.source_type,
        recorded_at=as_utc(row.recorded_at),
        version=row.version,
    )


def _scaled_total(rows: list[FulfillmentEvent], stage: FulfillmentStage) -> int:
    return sum(_scaled(Decimal(row.quantity)) for row in rows if row.event_type == stage.value)


def _quantity(scaled: int) -> Decimal:
    sign = 1 if scaled < 0 else 0
    digits = tuple(int(digit) for digit in str(abs(scaled)))
    return Decimal((sign, digits, -18))


def _request_hash(command: RecordFulfillmentCommand) -> str:
    payload = {
        "agreement_version_id": str(command.agreement_version_id),
        "terms_hash": command.terms_hash,
        "obligation_id": str(command.obligation_id),
        "organization_id": str(command.organization_id),
        "stage": command.stage.value,
        "quantity": quantity_text(command.quantity),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class SqlAlchemyFulfillmentRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_snapshot(self, deal_id: UUID) -> FulfillmentSnapshot:
        deal = self._db.scalar(
            select(Deal).where(Deal.id == deal_id).execution_options(populate_existing=True)
        )
        if deal is None:
            raise FulfillmentUnavailable("Deal not found")
        all_events = list(
            self._db.scalars(
                select(FulfillmentEvent)
                .where(FulfillmentEvent.deal_id == deal_id)
                .order_by(FulfillmentEvent.recorded_at, FulfillmentEvent.version)
            )
        )
        agreement = (
            self._db.get(AgreementVersion, deal.current_agreement_version_id)
            if deal.current_agreement_version_id is not None
            else None
        )
        if (
            agreement is None
            or agreement.deal_id != deal_id
            or agreement.status != "COMMITTED"
            or agreement.committed_at is None
        ):
            return FulfillmentSnapshot(
                deal_id=deal_id,
                state="STALE" if all_events else "PENDING",
                agreement_version_id=None,
                agreement_version_number=None,
                terms_hash=None,
                obligation_id=None,
                planned_quantity=None,
                unit=None,
                destination=None,
                target_date=None,
                shipped_quantity=Decimal("0"),
                observed_quantity=Decimal("0"),
                confirmed_quantity=Decimal("0"),
                fulfillment_version=0,
                payment_complete=False,
                deal_completed=deal.status == DealStatus.COMPLETED.value,
                events=tuple(_record(row) for row in all_events),
            )
        try:
            terms = TradeTerms.from_canonical_json(agreement.canonical_terms_json)
            terms.validate_for_commit()
        except (KeyError, TypeError, ValueError, InvariantViolation) as error:
            raise FulfillmentUnavailable("Committed delivery terms are unavailable") from error
        if terms.terms_hash != agreement.terms_hash:
            raise FulfillmentUnavailable("Committed delivery terms failed integrity verification")
        obligation = self._delivery_obligation(deal_id, agreement.id)
        matching_obligation_ids = set(
            self._db.scalars(
                select(Obligation.id).where(
                    Obligation.deal_id == deal_id,
                    Obligation.source_terms_reference == obligation.source_terms_reference,
                )
            )
        ) if obligation.source_terms_reference else {obligation.id}
        current_events = [
            row for row in all_events
            if row.obligation_id in matching_obligation_ids
        ]
        return FulfillmentSnapshot(
            deal_id=deal_id,
            state="READY" if current_events else "EMPTY",
            agreement_version_id=agreement.id,
            agreement_version_number=agreement.version_number,
            terms_hash=agreement.terms_hash,
            obligation_id=obligation.id,
            planned_quantity=terms.shipments[0].quantity,
            unit=terms.line_items[0].unit,
            destination=terms.shipments[0].destination,
            target_date=(terms.shipments[0].target_date.isoformat() if terms.shipments[0].target_date else None),
            shipped_quantity=_quantity(_scaled_total(current_events, FulfillmentStage.SHIPPED)),
            observed_quantity=_quantity(_scaled_total(current_events, FulfillmentStage.OBSERVED)),
            confirmed_quantity=_quantity(_scaled_total(current_events, FulfillmentStage.CONFIRMED)),
            fulfillment_version=obligation.fulfillment_version,
            payment_complete=payments_reconciled(self._db, deal_id, agreement.id, terms),
            deal_completed=deal.status == DealStatus.COMPLETED.value,
            events=tuple(_record(row) for row in all_events),
        )

    def append_event(
        self,
        *,
        deal: DomainDeal,
        actor: ActorContext,
        command: RecordFulfillmentCommand,
    ) -> FulfillmentEventRecord:
        request_hash = _request_hash(command)
        try:
            prior = self._db.scalar(
                select(FulfillmentEvent).where(
                    FulfillmentEvent.deal_id == deal.id,
                    FulfillmentEvent.actor_user_id == actor.user_id,
                    FulfillmentEvent.idempotency_key == command.idempotency_key,
                )
            )
            if prior is not None:
                if prior.request_hash != request_hash:
                    raise FulfillmentConflict("Idempotency key belongs to a different fulfillment event")
                return _record(prior)

            deal_row = self._db.scalar(
                select(Deal)
                .where(Deal.id == deal.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if deal_row is None or deal_row.status not in (DealStatus.AGREED.value, DealStatus.EXECUTING.value):
                raise FulfillmentUnavailable("Deal is not accepting delivery facts")
            agreement = self._db.get(AgreementVersion, deal_row.current_agreement_version_id)
            if (
                agreement is None
                or agreement.id != command.agreement_version_id
                or agreement.deal_id != deal.id
                or agreement.status != "COMMITTED"
                or agreement.committed_at is None
                or agreement.terms_hash != command.terms_hash
            ):
                raise FulfillmentUnavailable("The committed agreement changed; reload delivery terms")
            try:
                terms = TradeTerms.from_canonical_json(agreement.canonical_terms_json)
                terms.validate_for_commit()
            except (KeyError, TypeError, ValueError, InvariantViolation) as error:
                raise FulfillmentUnavailable("Committed delivery terms are unavailable") from error
            if terms.terms_hash != agreement.terms_hash:
                raise FulfillmentUnavailable("Committed delivery terms failed integrity verification")
            obligation = self._delivery_obligation(deal.id, agreement.id)
            if obligation.id != command.obligation_id:
                raise FulfillmentUnavailable("The delivery obligation changed; reload delivery terms")
            if command.organization_id not in (deal_row.buyer_organization_id, deal_row.seller_organization_id):
                raise FulfillmentUnavailable("Selected organization is not a party to this deal")
            responsible = (
                deal_row.seller_organization_id
                if command.stage is FulfillmentStage.SHIPPED
                else deal_row.buyer_organization_id
            )
            if command.organization_id != responsible:
                raise FulfillmentUnavailable("Selected organization cannot record this delivery fact")
            if command.quantity > terms.shipments[0].quantity:
                raise InvariantViolation("Fulfillment quantity exceeds the agreed shipment quantity")

            matching_obligation_ids = (
                select(Obligation.id).where(
                    Obligation.deal_id == deal.id,
                    Obligation.source_terms_reference == obligation.source_terms_reference,
                )
                if obligation.source_terms_reference
                else [obligation.id]
            )
            existing = list(
                self._db.scalars(
                    select(FulfillmentEvent).where(
                        FulfillmentEvent.deal_id == deal.id,
                        FulfillmentEvent.obligation_id.in_(matching_obligation_ids),
                    )
                )
            )
            totals = {
                stage: _scaled_total(existing, stage)
                for stage in FulfillmentStage
            }
            proposed = totals[command.stage] + _scaled(command.quantity)
            expected = _scaled(terms.shipments[0].quantity)
            if proposed > expected:
                raise InvariantViolation("Cumulative fulfillment quantity exceeds the agreed shipment quantity")
            if command.stage is FulfillmentStage.OBSERVED and proposed > totals[FulfillmentStage.SHIPPED]:
                raise InvariantViolation("Observed quantity cannot exceed the quantity reported as shipped")
            if command.stage is FulfillmentStage.CONFIRMED and proposed > totals[FulfillmentStage.OBSERVED]:
                raise InvariantViolation("Confirmed quantity cannot exceed the quantity observed")
            if command.stage is not FulfillmentStage.SHIPPED and command.quantity > terms.line_items[0].quantity:
                raise InvariantViolation("Delivery quantity exceeds the agreed line-item quantity")

            deal_update = self._db.execute(
                update(Deal)
                .where(
                    Deal.id == deal.id,
                    Deal.version == deal_row.version,
                    Deal.status == deal_row.status,
                    Deal.current_agreement_version_id == agreement.id,
                )
                .values(version=deal_row.version + 1)
                .execution_options(synchronize_session=False)
            )
            if deal_update.rowcount != 1:
                raise FulfillmentConflict("Deal terms changed; refresh before recording delivery facts")
            deal_row.version += 1

            update_result = self._db.execute(
                update(Obligation)
                .where(
                    Obligation.id == obligation.id,
                    Obligation.fulfillment_version == command.expected_version,
                    Obligation.agreement_version_id == agreement.id,
                )
                .values(fulfillment_version=command.expected_version + 1)
                .execution_options(synchronize_session=False)
            )
            if update_result.rowcount != 1:
                raise FulfillmentConflict("Delivery history changed; refresh before recording another fact")
            row = FulfillmentEvent(
                id=uuid4(),
                deal_id=deal.id,
                agreement_version_id=agreement.id,
                terms_hash=agreement.terms_hash,
                obligation_id=obligation.id,
                actor_organization_id=command.organization_id,
                actor_user_id=actor.user_id,
                event_type=command.stage.value,
                quantity=quantity_text(command.quantity),
                unit=terms.line_items[0].unit,
                source_type="USER_ATTESTATION",
                idempotency_key=command.idempotency_key,
                request_hash=request_hash,
                version=command.expected_version + 1,
                recorded_at=datetime.now(UTC),
            )
            self._db.add(row)
            self._db.flush()
            self._db.add(
                AuditEvent(
                    aggregate_type="deal",
                    aggregate_id=deal.id,
                    event_type=f"FULFILLMENT_{command.stage.value}",
                    actor_type="USER",
                    actor_id=str(actor.user_id),
                    occurred_at=row.recorded_at,
                    payload={
                        "event_id": str(row.id),
                        "agreement_version_id": str(agreement.id),
                        "terms_hash": agreement.terms_hash,
                        "obligation_id": str(obligation.id),
                        "quantity": row.quantity,
                        "unit": row.unit,
                        "source_type": row.source_type,
                    },
                )
            )
            queue_deal_workflow_notification(
                self._db,
                deal_id=deal.id,
                record_id=row.id,
                kind=NotificationKind.FULFILLMENT_EVENT_RECORDED,
            )
            maybe_complete_deal(self._db, deal.id, row.id)
            self._db.commit()
            return _record(row)
        except IntegrityError as error:
            self._db.rollback()
            prior = self._db.scalar(
                select(FulfillmentEvent).where(
                    FulfillmentEvent.deal_id == deal.id,
                    FulfillmentEvent.actor_user_id == actor.user_id,
                    FulfillmentEvent.idempotency_key == command.idempotency_key,
                )
            )
            if prior is not None and prior.request_hash == request_hash:
                return _record(prior)
            raise FulfillmentConflict("Delivery history changed concurrently; refresh and retry") from error
        except Exception:
            self._db.rollback()
            raise

    def _delivery_obligation(self, deal_id: UUID, agreement_version_id: UUID) -> Obligation:
        agreement = self._db.get(AgreementVersion, agreement_version_id)
        ref = "shipments[0]"
        if agreement is not None:
            try:
                terms = TradeTerms.from_canonical_json(agreement.canonical_terms_json)
                if terms.shipments:
                    s0 = terms.shipments[0]
                    ref = s0.id if (terms.schema_version == 2 and s0.id) else "shipments[0]"
            except Exception:
                pass
        obligation = self._db.scalar(
            select(Obligation).where(
                Obligation.deal_id == deal_id,
                Obligation.agreement_version_id == agreement_version_id,
                Obligation.obligation_type == "DELIVERY",
                Obligation.source_terms_reference == ref,
            )
        )
        if obligation is None:
            obligation = self._db.scalar(
                select(Obligation).where(
                    Obligation.deal_id == deal_id,
                    Obligation.agreement_version_id == agreement_version_id,
                    Obligation.obligation_type == "DELIVERY",
                )
            )
        if obligation is None:
            raise FulfillmentUnavailable("The committed delivery obligation is unavailable")
        return obligation
