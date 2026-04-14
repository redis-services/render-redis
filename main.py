"""
Multi-Tenant Redis API
----------------------
One Redis instance, isolated namespaces per project.
Each project has its own API key.
All keys are prefixed internally as: {project_id}:{key}

Admin panel available at /admin  (password-protected via ADMIN_PASSWORD env var)
"""

import os
import json
import secrets
from typing import Any, Optional, Annotated
from contextlib import asynccontextmanager
from urllib.parse import urlencode

import redis.asyncio as aioredis
import uvicorn
from fastapi import FastAPI, HTTPException, Header, Depends, Request, Form, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from projects import PROJECT_REGISTRY  # { "project_id": "api_key" }


# ── Redis connection ───────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = aioredis.from_url(
        os.environ["REDIS_URL"],
        decode_responses=True,
    )
    yield
    await app.state.redis.aclose()

app = FastAPI(title="Multi-Tenant Redis API", lifespan=lifespan)

templates = Jinja2Templates(directory="templates")

# Admin password — set ADMIN_PASSWORD env var, defaults to a random one printed at startup
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
if not ADMIN_PASSWORD:
    ADMIN_PASSWORD = secrets.token_urlsafe(16)
    print(f"\n⚠️  No ADMIN_PASSWORD set. Generated for this session: {ADMIN_PASSWORD}\n")


# ── Auth ───────────────────────────────────────────────────────────────────────

def get_project(project_id: str, x_api_key: str = Header(...)) -> str:
    expected = PROJECT_REGISTRY.get(project_id)
    if not expected:
        raise HTTPException(404, f"Project '{project_id}' not found")
    if x_api_key != expected:
        raise HTTPException(401, "Invalid API key")
    return project_id

def k(project_id: str, key: str) -> str:
    """Namespace a key: project_id:key"""
    return f"{project_id}:{key}"

def check_admin(password: str) -> bool:
    return password == ADMIN_PASSWORD


# ── Models ─────────────────────────────────────────────────────────────────────

class SetBody(BaseModel):
    value: Any
    ttl: Optional[int] = None

class MSetBody(BaseModel):
    pairs: dict[str, Any]
    ttl: Optional[int] = None

class ExpireBody(BaseModel):
    ttl: int

class LPushBody(BaseModel):
    values: list[Any]

class HSetBody(BaseModel):
    mapping: dict[str, Any]

class IncrBody(BaseModel):
    by: int = 1

class AdminVerifyBody(BaseModel):
    admin_password: str


# ── Helpers ────────────────────────────────────────────────────────────────────

def ser(v: Any) -> str:
    return json.dumps(v) if not isinstance(v, str) else v

def de(v: Optional[str]) -> Any:
    if v is None:
        return None
    try:
        return json.loads(v)
    except Exception:
        return v

def get_base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")

def redirect_admin(message: str, message_type: str = "ok") -> RedirectResponse:
    query = urlencode({"msg": message, "msg_type": message_type})
    return RedirectResponse(url=f"/admin?{query}", status_code=303)

def get_redis(request: Request) -> aioredis.Redis:
    return request.app.state.redis


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health(redis: aioredis.Redis = Depends(get_redis)):
    await redis.ping()
    return {"status": "ok"}


# ── Admin panel ────────────────────────────────────────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, msg: str = "", msg_type: str = "ok"):
    projects = [
        {"id": pid, "key": key}
        for pid, key in PROJECT_REGISTRY.items()
    ]
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "projects": projects,
        "base_url": get_base_url(request),
        "message": msg,
        "message_type": msg_type,
    })


@app.post("/admin/verify")
async def admin_verify(body: AdminVerifyBody):
    pw = body.admin_password
    return JSONResponse({"ok": check_admin(pw)})


@app.post("/admin/add-project")
async def admin_add_project(
    admin_password: str = Form(...),
    project_id: str = Form(...),
    api_key: str = Form(""),
):
    if not check_admin(admin_password):
        return redirect_admin("Wrong admin password", "err")

    # Sanitise project_id
    project_id = project_id.strip().lower().replace(" ", "_").replace("-", "_")
    if not project_id:
        return redirect_admin("Project ID cannot be empty", "err")
    if project_id in PROJECT_REGISTRY:
        return redirect_admin(f"Project {project_id} already exists", "err")

    # Generate key if not supplied
    if not api_key.strip():
        api_key = secrets.token_urlsafe(32)

    PROJECT_REGISTRY[project_id] = api_key.strip()

    return redirect_admin(f"Project {project_id} added successfully")


@app.post("/admin/remove-project/{project_id}")
async def admin_remove_project(
    project_id: str,
    admin_password: str = Form(...),
    redis: aioredis.Redis = Depends(get_redis),
):
    if not check_admin(admin_password):
        return redirect_admin("Wrong admin password", "err")

    if project_id not in PROJECT_REGISTRY:
        return redirect_admin(f"Project {project_id} not found", "err")

    del PROJECT_REGISTRY[project_id]

    # Optionally flush project's keys from Redis
    pattern = f"{project_id}:*"
    keys = await redis.keys(pattern)
    if keys:
        await redis.delete(*keys)

    return redirect_admin(f"Project {project_id} removed and keys flushed")


