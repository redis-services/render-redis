"""Password hashing, API key generation, and session tokens.

Passwords use scrypt from the standard library — deliberately slow, salted per
user. API keys and session tokens are high-entropy random strings, so they are
stored as plain SHA-256 digests: a slow KDF buys nothing against a 256-bit
random secret and would add latency to every single API request.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from .config import API_KEY_PREFIX

# scrypt parameters. n=2**14 keeps a hash around 50-100ms on typical hardware.
_SCRYPT_N = 2 ** 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


# ── Passwords ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt,
        n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_SCRYPT_DKLEN,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, digest_b64 = encoded.split("$")
        if scheme != "scrypt":
            return False
        expected = _unb64(digest_b64)
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=_unb64(salt_b64),
            n=int(n), r=int(r), p=int(p), dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def password_problem(password: str) -> str | None:
    """Return a human-readable reason the password is unacceptable, or None."""
    if len(password) < 10:
        return "Password must be at least 10 characters."
    if len(password) > 200:
        return "Password must be at most 200 characters."
    if password.lower() in _COMMON_PASSWORDS:
        return "That password is too common. Pick something less guessable."
    return None


_COMMON_PASSWORDS = frozenset({
    "password", "password1", "password123", "1234567890", "12345678910",
    "qwertyuiop", "letmein123", "iloveyou1", "administrator", "welcome123",
    "abc123456", "passw0rd1", "changeme123", "redis12345",
})


# ── API keys ───────────────────────────────────────────────────────────────────

def generate_api_key() -> str:
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def mask_api_key(key: str) -> str:
    """sk_live_abcd…wxyz — enough to recognise a key, not enough to use it."""
    body = key[len(API_KEY_PREFIX):] if key.startswith(API_KEY_PREFIX) else key
    if len(body) <= 8:
        return f"{API_KEY_PREFIX}{'•' * len(body)}"
    return f"{API_KEY_PREFIX}{body[:4]}{'•' * 12}{body[-4:]}"


# ── Session tokens ─────────────────────────────────────────────────────────────

def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(12)}"
