"""Integration tests for the buyer sourcing REST API router (/sourcing/*).

Tests all endpoints via httpx.AsyncClient with in-memory SQLite and mock actor dependencies:
- POST /sourcing/interpret
- GET  /sourcing/listings
- POST /sourcing/compare
- POST /sourcing/gap-analysis
- POST /sourcing/draft-inquiry
- POST /sourcing/evaluate
- Security & Middleware: 401 unauthorized and 413 payload limit.
"""

from __future__ import annotations

import asyncio
import json
import unittest
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import httpx
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.auth import get_current_actor
from syncally.api.main import app
from syncally.api.sourcing import SourcingService
from syncally.application.ai import AIConfigurationError, AIPermanentError
from syncally.application.identity import ActorContext
from syncally.config import Settings
from syncally.domain.sourcing.contracts import BuyerRequirements
from syncally.infrastructure.ai.gemini import GeminiGenerateContent
from syncally.infrastructure.ai.openai import OpenAIChatCompletions
from syncally.infrastructure.ai.selection import ConfiguredAIProvider
from syncally.infrastructure.ai.sourcing import _grounded, interpret_sourcing_requirements
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import (
    Base,
    MarketplaceListing,
    Organization,
    OrganizationMember,
    User,
)


class SourcingApiIntegrationTests(unittest.TestCase):
    """Full HTTP contract test suite for the /sourcing/* router."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        self.user, self.buyer_org = self._seed_buyer()
        self.actor = ActorContext(
            user_id=self.user.id,
            organization_ids=frozenset({self.buyer_org.id}),
        )
        self._authenticate(self.actor)
        self._ai_interpreter_patch = patch(
            "syncally.api.sourcing._interpret_natural",
            side_effect=self._interpret_with_test_provider,
        )
        self._ai_interpreter_patch.start()

    def tearDown(self) -> None:
        self._ai_interpreter_patch.stop()
        app.dependency_overrides.clear()
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    @staticmethod
    def _interpret_with_test_provider(prompt, structured_overrides):
        requirements, fields = SourcingService.interpret_requirements(prompt, structured_overrides)
        provider = SimpleNamespace(provenance=SimpleNamespace(
            provider="openai",
            model="test-only-model",
            fallback_reason=None,
        ))
        return requirements, fields, provider

    def test_interpret_reports_missing_remote_ai_configuration(self) -> None:
        self._ai_interpreter_patch.stop()
        try:
            with patch(
                "syncally.api.sourcing.ConfiguredAIProvider",
                side_effect=AIConfigurationError("not configured"),
            ):
                response = self._request(
                    "POST",
                    "/sourcing/interpret",
                    json={"prompt": "1000 boxes of fasteners"},
                )
        finally:
            self._ai_interpreter_patch.start()
        self.assertEqual(response.status_code, 503)
        self.assertIn("Sourcing AI is not configured", response.json()["detail"])

    def _seed_buyer(self) -> tuple[User, Organization]:
        user = User(
            email="sourcing.lead@apexprocure.com",
            display_name="Elena Vance",
            password_hash="test-argon2-hash",
            status="ACTIVE",
        )
        buyer_org = Organization(
            legal_name="Apex Global Procurement AG",
            country_code="DE",
            status="ACTIVE",
        )
        self.session.add_all([user, buyer_org])
        self.session.flush()

        self.session.add(
            OrganizationMember(
                user_id=user.id,
                organization_id=buyer_org.id,
                role="ADMIN",
                status="ACTIVE",
            )
        )
        self.session.commit()
        return user, buyer_org

    def test_marketplace_browsing_remains_available_but_sourcing_catalogue_fails_closed(self) -> None:
        seller = Organization(legal_name="Actual Seller", country_code="FR", status="ACTIVE")
        inactive_seller = Organization(legal_name="Inactive Seller", country_code="GB", status="INACTIVE")
        self.session.add_all([seller, inactive_seller])
        self.session.flush()

        def listing(org, title, status):
            return MarketplaceListing(
                organization_id=org.id, title=title, description="Actual offer",
                category="Hardware", available_quantity=Decimal("3"), unit="pieces",
                unit_price=Decimal("0"), currency="EUR", status=status,
            )
        self.session.add_all([
            listing(seller, "Actual bolts", "ACTIVE"),
            listing(seller, "Hidden bolts", "INACTIVE"),
            listing(inactive_seller, "Inactive seller bolts", "ACTIVE"),
        ])
        self.session.add_all(
            listing(seller, f"Extra offer {number}", "ACTIVE") for number in range(100)
        )
        self.session.commit()

        for params in (
            {},
            {"q": "bolts"},
            {"category": "hard", "completeness": "unknown"},
            {"completeness": "FULL_COMPLETE"},
            {"q": "%"},
        ):
            with self.subTest(params=params):
                response = self._request("GET", "/sourcing/listings", params=params)
                self.assertEqual(response.status_code, 503)
                self.assertIn("Marketplace", response.json()["detail"])
                self.assertIn("/marketplace/listings", response.json()["detail"])
                self.assertNotIn("listings", response.json())
                self.assertNotIn("total", response.json())

        response = self._request("GET", "/marketplace/listings", params={"q": "bolts"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()), 1)
        item = response.json()[0]
        self.assertEqual(item["organization_name"], "Actual Seller")
        self.assertEqual(item["organization_id"], str(seller.id))
        self.assertEqual(item["currency"], "EUR")
        self.assertEqual(Decimal(item["unit_price"]), 0)
        self.assertEqual(
            len(self._request("GET", "/marketplace/listings", params={"category": "hard", "limit": 100}).json()),
            100,
        )
        self.assertEqual(
            len(self._request("GET", "/marketplace/listings", params={"category": "hard", "offset": 100}).json()),
            1,
        )
        self.assertEqual(self._request("GET", "/marketplace/listings", params={"q": "%"}).json(), [])
        seller.status = "INACTIVE"
        self.session.commit()
        self.assertEqual(self._request("GET", "/marketplace/listings").json(), [])

    def test_sourcing_scoring_and_drafts_fail_closed_without_provider_calls(self) -> None:
        requirements = self._sample_requirements()
        seller = Organization(legal_name="Recorded Seller", country_code="FR", status="ACTIVE")
        self.session.add(seller)
        self.session.flush()
        listing = MarketplaceListing(
            organization_id=seller.id, title="Recorded bolts", description="",
            category="Hardware", available_quantity=Decimal("3"), unit="pieces",
            unit_price=Decimal("1"), currency="EUR",
        )
        self.session.add(listing)
        self.session.commit()
        for path, payload in (
            ("/sourcing/compare", {"requirements": requirements, "listing_ids": ["bundled-id"]}),
            ("/sourcing/compare", {"requirements": requirements, "listing_ids": [str(listing.id)]}),
            ("/sourcing/gap-analysis", {"requirements": requirements, "listing_id": "bundled-id"}),
            ("/sourcing/draft-inquiry", {"requirements": requirements, "listing_id": "bundled-id"}),
            ("/sourcing/draft-inquiry", {"requirements": requirements, "listing_id": str(listing.id)}),
            ("/sourcing/evaluate", {"prompt": "Please source bolts"}),
            ("/sourcing/evaluate", {"requirements": requirements}),
        ):
            with self.subTest(path=path), patch("syncally.api.sourcing._interpret_natural") as interpret:
                response = self._request("POST", path, json=payload)
                self.assertEqual(response.status_code, 503, response.text)
                self.assertIn("Browse active offers", response.json()["detail"])
                interpret.assert_not_called()

    def test_sourcing_catalogue_and_unavailable_operations_require_authentication(self) -> None:
        self._authenticate(None)
        self.assertEqual(self._request("GET", "/sourcing/listings").status_code, 401)
        requirements = self._sample_requirements()
        for path, payload in (
            ("/sourcing/compare", {"requirements": requirements}),
            ("/sourcing/gap-analysis", {"requirements": requirements, "listing_id": "id"}),
            ("/sourcing/draft-inquiry", {"requirements": requirements, "listing_id": "id"}),
            ("/sourcing/evaluate", {"prompt": "bolts"}),
        ):
            with self.subTest(path=path):
                self.assertEqual(self._request("POST", path, json=payload).status_code, 401)

    def test_demo_service_rejects_production_access(self) -> None:
        with patch("syncally.application.sourcing.service.settings", SimpleNamespace(app_env="production")):
            with self.assertRaisesRegex(RuntimeError, "only in development or test"):
                SourcingService.get_listings()
            with self.assertRaisesRegex(RuntimeError, "only in development or test"):
                SourcingService.get_listing_by_id("demo")
            with self.assertRaisesRegex(RuntimeError, "only in development or test"):
                SourcingService.compare_listings(BuyerRequirements.model_validate(self._sample_requirements()))

    def _authenticate(self, actor: ActorContext | None) -> None:
        app.dependency_overrides[get_db] = lambda: self.session
        if actor is not None:
            app.dependency_overrides[get_current_actor] = lambda: actor
        else:
            app.dependency_overrides.pop(get_current_actor, None)

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
            ) as client:
                return await client.request(
                    method, path, params=params, json=json, headers=headers
                )

        return asyncio.run(send())

    def _request_with_remote_ai(
        self,
        provider_name: str,
        prompt: str,
        respond,
        overrides: dict[str, Any] | None = None,
        path: str = "/sourcing/interpret",
    ) -> httpx.Response:
        settings_values: dict[str, Any] = {
            "app_env": "test",
            "ai_provider": provider_name,
            "ai_remote_egress_enabled": True,
        }
        if provider_name.startswith("gemini"):
            settings_values.update(
                gemini_model="gemini-configured-model",
                google_api_key="test-gemini-key",
            )
        elif provider_name.startswith("nvidia"):
            settings_values.update(
                nvidia_model="nvidia/nemotron-3.5-super-vl-120b-a12b",
                nvidia_api_key="test-nvidia-key",
            )
        else:
            settings_values.update(
                openai_model="openai-configured-model",
                openai_api_key="test-openai-key",
            )
        provider_settings = Settings(_env_file=None, **settings_values)
        transport = httpx.MockTransport(respond)

        self._ai_interpreter_patch.stop()
        try:
            with (
                patch("syncally.api.sourcing.settings", provider_settings),
                patch(
                    "syncally.api.sourcing.ConfiguredAIProvider",
                    side_effect=lambda _: ConfiguredAIProvider(
                        provider_settings,
                        transport=transport,
                    ),
                ),
            ):
                return self._request(
                    "POST",
                    path,
                    json={"prompt": prompt, "structured_overrides": overrides},
                )
        finally:
            self._ai_interpreter_patch.start()

    def _sample_requirements(
        self,
        category: str = "Industrial Fasteners",
        title: str = "M8 Stainless Steel Hex Cap Bolts",
        target_qty: int = 1000,
        max_price: str = "14.00",
        target_price: str = "12.00",
        max_lead_days: int = 30,
    ) -> dict[str, Any]:
        return {
            "title": title,
            "category": category,
            "description": f"Detailed requirement for {title}",
            "technical_specs": {
                "materials": ["316 Stainless Steel"],
                "tolerances": "ISO 965-1 6g",
                "certifications": ["ISO 9001", "CE", "RoHS"],
                "standards": ["DIN 933"],
            },
            "pricing": {
                "target_unit_price": target_price,
                "max_unit_price": max_price,
                "currency": "USD",
            },
            "quantity": {
                "target_quantity": str(target_qty),
                "unit": "boxes",
            },
            "delivery": {
                "destination_country_code": "DE",
                "destination_port_or_city": "Berlin",
                "max_lead_time_days": max_lead_days,
            },
            "commercial_terms": {
                "preferred_incoterm": "DDP",
                "acceptable_incoterms": ["DDP", "CIF", "FOB"],
                "preferred_payment_term": "NET_30",
                "min_warranty_months": 12,
                "inspection_requirement": "FACTORY_MILL_CERTIFICATE",
            },
        }

    # =========================================================================
    # 1. POST /sourcing/interpret
    # =========================================================================

    @staticmethod
    def _remote_sourcing_extraction() -> dict[str, Any]:
        return {
            "extractions": [
                {"field": "title", "value": "M8 fasteners", "quote": "M8 fasteners"},
                {"field": "category", "value": "Industrial Fasteners", "quote": "M8 fasteners"},
                {"field": "pricing.currency", "value": "USD", "quote": "USD currency"},
                {"field": "quantity.target_quantity", "value": "1000", "quote": "1000 boxes"},
                {"field": "quantity.unit", "value": "boxes", "quote": "1000 boxes"},
                {"field": "delivery.destination_country_code", "value": "DE", "quote": "Germany"},
                {
                    "field": "commercial_terms.min_warranty_months",
                    "value": "12",
                    "quote": "12 month warranty",
                },
                {
                    "field": "commercial_terms.inspection_requirement",
                    "value": "FACTORY_MILL_CERTIFICATE",
                    "quote": "factory mill certificate",
                },
            ],
            "unknown_fields": [],
        }

    def test_interpret_uses_configured_openai_and_gemini_http_transports(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Berlin, Germany, in USD currency, "
            "with a 12 month warranty and factory mill certificate."
        )
        for provider_name in ("openai", "gemini"):
            with self.subTest(provider=provider_name):
                requests: list[httpx.Request] = []

                def respond(request: httpx.Request) -> httpx.Response:
                    requests.append(request)
                    if provider_name == "openai":
                        return httpx.Response(200, json={
                            "object": "chat.completion",
                            "model": "openai-response-model",
                            "choices": [{
                                "index": 0,
                                "finish_reason": "stop",
                                "message": {
                                    "role": "assistant",
                                    "content": json.dumps(self._remote_sourcing_extraction()),
                                    "refusal": None,
                                },
                            }],
                        })
                    return httpx.Response(200, json={
                        "modelVersion": "gemini-response-model",
                        "candidates": [{
                            "index": 0,
                            "finishReason": "STOP",
                            "content": {
                                "role": "model",
                                "parts": [{
                                    "text": json.dumps(self._remote_sourcing_extraction()),
                                }],
                            },
                        }],
                    })

                response = self._request_with_remote_ai(provider_name, prompt, respond)

                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()
                self.assertEqual(result["ai_provider"], provider_name)
                self.assertEqual(
                    result["ai_model"],
                    f"{provider_name}-response-model",
                )
                self.assertIsNone(result["fallback_reason"])
                self.assertEqual(result["requirements"]["quantity"]["target_quantity"], "1000")
                self.assertEqual(result["requirements"]["delivery"]["destination_country_code"], "DE")
                self.assertEqual(len(requests), 1)
                self.assertIn(prompt.encode(), requests[0].content)
                self.assertNotIn(b"test-openai-key", requests[0].content)
                self.assertNotIn(b"test-gemini-key", requests[0].content)
                self.assertEqual(
                    requests[0].url.host,
                    "generativelanguage.googleapis.com"
                    if provider_name == "gemini"
                    else "api.openai.com",
                )

    def test_remote_sourcing_releases_read_transaction_before_provider_call(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Germany in USD currency, "
            "12 month warranty and factory mill certificate."
        )
        for path in ("/sourcing/interpret",):
            with self.subTest(path=path):
                self.session.execute(select(User.id)).first()
                self.assertTrue(self.session.in_transaction())
                transaction_states: list[bool] = []

                def respond(request: httpx.Request) -> httpx.Response:
                    transaction_states.append(self.session.in_transaction())
                    self.assertFalse(self.session.in_transaction())
                    return httpx.Response(200, json={
                        "object": "chat.completion",
                        "model": "openai-response-model",
                        "choices": [{
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": json.dumps(self._remote_sourcing_extraction()),
                                "refusal": None,
                            },
                        }],
                    })

                response = self._request_with_remote_ai("openai", prompt, respond, path=path)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(transaction_states, [False])

    def test_interpret_remote_provider_failures_are_explicit_without_fallback(self) -> None:
        prompt = "Need 1000 boxes of M8 fasteners."
        for provider_name in ("openai", "gemini"):
            with self.subTest(provider=provider_name):
                requests: list[httpx.Request] = []

                def respond(request: httpx.Request) -> httpx.Response:
                    requests.append(request)
                    return httpx.Response(503, text="private provider diagnostics")

                response = self._request_with_remote_ai(
                    f"{provider_name}_with_offline_fallback",
                    prompt,
                    respond,
                )

                self.assertEqual(response.status_code, 503)
                self.assertIn("temporarily unavailable", response.json()["detail"])
                self.assertNotIn("private provider diagnostics", response.text)
                self.assertEqual(len(requests), 1)

    def test_interpret_nvidia_access_rejection_is_actionable(self) -> None:
        requests: list[httpx.Request] = []

        def respond(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                403,
                text="private provider diagnostics",
                headers={"content-encoding": "identity"},
            )

        response = self._request_with_remote_ai(
            "nvidia",
            "Need 1000 boxes of M8 fasteners.",
            respond,
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("not authorized", response.json()["detail"])
        self.assertIn("Public API Endpoints", response.json()["detail"])
        self.assertNotIn("private provider diagnostics", response.text)
        self.assertEqual(len(requests), 1)

    def test_interpret_rejects_unsupported_remote_commercial_value(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Germany, in USD currency, "
            "with a 12 month warranty, factory mill certificate, and EXE delivery terms."
        )
        extraction = self._remote_sourcing_extraction()
        extraction["extractions"].append({
            "field": "commercial_terms.preferred_incoterm",
            "value": "EXE",
            "quote": "EXE",
        })
        requests: list[httpx.Request] = []

        def respond(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={
                "object": "chat.completion",
                "model": "openai-response-model",
                "choices": [{
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(extraction),
                        "refusal": None,
                    },
                }],
            })

        response = self._request_with_remote_ai("openai", prompt, respond)

        self.assertEqual(response.status_code, 502)
        self.assertIn("invalid output", response.json()["detail"])
        self.assertEqual(len(requests), 1)

    def test_interpret_reports_ungrounded_model_output_as_bad_gateway(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Germany in USD currency, "
            "12 month warranty, factory mill certificate, and maximum unit price 24 USD."
        )
        extraction = self._remote_sourcing_extraction()
        extraction["extractions"].append({
            "field": "pricing.target_unit_price",
            "value": "24",
            "quote": "maximum unit price 24 USD",
        })

        def respond(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={
                "object": "chat.completion",
                "model": "openai-response-model",
                "choices": [{
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(extraction),
                        "refusal": None,
                    },
                }],
            })

        response = self._request_with_remote_ai("openai", prompt, respond)
        self.assertEqual(response.status_code, 502)
        self.assertIn("invalid output", response.json()["detail"])

    def test_interpret_missing_required_field_must_be_declared_unknown(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Germany in USD currency, "
            "and factory mill certificate."
        )
        field = "commercial_terms.min_warranty_months"
        for declared in (False, True):
            with self.subTest(declared=declared):
                extraction = self._remote_sourcing_extraction()
                extraction["extractions"] = [
                    item for item in extraction["extractions"] if item["field"] != field
                ]
                extraction["unknown_fields"] = [field] if declared else []

                def respond(request: httpx.Request) -> httpx.Response:
                    return httpx.Response(200, json={
                        "object": "chat.completion",
                        "model": "openai-response-model",
                        "choices": [{
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": json.dumps(extraction),
                                "refusal": None,
                            },
                        }],
                    })

                response = self._request_with_remote_ai("openai", prompt, respond)
                self.assertEqual(response.status_code, 422 if declared else 502)
                self.assertIn(
                    "minimum warranty" if declared else "invalid output",
                    response.json()["detail"],
                )

    def test_interpret_invalid_explicit_controls_remain_unprocessable(self) -> None:
        requests: list[httpx.Request] = []

        def respond(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(500)

        response = self._request_with_remote_ai(
            "openai",
            "Need 1000 boxes of fasteners.",
            respond,
            {"commercial_terms": {"inspection_requirement": "INVALID"}},
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("supported value", response.json()["detail"])
        self.assertEqual(requests, [])

    def test_interpret_nlp_prompt_extracts_fasteners_specification(self) -> None:
        prompt = (
            "Procurement requirement: We need 1,000 boxes of M8x30 DIN 933 Grade 316 stainless steel "
            "hex cap bolts with ISO 965-1 6g tolerance. Must have ISO 9001, CE, and RoHS certifications. "
            "Target price $12.00/box, max $14.00 USD. Deliver to Berlin, Germany by 2026-12-08 under DDP terms."
        )
        res = self._request("POST", "/sourcing/interpret", json={"prompt": prompt})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("requirements", data)
        self.assertIn("parsed_fields", data)

        req = data["requirements"]
        self.assertIn("fastener", req["category"].lower())
        self.assertEqual(Decimal(str(req["quantity"]["target_quantity"])), Decimal("1000"))
        self.assertEqual(req["quantity"]["unit"].lower(), "boxes")
        self.assertEqual(Decimal(str(req["pricing"]["target_unit_price"])), Decimal("12.00"))
        self.assertEqual(Decimal(str(req["pricing"]["max_unit_price"])), Decimal("14.00"))
        self.assertEqual(req["pricing"]["currency"], "USD")
        self.assertEqual(req["delivery"]["destination_country_code"], "DE")

        specs = req["technical_specs"]
        self.assertTrue(any("316" in m for m in specs.get("materials", [])))
        self.assertIn("CE", specs.get("certifications", []))
        self.assertIn("RoHS", specs.get("certifications", []))

    def test_interpret_structured_overrides_priority(self) -> None:
        prompt = "Need 500 units of bolts at $10.00 each."
        overrides = {
            "quantity": {"target_quantity": "2500", "unit": "boxes"},
            "pricing": {"target_unit_price": "8.50", "max_unit_price": "9.50", "currency": "EUR"},
            "delivery": {"destination_country_code": "FR", "max_lead_time_days": 15},
        }
        res = self._request("POST", "/sourcing/interpret", json={"prompt": prompt, "structured_overrides": overrides})
        self.assertEqual(res.status_code, 200)
        req = res.json()["requirements"]

        self.assertEqual(Decimal(str(req["quantity"]["target_quantity"])), Decimal("2500"))
        self.assertEqual(req["quantity"]["unit"], "boxes")
        self.assertEqual(Decimal(str(req["pricing"]["target_unit_price"])), Decimal("8.50"))
        self.assertEqual(req["pricing"]["currency"], "EUR")
        self.assertEqual(req["delivery"]["destination_country_code"], "FR")
        self.assertEqual(req["delivery"]["max_lead_time_days"], 15)

    def test_interpret_empty_payload_rejects_missing_controls(self) -> None:
        res = self._request("POST", "/sourcing/interpret", json={})
        self.assertEqual(res.status_code, 422)
        self.assertIn("target quantity", res.json()["detail"])

    def test_interpret_long_prompt_within_limits(self) -> None:
        prompt = "Need 500 boxes of M8 bolts. " + ("Additional technical specifications and standard notes. " * 80)
        res = self._request("POST", "/sourcing/interpret", json={"prompt": prompt})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("requirements", data)

    # =========================================================================
    # 2. GET /sourcing/listings
    # =========================================================================

    def test_get_listings_nonexistent_filter_still_reports_unavailable(self) -> None:
        res = self._request("GET", "/sourcing/listings", params={"category": "NonExistentSector999"})
        self.assertEqual(res.status_code, 503)
        self.assertIn("Marketplace", res.json()["detail"])

    # =========================================================================
    # 7. Security, Auth, and Middleware
    # =========================================================================

    def test_unauthenticated_requests_rejected(self) -> None:
        # Clear dependency override to test live auth enforcement
        self._authenticate(actor=None)

        res = self._request("GET", "/sourcing/listings")
        self.assertEqual(res.status_code, 401)

        res = self._request("POST", "/sourcing/interpret", json={"prompt": "Fasteners"})
        self.assertEqual(res.status_code, 401)

    def test_request_body_size_limit_middleware(self) -> None:
        # Middleware limits body size to 16 KB
        huge_prompt = "A" * (20 * 1024)
        res = self._request("POST", "/sourcing/interpret", json={"prompt": huge_prompt})
        self.assertEqual(res.status_code, 413)
        self.assertIn("too large", res.json()["detail"].lower())


class SourcingAIInterpretationTests(unittest.TestCase):
    class Adapter:
        def __init__(self, response: dict[str, Any]) -> None:
            self.response = response
            self.request: dict[str, Any] | None = None

        def _call(
            self,
            context: Any,
            operation: str,
            schema: dict[str, Any],
            timeout: float,
            **kwargs: Any,
        ) -> dict[str, Any]:
            self.request = {
                "context": context,
                "operation": operation,
                "schema": schema,
                "timeout": timeout,
                **kwargs,
            }
            return self.response

    def _extraction(self) -> dict[str, Any]:
        return {
            "extractions": [
                {"field": "title", "value": "M8 fasteners", "quote": "M8 fasteners"},
                {"field": "category", "value": "Industrial Fasteners", "quote": "M8 fasteners"},
                {"field": "pricing.currency", "value": "USD", "quote": "USD currency"},
                {"field": "quantity.target_quantity", "value": "1000", "quote": "1000 boxes"},
                {"field": "quantity.unit", "value": "boxes", "quote": "1000 boxes"},
                {"field": "delivery.destination_country_code", "value": "DE", "quote": "Germany"},
                {"field": "commercial_terms.min_warranty_months", "value": "12", "quote": "12 month warranty"},
                {
                    "field": "commercial_terms.inspection_requirement",
                    "value": "FACTORY_MILL_CERTIFICATE",
                    "quote": "factory mill certificate",
                },
            ],
            "unknown_fields": [],
        }

    def test_structured_ai_fields_require_exact_grounded_evidence(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Berlin, Germany, USD currency, "
            "12 month warranty and factory mill certificate."
        )
        requests: list[httpx.Request] = []

        def respond(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={
                "object": "chat.completion",
                "model": "sourcing-test-model",
                "choices": [{
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(self._extraction()),
                        "refusal": None,
                    },
                }],
            })

        adapter = OpenAIChatCompletions(
            api_key=SecretStr("test-only-key"),
            model="sourcing-test-model",
            transport=httpx.MockTransport(respond),
        )

        requirements, parsed_fields = interpret_sourcing_requirements(adapter, prompt)

        request_payload = json.loads(requests[0].content)
        self.assertEqual(
            request_payload["response_format"]["json_schema"]["name"],
            "sourcing_requirements",
        )
        self.assertTrue(request_payload["response_format"]["json_schema"]["strict"])
        self.assertIn("at most one extraction per scalar field", requests[0].content.decode())
        self.assertIn(prompt, requests[0].content.decode())
        self.assertNotIn("test-only-key", requests[0].content.decode())
        self.assertEqual(requirements.quantity.target_quantity, Decimal("1000"))
        self.assertEqual(requirements.delivery.destination_country_code, "DE")
        self.assertEqual(requirements.commercial_terms.min_warranty_months, 12)
        self.assertIn("commercial_terms.inspection_requirement", parsed_fields)

        fabricated = self._extraction()
        fabricated["extractions"].append({
            "field": "pricing.max_unit_price",
            "value": "99.00",
            "quote": "USD currency",
        })
        with self.assertRaisesRegex(AIPermanentError, "ungrounded value"):
            interpret_sourcing_requirements(self.Adapter(fabricated), prompt)

    def test_identical_scalar_values_from_multiple_quotes_are_deduplicated(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Hamburg, Germany, USD currency, "
            "12 month warranty and factory mill certificate."
        )
        extraction = self._extraction()
        extraction["extractions"].append({
            "field": "delivery.destination_country_code",
            "value": "DE",
            "quote": "Hamburg",
        })

        requirements, parsed_fields = interpret_sourcing_requirements(self.Adapter(extraction), prompt)

        self.assertEqual(requirements.delivery.destination_country_code, "DE")
        self.assertEqual(parsed_fields.count("delivery.destination_country_code"), 1)

    def test_mumbai_quote_grounds_india_destination_country(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Mumbai, India, USD currency, "
            "12 month warranty and factory mill certificate."
        )
        extraction = self._extraction()
        extraction["extractions"] = [
            {
                **item,
                **({"value": "IN", "quote": "Mumbai"}
                   if item["field"] == "delivery.destination_country_code" else {}),
            }
            for item in extraction["extractions"]
        ]

        requirements, _ = interpret_sourcing_requirements(self.Adapter(extraction), prompt)

        self.assertEqual(requirements.delivery.destination_country_code, "IN")

    def test_product_descriptors_do_not_conflict_with_the_count_unit(self) -> None:
        prompt = (
            "Need 250 stainless steel water bottles delivered to Berlin, Germany, USD currency, "
            "12 month warranty and factory mill certificate."
        )
        extraction = self._extraction()
        extraction["extractions"] = [
            {
                **item,
                **({"value": "water bottles", "quote": "stainless steel water bottles"}
                   if item["field"] == "title" else {}),
                **({"value": "Water Bottles", "quote": "water bottles"}
                   if item["field"] == "category" else {}),
                **({"value": "250", "quote": "250 stainless steel water bottles"}
                   if item["field"] == "quantity.target_quantity" else {}),
                **({"value": "water bottles", "quote": "water bottles"}
                   if item["field"] == "quantity.unit" else {}),
            }
            for item in extraction["extractions"]
        ]
        extraction["extractions"].append({
            "field": "quantity.unit",
            "value": "bottles",
            "quote": "250 stainless steel water bottles",
        })
        extraction["unknown_fields"] = ["quantity.unit"]

        requirements, parsed_fields = interpret_sourcing_requirements(self.Adapter(extraction), prompt)

        self.assertEqual(requirements.quantity.unit, "bottles")
        self.assertEqual(parsed_fields.count("quantity.unit"), 1)

    def test_distinct_count_units_remain_rejected(self) -> None:
        prompt = (
            "Need 250 bottles delivered to Berlin, Germany, USD currency, 12 month warranty, "
            "factory mill certificate, packed in 5 boxes."
        )
        extraction = self._extraction()
        extraction["extractions"] = [
            {
                **item,
                **({"value": "bottles", "quote": "bottles"}
                   if item["field"] in {"title", "category"} else {}),
                **({"value": "250", "quote": "250 bottles"}
                   if item["field"] == "quantity.target_quantity" else {}),
                **({"value": "bottles", "quote": "250 bottles"}
                   if item["field"] == "quantity.unit" else {}),
            }
            for item in extraction["extractions"]
        ]
        extraction["extractions"].append({
            "field": "quantity.unit",
            "value": "boxes",
            "quote": "5 boxes",
        })
        extraction["unknown_fields"] = ["quantity.unit"]

        with self.assertRaisesRegex(AIPermanentError, "conflicting values"):
            interpret_sourcing_requirements(self.Adapter(extraction), prompt)

    def test_unknown_count_unit_is_not_matched_to_a_different_quantity(self) -> None:
        prompt = (
            "Need 250 boxes of M8 fasteners delivered to Berlin, Germany, USD currency, "
            "12 month warranty and factory mill certificate; also include 5 bottles for display samples."
        )
        extraction = self._extraction()
        extraction["extractions"] = [
            {
                **item,
                **({"value": "250", "quote": "250 boxes"}
                   if item["field"] == "quantity.target_quantity" else {}),
                **({"value": "bottles", "quote": "bottles"}
                   if item["field"] == "quantity.unit" else {}),
            }
            for item in extraction["extractions"]
        ]
        extraction["unknown_fields"] = ["quantity.unit"]

        with self.assertRaises(AIPermanentError) as raised:
            interpret_sourcing_requirements(self.Adapter(extraction), prompt)

        self.assertEqual(raised.exception.diagnostic_code, "AI_SOURCING_CONFLICTING_UNKNOWN")
        self.assertEqual(raised.exception.diagnostic_field, "quantity.unit")

    def test_conflicting_scalar_values_remain_rejected(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Berlin, Germany or Paris, France, "
            "USD currency, 12 month warranty and factory mill certificate."
        )
        extraction = self._extraction()
        extraction["extractions"].append({
            "field": "delivery.destination_country_code",
            "value": "FR",
            "quote": "France",
        })

        with self.assertRaisesRegex(AIPermanentError, "conflicting values") as raised:
            interpret_sourcing_requirements(self.Adapter(extraction), prompt)
        self.assertEqual(raised.exception.diagnostic_field, "delivery.destination_country_code")

    def test_unknown_required_commercial_fields_are_not_defaulted(self) -> None:
        prompt = "Need 1000 boxes of M8 fasteners delivered to Berlin, Germany, USD currency."
        extraction = self._extraction()
        extraction["extractions"] = [
            item for item in extraction["extractions"]
            if item["field"] not in {
                "commercial_terms.min_warranty_months",
                "commercial_terms.inspection_requirement",
            }
        ]
        extraction["unknown_fields"] = [
            "commercial_terms.min_warranty_months",
            "commercial_terms.inspection_requirement",
        ]

        with self.assertRaisesRegex(ValueError, "minimum warranty.*inspection requirement"):
            interpret_sourcing_requirements(self.Adapter(extraction), prompt)

    def test_unmarked_required_omission_has_safe_field_diagnostic(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Berlin, Germany, USD currency, "
            "12 month warranty and factory mill certificate."
        )
        extraction = self._extraction()
        extraction["extractions"] = [
            item for item in extraction["extractions"] if item["field"] != "quantity.unit"
        ]

        with self.assertRaisesRegex(AIPermanentError, "omitted required sourcing fields") as raised:
            interpret_sourcing_requirements(self.Adapter(extraction), prompt)

        self.assertEqual(raised.exception.diagnostic_code, "AI_SOURCING_REQUIRED_OMITTED")
        self.assertEqual(raised.exception.diagnostic_field, "quantity.unit")

    def test_explicit_price_currency_is_recovered_when_ai_omits_it(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Berlin, Germany; target price is USD 8 each; "
            "12 month warranty and factory mill certificate."
        )
        extraction = self._extraction()
        extraction["extractions"] = [
            item for item in extraction["extractions"] if item["field"] != "pricing.currency"
        ]

        requirements, parsed_fields = interpret_sourcing_requirements(self.Adapter(extraction), prompt)

        self.assertEqual(requirements.pricing.currency, "USD")
        self.assertIn("pricing.currency", parsed_fields)

    def test_explicit_minimum_warranty_is_recovered_when_ai_omits_it(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Berlin, Germany, USD currency, "
            "minimum warranty 12 months and factory mill certificate."
        )
        extraction = self._extraction()
        field = "commercial_terms.min_warranty_months"
        extraction["extractions"] = [
            item for item in extraction["extractions"] if item["field"] != field
        ]
        extraction["unknown_fields"] = [field]

        requirements, parsed_fields = interpret_sourcing_requirements(
            self.Adapter(extraction), prompt
        )

        self.assertEqual(requirements.commercial_terms.min_warranty_months, 12)
        self.assertIn(field, parsed_fields)

    def test_conflicting_explicit_warranties_are_not_recovered(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Berlin, Germany, USD currency, "
            "minimum warranty 12 months, or 24 month guarantee, and factory mill certificate."
        )
        extraction = self._extraction()
        field = "commercial_terms.min_warranty_months"
        extraction["extractions"] = [
            item for item in extraction["extractions"] if item["field"] != field
        ]

        with self.assertRaises(AIPermanentError) as raised:
            interpret_sourcing_requirements(self.Adapter(extraction), prompt)

        self.assertEqual(raised.exception.diagnostic_code, "AI_SOURCING_REQUIRED_OMITTED")
        self.assertEqual(raised.exception.diagnostic_field, field)

    def test_currency_is_not_inferred_from_symbol_when_ai_omits_it(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Berlin, Germany; target price is $8 each; "
            "12 month warranty and factory mill certificate."
        )
        extraction = self._extraction()
        extraction["extractions"] = [
            item for item in extraction["extractions"] if item["field"] != "pricing.currency"
        ]

        with self.assertRaises(AIPermanentError) as raised:
            interpret_sourcing_requirements(self.Adapter(extraction), prompt)

        self.assertEqual(raised.exception.diagnostic_code, "AI_SOURCING_REQUIRED_OMITTED")
        self.assertEqual(raised.exception.diagnostic_field, "pricing.currency")

    def test_explicit_price_currency_resolves_ai_unknown_marker(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Berlin, Germany; target price is USD 8 each; "
            "12 month warranty and factory mill certificate."
        )
        extraction = self._extraction()
        extraction["extractions"] = [
            item for item in extraction["extractions"] if item["field"] != "pricing.currency"
        ]
        extraction["unknown_fields"] = ["pricing.currency"]

        requirements, _ = interpret_sourcing_requirements(self.Adapter(extraction), prompt)

        self.assertEqual(requirements.pricing.currency, "USD")

    def test_conflicting_explicit_price_currencies_are_not_guessed(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Berlin, Germany; target price is USD 8 each, "
            "maximum price EUR 9 each; 12 month warranty and factory mill certificate."
        )
        extraction = self._extraction()
        extraction["extractions"] = [
            item for item in extraction["extractions"] if item["field"] != "pricing.currency"
        ]

        with self.assertRaises(AIPermanentError) as raised:
            interpret_sourcing_requirements(self.Adapter(extraction), prompt)

        self.assertEqual(raised.exception.diagnostic_code, "AI_SOURCING_REQUIRED_OMITTED")
        self.assertEqual(raised.exception.diagnostic_field, "pricing.currency")

    def test_extracted_and_unknown_collision_has_safe_field_diagnostic(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Berlin, Germany, USD currency, "
            "12 month warranty and factory mill certificate."
        )
        extraction = self._extraction()
        extraction["unknown_fields"] = ["title"]

        with self.assertRaisesRegex(AIPermanentError, "marked an extracted field as unknown") as raised:
            interpret_sourcing_requirements(self.Adapter(extraction), prompt)

        self.assertEqual(raised.exception.diagnostic_code, "AI_SOURCING_CONFLICTING_UNKNOWN")
        self.assertEqual(raised.exception.diagnostic_field, "title")

    def test_ungrounded_price_quantity_currency_and_destination_are_rejected(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Berlin, Germany, USD currency, "
            "12 month warranty and factory mill certificate."
        )
        invented_values = (
            ("pricing.max_unit_price", "99.00", "USD currency"),
            ("quantity.target_quantity", "900", "1000 boxes"),
            ("pricing.currency", "EUR", "USD currency"),
            ("delivery.destination_country_code", "FR", "Germany"),
        )
        for field, value, quote in invented_values:
            with self.subTest(field=field):
                extraction = self._extraction()
                extraction["extractions"].append({
                    "field": field,
                    "value": value,
                    "quote": quote,
                })
                with self.assertRaisesRegex(AIPermanentError, "ungrounded value") as raised:
                    interpret_sourcing_requirements(self.Adapter(extraction), prompt)
                self.assertEqual(raised.exception.diagnostic_field, field)

    def test_numeric_and_inspection_values_cannot_borrow_wrong_claim_roles(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Germany in USD currency, "
            "12 month warranty, factory mill certificate, total budget 12000 USD, "
            "and payment code NONE."
        )
        wrong_role_values = (
            ("pricing.target_unit_price", "12000", "total budget 12000 USD"),
            ("quantity.target_quantity", "12", "12 month warranty"),
            ("commercial_terms.min_warranty_months", "1000", "1000 boxes"),
            ("commercial_terms.inspection_requirement", "NONE", "NONE"),
        )
        for field, value, quote in wrong_role_values:
            with self.subTest(field=field):
                extraction = self._extraction()
                extraction["extractions"].append({
                    "field": "pricing.max_total_budget",
                    "value": "12000",
                    "quote": "total budget 12000 USD",
                })
                extraction["extractions"].append({
                    "field": field,
                    "value": value,
                    "quote": quote,
                })
                with self.assertRaisesRegex(AIPermanentError, "ungrounded value"):
                    interpret_sourcing_requirements(self.Adapter(extraction), prompt)

    def test_role_units_inspection_and_category_grounding(self) -> None:
        cases = (
            ("pricing.target_unit_price", "24", "maximum unit price 24 USD", False),
            ("pricing.max_unit_price", "24", "target unit price 24 USD", False),
            ("pricing.max_unit_price", "24", "maximum unit price 24 USD", True),
            ("pricing.target_unit_price", "24", "target unit price 24 USD", True),
            ("quantity.target_quantity", "24", "minimum warranty is 24 months", False),
            ("quantity.target_quantity", "24", "minimum 24 boxes", False),
            ("quantity.min_acceptable_quantity", "24", "minimum 24 boxes", True),
            ("quantity.min_acceptable_quantity", "24", "need 24 boxes", False),
            ("commercial_terms.min_warranty_months", "2", "2 years warranty", False),
            ("commercial_terms.min_warranty_months", "24", "minimum warranty is 24 months", True),
            (
                "commercial_terms.inspection_requirement", "PRE_SHIPMENT_THIRD_PARTY",
                "third-party pre-shipment freight booking is available", False,
            ),
            (
                "commercial_terms.inspection_requirement", "PRE_SHIPMENT_THIRD_PARTY",
                "third-party pre-shipment inspection", True,
            ),
            ("category", "Industrial Fasteners", "coffee", False),
            ("category", "Industrial Fasteners", "bolts", True),
            ("category", "Agricultural Commodities", "coffee", True),
        )
        for field, value, quote, expected in cases:
            with self.subTest(field=field, quote=quote):
                self.assertEqual(_grounded(field, value, quote), expected)

        extraction = self._extraction()
        quantity = next(item for item in extraction["extractions"] if item["field"] == "quantity.target_quantity")
        quantity["value"] = "24"
        quantity["quote"] = "24 boxes"
        prompt = (
            "Need a minimum 24 boxes of M8 fasteners delivered to Germany in USD currency, "
            "12 month warranty and factory mill certificate."
        )
        with self.assertRaisesRegex(AIPermanentError, "ungrounded value"):
            interpret_sourcing_requirements(self.Adapter(extraction), prompt)

    def test_original_clause_rejects_wrong_role_and_negated_claims(self) -> None:
        base = (
            "Need 1000 boxes of M8 fasteners delivered to Germany in USD currency, "
            "12 month warranty and factory mill certificate."
        )
        cases = (
            (
                base.replace("1000 boxes", "minimum order quantity is 24 boxes"),
                "quantity.target_quantity", "24", "minimum order quantity is 24 boxes",
            ),
            (
                base.replace("1000 boxes", "minimum order quantity is 24 boxes"),
                "quantity.target_quantity", "24", "24 boxes",
            ),
            (
                base.replace("factory mill certificate", "Do not require a third-party pre-shipment inspection"),
                "commercial_terms.inspection_requirement", "PRE_SHIPMENT_THIRD_PARTY",
                "Do not require a third-party pre-shipment inspection",
            ),
            (
                base.replace("M8 fasteners", "I don't want bolts; I need coffee"),
                "category", "Industrial Fasteners", "I don't want bolts",
            ),
            (
                base.replace("M8 fasteners", "I don't want bolts; I need coffee"),
                "category", "Industrial Fasteners", "bolts",
            ),
            (
                base.replace("factory mill certificate", "Do not require a third-party pre-shipment inspection"),
                "commercial_terms.inspection_requirement", "PRE_SHIPMENT_THIRD_PARTY",
                "third-party pre-shipment inspection",
            ),
        )
        for prompt, field, value, quote in cases:
            with self.subTest(field=field, quote=quote):
                extraction = self._extraction()
                if field == "category":
                    title = next(item for item in extraction["extractions"] if item["field"] == "title")
                    title.update(value="coffee", quote="coffee")
                if field == "quantity.target_quantity":
                    unit = next(item for item in extraction["extractions"] if item["field"] == "quantity.unit")
                    unit["quote"] = "24 boxes"
                item = next(item for item in extraction["extractions"] if item["field"] == field)
                item.update(value=value, quote=quote)
                with self.assertRaisesRegex(AIPermanentError, "ungrounded value"):
                    interpret_sourcing_requirements(self.Adapter(extraction), prompt)

    def test_explicit_unit_price_and_total_budget_roles_are_accepted(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Germany in USD currency, "
            "target price USD 12 per box, total budget 12000 USD, 12 month warranty, "
            "and factory mill certificate."
        )
        extraction = self._extraction()
        extraction["extractions"].extend([
            {
                "field": "pricing.target_unit_price",
                "value": "12",
                "quote": "target price USD 12 per box",
            },
            {
                "field": "pricing.max_total_budget",
                "value": "12000",
                "quote": "total budget 12000 USD",
            },
        ])

        requirements, _ = interpret_sourcing_requirements(self.Adapter(extraction), prompt)

        self.assertEqual(requirements.pricing.target_unit_price, Decimal("12"))
        self.assertEqual(requirements.pricing.max_total_budget, Decimal("12000"))

    def test_gemini_uses_the_same_grounded_structured_sourcing_contract(self) -> None:
        prompt = (
            "Need 1000 boxes of M8 fasteners delivered to Berlin, Germany, USD currency, "
            "12 month warranty and factory mill certificate."
        )
        requests: list[httpx.Request] = []

        def respond(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={
                "modelVersion": "gemini-test-model",
                "candidates": [{
                    "index": 0,
                    "finishReason": "STOP",
                    "content": {
                        "role": "model",
                        "parts": [{"text": json.dumps(self._extraction())}],
                    },
                }],
            })

        adapter = GeminiGenerateContent(
            api_key=SecretStr("test-only-key"),
            model="gemini-test-model",
            transport=httpx.MockTransport(respond),
        )

        requirements, _ = interpret_sourcing_requirements(adapter, prompt)

        request_payload = json.loads(requests[0].content)
        self.assertIn("responseJsonSchema", request_payload["generationConfig"])
        self.assertEqual(request_payload["generationConfig"]["responseMimeType"], "application/json")
        self.assertEqual(requirements.delivery.destination_country_code, "DE")
        self.assertNotIn("test-only-key", requests[0].content.decode())
