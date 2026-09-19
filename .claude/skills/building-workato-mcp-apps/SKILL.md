---
name: building-workato-mcp-apps
description: "Step-by-step guide for building Workato MCP Apps from idea to production. Covers prerequisites, use case design, Workato recipe setup, MCP server configuration, connecting to Claude, MCP app HTML scaffold, CSP config, debug patterns, and production cleanup. Use when someone wants to build a new Workato MCP App, iterate on an existing one, debug an MCP app that is not firing or rendering correctly, or design the architecture for an MCP app use case. Keywords: MCP app, Workato, ext-apps, callTool, app.connect, MCP server, AI Hub, CSP domains, HTML scaffold, trigger tool, recipe, demo, internal tool, productivity, automation."
---

# Building Workato MCP Apps

# Purpose

This skill guides a builder through the complete lifecycle of a Workato MCP App: prerequisites, use case design, Workato recipe setup, MCP server configuration, connecting to Claude, HTML/JS app construction, debug, and production cleanup. It encodes patterns from multiple completed builds so each new build starts from a proven foundation.

An MCP App is an interactive HTML/JS interface that fires inside Claude chat when the LLM calls a specific tool. The app connects to the Workato MCP server via SDK, makes further tool calls independently, and handles the full interaction — no LLM involvement needed after launch.

**The pitch in one sentence:** "What used to take 20 minutes across 5 tabs happened in one sentence and one button click."

This skill works equally well for customer-facing demos and internal Workato productivity tools. The technical build is identical either way.

# Scope Boundaries

This skill:
- ✅ Walks through the full build: prerequisites through production-ready app
- ✅ Provides verified technical patterns for SDK setup, tool calls, CSP, and envelope parsing
- ✅ Produces a recipe spec, MCP server config block, HTML app scaffold, and production checklist
- ✅ Covers debugging for all known failure modes
- ✅ Applies to new builds and to iterations on existing apps
- ❌ Does not deploy to Workato — all Workato-side config is manual
- ❌ Does not generate Workato recipe JSON — produces pseudocode and field schemas
- ❌ Does not cover the MCP App Builder automation track (Workato Developer API MCP)

# Prerequisites

Before starting a build, confirm these are in place:

**Workato workspace:**
- AI Hub enabled (MCP Servers and MCP Apps must be available in the sidebar)
- Ability to create and run recipes with HTTP triggers
- Note: Workato-provided MCP App templates require CBP pricing (Skills/Genies tier). Custom MCP servers built from scratch work on standard Workato plans.

**Claude access:**
- Claude Pro, Team, or Enterprise plan on claude.ai — or API access with MCP support
- Ability to add MCP server connections (Settings > Integrations, or within a Claude Project)

**Skills needed:**
- Basic recipe building in Workato (HTTP trigger, data step, HTTP response action)
- Ability to write or read basic HTML and JavaScript — you do not need to write it from scratch, but you need to paste and edit it

If AI Hub is not in your Workato sidebar, contact your Workato admin or the BT team to request access.

# Core Workflow

Follow these steps in order. Do not skip Step 1 or Step 2 — both shape the entire build.

## Step 1: Establish the Mental Model

Before touching Workato, communicate this clearly to the builder:

**The trigger tool is a doorbell.** The LLM calls it once to launch the app. Once `app.connect()` resolves, the app makes all subsequent tool calls independently. The LLM is done. The app IS the interaction surface.

This changes how the trigger tool is designed: its parameter schema carries only what is needed to launch, not the full interaction payload. Detailed inputs are collected by the app's own UI.

## Step 2: Define the Use Case

Do not proceed without answers to these three questions:

**Trigger sentence** — one natural language sentence that causes the app to fire with no ambiguity. If the builder cannot write this sentence, the use case is not ready. Examples: "Show me troubleshooting steps for this ThinkPad." / "Find me espresso machines under $200."

**Demo moment** — the single thing that cannot be explained, only shown. Ask: what is the thing someone remembers after the call (or the session) ends?

**Purpose type** — is this a customer-facing demo or an internal Workato tool? Both are valid. The answer affects the data source choice and who the "end user" is.

Load `references/use-case-ideation.md` for use case brainstorming, demo diversity guidance, and the full build pipeline ranked by effort.

