"""JSON API consumed by the dashboard. Session-authenticated, never key-authenticated."""

from __future__ import annotations

import re
import time
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .. import config, keyspace, metrics
from ..deps import get_redis, get_store, key_cache, owned_project, require_user
from ..security import generate_api_key, hash_api_key, mask_api_key, new_id
from ..store import Store, utcnow

router = APIRouter(prefix="/api", tags=["dashboard"])

PROJECT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,38}[a-z0-9]$")
RANGE_HOURS = {"24h": 24, "7d": 24 * 7, "30d": 24 * 30}


# ── Models ─────────────────────────────────────────────────────────────────────

class CreateProject(BaseModel):
    project_id: str
    name: str = ""
    description: str = ""


class UpdateProject(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_ttl: Optional[int] = Field(default=None, ge=0)
    apply_default_ttl: Optional[bool] = None


class CreateApiKey(BaseModel):
    name: str = "Untitled key"


class WriteKey(BaseModel):
    type: str = "string"
    value: Any = None
    ttl: Optional[int] = Field(default=None, ge=0)


class ConsoleRequest(BaseModel):
    operation: str
    key: str = ""
    field: str = ""
    body: dict[str, Any] = Field(default_factory=dict)


# ── Helpers ────────────────────────────────────────────────────────────────────

def normalise_project_id(raw: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", raw.strip().lower().replace(" ", "_").replace("-", "_"))


def validate_project_id(project_id: str) -> None:
    if not PROJECT_ID_PATTERN.match(project_id):
        raise HTTPException(
            400,
            "Project ID must be 3-40 characters, start with a letter, end with a letter "
            "or number, and contain only lowercase letters, numbers, and underscores.",
        )
    if project_id in config.RESERVED_PROJECT_IDS:
        raise HTTPException(400, f"'{project_id}' is reserved. Pick another ID.")


def public_project(project: dict, request: Request) -> dict:
    from ..templating import base_url
    return {
        "id": project["id"],
        "name": project.get("name") or project["id"],
        "description": project.get("description", ""),
        "created_at": project["created_at"].isoformat() if project.get("created_at") else None,
        "base_url": f"{base_url(request)}/{project['id']}",
        "settings": project.get("settings", {}),
    }


def public_api_key(record: dict) -> dict:
    return {
        "id": record["id"],
        "name": record.get("name", "Untitled key"),
        "masked": record.get("masked", ""),
        "created_at": record["created_at"].isoformat() if record.get("created_at") else None,
        "last_used_at": record["last_used_at"].isoformat() if record.get("last_used_at") else None,
        "revoked": bool(record.get("revoked_at")),
    }


# ── Projects ───────────────────────────────────────────────────────────────────

@router.get("/projects")
async def list_projects(request: Request, user: dict = Depends(require_user),
                        store: Store = Depends(get_store), redis=Depends(get_redis)):
    projects = await store.list_projects(user["id"])
    payload = []
    for project in projects:
        stats = await keyspace.project_stats(redis, project["id"], sample_limit=2000)
        usage = await metrics.summary(redis, project["id"], hours=24)
        entry = public_project(project, request)
        entry.update({
            "keys": stats["keys"],
            "bytes": stats["bytes"],
            "requests_24h": usage["requests"],
            "status": "active" if usage["requests"] else "idle",
        })
        payload.append(entry)
    return {"projects": payload, "limit": config.LIMIT_PROJECTS_PER_USER}


@router.post("/projects", status_code=201)
async def create_project(payload: CreateProject, request: Request,
                         user: dict = Depends(require_user), store: Store = Depends(get_store)):
    project_id = normalise_project_id(payload.project_id)
    validate_project_id(project_id)

    if await store.count_projects(user["id"]) >= config.LIMIT_PROJECTS_PER_USER:
        raise HTTPException(
            403, f"You've reached the limit of {config.LIMIT_PROJECTS_PER_USER} projects."
        )
    if await store.get_project(project_id):
        raise HTTPException(409, f"Project ID '{project_id}' is already taken.")

    project = {
        "id": project_id,
        "user_id": user["id"],
        "name": payload.name.strip()[:120] or project_id,
        "description": payload.description.strip()[:500],
        "created_at": utcnow(),
        "settings": {"default_ttl": 0, "apply_default_ttl": False},
    }
    try:
        await store.create_project(project)
    except Exception:  # noqa: BLE001 - unique index race
        raise HTTPException(409, f"Project ID '{project_id}' is already taken.") from None

    api_key = generate_api_key()
    record = {
        "id": new_id("key"),
        "project_id": project_id,
        "user_id": user["id"],
        "name": "Default",
        "key_hash": hash_api_key(api_key),
        "masked": mask_api_key(api_key),
        "created_at": utcnow(),
        "last_used_at": None,
        "revoked_at": None,
    }
    await store.create_api_key(record)

    result = public_project(project, request)
    # The only time the full key is ever returned.
    result["api_key"] = api_key
    result["api_key_id"] = record["id"]
    return result


@router.get("/projects/{project_id}")
async def get_project(request: Request, project: dict = Depends(owned_project),
                      redis=Depends(get_redis)):
    stats = await keyspace.project_stats(redis, project["id"])
    usage = await metrics.summary(redis, project["id"], hours=24)
    result = public_project(project, request)
    result.update({"stats": stats, "usage": usage})
    return result


@router.patch("/projects/{project_id}")
async def update_project(payload: UpdateProject, request: Request,
                         project: dict = Depends(owned_project),
                         store: Store = Depends(get_store)):
    fields: dict[str, Any] = {}
    if payload.name is not None:
        fields["name"] = payload.name.strip()[:120] or project["id"]
    if payload.description is not None:
        fields["description"] = payload.description.strip()[:500]

    settings = dict(project.get("settings", {}))
    if payload.default_ttl is not None:
        settings["default_ttl"] = payload.default_ttl
    if payload.apply_default_ttl is not None:
        settings["apply_default_ttl"] = payload.apply_default_ttl
    if settings != project.get("settings", {}):
        fields["settings"] = settings

    if fields:
        await store.update_project(project["id"], fields)
    merged = {**project, **fields}
    return public_project(merged, request)


@router.delete("/projects/{project_id}")
async def delete_project(project: dict = Depends(owned_project),
                         store: Store = Depends(get_store), redis=Depends(get_redis)):
    deleted = await keyspace.flush_project(redis, project["id"])
    await metrics.purge(redis, project["id"])
    for record in await store.list_api_keys(project["id"]):
        key_cache.evict(record["key_hash"])
    await store.delete_project_api_keys(project["id"])
    await store.delete_project(project["id"])
    return {"ok": True, "keys_deleted": deleted}


@router.post("/projects/{project_id}/flush")
async def flush_project(project: dict = Depends(owned_project), redis=Depends(get_redis)):
    deleted = await keyspace.flush_project(redis, project["id"])
    return {"ok": True, "deleted": deleted}


@router.get("/projects/{project_id}/stats")
async def project_stats(project: dict = Depends(owned_project), redis=Depends(get_redis)):
    stats = await keyspace.project_stats(redis, project["id"])
    return {
        **stats,
        "limits": {
            "keys": config.LIMIT_KEYS,
            "bytes": config.LIMIT_BYTES,
            "requests_month": config.LIMIT_REQUESTS_MONTH,
            "enforced": config.enforce_limits(),
        },
    }


# ── Data browser ───────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/browse")
async def browse(project: dict = Depends(owned_project), redis=Depends(get_redis),
                 pattern: str = Query("*"), cursor: int = Query(0, ge=0),
                 limit: int = Query(50, ge=1, le=200),
                 type: Optional[str] = Query(None)):
    return await keyspace.scan_keys(
        redis, project["id"], pattern=pattern, cursor=cursor, limit=limit,
        type_filter=type if type and type != "all" else None,
    )


@router.get("/projects/{project_id}/keys/{key:path}")
async def read_key(key: str, project: dict = Depends(owned_project), redis=Depends(get_redis)):
    entry = await keyspace.read_key(redis, project["id"], key)
    if entry is None:
        raise HTTPException(404, f"Key '{key}' not found")
    return entry


@router.put("/projects/{project_id}/keys/{key:path}")
async def write_key(key: str, payload: WriteKey, project: dict = Depends(owned_project),
                    redis=Depends(get_redis)):
    if payload.type not in {"string", "list", "hash", "set"}:
        raise HTTPException(400, "type must be one of: string, list, hash, set")
    settings = project.get("settings", {})
    ttl = payload.ttl
    if not ttl and settings.get("apply_default_ttl") and settings.get("default_ttl"):
        ttl = int(settings["default_ttl"])
    await keyspace.write_key(
        redis, project["id"], key, key_type=payload.type, value=payload.value, ttl=ttl
    )
    return await keyspace.read_key(redis, project["id"], key)


@router.delete("/projects/{project_id}/keys/{key:path}")
async def remove_key(key: str, project: dict = Depends(owned_project), redis=Depends(get_redis)):
    return {"ok": True, "deleted": await keyspace.delete_key(redis, project["id"], key)}


# ── API keys ───────────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/api-keys")
async def list_api_keys(project: dict = Depends(owned_project), store: Store = Depends(get_store)):
    records = await store.list_api_keys(project["id"])
    return {"api_keys": [public_api_key(record) for record in records]}


@router.post("/projects/{project_id}/api-keys", status_code=201)
async def create_api_key(payload: CreateApiKey, project: dict = Depends(owned_project),
                         store: Store = Depends(get_store), user: dict = Depends(require_user)):
    existing = await store.list_api_keys(project["id"])
    if len(existing) >= 10:
        raise HTTPException(403, "A project can have at most 10 API keys.")

    api_key = generate_api_key()
    record = {
        "id": new_id("key"),
        "project_id": project["id"],
        "user_id": user["id"],
        "name": payload.name.strip()[:60] or "Untitled key",
        "key_hash": hash_api_key(api_key),
        "masked": mask_api_key(api_key),
        "created_at": utcnow(),
        "last_used_at": None,
        "revoked_at": None,
    }
    await store.create_api_key(record)
    return {**public_api_key(record), "api_key": api_key}


@router.post("/projects/{project_id}/api-keys/{key_id}/rotate")
async def rotate_api_key(key_id: str, project: dict = Depends(owned_project),
                         store: Store = Depends(get_store)):
    record = await store.get_api_key(key_id)
    if not record or record["project_id"] != project["id"]:
        raise HTTPException(404, "API key not found")

    key_cache.evict(record["key_hash"])
    api_key = generate_api_key()
    fields = {
        "key_hash": hash_api_key(api_key),
        "masked": mask_api_key(api_key),
        "rotated_at": utcnow(),
        "last_used_at": None,
        "revoked_at": None,
    }
    await store.update_api_key(key_id, fields)
    return {**public_api_key({**record, **fields}), "api_key": api_key}


@router.delete("/projects/{project_id}/api-keys/{key_id}")
async def revoke_api_key(key_id: str, project: dict = Depends(owned_project),
                         store: Store = Depends(get_store)):
    record = await store.get_api_key(key_id)
    if not record or record["project_id"] != project["id"]:
        raise HTTPException(404, "API key not found")

    remaining = [k for k in await store.list_api_keys(project["id"]) if k["id"] != key_id]
    if not remaining:
        raise HTTPException(
            400, "This is the project's only key. Create another before revoking this one."
        )

    key_cache.evict(record["key_hash"])
    await store.delete_api_key(key_id)
    return {"ok": True}


# ── Usage ──────────────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/usage")
async def usage(project: dict = Depends(owned_project), redis=Depends(get_redis),
                range: str = Query("24h")):
    hours = RANGE_HOURS.get(range, 24)
    summary = await metrics.summary(redis, project["id"], hours)
    points = await metrics.series(redis, project["id"], hours, group_by_day=hours > 48)
    stats = await keyspace.project_stats(redis, project["id"])
    month = await metrics.summary(redis, project["id"], hours=24 * 30)

    return {
        "range": range,
        "summary": summary,
        "series": points,
        "stats": stats,
        "top_keys": await keyspace.top_keys_by_size(redis, project["id"]),
        "errors": await metrics.recent_errors(redis, project["id"], limit=20),
        "limits": {
            "keys": {"used": stats["keys"], "limit": config.LIMIT_KEYS},
            "bytes": {"used": stats["bytes"], "limit": config.LIMIT_BYTES},
            "requests": {"used": month["requests"], "limit": config.LIMIT_REQUESTS_MONTH},
            "enforced": config.enforce_limits(),
        },
    }


@router.get("/projects/{project_id}/activity")
async def activity(project: dict = Depends(owned_project), redis=Depends(get_redis),
                   limit: int = Query(20, ge=1, le=100)):
    return {"activity": await metrics.recent(redis, project["id"], limit)}


# ── API console ────────────────────────────────────────────────────────────────

_CONSOLE_SPECS: dict[str, tuple[str, str, bool]] = {
    # operation: (http method, path template, needs key)
    "get": ("GET", "/get/{key}", True),
    "set": ("POST", "/set/{key}", True),
    "delete": ("DELETE", "/delete/{key}", True),
    "expire": ("POST", "/expire/{key}", True),
    "ttl": ("GET", "/ttl/{key}", True),
    "incr": ("POST", "/incr/{key}", True),
    "mset": ("POST", "/mset", False),
    "mget": ("POST", "/mget", False),
    "lpush": ("POST", "/lpush/{key}", True),
    "rpush": ("POST", "/rpush/{key}", True),
    "lrange": ("GET", "/lrange/{key}", True),
    "lpop": ("DELETE", "/lpop/{key}", True),
    "rpop": ("DELETE", "/rpop/{key}", True),
    "hset": ("POST", "/hset/{key}", True),
    "hget": ("GET", "/hget/{key}/{field}", True),
    "hgetall": ("GET", "/hgetall/{key}", True),
    "hdel": ("DELETE", "/hdel/{key}/{field}", True),
    "sadd": ("POST", "/sadd/{key}", True),
    "smembers": ("GET", "/smembers/{key}", True),
    "srem": ("POST", "/srem/{key}", True),
    "keys": ("GET", "/keys", False),
    "scan": ("GET", "/scan", False),
    "flush": ("DELETE", "/flush", False),
}


@router.get("/console/operations")
async def console_operations(_: dict = Depends(require_user)):
    groups = {
        "strings": ["get", "set", "delete", "expire", "ttl", "incr", "mset", "mget"],
        "lists": ["lpush", "rpush", "lrange", "lpop", "rpop"],
        "hashes": ["hset", "hget", "hgetall", "hdel"],
        "sets": ["sadd", "smembers", "srem"],
        "utility": ["keys", "scan", "flush"],
    }
    return {
        "groups": groups,
        "specs": {
            name: {"method": spec[0], "path": spec[1], "needs_key": spec[2]}
            for name, spec in _CONSOLE_SPECS.items()
        },
    }


@router.post("/projects/{project_id}/console")
async def run_console(payload: ConsoleRequest, project: dict = Depends(owned_project),
                      redis=Depends(get_redis)):
    """Execute an operation against the project, from the dashboard.

    This dispatches directly rather than making an HTTP call to ourselves,
    because the server never holds a plaintext API key to authenticate with.
    The result is shaped identically to the public API's response.
    """
    spec = _CONSOLE_SPECS.get(payload.operation)
    if not spec:
        raise HTTPException(400, f"Unknown operation '{payload.operation}'")

    method, path_template, needs_key = spec
    key = payload.key.strip()
    if needs_key and not key:
        raise HTTPException(400, f"Operation '{payload.operation}' requires a key")

    path = path_template.replace("{key}", key).replace("{field}", payload.field.strip())
    started = time.perf_counter()
    try:
        result = await _dispatch(redis, project, payload)
        status = 200
    except HTTPException as exc:
        result = {"detail": exc.detail}
        status = exc.status_code
    except Exception as exc:  # noqa: BLE001 - surface the error to the console
        result = {"detail": str(exc)}
        status = 500
    duration_ms = (time.perf_counter() - started) * 1000

    await metrics.record(
        redis, project["id"], operation=payload.operation, method=method,
        path=path, status=status, duration_ms=duration_ms,
        error=result.get("detail") if status >= 400 else None,
    )

    return {
        "status": status,
        "duration_ms": round(duration_ms, 2),
        "method": method,
        "path": f"/{project['id']}{path}",
        "result": result,
    }


async def _dispatch(redis, project: dict, payload: ConsoleRequest) -> Any:
    project_id = project["id"]
    key = payload.key.strip()
    body = payload.body or {}
    ns = keyspace.namespaced

    operation = payload.operation
    if operation == "get":
        raw = await redis.get(ns(project_id, key))
        return {"key": key, "value": keyspace.deserialise(raw), "exists": raw is not None}
    if operation == "set":
        encoded = keyspace.serialise(body.get("value"))
        ttl = body.get("ttl")
        if ttl:
            await redis.setex(ns(project_id, key), int(ttl), encoded)
        else:
            await redis.set(ns(project_id, key), encoded)
        return {"ok": True, "key": key, "ttl": ttl}
    if operation == "delete":
        return {"ok": True, "deleted": bool(await redis.delete(ns(project_id, key)))}
    if operation == "expire":
        return {"ok": bool(await redis.expire(ns(project_id, key), int(body.get("ttl", 60))))}
    if operation == "ttl":
        return {"key": key, "ttl": await redis.ttl(ns(project_id, key))}
    if operation == "incr":
        return {"key": key, "value": await redis.incrby(ns(project_id, key), int(body.get("by", 1)))}
    if operation == "mset":
        pairs = body.get("pairs") or {}
        if not pairs:
            raise HTTPException(400, "pairs must not be empty")
        mapping = {ns(project_id, k): keyspace.serialise(v) for k, v in pairs.items()}
        await redis.mset(mapping)
        return {"ok": True, "count": len(mapping)}
    if operation == "mget":
        keys = body.get("keys") or []
        values = await redis.mget([ns(project_id, k) for k in keys]) if keys else []
        return {"result": {k: keyspace.deserialise(v) for k, v in zip(keys, values)}}
    if operation in {"lpush", "rpush"}:
        values = body.get("values") or []
        if not values:
            raise HTTPException(400, "values must not be empty")
        push = redis.lpush if operation == "lpush" else redis.rpush
        length = await push(ns(project_id, key), *[keyspace.serialise(v) for v in values])
        return {"ok": True, "length": length}
    if operation == "lrange":
        start = int(body.get("start", 0))
        end = int(body.get("end", -1))
        values = await redis.lrange(ns(project_id, key), start, end)
        return {"key": key, "values": [keyspace.deserialise(v) for v in values]}
    if operation in {"lpop", "rpop"}:
        pop = redis.lpop if operation == "lpop" else redis.rpop
        return {"value": keyspace.deserialise(await pop(ns(project_id, key)))}
    if operation == "hset":
        mapping = body.get("mapping") or {}
        if not mapping:
            raise HTTPException(400, "mapping must not be empty")
        await redis.hset(
            ns(project_id, key),
            mapping={f: keyspace.serialise(v) for f, v in mapping.items()},
        )
        return {"ok": True, "fields": len(mapping)}
    if operation == "hget":
        value = await redis.hget(ns(project_id, key), payload.field)
        return {"field": payload.field, "value": keyspace.deserialise(value),
                "exists": value is not None}
    if operation == "hgetall":
        result = await redis.hgetall(ns(project_id, key))
        return {"key": key, "value": {f: keyspace.deserialise(v) for f, v in result.items()}}
    if operation == "hdel":
        return {"ok": True, "deleted": bool(await redis.hdel(ns(project_id, key), payload.field))}
    if operation in {"sadd", "srem"}:
        members = body.get("members") or []
        if not members:
            raise HTTPException(400, "members must not be empty")
        call = redis.sadd if operation == "sadd" else redis.srem
        count = await call(ns(project_id, key), *[keyspace.serialise(m) for m in members])
        return {"ok": True, ("added" if operation == "sadd" else "removed"): count}
    if operation == "smembers":
        members = await redis.smembers(ns(project_id, key))
        return {"key": key, "members": [keyspace.deserialise(m) for m in members]}
    if operation in {"keys", "scan"}:
        result = await keyspace.scan_keys(
            redis, project_id, pattern=body.get("pattern", "*"),
            cursor=int(body.get("cursor", 0)), limit=int(body.get("limit", 50)),
        )
        if operation == "keys":
            return {"project": project_id, "keys": [e["key"] for e in result["keys"]],
                    "count": len(result["keys"]), "cursor": result["cursor"],
                    "done": result["done"]}
        return result
    if operation == "flush":
        return {"ok": True, "deleted": await keyspace.flush_project(redis, project_id)}

    raise HTTPException(400, f"Unhandled operation '{operation}'")
