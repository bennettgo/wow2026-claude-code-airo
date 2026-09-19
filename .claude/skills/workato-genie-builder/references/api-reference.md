# Workato Genie API reference

Every endpoint touched by the build-a-genie flow, curl-ready.

## Host conventions

These examples use `app.workato.com` and `genie-api.workato.com` (US DC). **Substitute your data center**:

| DC | Dev API base | Headless API base |
|---|---|---|
| US (default) | `app.workato.com` | `genie-api.workato.com` |
| EU | `app.eu.workato.com` | `genie-api.eu.workato.com` |
| Japan | `app.jp.workato.com` | `genie-api.jp.workato.com` |
| Singapore | `app.sg.workato.com` | `genie-api.sg.workato.com` |
| Australia | `app.au.workato.com` | `genie-api.au.workato.com` |
| India | `app.in.workato.com` | `genie-api.in.workato.com` |
| Israel | `app.il.workato.com` | `genie-api.il.workato.com` |

Tokens are DC-scoped. A US `wrkaus-…` token cannot call an EU workspace and vice versa.

Set environment variables:

```bash
export TOKEN=wrkaus-...                    # Dev API builder token
export RT_TOKEN=...                        # 64-char Headless runtime token (from a client mint)
export DEV_API_BASE=https://app.workato.com           # change for non-US
export HEADLESS_BASE=https://genie-api.workato.com    # change for non-US
```

---

## Dev API — `$DEV_API_BASE`

All Dev API calls take `Authorization: Bearer $TOKEN` and `Content-Type: application/json` (for POST/PUT).

### Folders

```bash
# Find your root folder id
curl -sS -H "Authorization: Bearer $TOKEN" \
  "https://app.workato.com/api/users/me"
# → .root_folder_id

# Create a folder
curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "HR Concierge", "parent_id": <ROOT_FOLDER_ID>}' \
  "https://app.workato.com/api/folders"
# → flat object with id, parent_id, project_id, is_project (note: NOT wrapped in {data:...})

# Delete (root-level folders are projects: use /api/projects/{project_id})
curl -sS -X DELETE -H "Authorization: Bearer $TOKEN" \
  "https://app.workato.com/api/folders/<FOLDER_ID>"
```

### Genies

```bash
# List
curl -sS -H "Authorization: Bearer $TOKEN" \
  "https://app.workato.com/api/agentic/genies?per_page=50"

# Get one
curl -sS -H "Authorization: Bearer $TOKEN" \
  "https://app.workato.com/api/agentic/genies/<GIN>"

# Create
curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "name": "InnovaTech HR Concierge",
    "description": "AI assistant for HR questions",
    "folder_id": <FOLDER_ID>,
    "instructions": "**What's my job?** ...",
    "ai_provider": "open_ai",
    "matrix": {}
  }' \
  "https://app.workato.com/api/agentic/genies"
# → {"data":{"id":"gin-...-CD"}}

# Update (PATCH-style — only send what you want to change)
curl -sS -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"instructions": "...new system prompt..."}' \
  "https://app.workato.com/api/agentic/genies/<GIN>"

# Start / Stop
curl -sS -X POST -H "Authorization: Bearer $TOKEN" \
  "https://app.workato.com/api/agentic/genies/<GIN>/start"
curl -sS -X POST -H "Authorization: Bearer $TOKEN" \
  "https://app.workato.com/api/agentic/genies/<GIN>/stop"
```

### Recipes (skills are recipes with the `workato_genie` trigger)

```bash
# Create recipe — auto-creates skill record IF code has workato_genie trigger
curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"recipe": {
    "name": "Get PTO Balance",
    "folder_id": "<FOLDER_ID>",
    "code": "<json-stringified-recipe-code>",
    "config": "[{\"keyword\":\"application\",\"name\":\"workato_genie\",\"provider\":\"workato_genie\",\"skip_validation\":false,\"account_id\":null}]"
  }}' \
  "https://app.workato.com/api/recipes"
# → {"id":<RECIPE_ID>, ...}

# Start (required before genie can invoke)
curl -sS -X PUT -H "Authorization: Bearer $TOKEN" \
  "https://app.workato.com/api/recipes/<RECIPE_ID>/start"

# Stop
curl -sS -X PUT -H "Authorization: Bearer $TOKEN" \
  "https://app.workato.com/api/recipes/<RECIPE_ID>/stop"
```

### Skills (read-only on the agentic surface)

```bash
# Find skills in a folder (use this to look up auto-created skill IDs from recipes)
curl -sS -H "Authorization: Bearer $TOKEN" \
  "https://app.workato.com/api/agentic/skills?folder_id=<FOLDER_ID>&per_page=100"
# Find entry where .provider_id == <RECIPE_ID> and read its .id (skl-...-CD)

# NOTE: ?recipe_id= and ?provider_id= filters are silently ignored. Use ?folder_id=.

# Attach skills to a genie
curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"skill_ids": ["skl-...","skl-..."]}' \
  "https://app.workato.com/api/agentic/genies/<GIN>/assign_skills"

# Detach
curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"skill_ids": ["skl-..."]}' \
  "https://app.workato.com/api/agentic/genies/<GIN>/remove_skills"
```

### Knowledge bases

```bash
# Attach
curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"knowledge_base_ids": ["kb-..."]}' \
  "https://app.workato.com/api/agentic/genies/<GIN>/assign_knowledge_bases"
```

KB authoring (file upload, recipe-backed) is documented separately in Workato's Knowledge Base API. Phase 1 of the headless API does not exercise it; v1 genies typically embed reference content directly in `instructions`.

### IAM — users & groups

```bash
# Find user by email
curl -sS -H "Authorization: Bearer $TOKEN" \
  "https://app.workato.com/api/iam/users?query=alice@example.com"
# → {"data": [{"id": "<IDP_USER_ID>", ...}]}

# Create user (if they've never signed in)
curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "full_name": "Alice Example"}' \
  "https://app.workato.com/api/iam/users"

# Create user group
curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "HR Concierge Users"}' \
  "https://app.workato.com/api/iam/user_groups"
# → {"data": {"id": "<GROUP_ID>", ...}}

# Add user to group
curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"user_group_id": "<GROUP_ID>"}' \
  "https://app.workato.com/api/iam/users/<IDP_USER_ID>/add_to_group"

# Allow-list group on a genie
curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"user_group_ids": ["<GROUP_ID>"]}' \
  "https://app.workato.com/api/agentic/genies/<GIN>/assign_user_groups"
```

### Genie clients

```bash
# Mint API-key client
curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"client_name": "HR Widget", "auth": {"type": "api_key"}}' \
  "https://app.workato.com/api/agentic/genies/clients"
# → {"data": {"client_id":"gincl-...", "api_key":"<64-char hex, SHOW ONCE>"}}

# Mint OAuth-PKCE client
curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "client_name": "HR Widget (OAuth)",
    "auth": {
      "type": "oauth",
      "oauth_redirect_url": "https://employees.acme.com/oauth/callback"
    }
  }' \
  "https://app.workato.com/api/agentic/genies/clients"
# → {"data": {"client_id":"gincl-...", "oauth_client_id":"<public>"}}

# Attach client to genie (Phase 1: 1:1)
curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"genie_client_id": "<CLIENT_ID>"}' \
  "https://app.workato.com/api/agentic/genies/<GIN>/clients"

# Detach
curl -sS -X DELETE -H "Authorization: Bearer $TOKEN" \
  "https://app.workato.com/api/agentic/genies/<GIN>/clients/<CLIENT_ID>"

# Regenerate api_key (API-key clients only)
curl -sS -X POST -H "Authorization: Bearer $TOKEN" \
  "https://app.workato.com/api/agentic/genies/clients/<CLIENT_ID>/regenerate"
```

---

## Headless API — `https://genie-api.workato.com`

All Headless calls take **either**:

```
Authorization: Bearer <api_key>      # 64-char hex from the API-key client
X-IDP-User-Id: <idp_user_id>          # the end user (must be in an allow-listed group)
```

**or** (OAuth-PKCE mode):

```
Authorization: Bearer <oauth_access_token>   # from the code-for-token exchange
```

### Conversations

```bash
# List user's conversations
curl -sS \
  -H "Authorization: Bearer $RT_TOKEN" -H "X-IDP-User-Id: $UID" \
  "https://genie-api.workato.com/api/v1/genies/$GIN/chat/conversations?limit=20"

# Get one
curl -sS \
  -H "Authorization: Bearer $RT_TOKEN" -H "X-IDP-User-Id: $UID" \
  "https://genie-api.workato.com/api/v1/genies/$GIN/chat/conversations/$CID"

# Create
curl -sS -X POST \
  -H "Authorization: Bearer $RT_TOKEN" -H "X-IDP-User-Id: $UID" \
  -H "Content-Type: application/json" -d '{}' \
  "https://genie-api.workato.com/api/v1/genies/$GIN/chat/conversations"

# Delete
curl -sS -X DELETE \
  -H "Authorization: Bearer $RT_TOKEN" -H "X-IDP-User-Id: $UID" \
  "https://genie-api.workato.com/api/v1/genies/$GIN/chat/conversations/$CID"
```

### Messages — send (SSE streaming)

```bash
curl -sN -X POST \
  -H "Authorization: Bearer $RT_TOKEN" -H "X-IDP-User-Id: $UID" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"file_id":"","message":"How much PTO do I have?","stream":true}' \
  "https://genie-api.workato.com/api/v1/genies/$GIN/chat/conversations/$CID/messages"
```

Response: stream of SSE events. Event types:

| Event | Persisted? | Meaning |
|---|---|---|
| `processing.started` | no | turn started |
| `processing.finished` | no | turn complete |
| `agent.message` | **yes** | text reply from genie |
| `skill.running` | no | skill execution started |
| `skill.completed` | no | skill finished OK. **Note:** the structured `result` is fed to the LLM internally but typically **not echoed** in this SSE event. The agent's reply (in `agent.message`) reflects the data |
| `skill.stopped` | no | terminal-success state sometimes emitted in place of `skill.completed`; same semantics — handle identically |
| `skill.failed` | **yes** | skill raised an error |
| `skill.confirmation_required` | **yes** | mutating skill needs user approval |
| `runtime_connection.auth_required` | **yes** | skill needs end-user OAuth (e.g. their Salesforce); carries `auth_link` |
| `runtime_connection.auth_success` | no | connection completed |
| `runtime_connection.auth_failed` | **yes** | connection failed |
| `business_approval.required` | **yes** | recipe-side approval (Phase 2) |
| `system.ping` | no | heartbeat every ~30s during long-running conversations; **ignore in handlers** |

### Messages — list (history)

```bash
curl -sS \
  -H "Authorization: Bearer $RT_TOKEN" -H "X-IDP-User-Id: $UID" \
  "https://genie-api.workato.com/api/v1/genies/$GIN/chat/conversations/$CID/messages?limit=50"
# Returns newest-first — reverse client-side before rendering
```

### Skill approval

When a `skill.confirmation_required` event arrives, the conversation goes into `awaiting_approval` state. Resolve:

```bash
curl -sS -X POST \
  -H "Authorization: Bearer $RT_TOKEN" -H "X-IDP-User-Id: $UID" \
  -H "Content-Type: application/json" \
  -d '{"resolution":"approved"}' \
  "https://genie-api.workato.com/api/v1/genies/$GIN/chat/conversations/$CID/skill_approval/$CALL_ID"

# Or reject
curl -sS -X POST \
  -H "Authorization: Bearer $RT_TOKEN" -H "X-IDP-User-Id: $UID" \
  -H "Content-Type: application/json" \
  -d '{"resolution":"rejected","rejection_reason":"User declined"}' \
  "https://genie-api.workato.com/api/v1/genies/$GIN/chat/conversations/$CID/skill_approval/$CALL_ID"
```

