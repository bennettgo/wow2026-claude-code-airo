# Recipe Build Notes — `recipe_copilot_*` Sequence + Data-Table Create Path

> Spike output for Task 0.2. Tool names and schemas verified via ToolSearch against the live AIRO MCP server. No mutating tools were called.

---

## 1. Full `recipe_copilot_*` Tool Inventory

All tools confirmed present on `mcp__workato-airo-mcp-server`:

| Tool | Purpose |
|---|---|
| `recipe_copilot_init` | Create a new empty recipe in Workato and open a session. |
| `recipe_copilot_init_skill` | Create a new recipe pre-wired with a `workato_skill` trigger and open a session. Use instead of `init` when building a skill asset. |
| `recipe_copilot_pull` | Load an existing recipe into a session for editing. |
| `recipe_copilot_show` | Render the current session recipe as Python DSL. |
| `recipe_copilot_connectors` | Search/list all connectors, or filter to `recommended` (those with existing connections). |
| `recipe_copilot_list_connections` | List available connections for specific providers (returns name, ID, auth status). |
| `recipe_copilot_select_connections` | Map provider names to connection IDs for the recipe. |
| `recipe_copilot_actions` | List/search triggers and actions for one or more connectors. |
| `recipe_copilot_add_step` | Add a step at a given position (types: `trigger`, `action`, `if`/`elsif`/`else`, `foreach`, `repeat`, `error_handling`, `stop`, `while_condition`). |
| `recipe_copilot_update_step` | Update connector, action, comment, skip, or mask_data on an existing step. |
| `recipe_copilot_remove_step` | Remove a step (optionally collapsing or promoting children). |
| `recipe_copilot_move_step` | Move a single step to a new position/parent. |
| `recipe_copilot_move_steps` | Atomically move multiple steps. |
| `recipe_copilot_get_input_schema` | Get the input schema for a step (filterable by `required`, `sticky`, or `all`). |
| `recipe_copilot_set_input_field` | Set one or more input field values on a step (datapills as Python DSL expressions). |
| `recipe_copilot_remove_input_field` | Clear an input field on a step. |
| `recipe_copilot_get_datapills` | Get available datapills for a step from preceding steps. |
| `recipe_copilot_get_picklist` | Get picklist options for a select/multiselect field. |
| `recipe_copilot_set_condition` | Set conditions on `if`/`elsif`/`while_condition`/`repeat` blocks. |
| `recipe_copilot_set_foreach_source` | Set the source list datapill on a `foreach` step. |
| `recipe_copilot_set_error_handling_config` | Configure retry count/interval/conditions on an `error_handling` block. |
| `recipe_copilot_set_block_comments` | Set or clear comments on one or more steps. |
| `recipe_copilot_save` | Save (create) the recipe in Workato and persist the recipe ID + URL to the session. |
| `recipe_copilot_push` | Push the current session code to the already-saved Workato recipe (update). |
| `recipe_copilot_update_asset_metadata` | Rename, re-describe, or move a recipe/genie/mcp_server asset. |
| `recipe_copilot_convert_to_skill` | Convert an existing recipe to a skill; returns `skill_handle`. |

**Important distinction:** `recipe_copilot_init` creates the recipe in Workato immediately (no separate save needed). `recipe_copilot_save` is the call that persists an in-session recipe if the session was built without a prior `init` — in practice the builder flow uses `init` (which creates on init) and then `push` (which updates). The two paths are described separately in §2 and §3.

---

## 2. Recipe Build Sequence (trigger → steps)

This is the confirmed ordered call sequence for building a new recipe from scratch.

### Step 1 — Open a session and create the recipe placeholder

```
recipe_copilot_init(
  session_id = "<build-slug>",
  name       = "<recipe name>",
  folder_id  = "<folder_id>",          # string; the build folder
  description = "<optional>"
)
```

Returns: `recipe_id` (integer), `recipe_url`. The empty recipe is saved to Workato immediately.

