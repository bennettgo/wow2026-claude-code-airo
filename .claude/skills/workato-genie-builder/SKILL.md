---
name: workato-genie-builder
description: Use when the user wants to create, configure, deploy, or troubleshoot a Workato Genie (agentic AI assistant). Walks them through Agent Studio UI, Dev API provisioning, and the Headless runtime API. Handles skill attachment, client minting (API-key or OAuth-PKCE), user-group allow-listing, and runtime chat integration. Invoke for prompts like "build a Workato Genie", "create an AI agent in Workato", "set up an HR/support/ops assistant", "wire up the Workato Headless chat API", or any 401/406/409 on agentic endpoints.
---

# Workato Genie Builder

You are helping the user build a Workato Genie — Workato's framework for an agentic AI assistant. This skill takes them from zero to a running, callable Genie. Stay practical and concrete; produce commands, not theory.

---

## 0. What the user needs to start (ASK FIRST)

**Two pieces of info:**

1. **A Dev API token** (a `wrkaus-…` string) from their Workato workspace.
2. **Which Workato data center their workspace is on** — `app.workato.com` is US only. Workato runs separate, isolated workspaces in EU, Japan, Singapore, Australia, India, Israel, etc., and the API base URL changes accordingly. Look at the URL they see when signed in to Workato: whatever's between `app.` and `.workato.com` is the DC prefix. Examples:

   | DC | Web URL | Dev API base | Headless API base |
   |---|---|---|---|
   | US | `app.workato.com` | `https://app.workato.com` | `https://genie-api.workato.com` |
   | EU | `app.eu.workato.com` | `https://app.eu.workato.com` | `https://genie-api.eu.workato.com` |
   | Japan | `app.jp.workato.com` | `https://app.jp.workato.com` | `https://genie-api.jp.workato.com` |
   | Singapore | `app.sg.workato.com` | `https://app.sg.workato.com` | `https://genie-api.sg.workato.com` |
   | Australia | `app.au.workato.com` | `https://app.au.workato.com` | `https://genie-api.au.workato.com` |
   | India | `app.in.workato.com` | `https://app.in.workato.com` | `https://genie-api.in.workato.com` |
   | Israel | `app.il.workato.com` | `https://app.il.workato.com` | `https://genie-api.il.workato.com` |

   Tokens are **scoped to their DC** — a US `wrkaus-…` token cannot call an EU workspace and vice versa. The provision script accepts a `WORKATO_DC` env var (e.g. `WORKATO_DC=eu`); defaults to US.

When the user invokes this skill, your **first action** is to confirm both pieces and walk them through getting a token if they don't have one:

### If they don't have a token yet

Tell them:
1. Sign in to their Workato workspace as an admin (URL depends on DC — see table above).
2. Go to **Workspace admin → API clients** (or **Settings → Developer API** in some workspace layouts).
3. Click **+ Create client**.
4. Give the client a name (e.g. "Genie Builder").
5. Assign these **client roles** (this is the part most often missed — the token will silently 401 on agentic endpoints without them):
   - `Genies` — read + write
   - `Genie Client` — read + write  ← THE MOST COMMONLY MISSED ONE
   - `Recipes` — read + write
   - `Folders` / `Projects` — read + write
   - `IAM Users` — read + write
   - `IAM User Groups` — read + write
6. Copy the `wrkaus-…` token shown once. Store it somewhere safe (a password manager, `1password`, `.env` file, etc.).

If their workspace UI doesn't surface API clients, they may be on an older Workato tier — they should contact their Workato CSM to enable the Developer API.

### Optional but useful inputs

Once they have the token, ask:

| Input | Default | Why |
|---|---|---|
| `DEV_API_TOKEN` | (required) | the `wrkaus-…` string |
| `WORKATO_DC` | `us` | which DC their workspace lives in: `us`, `eu`, `jp`, `sg`, `au`, `in`, `il` |
| Email to allow-list at runtime | their own email | the genie won't respond to a user who isn't in an allow-listed user group; default to the token owner's email |
| Auth flow for runtime | `api_key` | simpler for first-time exploration; switch to `oauth` later for user-facing widgets |
| OAuth redirect URL | (only when `AUTH_TYPE=oauth`) | the URL their app's OAuth popup redirects back to |

