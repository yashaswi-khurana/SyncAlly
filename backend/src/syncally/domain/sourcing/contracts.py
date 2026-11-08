"""Domain contracts for buyer sourcing requirements, listings, comparisons, gaps, and inquiries."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Incoterm(StrEnum):
    EXW = "EXW"  # Ex Works
    FCA = "FCA"  # Free Carrier
    CPT = "CPT"  # Carriage Paid To
    CIP = "CIP"  # Carriage and Insurance Paid To
    DAP = "DAP"  # Delivered at Place
    DPU = "DPU"  # Delivered at Place Unloaded
    DDP = "DDP"  # Delivered Duty Paid
    FAS = "FAS"  # Free Alongside Ship
    FOB = "FOB"  # Free On Board
    CFR = "CFR"  # Cost and Freight
    CIF = "CIF"  # Cost, Insurance and Freight


class PaymentMethodPreference(StrEnum):
    NET_30 = "NET_30"
    NET_60 = "NET_60"
    ESCROW = "ESCROW"
    LC = "LC"
    SPLIT_30_70 = "30_70_SPLIT"
    SELLER_INVOICE = "seller_invoice"


class InspectionPreference(StrEnum):
    PRE_SHIPMENT_THIRD_PARTY = "PRE_SHIPMENT_THIRD_PARTY"
    FACTORY_MILL_CERTIFICATE = "FACTORY_MILL_CERTIFICATE"
    BUYER_RECEIVING_INSPECTION = "BUYER_RECEIVING_INSPECTION"
    NONE = "NONE"


class GapCategory(StrEnum):
    MISSING = "MISSING"
    AMBIGUOUS = "AMBIGUOUS"
    NON_COMPLIANT = "NON_COMPLIANT"


class GapSeverity(StrEnum):
    CRITICAL = "CRITICAL"
    MODERATE = "MODERATE"
    LOW = "LOW"


class ComparisonStatus(StrEnum):
    MATCH = "MATCH"
    ACCEPTABLE_VARIANCE = "ACCEPTABLE_VARIANCE"
    GAP = "GAP"


class MatchTier(StrEnum):
    TIER_A = "Tier A"  # 90-100% Ideal Match
    TIER_B = "Tier B"  # 75-89% Strong Candidate
    TIER_C = "Tier C"  # 50-74% Conditional Candidate
    TIER_D = "Tier D"  # < 50% Substantial Mismatch / Disqualified


class TechnicalSpecification(BaseModel):
    model_config = ConfigDict(frozen=True)

    materials: list[str] = Field(default_factory=list, description="List of materials, alloys, or fabrics")
    tolerances: str | None = Field(default=None, description="Tolerance requirements e.g. +/- 0.05mm")
    certifications: list[str] = Field(default_factory=list, description="Regulatory and quality certifications")
    standards: list[str] = Field(default_factory=list, description="Industry or engineering standards e.g. DIN 933")
    quality_grade: str | None = Field(default=None, description="Material grade or specification grade")
    notes: str | None = Field(default=None, max_length=1000)


class PricingConstraint(BaseModel):
    model_config = ConfigDict(frozen=True)

    target_unit_price: Decimal | None = Field(default=None, ge=0)
    max_unit_price: Decimal | None = Field(default=None, ge=0)
    max_total_budget: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class QuantityRequirement(BaseModel):
    model_config = ConfigDict(frozen=True)

    target_quantity: Decimal = Field(gt=0)
    min_acceptable_quantity: Decimal | None = Field(default=None, gt=0)
    unit: str = Field(min_length=1, max_length=32)
    packaging_preference: str | None = Field(default=None, max_length=200)


class DeliveryConstraint(BaseModel):
    model_config = ConfigDict(frozen=True)

    destination_country_code: str = Field(min_length=2, max_length=2)
    destination_port_or_city: str | None = Field(default=None, max_length=120)
    required_delivery_date: date | None = None
    max_lead_time_days: int | None = Field(default=None, gt=0)


class CommercialTermsRequirement(BaseModel):
    model_config = ConfigDict(frozen=True)

    preferred_incoterm: Incoterm | str | None = None
    acceptable_incoterms: list[Incoterm | str] = Field(default_factory=list)
    preferred_payment_term: PaymentMethodPreference | str | None = None
    min_warranty_months: int = Field(default=12, ge=0)
    inspection_requirement: InspectionPreference | str = InspectionPreference.FACTORY_MILL_CERTIFICATE


class BuyerRequirements(BaseModel):
    """Complete canonical buyer sourcing requirement specification."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=4000)
    technical_specs: TechnicalSpecification = Field(default_factory=TechnicalSpecification)
    pricing: PricingConstraint = Field(default_factory=PricingConstraint)
    quantity: QuantityRequirement
    delivery: DeliveryConstraint
    commercial_terms: CommercialTermsRequirement = Field(default_factory=CommercialTermsRequirement)
    raw_prompt: str | None = Field(default=None, max_length=8000)