### Step 2 — Discover available connections (optional but recommended)

```
recipe_copilot_connectors(scope="recommended")   # lists connectors that have existing connections
recipe_copilot_list_connections(
  session_id = "<build-slug>",
  providers  = ["<connector-name>", ...]
)
```

Returns connection names, IDs, and auth status. Use to validate a connection exists before wiring.

### Step 3 — Bind connections to the recipe

```
recipe_copilot_select_connections(
  session_id  = "<build-slug>",
  connections = { "<provider>": <connection_id>, ... }
)
```

Use `null` as the connection ID for embedded (no-auth) connectors.

### Step 4 — Configure the trigger (step 1 in recipe numbering)

```
recipe_copilot_add_step(
  session_id = "<build-slug>",
  type       = "trigger",
  connector  = "<connector>",
  action     = "<trigger-action>"
)
```

Then set trigger fields:

```
recipe_copilot_get_input_schema(session_id="<build-slug>", step=1, fields_filter="required")
recipe_copilot_set_input_field(
  session_id = "<build-slug>",
  step       = 1,
  fields     = [{"path": "<field>", "value": "<value>"}, ...]
)
```

For picklist fields, call `recipe_copilot_get_picklist` to resolve option IDs before setting.

### Step 5 — Add action steps

Repeat for each action step (step numbers increment from 2):

```
recipe_copilot_add_step(
  session_id = "<build-slug>",
  type       = "action",
  connector  = "<connector>",
  action     = "<action-name>",
  parent     = 1,               # trigger-level; adjust for nested blocks
  position   = <N>
)
recipe_copilot_get_input_schema(session_id="<build-slug>", step=<N>, fields_filter=["required","sticky"])
recipe_copilot_get_datapills(session_id="<build-slug>", for_step=<N>, keywords=["..."])
recipe_copilot_set_input_field(
  session_id = "<build-slug>",
  step       = <N>,
  fields     = [{"path": "<field>", "value": "<datapill or literal>"}, ...]
)
```

For conditional branches, add `if`/`elsif`/`else` steps and call `recipe_copilot_set_condition`. For loops, add `foreach` and call `recipe_copilot_set_foreach_source`.

### Step 6 — Inspect the recipe

```
recipe_copilot_show(session_id="<build-slug>")
```

Reviews the full Python DSL. Validation inconsistencies are included in the response.

### Step 7 — Push to Workato

```
recipe_copilot_push(session_id="<build-slug>")
```

Updates the already-created recipe in Workato with the current session state. This is the final persist step.

### Optional post-build: convert to skill

```
recipe_copilot_convert_to_skill(session_id="<build-slug>")
```

Returns `recipe_id`, `skill_handle`, `recipe_url`. Use this if the recipe needs to be attached to a genie as a skill.

---

## 3. Skill Recipe Build Sequence (variant)

When building a recipe that will be a genie skill, use `recipe_copilot_init_skill` instead of `recipe_copilot_init`. The trigger is pre-configured as `workato_skill`.

```
recipe_copilot_init_skill(
  session_id  = "<build-slug>",
  name        = "<skill name>",
  folder_id   = "<folder_id>",
  description = "<optional>"
)
```

Returns `recipe_id`, `skill_handle`, `recipe_url` immediately.

Do NOT call `recipe_copilot_add_step(type="trigger")` after this — the trigger already exists at step 1. Proceed directly to configuring trigger input fields (parameters/results schema for the skill) and then adding action steps from step 2 onward. The remainder of the sequence (steps 5–7 in §2) applies unchanged.

---

## 4. Data-Table Create Path

### 4.1 AIRO MCP is read-only for tables

The AIRO MCP server exposes three data-table tools, all read-only:

| Tool | Description |
|---|---|
| `data_table_list` | List all data tables in the workspace (schema column counts). |
| `data_table_get(data_table_id)` | Get full column schema for a specific table. |
| `data_table_query(data_table_id, ...)` | Query rows with filters, sort, pagination. |

