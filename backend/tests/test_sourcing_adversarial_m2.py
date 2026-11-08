"""Adversarial challenger test suite for Milestone M2 REST APIs.

Author: challenger_sourcing_m2_1
Mission: Empirically stress-test Milestone M2 REST APIs with adversarial requests:
- Malformed JSON payloads (syntax errors, invalid types, empty streams)
- Unauthenticated requests (no auth, invalid token, bad header format) -> 401
- Non-existent UUIDs & resource identifiers -> 404 (or safe 200 for filters), never 500
- Negative pricing & numerical extremes -> appropriate validation (422), never 500
- Oversized payloads > 16KB -> 413, never 500
- 500-invariance verification across all 6 endpoints:
  1. POST /sourcing/interpret
  2. GET  /sourcing/listings
  3. POST /sourcing/compare
  4. POST /sourcing/gap-analysis
  5. POST /sourcing/draft-inquiry
  6. POST /sourcing/evaluate
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.auth import get_current_actor
from syncally.api.main import app
from syncally.application.identity import ActorContext
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import (
    Base,
    Organization,
    OrganizationMember,
    User,
)

REAL_LISTING_ID = "00000000-0000-4000-8000-000000000101"
NONEXISTENT_UUID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    session = Session(db_engine)
    user = User(
        email=f"tester-{uuid4()}@syncally.test",
        display_name="Adversarial Challenger",
        password_hash="argon2-hash",
        status="ACTIVE",
    )
    org = Organization(
        legal_name="Challenger Corp",
        country_code="DE",
        status="ACTIVE",
    )
    session.add_all([user, org])
    session.flush()
    session.add(
        OrganizationMember(
            user_id=user.id,
            organization_id=org.id,
            role="ADMIN",
            status="ACTIVE",
        )
    )
    session.commit()
    yield session, user, org
    session.close()


@pytest.fixture
def auth_client(db_session):
    session, user, org = db_session
    actor = ActorContext(
        user_id=user.id,
        organization_ids=frozenset({org.id}),
    )
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_actor] = lambda: actor
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def unauth_client(db_session):
    session, _, _ = db_session
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides.pop(get_current_actor, None)
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def valid_requirements() -> dict[str, Any]:
    return {
        "title": "M8 Hex Cap Screws DIN 933",
        "category": "Industrial Fasteners",
        "description": "Requirement for high precision screws",
        "quantity": {"target_quantity": "1000", "unit": "boxes"},
        "delivery": {"destination_country_code": "DE", "max_lead_time_days": 30},
        "pricing": {
            "target_unit_price": "12.00",
            "max_unit_price": "15.00",
            "currency": "USD",
        },
    }


# =============================================================================
# 1. Unauthenticated Requests (401 Verification)
# =============================================================================

class TestUnauthenticatedAccess:
    """Verify that all 6 endpoints strictly reject unauthenticated calls with 401."""

    ENDPOINTS = [
        ("POST", "/sourcing/interpret", {"prompt": "test"}),
        ("GET", "/sourcing/listings", None),
        ("POST", "/sourcing/compare", {"requirements": {}}),
        ("POST", "/sourcing/gap-analysis", {"requirements": {}, "listing_id": "x"}),
        ("POST", "/sourcing/draft-inquiry", {"requirements": {}, "listing_id": "x"}),
        ("POST", "/sourcing/evaluate", {"prompt": "test"}),
    ]

    @pytest.mark.parametrize("method,path,payload", ENDPOINTS)
    def test_missing_auth_header_returns_401(self, unauth_client, method, path, payload):
        res = unauth_client.request(method, path, json=payload) if payload else unauth_client.request(method, path)
        assert res.status_code == 401, f"{method} {path} returned {res.status_code}, expected 401"

    @pytest.mark.parametrize("method,path,payload", ENDPOINTS)
    def test_invalid_bearer_token_returns_401(self, unauth_client, method, path, payload):
        headers = {"Authorization": "Bearer invalid-bearer-token"}
        res = unauth_client.request(method, path, json=payload, headers=headers) if payload else unauth_client.request(method, path, headers=headers)
        assert res.status_code == 401, f"{method} {path} with invalid token returned {res.status_code}, expected 401"

    @pytest.mark.parametrize("method,path,payload", ENDPOINTS)
    def test_malformed_auth_header_returns_401(self, unauth_client, method, path, payload):
        headers = {"Authorization": "Basic not-a-bearer-token"}
        res = unauth_client.request(method, path, json=payload, headers=headers) if payload else unauth_client.request(method, path, headers=headers)
        assert res.status_code == 401, f"{method} {path} with malformed header returned {res.status_code}, expected 401"


# =============================================================================
# 2. Oversized Payloads > 16KB (413 Verification)
# =============================================================================

class TestOversizedPayloads:
    """Verify that payloads exceeding 16KB return 413 on all endpoints."""

    ENDPOINTS = [
        ("POST", "/sourcing/interpret"),
        ("GET", "/sourcing/listings"),
        ("POST", "/sourcing/compare"),
        ("POST", "/sourcing/gap-analysis"),
        ("POST", "/sourcing/draft-inquiry"),
        ("POST", "/sourcing/evaluate"),
    ]

    @pytest.mark.parametrize("method,path", ENDPOINTS)
    def test_payload_exceeding_16kb_returns_413(self, auth_client, method, path):
        # 20KB payload
        huge_body = b"{\"padding\": \"" + b"X" * (20 * 1024) + b"\"}"
        res = auth_client.request(
            method,
            path,
            content=huge_body,
            headers={"Content-Type": "application/json"},
        )
        assert res.status_code == 413, f"{method} {path} returned {res.status_code}, expected 413"
        assert res.status_code != 500, f"{method} {path} crashed with 500 on oversized payload"


# =============================================================================
# 3. Malformed JSON (422/400 Validation Verification)
# =============================================================================

class TestMalformedJsonPayloads:
    """Verify that corrupt/malformed JSON returns 422/400 and NEVER 500."""

    MALFORMED_BODIES = [
        (b"{\"unclosed\": \"json", "truncated json"),
        (b"{bad syntax :", "syntax error"),
        (b"", "empty body"),
        (b"null", "null body"),
        (b"[\"array\", \"not\", \"object\"]", "top-level array"),
        (b"{\"prompt\": \x00}", "null byte in value"),
        (b"{\"nested\": { \"deep\": {", "unclosed nested object"),
    ]

    POST_ENDPOINTS = [
        "/sourcing/interpret",
        "/sourcing/compare",
        "/sourcing/gap-analysis",
        "/sourcing/draft-inquiry",
        "/sourcing/evaluate",
    ]

    @pytest.mark.parametrize("path", POST_ENDPOINTS)
    @pytest.mark.parametrize("body,desc", MALFORMED_BODIES)
    def test_malformed_json_never_500(self, auth_client, path, body, desc):
        res = auth_client.post(
            path,
            content=body,
            headers={"Content-Type": "application/json"},
        )
        assert res.status_code != 500, f"{path} returned 500 on {desc}!"
        assert res.status_code in (400, 422, 200), (
            f"{path} returned unexpected status {res.status_code} on {desc}"
        )


# =============================================================================
# 4. Non-Existent UUIDs and Identifiers (404 / Safe Handling)
# =============================================================================

class TestNonExistentIdentifiers:
    """Verify non-existent UUIDs return 404 for lookups and 200 for filters, never 500."""

    def test_gap_analysis_nonexistent_uuid_returns_404(self, auth_client, valid_requirements):
        res = auth_client.post(
            "/sourcing/gap-analysis",
            json={"requirements": valid_requirements, "listing_id": NONEXISTENT_UUID},
        )
        assert res.status_code == 404, f"Expected 404, got {res.status_code}"
        assert res.status_code != 500

    def test_gap_analysis_arbitrary_string_id_returns_404(self, auth_client, valid_requirements):
        res = auth_client.post(
            "/sourcing/gap-analysis",
            json={"requirements": valid_requirements, "listing_id": "totally-fake-listing-id"},
        )
        assert res.status_code == 404, f"Expected 404, got {res.status_code}"
        assert res.status_code != 500

    def test_draft_inquiry_nonexistent_uuid_returns_404(self, auth_client, valid_requirements):
        res = auth_client.post(
            "/sourcing/draft-inquiry",
            json={"requirements": valid_requirements, "listing_id": NONEXISTENT_UUID},
        )
        assert res.status_code == 404, f"Expected 404, got {res.status_code}"
        assert res.status_code != 500

    def test_draft_inquiry_nonexistent_buyer_org_handles_gracefully(self, auth_client, valid_requirements):
        res = auth_client.post(
            "/sourcing/draft-inquiry",
            json={
                "requirements": valid_requirements,
                "listing_id": REAL_LISTING_ID,
                "buyer_organization_id": NONEXISTENT_UUID,
            },
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        assert res.status_code != 500

    def test_draft_inquiry_malformed_buyer_org_uuid_handles_gracefully(self, auth_client, valid_requirements):
        res = auth_client.post(
            "/sourcing/draft-inquiry",
            json={
                "requirements": valid_requirements,
                "listing_id": REAL_LISTING_ID,
                "buyer_organization_id": "not-a-valid-uuid-format",
            },
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        assert res.status_code != 500

    def test_compare_nonexistent_uuids_returns_empty_results(self, auth_client, valid_requirements):
        res = auth_client.post(
            "/sourcing/compare",
            json={
                "requirements": valid_requirements,
                "listing_ids": [NONEXISTENT_UUID, "not-a-uuid-1234"],
            },
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        assert res.json()["results"] == []

    def test_listings_nonexistent_query_filters_return_empty(self, auth_client):
        res = auth_client.get(
            "/sourcing/listings",
            params={"category": "NonExistentCategory999", "completeness": "FAKE_TIER"},
        )
        assert res.status_code == 200
        assert res.json()["listings"] == []
        assert res.json()["total"] == 0


# =============================================================================
# 5. Negative Pricing and Numerical Validation Stress Tests
# =============================================================================

class TestNegativePricingAndNumericalAdversaries:
    """Stress test negative prices, zero division, and numerical bounds across endpoints."""

    def test_compare_negative_target_price_rejected_with_422(self, auth_client, valid_requirements):
        bad_req = dict(valid_requirements)
        bad_req["pricing"] = {"target_unit_price": "-10.00", "currency": "USD"}
        res = auth_client.post("/sourcing/compare", json={"requirements": bad_req})
        assert res.status_code == 422
        assert res.status_code != 500

    def test_gap_analysis_negative_max_price_rejected_with_422(self, auth_client, valid_requirements):
        bad_req = dict(valid_requirements)
        bad_req["pricing"] = {"max_unit_price": "-15.00", "currency": "USD"}
        res = auth_client.post(
            "/sourcing/gap-analysis",
            json={"requirements": bad_req, "listing_id": REAL_LISTING_ID},
        )
        assert res.status_code == 422
        assert res.status_code != 500

    def test_draft_inquiry_negative_budget_rejected_with_422(self, auth_client, valid_requirements):
        bad_req = dict(valid_requirements)
        bad_req["pricing"] = {"max_total_budget": "-500.00", "currency": "USD"}
        res = auth_client.post(
            "/sourcing/draft-inquiry",
            json={"requirements": bad_req, "listing_id": REAL_LISTING_ID},
        )
        assert res.status_code == 422
        assert res.status_code != 500

    def test_evaluate_negative_price_rejected_with_422(self, auth_client, valid_requirements):
        bad_req = dict(valid_requirements)
        bad_req["pricing"] = {"target_unit_price": "-99.99", "currency": "USD"}
        res = auth_client.post("/sourcing/evaluate", json={"requirements": bad_req})
        assert res.status_code == 422
        assert res.status_code != 500

    def test_zero_pricing_handles_without_zero_division_500(self, auth_client, valid_requirements):
        zero_req = dict(valid_requirements)
        zero_req["pricing"] = {
            "target_unit_price": "0.00",
            "max_unit_price": "0.00",
            "max_total_budget": "0.00",
            "currency": "USD",
        }
        res_comp = auth_client.post("/sourcing/compare", json={"requirements": zero_req})
        assert res_comp.status_code == 200, f"Compare returned {res_comp.status_code}"
        assert res_comp.status_code != 500

        res_gap = auth_client.post(
            "/sourcing/gap-analysis",
            json={"requirements": zero_req, "listing_id": REAL_LISTING_ID},
        )
        assert res_gap.status_code == 200, f"Gap-analysis returned {res_gap.status_code}"
        assert res_gap.status_code != 500

    def test_interpret_negative_pricing_in_structured_overrides(self, auth_client):
        """VULNERABILITY PROBE: Sending negative pricing in structured_overrides must NEVER return 500."""
        res = auth_client.post(
            "/sourcing/interpret",
            json={"structured_overrides": {"pricing": {"target_unit_price": -10.00}}},
        )
        # Expected appropriate validation status (422/400). If it returns 500, it fails 500-invariance!
        assert res.status_code != 500, (
            f"VULNERABILITY CONFIRMED: POST /sourcing/interpret threw unhandled 500 on negative price! "
            f"Response: {res.text}"
        )
        assert res.status_code in (400, 422)

    def test_interpret_negative_quantity_in_structured_overrides(self, auth_client):
        """VULNERABILITY PROBE: Sending negative quantity in structured_overrides must NEVER return 500."""
        res = auth_client.post(
            "/sourcing/interpret",
            json={"structured_overrides": {"quantity": {"target_quantity": -50}}},
        )
        assert res.status_code != 500, (
            f"VULNERABILITY CONFIRMED: POST /sourcing/interpret threw unhandled 500 on negative quantity! "
            f"Response: {res.text}"
        )
        assert res.status_code in (400, 422)

    def test_interpret_huge_price_quantize_overflow(self, auth_client):
        """VULNERABILITY PROBE: Sending astronomical price string must NEVER throw unhandled 500."""
        astronomical_price = "9" * 80
        res = auth_client.post(
            "/sourcing/interpret",
            json={"prompt": f"target price ${astronomical_price} per box"},
        )
        assert res.status_code != 500, (
            f"VULNERABILITY CONFIRMED: POST /sourcing/interpret threw unhandled 500 on Decimal overflow! "
            f"Response: {res.text}"
        )
        assert res.status_code in (200, 400, 422)

    def test_evaluate_huge_price_quantize_overflow(self, auth_client):
        """VULNERABILITY PROBE: Sending astronomical price string to evaluate must NEVER throw unhandled 500."""
        astronomical_price = "9" * 80
        res = auth_client.post(
            "/sourcing/evaluate",
            json={"prompt": f"target price ${astronomical_price} per box"},
        )
        assert res.status_code != 500, (
            f"VULNERABILITY CONFIRMED: POST /sourcing/evaluate threw unhandled 500 on Decimal overflow! "
            f"Response: {res.text}"
        )
        assert res.status_code in (200, 400, 422)

