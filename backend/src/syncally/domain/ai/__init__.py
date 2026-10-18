"""Versioned, provider-independent contracts for AI suggestions."""

from syncally.domain.ai.contracts import (
    AI_SCHEMA_VERSION,
    AIContractError,
    AIValidationClaim,
    ExtractedFact,
    FactField,
    ProposedTerms,
    ScopedFactCandidate,
    SourceReference,
    ValidationIssue,
    ValidationResult,
    scope_extracted_facts,
)

__all__ = [
    "AI_SCHEMA_VERSION",
    "AIContractError",
    "AIValidationClaim",
    "ExtractedFact",
    "FactField",
    "ProposedTerms",
    "ScopedFactCandidate",
    "SourceReference",
    "ValidationIssue",
    "ValidationResult",
    "scope_extracted_facts",
]
