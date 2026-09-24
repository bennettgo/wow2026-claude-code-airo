# provision-genie.py — Interface Notes for Vendoring

> Spike output for Task 0.1. Source read: `/Users/bennettgoh/.claude/skills/workato-genie-builder/scripts/provision-genie.py` (and `teardown-genie.py`, `sse-parser.py`, `test-headless-chat.sh`).

---

## 1. Environment Variables

### Required

| Var | Description |
|---|---|
| `DEV_API_TOKEN` | Builder token (`wrkaus-...`). Script exits immediately if absent. |

### Optional

| Var | Default | Description |
|---|---|---|
| `WORKATO_DC` | `us` | Data-centre slug (`us`, `eu`, `jp`, `sg`, `au`, `in`, `il`). Drives both `DC_HOST` (`app.workato.com` / `app.<dc>.workato.com`) and `HEADLESS_HOST` (`genie-api.workato.com` / `genie-api.<dc>.workato.com`). |
| `USER_EMAIL_TO_ALLOWLIST` | token owner's email (resolved via `/api/users/me`) | The workspace user who will be added to the new user group. |
| `AUTH_TYPE` | `api_key` | `api_key` or `oauth`. Controls which client type is minted in step 8. |
| `OAUTH_REDIRECT_URL` | — | Required when `AUTH_TYPE=oauth`; script exits if absent in that mode. |
| `PARENT_FOLDER_ID` | root folder from `/api/users/me` → `root_folder_id` | Override the folder under which the new project folder is created. |
| `DRY_RUN` | off | Set to `1`, `true`, or `yes`. See §4 below. |

---

## 2. `spec.json` Shape

The script is invoked as `python3 provision-genie.py <path/to/spec.json>`. The JSON file must contain:

```json
{
  "genie": {
    "name": "string — required",
    "description": "string — optional",
    "instructions": "string — inline instructions text (takes precedence over instructions_file)",
    "instructions_file": "string — path relative to spec file; loaded if instructions is absent",
    "ai_provider": "string — optional, e.g. open_ai; defaults to workspace default"
  },
  "folder_name": "string — optional; defaults to genie.name",
  "user_group_name": "string — optional; defaults to '<genie.name> Users'",
  "skills": [
    {
      "name": "string — required",
      "description": "string — required",
      "parameters": [
        { "name": "string", "type": "string", "label": "string", "optional": true/false }
      ],
      "results": [
        { "name": "string", "type": "string", "label": "string", "optional": true/false }
      ],
      "stub_response": { "key": "value" },
      "requires_confirmation": false
    }
  ]
}
```

Key points:
- `parameters` and `results` arrays follow the Workato schema-pill format; both default to `[]` if absent.
- `stub_response` is an arbitrary JSON object embedded verbatim as the `workflow_return_result` action's `result` input.
- `requires_confirmation` controls the `requires_user_confirmation` trigger field.

---

## 3. Ordered Call Sequence

The script performs exactly 10 logical steps (step 0 is a sanity check):

| Step | Function / inline code | API call | Notes |
|---|---|---|---|
| 0 | inline token verify | `GET /api/agentic/genies?per_page=1` | Validates token+DC. Also calls `GET /api/users/me` to resolve `token_owner_email` and `root_folder_id`. |
| 1 | inline folder create | `POST /api/folders` `{"name": folder_name, "parent_id": parent_folder_id}` | Returns `folder_id` + `project_id`. |
| 2 | inline genie create | `POST /api/agentic/genies` `{name, description, folder_id, instructions, ai_provider, matrix:{}}` | Returns `genie_id` (e.g. `gin-...`). |
| 3 | inline genie start | `POST /api/agentic/genies/{genie_id}/start` | Activates the genie. |
| 4 | `stub_recipe_code()` + inline loop | For each skill: `POST /api/recipes` then `PUT /api/recipes/{rid}/start` | Creates a stub recipe per skill with `workato_genie` trigger+return-result action, then starts it. Includes a 0.4 s sleep between skills. |
| 5 | inline skill lookup | `GET /api/agentic/skills?folder_id={folder_id}&per_page=100` | Matches auto-created skill IDs to recipe IDs via `skill.provider_id == recipe_id`. Retries once after 3 s if a skill is missing. |
| 6 | inline user group + membership | `POST /api/iam/user_groups` (idempotent — falls back to `GET /api/iam/user_groups?query=...` if 422 already-exists), then `GET /api/iam/users?query=<email>` to resolve `idp_user_id`, then `POST /api/iam/users/{idp_user_id}/add_to_group {"user_group_id": group_id}` | Ignores "already member" errors. |
| 7 | inline attach | `POST /api/agentic/genies/{genie_id}/assign_skills {"skill_ids": [...]}` then `POST /api/agentic/genies/{genie_id}/assign_user_groups {"user_group_ids": [...]}` | Wires skills + group to the genie. |
| 8 | inline mint client | `POST /api/agentic/genies/clients {"client_name": "...", "auth": {"type": "api_key"}}` (or `oauth`), then `POST /api/agentic/genies/{genie_id}/clients {"genie_client_id": client_id}` | Returns `client_id`, `api_key` (api_key mode) or `oauth_client_id` (oauth mode). |
| 9 | inline summary | stdout only | Prints `genie_id`, `client_id`, API key / OAuth client ID, `headless_base`, and the smoke-test command. |

