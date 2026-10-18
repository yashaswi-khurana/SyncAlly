"""Obligations and payment milestones derived from a committed agreement's trade terms."""

from dataclasses import dataclass
from datetime import UTC, datetime

from syncally.domain.agreements.trade_terms import TradeTerms
from syncally.domain.shared.identifiers import OrganizationId
from syncally.domain.shared.money import Money


@dataclass(frozen=True, slots=True)
class ObligationDraft:
    obligation_type: str
    owner_organization_id: OrganizationId
    counterparty_organization_id: OrganizationId
    due_condition: str | None
    due_date: datetime | None
    source_terms_reference: str


@dataclass(frozen=True, slots=True)
class PaymentMilestoneDraft:
    sequence_number: int
    payer_organization_id: OrganizationId
    amount: Money
    trigger_type: str
    due_condition: str
    source_terms_reference: str


def build_obligations(terms: TradeTerms) -> list[ObligationDraft]:
    """One DELIVERY obligation per shipment, one PAYMENT obligation per payment term.

    ``validate_for_commit`` guarantees exactly one of each for the demo, but
    this stays generic rather than special-cased to that count.
    """
    obligations = [
        ObligationDraft(
            obligation_type="DELIVERY",
            owner_organization_id=terms.seller_id,
            counterparty_organization_id=terms.buyer_id,
            due_condition=None,
            due_date=(
                datetime.combine(shipment.target_date, datetime.min.time(), tzinfo=UTC)
                if shipment.target_date
                else None
            ),
            source_terms_reference=f"shipments[{index}]",
        )
        for index, shipment in enumerate(terms.shipments)
    ]
    obligations.extend(
        ObligationDraft(
            obligation_type="PAYMENT",
            owner_organization_id=terms.buyer_id,
            counterparty_organization_id=terms.seller_id,
            due_condition=term.due_condition,
            due_date=None,
            source_terms_reference=f"payment_terms[{index}]",
        )
        for index, term in enumerate(terms.payment_terms)
    )
    return obligations


def build_payment_milestones(terms: TradeTerms) -> list[PaymentMilestoneDraft]:
    """One payment milestone per payment term, so payment intents have an amount to authorize."""
    return [
        PaymentMilestoneDraft(
            sequence_number=index + 1,
            payer_organization_id=terms.buyer_id,
            amount=term.amount,
            trigger_type=term.trigger,
            due_condition=term.due_condition,
            source_terms_reference=f"payment_terms[{index}]",
        )
        for index, term in enumerate(terms.payment_terms)
    ]
