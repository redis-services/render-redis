"""FastAPI dependencies: session auth for the dashboard, key auth for the API."""

from __future__ import annotations

import os
import time
from datetime import timedelta

from fastapi import Depends, HTTPException, Header, Request, status
from fastapi.responses import RedirectResponse

from . import config
from .security import hash_api_key, hash_session_token
from .store import Store, utcnow


class LoginRequired(Exception):
    """Raised by page routes so the app can redirect instead of returning 401."""

    def __init__(self, next_url: str = "/app"):
        self.next_url = next_url


def get_store(request: Request) -> Store:
    return request.app.state.store


def get_redis(request: Request):
    return request.app.state.redis


# ── Session auth (dashboard) ───────────────────────────────────────────────────

async def get_optional_user(request: Request) -> dict | None:
    token = request.cookies.get(config.SESSION_COOKIE)
    if not token:
        return None

    store: Store = request.app.state.store
    session = await store.get_session(hash_session_token(token))
    if not session:
        return None

    expires_at = session.get("expires_at")
    if expires_at and expires_at < utcnow():
        await store.delete_session(session["token_hash"])
        return None

    user = await store.get_user(session["user_id"])
    if not user:
        await store.delete_session(session["token_hash"])
        return None

    # Refresh last_seen at most once an hour to avoid a write per request.
    last_seen = session.get("last_seen_at")
    if not last_seen or (utcnow() - last_seen) > timedelta(hours=1):
        await store.touch_session(session["token_hash"], utcnow())

    request.state.session = session
    return user


async def require_user(request: Request) -> dict:
    """For JSON endpoints — 401 when unauthenticated."""
    user = await get_optional_user(request)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to continue")
    return user


async def require_user_page(request: Request) -> dict:
    """For HTML pages — signals a redirect to the login screen."""
    user = await get_optional_user(request)
    if not user:
        raise LoginRequired(next_url=str(request.url.path))
    return user


# ── Project access (dashboard) ─────────────────────────────────────────────────

async def owned_project(
    project_id: str,
    request: Request,
    user: dict = Depends(require_user),
) -> dict:
    store: Store = request.app.state.store
    project = await store.get_project(project_id)
    # Deliberately 404 rather than 403 on someone else's project — a 403 would
    # confirm the project exists to a user who has no business knowing.
    if not project or project.get("user_id") != user["id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Project '{project_id}' not found")
    return project


async def owned_project_page(
    project_id: str,
    request: Request,
    user: dict = Depends(require_user_page),
) -> dict:
    store: Store = request.app.state.store
    project = await store.get_project(project_id)
    if not project or project.get("user_id") != user["id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Project '{project_id}' not found")
    return project


# ── API key auth (tenant data API) ─────────────────────────────────────────────

class _KeyCache:
    """Short-lived cache of key-hash lookups.

    Without it every data request costs a control-plane round trip. 30 seconds
    is short enough that a revoked key stops working almost immediately, and
    revocation also evicts the entry directly.
    """

    def __init__(self, ttl_seconds: float = 30.0, max_entries: int = 5000):
        self._ttl = ttl_seconds
        self._max = max_entries
        self._entries: dict[str, tuple[float, dict | None]] = {}

    def get(self, key_hash: str) -> tuple[bool, dict | None]:
        found = self._entries.get(key_hash)
        if not found:
            return False, None
        expires_at, value = found
        if expires_at < time.monotonic():
            self._entries.pop(key_hash, None)
            return False, None
        return True, value

    def put(self, key_hash: str, value: dict | None) -> None:
        if len(self._entries) >= self._max:
            self._entries.clear()
        self._entries[key_hash] = (time.monotonic() + self._ttl, value)

    def evict(self, key_hash: str) -> None:
        self._entries.pop(key_hash, None)

    def clear(self) -> None:
        self._entries.clear()


key_cache = _KeyCache()


def _legacy_env_key(project_id: str) -> str | None:
    """Backwards compatibility with the original PROJECT_<ID> environment keys,
    so deployments that predate user accounts keep working."""
    return os.environ.get(f"PROJECT_{project_id.upper()}") or None


async def authorised_project(
    request: Request,
    project_id: str,
    x_api_key: str = Header(..., description="Project API key"),
) -> str:
    """Resolve and verify the caller's project. Returns the project ID."""
    store: Store = request.app.state.store
    key_hash = hash_api_key(x_api_key)

    cached, record = key_cache.get(key_hash)
    if not cached:
        record = await store.get_api_key_by_hash(key_hash)
        key_cache.put(key_hash, record)

    if record and record.get("project_id") == project_id and not record.get("revoked_at"):
        request.state.api_key_id = record["id"]
        request.state.project_id = project_id
        return project_id

    legacy = _legacy_env_key(project_id)
    if legacy and _constant_time_equal(x_api_key, legacy):
        request.state.api_key_id = None
        request.state.project_id = project_id
        return project_id

    # Distinguish "no such project" from "wrong key" only where it is safe to:
    # if no key anywhere matches, the project may still exist for someone else.
    project = await store.get_project(project_id)
    if not project and not legacy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Project '{project_id}' not found")
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")


def _constant_time_equal(left: str, right: str) -> bool:
    import hmac
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))
