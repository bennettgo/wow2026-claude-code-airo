# API reference — what this pattern actually calls

Everything below was exercised against a live Workato workspace while
building the EnterpriseRAG-Bench reference suite. Endpoints not listed here
weren't needed for this specific pattern (populating a Knowledge Base from
local files) — see the `workato-genie-builder` skill for the Genie side.

## Required Dev API client roles

Workspace admin -> API clients -> your client -> roles:

| Role | Access | Why |
|---|---|---|
| Folders / Projects | read + write | create the project |
| Knowledge Bases (Agentic) | read + write | create the Knowledge Base(s) |
| Recipes | read + write | create the ingest recipe |
| API Platform | read + write | create the API Collection/Endpoint/Client/Access Profile |

A token with every role except "Recipes" produces a bare 401 on
`POST /api/recipes` with no distinguishing detail — see gotchas.md #1's
sibling issue if every other call in `init_kb_ingest.py` succeeds but recipe
creation doesn't.

## Recipe shape (the actual, verified working recipe)

Trigger: `workato_api_platform.receive_request`
Request schema: `{knowledge_base_id: string, documents: [{document_id: string, title: string, content: string, content_type: string}]}` (up to 100 items in `documents`)
Response: `{total_count: integer, failed_documents: [{document_id, title}]}`

Action: `enterprise_context.upsert_documents`
Input: `{knowledge_base_id: <from request>, documents: [<mapped from request.documents, with content_type set explicitly — see gotchas.md #1>]}`
Output: `{failed_documents: [{document_id, title, reason}]}` — `reason` carries
the real per-document error text (e.g. the content-type message in
gotchas.md #1); the recipe's own response schema only surfaces
`{document_id, title}` from this by default, so if you're debugging a
failure, pull the raw job record (see below) to see `reason`.

Action: `workato_api_platform.return_response` — echoes `total_count` and
`failed_documents` back to the caller.

The exact, working `code` blob for this recipe is bundled at
`templates/ingest_recipe_code.json` — `init_kb_ingest.py` loads it verbatim
and POSTs it to `/api/recipes`. If you modify the recipe through the AIRO
MCP's `recipe_builder_*` tools, re-capture the template the same way this
skill's original build did:

```python
from workato_client import WorkatoClient
c = WorkatoClient(token=DEV_API_TOKEN, dc="us")
status, body = c.call("GET", f"/api/recipes/{recipe_id}")
open("templates/ingest_recipe_code.json", "w").write(body["code"])
```

Never hand-edit the JSON directly — Workato's internal datapill encoding
(`#{_dp('{"pill_type":...}')}`) is fragile to edit by hand; always go
through the recipe builder and re-extract.

## Debugging a specific failed document

`GET /recipes/{recipe_id}/jobs` (no status filter — job-level status is
`succeeded` even for documents that failed inside the action, see
gotchas.md #1) lists recent jobs; each item has an `id`. Pull one job's full
record with:

```
GET /recipes/{recipe_id}/jobs/{job_id}
```

The response's `lines[1].output.failed_documents[*].reason` (the
`upsert_documents` action's line) has the real per-document error text.
This is the only place that error text surfaces — the recipe's own
`return_response` output schema (and therefore what `ingest_folder.py`'s
HTTP response shows the caller) only carries `{document_id, title}`, not
`reason`, unless you extend the recipe's response schema to include it.

## Dev API list-endpoint response shapes used

See gotchas.md #3 for the full table — every endpoint below wraps its list
differently and none of them agree:

- `GET /api/folders` — bare array
- `GET /api/agentic/knowledge_bases?folder_id=...` — `{"data": [...]}`
- `GET /api/recipes?folder_id=...&per_page=100` — `{"items": [...]}`
- `GET /api/api_collections?per_page=100` — bare array
- `GET /api/api_endpoints?api_collection_id=...` — bare array
- `GET /api/api_clients?per_page=100` — bare array
- `GET /api/api_access_profiles?per_page=100` — bare array

## Data-center resolution

Workato runs isolated workspaces per data center; the web URL's subdomain
tells you which one (`app.workato.com` = US, `app.eu.workato.com` = EU,
etc.). `workato_client.py`'s `resolve_dc()` maps `WORKATO_DC` (`us` default,
or `eu`/`jp`/`sg`/`au`/`in`/`il`) to the right Dev API base URL. A token is
scoped to its DC — a US token cannot call an EU workspace.
