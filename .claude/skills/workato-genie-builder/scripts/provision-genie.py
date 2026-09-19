#!/usr/bin/env python3
"""
provision-genie.py — end-to-end provisioning of a Workato Genie.

Usage:
    DEV_API_TOKEN=wrkaus-... \\
    WORKATO_DC=us \\
    USER_EMAIL_TO_ALLOWLIST=alice@example.com \\
    AUTH_TYPE=api_key \\
    python3 provision-genie.py path/to/genie-spec.json

Required env:
    DEV_API_TOKEN              builder token (wrkaus-...)

Optional env:
    WORKATO_DC                 us (default) | eu | jp | sg | au | in | il
    USER_EMAIL_TO_ALLOWLIST    email of a user to add to the allow-listed group;
                               defaults to the token owner's email (resolved via /users/me)
    AUTH_TYPE                  api_key (default) | oauth
    OAUTH_REDIRECT_URL         required when AUTH_TYPE=oauth
    PARENT_FOLDER_ID           override the parent folder; defaults to workspace root
    DRY_RUN                    print what would happen, don't make changes

Spec file shape (JSON):
{
  "genie": {
    "name": "InnovaTech HR Concierge",
    "description": "...",
    "instructions_file": "hr-concierge-instructions.md",  // path relative to spec file
    "ai_provider": "open_ai"   // optional, defaults to workspace default
  },
  "folder_name": "InnovaTech HR Concierge",   // creates if missing
  "user_group_name": "HR Concierge Users",    // creates if missing
  "skills": [
    {
      "name": "Get PTO Balance",
      "description": "Returns the signed-in employee's PTO balance.",
      "parameters": [],
      "results": [
        {"name":"status","type":"string","label":"Status","optional":false}
      ],
      "stub_response": { "status": "ok", "days_used": 9 },
      "requires_confirmation": false
    },
    ...
  ]
}
"""

import json, os, sys, time, uuid, urllib.request, urllib.error, urllib.parse
from pathlib import Path


# ---------------- env / config ----------------
TOKEN = os.environ.get("DEV_API_TOKEN")
if not TOKEN:
    sys.exit("error: DEV_API_TOKEN env var is required. See SKILL.md section 0.")

DC = os.environ.get("WORKATO_DC", "us").lower()
if DC == "us":
    DC_HOST = "app.workato.com"
    HEADLESS_HOST = "genie-api.workato.com"
elif DC == "preview":
    # Workato's internal pre-release stack, not a customer-facing DC.
    DC_HOST = "app.preview.workato.com"
    HEADLESS_HOST = "genie-api.preview.workato.com"
else:
    DC_HOST = f"app.{DC}.workato.com"
    HEADLESS_HOST = f"genie-api.{DC}.workato.com"
DEV_BASE = f"https://{DC_HOST}"
HEADLESS_BASE = f"https://{HEADLESS_HOST}"

AUTH_TYPE = os.environ.get("AUTH_TYPE", "api_key").lower()
if AUTH_TYPE not in ("api_key", "oauth"):
    sys.exit(f"error: AUTH_TYPE must be 'api_key' or 'oauth', got {AUTH_TYPE!r}")
OAUTH_REDIRECT_URL = os.environ.get("OAUTH_REDIRECT_URL", "")
if AUTH_TYPE == "oauth" and not OAUTH_REDIRECT_URL:
    sys.exit("error: AUTH_TYPE=oauth requires OAUTH_REDIRECT_URL")

DRY_RUN = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")

if len(sys.argv) < 2:
    sys.exit(f"usage: {sys.argv[0]} <spec.json>")
SPEC_PATH = Path(sys.argv[1])
if not SPEC_PATH.exists():
    sys.exit(f"error: spec file not found: {SPEC_PATH}")
SPEC = json.loads(SPEC_PATH.read_text())


