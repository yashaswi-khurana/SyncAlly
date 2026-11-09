"""Multi-factor seller suggestion matching engine.

Evaluates registered active organizations, profiles, and marketplace listings
against normalized trade requirements using a weighted scoring model:
- Product match: 40% (token overlap between requirement item/category and seller products/listings)
- Capability match: 25% (overlap with seller capabilities)
- Geographic match: 20% (delivery destination matching seller country or operational regions)
- Catalog fit: 15% (active listing with sufficient available quantity and unit price <= target price)

Invariants:
- Excludes requesting buyer organization (candidate.id != buyer_organization_id)
- Excludes inactive / suspended organizations (status == "ACTIVE" only)
- Never exposes private contacts of suggested sellers
- Deterministic tie-breaking: score desc -> token match count desc -> legal_name asc -> id asc
- Minimum threshold: score >= 0.15, max 10 candidates
"""

from __future__ import annotations

import collections
import re
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from syncally.infrastructure.models.identity import Organization, OrganizationProfile
from syncally.infrastructure.models.marketplace import MarketplaceListing

if TYPE_CHECKING:
    from syncally.domain.ai.contracts import NormalizedRequirement

_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "of", "to", "in", "for", "with", "at", "by",
    "from", "on", "off", "is", "are", "was", "were", "be", "been", "we", "you",
    "they", "it", "our", "my", "need", "looking", "purchase", "procure",
    "procurement", "order", "rfq", "target", "budget", "deliver", "delivered",
    "delivery", "ship", "shipment", "shipping", "urgent", "required",
    "requirement", "requirements", "specifications", "spec", "specs", "per",
    "each", "units", "unit", "pieces", "piece", "pc", "pcs", "kg", "kilograms",
    "boxes", "box", "yards", "yard", "m", "meters", "meter", "usd", "eur", "gbp",
    "cad", "aud", "jpy", "inr", "dollars", "dollar", "please", "can", "could",
    "would", "have", "has", "had", "will", "shall", "under", "over", "about",
    "into", "through", "during", "before", "after", "above", "below", "between",
})

WEIGHT_PRODUCT = 0.40
WEIGHT_CAPABILITY = 0.25
WEIGHT_REGION = 0.20
WEIGHT_CATALOG = 0.15
DEFAULT_MATCH_THRESHOLD = 0.15
DEFAULT_TOP_N_LIMIT = 10


def _normalize_token(token: str) -> str:
    """Stem simple English inflections for reliable token overlap matching."""
    t = token.lower()
    if t.endswith("ies") and len(t) > 4:
        return t[:-3] + "y"
    if t.endswith("es") and len(t) > 4 and not t.endswith(("sses", "ches", "shes")):
        return t[:-2]
    if t.endswith("s") and len(t) > 3 and not t.endswith("ss"):
        return t[:-1]
    return t


def tokenize(text: str | None) -> list[str]:
    """Extract normalized alphanumeric tokens, discarding numbers and stopwords."""
    if not text:
        return []
    raw = re.findall(r"[A-Za-z0-9]+", text)
    tokens: list[str] = []
    for word in raw:
        if len(word) < 2 or word.isdigit():
            continue
        norm = _normalize_token(word)
        if norm not in _STOPWORDS and word.lower() not in _STOPWORDS:
            tokens.append(norm)
    return tokens


class SellerSuggestionItem(BaseModel):
    """Ranked suggestion representing an active seller matching trade requirements."""

    organization_id: UUID
    legal_name: str
    country_code: str
    match_score: float = Field(ge=0.0, le=1.0)
    match_reasons: list[str]
    matched_products: list[str] = Field(default_factory=list)
    matched_capabilities: list[str] = Field(default_factory=list)
    matched_listing_ids: list[UUID] = Field(default_factory=list)


