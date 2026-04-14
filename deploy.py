"""
Render Deployer
---------------
Deploys the Redis API service + managed Redis on Render.

Usage:
    python deploy.py                        # interactive
    python deploy.py --name my-redis-api    # with args
    python deploy.py add-project            # add a new project + generate key
    python deploy.py list-projects          # show all projects
"""

import os
import sys
import time
import secrets
import click
import requests
from dotenv import load_dotenv

load_dotenv()

RENDER_API   = "https://api.render.com/v1"
RENDER_KEY   = os.getenv("RENDER_API_KEY")
GITHUB_REPO  = os.getenv("GITHUB_REPO")   # e.g. https://github.com/you/redis-saas
POLL_INTERVAL = 6
POLL_TIMEOUT  = 360


def hdrs():
    if not RENDER_KEY:
        click.echo("❌  RENDER_API_KEY not set in .env", err=True)
        sys.exit(1)
    return {"Authorization": f"Bearer {RENDER_KEY}", "Content-Type": "application/json"}


def get(path, params=None):
    r = requests.get(f"{RENDER_API}{path}", headers=hdrs(), params=params)
    r.raise_for_status()
    return r.json()


def post(path, body):
    r = requests.post(f"{RENDER_API}{path}", headers=hdrs(), json=body)
    r.raise_for_status()
    return r.json()


def patch(path, body):
    r = requests.patch(f"{RENDER_API}{path}", headers=hdrs(), json=body)
    r.raise_for_status()
    return r.json()


# ── CLI ────────────────────────────────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """🔴 Redis SaaS Deployer — deploy your multi-tenant Redis API on Render."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(deploy)


@cli.command()
@click.option("--name",    default="redis-saas-api",  show_default=True, help="Service name on Render")
@click.option("--region",  default="oregon",           show_default=True,
              type=click.Choice(["oregon", "ohio", "virginia", "frankfurt", "singapore"]))
@click.option("--plan",    default="starter",          show_default=True,
              type=click.Choice(["free", "starter", "standard", "pro"]))
@click.option("--redis-plan", default="free",          show_default=True,
              type=click.Choice(["free", "starter", "standard", "pro"]), help="Managed Redis plan")
def deploy(name, region, plan, redis_plan):
    """Deploy the Redis API + managed Redis on Render."""

    if not GITHUB_REPO:
        click.echo("❌  GITHUB_REPO not set in .env (e.g. https://github.com/you/redis-saas)", err=True)
        sys.exit(1)

    click.echo(f"\n🚀 Starting deployment: {name}")
    click.echo(f"   Region: {region} | API plan: {plan} | Redis plan: {redis_plan}\n")

    # ── Step 1: Create managed Redis ──────────────────────────────────────────
    click.echo("1️⃣  Creating managed Redis instance...")
    try:
        redis_res = post("/redis", {
            "name": f"{name}-store",
            "plan": redis_plan,
            "region": region,
        })
    except requests.HTTPError as e:
        click.echo(f"❌  Failed to create Redis: {e.response.text}", err=True)
        sys.exit(1)

    redis_id = redis_res["id"]
    click.echo(f"   ✅ Redis created → ID: {redis_id}")

    # ── Step 2: Poll Redis until available ───────────────────────────────────
    click.echo("   ⏳ Waiting for Redis to be ready", nl=False)
    redis_url = _poll_redis(redis_id)
    click.echo(f"\n   ✅ Redis ready!")

    # ── Step 3: Deploy FastAPI web service ───────────────────────────────────
    click.echo("\n2️⃣  Deploying FastAPI service...")

    env_vars = [
        {"key": "REDIS_URL",    "value": redis_url},
        {"key": "PYTHON_VERSION", "value": "3.11.0"},
    ]

    try:
        svc_res = post("/services", {
            "type": "web_service",
            "name": name,
            "region": region,
            "plan": plan,
            "repo": GITHUB_REPO,
            "branch": "main",
            "buildCommand": "pip install -r requirements.txt",
            "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
            "envVars": env_vars,
        })
    except requests.HTTPError as e:
        click.echo(f"❌  Failed to create web service: {e.response.text}", err=True)
        sys.exit(1)

    svc_id  = svc_res["service"]["id"]
    svc_url = svc_res["service"].get("serviceDetails", {}).get("url", "")
    click.echo(f"   ✅ Service created → ID: {svc_id}")

    # ── Step 4: Poll service until live ──────────────────────────────────────
    click.echo("   ⏳ Waiting for service to go live", nl=False)
    svc_url = _poll_service(svc_id, svc_url)
    click.echo(f"\n   ✅ Service live!")

    # ── Done ──────────────────────────────────────────────────────────────────
    click.echo("\n" + "═" * 55)
    click.echo("🎉  DEPLOYMENT COMPLETE")
    click.echo("═" * 55)
    click.echo(f"  API URL    : https://{svc_url}")
    click.echo(f"  Health     : https://{svc_url}/health")
    click.echo(f"  Redis ID   : {redis_id}")
    click.echo(f"  Service ID : {svc_id}")
    click.echo("═" * 55)
    click.echo("\nNext: run `python deploy.py add-project` to create your first project.\n")

    # Save to .render-state for future commands
    _save_state(svc_id, svc_url, redis_id)