# ---------------- HTTP ----------------
def call(method, path, body=None, base=DEV_BASE):
    url = f"{base}{path}"
    headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if DRY_RUN and method != "GET":
        print(f"    [DRY_RUN] {method} {url}")
        return 200, "{}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def must(status, body, what):
    if status >= 400:
        print(f"    FAILED {what}: [{status}] {body[:300]}")
        sys.exit(1)
    return body


def step(n, label):
    print(f"\n[{n}/9] {label}")


# ---------------- 0. sanity: verify token ----------------
print(f"▶ Workato Genie provisioner")
print(f"  DC:       {DC} ({DC_HOST})")
print(f"  Spec:     {SPEC_PATH}")
print(f"  Dry-run:  {DRY_RUN}")

step(0, "Verify token + DC")
s, b = call("GET", "/api/agentic/genies?per_page=1")
if s == 401:
    print(f"    [401] Token rejected. Check: (a) token belongs to DC '{DC}', (b) has all client roles.")
    sys.exit(1)
must(s, b, "verify token")
print(f"    ✓ Token works against {DC_HOST}")

# Look up "me" so we know who to allow-list
s, b = call("GET", "/api/users/me")
me = json.loads(must(s, b, "get /users/me"))
token_owner_email = me.get("email", "")
root_folder_id = me.get("root_folder_id")
print(f"    ✓ Token belongs to: {token_owner_email}")

allowlist_email = os.environ.get("USER_EMAIL_TO_ALLOWLIST", "").strip() or token_owner_email
print(f"    Allow-list target: {allowlist_email}")

parent_folder_id = int(os.environ.get("PARENT_FOLDER_ID", "0")) or root_folder_id
if not parent_folder_id:
    sys.exit("error: no parent folder ID (set PARENT_FOLDER_ID or ensure /users/me returns root_folder_id)")

# ---------------- 1. Create folder ----------------
step(1, f"Create folder {SPEC.get('folder_name', SPEC['genie']['name'])!r}")
folder_name = SPEC.get("folder_name") or SPEC["genie"]["name"]
s, b = call("POST", "/api/folders", {"name": folder_name, "parent_id": parent_folder_id})
folder = json.loads(must(s, b, "create folder"))
folder_id = folder["id"]
project_id = folder.get("project_id")
print(f"    ✓ folder_id={folder_id}  project_id={project_id}")

# ---------------- 2. Create genie ----------------
step(2, f"Create genie {SPEC['genie']['name']!r}")
instructions = SPEC["genie"].get("instructions", "")
if not instructions:
    inst_file = SPEC["genie"].get("instructions_file")
    if inst_file:
        inst_path = (SPEC_PATH.parent / inst_file).resolve()
        if not inst_path.exists():
            sys.exit(f"error: instructions_file not found: {inst_path}")
        instructions = inst_path.read_text()
genie_body = {
    "name":        SPEC["genie"]["name"],
    "description": SPEC["genie"].get("description", ""),
    "folder_id":   folder_id,
    "instructions": instructions,
    "ai_provider": SPEC["genie"].get("ai_provider", "open_ai"),
    "matrix": {},
}
s, b = call("POST", "/api/agentic/genies", genie_body)
genie_id = json.loads(must(s, b, "create genie"))["data"]["id"]
print(f"    ✓ genie_id={genie_id}")

# ---------------- 3. Start genie ----------------
step(3, "Start genie")
s, b = call("POST", f"/api/agentic/genies/{genie_id}/start")
must(s, b, "start genie")
print(f"    ✓ state=active")

# ---------------- 4. Build stub skills (recipes with workato_genie trigger) ----------------
step(4, f"Build {len(SPEC['skills'])} stub skills")

