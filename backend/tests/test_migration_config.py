import os
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

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

    def test_database_url_is_required(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValidationError):
                MigrationSettings(_env_file=None)

    def test_env_file_is_resolved_from_backend_directory(self) -> None:
        expected = Path(__file__).resolve().parents[1] / ".env"

        self.assertEqual(Path(MigrationSettings.model_config["env_file"]), expected)