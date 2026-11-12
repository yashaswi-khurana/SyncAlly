"""FastAPI router for Buyer Sourcing Agent endpoints.

Exposes REST APIs for:
- POST /sourcing/interpret: configured-provider NLP or explicit structured-control validation
- GET /sourcing/listings: unavailable; browse /marketplace/listings instead
- POST /sourcing/compare, /gap-analysis, /draft-inquiry, /evaluate: unavailable
  until persisted offers support reliable scoring and inquiry drafting
"""

from __future__ import annotations

import logging
from decimal import InvalidOperation
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
from syncally.application.ai import (
    AIConfigurationError,
    AIPermanentError,
    AIProviderAccessError,
    AITransientError,
)
from syncally.application.identity import ActorContext
from syncally.application.sourcing.service import SourcingService
from syncally.config import settings
from syncally.domain.sourcing.contracts import (
    BuyerRequirements,
    CommercialGap,
    ComparisonResult,
    InquiryDraft,
    MarketplaceListingDetail,
)
from syncally.infrastructure.ai.selection import ConfiguredAIProvider
from syncally.infrastructure.ai.sourcing import (
    missing_required_fields,
    validate_structured_overrides,
)
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import Organization, User
from syncally.operations import Operation, log_operation

router = APIRouter()
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Request & Response Schemas
# -----------------------------------------------------------------------------


class InterpretRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    prompt: str | None = Field(default=None, max_length=8000)
    structured_overrides: dict[str, Any] | None = None


class InterpretResponse(BaseModel):
    requirements: BuyerRequirements
    parsed_fields: list[str]
    ai_provider: str
    ai_model: str | None = None
    fallback_reason: str | None = None


class ListingsResponse(BaseModel):
    listings: list[MarketplaceListingDetail]
    total: int


class CompareRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    requirements: BuyerRequirements
    listing_ids: list[str] | None = None


class CompareResponse(BaseModel):
    results: list[dict[str, Any]]


class GapAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    requirements: BuyerRequirements
    listing_id: str


class GapAnalysisResponse(BaseModel):
    listing: MarketplaceListingDetail
    gaps: list[CommercialGap]
    overall_severity: str


class DraftInquiryRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    requirements: BuyerRequirements
    listing_id: str
    buyer_organization_id: str | None = None


class EvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    prompt: str | None = Field(default=None, max_length=8000)
    requirements: BuyerRequirements | None = None
    listing_ids: list[str] | None = None
    buyer_organization_id: str | None = None


class EvaluateResponse(BaseModel):
    requirements: BuyerRequirements
    comparisons: list[dict[str, Any]]
    inquiries: dict[str, InquiryDraft]
    total_listings_evaluated: int
    ai_provider: str | None = None
    ai_model: str | None = None
    fallback_reason: str | None = None


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _interpret_structured(
    overrides: dict[str, Any] | None,
) -> tuple[BuyerRequirements, list[str]]:
    data = overrides or {}
    validate_structured_overrides(data)
    missing = missing_required_fields(data)
    if missing:
        raise ValueError("Please enter or confirm: " + ", ".join(missing) + ".")
    try:
        requirements = BuyerRequirements.model_validate(data)
    except ValidationError as err:
        details = "; ".join(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in err.errors()
        )
        raise ValueError(f"Please correct the sourcing requirements: {details}") from err
    return requirements, list(data.keys())


def _require_explicit_commercial_controls(requirements: BuyerRequirements) -> None:
    missing: list[str] = []
    if "currency" not in requirements.pricing.model_fields_set:
        missing.append("price currency")
    for field, label in (
        ("min_warranty_months", "minimum warranty in months"),
        ("inspection_requirement", "inspection requirement"),
    ):
        if field not in requirements.commercial_terms.model_fields_set:
            missing.append(label)
    if missing:
        raise ValueError(
            "Please explicitly specify or confirm: " + ", ".join(missing) + "."
        )


