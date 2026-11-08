"""Provider-independent AI suggestion boundary and bounded orchestration.

Business rules never import a provider SDK. Providers implement the small
``AISuggestionProvider`` port and translate their response into the versioned
S4-01 contracts; the use cases here compose the organization-scoped context from
S4-02 with a bounded, retry-limited call. Every result is an unreviewed
candidate: nothing here confirms a fact, approves terms, or starts a payment.
"""

from __future__ import annotations

import decimal
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from time import monotonic
from time import sleep as default_sleep
from typing import Literal, Protocol, runtime_checkable
from uuid import UUID, uuid4

from syncally.application.conversations import (
    MAX_PAGE_SIZE,
    AiContext,
    CommunicationNotFound,
    CommunicationRepository,
    OrganizationAccessDenied,
    select_ai_context,
)
from syncally.application.identity import ActorContext
from syncally.domain.ai.contracts import (
    AI_SCHEMA_VERSION,
    AIContractError,
    ExtractedFact,
    NormalizedRequirement,
    ProposedTerms,
    ScopedFactCandidate,
    ValidationIssue,
    ValidationResult,
    ValidationStatus,
    scope_extracted_facts,
)
from syncally.domain.conversations import Constraint, ConstraintKind, ConstraintStatus, Visibility
from syncally.domain.shared.identifiers import ConstraintId, DealId, OrganizationId

NormalizedTradeRequirements = NormalizedRequirement

DEFAULT_MAX_ATTEMPTS = 2
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_BACKOFF_SECONDS = 0.5

_REQUIRED_PROPOSAL_FIELDS = (
    ("description", frozenset({"description", "item_description"})),
    ("quantity", frozenset({"quantity"})),
    ("unit", frozenset({"unit"})),
    ("unit_price", frozenset({"unit_price"})),
    ("delivery_destination", frozenset({"delivery_destination"})),
    ("delivery_date", frozenset({"delivery_date"})),
)


def missing_trade_fields(constraints: Iterable[Constraint]) -> list[str]:
    """List required proposal fields not represented by visible deal facts."""
    ignored_statuses = {
        ConstraintStatus.NEEDS_CLARIFICATION,
        ConstraintStatus.REJECTED,
        ConstraintStatus.SUPERSEDED,
    }
    present = {
        constraint.field.casefold().replace(" ", "_")
        for constraint in constraints
        if constraint.status not in ignored_statuses
    }
    return [
        proposal_field
        for proposal_field, aliases in _REQUIRED_PROPOSAL_FIELDS
        if not present.intersection(aliases)
    ]


def fact_suggestion_guidance(missing_fields: list[str]) -> str:
    """Give the user a deterministic prompt for missing trade details."""
    if not missing_fields:
        return "All required trade details were found. Review each fact before using a draft."
    labels = {
        "description": "item description",
        "quantity": "quantity",
        "unit": "unit",
        "unit_price": "unit price",
        "delivery_destination": "delivery destination",
        "delivery_date": "delivery date",
    }
    missing = ", ".join(labels[field] for field in missing_fields)
    return (
        f"Add the missing details: {missing}. Suggested format: "
        "‘Order of [item], [quantity] [unit] at USD [price] each, "
        "ship to [city or port] by YYYY-MM-DD.’"
    )


class AIProviderError(Exception):
    """Base class for a failed AI provider call."""


class AITransientError(AIProviderError):
    """A retryable provider failure, such as a timeout or temporary outage."""


class AIPermanentError(AIProviderError):
    """A non-retryable provider failure, such as malformed provider output."""


class AIConfigurationError(AIProviderError):
    """Remote suggestions require explicit operator configuration."""


@dataclass(frozen=True, slots=True)
class AIProvenance:
    provider: Literal["offline", "openai", "unknown"] = "unknown"
    mode: Literal["offline", "openai", "openai_with_offline_fallback", "unknown"] = "unknown"
    model: str | None = None
    context_scope: Literal["authorized", "shareable_only", "authorized_private", "unknown"] = "unknown"
    fallback_reason: Literal["missing_credentials", "transient_exhausted"] | None = None


def provider_provenance(provider: AISuggestionProvider) -> AIProvenance:
    provenance = getattr(provider, "provenance", None)
    return provenance if isinstance(provenance, AIProvenance) else AIProvenance()


def _provider_context(context: AiContext, provider: AISuggestionProvider) -> AiContext:
    prepare = getattr(provider, "prepare_context", None)
    return prepare(context) if prepare is not None else context


@dataclass(frozen=True, slots=True)
class AIRetryPolicy:
    """A fixed bound on how long and how often one provider call may run."""

    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS

    def __post_init__(self) -> None:
        if (
            not isinstance(self.max_attempts, int)
            or isinstance(self.max_attempts, bool)
            or self.max_attempts < 1
        ):
            raise ValueError("max_attempts must be a positive integer")
        if (
            not isinstance(self.timeout_seconds, (int, float))
            or isinstance(self.timeout_seconds, bool)
            or self.timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be positive")
        if (
            not isinstance(self.backoff_seconds, (int, float))
            or isinstance(self.backoff_seconds, bool)
            or self.backoff_seconds < 0
        ):
            raise ValueError("backoff_seconds must be zero or greater")


@dataclass(frozen=True, slots=True)
class FactExtractionRequest:
    """Authorized, organization-scoped input for one extraction call."""

    context: AiContext


@dataclass(frozen=True, slots=True)
class ProposalDraftRequest:
    """Authorized, organization-scoped input for one proposal call."""

    context: AiContext


@runtime_checkable
class AISuggestionProvider(Protocol):
    """The boundary every AI provider adapter implements.

    Implementations own provider-specific transport, credentials, and output
    parsing; they receive only the S4-02 filtered context and return S4-01
    contracts. They must raise ``AITransientError`` for retryable failures and
    ``AIPermanentError`` for unusable output.
    """

    def extract_facts(
        self, request: FactExtractionRequest, *, timeout_seconds: float
    ) -> tuple[ExtractedFact, ...]:
        """Return ungrounded candidate facts; the caller binds and validates them."""

    def draft_proposal(
        self, request: ProposalDraftRequest, *, timeout_seconds: float
    ) -> ProposedTerms:
        """Return one untrusted draft; it is never an agreement."""


@dataclass(frozen=True, slots=True)
class FactExtractionResult:
    """A validated extraction outcome.

    ``candidates`` is populated only when ``result`` is VALID. Invalid or
    ungrounded provider output yields no candidates, so it can never be
    auto-confirmed or silently treated as agreed truth.
    """

    result: ValidationResult
    candidates: tuple[ScopedFactCandidate, ...]
    provenance: AIProvenance = AIProvenance()

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidates", tuple(self.candidates))
        if self.result.status is not ValidationStatus.VALID and self.candidates:
            raise ValueError("an invalid extraction result must not carry candidates")


@dataclass(frozen=True, slots=True)
class ProposalDraftResult:
    """A validated proposal outcome; a rejected draft carries no proposal."""

    result: ValidationResult
    proposal: ProposedTerms | None
    provenance: AIProvenance = AIProvenance()

    def __post_init__(self) -> None:
        if self.result.status is ValidationStatus.VALID and self.proposal is None:
            raise ValueError("a valid proposal result must carry a proposal")
        if self.result.status is not ValidationStatus.VALID and self.proposal is not None:
            raise ValueError("an invalid proposal result must not carry a proposal")


def parse_extracted_facts(
    payloads: Iterable[Mapping[str, object]],
) -> tuple[ExtractedFact, ...]:
    """Validate raw provider fact payloads with the S4-01 contract.

    The raised error deliberately omits the payload, so provider output - which
    may echo private context - never reaches logs through an exception message.
    """
    try:
        return tuple(ExtractedFact.from_mapping(payload) for payload in payloads)
    except (AIContractError, TypeError) as exc:
        raise AIPermanentError("AI provider returned invalid fact output") from exc


def parse_proposed_terms(payload: Mapping[str, object]) -> ProposedTerms:
    """Validate a raw provider proposal payload with the S4-01 contract."""
    try:
        return ProposedTerms.from_mapping(payload)
    except (AIContractError, TypeError) as exc:
        raise AIPermanentError("AI provider returned invalid proposal output") from exc


def call_with_bounded_retry[T](
    operation: Callable[[], T],
    policy: AIRetryPolicy,
    *,
    sleep: Callable[[float], None] = default_sleep,
) -> T:
    """Run one provider operation, retrying only transient failures.

    Permanent failures and unexpected errors propagate immediately; transient
    failures are retried at most ``policy.max_attempts`` times and then surface
    as a single ``AITransientError`` for the caller (or worker) to retry later.
    """
    deadline = monotonic() + policy.max_attempts * policy.timeout_seconds + (policy.max_attempts - 1) * policy.backoff_seconds
    for attempt in range(1, policy.max_attempts + 1):
        if monotonic() >= deadline:
            break
        try:
            value = operation()
            if monotonic() >= deadline:
                raise AITransientError("AI provider deadline exceeded")
            return value
        except AITransientError:
            if attempt < policy.max_attempts and monotonic() + policy.backoff_seconds < deadline:
                sleep(policy.backoff_seconds)
    raise AITransientError(
        f"AI provider was unavailable after {policy.max_attempts} attempts"
    ) from None


def extract_facts(
    actor: ActorContext,
    deal_id: UUID,
    organization_id: UUID,
    repository: CommunicationRepository,
    provider: AISuggestionProvider,
    *,
    policy: AIRetryPolicy = AIRetryPolicy(),
    sleep: Callable[[float], None] = default_sleep,
) -> FactExtractionResult:
    """Suggest facts from one organization's authorized context.

    The provider only ever receives the S4-02 filtered context. Its output is
    grounded against those same authorized messages, so it cannot smuggle in a
    fact from the counterparty's private data.
    """
    context = select_ai_context(actor, deal_id, organization_id, repository)
    return extract_facts_from_context(context, provider, policy=policy, sleep=sleep)


def extract_facts_from_context(
    context: AiContext,
    provider: AISuggestionProvider,
    *,
    policy: AIRetryPolicy = AIRetryPolicy(),
    sleep: Callable[[float], None] = default_sleep,
) -> FactExtractionResult:
    """Call the provider and validate candidates after authorized context is loaded."""
    context = _provider_context(context, provider)
    request = FactExtractionRequest(context=context)

    try:
        try:
            facts = call_with_bounded_retry(
                lambda: provider.extract_facts(request, timeout_seconds=policy.timeout_seconds),
                policy,
                sleep=sleep,
            )
        except AITransientError:
            fallback = getattr(provider, "fallback_facts", None)
            if fallback is None:
                raise
            facts = fallback(request, timeout_seconds=policy.timeout_seconds)
        candidates = scope_extracted_facts(
            facts,
            authorized_messages={message.id: message.body for message in context.messages},
            owner_organization_id=context.organization_id,
        )
    except AIPermanentError as error:
        return _rejected_fact_result("AI_OUTPUT_INVALID", str(error), provider_provenance(provider))
    except AIContractError as error:
        return _rejected_fact_result("AI_OUTPUT_UNGROUNDED", str(error), provider_provenance(provider))
    return FactExtractionResult(ValidationResult.valid(), candidates, provider_provenance(provider))


def draft_proposal(
    actor: ActorContext,
    deal_id: UUID,
    organization_id: UUID,
    repository: CommunicationRepository,
    provider: AISuggestionProvider,
    *,
    policy: AIRetryPolicy = AIRetryPolicy(),
    sleep: Callable[[float], None] = default_sleep,
) -> ProposalDraftResult:
    """Draft one non-binding proposal from a single organization's context."""
    context = select_ai_context(actor, deal_id, organization_id, repository)
    return draft_proposal_from_context(context, provider, policy=policy, sleep=sleep)


def draft_proposal_from_context(
    context: AiContext,
    provider: AISuggestionProvider,
    *,
    policy: AIRetryPolicy = AIRetryPolicy(),
    sleep: Callable[[float], None] = default_sleep,
) -> ProposalDraftResult:
    """Call a provider with an already authorized, transaction-free context."""
    context = _provider_context(context, provider)
    request = ProposalDraftRequest(context=context)

    try:
        try:
            proposal = call_with_bounded_retry(
                lambda: provider.draft_proposal(request, timeout_seconds=policy.timeout_seconds),
                policy,
                sleep=sleep,
            )
        except AITransientError:
            fallback = getattr(provider, "fallback_proposal", None)
            if fallback is None:
                raise
            proposal = fallback(request, timeout_seconds=policy.timeout_seconds)
    except AIPermanentError as error:
        issue = ValidationIssue(
            schema_version=AI_SCHEMA_VERSION,
            code="AI_OUTPUT_INVALID",
            path="proposal",
            message=str(error),
        )
        return ProposalDraftResult(ValidationResult.invalid((issue,)), None, provider_provenance(provider))
    return ProposalDraftResult(ValidationResult.valid(), proposal, provider_provenance(provider))


def persist_fact_candidates(
    actor: ActorContext,
    deal_id: UUID,
    result: FactExtractionResult,
    repository: CommunicationRepository,
    *,
    now: datetime | None = None,
) -> tuple[Constraint, ...]:
    """Save validated candidates as private, unconfirmed facts for human review."""
    should_write = result.result.status is ValidationStatus.VALID and bool(result.candidates)
    deal = (
        repository.lock_deal_for_fact_persistence(deal_id, actor.user_id)
        if should_write
        else repository.get_deal_for_participant(deal_id, actor.user_id)
    )
    if deal is None or deal.id != deal_id or not actor.can_access_deal(deal):
        raise CommunicationNotFound("Deal not found")
    if result.result.status is not ValidationStatus.VALID:
        return ()

    saved: list[Constraint] = []
    candidate_owners = {candidate.owner_organization_id for candidate in result.candidates}
    existing = [
        fact
        for owner_id in candidate_owners
        if owner_id in actor.organization_ids
        for fact in _list_all_constraints_for_owner(repository, deal_id, owner_id)
    ]
    existing_by_signature = {
        (fact.owner_organization_id, fact.source_message_id, fact.field, fact.typed_value): fact
        for fact in existing
    }
    created_at = now or datetime.now(UTC)
    for candidate in result.candidates:
        if candidate.owner_organization_id not in actor.organization_ids or candidate.owner_organization_id not in (
            deal.buyer_organization_id,
            deal.seller_organization_id,
        ):
            raise OrganizationAccessDenied("Actor cannot save a fact for this organization")
        signature = (
            candidate.owner_organization_id,
            candidate.source_message_id,
            candidate.fact.field.value,
            candidate.fact.value,
        )
        existing_fact = existing_by_signature.get(signature)
        if existing_fact is not None:
            if existing_fact.status in {
                ConstraintStatus.EXTRACTED,
                ConstraintStatus.NEEDS_CLARIFICATION,
            }:
                saved.append(existing_fact)
            continue
        fact = Constraint(
            id=ConstraintId(uuid4()),
            deal_id=DealId(deal_id),
            owner_organization_id=OrganizationId(candidate.owner_organization_id),
            field=candidate.fact.field.value,
            typed_value=candidate.fact.value,
            currency_or_unit=candidate.fact.currency_or_unit,
            kind=ConstraintKind.INFORMATIONAL,
            visibility=Visibility.PRIVATE,
            source_message_id=candidate.source_message_id,
            source_span=candidate.fact.source.quote,
            created_at=created_at,
        )
        saved.append(repository.add_constraint(fact))
        existing_by_signature[signature] = fact
    return tuple(saved)


def _list_all_constraints_for_owner(
    repository: CommunicationRepository, deal_id: UUID, owner_id: UUID
) -> list[Constraint]:
    """Page through all visible facts so old signatures cannot be duplicated."""
    constraints: list[Constraint] = []
    offset = 0
    while True:
        page = repository.list_constraints(
            deal_id, owner_id, limit=MAX_PAGE_SIZE, offset=offset
        )
        constraints.extend(page)
        if len(page) < MAX_PAGE_SIZE:
            return constraints
        offset += len(page)


def _rejected_fact_result(
    code: str, message: str, provenance: AIProvenance = AIProvenance(),
) -> FactExtractionResult:
    issue = ValidationIssue(
        schema_version=AI_SCHEMA_VERSION,
        code=code,
        path="facts",
        message=message,
    )
    return FactExtractionResult(ValidationResult.invalid((issue,)), (), provenance)


# ---------------------------------------------------------------------------
# Opening Request Normalization & Extraction
# ---------------------------------------------------------------------------

_COUNTRY_MAP: dict[str, str] = {
    "united states": "US", "usa": "US", "us": "US", "u.s.": "US", "u.s.a.": "US", "america": "US",
    "canada": "CA",
    "germany": "DE", "deutschland": "DE",
    "japan": "JP", "nippon": "JP",
    "france": "FR",
    "united kingdom": "GB", "uk": "GB", "u.k.": "GB", "great britain": "GB", "britain": "GB", "england": "GB",
    "italy": "IT", "italia": "IT",
    "spain": "ES", "espana": "ES",
    "australia": "AU",
    "china": "CN",
    "india": "IN",
    "netherlands": "NL", "holland": "NL",
    "mexico": "MX",
    "brazil": "BR", "brasil": "BR",
    "singapore": "SG",
    "south korea": "KR", "korea": "KR",
    "switzerland": "CH",
    "sweden": "SE",
    "poland": "PL",
    "austria": "AT",
    "belgium": "BE",
    "taiwan": "TW",
    "vietnam": "VN",
    "thailand": "TH",
    "turkey": "TR",
    "ireland": "IE",
    "new zealand": "NZ",
    "norway": "NO",
    "denmark": "DK",
    "finland": "FI",
    "portugal": "PT",
    "czech republic": "CZ", "czechia": "CZ",
    "israel": "IL",
    "united arab emirates": "AE", "uae": "AE",
    "saudi arabia": "SA",
    "south africa": "ZA",
    "chile": "CL",
    "argentina": "AR",
    "colombia": "CO",
    "indonesia": "ID",
    "malaysia": "MY",
    "philippines": "PH",
}

_CITY_COUNTRY_MAP: dict[str, str] = {
    "berlin": "DE", "munich": "DE", "frankfurt": "DE", "hamburg": "DE", "stuttgart": "DE",
    "tokyo": "JP", "osaka": "JP", "kyoto": "JP", "yokohama": "JP", "nagoya": "JP",
    "toronto": "CA", "vancouver": "CA", "montreal": "CA", "calgary": "CA", "ottawa": "CA",
    "london": "GB", "manchester": "GB", "birmingham": "GB", "edinburgh": "GB",
    "paris": "FR", "lyon": "FR", "marseille": "FR", "toulouse": "FR",
    "seattle": "US", "new york": "US", "los angeles": "US", "chicago": "US", "san francisco": "US",
    "boston": "US", "austin": "US", "dallas": "US", "houston": "US", "atlanta": "US",
    "sydney": "AU", "melbourne": "AU", "brisbane": "AU",
    "shanghai": "CN", "beijing": "CN", "shenzhen": "CN", "guangzhou": "CN",
    "mumbai": "IN", "delhi": "IN", "bangalore": "IN", "chennai": "IN", "hyderabad": "IN",
    "amsterdam": "NL", "rotterdam": "NL",
    "seoul": "KR", "zurich": "CH", "geneva": "CH", "singapore": "SG",
    "rome": "IT", "milan": "IT", "madrid": "ES", "barcelona": "ES",
    "warsaw": "PL", "vienna": "AT", "brussels": "BE", "stockholm": "SE",
    "dublin": "IE", "auckland": "NZ", "sao paulo": "BR", "mexico city": "MX",
}

_US_CAN_PROVINCES: dict[str, str] = {
    "WA": "US", "CA": "US", "NY": "US", "TX": "US", "IL": "US", "FL": "US", "PA": "US",
    "OH": "US", "GA": "US", "NC": "US", "MI": "US", "NJ": "US", "VA": "US", "MA": "US",
    "AZ": "US", "IN": "US", "TN": "US", "MO": "US", "MD": "US", "WI": "US", "CO": "US",
    "MN": "US", "SC": "US", "AL": "US", "LA": "US", "KY": "US", "OR": "US", "OK": "US",
    "CT": "US", "UT": "US", "IA": "US", "NV": "US", "AR": "US", "MS": "US", "KS": "US",
    "NM": "US", "NE": "US", "ID": "US", "WV": "US", "HI": "US", "NH": "US", "ME": "US",
    "RI": "US", "MT": "US", "DE": "US", "SD": "US", "ND": "US", "AK": "US", "DC": "US",
    "VT": "US", "WY": "US",
    "ON": "CA", "QC": "CA", "BC": "CA", "AB": "CA", "MB": "CA", "SK": "CA", "NS": "CA",
    "NB": "CA", "NL": "CA", "PE": "CA", "NT": "CA", "YT": "CA", "NU": "CA",
}

_KNOWN_CAPABILITIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("precision CNC machining", ("precision cnc machining", "precision cnc", "cnc machining", "precision machining")),
    ("CNC Machining", ("cnc", "machining")),
    ("Injection Molding", ("plastic injection molding", "injection molding", "molding")),
    ("Sheet Metal Fabrication", ("sheet metal fabrication", "metal fabrication", "fabrication")),
    ("Electronics Manufacturing", ("electronics manufacturing", "pcb assembly", "pcb", "electronics assembly")),
    ("Packaging", ("packaging materials", "custom packaging", "packaging")),
    ("Global Logistics", ("global logistics", "freight forwarding", "shipping logistics", "logistics")),
    ("Surface Finishing", ("surface finishing", "coating", "heat treatment", "electroplating", "anodizing")),
    ("Quality Inspection", ("quality inspection", "iso 9001", "quality assurance")),
    ("Assembly", ("assembly", "mechanical assembly")),
    ("Casting & Forging", ("die casting", "casting", "forging", "stamping")),
    ("Additive Manufacturing", ("3d printing", "additive manufacturing")),
    ("Procurement", ("procurement", "sourcing")),
)

_CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Fasteners", ("bolts", "screws", "fasteners", "nuts", "washers", "rivets", "studs", "hardware")),
    ("Automotive", ("automotive", "vehicle", "engine", "car parts", "brake", "transmission")),
    ("Electronics", ("copper wire", "wire", "cable", "pcb", "circuit", "sensor", "semiconductor")),
    ("Packaging", ("packaging materials", "packaging", "boxes", "cartons", "corrugated", "crates", "pallet")),
    ("Agriculture", ("wheat", "grain", "coffee", "rice", "corn", "soybean", "barley", "flour")),
    ("Machining", ("cnc", "machined", "machining", "turned parts", "milled")),
    ("Raw Materials", ("steel", "aluminum", "copper", "brass", "titanium", "plastic resin")),
    ("Plastics & Polymers", ("plastic housings", "housings", "plastic parts", "polymer")),
)

_CURRENCY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("CAD", re.compile(r"\b(?:CAD|Canadian\s*Dollars?)\b|C\$", re.IGNORECASE)),
    ("AUD", re.compile(r"\b(?:AUD|Australian\s*Dollars?)\b|A\$", re.IGNORECASE)),
    ("USD", re.compile(r"\b(?:USD|US\s*Dollars?)\b|(?<![A-Za-z])\$", re.IGNORECASE)),
    ("EUR", re.compile(r"\b(?:EUR|Euros?)\b|€", re.IGNORECASE)),
    ("GBP", re.compile(r"\b(?:GBP|Pounds?)\b|£", re.IGNORECASE)),
    ("JPY", re.compile(r"\b(?:JPY|Yen)\b|¥", re.IGNORECASE)),
    ("CHF", re.compile(r"\b(?:CHF|Swiss\s*Francs?)\b", re.IGNORECASE)),
    ("CNY", re.compile(r"\b(?:CNY|RMB|Yuan)\b", re.IGNORECASE)),
    ("INR", re.compile(r"\b(?:INR|Rupees?)\b|₹", re.IGNORECASE)),
)


