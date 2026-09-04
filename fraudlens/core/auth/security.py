"""Password hashing and JWT issuance for analyst authentication.

Password hashing uses stdlib PBKDF2-HMAC-SHA256 (hashlib) — no bcrypt/
passlib dependency, since those need C extensions that aren't guaranteed to
build cleanly on every teammate's machine this close to a deadline.
PBKDF2 with a per-password random salt and 200k iterations is a real,
defensible choice, not a toy hash.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import time
from typing import Optional

import jwt

_PBKDF2_ITERATIONS = 200_000
_JWT_ALGORITHM = "HS256"
_JWT_TTL_SECONDS = 24 * 60 * 60  # 24h session — a hackathon demo, not a bank

# A real secret in production would come from a secrets manager; for this
# demo it's env-overridable with a fixed dev fallback so every teammate's
# locally-issued tokens verify against every other teammate's locally-run
# backend without extra setup.
_JWT_SECRET = os.environ.get("FRAUDLENS_JWT_SECRET", "fraudlens-hackathon-dev-secret-not-for-prod")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _PBKDF2_ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, expected_hex = stored_hash.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _PBKDF2_ITERATIONS)
    return secrets.compare_digest(digest.hex(), expected_hex)


def create_access_token(username: str) -> str:
    now = int(time.time())
    payload = {"sub": username, "iat": now, "exp": now + _JWT_TTL_SECONDS}
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """Returns the username the token was issued for, or None if the token
    is missing, malformed, expired, or signed with a different secret."""
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    return payload.get("sub")
