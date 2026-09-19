#!/usr/bin/env python3
"""Rebuild the WoW 2026 demo stub MCP servers (sales-inventory-mcp, crm-promotions-mcp)
in a fresh Workato preview workspace, then point Claude Code's .mcp.json at them.

Rebuilt assets (deterministic stubs, seeded IDEA Lifestyle storyline):
  - 8 function recipes (one per MCP tool) created in the target folder
  - 2 MCP servers (project-asset type) with the recipes assigned as tools
  - 2 hashed token profiles, renewed to obtain plain tokens + gateway URLs
  - .mcp.json at the project root pointing Claude Code at both servers

Usage:
  WK_TOKEN=<api-token-for-new-workspace> \\
  WK_FOLDER=<target-folder-id> \\
  python3 scripts/migrate_mcp_stubs.py

Env:
  WK_TOKEN    (required) API token for the NEW workspace. Create via an MCP
              'Developer API client' in the new workspace's settings.
  WK_FOLDER   (default 578470) folder id in the new workspace for the assets.
  WK_BASE     (optional) force API base URL; otherwise auto-probed.
  DRY_RUN=1   probe auth + folder only, no writes.
"""
import json
import os
import sys
import urllib.request
import urllib.error
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODES_DIR = ROOT / "mcp-servers" / "recipe-codes"
MCP_JSON = ROOT / ".mcp.json"

TOKEN = os.environ.get("WK_TOKEN", "").strip()
FOLDER = os.environ.get("WK_FOLDER", "578470").strip()
DRY_RUN = os.environ.get("DRY_RUN") == "1"

BASE_CANDIDATES = [
    "https://app.preview.workato.com/api",
    "https://api.preview.workato.com",
]

SALES_TOOLS = [
    "get_sell_through", "get_store_sell_through", "get_inventory_positions",
    "get_purchase_orders", "get_backorder_cases", "get_product",
]
CRM_TOOLS = ["get_promotions", "get_price_history"]

SERVERS = {
    "sales-inventory-mcp": {
        "tools": SALES_TOOLS,
        "description": "Stub MCP server for the WoW 2026 demo - IDEA Lifestyle sell-through, "
                       "inventory positions, purchase orders, backorder cases, and product catalog. "
                       "Deterministic seeded data; not connected to live systems.",
    },
    "crm-promotions-mcp": {
        "tools": CRM_TOOLS,
        "description": "Stub MCP server for the WoW 2026 demo - IDEA Lifestyle promotion calendar "
                       "and price history. Deterministic seeded data; not connected to live systems.",
    },
}

EXPECTED_USER_ID = 325807  # "IDEA Lifestyle CS" - sanity check we hit the right workspace


def api(base, method, path, body=None):
    url = f"{base}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"_raw": raw[:500]}


def fail(msg):
    print(f"FATAL: {msg}", file=sys.stderr)
    sys.exit(1)


def find_base():
    for base in BASE_CANDIDATES:
        status, body = api(base, "GET", "/users/me")
        if status == 200 and isinstance(body, dict) and body.get("id"):
            return base, body
    fail("token rejected on all base candidates - is WK_TOKEN for the NEW workspace?")


def load_codes():
    codes = {}
    for f in sorted(CODES_DIR.glob("*.code.json")):
        tool = f.name.replace(".code.json", "")
        codes[tool] = json.loads(f.read_text())
    missing = set(SALES_TOOLS + CRM_TOOLS) - set(codes)
    if missing:
        fail(f"missing recipe code files for: {sorted(missing)}")
    return codes


def fresh_uuids(code):
    """Rewrite trigger + step uuids so recipes don't collide with any prior copy."""
    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "uuid" and isinstance(v, str):
                    node[k] = str(uuid.uuid4())
                else:
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(code)
    return code