## Step 3: Design the Architecture

Every MCP app has exactly three components:

```
[Workato Recipe] <-> [MCP Server (tool definitions)] <-> [MCP App (HTML/JS UI)]
```

**Workato Recipe** — Data and logic layer. HTTP trigger endpoint, data source (real API or mock Data Table), output schema. This is what tools call.

**MCP Server** — Contract layer. Tool names, trigger descriptions (what the LLM reads to decide when and why to call), input/output schema. Config lives in AI Hub > MCP Servers.

**MCP App** — UI layer. HTML + JS, connected to MCP server via SDK. Config lives in AI Hub > MCP Apps. HTML is pasted into the app config manually.

Why Workato as middleware: (1) data source can be swapped inside the recipe without touching app code; (2) for customer demos, this makes the value concrete — the customer's data connects through Workato, not a custom backend they have to build themselves.

## Step 4: Build the Recipe (Mock-First Always)

**Rule: always mock first.** Build the recipe with a hardcoded JSON response before touching any real API auth. Get the server connected and the app rendering on fake data. Swapping to real data is one recipe change. Debugging auth before the UI works is 3-hour sessions.

**Mock approach:** Workato Data Table with rows shaped exactly like the real API's response schema. Name fields to match what the real API returns so app code requires zero changes at swap time.

**Recipe pseudocode:**
```
HTTP trigger (API key auth)
  → [query Data Table OR call external API]
  → format response as JSON
  → return via HTTP response action
```

**Output schema conventions:**
- Always return `items[]` as the primary array
- Include a `filters[]` or `filterMetadata[]` array alongside `items[]` if the app has dynamic filters — the exact field name should match whatever your recipe returns; the point is to let the data source tell the app which filter options are relevant rather than hardcoding them
- The tool I/O schema is visible in AI Hub > MCP Apps > [app] > Tool inputs and outputs — verify this matches before writing app code

## Step 5: Configure the MCP Server

In AI Hub > MCP Servers > Create (or edit existing):

**Tool name** — Workato derives the slug from the asset name. The convention varies by asset type:
- **API recipe tools** → lowercase underscored from the recipe name: `search_products`, `open_device_troubleshooter`
- **Skill tools** → underscore-joined but **preserves the original case** of the skill name. A skill named `Get Jira Issues` slugs as `Get_Jira_Issues`, not `get_jira_issues`.

**Always verify the actual slug** in AI Hub > MCP Apps > [app] > Tool inputs and outputs before writing `app.callServerTool()` calls — guessing the casing wastes hours.

**Tool description** — This is what the LLM reads to decide when to call. Make it an explicit trigger condition, not a capability description.
- Good: *"Call this when the user asks to search for, browse, or find products by name, category, or description."*
- Bad: *"Searches for products."*

**Critical distinction — recipe description vs trigger-step description.** Workato has two `description` fields and they are NOT interchangeable:
- The **recipe-level description** (set via `recipe_copilot_init_skill(description=...)` or `recipe_copilot_update_asset_metadata`) is what the MCP server exposes as the tool's description. **This is what Claude reads.**
- The **trigger step's `description` field** (set via `recipe_copilot_set_input_field(step=1, path="description", ...)`) is internal to Workato Genies. Not exposed via MCP.

Updating the wrong one means the LLM never sees your changes. Always update the recipe-level description to control LLM behavior at the MCP layer.

**Suppress post-render text summary.** When an MCP App handles the UI, Claude will by default still emit a text summary alongside the iframe — usually duplicated content and visual noise. Add a UI-rendering contract to the recipe description to stop this. Pattern:

> *Returns Jira issues with filter metadata. IMPORTANT — UI rendering contract: The result of this tool is rendered as an interactive MCP App (inline iframe) in the chat. The app IS the response. Do NOT list, summarize, restate, table-ify, or describe the returned items in your text reply. After calling this tool, your text reply should be empty or a one-line acknowledgement only.*

Apply to every tool whose output is shown in an interactive surface (modal, panel, sidebar). Without it, users see redundant text below the rendered app.

**Input parameters** — Keep the trigger tool's schema minimal. `query: string` is usually enough. The app collects detailed inputs through its own UI.

**Recipe must be running** before the tool can be tested.

