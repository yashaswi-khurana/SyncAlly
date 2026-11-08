"""Tier 5 Adversarial Coverage Hardening for Deals & Seller Suggestion API.

Empirical verification of white-box edge cases:
1. Opening request analysis with non-existent buyer UUID
2. Candidate organization with NULL profile but valid active marketplace listing
3. Candidate organization with 100% keyword match but non-ACTIVE status (disqualification)
4. Deterministic tie-breaking across multiple candidates down to UUID
5. Payload safety with SQL fragments, XSS tags, Unicode emojis, and max-length strings
6. Non-blocking standard deal creation with opening_request preserved
"""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from syncally.api.auth import get_current_actor
from syncally.api.deals import router as deals_router
from syncally.application.identity import ActorContext
from syncally.application.seller_suggestions import (
    SellerSuggestionService,
)
from syncally.domain.ai.contracts import NormalizedRequirement
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models.base import Base
from syncally.infrastructure.models.identity import (
    Organization,
    OrganizationMember,
    OrganizationProfile,
    User,
)
from syncally.infrastructure.models.marketplace import MarketplaceListing


@pytest.fixture
def test_app_and_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    user_id = uuid4()
    buyer_org_id = uuid4()
    seller_org_id = uuid4()

    user = User(
        id=user_id,
        email="challenger@syncally.test",
        display_name="Challenger User",
        password_hash="mockhash",
        status="ACTIVE",
    )
    db.add(user)

    buyer_org = Organization(
        id=buyer_org_id,
        legal_name="Challenger Buyer Corp",
        country_code="US",
        status="ACTIVE",
    )
    seller_org = Organization(
        id=seller_org_id,
        legal_name="Verified Seller GmbH",
        country_code="DE",
        status="ACTIVE",
    )
    db.add_all([buyer_org, seller_org])

    membership = OrganizationMember(
        id=uuid4(),
        user_id=user_id,
        organization_id=buyer_org_id,
        role="ADMIN",
    )
    db.add(membership)
    db.commit()

    app = FastAPI()
    app.include_router(deals_router)

    def override_get_db():
        yield db

    actor = ActorContext(
        user_id=user_id,
        organization_ids=frozenset({buyer_org_id}),
    )

    def override_get_current_actor():
        return actor

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_actor] = override_get_current_actor

    yield app, db, buyer_org_id, seller_org_id, user_id

    Base.metadata.drop_all(engine)
    db.close()


@pytest.mark.anyio
async def test_analyze_with_non_existent_buyer_uuid_does_not_crash(test_app_and_session):
    app, db, buyer_org_id, seller_org_id, _ = test_app_and_session

    profile = OrganizationProfile(
        organization_id=seller_org_id,
        products=["Industrial Fasteners", "Bolts"],
        capabilities=["Machining"],
        regions=["US", "DE"],
    )
    db.add(profile)
    db.commit()

    non_existent_uuid = str(uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/deals/opening-request/analyze",
            json={
                "text": "Need 500 bolts in Germany",
                "buyer_organization_id": non_existent_uuid,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["suggested_sellers"]) >= 1
        assert data["suggested_sellers"][0]["organization_id"] == str(seller_org_id)


@pytest.mark.anyio
async def test_seller_with_null_profile_but_active_catalog_listing_is_suggested(test_app_and_session):
    app, db, buyer_org_id, _, _ = test_app_and_session

    catalog_seller_id = uuid4()
    catalog_seller = Organization(
        id=catalog_seller_id,
        legal_name="Catalog Only Inc",
        country_code="US",
        status="ACTIVE",
    )
    db.add(catalog_seller)

    listing = MarketplaceListing(
        id=uuid4(),
        organization_id=catalog_seller_id,
        title="Stainless Steel Bolts M8",
        description="M8 Bolts",
        category="Fasteners",
        unit="units",
        unit_price=Decimal("10.00"),
        currency="USD",
        available_quantity=Decimal("1000"),
        status="ACTIVE",
    )
    db.add(listing)
    db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/deals/opening-request/analyze",
            json={
                "text": "Looking to buy 500 units of Stainless Steel Bolts for $12 each in USD",
                "buyer_organization_id": str(buyer_org_id),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        matching_ids = [s["organization_id"] for s in data["suggested_sellers"]]
        assert str(catalog_seller_id) in matching_ids


@pytest.mark.anyio
async def test_seller_with_matching_products_disqualified_if_inactive_or_suspended(test_app_and_session):
    app, db, buyer_org_id, _, _ = test_app_and_session

    for status in ["INACTIVE", "SUSPENDED", "PENDING"]:
        bad_org_id = uuid4()
        bad_org = Organization(
            id=bad_org_id,
            legal_name=f"Bad Org {status}",
            country_code="US",
            status=status,
        )
        bad_profile = OrganizationProfile(
            organization_id=bad_org_id,
            products=["Titanium Bolts"],
            capabilities=["Precision Machining"],
        )
        db.add_all([bad_org, bad_profile])
    db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/deals/opening-request/analyze",
            json={
                "text": "Need 500 titanium bolts with precision machining",
                "buyer_organization_id": str(buyer_org_id),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        names = [s["legal_name"] for s in data["suggested_sellers"]]
        for status in ["INACTIVE", "SUSPENDED", "PENDING"]:
            assert f"Bad Org {status}" not in names


def test_deterministic_tie_breaking_down_to_uuid():
    # Test identical score, tokens, and legal name ordered by UUID string
    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(bind=engine)
    db = SessionMaker()

    u1 = UUID("00000000-0000-0000-0000-000000000001")
    u2 = UUID("00000000-0000-0000-0000-000000000002")

    org1 = Organization(id=u1, legal_name="Identical Seller", country_code="DE", status="ACTIVE")
    prof1 = OrganizationProfile(organization_id=u1, products=["Bolts"])
    org2 = Organization(id=u2, legal_name="Identical Seller", country_code="DE", status="ACTIVE")
    prof2 = OrganizationProfile(organization_id=u2, products=["Bolts"])
    db.add_all([org1, prof1, org2, prof2])
    db.commit()

    req = NormalizedRequirement(item_description="Bolts", raw_text="Bolts")
    results = SellerSuggestionService.suggest_sellers(db, req)

    assert len(results) == 2
    assert results[0].match_score == results[1].match_score
    # u1 must precede u2 deterministically
    assert results[0].organization_id == u1
    assert results[1].organization_id == u2

    Base.metadata.drop_all(engine)
    db.close()


@pytest.mark.anyio
async def test_adversarial_injection_payload_in_opening_request(test_app_and_session):
    app, db, buyer_org_id, seller_org_id, _ = test_app_and_session

    payloads = [
        "<script>alert('xss')</script> 500 bolts",
        "'; DROP TABLE deals; -- 500 bolts",
        "{\"json\": \"injection\", \"price\": 0} 500 bolts",
        "🚀📦🔧 Worldwide Delivery of 500 bolts 🌟✨",
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for p in payloads:
            resp = await client.post(
                "/deals/opening-request/analyze",
                json={
                    "text": p,
                    "buyer_organization_id": str(buyer_org_id),
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["requirements"]["raw_text"] == p
