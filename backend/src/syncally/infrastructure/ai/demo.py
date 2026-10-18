"""Rule-based local provider used for the first end-to-end AI review demo."""

from __future__ import annotations

import re
from datetime import date
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

_QUANTITY = re.compile(r"\b(\d+(?:\.\d+)?)\s+(boxes|cases|pieces|units|kg|kilograms|lb|pounds)\b", re.I)
_USD_PRICE = re.compile(r"\bUSD\s*(\d+(?:\.\d{1,2})?)\b|\b(\d+(?:\.\d{1,2})?)\s*USD\b", re.I)
_DESCRIPTION = re.compile(r"\b(?:item|product)\s*:\s*([^,.;\n]{1,200})", re.I)
_DESTINATION = re.compile(r"\b(?:deliver|ship)\s+to\s+([^,.;\n]{1,200})", re.I)
_ISO_DATE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")


class DemoAISuggestionProvider:
    """Extract explicitly marked values without networking or inventing facts."""

    def extract_facts(
        self, request: FactExtractionRequest, *, timeout_seconds: float
    ) -> tuple[ExtractedFact, ...]:
        del timeout_seconds
        extracted: list[ExtractedFact] = []
        for message in request.context.messages:
            body = message.body
            self._append_match(extracted, message.id, body, _DESCRIPTION, FactField.ITEM_DESCRIPTION)
            self._append_match(extracted, message.id, body, _DESTINATION, FactField.DELIVERY_DESTINATION)
            self._append_match(extracted, message.id, body, _ISO_DATE, FactField.DELIVERY_DATE)
            quantity_match = _QUANTITY.search(body)
            if quantity_match:
                number, unit = quantity_match.group(1), quantity_match.group(2)
                quote = quantity_match.group(0)
                extracted.append(self._fact(FactField.QUANTITY, number, message.id, quote, unit.lower()))
                extracted.append(self._fact(FactField.UNIT, unit.lower(), message.id, quote))
            price_match = _USD_PRICE.search(body)
            if price_match:
                amount = price_match.group(1) or price_match.group(2)
                extracted.append(
                    self._fact(FactField.UNIT_PRICE, amount, message.id, price_match.group(0), "USD")
                )
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

    @staticmethod
    def _append_match(
        facts: list[ExtractedFact], message_id, body: str, pattern: re.Pattern[str], field: FactField
    ) -> None:
        match = pattern.search(body)
        if match:
            value = match.group(1).strip()
            facts.append(DemoAISuggestionProvider._fact(field, value, message_id, match.group(0)))

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