class SellerSuggestionService:
    """Coordinates seller discovery and multi-factor ranking."""

    @classmethod
    def suggest_sellers(
        cls,
        db: Session,
        requirements: NormalizedRequirement,
        buyer_organization_id: UUID | None = None,
        *,
        threshold: float = DEFAULT_MATCH_THRESHOLD,
        limit: int = DEFAULT_TOP_N_LIMIT,
    ) -> list[SellerSuggestionItem]:
        """Rank and filter active sellers against normalized trade requirements."""
        # 1. Fetch active candidate organizations and profiles
        query = (
            select(Organization, OrganizationProfile)
            .outerjoin(OrganizationProfile, OrganizationProfile.organization_id == Organization.id)
            .where(Organization.status == "ACTIVE")
        )
        if buyer_organization_id is not None:
            query = query.where(Organization.id != buyer_organization_id)

        candidates = db.execute(query).all()
        if not candidates:
            return []

        # 2. Fetch active marketplace listings for candidate organizations
        listing_query = select(MarketplaceListing).where(MarketplaceListing.status == "ACTIVE")
        if buyer_organization_id is not None:
            listing_query = listing_query.where(MarketplaceListing.organization_id != buyer_organization_id)

        active_listings = db.scalars(listing_query).all()
        listings_by_org: dict[UUID, list[MarketplaceListing]] = collections.defaultdict(list)
        for listing in active_listings:
            listings_by_org[listing.organization_id].append(listing)

        # 3. Extract requirement tokens
        req_raw_text = requirements.raw_text or ""
        req_raw_tokens = set(tokenize(req_raw_text))

        req_item_tokens = set(tokenize(requirements.item_description))
        req_cat_tokens = set(tokenize(requirements.category))
        primary_product_tokens = req_item_tokens | req_cat_tokens
        if not primary_product_tokens:
            primary_product_tokens = req_raw_tokens

        req_cap_tokens = set()
        for cap in requirements.capabilities_required:
            req_cap_tokens.update(tokenize(cap))

        dest_code = (
            requirements.destination_country_code.upper()
            if requirements.destination_country_code
            else None
        )

        scored_items: list[SellerSuggestionItem] = []
        token_match_counts: dict[UUID, int] = {}

        for org, profile in candidates:
            reasons: list[str] = []
            matched_products: list[str] = []
            matched_prod_tokens: set[str] = set()

            seller_products = profile.products if profile and profile.products else []
            seller_capabilities = profile.capabilities if profile and profile.capabilities else []
            seller_regions = {
                r.upper() for r in (profile.regions if profile and profile.regions else [])
            }
            org_listings = listings_by_org.get(org.id, [])

            # --- Factor 1: Product Matching (40%) ---
            for prod in seller_products:
                prod_tokens = set(tokenize(prod))
                overlap = prod_tokens & primary_product_tokens
                if overlap or (prod.lower() in req_raw_text.lower()):
                    matched_products.append(prod)
                    matched_prod_tokens.update(overlap if overlap else prod_tokens)

            # Also inspect active listing titles / categories for product matches
            for listing in org_listings:
                listing_tokens = set(tokenize(listing.title)) | set(tokenize(listing.category))
                listing_overlap = listing_tokens & primary_product_tokens
                if listing_overlap:
                    matched_prod_tokens.update(listing_overlap)

            prod_score = 0.0
            if primary_product_tokens:
                overlap = matched_prod_tokens & primary_product_tokens
                if overlap:
                    ratio = len(overlap) / len(primary_product_tokens)
                    prod_score = min(1.0, max(0.5, ratio))
                elif any(p.lower() in req_raw_text.lower() for p in seller_products):
                    prod_score = 1.0

            if matched_products:
                reasons.append(f"Product match: {', '.join(matched_products)}")

            # --- Factor 2: Capability Matching (25%) ---
            matched_capabilities: list[str] = []
            matched_cap_tokens: set[str] = set()
            raw_text_lower = req_raw_text.lower()

            for cap in seller_capabilities:
                cap_lower = cap.lower()
                cap_tokens = set(tokenize(cap))
                if (
                    cap_lower in raw_text_lower
                    or (cap_tokens and cap_tokens.issubset(req_raw_tokens))
                    or (cap_tokens & req_cap_tokens)
                ):
                    matched_capabilities.append(cap)
                    matched_cap_tokens.update(cap_tokens)
                    reasons.append(f"Matches capability: {cap}")

            cap_score = 0.0
            if matched_capabilities:
                cap_score = 1.0 if len(matched_capabilities) >= 2 else 0.7

            # --- Factor 3: Geographic Compatibility (20%) ---
            reg_score = 0.0
            if dest_code:
                seller_country = org.country_code.upper() if org.country_code else ""
                if dest_code in seller_regions or dest_code == seller_country:
                    reg_score = 1.0
                    reasons.append(f"Delivers to destination region ({dest_code})")
                elif not seller_regions:
                    # Operational regions unspecified
                    reg_score = 0.0
                else:
                    # Explicit regions defined and destination not included
                    reg_score = 0.0

            # --- Factor 4: Marketplace Catalog Fit (15%) ---
            matched_listing_ids: list[UUID] = []
            cat_score = 0.0

            for listing in org_listings:
                listing_tokens = set(tokenize(listing.title)) | set(tokenize(listing.category))
                if not (listing_tokens & primary_product_tokens or listing_tokens & req_raw_tokens):
                    continue

                # Available quantity check
                if requirements.quantity is not None and listing.available_quantity < requirements.quantity:
                    continue

                # Unit price check
                if requirements.target_unit_price is not None and listing.unit_price > requirements.target_unit_price:
                    continue

                # Currency check
                if requirements.currency is not None and listing.currency.upper() != requirements.currency.upper():
                    continue

                matched_listing_ids.append(listing.id)
                reasons.append(f"Catalog listing fits requirements: {listing.title}")
                cat_score = 1.0

            # Invariant: A candidate with 0 product match, 0 capability match, and 0 catalog fit
            # has no substantive relevance to the trade request and is disqualified.
            if prod_score == 0.0 and cap_score == 0.0 and cat_score == 0.0:
                continue

            raw_score = (
                WEIGHT_PRODUCT * prod_score
                + WEIGHT_CAPABILITY * cap_score
                + WEIGHT_REGION * reg_score
                + WEIGHT_CATALOG * cat_score
            )
            final_score = round(min(1.0, max(0.0, raw_score)), 4)

            if final_score < threshold:
                continue

            total_tokens = len(matched_prod_tokens) + len(matched_cap_tokens)
            token_match_counts[org.id] = total_tokens

            scored_items.append(
                SellerSuggestionItem(
                    organization_id=org.id,
                    legal_name=org.legal_name,
                    country_code=org.country_code,
                    match_score=final_score,
                    match_reasons=reasons,
                    matched_products=matched_products,
                    matched_capabilities=matched_capabilities,
                    matched_listing_ids=matched_listing_ids,
                )
            )

        # Deterministic tie-breaking:
        # primary: score desc -> secondary: token match count desc -> tertiary: legal_name asc -> quaternary: id asc
        scored_items.sort(
            key=lambda item: (
                -item.match_score,
                -token_match_counts.get(item.organization_id, 0),
                item.legal_name.lower(),
                str(item.organization_id),
            )
        )

        return scored_items[:limit]