**No native clone feature.** Duplicating an MCP server requires manual recreation: AI Hub > MCP Servers > Create, rebuild tool definitions by hand. Import package errors showing "duplicate in different folder": delete the conflicting connection at `Home/[folder]` first, then reimport or use Overwrite.

### Connect the MCP Server to Claude

After saving the MCP server in AI Hub, connect it to Claude so tools are callable:

1. In Claude.ai or Claude Desktop: Settings > Connectors > Add custom connector. Paste the server URL from AI Hub.
2. Or inside a Claude Project: Project settings > Add MCP server.
3. For Claude Code (CLI): `claude mcp add <name> --transport sse "<url>"`. **Use `sse` transport, not `http`** — Workato's MCP endpoint speaks streamable HTTP / Server-Sent Events. The plain `http` transport will register the connector but fail every reconnect with token-rejection errors.
4. Authentication: Workato Identity OAuth triggers automatically on first connection (browser-redirect flow). If using recipe-level API key auth, enter the key when prompted.
5. **Test the connection:** Ask Claude "What tools do you have available?" or "List your MCP tools." Claude should name your tool(s) by the exact names defined in the MCP server.

If tools do not appear: confirm the recipe is running, the MCP server is saved in AI Hub, and authentication succeeded. A tool that is not listed cannot be called regardless of how the HTML is written.

**VUA Required + URL token — critical security gotcha.** The MCP server URL Workato gives you contains a `?wkt_token=...` query param. This token bypasses VUA enforcement for non-VUA tools. The moment you flip `VUA Required: Yes` on ANY tool on the server:

- The server URL you distribute to clients must NOT include the `wkt_token` query param
- Clients authenticate via Workato Identity OAuth instead (browser flow on first connect)
- Mixing the two (token URL + VUA tools) leaves the VUA tools failing while non-VUA tools keep working — confusing to debug

Workato's UI may default `VUA Required: Yes` when re-attaching tools via the Skill picker. Verify the column in `mcp_server_get` output after every Tools-tab save. Mutation tools (`Update_*`, `Add_*`) are usually the right candidates for VUA; trigger/list tools are usually not.

## Step 6: Build the MCP App HTML

Give the builder `assets/html-scaffold-template.html` as their starting point. Sections marked `[CUSTOMIZE]` must be updated per use case.

**Core patterns every app requires:**

### SDK Setup
```javascript
// type="module" on the script tag is required — top-level await does not work without it
import {App} from 'https://cdn.jsdelivr.net/npm/@modelcontextprotocol/ext-apps@1.3.1/dist/src/app-with-deps.js';
const app = new App({name: 'App Name', version: '1.0.0'});
app.ontoolresult = () => {};
await app.connect();
```
`app.connect()` handles auth, context, and session. It must be awaited before any tool calls or UI rendering. Check `cdn.jsdelivr.net` for the current SDK version — pin to the latest stable release.

### Tool Call Pattern (Workato Envelope Parsing)
```javascript
// ext-apps SDK 1.3.x. The older app.callTool() API does not exist.
const raw = await app.callServerTool({ name: 'tool_name', arguments: { param: value } });

// Prefer the typed result. Fall back to text-envelope parsing for older shapes.
let parsed = raw?.structuredContent;
if (!parsed) {
  const text = raw?.content?.[0]?.text;
  parsed = text ? JSON.parse(text) : raw;
}

// Workato Skills wrap workflow_return_result output under a `result` key.
// API recipes do not. This line normalizes both shapes.
const result = parsed?.result ?? parsed;
```
Two wrapping layers, both easy to miss:
1. **MCP envelope** — `raw.structuredContent` (typed) or `raw.content[0].text` (JSON string). Reading `raw.items` directly returns undefined.
2. **Workato Skill wrapper** — `workflow_return_result` adds a `{result: ...}` layer around the payload. API recipes do not. The `parsed?.result ?? parsed` line handles both.

### CSP Configuration (critical)
All four CSP fields in the MCP app config — Connect domains, Resource domains, Frame domains, Base URI domains — must contain **every external domain the app touches**. Missing any one of the four silently breaks external scripts or images.

### Debug Panel
Add a visible debug element during development. When going to production: delete the CSS block, delete the HTML element, replace `log()` with `function log() {}`. Then check for orphaned CSS rules referencing the removed debug class names.

