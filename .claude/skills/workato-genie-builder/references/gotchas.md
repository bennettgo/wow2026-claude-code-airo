# Common errors and fixes

When a genie misbehaves, this is the lookup table. Each row: symptom → cause → fix.

---

## Auth & permissions

### `401 Unauthorized` on `/api/agentic/genies/clients`
**Cause:** Dev token's role is missing `Genie Client` scope. Other agentic endpoints may succeed; only the client-management endpoints fail.
**Fix:** Workspace admin → API clients → edit your client → assign the `Genie Client` role (read + write). Token doesn't need rotating.

### `401 Unauthorized` on every Dev API endpoint
**Cause (most common):** wrong DC. `wrkaus-…` tokens are scoped to their data center. A US token cannot call `app.eu.workato.com` and vice versa.
**Fix:** check `WORKATO_DC` matches the workspace's actual DC. See the host table in the skill README.
**Cause (alternate):** token revoked or expired. Tokens don't auto-expire but admins can revoke.
**Fix:** mint a new one.

### `401 Unauthorized` on a Headless API call
**Cause (most common):** sending a `wrkaus-…` token to `genie-api.workato.com`. That's the *builder* token, wrong realm.
**Fix:** use the 64-char hex `api_key` you got when minting an API-key client (or the OAuth `access_token` for OAuth flow).
**Cause (alternate):** missing `X-IDP-User-Id` header in API-key mode. The runtime requires the IDP user ID to look up group membership.
**Fix:** add the header.

