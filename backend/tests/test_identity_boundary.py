import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import jwt
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.requests import Request

from syncally.api.auth import (
    RefreshRequest,
    _decode_token,
    _encode_access_token,
    _hash_refresh_token,
    get_current_actor,
    refresh_access_token,
)
from syncally.application.identity import ActorContext
from syncally.config import Settings, settings
from syncally.infrastructure.models import Deal


class IdentityBoundaryTests(unittest.TestCase):
    def test_deal_requests_require_authentication(self) -> None:
        request = Request({"type": "http", "headers": []})

        with self.assertRaises(HTTPException) as raised:
            get_current_actor(request, credentials=None, db=Session())

        self.assertEqual(raised.exception.status_code, 401)

    def test_token_identity_is_used_even_when_claims_contain_untrusted_organizations(self) -> None:
        user_id = uuid4()
        token = jwt.encode(
            {
                "sub": str(user_id),
                "exp": datetime.now(UTC) + timedelta(minutes=5),
                "organization_ids": [str(uuid4())],
                "role": "ADMIN",
            },
            "t" * 32,
            algorithm="HS256",
        )

        original_secret = settings.jwt_secret
        try:
            settings.jwt_secret = "t" * 32
            self.assertEqual(_decode_token(token), user_id)
        finally:
            settings.jwt_secret = original_secret

    def test_actor_can_access_only_a_deal_party(self) -> None:
        member_org = uuid4()
        other_org = uuid4()
        actor = ActorContext(user_id=uuid4(), organization_ids=frozenset({member_org}))
        accessible = Deal(
            buyer_organization_id=member_org,
            seller_organization_id=uuid4(),
            status="DRAFT",
        )
        inaccessible = Deal(
            buyer_organization_id=other_org,
            seller_organization_id=uuid4(),
            status="DRAFT",
        )

        self.assertTrue(actor.can_access_deal(accessible))
        self.assertFalse(actor.can_access_deal(inaccessible))

    def test_development_identity_is_rejected_outside_local_environments(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(
                app_env="production",
                jwt_secret="a" * 32,
                dev_auth_user_id=str(uuid4()),
            )

    def test_production_requires_a_configured_secret(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(app_env="production")

    def test_omitting_app_env_keeps_production_authentication_defaults(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, jwt_secret="s" * 32, dev_auth_user_id=str(uuid4()))

        with self.assertRaises(ValidationError):
            Settings(_env_file=None, jwt_secret="weak")

    def test_production_requires_an_explicit_database_url(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, app_env="production", jwt_secret="s" * 32)

    def test_unsupported_jwt_algorithm_is_rejected_at_startup(self) -> None:
        with self.assertRaises(ValidationError) as raised:
            Settings(
                _env_file=None,
                app_env="development",
                jwt_algorithm="bogus",
                jwt_secret="s" * 32,
            )

        self.assertIn("JWT_ALGORITHM", str(raised.exception))

    def test_asymmetric_jwt_algorithm_is_rejected_with_only_a_shared_secret(self) -> None:
        with self.assertRaises(ValidationError) as raised:
            Settings(
                _env_file=None,
                app_env="development",
                jwt_algorithm="RS256",
                jwt_secret="s" * 32,
            )

        self.assertIn("JWT_ALGORITHM", str(raised.exception))

    def test_access_token_contains_access_type_and_expiry(self) -> None:
        original_secret = settings.jwt_secret
        try:
            settings.jwt_secret = "t" * 32
            token = _encode_access_token(uuid4())
            claims = jwt.decode(token, "t" * 32, algorithms=["HS256"])
        finally:
            settings.jwt_secret = original_secret

        self.assertEqual(claims["typ"], "access")
        self.assertIn("exp", claims)

    def test_refresh_token_hash_accepts_non_ascii_input(self) -> None:
        token_hash = _hash_refresh_token("refresh-token-✓")

        self.assertEqual(len(token_hash), 64)

    def test_expired_refresh_token_reuse_revokes_its_family(self) -> None:
        now = datetime.now(UTC)
        stored = SimpleNamespace(
            family_id=uuid4(),
            expires_at=now - timedelta(seconds=1),
            revoked_at=now - timedelta(seconds=2),
            replaced_by_id=None,
        )

        class FakeSession:
            def __init__(self) -> None:
                self.family_revocation_attempted = False

            def scalar(self, _query: object) -> SimpleNamespace:
                return stored

            def execute(self, _query: object) -> None:
                self.family_revocation_attempted = True

            def commit(self) -> None:
                pass

        db = FakeSession()
        with self.assertRaises(HTTPException) as raised:
            refresh_access_token(RefreshRequest(refresh_token="o" * 64), db)

        self.assertEqual(raised.exception.detail, "Refresh token reuse detected")
        self.assertTrue(db.family_revocation_attempted)

    def test_rotated_refresh_token_replay_preserves_its_replacement(self) -> None:
        stored = SimpleNamespace(
            family_id=uuid4(),
            replaced_by_id=uuid4(),
            revoked_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )

        class FakeSession:
            def __init__(self) -> None:
                self.family_revocation_attempted = False

            def scalar(self, _query: object) -> SimpleNamespace:
                return stored

            def execute(self, _query: object) -> None:
                self.family_revocation_attempted = True

        db = FakeSession()
        with self.assertRaises(HTTPException) as raised:
            refresh_access_token(RefreshRequest(refresh_token="o" * 64), db)

        self.assertEqual(raised.exception.detail, "Refresh token already rotated")
        self.assertFalse(db.family_revocation_attempted)

    def test_refresh_rotates_token_and_revokes_previous_token(self) -> None:
        user_id = uuid4()
        now = datetime.now(UTC)
        stored = SimpleNamespace(
            user_id=user_id,
            family_id=uuid4(),
            token_hash=None,
            expires_at=now + timedelta(days=1),
            revoked_at=None,
            replaced_by_id=None,
        )
        replacement_rows: list[object] = []

        class FakeSession:
            def scalar(self, _query: object) -> SimpleNamespace:
                return stored

            def add(self, row: object) -> None:
                replacement_rows.append(row)

            def flush(self) -> None:
                replacement_rows[0].id = uuid4()  # type: ignore[attr-defined]

            def commit(self) -> None:
                pass

        with (
            patch("syncally.api.auth.resolve_actor", return_value=SimpleNamespace(user_id=user_id)),
            patch("syncally.api.auth.secrets.token_urlsafe", return_value="r" * 64),
            patch("syncally.api.auth.datetime") as mocked_datetime,
        ):
            original_secret = settings.jwt_secret
            try:
                settings.jwt_secret = "t" * 32
                mocked_datetime.now.return_value = now
                result = refresh_access_token(RefreshRequest(refresh_token="o" * 64), FakeSession())
            finally:
                settings.jwt_secret = original_secret

        self.assertEqual(result.refresh_token, "r" * 64)
        self.assertIsNotNone(stored.revoked_at)
        self.assertEqual(len(replacement_rows), 1)
        self.assertEqual(stored.replaced_by_id, replacement_rows[0].id)

    def test_failed_access_token_encoding_does_not_rotate_refresh_token(self) -> None:
        user_id = uuid4()
        now = datetime.now(UTC)
        stored = SimpleNamespace(
            user_id=user_id,
            family_id=uuid4(),
            token_hash=None,
            expires_at=now + timedelta(days=1),
            revoked_at=None,
            replaced_by_id=None,
        )

        class FakeSession:
            def __init__(self) -> None:
                self.committed = False

            def scalar(self, _query: object) -> SimpleNamespace:
                return stored

            def add(self, _row: object) -> None:
                pass

            def flush(self) -> None:
                pass

            def commit(self) -> None:
                self.committed = True

        db = FakeSession()
        with (
            patch("syncally.api.auth.resolve_actor", return_value=SimpleNamespace(user_id=user_id)),
            patch(
                "syncally.api.auth._encode_access_token",
                side_effect=jwt.InvalidAlgorithmError("unsupported"),
            ),
            patch("syncally.api.auth.datetime") as mocked_datetime,
        ):
            mocked_datetime.now.return_value = now
            with self.assertRaises(jwt.InvalidAlgorithmError):
                refresh_access_token(RefreshRequest(refresh_token="o" * 64), db)

        self.assertFalse(db.committed)
        self.assertIsNone(stored.revoked_at)
        self.assertIsNone(stored.replaced_by_id)