### Naming constraints (verify before running)

- **Genie name: max 35 characters.** Anything longer returns `422 Name is too long`. Test/scratch suffixes like `(Skill Test 2026-06-08-091300)` will overflow if combined with a descriptive name — keep the whole string ≤35.
- Folder names: same workspace can't have duplicate folder names under the same parent. If re-running, append a unique suffix to `folder_name`.
- User group names: must be unique within the workspace. The script handles "already exists" by reusing.

**That's it.** Folder gets auto-created. AI model defaults to the workspace's default. Genie ID, skill IDs, client ID are all created by the script and printed at the end. The user doesn't need to know any of these before starting.

### Verify the token works (before doing anything else)

Run this one curl to verify the token's scopes are correct **and** that you're hitting the right DC:

```bash
export DEV_API_TOKEN=wrkaus-...
export WORKATO_DC=us   # or eu, jp, sg, au, in, il
DC_HOST="app${WORKATO_DC:+.$WORKATO_DC}.workato.com"
[ "$WORKATO_DC" = "us" ] && DC_HOST="app.workato.com"

curl -sS -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer $DEV_API_TOKEN" \
  "https://$DC_HOST/api/agentic/genies?per_page=1"
# Expected: 200
# If 401: token wrong, missing scopes, OR wrong DC (token is scoped to its DC)
# If 404 / no response: wrong DC subdomain — re-check section 0 table
```

If they get `200`, they're ready. Proceed to section 3.

---

## 1. Mental model

There are three surfaces. They are complementary, not redundant.

| Surface | Base | Auth | Use for |
|---|---|---|---|
| Agent Studio (UI) | `https://app.workato.com/genies` | session cookie | exploration, demos, click-config |
| Dev API | `https://app.workato.com/api/agentic/*` + `/api/iam/*` + `/api/recipes` + `/api/folders` | `Bearer <wrkaus-…>` | automation, IaC, multi-env promotion |
| Headless API (runtime) | `https://genie-api.workato.com/api/v1/genies/{gin}/chat/*` | `Bearer <64-char hex>` + `X-IDP-User-Id` **OR** `Bearer <oauth_access_token>` | runtime chat — what end users hit |

**The two-token rule:** `wrkaus-…` is a *builder* token (Dev API only). The 64-char hex is a *runtime* token (Headless API only). They are not interchangeable. Sending one where the other belongs → `401`.

> **Fourth surface (optional):** if the **Workato AIRO MCP** is connected this session, it's a build-time alternative to the Dev API — genie/skill/KB authoring through your MCP session, no token. It does **not** cover runtime clients, allow-listing, or the Headless API. See § 3.5.

Artifact graph for any Genie:

```
Folder → Genie ─┬─ Skills (auto-created from recipes with workato_genie trigger)
                ├─ Knowledge bases
                └─ User groups (allow-list)

Genie ←──── attached 1:1 ──── Client (mints the runtime token / oauth_client_id)
```

Phase 1 constraint: **1 Genie ↔ 1 Client.** No fan-out.

---

## 2. Decision tree — what to do first

Once the user has confirmed `DEV_API_TOKEN` works (section 0), gather just enough to fill in this template — most fields can default:

```
GENIE_NAME:                  default to "My Genie" if they don't specify
GENIE_PURPOSE (one sentence): one-liner of what it does
AUDIENCE:                    internal-only (default) | external-via-sso
PREFERRED PATH:              api (default; reproducible) | ui (exploration) | mcp (if AIRO MCP is connected — fastest build-time path, § 3.5)
AUTH FLOW (runtime):         api_key (default) | oauth_pkce (only for user-facing widgets)
EMAIL TO ALLOW-LIST:         default to the token owner's email (resolve via GET /api/users/me)
```

**Recommended default for a first-time user:** use `examples/hr-concierge.json` as-is and just provide `DEV_API_TOKEN` + their email. They'll have a working genie in under a minute. Then customize from there.

---

