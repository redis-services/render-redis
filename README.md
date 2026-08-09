# Central

Multi-tenant Redis as a service. One Redis instance, one isolated namespace per
project, one API key per client, and a dashboard to manage it all.

A project's base URL is simply `https://your-host/{project_id}`, so a client
never learns a connection string — only a key and a URL.

```bash
curl -X POST https://your-host/checkout_svc/set/cart:42 \
  -H "x-api-key: $CENTRAL_KEY" \
  -H "Content-Type: application/json" \
  -d '{"value": {"items": 3}, "ttl": 3600}'
```

## Running it

```bash
pip install -r requirements.txt

export REDIS_URL="redis://localhost:6379/0"
export MONGODB_URI="mongodb+srv://…"     # optional locally, required in production
python main.py                            # http://localhost:8000
```

Without `MONGODB_URI` the app runs against an in-memory control plane. Accounts,
projects, and API keys work normally but vanish on restart — fine for a local
poke around, never appropriate in production. The app prints a warning at
startup when this happens, and `GET /health` reports `persistent_store: false`.

## Layout

```
main.py                  app assembly, metrics middleware, error handling, health
app/
  config.py              environment settings, reserved IDs, free-tier limits
  security.py            scrypt passwords, API key generation and hashing
  store.py               control plane — MongoStore and MemoryStore behind one interface
  keyspace.py            tenant data access; SCAN-based listing, type-aware reads
  metrics.py             request counters and latency histograms, stored in Redis
  deps.py                session auth, project ownership, API key resolution
  templating.py          Jinja environment and view filters
  routers/
    auth.py              signup, login, sessions, account management
    pages.py             dashboard HTML
    projects_api.py      JSON API the dashboard talks to
    data.py              the public tenant API
templates/               Jinja templates (no build step)
static/                  one stylesheet, one script (no build step)
tests/                   69 tests against fakeredis + the in-memory store
legacy/                  the pre-accounts admin panel and project registry
```

## How auth works

There are two independent authentication systems, and they never overlap.

**Dashboard — session cookies.** Passwords are hashed with scrypt (stdlib,
per-user salt). A successful login mints a random token; only its SHA-256 hash
is stored. Sessions carry an expiry that Mongo enforces with a TTL index, so
expired rows are removed even if nobody looks at them. Changing a password
revokes every other session.

**Tenant API — `x-api-key`.** Keys are `sk_live_` plus 32 random bytes. Only the
SHA-256 digest is stored; the full key is shown exactly once, at creation or
rotation. Lookups are indexed on the digest and cached in-process for 30
seconds, so a hot path doesn't hit the database on every request. Revocation and
rotation evict the cache entry immediately.

A key is bound to one project. Presenting a valid key for a *different* project
returns 401, not 404 — and asking for someone else's project from the dashboard
returns 404 rather than 403, because a 403 would confirm the project exists.

## Isolation

Every tenant key is stored as `{project_id}:{key}`. Nothing in `keyspace.py`
reads or writes outside that prefix. Metrics live under `_m:` so they can never
be confused with tenant data, and `_m:` is not a valid project ID.

Listing uses `SCAN` with a cursor, not `KEYS`. `KEYS` is O(N) and blocks the
whole server, which on a shared instance means one large tenant stalls everyone
else. `/keys` returns a cursor; pass it back until `done` is true.

## Metrics

A middleware records every tenant request into a Redis hash, one per project per
hour: request and error counts, per-operation counts, status codes, a duration
sum, and a latency histogram. Any time range is a fan-in over hourly keys.
Hashes expire after 35 days.

Percentiles come from histogram buckets, so a reported p95 of 50ms means
"between 25ms and 50ms" — an upper bound, not an exact figure. Metrics writes
are best-effort: a metrics failure never fails the request.

## Limits

Free-tier limits are displayed on the Usage page but not enforced unless you set
`ENFORCE_LIMITS=true`. Defaults: 10,000 keys, 100 MB, 1M requests/month, 10
projects per user, 10 API keys per project. All are overridable by environment
variable — see `app/config.py`.

## Migrating from the old version

The previous version had no user accounts: a single `ADMIN_PASSWORD` and a
global `PROJECT_REGISTRY` populated from `PROJECT_<ID>` environment variables.
`GET /admin` returned every project ID and plaintext API key with no server-side
authentication — the password check was client-side JavaScript. That route is
gone.

**Existing clients keep working.** Every original data endpoint is unchanged, at
the same path, with the same request and response shapes. `PROJECT_<ID>`
environment variables still authenticate their project, so deployments that
predate accounts don't break. Those projects won't appear in anyone's dashboard;
to bring one under management, create a project with the same ID from the
dashboard and move your clients to the new key.

**What changed for you:**

| Before | Now |
|---|---|
| `/admin` panel, one shared password | `/app` dashboard, per-user accounts |
| One API key per project | Up to 10, individually named and revocable |
| `KEYS` on every list | `SCAN` with a cursor |
| No metrics | Requests, latency, errors, per-operation counts |
| Keys visible in plaintext | Hashed; full value shown once |
| `projects.py` registry | `legacy/projects.py`, superseded by the store |

**Set `MONGODB_URI` before you deploy.** Without it every account is lost on the
next restart.

## Tests

```bash
pip install pytest fakeredis
python -m pytest tests/ -q
```

69 tests covering password hashing, session lifecycle, project ownership
boundaries, namespace isolation, key rotation and revocation, the data browser,
metrics accumulation, and that every page renders. They run against `fakeredis`
and the in-memory store, so no external services are needed.

## Known gaps

- No email verification or password reset. Both need an email provider.
- No OAuth. The sign-in screens leave room for it.
- No 2FA.
- IP allowlisting is designed but not implemented.
- Memory figures are extrapolated from a 500-key sample on large keyspaces;
  exact for anything smaller.
- Sorted sets and streams are readable in the browser but have no API endpoints.
