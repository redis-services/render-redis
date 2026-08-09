"""Account lifecycle: sign up, sign in, sessions, profile, deletion."""

from __future__ import annotations

import re
from datetime import timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .. import config, keyspace, metrics
from ..deps import get_optional_user, get_redis, get_store, require_user_page
from ..security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    new_id,
    password_problem,
    verify_password,
)
from ..store import Store, utcnow
from ..templating import page

router = APIRouter(tags=["auth"])

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


def _redirect(path: str, message: str = "", message_type: str = "ok") -> RedirectResponse:
    if message:
        path = f"{path}?{urlencode({'msg': message, 'msg_type': message_type})}"
    return RedirectResponse(path, status_code=303)


def _set_session_cookie(response: RedirectResponse, token: str) -> None:
    response.set_cookie(
        config.SESSION_COOKIE,
        token,
        max_age=config.SESSION_TTL_DAYS * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=config.secure_cookies(),
        path="/",
    )


async def _start_session(request: Request, store: Store, user_id: str) -> str:
    token = generate_session_token()
    await store.create_session({
        "token_hash": hash_session_token(token),
        "user_id": user_id,
        "created_at": utcnow(),
        "last_seen_at": utcnow(),
        "expires_at": utcnow() + timedelta(days=config.SESSION_TTL_DAYS),
        "user_agent": (request.headers.get("user-agent") or "")[:300],
        "ip": request.client.host if request.client else "",
    })
    return token


# ── Pages ──────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    user = await get_optional_user(request)
    return RedirectResponse("/app" if user else "/login", status_code=303)


@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    if await get_optional_user(request):
        return RedirectResponse("/app", status_code=303)
    return page(request, "auth/signup.html", {
        "signups_enabled": config.signups_enabled(),
    })


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if await get_optional_user(request):
        return RedirectResponse("/app", status_code=303)
    return page(request, "auth/login.html", {
        "next_url": request.query_params.get("next", "/app"),
    })


# ── Actions ────────────────────────────────────────────────────────────────────

@router.post("/signup")
async def signup(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(""),
    store: Store = Depends(get_store),
):
    if not config.signups_enabled():
        return _redirect("/signup", "Sign-ups are currently closed.", "err")

    email = email.strip().lower()
    if not EMAIL_PATTERN.match(email):
        return _redirect("/signup", "Enter a valid email address.", "err")

    problem = password_problem(password)
    if problem:
        return _redirect("/signup", problem, "err")

    if await store.get_user_by_email(email):
        # Deliberately vague: confirming which emails are registered leaks
        # membership. The message points at the recovery path instead.
        return _redirect("/login", "That email is already registered. Try signing in.", "err")

    user = {
        "id": new_id("usr"),
        "email": email,
        "name": name.strip()[:120],
        "password_hash": hash_password(password),
        "created_at": utcnow(),
        "email_verified": False,
        # Derived from ADMIN_EMAILS, never from anything the visitor sends.
        "role": config.role_for(email),
    }
    try:
        await store.create_user(user)
    except Exception:  # noqa: BLE001 - unique index race
        return _redirect("/login", "That email is already registered. Try signing in.", "err")

    token = await _start_session(request, store, user["id"])
    response = _redirect("/app", "Welcome to Central. Create your first project to get started.")
    _set_session_cookie(response, token)
    return response


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next_url: str = Form("/app"),
    store: Store = Depends(get_store),
):
    email = email.strip().lower()
    user = await store.get_user_by_email(email)

    # Hash even when the user is missing, so a failed lookup and a wrong
    # password take the same amount of time.
    stored_hash = user["password_hash"] if user else hash_password("placeholder")
    if not user or not verify_password(password, stored_hash):
        return _redirect("/login", "Incorrect email or password.", "err")

    token = await _start_session(request, store, user["id"])
    destination = next_url if next_url.startswith("/") and not next_url.startswith("//") else "/app"
    response = _redirect(destination)
    _set_session_cookie(response, token)
    return response


@router.post("/logout")
async def logout(request: Request, store: Store = Depends(get_store)):
    token = request.cookies.get(config.SESSION_COOKIE)
    if token:
        await store.delete_session(hash_session_token(token))
    response = _redirect("/login", "Signed out.")
    response.delete_cookie(config.SESSION_COOKIE, path="/")
    return response


# ── Account ────────────────────────────────────────────────────────────────────

