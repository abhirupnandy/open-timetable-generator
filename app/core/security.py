"""Password hashing and signed session tokens (standard library only).

Passwords are hashed with scrypt. A session token is
``<user id>.<expiry>.<password stamp>.<HMAC-SHA256>``; the password stamp
is derived from the stored hash, so changing a password signs out every
existing session of that user.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from functools import lru_cache
from pathlib import Path

from app.core.config import settings

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        candidate = hashlib.scrypt(
            password.encode(), salt=_unb64(salt), n=int(n), r=int(r), p=int(p), dklen=32
        )
    except ValueError, TypeError:
        return False
    return hmac.compare_digest(candidate, _unb64(digest))


def generate_password(length: int = 10) -> str:
    """A readable random password (no 0/O/1/l/I)."""

    alphabet = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@lru_cache
def secret_key() -> bytes:
    """``SECRET_KEY`` from the environment, else a key generated once and kept
    in ``secret_key_file`` so sessions survive restarts."""

    if settings.secret_key:
        return settings.secret_key.encode()

    path = Path(settings.secret_key_file)
    if path.exists():
        return path.read_text().strip().encode()

    path.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_urlsafe(48)
    path.write_text(key)
    path.chmod(0o600)
    return key.encode()


def _password_stamp(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode()).hexdigest()[:12]


def _sign(message: str) -> str:
    return _b64(hmac.new(secret_key(), message.encode(), hashlib.sha256).digest())


def create_token(user_id: int, password_hash: str, max_age_seconds: int) -> str:
    message = f"{user_id}.{int(time.time()) + max_age_seconds}.{_password_stamp(password_hash)}"
    return f"{message}.{_sign(message)}"


def read_token(token: str) -> tuple[int, str] | None:
    """Return (user id, password stamp) for a valid, unexpired token."""

    try:
        user_id, expires, stamp, signature = token.split(".")
        message = f"{user_id}.{expires}.{stamp}"
        if not hmac.compare_digest(signature, _sign(message)):
            return None
        if int(expires) < time.time():
            return None
        return int(user_id), stamp
    except ValueError:
        return None


def token_matches_password(stamp: str, password_hash: str) -> bool:
    return hmac.compare_digest(stamp, _password_stamp(password_hash))
