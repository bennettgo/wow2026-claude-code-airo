# Genie client + headless chat API reference

How to invoke a specific genie programmatically (the "invoke-to-test" path). Captured from the
vendored `provision-genie.py` + `test-headless-chat.sh` during the 2026-07-01 dogfood.

**Status:** none of these endpoints are exposed by the current Workato Dev API MCP. This is the
concrete gap behind the invoke-to-test harness requirement — see the `genie_chat` proposal at the
bottom.

---

## A. Management endpoints — Workato Dev API

Host: `https://app.workato.com` (or `https://app.{dc}.workato.com`)
Auth: `Authorization: Bearer <DEV_API_TOKEN>` · `Content-Type: application/json`

### A1. Mint a genie client
`POST /api/agentic/genies/clients`
```json
{ "client_name": "My Genie Client", "auth": { "type": "api_key" } }
```
OAuth variant: `"auth": { "type": "oauth", "oauth_redirect_url": "<url>" }`
Response:
```json
{ "data": { "client_id": "...", "api_key": "<64-char runtime token>", "oauth_client_id": null } }
```
The `api_key` is the `GENIE_API_TOKEN` used for all headless calls (group B).

### A2. Attach the client to a genie
`POST /api/agentic/genies/{genie_id}/clients`
```json
{ "genie_client_id": "<client_id>" }
```

### Supporting — IDP user context
- `GET /api/iam/users?query=<email>` → `{ "data": [ { "id", "email", "name" } ] }` — the `id` is the `IDP_USER_ID`.
- `POST /api/iam/users/{idp_user_id}/add_to_group` → `{ "user_group_id": <id> }` (only needed if the genie restricts access by user group).

---

## B. Runtime / headless endpoints — Genie API

Host: `https://genie-api.workato.com` (or `https://genie-api.{dc}.workato.com`)
Base: `/api/v1/genies/{genie_id}/chat`
Auth headers on **every** call: `Authorization: Bearer <GENIE_API_TOKEN>` **and** `X-IDP-User-Id: <idp_user_id>`

### B1. Create a conversation
`POST {base}/conversations`  body `{}`
Response: `{ "result": { "conversation_id": "..." } }`

### B2. Send a message (SSE stream)
`POST {base}/conversations/{conversation_id}/messages` · add header `Accept: text/event-stream`
```json
{ "file_id": "", "message": "<user text>", "stream": true }
```
Returns Server-Sent Events; the answer streams in and terminates on a `processing.finished` event.
(`scripts/sse-parser.py` reassembles the streamed text.)

---

## End-to-end sequence (build → invoke-to-test)

1. Build the genie (AIRO MCP `genie_create` + `knowledge_base_assign_to_genie` + `..._start`).
2. `POST /api/agentic/genies/clients` → `api_key` (= `GENIE_API_TOKEN`), `client_id`.
3. `POST /api/agentic/genies/{genie_id}/clients` `{genie_client_id}` — attach.
4. Resolve `IDP_USER_ID` (`GET /api/iam/users?query=<email>`).
5. `POST /api/v1/genies/{genie_id}/chat/conversations` → `conversation_id`.
6. `POST .../conversations/{conversation_id}/messages` `{message, stream:true}` → read SSE.

---

## Proposed MCP tool to close the gap

The building agent should be able to test a genie it just built without juggling clients, IDP
users, conversations, and SSE. Propose a single native tool on the AIRO/Dev API MCP:

**`genie_chat(genie_id, message, [idp_user_id])` → `{ response, conversation_id }`**

Internally: reuse-or-mint an api_key client for the genie, ensure it's attached, create a
conversation, send the message, drain the SSE stream, and return the final assembled text. This is
the "invoke-to-test" primitive — with it, the `airo-architect` `builder-integrator` can run its
sample tests via one call instead of the generic `post_airo_chat` (which hits the generic Airo
copilot, not the specific genie).
