"""Control-plane storage: users, sessions, projects, API keys.

Two interchangeable backends sit behind one interface:

  MongoStore   — production. MongoDB Atlas, or any Mongo reachable via MONGODB_URI.
  MemoryStore  — tests and local development with no database running.

Tenant *data* never touches this layer; that lives in Redis. This is only the
control plane, which is small, low-traffic, and needs to survive restarts.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: Any) -> Any:
    """Mongo returns naive UTC datetimes; normalise them so comparisons work."""
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _normalise(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    doc.pop("_id", None)
    return {key: _as_aware(val) for key, val in doc.items()}


class Store(ABC):
    """Interface implemented by both backends."""

    @abstractmethod
    async def connect(self) -> None: ...
    @abstractmethod
    async def close(self) -> None: ...

    # Users
    @abstractmethod
    async def create_user(self, doc: dict) -> dict: ...
    @abstractmethod
    async def get_user_by_email(self, email: str) -> dict | None: ...
    @abstractmethod
    async def get_user(self, user_id: str) -> dict | None: ...
    @abstractmethod
    async def update_user(self, user_id: str, fields: dict) -> None: ...
    @abstractmethod
    async def delete_user(self, user_id: str) -> None: ...

    # Sessions
    @abstractmethod
    async def create_session(self, doc: dict) -> dict: ...
    @abstractmethod
    async def get_session(self, token_hash: str) -> dict | None: ...
    @abstractmethod
    async def touch_session(self, token_hash: str, when: datetime) -> None: ...
    @abstractmethod
    async def delete_session(self, token_hash: str) -> None: ...
    @abstractmethod
    async def list_sessions(self, user_id: str) -> list[dict]: ...
    @abstractmethod
    async def delete_user_sessions(self, user_id: str, keep: str | None = None) -> int: ...

    # Projects
    @abstractmethod
    async def create_project(self, doc: dict) -> dict: ...
    @abstractmethod
    async def get_project(self, project_id: str) -> dict | None: ...
    @abstractmethod
    async def list_projects(self, user_id: str) -> list[dict]: ...
    @abstractmethod
    async def update_project(self, project_id: str, fields: dict) -> None: ...
    @abstractmethod
    async def delete_project(self, project_id: str) -> None: ...
    @abstractmethod
    async def count_projects(self, user_id: str) -> int: ...

    # API keys
    @abstractmethod
    async def create_api_key(self, doc: dict) -> dict: ...
    @abstractmethod
    async def get_api_key_by_hash(self, key_hash: str) -> dict | None: ...
    @abstractmethod
    async def get_api_key(self, key_id: str) -> dict | None: ...
    @abstractmethod
    async def list_api_keys(self, project_id: str) -> list[dict]: ...
    @abstractmethod
    async def update_api_key(self, key_id: str, fields: dict) -> None: ...
    @abstractmethod
    async def delete_api_key(self, key_id: str) -> None: ...
    @abstractmethod
    async def delete_project_api_keys(self, project_id: str) -> int: ...


# ── MongoDB ────────────────────────────────────────────────────────────────────

class MongoStore(Store):
    def __init__(self, uri: str, db_name: str):
        self._uri = uri
        self._db_name = db_name
        self._client = None
        self.users = None
        self.sessions = None
        self.projects = None
        self.api_keys = None

    async def connect(self) -> None:
        from pymongo import AsyncMongoClient

        self._client = AsyncMongoClient(self._uri, serverSelectionTimeoutMS=8000)
        await self._client.admin.command("ping")
        db = self._client[self._db_name]
        self.users = db["users"]
        self.sessions = db["sessions"]
        self.projects = db["projects"]
        self.api_keys = db["api_keys"]

        await self.users.create_index("id", unique=True)
        await self.users.create_index("email", unique=True)
        await self.sessions.create_index("token_hash", unique=True)
        await self.sessions.create_index("user_id")
        # Mongo evicts expired sessions for us.
        await self.sessions.create_index("expires_at", expireAfterSeconds=0)
        await self.projects.create_index("id", unique=True)
        await self.projects.create_index("user_id")
        await self.api_keys.create_index("id", unique=True)
        await self.api_keys.create_index("key_hash", unique=True)
        await self.api_keys.create_index("project_id")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()

    async def create_user(self, doc: dict) -> dict:
        await self.users.insert_one(dict(doc))
        return doc

    async def get_user_by_email(self, email: str) -> dict | None:
        return _normalise(await self.users.find_one({"email": email}))

    async def get_user(self, user_id: str) -> dict | None:
        return _normalise(await self.users.find_one({"id": user_id}))

    async def update_user(self, user_id: str, fields: dict) -> None:
        await self.users.update_one({"id": user_id}, {"$set": fields})

    async def delete_user(self, user_id: str) -> None:
        await self.users.delete_one({"id": user_id})

    async def create_session(self, doc: dict) -> dict:
        await self.sessions.insert_one(dict(doc))
        return doc

    async def get_session(self, token_hash: str) -> dict | None:
        return _normalise(await self.sessions.find_one({"token_hash": token_hash}))

    async def touch_session(self, token_hash: str, when: datetime) -> None:
        await self.sessions.update_one(
            {"token_hash": token_hash}, {"$set": {"last_seen_at": when}}
        )

    async def delete_session(self, token_hash: str) -> None:
        await self.sessions.delete_one({"token_hash": token_hash})

    async def list_sessions(self, user_id: str) -> list[dict]:
        cursor = self.sessions.find({"user_id": user_id}).sort("created_at", -1)
        return [_normalise(doc) async for doc in cursor]

    async def delete_user_sessions(self, user_id: str, keep: str | None = None) -> int:
        query: dict[str, Any] = {"user_id": user_id}
        if keep:
            query["token_hash"] = {"$ne": keep}
        result = await self.sessions.delete_many(query)
        return result.deleted_count

    async def create_project(self, doc: dict) -> dict:
        await self.projects.insert_one(dict(doc))
        return doc

    async def get_project(self, project_id: str) -> dict | None:
        return _normalise(await self.projects.find_one({"id": project_id}))

    async def list_projects(self, user_id: str) -> list[dict]:
        cursor = self.projects.find({"user_id": user_id}).sort("created_at", -1)
        return [_normalise(doc) async for doc in cursor]

    async def update_project(self, project_id: str, fields: dict) -> None:
        await self.projects.update_one({"id": project_id}, {"$set": fields})

    async def delete_project(self, project_id: str) -> None:
        await self.projects.delete_one({"id": project_id})

    async def count_projects(self, user_id: str) -> int:
        return await self.projects.count_documents({"user_id": user_id})

    async def create_api_key(self, doc: dict) -> dict:
        await self.api_keys.insert_one(dict(doc))
        return doc

    async def get_api_key_by_hash(self, key_hash: str) -> dict | None:
        return _normalise(await self.api_keys.find_one({"key_hash": key_hash}))

    async def get_api_key(self, key_id: str) -> dict | None:
        return _normalise(await self.api_keys.find_one({"id": key_id}))

    async def list_api_keys(self, project_id: str) -> list[dict]:
        cursor = self.api_keys.find({"project_id": project_id}).sort("created_at", 1)
        return [_normalise(doc) async for doc in cursor]

    async def update_api_key(self, key_id: str, fields: dict) -> None:
        await self.api_keys.update_one({"id": key_id}, {"$set": fields})

    async def delete_api_key(self, key_id: str) -> None:
        await self.api_keys.delete_one({"id": key_id})

    async def delete_project_api_keys(self, project_id: str) -> int:
        result = await self.api_keys.delete_many({"project_id": project_id})
        return result.deleted_count


# ── In-memory ──────────────────────────────────────────────────────────────────

class MemoryStore(Store):
    """Non-persistent backend. Everything vanishes on restart — fine for tests,
    fine for `python -m app` on a laptop, never appropriate in production."""

    def __init__(self):
        self._users: dict[str, dict] = {}
        self._sessions: dict[str, dict] = {}
        self._projects: dict[str, dict] = {}
        self._api_keys: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def create_user(self, doc: dict) -> dict:
        async with self._lock:
            if any(u["email"] == doc["email"] for u in self._users.values()):
                raise ValueError("duplicate email")
            self._users[doc["id"]] = dict(doc)
        return doc

    async def get_user_by_email(self, email: str) -> dict | None:
        for user in self._users.values():
            if user["email"] == email:
                return dict(user)
        return None

    async def get_user(self, user_id: str) -> dict | None:
        user = self._users.get(user_id)
        return dict(user) if user else None

    async def update_user(self, user_id: str, fields: dict) -> None:
        if user_id in self._users:
            self._users[user_id].update(fields)

    async def delete_user(self, user_id: str) -> None:
        self._users.pop(user_id, None)

    async def create_session(self, doc: dict) -> dict:
        self._sessions[doc["token_hash"]] = dict(doc)
        return doc

    async def get_session(self, token_hash: str) -> dict | None:
        session = self._sessions.get(token_hash)
        return dict(session) if session else None

    async def touch_session(self, token_hash: str, when: datetime) -> None:
        if token_hash in self._sessions:
            self._sessions[token_hash]["last_seen_at"] = when

    async def delete_session(self, token_hash: str) -> None:
        self._sessions.pop(token_hash, None)

    async def list_sessions(self, user_id: str) -> list[dict]:
        found = [dict(s) for s in self._sessions.values() if s["user_id"] == user_id]
        return sorted(found, key=lambda s: s["created_at"], reverse=True)

    async def delete_user_sessions(self, user_id: str, keep: str | None = None) -> int:
        doomed = [
            token for token, s in self._sessions.items()
            if s["user_id"] == user_id and token != keep
        ]
        for token in doomed:
            del self._sessions[token]
        return len(doomed)

    async def create_project(self, doc: dict) -> dict:
        async with self._lock:
            if doc["id"] in self._projects:
                raise ValueError("duplicate project")
            self._projects[doc["id"]] = dict(doc)
        return doc

    async def get_project(self, project_id: str) -> dict | None:
        project = self._projects.get(project_id)
        return dict(project) if project else None

    async def list_projects(self, user_id: str) -> list[dict]:
        found = [dict(p) for p in self._projects.values() if p["user_id"] == user_id]
        return sorted(found, key=lambda p: p["created_at"], reverse=True)

    async def update_project(self, project_id: str, fields: dict) -> None:
        if project_id in self._projects:
            self._projects[project_id].update(fields)

    async def delete_project(self, project_id: str) -> None:
        self._projects.pop(project_id, None)

    async def count_projects(self, user_id: str) -> int:
        return sum(1 for p in self._projects.values() if p["user_id"] == user_id)

    async def create_api_key(self, doc: dict) -> dict:
        self._api_keys[doc["id"]] = dict(doc)
        return doc

    async def get_api_key_by_hash(self, key_hash: str) -> dict | None:
        for key in self._api_keys.values():
            if key["key_hash"] == key_hash:
                return dict(key)
        return None

    async def get_api_key(self, key_id: str) -> dict | None:
        key = self._api_keys.get(key_id)
        return dict(key) if key else None

    async def list_api_keys(self, project_id: str) -> list[dict]:
        found = [dict(k) for k in self._api_keys.values() if k["project_id"] == project_id]
        return sorted(found, key=lambda k: k["created_at"])

    async def update_api_key(self, key_id: str, fields: dict) -> None:
        if key_id in self._api_keys:
            self._api_keys[key_id].update(fields)

    async def delete_api_key(self, key_id: str) -> None:
        self._api_keys.pop(key_id, None)

    async def delete_project_api_keys(self, project_id: str) -> int:
        doomed = [kid for kid, k in self._api_keys.items() if k["project_id"] == project_id]
        for kid in doomed:
            del self._api_keys[kid]
        return len(doomed)


async def build_store(uri: str, db_name: str) -> tuple[Store, bool]:
    """Return (store, is_persistent). Falls back to memory if Mongo is absent
    or unreachable, so a misconfigured deploy degrades instead of crashing."""
    if not uri:
        print("⚠️  MONGODB_URI not set — using in-memory store. Data will not survive a restart.")
        store = MemoryStore()
        await store.connect()
        return store, False

    store = MongoStore(uri, db_name)
    try:
        await store.connect()
        print(f"MongoDB connected: {db_name}")
        return store, True
    except Exception as exc:  # noqa: BLE001 - any driver error should degrade, not crash
        print(f"⚠️  MongoDB connection failed ({exc}); falling back to in-memory store.")
        await store.close()
        fallback = MemoryStore()
        await fallback.connect()
        return fallback, False
