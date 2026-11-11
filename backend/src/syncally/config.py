"""Application configuration via environment variables."""

import re
from ipaddress import ip_address
from pathlib import Path
from typing import Literal
from urllib.parse import unquote, urlsplit
from uuid import UUID

from cryptography.fernet import Fernet
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


def _is_loopback_temporal_address(address: str) -> bool:
    """Allow plaintext Temporal only when the endpoint cannot leave this host."""
    try:
        parsed = urlsplit(f"//{address}")
        hostname = parsed.hostname
        parsed.port  # Validate the optional port instead of accepting malformed values.
    except ValueError:
        return False
    if (
        not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        return False
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return hostname.lower() == "localhost"


class Settings(BaseSettings):
    # Fail closed when a deployment forgets to set APP_ENV. Local .env files
    # should opt into development explicitly.
    app_env: str = "production"
    public_frontend_url: str | None = None
    debug: bool = False
    database_url: str = ""
    jwt_secret: str = ""
    jwt_secret_required: bool = True
    jwt_algorithm: str = "HS256"
    jwt_issuer: str | None = None
    jwt_audience: str | None = None
    system_admin_bootstrap_token: SecretStr = SecretStr("")
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    max_organizations_per_user: int = 5
    dev_auth_user_id: str | None = None
    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "syncally-deals"
    temporal_tls: bool = False
    temporal_api_key: SecretStr = SecretStr("")
    outbox_poll_interval_seconds: float = 2.0
    outbox_batch_size: int = 25
    ai_provider: Literal[
        "offline", "openai", "openai_with_offline_fallback",
        "gemini", "gemini_with_offline_fallback",
    ] = "offline"
    payment_mode: Literal["PAYPAL_SANDBOX", "OFFLINE_DEMO"] = "PAYPAL_SANDBOX"
    ai_remote_egress_enabled: bool = False
    ai_remote_allow_private: bool = False
    ai_remote_private_organization_ids: frozenset[UUID] = frozenset()
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = ""
    google_api_key: SecretStr = SecretStr("")
    gemini_model: str = ""
    slack_client_id: str = ""
    slack_client_secret: SecretStr = SecretStr("")
    slack_redirect_uri: str = ""
    slack_signing_secret: SecretStr = SecretStr("")
    slack_events_poll_interval_seconds: float = 2.0
    slack_events_batch_size: int = 20
    integration_token_encryption_key: SecretStr = SecretStr("")

    @model_validator(mode="after")
    def validate_auth_configuration(self) -> "Settings":
        local_environment = self.app_env.lower() in {"development", "test"}
        bootstrap_token = self.system_admin_bootstrap_token.get_secret_value()
        if bootstrap_token and len(bootstrap_token) < 32:
            raise ValueError("SYSTEM_ADMIN_BOOTSTRAP_TOKEN must contain at least 32 characters")
        if self.payment_mode == "OFFLINE_DEMO" and not local_environment:
            raise ValueError("OFFLINE_DEMO payments are only allowed in development/test")
        slack_oauth_values = (
            self.slack_client_id.strip(),
            self.slack_client_secret.get_secret_value().strip(),
            self.slack_redirect_uri.strip(),
            self.integration_token_encryption_key.get_secret_value().strip(),
        )
        if any(slack_oauth_values) and not all(slack_oauth_values):
            raise ValueError(
                "SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, SLACK_REDIRECT_URI, and "
                "INTEGRATION_TOKEN_ENCRYPTION_KEY must be configured together"
            )
        if all(slack_oauth_values):
            try:
                Fernet(slack_oauth_values[3].encode("ascii"))
            except (ValueError, UnicodeEncodeError) as error:
                raise ValueError("INTEGRATION_TOKEN_ENCRYPTION_KEY must be a valid Fernet key") from error
        if not self.database_url.strip():
            if local_environment:
                self.database_url = "postgresql+psycopg://localhost:5432/syncally"
            else:
                raise ValueError("DATABASE_URL must be configured outside development/test")
        if not local_environment:
            if self.jwt_secret_required and (
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
        if self.slack_redirect_uri:
            try:
                slack_redirect = urlsplit(self.slack_redirect_uri)
                slack_port = slack_redirect.port
            except ValueError as error:
                raise ValueError("SLACK_REDIRECT_URI must be a valid HTTPS callback URL") from error
            if (
                slack_redirect.scheme not in ({"http", "https"} if local_environment else {"https"})
                or not slack_redirect.hostname
                or slack_redirect.username is not None
                or slack_redirect.password is not None
                or slack_redirect.query
                or slack_redirect.fragment
                or (slack_port is not None and not 1 <= slack_port <= 65535)
            ):
                raise ValueError("SLACK_REDIRECT_URI must be a valid HTTPS callback URL")
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
        if self.slack_events_batch_size <= 0:
            raise ValueError("SLACK_EVENTS_BATCH_SIZE must be positive")
        if self.slack_events_poll_interval_seconds <= 0:
            raise ValueError("SLACK_EVENTS_POLL_INTERVAL_SECONDS must be positive")
        if (
            not local_environment
            and not self.temporal_tls
            and not _is_loopback_temporal_address(self.temporal_address)
        ):
            raise ValueError(
                "TEMPORAL_TLS must be enabled outside development/test unless "
                "TEMPORAL_ADDRESS is loopback"
            )
        return self

    @model_validator(mode="after")
    def validate_public_frontend_url(self) -> "Settings":
        local_environment = self.app_env.lower() in {"development", "test"}
        value = self.public_frontend_url
        if value is None:
            if not local_environment:
                raise ValueError("PUBLIC_FRONTEND_URL must be configured outside development/test")
            value = "http://localhost:5173"
        error = "PUBLIC_FRONTEND_URL must be a valid frontend base URL"
        if (
            not value
            or any(character.isspace() or ord(character) < 32 or 127 <= ord(character) <= 159 for character in value)
            or any(character in value for character in ("\\", "?", "#"))
            or re.search(r"%(?![0-9a-fA-F]{2})", value)
        ):
            raise ValueError(error)
        try:
            parsed = urlsplit(value)
            hostname = parsed.hostname
            port = parsed.port
        except ValueError as exc:
            raise ValueError(error) from exc
        if (
            parsed.scheme not in {"http", "https"}
            or not hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.netloc.endswith(":")
            or not re.fullmatch(r"(?:\[[0-9a-fA-F:.]+\]|[^:\[\]]+)(?::[0-9]+)?", parsed.netloc)
            or (port is not None and not 1 <= port <= 65535)
        ):
            raise ValueError(error)
        try:
            address = ip_address(hostname)
        except ValueError:
            address = None
            labels = hostname.removesuffix(".").split(".")
            if (
                len(hostname) > 253
                or any(not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label) for label in labels)
                or re.fullmatch(r"(?:[0-9]+|0[xX][0-9a-fA-F]+)", labels[-1])
            ):
                raise ValueError(error)
        if not local_environment and (
            parsed.scheme != "https"
            or (address is not None and (
                not address.is_global
                or address.is_multicast
                or getattr(address, "is_site_local", False)
            ))
            or (address is None and (
                "." not in hostname.rstrip(".")
                or hostname.lower().rstrip(".").endswith((".localhost", ".local"))
            ))
        ):
            raise ValueError("PUBLIC_FRONTEND_URL must use HTTPS and a public host outside development/test")
        decoded_path = unquote(parsed.path)
        if (
            re.search(r"%(?:2f|5c|25)", parsed.path, re.IGNORECASE)
            or any(segment in {".", ".."} for segment in decoded_path.split("/"))
            or any(ord(character) < 32 or 127 <= ord(character) <= 159 for character in decoded_path)
        ):
            raise ValueError(error)
        self.public_frontend_url = value.rstrip("/")
        return self

    model_config = SettingsConfigDict(
        env_file=_BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


class PayPalSettings(BaseSettings):
    """PayPal Sandbox credentials shared by the webhook API and payment worker."""

    paypal_client_id: str = ""
    paypal_client_secret: SecretStr = SecretStr("")
    paypal_webhook_id: str = ""

    model_config = SettingsConfigDict(
        env_file=_BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class EmailSettings(BaseSettings):
    """Optional transactional email API credentials."""

    gmail_api_client_id: str = ""
    gmail_api_client_secret: SecretStr = SecretStr("")
    gmail_api_refresh_token: SecretStr = SecretStr("")
    gmail_api_sender_email: str = ""
    gmail_smtp_username: str = ""
    gmail_app_password: SecretStr = SecretStr("")
    gmail_from_email: str = ""

    model_config = SettingsConfigDict(
        env_file=_BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


GmailSettings = EmailSettings
