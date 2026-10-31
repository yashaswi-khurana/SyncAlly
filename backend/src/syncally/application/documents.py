"""Generate review-only commercial document drafts from committed terms."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from html import escape
from io import BytesIO
from typing import Any, Literal
from uuid import UUID
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from syncally.application.agreements import AgreementRepository, get_current_agreement
from syncally.application.deals import DealRepository
from syncally.application.identity import ActorContext
from syncally.domain.agreements.agreement import Agreement, AgreementStatus
from syncally.domain.agreements.trade_terms import TradeTerms
from syncally.domain.shared.errors import DomainError
from syncally.domain.shared.money import Money, canonical_decimal


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


MAX_DISPLAY_JSON_BYTES = 2 * 1024 * 1024
MAX_TRADE_PACK_BYTES = 16 * 1024 * 1024
TRADE_PACK_SCHEMA_VERSION = 1


class TradePackTooLarge(DomainError):
    """The export exceeds its uncompressed resource budget."""


class InvalidTradePack(DomainError):
    """The stored commitment cannot be exported safely."""


@dataclass(frozen=True, slots=True)
class TradePack:
    content: bytes
    media_type: str
    filename: str


def _json_bytes(value: Any, limit: int) -> bytes:
    output = bytearray()
    for chunk in json.JSONEncoder(sort_keys=True, separators=(",", ":"),
                                  ensure_ascii=False, allow_nan=False).iterencode(value):
        if len(chunk) > limit - len(output):
            raise TradePackTooLarge("Trade pack size limit exceeded")
        encoded = chunk.encode("utf-8")
        if len(encoded) > limit - len(output):
            raise TradePackTooLarge("Trade pack size limit exceeded")
        output.extend(encoded)
    return bytes(output)


def _shape(value: Any, fields: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != fields:
        raise InvalidTradePack("Unknown or missing commitment fields")


def export_display_terms(stored: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(stored, dict):
        raise InvalidTradePack("Invalid stored terms")
    public = {key: value for key, value in stored.items() if key != "_f6_evidence"}
    _shape(public, {"schema_version", "buyer_id", "seller_id", "line_items", "shipments",
                    "payment_terms", "delivery_location", "incoterm", "cancellation_terms"})
    if type(public["schema_version"]) is not int or public["schema_version"] != 1:
        raise InvalidTradePack("Unsupported commitment schema")
    decimal_values = []
    for collection, fields in (
        ("line_items", {"description", "sku", "quantity", "unit", "unit_price"}),
        ("shipments", {"quantity", "destination", "target_date"}),
        ("payment_terms", {"amount", "trigger", "due_condition"}),
    ):
        if not isinstance(public[collection], list) or not public[collection]:
            raise InvalidTradePack("Missing commitment entries")
        for entry in public[collection]:
            _shape(entry, fields)
            for key in fields - {"quantity", "unit_price", "amount"}:
                value = entry[key]
                if not isinstance(value, str) and not (key in {"sku", "target_date"} and value is None):
                    raise InvalidTradePack("Invalid commitment text")
            if "quantity" in entry:
                if not isinstance(entry["quantity"], str):
                    raise InvalidTradePack("Decimal values must be strings")
                decimal_values.append(entry["quantity"])
            for key in ("unit_price", "amount"):
                if key in entry:
                    _shape(entry[key], {"amount", "currency"})
                    if not isinstance(entry[key]["currency"], str):
                        raise InvalidTradePack("Invalid commitment currency")
                    if not isinstance(entry[key]["amount"], str):
                        raise InvalidTradePack("Decimal values must be strings")
                    decimal_values.append(entry[key]["amount"])
    for key in ("buyer_id", "seller_id", "delivery_location", "cancellation_terms", "incoterm"):
        if not isinstance(public[key], str) and not (key == "incoterm" and public[key] is None):
            raise InvalidTradePack("Invalid commitment text")
    display_bytes = _json_bytes(public, MAX_DISPLAY_JSON_BYTES)
    expanded_size = len(display_bytes)
    try:
        for value in decimal_values:
            if not isinstance(value, str):
                raise InvalidTradePack("Decimal values must be strings")
            number = Decimal(value)
            if not number.is_finite():
                raise InvalidTradePack("Invalid decimal")
            parts = number.as_tuple()
            if len(parts.digits) + abs(parts.exponent) > MAX_DISPLAY_JSON_BYTES:
                raise TradePackTooLarge("Decimal expansion exceeds export limit")
            expanded_size += max(0, len(parts.digits) + abs(parts.exponent) + 3 - len(value))
            if expanded_size > MAX_DISPLAY_JSON_BYTES:
                raise TradePackTooLarge("Cumulative decimal expansion exceeds 2 MiB")
    except InvalidOperation as error:
        raise InvalidTradePack("Invalid decimal") from error
    return deepcopy(public)


def generate_trade_pack(
    projection: dict[str, Any], *, deal_id: UUID, number: int,
    agreement_version_id: UUID, terms_hash: str, format: Literal["html", "zip"],
) -> TradePack:
    try:
        if (projection["id"] != str(agreement_version_id)
                or projection["deal_id"] != str(deal_id)
                or projection["version_number"] != number
                or projection["terms_hash"] != terms_hash
                or projection["status"] != "COMMITTED"
                or not isinstance(projection["committed_at"], datetime)
                or not isinstance(projection["created_at"], datetime)):
            raise InvalidTradePack("A matching committed version is required")
        display = export_display_terms(projection["terms"])
        terms = TradeTerms.from_canonical_json(display)
        canonical_text = terms.canonical_json()
        if len(canonical_text) > MAX_DISPLAY_JSON_BYTES:
            raise TradePackTooLarge("Expanded canonical terms exceed 2 MiB")
        canonical = canonical_text.encode("utf-8")
        if len(canonical) > MAX_DISPLAY_JSON_BYTES:
            raise TradePackTooLarge("Expanded canonical terms exceed 2 MiB")
        if hashlib.sha256(canonical).hexdigest() != terms_hash:
            raise InvalidTradePack("Stored commitment hash does not match")
        parties = {display["buyer_id"], display["seller_id"]}
        approvals = projection["approvals"]
        if len(approvals) != 2 or {approval["organization_id"] for approval in approvals} != parties:
            raise InvalidTradePack("Bilateral approval is required")
        for approval in approvals:
            if (approval["decision"] != "APPROVE" or approval["terms_hash"] != terms_hash
                    or approval["agreement_version_id"] != str(agreement_version_id)
                    or approval["deal_id"] != str(deal_id)
                    or approval["version_number"] != number):
                raise InvalidTradePack("Approval does not match the commitment")
        manifest = {
            "schema_version": TRADE_PACK_SCHEMA_VERSION,
            "trade_terms_schema_version": display["schema_version"],
            "deal_id": str(deal_id), "agreement_version_id": str(agreement_version_id),
            "agreement_version_number": number, "terms_hash": terms_hash,
            "created_at": projection["created_at"].isoformat(),
            "committed_at": projection["committed_at"].isoformat(),
            "buyer_organization_id": display["buyer_id"],
            "seller_organization_id": display["seller_id"],
            "counts": {key: len(display[key]) for key in ("line_items", "shipments", "payment_terms")},
            "display_terms": display,
            "status": "DRAFT - FOR REVIEW ONLY",
        }
        manifest_bytes = _json_bytes(manifest, MAX_TRADE_PACK_BYTES)
        html = _trade_pack_html(manifest, terms,
            MAX_TRADE_PACK_BYTES - len(canonical) - len(manifest_bytes)).encode("utf-8")
        if len(html) + len(canonical) + len(manifest_bytes) > MAX_TRADE_PACK_BYTES:
            raise TradePackTooLarge("Uncompressed trade pack exceeds 16 MiB")
        filename = f"syncally-deal-{deal_id}-agreement-v{number}-trade-pack.{format}"
        if format == "html":
            return TradePack(html, "text/html; charset=utf-8", filename)
        if format != "zip":
            raise InvalidTradePack("Unsupported export format")
        buffer = BytesIO()
        with ZipFile(buffer, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
            for name, content in (("trade-pack.html", html), ("canonical-terms.json", canonical),
                                  ("manifest.json", manifest_bytes)):
                info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = ZIP_DEFLATED
                archive.writestr(info, content, compresslevel=9)
        return TradePack(buffer.getvalue(), "application/zip", filename)
    except (InvalidTradePack, TradePackTooLarge):
        raise
    except (DomainError, KeyError, TypeError, ValueError, ArithmeticError) as error:
        raise InvalidTradePack("Stored commitment is invalid") from error


def _trade_pack_html(manifest: dict[str, Any], terms: TradeTerms, budget: int) -> str:
    missing = "Not recorded in committed terms"
    sections = []
    used = 0

    def section(title: str, rows: list[tuple[str, Any]]) -> None:
        nonlocal used
        content = "".join(f"<dt>{escape(label, quote=True)}</dt><dd>"
                          f"{escape(str(value) if value not in (None, '') else missing, quote=True)}</dd>"
                          for label, value in rows)
        rendered = (f"<section><h2>{escape(title, quote=True)}</h2>"
                    f"<p class='review'>DRAFT - FOR REVIEW ONLY</p><dl>{content}</dl></section>")
        used += len(rendered.encode("utf-8"))
        if used > budget:
            raise TradePackTooLarge("Uncompressed trade pack exceeds 16 MiB")
        sections.append(rendered)

    section("Source", [(key.replace("_", " ").title(), manifest[key]) for key in (
        "deal_id", "agreement_version_id", "agreement_version_number", "terms_hash", "created_at", "committed_at")])
    display = manifest["display_terms"]
    section("Parties", [("Buyer organization ID (not a legal name)", display["buyer_id"]),
                        ("Seller organization ID (not a legal name)", display["seller_id"]),
                        ("Buyer legal name", None), ("Seller legal name", None),
                        ("Buyer address", None), ("Seller address", None)])
    for index, item in enumerate(display["line_items"], 1):
        price = item["unit_price"]
        total = Decimal(price["amount"])
        line_total = Money(total, price["currency"]).multiply(Decimal(item["quantity"]))
        section(f"Item {index}", [("Description", item["description"]), ("SKU", item["sku"]),
            ("Quantity", item["quantity"]), ("Unit", item["unit"]),
            ("Unit price", f"{price['amount']} {price['currency']}"),
            ("Line total", f"{canonical_decimal(line_total.amount)} {line_total.currency}"),
            ("Weight", None), ("Packaging", None)])
    for index, shipment in enumerate(display["shipments"], 1):
        section(f"Shipment {index}", [("Quantity", shipment["quantity"]),
            ("Destination", shipment["destination"]), ("Target delivery date", shipment["target_date"]),
            ("Item allocation / quantity unit", None), ("Shipping address", None)])
    for index, payment in enumerate(display["payment_terms"], 1):
        section(f"Payment term {index}", [("Amount", f"{payment['amount']['amount']} {payment['amount']['currency']}"),
            ("Trigger", payment["trigger"]), ("Due condition", payment["due_condition"]),
            ("Banking details", None)])
    section("Trade conditions", [("Delivery location", display["delivery_location"]),
        ("Incoterm", display["incoterm"]), ("Cancellation terms", display["cancellation_terms"]),
        ("Trade total", f"{canonical_decimal(terms.total.amount)} {terms.currency}"),
        ("Tax", None), ("Freight and other fees", None), ("Customs classification", None)])
    section("Review limitations", [("Document scope", "Not an invoice, signed proof, or payment proof. "
        "Does not certify legal, tax, or customs compliance. No missing values or allocations were inferred.")])
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; "
        "style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">"
        "<title>SyncAlly trade pack - DRAFT FOR REVIEW</title><style>"
        "body{font-family:Georgia,serif;color:#222;max-width:960px;margin:24px auto;padding:16px}"
        "section{border-top:1px solid #888;margin-top:24px;break-inside:avoid}"
        "dl{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,3fr);gap:8px}"
        "dt{font-weight:bold}dd{margin:0;white-space:pre-wrap;overflow-wrap:anywhere}"
        ".review{font-weight:bold;color:#8b1818}h1,h2{overflow-wrap:anywhere}"
        "@media print{body{margin:0;max-width:none;padding:0}@page{margin:18mm}}"
        "@media(max-width:480px){dl{grid-template-columns:minmax(0,1fr)}}"
        "</style></head><body><h1>SyncAlly Commercial Trade Pack</h1>"
        "<p class='review'>DRAFT - FOR REVIEW ONLY</p>" + "".join(sections) + "</body></html>")
