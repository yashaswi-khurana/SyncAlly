"""Domain models, errors, and impact assessments for agreement amendments."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from syncally.application.agreements import compare_agreement_terms
from syncally.domain.agreements.fulfillment import bounded_quantity
from syncally.domain.agreements.trade_terms import TradeTerms
from syncally.domain.shared.errors import DomainError


class AmendmentError(DomainError):
    """Base class for amendment domain errors."""


class AmendmentConflict(AmendmentError):
    """An amendment draft is already pending or deal state conflicts."""


class AmendmentImpactBlocked(AmendmentError):
    """The amendment cannot be committed due to policy blockers on fulfillment or payments."""


class StalePriorVersion(AmendmentError):
    """The prior version number does not match the currently committed agreement version."""


class WrongPriorHash(AmendmentError):
    """The prior terms hash does not match the currently committed agreement terms hash."""


class AmendmentAlreadyCommitted(AmendmentError):
    """The amendment version was already committed."""


@dataclass(frozen=True, slots=True)
class FulfillmentObligationImpact:
    obligation_reference: str
    item_id: str | None
    planned_quantity: str
    unit: str
    shipped_quantity: str
    confirmed_quantity: str
    preserved: bool
    status: str
    details: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "obligation_reference": self.obligation_reference,
            "item_id": self.item_id,
            "planned_quantity": self.planned_quantity,
            "unit": self.unit,
            "shipped_quantity": self.shipped_quantity,
            "confirmed_quantity": self.confirmed_quantity,
            "preserved": self.preserved,
            "status": self.status,
            "details": self.details,
        }


@dataclass(frozen=True, slots=True)
class PaymentMilestoneImpact:
    milestone_reference: str
    amount: str
    currency: str
    payment_status: str
    has_active_intent: bool
    preserved: bool
    status: str
    details: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "milestone_reference": self.milestone_reference,
            "amount": self.amount,
            "currency": self.currency,
            "payment_status": self.payment_status,
            "has_active_intent": self.has_active_intent,
            "preserved": self.preserved,
            "status": self.status,
            "details": self.details,
        }


@dataclass(frozen=True, slots=True)
class AmendmentImpact:
    prior_version_number: int
    prior_terms_hash: str
    proposed_version_number: int
    proposed_terms_hash: str
    diff: dict[str, Any]
    fulfillment_impact: list[dict[str, Any]]
    payment_impact: list[dict[str, Any]]
    active_cases: list[dict[str, Any]]
    blockers: list[str]
    can_commit: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "prior_version_number": self.prior_version_number,
            "prior_terms_hash": self.prior_terms_hash,
            "proposed_version_number": self.proposed_version_number,
            "proposed_terms_hash": self.proposed_terms_hash,
            "diff": self.diff,
            "fulfillment_impact": self.fulfillment_impact,
            "payment_impact": self.payment_impact,
            "active_cases": self.active_cases,
            "blockers": self.blockers,
            "can_commit": self.can_commit,
        }


def assess_amendment_impact(
    *,
    prior_version_number: int,
    prior_terms: TradeTerms,
    proposed_version_number: int,
    proposed_terms: TradeTerms,
    prior_fulfillment_summary: list[dict[str, Any]] | None = None,
    prior_payment_summary: list[dict[str, Any]] | None = None,
    active_cases: list[dict[str, Any]] | None = None,
) -> AmendmentImpact:
    """Assess impacts of proposed trade terms against prior committed terms and operational facts.

    Enforces commercial boundaries:
    - Paid milestones cannot be reduced, altered, or deleted without explicit approved settlement.
    - In-flight milestones cannot be amended while processing.
    - Fulfilled delivery quantities (shipped / confirmed) cannot be reduced below delivered quantities.
    - Active disputes or cancellations flag policy blockers.
    """
    diff = compare_agreement_terms(prior_terms.to_storage_dict(), proposed_terms.to_storage_dict())
    fulfillment_impact: list[dict[str, Any]] = []
    payment_impact: list[dict[str, Any]] = []
    blockers: list[str] = []

    # Map proposed shipments by reference / ID
    proposed_shipments_by_ref: dict[str, Any] = {}
    for idx, s in enumerate(proposed_terms.shipments):
        ref = s.id if (proposed_terms.schema_version == 2 and s.id) else f"shipments[{idx}]"
        proposed_shipments_by_ref[ref] = s

    # 1. Fulfillment assessment
    for f in (prior_fulfillment_summary or []):
        ref = f.get("obligation_reference", "")
        shipped = Decimal(str(f.get("shipped_quantity", "0")))
        confirmed = Decimal(str(f.get("confirmed_quantity", "0")))
        unit = f.get("unit", "")
        item_id = f.get("item_id")

        if ref in proposed_shipments_by_ref:
            new_shipment = proposed_shipments_by_ref[ref]
            new_qty = bounded_quantity(new_shipment.quantity)
            max_fulfilled = max(shipped, confirmed)
            if max_fulfilled > 0 and new_qty < max_fulfilled:
                msg = (
                    f"Shipment {ref} quantity reduced to {new_qty} {unit}, but {max_fulfilled} {unit} "
                    f"has already been fulfilled (shipped: {shipped}, confirmed: {confirmed}). "
                    f"Retroactive delivery reduction without approved settlement is blocked."
                )
                blockers.append(msg)
                impact_item = FulfillmentObligationImpact(
                    obligation_reference=ref,
                    item_id=item_id,
                    planned_quantity=str(new_qty),
                    unit=unit,
                    shipped_quantity=str(shipped),
                    confirmed_quantity=str(confirmed),
                    preserved=False,
                    status="REDUCED_BELOW_FULFILLED",
                    details=msg,
                )
            else:
                impact_item = FulfillmentObligationImpact(
                    obligation_reference=ref,
                    item_id=item_id,
                    planned_quantity=str(new_qty),
                    unit=unit,
                    shipped_quantity=str(shipped),
                    confirmed_quantity=str(confirmed),
                    preserved=True,
                    status="PRESERVED",
                    details=None,
                )
        else:
            # Shipment was removed in proposed terms
            max_fulfilled = max(shipped, confirmed)
            if max_fulfilled > 0:
                msg = (
                    f"Shipment {ref} was removed in proposed terms, but {max_fulfilled} {unit} "
                    f"has already been fulfilled. Removing fulfilled obligations is blocked."
                )
                blockers.append(msg)
                impact_item = FulfillmentObligationImpact(
                    obligation_reference=ref,
                    item_id=item_id,
                    planned_quantity="0",
                    unit=unit,
                    shipped_quantity=str(shipped),
                    confirmed_quantity=str(confirmed),
                    preserved=False,
                    status="REMOVED_WHILE_FULFILLED",
                    details=msg,
                )
            else:
                impact_item = FulfillmentObligationImpact(
                    obligation_reference=ref,
                    item_id=item_id,
                    planned_quantity="0",
                    unit=unit,
                    shipped_quantity="0",
                    confirmed_quantity="0",
                    preserved=True,
                    status="REMOVED_UNFULFILLED",
                    details="Unfulfilled shipment removed in amendment",
                )
        fulfillment_impact.append(impact_item.to_dict())

    # Map proposed payment terms by reference / ID
    proposed_payment_terms_by_ref: dict[str, Any] = {}
    for idx, p in enumerate(proposed_terms.payment_terms):
        ref = p.id if (proposed_terms.schema_version == 2 and p.id) else f"payment_terms[{idx}]"
        proposed_payment_terms_by_ref[ref] = p

    # 2. Payment assessment
    for p in (prior_payment_summary or []):
        ref = p.get("milestone_reference", "")
        amount = Decimal(str(p.get("amount", "0")))
        currency = p.get("currency", "")
        pay_status = p.get("payment_status", "PENDING")
        has_active = bool(p.get("has_active_intent", False))

        if has_active:
            msg = (
                f"Payment milestone {ref} has an active in-flight payment intent. "
                f"Amending terms during payment execution is blocked until intent finishes or is cancelled."
            )
            blockers.append(msg)
            payment_impact.append(
                PaymentMilestoneImpact(
                    milestone_reference=ref,
                    amount=str(amount),
                    currency=currency,
                    payment_status=pay_status,
                    has_active_intent=True,
                    preserved=False,
                    status="IN_FLIGHT_CONFLICT",
                    details=msg,
                ).to_dict()
            )
            continue

        if pay_status == "PAID":
            if ref in proposed_payment_terms_by_ref:
                new_term = proposed_payment_terms_by_ref[ref]
                new_amount = new_term.amount.amount
                new_currency = new_term.amount.currency
                if new_currency != currency or new_amount < amount:
                    msg = (
                        f"Paid milestone {ref} ({amount} {currency}) altered or reduced to "
                        f"{new_amount} {new_currency} in proposed terms. "
                        f"Unilateral reduction of paid milestones without approved refund policy is blocked."
                    )
                    blockers.append(msg)
                    payment_impact.append(
                        PaymentMilestoneImpact(
                            milestone_reference=ref,
                            amount=str(new_amount),
                            currency=new_currency,
                            payment_status="PAID",
                            has_active_intent=False,
                            preserved=False,
                            status="PAID_ALTERED",
                            details=msg,
                        ).to_dict()
                    )
                else:
                    payment_impact.append(
                        PaymentMilestoneImpact(
                            milestone_reference=ref,
                            amount=str(new_amount),
                            currency=new_currency,
                            payment_status="PAID",
                            has_active_intent=False,
                            preserved=True,
                            status="PAID_PRESERVED",
                            details="Paid milestone preserved in new terms",
                        ).to_dict()
                    )
            else:
                msg = (
                    f"Paid milestone {ref} ({amount} {currency}) was deleted in proposed terms. "
                    f"Deleting paid obligations without approved refund or settlement policy is blocked."
                )
                blockers.append(msg)
                payment_impact.append(
                    PaymentMilestoneImpact(
                        milestone_reference=ref,
                        amount=str(amount),
                        currency=currency,
                        payment_status="PAID",
                        has_active_intent=False,
                        preserved=False,
                        status="PAID_DELETED",
                        details=msg,
                    ).to_dict()
                )
        else:
            # Unpaid milestone
            if ref in proposed_payment_terms_by_ref:
                new_term = proposed_payment_terms_by_ref[ref]
                payment_impact.append(
                    PaymentMilestoneImpact(
                        milestone_reference=ref,
                        amount=str(new_term.amount.amount),
                        currency=new_term.amount.currency,
                        payment_status=pay_status,
                        has_active_intent=False,
                        preserved=True,
                        status="UNPAID_MODIFIED" if (new_term.amount.amount != amount or new_term.amount.currency != currency) else "UNPAID_PRESERVED",
                        details="Unpaid milestone adjusted in proposed terms",
                    ).to_dict()
                )
            else:
                payment_impact.append(
                    PaymentMilestoneImpact(
                        milestone_reference=ref,
                        amount=str(amount),
                        currency=currency,
                        payment_status=pay_status,
                        has_active_intent=False,
                        preserved=True,
                        status="UNPAID_REMOVED",
                        details="Unpaid milestone removed in proposed terms",
                    ).to_dict()
                )

    cases = active_cases or []
    for case in cases:
        case_id = case.get("id") or case.get("case_id")
        blockers.append(f"Deal has an active case {case_id}; resolution required before amending terms.")

    can_commit = len(blockers) == 0

    return AmendmentImpact(
        prior_version_number=prior_version_number,
        prior_terms_hash=prior_terms.terms_hash,
        proposed_version_number=proposed_version_number,
        proposed_terms_hash=proposed_terms.terms_hash,
        diff=diff,
        fulfillment_impact=fulfillment_impact,
        payment_impact=payment_impact,
        active_cases=cases,
        blockers=blockers,
        can_commit=can_commit,
    )