Total mutating calls per run: ~2 + 2×N (N = number of skills) + 5 fixed = roughly 9 + 2N POST/PUT calls.

### Helper functions

- `call(method, path, body, base)` — thin `urllib.request` wrapper; handles JSON encode/decode; returns `(status, body_str)`.
- `must(status, body, what)` — asserts `status < 400`, exits on failure.
- `step(n, label)` — progress printer.
- `stub_recipe_code(name, description, params, results, stub, require_confirm)` — builds the recipe `code` dict with a `workato_genie` trigger and a `workflow_return_result` action. The `result` key in the action's `input` must be a nested object; the `extended_input_schema` declares its `properties` explicitly (empirically required by the runtime as of 2026-06-08).

---

## 4. `DRY_RUN` Behaviour

When `DRY_RUN=1` (or `true`/`yes`):
- The `call()` function short-circuits on every non-GET method: it prints `[DRY_RUN] METHOD URL` and returns `(200, "{}")`.
- `GET` calls still execute (token verify, `/users/me`, skill lookup, etc.).
- The script will appear to succeed for all mutable steps but will not create any Workato resources.
- This makes `DRY_RUN` suitable for unit tests that mock GET responses: import or subprocess the script with `DRY_RUN=1` and assert on the printed output.

---

## 5. `teardown-genie.py` Summary

Accepts a `GENIE_ID` arg. Two modes:

- **Quick** (default): stop genie → detach + delete matched clients (matched by name prefix `"<genie_name> Client"`).
- **Full** (`--full`): additionally stops + deletes each skill recipe (found via `GET /api/agentic/skills?folder_id=...`), deletes user groups attached to the genie, then deletes the project (preferred) or folder.

Uses the same `DEV_API_TOKEN` / `WORKATO_DC` env vars.

---

## 6. `sse-parser.py` and `test-headless-chat.sh` Summary

These are smoke-test utilities, not provisioning. After provisioning:

1. `test-headless-chat.sh` creates a conversation (`POST /api/v1/genies/{GENIE_ID}/chat/conversations`) and sends a streaming message (`POST .../conversations/{CONV_ID}/messages` with `stream: true`, `Accept: text/event-stream`). Requires `GENIE_ID`, `GENIE_API_TOKEN`, `IDP_USER_ID`, `WORKATO_DC`.
2. `sse-parser.py` reads the SSE stream from stdin and pretty-prints `agent.message`, `skill.running`, `skill.completed`, `skill.stopped`, `skill.failed`, `skill.confirmation_required`, `processing.started`, and `processing.finished` events.

---

## 7. Gaps vs. airo-architect Needs

The existing `provision-genie.py` provisions: folder, genie, stub-skill recipes, user group + membership, and a headless API client. It does **not** handle:

### 7.1 Knowledge Bases (KBs)

No KB creation or assignment. We must add:

- **Create KB**: Dev API `POST /api/agentic/knowledge_bases` (tool: `mcp__workato-dev-api__post_agentic_knowledge_bases`) or AIRO MCP `knowledge_base_create`.
- **Assign KB to genie**: Dev API `POST /api/agentic/genies/{id}/assign_knowledge_bases` (tool: `mcp__workato-dev-api__post_agentic_genies_assign_knowledge_bases`) or AIRO MCP `knowledge_base_assign_to_genie`.
- Source documents must be linked to the KB before assignment; the exact upload flow needs verification during Task 4.x.

### 7.2 Data Tables

No data-table creation. We must add:

- **Create data table**: Dev API `POST /data_tables` (tool: `mcp__workato-dev-api__post_data_tables`). Required fields: `name` (string), `schema` (array of column objects), `folder_id` (integer). Each column requires `type` (string), `name` (string), `optional` (boolean); optional fields include `default_value`, `hint`, `multivalue`, `relation`, `field_id`, `metadata`.
- AIRO MCP exposes only `data_table_get`, `data_table_list`, and `data_table_query` — all read-only. Creation is Dev API only.

### 7.3 Connections

No connection creation or selection. Recipes built via `recipe_copilot_*` need connections wired via `recipe_copilot_select_connections`. Pre-existing connections can be discovered with `recipe_copilot_list_connections`. Creating net-new authenticated connections programmatically requires additional Dev API calls (`POST /api/connections`) and is likely manual for OAuth connectors; flag for Task 4.x.

### 7.4 Sandbox discipline

`provision-genie.py` always creates resources in the live workspace. The vendored version for airo-architect must be wrapped with a `SANDBOX=1` mode that names all assets with a `[sandbox]` or build-slug prefix and records IDs into `builds/<slug>/build-state.json` for teardown. This is an airo-architect addition, not present in the upstream script.
