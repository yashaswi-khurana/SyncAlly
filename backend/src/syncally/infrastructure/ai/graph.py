"""Small LangGraph branch for proposal readiness and drafting."""

from typing import TypedDict

from syncally.application.ai import (
    AI_SCHEMA_VERSION,
    AISuggestionProvider,
    ProposalDraftResult,
    ValidationIssue,
    ValidationResult,
    draft_proposal_from_context,
    fact_suggestion_guidance,
    missing_trade_fields,
    provider_provenance,
)
from syncally.application.conversations import AiContext


class _ProposalState(TypedDict, total=False):
    context: AiContext
    provider: AISuggestionProvider
    missing_fields: list[str]
    result: ProposalDraftResult


def _check_readiness(state: _ProposalState) -> dict[str, object]:
    context = state["context"]
    # A delivery date is needed for complete trade terms, but a draft may leave it blank.
    missing = [] if context.messages else [
        field for field in missing_trade_fields(context.constraints) if field != "delivery_date"
    ]
    if not missing:
        return {"missing_fields": []}
    issue = ValidationIssue(
        schema_version=AI_SCHEMA_VERSION,
        code="AI_REQUIRED_FACTS_MISSING",
        path="proposal",
        message=fact_suggestion_guidance(missing),
    )
    result = ProposalDraftResult(
        ValidationResult.invalid((issue,), needs_clarification=True),
        None,
        provider_provenance(state["provider"]),
    )
    return {"missing_fields": missing, "result": result}


def _route_proposal(state: _ProposalState) -> str:
    return "draft" if not state["missing_fields"] else "clarification"


def _draft(state: _ProposalState) -> dict[str, ProposalDraftResult]:
    return {
        "result": draft_proposal_from_context(state["context"], state["provider"]),
    }


try:
    from langgraph.graph import END, START, StateGraph

    _proposal_graph = (
        StateGraph(_ProposalState)
        .add_node("check_readiness", _check_readiness)
        .add_node("draft", _draft)
        .add_edge(START, "check_readiness")
        .add_conditional_edges(
            "check_readiness",
            _route_proposal,
            {"draft": "draft", "clarification": END},
        )
        .add_edge("draft", END)
        .compile()
    )
except ImportError:
    _proposal_graph = None


def draft_proposal_with_graph(
    context: AiContext,
    provider: AISuggestionProvider,
) -> ProposalDraftResult:
    """Route incomplete context to guidance; call the provider only when ready."""
    if _proposal_graph is not None:
        state = _proposal_graph.invoke({"context": context, "provider": provider})
        return state["result"]
    readiness = _check_readiness({"context": context, "provider": provider})
    if readiness.get("missing_fields"):
        return readiness["result"]  # type: ignore[return-value]
    return draft_proposal_from_context(context, provider)
