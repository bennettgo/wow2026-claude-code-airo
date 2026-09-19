#!/usr/bin/env python3
"""init_kb_ingest.py — provision a Workato Knowledge Base + bulk-ingest API endpoint.

Generalized from a working reference build (the EnterpriseRAG-Bench suite,
see references/gotchas.md for the debugging history behind every choice
here). Creates, idempotently by name:

    project folder -> one or more Knowledge Bases -> "Bulk document ingest"
    recipe (workato_api_platform.receive_request -> enterprise_context.
    upsert_documents -> workato_api_platform.return_response) -> the API
    Collection/Endpoint/Client/Access Profile stack needed to call that
    recipe over plain HTTP with a static token.

There is no generic Workato REST endpoint to upload an arbitrary local file
into a Knowledge Base (verified live: POST /api/files 404s — it does not
exist). This recipe + upsert_documents is the actual mechanism; this script
just automates building it once so ingest_folder.py can drive it repeatedly.

Usage:
    DEV_API_TOKEN=wrkaus-... WORKATO_DC=us python3 init_kb_ingest.py \\
        --project-name "[AI] My Knowledge Base" \\
        --kb-names docs,transcripts

    # or a single KB (the common case):
    DEV_API_TOKEN=wrkaus-... python3 init_kb_ingest.py --project-name "My KB"

Env:
    DEV_API_TOKEN   required, wrkaus-... Dev API client token
    WORKATO_DC      us (default) | eu | jp | sg | au | in | il

Required Dev API client roles (Workspace admin -> API clients -> your
client -> roles):
    Folders / Projects   read + write
    Knowledge Bases      read + write   (listed as "Agentic" or similar in
                                          some workspaces — look for
                                          knowledge_bases/agentic scope)
    Recipes              read + write   (creates the ingest recipe)
    API Platform         read + write   (creates the API Collection/
                                          Endpoint/Client/Access Profile)

Without "Recipes" write specifically, POST /api/recipes returns a bare 401
Unauthorized with no further detail distinguishing it from any other auth
failure — verified live, not a payload-shape issue (confirmed with both
string and int folder_id). If every other call in this script succeeds but
recipe creation 401s, this is almost always the missing role.
"""
import argparse
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))
from workato_client import WorkatoClient  # noqa: E402

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")

INGEST_RECIPE_CONFIG = [
    {"keyword": "application", "name": "workato_api_platform",
     "provider": "workato_api_platform", "skip_validation": False, "account_id": None},
    {"keyword": "application", "name": "enterprise_context",
     "provider": "enterprise_context", "account_id": None},
]


def get_existing_project(client: WorkatoClient, folder_id: int) -> dict:
    """Use an already-existing project folder instead of creating a new one."""
    status, body = client.call("GET", f"/api/folders/{folder_id}")
    f = client.must(status, body, f"fetch folder {folder_id}")
    if not f.get("is_project"):
        raise RuntimeError(f"folder {folder_id} ({f.get('name')!r}) is not a project folder")
    return {"folder_id": f["id"], "project_id": f["project_id"], "name": f["name"]}


def create_project(client: WorkatoClient, name: str) -> dict:
    status, body = client.call("GET", f"/api/folders?query={urllib.parse.quote(name)}")
    # NOTE: verified live — GET /api/folders returns a bare JSON array, not
    # {"result": [...]}. The `query` param does not filter server-side
    # either; the exact-name match below does the real work.
    existing = [f for f in client.must(status, body, "list folders")
                if f.get("name") == name]
    if existing:
        f = existing[0]
        return {"folder_id": f["id"], "project_id": f["project_id"]}

    status, body = client.call("POST", "/api/folders", {"name": name})
    f = client.must(status, body, "create project folder")
    return {"folder_id": f["id"], "project_id": f["project_id"]}


