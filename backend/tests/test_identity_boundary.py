import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import jwt
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from starlette.requests import Request

from syncally.api.auth import (
    RefreshRequest,
    _decode_token,
    _derive_rotated_refresh_token,
    _encode_access_token,
    _hash_refresh_token,
    _revoke_family,
    get_current_actor,
    refresh_access_token,
)
from syncally.application.identity import ActorContext
from syncally.config import Settings, settings
from syncally.infrastructure.models import Deal


class IdentityBoundaryTests(unittest.TestCase):
    def test_settings_load_backend_env_independent_of_working_directory(self) -> None:
        configured_env_file = Path(Settings.model_config["env_file"])

        self.assertEqual(configured_env_file, Path(__file__).resolve().parents[1] / ".env")

    def test_family_revocation_locks_rows_before_updating_them(self) -> None:
        class FakeSession:
            def __init__(self) -> None:
                self.statements: list[object] = []
                self.committed = False

            def execute(self, statement: object) -> None:
                self.statements.append(statement)

            def commit(self) -> None:
                self.committed = True

        db = FakeSession()
        _revoke_family(db, uuid4(), datetime.now(UTC))

        self.assertTrue(getattr(db.statements[0], "is_select", False))
        select_sql = str(db.statements[0].compile(dialect=postgresql.dialect()))
        self.assertIn("FOR UPDATE", select_sql)
        self.assertTrue(getattr(db.statements[1], "is_update", False))
        self.assertTrue(db.committed)

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
                _env_file=None,
                app_env="production",
                database_url="postgresql+psycopg://configured.example/syncally",
                jwt_secret="a" * 32,
                dev_auth_user_id=str(uuid4()),
            )

    def test_production_requires_a_configured_secret(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                app_env="production",
                database_url="postgresql+psycopg://configured.example/syncally",
            )

    def test_clean_checkout_settings_use_local_defaults(self) -> None:
        local_settings = Settings(_env_file=None)

        self.assertEqual(local_settings.app_env, "development")
        self.assertEqual(local_settings.database_url, "postgresql+psycopg://localhost:5432/syncally")

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

    def test_replay_with_future_revocation_timestamp_is_rejected(self) -> None:
        now = datetime.now(UTC)
        stored = SimpleNamespace(
            id=uuid4(),
            user_id=uuid4(),
            family_id=uuid4(),
            replaced_by_id=uuid4(),
            revoked_at=now + timedelta(seconds=1),
            expires_at=now + timedelta(days=1),
        )
        replacement = SimpleNamespace(
            family_id=stored.family_id,
            revoked_at=now,
        )

        class FakeSession:
            def __init__(self) -> None:
                self.family_revocation_attempted = False
                self.scalar_calls = 0

            def scalar(self, _query: object) -> SimpleNamespace:
                self.scalar_calls += 1
                return stored if self.scalar_calls == 1 else replacement

            def execute(self, _query: object) -> None:
                self.family_revocation_attempted = True

            def commit(self) -> None:
                pass

        db = FakeSession()
        with patch("syncally.api.auth.datetime") as mocked_datetime:
            mocked_datetime.now.return_value = now
            with self.assertRaises(HTTPException) as raised:
                refresh_access_token(RefreshRequest(refresh_token="o" * 64), db)

        self.assertEqual(raised.exception.detail, "Refresh token reuse detected")
        self.assertTrue(db.family_revocation_attempted)

    def test_refresh_rotates_token_and_revokes_previous_token(self) -> None:
        user_id = uuid4()
        now = datetime.now(UTC)
        token_id = uuid4()
        stored = SimpleNamespace(
            id=token_id,
            user_id=user_id,
            family_id=uuid4(),
            token_hash=None,
            expires_at=now + timedelta(days=1),
            revoked_at=None,
            replaced_by_id=None,
        )
        replacement_rows: list[object] = []

        class FakeSession:
            def __init__(self) -> None:
                self.committed = False

            def scalar(self, _query: object) -> SimpleNamespace:
                return stored

            def add(self, row: object) -> None:
                replacement_rows.append(row)

            def flush(self) -> None:
                replacement_rows[0].id = uuid4()  # type: ignore[attr-defined]

            def commit(self) -> None:
                self.committed = True

        db = FakeSession()
        with (
            patch("syncally.api.auth.resolve_actor", return_value=SimpleNamespace(user_id=user_id)),
            patch("syncally.api.auth.datetime") as mocked_datetime,
        ):
            original_secret = settings.jwt_secret
            try:
                settings.jwt_secret = "t" * 32
                mocked_datetime.now.return_value = now
                result = refresh_access_token(RefreshRequest(refresh_token="o" * 64), db)
                expected = _derive_rotated_refresh_token(token_id)
            finally:
                settings.jwt_secret = original_secret

        self.assertEqual(result.refresh_token, expected)
        self.assertTrue(db.committed)
        self.assertIsNotNone(stored.revoked_at)
        self.assertEqual(len(replacement_rows), 1)
        self.assertEqual(stored.replaced_by_id, replacement_rows[0].id)
        self.assertEqual(
            replacement_rows[0].token_hash,  # type: ignore[attr-defined]
            _hash_refresh_token(result.refresh_token),
        )

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
