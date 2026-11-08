"""Sourcing application service.

Orchestrates buyer requirement interpretation, candidate listing comparison,
gap taxonomy analysis, and seller inquiry generation.
Operates 100% locally with zero external network or LLM dependencies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from syncally.application.sourcing.comparison_engine import ComparisonEngine
from syncally.application.sourcing.gap_analyzer import GapAnalyzer
from syncally.application.sourcing.inquiry_drafter import InquiryDrafter
from syncally.application.sourcing.interpreter import RequirementInterpreter
from syncally.domain.sourcing.contracts import (
    BuyerRequirements,
    CommercialGap,
    ComparisonResult,
    GapSeverity,
    InquiryDraft,
    MarketplaceListingDetail,
    SourcingEvaluationReport,
)
from syncally.infrastructure.sourcing.bundled_dataset import (
    get_bundled_listing_by_id,
    get_bundled_listings,
)


class SourcingService:
    """Core orchestration service for buyer sourcing workflows."""

    @classmethod
    def interpret_requirements(
        cls,
        prompt: str | None = None,
        structured_overrides: dict[str, Any] | None = None,
    ) -> tuple[BuyerRequirements, list[str]]:
        """Interpret natural language prompt and compose with structured overrides."""
        return RequirementInterpreter.interpret(prompt, structured_overrides)

    @classmethod
    def get_listings(
        cls,
        category: str | None = None,
        completeness: str | None = None,
        query: str | None = None,
    ) -> list[MarketplaceListingDetail]:
        """Query bundled candidate marketplace listings."""
        return get_bundled_listings(category=category, completeness=completeness, query=query)

    @classmethod
    def get_listing_by_id(
        cls, listing_id: str, db: Session | None = None
    ) -> MarketplaceListingDetail | None:
        """Retrieve a specific marketplace listing by its unique identifier."""
        bundled = get_bundled_listing_by_id(listing_id)
        if bundled is not None:
            return bundled
        if db is not None:
            try:
                from uuid import UUID

                from syncally.infrastructure.models import MarketplaceListing, Organization

                listing_uuid = UUID(str(listing_id))
                listing = db.get(MarketplaceListing, listing_uuid)
                if listing is not None:
                    org = db.get(Organization, listing.organization_id)
                    org_name = org.legal_name if org else "Marketplace Supplier"
                    country_code = org.country_code if org else "US"
                    return MarketplaceListingDetail(
                        id=str(listing.id),
                        organization_id=str(listing.organization_id),
                        organization_name=org_name,
                        country_code=country_code,
                        title=listing.title,
                        category=listing.category,
                        description=listing.description or "",
                        available_quantity=listing.available_quantity,
                        unit=listing.unit,
                        unit_price=listing.unit_price,
                        currency=listing.currency,
                        completeness_tier="FULL_COMPLETE",
                    )
            except Exception:
                pass
        return None

    @classmethod
    def compare_listings(
        cls,
        requirements: BuyerRequirements,
        listing_ids: list[str] | None = None,
        db: Session | None = None,
    ) -> list[ComparisonResult]:
        """Evaluate candidate marketplace listings against buyer requirements."""
        if listing_ids:
            clean_ids = {lid.strip().lower() for lid in listing_ids}
            candidates = [
                item for item in get_bundled_listings()
                if item.id.lower() in clean_ids
            ]
            if len(candidates) < len(clean_ids) and db is not None:
                for lid in clean_ids:
                    if not any(c.id.lower() == lid for c in candidates):
                        extra = cls.get_listing_by_id(lid, db=db)
                        if extra:
                            candidates.append(extra)
        else:
            candidates = get_bundled_listings()

        return ComparisonEngine.compare_multiple(requirements, candidates)

    @classmethod
    def analyze_gaps(
        cls,
        requirements: BuyerRequirements,
        listing_id: str,
        db: Session | None = None,
    ) -> tuple[MarketplaceListingDetail, list[CommercialGap], str]:
        """Analyze gaps between buyer requirements and a candidate listing.

        Returns (listing, gaps, overall_severity).
        Raises ValueError if listing is not found.
        """
        listing = cls.get_listing_by_id(listing_id, db=db)
        if not listing:
            raise ValueError(f"Marketplace listing not found: {listing_id}")

        gaps = GapAnalyzer.detect_gaps(requirements, listing)

        if any(g.severity == GapSeverity.CRITICAL for g in gaps):
            overall_severity = "CRITICAL"
        elif any(g.severity == GapSeverity.MODERATE for g in gaps):
            overall_severity = "MODERATE"
        elif any(g.severity == GapSeverity.LOW for g in gaps):
            overall_severity = "LOW"
        else:
            overall_severity = "NONE"

        return listing, gaps, overall_severity

    @classmethod
    def draft_inquiry(
        cls,
        requirements: BuyerRequirements,
        listing_id: str,
        buyer_organization_id: str | None = None,
        buyer_org_name: str | None = None,
        buyer_contact_name: str | None = None,
        db: Session | None = None,
    ) -> InquiryDraft:
        """Generate targeted seller inquiry letter for a specific listing."""
        listing = cls.get_listing_by_id(listing_id, db=db)
        if not listing:
            raise ValueError(f"Marketplace listing not found: {listing_id}")

        gaps = GapAnalyzer.detect_gaps(requirements, listing)
        return InquiryDrafter.draft_inquiry(
            requirements=requirements,
            listing=listing,
            gaps=gaps,
            buyer_org_name=buyer_org_name,
            buyer_contact_name=buyer_contact_name,
        )

    @classmethod
    def evaluate(
        cls,
        prompt: str | None = None,
        requirements: BuyerRequirements | None = None,
        listing_ids: list[str] | None = None,
        buyer_organization_id: str | None = None,
        buyer_org_name: str | None = None,
        buyer_contact_name: str | None = None,
        db: Session | None = None,
    ) -> SourcingEvaluationReport:
        """Run complete end-to-end sourcing evaluation.

        Parses requirements (if prompt provided), scores candidate listings,
        detects gaps, and generates inquiry drafts for evaluated listings.
        """
        if requirements is None:
            requirements, _ = cls.interpret_requirements(prompt)

        comparisons = cls.compare_listings(requirements, listing_ids=listing_ids, db=db)

        inquiries: dict[str, InquiryDraft] = {}
        for comp in comparisons:
            listing = cls.get_listing_by_id(comp.listing_id, db=db)
            if listing:
                draft = InquiryDrafter.draft_inquiry(
                    requirements=requirements,
                    listing=listing,
                    gaps=comp.detected_gaps,
                    buyer_org_name=buyer_org_name,
                    buyer_contact_name=buyer_contact_name,
                )
                inquiries[comp.listing_id] = draft

        return SourcingEvaluationReport(
            requirements=requirements,
            comparisons=comparisons,
            inquiries=inquiries,
            total_listings_evaluated=len(comparisons),
        )