def stub_recipe_code(name, description, params, results, stub, require_confirm):
    """Build a Workato recipe-code dict for a stub skill.

    The workflow_return_result action canonically takes ONE input field named
    `result` (an object). Two things have to line up or the runtime returns
    nothing:

    1. The action's `input` must be `{"result": <dict matching result_schema>}`.
       Flat keys at the top of `input` will get persisted but the runtime
       reads them as `input.result = null`.
    2. The action must declare `extended_input_schema` that names a single
       field `result` of type `object` with `properties` mirroring
       result_schema_json. Without `properties`, Workato strips the value
       on POST.

    Verified empirically against app.workato.com on 2026-06-08.
    """
    trig_as = f"start_workflow_{uuid.uuid4().hex[:8]}"
    ret_as = f"workflow_return_result_{uuid.uuid4().hex[:8]}"
    return {
        "number": 0, "provider": "workato_genie", "name": "start_workflow",
        "as": trig_as,
        "description": f'Start <span class="provider">{name}</span> in a genie',
        "keyword": "trigger",
        "input": {
            "requires_user_confirmation": "true" if require_confirm else "false",
            "parameters_schema_json": json.dumps(params),
            "result_schema_json": json.dumps(results),
            "description": description,
        },
        "block": [{
            "number": 1, "provider": "workato_genie", "name": "workflow_return_result",
            "as": ret_as, "keyword": "action",
            "input": {"result": stub},
            "extended_input_schema": [{
                "name": "result", "label": "Result",
                "type": "object", "control_type": "object",
                "properties": results,
            }],
            "uuid": str(uuid.uuid4()),
        }],
        "uuid": str(uuid.uuid4()), "unfinished": False,
    }

recipe_to_name = {}
for sk in SPEC["skills"]:
    code = stub_recipe_code(
        sk["name"], sk["description"],
        sk.get("parameters", []), sk.get("results", []),
        sk.get("stub_response", {}), sk.get("requires_confirmation", False),
    )
    config = [{"keyword":"application","name":"workato_genie","provider":"workato_genie",
               "skip_validation":False,"account_id":None}]
    body = {"recipe": {
        "name": sk["name"],
        "description": sk["description"],
        "folder_id": str(folder_id),
        "code": json.dumps(code),
        "config": json.dumps(config),
    }}
    s, b = call("POST", "/api/recipes", body)
    rec = json.loads(must(s, b, f"create recipe {sk['name']!r}"))
    rid = rec.get("id") or rec.get("data", {}).get("id")
    print(f"    ✓ recipe_id={rid}  {sk['name']}")
    # Start it
    s, b = call("PUT", f"/api/recipes/{rid}/start")
    must(s, b, f"start recipe {rid}")
    recipe_to_name[rid] = sk["name"]
    time.sleep(0.4)

# ---------------- 5. Look up skill IDs ----------------
step(5, "Look up auto-created skill IDs")
time.sleep(2)
s, b = call("GET", f"/api/agentic/skills?folder_id={folder_id}&per_page=100")
all_skills = json.loads(must(s, b, "list skills"))["data"]
skill_ids = []
for rid, name in recipe_to_name.items():
    match = next((sk for sk in all_skills if sk.get("provider_id") == rid), None)
    if match:
        print(f"    ✓ skill_id={match['id']}  {name}")
        skill_ids.append(match["id"])
    else:
        print(f"    ! skill not found for recipe {rid} ({name}) — retrying in 3s")
        time.sleep(3)
        s, b = call("GET", f"/api/agentic/skills?folder_id={folder_id}&per_page=100")
        all_skills = json.loads(b)["data"]
        match = next((sk for sk in all_skills if sk.get("provider_id") == rid), None)
        if match:
            print(f"    ✓ skill_id={match['id']}  {name}")
            skill_ids.append(match["id"])
        else:
            print(f"    ✗ giving up on {name} — re-run script to retry")

# ---------------- 6. User group + membership ----------------
step(6, f"User group {SPEC.get('user_group_name', 'Genie Users')!r}")
group_name = SPEC.get("user_group_name") or f"{SPEC['genie']['name']} Users"
s, b = call("POST", "/api/iam/user_groups", {"name": group_name})
if s == 422 and "already" in b.lower():
    # Group already exists — find it
    s2, b2 = call("GET", f"/api/iam/user_groups?query={urllib.parse.quote(group_name)}")
    groups = json.loads(b2).get("data", [])
    group = next((g for g in groups if g["name"] == group_name), None)
    if not group:
        sys.exit(f"could not find existing group {group_name!r}")
    group_id = group["id"]
    print(f"    ↻ group already exists: id={group_id}")
