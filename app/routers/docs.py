"""The public API reference.

Served as a real page rather than the generated Swagger UI. Swagger describes
every route the application has, including the dashboard's own endpoints, which
is noise to someone who only wants to know how to store a key. The schema is
still available to admins at /api/docs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from .. import config
from ..deps import get_store, is_admin, require_user_page
from ..store import Store
from ..templating import base_url, page

router = APIRouter(tags=["docs"])


@router.get("/docs", response_class=HTMLResponse)
async def api_reference(request: Request, user: dict = Depends(require_user_page),
                        store: Store = Depends(get_store)):
    # Substitute the reader's own project into the examples where we can.
    projects = await store.list_projects(user["id"])
    example_project = projects[0]["id"] if projects else "your_project"

    return page(request, "docs.html", {
        "user": user,
        "projects": projects,
        "project": None,
        "active": "docs",
        "project_base_url": "",
        "example_project": example_project,
        "example_base": f"{base_url(request)}/{example_project}",
        "is_admin": is_admin(user),
        "project_limit": config.LIMIT_PROJECTS_PER_USER,
    })
