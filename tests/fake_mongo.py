"""A minimal async Mongo stand-in, just faithful enough to reproduce index bugs.

This exists for one reason: the migration failed twice in production because of
unique-index semantics — nulls collide, and an index left over from the old
schema rejects writes the migration needs to make. Those failures are invisible
to a test that only checks document shapes, so this fake enforces unique
indexes on insert *and* update, which is exactly where the real failures were.

It is not a general Mongo emulator. It supports only the operations
`MongoStore.migrate` and `ensure_indexes` actually perform.
"""

from __future__ import annotations

import itertools
from typing import Any


class DuplicateKeyError(Exception):
    pass


_counter = itertools.count(1)


def _matches(doc: dict, query: dict) -> bool:
    for field, condition in query.items():
        if field == "$or":
            if not any(_matches(doc, clause) for clause in condition):
                return False
            continue
        value = doc.get(field, _MISSING)
        if isinstance(condition, dict):
            for operator, operand in condition.items():
                if operator == "$exists":
                    if (value is not _MISSING) != operand:
                        return False
                elif operator == "$ne":
                    if (None if value is _MISSING else value) == operand:
                        return False
                else:
                    raise NotImplementedError(f"operator {operator}")
        else:
            if value is _MISSING or value != condition:
                return False
    return True


class _Missing:
    def __repr__(self) -> str:
        return "<missing>"


_MISSING = _Missing()


class _Cursor:
    def __init__(self, docs: list[dict]):
        self._docs = docs

    def __aiter__(self):
        async def generator():
            for doc in self._docs:
                yield dict(doc)
        return generator()

    def sort(self, *_args, **_kwargs):
        return self


class FakeCollection:
    def __init__(self, name: str):
        self.name = name
        self._docs: list[dict] = []
        self._indexes: dict[str, dict] = {"_id_": {"key": [("_id", 1)], "unique": True}}

    # ── Index management ────────────────────────────────────────────────────

    async def index_information(self) -> dict:
        return {name: dict(spec) for name, spec in self._indexes.items()}

    async def create_index(self, field: str, unique: bool = False, **_options) -> str:
        name = f"{field}_1"
        if unique:
            self._assert_unique(field, self._docs)
        self._indexes[name] = {"key": [(field, 1)], "unique": unique}
        return name

    async def drop_index(self, name: str) -> None:
        self._indexes.pop(name, None)

    def _assert_unique(self, field: str, docs: list[dict]) -> None:
        seen = set()
        for doc in docs:
            value = doc.get(field)  # a missing field indexes as null, as in Mongo
            if value in seen:
                raise DuplicateKeyError(
                    f"E11000 duplicate key error collection: {self.name} "
                    f"index: {field}_1 dup key: {{ {field}: {value!r} }}"
                )
            seen.add(value)

    def _check_unique_indexes(self, candidate_docs: list[dict]) -> None:
        for name, spec in self._indexes.items():
            if not spec.get("unique") or name == "_id_":
                continue
            field = spec["key"][0][0]
            self._assert_unique(field, candidate_docs)

    # ── Reads ───────────────────────────────────────────────────────────────

    def find(self, query: dict | None = None, projection: Any = None) -> _Cursor:
        return _Cursor([d for d in self._docs if _matches(d, query or {})])

    async def find_one(self, query: dict) -> dict | None:
        for doc in self._docs:
            if _matches(doc, query):
                return dict(doc)
        return None

    async def count_documents(self, query: dict) -> int:
        return sum(1 for doc in self._docs if _matches(doc, query))

    # ── Writes ──────────────────────────────────────────────────────────────

    async def insert_one(self, doc: dict):
        record = dict(doc)
        record.setdefault("_id", next(_counter))
        self._check_unique_indexes(self._docs + [record])
        self._docs.append(record)
        return type("Result", (), {"inserted_id": record["_id"]})()

    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        for index, doc in enumerate(self._docs):
            if not _matches(doc, query):
                continue
            candidate = dict(doc)
            candidate.update(update.get("$set", {}))
            for field in update.get("$unset", {}):
                candidate.pop(field, None)

            others = self._docs[:index] + self._docs[index + 1:]
            self._check_unique_indexes(others + [candidate])
            self._docs[index] = candidate
            return type("Result", (), {"modified_count": 1})()

        if upsert:
            await self.insert_one({**query, **update.get("$set", {})})
            return type("Result", (), {"modified_count": 0})()
        return type("Result", (), {"modified_count": 0})()

    async def update_many(self, query: dict, update: dict):
        modified = 0
        for index, doc in enumerate(self._docs):
            if _matches(doc, query):
                self._docs[index] = {**doc, **update.get("$set", {})}
                modified += 1
        return type("Result", (), {"modified_count": modified})()

    async def delete_one(self, query: dict):
        for index, doc in enumerate(self._docs):
            if _matches(doc, query):
                del self._docs[index]
                return type("Result", (), {"deleted_count": 1})()
        return type("Result", (), {"deleted_count": 0})()

    async def delete_many(self, query: dict):
        before = len(self._docs)
        self._docs = [doc for doc in self._docs if not _matches(doc, query)]
        return type("Result", (), {"deleted_count": before - len(self._docs)})()


def build_legacy_database(projects: list[dict]) -> dict[str, FakeCollection]:
    """A database in exactly the state the old app left behind: project
    documents keyed on `project_id`, with a unique index on that field."""
    collections = {
        name: FakeCollection(name)
        for name in ("users", "sessions", "projects", "api_keys")
    }
    for doc in projects:
        collections["projects"]._docs.append({**doc, "_id": next(_counter)})
    collections["projects"]._indexes["project_id_1"] = {
        "key": [("project_id", 1)], "unique": True
    }
    return collections
