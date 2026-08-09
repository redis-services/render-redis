"""Request instrumentation, stored in Redis alongside the data it measures.

Counters live in one hash per project per hour, which keeps writes to a single
HINCRBY pipeline and makes any time range a simple fan-in over hourly keys.
Latency is bucketed rather than sampled, so percentiles are approximate but
bounded — a p95 reported as 50ms means "between 25ms and 50ms".

Every metrics key is namespaced under `_m:` so it can never collide with a
tenant key, which is always `{project_id}:...`.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone

from .config import (
    LATENCY_BUCKETS_MS,
    METRICS_RETENTION_DAYS,
    RECENT_ACTIVITY_MAX,
    RECENT_ERRORS_MAX,
)

_RETENTION_SECONDS = METRICS_RETENTION_DAYS * 24 * 3600


def _hour_key(project_id: str, moment: datetime) -> str:
    return f"_m:{project_id}:h:{moment.strftime('%Y%m%d%H')}"


def _hours_back(count: int) -> list[datetime]:
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return [now - timedelta(hours=offset) for offset in range(count - 1, -1, -1)]


def _bucket_for(duration_ms: float) -> str:
    for edge in LATENCY_BUCKETS_MS:
        if duration_ms <= edge:
            return str(edge)
    return "inf"


async def record(
    redis,
    project_id: str,
    *,
    operation: str,
    method: str,
    path: str,
    status: int,
    duration_ms: float,
    error: str | None = None,
) -> None:
    """Fire-and-forget. A metrics failure must never fail the request itself."""
    now = datetime.now(timezone.utc)
    hour_key = _hour_key(project_id, now)
    is_error = status >= 400

    entry = json.dumps({
        "t": int(time.time() * 1000),
        "m": method,
        "p": path,
        "o": operation,
        "s": status,
        "d": round(duration_ms, 2),
        "e": error,
    })

    try:
        pipe = redis.pipeline(transaction=False)
        pipe.hincrby(hour_key, "req", 1)
        pipe.hincrbyfloat(hour_key, "dur_sum", duration_ms)
        pipe.hincrby(hour_key, "dur_cnt", 1)
        pipe.hincrby(hour_key, f"op:{operation}", 1)
        pipe.hincrby(hour_key, f"st:{status}", 1)
        pipe.hincrby(hour_key, f"lat:{_bucket_for(duration_ms)}", 1)
        if is_error:
            pipe.hincrby(hour_key, "err", 1)
        pipe.expire(hour_key, _RETENTION_SECONDS)

        pipe.lpush(f"_m:{project_id}:recent", entry)
        pipe.ltrim(f"_m:{project_id}:recent", 0, RECENT_ACTIVITY_MAX - 1)
        pipe.expire(f"_m:{project_id}:recent", 7 * 24 * 3600)
        if is_error:
            pipe.lpush(f"_m:{project_id}:errors", entry)
            pipe.ltrim(f"_m:{project_id}:errors", 0, RECENT_ERRORS_MAX - 1)
            pipe.expire(f"_m:{project_id}:errors", 30 * 24 * 3600)
        await pipe.execute()
    except Exception:  # noqa: BLE001 - metrics are best-effort by design
        pass


async def _fetch_hours(redis, project_id: str, hours: int) -> list[tuple[datetime, dict]]:
    moments = _hours_back(hours)
    try:
        pipe = redis.pipeline(transaction=False)
        for moment in moments:
            pipe.hgetall(_hour_key(project_id, moment))
        raw = await pipe.execute()
    except Exception:  # noqa: BLE001
        raw = [{} for _ in moments]
    return list(zip(moments, [row or {} for row in raw]))


def _num(bucket: dict, field: str) -> float:
    try:
        return float(bucket.get(field, 0) or 0)
    except (TypeError, ValueError):
        return 0.0


async def series(redis, project_id: str, hours: int, group_by_day: bool = False) -> list[dict]:
    """Time series of requests, errors, and mean latency."""
    buckets = await _fetch_hours(redis, project_id, hours)

    points: list[dict] = []
    for moment, bucket in buckets:
        requests = int(_num(bucket, "req"))
        errors = int(_num(bucket, "err"))
        duration_count = _num(bucket, "dur_cnt")
        points.append({
            "at": moment.isoformat(),
            "requests": requests,
            "errors": errors,
            "reads": int(sum(
                _num(bucket, f"op:{op}")
                for op in ("get", "mget", "lrange", "hget", "hgetall", "ttl", "keys")
            )),
            "writes": int(sum(
                _num(bucket, f"op:{op}")
                for op in ("set", "mset", "incr", "expire", "lpush", "rpush",
                           "lpop", "rpop", "hset", "hdel", "delete", "flush")
            )),
            "avg_ms": round(_num(bucket, "dur_sum") / duration_count, 2) if duration_count else 0.0,
        })

    if not group_by_day:
        return points

    days: dict[str, dict] = {}
    for point in points:
        day = point["at"][:10]
        slot = days.setdefault(day, {
            "at": day, "requests": 0, "errors": 0, "reads": 0, "writes": 0,
            "_ms": 0.0, "_n": 0,
        })
        slot["requests"] += point["requests"]
        slot["errors"] += point["errors"]
        slot["reads"] += point["reads"]
        slot["writes"] += point["writes"]
        slot["_ms"] += point["avg_ms"] * point["requests"]
        slot["_n"] += point["requests"]

    result = []
    for slot in days.values():
        total = slot.pop("_n")
        weighted = slot.pop("_ms")
        slot["avg_ms"] = round(weighted / total, 2) if total else 0.0
        result.append(slot)
    return sorted(result, key=lambda point: point["at"])


async def summary(redis, project_id: str, hours: int) -> dict:
    """Totals, operation breakdown, status breakdown, and latency percentiles."""
    buckets = await _fetch_hours(redis, project_id, hours)

    requests = errors = 0
    duration_sum = 0.0
    duration_count = 0.0
    operations: dict[str, int] = {}
    statuses: dict[str, int] = {}
    latency: dict[str, int] = {}

    for _, bucket in buckets:
        requests += int(_num(bucket, "req"))
        errors += int(_num(bucket, "err"))
        duration_sum += _num(bucket, "dur_sum")
        duration_count += _num(bucket, "dur_cnt")
        for field, value in bucket.items():
            if field.startswith("op:"):
                operations[field[3:]] = operations.get(field[3:], 0) + int(float(value))
            elif field.startswith("st:"):
                statuses[field[3:]] = statuses.get(field[3:], 0) + int(float(value))
            elif field.startswith("lat:"):
                latency[field[4:]] = latency.get(field[4:], 0) + int(float(value))

    return {
        "requests": requests,
        "errors": errors,
        "error_rate": round(errors / requests * 100, 3) if requests else 0.0,
        "avg_ms": round(duration_sum / duration_count, 2) if duration_count else 0.0,
        "operations": dict(sorted(operations.items(), key=lambda kv: kv[1], reverse=True)),
        "statuses": dict(sorted(statuses.items())),
        "percentiles": percentiles(latency),
    }


def percentiles(latency: dict[str, int]) -> dict[str, float]:
    """Estimate p50/p95/p99 from histogram buckets, reporting the bucket edge."""
    ordered = [str(edge) for edge in LATENCY_BUCKETS_MS] + ["inf"]
    counts = [(label, latency.get(label, 0)) for label in ordered]
    total = sum(count for _, count in counts)
    if not total:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0}

    result: dict[str, float] = {}
    for name, fraction in (("p50", 0.50), ("p95", 0.95), ("p99", 0.99)):
        target = total * fraction
        running = 0
        result[name] = float(LATENCY_BUCKETS_MS[-1])
        for label, count in counts:
            running += count
            if running >= target:
                result[name] = float(LATENCY_BUCKETS_MS[-1] * 2) if label == "inf" else float(label)
                break
    return result


async def _read_list(redis, key: str, limit: int) -> list[dict]:
    try:
        raw = await redis.lrange(key, 0, limit - 1)
    except Exception:  # noqa: BLE001
        return []
    entries = []
    for item in raw:
        try:
            entries.append(json.loads(item))
        except (TypeError, ValueError):
            continue
    return entries


async def recent(redis, project_id: str, limit: int = 20) -> list[dict]:
    return await _read_list(redis, f"_m:{project_id}:recent", limit)


async def recent_errors(redis, project_id: str, limit: int = 20) -> list[dict]:
    return await _read_list(redis, f"_m:{project_id}:errors", limit)


async def purge(redis, project_id: str) -> None:
    """Delete every metrics key for a project. Called on project deletion."""
    try:
        doomed = [f"_m:{project_id}:recent", f"_m:{project_id}:errors"]
        async for key in redis.scan_iter(match=f"_m:{project_id}:h:*", count=500):
            doomed.append(key)
        if doomed:
            await redis.delete(*doomed)
    except Exception:  # noqa: BLE001
        pass