def create_knowledge_bases(client: WorkatoClient, folder_id: int,
                             kb_names: list[str]) -> dict[str, str]:
    status, body = client.call("GET", f"/api/agentic/knowledge_bases?folder_id={folder_id}")
    # NOTE: verified live — this endpoint wraps its list under "data", not "result".
    existing = {kb["name"]: kb["id"] for kb in client.must(status, body, "list knowledge bases").get("data", [])}

    kb_ids: dict[str, str] = {}
    for kb_name in kb_names:
        if kb_name in existing:
            kb_ids[kb_name] = existing[kb_name]
            continue
        status, body = client.call("POST", "/api/agentic/knowledge_bases", {
            "name": kb_name, "folder_id": folder_id,
            "description": f"Populated via ingest_folder.py from a local folder.",
        })
        kb = client.must(status, body, f"create knowledge base {kb_name!r}")
        kb_ids[kb_name] = kb["data"]["id"]
    return kb_ids


def _find_by_name(items: list[dict], name: str) -> dict | None:
    return next((item for item in items if item.get("name") == name), None)


def create_recipe_from_template(client: WorkatoClient, folder_id: int, name: str,
                                  description: str, config: list[dict],
                                  template_path: str) -> str:
    """Create (or reuse) the ingest recipe from the verified `code` template.

    Idempotent by name within the folder. NOTE: verified live — GET
    /api/recipes wraps its list under "items", not "data"/"result" (yet
    another shape distinct from every other list endpoint this script uses —
    none of the list shapes across the whole Dev API agree with each other,
    so don't assume one endpoint's wrapper generalizes to the next).
    """
    status, body = client.call("GET", f"/api/recipes?folder_id={folder_id}&per_page=100")
    existing = _find_by_name(client.must(status, body, "list recipes").get("items", []), name)
    if existing:
        return str(existing["id"])

    with open(template_path) as f:
        code = f.read()

    status, body = client.call("POST", "/api/recipes", {"recipe": {
        "name": name, "description": description, "folder_id": str(folder_id),
        "code": code, "config": json.dumps(config),
    }})
    recipe = client.must(status, body, f"create recipe {name!r}")
    recipe_id = recipe.get("id") or recipe.get("data", {}).get("id")

    status, body = client.call("PUT", f"/api/recipes/{recipe_id}/start")
    client.must(status, body, f"start recipe {name!r}")
    return str(recipe_id)


