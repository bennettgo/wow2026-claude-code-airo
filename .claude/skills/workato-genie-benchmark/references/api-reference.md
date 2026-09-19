# API reference — call sequences and response shapes

Everything below is verified against a live workspace. Where a shape looks
surprising, that's the point of writing it down — it's the thing worth
double-checking before you write a parser from assumption.

## Two tokens, two realms

The Dev API (`app.<dc>.workato.com`, or `app.workato.com` for `us`) and
the Headless/genie runtime API (`genie-api.<dc>.workato.com`) are separate
realms with separate auth:

- **Dev API** — `Authorization: Bearer <wrkaus-... token>`, the token from
  Workspace admin -> API clients. Used for provisioning, and for pulling
  conversation-events traces.
- **Headless API** — `Authorization: Bearer <genie's own minted client
  api_key>` (from `POST /api/agentic/genies/clients` +
  `POST /api/agentic/genies/{id}/clients`), **plus** an
  `X-IDP-User-Id` header set to the real IDP user ID (not an email — a
  real allow-listed user's email returns `401
  user_nonactive_or_missing`). Get the ID from `GET /api/iam/users`.
- **API-Platform endpoints** (your own ingest/judge/search recipes) — a
  static `api-token` header (from the Access Profile), not the
  `Authorization: Bearer` scheme. A harmless default `Authorization`
  header sent alongside it is simply ignored by these endpoints.

## Headless API — running one question through the Candidate

```
POST   /api/v1/genies/{genie_id}/chat/conversations
       body: {}
       -> {"result": {"conversation_id": "..."}}

POST   /api/v1/genies/{genie_id}/chat/conversations/{conversation_id}/messages
       body: {"message": "<question text>"}
       headers: X-IDP-User-Id: <idp_user_id>

GET    /api/v1/genies/{genie_id}/chat/conversations/{conversation_id}
       -> {"result": {"state": "idle" | "running" | ...}}
       Poll this every ~2s until state == "idle". No webhook/push option
       observed — polling is the only mechanism.

GET    /api/v1/genies/{genie_id}/chat/conversations/{conversation_id}/messages
       -> {"result": {"messages": [{"source": "user"|"genie", "content": "..."}]}}
       Messages are newest-first. Take the first message where source == "genie".
```

Gotcha: every payload is wrapped under `"result"`, never `"data"`.
Messages use `source`, never `role`.

## Dev API — pulling the trace for one conversation

```
GET /agentic/genies/{genie_id}/conversations/{conversation_id}/events
```

Returns the full event list for that conversation, in order:
`genie_run_start`, `ai_job_started`, `user_message`, `llm_call_started`,
`llm_call_completed`, `request_tool_call`, `tool_execution_started`,
`tool_execution_completed`, ... , `agent_message`, `ai_job_completed`,
`genie_run_finish`, `topic_assigned`.

**Everything you need for scoring comes out of this list, not the chat
reply:**

- **Cited/retrieved document IDs** — from every `tool_execution_completed`
  event where the underlying tool is `enterprise_search`. Its `data` field
  is a JSON-encoded string; decode it, then decode its own nested
  `message` field (also a JSON-encoded string) to reach
  `knowledge_fragments: [{document_id, title, content}, ...]`. A
  multi-search conversation has more than one such event — take the union
  across all of them (first-occurrence content wins on duplicate IDs).
- **Latency** — difference between `genie_run_start` and
  `genie_run_finish` timestamps (`date_time` fields, ISO 8601 with
  fractional seconds).
- **Total tokens** — sum `input_tokens` + `output_tokens` across every
  `llm_call_completed` event.
- **Step count** — count of `tool_execution_completed` events (each one
  is a distinct `enterprise_search` invocation the Genie made).

## The API-Platform recipe pattern (ingest / judge / search)

All three (bulk ingest, judge scoring, retrieval-only search) share one
shape: a recipe triggered by `workato_api_platform.receive_request`,
one or more actions, and `workato_api_platform.return_response`. This
gets exposed as a plain HTTP endpoint via an API Collection -> API
Endpoint -> API Client -> Access Profile stack (provision once, call many
times with a static token).

```
receive_request (trigger)
  -> declares a JSON request schema + response schema(s)
     (a "response" name/http_status_code pair per outcome, e.g. "ok"/200
     and "error"/400)
  -> your action(s) here, referencing receive_request_N['request']['field']
     via an f-string-style datapill
  -> return_response (action)
     -> maps your action's output fields into the declared response schema
```

`enterprise_context.search_documents` accepts
`enable_llm_reranking="true"` or `"false"` in the recipe action. This
changes only that direct action; it does not change a Genie's native
`enterprise_search` tool. For a benchmark, record the setting and compare
both values against the same corpus and queries rather than assuming
reranking helps every workload.

`workato_genie.assign_task_to_genie` (used for judging) takes a
`genie_handle`, free-text `task_instructions` (an f-string embedding
whatever context the judgment needs), and a `structured_output` field: a
JSON-encoded array of `{name, type, control_type}` field specs (types seen
in practice: `string`/`text`, `boolean`/`checkbox`, `array of object` with
nested `properties`). The action's own output surfaces under
`<step_name>['structured_output']['<field_name>']`.

To regenerate a template's `code` field after modifying a recipe through
the AIRO MCP's `recipe_builder_*` tools (never hand-edit the JSON directly
— the datapill encoding is fragile to edit by hand):

```python
from workato_client import WorkatoClient
c = WorkatoClient(token=DEV_API_TOKEN, dc="us")
status, body = c.call("GET", f"/api/recipes/{recipe_id}")
code = body["code"]
open("assets/<name>.json", "w").write(code)
```

## Debugging a specific failed recipe job

The recipe's own HTTP error response is often thin (e.g. a bare job
handle). Pull the real error via the Dev API:

```
GET /recipes/{recipe_id}/jobs/{job_id}
```

or `mcp__workato-airo-mcp-server__job_get(recipe_id, job_handle)` if
working through the AIRO MCP directly. This returns the actual failed
line's `Error` text, its full `Inputs`, and (on success) `Outputs` — the
`Inputs` blob is also how you recover a job's exact original inputs after
the fact, useful for reproducing a fix against the precise conditions that
originally failed.
