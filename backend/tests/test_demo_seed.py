import unittest

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.main import app
from syncally.application.passwords import verify_password
from syncally.cli.seed_demo import DEMO_IDENTITIES, seed_demo_data
from syncally.config import settings
from syncally.infrastructure.models import Base, Organization, OrganizationMember, User


class DemoSeedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.original_app_env = settings.app_env
        settings.app_env = "test"

    def tearDown(self) -> None:
        settings.app_env = self.original_app_env
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_seed_creates_demo_users_orgs_and_admin_memberships(self) -> None:
        passwords = ("buyer-password-123", "seller-password-456")

        seed_demo_data(self.db, passwords)

        users = list(self.db.scalars(select(User).order_by(User.email)))
        organizations = list(
            self.db.scalars(select(Organization).order_by(Organization.legal_name))
        )
        memberships = list(self.db.scalars(select(OrganizationMember)))
        self.assertEqual(
            [user.email for user in users], [identity.email for identity in DEMO_IDENTITIES]
        )
        self.assertEqual(len(organizations), 2)
        self.assertEqual(len(memberships), 2)
        self.assertEqual({membership.role for membership in memberships}, {"ADMIN"})
        self.assertEqual({membership.status for membership in memberships}, {"ACTIVE"})
        self.assertTrue(
            all(user.password_hash and user.password_hash.startswith("scrypt$") for user in users)
        )
        self.assertTrue(verify_password(passwords[0], users[0].password_hash))
        self.assertTrue(verify_password(passwords[1], users[1].password_hash))

    def test_seed_is_idempotent_and_preserves_existing_passwords(self) -> None:
        passwords = ("buyer-password-123", "seller-password-456")
        seed_demo_data(self.db, passwords)
        existing_hashes = {
            user.email: user.password_hash for user in self.db.scalars(select(User))
        }

        seed_demo_data(self.db, ("ignored-new-buyer-password", "ignored-new-seller-password"))

        self.assertEqual(self.db.scalar(select(func.count()).select_from(User)), 2)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Organization)), 2)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(OrganizationMember)), 2)
        self.assertEqual(
            {user.email: user.password_hash for user in self.db.scalars(select(User))},
            existing_hashes,
        )

    def test_seed_refuses_non_local_environment_and_register_is_not_public(self) -> None:
        settings.app_env = "production"
        with self.assertRaises(RuntimeError):
            seed_demo_data(self.db, ("buyer-password-123", "seller-password-456"))

        self.assertNotIn("/auth/register", app.openapi()["paths"])


if __name__ == "__main__":
    unittest.main()
