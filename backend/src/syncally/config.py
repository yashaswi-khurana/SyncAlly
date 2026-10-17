"""Application configuration via environment variables."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "production"
    debug: bool = False
    database_url: str = ""
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_issuer: str | None = None
    jwt_audience: str | None = None
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    dev_auth_user_id: str | None = None

    @model_validator(mode="after")
    def validate_auth_configuration(self) -> "Settings":
        local_environment = self.app_env.lower() in {"development", "test"}
        if not self.database_url.strip():
            if local_environment:
                self.database_url = "postgresql+psycopg://localhost:5432/syncally"
            else:
                raise ValueError("DATABASE_URL must be configured outside development/test")
        if not local_environment and len(self.jwt_secret) < 32:
            raise ValueError(
                "JWT_SECRET must contain at least 32 characters outside development/test"
            )
        if self.dev_auth_user_id and not local_environment:
            raise ValueError("DEV_AUTH_USER_ID is only allowed in development/test")
        if self.access_token_ttl_minutes <= 0 or self.refresh_token_ttl_days <= 0:
            raise ValueError("Token lifetimes must be positive")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