_UNIT_PRICE_RE = re.compile(
    r"(?:"
    r"(?:(?:target(?:\s+unit)?\s+price|unit\s+price|price|budget\s+is|target\s+price)\s*(?:is|:|=)?\s*|\bat\s+)"
    r"[$€£¥₹]?\s*(?P<price>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?!\d)\s*(?:USD|EUR|GBP|CAD|AUD|JPY|INR|dollars?|euros?|pounds?)?\s*"
    r"(?:/(?:unit|m|meter|piece|pc|box|kg|part|item)|\bper\s+(?:unit|m|meter|piece|pc|box|kg|part|item)|\beach\b|\bUSD/m\b)"
    r"|"
    r"\b(?P<price_alt>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?!\d)\s*(?:USD/m|USD/unit|USD/pc|\$/unit|\$/pc|\$/m)\b"
    r")",
    re.IGNORECASE,
)

_BUDGET_RE = re.compile(
    r"(?:"
    r"(?:total\s+budget|budget|max\s+budget|under|not\s+to\s+exceed|up\s+to|max)\s*(?:is|of|:|=)?\s*"
    r")"
    r"[$€£¥₹]?\s*(?P<amount>\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?:USD|EUR|GBP|CAD|AUD|JPY|INR|dollars?|euros?|pounds?)?\b"
    r"(?!\s*(?:/(?:unit|m|piece|pc|box|kg|part)|\bper\s+|\beach\b))",
    re.IGNORECASE,
)

