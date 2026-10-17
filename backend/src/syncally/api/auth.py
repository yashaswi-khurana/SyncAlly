"""HTTP authentication and authorization dependencies."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from syncally.application.identity import ActorContext, resolve_actor
from syncally.config import settings
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import RefreshToken

bearer_scheme = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/auth", tags=["authentication"])


def _unauthorized(detail: str = "Authentication required") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _decode_token(token: str) -> UUID:
    if not settings.jwt_secret:
        raise _unauthorized("Authentication is not configured")

    decode_kwargs: dict[str, object] = {
        "algorithms": [settings.jwt_algorithm],
        "options": {"require": ["sub", "exp", "typ"]},
    }
    if settings.jwt_issuer:
        decode_kwargs["issuer"] = settings.jwt_issuer
    if settings.jwt_audience:
        decode_kwargs["audience"] = settings.jwt_audience
    try:
        claims = jwt.decode(token, settings.jwt_secret, **decode_kwargs)
        if claims.get("typ") != "access":
            raise jwt.InvalidTokenError("Token type is not valid for access authentication")
        return UUID(str(claims["sub"]))
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise _unauthorized("Invalid authentication token") from exc


def _encode_access_token(user_id: UUID, now: datetime | None = None) -> str:
    issued_at = now or datetime.now(UTC)
    claims: dict[str, object] = {
        "sub": str(user_id),
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=settings.access_token_ttl_minutes),
        "typ": "access",
    }
    if settings.jwt_issuer:
        claims["iss"] = settings.jwt_issuer
    if settings.jwt_audience:
        claims["aud"] = settings.jwt_audience
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _derive_rotated_refresh_token(token_id: UUID) -> str:
    """Derive the replacement token for a rotation deterministically.

    A rotation can be presented more than once around the same commit, either
    because two requests race with the same refresh token or because the
    rotation succeeded but its response was lost and the client retried.
    The replacement is derived from the original token ID and persisted with
    its hash, so replay can reconstruct the same raw value.
    """
    key = settings.jwt_secret.encode("utf-8")
    message = f"refresh-rotation:{token_id}".encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def create_refresh_token(db: Session, user_id: UUID, now: datetime | None = None) -> str:
    """Create and persist a refresh token for a completed sign-in flow."""
    if not settings.jwt_secret:
        raise _unauthorized("Authentication is not configured")
    if resolve_actor(db, user_id) is None:
        raise _unauthorized("User is inactive or does not exist")
    issued_at = now or datetime.now(UTC)
    raw_token = secrets.token_urlsafe(48)
    db.add(
        RefreshToken(
            user_id=user_id,
            family_id=uuid4(),
            token_hash=_hash_refresh_token(raw_token),
            expires_at=issued_at + timedelta(days=settings.refresh_token_ttl_days),
        )
    )
    db.commit()
    return raw_token


def _revoke_family(db: Session, family_id: UUID, now: datetime) -> None:
    db.execute(
        select(RefreshToken.id)
        .where(RefreshToken.family_id == family_id)
        .with_for_update()
    )
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    db.commit()


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=64)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@router.post("/dev-login", response_model=TokenResponse)
def development_login(request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    """Issue initial credentials for the configured local development identity."""
    user_id = _development_actor(request)
    if user_id is None:
        raise _unauthorized("Development authentication is not configured")

    now = datetime.now(UTC)
    actor = resolve_actor(db, user_id)
    if actor is None:
        raise _unauthorized("User is inactive or does not exist")
    return TokenResponse(
        access_token=_encode_access_token(actor.user_id, now),
        refresh_token=create_refresh_token(db, actor.user_id, now),
    )


def _replay_rotation(stored: RefreshToken, now: datetime, db: Session) -> TokenResponse:
    """Return an active replacement for a legitimate retry.

    A rotated token is only treated as credential reuse when its replacement is
    missing or has already been revoked. An active replacement indicates a
    concurrent request or a client retry after losing the original response.
    """
    replacement = None
    if stored.replaced_by_id is not None:
        replacement = db.scalar(
            select(RefreshToken).where(RefreshToken.id == stored.replaced_by_id)
        )
    if replacement is not None and replacement.revoked_at is None:
        actor = resolve_actor(db, stored.user_id)
        if actor is not None:
            return TokenResponse(
                access_token=_encode_access_token(actor.user_id, now),
                refresh_token=_derive_rotated_refresh_token(stored.id),
            )

    _revoke_family(db, stored.family_id, now)
    raise _unauthorized("Refresh token reuse detected")


@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Rotate a refresh token and issue a short-lived access token."""
    stored = db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == _hash_refresh_token(payload.refresh_token))
        .with_for_update()
    )
    now = datetime.now(UTC)
    if stored is None:
        raise _unauthorized("Invalid refresh token")
    if stored.revoked_at is not None:
        return _replay_rotation(stored, now, db)
    if stored.expires_at <= now:
        raise _unauthorized("Invalid refresh token")

    actor = resolve_actor(db, stored.user_id)
    if actor is None:
        stored.revoked_at = now
        db.commit()
        raise _unauthorized("User is inactive or does not exist")

    # Encode the access token before persisting the rotation so that an invalid
    # JWT algorithm or key configuration cannot revoke a usable refresh token
    # without producing its replacement.
    access_token = _encode_access_token(actor.user_id, now)
    replacement = _derive_rotated_refresh_token(stored.id)
    replacement_row = RefreshToken(
        user_id=stored.user_id,
        family_id=stored.family_id,
        token_hash=_hash_refresh_token(replacement),
        expires_at=now + timedelta(days=settings.refresh_token_ttl_days),
    )
    db.add(replacement_row)
    db.flush()
    stored.revoked_at = now
    stored.replaced_by_id = replacement_row.id
    db.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=replacement,
    )


def _development_actor(request: Request) -> UUID | None:
    """Allow a configured local identity without weakening non-local environments."""
    if settings.app_env.lower() not in {"development", "test"} or not settings.dev_auth_user_id:
        return None
    if request.headers.get("X-Dev-User-Id") != settings.dev_auth_user_id:
        return None
    try:
        return UUID(settings.dev_auth_user_id)
    except ValueError as exc:
        raise _unauthorized("Invalid development authentication identity") from exc


def get_current_actor(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> ActorContext:
    """Authenticate a request and resolve its active memberships."""
    user_id = _development_actor(request)
    if user_id is None:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise _unauthorized()
        user_id = _decode_token(credentials.credentials)

    actor = resolve_actor(db, user_id)
    if actor is None:
        raise _unauthorized("User is inactive or does not exist")
    return actor
