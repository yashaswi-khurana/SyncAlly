"""FastAPI router for Buyer Sourcing Agent endpoints.

Exposes REST APIs for:
- POST /sourcing/interpret: NLP & structured requirements extraction
- GET /sourcing/listings: Bundled marketplace candidate listings retrieval
- POST /sourcing/compare: 5-dimension multi-candidate ranking and matrix evaluation
- POST /sourcing/gap-analysis: Deep discrepancy taxonomy and commercial delta detection
- POST /sourcing/draft-inquiry: Targeted seller inquiry letter generation
- POST /sourcing/evaluate: End-to-end evaluation pipeline with deal room handoff support
"""

from __future__ import annotations

from decimal import InvalidOperation
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
from syncally.application.identity import ActorContext
from syncally.application.sourcing.service import SourcingService
from syncally.domain.sourcing.contracts import (
    BuyerRequirements,
    CommercialGap,
    ComparisonResult,
    InquiryDraft,
    MarketplaceListingDetail,
)
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import Organization, User

router = APIRouter()


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


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


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
) -> dict[str, Any]:
    """Parse natural language sourcing prompt and merge with structured overrides."""
    try:
        requirements, parsed_fields = SourcingService.interpret_requirements(
            prompt=payload.prompt,
            structured_overrides=payload.structured_overrides,
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
        "requirements": requirements,
        "parsed_fields": parsed_fields,
    }


@router.get("/listings", response_model=ListingsResponse)
def get_listings(
    category: str | None = Query(default=None),
    completeness: str | None = Query(default=None),
    q: str | None = Query(default=None),
    _actor: ActorContext = Depends(get_current_actor),
) -> dict[str, Any]:
    """Query bundled candidate marketplace listings with optional category and completeness filters."""
    listings = SourcingService.get_listings(
        category=category,
        completeness=completeness,
        query=q,
    )
    return {
        "listings": listings,
        "total": len(listings),
    }


@router.post("/compare", response_model=CompareResponse)
def compare_listings(
    payload: CompareRequest,
    _actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Evaluate candidate listings against buyer requirements across 5 weighted dimensions."""
    try:
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
    return {"results": [_serialize_comparison_result(r) for r in results]}


@router.post("/gap-analysis", response_model=GapAnalysisResponse)
def gap_analysis(
    payload: GapAnalysisRequest,
    _actor: ActorContext = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Perform detailed gap detection between buyer requirements and a specific listing."""
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
) -> InquiryDraft:
    """Generate professional B2B inquiry letter proposing targeted compromises for all detected gaps."""
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
) -> dict[str, Any]:
    """Execute complete end-to-end buyer sourcing pipeline: parse, compare, analyze gaps, and draft inquiries."""
    buyer_org_id = payload.buyer_organization_id or (
        str(next(iter(actor.organization_ids))) if actor.organization_ids else None
    )
    buyer_org_name, buyer_contact_name = _resolve_buyer_names(actor, db, buyer_org_id)

    try:
        report = SourcingService.evaluate(
            prompt=payload.prompt,
            requirements=payload.requirements,
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
    }