The original SSE stream stays open and resumes with the next events (skill.running → skill.completed → agent.message).

### Event recovery (after stream drop)

Retrieve persisted events that happened since a known timestamp:

```bash
curl -sS \
  -H "Authorization: Bearer $RT_TOKEN" -H "X-IDP-User-Id: $UID" \
  "https://genie-api.workato.com/api/v1/genies/$GIN/chat/conversations/events\
?conversation_id=$CID\
&since_created_at=2026-06-08T12:34:56Z\
&limit=50"
```

**Field name is `since_created_at` (ISO 8601), not `since_ms`.** Preview used `since_ms` (Unix epoch); prod renamed it. Sort the returned events by `(created_at, event_id)` before applying.

### Connection actions (per-user OAuth for skills)

When a `runtime_connection.auth_required` event arrives, the user must complete an upstream OAuth flow at `auth_link`. After they return, the SSE stream emits `runtime_connection.auth_success` and resumes the turn.

```bash
# Manually retrigger a stalled connection check (rarely needed)
curl -sS -X POST \
  -H "Authorization: Bearer $RT_TOKEN" -H "X-IDP-User-Id: $UID" \
  "https://genie-api.workato.com/api/v1/genies/$GIN/chat/conversations/$CID/runtime_connection/$CONN_REQ_ID/retry"
```

---

## OAuth-PKCE flow (browser-direct, no client secret)

The user-facing flow uses Workato Identity (`id.workato.com`). High-level:

1. Browser generates `code_verifier` (random 43+ char URL-safe string) and `code_challenge = base64url(sha256(code_verifier))`.
2. Browser opens popup to `https://id.workato.com/oauth/authorize?response_type=code&client_id=<OAUTH_CLIENT_ID>&redirect_uri=<URL>&scope=openid+profile+email&state=<random>&code_challenge=<challenge>&code_challenge_method=S256`.
3. User authenticates, popup redirects to `redirect_uri?code=<authorization_code>&state=<random>`.
4. Browser exchanges code for token at `https://id.workato.com/oauth/token` with form-encoded body: `grant_type=authorization_code&client_id=<...>&redirect_uri=<...>&code=<...>&code_verifier=<...>`. **No client secret.**
5. Browser stores `access_token`, uses it in `Authorization: Bearer <access_token>` against the Headless API.

A small same-origin server typically relays step 4 to avoid CORS on `id.workato.com`. Reference implementation: parent repo `src/server.js` `tokenExchange()` function.

---

## Quick reference: UI ↔ Dev API ↔ Headless API

| Action | UI | Dev API | Headless API |
|---|---|---|---|
| Create genie | + New genie | `POST /api/agentic/genies` | — |
| Edit instructions | Instructions tab | `PUT /api/agentic/genies/{id}` | — |
| Add skill | Skills panel | `POST /api/agentic/genies/{id}/assign_skills` | — |
| Add knowledge base | KBs panel | `POST /api/agentic/genies/{id}/assign_knowledge_bases` | — |
| Allow-list group | People panel | `POST /api/agentic/genies/{id}/assign_user_groups` | — |
| Mint client | Connect Interface | `POST /api/agentic/genies/clients` | — |
| Attach client | (implicit) | `POST /api/agentic/genies/{id}/clients` | — |
| Start/Stop | Top-right toggle | `POST /api/agentic/genies/{id}/start` / `/stop` | — |
| Chat | Test tab | — | `POST /chat/conversations/{id}/messages` |
| List conversations | Conversations tab | — | `GET /chat/conversations` |
| Approve skill | (inside Test UI) | — | `POST /chat/conversations/{id}/skill_approval/{call_id}` |
