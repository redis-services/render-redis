"""Control-plane storage: users, sessions, projects, API keys.

Two interchangeable backends sit behind one interface:

  MongoStore   — production. MongoDB Atlas, or any Mongo reachable via MONGODB_URI.
  MemoryStore  — tests and local development with no database running.

Tenant *data* never touches this layer; that lives in Redis. This is only the
control plane, which is small, low-traffic, and needs to survive restarts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from .security import hash_api_key, mask_api_key, new_id


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Fields that only existed in the pre-accounts schema. Any index built on one
# of them belongs to the old app and must be removed before migrating: the
# migration unsets these fields, and a unique index over a field that is about
# to become null on every document will reject the second document it sees.
OBSOLETE_INDEX_FIELDS = frozenset({"project_id", "api_key"})


def is_obsolete_index(name: str, spec: dict) -> bool:
    if name == "_id_":
        return False
    keys = [field for field, _direction in spec.get("key", [])]
    return any(field in OBSOLETE_INDEX_FIELDS for field in keys)


def legacy_project_documents(doc: dict) -> tuple[dict, dict | None]:
    """Convert a pre-accounts project document into the current schema.

    The original app stored projects as `{project_id, api_key}` with the key in
    plaintext. The current schema uses `id` as the primary field and keeps API
    keys in their own collection, hashed. Returns the fields to set on the
    project plus an api_keys document, or (None-ish) if the row is unusable.

    Migrated projects get `user_id: None` — nobody owns them, so they stay out
    of every dashboard until explicitly claimed, but their keys keep working.
    """
    project_id = str(doc.get("project_id") or "").strip().lower()
    if not project_id:
        return {}, None

    created_at = doc.get("created_at") or utcnow()
    project_fields = {
        "id": project_id,
        "user_id": doc.get("user_id"),
        "name": doc.get("name") or project_id,
        "description": doc.get("description", ""),
        "created_at": created_at,
        "settings": doc.get("settings") or {"default_ttl": 0, "apply_default_ttl": False},
        "migrated_from_legacy": True,
    }

    api_key = str(doc.get("api_key") or "").strip()
    key_document = None
    if api_key:
        key_document = {
            "id": new_id("key"),
            "project_id": project_id,
            "user_id": doc.get("user_id"),
            "name": "Legacy key",
            "key_hash": hash_api_key(api_key),
            "masked": mask_api_key(api_key),
            "created_at": created_at,
            "last_used_at": None,
            "revoked_at": None,
        }
    return project_fields, key_document


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
    @abstractmethod
    async def list_unowned_projects(self) -> list[dict]: ...
    @abstractmethod
    async def list_all_projects(self) -> list[dict]: ...
    @abstractmethod
    async def list_all_users(self) -> list[dict]: ...

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

        # Migrations run first. Unique indexes cannot be built over documents
        # from the old schema, where `id` is absent and therefore null.
        await self.migrate()
        await self.ensure_indexes()

    async def ensure_indexes(self) -> None:
        wanted = [
            (self.users, "id", {"unique": True}),
            (self.users, "email", {"unique": True}),
            (self.sessions, "token_hash", {"unique": True}),
            (self.sessions, "user_id", {}),
            # Mongo evicts expired sessions for us.
            (self.sessions, "expires_at", {"expireAfterSeconds": 0}),
            (self.projects, "id", {"unique": True}),
            (self.projects, "user_id", {}),
            (self.api_keys, "id", {"unique": True}),
            (self.api_keys, "key_hash", {"unique": True}),
            (self.api_keys, "project_id", {}),
        ]
        for collection, field, options in wanted:
            try:
                await collection.create_index(field, **options)
            except Exception as exc:  # noqa: BLE001 - report, don't guess
                raise RuntimeError(
                    f"Could not build the index on {collection.name}.{field}: {exc}\n"
                    "This usually means documents from an older schema are still present. "
                    "Run `python migrate.py` to see what's there, then `--apply` to fix it."
                ) from exc

    async def drop_obsolete_indexes(self) -> list[str]:
        """Remove indexes left behind by the pre-accounts schema."""
        dropped: list[str] = []
        for collection in (self.projects, self.api_keys, self.users, self.sessions):
            try:
                existing = await collection.index_information()
            except Exception:  # noqa: BLE001 - a missing collection has no indexes
                continue
            for name, spec in existing.items():
                if is_obsolete_index(name, spec):
                    # api_keys.project_id is a current index, not a legacy one.
                    if collection is self.api_keys and name == "project_id_1":
                        continue
                    await collection.drop_index(name)
                    dropped.append(f"{collection.name}.{name}")
        if dropped:
            print(f"Migration: dropped obsolete index(es) {', '.join(dropped)}")
        return dropped

    async def migrate(self) -> dict:
        """Bring documents from the pre-accounts schema up to date.

        Idempotent: it only touches project documents that have no `id`, so
        running it on an already-migrated database does nothing.
        """
        report = {"projects": 0, "api_keys": 0, "discarded": 0, "indexes_dropped": 0}

        # Must happen before any document is touched. The migration unsets
        # `project_id`, and the old unique index on that field would reject the
        # second document to have it nulled.
        report["indexes_dropped"] = len(await self.drop_obsolete_indexes())

        query = {"$or": [{"id": {"$exists": False}}, {"id": None}]}

        # Materialise before mutating: updating documents that the cursor is
        # still walking can skip or repeat rows.
        legacy_docs = [doc async for doc in self.projects.find(query)]

        for doc in legacy_docs:
            fields, key_document = legacy_project_documents(doc)

            if not fields:
                # No usable project ID — nothing to migrate, and leaving it
                # would keep blocking the unique index.
                await self.projects.delete_one({"_id": doc["_id"]})
                report["discarded"] += 1
                continue

            # A project with this ID may already exist from a partial run.
            existing = await self.projects.find_one({"id": fields["id"]})
            if existing and existing["_id"] != doc["_id"]:
                await self.projects.delete_one({"_id": doc["_id"]})
                report["discarded"] += 1
                continue

            await self.projects.update_one(
                {"_id": doc["_id"]},
                {"$set": fields, "$unset": {"project_id": "", "api_key": ""}},
            )
            report["projects"] += 1

            if key_document and not await self.api_keys.find_one(
                {"key_hash": key_document["key_hash"]}
            ):
                await self.api_keys.insert_one(key_document)
                report["api_keys"] += 1

        # Stray null-id documents in the other collections predate nothing and
        # only exist to break unique indexes.
        for collection in (self.users, self.api_keys, self.sessions):
            field = "token_hash" if collection is self.sessions else "id"
            result = await collection.delete_many(
                {"$or": [{field: {"$exists": False}}, {field: None}]}
            )
            report["discarded"] += result.deleted_count

        if report["projects"] or report["discarded"]:
            print(
                f"Migration: {report['projects']} project(s) upgraded, "
                f"{report['api_keys']} legacy key(s) imported, "
                f"{report['discarded']} unusable document(s) removed."
            )
        return report

    async def repair(self) -> dict:
        """Migrate, then rebuild indexes. Safe to run repeatedly."""
        report = await self.migrate()
        await self.ensure_indexes()
        return report

    async def claim_unowned_projects(self, user_id: str) -> int:
        """Assign every ownerless project to a user. Used by LEGACY_OWNER_EMAIL."""
        result = await self.projects.update_many(
            {"$or": [{"user_id": None}, {"user_id": {"$exists": False}}]},
            {"$set": {"user_id": user_id}},
        )
        await self.api_keys.update_many(
            {"$or": [{"user_id": None}, {"user_id": {"$exists": False}}]},
            {"$set": {"user_id": user_id}},
        )
        return result.modified_count

    async def list_unowned_projects(self) -> list[dict]:
        cursor = self.projects.find(
            {"$or": [{"user_id": None}, {"user_id": {"$exists": False}}]}
        )
        return [_normalise(doc) async for doc in cursor]

    async def list_all_projects(self) -> list[dict]:
        cursor = self.projects.find({}).sort("created_at", -1)
        return [_normalise(doc) async for doc in cursor]

    async def list_all_users(self) -> list[dict]:
        cursor = self.users.find({}).sort("created_at", -1)
        return [_normalise(doc) async for doc in cursor]

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

    # No locking: every critical section below is a dict read followed by a
    # dict write with no await between them, so asyncio's single-threaded
    # scheduling already makes them atomic.

    def __init__(self):
        self._users: dict[str, dict] = {}
        self._sessions: dict[str, dict] = {}
        self._projects: dict[str, dict] = {}
        self._api_keys: dict[str, dict] = {}

    async def connect(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def create_user(self, doc: dict) -> dict:
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

    async def list_unowned_projects(self) -> list[dict]:
        return [dict(p) for p in self._projects.values() if not p.get("user_id")]

    async def list_all_projects(self) -> list[dict]:
        return sorted(
            (dict(p) for p in self._projects.values()),
            key=lambda p: p["created_at"], reverse=True,
        )

    async def list_all_users(self) -> list[dict]:
        return sorted(
            (dict(u) for u in self._users.values()),
            key=lambda u: u["created_at"], reverse=True,
        )

    async def claim_unowned_projects(self, user_id: str) -> int:
        claimed = 0
        for project in self._projects.values():
            if not project.get("user_id"):
                project["user_id"] = user_id
                claimed += 1
        for key in self._api_keys.values():
            if not key.get("user_id"):
                key["user_id"] = user_id
        return claimed

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


class StoreUnavailable(RuntimeError):
    """Raised when the control plane cannot be reached and falling back to a
    non-persistent store would silently destroy user data."""


async def build_store(uri: str, db_name: str, allow_fallback: bool = True) -> tuple[Store, bool]:
    """Return (store, is_persistent).

    Falling back to memory is convenient locally and catastrophic in
    production: the app boots, accepts sign-ups, and loses every account on the
    next restart. So the fallback is opt-in via `allow_fallback`, which
    main.py sets to False whenever the app is running in production.
    """
    if not uri:
        message = "MONGODB_URI is not set."
        if not allow_fallback:
            raise StoreUnavailable(
                f"{message} Refusing to start in production without a persistent store — "
                "accounts would be lost on every restart. Set MONGODB_URI, or set "
                "ALLOW_MEMORY_STORE=true if you really want an ephemeral deployment."
            )
        print(f"⚠️  {message} Using in-memory store; data will not survive a restart.")
        store = MemoryStore()
        await store.connect()
        return store, False

    store = MongoStore(uri, db_name)
    try:
        await store.connect()
        print(f"MongoDB connected: {db_name}")
        return store, True
    except Exception as exc:  # noqa: BLE001 - driver errors vary widely
        await store.close()
        if not allow_fallback:
            raise StoreUnavailable(
                f"MongoDB connection failed: {exc}\n"
                "Refusing to fall back to an in-memory store in production."
            ) from exc
        print(f"⚠️  MongoDB connection failed ({exc}); falling back to in-memory store.")
        fallback = MemoryStore()
        await fallback.connect()
        return fallback, False