@router.get("/account", response_class=HTMLResponse)
async def account_page(request: Request, user: dict = Depends(require_user_page),
                       store: Store = Depends(get_store)):
    sessions = await store.list_sessions(user["id"])
    current_hash = hash_session_token(request.cookies.get(config.SESSION_COOKIE, ""))
    for session in sessions:
        session["is_current"] = session["token_hash"] == current_hash
        session["device"] = _describe_user_agent(session.get("user_agent", ""))
    projects = await store.list_projects(user["id"])
    return page(request, "app/account.html", {
        "user": user,
        "sessions": sessions,
        "projects": projects,
        "project_count": len(projects),
    })


@router.post("/account/profile")
async def update_profile(
    request: Request,
    name: str = Form(""),
    user: dict = Depends(require_user_page),
    store: Store = Depends(get_store),
):
    await store.update_user(user["id"], {"name": name.strip()[:120]})
    return _redirect("/account", "Profile updated.")


@router.post("/account/password")
async def update_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    user: dict = Depends(require_user_page),
    store: Store = Depends(get_store),
):
    if not verify_password(current_password, user["password_hash"]):
        return _redirect("/account", "Current password is incorrect.", "err")
    if new_password != confirm_password:
        return _redirect("/account", "New passwords do not match.", "err")
    problem = password_problem(new_password)
    if problem:
        return _redirect("/account", problem, "err")

    await store.update_user(user["id"], {"password_hash": hash_password(new_password)})
    # Changing a password should end every other session.
    current_hash = hash_session_token(request.cookies.get(config.SESSION_COOKIE, ""))
    revoked = await store.delete_user_sessions(user["id"], keep=current_hash)
    suffix = f" {revoked} other session{'s' if revoked != 1 else ''} signed out." if revoked else ""
    return _redirect("/account", f"Password updated.{suffix}")


@router.post("/account/sessions/revoke")
async def revoke_session(
    request: Request,
    token_hash: str = Form(...),
    user: dict = Depends(require_user_page),
    store: Store = Depends(get_store),
):
    session = await store.get_session(token_hash)
    if not session or session["user_id"] != user["id"]:
        return _redirect("/account", "Session not found.", "err")
    await store.delete_session(token_hash)
    return _redirect("/account", "Session revoked.")


@router.post("/account/sessions/revoke-others")
async def revoke_other_sessions(
    request: Request,
    user: dict = Depends(require_user_page),
    store: Store = Depends(get_store),
):
    current_hash = hash_session_token(request.cookies.get(config.SESSION_COOKIE, ""))
    revoked = await store.delete_user_sessions(user["id"], keep=current_hash)
    return _redirect("/account", f"Signed out of {revoked} other session{'s' if revoked != 1 else ''}.")


@router.post("/account/delete")
async def delete_account(
    request: Request,
    confirm_email: str = Form(...),
    password: str = Form(...),
    user: dict = Depends(require_user_page),
    store: Store = Depends(get_store),
    redis=Depends(get_redis),
):
    if confirm_email.strip().lower() != user["email"]:
        return _redirect("/account", "Email confirmation did not match.", "err")
    if not verify_password(password, user["password_hash"]):
        return _redirect("/account", "Password is incorrect.", "err")

    for project in await store.list_projects(user["id"]):
        await keyspace.flush_project(redis, project["id"])
        await metrics.purge(redis, project["id"])
        await store.delete_project_api_keys(project["id"])
        await store.delete_project(project["id"])

    await store.delete_user_sessions(user["id"])
    await store.delete_user(user["id"])

    response = _redirect("/signup", "Your account and all of its data have been deleted.")
    response.delete_cookie(config.SESSION_COOKIE, path="/")
    return response


def _describe_user_agent(agent: str) -> str:
    agent = agent or ""
    browser = next(
        (name for token, name in (
            ("Edg/", "Edge"), ("OPR/", "Opera"), ("Chrome/", "Chrome"),
            ("Firefox/", "Firefox"), ("Safari/", "Safari"),
        ) if token in agent),
        "Unknown browser",
    )
    platform = next(
        (name for token, name in (
            ("Windows", "Windows"), ("Macintosh", "macOS"), ("iPhone", "iPhone"),
            ("iPad", "iPad"), ("Android", "Android"), ("Linux", "Linux"),
        ) if token in agent),
        "Unknown device",
    )
    return f"{browser} on {platform}"
