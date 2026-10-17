import os
import unittest
from unittest.mock import patch

from syncally.infrastructure.migration_config import MigrationSettings


class MigrationConfigTests(unittest.TestCase):
    def test_production_migrations_do_not_require_jwt_secret(self) -> None:
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "DATABASE_URL": "postgresql+psycopg://migration.example/syncally",
            },
            clear=True,
        ):
            settings = MigrationSettings(_env_file=None)

        self.assertEqual(settings.database_url, "postgresql+psycopg://migration.example/syncally")