## 3. Provisioning a Genie via Dev API (recommended path)

`scripts/provision-genie.py` does the full end-to-end — folder → genie → skills → user group → client → attach. It reads a JSON spec.

```bash
export DEV_API_TOKEN=wrkaus-...           # builder token (Genies + Genie Client + Recipes + IAM scopes)
export USER_EMAIL_TO_ALLOWLIST=alice@example.com
export AUTH_TYPE=api_key                   # or "oauth"
export OAUTH_REDIRECT_URL=https://...      # only when AUTH_TYPE=oauth

python3 scripts/provision-genie.py examples/hr-concierge.json
```

The script prints:
- the `gin-…-CD` genie ID
- the `skl-…-CD` skill IDs
- the runtime credentials (`api_key` for API-key mode; `oauth_client_id` for OAuth mode)
- a ready-to-run smoke-test command

To build a different Genie (support, ops, finance), copy `examples/hr-concierge.json` and edit:
- `genie.name`, `genie.description`, `genie.instructions` (or `genie.instructions_file`)
- `skills[]` array — each entry has name, description, parameters schema, results schema, stub response, and `requires_confirmation`
- `user_group.name`

**Note on `instructions_file`:** the path is resolved **relative to the spec file**, not the current working directory. If you `cp` the spec elsewhere (e.g. to `/tmp/my-spec.json`), either copy the instructions file alongside it OR change `instructions_file` to an absolute path. Otherwise the provisioner will fail at step 2 with "instructions_file not found".

`examples/hr-concierge-instructions.md` shows the recommended instructions structure: **What's my job? / Who needs my help? / How do I get things done? / Available skills / Policy library / What to avoid / Tone / Tips.**

---

## 3.5 Provisioning via the AIRO MCP (if available)

If the current session has the **Workato AIRO MCP server** connected (tools prefixed `mcp__workato-airo-mcp-server__…`), you can build the genie's **authoring surface conversationally — no `wrkaus-…` token, no curl, no provision script.** The MCP authenticates through your signed-in MCP session, so it's often the fastest path when the user is already connected.

**What the MCP covers (build-time):**

| Task | MCP tool(s) |
|---|---|
| Genie CRUD | `genie_create`, `genie_get`, `genie_list`, `genie_update` (incremental `skills_to_add` / `skills_to_remove`, model, instructions) |
| Build a skill | `recipe_copilot_init_skill` (creates recipe + converts to skill in one shot), `recipe_copilot_convert_to_skill`, plus the full `recipe_copilot_*` suite (`add_step`, `set_input_field`, `set_condition`, `save`/`push`, …) to author the recipe step by step |
| Knowledge bases | `knowledge_base_create`, `knowledge_base_assign_to_genie`, `knowledge_base_list_for_genie`, `knowledge_base_remove_from_genie`, `knowledge_base_list_recipes` — useful because the Dev-API path here does **not** exercise KB authoring |
| Discovery | `folder_list`, `project_list`, `genie_list` |
| Publish as MCP tools | `mcp_server_create` |

Genie/skill/recipe-builder tools take a `session_id` (the Genie Builder workflow session). Pass skill **handles** (`skl-…`), not blueprint placeholder IDs. When the workflow isn't obvious, start with `docs_get(id="guides:overview")`.

**What the MCP does NOT cover — still use the Dev API + scripts (sections 3, 5, 6.5):**
- Minting runtime **clients** (api_key / OAuth-PKCE) and attaching them 1:1
- **User-group allow-listing** (runtime calls 403/401 without it)
- The **Headless runtime chat API** (SSE, conversations, skill approval)
- `start` / `stop` and teardown

