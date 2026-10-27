"""Rule-based local provider used for the first end-to-end AI review demo."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal

from syncally.application.ai import (
    AIPermanentError,
    FactExtractionRequest,
    ProposalDraftRequest,
)
from syncally.domain.ai.contracts import (
    AI_SCHEMA_VERSION,
    ExtractedFact,
    FactField,
    ProposedTerms,
    SourceReference,
)

_NUMBER = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
_NUMBER_END = r"(?!\w|[.,]\d)"
_UNIT = (
    r"metric\s+tons?|metric\s+tonnes?|tons?|tonnes?|boxes|cases|pieces|units|"
    r"kg|kilograms?|lb|pounds?|bags?"
)
_QUANTITY = re.compile(rf"(?<![\w.,])({_NUMBER})\s+({_UNIT})\b", re.I)
_RANGE_TERM = (
    rf"(?:(?:USD)\s*)?\$?\s*{_NUMBER}"
    rf"(?:\s*(?:USD(?:\s*/\s*[\w-]+)?|dollars?))?"
)
_RANGE_UNIT = rf"(?:\s+(?:{_UNIT}))?"
_NUMERIC_RANGES = (
    re.compile(
        rf"(?<![\w.,]){_RANGE_TERM}\s*[-–—]\s*{_RANGE_TERM}{_NUMBER_END}", re.I
    ),
    re.compile(
        rf"(?<![\w.,]){_RANGE_TERM}{_RANGE_UNIT}\s+to\s+{_RANGE_TERM}{_NUMBER_END}", re.I
    ),
    re.compile(rf"\bbetween\s+{_RANGE_TERM}{_RANGE_UNIT}\s+and\s+{_RANGE_TERM}", re.I),
    re.compile(rf"\bfrom\s+{_RANGE_TERM}{_RANGE_UNIT}\s+to\s+{_RANGE_TERM}", re.I),
    re.compile(
        rf"(?<![\w.,]){_RANGE_TERM}{_RANGE_UNIT}\s+or\s+{_RANGE_TERM}{_NUMBER_END}", re.I
    ),
)
_QUALIFIER_PREFIX = re.compile(
    r"\b(?:about|around|approximately|approx\.?|roughly|at least|at most|up to|"
    r"no more than|no less than|more than|less than|over|under|minimum(?: of)?|"
    r"maximum(?: of)?|in excess of|no fewer than)\s+(?:(?:USD)\s*)?\$?\s*$",
    re.I,
)
_QUALIFIER_SUFFIX = re.compile(
    rf"^\s*(?:(?:{_UNIT}|USD(?:\s*/\s*[\w-]+)?|dollars?)\s*)?[,;:]?\s*"
    r"(?:\+|(?:or\s+)?(?:more|less|minimum|maximum|at least|at most|above|below|"
    r"and\s+up|"
    r"greater|fewer|higher|lower)\b)",
    re.I,
)
_USD_PRICE = re.compile(
    rf"(?:"
    rf"\$\s*(?P<dollar>{_NUMBER}){_NUMBER_END}"
    rf"|\bUSD\s*(?P<usd_prefix>{_NUMBER}){_NUMBER_END}"
    rf"|(?<![\w.,])(?P<usd_suffix>{_NUMBER})\s*(?:USD(?:\s*/\s*[\w-]+)?|dollars?\b)"
    rf"|\bat\s+(?:USD\s*)?\$?(?P<each>{_NUMBER})\s+each\b"
    rf")",
    re.I,
)
_ITEM_PATTERNS = (
    re.compile(
        r"\b(?:item|product)\s*:\s*(?P<value>(?:\d{1,3},\d{3}|[^,.;\n]){1,200})", re.I
    ),
    re.compile(
        r"\b(?:order\s+of|buying|supplying)\s+"
        r"(?P<value>(?:\d{1,3},\d{3}|[^,.;\n]){1,200})",
        re.I,
    ),
)
_DESTINATION = re.compile(
    r"\b(?:ship(?:ping)?\s+to|deliver(?:y|ing)?\s+(?:to|at)|destination\s*:)\s*"
    r"(?P<value>[^,.;\n]{1,200}(?:,\s*[A-Z]{2,3}\b"
    r"(?=\s*(?:[,.;\n]|$|\b(?:by|on)\b)))*)",
    re.I,
)
_DATE = re.compile(
    r"\b(?P<value>20\d{2}-\d{2}-\d{2}|"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2},?\s+20\d{2})\b",
    re.I,
)
_QUANTITY_PREFIX = re.compile(rf"^{_NUMBER}\s+(?:{_UNIT})\b\s*(?:of\s+)?", re.I)
_QUANTITY_SUFFIX = re.compile(rf"\s+{_NUMBER}\s+(?:{_UNIT})\b.*$", re.I)
_ITEM_CLAUSE = re.compile(
    r"\s+(?:at\b|for\b|ship(?:ping)?\s+to\b|deliver(?:y|ing)?\s+(?:to|at)\b|"
    r"destination\s*:|by\b).*$",
    re.I,
)
_DESTINATION_CLAUSE = re.compile(r"\s+(?:by\b|on\b).*$", re.I)


class DemoAISuggestionProvider:
    """Extract deterministically phrased values without networking or inventing facts."""

    def extract_facts(
        self, request: FactExtractionRequest, *, timeout_seconds: float
    ) -> tuple[ExtractedFact, ...]:
        del timeout_seconds
        extracted: list[ExtractedFact] = []
        for message in request.context.messages:
            body = message.body
            self._append_item(extracted, message.id, body)
            self._append_text_match(
                extracted, message.id, body, _DESTINATION, FactField.DELIVERY_DESTINATION,
                cleaner=_DESTINATION_CLAUSE,
            )
            self._append_date(extracted, message.id, body)

            quantity_match = next(
                (
                    match
                    for match in _QUANTITY.finditer(body)
                    if not _is_ambiguous_numeric_term(body, *match.span(1))
                ),
                None,
            )
            if quantity_match:
                number = quantity_match.group(1).replace(",", "")
                unit = re.sub(r"\s+", " ", quantity_match.group(2)).lower()
                quote = quantity_match.group(0)
                extracted.append(self._fact(FactField.QUANTITY, number, message.id, quote, unit))
                extracted.append(self._fact(FactField.UNIT, unit, message.id, quote))

            for price_match in _USD_PRICE.finditer(body):
                amount_group = next(
                    name
                    for name, value in price_match.groupdict().items()
                    if value is not None
                )
                if _is_ambiguous_numeric_term(body, *price_match.span(amount_group)):
                    continue
                amount = price_match.group(amount_group).replace(",", "")
                extracted.append(
                    self._fact(
                        FactField.UNIT_PRICE,
                        amount,
                        message.id,
                        price_match.group(0),
                        "USD",
                    )
                )
                break
        return tuple(extracted)

    def draft_proposal(
        self, request: ProposalDraftRequest, *, timeout_seconds: float
    ) -> ProposedTerms:
        facts = self.extract_facts(
            FactExtractionRequest(request.context), timeout_seconds=timeout_seconds
        )
        values = {fact.field: fact for fact in facts}
        stored = {
            fact.field.casefold().replace(" ", "_"): fact
            for fact in request.context.constraints
        }

        def value(field: FactField, stored_field: str | None = None) -> str:
            extracted = values.get(field)
            if extracted is not None:
                return extracted.value
            saved = stored.get(stored_field or field.value)
            return saved.typed_value if saved is not None else ""

        description = value(FactField.ITEM_DESCRIPTION)
        quantity = value(FactField.QUANTITY)
        unit = value(FactField.UNIT)
        price = value(FactField.UNIT_PRICE)
        destination = value(FactField.DELIVERY_DESTINATION)
        delivery_date = value(FactField.DELIVERY_DATE)
        if not all((description, quantity, unit, price, destination)):
            raise AIPermanentError("The available context does not support complete demo terms")
        try:
            return ProposedTerms(
                schema_version=AI_SCHEMA_VERSION,
                description=description,
                quantity=Decimal(quantity),
                unit=unit,
                unit_price=Decimal(price),
                currency="USD",
                delivery_destination=destination,
                delivery_date=date.fromisoformat(delivery_date) if delivery_date else None,
            )
        except (ValueError, ArithmeticError) as error:
            raise AIPermanentError("The available context does not support valid demo terms") from error

    @classmethod
    def _append_item(cls, facts: list[ExtractedFact], message_id, body: str) -> None:
        for pattern in _ITEM_PATTERNS:
            match = pattern.search(body)
            if match:
                value = cls._clean_item(match.group("value"))
                if value:
                    facts.append(
                        cls._fact(FactField.ITEM_DESCRIPTION, value, message_id, match.group(0))
                    )
                return

    @staticmethod
    def _clean_item(value: str) -> str:
        value = _ITEM_CLAUSE.sub("", value).strip(" \t:-")
        value = _QUANTITY_PREFIX.sub("", value).strip()
        value = _QUANTITY_SUFFIX.sub("", value).strip(" \t,;:-")
        return value[:200].strip()

    @classmethod
    def _append_text_match(
        cls,
        facts: list[ExtractedFact],
        message_id,
        body: str,
        pattern: re.Pattern[str],
        field: FactField,
        *,
        cleaner: re.Pattern[str] | None = None,
    ) -> None:
        match = pattern.search(body)
        if match:
            value = match.group("value").strip()
            if cleaner is not None:
                value = cleaner.sub("", value).strip(" \t,;:-")
            if value:
                facts.append(cls._fact(field, value[:200], message_id, match.group(0)))

    @classmethod
    def _append_date(cls, facts: list[ExtractedFact], message_id, body: str) -> None:
        match = _DATE.search(body)
        if not match:
            return
        raw_date = match.group("value")
        try:
            normalized = date.fromisoformat(raw_date)
        except ValueError:
            normalized = None
            for format_string in ("%B %d %Y", "%b %d %Y"):
                try:
                    normalized = datetime.strptime(
                        raw_date.replace(",", ""), format_string
                    ).date()
                    break
                except ValueError:
                    continue
        if normalized is not None:
            facts.append(
                cls._fact(FactField.DELIVERY_DATE, normalized.isoformat(), message_id, match.group(0))
            )

    @staticmethod
    def _fact(
        field: FactField,
        value: str,
        message_id,
        quote: str,
        currency_or_unit: str | None = None,
    ) -> ExtractedFact:
        return ExtractedFact(
            schema_version=AI_SCHEMA_VERSION,
            field=field,
            value=value,
            source=SourceReference(
                schema_version=AI_SCHEMA_VERSION,
                message_id=message_id,
                quote=quote,
                unknown_reason=None,
            ),
            currency_or_unit=currency_or_unit,
        )


def _is_ambiguous_numeric_term(body: str, start: int, end: int) -> bool:
    """Avoid presenting a range or qualified amount as an exact trade term."""
    if any(
        match.start() <= start and end <= match.end()
        for pattern in _NUMERIC_RANGES
        for match in pattern.finditer(body)
    ):
        return True
    if _QUALIFIER_PREFIX.search(body[:start]):
        return True
    return _QUALIFIER_SUFFIX.match(body[end:]) is not None
