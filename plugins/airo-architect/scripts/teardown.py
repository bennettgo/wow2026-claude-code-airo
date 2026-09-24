#!/usr/bin/env python3
"""
teardown.py — tear down all assets recorded in a build-state.json.

Usage:
    DEV_API_TOKEN=wrkaus-... WORKATO_DC=us \\
    python3 teardown.py path/to/build-state.json

    Set DRY_RUN=1 to print each delete without making real calls.

build-state.json keys (all optional — missing/null/empty are skipped):
    genie_id        string
    skill_ids       list of strings
    kb_ids          list of strings
    recipe_ids      list of strings
    data_table_ids  list of strings
    user_group_id   string
    folder_id       string

Deletion order (reverse-dependency):
    genie → skills → KBs → recipes → data tables → user group → folder
"""

import json, os, sys, urllib.request, urllib.error
from pathlib import Path

# ---------------- env / config ----------------
TOKEN = os.environ.get("DEV_API_TOKEN")
if not TOKEN:
    sys.exit("error: DEV_API_TOKEN env var is required")

DC = os.environ.get("WORKATO_DC", "us").lower()
DEV_BASE = "https://app.workato.com" if DC == "us" else f"https://app.{DC}.workato.com"

DRY_RUN = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")

if len(sys.argv) < 2:
    sys.exit(f"usage: {sys.argv[0]} <build-state.json>")

STATE_PATH = Path(sys.argv[1])
if not STATE_PATH.exists():
    sys.exit(f"error: build-state.json not found: {STATE_PATH}")

STATE = json.loads(STATE_PATH.read_text())

# ---------------- HTTP ----------------
def call(method, path, body=None):
    url = f"{DEV_BASE}{path}"
    if DRY_RUN:
        print(f"[DRY_RUN] {method} {url}")
        return 200, "{}"
    headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def delete(path, label):
    s, b = call("DELETE", path)
    if s >= 400:
        print(f"  WARN: DELETE {path} returned [{s}] {b[:200]}")
    else:
        print(f"  deleted {label}")
    return s


# ---------------- teardown (reverse-dependency order) ----------------
print(f"▶ Teardown  (DC={DC}, dry_run={DRY_RUN})")
print(f"  State: {STATE_PATH}\n")

# 1. Genie (must be stopped before other assets become free)
genie_id = STATE.get("genie_id") or None
if genie_id:
    call("POST", f"/api/agentic/genies/{genie_id}/stop")
    delete(f"/api/agentic/genies/{genie_id}", f"genie {genie_id}")

# 2. Skills (agentic skill records, not the underlying recipes)
for sk_id in STATE.get("skill_ids") or []:
    delete(f"/api/agentic/skills/{sk_id}", f"skill {sk_id}")

# 3. Knowledge bases
for kb_id in STATE.get("kb_ids") or []:
    delete(f"/api/agentic/knowledge_bases/{kb_id}", f"knowledge_base {kb_id}")

# 4. Recipes
for rcp_id in STATE.get("recipe_ids") or []:
    call("PUT", f"/api/recipes/{rcp_id}/stop")
    delete(f"/api/recipes/{rcp_id}", f"recipe {rcp_id}")

# 5. Data tables
for dt_id in STATE.get("data_table_ids") or []:
    delete(f"/api/data_tables/{dt_id}", f"data_table {dt_id}")

# 6. User group
ug_id = STATE.get("user_group_id") or None
if ug_id:
    delete(f"/api/iam/user_groups/{ug_id}", f"user_group {ug_id}")

# 7. Folder (last — everything inside must be gone first)
folder_id = STATE.get("folder_id") or None
if folder_id:
    delete(f"/api/folders/{folder_id}", f"folder {folder_id}")

print("\n✓ Teardown complete.")
