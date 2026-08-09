"""Central — multi-tenant Redis as a service.

One Redis instance, one isolated namespace per project, one API key per client.
The dashboard lives under /app; the tenant API is mounted at the root so that a
project's base URL is simply https://host/{project_id}.

Run locally:
    REDIS_URL=redis://localhost:6379/0 python main.py
"""

from __future__ import annotations

import asyncio
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

import httpx
import redis.asyncio as aioredis
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import config, metrics
from app.deps import LoginRequired
from app.routers import auth, data, pages, projects_api
from app.store import build_store, utcnow
from app.templating import page

STATIC_DIR = Path(__file__).resolve().parent / "static"

# Throttles the last_used_at write so a hot key doesn't cause a database write
# on every single request.
_last_used_written: dict[str, float] = {}
_LAST_USED_INTERVAL = 60.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = aioredis.from_url(config.redis_url(), decode_responses=True)
    app.state.store, app.state.persistent = await build_store(
        config.mongodb_uri(), config.mongodb_db(),
        allow_fallback=config.allow_memory_store(),
    )
    app.state.keep_alive_task = None
    await _claim_legacy_projects(app)

    if config.keep_alive_enabled():
        app.state.keep_alive_task = asyncio.create_task(_self_ping_loop())

    try:
        yield
    finally:
        task = app.state.keep_alive_task
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await app.state.store.close()
        await app.state.redis.aclose()


app = FastAPI(
    title="Central — Multi-Tenant Redis",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Metrics middleware ─────────────────────────────────────────────────────────

def _tenant_route(path: str) -> tuple[str, str] | None:
    """Return (project_id, operation) if this looks like a tenant API call."""
    parts = [segment for segment in path.split("/") if segment]
    if len(parts) < 2:
        return None
    project_id, operation = parts[0], parts[1]
    if project_id in config.RESERVED_PROJECT_IDS:
        return None
    return project_id, operation


@app.middleware("http")
async def instrument(request: Request, call_next):
    route = _tenant_route(request.url.path)
    if route is None:
        return await call_next(request)

    project_id, operation = route
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000

    await metrics.record(
        request.app.state.redis,
        project_id,
        operation=operation,
        method=request.method,
        path=request.url.path[len(project_id) + 1:],
        status=response.status_code,
        duration_ms=duration_ms,
        error=getattr(request.state, "error_detail", None),
    )

    key_id = getattr(request.state, "api_key_id", None)
    if key_id and response.status_code < 500:
        now = time.monotonic()
        if now - _last_used_written.get(key_id, 0.0) > _LAST_USED_INTERVAL:
            _last_used_written[key_id] = now
            try:
                await request.app.state.store.update_api_key(key_id, {"last_used_at": utcnow()})
            except Exception:  # noqa: BLE001 - never fail a request over bookkeeping
                pass

    return response


# ── Error handling ─────────────────────────────────────────────────────────────

def _wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept and not request.url.path.startswith("/api")


@app.exception_handler(LoginRequired)
async def handle_login_required(request: Request, exc: LoginRequired):
    return RedirectResponse(f"/login?next={quote(exc.next_url)}", status_code=303)


@app.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exc: HTTPException):
    request.state.error_detail = str(exc.detail)
    if exc.status_code == 404 and _wants_html(request):
        return page(request, "error.html", {
            "code": 404,
            "title": "Not found",
            "detail": str(exc.detail),
        }, status_code=404)
    if exc.status_code == 401 and _wants_html(request):
        return RedirectResponse(f"/login?next={quote(request.url.path)}", status_code=303)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code,
                        headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    request.state.error_detail = "Validation error"
    return JSONResponse({"detail": exc.errors()}, status_code=422)


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
async def health(request: Request):
    try:
        await request.app.state.redis.ping()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"Redis unavailable: {exc}") from exc
    return {
        "status": "ok",
        "persistent_store": request.app.state.persistent,
        "version": app.version,
    }


@app.get("/keep-alive", tags=["ops"])
async def keep_alive(request: Request):
    try:
        pong = await request.app.state.redis.ping()
        await request.app.state.redis.set("_internal:keepalive", "1", ex=60)
        return {"status": "alive", "redis": pong}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"Keep-alive failed: {exc}") from exc


async def _claim_legacy_projects(app: FastAPI) -> None:
    """Hand ownerless projects — the ones migrated from the pre-accounts schema
    — to the account named by LEGACY_OWNER_EMAIL, if that account exists."""
    unowned = await app.state.store.list_unowned_projects()
    if not unowned:
        return

    email = config.legacy_owner_email()
    if not email:
        names = ", ".join(project["id"] for project in unowned[:5])
        suffix = "…" if len(unowned) > 5 else ""
        print(
            f"ℹ️  {len(unowned)} migrated project(s) have no owner ({names}{suffix}). "
            "Their API keys still work, but they are hidden from every dashboard. "
            "Set LEGACY_OWNER_EMAIL to an existing account to claim them."
        )
        return

    user = await app.state.store.get_user_by_email(email)
    if not user:
        print(f"⚠️  LEGACY_OWNER_EMAIL is {email}, but no such account exists yet. "
              "Sign up with that address and restart to claim the migrated projects.")
        return

    claimed = await app.state.store.claim_unowned_projects(user["id"])
    print(f"Assigned {claimed} migrated project(s) to {email}.")


async def _self_ping_loop():
    """Render's free tier sleeps idle services; a periodic self-request avoids
    a cold start on the first real request."""
    await asyncio.sleep(10)
    url = config.base_url_override()
    if not url:
        print("⚠️  Keep-alive skipped: BASE_URL / RENDER_EXTERNAL_URL not set")
        return

    async with httpx.AsyncClient(follow_redirects=True) as client:
        while True:
            try:
                response = await client.get(f"{url}/keep-alive", timeout=10)
                response.raise_for_status()
            except Exception as exc:  # noqa: BLE001
                print("Keep-alive failed:", exc)
            await asyncio.sleep(300)


# ── Routers ────────────────────────────────────────────────────────────────────
# Order matters. The data router matches /{project_id}/... and would otherwise
# swallow every application path, so it is registered last.

app.include_router(auth.router)
app.include_router(pages.router)
app.include_router(projects_api.router)
app.include_router(data.router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=bool(os.getenv("RELOAD")),
    )