def create_api_platform_endpoint(client: WorkatoClient, collection_name: str, endpoint_name: str,
                                    endpoint_path: str, recipe_id: str, api_client_name: str,
                                    access_profile_name: str) -> dict:
    """Idempotent: API Collection -> enabled API Endpoint -> API Client ->
    enabled Access Profile (token auth). Returns {"endpoint_url", "api_token"}.

    NOTE: verified live — /api/api_collections, /api/api_endpoints,
    /api/api_clients, and /api/api_access_profiles all return bare JSON
    arrays (no "data"/"result"/"items" wrapper), unlike every other list
    endpoint in this script.

    An access profile's token secret is returned only once — at creation, or
    via refresh_secret. Reusing an existing profile therefore refreshes it,
    which invalidates whatever token a previous run had. That's the right
    behavior for provisioning ("wire up this deployment with working
    credentials"), just worth knowing if something else depended on the old
    token surviving a re-run.
    """
    status, body = client.call("GET", "/api/api_collections?per_page=100")
    collection = _find_by_name(client.must(status, body, "list API collections"), collection_name)
    if not collection:
        status, body = client.call("POST", "/api/api_collections", {"name": collection_name})
        collection = client.must(status, body, f"create API collection {collection_name!r}")
    collection_id = collection["id"]

    status, body = client.call("GET", f"/api/api_endpoints?api_collection_id={collection_id}")
    endpoint = _find_by_name(client.must(status, body, "list API endpoints"), endpoint_name)
    if not endpoint:
        status, body = client.call("POST", f"/api/api_collections/{collection_id}/api_endpoints", {
            "name": endpoint_name, "method": "POST", "path": endpoint_path,
            "flow_id": str(recipe_id),
        })
        endpoint = client.must(status, body, f"create API endpoint {endpoint_name!r}")
        status, body = client.call("PUT", f"/api/api_endpoints/{endpoint['id']}/enable")
        client.must(status, body, f"enable API endpoint {endpoint_name!r}")
    endpoint_url = endpoint["url"]

    status, body = client.call("GET", "/api/api_clients?per_page=100")
    api_client = _find_by_name(client.must(status, body, "list API clients"), api_client_name)
    if not api_client:
        status, body = client.call("POST", "/api/api_clients", {"name": api_client_name})
        api_client = client.must(status, body, f"create API client {api_client_name!r}")

    status, body = client.call("GET", "/api/api_access_profiles?per_page=100")
    access_profile = _find_by_name(
        client.must(status, body, "list access profiles"), access_profile_name)
    if access_profile:
        status, body = client.call(
            "PUT", f"/api/api_access_profiles/{access_profile['id']}/refresh_secret")
        api_token = client.must(status, body, f"refresh secret for {access_profile_name!r}")["secret"]
    else:
        status, body = client.call("POST", "/api/api_access_profiles", {
            "name": access_profile_name, "api_client_id": str(api_client["id"]),
            "api_collection_ids": [collection_id], "auth_type": "token",
        })
        access_profile = client.must(status, body, f"create access profile {access_profile_name!r}")
        api_token = access_profile["secret"]
        status, body = client.call(
            "PUT", f"/api/api_access_profiles/{access_profile['id']}/enable")
        client.must(status, body, f"enable access profile {access_profile_name!r}")

    return {"endpoint_url": endpoint_url, "api_token": api_token}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-name",
                         help='Project/folder name to create/reuse by name, e.g. "[AI] My Knowledge Base". '
                              "Ignored if --folder-id is given.")
    parser.add_argument("--folder-id", type=int,
                         help="Use this already-existing project folder ID instead of creating/looking up "
                              "one by name.")
    parser.add_argument("--kb-names", required=True,
                         help="Comma-separated Knowledge Base names to create under the project "
                              '(one is fine, e.g. --kb-names docs; multiple: --kb-names docs,transcripts)')
    parser.add_argument("--manifest-out", default="kb_manifest.json")
    args = parser.parse_args()

    token = os.environ.get("DEV_API_TOKEN")
    if not token:
        sys.exit("error: DEV_API_TOKEN env var is required")
    dc = os.environ.get("WORKATO_DC", "us")
    kb_names = [n.strip() for n in args.kb_names.split(",") if n.strip()]

    if not args.folder_id and not args.project_name:
        sys.exit("error: provide either --project-name or --folder-id")

    client = WorkatoClient(token=token, dc=dc)

    if args.folder_id:
        print(f"[1/3] Using existing project folder_id={args.folder_id} on DC={dc}")
        project = get_existing_project(client, args.folder_id)
        label = args.project_name or project["name"]
    else:
        print(f"[1/3] Creating/reusing project {args.project_name!r} on DC={dc}")
        project = create_project(client, args.project_name)
        label = args.project_name
    folder_id = project["folder_id"]
    print(f"    folder_id={folder_id} project_id={project['project_id']}")

    print(f"[2/3] Creating/reusing {len(kb_names)} knowledge base(s)")
    kb_ids = create_knowledge_bases(client, folder_id, kb_names)
    for name, kb_id in kb_ids.items():
        print(f"    {name}: {kb_id}")

    print("[3/3] Provisioning the ingest recipe + API endpoint")
    ingest_recipe_id = create_recipe_from_template(
        client, folder_id, "Bulk document ingest API",
        "API endpoint that batch-upserts documents into a Knowledge Base. "
        "Used by ingest_folder.py.",
        INGEST_RECIPE_CONFIG, os.path.join(TEMPLATES_DIR, "ingest_recipe_code.json"))
    ingest_endpoint = create_api_platform_endpoint(
        client, f"{label} Ingest", "Upsert documents", "/documents",
        ingest_recipe_id, f"{label} Ingest Client",
        f"{label} Ingest Access Profile")
    print(f"    ingest_recipe_id={ingest_recipe_id}")
    print(f"    ingest_endpoint_url={ingest_endpoint['endpoint_url']}")

    manifest = {
        **project,
        "knowledge_bases": kb_ids,
        "ingest_recipe_id": ingest_recipe_id,
        "ingest_endpoint_url": ingest_endpoint["endpoint_url"],
        "ingest_api_token": ingest_endpoint["api_token"],
        "dc": dc,
    }
    with open(args.manifest_out, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nWrote {args.manifest_out} — hand this to ingest_folder.py")


if __name__ == "__main__":
    main()
