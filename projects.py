"""
Project Registry
----------------
Add your projects here.
Format: { "project_id": "api_key" }

Generate a strong API key with:
    python -c "import secrets; print(secrets.token_urlsafe(32))"
"""

PROJECT_REGISTRY: dict[str, str] = {
    # "project_1": "your-secret-api-key-here",
    # "project_2": "another-secret-api-key-here",
}

# ── OR load from env (recommended for production) ──────────────────────────────
# Set env vars like:
#   PROJECT_project_1=api_key_for_project_1
#   PROJECT_project_2=api_key_for_project_2

import os

for key, val in os.environ.items():
    if key.startswith("PROJECT_"):
        project_id = key[len("PROJECT_"):].lower()
        PROJECT_REGISTRY[project_id] = val