_STD_UNITS = (
    r"metric\s+tons?|metric\s+tonnes?|tons?|tonnes?|boxes|cases|cartons?|crates?|"
    r"pallets?|packages?|packs?|bags?|units?|parts?|pieces?|pcs?|items?|meters?|metres?|"
    r"m\b|km\b|feet|ft\b|yards?|kg\b|kilograms?|g\b|grams?|lbs?\b|pounds?|"
    r"liters?|litres?|l\b|gallons?|gal\b|rolls?|sheets?|pairs?|sets?|housings?\b"
)

_QUANTITY_P1 = re.compile(
    rf"(?<![\w.,])(?P<quantity>\d{{1,3}}(?:,\d{{3}})+|\d+(?:\.\d+)?)\s*(?P<unit>{_STD_UNITS})\b",
    re.IGNORECASE,
)

_QUANTITY_P2 = re.compile(
    r"(?<![\w.,])(?P<quantity>\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s+(?:[a-zA-Z-]+\s+)+(?P<unit>parts?|units?|pieces?|pcs?|items?|housings?|components?|brackets?)\b",
    re.IGNORECASE,
)


_QUANTITY_RFQ = re.compile(
    rf"\b(?:quantity|qty)\s*[:=]\s*(?P<quantity>\d{{1,3}}(?:,\d{{3}})+|\d+(?:\.\d+)?)\s*(?P<unit>{_STD_UNITS}|\w+)?\b",
    re.IGNORECASE,
)