def _interpret_natural(
    prompt: str,
    structured_overrides: dict[str, Any] | None,
) -> tuple[BuyerRequirements, list[str], ConfiguredAIProvider]:
    try:
        provider = ConfiguredAIProvider(settings)
    except AIConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sourcing AI is not configured. Configure an enabled AI provider.",
        ) from exc
    try:
        requirements, parsed_fields = provider.interpret_sourcing_requirements(
            prompt,
            structured_overrides,
        )
        return requirements, parsed_fields, provider
    except AIConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sourcing AI is not configured. Configure an enabled AI provider.",
        ) from exc
    except AITransientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The configured sourcing AI is temporarily unavailable. Please retry.",
        ) from exc
    except AIProviderAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The configured sourcing AI key is not authorized. Check its NVIDIA Public API Endpoints and model access.",
        ) from exc
    except AIPermanentError as exc:
        log_operation(
            logger,
            Operation.AI_PROVIDER_FAILURE,
            failure_kind="PERMANENT",
            error_code=exc.diagnostic_code or "AI_SOURCING_OUTPUT_REJECTED",
            sourcing_field=exc.diagnostic_field,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The configured sourcing AI returned invalid output. Please retry or use structured controls.",
        ) from exc
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


def _serialize_comparison_result(result: ComparisonResult) -> dict[str, Any]:
    """Serialize ComparisonResult with enriched score fields and single-letter match_tier."""
    data = result.model_dump(mode="json")
    tier_val = result.tier.value if hasattr(result.tier, "value") else str(result.tier)
    tier_code = tier_val.replace("Tier ", "").strip()
    data["match_tier"] = tier_code
    data["spec_score"] = result.score_breakdown.specifications
    data["price_score"] = result.score_breakdown.pricing
    data["quantity_score"] = result.score_breakdown.quantity_and_moq
    data["lead_time_score"] = result.score_breakdown.lead_time
    data["terms_score"] = result.score_breakdown.commercial_terms

    matrix: list[dict[str, Any]] = []
    for ac in result.attribute_comparisons:
        row = ac.model_dump(mode="json")
        row["attribute"] = ac.field_name
        matrix.append(row)

    data["attribute_matrix"] = matrix
    return data


def _resolve_buyer_names(
    actor: ActorContext,
    db: Session,
    buyer_org_id: str | None,
) -> tuple[str | None, str | None]:
    """Resolve buyer legal organization name and contact name from database."""
    buyer_org_name: str | None = None
    buyer_contact_name: str | None = None

    if buyer_org_id:
        try:
            org = db.get(Organization, UUID(str(buyer_org_id)))
            if org:
                buyer_org_name = org.legal_name
        except (ValueError, TypeError):
            pass

    if actor.user_id:
        try:
            user = db.get(User, actor.user_id)
            if user:
                buyer_contact_name = user.display_name
        except Exception:
            pass

    return buyer_org_name, buyer_contact_name


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@router.post("/interpret", response_model=InterpretResponse)
def interpret_requirements(
    payload: InterpretRequest,
    _actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Interpret natural language with the configured provider or validate explicit controls."""
    provider: ConfiguredAIProvider | None = None
    if payload.prompt and payload.prompt.strip():
        db.rollback()
        requirements, parsed_fields, provider = _interpret_natural(
            payload.prompt,
            payload.structured_overrides,
        )
    else:
        try:
            requirements, parsed_fields = _interpret_structured(payload.structured_overrides)
        except (ValueError, TypeError, InvalidOperation) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
    return {
        "requirements": requirements,
        "parsed_fields": parsed_fields,
        "ai_provider": provider.provenance.provider if provider else "structured",
        "ai_model": provider.provenance.model if provider else None,
        "fallback_reason": provider.provenance.fallback_reason if provider else None,
    }


@router.get("/listings", response_model=ListingsResponse)
def get_listings(
    category: str | None = Query(default=None),
    completeness: str | None = Query(default=None),
    q: str | None = Query(default=None),
    _actor: ActorContext = Depends(get_current_actor),
) -> dict[str, Any]:
    """Do not misrepresent unavailable listing details or a page count as a total."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "The sourcing catalogue is unavailable because its response cannot accurately "
            "represent marketplace data. Browse active offers in Marketplace or use "
            "GET /marketplace/listings instead."
        ),
    )


def _scoring_unavailable() -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Sourcing comparison and inquiry drafting are unavailable: marketplace listings "
            "do not contain the commercial and technical details required for reliable scoring. "
            "Browse active offers in Marketplace and confirm terms directly."
        ),
    )


@router.post("/compare", response_model=CompareResponse)
def compare_listings(
    payload: CompareRequest,
    _actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
    _availability: None = Depends(_scoring_unavailable),
) -> dict[str, Any]:
    """Evaluate candidate listings against buyer requirements across 5 weighted dimensions."""
    try:
        _require_explicit_commercial_controls(payload.requirements)
        results = SourcingService.compare_listings(
            requirements=payload.requirements,
            listing_ids=payload.listing_ids,
            db=db,
        )
    except ValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=jsonable_encoder(err.errors()),
        ) from err
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return {"results": [_serialize_comparison_result(r) for r in results]}


@router.post("/gap-analysis", response_model=GapAnalysisResponse)
def gap_analysis(
    payload: GapAnalysisRequest,
    _actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
    _availability: None = Depends(_scoring_unavailable),
) -> dict[str, Any]:
    """Perform detailed gap detection between buyer requirements and a specific listing."""
    try:
        _require_explicit_commercial_controls(payload.requirements)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    try:
        listing, gaps, overall_severity = SourcingService.analyze_gaps(
            requirements=payload.requirements,
            listing_id=payload.listing_id,
            db=db,
        )
    except ValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=jsonable_encoder(err.errors()),
        ) from err
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return {
        "listing": listing,
        "gaps": gaps,
        "overall_severity": overall_severity,
    }


@router.post("/draft-inquiry", response_model=InquiryDraft)
def draft_inquiry(
    payload: DraftInquiryRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
    _availability: None = Depends(_scoring_unavailable),
) -> InquiryDraft:
    """Generate professional B2B inquiry letter proposing targeted compromises for all detected gaps."""
    try:
        _require_explicit_commercial_controls(payload.requirements)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    buyer_org_id = payload.buyer_organization_id or (
        str(next(iter(actor.organization_ids))) if actor.organization_ids else None
    )
    buyer_org_name, buyer_contact_name = _resolve_buyer_names(actor, db, buyer_org_id)

    try:
        return SourcingService.draft_inquiry(
            requirements=payload.requirements,
            listing_id=payload.listing_id,
            buyer_organization_id=buyer_org_id,
            buyer_org_name=buyer_org_name,
            buyer_contact_name=buyer_contact_name,
            db=db,
        )
    except ValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=jsonable_encoder(err.errors()),
        ) from err
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate_sourcing(
    payload: EvaluateRequest,
    actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
    _availability: None = Depends(_scoring_unavailable),
) -> dict[str, Any]:
    """Rank the catalogue with explicit requirements, interpreting a prompt through configured AI."""
    buyer_org_id = payload.buyer_organization_id or (
        str(next(iter(actor.organization_ids))) if actor.organization_ids else None
    )
    buyer_org_name, buyer_contact_name = _resolve_buyer_names(actor, db, buyer_org_id)

    requirements = payload.requirements
    provider: ConfiguredAIProvider | None = None
    if requirements is None:
        if not payload.prompt or not payload.prompt.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Provide buyer requirements or a sourcing prompt.",
            )
        db.rollback()
        requirements, _, provider = _interpret_natural(payload.prompt, None)

    try:
        _require_explicit_commercial_controls(requirements)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    try:
        report = SourcingService.evaluate(
            requirements=requirements,
            listing_ids=payload.listing_ids,
            buyer_organization_id=buyer_org_id,
            buyer_org_name=buyer_org_name,
            buyer_contact_name=buyer_contact_name,
            db=db,
        )
    except ValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=jsonable_encoder(err.errors()),
        ) from err
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return {
        "requirements": report.requirements,
        "comparisons": [_serialize_comparison_result(c) for c in report.comparisons],
        "inquiries": report.inquiries,
        "total_listings_evaluated": report.total_listings_evaluated,
        "ai_provider": provider.provenance.provider if provider else None,
        "ai_model": provider.provenance.model if provider else None,
        "fallback_reason": provider.provenance.fallback_reason if provider else None,
    }
