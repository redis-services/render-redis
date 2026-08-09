"""HTML pages for the dashboard. Data is fetched client-side from /api."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from .. import config, keyspace, metrics
from ..deps import get_redis, get_store, owned_project_page, require_user_page
from ..store import Store
from ..templating import base_url, page

router = APIRouter(prefix="/app", tags=["pages"])


async def _shell(request: Request, user: dict, store: Store, project: dict | None = None,
                 active: str = "") -> dict:
    projects = await store.list_projects(user["id"])
    return {
        "user": user,
        "projects": projects,
        "project": project,
        "active": active,
        "project_base_url": f"{base_url(request)}/{project['id']}" if project else "",
    }


@router.get("", response_class=HTMLResponse)
async def projects_page(request: Request, user: dict = Depends(require_user_page),
                        store: Store = Depends(get_store), redis=Depends(get_redis)):
    context = await _shell(request, user, store, active="projects")
    enriched = []
    for project in context["projects"]:
        stats = await keyspace.project_stats(redis, project["id"], sample_limit=2000)
        usage = await metrics.summary(redis, project["id"], hours=24)
        enriched.append({
            **project,
            "keys": stats["keys"],
            "bytes": stats["bytes"],
            "requests_24h": usage["requests"],
            "status": "active" if usage["requests"] else "idle",
            "base_url": f"{base_url(request)}/{project['id']}",
        })
    context["projects"] = enriched
    context["project_limit"] = config.LIMIT_PROJECTS_PER_USER
    return page(request, "app/projects.html", context)


@router.get("/{project_id}", response_class=HTMLResponse)
async def overview_page(request: Request, project: dict = Depends(owned_project_page),
                        user: dict = Depends(require_user_page),
                        store: Store = Depends(get_store), redis=Depends(get_redis)):
    context = await _shell(request, user, store, project, active="overview")
    context["stats"] = await keyspace.project_stats(redis, project["id"])
    context["api_keys"] = await store.list_api_keys(project["id"])
    return page(request, "app/overview.html", context)


@router.get("/{project_id}/browser", response_class=HTMLResponse)
async def browser_page(request: Request, project: dict = Depends(owned_project_page),
                       user: dict = Depends(require_user_page), store: Store = Depends(get_store)):
    context = await _shell(request, user, store, project, active="browser")
    return page(request, "app/browser.html", context)


@router.get("/{project_id}/console", response_class=HTMLResponse)
async def console_page(request: Request, project: dict = Depends(owned_project_page),
                       user: dict = Depends(require_user_page), store: Store = Depends(get_store)):
    context = await _shell(request, user, store, project, active="console")
    return page(request, "app/console.html", context)


@router.get("/{project_id}/keys", response_class=HTMLResponse)
async def keys_page(request: Request, project: dict = Depends(owned_project_page),
                    user: dict = Depends(require_user_page), store: Store = Depends(get_store),
                    redis=Depends(get_redis)):
    context = await _shell(request, user, store, project, active="keys")
    context["stats"] = await keyspace.project_stats(redis, project["id"], sample_limit=2000)
    return page(request, "app/keys.html", context)


@router.get("/{project_id}/usage", response_class=HTMLResponse)
async def usage_page(request: Request, project: dict = Depends(owned_project_page),
                     user: dict = Depends(require_user_page), store: Store = Depends(get_store)):
    context = await _shell(request, user, store, project, active="usage")
    context["limits"] = {
        "keys": config.LIMIT_KEYS,
        "bytes": config.LIMIT_BYTES,
        "requests": config.LIMIT_REQUESTS_MONTH,
        "enforced": config.enforce_limits(),
    }
    return page(request, "app/usage.html", context)


@router.get("/{project_id}/settings", response_class=HTMLResponse)
async def settings_page(request: Request, project: dict = Depends(owned_project_page),
                        user: dict = Depends(require_user_page), store: Store = Depends(get_store),
                        redis=Depends(get_redis)):
    context = await _shell(request, user, store, project, active="settings")
    context["stats"] = await keyspace.project_stats(redis, project["id"], sample_limit=2000)
    return page(request, "app/settings.html", context)


@router.get("/{project_id}/quickstart", response_class=HTMLResponse)
async def quickstart_page(request: Request, project: dict = Depends(owned_project_page),
                          user: dict = Depends(require_user_page),
                          store: Store = Depends(get_store)):
    context = await _shell(request, user, store, project, active="")
    context["api_key"] = request.query_params.get("key", "")
    return page(request, "app/quickstart.html", context)