So the clean hybrid is: **build the genie + skills + KBs via the MCP, then switch to the Dev API** (or the UI's Connect Interface) to mint a client, allow-list users, and run the Headless smoke test.

> ⚠️ **Identity caveat.** The MCP session and a `wrkaus-…` Dev API token may authenticate as **different identities** — a genie created via the MCP can be invisible to a Dev API token, and vice versa. Pick ONE identity for a given genie's full lifecycle, or verify both resolve to the same user (`GET /api/users/me`). See `references/gotchas.md` → "Sub-agent provisioning a genie that 'doesn't exist'."

---

## 4. Building the Genie via Agent Studio (UI)

Use when the user wants to click through it. The steps are:
1. `app.workato.com/genies` → **+ New genie** → **Build manually**.
2. Pick a folder (under a workspace project).
3. Paste the instructions (use the structure from `examples/hr-concierge-instructions.md`).
4. Pick an AI model (workspace default usually fine).
5. **Skills** panel → + Add. (Build the recipe first in **Recipes** if it doesn't exist — a recipe with a `workato_genie.start_workflow` trigger auto-creates a skill.)
6. **Knowledge bases** panel → + Add (optional).
7. **People who can chat** panel → + Add user group.
8. **Connect interface** → Web Widget / Slack / Teams / Go → choose API-key or OAuth.
9. Toggle the genie to **Active** (top-right).

The UI and Dev API edit the same underlying records — you can build in the UI and then read state via Dev API (`GET /api/agentic/genies/{id}`) for verification.

---

## 5. Runtime chat via the Headless API

Once the Genie is provisioned and a client is attached, the Genie is callable. **Wait ~30–60 seconds after provisioning before the first call** — user-group / skill / client wiring takes a moment to propagate at the runtime gateway. A `403 access_denied` on the first attempt is normal; retry with 10s backoff up to a minute. Once it succeeds, it stays available.

Use `scripts/test-headless-chat.sh` for a smoke test:

```bash
export GENIE_ID=gin-AaNpL4XP-baNnFY-CD
export GENIE_API_TOKEN=...        # api_key from step 3 (api_key mode) — or oauth_access_token
export IDP_USER_ID=...            # only when api_key mode
./scripts/test-headless-chat.sh "How much PTO do I have left?"
```

The full event lifecycle on a turn:
```
processing.started → skill.running → skill.completed → agent.message → processing.finished
```

For mutating skills (e.g. "Submit Time Off Request"):
```
processing.started → skill.confirmation_required → [user approves via POST /skill_approval/{call_id}]
  → skill.running → skill.completed → agent.message → processing.finished
```

Persisted vs ephemeral events: `agent.message`, `skill.failed`, `skill.confirmation_required`, `runtime_connection.auth_*`, `business_approval.*` are persisted for 24h and retrievable via `GET /chat/conversations/events?since_created_at=ISO8601`. Everything else (`processing.*`, `skill.running`, `skill.completed`) is ephemeral — you only see it live.

---

## 6. Integrating into a real product

Three deployment shapes:

1. **Inside Workato's own channels** — Slack / Teams / Workato Go. Connect Interface in the UI. No code needed.
2. **OAuth-PKCE web widget** — for a customer's own web app where end users SSO via Workato Identity. Reference implementation: the parent repo's `src/` directory — `server.js` (proxy + token exchange) and `public/embed.js` (PKCE flow + SSE handling). See `references/api-reference.md` for the call sequence.
3. **Server-mediated chat** — the customer's backend mints the headless token, holds it, and forwards user messages. Use API-key mode. Identity is conveyed via `X-IDP-User-Id`. Useful for systems where users don't have Workato SSO accounts.

### Quick-start UI

For a runnable starting point, point the user at `examples/simple-ui/` — a ~350-line chat widget (Python proxy + single HTML page) that:
- Streams SSE responses to message bubbles
- Renders skill-running chips
- Handles `skill.confirmation_required` with approve/reject cards
- Uses only Python stdlib for the proxy — no install needed

```bash
GENIE_ID=gin-...-CD GENIE_API_TOKEN=... IDP_USER_ID=... WORKATO_DC=us \
  python3 examples/simple-ui/server.py
# opens http://localhost:8088/
```

Read `examples/simple-ui/README.md` for the differences between this demo and a production deployment.

### Behaviors the UI needs to handle

See `references/handlers.md` for the verified-against-prod details on:
- **Unverified user access** — returns `401 user_nonactive_or_missing` (not 403 as some docs say)
- **Skill confirmation flow** — full event sequence, `skill.confirmation_required` payload shape, approve/reject calls, what happens on rejection
- **Conversation state** — `idle` vs `skill_processing`, why there's no distinct `awaiting_approval` state
- **Recovery from stream drops** — using `GET /chat/conversations/events?since_created_at=…`
- **`system.ping` heartbeats** — ignore them
- **ID format gotchas** — SSE uses `recipe:<numeric>` for `skill_id`, Dev API uses `skl-…-CD`
- **Rendering events in the UI** — patterns for the skill-card lifecycle (running → completed/failed/awaiting), approval card with parameters, color palette mapping to intent, dedupe + markdown handling. § 8 of `handlers.md`

---

## 6.5 Tearing it down

When the user is done testing and wants to remove what was provisioned:

```bash
# Quick teardown (stop + detach + delete client) — leaves recipes/group/folder.
DEV_API_TOKEN=$DEV_API_TOKEN WORKATO_DC=$WORKATO_DC python3 scripts/teardown-genie.py <GENIE_ID>

# Full teardown (also deletes recipes, group, project — the genie record dies with the project).
DEV_API_TOKEN=$DEV_API_TOKEN WORKATO_DC=$WORKATO_DC python3 scripts/teardown-genie.py <GENIE_ID> --full
```

Manual steps if the script is unavailable:
1. Stop the genie:    `POST /api/agentic/genies/{gin}/stop`
2. Detach the client: `DELETE /api/agentic/genies/{gin}/clients/{gincl}`
3. Delete the client: `DELETE /api/agentic/genies/clients/{gincl}` (optional; clients are otherwise reusable)
4. Delete recipes:    `DELETE /api/recipes/{recipe_id}` for each skill recipe
5. Delete group:      `DELETE /api/iam/user_groups/{group_id}`
6. Delete folder:     `DELETE /api/projects/{project_id}` (root-level folders are projects)

Note: a stopped + detached genie remains in the workspace as inactive. To remove the genie record itself, delete its enclosing project.

---

## 7. Troubleshooting

When the user reports an error, check `references/gotchas.md`. Quick lookup:

| Symptom | Most likely cause |
|---|---|
| `401` on `/api/agentic/genies/clients` | Dev token missing `Genie Client` role |
| `401` on every Dev API endpoint | Wrong DC — token is scoped to its data center |
| `406` on every runtime call | No client attached to genie (`chat_interface: null`) |
| `409` on `POST /messages` | Conversation not in `idle` — previous turn still streaming, or pending approval |
| `422 Name is too long` on genie create | Genie name >35 chars |
| `422 recipe already has a skill` | Skill auto-created on recipe POST; don't POST `/skills` separately |
| Skill recipe runs but agent says "I didn't get any data back" | The `workflow_return_result` action is missing `extended_input_schema`. Workato silently drops `input` fields without it. Use the `stub_recipe_code()` shape from `provision-genie.py` |
| Agent answer hedges ("I tried to look up X but didn't get the details I need") even though the recipe succeeded | Mismatch between declared `result_schema_json` and what `input.result` actually returns. The LLM expects the fields you declared but gets fewer/empty — so it falls back to apologetic phrasing. **Fix:** either populate every declared field, or shrink `result_schema_json` to match what you actually return. For pure action skills (post Slack, send email), set `result_schema_json: []` and return `{}` — the LLM treats it as a successful side-effect and just confirms |
| `skill.stopped` SSE event instead of `skill.completed` | Sometimes emitted in place of `skill.completed`; treat as terminal success. Inspect `result` field — empty result usually means recipe input was stripped (see row above) |
| Genie returns instantly, no `agent.message` | AI model not resolved — wrong `ai_provider` or workspace lacks credentials for it |
| Delegation errors `"Genie is not active."` | The target sub-genie is stopped — start every specialist before running the orchestrator (`POST …/genies/{gin}/start`). One stopped genie silently pauses the whole pipeline |
| VUA "Connect" works but the conversation never continues | After auth, `auth_success` and the resumed turn reach **neither the stream nor `/events`** — the resumed answer is **only** in `GET …/messages`. Poll `/messages` for a new genie message; don't wait on the dead stream (see `handlers.md` §4a) |
| KB lookup shows nothing in the UI (no chip/event) | Native Enterprise Search (attached-KB retrieval) emits **no event**. Route KB lookups through a **recipe skill** if you need them visible/auditable (see `handlers.md` §8.1a) |
| Long turn hangs on "working…" forever | Stream was cut (`system.stream_interrupted`) — react to that event and fall back to polling `/events` + `/messages` until `idle` (see `handlers.md` §6) |
| Polling endpoint returns nothing | Using `since_ms` (preview API) on prod — should be `since_created_at` (ISO 8601) |
| OAuth popup hangs after redirect | `OAUTH_REDIRECT_URI` registered on the client doesn't exactly match what's in the authorize URL |
| Two clients on one genie | Phase 1 is 1:1. Detach the old: `DELETE /api/agentic/genies/{gin}/clients/{gincl}` |
| Guardrails "read-only" / `PUT` ignored | You're writing to the genie object. Guardrails write **per-policy**: `PUT …/genies/{gin}/guardrails/policies/{policy_type}` (full-replace upsert), not a `guardrails` field on `PUT …/genies/{gin}`. See `references/guardrails.md` |
| `404` on every guardrails endpoint | `genie_guardrails_enabled` flag is off for the environment (a `200` from `GET …/guardrails/policies/pii_entities` confirms it's on) |
| Disable `prompt_attack` / `harmful_content` | Set **`strength: "NONE"`** (verified for `prompt_attack` — it's what the UI off-toggle writes), NOT `enabled` (→ `422`). `NONE` is a valid strength; no `DELETE` but `NONE` turns the policy off. See `references/guardrails.md` |

---

## 8. What NOT to do

- Don't call `genie-api.workato.com` with a `wrkaus-…` token (or vice versa).
- Don't embed `dev_api_token` in any client-side code — it's a builder secret. The browser only sees: (a) public OAuth `client_id`, (b) per-user `oauth_access_token`.
- Don't use API-key auth for user-facing widgets — every browser would share one key. Use OAuth-PKCE.
- Don't mint a new client every chat session — clients are durable. Mint once, reuse.
- Don't declare a rich `result_schema_json` for a skill that returns `{}` — the LLM will look for the fields, not find them, and hedge in its reply. Match the declared schema to what `input.result` actually carries. For pure action skills, set `result_schema_json: []`.
- Don't fabricate API endpoints. If you don't see it in `references/api-reference.md` or the user's testing, ask the user or check the live PRD before claiming it exists.
- Don't skip the user-group allow-list step. Without it, runtime calls return `403` even with a valid token.

---

## 9. Files in this skill

- `SKILL.md` — this file. Skill orchestration.
- `README.md` — how to install / share this skill.
- `references/api-reference.md` — complete endpoint reference, curl-ready.
- `references/gotchas.md` — every common error and its fix.
- `references/handlers.md` — verified behaviors for non-allow-listed access, skill confirmation/rejection, conversation state, SSE heartbeats, ID-format quirks.
- `references/guardrails.md` — guardrails Dev API: read/upsert policies per type, the `genie_guardrails_enabled` flag, and the verified disable rules (no `DELETE`; `prompt_attack`/`harmful_content` can't be turned off).
- `scripts/provision-genie.py` — working end-to-end provisioning code (reads a JSON spec).
- `scripts/test-headless-chat.sh` + `scripts/sse-parser.py` — runtime smoke test.
- `scripts/teardown-genie.py` — undo provisioning when the user is done testing.
- `examples/hr-concierge.json` — complete spec for the HR Concierge example (drop-in).
- `examples/hr-concierge-instructions.md` — the HR Concierge instructions (the genie's system prompt).
- `examples/sample-run.md` — what running the provision script looks like, end-to-end output.
- `examples/simple-ui/` — runnable chat-widget starter (Python proxy + HTML/JS), ~350 lines.

When a user invokes this skill, **read SKILL.md first**, then load `references/` and `examples/` as needed. Do not copy file contents into your response — point the user at the file path.