class MarketplaceListingDetail(BaseModel):
    """Detailed marketplace listing for candidate comparison and gap detection."""

    model_config = ConfigDict(frozen=True)

    id: str
    organization_id: str
    organization_name: str
    country_code: str = Field(min_length=2, max_length=2)
    title: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=4000)
    available_quantity: Decimal = Field(ge=0)
    moq: Decimal | None = Field(default=None, ge=0)
    unit: str = Field(min_length=1, max_length=32)
    unit_price: Decimal = Field(ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    lead_time_days: int | None = Field(default=None, ge=0)
    incoterms: list[Incoterm | str] = Field(default_factory=list)
    payment_terms: str | None = None
    technical_specs: TechnicalSpecification = Field(default_factory=TechnicalSpecification)
    warranty_months: int | None = Field(default=None, ge=0)
    warranty_description: str | None = None
    inspection_terms: str | None = None
    completeness_tier: str = "FULL_COMPLETE"


class CommercialGap(BaseModel):
    """A classified commercial, technical, or delivery discrepancy between requirement and offering."""

    model_config = ConfigDict(frozen=True)

    gap_id: str
    field_name: str
    category: GapCategory
    severity: GapSeverity
    buyer_requirement_value: str
    seller_offered_value: str | None = None
    explanation: str
    suggested_action: str
    negotiation_priority: int = 1  # 1 = Highest


class AttributeComparison(BaseModel):
    """Attribute-by-attribute evaluation line item for side-by-side matrix view."""

    model_config = ConfigDict(frozen=True)

    field_name: str
    display_name: str
    buyer_value: str
    seller_value: str | None = None
    variance: str
    status: ComparisonStatus
    gap_category: GapCategory | None = None
    explanation: str | None = None


class ScoreBreakdown(BaseModel):
    """Sub-scores across the 5 evaluation dimensions and overall composite score."""

    model_config = ConfigDict(frozen=True)

    specifications: float = 0.0  # 0 to 100
    pricing: float = 0.0  # 0 to 100
    quantity_and_moq: float = 0.0  # 0 to 100
    lead_time: float = 0.0  # 0 to 100
    commercial_terms: float = 0.0  # 0 to 100
    composite: float = 0.0  # 0 to 100


class ComparisonResult(BaseModel):
    """Full evaluation of a candidate listing against buyer requirements."""

    model_config = ConfigDict(frozen=True)

    listing_id: str
    listing_title: str
    seller_organization_id: str
    seller_organization_name: str
    country_code: str
    unit_price: Decimal
    currency: str
    available_quantity: Decimal
    moq: Decimal | None
    unit: str
    lead_time_days: int | None
    composite_score: float
    tier: MatchTier
    score_breakdown: ScoreBreakdown
    attribute_comparisons: list[AttributeComparison] = Field(default_factory=list)
    detected_gaps: list[CommercialGap] = Field(default_factory=list)
    is_disqualified: bool = False
    disqualification_reasons: list[str] = Field(default_factory=list)


class InquiryDraft(BaseModel):
    """Drafted B2B inquiry letter targeting identified gaps with proposed compromises."""

    model_config = ConfigDict(frozen=True)

    listing_id: str
    seller_organization_id: str
    seller_organization_name: str
    subject: str
    body: str
    gaps_addressed: list[str] = Field(default_factory=list)
    proposed_terms: dict[str, Any] = Field(default_factory=dict)


class SourcingEvaluationReport(BaseModel):
    """Comprehensive sourcing report covering requirements, ranked comparisons, and inquiry drafts."""

    model_config = ConfigDict(frozen=True)

    requirements: BuyerRequirements
    comparisons: list[ComparisonResult] = Field(default_factory=list)
    inquiries: dict[str, InquiryDraft] = Field(default_factory=dict)
    total_listings_evaluated: int = 0