### `401 user_nonactive_or_missing` on Headless API
**Cause:** the IDP user (from `X-IDP-User-Id` or the OAuth token's `sub`) is not in any user group that's allow-listed on this genie, OR the user doesn't exist in the workspace at all. The runtime returns the same error for both cases.
**Fix:** add the user to an allow-listed group via `POST /api/iam/users/<idp_user_id>/add_to_group`. If they don't exist yet, create them via `POST /api/iam/users` first.
**Note:** despite some Workato docs describing this as `403 access_denied`, prod returns `401 user_nonactive_or_missing`. See `references/handlers.md` § 1 for full details.

---

## Conversation & runtime

### `406 Not Acceptable` on every Headless call
**Cause:** the genie has no client attached. `chat_interface` is `null` on `GET /api/agentic/genies/{id}`.
**Fix:** mint a client (`POST /api/agentic/genies/clients`) and attach it (`POST /api/agentic/genies/{id}/clients`).

### `409 Conflict` on `POST /messages`
**Cause:** conversation isn't in `idle` state. Either the previous turn is still streaming, or a skill confirmation is pending.
**Fix:** wait for `processing.finished`, or resolve the pending skill approval (`POST /chat/conversations/{id}/skill_approval/{call_id}`). Check current state with `GET /chat/conversations/{id}`.

### Genie returns instantly with no `agent.message`
**Cause:** the configured AI model isn't resolved. Either `ai_provider` points to a connector the workspace doesn't have, or no OAuth-keyed connection is set up for it.
**Fix:** `GET /api/agentic/genies/{id}` and check `ai_provider` + `ai_model`. Set to `open_ai` (workspace default) for fastest unblock. Test in Agent Studio's Test UI to confirm the model itself works.

### Stream connects but no events arrive, then closes after ~30s
**Cause:** corporate proxy or VPN cutting idle connections. Could also be a load-balancer between you and Workato that doesn't preserve `text/event-stream`.
**Fix:** make sure your code sends `Accept: text/event-stream` and consumes the response body incrementally. If using `fetch()`, read from `response.body.getReader()` — do not `await response.text()` (that buffers the whole stream).

### Connection drops mid-turn
**Cause:** any network hiccup; SSE has no built-in reconnect.
**Fix:** poll the recovery endpoint:
```bash
GET /chat/conversations/events?conversation_id=<CID>&since_created_at=<ISO8601>&limit=50
```
Use the `created_at` of the last event you successfully processed as `since_created_at`. Stop when `processing.finished` arrives or conversation state returns to `idle`.
**Note:** field is `since_created_at` (ISO 8601) on prod. Preview API used `since_ms` (Unix epoch ms) — that was renamed.

---

## Skills & recipes

### `422 Name is too long (maximum is 35 characters)` on genie create
**Cause:** Workato enforces a 35-character limit on genie names (likely on folder names too). Suffixes like `(Skill Test 2026-06-08-091300)` will overflow when combined with a descriptive base name.
**Fix:** trim to ≤35 chars before POSTing. The provisioner does not pre-check; the user should pre-shorten.

### `422 "Recipe already has a skill"` when calling `POST /api/agentic/skills`
**Cause:** a recipe with a `workato_genie.start_workflow` trigger **auto-creates** the skill record on `POST /api/recipes`. You don't need a second call.
**Fix:** look up the auto-created skill ID via `GET /api/agentic/skills?folder_id=<FOLDER>` and grab the entry where `provider_id == <RECIPE_ID>`.

### `GET /api/agentic/skills?recipe_id=...` returns nothing useful
**Cause:** `?recipe_id=` and `?provider_id=` filters are silently ignored by the skills endpoint.
**Fix:** use `?folder_id=<FOLDER>` and post-filter in your code by `provider_id`.

### Stub skill recipe runs but returns no data ("I didn't get any data back")
**Cause:** the `workflow_return_result` action's `input` fields are silently stripped on `POST /api/recipes` unless the action declares `extended_input_schema` matching the trigger's `result_schema_json`. The recipe POST succeeds, the recipe runs at chat-time, but every result field is null.
**Fix:** include `extended_input_schema: [...]` on the action block, mirroring the result schema. Keys in the action `input` must be the flat field names — not nested under `result`. `provision-genie.py` in this skill handles this correctly via `stub_recipe_code()`. If you're hand-rolling recipes, mirror that shape.
**Verify:** after creating the recipe, `GET /api/recipes/{id}` and check `code.block[0].input` — if it's `{}`, the input was stripped; if it shows your field values, you're good.

### Recipe-skill won't start: `Unknown data field "<param>" used in <field>`
**Symptom:** `PUT /api/recipes/{id}/start` returns `{"success":false,"code_errors":[[...,[...,"Unknown data field \"My Param\" used in ","id"]]]}`. The recipe was built via the MCP `recipe_copilot_*` tools and the trigger declares `parameters_schema_json: [{"name":"my_param",...}]`. Downstream steps reference `start_workflow_1['my_param']`.
**Cause:** user-defined skill parameters live under a `parameters` sub-object on the `workato_skill.start_workflow` trigger output — they are **not** top-level keys. The trigger's `extended_output_schema` contains a single `parameters` object whose `properties` are the schema you declared. So the actual datapill path is `start_workflow_1['parameters']['my_param']`, not `start_workflow_1['my_param']`. The MCP also warns about this via `[datapill:DatapillInvalidPath]` inconsistencies after `add_step` / `set_input_field` — **do not dismiss these as cache noise**, they're real.
**Fix:** edit every downstream reference to nest under `['parameters']`:
```python
# WRONG (start fails with "Unknown data field")
jira.get_issue(id=f"{start_workflow_1['pmo_key']}", ...)
# RIGHT
jira.get_issue(id=f"{start_workflow_1['parameters']['pmo_key']}", ...)

# In ruby() bindings, same rule:
ruby("bindings.q.to_s", bindings={"q": start_workflow_1['parameters']['quarter']})
```
**Verify:** `PUT /api/recipes/{id}/start` should return `{"success":true}` (HTTP 200 with `success:false` was a code-validation failure, not a transport error). The MCP also stops emitting `DatapillInvalidPath` warnings once the path is correct.
**Note:** The `result_schema_json` (skill output) on the *same trigger* uses flat keys — `result['pmo_key']` is correct in the `workflow_return_result` action. Only the **input** parameters are nested under `parameters`.

### `skill.stopped` event arrives instead of `skill.completed`
**Cause:** the runtime sometimes emits `skill.stopped` as the terminal event. The `result` payload behaves the same as `skill.completed`.
**Fix:** treat `skill.stopped` as equivalent to `skill.completed` in your event handler. If `result` is empty, the root cause is the input-stripping issue above.

### `skill.completed` / `skill.stopped` SSE event has no `result` field
**Cause:** by design — the skill's return payload is fed to the LLM internally but is **not** echoed to the SSE client. The agent's response will reference it (e.g. "You have 12 days remaining"), but a UI widget cannot read the structured data from the SSE event itself.
**Fix:** if you need the structured payload for UI rendering, either (a) parse it from the `agent.message` text, or (b) replay the recipe job via `GET /api/recipes/{id}/jobs/{job_id}` to read the action's input/output directly.

### Skill is attached but genie never invokes it
**Cause (most common):** recipe isn't started. Skills depend on the underlying recipe being in `running` state.
**Fix:** `PUT /api/recipes/{recipe_id}/start`.
**Cause (alternate):** skill description is too vague. The genie picks skills by matching user intent to the skill's `description`. Make descriptions concrete.
**Fix:** rewrite the description to be action-specific ("Submits a paid time off request for the signed-in employee. Requires start_date, end_date, leave_type.").

### `skill.failed` arrives but no useful error
**Cause:** the recipe ran but its action raised an exception. Workato sanitizes runtime errors before returning them.
**Fix:** check the recipe's job log in Workato UI (Recipes → click recipe → Job history). The full stack trace is there.

### A scheduled (clock-triggered) recipe won't run on demand from the Dev API
**Symptom:** you need a one-shot run of a recipe whose trigger is `clock`/schedule (e.g. a "Sync Confluence → Knowledge Base" recipe). `PUT /api/recipes/{id}/start` returns `{"success":true}` and sets `running:true`, **but no job fires immediately** — the clock trigger waits for its next aligned interval (verified: a recipe set to "every 1 hour at 3:00am" started mid-cycle produced **zero jobs** over 70s). There is **no trigger-now Dev API** — `/run`, `/test`, `/poll` on `/api/recipes/{id}` all `404`.
**Fix:** the only instant one-shot is the **UI "Test recipe"** button (which *does* create a normal job, visible in `GET /api/recipes/{id}/jobs`). For unattended automation, either start the recipe and wait for the schedule, or temporarily set a 1-minute schedule. Flag this when E2E-testing scheduler-triggered flows — they can't be fired head­lessly.

### A knowledge base exists + is attached to the genie, but the genie isn't grounded
**Cause:** attaching a recipe-backed KB to a genie does **not** populate it — the **sync recipe must run at least once** to index content. A freshly created KB is empty.
**Verify (authoritative):** `GET /api/agentic/knowledge_bases/{kb-…}` → `data.storage_size` (**0 = empty/not synced**) and `data.active_recipes_count`. Don't trust attachment alone. List a genie's KBs via the MCP `knowledge_base_list_for_genie`, and the KB's feeder recipe via `knowledge_base_list_recipes`.
**Fix:** run the sync recipe once (UI **Test recipe** — see the clock-trigger gotcha above), then re-check `storage_size` is non-zero. Specialists/sub-agents only cite KB content after this.

---

## Multi-agent orchestration (`assign_task_to_genie`)

### Structured output datapills are nested under `['structured_output']`
**Symptom:** after configuring a delegation skill with `workato_genie.assign_task_to_genie` and a `structured_output` schema (e.g. fields `findings_markdown`, `verdict`, `confidence`), referencing those fields downstream as `assign_task_to_genie_2['findings_markdown']` fails with `[datapill:DatapillInvalidPath] Datapill path 'findings_markdown' doesn't exist in output schema of 'assign_task_to_genie_...'`.
**Cause:** the structured-output fields don't sit at the top level of the action's output. They live under a `structured_output` sub-object. The top-level action output is `{response, conversation_id, artifacts, structured_output}`; your declared fields are properties of `structured_output`.
**Fix:** prefix every reference with `['structured_output']`:
```python
# WRONG
assign_task_to_genie_2['findings_markdown']
# RIGHT
assign_task_to_genie_2['structured_output']['findings_markdown']
```
**Verify:** run `recipe_copilot_get_datapills(for_step=<next>)` after configuring the action — the valid paths are listed explicitly. The free-form text response sits at `assign_task_to_genie_2['response']` (no structured schema needed); use this when you don't define `structured_output`.

### `genie_handle` field is a toggle — pick the right mode
**Symptom:** validation error `Missed required field at path genie_handle` even though you set it, OR the genie_id is treated as a picklist option ID and rejected.
**Cause:** `genie_handle` on `workato_genie.assign_task_to_genie` is a toggle field with two modes — `primary` (picklist of genies via the `genies_for_task_picklist`) and `secondary` (free-text genie ID like `gin-…-CD`). Setting a raw `gin-` ID without specifying the secondary toggle puts the parser into picklist mode where it fails to resolve.
**Fix:** pass `toggle_config: {"genie_handle": false}` to switch to the text/secondary mode when you have the genie ID as a literal:
```python
recipe_copilot_set_input_field(step=2, fields=[{
    "path": "genie_handle",
    "value": "gin-AaR364th-8r48kY-CD",
    "toggle_config": {"genie_handle": false}
}])
```

### "Cannot find genie" / silently empty response from delegation
**Cause:** the target genie is in a different project than the recipe calling `assign_task_to_genie`. Cross-project delegation is not supported — this is a platform constraint, not a config gap.
**Fix:** move the target genie into the same project as the calling recipe. For multi-agent systems, put the orchestrator, all sub-agents, and all delegation skills in **one** project from the start.

### Delegation works in Draft but fails after Deploy to Test/Prod
**Cause:** known bug (`<TICKET-ID>`) — the `assign_task_to_genie` action shows a validation error after a recipe containing it is deployed to a Test or Production environment.
**Fix:** track the bug; current workaround is to re-attach the genie reference in the deployed environment, or roll forward by deleting and re-saving the action in the destination env. Confirm with `<INTERNAL-TEAM>` before relying on it for prod.

### Sub-agent silently does nothing when called via `Assign Task to Genie`
**Cause (most common):** the target sub-agent has a skill that requires Verified User Access (VUA) or a Business Approval. Both are blocked during headless invocation — there's no end user to authenticate or approve. The whole delegation fails closed.
**Fix:** remove VUA / approval-required skills from the sub-agent, OR redesign so those skills live on the user-facing orchestrator instead of the headless specialist.

### Sub-agent returns prose instead of a structured object
**Cause:** the `structured_output` schema was declared on the calling recipe's `assign_task_to_genie` action, but the sub-agent's instructions don't tell it to follow that schema. The sub-agent treats the task as conversational.
**Fix:** in the sub-agent's job description (under "How do I get things done?"), explicitly say it produces structured output only and reference the fields. The declared schema *constrains* the output shape but the JD reinforces it — both are needed for high-confidence structured returns.

### Intermediate sub-agent messages aren't visible in the parent recipe
**Cause:** known gap (`<TICKET-ID>` / `<TICKET-ID>`) — when a sub-agent calls multiple skills as part of processing a task, those intermediate messages are visible in the sub-agent's conversation history but **not** exposed in the `assign_task_to_genie` output.
**Fix:** for now, only the final `response` and `structured_output` come back. If you need step-by-step visibility, retrieve the sub-agent's conversation via the Headless API (`GET /chat/conversations/...?conversation_id=<id from output>`) using the conversation_id returned by `assign_task`.

### Delegation job errors `"Genie is not active."`
**Cause:** the target sub-genie is **stopped/inactive**. A delegation only works against a *started* genie; if a specialist was stopped (e.g. left stopped after a recovery test, or never started), every `assign_task_to_genie` to it fails closed with `Genie is not active.` — and the orchestrator surfaces it as "agent unavailable," not as a config error.
**Fix:** ensure every sub-agent is `state: started`/`active` before running the orchestrator — `POST /api/agentic/genies/{gin}/start` for any that aren't. Check `GET /api/agentic/genies/{gin}` → `state`. Make "all specialists active" a pre-run checklist item; one stopped genie silently pauses the whole pipeline.

### Design: treat the SHARED data table as the source of truth, not the delegation's return value
**Why:** specialists in a master-slave system read/write a shared data table (the "case"). Build the orchestrator and your UI to read results **back from that table**, not solely from the `assign_task_to_genie` return — the shared record is the durable, auditable state and survives if a wrapper's return is delayed or a turn is re-run. Corollary: **don't re-run an orchestrator on a half-finished case expecting it to redo everything** — instruct it to read the case first and resume from the first incomplete step (its result field is empty), so a re-run after a recovered failure continues instead of restarting or wrongly reporting "done."

---

## Folder & project

### Can't delete a folder via `DELETE /api/folders/{id}`
**Cause:** folders directly under the workspace root auto-promote to "project folders". The `/folders` endpoint refuses to delete projects.
**Fix:** delete via `/api/projects/{project_id}` instead. Use `GET /api/folders/{id}` to find the `project_id`.

### `POST /api/folders` succeeds but the response isn't wrapped in `{data: ...}`
**Cause:** the `/folders` endpoint is a flat REST shape, unlike most agentic endpoints. Just `{id, parent_id, project_id, is_project, ...}` at the top level.
**Fix:** don't write `response['data']['id']` — write `response['id']`.

---

## OAuth-PKCE specific

### Popup redirects but parent window doesn't pick up the code
**Cause:** the popup is posting to `window.opener.postMessage(...)` but the parent's origin doesn't match the popup's `location.origin`. Browsers silently drop the message.
**Fix:** ensure the popup is on the same origin as the parent. If the popup must run on a different origin (uncommon), pass an explicit `targetOrigin` and validate it on the parent side.

### `invalid_grant` on `POST /oauth/token`
**Cause (most common):** the `code_verifier` sent to `/token` doesn't match the `code_challenge` used in `/authorize`. Usually because of a state mismatch between the two pages.
**Fix:** store the verifier in `sessionStorage` (not a regular var) keyed by `state`. Look it up when the popup returns.
**Cause (alternate):** the `redirect_uri` on `/token` doesn't exactly match the one on `/authorize`. Trailing slashes count.
**Fix:** use the same string literal in both places, and make sure it's the one registered on the OAuth client.

### Popup hangs after Workato login screen
**Cause:** the `redirect_uri` isn't registered on the OAuth client.
**Fix:** when minting the client, include `oauth_redirect_url` in the request body. Multiple URLs supported if you pass an array.

### The access token expires in ~1h — use the refresh token (it IS issued)
**Cause:** the OAuth access token has a short TTL (`expires_in` = 3600s). After ~1h every Headless call `401`s and a naive app forces a full interactive re-login.
**Fix:** **store and use the `refresh_token`.** Workato Identity's token exchange returns one (`refresh_token` alongside `access_token` + `id_token`) and supports `grant_type=refresh_token` at `/oauth/token` — exchange it for a fresh access token to renew silently. Verified-against-prod details that surprise people:
- The refresh token is **issued WITHOUT requesting `offline_access`** — in fact requesting `offline_access` is **rejected** (`"The requested scope is invalid, unknown, or malformed."`) and it isn't in the discovery doc's `scopes_supported`. So use the default `openid profile email` scope; don't add `offline_access`.
- Refresh tokens are **single-use / rotating** — each refresh returns a new `refresh_token`; persist the new one or the next refresh fails.
- Many builders never capture `refresh_token` (only `access_token`) and wrongly conclude there's no refresh path. There is.

### "Sign out" silently signs the user back in (no clean federated logout)
**Cause:** clearing the local app session leaves the **Workato Identity SSO session** intact, so the next "Sign in" SSO's straight back in as the same user. The OIDC `end_session_endpoint` (`/oauth/logout`) exists but requires an `id_token_hint`, and a `post_logout_redirect_uri` must be pre-registered — there's **no field to register one on the genie OAuth client**, so a federated logout strands the user on an Identity page with no route back.
**Fix:** do a **local logout** — clear your app's session + cookie and return to your own login screen (don't redirect to the federated `end_session` endpoint). Accept that the Identity SSO session persists (the next login is silent). Capture the `id_token` at token-exchange time anyway, in case `<ROADMAP-ITEM>` (post-logout-redirect registration support) becomes available.

