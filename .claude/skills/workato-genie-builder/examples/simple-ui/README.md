# simple-ui — a minimal chat widget for any Workato Genie

About 350 lines of code (60 Python + ~280 HTML/JS) that wraps a Workato Genie in a runnable chat UI. Run it locally to see your genie answer real questions, invoke skills, and handle user-approval flows.

## What you get

- A single-page chat UI (`index.html`) — message bubbles, streaming responses, skill-running chips, and approval cards for `requires_user_confirmation: true` skills.
- A tiny Python proxy (`server.py`) that forwards `/api/*` to `genie-api.workato.com` with the right `Authorization: Bearer <api_key>` and `X-IDP-User-Id` headers. The api_key never enters the browser.

## Prerequisites

Provision a genie first via `python3 ../../scripts/provision-genie.py ../hr-concierge.json` (or your own spec). Save the printed:
- `GENIE_ID` (e.g. `gin-...-CD`)
- `GENIE_API_TOKEN` (64-char hex — the api_key)
- `IDP_USER_ID` (printed alongside the credentials)

Use `AUTH_TYPE=api_key` during provisioning. For OAuth-PKCE (a public web widget where end users SSO via Workato Identity), see the parent repo's `src/` — that's a more involved flow that the simple-ui doesn't cover.

## Run

```bash
GENIE_ID=gin-...-CD \
GENIE_API_TOKEN=<64-char api_key> \
IDP_USER_ID=<from provisioner> \
WORKATO_DC=us \
python3 server.py
```

Open `http://localhost:8088/` in a browser. Type "How much PTO do I have left?" and you should see:
1. Your message bubble
2. A purple "Running Get PTO Balance…" chip
3. The chip turns green (`✓ Get PTO Balance`)
4. The agent's reply with the data

For confirmation-required skills (like "Submit Time Off Request"): the UI shows an Approve / Reject card with the proposed inputs. Approve resumes the recipe and shows the agent's follow-up.

## What the proxy is doing

```
Browser                  server.py                  genie-api.workato.com
   │                         │                              │
   │  POST /api/messages     │                              │
   ├────────────────────────▶│                              │
   │                         │  POST /chat/.../messages     │
   │                         │  + Bearer <api_key>          │
   │                         │  + X-IDP-User-Id             │
   │                         ├─────────────────────────────▶│
   │                         │                              │
   │                         │  ◀── SSE stream ─────────────┤
   │  ◀── SSE stream ────────┤                              │
   │  (parses event types)   │                              │
```

The proxy is ~60 lines of Python and uses only the stdlib (`http.server`, `urllib.request`). It threads connections so multiple browser tabs work. SSE streams pass through chunk by chunk — `urlopen` returns an `HTTPResponse` whose `.read(n)` reads from the underlying socket without buffering the full body.

## Production differences

This demo is intentionally minimal. A production deployment would:

1. **Identity**: replace `IDP_USER_ID` env var with a per-request value sourced from your own SSO session (e.g. read from a JWT cookie, look up the IDP user ID, inject into `X-IDP-User-Id`).
2. **Multi-tenant**: serve multiple genies from one proxy, dispatching by hostname or path. Per-customer config in a database.
3. **OAuth-PKCE**: for direct browser → Workato auth (no server-mediated identity). Each end user signs in to Workato Identity, gets their own access_token, and the proxy disappears. See parent repo's `src/server.js` + `src/public/embed.js` for a working PKCE implementation.
4. **Conversation history**: persist `conversation_id` per user. Let users switch between past conversations. The simple-ui only tracks one conversation per tab.
5. **Stream resilience**: handle network drops via `GET /chat/conversations/events?since_created_at=…`. The simple-ui just shows an error and lets the user retry.
6. **CSP / origin**: lock down `Access-Control-Allow-Origin`. The simple-ui doesn't set any CORS headers since browser and proxy are same-origin.

## File map

| File | Lines | What it does |
|---|---|---|
| `server.py` | 60 | Python http.server with /api/* proxy |
| `index.html` | 280 | Chat UI with skill chips and approval cards |
| `README.md` | — | This file |
