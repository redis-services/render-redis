"""End-to-end coverage of the paths a real user and a real client take."""

from __future__ import annotations

import pytest

from app.security import (
    generate_api_key,
    hash_api_key,
    hash_password,
    mask_api_key,
    password_problem,
    verify_password,
)
from app.metrics import percentiles


# ── Pure functions ─────────────────────────────────────────────────────────────

def test_password_round_trip():
    encoded = hash_password("correct-horse-battery")
    assert verify_password("correct-horse-battery", encoded)
    assert not verify_password("wrong-horse-battery", encoded)
    assert not verify_password("", encoded)


def test_password_hashes_are_salted():
    assert hash_password("same-password") != hash_password("same-password")


def test_password_policy():
    assert password_problem("short") is not None
    assert password_problem("password123") is not None
    assert password_problem("a-perfectly-fine-password") is None


def test_verify_password_rejects_malformed_hash():
    assert not verify_password("anything", "not-a-hash")
    assert not verify_password("anything", "bcrypt$1$2$3$4$5")


def test_api_key_shape():
    key = generate_api_key()
    assert key.startswith("sk_live_")
    assert len(hash_api_key(key)) == 64
    masked = mask_api_key(key)
    assert "•" in masked and key not in masked


def test_percentiles_from_buckets():
    # 100 samples: 60 under 1ms, 95 cumulative under 5ms, 99 cumulative under 50ms.
    result = percentiles({"1": 60, "5": 35, "50": 4, "500": 1})
    assert result["p50"] == 1
    assert result["p95"] == 5
    assert result["p99"] == 50


def test_percentiles_with_no_data():
    assert percentiles({}) == {"p50": 0.0, "p95": 0.0, "p99": 0.0}


# ── Auth ───────────────────────────────────────────────────────────────────────

