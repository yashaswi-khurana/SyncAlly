"""Account lock and unlock authorization invariants."""

import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from syncally.api.auth import _encode_access_token, get_current_actor
from syncally.api.platform import (
    OrganizationOwnerUpdate,
    UserStatusUpdate,
    set_platform_organization_owner,
    update_platform_user_status,
)
from syncally.application.identity import ActorContext
from syncally.config import settings
from syncally.infrastructure.models import (
    AuditEvent,
    Base,
    Organization,
    OrganizationMember,
    RefreshToken,
    User,
)


class PlatformUserLockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.admin = User(email="admin@example.com", display_name="Admin", status="ACTIVE", system_role="SYSTEM_ADMIN")
        self.user = User(email="user@example.com", display_name="User", status="ACTIVE", system_role="USER")
        self.db.add_all([self.admin, self.user])
        self.db.flush()
        self.db.add(RefreshToken(id=uuid4(), user_id=self.user.id, family_id=uuid4(), token_hash="a" * 64,
                                 expires_at=datetime.now(UTC) + timedelta(days=1)))
        self.db.commit()
        self.actor = ActorContext(user_id=self.admin.id, organization_ids=frozenset(), system_role="SYSTEM_ADMIN")

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_lock_revokes_refresh_and_audits_transition(self) -> None:
        result = update_platform_user_status(self.user.id, UserStatusUpdate(status="LOCKED", reason="support request"), self.actor, self.db)
        self.assertEqual(result["status"], "LOCKED")
        token = self.db.scalar(select(RefreshToken).where(RefreshToken.user_id == self.user.id))
        self.assertIsNotNone(token.revoked_at)
        event = self.db.scalar(select(AuditEvent).where(AuditEvent.aggregate_id == self.user.id))
        self.assertEqual(event.event_type, "user.account_status_changed")
        self.assertEqual(event.payload["from"], "ACTIVE")
        self.assertEqual(event.payload["to"], "LOCKED")

    def test_unlock_does_not_restore_revoked_refresh(self) -> None:
        update_platform_user_status(self.user.id, UserStatusUpdate(status="LOCKED"), self.actor, self.db)
        token = self.db.scalar(select(RefreshToken).where(RefreshToken.user_id == self.user.id))
        revoked_at = token.revoked_at
        update_platform_user_status(self.user.id, UserStatusUpdate(status="ACTIVE"), self.actor, self.db)
        self.assertEqual(token.revoked_at, revoked_at)

    def test_actor_cannot_lock_self_or_last_system_admin(self) -> None:
        with self.assertRaises(HTTPException) as self_lock:
            update_platform_user_status(self.admin.id, UserStatusUpdate(status="LOCKED"), self.actor, self.db)
        self.assertEqual(self_lock.exception.status_code, 409)
        second_admin = User(email="other-admin@example.com", display_name="Other", status="ACTIVE", system_role="SYSTEM_ADMIN")
        self.db.add(second_admin)
        self.db.commit()
        result = update_platform_user_status(second_admin.id, UserStatusUpdate(status="LOCKED"), self.actor, self.db)
        self.assertEqual(result["status"], "LOCKED")

    def test_previously_issued_access_token_is_rejected_after_lock(self) -> None:
        with patch.object(settings, "jwt_secret", "test-secret-with-more-than-32-characters"):
            token = _encode_access_token(self.user.id)
            request = Request({"type": "http", "headers": []})
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            self.assertEqual(get_current_actor(request, credentials, self.db).user_id, self.user.id)

            update_platform_user_status(self.user.id, UserStatusUpdate(status="LOCKED"), self.actor, self.db)

            with self.assertRaises(HTTPException) as rejected:
                get_current_actor(request, credentials, self.db)
            self.assertEqual(rejected.exception.status_code, 401)

    def test_owner_transfer_recovers_unowned_org_and_prevents_locking_sole_owner(self) -> None:
        organization = Organization(legal_name="Owner Recovery", country_code="US", status="ACTIVE")
        self.db.add(organization)
        self.db.flush()
        owner = OrganizationMember(
            organization_id=organization.id,
            user_id=self.user.id,
            role="ADMIN",
            status="ACTIVE",
            is_owner=True,
        )
        self.db.add(owner)
        replacement = User(email="replacement@example.com", display_name="Replacement", status="ACTIVE")
        self.db.add(replacement)
        self.db.flush()
        replacement_member = OrganizationMember(
            organization_id=organization.id,
            user_id=replacement.id,
            role="MEMBER",
            status="ACTIVE",
        )
        self.db.add(replacement_member)
        self.db.commit()

        with self.assertRaises(HTTPException) as blocked:
            update_platform_user_status(self.user.id, UserStatusUpdate(status="LOCKED"), self.actor, self.db)
        self.assertEqual(blocked.exception.status_code, 409)

        owner.is_owner = False
        self.db.commit()
        result = set_platform_organization_owner(
            organization.id,
            OrganizationOwnerUpdate(user_id=replacement.id, reason="recover ownership"),
            self.actor,
            self.db,
        )
        self.assertEqual(result["status"], "transferred")
        self.assertTrue(replacement_member.is_owner)
        self.assertFalse(owner.is_owner)

        returned = set_platform_organization_owner(
            organization.id,
            OrganizationOwnerUpdate(user_id=self.user.id, reason="transfer ownership"),
            self.actor,
            self.db,
        )
        self.assertEqual(returned["owner_user_id"], str(self.user.id))
        self.assertFalse(replacement_member.is_owner)
        self.assertTrue(owner.is_owner)


if __name__ == "__main__":
    unittest.main()
