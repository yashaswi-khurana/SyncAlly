"""Generate review-only commercial document drafts from committed terms."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from syncally.application.agreements import AgreementRepository, get_current_agreement
from syncally.application.deals import DealRepository
from syncally.application.identity import ActorContext
from syncally.domain.agreements.agreement import Agreement, AgreementStatus
from syncally.domain.shared.errors import DomainError
from syncally.domain.shared.money import canonical_decimal


class AgreementNotCommitted(DomainError):
    """A document draft can only be generated from a committed version."""


@dataclass(frozen=True, slots=True)
class CommercialDocumentDraft:
    """Rendered text and immutable source identity for a generated draft."""

    agreement_version_id: UUID
    agreement_version_number: int
    terms_hash: str
    content: str


def generate_commercial_document_draft(
    actor: ActorContext,
    deal_id: UUID,
    deal_repository: DealRepository,
    agreement_repository: AgreementRepository,
) -> CommercialDocumentDraft:
    """Render a review-only draft without persisting or mutating its source terms."""
    agreement = get_current_agreement(actor, deal_id, deal_repository, agreement_repository)
    if agreement.status is not AgreementStatus.COMMITTED:
        raise AgreementNotCommitted("Only a committed agreement can generate a document draft")

    return CommercialDocumentDraft(
        agreement_version_id=agreement.version_id,
        agreement_version_number=agreement.version_number,
        terms_hash=agreement.terms_hash,
        content=_render(agreement),
    )


def _render(agreement: Agreement) -> str:
    terms = agreement.terms
    item = terms.line_items[0]
    shipment = terms.shipments[0]
    payment = terms.payment_terms[0]
    missing = "Not specified in committed terms"

    lines = [
        "SYNCALLY - COMMERCIAL TRADE SUMMARY",
        "DRAFT - FOR REVIEW ONLY",
        "This is not an invoice or signed agreement. It does not certify legal, tax, or customs compliance.",
        "",
        "Source",
        f"Deal ID: {agreement.deal_id}",
        f"Agreement version: {agreement.version_number} ({agreement.version_id})",
        f"Terms hash: {agreement.terms_hash}",
        f"Committed at: {_display(agreement.committed_at.isoformat() if agreement.committed_at else None, missing)}",
        "",
        "Parties",
        f"Buyer legal/business name: {missing}",
        f"Buyer organization ID: {terms.buyer_id}",
        f"Seller legal/business name: {missing}",
        f"Seller organization ID: {terms.seller_id}",
        "",
        "Trade terms",
        f"Item: {_display(item.description, missing)}",
        f"SKU: {_display(item.sku, missing)}",
        f"Quantity: {canonical_decimal(item.quantity)} {_display(item.unit, missing)}",
        f"Unit price: {canonical_decimal(item.unit_price.amount)} {item.unit_price.currency}",
        f"Line total: {canonical_decimal(item.total.amount)} {item.total.currency}",
        f"Delivery destination: {_display(shipment.destination, missing)}",
        f"Target delivery date: {_display(shipment.target_date.isoformat() if shipment.target_date else None, missing)}",
        f"Incoterm: {_display(terms.incoterm, missing)}",
        f"Payment amount: {canonical_decimal(payment.amount.amount)} {payment.amount.currency}",
        f"Payment trigger: {_display(payment.trigger, missing)}",
        f"Payment due condition: {_display(payment.due_condition, missing)}",
        f"Cancellation terms: {_display(terms.cancellation_terms, missing)}",
        f"Taxes, freight, customs classification, and other fees: {missing}",
        "",
        "This draft contains only values recorded in the committed agreement; no missing terms were inferred.",
    ]
    return "\n".join(lines)


def _display(value: str | None, missing: str) -> str:
    if value is None or not value.strip():
        return missing
    return " ".join(value.split())