def main():
    if not TOKEN:
        fail("WK_TOKEN not set")

    base, me = find_base()
    print(f"API base: {base}")
    print(f"Authenticated as: {me.get('name', me.get('full_name'))} (id={me.get('id')})")
    if me.get("id") != EXPECTED_USER_ID:
        print(f"WARN: expected user id {EXPECTED_USER_ID}, got {me.get('id')} - continuing anyway")

    status, folder = api(base, "GET", f"/folders/{FOLDER}")
    if status == 200:
        print(f"Target folder: {folder.get('name', '?')} (id={FOLDER})")
    else:
        fail(f"folder {FOLDER} not reachable ({status}: {folder})")

    if DRY_RUN:
        print("DRY_RUN: auth + folder OK, no writes performed")
        return

    codes = load_codes()

    # 1. Create recipes
    recipe_ids = {}
    for tool in SALES_TOOLS + CRM_TOOLS:
        code = fresh_uuids(codes[tool])
        desc = code["input"]["description"]
        status, body = api(base, "POST", "/recipes", {
            "recipe": {"name": tool, "description": desc, "code": json.dumps(code), "folder_id": FOLDER,
                       "config": "[]"}
        })
        if status not in (200, 201) or not body.get("id"):
            fail(f"create recipe {tool}: {status} {body}")
        recipe_ids[tool] = body["id"]
        print(f"recipe {tool}: id={body['id']}")

    # 2. Start recipes (function recipes must be running to serve the MCP gateway)
    for tool, rid in recipe_ids.items():
        status, body = api(base, "PUT", f"/recipes/{rid}/start")
        if status in (200, 201) and body.get("success", True):
            print(f"started {tool} (id={rid})")
        else:
            print(f"WARN: start {tool} (id={rid}): {status} {body}")

    # 3. Create MCP servers with tools assigned inline
    servers = {}
    for name, spec in SERVERS.items():
        tools = [{"trigger_application": "workato_recipe_function", "id": str(recipe_ids[t])}
                 for t in spec["tools"]]
        status, body = api(base, "POST", "/mcp/mcp_servers", {
            "name": name, "description": spec["description"],
            "folder_id": int(FOLDER), "tools": tools,
        })
        handle = body.get("handle") or body.get("id")
        if status not in (200, 201) or not handle:
            fail(f"create MCP server {name}: {status} {body}")
        servers[name] = body
        print(f"MCP server {name}: handle={handle}")

    # 4. Token profile + renew (renew returns the plain token and mcp_url)
    mcp_json_servers = {}
    for name, srv in servers.items():
        handle = srv.get("handle") or srv.get("id")
        status, body = api(base, "POST", f"/mcp/mcp_servers/{handle}/tokens",
                           {"name": "claudecode-demo-20260915"})
        if status not in (200, 201):
            fail(f"create token profile for {name}: {status} {body}")
        renewed = None
        for renew_path in (f"/mcp/mcp_servers/{handle}/token/renew",
                           f"/mcp/mcp_servers/{handle}/tokens/renew"):
            status, body = api(base, "POST", renew_path)
            if status in (200, 201) and (body.get("token") or body.get("plain_token")):
                renewed = body
                break
        if not renewed:
            fail(f"token renew for {name}: last={status} {body}")
        token = renewed.get("token") or renewed.get("plain_token")
        mcp_url = renewed.get("mcp_url") or renewed.get("server", {}).get("mcp_url")
        if not (token and mcp_url):
            fail(f"renew response for {name} missing token/mcp_url: {renewed}")
        mcp_json_servers[name] = {
            "type": "http",
            "url": mcp_url,
            "headers": {"Authorization": f"Bearer {token}"},
        }
        print(f"token for {name}: {token[:8]}...{token[-4:]} url={mcp_url}")

    # 5. Write .mcp.json
    MCP_JSON.write_text(json.dumps({"mcpServers": mcp_json_servers}, indent=2) + "\n")
    print(f"wrote {MCP_JSON}")

    # 6. Verify all 8 tools end-to-end and assert storyline invariants
    print("\n--- verification ---")
    failures = []

    def call(server, tool, args):
        cfg = mcp_json_servers[server]
        req = urllib.request.Request(cfg["url"], method="POST", data=json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool, "arguments": args},
        }).encode())
        req.add_header("Authorization", cfg["headers"]["Authorization"])
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
        # gateway may answer with SSE framing
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                raw = line[5:].strip()
                break
        env = json.loads(raw)
        if "error" in env:
            raise RuntimeError(f"{tool}: {env['error']}")
        text = env["result"]["content"][0]["text"]
        outer = json.loads(text)
        return outer, json.loads(outer["data"])

    def check(label, tool, server, args, predicate):
        try:
            outer, data = call(server, tool, args)
            ok = predicate(data)
            print(f"{'PASS' if ok else 'FAIL'} {label}")
            if not ok:
                failures.append(label)
        except Exception as e:
            print(f"FAIL {label}: {e}")
            failures.append(label)

    check("1 get_sell_through: Texas -39.7%, national flat", "get_sell_through", "sales-inventory-mcp",
          {"sku": "BRH-2240"},
          lambda d: d["regions"]["Texas"][0] - d["regions"]["Texas"][-1] > 20
          and abs(d["regions"]["US National"][0] - d["regions"]["US National"][-1]) < 8)
    check("2 get_store_sell_through: 12 driver stores", "get_store_sell_through", "sales-inventory-mcp",
          {"sku": "BRH-2240", "region": "Texas"},
          lambda d: len([s for s in d["stores"] if s.get("driver") or s.get("flag")]) == 12
          or len(d["stores"]) >= 12)
    check("3 get_inventory_positions: 8 stores below safety 3+ weeks", "get_inventory_positions",
          "sales-inventory-mcp", {"sku": "BRH-2240", "region": "Texas"},
          lambda d: len([p for p in d["positions"] if p.get("weeks_below_safety", 0) >= 3]) == 8)
    check("4 get_purchase_orders: Branchwood delayed", "get_purchase_orders", "sales-inventory-mcp",
          {"sku": "BRH-2240"},
          lambda d: any(p["vendor"] == "Branchwood" and p["status"] == "DELAYED"
                        for p in d["purchase_orders"]))
    check("5 get_backorder_cases: 8 cases, vendor delay", "get_backorder_cases", "sales-inventory-mcp",
          {"sku": "BRH-2240"},
          lambda d: len(d["cases"]) == 8
          and all("VENDOR" in c["reason_code"] for c in d["cases"]))
    check("6 get_product: substitute IDH-3310", "get_product", "sales-inventory-mcp",
          {"sku": "BRH-2240"},
          lambda d: any(s["sku"] == "IDH-3310" for s in d["substitutes"]))
    check("7 get_promotions: Texas clean", "get_promotions", "crm-promotions-mcp",
          {"sku": "BRH-2240", "region": "Texas"},
          lambda d: d["promotions"] == [])
    check("8 get_price_history: flat", "get_price_history", "crm-promotions-mcp",
          {"sku": "BRH-2240", "region": "Texas"},
          lambda d: d["regions"]["Texas"][0] == d["regions"]["Texas"][-1])

    if failures:
        fail(f"{len(failures)} verification checks failed")
    print("\nAll 8 tools verified. .mcp.json ready - restart Claude Code to pick up the servers.")


if __name__ == "__main__":
    main()
