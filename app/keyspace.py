"""Tenant keyspace access.

Every tenant key is stored as `{project_id}:{key}`. Nothing in this module may
read or write outside that prefix — that invariant is the whole isolation model.

Listing uses SCAN with a cursor rather than KEYS. KEYS is O(N) and blocks the
entire Redis server for the duration, which on a shared instance means one
tenant with a large keyspace stalls everyone else.
"""

from __future__ import annotations

import json
from typing import Any

SCAN_PAGE = 50
MAX_SCAN_ITERATIONS = 40  # bounds worst-case work when a pattern matches nothing

TYPE_LABELS = {
    "string": "STR",
    "list": "LST",
    "hash": "HSH",
    "set": "SET",
    "zset": "ZST",
    "stream": "STM",
    "none": "—",
}


def namespaced(project_id: str, key: str) -> str:
    return f"{project_id}:{key}"


def strip_namespace(project_id: str, full_key: str) -> str:
    prefix = f"{project_id}:"
    return full_key[len(prefix):] if full_key.startswith(prefix) else full_key


def serialise(value: Any) -> str:
    return json.dumps(value) if not isinstance(value, str) else value


def deserialise(value: str | None) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value


async def _memory_usage(redis, full_key: str) -> int | None:
    """MEMORY USAGE is unavailable on some Redis-compatible backends."""
    try:
        return await redis.memory_usage(full_key)
    except Exception:  # noqa: BLE001
        return None


async def scan_keys(
    redis,
    project_id: str,
    *,
    pattern: str = "*",
    cursor: int = 0,
    limit: int = SCAN_PAGE,
    type_filter: str | None = None,
) -> dict:
    """One page of keys with type, TTL, and size. Returns the next cursor;
    a cursor of 0 means the iteration is complete."""
    pattern = pattern.strip() or "*"
    match = namespaced(project_id, pattern)

    collected: list[str] = []
    iterations = 0
    while len(collected) < limit and iterations < MAX_SCAN_ITERATIONS:
        iterations += 1
        cursor, batch = await redis.scan(
            cursor=cursor, match=match, count=max(limit * 2, 100)
        )
        collected.extend(batch)
        if cursor == 0:
            break

    collected = collected[:limit]
    if not collected:
        return {"keys": [], "cursor": int(cursor), "done": int(cursor) == 0}

    pipe = redis.pipeline(transaction=False)
    for full_key in collected:
        pipe.type(full_key)
        pipe.ttl(full_key)
    raw = await pipe.execute()

    entries = []
    for index, full_key in enumerate(collected):
        key_type = raw[index * 2] or "none"
        ttl = raw[index * 2 + 1]
        if type_filter and key_type != type_filter:
            continue
        entries.append({
            "key": strip_namespace(project_id, full_key),
            "type": key_type,
            "type_label": TYPE_LABELS.get(key_type, key_type.upper()[:3]),
            "ttl": None if ttl in (-1, -2) else ttl,
            "persistent": ttl == -1,
            "size": await _memory_usage(redis, full_key),
        })

    return {"keys": entries, "cursor": int(cursor), "done": int(cursor) == 0}


async def read_key(redis, project_id: str, key: str) -> dict | None:
    """Type-aware read. Returns None if the key does not exist."""
    full_key = namespaced(project_id, key)
    key_type = await redis.type(full_key)
    if key_type in (None, "none"):
        return None

    if key_type == "string":
        value: Any = deserialise(await redis.get(full_key))
    elif key_type == "list":
        value = [deserialise(item) for item in await redis.lrange(full_key, 0, -1)]
    elif key_type == "hash":
        value = {
            field: deserialise(item)
            for field, item in (await redis.hgetall(full_key)).items()
        }
    elif key_type == "set":
        value = [deserialise(item) for item in await redis.smembers(full_key)]
    else:
        value = None

    ttl = await redis.ttl(full_key)
    return {
        "key": key,
        "type": key_type,
        "type_label": TYPE_LABELS.get(key_type, key_type.upper()[:3]),
        "value": value,
        "ttl": None if ttl in (-1, -2) else ttl,
        "persistent": ttl == -1,
        "size": await _memory_usage(redis, full_key),
    }


async def write_key(
    redis,
    project_id: str,
    key: str,
    *,
    key_type: str,
    value: Any,
    ttl: int | None = None,
    replace: bool = True,
) -> None:
    """Write a key of a given type. Replacing changes type safely by deleting first."""
    full_key = namespaced(project_id, key)
    pipe = redis.pipeline(transaction=True)

    if replace:
        pipe.delete(full_key)

    if key_type == "string":
        pipe.set(full_key, serialise(value))
    elif key_type == "list":
        items = value if isinstance(value, list) else [value]
        if items:
            pipe.rpush(full_key, *[serialise(item) for item in items])
    elif key_type == "hash":
        mapping = value if isinstance(value, dict) else {}
        if mapping:
            pipe.hset(full_key, mapping={f: serialise(v) for f, v in mapping.items()})
    elif key_type == "set":
        items = value if isinstance(value, list) else [value]
        if items:
            pipe.sadd(full_key, *[serialise(item) for item in items])
    else:
        raise ValueError(f"Unsupported key type: {key_type}")

    if ttl and ttl > 0:
        pipe.expire(full_key, ttl)
    await pipe.execute()


async def delete_key(redis, project_id: str, key: str) -> bool:
    return bool(await redis.delete(namespaced(project_id, key)))


async def project_stats(redis, project_id: str, sample_limit: int = 5000) -> dict:
    """Key count and approximate memory for a project.

    Counting is exact up to `sample_limit` keys, then extrapolates. This keeps
    the dashboard responsive on large keyspaces instead of scanning millions of
    keys on every page load.
    """
    count = 0
    total_bytes = 0
    measured = 0
    truncated = False

    try:
        async for full_key in redis.scan_iter(match=f"{project_id}:*", count=500):
            count += 1
            if measured < 500:
                size = await _memory_usage(redis, full_key)
                if size:
                    total_bytes += size
                    measured += 1
            if count >= sample_limit:
                truncated = True
                break
    except Exception:  # noqa: BLE001
        pass

    if measured:
        average = total_bytes / measured
        estimated_bytes = int(average * count)
    else:
        estimated_bytes = 0

    return {
        "keys": count,
        "bytes": estimated_bytes,
        "exact": not truncated and measured >= min(count, 500),
        "truncated": truncated,
    }


async def flush_project(redis, project_id: str) -> int:
    """Delete every key belonging to a project, in batches."""
    deleted = 0
    batch: list[str] = []
    async for full_key in redis.scan_iter(match=f"{project_id}:*", count=500):
        batch.append(full_key)
        if len(batch) >= 500:
            deleted += await redis.delete(*batch)
            batch = []
    if batch:
        deleted += await redis.delete(*batch)
    return deleted


async def top_keys_by_size(redis, project_id: str, limit: int = 6, scan_limit: int = 2000) -> list[dict]:
    entries: list[dict] = []
    scanned = 0
    try:
        async for full_key in redis.scan_iter(match=f"{project_id}:*", count=500):
            scanned += 1
            size = await _memory_usage(redis, full_key)
            if size:
                key_type = await redis.type(full_key)
                entries.append({
                    "key": strip_namespace(project_id, full_key),
                    "type": key_type,
                    "type_label": TYPE_LABELS.get(key_type, "—"),
                    "size": size,
                })
            if scanned >= scan_limit:
                break
    except Exception:  # noqa: BLE001
        return []
    entries.sort(key=lambda entry: entry["size"], reverse=True)
    return entries[:limit]
