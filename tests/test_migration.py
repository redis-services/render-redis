"""Migration tests run against a fake Mongo that enforces unique indexes.

Each test here corresponds to a real production failure.
"""

from __future__ import annotations

import asyncio

import pytest

from app.security import hash_api_key
from app.store import MongoStore
from tests.fake_mongo import DuplicateKeyError, build_legacy_database


def store_over(collections: dict) -> MongoStore:
    store = MongoStore("mongodb://fake", "central_redis")
    store.users = collections["users"]
    store.sessions = collections["sessions"]
    store.projects = collections["projects"]
    store.api_keys = collections["api_keys"]
    return store


def run(coroutine):
    return asyncio.run(coroutine)


LEGACY_PROJECTS = [
    {"project_id": "checkout_svc", "api_key": "old-key-one"},
    {"project_id": "user_sessions", "api_key": "old-key-two"},
    {"project_id": "rate_limiter", "api_key": "old-key-three"},
]


# ── The two failures that happened in production ───────────────────────────────

def test_index_build_fails_on_unmigrated_data():
    """Failure #1: every old document has no `id`, so they all index as null.

    The raw driver error is unreadable, so it is now wrapped in one that says
    what to do about it.
    """
    collections = build_legacy_database(LEGACY_PROJECTS)
    store = store_over(collections)

    with pytest.raises(RuntimeError) as caught:
        run(store.ensure_indexes())

    assert "projects.id" in str(caught.value)
    assert "migrate.py" in str(caught.value)


def test_migration_fails_while_the_old_unique_index_survives():
    """Failure #2: unsetting project_id nulls it on every document at once, and
    the old unique index rejects the second null."""
    collections = build_legacy_database(LEGACY_PROJECTS)
    store = store_over(collections)

    async def migrate_without_dropping_indexes():
        # Reproduce the buggy ordering: skip drop_obsolete_indexes.
        docs = [doc async for doc in store.projects.find({"id": {"$exists": False}})]
        for doc in docs:
            await store.projects.update_one(
                {"_id": doc["_id"]},
                {"$set": {"id": doc["project_id"]}, "$unset": {"project_id": ""}},
            )

    with pytest.raises(DuplicateKeyError, match="project_id_1"):
        run(migrate_without_dropping_indexes())


# ── The fix ────────────────────────────────────────────────────────────────────

def test_repair_migrates_and_builds_indexes():
    collections = build_legacy_database(LEGACY_PROJECTS)
    store = store_over(collections)

    report = run(store.repair())

    assert report["projects"] == 3
    assert report["api_keys"] == 3
    assert report["indexes_dropped"] == 1

    # The obsolete index is gone; the current ones exist.
    indexes = run(store.projects.index_information())
    assert "project_id_1" not in indexes
    assert "id_1" in indexes


def test_migrated_projects_have_the_current_shape():
    collections = build_legacy_database(LEGACY_PROJECTS)
    store = store_over(collections)
    run(store.repair())

    project = run(store.get_project("checkout_svc"))
    assert project["id"] == "checkout_svc"
    assert project["user_id"] is None
    assert project["migrated_from_legacy"] is True
    assert "project_id" not in project
    assert "api_key" not in project


def test_legacy_keys_still_authenticate_after_migration():
    collections = build_legacy_database(LEGACY_PROJECTS)
    store = store_over(collections)
    run(store.repair())

    record = run(store.get_api_key_by_hash(hash_api_key("old-key-two")))
    assert record is not None
    assert record["project_id"] == "user_sessions"
    assert record["name"] == "Legacy key"


def test_plaintext_keys_are_gone_after_migration():
    collections = build_legacy_database(LEGACY_PROJECTS)
    store = store_over(collections)
    run(store.repair())

    stored = str(collections["projects"]._docs) + str(collections["api_keys"]._docs)
    for secret in ("old-key-one", "old-key-two", "old-key-three"):
        assert secret not in stored


def test_repair_is_idempotent():
    collections = build_legacy_database(LEGACY_PROJECTS)
    store = store_over(collections)

    first = run(store.repair())
    second = run(store.repair())

    assert first["projects"] == 3
    assert second["projects"] == 0
    assert second["api_keys"] == 0
    assert len(collections["projects"]._docs) == 3
    assert len(collections["api_keys"]._docs) == 3


def test_repair_resumes_after_a_partial_failure():
    """The first production attempt died mid-migration. Re-running must finish
    the job rather than duplicating what already succeeded."""
    collections = build_legacy_database(LEGACY_PROJECTS)
    # Simulate one document having already been converted.
    already = collections["projects"]._docs[0]
    already["id"] = already.pop("project_id")
    already.pop("api_key")
    already["user_id"] = None

    store = store_over(collections)
    report = run(store.repair())

    assert report["projects"] == 2
    assert len(collections["projects"]._docs) == 3
    assert run(store.get_project("checkout_svc")) is not None


def test_junk_documents_are_discarded():
    collections = build_legacy_database(
        LEGACY_PROJECTS + [{"api_key": "orphan-with-no-project"}]
    )
    store = store_over(collections)

    report = run(store.repair())

    assert report["projects"] == 3
    assert report["discarded"] == 1
    assert len(collections["projects"]._docs) == 3


def test_duplicate_project_ids_collapse_to_one():
    collections = build_legacy_database([
        {"project_id": "checkout_svc", "api_key": "key-a"},
        {"project_id": "Checkout_SVC", "api_key": "key-b"},
    ])
    store = store_over(collections)

    run(store.repair())

    assert len(collections["projects"]._docs) == 1
    assert run(store.get_project("checkout_svc")) is not None


def test_claiming_assigns_migrated_projects_and_keys():
    collections = build_legacy_database(LEGACY_PROJECTS)
    store = store_over(collections)
    run(store.repair())

    claimed = run(store.claim_unowned_projects("usr_abc"))
    assert claimed == 3
    assert run(store.list_unowned_projects()) == []
    assert all(doc["user_id"] == "usr_abc" for doc in collections["api_keys"]._docs)


def test_a_clean_database_needs_no_migration():
    collections = {name: type(build_legacy_database([])["projects"])(name)
                   for name in ("users", "sessions", "projects", "api_keys")}
    store = store_over(collections)

    report = run(store.repair())

    assert report == {"projects": 0, "api_keys": 0, "discarded": 0, "indexes_dropped": 0}