---

## Conversation listing & display

### `topic` field on `GET /conversations/{id}` returns a number like "5951" instead of text
**Cause:** the detail endpoint's topic auto-generation hasn't run yet. List endpoint's topic is correct.
**Fix:** prefer the list endpoint for display, or fall back to the first user message if `topic` looks like a numeric ID.

### Messages come back in the wrong order
**Cause:** `GET /messages?limit=50` returns newest-first.
**Fix:** reverse client-side before rendering. Or paginate using the `cursor` field.

---

## Provisioning anomalies

### Two clients accidentally attached to one genie
**Cause:** Phase 1 enforces 1:1 but earlier API versions briefly didn't. You can also hit this if a previous attach didn't fully roll back.
**Fix:** `DELETE /api/agentic/genies/{gin}/clients/{old_gincl_id}` for the unwanted client. Then `POST /api/agentic/genies/{gin}/clients` with the right one.

### `409 "Genie has already been taken"` when attaching a client
**Cause:** Phase 1 1:1 violation — that client is already on a different genie, or this genie already has another client.
**Fix:** detach the existing pairing first, then attach.

### Genie created by one user, invisible to another
**Cause:** sub-tokens or scoped tokens see only what their identity can access. Two `wrkaus-…` tokens in the same workspace may belong to different identities with different folder access.
**Fix:** verify with `GET /api/users/me` on both tokens that the `id` is the same — if not, you're authenticated as different users.

### Sub-agent provisioning a genie that "doesn't exist"
**Cause:** MCP servers and Dev API tokens may authenticate as different identities. The MCP-provisioned genie isn't visible to the Dev API token.
**Fix:** mint a single Dev API token and use it for *all* provisioning. Don't mix MCP + Dev API for the same genie's lifecycle.

---

## When to escalate to Workato support

Open a ticket if:
- You hit a `5xx` on any documented endpoint and it persists for more than a few minutes.
- Runtime calls succeed but the genie consistently returns instantly with no `agent.message` even after fixing AI provider config — there may be a workspace-level gateway issue, the kind that took a manual fix from `<INTERNAL-TEAM>` to resolve previously.
- A `genie_run_id` from a failed turn — include this in the ticket. Support uses it to pull internal logs.

Include in any ticket: workspace ID, DC, genie ID, conversation ID, the failing `genie_run_id` (in `processing.started` events), and approximate UTC timestamp.
