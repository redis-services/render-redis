"""Test fixtures: a real app instance backed by fakeredis and the memory store."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Must be set before importing the app, which reads config at import time.
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.pop("MONGODB_URI", None)
os.environ["SECURE_COOKIES"] = "false"
os.environ["KEEP_ALIVE_ENABLED"] = "false"


@pytest.fixture()
def client(monkeypatch):
    import fakeredis.aioredis as fakeredis
    import redis.asyncio as aioredis

    monkeypatch.setattr(
        aioredis, "from_url",
        lambda *args, **kwargs: fakeredis.FakeRedis(decode_responses=True),
    )

    import main
    from app.deps import key_cache

    key_cache.clear()

    from fastapi.testclient import TestClient

    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture()
def account(client):
    """A signed-up user with an active session cookie."""
    response = client.post(
        "/signup",
        data={"email": "dev@example.com", "password": "correct-horse-battery", "name": "Dev"},
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    return {"email": "dev@example.com", "password": "correct-horse-battery"}


@pytest.fixture()
def project(client, account):
    response = client.post("/api/projects", json={"project_id": "checkout_svc"})
    assert response.status_code == 201, response.text
    return response.json()
