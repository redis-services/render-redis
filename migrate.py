"""Inspect and migrate a pre-accounts MongoDB database.

The original app stored projects as `{project_id, api_key}` with the key in
plaintext. The current schema keys projects on `id` and holds API keys in their
own collection, hashed. Documents from the old schema have no `id`, so Mongo
reads them all as `id: null` and refuses to build the unique index.

The app runs this migration automatically at startup. This script exists so you
can look at what will happen first.

    python migrate.py            # dry run — reports, changes nothing
    python migrate.py --apply    # perform the migration
    python migrate.py --claim you@example.com --apply
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from dotenv import load_dotenv

from app import config
from app.store import MongoStore, is_obsolete_index, legacy_project_documents

load_dotenv()


async def inspect(store: MongoStore) -> dict:
    legacy = [
        doc async for doc in store.projects.find(
            {"$or": [{"id": {"$exists": False}}, {"id": None}]}
        )
    ]
    current = await store.projects.count_documents({"id": {"$ne": None}})
    unowned = await store.projects.count_documents(
        {"$or": [{"user_id": None}, {"user_id": {"$exists": False}}], "id": {"$ne": None}}
    )

    obsolete = []
    for collection in (store.projects, store.users, store.sessions):
        try:
            existing = await collection.index_information()
        except Exception:  # noqa: BLE001
            continue
        obsolete += [
            f"{collection.name}.{name}"
            for name, spec in existing.items()
            if is_obsolete_index(name, spec)
        ]

    return {"legacy": legacy, "current": current, "unowned": unowned, "obsolete": obsolete}


async def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate a pre-accounts Central database.")
    parser.add_argument("--apply", action="store_true", help="Actually write changes")
    parser.add_argument("--claim", metavar="EMAIL",
                        help="Assign every ownerless project to this account")
    args = parser.parse_args()

    uri = config.mongodb_uri()
    if not uri:
        print("MONGODB_URI is not set. Nothing to migrate.")
        return 1

    store = MongoStore(uri, config.mongodb_db())
    from pymongo import AsyncMongoClient

    # Connect without running migrations or building indexes — index creation is
    # exactly what fails on an unmigrated database.
    store._client = AsyncMongoClient(uri, serverSelectionTimeoutMS=8000)
    await store._client.admin.command("ping")
    database = store._client[config.mongodb_db()]
    store.users = database["users"]
    store.sessions = database["sessions"]
    store.projects = database["projects"]
    store.api_keys = database["api_keys"]

    try:
        state = await inspect(store)

        print(f"\nDatabase: {config.mongodb_db()}")
        print(f"  Projects on the current schema : {state['current']}")
        print(f"  Projects on the old schema     : {len(state['legacy'])}")
        print(f"  Projects with no owner         : {state['unowned']}")

        if state["obsolete"]:
            print("\nWould drop these indexes, left over from the old schema:")
            for name in state["obsolete"]:
                print(f"  ✗ {name}")

        if state["legacy"]:
            print("\nWould migrate:")
            for doc in state["legacy"]:
                fields, key_document = legacy_project_documents(doc)
                if not fields:
                    print(f"  ✗ {doc.get('_id')} — no usable project_id, would be deleted")
                    continue
                key_note = "1 legacy key imported" if key_document else "no key found"
                print(f"  → {fields['id']:<24} {key_note}")

        if not state["legacy"] and not state["obsolete"]:
            print("\nNothing to migrate — this database is already on the current schema.")

        if not args.apply:
            print("\nDry run. Re-run with --apply to make these changes.\n")
            return 0

        report = await store.repair()
        print(f"\nMigrated {report['projects']} project(s), "
              f"imported {report['api_keys']} key(s), "
              f"dropped {report['indexes_dropped']} obsolete index(es), "
              f"removed {report['discarded']} unusable document(s).")
        print("Indexes built successfully.")

        if args.claim:
            user = await store.get_user_by_email(args.claim.strip().lower())
            if not user:
                print(f"\n⚠️  No account found for {args.claim}. "
                      "Sign up with that address first, then re-run with --claim.")
                return 1
            claimed = await store.claim_unowned_projects(user["id"])
            print(f"Assigned {claimed} project(s) to {args.claim}.")
        elif state["legacy"]:
            print("\nMigrated projects have no owner, so they are hidden from every "
                  "dashboard. Their API keys still work.\nRun with "
                  "--claim your@email.com to move them into your account.")

        print()
        return 0
    finally:
        await store.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
