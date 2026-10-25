"""Tests for organization directory and search API."""

import asyncio
import unittest
from typing import Any
from uuid import UUID

import httpx
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


class OrganizationDirectoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.user = User(
            email="actor@example.com",
            display_name="Actor",
            password_hash="test-password-hash",
            status="ACTIVE",
        )
        self.session.add(self.user)
        self.session.commit()
        self.actor = ActorContext(
            user_id=self.user.id,
            organization_ids=frozenset(),
        )

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _authenticate(self, actor: ActorContext | None = None) -> None:
        target_actor = actor or self.actor
        app.dependency_overrides[get_db] = lambda: self.session
        app.dependency_overrides[get_current_actor] = lambda: target_actor

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        async def send() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
                headers=headers,
            ) as client:
                return await client.request(method, path, params=params)

        return asyncio.run(send())

    def _create_org(
        self,
        legal_name: str,
        country_code: str = "US",
        status: str = "ACTIVE",
    ) -> Organization:
        org = Organization(
            legal_name=legal_name,
            country_code=country_code,
            status=status,
        )
        self.session.add(org)
        self.session.commit()
        return org

    def test_directory_route_registered_in_openapi(self) -> None:
        paths = app.openapi()["paths"]
        self.assertIn("/organizations/directory", paths)
        self.assertIn("get", paths["/organizations/directory"])

    def test_directory_requires_authentication(self) -> None:
        # App dependency overrides not set for get_current_actor
        app.dependency_overrides[get_db] = lambda: self.session
        response = self._request("GET", "/organizations/directory")
        self.assertEqual(response.status_code, 401)

    def test_directory_empty_query_returns_active_organizations(self) -> None:
        self._authenticate()
        org1 = self._create_org("Acme Corp", "US")
        org2 = self._create_org("Beta Industries", "CA")

        response = self._request("GET", "/organizations/directory")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["legal_name"], "Acme Corp")
        self.assertEqual(data[0]["country_code"], "US")
        self.assertEqual(data[0]["id"], str(org1.id))
        self.assertEqual(UUID(data[0]["id"]), org1.id)
        self.assertEqual(data[1]["legal_name"], "Beta Industries")
        self.assertEqual(data[1]["country_code"], "CA")
        self.assertEqual(data[1]["id"], str(org2.id))
        self.assertEqual(UUID(data[1]["id"]), org2.id)

    def test_directory_search_case_insensitive_prefix(self) -> None:
        self._authenticate()
        andean = self._create_org("Andean Coffee Roasters", "CO")
        self._create_org("Acme Corp", "US")
        self._create_org("Bolivian Exports", "BO")

        # Test exact match prefix
        response = self._request("GET", "/organizations/directory", params={"q": "Andean"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], str(andean.id))
        self.assertEqual(data[0]["legal_name"], "Andean Coffee Roasters")

        # Test lowercase prefix
        response = self._request("GET", "/organizations/directory", params={"q": "andean"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], str(andean.id))

        # Test uppercase prefix
        response = self._request("GET", "/organizations/directory", params={"q": "ANDEAN"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], str(andean.id))

    def test_directory_prefix_search_does_not_match_infix(self) -> None:
        self._authenticate()
        self._create_org("Great Andean Coffee", "CO")  # 'Andean' is not at the start
        andean_first = self._create_org("Andean Supplies", "PE")

        response = self._request("GET", "/organizations/directory", params={"q": "Andean"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], str(andean_first.id))

    def test_directory_search_no_matches_returns_empty_list(self) -> None:
        self._authenticate()
        self._create_org("Andean Coffee Roasters", "CO")

        response = self._request("GET", "/organizations/directory", params={"q": "NonExistent"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_directory_whitespace_query_returns_active_organizations(self) -> None:
        self._authenticate()
        self._create_org("Alpha Co", "US")
        self._create_org("Beta Co", "US")

        # Whitespace-only should behave as empty search
        response = self._request("GET", "/organizations/directory", params={"q": "   "})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)

    def test_directory_filters_inactive_and_suspended_organizations(self) -> None:
        self._authenticate()
        active_org = self._create_org("Andean Active", "CO", status="ACTIVE")
        self._create_org("Andean Inactive", "CO", status="INACTIVE")
        self._create_org("Andean Suspended", "CO", status="SUSPENDED")
        self._create_org("Andean Pending", "CO", status="PENDING")

        response = self._request("GET", "/organizations/directory", params={"q": "Andean"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], str(active_org.id))
        self.assertEqual(data[0]["legal_name"], "Andean Active")

    def test_directory_does_not_expose_private_fields(self) -> None:
        self._authenticate()
        org = self._create_org("Privacy Inc", "US")
        # Add a member to verify member/email fields aren't leaked
        member_user = User(
            email="sensitive_ceo@example.com",
            display_name="Sensitive CEO",
            password_hash="secret-hash",
            status="ACTIVE",
        )
        self.session.add(member_user)
        self.session.flush()
        self.session.add(
            OrganizationMember(
                organization_id=org.id,
                user_id=member_user.id,
                role="ADMIN",
                status="ACTIVE",
            )
        )
        self.session.commit()

        response = self._request("GET", "/organizations/directory")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        item = data[0]

        # Ensure only the 3 permitted contract keys are exposed
        self.assertEqual(set(item.keys()), {"id", "legal_name", "country_code"})
        # String representation of json should not contain sensitive user data
        raw_text = response.text
        self.assertNotIn("sensitive_ceo@example.com", raw_text)
        self.assertNotIn("secret-hash", raw_text)
        self.assertNotIn("created_at", raw_text)
        self.assertNotIn("updated_at", raw_text)

    def test_directory_default_limit_50(self) -> None:
        self._authenticate()
        for i in range(55):
            self._create_org(f"Org {i:03d}", "US")

        response = self._request("GET", "/organizations/directory")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 50)

    def test_directory_pagination_limit_and_offset(self) -> None:
        self._authenticate()
        for i in range(5):
            self._create_org(f"Company {i:02d}", "US")

        response = self._request(
            "GET", "/organizations/directory", params={"limit": 2, "offset": 1}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["legal_name"], "Company 01")
        self.assertEqual(data[1]["legal_name"], "Company 02")

    def test_directory_query_length_limit(self) -> None:
        self._authenticate()
        long_query = "a" * 101
        response = self._request("GET", "/organizations/directory", params={"q": long_query})
        self.assertEqual(response.status_code, 422)

    def test_directory_offset_upper_bound(self) -> None:
        self._authenticate()
        self._create_org("Offset Co", "US")

        # Boundary value is allowed
        response = self._request("GET", "/organizations/directory", params={"offset": 10000})
        self.assertEqual(response.status_code, 200)

        # One past the boundary is rejected to block deep-paging queries
        response = self._request("GET", "/organizations/directory", params={"offset": 10001})
        self.assertEqual(response.status_code, 422)

    def test_directory_wildcards_escaped_safely(self) -> None:
        self._authenticate()
        # Create org with literal % and _
        org_percent = self._create_org("100% Cotton Co", "US")
        self._create_org("1000 Cotton Co", "US")
        org_underscore = self._create_org("A_B Inc", "US")
        self._create_org("AXB Inc", "US")

        # Search for '100%' should only return '100% Cotton Co', not '1000 Cotton Co'
        response = self._request("GET", "/organizations/directory", params={"q": "100%"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], str(org_percent.id))

        # Search for 'A_' should only return 'A_B Inc', not 'AXB Inc'
        response = self._request("GET", "/organizations/directory", params={"q": "A_"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], str(org_underscore.id))