@cli.command("add-project")
@click.option("--project-id", prompt="Project ID (e.g. project_1)", help="Unique project identifier")
def add_project(project_id):
    """Add a new project to the deployed service."""

    project_id = project_id.lower().replace(" ", "_").replace("-", "_")
    api_key = secrets.token_urlsafe(32)

    state = _load_state()
    if not state:
        click.echo("❌  No deployed service found. Run `python deploy.py deploy` first.", err=True)
        sys.exit(1)

    svc_id  = state["service_id"]
    svc_url = state["service_url"]

    click.echo(f"\n➕ Adding project '{project_id}' to service {svc_id}...")

    # Add env var PROJECT_{project_id}=api_key to Render service
    env_key = f"PROJECT_{project_id.upper()}"
    try:
        patch(f"/services/{svc_id}/env-vars", [
            {"key": env_key, "value": api_key}
        ])
    except requests.HTTPError as e:
        click.echo(f"❌  Failed to update env vars: {e.response.text}", err=True)
        sys.exit(1)

    click.echo("\n" + "═" * 55)
    click.echo(f"✅  Project '{project_id}' created!")
    click.echo("═" * 55)
    click.echo(f"  Project ID : {project_id}")
    click.echo(f"  API Key    : {api_key}")
    click.echo(f"  Base URL   : https://{svc_url}/{project_id}")
    click.echo("═" * 55)
    click.echo("\nExample usage:")
    click.echo(f"  GET  https://{svc_url}/{project_id}/get/mykey  -H 'x-api-key: {api_key}'")
    click.echo(f"  POST https://{svc_url}/{project_id}/set/mykey  -H 'x-api-key: {api_key}'")
    click.echo(f"       Body: {{\"value\": \"hello world\", \"ttl\": 3600}}\n")

    # Append to local .projects file
    with open(".projects", "a") as f:
        f.write(f"{project_id}={api_key}={svc_url}\n")


@cli.command("list-projects")
def list_projects():
    """List all projects and their URLs."""
    try:
        lines = open(".projects").readlines()
    except FileNotFoundError:
        click.echo("No projects yet. Run `python deploy.py add-project`")
        return

    click.echo(f"\n{'PROJECT ID':<20} {'BASE URL':<45} {'API KEY'}")
    click.echo("─" * 100)
    for line in lines:
        parts = line.strip().split("=")
        if len(parts) == 3:
            pid, key, url = parts
            click.echo(f"{pid:<20} https://{url}/{pid:<35} {key}")
    click.echo()


# ── Polling helpers ───────────────────────────────────────────────────────────

def _poll_redis(redis_id: str) -> str:
    elapsed = 0
    while elapsed < POLL_TIMEOUT:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
        click.echo(".", nl=False)
        sys.stdout.flush()
        try:
            info = get(f"/redis/{redis_id}")
            if info.get("status") == "available":
                # Get connection string
                conn = get(f"/redis/{redis_id}/connection-string")
                return conn.get("redisUrl") or conn.get("connectionString") or info.get("connectionString", "")
        except Exception:
            continue
    click.echo("\n⚠️  Timed out waiting for Redis.")
    sys.exit(1)


def _poll_service(svc_id: str, url: str) -> str:
    elapsed = 0
    while elapsed < POLL_TIMEOUT:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
        click.echo(".", nl=False)
        sys.stdout.flush()
        try:
            info = get(f"/services/{svc_id}")
            svc  = info.get("service", info)
            status = svc.get("suspended") or svc.get("serviceDetails", {}).get("buildStatus", "")
            url  = svc.get("serviceDetails", {}).get("url", url)
            deploys = get(f"/services/{svc_id}/deploys", {"limit": 1})
            if deploys and deploys[0].get("deploy", {}).get("status") == "live":
                return url
        except Exception:
            continue
    click.echo(f"\n⚠️  Timed out. Check Render dashboard. Service ID: {svc_id}")
    sys.exit(1)


# ── State persistence ─────────────────────────────────────────────────────────

def _save_state(svc_id, svc_url, redis_id):
    with open(".render-state", "w") as f:
        f.write(f"{svc_id}\n{svc_url}\n{redis_id}\n")


def _load_state():
    try:
        lines = open(".render-state").readlines()
        return {"service_id": lines[0].strip(), "service_url": lines[1].strip(), "redis_id": lines[2].strip()}
    except Exception:
        return None


if __name__ == "__main__":
    cli()