_DEST_TRIGGER = re.compile(
    r"\b(?:deliver(?:y|ed|ing)?\s+(?:to|at|in)|ship(?:ped|ping|ment)?\s+to|destination\s*:|ship\s+to\s*:|"
    r"(?-i:to\s+(?=[A-Z])|in\s+(?=[A-Z])))"
    r"(?P<dest>(?:(?!\b(?:by|before|under|for|at|with|budget|target|net|due|total)\b)[^,.;\n])+"
    r"(?:,\s*(?:(?!\b(?:by|before|under|for|at|with|budget|target|net|due|total)\b)[^,.;\n])+)?)"
    r"(?=\s*(?:[,.;\n]|$|\b(?:by|before|under|for|at|with|budget|target|net|due|total)\b))",
    re.IGNORECASE,
)


_DATE_ISO = re.compile(r"\b(?P<date>20\d{2}-\d{2}-\d{2})\b")
_DATE_TEXT = re.compile(
    r"\b(?P<date>(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2},?\s+20\d{2})\b",
    re.IGNORECASE,
)
_DATE_TEXT_DMY = re.compile(
    r"\b(?P<date>\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?),?\s+20\d{2})\b",
    re.IGNORECASE,
)
_DATE_RELATIVE_NEXT_MONTH = re.compile(r"\bby\s+next\s+month\b", re.IGNORECASE)
_DATE_WITHIN_DAYS = re.compile(r"\bwithin\s+(?P<days>\d+)\s+days?\b", re.IGNORECASE)
_DATE_WITHIN_WEEKS = re.compile(r"\bwithin\s+(?P<weeks>\d+)\s+weeks?\b", re.IGNORECASE)

_PAYMENT_TERMS_RE = re.compile(
    r"\b(?:"
    r"(?P<net>Net\s*(?:10|15|30|45|60|90|120)(?:\s*days?)?)"
    r"|(?P<cia>Cash\s+in\s+Advance|CIA|100%\s+advance|prepayment)"
    r"|(?P<lc>Letter\s+of\s+Credit(?:\s*\(LC\))?|L/C|LC\b)"
    r"|(?P<split>\d{1,2}%\s*(?:advance|upfront)[,\s]+\d{1,2}%\s*(?:upon|on)\s+delivery)"
    r"|payment\s+terms?\s*[:=]\s*(?P<custom>[^,.;\n]+)"
    r"|(?P<wire>wire\s+transfer|bank\s+transfer|ESCROW)"
    r")\b",
    re.IGNORECASE,
)