else:
    group = json.loads(must(s, b, "create user group"))["data"]
    group_id = group["id"]
    print(f"    ✓ group_id={group_id}")

# Resolve IDP user ID
s, b = call("GET", f"/api/iam/users?query={urllib.parse.quote(allowlist_email)}")
users = json.loads(must(s, b, "lookup user"))["data"]
user = next((u for u in users if (u.get("email","").lower() == allowlist_email.lower())), None)
if not user:
    sys.exit(f"error: user {allowlist_email!r} not found in workspace. Create them first or change USER_EMAIL_TO_ALLOWLIST.")
idp_user_id = user["id"]
print(f"    ✓ idp_user_id={idp_user_id}")

# Add to group (idempotent — ignore "already member")
s, b = call("POST", f"/api/iam/users/{idp_user_id}/add_to_group", {"user_group_id": group_id})
if s >= 400 and "already" not in b.lower():
    must(s, b, "add user to group")
print(f"    ✓ {allowlist_email} ∈ {group_name}")

# ---------------- 7. Attach skills + group to genie ----------------
step(7, "Attach skills + group to genie")
if skill_ids:
    s, b = call("POST", f"/api/agentic/genies/{genie_id}/assign_skills", {"skill_ids": skill_ids})
    must(s, b, "assign skills")
    print(f"    ✓ {len(skill_ids)} skills attached")
s, b = call("POST", f"/api/agentic/genies/{genie_id}/assign_user_groups", {"user_group_ids": [group_id]})
must(s, b, "assign user group")
print(f"    ✓ user group attached")

# ---------------- 8. Mint client ----------------
step(8, f"Mint {AUTH_TYPE} client + attach")
client_body = {"client_name": f"{SPEC['genie']['name']} Client"}
if AUTH_TYPE == "api_key":
    client_body["auth"] = {"type": "api_key"}
else:
    client_body["auth"] = {"type": "oauth", "oauth_redirect_url": OAUTH_REDIRECT_URL}
s, b = call("POST", "/api/agentic/genies/clients", client_body)
client = json.loads(must(s, b, "mint client"))["data"]
client_id = client["client_id"]
api_key = client.get("api_key")
oauth_client_id = client.get("oauth_client_id")
print(f"    ✓ client_id={client_id}")

s, b = call("POST", f"/api/agentic/genies/{genie_id}/clients", {"genie_client_id": client_id})
must(s, b, "attach client to genie")
print(f"    ✓ client attached to genie")

# ---------------- 9. Summary ----------------
step(9, "Done — runtime credentials")
print()
print("=" * 64)
print(f"  Genie ID:         {genie_id}")
print(f"  Client ID:        {client_id}")
if AUTH_TYPE == "api_key":
    print(f"  Runtime API key:  {api_key}")
    print(f"  IDP user ID:      {idp_user_id}")
else:
    print(f"  OAuth client_id:  {oauth_client_id}")
    print(f"  Redirect URL:     {OAUTH_REDIRECT_URL}")
print(f"  Headless base:    {HEADLESS_BASE}")
print("=" * 64)
print()
print("Smoke test (api_key flow):")
if AUTH_TYPE == "api_key":
    print(f'  export GENIE_ID={genie_id}')
    print(f'  export GENIE_API_TOKEN={api_key}')
    print(f'  export IDP_USER_ID={idp_user_id}')
    print(f'  export WORKATO_DC={DC}')
    script_dir = Path(__file__).parent
    print(f'  bash {script_dir}/test-headless-chat.sh "Hello, who are you?"')
else:
    print("  Open your OAuth-enabled widget against the genie. See parent repo src/ for a working reference.")
print()
