"""Provider-independent AI suggestion boundary and bounded orchestration.

Business rules never import a provider SDK. Providers implement the small
``AISuggestionProvider`` port and translate their response into the versioned
S4-01 contracts; the use cases here compose the organization-scoped context from
S4-02 with a bounded, retry-limited call. Every result is an unreviewed
candidate: nothing here confirms a fact, approves terms, or starts a payment.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from time import sleep as default_sleep
from typing import Protocol, runtime_checkable
from uuid import UUID

from syncally.application.conversations import (
    AiContext,
    CommunicationRepository,
    select_ai_context,
)
from syncally.application.identity import ActorContext
from syncally.domain.ai.contracts import (
    AI_SCHEMA_VERSION,
    AIContractError,
    ExtractedFact,
    ProposedTerms,
    ScopedFactCandidate,
    ValidationIssue,
    ValidationResult,
    ValidationStatus,
    scope_extracted_facts,
)

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_BACKOFF_SECONDS = 0.5


class AIProviderError(Exception):
    """Base class for a failed AI provider call."""


class AITransientError(AIProviderError):
    """A retryable provider failure, such as a timeout or temporary outage."""


class AIPermanentError(AIProviderError):
    """A non-retryable provider failure, such as malformed provider output."""


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

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidates", tuple(self.candidates))
        if self.result.status is not ValidationStatus.VALID and self.candidates:
            raise ValueError("an invalid extraction result must not carry candidates")


@dataclass(frozen=True, slots=True)
class ProposalDraftResult:
    """A validated proposal outcome; a rejected draft carries no proposal."""

    result: ValidationResult
    proposal: ProposedTerms | None

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
    last_error: AITransientError | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return operation()
        except AITransientError as error:
            last_error = error
            if attempt < policy.max_attempts:
                sleep(policy.backoff_seconds)
    raise AITransientError(
        f"AI provider was unavailable after {policy.max_attempts} attempts"
    ) from last_error


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
    request = FactExtractionRequest(context=context)

    try:
        facts = call_with_bounded_retry(
            lambda: provider.extract_facts(request, timeout_seconds=policy.timeout_seconds),
            policy,
            sleep=sleep,
        )
        candidates = scope_extracted_facts(
            facts,
            authorized_messages={message.id: message.body for message in context.messages},
            owner_organization_id=organization_id,
        )
    except AIPermanentError as error:
        return _rejected_fact_result("AI_OUTPUT_INVALID", str(error))
    except AIContractError as error:
        return _rejected_fact_result("AI_OUTPUT_UNGROUNDED", str(error))
    return FactExtractionResult(ValidationResult.valid(), candidates)


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
    request = ProposalDraftRequest(context=context)

    try:
        proposal = call_with_bounded_retry(
            lambda: provider.draft_proposal(request, timeout_seconds=policy.timeout_seconds),
            policy,
            sleep=sleep,
        )
    except AIPermanentError as error:
        issue = ValidationIssue(
            schema_version=AI_SCHEMA_VERSION,
            code="AI_OUTPUT_INVALID",
            path="proposal",
            message=str(error),
        )
        return ProposalDraftResult(ValidationResult.invalid((issue,)), None)
    return ProposalDraftResult(ValidationResult.valid(), proposal)


def _rejected_fact_result(code: str, message: str) -> FactExtractionResult:
    issue = ValidationIssue(
        schema_version=AI_SCHEMA_VERSION,
        code=code,
        path="facts",
        message=message,
    )
    return FactExtractionResult(ValidationResult.invalid((issue,)), ())