def _resolve_country_code(text: str) -> str | None:
    lower = text.lower()
    for name, code in sorted(_COUNTRY_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", lower):
            return code
    for city, code in sorted(_CITY_COUNTRY_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if re.search(rf"\b{re.escape(city)}\b", lower):
            return code
    for prov, code in _US_CAN_PROVINCES.items():
        if re.search(rf"\b{prov}\b", text):
            return code
    for code in sorted(set(_COUNTRY_MAP.values())):
        if re.search(rf"\b{code}\b", text):
            return code
    return None


def _extract_delivery_date(text: str) -> date | None:
    iso_m = _DATE_ISO.search(text)
    if iso_m:
        try:
            return date.fromisoformat(iso_m.group("date"))
        except (ValueError, OverflowError):
            pass
    text_m = _DATE_TEXT.search(text)
    if text_m:
        raw = text_m.group("date").replace(",", "")
        for fmt in ("%B %d %Y", "%b %d %Y"):
            try:
                return datetime.strptime(raw, fmt).date()
            except (ValueError, OverflowError):
                pass
    dmy_m = _DATE_TEXT_DMY.search(text)
    if dmy_m:
        raw = dmy_m.group("date").replace(",", "")
        for fmt in ("%d %B %Y", "%d %b %Y"):
            try:
                return datetime.strptime(raw, fmt).date()
            except (ValueError, OverflowError):
                pass
    if _DATE_RELATIVE_NEXT_MONTH.search(text):
        try:
            today = date.today()
            year = today.year + (1 if today.month == 12 else 0)
            month = 1 if today.month == 12 else today.month + 1
            return date(year, month, 1)
        except (ValueError, OverflowError):
            pass
    within_m = _DATE_WITHIN_DAYS.search(text)
    if within_m:
        try:
            days = int(within_m.group("days"))
            return date.today() + timedelta(days=days)
        except (ValueError, OverflowError):
            pass
    weeks_m = _DATE_WITHIN_WEEKS.search(text)
    if weeks_m:
        try:
            weeks = int(weeks_m.group("weeks"))
            return date.today() + timedelta(weeks=weeks)
        except (ValueError, OverflowError):
            pass
    return None


def _extract_capabilities(text: str) -> list[str]:
    caps: list[str] = []
    lower = text.lower()
    for name, aliases in _KNOWN_CAPABILITIES:
        if any(re.search(rf"\b{re.escape(alias)}\b", lower) for alias in aliases):
            if name == "CNC Machining" and "precision CNC machining" in caps:
                continue
            caps.append(name)
    return caps


def _extract_payment_terms(text: str) -> str | None:
    m = _PAYMENT_TERMS_RE.search(text)
    if m:
        for g in ("net", "cia", "lc", "split", "custom", "wire"):
            val = m.group(g)
            if val:
                return val.strip()
    return None


def _extract_category(item: str | None, text: str) -> str | None:
    combined = f"{item or ''} {text}".lower()
    for cat, keywords in _CATEGORY_KEYWORDS:
        if any(re.search(rf"\b{re.escape(kw)}\b", combined) for kw in keywords):
            return cat
    return None


def _extract_item_description(text: str) -> str | None:
    m = re.search(
        r"\b(?:\d[\d,.]*)\s+[a-zA-Z]+\s+of\s+([a-zA-Z0-9\s-]+?)(?=\s+(?:delivered|to\b|in\b|by\b|under\b|for\b|at\b|with\b|budget\b|target\b|\$|\d|net\b|[.;,\n]|$))",
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()

    m = re.search(
        r"\b(?:\d[\d,.]*)\s+([a-zA-Z0-9\s-]+?\s+(?:parts?|units?|pieces?|pcs?|items?|housings?|components?|brackets?))\b",
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()

    m = re.search(
        r"\b(?:\d[\d,.]*)\s+(?:kg|kilograms?|tons?|tonnes?|lbs?|pounds?|meters?|boxes|cases|bags?)\s+([a-zA-Z0-9\s-]+?)(?=\s+(?:delivered|to\b|in\b|by\b|under\b|for\b|at\b|with\b|budget\b|target\b|\$|\d|net\b|[.;,\n]|$))",
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()

    m = re.search(
        r"\b(?:RFQ\s*:|order\s+of|buying|supply(?:ing)?|need|looking\s+for|seeking|require)\s+(?:supplier\s+for\s+)?(?:[a-zA-Z\s]+?\s+for\s+)?([a-zA-Z0-9\s-]+?)(?=\s+(?:delivered|to\b|in\b|by\b|under\b|for\b|at\b|with\b|budget\b|target\b|\$|\d|net\b|[.;,\n]|$))",
        text,
        re.IGNORECASE,
    )
    if m:
        item = m.group(1).strip()
        item = re.sub(r"^\d[\d,.]*\s+(?:[a-zA-Z]+\s+)?(?:of\s+)?", "", item)
        item = re.sub(r"^(?:units?|pcs?|pieces?|parts?|boxes|cases|meters?)\s+", "", item)
        if item:
            return item.strip()

    m = re.search(
        r"\b(?:item|product|specification|description)\s*[:=]\s*([a-zA-Z0-9\s-]+?)(?=[.;,\n]|$)",
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()

    return None


def extract_normalized_requirement(raw_text: str) -> NormalizedRequirement:
    """Extract standard trade attributes from natural language opening request text."""
    if not raw_text or not raw_text.strip():
        return NormalizedRequirement(raw_text=raw_text or "")

    text = raw_text.strip()

    quantity: Decimal | None = None
    unit: str | None = None

    q_match = _QUANTITY_RFQ.search(text)
    if not q_match:
        q_match = _QUANTITY_P1.search(text)
    if not q_match:
        q_match = _QUANTITY_P2.search(text)

    if q_match:
        try:
            quantity = Decimal(q_match.group("quantity").replace(",", ""))
            raw_unit = q_match.group("unit")
            if raw_unit:
                unit = re.sub(r"\s+", " ", raw_unit.strip()).lower()
        except (ArithmeticError, ValueError, decimal.DecimalException):
            quantity = None

    currency: str | None = None
    for curr_code, curr_re in _CURRENCY_PATTERNS:
        if curr_re.search(text):
            currency = curr_code
            break

    target_unit_price: Decimal | None = None
    budget: Decimal | None = None

    up_m = _UNIT_PRICE_RE.search(text)
    if up_m:
        val = up_m.group("price") or up_m.group("price_alt")
        if val:
            try:
                target_unit_price = Decimal(val.replace(",", ""))
                if currency is None:
                    currency = "USD"
            except (ArithmeticError, ValueError, decimal.DecimalException):
                target_unit_price = None

    b_m = _BUDGET_RE.search(text)
    if b_m:
        val = b_m.group("amount")
        if val:
            try:
                budget = Decimal(val.replace(",", ""))
                if currency is None:
                    currency = "USD"
            except (ArithmeticError, ValueError, decimal.DecimalException):
                budget = None

    if quantity and quantity > 0:
        if target_unit_price is not None and budget is None:
            try:
                budget = (target_unit_price * quantity)
            except (ArithmeticError, ValueError, decimal.DecimalException):
                pass
        elif budget is not None and target_unit_price is None:
            try:
                calc_price = (budget / quantity)
                target_unit_price = (
                    calc_price.quantize(Decimal("0.01"))
                    if (budget % quantity)
                    else calc_price
                )
            except (ArithmeticError, ValueError, decimal.DecimalException):
                pass

    destination_name: str | None = None
    destination_country_code: str | None = None

    dest_match = _DEST_TRIGGER.search(text)
    if dest_match:
        raw_dest = dest_match.group("dest").strip(" ,.;\t\n")
        raw_dest = re.sub(
            r"\s+(?:by|before|under|for|at|with|budget|target|net|due|total)\b.*$",
            "",
            raw_dest,
            flags=re.IGNORECASE,
        ).strip(" ,.")

        if raw_dest:
            destination_name = raw_dest
            destination_country_code = _resolve_country_code(raw_dest)

    if destination_country_code is None:
        destination_country_code = _resolve_country_code(text)
        if destination_country_code and destination_name is None:
            for name, code in _COUNTRY_MAP.items():
                if code == destination_country_code and re.search(rf"\b{re.escape(name)}\b", text, re.IGNORECASE):
                    destination_name = name.title() if len(name) > 2 else name.upper()
                    break

    target_delivery_date: date | None = _extract_delivery_date(text)
    capabilities_required: list[str] = _extract_capabilities(text)
    payment_terms: str | None = _extract_payment_terms(text)
    item_description: str | None = _extract_item_description(text)
    category: str | None = _extract_category(item_description, text)

    return NormalizedRequirement(
        item_description=item_description,
        category=category,
        quantity=quantity,
        unit=unit,
        target_unit_price=target_unit_price,
        budget=budget,
        currency=currency,
        destination_country_code=destination_country_code,
        destination_name=destination_name,
        target_delivery_date=target_delivery_date,
        capabilities_required=capabilities_required,
        payment_terms=payment_terms,
        raw_text=raw_text,
    )


@dataclass(frozen=True, slots=True)
class OpeningRequestNormalizationResult:
    """Outcome of opening request analysis, combining normalized fields and AI provenance."""

    requirements: NormalizedRequirement
    provenance: AIProvenance


class OpeningRequestNormalizationService:
    """Application service standardizing buyer opening requests and quotes."""

    def __init__(self, provider: AISuggestionProvider | None = None) -> None:
        self._provider = provider

    def normalize(self, text: str) -> OpeningRequestNormalizationResult:
        return normalize_opening_request(text, provider=self._provider)


def normalize_opening_request(
    text: str,
    provider: AISuggestionProvider | None = None,
    *,
    policy: AIRetryPolicy = AIRetryPolicy(),
    sleep: Callable[[float], None] = default_sleep,
) -> OpeningRequestNormalizationResult:
    """Normalize natural language opening request into a standardized requirement.

    If a provider is supplied and supports normalization, delegates to it with
    bounded retry on transient failures. If the provider fails or is unconfigured/offline,
    it falls back gracefully to offline extraction without raising unhandled errors.
    """
    if provider is None:
        try:
            req = extract_normalized_requirement(text)
        except Exception:
            req = NormalizedRequirement(raw_text=text)
        return OpeningRequestNormalizationResult(
            requirements=req,
            provenance=AIProvenance(provider="offline", mode="offline", context_scope="authorized"),
        )

    provenance = provider_provenance(provider)
    if not hasattr(provider, "normalize_opening_request"):
        try:
            req = extract_normalized_requirement(text)
        except Exception:
            req = NormalizedRequirement(raw_text=text)
        return OpeningRequestNormalizationResult(requirements=req, provenance=provenance)

    try:
        req = call_with_bounded_retry(
            lambda: provider.normalize_opening_request(text),  # type: ignore[attr-defined]
            policy,
            sleep=sleep,
        )
        return OpeningRequestNormalizationResult(
            requirements=req,
            provenance=provider_provenance(provider),
        )
    except AITransientError:
        fallback_fn = getattr(provider, "fallback_normalize_opening_request", None)
        if fallback_fn is not None:
            try:
                req = fallback_fn(text)
                return OpeningRequestNormalizationResult(
                    requirements=req,
                    provenance=provider_provenance(provider),
                )
            except Exception:
                pass
        try:
            req = extract_normalized_requirement(text)
        except Exception:
            req = NormalizedRequirement(raw_text=text)
        fallback_prov = replace(
            provenance,
            provider="offline",
            model=None,
            fallback_reason="transient_exhausted",
        )
        return OpeningRequestNormalizationResult(requirements=req, provenance=fallback_prov)
    except Exception:
        try:
            req = extract_normalized_requirement(text)
        except Exception:
            req = NormalizedRequirement(raw_text=text)
        fallback_prov = replace(
            provenance,
            provider="offline",
            model=None,
            fallback_reason="transient_exhausted" if provenance.fallback_reason is None else provenance.fallback_reason,
        )
        return OpeningRequestNormalizationResult(requirements=req, provenance=fallback_prov)

