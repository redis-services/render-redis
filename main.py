"""
Multi-Tenant Redis API
----------------------
One Redis instance, isolated namespaces per project.
"""

import os
import json
import secrets
import asyncio
from typing import Any, Optional, Annotated
from contextlib import asynccontextmanager
from urllib.parse import urlencode

import redis.asyncio as aioredis
import uvicorn
import httpx
from fastapi import FastAPI, HTTPException, Header, Depends, Request, Form, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from projects import PROJECT_REGISTRY


# ── Redis connection ───────────────────────────────────────────────────────────

def get_redis_url() -> str:
    for env_key in ("REDIS_URL", "REDIS_CONNECTION_STRING", "REDIS_INTERNAL_URL"):
        value = os.getenv(env_key, "").strip()
        if value:
            return value

    raise RuntimeError("Redis connection string is missing.")


async def self_ping_loop():
    await asyncio.sleep(10)

    url = os.getenv("BASE_URL")
    if not url:
        print("⚠️ BASE_URL not set, skipping self-ping")
        return

    while True:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{url}/keep-alive", timeout=10)
                print("Keep-alive ping:", res.status_code)
        except Exception as e:
            print("Keep-alive failed:", e)

        await asyncio.sleep(300)  # 5 minutes


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = aioredis.from_url(
        get_redis_url(),
        decode_responses=True,
    )

    asyncio.create_task(self_ping_loop())

    yield

    await app.state.redis.aclose()


app = FastAPI(title="Multi-Tenant Redis API", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")


# ── Admin password ─────────────────────────────────────────────────────────────

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
if not ADMIN_PASSWORD:
    ADMIN_PASSWORD = secrets.token_urlsafe(16)
    print(f"\n⚠️ Generated ADMIN_PASSWORD: {ADMIN_PASSWORD}\n")


# ── Auth ───────────────────────────────────────────────────────────────────────

def get_project(project_id: str, x_api_key: str = Header(...)) -> str:
    expected = PROJECT_REGISTRY.get(project_id)
    if not expected:
        raise HTTPException(404, "Project not found")
    if x_api_key != expected:
        raise HTTPException(401, "Invalid API key")
    return project_id


def k(project_id: str, key: str) -> str:
    return f"{project_id}:{key}"


def check_admin(password: str) -> bool:
    return password == ADMIN_PASSWORD


def get_redis(request: Request) -> aioredis.Redis:
    return request.app.state.redis


# ── Models ─────────────────────────────────────────────────────────────────────

class SetBody(BaseModel):
    value: Any
    ttl: Optional[int] = None


class ExpireBody(BaseModel):
    ttl: int


class LPushBody(BaseModel):
    values: list[Any]


class HSetBody(BaseModel):
    mapping: dict[str, Any]


class IncrBody(BaseModel):
    by: int = 1


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


# ── Health + Keep Alive ─────────────────────────────────────────────────────────

@app.get("/health")
async def health(redis: aioredis.Redis = Depends(get_redis)):
    await redis.ping()
    return {"status": "ok"}


@app.get("/keep-alive")
async def keep_alive(redis: aioredis.Redis = Depends(get_redis)):
    try:
        pong = await redis.ping()

        # Touch Redis
        await redis.set("internal:keepalive", "1", ex=60)
        val = await redis.get("internal:keepalive")

        return {
            "status": "alive",
            "redis": pong,
            "cache": val,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── Basic Redis Ops ────────────────────────────────────────────────────────────

@app.get("/{project_id}/get/{key}")
async def get(
    key: str,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    val = await redis.get(k(project_id, key))
    return {"value": de(val)}


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

    return {"ok": True}


@app.delete("/{project_id}/delete/{key}")
async def delete(
    key: str,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    await redis.delete(k(project_id, key))
    return {"ok": True}


@app.post("/{project_id}/incr/{key}")
async def incr(
    key: str,
    body: IncrBody,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    val = await redis.incrby(k(project_id, key), body.by)
    return {"value": val}


# ── Lists ──────────────────────────────────────────────────────────────────────

@app.post("/{project_id}/lpush/{key}")
async def lpush(
    key: str,
    body: LPushBody,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    val = await redis.lpush(k(project_id, key), *[ser(v) for v in body.values])
    return {"length": val}


@app.get("/{project_id}/lrange/{key}")
async def lrange(
    key: str,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    vals = await redis.lrange(k(project_id, key), 0, -1)
    return {"values": [de(v) for v in vals]}


# ── Hash ───────────────────────────────────────────────────────────────────────

@app.post("/{project_id}/hset/{key}")
async def hset(
    key: str,
    body: HSetBody,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    await redis.hset(k(project_id, key), mapping={k: ser(v) for k, v in body.mapping.items()})
    return {"ok": True}


@app.get("/{project_id}/hgetall/{key}")
async def hgetall(
    key: str,
    project_id: str = Depends(get_project),
    redis: aioredis.Redis = Depends(get_redis),
):
    data = await redis.hgetall(k(project_id, key))
    return {k: de(v) for k, v in data.items()}


# ── Run ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
