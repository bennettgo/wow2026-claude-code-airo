#!/usr/bin/env python3
"""
teardown-genie.py — undo what provision-genie.py created.

Usage:
    DEV_API_TOKEN=wrkaus-... WORKATO_DC=us \\
    python3 teardown-genie.py <GENIE_ID>           # quick: stop + detach + delete client
    python3 teardown-genie.py <GENIE_ID> --full    # also delete recipes, group, project

The quick teardown leaves the genie record + recipes + folder + group in place
so you can reattach a client and resume. --full removes everything that the
provision script created.
"""

import json, os, sys, urllib.request, urllib.error

TOKEN = os.environ.get("DEV_API_TOKEN")
if not TOKEN:
    sys.exit("error: DEV_API_TOKEN env var is required")
DC = os.environ.get("WORKATO_DC", "us").lower()
DEV_BASE = "https://app.workato.com" if DC == "us" else f"https://app.{DC}.workato.com"

if len(sys.argv) < 2 or not sys.argv[1].startswith("gin-"):
    sys.exit(f"usage: {sys.argv[0]} <GENIE_ID> [--full]")
GENIE_ID = sys.argv[1]
FULL = "--full" in sys.argv[2:]


def call(method, path, body=None):
    h = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    r = urllib.request.Request(f"{DEV_BASE}{path}", data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


print(f"▶ Teardown {GENIE_ID}  (DC={DC}, full={FULL})\n")

# 1. Fetch genie — get name (for client matching), folder_id, project_id, user_groups
s, b = call("GET", f"/api/agentic/genies/{GENIE_ID}")
if s == 404:
    sys.exit(f"error: genie {GENIE_ID} not found in DC {DC}")
if s >= 400:
    sys.exit(f"error: fetching genie failed: {s} {b[:200]}")
g = json.loads(b)["data"]
genie_name = g.get("name", "")
folder_id = g.get("folder_id")
project_id = g.get("project_id")
user_group_ids = [ug["id"] for ug in g.get("user_groups", []) if "id" in ug]

print(f"  name:        {genie_name}")
print(f"  state:       {g.get('state')}")
print(f"  folder_id:   {folder_id}")
print(f"  project_id:  {project_id}")
print(f"  skills_count: {g.get('skills_count')}  user_groups: {len(user_group_ids)}")
print()

# 2. Look up clients via separate list endpoint, match by name prefix ("<genie_name> Client")
print("[1] Finding clients attached to this genie...")
client_ids_to_clean = []
s, b = call("GET", "/api/agentic/genies/clients?per_page=100")
if s < 400:
    for c in json.loads(b).get("data", []):
        # Provision script names clients "<genie_name> Client"
        if c.get("client_name", "").startswith(genie_name) and c["client_name"].endswith(" Client"):
            client_ids_to_clean.append(c["client_id"])
            print(f"    matched: {c['client_id']}  ({c['client_name']})")
if not client_ids_to_clean:
    print("    (no matching clients — may already be detached/deleted, or named differently)")

# 3. Stop the genie
print("\n[2] Stopping genie...")
s, b = call("POST", f"/api/agentic/genies/{GENIE_ID}/stop")
print(f"    [{s}]")

# 4. Detach + delete each matched client
for cid in client_ids_to_clean:
    print(f"\n[3] Detaching client {cid}...")
    s, b = call("DELETE", f"/api/agentic/genies/{GENIE_ID}/clients/{cid}")
    print(f"    detach: [{s}]")
    s, b = call("DELETE", f"/api/agentic/genies/clients/{cid}")
    print(f"    delete: [{s}]")

if not FULL:
    print("\n✓ Quick teardown complete. Genie stopped + clients deleted.")
    print("  To also delete recipes, group, and folder/project:  re-run with --full")
    sys.exit(0)

# 5. Look up recipes (via skills lookup → skill.provider_id == recipe_id)
print("\n[4] Looking up recipe IDs via skills...")
recipe_ids = []
if folder_id:
    s, b = call("GET", f"/api/agentic/skills?folder_id={folder_id}&per_page=100")
    if s < 400:
        for sk in json.loads(b).get("data", []):
            rid = sk.get("provider_id")
            if rid:
                recipe_ids.append(rid)
        print(f"    found {len(recipe_ids)} recipes")

# 6. Stop + delete each recipe
for rid in recipe_ids:
    print(f"\n[5] Stopping recipe {rid}...")
    s, b = call("PUT", f"/api/recipes/{rid}/stop")
    print(f"    stop:   [{s}]")
    s, b = call("DELETE", f"/api/recipes/{rid}")
    print(f"    delete: [{s}]")

# 7. Delete user groups attached to this genie (best-effort — they may be shared)
for ugid in user_group_ids:
    print(f"\n[6] Deleting user group {ugid}...")
    s, b = call("DELETE", f"/api/iam/user_groups/{ugid}")
    print(f"    [{s}]" + (f" {b[:140]}" if s >= 400 else ""))

# 8. Delete the project (this removes folder, genie, and anything still inside)
if project_id:
    print(f"\n[7] Deleting project {project_id} (removes genie record + remaining folder contents)...")
    s, b = call("DELETE", f"/api/projects/{project_id}")
    print(f"    [{s}]" + (f" {b[:200]}" if s >= 400 else ""))
elif folder_id:
    print(f"\n[7] Deleting folder {folder_id}...")
    s, b = call("DELETE", f"/api/folders/{folder_id}")
    print(f"    [{s}]" + (f" {b[:200]}" if s >= 400 else ""))

print("\n✓ Full teardown complete.")
