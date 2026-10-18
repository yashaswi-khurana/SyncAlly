"""Strict versioned contracts for untrusted AI suggestions.

These types intentionally contain no approval, commitment, ownership, visibility,
or payment-operation fields. Authorization and lifecycle actions stay in normal
application/domain commands.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any
from uuid import UUID

from syncally.domain.agreements.trade_terms import (
    PaymentTerm,
    ShipmentTerm,
    TradeLineItem,
    TradeTerms,
)
from syncally.domain.conversations import ConstraintStatus
from syncally.domain.shared.errors import InvariantViolation
from syncally.domain.shared.identifiers import MessageId, OrganizationId
from syncally.domain.shared.money import Money

AI_SCHEMA_VERSION = 1


class AIContractError(ValueError):
    """An untrusted AI payload does not satisfy the supported contract."""


class FactField(StrEnum):
    ITEM_DESCRIPTION = "item_description"
    ITEM_SPECIFICATION = "item_specification"
    QUANTITY = "quantity"
    UNIT = "unit"
    UNIT_PRICE = "unit_price"
    DELIVERY_DESTINATION = "delivery_destination"
    DELIVERY_DATE = "delivery_date"
    PAYMENT_OBLIGATION = "payment_obligation"


class ValidationStatus(StrEnum):
    VALID = "VALID"
    INVALID = "INVALID"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


@dataclass(frozen=True, slots=True)
class SourceReference:
    """Evidence from one authorized message, or an explicit unknown source."""

    schema_version: int
    message_id: MessageId | None
    quote: str | None
    unknown_reason: str | None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> SourceReference:
        _check_keys(payload, {"schema_version", "message_id", "quote", "unknown_reason"})
        version = _version(payload)
        message_raw = payload.get("message_id")
        quote = payload.get("quote")
        reason = payload.get("unknown_reason")
        if message_raw is not None:
            try:
                message_id = MessageId(UUID(_required_string(message_raw, "message_id")))
            except (ValueError, TypeError, AttributeError) as exc:
                raise AIContractError("source message_id must be a UUID") from exc
            if not isinstance(quote, str) or not quote.strip():
                raise AIContractError("grounded source requires a non-empty quote")
            if reason is not None:
                raise AIContractError("source cannot be both grounded and unknown")
            return cls(version, message_id, quote.strip(), None)
        if quote is not None:
            raise AIContractError("source quote requires a message_id")
        if not isinstance(reason, str) or not reason.strip():
            raise AIContractError("source requires a message reference or unknown_reason")
        return cls(version, None, None, reason.strip())


@dataclass(frozen=True, slots=True)
class ExtractedFact:
    """An untrusted typed fact suggestion; it is not a persisted Constraint."""

    schema_version: int
    field: FactField
    value: str
    source: SourceReference
    currency_or_unit: str | None = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ExtractedFact:
        _check_keys(payload, {"schema_version", "field", "value", "source", "currency_or_unit"})
        version = _version(payload)
        try:
            fact_field = FactField(_required_string(payload.get("field"), "field"))
        except ValueError as exc:
            raise AIContractError("unsupported extracted fact field") from exc
        value = _required_string(payload.get("value"), "value").strip()
        currency_or_unit = payload.get("currency_or_unit")
        _validate_fact_value(fact_field, value, currency_or_unit)
        source_raw = payload.get("source")
        if not isinstance(source_raw, Mapping):
            raise AIContractError("source must be an object")
        return cls(
            version,
            fact_field,
            value,
            SourceReference.from_mapping(source_raw),
            currency_or_unit,
        )


@dataclass(frozen=True, slots=True)
class ScopedFactCandidate:
    """A grounded, still-unreviewed candidate bound to trusted owner scope."""

    fact: ExtractedFact
    source_message_id: MessageId
    owner_organization_id: OrganizationId

    @property
    def review_status(self) -> ConstraintStatus:
        """AI extraction always starts pending; only the human review flow advances it."""
        return ConstraintStatus.EXTRACTED


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """Machine-readable validation error suitable for a user review response."""

    schema_version: int
    code: str
    path: str
    message: str

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != AI_SCHEMA_VERSION:
            raise AIContractError("unsupported validation issue schema_version")
        for name, value in (("code", self.code), ("path", self.path), ("message", self.message)):
            if not isinstance(value, str) or not value.strip():
                raise AIContractError(f"validation issue {name} is required")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ValidationIssue:
        _check_keys(payload, {"schema_version", "code", "path", "message"})
        return cls(
            _version(payload),
            _required_string(payload.get("code"), "code"),
            _required_string(payload.get("path"), "path"),
            _required_string(payload.get("message"), "message"),
        )


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Normal-code validation outcome. AI claims are not authoritative results."""

    schema_version: int
    status: ValidationStatus
    issues: tuple[ValidationIssue, ...]

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != AI_SCHEMA_VERSION:
            raise AIContractError("unsupported validation result schema_version")
        if not isinstance(self.status, ValidationStatus):
            raise AIContractError("validation result requires a supported status")
        object.__setattr__(self, "issues", tuple(self.issues))
        if any(not isinstance(issue, ValidationIssue) for issue in self.issues):
            raise AIContractError("validation result issues must be ValidationIssue values")
        if self.status is ValidationStatus.VALID and self.issues:
            raise AIContractError("valid result cannot contain validation issues")
        if self.status is not ValidationStatus.VALID and not self.issues:
            raise AIContractError("invalid or unclear result requires validation issues")

    @classmethod
    def valid(cls) -> ValidationResult:
        """Create the success result after ordinary code completes validation."""
        return cls(AI_SCHEMA_VERSION, ValidationStatus.VALID, ())

    @classmethod
    def invalid(
        cls,
        issues: tuple[ValidationIssue, ...] | list[ValidationIssue],
        *,
        needs_clarification: bool = False,
    ) -> ValidationResult:
        """Create a failed result after ordinary code completes validation."""
        status = (
            ValidationStatus.NEEDS_CLARIFICATION
            if needs_clarification
            else ValidationStatus.INVALID
        )
        return cls(AI_SCHEMA_VERSION, status, tuple(issues))


@dataclass(frozen=True, slots=True)
class AIValidationClaim:
    """Untrusted advisory validation output; never an authoritative result."""

    schema_version: int
    status: ValidationStatus
    issues: tuple[ValidationIssue, ...]

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != AI_SCHEMA_VERSION:
            raise AIContractError("unsupported AI validation claim schema_version")
        if not isinstance(self.status, ValidationStatus):
            raise AIContractError("AI validation claim requires a supported status")
        object.__setattr__(self, "issues", tuple(self.issues))
        if any(not isinstance(issue, ValidationIssue) for issue in self.issues):
            raise AIContractError("AI validation claim issues must be ValidationIssue values")
        if self.status is ValidationStatus.VALID and self.issues:
            raise AIContractError("valid AI claim cannot contain validation issues")
        if self.status is not ValidationStatus.VALID and not self.issues:
            raise AIContractError("invalid AI claim requires validation issues")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> AIValidationClaim:
        _check_keys(payload, {"schema_version", "status", "issues"})
        try:
            status = ValidationStatus(_required_string(payload.get("status"), "status"))
        except ValueError as exc:
            raise AIContractError("unsupported validation status") from exc
        raw_issues = payload.get("issues")
        if not isinstance(raw_issues, list):
            raise AIContractError("issues must be an array")
        if any(not isinstance(item, Mapping) for item in raw_issues):
            raise AIContractError("each issue must be an object")
        return cls(
            _version(payload),
            status,
            tuple(ValidationIssue.from_mapping(i) for i in raw_issues),
        )


@dataclass(frozen=True, slots=True)
class ProposedTerms:
    """Supported first-demo trade terms, with no workflow or approval controls."""

    schema_version: int
    description: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    currency: str
    delivery_destination: str
    delivery_date: date | None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ProposedTerms:
        _check_keys(
            payload,
            {
                "schema_version", "description", "quantity", "unit", "unit_price",
                "currency", "delivery_destination", "delivery_date",
            },
        )
        currency = _required_string(payload.get("currency"), "currency")
        if currency != "USD":
            raise AIContractError("only USD is supported for the demo proposal")
        raw_date = payload.get("delivery_date")
        try:
            delivery_date = None if raw_date is None else date.fromisoformat(
                _required_string(raw_date, "delivery_date")
            )
        except ValueError as exc:
            raise AIContractError("delivery_date must be an ISO date") from exc
        quantity = _decimal(payload.get("quantity"), "quantity")
        unit_price = _decimal(payload.get("unit_price"), "unit_price")
        if quantity <= 0:
            raise AIContractError("quantity must be positive")
        if unit_price <= 0:
            raise AIContractError("unit_price must be positive")
        return cls(
            _version(payload),
            _required_string(payload.get("description"), "description").strip(),
            quantity,
            _required_string(payload.get("unit"), "unit").strip(),
            unit_price,
            currency,
            _required_string(payload.get("delivery_destination"), "delivery_destination").strip(),
            delivery_date,
        )

    def to_trade_terms(
        self, *, buyer_id: OrganizationId, seller_id: OrganizationId
    ) -> TradeTerms:
        """Build ordinary domain terms; caller supplies trusted parties and must review."""
        try:
            unit_price = Money(self.unit_price, self.currency)
            line = TradeLineItem(self.description, self.quantity, self.unit, unit_price)
            total = line.total
            return TradeTerms(
                buyer_id=buyer_id,
                seller_id=seller_id,
                line_items=(line,),
                shipments=(ShipmentTerm(self.quantity, self.delivery_destination, self.delivery_date),),
                payment_terms=(PaymentTerm(total, "seller_invoice", "when seller invoices"),),
                delivery_location=self.delivery_destination,
                schema_version=self.schema_version,
            )
        except (InvariantViolation, ArithmeticError) as exc:
            raise AIContractError(f"proposal terms violate domain rules: {exc}") from exc


