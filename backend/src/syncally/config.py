"""Application configuration via environment variables."""

import re
from pathlib import Path

from jwt.algorithms import HMACAlgorithm, get_default_algorithms
from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_JWT_ALGORITHMS = get_default_algorithms()
_SUPPORTED_JWT_ALGORITHMS = frozenset(_DEFAULT_JWT_ALGORITHMS)
# Only shared-secret (HMAC) algorithms can be used with the configured JWT_SECRET.
_SYMMETRIC_JWT_ALGORITHMS = frozenset(
    name
    for name, algorithm in _DEFAULT_JWT_ALGORITHMS.items()
    if isinstance(algorithm, HMACAlgorithm)
)
_BACKEND_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
_MIN_JWT_SECRET_LENGTH = 43  # 32 random bytes encoded with URL-safe base64.
_KNOWN_WEAK_JWT_SECRETS = frozenset(
    {
        "change-me",
        "dev-secret",
        "development-secret",
        "replace-with-a-random-secret",
        "secret",
        "test-secret",
        "your-secret-key",
    }
)
_KNOWN_WEAK_JWT_FRAGMENTS = (
    "change-me",
    "dev-secret",
    "development-secret",
    "jwt-secret",
    "replace-with",
    "static-production-secret",
    "secret-key",
    "test-secret",
    "your-secret",
)


def _is_weak_jwt_secret(secret: str) -> bool:
    normalized = secret.strip().lower()
    if (
        normalized in _KNOWN_WEAK_JWT_SECRETS
        or any(fragment in normalized for fragment in _KNOWN_WEAK_JWT_FRAGMENTS)
        or len(set(normalized)) < 8
    ):
        return True
    return re.fullmatch(r"(.{1,64})\1+", normalized) is not None


class Settings(BaseSettings):
    app_env: str = "development"
    debug: bool = False
    database_url: str = ""
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_issuer: str | None = None
    jwt_audience: str | None = None
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    max_organizations_per_user: int = 5
    dev_auth_user_id: str | None = None
    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "syncally-deals"
    temporal_tls: bool = False
    outbox_poll_interval_seconds: float = 2.0
    outbox_batch_size: int = 25

    @model_validator(mode="after")
    def validate_auth_configuration(self) -> "Settings":
        local_environment = self.app_env.lower() in {"development", "test"}
        if not self.database_url.strip():
            if local_environment:
                self.database_url = "postgresql+psycopg://localhost:5432/syncally"
            else:
                raise ValueError("DATABASE_URL must be configured outside development/test")
        if not local_environment:
            if (
                len(self.jwt_secret) < _MIN_JWT_SECRET_LENGTH
                or _is_weak_jwt_secret(self.jwt_secret)
            ):
                raise ValueError(
                    "JWT_SECRET must be a cryptographically generated secret containing "
                    "at least 32 random bytes outside development/test"
                )
        if self.jwt_algorithm in _SYMMETRIC_JWT_ALGORITHMS:
            pass
        elif self.jwt_algorithm in _SUPPORTED_JWT_ALGORITHMS:
            raise ValueError(
                "JWT_ALGORITHM must be a symmetric algorithm (HS256, HS384, or HS512) "
                "when only a shared JWT_SECRET is configured"
            )
        else:
            raise ValueError(f"JWT_ALGORITHM {self.jwt_algorithm!r} is not supported")
        if self.dev_auth_user_id and not local_environment:
            raise ValueError("DEV_AUTH_USER_ID is only allowed in development/test")
        if self.access_token_ttl_minutes <= 0 or self.refresh_token_ttl_days <= 0:
            raise ValueError("Token lifetimes must be positive")
        if self.max_organizations_per_user <= 0:
            raise ValueError("MAX_ORGANIZATIONS_PER_USER must be positive")
        if self.outbox_batch_size <= 0:
            raise ValueError("OUTBOX_BATCH_SIZE must be positive")
        if self.outbox_poll_interval_seconds <= 0:
            raise ValueError("OUTBOX_POLL_INTERVAL_SECONDS must be positive")
        if not local_environment and not self.temporal_tls:
            raise ValueError("TEMPORAL_TLS must be enabled outside development/test")
        return self

    model_config = SettingsConfigDict(
        env_file=_BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


class PayPalSettings(BaseSettings):
    """Credentials loaded only by the dedicated PayPal worker process."""

    paypal_client_id: str = ""
    paypal_client_secret: SecretStr = SecretStr("")

    model_config = SettingsConfigDict(
        env_file=_BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class GmailSettings(BaseSettings):
    """Optional Gmail SMTP credentials loaded only by the payment worker."""

    gmail_smtp_username: str = ""
    gmail_app_password: SecretStr = SecretStr("")
    gmail_from_email: str = ""

    model_config = SettingsConfigDict(
        env_file=_BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )
