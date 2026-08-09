"""Runtime configuration, read from the environment."""

from __future__ import annotations

import os

# Project IDs that would collide with application routes.
RESERVED_PROJECT_IDS = frozenset({
    "admin", "api", "app", "auth", "account", "assets", "static", "docs",
    "health", "keep_alive", "keep-alive", "login", "logout", "signup",
    "openapi", "redoc", "favicon", "robots", "well_known", "internal",
    "projects", "settings", "usage", "console", "browser", "keys", "new",
})

SESSION_COOKIE = "central_session"
SESSION_TTL_DAYS = 30

# API keys look like sk_live_<43 urlsafe chars>
API_KEY_PREFIX = "sk_live_"

# Free-tier limits. Surfaced in the UI; enforced only when ENFORCE_LIMITS is on.
LIMIT_KEYS = int(os.getenv("LIMIT_KEYS", "10000"))
LIMIT_BYTES = int(os.getenv("LIMIT_BYTES", str(100 * 1024 * 1024)))
LIMIT_REQUESTS_MONTH = int(os.getenv("LIMIT_REQUESTS_MONTH", "1000000"))
LIMIT_PROJECTS_PER_USER = int(os.getenv("LIMIT_PROJECTS_PER_USER", "10"))

# Latency histogram buckets in milliseconds, used for percentile estimates.
LATENCY_BUCKETS_MS = (1, 2, 5, 10, 25, 50, 100, 250, 500, 1000)

METRICS_RETENTION_DAYS = 35
RECENT_ACTIVITY_MAX = 100
RECENT_ERRORS_MAX = 50


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def enforce_limits() -> bool:
    return _flag("ENFORCE_LIMITS", "false")


def is_production() -> bool:
    return bool(os.getenv("RENDER")) or _flag("PRODUCTION", "false")


def secure_cookies() -> bool:
    """Secure cookies in production; overridable for local HTTPS-less testing."""
    return _flag("SECURE_COOKIES", "true" if is_production() else "false")


def redis_url() -> str:
    for env_key in ("REDIS_URL", "REDIS_CONNECTION_STRING", "REDIS_INTERNAL_URL"):
        value = os.getenv(env_key, "").strip()
        if value:
            return value
    if is_production():
        raise RuntimeError(
            "Redis connection string is missing. In Render, set REDIS_URL or map it "
            "from your Key Value instance with fromService.property=connectionString."
        )
    raise RuntimeError(
        "Redis connection string is missing. Set REDIS_URL, e.g. redis://localhost:6379/0."
    )


def mongodb_uri() -> str:
    return os.getenv("MONGODB_URI", "").strip()


def mongodb_db() -> str:
    return os.getenv("MONGODB_DB", "central_redis").strip() or "central_redis"


def base_url_override() -> str:
    for env_key in ("BASE_URL", "RENDER_EXTERNAL_URL"):
        value = os.getenv(env_key, "").strip().rstrip("/")
        if value:
            return value
    return ""


def keep_alive_enabled() -> bool:
    return _flag("KEEP_ALIVE_ENABLED", "true")


def signups_enabled() -> bool:
    return _flag("SIGNUPS_ENABLED", "true")
