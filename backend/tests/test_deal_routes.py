"""HTTP contract tests for the deal create and detail routes."""

import asyncio
import unittest
from typing import Any
from uuid import uuid4

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
    Deal,
    Organization,
    OrganizationMember,
    User,
)


class DealRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _seed_participants(self, *, member_role: str = "ADMIN") -> tuple[User, Organization, Organization]:
        user = User(email="member@example.com", display_name="Member")
        buyer = Organization(legal_name="Buyer Co", country_code="US")
        seller = Organization(legal_name="Seller Co", country_code="CA")
        self.session.add_all([user, buyer, seller])
        self.session.flush()
        self.session.add(
            OrganizationMember(
                user_id=user.id,
                organization_id=buyer.id,
                role=member_role,
                status="ACTIVE",
            )
        )
        self.session.commit()
        return user, buyer, seller

    def _authenticate(self, actor: ActorContext) -> None:
        app.dependency_overrides[get_db] = lambda: self.session
        app.dependency_overrides[get_current_actor] = lambda: actor

    def _request(
        self, method: str, path: str, *, json: dict[str, Any] | None = None
    ) -> httpx.Response:
        async def send() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                return await client.request(method, path, json=json)

        return asyncio.run(send())

    def test_create_deal_returns_201_with_only_schema_fields(self) -> None:
        user, buyer, seller = self._seed_participants()
        self._authenticate(
            ActorContext(user_id=user.id, organization_ids=frozenset({buyer.id}))
        )

        response = self._request(
            "POST",
            "/deals",
            json={
                "buyer_organization_id": str(buyer.id),
                "seller_organization_id": str(seller.id),
            },
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(
            set(body),
            {
                "id",
                "buyer_organization_id",
                "seller_organization_id",
                "status",
                "version",
            },
        )
        self.assertEqual(body["buyer_organization_id"], str(buyer.id))
        self.assertEqual(body["seller_organization_id"], str(seller.id))
        self.assertEqual(body["status"], "DRAFT")
        self.assertEqual(body["version"], 0)

    def test_create_deal_rejects_invalid_input(self) -> None:
        _, buyer, seller = self._seed_participants()
        self._authenticate(ActorContext(user_id=uuid4(), organization_ids=frozenset()))

        missing_field = self._request(
            "POST", "/deals", json={"buyer_organization_id": str(buyer.id)}
        )
        invalid_id = self._request(
            "POST",
            "/deals",
            json={
                "buyer_organization_id": str(buyer.id),
                "seller_organization_id": "not-a-uuid",
            },
        )

        self.assertEqual(missing_field.status_code, 422)
        self.assertEqual(invalid_id.status_code, 422)
        self.assertIn("detail", missing_field.json())

    def test_create_deal_requires_authentication(self) -> None:
        app.dependency_overrides[get_db] = lambda: self.session
        _, buyer, seller = self._seed_participants()

        response = self._request(
            "POST",
            "/deals",
            json={
                "buyer_organization_id": str(buyer.id),
                "seller_organization_id": str(seller.id),
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_create_deal_is_forbidden_for_non_buyer_members(self) -> None:
        _, buyer, seller = self._seed_participants()
        self._authenticate(
            ActorContext(user_id=uuid4(), organization_ids=frozenset({uuid4()}))
        )

        response = self._request(
            "POST",
            "/deals",
            json={
                "buyer_organization_id": str(buyer.id),
                "seller_organization_id": str(seller.id),
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_create_deal_returns_404_for_missing_organizations(self) -> None:
        _, buyer, _ = self._seed_participants()
        self._authenticate(
            ActorContext(user_id=uuid4(), organization_ids=frozenset({buyer.id}))
        )

        response = self._request(
            "POST",
            "/deals",
            json={
                "buyer_organization_id": str(buyer.id),
                "seller_organization_id": str(uuid4()),
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_create_deal_rejects_identical_buyer_and_seller(self) -> None:
        _, buyer, _ = self._seed_participants()
        self._authenticate(
            ActorContext(user_id=uuid4(), organization_ids=frozenset({buyer.id}))
        )

        response = self._request(
            "POST",
            "/deals",
            json={
                "buyer_organization_id": str(buyer.id),
                "seller_organization_id": str(buyer.id),
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_get_deal_returns_404_for_unknown_deal(self) -> None:
        user, buyer, _ = self._seed_participants()
        self._authenticate(
            ActorContext(user_id=user.id, organization_ids=frozenset({buyer.id}))
        )

        response = self._request("GET", f"/deals/{uuid4()}")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Deal not found"})

    def test_get_deal_hides_another_organizations_deal(self) -> None:
        _, buyer, seller = self._seed_participants()
        outsider = User(email="outsider@example.com", display_name="Outsider")
        outsider_org = Organization(legal_name="Outsider Co", country_code="DE")
        self.session.add_all([outsider, outsider_org])
        self.session.flush()
        self.session.add(
            OrganizationMember(
                user_id=outsider.id,
                organization_id=outsider_org.id,
                status="ACTIVE",
            )
        )
        deal = Deal(
            buyer_organization_id=buyer.id,
            seller_organization_id=seller.id,
            status="DRAFT",
            version=0,
        )
        self.session.add(deal)
        self.session.commit()
        self._authenticate(
            ActorContext(
                user_id=outsider.id, organization_ids=frozenset({outsider_org.id})
            )
        )

        response = self._request("GET", f"/deals/{deal.id}")

        self.assertEqual(response.status_code, 404)
        self.assertNotIn(str(buyer.id), response.text)
        self.assertNotIn(str(seller.id), response.text)

    def test_get_deal_succeeds_for_a_participant(self) -> None:
        user, buyer, seller = self._seed_participants()
        deal = Deal(
            buyer_organization_id=buyer.id,
            seller_organization_id=seller.id,
            status="DRAFT",
            version=0,
        )
        self.session.add(deal)
        self.session.commit()
        self._authenticate(
            ActorContext(user_id=user.id, organization_ids=frozenset({buyer.id}))
        )

        response = self._request("GET", f"/deals/{deal.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": str(deal.id),
                "buyer_organization_id": str(buyer.id),
                "seller_organization_id": str(seller.id),
                "status": "DRAFT",
                "version": 0,
            },
        )

    def test_get_deal_succeeds_for_the_seller_party(self) -> None:
        _, buyer, seller = self._seed_participants()
        seller_user = User(email="seller@example.com", display_name="Seller")
        self.session.add(seller_user)
        self.session.flush()
        self.session.add(
            OrganizationMember(
                user_id=seller_user.id,
                organization_id=seller.id,
                status="ACTIVE",
            )
        )
        deal = Deal(
            buyer_organization_id=buyer.id,
            seller_organization_id=seller.id,
            status="DRAFT",
            version=0,
        )
        self.session.add(deal)
        self.session.commit()
        self._authenticate(
            ActorContext(user_id=seller_user.id, organization_ids=frozenset({seller.id}))
        )

        response = self._request("GET", f"/deals/{deal.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(deal.id))

    def test_list_deals_returns_participating_deals_with_the_viewer_role(self) -> None:
        _, buyer, seller = self._seed_participants()
        seller_user = User(email="seller@example.com", display_name="Seller")
        self.session.add(seller_user)
        self.session.flush()
        self.session.add(
            OrganizationMember(
                user_id=seller_user.id,
                organization_id=seller.id,
                status="ACTIVE",
            )
        )
        deal = Deal(
            buyer_organization_id=buyer.id,
            seller_organization_id=seller.id,
            status="DRAFT",
            version=0,
        )
        self.session.add(deal)
        self.session.commit()
        self._authenticate(
            ActorContext(user_id=seller_user.id, organization_ids=frozenset({seller.id}))
        )

        response = self._request("GET", "/deals")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    "id": str(deal.id),
                    "buyer_organization_id": str(buyer.id),
                    "seller_organization_id": str(seller.id),
                    "status": "DRAFT",
                    "version": 0,
                    "viewer_role": "SELLER",
                }
            ],
        )

    def test_list_deals_is_empty_for_a_non_participant(self) -> None:
        _, buyer, seller = self._seed_participants()
        outsider = User(email="outsider@example.com", display_name="Outsider")
        outsider_org = Organization(legal_name="Outsider Co", country_code="DE")
        self.session.add_all([outsider, outsider_org])
        self.session.flush()
        self.session.add(
            OrganizationMember(
                user_id=outsider.id,
                organization_id=outsider_org.id,
                status="ACTIVE",
            )
        )
        self.session.add(
            Deal(
                buyer_organization_id=buyer.id,
                seller_organization_id=seller.id,
                status="DRAFT",
                version=0,
            )
        )
        self.session.commit()
        self._authenticate(
            ActorContext(user_id=outsider.id, organization_ids=frozenset({outsider_org.id}))
        )

        response = self._request("GET", "/deals")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_list_deals_requires_authentication(self) -> None:
        app.dependency_overrides[get_db] = lambda: self.session
        self._seed_participants()

        response = self._request("GET", "/deals")

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
