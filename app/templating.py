"""Shared Jinja environment and view helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


def format_bytes(value: int | float | None) -> str:
    if not value:
        return "0 B"
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def format_count(value: int | float | None) -> str:
    number = int(value or 0)
    if number < 1000:
        return str(number)
    if number < 1_000_000:
        return f"{number / 1000:.1f}k".replace(".0k", "k")
    return f"{number / 1_000_000:.1f}M".replace(".0M", "M")


def format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "∞"
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"


def relative_time(value: datetime | None) -> str:
    if not value:
        return "never"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - value
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    if seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    days = seconds // 86400
    if days < 30:
        return f"{days} day{'s' if days > 1 else ''} ago"
    return value.strftime("%b %d, %Y")


templates.env.filters["bytes"] = format_bytes
templates.env.filters["count"] = format_count
templates.env.filters["duration"] = format_duration
templates.env.filters["ago"] = relative_time


def base_url(request: Request) -> str:
    from . import config
    override = config.base_url_override()
    return override or str(request.base_url).rstrip("/")


def page(request: Request, name: str, context: dict | None = None, status_code: int = 200):
    """Render a template with the values every page needs."""
    payload = {
        "request": request,
        "base_url": base_url(request),
        "message": request.query_params.get("msg", ""),
        "message_type": request.query_params.get("msg_type", "ok"),
    }
    payload.update(context or {})
    return templates.TemplateResponse(request, name, payload, status_code=status_code)