def test_root_redirects_to_login_when_anonymous(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_signup_creates_session(client):
    response = client.post(
        "/signup",
        data={"email": "new@example.com", "password": "a-good-long-password"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/app")
    assert client.cookies.get("central_session")


def test_signup_rejects_weak_password(client):
    response = client.post(
        "/signup", data={"email": "weak@example.com", "password": "short"},
        follow_redirects=False,
    )
    assert response.headers["location"].startswith("/signup?")
    assert "msg_type=err" in response.headers["location"]


def test_signup_rejects_duplicate_email(client, account):
    client.cookies.clear()
    response = client.post(
        "/signup", data={"email": account["email"], "password": "another-long-password"},
        follow_redirects=False,
    )
    assert response.headers["location"].startswith("/login?")


def test_login_with_wrong_password_fails(client, account):
    client.cookies.clear()
    response = client.post(
        "/login", data={"email": account["email"], "password": "nope-nope-nope"},
        follow_redirects=False,
    )
    assert "msg_type=err" in response.headers["location"]
    assert not client.cookies.get("central_session")


def test_login_then_logout(client, account):
    client.cookies.clear()
    login = client.post(
        "/login", data={"email": account["email"], "password": account["password"]},
        follow_redirects=False,
    )
    assert login.status_code == 303
    assert client.get("/api/projects").status_code == 200

    client.post("/logout", follow_redirects=False)
    assert client.get("/api/projects").status_code == 401


def test_dashboard_requires_login(client):
    response = client.get("/app", follow_redirects=False)
    assert response.status_code == 303
    assert "/login" in response.headers["location"]


def test_login_redirects_to_requested_page(client, account):
    client.cookies.clear()
    response = client.post(
        "/login",
        data={"email": account["email"], "password": account["password"], "next_url": "/account"},
        follow_redirects=False,
    )
    assert response.headers["location"] == "/account"


def test_login_ignores_external_redirect(client, account):
    client.cookies.clear()
    response = client.post(
        "/login",
        data={"email": account["email"], "password": account["password"],
              "next_url": "//evil.example.com"},
        follow_redirects=False,
    )
    assert response.headers["location"] == "/app"


# ── Projects ───────────────────────────────────────────────────────────────────

def test_create_project_returns_key_once(client, account):
    response = client.post("/api/projects", json={"project_id": "My Project"})
    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] == "my_project"
    assert payload["api_key"].startswith("sk_live_")

    listing = client.get("/api/projects").json()
    assert listing["projects"][0]["id"] == "my_project"
    assert "api_key" not in listing["projects"][0]


@pytest.mark.parametrize("project_id", ["admin", "api", "app", "health", "static"])
def test_reserved_project_ids_are_rejected(client, account, project_id):
    response = client.post("/api/projects", json={"project_id": project_id})
    assert response.status_code == 400
    assert "reserved" in response.json()["detail"].lower()


@pytest.mark.parametrize("project_id", ["ab", "1abc", "a" * 45, "_leading"])
def test_invalid_project_ids_are_rejected(client, account, project_id):
    assert client.post("/api/projects", json={"project_id": project_id}).status_code == 400


def test_duplicate_project_id_is_rejected(client, project):
    assert client.post("/api/projects", json={"project_id": "checkout_svc"}).status_code == 409


def test_projects_are_scoped_to_their_owner(client, project):
    client.post("/logout")
    client.post(
        "/signup", data={"email": "other@example.com", "password": "another-long-password"},
        follow_redirects=False,
    )
    # A 404 rather than 403: confirming existence would leak the other user's data.
    assert client.get("/api/projects/checkout_svc").status_code == 404
    assert client.get("/api/projects").json()["projects"] == []


# ── Tenant API ─────────────────────────────────────────────────────────────────

def test_set_and_get_round_trip(client, project):
    headers = {"x-api-key": project["api_key"]}
    write = client.post(
        f"/{project['id']}/set/cart:42", json={"value": {"items": 3}}, headers=headers
    )
    assert write.status_code == 200

    read = client.get(f"/{project['id']}/get/cart:42", headers=headers).json()
    assert read["value"] == {"items": 3}
    assert read["exists"] is True


def test_missing_key_reports_absence(client, project):
    read = client.get(
        f"/{project['id']}/get/nothing", headers={"x-api-key": project["api_key"]}
    ).json()
    assert read["exists"] is False and read["value"] is None


def test_wrong_api_key_is_rejected(client, project):
    response = client.get(f"/{project['id']}/get/cart:42", headers={"x-api-key": "sk_live_wrong"})
    assert response.status_code == 401


def test_missing_api_key_header_is_rejected(client, project):
    assert client.get(f"/{project['id']}/get/cart:42").status_code == 422


def test_unknown_project_is_not_found(client, project):
    response = client.get("/no_such_project/get/x", headers={"x-api-key": project["api_key"]})
    assert response.status_code == 404


def test_key_from_one_project_cannot_read_another(client, project):
    second = client.post("/api/projects", json={"project_id": "other_svc"}).json()
    response = client.get(
        f"/{second['id']}/get/anything", headers={"x-api-key": project["api_key"]}
    )
    assert response.status_code == 401


def test_namespaces_are_isolated(client, project):
    second = client.post("/api/projects", json={"project_id": "other_svc"}).json()
    client.post(f"/{project['id']}/set/shared", json={"value": "first"},
                headers={"x-api-key": project["api_key"]})
    client.post(f"/{second['id']}/set/shared", json={"value": "second"},
                headers={"x-api-key": second["api_key"]})

    first_value = client.get(f"/{project['id']}/get/shared",
                             headers={"x-api-key": project["api_key"]}).json()["value"]
    second_value = client.get(f"/{second['id']}/get/shared",
                              headers={"x-api-key": second["api_key"]}).json()["value"]
    assert (first_value, second_value) == ("first", "second")


def test_list_and_hash_operations(client, project):
    headers = {"x-api-key": project["api_key"]}
    client.post(f"/{project['id']}/rpush/queue", json={"values": ["a", "b"]}, headers=headers)
    values = client.get(f"/{project['id']}/lrange/queue", headers=headers).json()["values"]
    assert values == ["a", "b"]

    client.post(f"/{project['id']}/hset/user:1", json={"mapping": {"name": "Ada"}}, headers=headers)
    result = client.get(f"/{project['id']}/hgetall/user:1", headers=headers).json()
    assert result["value"] == {"name": "Ada"}


def test_set_operations(client, project):
    headers = {"x-api-key": project["api_key"]}
    client.post(f"/{project['id']}/sadd/tags", json={"members": ["x", "y", "x"]}, headers=headers)
    members = client.get(f"/{project['id']}/smembers/tags", headers=headers).json()["members"]
    assert sorted(members) == ["x", "y"]


def test_keys_endpoint_paginates(client, project):
    headers = {"x-api-key": project["api_key"]}
    for index in range(12):
        client.post(f"/{project['id']}/set/item:{index}", json={"value": index}, headers=headers)

    payload = client.get(f"/{project['id']}/keys?limit=1000", headers=headers).json()
    assert payload["count"] == 12
    assert all(not key.startswith(project["id"]) for key in payload["keys"])


def test_flush_only_clears_own_project(client, project):
    second = client.post("/api/projects", json={"project_id": "other_svc"}).json()
    client.post(f"/{project['id']}/set/a", json={"value": 1},
                headers={"x-api-key": project["api_key"]})
    client.post(f"/{second['id']}/set/a", json={"value": 1},
                headers={"x-api-key": second["api_key"]})

    client.delete(f"/{project['id']}/flush", headers={"x-api-key": project["api_key"]})

    assert client.get(f"/{project['id']}/keys",
                      headers={"x-api-key": project["api_key"]}).json()["count"] == 0
    assert client.get(f"/{second['id']}/keys",
                      headers={"x-api-key": second["api_key"]}).json()["count"] == 1


def test_ttl_is_applied(client, project):
    headers = {"x-api-key": project["api_key"]}
    client.post(f"/{project['id']}/set/temp", json={"value": "x", "ttl": 60}, headers=headers)
    ttl = client.get(f"/{project['id']}/ttl/temp", headers=headers).json()["ttl"]
    assert 0 < ttl <= 60


# ── API key management ─────────────────────────────────────────────────────────

def test_rotate_key_invalidates_the_old_one(client, project):
    keys = client.get(f"/api/projects/{project['id']}/api-keys").json()["api_keys"]
    rotated = client.post(
        f"/api/projects/{project['id']}/api-keys/{keys[0]['id']}/rotate"
    ).json()

    old = client.get(f"/{project['id']}/get/x", headers={"x-api-key": project["api_key"]})
    new = client.get(f"/{project['id']}/get/x", headers={"x-api-key": rotated["api_key"]})
    assert old.status_code == 401
    assert new.status_code == 200


def test_second_key_also_works(client, project):
    created = client.post(
        f"/api/projects/{project['id']}/api-keys", json={"name": "CI"}
    ).json()
    response = client.get(f"/{project['id']}/get/x", headers={"x-api-key": created["api_key"]})
    assert response.status_code == 200


def test_revoking_the_last_key_is_blocked(client, project):
    keys = client.get(f"/api/projects/{project['id']}/api-keys").json()["api_keys"]
    response = client.delete(f"/api/projects/{project['id']}/api-keys/{keys[0]['id']}")
    assert response.status_code == 400


def test_revoked_key_stops_working(client, project):
    extra = client.post(f"/api/projects/{project['id']}/api-keys", json={"name": "CI"}).json()
    assert client.get(f"/{project['id']}/get/x",
                      headers={"x-api-key": extra["api_key"]}).status_code == 200

    client.delete(f"/api/projects/{project['id']}/api-keys/{extra['id']}")
    assert client.get(f"/{project['id']}/get/x",
                      headers={"x-api-key": extra["api_key"]}).status_code == 401


# ── Dashboard API ──────────────────────────────────────────────────────────────

def test_browse_returns_types_and_ttl(client, project):
    headers = {"x-api-key": project["api_key"]}
    client.post(f"/{project['id']}/set/cart:1", json={"value": "a", "ttl": 300}, headers=headers)
    client.post(f"/{project['id']}/rpush/queue", json={"values": [1, 2]}, headers=headers)

    entries = client.get(f"/api/projects/{project['id']}/browse?limit=50").json()["keys"]
    by_key = {entry["key"]: entry for entry in entries}
    assert by_key["cart:1"]["type"] == "string"
    assert by_key["cart:1"]["ttl"] is not None
    assert by_key["queue"]["type"] == "list"
    assert by_key["queue"]["persistent"] is True


def test_browse_pattern_filter(client, project):
    headers = {"x-api-key": project["api_key"]}
    client.post(f"/{project['id']}/set/cart:1", json={"value": 1}, headers=headers)
    client.post(f"/{project['id']}/set/session:1", json={"value": 1}, headers=headers)

    entries = client.get(f"/api/projects/{project['id']}/browse?pattern=cart:*").json()["keys"]
    assert [entry["key"] for entry in entries] == ["cart:1"]


def test_dashboard_key_crud(client, project):
    base = f"/api/projects/{project['id']}/keys/config:flags"
    written = client.put(base, json={"type": "hash", "value": {"beta": True}})
    assert written.status_code == 200
    assert written.json()["value"] == {"beta": True}

    assert client.get(base).json()["type"] == "hash"
    assert client.delete(base).json()["deleted"] is True
    assert client.get(base).status_code == 404


def test_dashboard_rejects_mismatched_type(client, project):
    response = client.put(
        f"/api/projects/{project['id']}/keys/oops", json={"type": "banana", "value": 1}
    )
    assert response.status_code == 400


def test_console_executes_and_records(client, project):
    response = client.post(
        f"/api/projects/{project['id']}/console",
        json={"operation": "set", "key": "hello", "body": {"value": "world"}},
    )
    assert response.status_code == 200
    assert response.json()["status"] == 200

    read = client.get(f"/{project['id']}/get/hello",
                      headers={"x-api-key": project["api_key"]}).json()
    assert read["value"] == "world"


def test_console_rejects_unknown_operation(client, project):
    response = client.post(
        f"/api/projects/{project['id']}/console", json={"operation": "drop_database"}
    )
    assert response.status_code == 400


def test_metrics_accumulate_from_real_requests(client, project):
    headers = {"x-api-key": project["api_key"]}
    for index in range(4):
        client.post(f"/{project['id']}/set/k{index}", json={"value": index}, headers=headers)
    client.get(f"/{project['id']}/get/k0", headers=headers)

    usage = client.get(f"/api/projects/{project['id']}/usage?range=24h").json()
    assert usage["summary"]["requests"] >= 5
    assert usage["summary"]["operations"]["set"] >= 4
    assert usage["summary"]["operations"]["get"] >= 1

    activity = client.get(f"/api/projects/{project['id']}/activity").json()["activity"]
    assert activity and activity[0]["o"] in {"get", "set"}


def test_failed_auth_is_recorded_as_an_error(client, project):
    client.get(f"/{project['id']}/get/x", headers={"x-api-key": "sk_live_bogus"})
    usage = client.get(f"/api/projects/{project['id']}/usage?range=24h").json()
    assert usage["summary"]["errors"] >= 1


def test_delete_project_removes_data_and_keys(client, project):
    headers = {"x-api-key": project["api_key"]}
    client.post(f"/{project['id']}/set/gone", json={"value": 1}, headers=headers)

    assert client.delete(f"/api/projects/{project['id']}").status_code == 200
    assert client.get(f"/{project['id']}/get/gone", headers=headers).status_code == 404
    assert client.get("/api/projects").json()["projects"] == []


# ── Pages render ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", ["/login", "/signup"])
def test_public_pages_render(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert "Central" in response.text


@pytest.mark.parametrize("suffix", ["", "/browser", "/console", "/keys", "/usage", "/settings",
                                    "/quickstart"])
def test_project_pages_render(client, project, suffix):
    response = client.get(f"/app/{project['id']}{suffix}")
    assert response.status_code == 200
    assert project["id"] in response.text


def test_projects_and_account_pages_render(client, project):
    assert client.get("/app").status_code == 200
    assert client.get("/account").status_code == 200


def test_unknown_project_page_renders_error(client, account):
    response = client.get("/app/does_not_exist", headers={"accept": "text/html"})
    assert response.status_code == 404
    assert "Not found" in response.text


# ── Account management ─────────────────────────────────────────────────────────

def test_password_change_revokes_other_sessions(client, account):
    first_session = client.cookies.get("central_session")

    # Signing in again issues a second, independent session.
    client.post(
        "/login", data={"email": account["email"], "password": account["password"]},
        follow_redirects=False,
    )
    second_session = client.cookies.get("central_session")
    assert first_session != second_session

    client.post("/account/password", data={
        "current_password": account["password"],
        "new_password": "a-brand-new-password",
        "confirm_password": "a-brand-new-password",
    }, follow_redirects=False)

    # The session that made the change survives; the other one does not.
    assert client.get("/api/projects").status_code == 200

    client.cookies.clear()
    client.cookies.set("central_session", first_session)
    assert client.get("/api/projects").status_code == 401


def test_password_change_requires_the_current_password(client, account):
    response = client.post("/account/password", data={
        "current_password": "not-my-password",
        "new_password": "a-brand-new-password",
        "confirm_password": "a-brand-new-password",
    }, follow_redirects=False)
    assert "msg_type=err" in response.headers["location"]

    client.post("/logout")
    login = client.post(
        "/login", data={"email": account["email"], "password": account["password"]},
        follow_redirects=False,
    )
    assert login.headers["location"] == "/app"


def test_delete_account_removes_projects(client, project):
    response = client.post("/account/delete", data={
        "confirm_email": "dev@example.com",
        "password": "correct-horse-battery",
    }, follow_redirects=False)
    assert response.status_code == 303

    assert client.get(
        f"/{project['id']}/get/x", headers={"x-api-key": project["api_key"]}
    ).status_code == 404


# ── Ops ────────────────────────────────────────────────────────────────────────

def test_health_endpoint(client):
    payload = client.get("/health").json()
    assert payload["status"] == "ok"


def test_reserved_paths_are_not_treated_as_projects(client):
    assert client.get("/health").status_code == 200
    assert client.get("/login").status_code == 200
    assert client.get("/api/openapi.json").status_code == 200
