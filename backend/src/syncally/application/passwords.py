"""Password hashing shared by sign-in and trusted account provisioning."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from base64 import urlsafe_b64decode, urlsafe_b64encode


def hash_password(password: str) -> str:
    """Hash a password with a per-password random salt."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$" + "$".join(
        (urlsafe_b64encode(salt).decode("ascii"), urlsafe_b64encode(digest).decode("ascii"))
    )


def verify_password(password: str, encoded_hash: str | None) -> bool:
    """Check a password against the current scrypt encoding."""
    if encoded_hash is None:
        return False
    try:
        scheme, encoded_salt, encoded_digest = encoded_hash.split("$")
        if scheme != "scrypt":
            return False
        salt = urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected_digest = urlsafe_b64decode(encoded_digest.encode("ascii"))
    except (ValueError, UnicodeDecodeError):
        return False
    if len(salt) != 16 or len(expected_digest) != 32:
        return False
    actual_digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32
    )
    return hmac.compare_digest(actual_digest, expected_digest)