def scope_extracted_facts(
    facts: tuple[ExtractedFact, ...] | list[ExtractedFact],
    *,
    authorized_messages: Mapping[MessageId, str],
    owner_organization_id: OrganizationId,
) -> tuple[ScopedFactCandidate, ...]:
    """Bind candidates only when their quotes occur in caller-authorized messages."""
    authorized: list[ScopedFactCandidate] = []
    for index, fact in enumerate(facts):
        if fact.schema_version != AI_SCHEMA_VERSION or fact.source.schema_version != AI_SCHEMA_VERSION:
            raise AIContractError(f"facts[{index}] uses an unsupported schema version")
        message_id = fact.source.message_id
        if message_id is None:
            raise AIContractError(f"facts[{index}] is ungrounded: source is unknown")
        message_body = authorized_messages.get(message_id)
        if message_body is None:
            raise AIContractError(f"facts[{index}] references an unauthorized message")
        if fact.source.quote is None or fact.source.quote not in message_body:
            raise AIContractError(f"facts[{index}] source quote is not present in its message")
        if fact.value.casefold() not in fact.source.quote.casefold():
            raise AIContractError(f"facts[{index}] value is not stated in its source quote")
        authorized.append(ScopedFactCandidate(fact, message_id, owner_organization_id))
    return tuple(authorized)


def _validate_fact_value(
    fact_field: FactField, value: str, currency_or_unit: Any
) -> None:
    if fact_field in {FactField.QUANTITY, FactField.UNIT_PRICE}:
        if not _DECIMAL_PATTERN.fullmatch(value):
            raise AIContractError(f"{fact_field.value} must be a plain decimal string")
        try:
            decimal_value = Decimal(value)
        except InvalidOperation as exc:
            raise AIContractError(f"{fact_field.value} must be a decimal string") from exc
        if not decimal_value.is_finite() or decimal_value <= 0:
            raise AIContractError(f"{fact_field.value} must be finite and positive")
        if fact_field is FactField.UNIT_PRICE and currency_or_unit != "USD":
            raise AIContractError("unit_price requires currency_or_unit USD")
        if fact_field is FactField.QUANTITY and currency_or_unit is not None:
            _validate_unit(currency_or_unit)
        return
    if fact_field is FactField.DELIVERY_DATE:
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise AIContractError("delivery_date must be an ISO date") from exc
        if parsed.isoformat() != value:
            raise AIContractError("delivery_date must use YYYY-MM-DD format")
        if currency_or_unit is not None:
            raise AIContractError("delivery_date cannot have a currency or unit")
        return
    if fact_field is FactField.UNIT:
        _validate_unit(value)
        if currency_or_unit is not None:
            raise AIContractError("unit fact cannot have a separate currency or unit")
        return
    if currency_or_unit is not None:
        raise AIContractError(f"{fact_field.value} cannot have a currency or unit")
    if len(value) > 2_000:
        raise AIContractError(f"{fact_field.value} is too long")


_DECIMAL_PATTERN = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
_UNIT_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9 -]{0,31}")


def _validate_unit(value: Any) -> None:
    if not isinstance(value, str) or not _UNIT_PATTERN.fullmatch(value.strip()):
        raise AIContractError("unit must be well-formed plain text (1-32 characters)")


def _check_keys(payload: Mapping[str, Any], allowed: set[str]) -> None:
    if not isinstance(payload, Mapping):
        raise AIContractError("payload must be an object")
    missing = allowed - payload.keys()
    # nullable keys are still required so the JSON shape is stable and versioned.
    if missing:
        raise AIContractError(f"missing required fields: {', '.join(sorted(missing))}")
    extra = payload.keys() - allowed
    if extra:
        raise AIContractError(f"unsupported fields: {', '.join(sorted(extra))}")


def _version(payload: Mapping[str, Any]) -> int:
    version = payload.get("schema_version")
    if type(version) is not int or version != AI_SCHEMA_VERSION:
        raise AIContractError(f"schema_version must be {AI_SCHEMA_VERSION}")
    return version


def _required_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AIContractError(f"{field_name} must be a non-empty string")
    return value


def _decimal(value: Any, field_name: str) -> Decimal:
    # JSON numbers become binary floats; require decimal strings for exact values.
    if not isinstance(value, str) or not value.strip():
        raise AIContractError(f"{field_name} must be a decimal string")
    try:
        decimal_value = Decimal(value)
    except InvalidOperation as exc:
        raise AIContractError(f"{field_name} must be a decimal string") from exc
    if not decimal_value.is_finite():
        raise AIContractError(f"{field_name} must be finite")
    return decimal_value
