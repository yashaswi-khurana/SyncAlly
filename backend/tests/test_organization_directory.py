"""Tests for organization directory and search API."""

import asyncio
import unittest
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.auth import get_current_actor
from syncally.api.main import app
from syncally.api.organizations import _case_insensitive_prefix
from syncally.application.identity import ActorContext
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import (
    Base,
    Deal,
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
        json: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        async def send() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
                headers=headers,
            ) as client:
                return await client.request(method, path, params=params, json=json)

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

    def test_directory_search_case_insensitive_non_ascii(self) -> None:
        self._authenticate()
        accented = self._create_org("École Normale", "FR")
        self._create_org("Ecole NORMALE", "FR")
        lowercase_accent = self._create_org("Fundación Andina", "CO")

        # Lowercase query must match uppercase non-ASCII letters in the name
        response = self._request("GET", "/organizations/directory", params={"q": "école"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], [str(accented.id)])

        # Uppercase query must match lowercase non-ASCII letters as well
        response = self._request("GET", "/organizations/directory", params={"q": "FUNDACIÓN"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()], [str(lowercase_accent.id)]
        )

    def test_directory_search_compiles_to_indexed_expression_on_postgres(self) -> None:
        engine = create_engine("postgresql+psycopg://localhost/syncally")
        try:
            expression = _case_insensitive_prefix(
                Session(engine), Organization.legal_name, "Andean"
            )
            sql = str(
                select(Organization.id)
                .where(expression)
                .compile(
                    dialect=postgresql.dialect(),
                    compile_kwargs={"literal_binds": True},
                )
            )
        finally:
            engine.dispose()

        # The partial index is on lower(legal_name); ILIKE cannot use it, and the
        # prefix must be folded by the database rather than by Python.
        self.assertIn("lower(organizations.legal_name) LIKE lower('Andean", sql)
        self.assertNotIn("ILIKE", sql)

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

        # Ensure only the permitted contract keys are exposed in public directory
        self.assertEqual(
            set(item.keys()),
            {"id", "legal_name", "country_code", "capabilities", "products", "regions"},
        )
        self.assertNotIn("contacts", item)
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

    def test_get_organization_by_id_returns_active_organization(self) -> None:
        self._authenticate()
        org = self._create_org("Counterparty Logistics Ltd", "US")

        response = self._request("GET", f"/organizations/{org.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], str(org.id))
        self.assertEqual(data["legal_name"], "Counterparty Logistics Ltd")
        self.assertEqual(data["country_code"], "US")

    def test_get_organization_by_id_returns_404_when_missing_or_inactive(self) -> None:
        self._authenticate()
        inactive_org = self._create_org("Suspended Corp", "US", status="SUSPENDED")

        response_inactive = self._request("GET", f"/organizations/{inactive_org.id}")
        self.assertEqual(response_inactive.status_code, 404)

        from uuid import uuid4
        response_missing = self._request("GET", f"/organizations/{uuid4()}")
        self.assertEqual(response_missing.status_code, 404)

    def test_get_organization_by_id_requires_authentication(self) -> None:
        org = self._create_org("Private Org", "US")
        app.dependency_overrides[get_db] = lambda: self.session

        response = self._request("GET", f"/organizations/{org.id}")
        self.assertEqual(response.status_code, 401)

    def test_profile_unrecorded_defaults_to_version_zero(self) -> None:
        org = self._create_org("New Org", "US")
        self._authenticate(
            ActorContext(user_id=self.user.id, organization_ids=frozenset({org.id}))
        )

        response = self._request("GET", f"/organizations/{org.id}/profile")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["organization_id"], str(org.id))
        self.assertEqual(data["version"], 0)
        self.assertEqual(data["verification_status"], "UNVERIFIED")
        self.assertEqual(data["capabilities"], [])
        self.assertEqual(data["products"], [])
        self.assertEqual(data["regions"], [])
        self.assertEqual(data["contacts"], [])

    def test_profile_put_forbidden_for_non_admin(self) -> None:
        org = self._create_org("Target Org", "US")
        other_user = User(
            email="regular@example.com",
            display_name="Regular",
            status="ACTIVE",
        )
        self.session.add(other_user)
        self.session.add(
            OrganizationMember(
                organization_id=org.id,
                user_id=other_user.id,
                role="MEMBER",
                status="ACTIVE",
            )
        )
        self.session.commit()

        # Regular member actor
        self._authenticate(
            ActorContext(user_id=other_user.id, organization_ids=frozenset({org.id}))
        )

        payload = {
            "expected_version": 0,
            "capabilities": ["Logistics"],
            "products": ["Grain"],
            "regions": ["US"],
            "contacts": [
                {
                    "name": "Bob",
                    "purpose": "Sales",
                    "consent_obtained": True,
                    "email": "bob@example.com",
                }
            ],
        }
        response = self._request("PUT", f"/organizations/{org.id}/profile", json=payload)
        self.assertEqual(response.status_code, 403)

    def test_profile_put_and_optimistic_locking_conflict(self) -> None:
        org = self._create_org("Admin Org", "US")
        self.session.add(
            OrganizationMember(
                organization_id=org.id,
                user_id=self.user.id,
                role="ADMIN",
                status="ACTIVE",
            )
        )
        self.session.commit()
        self._authenticate(
            ActorContext(user_id=self.user.id, organization_ids=frozenset({org.id}))
        )

        # 1. Initial write with expected_version=0 creates version 1
        payload = {
            "expected_version": 0,
            "capabilities": ["Freight", "Logistics"],
            "products": ["Grain"],
            "regions": ["US", "GB"],
            "contacts": [
                {
                    "name": "Alice Lead",
                    "purpose": "Operations",
                    "consent_obtained": True,
                    "visibility": "PRIVATE",
                    "email": "alice@adminorg.com",
                }
            ],
        }
        res1 = self._request("PUT", f"/organizations/{org.id}/profile", json=payload)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertEqual(data1["version"], 1)
        self.assertEqual(data1["capabilities"], ["Freight", "Logistics"])
        self.assertEqual(data1["regions"], ["US", "GB"])
        self.assertEqual(data1["verification_status"], "UNVERIFIED")

        # 2. Update with expected_version=1 succeeds and increments to version 2
        payload["expected_version"] = 1
        payload["capabilities"] = ["Freight", "Logistics", "Cold Storage"]
        res2 = self._request("PUT", f"/organizations/{org.id}/profile", json=payload)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertEqual(data2["version"], 2)
        self.assertIn("Cold Storage", data2["capabilities"])

        # 3. Stale update with expected_version=1 fails with 409 Conflict
        res_stale = self._request("PUT", f"/organizations/{org.id}/profile", json=payload)
        self.assertEqual(res_stale.status_code, 409)
        self.assertIn("Profile version conflict", res_stale.json()["detail"])

    def test_profile_put_input_bounds_and_normalization(self) -> None:
        org = self._create_org("Bounds Org", "US")
        self.session.add(
            OrganizationMember(
                organization_id=org.id,
                user_id=self.user.id,
                role="ADMIN",
                status="ACTIVE",
            )
        )
        self.session.commit()
        self._authenticate(
            ActorContext(user_id=self.user.id, organization_ids=frozenset({org.id}))
        )

        # Oversized capabilities (>50) fails with 422
        bad_caps_payload = {
            "expected_version": 0,
            "capabilities": [f"cap-{i}" for i in range(51)],
            "products": [],
            "regions": [],
            "contacts": [],
        }
        res_caps = self._request("PUT", f"/organizations/{org.id}/profile", json=bad_caps_payload)
        self.assertEqual(res_caps.status_code, 422)

        # Individual capability > 200 chars fails with 422
        bad_single_cap_payload = {
            "expected_version": 0,
            "capabilities": ["c" * 201],
            "products": [],
            "regions": [],
            "contacts": [],
        }
        res_single_cap = self._request("PUT", f"/organizations/{org.id}/profile", json=bad_single_cap_payload)
        self.assertEqual(res_single_cap.status_code, 422)

        # Individual product > 200 chars fails with 422
        bad_single_prod_payload = {
            "expected_version": 0,
            "capabilities": [],
            "products": ["p" * 201],
            "regions": [],
            "contacts": [],
        }
        res_single_prod = self._request("PUT", f"/organizations/{org.id}/profile", json=bad_single_prod_payload)
        self.assertEqual(res_single_prod.status_code, 422)

        # Invalid country code fails with 422
        bad_region_payload = {
            "expected_version": 0,
            "capabilities": [],
            "products": [],
            "regions": ["USA"],
            "contacts": [],
        }
        res_region = self._request("PUT", f"/organizations/{org.id}/profile", json=bad_region_payload)
        self.assertEqual(res_region.status_code, 422)

        # Duplicate contact email across contacts fails with 422
        dup_email_payload = {
            "expected_version": 0,
            "capabilities": [],
            "products": [],
            "regions": [],
            "contacts": [
                {"name": "Alice", "purpose": "Sales", "email": "shared@org.com"},
                {"name": "Bob", "purpose": "Ops", "email": "SHARED@org.com"},
            ],
        }
        res_dup = self._request("PUT", f"/organizations/{org.id}/profile", json=dup_email_payload)
        self.assertEqual(res_dup.status_code, 422)

        # Unicode NFC normalization & case deduplication
        norm_payload = {
            "expected_version": 0,
            "capabilities": [" Caf\u0065\u0301 ", "caf\u00e9", "logistics"],
            "products": [" Bulk Grain "],
            "regions": ["us", "US"],
            "contacts": [
                {
                    "name": " Fran\u00e7ois ",
                    "purpose": " Support ",
                    "consent_obtained": True,
                    "email": " Francois@Org.COM ",
                }
            ],
        }
        res_norm = self._request("PUT", f"/organizations/{org.id}/profile", json=norm_payload)
        self.assertEqual(res_norm.status_code, 200)
        norm_data = res_norm.json()
        self.assertEqual(norm_data["capabilities"], ["Caf\u00e9", "logistics"])
        self.assertEqual(norm_data["regions"], ["US"])
        self.assertEqual(norm_data["contacts"][0]["name"], "Fran\u00e7ois")
        self.assertEqual(norm_data["contacts"][0]["email"], "francois@org.com")

    def test_profile_contact_privacy_projections(self) -> None:
        org = self._create_org("Privacy Org", "US")
        counterparty_org = self._create_org("Counterparty Org", "CA")
        unrelated_org = self._create_org("Unrelated Org", "MX")

        # Admin creates profile with 1 PRIVATE contact and 1 PARTICIPANTS contact
        self.session.add(
            OrganizationMember(
                organization_id=org.id,
                user_id=self.user.id,
                role="ADMIN",
                status="ACTIVE",
            )
        )
        self.session.commit()
        self._authenticate(
            ActorContext(user_id=self.user.id, organization_ids=frozenset({org.id}))
        )

        create_payload = {
            "expected_version": 0,
            "capabilities": ["Maritime Transport"],
            "products": ["Vessels"],
            "regions": ["US", "CA"],
            "contacts": [
                {
                    "name": "Secret Admin",
                    "purpose": "Executive Escalation",
                    "visibility": "PRIVATE",
                    "consent_obtained": True,
                    "email": "exec@privacyorg.com",
                },
                {
                    "name": "Public Deal Lead",
                    "purpose": "Commercial Terms",
                    "visibility": "PARTICIPANTS",
                    "consent_obtained": True,
                    "email": "deals@privacyorg.com",
                },
            ],
        }
        put_res = self._request("PUT", f"/organizations/{org.id}/profile", json=create_payload)
        self.assertEqual(put_res.status_code, 200)

        # Create deal between org and counterparty_org in DRAFT status
        from uuid import uuid4
        active_deal = Deal(
            id=uuid4(),
            buyer_organization_id=org.id,
            seller_organization_id=counterparty_org.id,
            status="DRAFT",
        )
        self.session.add(active_deal)
        self.session.commit()

        # 1. As active member of org: sees ALL contacts (2)
        self._authenticate(
            ActorContext(user_id=self.user.id, organization_ids=frozenset({org.id}))
        )
        res_member = self._request("GET", f"/organizations/{org.id}/profile")
        self.assertEqual(res_member.status_code, 200)
        member_contacts = res_member.json()["contacts"]
        self.assertEqual(len(member_contacts), 2)
        self.assertEqual(
            {c["visibility"] for c in member_contacts},
            {"PRIVATE", "PARTICIPANTS"},
        )

        # 2. Counterparty setup
        counterparty_user = User(
            email="counterparty@example.com",
            display_name="Counterparty Lead",
            status="ACTIVE",
        )
        self.session.add(counterparty_user)
        self.session.commit()
        self._authenticate(
            ActorContext(
                user_id=counterparty_user.id,
                organization_ids=frozenset({counterparty_org.id}),
            )
        )

        # 2a. Ineligible deal statuses (DRAFT, NEGOTIATING, PENDING_APPROVALS, CANCELLED, EXPIRED): 0 contacts
        for ineligible_status in ("DRAFT", "NEGOTIATING", "PENDING_APPROVALS", "CANCELLED", "EXPIRED"):
            active_deal.status = ineligible_status
            self.session.commit()
            res_ineligible = self._request("GET", f"/organizations/{org.id}/profile")
            self.assertEqual(res_ineligible.status_code, 200)
            self.assertEqual(
                res_ineligible.json()["contacts"],
                [],
                f"Expected 0 contacts for deal status {ineligible_status}",
            )

        # 2b. Eligible deal statuses (AGREED, EXECUTING, COMPLETED, DISPUTED): sees ONLY PARTICIPANTS contact (1)
        for eligible_status in ("AGREED", "EXECUTING", "COMPLETED", "DISPUTED"):
            active_deal.status = eligible_status
            self.session.commit()
            res_eligible = self._request("GET", f"/organizations/{org.id}/profile")
            self.assertEqual(res_eligible.status_code, 200)
            counterparty_contacts = res_eligible.json()["contacts"]
            self.assertEqual(
                len(counterparty_contacts),
                1,
                f"Expected 1 contact for deal status {eligible_status}",
            )
            self.assertEqual(counterparty_contacts[0]["visibility"], "PARTICIPANTS")
            self.assertEqual(counterparty_contacts[0]["name"], "Public Deal Lead")

        # 3. As unrelated actor: sees 0 contacts
        unrelated_user = User(
            email="unrelated@example.com",
            display_name="Unrelated Lead",
            status="ACTIVE",
        )
        self.session.add(unrelated_user)
        self.session.commit()
        self._authenticate(
            ActorContext(
                user_id=unrelated_user.id,
                organization_ids=frozenset({unrelated_org.id}),
            )
        )
        res_unrelated = self._request("GET", f"/organizations/{org.id}/profile")
        self.assertEqual(res_unrelated.status_code, 200)
        self.assertEqual(res_unrelated.json()["contacts"], [])

        # 4. Public directory and get org route include public projection (capabilities, products, regions)
        # but NEVER include contacts
        dir_res = self._request("GET", "/organizations/directory", params={"q": "Privacy"})
        self.assertEqual(dir_res.status_code, 200)
        dir_items = dir_res.json()
        self.assertEqual(len(dir_items), 1)
        self.assertEqual(dir_items[0]["capabilities"], ["Maritime Transport"])
        self.assertEqual(dir_items[0]["products"], ["Vessels"])
        self.assertEqual(dir_items[0]["regions"], ["US", "CA"])
        self.assertNotIn("contacts", dir_items[0])

        get_res = self._request("GET", f"/organizations/{org.id}")
        self.assertEqual(get_res.status_code, 200)
        get_item = get_res.json()
        self.assertEqual(get_item["capabilities"], ["Maritime Transport"])
        self.assertEqual(get_item["products"], ["Vessels"])
        self.assertEqual(get_item["regions"], ["US", "CA"])
        self.assertNotIn("contacts", get_item)
