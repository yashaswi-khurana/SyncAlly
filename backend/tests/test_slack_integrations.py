from __future__ import annotations

import asyncio
import hashlib
import runpy
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import httpx
from alembic.migration import MigrationContext
from alembic.operations import Operations
from cryptography.fernet import Fernet
from fastapi import HTTPException
from sqlalchemy import Column, DateTime, MetaData, String, Table, create_engine, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api import integrations
from syncally.application.identity import ActorContext
from syncally.infrastructure.integrations.slack import (
    SLACK_ACCESS_URL,
    SLACK_BOT_SCOPES,
    SlackIntegrationError,
    SlackOAuthClient,
    SlackTokenCipher,
)
from syncally.infrastructure.models import (
    AuditEvent,
    Base,
    Organization,
    OrganizationMember,
    SlackDealSubscription,
    SlackInstallation,
    SlackLinkChallenge,
    SlackNotificationDelivery,
    SlackOAuthState,
    SlackUserLink,
    User,
)
from syncally.infrastructure.models.base import UUID_TYPE

FERNET_KEY = Fernet.generate_key().decode("ascii")


class _FakeOAuth:
    def __init__(self, *, exchange_error: Exception | None = None, revoke_error: Exception | None = None) -> None:
        self.exchange_error = exchange_error
        self.revoke_error = revoke_error
        self.exchanged_codes: list[str] = []
        self.revoked_tokens: list[str] = []
        self.granted_scopes = SLACK_BOT_SCOPES

    def authorization_url(self, state: str) -> str:
        return f"https://slack.test/authorize?state={state}"

    async def exchange_code(self, code: str):
        self.exchanged_codes.append(code)
        if self.exchange_error:
            raise self.exchange_error
        from syncally.infrastructure.integrations.slack import SlackOAuthResult

        return SlackOAuthResult(
            workspace_id="T-workspace",
            workspace_name="Acme Slack",
            bot_user_id="B-bot",
            access_token="xoxb-secret-token",
            granted_scopes=self.granted_scopes,
        )

    async def revoke(self, token: str) -> None:
        self.revoked_tokens.append(token)
        if self.revoke_error:
            raise self.revoke_error


class SlackIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine, expire_on_commit=False)
        self.user = User(email="admin@example.com", display_name="Admin", status="ACTIVE")
        self.member_user = User(email="member@example.com", display_name="Member", status="ACTIVE")
        self.org = Organization(legal_name="Acme", country_code="US", status="ACTIVE")
        self.other_org = Organization(legal_name="Other", country_code="US", status="ACTIVE")
        self.db.add_all([self.user, self.member_user, self.org, self.other_org])
        self.db.flush()
        self.db.add_all([
            OrganizationMember(
                organization_id=self.org.id, user_id=self.user.id, role="ADMIN", status="ACTIVE", capabilities=[], permissions=["org.members.manage"]
            ),
            OrganizationMember(
                organization_id=self.org.id, user_id=self.member_user.id, role="MEMBER", status="ACTIVE", capabilities=[]
            ),
            OrganizationMember(
                organization_id=self.other_org.id, user_id=self.user.id, role="ADMIN", status="ACTIVE", capabilities=[], permissions=["org.members.manage"]
            ),
        ])
        self.db.commit()
        self.admin = ActorContext(user_id=self.user.id, organization_ids=frozenset({self.org.id, self.other_org.id}))
        self.member = ActorContext(user_id=self.member_user.id, organization_ids=frozenset({self.org.id}))
        self.fake_oauth = _FakeOAuth()
        self.patches = [
            patch.object(integrations, "_configured", return_value=True),
            patch.object(integrations, "_oauth_client", return_value=self.fake_oauth),
            patch.object(integrations, "_cipher", return_value=SlackTokenCipher(FERNET_KEY)),
        ]
        for patcher in self.patches:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in reversed(self.patches):
            patcher.stop()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _state(self, *, org_id=None, user_id=None, expires_at=None) -> str:
        raw = f"state-{uuid4()}"
        self.db.add(SlackOAuthState(
            state_hash=hashlib.sha256(raw.encode()).hexdigest(),
            organization_id=org_id or self.org.id,
            user_id=user_id or self.user.id,
            created_at=datetime.now(UTC),
            expires_at=expires_at or datetime.now(UTC) + timedelta(minutes=10),
        ))
        self.db.commit()
        return raw

    def _installation(self, organization_id, workspace_id="T-workspace") -> SlackInstallation:
        row = SlackInstallation(
            id=uuid4(), organization_id=organization_id, workspace_id=workspace_id,
            workspace_name="Acme Slack", bot_user_id="B-bot",
            encrypted_bot_token=SlackTokenCipher(FERNET_KEY).encrypt("existing-token"),
            granted_scopes=list(SLACK_BOT_SCOPES), status="CONNECTED",
            connected_by_user_id=self.user.id, connected_at=datetime.now(UTC),
        )
        self.db.add(row)
        self.db.commit()
        return row

    def test_start_requires_org_administration_and_generates_scoped_one_use_state(self) -> None:
        with self.assertRaises(HTTPException) as denied:
            integrations.start_slack_oauth(self.org.id, self.member, self.db)
        self.assertEqual(denied.exception.status_code, 403)

        result = integrations.start_slack_oauth(self.org.id, self.admin, self.db)
        state = parse_qs(urlparse(result["authorization_url"]).query)["state"][0]
        stored = self.db.scalar(select(SlackOAuthState))
        self.assertEqual(stored.state_hash, hashlib.sha256(state.encode()).hexdigest())
        self.assertNotEqual(stored.state_hash, state)
        self.assertLessEqual(stored.expires_at - stored.created_at, timedelta(minutes=10))

    def test_status_requires_org_administration(self) -> None:
        with self.assertRaises(HTTPException) as denied:
            integrations.get_slack_connection(self.org.id, self.member, self.db)
        self.assertEqual(denied.exception.status_code, 403)
        status = integrations.get_slack_connection(self.org.id, self.admin, self.db)
        self.assertTrue(status.configured)
        self.assertFalse(status.connected)

    def test_account_link_status_is_self_only_and_available_to_org_members(self) -> None:
        missing = integrations.get_slack_account_link_status(self.org.id, self.member, self.db)
        self.assertFalse(missing.workspace_connected)
        self.assertFalse(missing.account_linked)

        installation = self._installation(self.org.id)
        self.db.add(SlackUserLink(
            id=uuid4(), installation_id=installation.id, organization_id=self.org.id,
            workspace_id=installation.workspace_id, slack_user_id="U-admin",
            user_id=self.user.id, created_at=datetime.now(UTC),
        ))
        self.db.commit()
        unlinked = integrations.get_slack_account_link_status(self.org.id, self.member, self.db)
        self.assertTrue(unlinked.workspace_connected)
        self.assertFalse(unlinked.account_linked)

        self.db.add(SlackUserLink(
            id=uuid4(), installation_id=installation.id, organization_id=self.org.id,
            workspace_id=installation.workspace_id, slack_user_id="U-member",
            user_id=self.member_user.id, created_at=datetime.now(UTC),
        ))
        self.db.commit()
        linked = integrations.get_slack_account_link_status(self.org.id, self.member, self.db)
        self.assertTrue(linked.workspace_connected)
        self.assertTrue(linked.account_linked)

        with self.assertRaises(HTTPException) as denied:
            integrations.get_slack_account_link_status(uuid4(), self.member, self.db)
        self.assertEqual(denied.exception.status_code, 404)

    def test_oauth_adapter_requests_only_minimum_scopes_and_no_history(self) -> None:
        client = SlackOAuthClient(client_id="id", client_secret="secret", redirect_uri="https://app/callback")
        query = parse_qs(urlparse(client.authorization_url("opaque-state")).query)
        self.assertEqual(query["scope"], [",".join(SLACK_BOT_SCOPES)])
        self.assertNotIn("channels:history", query["scope"][0])
        self.assertNotIn("groups:history", query["scope"][0])

    def test_expired_unknown_and_replayed_states_never_exchange_code(self) -> None:
        expired = self._state(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        unknown = "not-a-saved-state"
        for state in (expired, unknown):
            response = asyncio.run(integrations.slack_oauth_callback(state=state, code="code", error=None, db=self.db))
            self.assertIn("integration=failed", response.headers["location"])
        fresh = self._state()
        first = asyncio.run(integrations.slack_oauth_callback(state=fresh, code="code", error=None, db=self.db))
        second = asyncio.run(integrations.slack_oauth_callback(state=fresh, code="code", error=None, db=self.db))
        self.assertIn("integration=connected", first.headers["location"])
        self.assertIn("integration=failed", second.headers["location"])
        self.assertEqual(self.fake_oauth.exchanged_codes, ["code"])

    def test_callback_rechecks_authorization_after_provider_exchange(self) -> None:
        state = self._state()
        self.db.query(OrganizationMember).filter_by(organization_id=self.org.id, user_id=self.user.id).one().status = "REVOKED"
        self.db.commit()
        response = asyncio.run(integrations.slack_oauth_callback(state=state, code="code", error=None, db=self.db))
        self.assertIn("integration=authorization_changed", response.headers["location"])
        self.assertIsNone(self.db.scalar(select(SlackInstallation)))
        self.assertEqual(self.fake_oauth.revoked_tokens, ["xoxb-secret-token"])

    def test_under_scoped_grant_is_rejected_and_revoked_if_workspace_is_unmapped(self) -> None:
        self.fake_oauth.granted_scopes = ("chat:write",)
        state = self._state()
        response = asyncio.run(integrations.slack_oauth_callback(state=state, code="code", error=None, db=self.db))
        self.assertIn("integration=failed", response.headers["location"])
        self.assertIsNone(self.db.scalar(select(SlackInstallation)))
        self.assertEqual(self.fake_oauth.revoked_tokens, ["xoxb-secret-token"])

    def test_connected_org_rejects_and_revokes_new_unmapped_workspace(self) -> None:
        existing = self._installation(self.org.id, workspace_id="T-existing")
        state = self._state()
        response = asyncio.run(integrations.slack_oauth_callback(state=state, code="code", error=None, db=self.db))
        self.assertIn("integration=already_connected", response.headers["location"])
        self.assertEqual(self.fake_oauth.revoked_tokens, ["xoxb-secret-token"])
        self.db.refresh(existing)
        self.assertEqual(existing.workspace_id, "T-existing")
        self.assertEqual(SlackTokenCipher(FERNET_KEY).decrypt(existing.encrypted_bot_token), "existing-token")

    def test_connected_org_does_not_revoke_already_mapped_workspace(self) -> None:
        existing = self._installation(self.org.id, workspace_id="T-workspace")
        state = self._state()
        response = asyncio.run(integrations.slack_oauth_callback(state=state, code="code", error=None, db=self.db))
        self.assertIn("integration=already_connected", response.headers["location"])
        self.assertEqual(self.fake_oauth.revoked_tokens, [])
        self.db.refresh(existing)
        self.assertEqual(SlackTokenCipher(FERNET_KEY).decrypt(existing.encrypted_bot_token), "existing-token")

    def test_success_persists_encrypted_token_and_audit_without_returning_secret(self) -> None:
        state = self._state()
        response = asyncio.run(integrations.slack_oauth_callback(state=state, code="code", error=None, db=self.db))
        installation = self.db.scalar(select(SlackInstallation))
        self.assertIn("integration=connected", response.headers["location"])
        self.assertNotEqual(installation.encrypted_bot_token, "xoxb-secret-token")
        self.assertEqual(SlackTokenCipher(FERNET_KEY).decrypt(installation.encrypted_bot_token), "xoxb-secret-token")
        self.assertNotIn("xoxb-secret-token", repr(integrations._connection_response(installation)))
        event = self.db.scalar(select(AuditEvent).where(AuditEvent.event_type == "integration.connected"))
        self.assertEqual(event.payload["organization_id"], str(self.org.id))
        self.assertEqual(event.payload["workspace_id"], "T-workspace")
        self.assertNotIn("token", str(event.payload).lower())

    def test_workspace_already_mapped_to_another_org_is_rejected(self) -> None:
        self._installation(self.org.id)
        existing = self.db.scalar(select(SlackInstallation).where(SlackInstallation.organization_id == self.org.id))
        state = self._state(org_id=self.other_org.id)
        response = asyncio.run(integrations.slack_oauth_callback(state=state, code="code", error=None, db=self.db))
        self.assertIn("integration=workspace_in_use", response.headers["location"])
        self.assertEqual(self.fake_oauth.revoked_tokens, [])
        self.db.refresh(existing)
        self.assertEqual(existing.status, "CONNECTED")
        self.assertEqual(SlackTokenCipher(FERNET_KEY).decrypt(existing.encrypted_bot_token), "existing-token")
        self.assertEqual(self.db.scalar(select(SlackInstallation).where(SlackInstallation.organization_id == self.other_org.id)), None)

    def test_integrity_failure_revokes_unstored_unmapped_token(self) -> None:
        state = self._state()
        original_commit = self.db.commit
        commit_count = 0

        def commit_with_installation_conflict() -> None:
            nonlocal commit_count
            commit_count += 1
            if commit_count == 1:
                original_commit()
                return
            raise IntegrityError("insert", {}, RuntimeError("duplicate mapping"))

        with patch.object(self.db, "commit", side_effect=commit_with_installation_conflict):
            response = asyncio.run(
                integrations.slack_oauth_callback(
                    state=state, code="code", error=None, db=self.db
                )
            )

        self.assertIn("integration=workspace_in_use", response.headers["location"])
        self.assertEqual(self.fake_oauth.revoked_tokens, ["xoxb-secret-token"])
        self.assertIsNone(self.db.scalar(select(SlackInstallation)))

    def test_exchange_failure_does_not_persist_connection(self) -> None:
        self.fake_oauth.exchange_error = SlackIntegrationError("provider details")
        state = self._state()
        response = asyncio.run(integrations.slack_oauth_callback(state=state, code="code", error=None, db=self.db))
        self.assertIn("integration=failed", response.headers["location"])
        self.assertIsNone(self.db.scalar(select(SlackInstallation)))
        self.assertIsNotNone(self.db.scalar(select(SlackOAuthState)).consumed_at)

    def test_disconnect_requires_admin_and_provider_failure_preserves_connection(self) -> None:
        installation = self._installation(self.org.id)
        with self.assertRaises(HTTPException) as denied:
            asyncio.run(integrations.disconnect_slack(self.org.id, self.member, self.db))
        self.assertEqual(denied.exception.status_code, 403)

        self.fake_oauth.revoke_error = SlackIntegrationError("provider details")
        with self.assertRaises(HTTPException) as failed:
            asyncio.run(integrations.disconnect_slack(self.org.id, self.admin, self.db))
        self.assertEqual(failed.exception.status_code, 502)
        self.db.refresh(installation)
        self.assertEqual(installation.status, "CONNECTED")
        self.assertIsNotNone(installation.encrypted_bot_token)

    def test_disconnect_revokes_token_erases_credential_and_audits(self) -> None:
        installation = self._installation(self.org.id)
        response = asyncio.run(integrations.disconnect_slack(self.org.id, self.admin, self.db))
        self.db.refresh(installation)
        self.assertEqual(self.fake_oauth.revoked_tokens, ["existing-token"])
        self.assertEqual(installation.status, "DISCONNECTED")
        self.assertIsNone(installation.encrypted_bot_token)
        self.assertIsNotNone(installation.disconnected_at)
        self.assertFalse(response.connected)
        self.assertIsNotNone(self.db.scalar(select(AuditEvent).where(AuditEvent.event_type == "integration.disconnected")))

    def test_disconnect_clears_user_links_and_challenges_only_after_revoke(self) -> None:
        installation = self._installation(self.org.id)
        now = datetime.now(UTC)
        link = SlackUserLink(
            id=uuid4(), installation_id=installation.id, organization_id=self.org.id,
            workspace_id=installation.workspace_id, slack_user_id="U-person",
            user_id=self.user.id, created_at=now,
        )
        challenge = SlackLinkChallenge(
            id=uuid4(), event_id="Ev-link", installation_id=installation.id,
            organization_id=self.org.id, workspace_id=installation.workspace_id,
            slack_user_id="U-person", code_hash=hashlib.sha256(b"pending").hexdigest(),
            encrypted_code=SlackTokenCipher(FERNET_KEY).encrypt("pending-code"),
            expires_at=now + timedelta(minutes=5), attempts=0,
        )
        subscription = SlackDealSubscription(
            id=uuid4(), installation_id=installation.id, organization_id=self.org.id,
            workspace_id=installation.workspace_id, slack_user_id="U-person",
            user_id=self.user.id, deal_id=uuid4(), channel_id="C-channel",
            thread_ts="125.000", created_at=now,
        )
        delivery = SlackNotificationDelivery(
            id=uuid4(), source_event_id=uuid4(), subscription_id=subscription.id,
            status="PENDING", attempts=0, available_at=now,
        )
        self.db.add_all([link, challenge, subscription, delivery])
        self.db.commit()

        self.fake_oauth.revoke_error = SlackIntegrationError("provider details")
        with self.assertRaises(HTTPException):
            asyncio.run(integrations.disconnect_slack(self.org.id, self.admin, self.db))
        self.assertIsNotNone(self.db.get(SlackUserLink, link.id))
        self.assertIsNotNone(self.db.get(SlackLinkChallenge, challenge.id))
        self.assertIsNotNone(self.db.get(SlackDealSubscription, subscription.id))
        self.assertIsNotNone(self.db.get(SlackNotificationDelivery, delivery.id))

        self.fake_oauth.revoke_error = None
        asyncio.run(integrations.disconnect_slack(self.org.id, self.admin, self.db))
        self.assertIsNone(self.db.get(SlackUserLink, link.id))
        self.assertIsNone(self.db.get(SlackLinkChallenge, challenge.id))
        self.assertIsNone(self.db.get(SlackDealSubscription, subscription.id))
        self.assertIsNone(self.db.get(SlackNotificationDelivery, delivery.id))

    def test_schema_rejects_invalid_lifecycle_and_duplicate_active_mappings(self) -> None:
        self._installation(self.org.id)
        invalid = SlackInstallation(
            id=uuid4(), organization_id=self.other_org.id, workspace_id="another",
            workspace_name="Other", bot_user_id="B-other", encrypted_bot_token=None,
            granted_scopes=[], status="CONNECTED", connected_by_user_id=self.user.id,
            connected_at=datetime.now(UTC),
        )
        self.db.add(invalid)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

        duplicate_workspace = SlackInstallation(
            id=uuid4(), organization_id=self.other_org.id, workspace_id="T-workspace",
            workspace_name="Other", bot_user_id="B-other",
            encrypted_bot_token=SlackTokenCipher(FERNET_KEY).encrypt("other-token"),
            granted_scopes=[], status="CONNECTED", connected_by_user_id=self.user.id,
            connected_at=datetime.now(UTC),
        )
        self.db.add(duplicate_workspace)
        with self.assertRaises(IntegrityError):
            self.db.commit()

    def test_alembic_migration_creates_and_drops_slack_schema(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:")
        metadata = MetaData()
        Table("organizations", metadata, Column("id", UUID_TYPE, primary_key=True))
        Table("users", metadata, Column("id", UUID_TYPE, primary_key=True))
        metadata.create_all(engine)
        migration_path = (
            Path(__file__).parents[1]
            / "alembic"
            / "versions"
            / "0033_slack_integrations.py"
        )
        migration = runpy.run_path(str(migration_path))

        with engine.begin() as connection:
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                migration["upgrade"]()

        inspector = inspect(engine)
        self.assertIn("slack_installations", inspector.get_table_names())
        self.assertIn("slack_oauth_states", inspector.get_table_names())
        self.assertEqual(
            {index["name"] for index in inspector.get_indexes("slack_installations")},
            {"uq_slack_installation_org_connected", "uq_slack_installation_workspace_connected"},
        )
        self.assertEqual(
            {constraint["name"] for constraint in inspector.get_check_constraints("slack_installations")},
            {"ck_slack_installation_status", "ck_slack_installation_credential_lifecycle"},
        )

        with engine.begin() as connection:
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                migration["downgrade"]()
        self.assertNotIn("slack_installations", inspect(engine).get_table_names())
        self.assertNotIn("slack_oauth_states", inspect(engine).get_table_names())
        engine.dispose()

    def test_slack_events_migration_upgrades_0033_and_downgrades_to_0033(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:")
        metadata = MetaData()
        Table("organizations", metadata, Column("id", UUID_TYPE, primary_key=True))
        Table("users", metadata, Column("id", UUID_TYPE, primary_key=True))
        Table("deals", metadata, Column("id", UUID_TYPE, primary_key=True))
        Table(
            "outbox_events", metadata,
            Column("id", UUID_TYPE, primary_key=True),
            Column("event_type", String(128), nullable=False),
            Column("created_at", DateTime(timezone=True), nullable=False),
        )
        metadata.create_all(engine)
        versions = Path(__file__).parents[1] / "alembic" / "versions"
        migration_0033 = runpy.run_path(str(versions / "0033_slack_integrations.py"))
        migration_0034 = runpy.run_path(str(versions / "0034_slack_events_and_links.py"))
        migration_0035 = runpy.run_path(str(versions / "0035_slack_deal_subscriptions.py"))

        for migration in (migration_0033, migration_0034, migration_0035):
            with engine.begin() as connection:
                context = MigrationContext.configure(connection)
                with Operations.context(context):
                    migration["upgrade"]()

        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        self.assertTrue({
            "slack_events", "slack_user_links", "slack_link_challenges",
            "slack_deal_subscriptions", "slack_notification_deliveries",
        }.issubset(tables))
        self.assertEqual(
            {index["name"] for index in inspector.get_indexes("slack_events")},
            {"ix_slack_events_pending", "ix_slack_events_retention"},
        )
        self.assertIn(
            {"event_id"},
            [set(constraint["column_names"]) for constraint in inspector.get_unique_constraints("slack_events")],
        )
        self.assertEqual(
            {constraint["name"] for constraint in inspector.get_check_constraints("slack_events")},
            {"ck_slack_event_status"},
        )
        self.assertEqual(
            {constraint["name"] for constraint in inspector.get_unique_constraints("slack_user_links")},
            {"uq_slack_user_link_slack_identity", "uq_slack_user_link_syncally_identity"},
        )
        self.assertEqual(
            {index["name"] for index in inspector.get_indexes("slack_link_challenges")},
            {"ix_slack_link_challenges_expires_at"},
        )
        challenge_uniques = inspector.get_unique_constraints("slack_link_challenges")
        self.assertEqual(
            {frozenset(constraint["column_names"]) for constraint in challenge_uniques},
            {frozenset({"code_hash"}), frozenset({"event_id"})},
        )
        encrypted_code_column = next(
            column for column in inspector.get_columns("slack_link_challenges")
            if column["name"] == "encrypted_code"
        )
        self.assertTrue(encrypted_code_column["nullable"])
        self.assertEqual(
            {constraint["name"] for constraint in inspector.get_unique_constraints("slack_deal_subscriptions")},
            {"uq_slack_deal_subscription_thread"},
        )
        self.assertEqual(
            {constraint["name"] for constraint in inspector.get_unique_constraints("slack_notification_deliveries")},
            {"uq_slack_notification_source_subscription"},
        )
        self.assertEqual(
            {index["name"] for index in inspector.get_indexes("slack_notification_deliveries")},
            {"ix_slack_notification_deliveries_pending", "ix_slack_notification_deliveries_retention"},
        )
        self.assertEqual(
            {constraint["name"] for constraint in inspector.get_check_constraints("slack_notification_deliveries")},
            {"ck_slack_notification_delivery_status"},
        )
        for table in ("slack_events", "slack_user_links", "slack_link_challenges"):
            self.assertTrue(inspector.get_foreign_keys(table), table)
        for table in ("slack_deal_subscriptions", "slack_notification_deliveries"):
            self.assertTrue(inspector.get_foreign_keys(table), table)

        with engine.begin() as connection:
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                migration_0035["downgrade"]()
                migration_0034["downgrade"]()
        tables_after = set(inspect(engine).get_table_names())
        self.assertTrue({"slack_installations", "slack_oauth_states"}.issubset(tables_after))
        self.assertFalse({
            "slack_events", "slack_user_links", "slack_link_challenges",
            "slack_deal_subscriptions", "slack_notification_deliveries",
        } & tables_after)
        engine.dispose()

    def test_token_cipher_does_not_expose_plaintext_and_rejects_wrong_key(self) -> None:
        cipher = SlackTokenCipher(FERNET_KEY)
        encrypted = cipher.encrypt("xoxb-secret-token")
        self.assertNotIn("xoxb-secret-token", encrypted)
        self.assertEqual(cipher.decrypt(encrypted), "xoxb-secret-token")
        with self.assertRaises(SlackIntegrationError):
            SlackTokenCipher(Fernet.generate_key().decode("ascii")).decrypt(encrypted)

    def test_config_requires_complete_slack_settings_and_valid_encryption_key(self) -> None:
        from pydantic import ValidationError

        from syncally.config import Settings

        with self.assertRaises(ValidationError):
            Settings(_env_file=None, app_env="test", database_url="sqlite://", slack_client_id="client")
        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None, app_env="test", database_url="sqlite://",
                slack_client_id="client", slack_client_secret="secret",
                slack_redirect_uri="http://localhost/callback", integration_token_encryption_key="invalid",
                slack_signing_secret="signing-secret",
            )
        valid = Settings(
            _env_file=None, app_env="test", database_url="sqlite://",
            slack_client_id="client", slack_client_secret="secret",
            slack_redirect_uri="http://localhost/callback", integration_token_encryption_key=FERNET_KEY,
        )
        self.assertEqual(valid.slack_client_id, "client")
        self.assertEqual(valid.slack_signing_secret.get_secret_value(), "")

    def test_slack_callback_redirects_provider_denial_without_attempting_exchange(self) -> None:
        state = self._state()
        response = asyncio.run(integrations.slack_oauth_callback(state=state, code=None, error="access_denied", db=self.db))
        self.assertIn("integration=cancelled", response.headers["location"])
        self.assertEqual(self.fake_oauth.exchanged_codes, [])


class SlackOAuthTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_response_parses_installation_and_granted_scopes(self) -> None:
        async def provider(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={
                "ok": True, "team": {"id": "T1", "name": "One"},
                "bot_user_id": "B1", "access_token": "xoxb-secret",
                "scope": "chat:write,app_mentions:read,users:read",
            })

        client = SlackOAuthClient(
            client_id="client", client_secret="secret", redirect_uri="https://app/callback",
            transport=httpx.MockTransport(provider),
        )
        result = await client.exchange_code("code")
        self.assertEqual((result.workspace_id, result.workspace_name, result.bot_user_id), ("T1", "One", "B1"))
        self.assertEqual(result.access_token, "xoxb-secret")
        self.assertNotIn(result.access_token, repr(result))
        self.assertEqual(result.granted_scopes, ("app_mentions:read", "chat:write", "users:read"))

    async def test_provider_exchange_error_and_missing_scope_are_returned_for_app_policy(self) -> None:
        async def provider(request: httpx.Request) -> httpx.Response:
            if request.url == httpx.URL(SLACK_ACCESS_URL):
                return httpx.Response(200, json={
                    "ok": True, "team": {"id": "T1", "name": "One"},
                    "bot_user_id": "B1", "access_token": "xoxb-secret", "scope": "chat:write",
                })
            return httpx.Response(503)

        client = SlackOAuthClient(
            client_id="client", client_secret="secret", redirect_uri="https://app/callback",
            transport=httpx.MockTransport(provider),
        )
        result = await client.exchange_code("code")
        self.assertEqual(result.granted_scopes, ("chat:write",))

        async def failed_provider(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503)

        failing = SlackOAuthClient(
            client_id="client", client_secret="secret", redirect_uri="https://app/callback",
            transport=httpx.MockTransport(failed_provider),
        )
        with self.assertRaises(SlackIntegrationError):
            await failing.exchange_code("code")

    async def test_revocation_requires_provider_confirmation(self) -> None:
        async def provider(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"ok": True, "revoked": False})

        client = SlackOAuthClient(
            client_id="client", client_secret="secret", redirect_uri="https://app/callback",
            transport=httpx.MockTransport(provider),
        )
        with self.assertRaises(SlackIntegrationError):
            await client.revoke("xoxb-token")


if __name__ == "__main__":
    unittest.main()
