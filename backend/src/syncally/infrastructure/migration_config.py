"""Configuration required to run database migrations."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class MigrationSettings(BaseSettings):
    database_url: str = "postgresql+psycopg://localhost:5432/syncally"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )