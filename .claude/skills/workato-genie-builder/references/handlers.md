# Handler reference — verified user access, confirmation flow, state machine

Every behavior in this file is verified empirically against `genie-api.workato.com` (US prod) on 2026-06-08 using a fresh HR Concierge genie + 4 stub skills.

---

## 1. Verified user access — what happens when the user isn't allow-listed

If the `X-IDP-User-Id` header sent to the Headless API is for a user **not in any user group attached to the genie** (or a user that doesn't exist in the workspace at all), the runtime returns:

```
HTTP 401 Unauthorized
{
  "error_code":    "user_nonactive_or_missing",
  "error_message": "The user was not found in this environment or has not accepted their invitation.",
  "request_id":    "..."
}
```

**Notes:**
- The status code is **`401`, not `403`**. Many specs and docs (including the Workato PRD) describe this as `403 access_denied`; in practice prod returns `401 user_nonactive_or_missing`.
- The error does **not distinguish** between "user doesn't exist" vs "user exists but not in the allow-listed group". Both produce the same code. If you need to surface a different message to a real user vs an unknown user, look them up via `GET /api/iam/users?query=<email>` server-side before the runtime call.
- Behaviour is identical across endpoints — `POST /conversations`, `GET /conversations`, `POST /messages` all return the same 401.

**Client handling:**
```js
if (resp.status === 401) {
  // user is not registered or not allow-listed — show signup / contact-admin UI
  showAccessDenied();
} else if (resp.status === 403) {
  // (Rare) genuinely forbidden — different cause, e.g. revoked token
  showForbidden();
}
```

---

## 2. User confirmation — the approve flow

For skills with `requires_user_confirmation: true` on the trigger (e.g. `Submit Time Off Request` in the HR Concierge example), the runtime emits a `skill.confirmation_required` SSE event before running the skill. The conversation pauses until the client posts a resolution.

### Sequence

```
User: "Submit a PTO request for Nov 1–3, type pto"
   │
   ▼
SSE event order:
  processing.started
  skill.confirmation_required   ← stream stays open, conversation in skill_processing state
  system.ping                   ← heartbeat every ~30s while paused
  system.ping
  …
   │
   ▼
Client POSTs:
  POST /chat/conversations/{cid}/skill_approval/{call_id}
  body: {"resolution": "approved"}
  → 200, empty body
   │
   ▼
Original SSE stream resumes with:
  skill.running
  skill.completed
  agent.message
  processing.finished
```

The **original SSE stream stays open** through the pause — you don't need to reconnect. If the client closes the stream (e.g. user closes the tab), use the recovery endpoint (section 4) on reconnect.

### `skill.confirmation_required` event payload (verbatim field names)

```json
{
  "type": "skill.confirmation_required",
  "call_id": "call_3U5J3k193gsJ7jJgQKshBObf",
  "skill_name": "Submit Time Off Request",
  "skill_id": "recipe:73237752",
  "skill_parameters": {
    "start_date": "2026-11-01",
    "end_date": "2026-11-03",
    "leave_type": "pto",
    "notes": "Vacation"
  },
  "skill_parameter_schema": [
    {"name": "start_date", "label": "Start date", "type": "string", "control_type": "text", "optional": false, "hint": "YYYY-MM-DD"},
    ...
  ],
  "conversation_id": "...",
  "genie_run_id": "...",
  "seq_num": 2,
  "created_at": "2026-06-08T..."
}
```

- **`call_id`** is OpenAI-tool-call style: `call_<22 alnum chars>`. This is the underlying model's `tool_call_id` passed through verbatim. Echo it back exactly in your approval POST.
- **`skill_id`** is the wire-format ID: `recipe:<numeric_recipe_id>`. This is **not** the `skl-…-CD` ID from the Dev API — those two surfaces use different ID forms. If you need to correlate, match on `skill_name`.
- **`skill_parameters`** is the *resolved* args the model wants to pass (key/value, ready to display).
- **`skill_parameter_schema`** is the full schema definition with labels, hints, optional/required — useful for rendering an editable confirmation form.

### Resolving the approval

```bash
curl -sS -X POST \
  -H "Authorization: Bearer $RT_TOKEN" -H "X-IDP-User-Id: $UID" \
  -H "Content-Type: application/json" \
  -d '{"resolution":"approved"}' \
  "https://genie-api.workato.com/api/v1/genies/$GIN/chat/conversations/$CID/skill_approval/$CALL_ID"
```

Returns **`200` with empty body**. The original SSE stream then resumes (or persisted events become recoverable via the events endpoint).

---

## 3. User confirmation — the reject flow

Same sequence up to `skill.confirmation_required`. To reject:

```bash
curl -sS -X POST \
  -H "Authorization: Bearer $RT_TOKEN" -H "X-IDP-User-Id: $UID" \
  -H "Content-Type: application/json" \
  -d '{"resolution":"rejected","rejection_reason":"User changed their mind"}' \
  "https://genie-api.workato.com/api/v1/genies/$GIN/chat/conversations/$CID/skill_approval/$CALL_ID"
```

What happens next:
- The skill **never runs** — there are no `skill.running` / `skill.completed` events.
- The agent receives the rejection as a tool-result back to the model.
- The agent's next `agent.message` surfaces the rejection reason verbatim. Example:
  > "You previously rejected this PTO submission (\"Rejected by user: User changed their mind\"), so I did not submit a new request just now…"

If you don't want the rejection_reason quoted back to the user, send a generic one (e.g. `"User declined"`) or omit it.

`rejection_reason` is optional. The minimum reject body is `{"resolution":"rejected"}`.

---

## 4. Recovery — when the SSE stream drops mid-turn

If the network drops between `skill.confirmation_required` and the user's resolution (or any other mid-turn break), poll the events endpoint:

```bash
GET /api/v1/genies/$GIN/chat/conversations/events
   ?conversation_id=$CID
   &since_created_at=<ISO8601 of last event you successfully processed>
   &limit=50
```

**Returns JSON** (not SSE): `{"result":{"events":[{...}]}}`. Each event has the same shape as its SSE counterpart, plus `created_at`. Sort by `(created_at, event_id)` before applying.

Persisted event types — returned by `/events` for ~24h:
- `agent.message`
- `skill.running` / `skill.completed` / `skill.failed` / `skill.stopped`
- `processing.started` / `processing.finished`
- `skill.confirmation_required`
- `runtime_connection.auth_required` / `auth_failed`
- `business_approval.required`

Truly ephemeral — never in `/events`, only seen live:
- `runtime_connection.auth_success`
- `system.ping`

> **⚠️ Corrected 2026-06-17 (the 2026-06-08 pass had this wrong).** The earlier version listed `skill.running`/`skill.completed`/`processing.*` as ephemeral/unrecoverable. **They are not** — verified on US prod that `GET /conversations/events` returns the full `skill.running`/`skill.completed`/`processing.*` timeline for completed conversations, including one **12.5 h old** (one 18-event dump: `processing.started ×3, agent.message ×5, skill.running ×2, skill.completed ×5, processing.finished ×2, skill.confirmation_required ×1`). **Consequence:** you can fully **rebuild a past conversation's skill-chip timeline on reload** from `/events` — no client-side cache needed. Only `auth_success` + `system.ping` are genuinely ephemeral. (A conversation showing *zero* skill events in `/events` simply made no skill calls — e.g. a guardrail-blocked turn — not expiry.)

**Rebuilding a conversation timeline on reload (recommended):**
```
events   = GET /conversations/events?conversation_id=$CID&since_created_at=2026-01-01T00:00:00Z&limit=100   # oldest-first
userMsgs = GET /conversations/$CID/messages   # for user bubbles (events carry the genie agent.message, not user turns)
# merge userMsgs(source=user) + events, sort by created_at, render skill.* as chips and agent.message as bubbles.
```
Dedup by `(genie_run_id, seq_num)` — `seq_num` resets to 1 at each new `processing.started` (each turn), so a global "seen 1,2,3 → skip" silently drops later turns.

If a recoverable confirmation event is still pending when you reconnect, the conversation will still be in `skill_processing` state. Resolve it, then keep polling for the post-resolution events.

---

## 4a. Verified User Access — the runtime-connection flow (the part that strands turns)

When a skill needs the **end user's own connection** (VUA / "act as the signed-in user", e.g. a Salesforce skill), the runtime emits `runtime_connection.auth_required` carrying an `auth_link` (`url`, `connector_name`, `expires_at` — a one-time OAuth link that **expires ~5 min** after issue). The turn then **parks**. Handled naively this strands the user. Verified behavior:

1. `runtime_connection.auth_required` fires; conversation is `skill_processing` with `last_event.type === "runtime_connection.auth_required"` (this *is* the "awaiting connection" state — there's no distinct one). `POST /messages` returns **409** while parked, so **do NOT "nudge" it with a new message — that 409s.** Show a "Connect <connector>" button to `auth_link.url`.
2. User authorizes in another tab; on success the genie **resumes the same turn**.
3. **Gotcha #1 — `auth_success` / `auth_failed` reach NO channel, and the resumed turn is `/messages`-only.** This is the big one, verified by holding the SSE stream open through a real authorization: after the user authorized, the open stream delivered **only `system.ping`** for minutes, then `system.stream_interrupted` — **no `auth_success`, no resumed `skill.*`, no resumed `agent.message`**. And **`/events` never contained `auth_success` or the resumed answer either.** The genie *did* finish — but the resumed answer was retrievable **only via `GET /conversations/$CID/messages`**. So there is **no event telling you `auth_required` → `auth_success`**; you can only **infer** success by polling `/messages` for a new genie answer. `auth_failed` is effectively **undetectable** (you just time out). _(This contradicts the PRD, which lists `auth_success`/`auth_failed` as 24h-retained SSE events — they aren't delivered in practice.)_
4. **Gotcha #2 — you cannot re-POST to reopen, and `/events` recovery misses the resumed turn.** `POST /messages` on the parked (non-idle) conversation → **409**, so the "resend to reconnect" pattern doesn't work. The only stream reopen is `GET /conversations/$CID/genie-runs/$GENIE_RUN_ID` with a `Last-Event-Id` header (exists, opens a stream) — but it does **not** surface the resumed VUA events either. And `seq_num` **resets to 1 per genie run**, and the resumed turn is a *new* run, so a per-run cursor can't reconcile across the pause. **Net:** the durable signal remains the new `/messages` answer.
5. **Gotcha #3 — the state endpoint can report `idle` while the turn is really parked** (state-vs-action inconsistency). Don't end the turn on `idle` alone while a connection is pending; keep polling `/messages` until the resumed answer appears.

**Practical client recipe:** while `auth_link` is set, render a "Connect <connector>" button, keep the card showing *"waiting for authorization…"* (do **not** optimistically flip to "authorized" on click/window-focus — there's no signal yet), and poll `GET /conversations/$CID/messages` for a new genie message. When it appears, the connection succeeded → remove the card and render the answer.

**Surviving a refresh:** both `runtime_connection.auth_required` and `skill.confirmation_required` **are** persisted in `/events`. On reload, if `state` is non-idle and the latest such event is unresolved, **rebuild the actionable card from it** (the `auth_link`, or the `call_id` + params) and resume polling. Without this, refreshing strands the user mid-flow.

There's no API to **pre-provision** or check a user's runtime connection ahead of time (the PRD specs `POST /runtime_connection/:attempt_id/link` returning `status: auth_required|authorized`, but it currently **404s**), and no event for "already connected, no prompt needed" — the first VUA call of a session always prompts.

---

## 5. Conversation states

`GET /api/v1/genies/$GIN/chat/conversations/$CID` returns:

```json
{
  "result": {
    "state": "idle",
    "last_event": { "type": "processing.finished", ... },
    "updated_at": "..."
  }
}
```

States observed in prod:

| State | When | What it means |
|---|---|---|
| `idle` | Default. After every `processing.finished` | Ready to accept the next user message |
| `skill_processing` | Between any `skill.running` or `skill.confirmation_required` and the terminal event | The runtime is busy. Covers BOTH actual skill execution AND awaiting human approval — same state for both |

**Important:** despite what some docs suggest, prod does **not** have a distinct `awaiting_approval` state. To distinguish "skill is busy running" from "skill is paused waiting for human approval," you must inspect `last_event.type`:

- `last_event.type === "skill.running"` → genuinely executing
- `last_event.type === "skill.confirmation_required"` → paused, needs human resolution
- `last_event.type === "skill.completed"` (briefly, before state flips to idle) → just finished

So a robust UI checks both `state` AND `last_event.type`:

```js
if (state === "skill_processing" && lastEvent.type === "skill.confirmation_required") {
  showApprovalCard(lastEvent);
} else if (state === "skill_processing") {
  showSpinner();
} else {
  showIdle();
}
```

---

## 6. SSE heartbeats

While a conversation is in `skill_processing` (or any long-running state), the runtime sends `system.ping` events every ~30s to keep the SSE connection alive through corporate proxies that close idle TCP connections.

```
event: system.ping
data: {"type":"system.ping","timestamp":"..."}
```

Action: **ignore them** in your event handler. They serve only to keep the TCP socket alive.

```js
function handle(eventType, data) {
  if (eventType === "system.ping") return; // ignore heartbeats
  // ... normal handling
}
```

**Other `system.*` / undocumented events you WILL receive** (emitted in prod, not always in the docs — handle them):

- **`system.stream_interrupted`** — the server cut the stream before `processing.finished` (carries `genie_run_id`, `last_seq_num`, `reason`, `retry_after_ms`). This is the **one event your client must react to** to start recovery: stop waiting on the dead stream and fall back to polling `GET /conversations/$CID` (state) + `GET …/events?since_created_at=…` (and `/messages` for the final answer) until `idle`. On long/agentic turns you *will* hit this.
- **`skill.stopped`** — a terminal variant alongside `skill.completed`; treat it the same (the skill finished). Don't leave a chip stuck "running" because you only matched `completed`.
- **`system.ping`** while parked on a VUA connection means nothing is coming on this stream (see §4a) — drop to `/messages` polling.

---

## 7. Double-confirmation interaction with `requires_user_confirmation`

The trigger's `requires_user_confirmation: true` is the **runtime gate** — it forces the genie to pause and emit `skill.confirmation_required` before invoking the action.

But if the skill's `description` (or the genie's instructions) tells the LLM to "always confirm details with the user before submitting" (as the HR Concierge does), the LLM **also** asks the user in chat first — *before* it even tries to invoke the skill.

End result: the user may see TWO confirmations:

1. **In-chat confirmation** (LLM-driven): "Just to confirm, you want PTO from Nov 1 to Nov 3?"
2. **Approval card** (runtime-gated): the structured `skill.confirmation_required` event with the parameters card.

For a clean UX, pick one:

- **In-chat only:** remove "always confirm" from the description; rely on `requires_user_confirmation: true` to pause and show a structured card.
- **Approval card only:** remove `requires_user_confirmation: true`; rely on the LLM's instructions for natural-language confirmation.

The HR Concierge example currently has both for demonstration — useful to see in isolation, awkward in production.

---

## 8. Rendering events in the UI — visual patterns

Translating the SSE event stream into a chat UI that feels live and trustworthy. These are the patterns that work in production; the parent repo's `src/public/embed.js` is a reference implementation.

### 8.1 Skill-card lifecycle (the most important visual)

For every skill invocation, render **one card** that lives across all the events for that call. Update it in place rather than appending separate items — the user sees one tile transition through states, not a noisy event log.

**Important: `skill.running` and `skill.completed` events typically DO NOT carry a `call_id`.** They only have `skill_name` and `skill_id` (in the form `recipe:<numeric_id>`). To track a card across the running → completed transition, key it by `skill_name` instead — or fall back to `skill_name` when `call_id` is absent. Only `skill.confirmation_required` is guaranteed to include `call_id`.

**Parallel tool calls emit ONE `skill.running` but N `skill.completed`.** When the agent fires several tools at once, you'll see a single `skill.running` (for just one of the skills) followed by a `skill.completed` for *each* skill — the other parallel skills never emit a `running` event. Verified against prod. If you key cards by `skill_name`, a `skill.completed` will arrive for a card that was never created. **Handle it:** on any `skill.completed`/`skill.stopped`/`skill.failed` whose `skill_name` has no existing card, synthesize the card (in `running` then immediately the terminal state) so every parallel call is represented. Don't assume running-precedes-completed.

The reference widget at `workato-genie-widget/src/public/embed.js` groups consecutive skill events under a single titled block (rendered as "Skills run" — a Slack-style plan/task pattern). Each task within the block has a status icon, name, status text, and duration. You can call your equivalent "Plan", "Activity", "Steps" — pick whatever fits your product's voice.

```
              ┌─────────────────────────────────┐
skill.running │ ● Get PTO Balance   Running…    │   purple, dot pulses
              └─────────────────────────────────┘
                              │
                              ▼
              ┌─────────────────────────────────┐
skill.completed │ ✓ Get PTO Balance   Done  0.4s│   green, dot static
              └─────────────────────────────────┘
```

Required state per card:
- `name` — from `skill_name` on the event
- `status` — running | completed | failed | awaiting
- `timing` — track `Date.now()` at running, diff on completed
- `error` — populated on failed
- `parameters` — populated on confirmation_required (the LLM-resolved args)

Color palette that maps to intent:
| Status | Bg | Border | Dot |
|---|---|---|---|
| running | purple-50 (#faf5ff) | purple-300 | accent, pulse animation |
| completed | green-50 (#f0fdf4) | green-300 | green-600, static |
| failed | red-50 (#fef2f2) | red-300 | red-600, static |
| awaiting | amber-50 (#fffbeb) | amber-300 | amber-500, pulse animation |

### 8.1a Native knowledge-base retrieval is INVISIBLE — use a recipe skill if you need it shown

A genie can answer from an **attached Knowledge Base** two ways, and they differ sharply in observability:
- **Built-in / native retrieval (Enterprise Search, RAG):** emits **no event at all** — not on the stream, not in `/events`. Verified: the genie cited the exact KB passage yet the stream was only `processing.started → agent.message → processing.finished`. You **cannot** show a "checked the knowledge base" chip or cite which docs grounded the answer.
- **A recipe skill that searches the KB** (a `workato_skill` recipe doing the lookup): emits the normal `skill.running` / `skill.completed`, so it's visible and auditable.

**Implication for builders:** if the UX or audit trail needs the KB lookup to be *visible* (e.g. a "grounded in policy X" chip, or a governance trail), route it through a **recipe skill**, not native retrieval. If you only care about the answer, native retrieval is simpler but silent.

### 8.2 Approval card — show parameters, not just buttons

When `skill.confirmation_required` arrives, render the **same skill-card** in `awaiting` state but expand it with:

1. The resolved parameters (`skill_parameters` field) — as a key/value list. Users need to verify what the LLM actually wants to submit, not just trust the skill name.
2. **Two buttons**: Approve (filled, positive color) and Reject (outline, neutral). Don't put them inline as small icons — they need visual weight.
3. After Approve: card transitions back to `running`, status text changes to "Running…", buttons disappear.
4. After Reject: card transitions to `failed`, status text shows "Rejected", buttons disappear.

```
┌─────────────────────────────────────────────────┐
│ ● Submit Time Off Request    Needs your approval│
│                                                 │
│  start_date    2026-11-03                       │
│  end_date      2026-11-07                       │
│  leave_type    pto                              │
│  notes         (none)                           │
│                                                 │
│  ┌─────────┐  ┌────────┐                        │
│  │ Approve │  │ Reject │                        │
│  └─────────┘  └────────┘                        │
└─────────────────────────────────────────────────┘
```

Implementation sketch:
```js
function renderConfirmation(ev) {
  const card = upsertSkillCard(ev.call_id, ev.skill_name, "awaiting");
  // Add params block
  for (const [k, v] of Object.entries(ev.skill_parameters || {})) {
    card.querySelector(".params").append(paramRow(k, v));
  }
  // Add approve/reject row
  card.querySelector(".actions").append(
    button("Approve", () => resolve(ev.call_id, "approved")),
    button("Reject",  () => resolve(ev.call_id, "rejected", "User rejected"))
  );
}
```

### 8.2a If you POLL, don't rebuild the action card every tick (it eats clicks)

If your UI polls for events (rather than holding the SSE open in the browser), a common bug makes the **Approve / Connect button unclickable**: the render loop wipes and rebuilds the turn on every poll, so the interactive card is destroyed and recreated continuously. Symptoms: the card visibly **flashes** in DevTools, and clicks "don't register" / need multiple tries — because a click that lands during a rebuild hits a node that's being replaced. During a wait state (e.g. parked on a confirmation or a runtime connection) the poll mostly receives heartbeats, so you're re-rendering identical content dozens of times for nothing.

**Fix (any of these):**
- **Skip the re-render when the rendered content is unchanged** (diff against the last render) — the simplest fix; during a wait the content is identical so the card is never touched.
- **Render the interactive card into its own node** that the event-list re-render never overwrites (separate container, or insert-once + update-in-place).
- Either way, **never destroy-and-recreate a node the user is about to click.** This applies equally to the approval card and the Verified-User-Access "Connect" card.

### 8.3 Conversation state pill (optional but recommended)

Show the conversation's overall state somewhere in the top bar:
- **Idle** — green dot, "Ready"
- **Processing** — blue dot pulsing, "Thinking…"
- **Skill processing** — purple dot pulsing, "Running a skill…"
- **Awaiting approval** — amber dot pulsing, "Needs your approval"

Source of truth: derive from the last event, with a fallback to `GET /chat/conversations/{cid}` when reconnecting. State transitions:
- `processing.started` → blue
- `skill.running` → purple
- `skill.confirmation_required` → amber
- `processing.finished` → green

### 8.4 Agent messages

Treat `agent.message` like a chat bubble. Three things to watch for:

- **Dedupe**: keep a `Set` of seen `message_id` values. Sometimes the same message appears in both the SSE stream AND the `/messages` history endpoint when you reconnect.
- **Markdown is the default**: the `message` text is **almost always markdown** — bold, lists, links, occasional code blocks. Rendering it raw makes asterisks and hyphens look noisy. Either pull in a library (`marked`, `react-markdown`, `markdown-it`) or inline a small renderer (see `examples/simple-ui/index.html` for a ~25-line implementation that handles bold/italic/code/lists/links). The reference widget at `workato-genie-widget/src/public/embed.js` does the same.
- **CSS gotcha when adding markdown**: the chat-bubble style typically has `white-space: pre-wrap` for plain-text wrapping. That conflicts with block-level HTML — set `white-space: normal` on the markdown container so `<p>` and `<ul>` lay out properly.

### 8.4a Typing-bubble positioning

When the user submits a message, the widget typically shows three bouncing dots ("typing indicator") to acknowledge that the agent is working. Where to put them matters:

- **Above the skill blocks (naive)**: append the typing indicator right after the user's message. The skill activity then appears *below* the dots, which makes the dots look stale (the genie is clearly doing things, not "thinking").
- **Below the skill blocks (better)**: re-anchor the typing indicator to the bottom of the message list whenever you append anything else (skill block, system messages, etc.). The user sees: their message → live skill activity → typing dots → final agent reply replaces the dots.

Pattern:
```js
function appendKeepingTypingLast(node) {
  msgs.append(node);
  const typing = msgs.querySelector(".typing");
  if (typing && typing !== msgs.lastChild) msgs.append(typing);
}
```
Use this for every plan/task/agent-bubble append. Reference: `workato-genie-widget/src/public/embed.js → appendKeepingTypingLast`.

### 8.5 Empty result on `skill.completed`

The SSE `skill.completed` event typically does **not** carry the structured `result` — only `skill_name` and `skill_id`. The result is fed to the LLM internally; the UI sees it reflected in the next `agent.message`. So:

- Don't try to render `result` from the SSE event — it'll usually be empty.
- Instead, show the skill card transitioning to `completed` (visual feedback that work happened) and let the agent message carry the actual data.
- If you need the structured result for UI rendering (e.g. to show a stock chart from a "Get Quote" skill), fetch the recipe's job output via `GET /api/recipes/{recipe_id}/jobs/{job_id}` (server-side only — this is a Dev API endpoint).

### 8.6 Handling rejections gracefully

When the user clicks Reject, the agent's next `agent.message` quotes the `rejection_reason` verbatim:

> "You previously rejected this PTO submission (\"Rejected by user: User declined\"), so I did not submit a new request just now."

If you don't want the user's words echoed back to them, send a generic rejection_reason (`"User declined"`) or omit it entirely. Some UIs ask the user "why?" with a textarea before submitting reject — that's risky because anything they type becomes part of the next conversation turn.

### 8.7 Reference implementation

The parent repo `workato-genie-widget/src/public/embed.js` (functions `upsertSkillCard`, `renderConfirmation`, `resolveSkill`) implements all of the above. The simple-ui in this skill (`examples/simple-ui/index.html`) is a minimal version — about 80 lines of JS specifically for SSE event rendering.

---

## 9. ID format reference

A confusing source of bugs: different surfaces use different ID strings for the same resource.

| Surface | Skill | Recipe (underlying) |
|---|---|---|
| Dev API (`/api/agentic/skills`) | `skl-AaPDrEWp-rF9dch-CD` | `73227015` (numeric, as `provider_id`) |
| Headless SSE events | `recipe:73227015` (numeric with prefix) | n/a |
| Dev API recipes (`/api/recipes/{id}`) | n/a | `73227015` (numeric) |

When correlating "the skill the user just approved" back to a skill record:
- From SSE → parse the numeric part of `skill_id` (strip the `recipe:` prefix), or match by `skill_name`.
- From Dev API → `provider_id` on the skill record gives you the recipe ID.

Matching by `skill_name` is generally the safest cross-surface key.

## Multi-turn loops: poll `state`, read history, pull the trace

Verified live 2026-09-09 (NIAH multi-hop benchmark). Three rules for any
turn where the genie may search/loop:

1. **Idle signal is `result.state == "idle"`** on
   `GET /chat/conversations/{id}`. There is no `status` field — polling
   `status` returns `None` forever, the caller times out mid-loop, and
   reads the first intermediate message as final. (Bit us: the genie was
   still working; we scored it a failure at message 1 of 4.)
2. **A turn emits MULTIPLE `agent.message` events.** Intermediate ones are
   real progress notes ("Let me do a more targeted search"). The final
   answer is the LAST `source: "genie"` message — pull
   `GET /chat/conversations/{id}/messages` after idle, don't trust a
   single streamed snapshot.
3. **Authoritative execution record is the Dev-API trace:**
   `GET /api/agentic/genies/{gin}/conversations/{id}/events` (wraps under
   `"data"`). It shows every `tool_execution_started/completed` including
   the `enterprise_search` query strings and returned fragments — the only
   way to know WHY a genie gave up (loop too shallow vs. retrieval ranked
   the wrong document first). In one verified multi-hop turn: 2 searches,
   3 LLM calls, 2 agent messages — and the second search returned the
   ORIGIN document as the top fragment, which is why the genie gave up
   (correctly, given what it saw).
