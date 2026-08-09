"""Roles, the project limit, and what an admin can and cannot reach."""

from __future__ import annotations

import pytest

from app import config


@pytest.fixture()
def as_admin(monkeypatch):
    """Promote the fixture account by naming it in ADMIN_EMAILS."""
    monkeypatch.setenv("ADMIN_EMAILS", "dev@example.com")


@pytest.fixture()
def one_project_limit(monkeypatch):
    monkeypatch.setattr(config, "LIMIT_PROJECTS_PER_USER", 1)


def signup(client, email, password="a-good-long-password"):
    return client.post(
        "/signup", data={"email": email, "password": password}, follow_redirects=False
    )


# ── Role assignment ────────────────────────────────────────────────────────────

def test_role_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "boss@example.com, other@example.com")
    assert config.role_for("boss@example.com") == "admin"
    assert config.role_for("BOSS@example.com") == "admin"
    assert config.role_for("someone@example.com") == "user"


def test_admin_emails_parsing(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", " A@x.com ; b@x.com , ,c@x.com ")
    assert config.admin_emails() == {"a@x.com", "b@x.com", "c@x.com"}


def test_no_admins_by_default(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    assert config.admin_emails() == frozenset()
    assert config.role_for("anyone@example.com") == "user"


def test_signup_assigns_the_user_role(client):
    signup(client, "plain@example.com")
    assert client.get("/app").status_code == 200
    assert client.get("/admin").status_code == 404


def test_promotion_takes_effect_without_a_new_signup(client, monkeypatch):
    signup(client, "later@example.com")
    assert client.get("/api/admin/overview").status_code == 404

    monkeypatch.setenv("ADMIN_EMAILS", "later@example.com")
    assert client.get("/api/admin/overview").status_code == 200


def test_demotion_takes_effect_immediately(client, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "temp@example.com")
    signup(client, "temp@example.com")
    assert client.get("/api/admin/overview").status_code == 200

    monkeypatch.setenv("ADMIN_EMAILS", "")
    assert client.get("/api/admin/overview").status_code == 404


def test_a_stored_admin_role_is_not_trusted(client, run_async):
    """Writing role=admin straight into the database must not grant anything."""
    import main

    signup(client, "sneaky@example.com")
    store = main.app.state.store
    user = run_async(store.get_user_by_email("sneaky@example.com"))
    run_async(store.update_user(user["id"], {"role": "admin"}))

    assert client.get("/api/admin/overview").status_code == 404
    # The next request also corrects the tampered value.
    refreshed = run_async(store.get_user(user["id"]))
    assert refreshed["role"] == "user"


# ── Project limit ──────────────────────────────────────────────────────────────

def test_user_is_capped_at_one_project(client, account, one_project_limit):
    assert client.post("/api/projects", json={"project_id": "first_svc"}).status_code == 201

    second = client.post("/api/projects", json={"project_id": "second_svc"})
    assert second.status_code == 403
    assert "1 project" in second.json()["detail"]


def test_deleting_frees_the_slot(client, account, one_project_limit):
    client.post("/api/projects", json={"project_id": "first_svc"})
    client.delete("/api/projects/first_svc")
    assert client.post("/api/projects", json={"project_id": "second_svc"}).status_code == 201


def test_admin_is_exempt_from_the_limit(client, as_admin, account, one_project_limit):
    assert client.post("/api/projects", json={"project_id": "first_svc"}).status_code == 201
    assert client.post("/api/projects", json={"project_id": "second_svc"}).status_code == 201


def test_limit_is_per_user_not_global(client, account, one_project_limit):
    client.post("/api/projects", json={"project_id": "first_svc"})
    client.post("/logout")

    signup(client, "second@example.com")
    assert client.post("/api/projects", json={"project_id": "their_svc"}).status_code == 201


# ── Admin visibility ───────────────────────────────────────────────────────────

def test_admin_sees_every_project_and_user(client, as_admin, account):
    client.post("/api/projects", json={"project_id": "mine_svc"})
    client.post("/logout")

    signup(client, "someone@example.com")
    client.post("/api/projects", json={"project_id": "theirs_svc"})
    client.post("/logout")

    client.post("/login", data={"email": account["email"], "password": account["password"]},
                follow_redirects=False)

    overview = client.get("/api/admin/overview").json()
    ids = {row["id"] for row in overview["projects"]}
    assert {"mine_svc", "theirs_svc"} <= ids
    assert overview["totals"]["users"] == 2

    emails = {row["email"] for row in overview["users"]}
    assert emails == {"dev@example.com", "someone@example.com"}
    roles = {row["email"]: row["role"] for row in overview["users"]}
    assert roles["dev@example.com"] == "admin"
    assert roles["someone@example.com"] == "user"


def test_admin_overview_attributes_projects_to_owners(client, as_admin, account):
    client.post("/logout")
    signup(client, "owner@example.com")
    client.post("/api/projects", json={"project_id": "theirs_svc"})
    client.post("/logout")
    client.post("/login", data={"email": account["email"], "password": account["password"]},
                follow_redirects=False)

    row = next(r for r in client.get("/api/admin/overview").json()["projects"]
               if r["id"] == "theirs_svc")
    assert row["owner_email"] == "owner@example.com"


def test_admin_detail_hides_key_material_and_values(client, as_admin, account):
    created = client.post("/api/projects", json={"project_id": "secret_svc"}).json()
    client.post("/secret_svc/set/private", json={"value": "top-secret-value"},
                headers={"x-api-key": created["api_key"]})

    detail = client.get("/api/admin/projects/secret_svc")
    assert detail.status_code == 200
    payload = detail.text

    assert created["api_key"] not in payload
    assert "top-secret-value" not in payload
    # Shape and volume are visible; contents are not.
    assert detail.json()["stats"]["keys"] == 1
    assert detail.json()["api_keys"][0]["name"] == "Default"
    assert "masked" not in detail.json()["api_keys"][0]


def test_admin_cannot_read_another_users_data(client, as_admin, account):
    client.post("/logout")
    signup(client, "victim@example.com")
    created = client.post("/api/projects", json={"project_id": "victim_svc"}).json()
    client.post("/victim_svc/set/private", json={"value": "theirs"},
                headers={"x-api-key": created["api_key"]})
    client.post("/logout")

    client.post("/login", data={"email": account["email"], "password": account["password"]},
                follow_redirects=False)

    # The ordinary project endpoints stay owner-scoped even for an admin.
    assert client.get("/api/projects/victim_svc").status_code == 404
    assert client.get("/api/projects/victim_svc/browse").status_code == 404
    assert client.get("/api/projects/victim_svc/api-keys").status_code == 404
    assert client.get("/api/projects/victim_svc/keys/private").status_code == 404


def test_admin_cannot_change_another_users_project(client, as_admin, account):
    client.post("/logout")
    signup(client, "victim@example.com")
    client.post("/api/projects", json={"project_id": "victim_svc"})
    client.post("/logout")
    client.post("/login", data={"email": account["email"], "password": account["password"]},
                follow_redirects=False)

    assert client.patch("/api/projects/victim_svc", json={"name": "seized"}).status_code == 404
    assert client.post("/api/projects/victim_svc/flush").status_code == 404
    assert client.delete("/api/projects/victim_svc").status_code == 404
    assert client.post("/api/projects/victim_svc/console",
                       json={"operation": "flush"}).status_code == 404


def test_admin_console_is_invisible_to_users(client, account):
    assert client.get("/admin").status_code == 404
    assert client.get("/api/admin/overview").status_code == 404
    assert client.get("/api/admin/projects/anything").status_code == 404


def test_admin_console_requires_a_session(client):
    assert client.get("/api/admin/overview").status_code == 401


def test_admin_pages_render(client, as_admin, account):
    client.post("/api/projects", json={"project_id": "mine_svc"})
    response = client.get("/admin")
    assert response.status_code == 200
    assert "Admin" in response.text


# ── Docs ───────────────────────────────────────────────────────────────────────

def test_docs_page_renders_for_a_user(client, account):
    client.post("/api/projects", json={"project_id": "mine_svc"})
    response = client.get("/docs")
    assert response.status_code == 200
    # Examples use the reader's own project.
    assert "mine_svc" in response.text
    assert "x-api-key" in response.text


def test_docs_page_falls_back_without_a_project(client, account):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "your_project" in response.text


def test_docs_require_a_session(client):
    response = client.get("/docs", follow_redirects=False)
    assert response.status_code == 303
    assert "/login" in response.headers["location"]


def test_swagger_is_admin_only(client, account):
    assert client.get("/api/docs").status_code == 404
    assert client.get("/api/openapi.json").status_code == 404


def test_swagger_is_available_to_admins(client, as_admin, account):
    assert client.get("/api/docs").status_code == 200
    schema = client.get("/api/openapi.json")
    assert schema.status_code == 200
    assert "/{project_id}/get/{key}" in schema.json()["paths"]