There is no `data_table_create` on the AIRO MCP server.

### 4.2 Dev API create path

Data tables are created via the Workato Dev API:

**Tool:** `mcp__workato-dev-api__post_data_tables`

**Required parameters:**

| Parameter | Type | Notes |
|---|---|---|
| `name` | string | Display name of the table. |
| `folder_id` | integer | Folder to create the table in. |
| `schema` | array | Column definitions (see below). |

**Schema column object — required fields:**

| Field | Type | Notes |
|---|---|---|
| `name` | string | Column name. |
| `type` | string | Column type (e.g. `"string"`, `"integer"`, `"number"`, `"boolean"`, `"date"`, `"datetime"`). |
| `optional` | boolean | Whether the column is optional. |

**Schema column object — optional fields:**

| Field | Type | Notes |
|---|---|---|
| `default_value` | string | Default value. |
| `hint` | string | UI hint text. |
| `multivalue` | boolean | Allow multiple values. |
| `field_id` | string | Custom field identifier. |
| `metadata` | object | Arbitrary metadata. |
| `relation` | object | `{table_id, field_id}` for foreign key relations. |

**Example request body:**

```json
{
  "name": "build_log",
  "folder_id": 12345,
  "schema": [
    { "name": "build_slug",  "type": "string",   "optional": false },
    { "name": "status",      "type": "string",   "optional": false },
    { "name": "created_at",  "type": "datetime", "optional": true  },
    { "name": "result_json", "type": "string",   "optional": true  }
  ]
}
```

After creation, use `data_table_get` (AIRO MCP) to confirm the schema and record the returned `data_table_id` (format: `dt-<hash>`) into `build-state.json`.

---

## 5. Uncertainties — Verify During Build

- **`recipe_copilot_save` vs `recipe_copilot_push` after `init`:** `recipe_copilot_init` creates the recipe in Workato immediately, so the sequence is `init` → build in-session → `push`. `recipe_copilot_save` appears to be for cases where a recipe was built in a session *without* a prior `init` (i.e., constructed fully in memory first). Confirm the exact behaviour during Task 7.x — specifically whether calling `save` after `init` creates a duplicate or errors.

- **Connection wiring timing:** It is not confirmed whether `recipe_copilot_select_connections` must be called before or after `recipe_copilot_add_step(type="trigger")`. The schema suggests before, but verify during Task 7.x.

- **`data_table_query` environment availability:** The tool description notes "if the deployed WorkAI service does not expose the query route, the tool returns a structured environment-unavailable error." Verify that `data_table_query` works in the target workspace during Task 7.x.

- **Skill recipe trigger input schema:** After `recipe_copilot_init_skill`, the parameters and results schema for the skill trigger (step 1) must be configured via `recipe_copilot_set_input_field`. The exact field paths for setting parameter/result schema on a `workato_skill` trigger need to be confirmed by calling `recipe_copilot_get_input_schema(step=1)` in a live session. Verify during Task 4.x.

- **`post_data_tables` valid `type` values:** The Dev API schema specifies `type` as a free-form string. The full list of accepted column type tokens (e.g. `string`, `integer`, `number`, `boolean`, `date`, `datetime`) should be confirmed against the Workato docs or a live call during Task 7.x.

---

## Tool-shape gotchas (observed live)

- **`recipe_get` argument shape:** `recipe_get` needs the correct argument shape — check `docs_get(id="guides:workspace-query")` for the expected params before calling. If it errors, read the error hint and retry with the corrected shape, or fall back to `recipe_copilot_pull` to load the recipe into a session instead.
- **`get_recipes_` (Dev API) `includes` restriction:** The `includes` parameter on `get_recipes_` only accepts `["tags"]`. Passing `["connections"]` is rejected by the API — drop it from the request rather than retrying with the same value.