# ── String ops ─────────────────────────────────────────────────────────────────

@app.get("/{project_id}/get/{key}")
async def get(
    key: str,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    val = await redis.get(k(project_id, key))
    return {"key": key, "value": de(val), "exists": val is not None}


@app.post("/{project_id}/set/{key}")
async def set_key(
    key: str,
    body: SetBody,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    val = ser(body.value)
    if body.ttl:
        await redis.setex(k(project_id, key), body.ttl, val)
    else:
        await redis.set(k(project_id, key), val)
    return {"ok": True, "key": key, "ttl": body.ttl}


@app.delete("/{project_id}/delete/{key}")
async def delete(
    key: str,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    deleted = await redis.delete(k(project_id, key))
    return {"ok": True, "deleted": deleted > 0}


@app.post("/{project_id}/expire/{key}")
async def expire(
    key: str,
    body: ExpireBody,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    result = await redis.expire(k(project_id, key), body.ttl)
    return {"ok": bool(result)}


@app.get("/{project_id}/ttl/{key}")
async def ttl(
    key: str,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    val = await redis.ttl(k(project_id, key))
    return {"key": key, "ttl": val}


@app.post("/{project_id}/incr/{key}")
async def incr(
    key: str,
    body: IncrBody,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    result = await redis.incrby(k(project_id, key), body.by)
    return {"key": key, "value": result}


@app.post("/{project_id}/mset")
async def mset(
    body: MSetBody,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    mapping = {k(project_id, key): ser(val) for key, val in body.pairs.items()}
    await redis.mset(mapping)
    if body.ttl:
        for key in mapping:
            await redis.expire(key, body.ttl)
    return {"ok": True, "count": len(mapping)}


@app.post("/{project_id}/mget")
async def mget(
    keys: Annotated[list[str], Body(...)],
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    namespaced = [k(project_id, key) for key in keys]
    values = await redis.mget(namespaced)
    return {"result": {key: de(val) for key, val in zip(keys, values)}}


# ── List ops ───────────────────────────────────────────────────────────────────

@app.post("/{project_id}/lpush/{key}")
async def lpush(
    key: str,
    body: LPushBody,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    result = await redis.lpush(k(project_id, key), *[ser(v) for v in body.values])
    return {"ok": True, "length": result}


@app.post("/{project_id}/rpush/{key}")
async def rpush(
    key: str,
    body: LPushBody,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    result = await redis.rpush(k(project_id, key), *[ser(v) for v in body.values])
    return {"ok": True, "length": result}


@app.get("/{project_id}/lrange/{key}")
async def lrange(
    key: str,
    start: int = 0,
    end: int = -1,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    result = await redis.lrange(k(project_id, key), start, end)
    return {"key": key, "values": [de(v) for v in result]}


@app.delete("/{project_id}/lpop/{key}")
async def lpop(
    key: str,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    val = await redis.lpop(k(project_id, key))
    return {"value": de(val)}


@app.delete("/{project_id}/rpop/{key}")
async def rpop(
    key: str,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    val = await redis.rpop(k(project_id, key))
    return {"value": de(val)}


# ── Hash ops ───────────────────────────────────────────────────────────────────

@app.post("/{project_id}/hset/{key}")
async def hset(
    key: str,
    body: HSetBody,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    mapping = {field: ser(val) for field, val in body.mapping.items()}
    await redis.hset(k(project_id, key), mapping=mapping)
    return {"ok": True}


@app.get("/{project_id}/hget/{key}/{field}")
async def hget(
    key: str,
    field: str,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    val = await redis.hget(k(project_id, key), field)
    return {"field": field, "value": de(val)}


@app.get("/{project_id}/hgetall/{key}")
async def hgetall(
    key: str,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    result = await redis.hgetall(k(project_id, key))
    return {"key": key, "value": {f: de(v) for f, v in result.items()}}


@app.delete("/{project_id}/hdel/{key}/{field}")
async def hdel(
    key: str,
    field: str,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    result = await redis.hdel(k(project_id, key), field)
    return {"ok": True, "deleted": result > 0}


# ── Key utils ──────────────────────────────────────────────────────────────────

@app.get("/{project_id}/keys")
async def list_keys(
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    pattern = f"{project_id}:*"
    keys = await redis.keys(pattern)
    stripped = [key[len(project_id) + 1:] for key in keys]
    return {"project": project_id, "keys": stripped, "count": len(stripped)}


@app.delete("/{project_id}/flush")
async def flush(
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    pattern = f"{project_id}:*"
    keys = await redis.keys(pattern)
    if keys:
        await redis.delete(*keys)
    return {"ok": True, "deleted": len(keys)}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