Load `references/html-scaffold-patterns.md` for: the full CSP domain list, the dynamic filter pattern, and state persistence wiring.

## Step 6b: Agentic Enrichment (when the LLM helps prioritize)

Skip this step for basic CRUD apps. Use it when your app shows the user something that benefits from LLM judgment — triage scoring, summarization, classification, priority re-ranking — applied to a batch of items returned by the upstream data source.

Pattern: the recipe loops over each item, calls an LLM to score it, and returns the enriched array. The MCP App renders score badges + reason text alongside the raw data.

**Critical design rules** (each one is the answer to a real bug encountered in field builds):

- **Compute deterministic facts in Ruby, judgment in the LLM.** LLMs hallucinate date math. Compute `days_since_updated`, customer-label presence, and similar facts in the recipe; embed them as labeled values in the prompt; ask the LLM only for the score + reason.
- **Banded scoring rubric, not open-ended.** "Score 0-10" produces flat 7-8 distributions. Use base-by-recency + named adjustments — the model anchors on the band and reasons against criteria.
- **Hard rules with thresholds.** "If days > 30 AND not security/customer, score MUST be ≤ 4." Otherwise the model rubber-stamps high-priority stale items.
- **Reason-format constraint.** Force the model to cite specific signals (days count, applied adjustment). Without it, every reason becomes "high priority and recently updated" — templated noise.
- **Skip the LLM for unambiguous cases.** Security bugs auto-9, stale-no-signals auto-3, etc. Only call the LLM for the borderline 4-30 day band. Cuts 60-80% of calls and keeps total runtime under MCP's ~30s timeout window.
- **Error-handling fallback.** Wrap each LLM call in `error_handling` with a priority-based fallback score. One bad call shouldn't kill the batch.
- **OpenAI `gpt-4o-mini` is the reliable workhorse.** Anthropic via Workato's custom connector has been intermittent due to upstream Ruby SDK validation issues; default to OpenAI until that's resolved.

**Load `references/agentic-enrichment-patterns.md`** when implementing — it has the foreach + LLM + parse + insert pattern, the banded prompt rubric, the skip-unambiguous JQL ternary, and the fallback error-handling block, all field-tested.

## Step 7: Handle State and Persistence

MCP apps run in sandboxed iframes. Chat history persists; **app internal state does not.** Saved items, filters, form inputs — all reset on navigation.

If session persistence matters, wire three Workato tools: `save_session_state`, `load_session_state`, `list_saved_sessions`. State lives in Airtable or Postgres via Workato recipes. This also works well as a demo moment: "watch what happens when I navigate away and come back."

## Step 8: Debug and Production Cleanup

Load `references/common-failures.md` when:
- App is not firing (tool description or recipe issue)
- External scripts fail to load (CSP issue)
- Tool call returns nothing or wrong shape (envelope parsing issue)
- HTML not persisting after save (content-specific known issue)
- App fires but renders blank (async timing or SDK connection issue)

**Production-ready checklist:**
- [ ] Debug panel removed: CSS block, HTML element, `log()` replaced with no-op
- [ ] CSS spot-checked for orphaned rules referencing removed debug class names
- [ ] All four CSP fields contain the same complete domain list
- [ ] Tool description is an explicit trigger condition, not a vague capability label
- [ ] Recipe running and tested end-to-end with mock data
- [ ] MCP server connected to Claude and tools confirmed visible
- [ ] HTML persistence confirmed: paste, save, reload, verify field still populated

# Output Format

When guiding a build, produce artifacts in this order. Deliver each when the builder confirms the prior step is complete.

**After Step 2 (use case):**
```
Trigger sentence: [exact sentence]
Demo moment: [the thing that makes this memorable]
Purpose: [customer demo / internal tool]
Data source: [what system or API holds the data]
```

**After Step 3 (architecture):**
```
Architecture:
  Recipe: [name] — HTTP trigger → [data step] → JSON response
  MCP Server tools: [tool name(s)]
  MCP App: [what the UI shows and does]
  Workato's role: [why it belongs in the middle for this use case]
```

**After Step 4 (recipe):**
```
Recipe: [tool name]
Trigger: HTTP (API key auth)
Steps: [pseudocode, numbered]
Output schema: { items: [...] }
Mock data source: [Data Table name / field list]
```

