"""Strict versioned contracts for untrusted AI suggestions.

These types intentionally contain no approval, commitment, ownership, visibility,
or payment-operation fields. Authorization and lifecycle actions stay in normal
application/domain commands.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any
from uuid import UUID

from syncally.domain.agreements.trade_terms import (
    SUPPORTED_DEMO_CURRENCY,
    SUPPORTED_DEMO_PAYMENT_DUE_CONDITION,
    SUPPORTED_DEMO_PAYMENT_TRIGGER,
    TRADE_TERMS_SCHEMA_VERSION,
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
MAX_DECIMAL_INPUT_LENGTH = 64
MAX_DECIMAL_SIGNIFICANT_DIGITS = 18
MAX_DECIMAL_FRACTIONAL_DIGITS = 9
MAX_DECIMAL_INTEGER_DIGITS = 18
MAX_DECIMAL_EXPANDED_LENGTH = 40


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

    def __post_init__(self) -> None:
        _validate_schema_version(self.schema_version, "source reference")
        if self.message_id is not None:
            if not isinstance(self.message_id, UUID):
                raise AIContractError("source message_id must be a UUID")
            if not isinstance(self.quote, str) or not self.quote.strip():
                raise AIContractError("grounded source requires a non-empty quote")
            if self.unknown_reason is not None:
                raise AIContractError("source cannot be both grounded and unknown")
            object.__setattr__(self, "quote", self.quote.strip())
            return
        if self.quote is not None:
            raise AIContractError("source quote requires a message_id")
        if not isinstance(self.unknown_reason, str) or not self.unknown_reason.strip():
            raise AIContractError("source requires a message reference or unknown_reason")
        object.__setattr__(self, "unknown_reason", self.unknown_reason.strip())

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

    def __post_init__(self) -> None:
        _validate_schema_version(self.schema_version, "extracted fact")
        if not isinstance(self.field, FactField):
            raise AIContractError("extracted fact requires a supported field")
        if not isinstance(self.value, str) or not self.value.strip():
            raise AIContractError("value must be a non-empty string")
        if not isinstance(self.source, SourceReference):
            raise AIContractError("extracted fact requires a SourceReference")
        value = self.value.strip()
        _validate_fact_value(self.field, value, self.currency_or_unit)
        object.__setattr__(self, "value", value)

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

    def __post_init__(self) -> None:
        if not isinstance(self.fact, ExtractedFact):
            raise AIContractError("scoped candidate requires an ExtractedFact")
        if self.fact.source.message_id != self.source_message_id:
            raise AIContractError("scoped candidate source must match its fact source")
        if not isinstance(self.owner_organization_id, UUID):
            raise AIContractError("scoped candidate requires an owner organization ID")

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

    def __post_init__(self) -> None:
        _validate_schema_version(self.schema_version, "proposed terms")
        _required_string(self.description, "description")
        if len(self.description.strip()) > 2_000:
            raise AIContractError("description is too long")
        if not isinstance(self.quantity, Decimal):
            raise AIContractError("quantity must be Decimal")
        _validate_decimal(self.quantity, "quantity")
        if self.quantity <= 0:
            raise AIContractError("quantity must be positive")
        if not isinstance(self.unit_price, Decimal):
            raise AIContractError("unit_price must be Decimal")
        _validate_decimal(self.unit_price, "unit_price")
        if self.unit_price <= 0:
            raise AIContractError("unit_price must be positive")
        _validate_unit(self.unit)
        if self.currency != SUPPORTED_DEMO_CURRENCY:
            raise AIContractError("only USD is supported for the demo proposal")
        _required_string(self.delivery_destination, "delivery_destination")
        if len(self.delivery_destination.strip()) > 2_000:
            raise AIContractError("delivery_destination is too long")
        if self.delivery_date is not None and type(self.delivery_date) is not date:
            raise AIContractError("delivery_date must be a date or None")
        object.__setattr__(self, "description", self.description.strip())
        object.__setattr__(self, "unit", self.unit.strip())
        object.__setattr__(self, "delivery_destination", self.delivery_destination.strip())

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
        if currency != SUPPORTED_DEMO_CURRENCY:
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
                payment_terms=(
                    PaymentTerm(
                        total,
                        SUPPORTED_DEMO_PAYMENT_TRIGGER,
                        SUPPORTED_DEMO_PAYMENT_DUE_CONDITION,
                    ),
                ),
                delivery_location=self.delivery_destination,
                schema_version=TRADE_TERMS_SCHEMA_VERSION,
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
        if not _fact_value_is_supported_by_quote(fact, fact.source.quote):
            raise AIContractError(
                f"facts[{index}] value, currency, or unit is not supported by its source quote"
            )
        authorized.append(ScopedFactCandidate(fact, message_id, owner_organization_id))
    return tuple(authorized)


def _validate_fact_value(
    fact_field: FactField, value: str, currency_or_unit: Any
) -> None:
    if fact_field in {FactField.QUANTITY, FactField.UNIT_PRICE}:
        if not _DECIMAL_PATTERN.fullmatch(value):
            raise AIContractError(f"{fact_field.value} must be a plain decimal string")
        decimal_value = _decimal(value, fact_field.value)
        if decimal_value <= 0:
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
_NATURAL_DATE_PATTERN = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2},?\s+20\d{2}\b",
    re.IGNORECASE,
)


def _validate_unit(value: Any) -> None:
    if not isinstance(value, str) or not _UNIT_PATTERN.fullmatch(value.strip()):
        raise AIContractError("unit must be well-formed plain text (1-32 characters)")


def _fact_value_is_supported_by_quote(fact: ExtractedFact, quote: str) -> bool:
    if fact.field in {FactField.QUANTITY, FactField.UNIT_PRICE}:
        if fact.field is FactField.UNIT_PRICE:
            return _number_with_currency_is_present(fact.value, "USD", quote)
        if fact.currency_or_unit is not None:
            return _number_with_unit_is_present(fact.value, fact.currency_or_unit, quote)
        return _contains_numeric_token(fact.value, quote)
    if fact.field is FactField.UNIT:
        return _contains_token(fact.value, quote)
    if fact.field is FactField.DELIVERY_DATE:
        return _date_value_is_present(fact.value, quote)
    return fact.value.casefold() in quote.casefold()


def _contains_numeric_token(value: str, text: str) -> bool:
    token = _numeric_pattern(value)
    return re.search(rf"(?<![\w.,+-]){token}(?![\w.,])", text) is not None


def _contains_token(value: str, text: str) -> bool:
    token = _flexible_whitespace_pattern(value.strip())
    return re.search(rf"(?<![A-Za-z0-9]){token}(?![A-Za-z0-9])", text, re.IGNORECASE) is not None


def _date_value_is_present(value: str, text: str) -> bool:
    parsed_value = date.fromisoformat(value)
    if _contains_token(value, text):
        return True
    for match in _NATURAL_DATE_PATTERN.finditer(text):
        raw_date = match.group(0).replace(",", "")
        for format_string in ("%B %d %Y", "%b %d %Y"):
            try:
                if datetime.strptime(raw_date, format_string).date() == parsed_value:
                    return True
            except ValueError:
                continue
    return False


def _number_with_currency_is_present(value: str, currency: str, text: str) -> bool:
    number = _numeric_pattern(value)
    currency_token = re.escape(currency)
    alternatives = [
        rf"(?<![A-Za-z]){currency_token}\s*{number}(?![\w.,])"
        rf"|(?<![\w.,+-]){number}\s*{currency_token}(?![A-Za-z])"
    ]
    if currency == SUPPORTED_DEMO_CURRENCY:
        alternatives.extend(
            (
                rf"(?<![\w.,+-])\$\s*{number}(?![\w.,])",
                rf"(?<![\w.,+-]){number}\s*dollars?\b",
                rf"\bat\s+(?:{currency_token}\s*)?\$?{number}\s+each\b",
            )
        )
    pattern = "|".join(alternatives)
    return re.search(pattern, text, re.IGNORECASE) is not None


def _number_with_unit_is_present(value: str, unit: str, text: str) -> bool:
    number = _numeric_pattern(value)
    unit_token = _flexible_whitespace_pattern(unit.strip())
    pattern = (
        rf"(?<![\w.,+-]){number}\s+{unit_token}(?![A-Za-z0-9])"
        rf"|(?<![A-Za-z0-9]){unit_token}\s+{number}(?![\w.,])"
    )
    return re.search(pattern, text, re.IGNORECASE) is not None


def _flexible_whitespace_pattern(value: str) -> str:
    """Match normalized multiword terms against irregular source whitespace."""
    return r"\s+".join(re.escape(part) for part in value.split())


def _numeric_pattern(value: str) -> str:
    """Match a normalized decimal with or without standard thousands separators."""
    integer, separator, fractional = value.partition(".")
    grouped_integer = f"{int(integer):,}"
    integer_pattern = re.escape(integer)
    if grouped_integer != integer:
        integer_pattern = rf"(?:{integer_pattern}|{re.escape(grouped_integer)})"
    if separator:
        return rf"{integer_pattern}\.{re.escape(fractional)}"
    return integer_pattern


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
    if len(value) > MAX_DECIMAL_INPUT_LENGTH:
        raise AIContractError(f"{field_name} exceeds the supported decimal input length")
    try:
        decimal_value = Decimal(value)
    except InvalidOperation as exc:
        raise AIContractError(f"{field_name} must be a decimal string") from exc
    _validate_decimal(decimal_value, field_name)
    return decimal_value


def _validate_decimal(value: Decimal, field_name: str) -> None:
    if not value.is_finite():
        raise AIContractError(f"{field_name} must be finite")
    sign, digits, exponent = value.as_tuple()
    del sign
    if (
        len(digits) > MAX_DECIMAL_SIGNIFICANT_DIGITS
        or exponent < -MAX_DECIMAL_FRACTIONAL_DIGITS
        or exponent > MAX_DECIMAL_INTEGER_DIGITS - 1
        or (value != 0 and value.adjusted() >= MAX_DECIMAL_INTEGER_DIGITS)
    ):
        raise AIContractError(f"{field_name} exceeds the supported decimal magnitude")
    if exponent >= 0:
        expanded_length = len(digits) + exponent
    else:
        decimal_point = len(digits) + exponent
        expanded_length = len(digits) + 1 if decimal_point > 0 else 2 - decimal_point + len(digits)
    if value.is_signed():
        expanded_length += 1
    if expanded_length > MAX_DECIMAL_EXPANDED_LENGTH:
        raise AIContractError(f"{field_name} exceeds the supported expanded decimal length")


def _validate_schema_version(version: Any, field_name: str) -> None:
    if type(version) is not int or version != AI_SCHEMA_VERSION:
        raise AIContractError(f"{field_name} schema_version must be {AI_SCHEMA_VERSION}")
