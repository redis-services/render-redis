"""The tenant-facing Redis API.

Mounted at the root so existing clients keep working:

    https://host/{project_id}/get/{key}   with header  x-api-key: sk_live_...

Because these paths start with a wildcard, this router must be registered LAST
and every application path must be a reserved project ID (see config).
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import authorised_project, get_redis
from ..keyspace import deserialise, namespaced, scan_keys, serialise, strip_namespace

router = APIRouter(tags=["data"])


class SetBody(BaseModel):
    value: Any
    ttl: Optional[int] = Field(default=None, ge=1)


class MSetBody(BaseModel):
    pairs: dict[str, Any]
    ttl: Optional[int] = Field(default=None, ge=1)


class ExpireBody(BaseModel):
    ttl: int = Field(ge=1)


class PushBody(BaseModel):
    values: list[Any]


class HSetBody(BaseModel):
    mapping: dict[str, Any]


class MembersBody(BaseModel):
    members: list[Any]


class IncrBody(BaseModel):
    by: int = 1


# ── Strings ────────────────────────────────────────────────────────────────────

@router.get("/{project_id}/get/{key:path}")
async def get_value(key: str, project_id: str = Depends(authorised_project), redis=Depends(get_redis)):
    raw = await redis.get(namespaced(project_id, key))
    return {"key": key, "value": deserialise(raw), "exists": raw is not None}


@router.post("/{project_id}/set/{key:path}")
async def set_value(key: str, body: SetBody,
                    project_id: str = Depends(authorised_project), redis=Depends(get_redis)):
    encoded = serialise(body.value)
    full_key = namespaced(project_id, key)
    if body.ttl:
        await redis.setex(full_key, body.ttl, encoded)
    else:
        await redis.set(full_key, encoded)
    return {"ok": True, "key": key, "ttl": body.ttl}


@router.delete("/{project_id}/delete/{key:path}")
async def delete_value(key: str, project_id: str = Depends(authorised_project),
                       redis=Depends(get_redis)):
    deleted = await redis.delete(namespaced(project_id, key))
    return {"ok": True, "deleted": deleted > 0}


@router.post("/{project_id}/expire/{key:path}")
async def set_expiry(key: str, body: ExpireBody,
                     project_id: str = Depends(authorised_project), redis=Depends(get_redis)):
    applied = await redis.expire(namespaced(project_id, key), body.ttl)
    return {"ok": bool(applied)}


@router.get("/{project_id}/ttl/{key:path}")
async def get_ttl(key: str, project_id: str = Depends(authorised_project), redis=Depends(get_redis)):
    value = await redis.ttl(namespaced(project_id, key))
    return {"key": key, "ttl": value}


@router.post("/{project_id}/incr/{key:path}")
async def increment(key: str, body: IncrBody,
                    project_id: str = Depends(authorised_project), redis=Depends(get_redis)):
    try:
        value = await redis.incrby(namespaced(project_id, key), body.by)
    except Exception as exc:  # noqa: BLE001 - non-integer value is a client error
        raise HTTPException(409, f"Key '{key}' does not hold an integer") from exc
    return {"key": key, "value": value}


@router.post("/{project_id}/mset")
async def multi_set(body: MSetBody, project_id: str = Depends(authorised_project),
                    redis=Depends(get_redis)):
    if not body.pairs:
        return {"ok": True, "count": 0}
    mapping = {namespaced(project_id, key): serialise(val) for key, val in body.pairs.items()}
    pipe = redis.pipeline(transaction=False)
    pipe.mset(mapping)
    if body.ttl:
        for full_key in mapping:
            pipe.expire(full_key, body.ttl)
    await pipe.execute()
    return {"ok": True, "count": len(mapping)}


@router.post("/{project_id}/mget")
async def multi_get(keys: Annotated[list[str], Body(...)],
                    project_id: str = Depends(authorised_project), redis=Depends(get_redis)):
    if not keys:
        return {"result": {}}
    values = await redis.mget([namespaced(project_id, key) for key in keys])
    return {"result": {key: deserialise(value) for key, value in zip(keys, values)}}


# ── Lists ──────────────────────────────────────────────────────────────────────

@router.post("/{project_id}/lpush/{key:path}")
async def list_push_left(key: str, body: PushBody,
                         project_id: str = Depends(authorised_project), redis=Depends(get_redis)):
    if not body.values:
        raise HTTPException(400, "values must not be empty")
    length = await redis.lpush(namespaced(project_id, key), *[serialise(v) for v in body.values])
    return {"ok": True, "length": length}


@router.post("/{project_id}/rpush/{key:path}")
async def list_push_right(key: str, body: PushBody,
                          project_id: str = Depends(authorised_project), redis=Depends(get_redis)):
    if not body.values:
        raise HTTPException(400, "values must not be empty")
    length = await redis.rpush(namespaced(project_id, key), *[serialise(v) for v in body.values])
    return {"ok": True, "length": length}


@router.get("/{project_id}/lrange/{key:path}")
async def list_range(key: str, start: int = 0, end: int = -1,
                     project_id: str = Depends(authorised_project), redis=Depends(get_redis)):
    values = await redis.lrange(namespaced(project_id, key), start, end)
    return {"key": key, "values": [deserialise(v) for v in values]}


@router.delete("/{project_id}/lpop/{key:path}")
async def list_pop_left(key: str, project_id: str = Depends(authorised_project),
                        redis=Depends(get_redis)):
    return {"value": deserialise(await redis.lpop(namespaced(project_id, key)))}


@router.delete("/{project_id}/rpop/{key:path}")
async def list_pop_right(key: str, project_id: str = Depends(authorised_project),
                         redis=Depends(get_redis)):
    return {"value": deserialise(await redis.rpop(namespaced(project_id, key)))}


# ── Hashes ─────────────────────────────────────────────────────────────────────

@router.post("/{project_id}/hset/{key:path}")
async def hash_set(key: str, body: HSetBody,
                   project_id: str = Depends(authorised_project), redis=Depends(get_redis)):
    if not body.mapping:
        raise HTTPException(400, "mapping must not be empty")
    mapping = {field: serialise(value) for field, value in body.mapping.items()}
    await redis.hset(namespaced(project_id, key), mapping=mapping)
    return {"ok": True, "fields": len(mapping)}


@router.get("/{project_id}/hget/{key}/{field}")
async def hash_get(key: str, field: str,
                   project_id: str = Depends(authorised_project), redis=Depends(get_redis)):
    value = await redis.hget(namespaced(project_id, key), field)
    return {"field": field, "value": deserialise(value), "exists": value is not None}


@router.get("/{project_id}/hgetall/{key:path}")
async def hash_get_all(key: str, project_id: str = Depends(authorised_project),
                       redis=Depends(get_redis)):
    result = await redis.hgetall(namespaced(project_id, key))
    return {"key": key, "value": {f: deserialise(v) for f, v in result.items()}}


@router.delete("/{project_id}/hdel/{key}/{field}")
async def hash_delete(key: str, field: str,
                      project_id: str = Depends(authorised_project), redis=Depends(get_redis)):
    removed = await redis.hdel(namespaced(project_id, key), field)
    return {"ok": True, "deleted": removed > 0}


# ── Sets ───────────────────────────────────────────────────────────────────────

@router.post("/{project_id}/sadd/{key:path}")
async def set_add(key: str, body: MembersBody,
                  project_id: str = Depends(authorised_project), redis=Depends(get_redis)):
    if not body.members:
        raise HTTPException(400, "members must not be empty")
    added = await redis.sadd(namespaced(project_id, key), *[serialise(m) for m in body.members])
    return {"ok": True, "added": added}


@router.get("/{project_id}/smembers/{key:path}")
async def set_members(key: str, project_id: str = Depends(authorised_project),
                      redis=Depends(get_redis)):
    members = await redis.smembers(namespaced(project_id, key))
    return {"key": key, "members": [deserialise(m) for m in members]}


@router.post("/{project_id}/srem/{key:path}")
async def set_remove(key: str, body: MembersBody,
                     project_id: str = Depends(authorised_project), redis=Depends(get_redis)):
    if not body.members:
        raise HTTPException(400, "members must not be empty")
    removed = await redis.srem(namespaced(project_id, key), *[serialise(m) for m in body.members])
    return {"ok": True, "removed": removed}


# ── Key utilities ──────────────────────────────────────────────────────────────

@router.get("/{project_id}/keys")
async def list_keys(
    project_id: str = Depends(authorised_project),
    redis=Depends(get_redis),
    pattern: str = Query("*", description="Glob pattern, scoped to your project"),
    cursor: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
):
    """Paginated via SCAN. Pass the returned `cursor` back until `done` is true."""
    result = await scan_keys(redis, project_id, pattern=pattern, cursor=cursor, limit=limit)
    return {
        "project": project_id,
        "keys": [entry["key"] for entry in result["keys"]],
        "count": len(result["keys"]),
        "cursor": result["cursor"],
        "done": result["done"],
    }


@router.get("/{project_id}/scan")
async def scan_detailed(
    project_id: str = Depends(authorised_project),
    redis=Depends(get_redis),
    pattern: str = Query("*"),
    cursor: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    """Like /keys, but returns type, TTL, and size for each key."""
    return await scan_keys(redis, project_id, pattern=pattern, cursor=cursor, limit=limit)


@router.delete("/{project_id}/flush")
async def flush(project_id: str = Depends(authorised_project), redis=Depends(get_redis)):
    from ..keyspace import flush_project
    deleted = await flush_project(redis, project_id)
    return {"ok": True, "deleted": deleted}
