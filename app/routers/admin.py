"""Admin console — visibility across every account, and nothing else.

This router is deliberately read-only. There are no write endpoints to guard,
so no amount of parameter tampering turns "see everyone's usage" into "change
someone's project". Nor does it ever expose stored values or API keys: an
operator needs to know that a project has 1,284 keys, not what is in them.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from .. import config, keyspace, metrics
from ..deps import get_redis, get_store, require_admin, require_admin_page
from ..store import Store
from ..templating import base_url, page

router = APIRouter(tags=["admin"])

RANGE_HOURS = {"24h": 24, "7d": 24 * 7, "30d": 24 * 30}


async def _collect(request: Request, store: Store, redis, hours: int) -> dict:
    users = await store.list_all_users()
    projects = await store.list_all_projects()

    users_by_id = {user["id"]: user for user in users}
    projects_by_user: dict[str, int] = {}

    rows = []
    totals = {"keys": 0, "bytes": 0, "requests": 0, "errors": 0}

    for project in projects:
        owner = users_by_id.get(project.get("user_id") or "")
        if project.get("user_id"):
            projects_by_user[project["user_id"]] = projects_by_user.get(project["user_id"], 0) + 1

        stats = await keyspace.project_stats(redis, project["id"], sample_limit=2000)
        usage = await metrics.summary(redis, project["id"], hours)
        keys = await store.list_api_keys(project["id"])

        totals["keys"] += stats["keys"]
        totals["bytes"] += stats["bytes"]
        totals["requests"] += usage["requests"]
        totals["errors"] += usage["errors"]

        rows.append({
            "id": project["id"],
            "name": project.get("name") or project["id"],
            "owner_email": owner["email"] if owner else None,
            "owner_id": project.get("user_id"),
            "created_at": project["created_at"].isoformat() if project.get("created_at") else None,
            "base_url": f"{base_url(request)}/{project['id']}",
            "keys": stats["keys"],
            "bytes": stats["bytes"],
            "api_key_count": len(keys),
            # Only whether keys are being used, never their value.
            "last_used_at": max(
                (k["last_used_at"] for k in keys if k.get("last_used_at")), default=None
            ),
            "requests": usage["requests"],
            "errors": usage["errors"],
            "error_rate": usage["error_rate"],
            "avg_ms": usage["avg_ms"],
            "status": "active" if usage["requests"] else "idle",
            "legacy": bool(project.get("migrated_from_legacy")),
        })

    user_rows = [
        {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name", ""),
            "role": config.role_for(user["email"]),
            "created_at": user["created_at"].isoformat() if user.get("created_at") else None,
            "project_count": projects_by_user.get(user["id"], 0),
        }
        for user in users
    ]

    return {
        "users": user_rows,
        "projects": rows,
        "totals": {
            **totals,
            "users": len(users),
            "projects": len(projects),
            "unowned": sum(1 for row in rows if not row["owner_id"]),
        },
    }


@router.get("/admin")
async def admin_page(request: Request, user: dict = Depends(require_admin_page),
                     store: Store = Depends(get_store), redis=Depends(get_redis)):
    projects = await store.list_projects(user["id"])
    return page(request, "app/admin.html", {
        "user": user,
        "projects": projects,
        "project": None,
        "active": "admin",
        "project_base_url": "",
        "admin_emails": sorted(config.admin_emails()),
        "project_limit": config.LIMIT_PROJECTS_PER_USER,
    })


@router.get("/api/admin/overview")
async def admin_overview(request: Request, _: dict = Depends(require_admin),
                         store: Store = Depends(get_store), redis=Depends(get_redis),
                         range: str = Query("24h")):
    return await _collect(request, store, redis, RANGE_HOURS.get(range, 24))


@router.get("/api/admin/projects/{project_id}")
async def admin_project_detail(project_id: str, request: Request,
                               _: dict = Depends(require_admin),
                               store: Store = Depends(get_store), redis=Depends(get_redis),
                               range: str = Query("24h")):
    """Usage detail for any project. Deliberately excludes stored values and
    key material — an operator sees shape and volume, not contents."""
    project = await store.get_project(project_id)
    if not project:
        from fastapi import HTTPException
        raise HTTPException(404, f"Project '{project_id}' not found")

    hours = RANGE_HOURS.get(range, 24)
    owner = await store.get_user(project.get("user_id") or "") if project.get("user_id") else None

    return {
        "id": project["id"],
        "name": project.get("name") or project["id"],
        "description": project.get("description", ""),
        "owner_email": owner["email"] if owner else None,
        "created_at": project["created_at"].isoformat() if project.get("created_at") else None,
        "stats": await keyspace.project_stats(redis, project["id"]),
        "summary": await metrics.summary(redis, project["id"], hours),
        "series": await metrics.series(redis, project["id"], hours, group_by_day=hours > 48),
        "api_keys": [
            {
                "name": record.get("name", ""),
                "created_at": record["created_at"].isoformat() if record.get("created_at") else None,
                "last_used_at": record["last_used_at"].isoformat() if record.get("last_used_at") else None,
            }
            for record in await store.list_api_keys(project["id"])
        ],
    }