**After Step 5 (MCP server + connection):**
```
Tool name: [name]
Tool description: [exact text for the LLM]
Input parameters: [name: type — description]
Connection test: ask Claude "what tools do you have?" — expected: [tool name] listed
```

**After Step 6 (HTML):** Provide the full contents of `assets/html-scaffold-template.html` with all `[CUSTOMIZE]` sections filled in for the specific use case. Remind the builder to paste this HTML into the MCP App config in AI Hub > MCP Apps > [app] > App Code.

**After Step 8 (production):** Confirm every item on the production-ready checklist is cleared.

# Key Principles

- **Mock-first always.** No exceptions. Real API auth problems are solvable after the UI works, not before.
- **Trigger tool is a doorbell.** The app takes over at `app.connect()`. Design the trigger schema accordingly — minimal params, not a full payload.
- **Trigger tool returns a doorbell-shaped *response* too.** The LLM only needs to know the app launched, not what's in it. Return `{success, count, hint}` from the trigger; have the app fetch the rich payload via a separate tool. Cuts LLM context by 10–100× on list/detail apps and unlocks the `_meta.ui.visibility: ["app"]` annotation for hard isolation. See `html-scaffold-patterns.md` → Token-efficient tool design.
- **CSP: all four fields, same list.** Every external domain goes in Connect, Resource, Frame, and Base URI. Missing one silently breaks things.
- **Parse the Workato envelope.** Prefer `raw.structuredContent` (typed result). Fall back to `JSON.parse(raw.content[0].text)`. Then unwrap `.result` for Skill-backed tools. Treating `raw` as your data object produces silent undefined values.
- **Use `app.callServerTool({name, arguments})`**, not `app.callTool()`. The latter does not exist in ext-apps 1.3.x. Tool arguments go in the `arguments` field, not as a second positional parameter.
- **`type="module"` is required.** Top-level `await app.connect()` only works inside a module script. Do not strip this attribute.
- **Confirm tools are visible in Claude before writing HTML.** A tool that Claude cannot see will never fire, regardless of how the app code is written.
- **Await `app.connect()` before anything.** Rendering or calling tools before the SDK connection resolves fails silently.
- **MCP transport for Claude Code is `sse`, not `http`.** Workato's MCP endpoint speaks SSE / streamable-HTTP. Using `--transport http` registers the connector but auth fails on every reconnect. `claude mcp add <name> --transport sse "<url>"` is the working incantation.
- **VUA Required tools require Workato Identity, not the URL token.** The moment any tool on a server has `VUA Required: Yes`, distribute the server URL WITHOUT the `?wkt_token=...` query param. Mixing token-URL with VUA tools breaks the VUA tools silently. See Step 5.
- **MCP client timeout is ~30s.** Per-item LLM foreach loops easily exceed it. Use the `agentic-enrichment-patterns.md` skip-unambiguous trick to keep runtime under 10s.
- **Fullscreen API is blocked in MCP iframes.** Use the CSS expand toggle (`max-height: 600px` ↔ `100vh`) pattern instead. See `html-scaffold-patterns.md` → Expand pattern.
- **Dev API for recipe start/stop:** `PUT https://www.workato.com/api/recipes/{id}/{start|stop}` with `Authorization: Bearer <token>`. The clean workaround for the running-recipe lock that blocks `recipe_copilot_push` and `recipe_copilot_update_asset_metadata` — programmatic stop → push → start in one cycle without UI.

# Reference Files

| File | Load when |
|---|---|
| `references/use-case-ideation.md` | Brainstorming use cases, picking next build, planning demo portfolio diversity |
| `references/html-scaffold-patterns.md` | CSP domain list, dynamic filter pattern, multi-tool patterns, expand toggle, keyboard ergonomics, token-efficient design, state persistence |
| `references/agentic-enrichment-patterns.md` | LLM scoring / triage / classification — banded rubric, deterministic facts in Ruby, skip-unambiguous optimization, error handling, LLM connector choice |
| `references/common-failures.md` | App not firing, scripts not loading, wrong tool call shape, HTML not persisting, SSE vs HTTP transport, VUA+token mismatch, MCP timeout, fullscreen blocked, Ruby formula validator surface |
